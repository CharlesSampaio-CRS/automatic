import ccxt
from datetime import datetime
import sys
import os

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.config.bot_config import MIN_VALUE_PER_CREATE_ORDER, MIN_VALUE_PER_SYMBOL, SYMBOLS, BASE_CURRENCY

# Importa estratégias de compra e venda
from src.clients.buy_strategy import BuyStrategy
from src.clients.sell_strategy import SellStrategy

# Importa conexão do MongoDB
try:
    from src.database.mongodb_connection import connection_mongo
    db = connection_mongo("Assets")
    print("✓ MongoDB conectado com sucesso")
except Exception as e:
    db = None
    print(f"⚠ MongoDB não disponível: {e}")

STATUS_SUCCESS = "SUCCESS"
STATUS_ERROR = "ERROR"

ERROR_INSUFFICIENT_FUNDS = "Insufficient funds to place orders"
ERROR_API_RESPONSE = "API response error"
ERROR_DB_SAVE = "Error saving to the database"
ERROR_BALANCE_FETCH = "Error fetching available balance"

# db = None  # Mock do banco de dados (desabilitado por enquanto)

class MexcClient:
    def __init__(self, api_key, api_secret):
        """
        Inicializa o cliente MEXC usando ccxt
        Carrega estratégias de compra e venda
        """
        self.client = ccxt.mexc({
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'spot',  # Trading spot
            }
        })
        
        # Inicializa estratégias
        self.buy_strategy = BuyStrategy()
        self.sell_strategy = SellStrategy()
        
    def get_usdt_available(self):
        """
        Retorna o saldo disponível em USDT
        """
        try:
            balance = self.client.fetch_balance()
            usdt_balance = balance['USDT']['free'] if 'USDT' in balance else 0
            return round(float(usdt_balance), 2)
        except Exception as e:
            print(f"{ERROR_BALANCE_FETCH}: {e}")
            return 0

    def get_brl_available(self):
        """
        Retorna o saldo disponível em BRL (se disponível na MEXC)
        Caso contrário, retorna USDT
        """
        try:
            balance = self.client.fetch_balance()
            brl_balance = balance.get('BRL', {}).get('free', 0)
            if brl_balance > 0:
                return round(float(brl_balance), 2)
            else:
                # Se não houver BRL, retorna USDT como fallback
                return self.get_usdt_available()
        except Exception as e:
            print(f"{ERROR_BALANCE_FETCH}: {e}")
            return 0

    def get_non_zero_sorted_assets(self):
        """
        Retorna ativos com saldo maior que 1, ordenados por valor
        """
        try:
            balance = self.client.fetch_balance()
            non_zero_assets = []
            
            for currency, data in balance['total'].items():
                if float(data) > 1:
                    non_zero_assets.append({
                        'currency': currency,
                        'balance': str(data),
                        'available': str(balance[currency].get('free', 0))
                    })
            
            return sorted(non_zero_assets, key=lambda x: float(x['balance']), reverse=True)
        except Exception as e:
            print(f"Error fetching assets: {e}")
            return []

    def get_total_assets_in_usdt(self):
        """
        Calcula o valor total dos ativos em USDT
        """
        try:
            balance = self.client.fetch_balance()
            total_in_usdt = 0.0
            
            for currency, data in balance['total'].items():
                balance_amount = float(data)
                if balance_amount <= 0:
                    continue
                    
                if currency == 'USDT':
                    total_in_usdt += balance_amount
                else:
                    total_in_usdt += self.convert_to_usdt(currency, balance_amount)
            
            available = self.get_usdt_available()
            assets_coin = self.get_non_zero_sorted_assets()
            
            return {
                "total_assets_usdt": round(total_in_usdt - available, 2),
                "available_usdt": available,
                "total_usdt": round(total_in_usdt, 2),
                "date": datetime.now().astimezone(),
                "tokens": assets_coin
            }
        except Exception as e:
            print(f"Error calculating total assets: {e}")
            return {"error": str(e)}

    def get_total_assets_in_brl(self):
        """
        Alias para manter compatibilidade com o código anterior
        """
        return self.get_total_assets_in_usdt()

    def convert_to_usdt(self, currency, balance):
        """
        Converte o saldo de uma moeda para USDT
        """
        if currency == 'USDT':
            return balance
            
        symbol = f"{currency}/USDT"
        try:
            ticker = self.client.fetch_ticker(symbol)
            last_price = float(ticker['last'])
            return balance * last_price
        except Exception as e:
            print(f"Error getting price for {symbol}: {e}")
            return 0

    def get_symbol_variations(self):
        """
        Retorna as variações de 24h dos símbolos configurados
        """
        variations = []
        for symbol in SYMBOLS:
            variation = self.get_symbol_variation(symbol)
            if variation:
                variations.append(variation)
        return sorted(variations, key=lambda x: x['variation_24h'])

    def get_symbol_variation(self, symbol):
        """
        Retorna a variação de 24h de um símbolo específico
        """
        try:
            ticker = self.client.fetch_ticker(symbol)
            if ticker and 'last' in ticker and 'open' in ticker:
                last_price = float(ticker['last'])
                opening_price24h = float(ticker['open'])
                
                if opening_price24h > 0:
                    variation_24h = ((last_price - opening_price24h) / opening_price24h) * 100
                    return {
                        "symbol": symbol,
                        "variation_24h": round(variation_24h, 2),
                        "last_price": last_price
                    }
        except Exception as e:
            print(f"Error fetching data for {symbol}: {e}")
        return None

    def create_order(self):
        """
        Cria ordens de compra nos símbolos configurados com estratégia avançada
        
        Estratégia de Maximização de Lucro:
        1. Compra APENAS em extremos (alta forte ou queda significativa)
        2. Usa DCA (Dollar Cost Average) - divide compras em partes
        3. Calcula lucro potencial baseado em histórico
        4. Implementa stop loss e take profit automaticamente
        """
        usdt_balance = self.get_usdt_available()
        
        if usdt_balance < MIN_VALUE_PER_CREATE_ORDER:
            error_message = f"{ERROR_INSUFFICIENT_FUNDS}: Available balance: $ {usdt_balance:.2f}"
            print(error_message)
            return {
                "error": ERROR_INSUFFICIENT_FUNDS,
                "available_balance": round(usdt_balance, 2)
            }

        # Busca variações e filtra apenas símbolos que atendem critérios
        symbol_variations = self.get_symbol_variations()
        filtered_symbols = self.filter_symbols_by_strategy(symbol_variations)
        
        if not filtered_symbols:
            print("⏸️  Nenhum símbolo atende os critérios de compra no momento")
            return {
                "status": "skipped",
                "reason": "No symbols meet trading criteria",
                "symbols_analyzed": len(symbol_variations),
                "available_balance": round(usdt_balance, 2)
            }
        
        # Inicializa ordens com análise de risco
        symbol_orders = self.initialize_symbol_orders_with_strategy(filtered_symbols)
        
        # Aloca fundos usando estratégia DCA (Dollar Cost Average)
        self.allocate_funds_with_dca_strategy(usdt_balance, symbol_orders)
        
        # Executa ordens com cálculo de lucro esperado
        results = self.execute_orders_with_profit_tracking(symbol_orders)
        
        # Calcula métricas de performance
        performance_metrics = self.calculate_performance_metrics(results)
        
        print(f"✅ Orders executed with strategy: {len(results)} orders")
        return {
            "status": "success",
            "orders": results,
            "total_invested": sum(order['value'] for order in results),
            "performance_metrics": performance_metrics,
            "strategy_used": "DCA + Risk Management"
        }
    
    def filter_symbols_by_strategy(self, symbol_variations):
        """
        Filtra símbolos usando BuyStrategy
        Delega lógica de compra para a classe especializada
        """
        from src.config.bot_config import BotConfig
        config = BotConfig()
        symbols_config = config.get('symbols', [])
        
        # Usa a estratégia de compra para filtrar símbolos
        filtered = self.buy_strategy.filter_symbols(symbol_variations, symbols_config)
        
        # Adiciona cálculo de lucro esperado
        for item in filtered:
            item['expected_profit_pct'] = self.calculate_expected_profit(
                item['variation_24h'], 
                item['config']
            )
        
        return filtered
    
    def calculate_expected_profit(self, variation, symbol_config):
        """
        Calcula o lucro esperado baseado na variação e configuração
        
        Lógica:
        - Se comprou na alta: espera-se mais 5-10% de alta
        - Se comprou na queda: espera-se recuperação de 10-20%
        """
        if variation > 0:
            # Compra em alta - lucro esperado menor (3-8%)
            return round(3 + (variation * 0.15), 2)
        else:
            # Compra em queda - lucro esperado maior (5-15%)
            recovery_potential = abs(variation) * 0.5
            return round(min(recovery_potential, 15), 2)
    
    def initialize_symbol_orders_with_strategy(self, filtered_symbols):
        """
        Inicializa ordens com análise de risco e lucro esperado
        Inclui porcentagem de compra gradativa baseada na queda
        """
        return {
            item['symbol']: {
                'value': 0,
                'date': None,
                'variation': item['variation_24h'],
                'signal_strength': item['signal_strength'],
                'reason': item['reason'],
                'expected_profit_pct': item['expected_profit_pct'],
                'buy_price': item['last_price'],
                'buy_percentage': item.get('buy_percentage', 100),  # % do saldo a investir
                'take_profit_price': item['last_price'] * (1 + item['expected_profit_pct'] / 100),
                'stop_loss_price': item['last_price'] * 0.95,  # Stop loss em -5%
                'allocation_pct': item['config'].get('allocation_percentage', 100)
            }
            for item in filtered_symbols
        }

    
    def allocate_funds_with_dca_strategy(self, usdt_balance, symbol_orders):
        """
        Aloca fundos usando BuyStrategy
        Delega cálculo de investimento para a classe especializada
        """
        if not symbol_orders:
            return
        
        for symbol, order in symbol_orders.items():
            # Usa a estratégia de compra para calcular quanto investir
            buy_percentage = order.get('buy_percentage', 100)
            investment_amount = self.buy_strategy.calculate_investment_amount(
                usdt_balance, 
                buy_percentage
            )
            
            # Garante valor mínimo
            if investment_amount >= MIN_VALUE_PER_SYMBOL:
                order['value'] = investment_amount
                order['date'] = datetime.utcnow()
                
                # Calcula lucro esperado em USDT
                order['expected_profit_usdt'] = round(
                    order['value'] * (order['expected_profit_pct'] / 100), 
                    2
                )
                
                print(f"📊 {symbol}: Queda de {order['variation']:.1f}% → Investe {buy_percentage}% do saldo (${order['value']:.2f})")
            else:
                order['value'] = 0
                print(f"⏸️  {symbol}: Valor muito baixo (${investment_amount:.2f} < ${MIN_VALUE_PER_SYMBOL})")
    
    def execute_orders_with_profit_tracking(self, symbol_orders):
        """
        Executa ordens e registra tracking de lucro/perda
        """
        results = []
        for symbol, order in symbol_orders.items():
            if order['value'] > 0:
                success, order_result = self.create_and_send_order(symbol, order['value'])
                status = STATUS_SUCCESS if success else STATUS_ERROR
                
                # Calcula quantidade comprada
                amount_bought = order['value'] / order['buy_price'] if success else 0
                
                result = {
                    'symbol': symbol,
                    'value': order['value'],
                    'amount_bought': round(amount_bought, 8),
                    'buy_price': order['buy_price'],
                    'status': status,
                    'variation_24h': order['variation'],
                    'signal_strength': order['signal_strength'],
                    'reason': order['reason'],
                    'date': order['date'],
                    'order_id': order_result.get('id') if order_result else None,
                    
                    # Profit Tracking
                    'expected_profit_pct': order['expected_profit_pct'],
                    'expected_profit_usdt': order['expected_profit_usdt'],
                    'take_profit_price': round(order['take_profit_price'], 8),
                    'stop_loss_price': round(order['stop_loss_price'], 8),
                    
                    # Cálculo de ROI esperado
                    'expected_roi': f"+{order['expected_profit_pct']}%",
                    'risk_reward_ratio': round(order['expected_profit_pct'] / 5, 2)  # 5% é o stop loss
                }
                results.append(result)
                
                # Salvar no banco com informações de lucro
                self.save_to_db_with_profit_tracking(symbol, result)
                
                print(f"{'✅' if success else '❌'} Order {status}: {symbol}")
                print(f"   💰 Investido: ${order['value']:.2f} USDT")
                print(f"   📊 Quantidade: {amount_bought:,.2f} tokens")
                print(f"   🎯 Take Profit: ${order['take_profit_price']:.8f} (+{order['expected_profit_pct']}%)")
                print(f"   🛡️  Stop Loss: ${order['stop_loss_price']:.8f} (-5%)")
                print(f"   💵 Lucro Esperado: ${order['expected_profit_usdt']:.2f} USDT")
        
        return results
    
    def calculate_performance_metrics(self, results):
        """
        Calcula métricas de performance da estratégia
        """
        if not results:
            return {}
        
        total_invested = sum(r['value'] for r in results)
        total_expected_profit = sum(r['expected_profit_usdt'] for r in results)
        avg_expected_roi = sum(r['expected_profit_pct'] for r in results) / len(results)
        
        return {
            'total_orders': len(results),
            'total_invested_usdt': round(total_invested, 2),
            'total_expected_profit_usdt': round(total_expected_profit, 2),
            'average_expected_roi_pct': round(avg_expected_roi, 2),
            'potential_return_usdt': round(total_invested + total_expected_profit, 2),
            'risk_exposure_pct': 5.0,  # Stop loss fixo em -5%
            'best_signal': max(results, key=lambda x: x['signal_strength'])['symbol'] if results else None
        }
    
    def save_to_db_with_profit_tracking(self, symbol, result):
        """
        Salva ordem no banco com informações de lucro/tracking
        """
        order_data = {
            "symbol": symbol,
            "value": result['value'],
            "amount_bought": result['amount_bought'],
            "buy_price": result['buy_price'],
            "date": result['date'],
            "variation_24h": result['variation_24h'],
            "status": result['status'],
            "signal_strength": result['signal_strength'],
            "reason": result['reason'],
            
            # Profit tracking
            "expected_profit_pct": result['expected_profit_pct'],
            "expected_profit_usdt": result['expected_profit_usdt'],
            "take_profit_price": result['take_profit_price'],
            "stop_loss_price": result['stop_loss_price'],
            "risk_reward_ratio": result['risk_reward_ratio'],
            
            # Status de acompanhamento
            "is_active": True,
            "sell_price": None,
            "actual_profit_pct": None,
            "actual_profit_usdt": None,
            "closed_at": None
        }
        
        try:
            if db:
                db.insert_one(order_data)
                print(f"   ✓ Order saved to database with profit tracking")
                return True
            else:
                print(f"   ⚠ MongoDB disabled - Order logged: {symbol}")
                return False
        except Exception as e:
            print(f"   ❌ {ERROR_DB_SAVE}: {e}")
            return False

    def initialize_symbol_orders(self, symbol_variations):
        """
        Inicializa a estrutura de ordens para cada símbolo
        """
        return {
            item['symbol']: {
                'value': 0,
                'date': None,
                'variation': item['variation_24h']
            }
            for item in symbol_variations
        }

    def allocate_funds_to_orders(self, usdt_balance, symbol_orders):
        """
        Distribui o saldo disponível entre os símbolos
        """
        while usdt_balance >= MIN_VALUE_PER_SYMBOL:
            for symbol in symbol_orders:
                if usdt_balance < MIN_VALUE_PER_SYMBOL:
                    break
                symbol_orders[symbol]['value'] += MIN_VALUE_PER_SYMBOL
                usdt_balance -= MIN_VALUE_PER_SYMBOL
                symbol_orders[symbol]['date'] = datetime.utcnow()

    def execute_orders(self, symbol_orders):
        """
        Executa as ordens para cada símbolo
        """
        results = []
        for symbol, order in symbol_orders.items():
            if order['value'] > 0:
                success, order_result = self.create_and_send_order(symbol, order['value'])
                status = STATUS_SUCCESS if success else STATUS_ERROR
                
                result = {
                    'symbol': symbol,
                    'value': order['value'],
                    'status': status,
                    'variation': order['variation'],
                    'date': order['date'],
                    'order_id': order_result.get('id') if order_result else None
                }
                results.append(result)
                
                # Salvar no banco se estiver configurado
                self.save_to_db(symbol, order['value'], order['date'], order['variation'], status)
                print(f"Order {status}: {symbol} - ${order['value']:.2f}")
        
        return results

    def create_and_send_order(self, symbol, value):
        """
        Cria e envia uma ordem de mercado
        """
        try:
            # Busca o preço atual para calcular a quantidade
            ticker = self.client.fetch_ticker(symbol)
            last_price = float(ticker['last'])
            
            # Calcula a quantidade baseada no valor em USDT
            amount = value / last_price
            
            # Arredonda a quantidade para o número de casas decimais aceito
            markets = self.client.load_markets()
            market = markets[symbol]
            amount = self.client.amount_to_precision(symbol, amount)
            
            # Cria ordem de mercado
            order = self.client.create_market_buy_order(symbol, float(amount))
            
            print(f"Order created: {symbol} - Amount: {amount} - Value: ${value:.2f}")
            return True, order
            
        except Exception as e:
            print(f"Error creating order for {symbol}: {e}")
            return False, None

    def save_to_db(self, symbol, value, date, variation, status):
        """
        Salva a ordem no banco de dados (se configurado)
        """
        order_data = {
            "symbol": symbol,
            "value": value,
            "date": date,
            "variation": variation,
            "status": status
        }
        
        try:
            if db:  # Só salva se o banco estiver disponível
                db.insert_one(order_data)
                print(f"✓ Order saved to database: {order_data}")
                return f"Order saved to database: {order_data}"
            else:
                print(f"⚠ MongoDB disabled - Order would be saved: {order_data}")
                return f"Order logged (DB disabled): {order_data}"
        except Exception as e:
            print(f"{ERROR_DB_SAVE}: {e}")
            return f"Error saving to DB: {e}"
