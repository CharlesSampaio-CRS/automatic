from novadax import RequestClient as NovaClient
from datetime import datetime
import connection

# Constantes
MIN_VALUE_PER_SYMBOL = 25
SYMBOLS = ["DOG_BRL", "MOG_BRL", "BABYDOGE_BRL", "PEPE_BRL", "SHIB_BRL"]
CSV_FILE_NAME = 'orders.csv'

db = connection.connection_mongo("Assets")

class NovaDaxClient:
    def __init__(self, api_key, api_secret):
        self.client = NovaClient(api_key, api_secret)
    
    def get_non_zero_sorted_assets(self):
        result = self.client.get_account_balance()
        data = result['data']
        non_zero_assets = [item for item in data if float(item['balance']) > 1]
        return sorted(non_zero_assets, key=lambda x: float(x['balance']), reverse=True)
    
    def get_brl_avaliable(self):
        response = self.client.get_account_balance_current()['data']['assets']
        brl_asset = next((asset for asset in response if asset['currency'] == 'BRL'), None)
        return float(brl_asset['available']) if brl_asset else 0 

    def get_symbol_variation(self, symbols):
        variations = []
        for symbol in symbols:
            try:
                ticker = self.client.get_ticker(symbol=symbol)
                if ticker.get('code') == 'A10000':
                    last_price = float(ticker['data']['lastPrice'])
                    opening_price24h = float(ticker['data']['open24h'])
                    variacao_24h = ((last_price - opening_price24h) / opening_price24h) * 100
                        
                    variations.append({
                        "symbol": symbol,
                        "variation_24h": round(variacao_24h, 2)
                    })
                else:
                    print(f"Erro na resposta da API para {symbol}: {ticker.get('message', 'Unknown error')}")
            except Exception as e:
                print(f"Erro ao buscar dados para {symbol}: {e}")

        sorted_variations = sorted(variations, key=lambda x: x['variation_24h'])
        return sorted_variations
    
    def create_order(self):
        brl = self.get_brl_avaliable()
        if brl < MIN_VALUE_PER_SYMBOL:
            return {"Saldo insuficiente para abrir ordens": round(brl, 2)}
        
        symbol_values_by_variations_asc = self.get_symbol_variation(SYMBOLS)

        symbol_values = {symbol['symbol']: {'value': 0, 'date': None, 'variation': round(symbol['variation_24h'], 2)} for symbol in symbol_values_by_variations_asc}

        while brl >= MIN_VALUE_PER_SYMBOL:
            for symbol in symbol_values:
                if brl < MIN_VALUE_PER_SYMBOL:
                    break
                symbol_values[symbol]['value'] += MIN_VALUE_PER_SYMBOL
                brl -= MIN_VALUE_PER_SYMBOL
                symbol_values[symbol]['date'] = datetime.now()

        for symbol, asset in symbol_values.items():
            if asset['value'] > 0:
                self.create_and_send_order(asset, symbol)
                self.save_to_db(symbol, asset['value'], asset['date'], asset['variation'])

        symbol_values_with_value = {symbol: asset for symbol, asset in symbol_values.items() if asset['value'] > 0}

        return {"assets": symbol_values_with_value, "restMoney": brl}
   
    def save_to_db(self, symbol, value, date, variation):
        order_data = {
            "symbol": symbol,
            "value": value,
            "date": date,
            "variation": variation
        }

        try:
            db.orders.insert_one(order_data) 
            print(f"Order saved to database: {order_data}")
        except Exception as e:
            print(f"Erro ao salvar no banco de dados: {e}")

    def create_and_send_order(self, asset, symbol):
        self.client.create_order(
            symbol=symbol, 
            _type='MARKET', 
            side='BUY', 
            value=asset['value']
        )
