from novadax import RequestClient as NovaClient
from datetime import datetime
import connection

# Constantes
MIN_VALUE_PER_SYMBOL = 25
SYMBOLS = ["DOG_BRL", "MOG_BRL", "BABYDOGE_BRL"]

# Status da Ordem
STATUS_SUCCESS = "SUCCESS"
STATUS_ERROR = "ERROR"

# Mensagens de Erro
ERROR_INSUFFICIENT_FUNDS = "Saldo insuficiente para abrir ordens"
ERROR_API_RESPONSE = "Erro na resposta da API"
ERROR_DB_SAVE = "Erro ao salvar no banco de dados"
ERROR_BALANCE_FETCH = "Erro ao buscar saldo disponível"

# Conexão com o MongoDB
db = connection.connection_mongo("Assets")

class NovaDaxClient:
    def __init__(self, api_key, api_secret):
        self.client = NovaClient(api_key, api_secret)

    # 1. MÉTODOS PARA OBTER SALDOS E ATIVOS
    def get_brl_available(self):
        """Retorna o saldo disponível em BRL."""
        try:
            assets = self.client.get_account_balance_current()['data']['assets']
            brl_asset = next((asset for asset in assets if asset['currency'] == 'BRL'), None)
            return float(brl_asset['available']) if brl_asset else 0
        except Exception as e:
            print(f"{ERROR_BALANCE_FETCH}: {e}")
            return 0

    def get_non_zero_sorted_assets(self):
        """Retorna ativos com saldo maior que 1, ordenados por saldo decrescente."""
        try:
            assets = self.client.get_account_balance_current()['data']['assets']
            non_zero_assets = [item for item in assets if float(item['balance']) > 1]
            return sorted(non_zero_assets, key=lambda x: float(x['balance']), reverse=True)
        except Exception as e:
            print(f"Erro ao buscar ativos: {e}")
            return []

    def get_total_assets_in_brl(self):
        """Calcula o valor total dos ativos convertidos para BRL."""
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

            print(f"Total dos ativos em BRL: R$ {total_in_brl:.2f}")
            return total_in_brl
        except Exception as e:
            print(f"Erro ao calcular total dos ativos: {e}")
            return 0

    def convert_to_brl(self, currency, balance):
        """Converte um ativo específico para BRL usando o preço atual."""
        symbol = f"{currency}_BRL"
        try:
            ticker = self.client.get_ticker(symbol=symbol)
            if ticker.get('code') == 'A10000':
                last_price = float(ticker['data']['lastPrice'])
                return balance * last_price
        except Exception as e:
            print(f"Erro ao obter preço para {symbol}: {e}")
        return 0

    # 2. MÉTODO PARA OBTER VARIAÇÕES DE PREÇOS
    def get_symbol_variations(self):
        """Retorna as variações de preço em 24h dos símbolos especificados."""
        variations = []
        for symbol in SYMBOLS:
            variation = self.get_symbol_variation(symbol)
            if variation:
                variations.append(variation)
        return sorted(variations, key=lambda x: x['variation_24h'])

    def get_symbol_variation(self, symbol):
        """Obtém a variação de preço de um símbolo específico."""
        try:
            ticker = self.client.get_ticker(symbol=symbol)
            if ticker.get('code') == 'A10000':
                last_price = float(ticker['data']['lastPrice'])
                opening_price24h = float(ticker['data']['open24h'])
                variation_24h = ((last_price - opening_price24h) / opening_price24h) * 100
                return {"symbol": symbol, "variation_24h": round(variation_24h, 2)}
            else:
                print(f"{ERROR_API_RESPONSE} para {symbol}: {ticker.get('message', 'Unknown error')}")
        except Exception as e:
            print(f"Erro ao buscar dados para {symbol}: {e}")
        return None

    # 3. MÉTODO PRINCIPAL PARA CRIAR ORDENS
    def create_order(self):
        """Cria ordens de compra com base no saldo disponível e variações de preço."""
        brl_balance = self.get_brl_available()
        if brl_balance < MIN_VALUE_PER_SYMBOL:
            error_message = f"{ERROR_INSUFFICIENT_FUNDS}: Saldo disponível: R$ {brl_balance:.2f}"
            print(error_message)
            return {"error": ERROR_INSUFFICIENT_FUNDS, "available_balance": round(brl_balance, 2)}

        symbol_variations = self.get_symbol_variations()
        symbol_orders = self.initialize_symbol_orders(symbol_variations)

        self.allocate_funds_to_orders(brl_balance, symbol_orders)
        self.execute_orders(symbol_orders)

        remaining_balance = self.get_brl_available()
        return {"assets": symbol_orders, "restMoney": round(remaining_balance, 2)}

    # 4. MÉTODOS AUXILIARES PARA ORDENS
    def initialize_symbol_orders(self, symbol_variations):
        """Inicializa os símbolos com valores zerados e variações."""
        return {item['symbol']: {'value': 0, 'date': None, 'variation': item['variation_24h']} for item in symbol_variations}

    def allocate_funds_to_orders(self, brl_balance, symbol_orders):
        """Distribui fundos igualmente entre os símbolos selecionados."""
        while brl_balance >= MIN_VALUE_PER_SYMBOL:
            for symbol in symbol_orders:
                if brl_balance < MIN_VALUE_PER_SYMBOL:
                    break
                symbol_orders[symbol]['value'] += MIN_VALUE_PER_SYMBOL
                brl_balance -= MIN_VALUE_PER_SYMBOL
                symbol_orders[symbol]['date'] = datetime.utcnow()

    def execute_orders(self, symbol_orders):
        """Executa as ordens de compra e salva no banco de dados."""
        for symbol, order in symbol_orders.items():
            if order['value'] > 0:
                success = self.create_and_send_order(symbol, order['value'])
                status = STATUS_SUCCESS if success else STATUS_ERROR
                self.save_to_db(symbol, order['value'], order['date'], order['variation'], status)

    def create_and_send_order(self, symbol, value):
        """Envia a ordem de compra para a API da NovaDAX."""
        try:
            self.client.create_order(symbol=symbol, _type='MARKET', side='BUY', value=value)
            return True
        except Exception as e:
            print(f"Erro ao criar ordem para {symbol}: {e}")
            return False

    def save_to_db(self, symbol, value, date, variation, status):
        """Salva a ordem no banco de dados."""
        order_data = {"symbol": symbol, "value": value, "date": date, "variation": variation, "status": status}
        try:
            db.orders.insert_one(order_data)
            print(f"Order saved to database: {order_data}")
        except Exception as e:
            print(f"{ERROR_DB_SAVE}: {e}")

