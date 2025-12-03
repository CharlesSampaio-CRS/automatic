"""
Backtesting Completo - 3 Cenários
Valida estratégias 4h e 24h em: ÓTIMO, BÁSICO e RUIM

Este teste simula 3 períodos diferentes de 30 dias cada:
1. ÓTIMO: Quedas seguidas de recuperações (alta volatilidade favorável)
2. BÁSICO: Baixa volatilidade, poucas oportunidades
3. RUIM: Queda contínua sem recuperação (bear market)

Uso:
    python3 test_backtest_3_scenarios.py
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

class MultiScenarioBacktest:
    """
    Simulador de backtesting em múltiplos períodos para detectar cenários
    """
    
    def __init__(self, symbol, initial_balance=100.0):
        """
        Args:
            symbol: Par de trading (ex: REKTCOIN/USDT)
            initial_balance: Saldo inicial em USDT
        """
        self.symbol = symbol
        self.initial_balance = initial_balance
        self.client = MexcClient(API_KEY, API_SECRET)
        
        # Carrega configuração do MongoDB
        print(f"🔍 Carregando configuração do MongoDB...")
        self.config = self._load_config_from_db()
        
        # Resultados por cenário
        self.scenarios = []
        
    def _load_config_from_db(self):
        """Carrega configuração real do MongoDB"""
        try:
            db = get_database()
            bot_configs = db['BotConfigs']
            config = bot_configs.find_one({'pair': self.symbol})
            
            if config:
                print(f"✅ Config carregada: {self.symbol}")
                strategy_4h = config.get('strategy_4h', {})
                strategy_24h = config.get('trading_strategy', {})
                print(f"   4h: {'✅' if strategy_4h.get('enabled') else '❌'} | 24h: {'✅' if strategy_24h.get('enabled') else '❌'}")
                return config
            
            return self._get_default_config()
            
        except Exception as e:
            print(f"⚠️  Usando config padrão: {e}")
            return self._get_default_config()
    
    def _get_default_config(self):
        """Config padrão"""
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
    
    def run_all_scenarios(self):
        """
        Executa backtesting em 3 períodos diferentes de 30 dias
        """
        print(f"\n{'='*80}")
        print("🧪 BACKTESTING - 3 CENÁRIOS")
        print(f"{'='*80}")
        print(f"📊 Par: {self.symbol}")
        print(f"💰 Capital inicial por cenário: ${self.initial_balance:.2f}")
        print(f"\nTestando 3 períodos diferentes de 30 dias para detectar:")
        print("   🎉 ÓTIMO: Quedas + recuperações")
        print("   ⚠️  BÁSICO: Baixa volatilidade")
        print("   ❌ RUIM: Queda contínua")
        
        # Busca dados históricos longos (90 dias = 3 períodos de 30)
        print(f"\n🔄 Buscando dados históricos (90 dias)...")
        ohlcv_data = self.client.client.fetch_ohlcv(
            self.symbol,
            '4h',
            limit=540  # 90 dias * 6 candles/dia
        )
        
        if len(ohlcv_data) < 180:
            print(f"⚠️  Dados insuficientes: {len(ohlcv_data)} candles (mínimo 180)")
            print("   Testando apenas com dados disponíveis...")
        
        print(f"✅ {len(ohlcv_data)} candles obtidos")
        
        # Divide em 3 períodos de 15 dias (90 candles cada) para ter 3 cenários
        period_length = 90  # 15 dias * 6 candles/dia
        num_periods = len(ohlcv_data) // period_length
        
        if num_periods < 3:
            print(f"\n⚠️  Só há {num_periods} período(s) completo(s) de 15 dias")
            
            if num_periods >= 3:
                periods = [
                    ohlcv_data[-270:-180],  # Período 1
                    ohlcv_data[-180:-90],   # Período 2
                    ohlcv_data[-90:]        # Período 3
                ]
            elif num_periods == 2:
                print(f"   Testando 2 períodos disponíveis...")
                periods = [
                    ohlcv_data[-180:-90],   # Período 1
                    ohlcv_data[-90:]        # Período 2
                ]
            else:
                print(f"   Testando período mais recente (15 dias)...")
                periods = [ohlcv_data[-90:]]
        else:
            print(f"\n✅ {num_periods} períodos de 15 dias disponíveis, usando os 3 mais recentes")
            periods = [
                ohlcv_data[-270:-180],  # Período 1 (mais antigo)
                ohlcv_data[-180:-90],   # Período 2 (meio)
                ohlcv_data[-90:]        # Período 3 (mais recente)
            ]
        
        # Testa cada período
        for idx, period_data in enumerate(periods, 1):
            print(f"\n{'='*80}")
            print(f"📅 PERÍODO {idx} DE {len(periods)}")
            print(f"{'='*80}")
            
            start_date = datetime.fromtimestamp(period_data[0][0]/1000).strftime('%Y-%m-%d')
            end_date = datetime.fromtimestamp(period_data[-1][0]/1000).strftime('%Y-%m-%d')
            print(f"Período: {start_date} a {end_date}")
            
            # Executa simulação
            scenario = self._run_single_scenario(period_data, idx)
            self.scenarios.append(scenario)
        
        # Mostra comparação final
        self._show_comparison()
    
    def _run_single_scenario(self, ohlcv_data, scenario_num):
        """
        Executa simulação em um único período
        """
        # Inicializa estado
        balance_usdt = self.initial_balance
        token_balance = 0.0
        trades = []
        
        # Estratégias
        strategy_4h_config = self.config.get('strategy_4h')
        if not strategy_4h_config:
            raise ValueError('❌ strategy_4h não encontrada na configuração!')
            
        buy_strategy_4h = BuyStrategy4h(strategy_4h_config)
        buy_strategy_24h = BuyStrategy(self.config.get('trading_strategy'))
        
        # Simula trading
        for i in range(6, len(ohlcv_data)):
            current_candle = ohlcv_data[i]
            timestamp = current_candle[0]
            current_price = current_candle[4]
            
            # Verifica compra (4h primeiro, depois 24h)
            if balance_usdt >= 5.0:
                # Calcula variações
                price_4h_ago = ohlcv_data[i-1][4]
                price_24h_ago = ohlcv_data[i-6][4]
                variation_4h = ((current_price - price_4h_ago) / price_4h_ago) * 100
                variation_24h = ((current_price - price_24h_ago) / price_24h_ago) * 100
                
                # Tenta 4h primeiro
                should_buy_4h, buy_info_4h = buy_strategy_4h.should_buy(variation_4h, self.symbol)
                
                if should_buy_4h:
                    strategy_used = '4h'
                    buy_info = buy_info_4h
                    variation = variation_4h
                else:
                    # Fallback para 24h
                    should_buy_24h, buy_info_24h = buy_strategy_24h.should_buy(variation_24h)
                    
                    if should_buy_24h:
                        strategy_used = '24h'
                        buy_info = buy_info_24h
                        variation = variation_24h
                    else:
                        should_buy_4h = False
                
                if should_buy_4h or (not should_buy_4h and 'buy_info' in locals()):
                    buy_percentage = buy_info['buy_percentage']
                    investment = (balance_usdt * buy_percentage) / 100
                    
                    if investment >= 5.0:
                        amount_bought = investment / current_price
                        token_balance += amount_bought
                        balance_usdt -= investment
                        
                        trades.append({
                            'type': 'BUY',
                            'timestamp': timestamp,
                            'price': current_price,
                            'amount': amount_bought,
                            'investment': investment,
                            'strategy': strategy_used,
                            'variation': variation
                        })
            
            # Verifica venda
            if token_balance > 0:
                buy_trades = [t for t in trades if t['type'] == 'BUY']
                if buy_trades:
                    total_investment = sum(t['investment'] for t in buy_trades)
                    total_tokens = sum(t['amount'] for t in buy_trades)
                    avg_buy_price = total_investment / total_tokens
                    profit_percent = ((current_price - avg_buy_price) / avg_buy_price) * 100
                    
                    if profit_percent >= 5.0:
                        sell_percentage = 30
                        if profit_percent >= 20:
                            sell_percentage = 100
                        elif profit_percent >= 10:
                            sell_percentage = 50
                        
                        amount_to_sell = (token_balance * sell_percentage) / 100
                        usdt_received = amount_to_sell * current_price
                        
                        token_balance -= amount_to_sell
                        balance_usdt += usdt_received
                        
                        trades.append({
                            'type': 'SELL',
                            'timestamp': timestamp,
                            'price': current_price,
                            'amount': amount_to_sell,
                            'usdt_received': usdt_received,
                            'profit_percent': profit_percent
                        })
        
        # Calcula resultado final
        final_price = ohlcv_data[-1][4]
        token_value = token_balance * final_price
        total_value = balance_usdt + token_value
        profit_loss = total_value - self.initial_balance
        roi = (profit_loss / self.initial_balance) * 100
        
        # Classifica cenário
        if roi > 10:
            scenario_type = "ÓTIMO"
            emoji = "🎉"
        elif roi > 0:
            scenario_type = "BÁSICO"
            emoji = "⚠️"
        else:
            scenario_type = "RUIM"
            emoji = "❌"
        
        # Estatísticas
        buys = [t for t in trades if t['type'] == 'BUY']
        sells = [t for t in trades if t['type'] == 'SELL']
        buys_4h = [t for t in buys if t['strategy'] == '4h']
        buys_24h = [t for t in buys if t['strategy'] == '24h']
        
        # Mostra resultado
        print(f"\n💰 Resultado:")
        print(f"   Capital final: ${total_value:.2f}")
        print(f"   ROI: {roi:+.2f}%")
        print(f"   Trades: {len(buys)} compras, {len(sells)} vendas")
        print(f"   Estratégia: 4h={len(buys_4h)}, 24h={len(buys_24h)}")
        
        if sells:
            avg_profit = sum(t['profit_percent'] for t in sells) / len(sells)
            print(f"   Lucro médio: {avg_profit:+.2f}%")
        
        print(f"\n{emoji} CENÁRIO: {scenario_type}")
        
        return {
            'scenario_num': scenario_num,
            'scenario_type': scenario_type,
            'emoji': emoji,
            'roi': roi,
            'capital_final': total_value,
            'profit_loss': profit_loss,
            'num_buys': len(buys),
            'num_sells': len(sells),
            'buys_4h': len(buys_4h),
            'buys_24h': len(buys_24h),
            'avg_profit': sum(t['profit_percent'] for t in sells) / len(sells) if sells else 0,
            'start_date': datetime.fromtimestamp(ohlcv_data[0][0]/1000).strftime('%Y-%m-%d'),
            'end_date': datetime.fromtimestamp(ohlcv_data[-1][0]/1000).strftime('%Y-%m-%d')
        }
    
    def _show_comparison(self):
        """
        Mostra comparação entre os cenários
        """
        print(f"\n{'='*80}")
        print("📊 COMPARAÇÃO DOS CENÁRIOS")
        print(f"{'='*80}")
        
        print(f"\n{'Período':<12} {'Datas':<25} {'Cenário':<12} {'ROI':<12} {'Trades':<15}")
        print(f"{'-'*80}")
        
        total_roi = 0
        best_scenario = None
        worst_scenario = None
        
        for s in self.scenarios:
            dates = f"{s['start_date']} a {s['end_date']}"
            trades = f"{s['num_buys']}C/{s['num_sells']}V"
            
            print(f"{s['emoji']} Período {s['scenario_num']:<3} {dates:<25} {s['scenario_type']:<12} {s['roi']:+.2f}%      {trades:<15}")
            
            total_roi += s['roi']
            
            if best_scenario is None or s['roi'] > best_scenario['roi']:
                best_scenario = s
            
            if worst_scenario is None or s['roi'] < worst_scenario['roi']:
                worst_scenario = s
        
        avg_roi = total_roi / len(self.scenarios)
        
        print(f"\n{'='*80}")
        print("📈 ESTATÍSTICAS GERAIS")
        print(f"{'='*80}")
        
        print(f"\n💰 Performance:")
        print(f"   ROI médio: {avg_roi:+.2f}%")
        print(f"   Melhor período: Período {best_scenario['scenario_num']} ({best_scenario['scenario_type']}) = {best_scenario['roi']:+.2f}%")
        print(f"   Pior período: Período {worst_scenario['scenario_num']} ({worst_scenario['scenario_type']}) = {worst_scenario['roi']:+.2f}%")
        
        # Conta cenários
        otimos = len([s for s in self.scenarios if s['scenario_type'] == 'ÓTIMO'])
        basicos = len([s for s in self.scenarios if s['scenario_type'] == 'BÁSICO'])
        ruins = len([s for s in self.scenarios if s['scenario_type'] == 'RUIM'])
        
        print(f"\n📊 Distribuição:")
        print(f"   🎉 ÓTIMO: {otimos}/{len(self.scenarios)}")
        print(f"   ⚠️  BÁSICO: {basicos}/{len(self.scenarios)}")
        print(f"   ❌ RUIM: {ruins}/{len(self.scenarios)}")
        
        # Análise de estratégias
        total_buys_4h = sum(s['buys_4h'] for s in self.scenarios)
        total_buys_24h = sum(s['buys_24h'] for s in self.scenarios)
        total_buys = total_buys_4h + total_buys_24h
        
        if total_buys > 0:
            print(f"\n⚡ Efetividade das Estratégias:")
            print(f"   4h: {total_buys_4h} compras ({total_buys_4h/total_buys*100:.1f}%)")
            print(f"   24h: {total_buys_24h} compras ({total_buys_24h/total_buys*100:.1f}%)")
        
        # Conclusão e recomendações
        print(f"\n{'='*80}")
        print("🎯 CONCLUSÃO E RECOMENDAÇÕES")
        print(f"{'='*80}")
        
        if ruins > 0:
            worst_loss = worst_scenario['roi']
            print(f"\n⚠️  ATENÇÃO - Cenário RUIM detectado:")
            print(f"   Pior prejuízo: {worst_loss:.2f}%")
            print(f"   Período: {worst_scenario['start_date']} a {worst_scenario['end_date']}")
            
            if worst_loss < -30:
                print(f"\n❌ PREJUÍZO ALTO (>{-worst_loss:.0f}%):")
                print(f"   • URGENTE: Implementar stop loss global")
                print(f"   • Sugestão: Stop loss em -20% do capital inicial")
                print(f"   • Considerar desativar bot em quedas contínuas")
            elif worst_loss < -10:
                print(f"\n⚠️  PREJUÍZO MODERADO ({worst_loss:.1f}%):")
                print(f"   • Implementar stop loss em -25%")
                print(f"   • Monitorar tendência de mercado")
                print(f"   • Considerar reduzir investimento por trade")
            else:
                print(f"\n✅ PREJUÍZO CONTROLADO ({worst_loss:.1f}%):")
                print(f"   • Sistema gerenciou risco adequadamente")
                print(f"   • Manter configuração atual")
        
        if avg_roi > 10:
            print(f"\n✅ SISTEMA VALIDADO:")
            print(f"   • ROI médio excelente: {avg_roi:+.2f}%")
            print(f"   • Aprovado para produção")
            print(f"   • Manter monitoramento contínuo")
        elif avg_roi > 0:
            print(f"\n⚠️  SISTEMA FUNCIONAL:")
            print(f"   • ROI médio positivo: {avg_roi:+.2f}%")
            print(f"   • Considerar otimização de thresholds")
            print(f"   • Testar ajustes para melhorar performance")
        else:
            print(f"\n❌ SISTEMA PRECISA AJUSTES:")
            print(f"   • ROI médio negativo: {avg_roi:.2f}%")
            print(f"   • Revisar configuração")
            print(f"   • Implementar proteções adicionais")
        
        print(f"\n{'='*80}\n")

def main():
    """
    Executa backtesting em 3 cenários
    """
    print("\n🚀 BACKTESTING - 3 CENÁRIOS")
    print("Valida estratégia híbrida em diferentes condições de mercado\n")
    
    SYMBOL = "REKTCOIN/USDT"
    INITIAL_BALANCE = 100.0
    
    simulator = MultiScenarioBacktest(
        symbol=SYMBOL,
        initial_balance=INITIAL_BALANCE
    )
    
    simulator.run_all_scenarios()

if __name__ == "__main__":
    main()
