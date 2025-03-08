from novadax import RequestClient as NovaClient
from datetime import datetime
import database.connection as connection

MIN_VALUE_PER_CREATE_ORDER = 80
MIN_VALUE_PER_SYMBOL = 25
SYMBOLS = ["NC_BRL", "GROK_BRL"]

STATUS_SUCCESS = "SUCCESS"
STATUS_ERROR = "ERROR"

ERROR_INSUFFICIENT_FUNDS = "Insufficient funds to place orders"
ERROR_API_RESPONSE = "API response error"
ERROR_DB_SAVE = "Error saving to the database"
ERROR_BALANCE_FETCH = "Error fetching available balance"

db = connection.connection_mongo("Assets")

class NovaDaxClient:
    def __init__(self, api_key, api_secret):
        self.client = NovaClient(api_key, api_secret)

    def get_brl_available(self):
        try:
            assets = self.client.get_account_balance_current()['data']['assets']
            brl_asset = next((asset for asset in assets if asset['currency'] == 'BRL'), None)
            available = float(brl_asset['available']) if brl_asset else 0
            return round(available, 2)
        except Exception as e:
            print(f"{ERROR_BALANCE_FETCH}: {e}")
            return 0

    def get_non_zero_sorted_assets(self):
        try:
            assets = self.client.get_account_balance_current()['data']['assets']
            non_zero_assets = [item for item in assets if float(item['balance']) > 1]
            return sorted(non_zero_assets, key=lambda x: float(x['balance']), reverse=True)
        except Exception as e:
            print(f"Error fetching assets: {e}")
            return []

    def get_total_assets_in_brl(self):
        try:
            assets = self.get_non_zero_sorted_assets()
            total_in_brl = 0.0

            for asset in assets:
                currency = asset['currency']
                balance = float(asset['balance'])

                if currency == 'BRL':
                    total_in_brl += balance
                else:
                    total_in_brl += self.convert_to_brl(currency, balance)

                available = self.get_brl_available()
                assets_coin = self.get_non_zero_sorted_assets()

            return {"total_assets_brl": round(total_in_brl - available, 2), "available_brl": available, "total_brl": round(total_in_brl + available, 2), "date": datetime.now().astimezone(), "tokens": assets_coin}
        
        except Exception as e:
            print(f"Error calculating total assets: {e}")
            return 0

    def convert_to_brl(self, currency, balance):
        symbol = f"{currency}_BRL"
        try:
            ticker = self.client.get_ticker(symbol=symbol)
            if ticker.get('code') == 'A10000':
                last_price = float(ticker['data']['lastPrice'])
                return balance * last_price
        except Exception as e:
            print(f"Error getting price for {symbol}: {e}")
        return 0

    def get_symbol_variations(self):
        variations = []
        for symbol in SYMBOLS:
            variation = self.get_symbol_variation(symbol)
            if variation:
                variations.append(variation)
        return sorted(variations, key=lambda x: x['variation_24h'])

    def get_symbol_variation(self, symbol):
        try:
            ticker = self.client.get_ticker(symbol=symbol)
            if ticker.get('code') == 'A10000':
                last_price = float(ticker['data']['lastPrice'])
                opening_price24h = float(ticker['data']['open24h'])
                variation_24h = ((last_price - opening_price24h) / opening_price24h) * 100
                return {"symbol": symbol, "variation_24h": round(variation_24h, 2)}
            else:
                print(f"{ERROR_API_RESPONSE} for {symbol}: {ticker.get('message', 'Unknown error')}")
        except Exception as e:
            print(f"Error fetching data for {symbol}: {e}")
        return None

    def create_order(self):
        brl_balance = self.get_brl_available()
        if brl_balance < MIN_VALUE_PER_CREATE_ORDER:
            error_message = f"{ERROR_INSUFFICIENT_FUNDS}: Available balance: R$ {brl_balance:.2f}"
            print(error_message)
            return {"error": ERROR_INSUFFICIENT_FUNDS, "available_balance": round(brl_balance, 2)}

        symbol_variations = self.get_symbol_variations()
        symbol_orders = self.initialize_symbol_orders(symbol_variations)

        self.allocate_funds_to_orders(brl_balance, symbol_orders)
        self.execute_orders(symbol_orders)
        print("Order executed.")

    def initialize_symbol_orders(self, symbol_variations):
        return {item['symbol']: {'value': 0, 'date': None, 'variation': item['variation_24h']} for item in symbol_variations}

    def allocate_funds_to_orders(self, brl_balance, symbol_orders):
        while brl_balance >= MIN_VALUE_PER_SYMBOL:
            for symbol in symbol_orders:
                if brl_balance < MIN_VALUE_PER_SYMBOL:
                    break
                symbol_orders[symbol]['value'] += MIN_VALUE_PER_SYMBOL
                brl_balance -= MIN_VALUE_PER_SYMBOL
                symbol_orders[symbol]['date'] = datetime.utcnow()

    def execute_orders(self, symbol_orders):
        for symbol, order in symbol_orders.items():
            if order['value'] > 0:
                success = self.create_and_send_order(symbol, order['value'])
                status = STATUS_SUCCESS if success else STATUS_ERROR
                self.save_to_db(symbol, order['value'], order['date'], order['variation'], status)

    def create_and_send_order(self, symbol, value):
        try:
            self.client.create_order(symbol=symbol, _type='MARKET', side='BUY', value=value)
            return True
        except Exception as e:
            print(f"Error creating order for {symbol}: {e}")
            return False

    def save_to_db(self, symbol, value, date, variation, status):
        order_data = {"symbol": symbol, "value": value, "date": date, "variation": variation, "status": status}
        try:
            db.orders.insert_one(order_data)
            return f"Order saved to database: {order_data}"
        except Exception as e:
            print(f"{ERROR_DB_SAVE}: {e}")
