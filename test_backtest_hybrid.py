"""
Backtesting Híbrido - 30 Dias
Valida estratégias 4h e 24h em 3 cenários: Ótimo, Básico e Ruim

Este teste simula o comportamento real do bot com estratégia híbrida:
- Strategy 4h (PRIORIDADE): -3%, -5%, -10%
- Strategy 24h (FALLBACK): -15%, -25%, -50%

Uso:
    python3 test_backtest_hybrid.py
"""

import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.clients.exchange import MexcClient
from src.clients.buy_strategy_4h import BuyStrategy4h
from src.clients.buy_strategy import BuyStrategy
from src.clients.sell_strategy import SellStrategy
from src.database.mongodb_connection import get_database

# Carrega variáveis do .env
load_dotenv()

API_KEY = os.getenv('API_KEY')
API_SECRET = os.getenv('API_SECRET')

class HybridBacktestSimulator:
    """
    Simulador de backtesting com estratégia híbrida (4h + 24h)
    Usa configuração real do MongoDB
    """
    
    def __init__(self, symbol, initial_balance=100.0, days=30):
        """
        Args:
            symbol: Par de trading (ex: REKTCOIN/USDT)
            initial_balance: Saldo inicial em USDT
            days: Número de dias para simular
        """
        self.symbol = symbol
        self.initial_balance = initial_balance
        self.days = days
        
        # Estado da simulação
        self.balance_usdt = initial_balance
        self.token_balance = 0.0
        self.trades = []
        self.portfolio_history = []
        
        # Cliente MEXC
        self.client = MexcClient(API_KEY, API_SECRET)
        
        # Busca configuração REAL do MongoDB
        print(f" Buscando configuração real do MongoDB para {symbol}...")
        config = self._load_config_from_db()
        
        if not config:
            print(f"⚠️  Configuração não encontrada no MongoDB, usando padrão")
            config = self._get_default_config()
        else:
            print(f" Configuração carregada do MongoDB")
        
        # Estratégias
        self.buy_strategy_4h = self._init_buy_strategy_4h(config)
        self.buy_strategy_24h = self._init_buy_strategy_24h(config)
        self.sell_strategy = self._init_sell_strategy()
        
    def _load_config_from_db(self):
        """Carrega configuração real do MongoDB"""
        try:
            db = get_database()
            bot_configs = db['BotConfigs']
            
            # Busca config do par
            config = bot_configs.find_one({'pair': self.symbol})
            
            if config:
                print(f"\n📋 Configuração MongoDB:")
                print(f"   Pair: {config.get('pair')}")
                print(f"   Enabled: {config.get('enabled')}")
                print(f"   Interval: {config.get('interval_minutes')} minutos")
                
                strategy_4h = config.get('strategy_4h', {})
                strategy_24h = config.get('trading_strategy', {})
                
                print(f"   Strategy 4h: {' Habilitada' if strategy_4h.get('enabled') else ' Desabilitada'}")
                print(f"   Strategy 24h: {' Habilitada' if strategy_24h.get('enabled') else ' Desabilitada'}")
                
                return config
            
            return None
            
        except Exception as e:
            print(f" Erro ao carregar config do MongoDB: {e}")
            return None
    
    def _get_default_config(self):
        """Retorna configuração padrão se não encontrar no MongoDB"""
        return {
            'pair': self.symbol,
            'enabled': True,
            'strategy_4h': {
                'enabled': True,
                'buy_on_dip': {
                    'enabled': True,
                    'thresholds': [
                        {'variation_min': -100, 'variation_max': -10, 'percentage_of_balance': 30},
                        {'variation_min': -10, 'variation_max': -5, 'percentage_of_balance': 20},
                        {'variation_min': -5, 'variation_max': -3, 'percentage_of_balance': 10}
                    ]
                }
            },
            'trading_strategy': {
                'enabled': True,
                'buy_on_dip': {
                    'enabled': True,
                    'thresholds': [
                        {'variation_min': -100, 'variation_max': -25, 'percentage_of_balance': 30},
                        {'variation_min': -25, 'variation_max': -15, 'percentage_of_balance': 20},
                        {'variation_min': -15, 'variation_max': -10, 'percentage_of_balance': 10}
                    ]
                }
            }
        }
    
    def _init_buy_strategy_4h(self, config):
        """Inicializa estratégia de compra 4h usando config do MongoDB"""
        strategy_4h = config.get('strategy_4h', {})
        if not strategy_4h:
            raise ValueError(' strategy_4h não encontrada na configuração!')
        return BuyStrategy4h(strategy_4h)
    
    def _init_buy_strategy_24h(self, config):
        """Inicializa estratégia de compra 24h usando config do MongoDB"""
        trading_strategy = config.get('trading_strategy', {})
        return BuyStrategy(trading_strategy)
    
    def _init_sell_strategy(self):
        """Inicializa estratégia de venda"""
        config = {
            'min_profit': 5.0,
            'levels': [
                {'profit_target': 5, 'percentage': 30},
                {'profit_target': 10, 'percentage': 30},
                {'profit_target': 20, 'percentage': 40}
            ]
        }
        return SellStrategy(config)
    
    def fetch_historical_data(self, timeframe='4h'):
        """
        Busca dados históricos
        
        Returns:
            Lista de candles OHLCV: [timestamp, open, high, low, close, volume]
        """
        try:
            # Calcula quantos candles precisamos
            if timeframe == '4h':
                candles_needed = (self.days * 24) // 4  # 6 candles por dia
            elif timeframe == '1h':
                candles_needed = self.days * 24
            else:
                candles_needed = self.days * 6
            
            ohlcv = self.client.client.fetch_ohlcv(
                self.symbol, 
                timeframe, 
                limit=candles_needed
            )
            
            return ohlcv
            
        except Exception as e:
            print(f" Erro ao buscar dados históricos: {e}")
            return []
    
    def calculate_variation(self, current_price, reference_price):
        """Calcula variação percentual"""
        if reference_price == 0:
            return 0.0
        return ((current_price - reference_price) / reference_price) * 100
    
    def check_hybrid_buy(self, current_price, ohlcv_data, current_index):
        """
        Verifica compra usando lógica híbrida (4h PRIMEIRO, depois 24h)
        
        Returns:
            (should_buy, strategy_used, buy_info)
        """
        # 1. PRIORIDADE: Verifica Strategy 4h
        if current_index >= 1:
            previous_candle_4h = ohlcv_data[current_index - 1]
            price_4h_ago = previous_candle_4h[4]
            variation_4h = self.calculate_variation(current_price, price_4h_ago)
            
            should_buy_4h, buy_info_4h = self.buy_strategy_4h.should_buy(
                variation_4h, 
                self.symbol
            )
            
            if should_buy_4h:
                return True, '4h', buy_info_4h, variation_4h
        
        # 2. FALLBACK: Verifica Strategy 24h (se 4h não comprou)
        if current_index >= 6:  # Precisa de pelo menos 24h de dados (6 candles de 4h)
            candle_24h_ago = ohlcv_data[current_index - 6]
            price_24h_ago = candle_24h_ago[4]
            variation_24h = self.calculate_variation(current_price, price_24h_ago)
            
            # BuyStrategy (24h) tem assinatura diferente - só recebe variation_24h
            should_buy_24h, buy_info_24h = self.buy_strategy_24h.should_buy(
                variation_24h
            )
            
            if should_buy_24h:
                return True, '24h', buy_info_24h, variation_24h
        
        return False, None, None, 0
    
    def simulate_buy(self, price, strategy_used, buy_info, variation, timestamp):
        """
        Simula compra
        
        Returns:
            True se comprou, False caso contrário
        """
        # Calcula quanto investir
        buy_percentage = buy_info['buy_percentage']
        investment = (self.balance_usdt * buy_percentage) / 100
        
        # Verifica saldo mínimo
        if investment < 5.0:
            return False
        
        # Executa compra
        amount_bought = investment / price
        self.token_balance += amount_bought
        self.balance_usdt -= investment
        
        # Registra trade
        trade = {
            'type': 'BUY',
            'timestamp': timestamp,
            'price': price,
            'amount': amount_bought,
            'investment': investment,
            'variation': variation,
            'strategy': strategy_used,
            'level': buy_info['reason'],
            'balance_usdt_after': self.balance_usdt,
            'token_balance_after': self.token_balance
        }
        self.trades.append(trade)
        
        return True
    
    def simulate_sell(self, price, timestamp):
        """
        Simula venda
        
        Returns:
            True se vendeu, False caso contrário
        """
        if self.token_balance == 0:
            return False
        
        # Busca preço médio de compra
        buy_trades = [t for t in self.trades if t['type'] == 'BUY']
        if not buy_trades:
            return False
        
        total_investment = sum(t['investment'] for t in buy_trades)
        total_tokens = sum(t['amount'] for t in buy_trades)
        
        if total_tokens == 0:
            return False
        
        avg_buy_price = total_investment / total_tokens
        
        # Calcula lucro atual
        profit_percent = ((price - avg_buy_price) / avg_buy_price) * 100
        
        # Verifica lucro mínimo
        min_profit = 5.0
        
        if profit_percent < min_profit:
            return False
        
        # Decide porcentagem a vender
        sell_percentage = 30
        if profit_percent >= 20:
            sell_percentage = 100
        elif profit_percent >= 10:
            sell_percentage = 50
        
        # Executa venda
        amount_to_sell = (self.token_balance * sell_percentage) / 100
        usdt_received = amount_to_sell * price
        
        self.token_balance -= amount_to_sell
        self.balance_usdt += usdt_received
        
        # Registra trade
        trade = {
            'type': 'SELL',
            'timestamp': timestamp,
            'price': price,
            'amount': amount_to_sell,
            'usdt_received': usdt_received,
            'profit_percent': profit_percent,
            'sell_percentage': sell_percentage,
            'balance_usdt_after': self.balance_usdt,
            'token_balance_after': self.token_balance
        }
        self.trades.append(trade)
        
        return True
    
    def run_simulation(self):
        """
        Executa simulação completa
        """
        print(f"\n{'='*80}")
        print(f"🧪 BACKTESTING HÍBRIDO - {self.days} DIAS")
        print(f"{'='*80}")
        print(f" Símbolo: {self.symbol}")
        print(f"💰 Saldo inicial: ${self.initial_balance:.2f} USDT")
        print(f"📅 Período: {self.days} dias")
        
        # Busca dados históricos
        print(f"\n Buscando dados históricos...")
        ohlcv_data = self.fetch_historical_data('4h')
        
        if not ohlcv_data or len(ohlcv_data) < 7:
            print(" Dados históricos insuficientes")
            return
        
        print(f" {len(ohlcv_data)} candles obtidos")
        print(f"\n🔄 Executando simulação...\n")
        
        # Simula trading em cada candle
        for i in range(6, len(ohlcv_data)):
            current_candle = ohlcv_data[i]
            
            timestamp = current_candle[0]
            current_price = current_candle[4]  # Close price
            date_str = datetime.fromtimestamp(timestamp/1000).strftime('%Y-%m-%d %H:%M')
            
            # Verifica compra híbrida (4h primeiro, depois 24h)
            if self.balance_usdt >= 5.0:
                should_buy, strategy_used, buy_info, variation = self.check_hybrid_buy(
                    current_price, 
                    ohlcv_data, 
                    i
                )
                
                if should_buy:
                    success = self.simulate_buy(
                        current_price, 
                        strategy_used, 
                        buy_info, 
                        variation, 
                        timestamp
                    )
                    
                    if success:
                        investment = (self.balance_usdt * buy_info['buy_percentage']) / (100 - buy_info['buy_percentage']) if buy_info['buy_percentage'] < 100 else self.balance_usdt + (self.token_balance * current_price)
                        print(f"🛒 COMPRA [{strategy_used}] {date_str} | Preço: ${current_price:.10f} | Var: {variation:+.1f}% | Investido: ${investment:.2f}")
            
            # Verifica venda
            if self.token_balance > 0:
                sold = self.simulate_sell(current_price, timestamp)
                
                if sold:
                    sell_trade = self.trades[-1]
                    print(f"💰 VENDA {date_str} | Preço: ${current_price:.10f} | Lucro: {sell_trade['profit_percent']:+.1f}% | Recebido: ${sell_trade['usdt_received']:.2f}")
            
            # Registra portfolio
            total_value = self.balance_usdt + (self.token_balance * current_price)
            self.portfolio_history.append({
                'timestamp': timestamp,
                'price': current_price,
                'balance_usdt': self.balance_usdt,
                'token_balance': self.token_balance,
                'total_value': total_value
            })
        
        # Mostra resultados
        self.show_results()
    
    def show_results(self):
        """
        Mostra resultados detalhados
        """
        print(f"\n{'='*80}")
        print("📈 RESULTADOS")
        print(f"{'='*80}")
        
        # Calcula valor final
        if not self.portfolio_history:
            print(" Sem dados")
            return
        
        final_price = self.portfolio_history[-1]['price']
        token_value = self.token_balance * final_price
        total_value = self.balance_usdt + token_value
        
        # Métricas básicas
        profit_loss = total_value - self.initial_balance
        profit_loss_pct = (profit_loss / self.initial_balance) * 100
        
        print(f"\n💰 Capital:")
        print(f"   Inicial: ${self.initial_balance:.2f}")
        print(f"   Final: ${total_value:.2f}")
        print(f"   Lucro: ${profit_loss:+.2f} ({profit_loss_pct:+.2f}%)")
        
        # Estatísticas por estratégia
        buys = [t for t in self.trades if t['type'] == 'BUY']
        sells = [t for t in self.trades if t['type'] == 'SELL']
        
        buys_4h = [t for t in buys if t['strategy'] == '4h']
        buys_24h = [t for t in buys if t['strategy'] == '24h']
        
        print(f"\n Trades:")
        print(f"   Compras: {len(buys)} (4h: {len(buys_4h)}, 24h: {len(buys_24h)})")
        print(f"   Vendas: {len(sells)}")
        
        if sells:
            avg_profit = sum(t['profit_percent'] for t in sells) / len(sells)
            best_sell = max(sells, key=lambda x: x['profit_percent'])
            print(f"   Lucro médio: {avg_profit:+.2f}%")
            print(f"   Melhor venda: {best_sell['profit_percent']:+.2f}%")
        
        # Performance
        if self.portfolio_history:
            max_value = max(p['total_value'] for p in self.portfolio_history)
            min_value = min(p['total_value'] for p in self.portfolio_history)
            
            print(f"\n📈 Performance:")
            print(f"   Máximo: ${max_value:.2f} ({((max_value/self.initial_balance)-1)*100:+.2f}%)")
            print(f"   Mínimo: ${min_value:.2f} ({((min_value/self.initial_balance)-1)*100:+.2f}%)")
        
        # Conclusão
        print(f"\n{'='*80}")
        if profit_loss_pct > 10:
            print(f" CENÁRIO ÓTIMO: {profit_loss_pct:+.2f}%")
        elif profit_loss_pct > 0:
            print(f"⚠️  CENÁRIO BÁSICO: {profit_loss_pct:+.2f}%")
        else:
            print(f" CENÁRIO RUIM: {profit_loss_pct:.2f}%")
        print(f"{'='*80}\n")

def main():
    """
    Executa backtesting híbrido de 30 dias com config do MongoDB
    """
    print("\nBACKTESTING HÍBRIDO - CONFIG DO MONGODB")
    print("=" * 80)
    
    # Configuração
    SYMBOL = "REKTCOIN/USDT"
    INITIAL_BALANCE = 100.0
    DAYS = 30
    
    # Cria simulador (busca config do MongoDB)
    simulator = HybridBacktestSimulator(
        symbol=SYMBOL,
        initial_balance=INITIAL_BALANCE,
        days=DAYS
    )
    
    # Executa simulação
    simulator.run_simulation()

if __name__ == "__main__":
    main()
