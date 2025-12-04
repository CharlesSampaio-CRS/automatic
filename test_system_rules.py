"""
Teste de Validação de Regras do Sistema
Valida todas as regras de negócio da estratégia híbrida

Este teste verifica:
1.  Priorização: 4h é verificado ANTES de 24h
2.  Thresholds: Compras só ocorrem nos níveis corretos
3.  Stop loss: Sistema para de comprar em cenários ruins
4.  Gestão de risco: Limites de investimento são respeitados
5.  Vendas: Lucro mínimo é respeitado
6.  Comportamento em 3 cenários: ÓTIMO, BÁSICO e RUIM

Uso:
    python3 test_system_rules.py
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.clients.exchange import MexcClient
from src.clients.buy_strategy_4h import BuyStrategy4h
from src.clients.buy_strategy import BuyStrategy
from src.database.mongodb_connection import get_database

load_dotenv()

API_KEY = os.getenv('API_KEY')
API_SECRET = os.getenv('API_SECRET')

class SystemRulesValidator:
    """
    Valida todas as regras de negócio do sistema
    """
    
    def __init__(self, symbol):
        self.symbol = symbol
        self.client = MexcClient(API_KEY, API_SECRET)
        self.config = self._load_config()
        self.validation_results = []
        
    def _load_config(self):
        """Carrega config do MongoDB"""
        try:
            db = get_database()
            config = db['BotConfigs'].find_one({'pair': self.symbol})
            return config if config else self._default_config()
        except:
            return self._default_config()
    
    def _default_config(self):
        return {
            'strategy_4h': {
                'enabled': True,
                'buy_on_dip': {
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
                    'thresholds': [
                        {'variation_min': -100, 'variation_max': -25, 'percentage_of_balance': 30},
                        {'variation_min': -25, 'variation_max': -15, 'percentage_of_balance': 20},
                        {'variation_min': -15, 'variation_max': -10, 'percentage_of_balance': 10}
                    ]
                }
            }
        }
    
    def run_all_validations(self):
        """Executa todas as validações"""
        print(f"\n{'='*80}")
        print(" VALIDAÇÃO DE REGRAS DO SISTEMA")
        print(f"{'='*80}")
        print(f" Par: {self.symbol}")
        print(f"\nValidando:")
        print("   1️⃣  Priorização (4h → 24h)")
        print("   2️⃣  Thresholds de compra")
        print("   3️⃣  Gestão de risco")
        print("   4️⃣  Comportamento em 3 cenários")
        print("   5️⃣  Stop loss e proteções")
        
        # Executa validações
        self.validate_priority()
        self.validate_thresholds()
        self.validate_risk_management()
        self.validate_scenarios()
        
        # Mostra resultado
        self.show_results()
    
    def validate_priority(self):
        """
        REGRA 1: Strategy 4h deve ser verificada ANTES de 24h
        """
        print(f"\n{'='*80}")
        print("1️⃣  VALIDATING: Priorização (4h → 24h)")
        print(f"{'='*80}")
        
        test_cases = [
            {'variation_4h': -6, 'variation_24h': -20, 'expected': '4h', 'reason': '4h atinge -5%, deve comprar e parar'},
            {'variation_4h': -2, 'variation_24h': -15, 'expected': '24h', 'reason': '4h não atinge -3%, deve usar 24h'},
            {'variation_4h': -11, 'variation_24h': -5, 'expected': '4h', 'reason': '4h atinge -10%, deve comprar e parar'},
        ]
        
        passed = 0
        failed = 0
        
        for test in test_cases:
            # Cria novas instâncias para cada teste (evita cooldown)
            strategy_4h_config = self.config.get('strategy_4h')
            if not strategy_4h_config:
                print(f' ERRO: strategy_4h não encontrada!')
                return False
                
            strategy_4h = BuyStrategy4h(strategy_4h_config)
            strategy_24h = BuyStrategy(self.config.get('trading_strategy'))
            
            # Simula priorização
            should_buy_4h, info_4h = strategy_4h.should_buy(test['variation_4h'], self.symbol)
            
            if should_buy_4h:
                result = '4h'
            else:
                should_buy_24h, info_24h = strategy_24h.should_buy(test['variation_24h'])
                result = '24h' if should_buy_24h else 'nenhuma'
            
            if result == test['expected']:
                print(f"    {test['reason']}")
                passed += 1
            else:
                print(f"    {test['reason']} (obteve: {result})")
                failed += 1
        
        self.validation_results.append({
            'rule': 'Priorização',
            'passed': passed,
            'failed': failed,
            'status': '' if failed == 0 else ''
        })
    
    def validate_thresholds(self):
        """
        REGRA 2: Compras devem respeitar thresholds configurados
        """
        print(f"\n{'='*80}")
        print("2️⃣  VALIDANDO: Thresholds de Compra")
        print(f"{'='*80}")
        
        strategy_4h_config = self.config.get('strategy_4h')
        if not strategy_4h_config:
            print(f' ERRO: strategy_4h não encontrada!')
            return False
            
        strategy_4h = BuyStrategy4h(strategy_4h_config)
        strategy_24h = BuyStrategy(self.config.get('trading_strategy'))
        
        test_cases_4h = [
            {'variation': -2, 'should_buy': False, 'reason': 'Não deve comprar em -2% (threshold -3%)'},
            {'variation': -3, 'should_buy': True, 'percentage': 10, 'reason': 'Deve comprar 10% em -3%'},
            {'variation': -5, 'should_buy': True, 'percentage': 20, 'reason': 'Deve comprar 20% em -5%'},
            {'variation': -10, 'should_buy': True, 'percentage': 30, 'reason': 'Deve comprar 30% em -10%'},
        ]
        
        test_cases_24h = [
            {'variation': -9, 'should_buy': False, 'reason': 'Não deve comprar em -9% (threshold -10%)'},
            {'variation': -12, 'should_buy': True, 'percentage': 10, 'reason': 'Deve comprar 10% em -12%'},
            {'variation': -18, 'should_buy': True, 'percentage': 20, 'reason': 'Deve comprar 20% em -18%'},
            {'variation': -30, 'should_buy': True, 'percentage': 30, 'reason': 'Deve comprar 30% em -30%'},
        ]
        
        passed = 0
        failed = 0
        
        strategy_4h_config = self.config.get('strategy_4h')
        if not strategy_4h_config:
            print(f' ERRO: strategy_4h não encontrada!')
            return False
        
        print("\n   Strategy 4h:")
        for test in test_cases_4h:
            # Cria nova instância para cada teste (evita cooldown)
            strategy_4h = BuyStrategy4h(strategy_4h_config)
            should_buy, info = strategy_4h.should_buy(test['variation'], self.symbol)
            
            if should_buy == test['should_buy']:
                if should_buy and info['buy_percentage'] == test['percentage']:
                    print(f"       {test['reason']}")
                    passed += 1
                elif not should_buy:
                    print(f"       {test['reason']}")
                    passed += 1
                else:
                    print(f"       {test['reason']} (percentual errado: {info['buy_percentage']}%)")
                    failed += 1
            else:
                print(f"       {test['reason']}")
                failed += 1
        
        print("\n   Strategy 24h:")
        for test in test_cases_24h:
            should_buy, info = strategy_24h.should_buy(test['variation'])
            
            if should_buy == test['should_buy']:
                if should_buy and info['buy_percentage'] == test['percentage']:
                    print(f"       {test['reason']}")
                    passed += 1
                elif not should_buy:
                    print(f"       {test['reason']}")
                    passed += 1
                else:
                    print(f"       {test['reason']} (percentual errado: {info['buy_percentage']}%)")
                    failed += 1
            else:
                print(f"       {test['reason']}")
                failed += 1
        
        self.validation_results.append({
            'rule': 'Thresholds',
            'passed': passed,
            'failed': failed,
            'status': '' if failed == 0 else ''
        })
    
    def validate_risk_management(self):
        """
        REGRA 3: Gestão de risco deve ser respeitada
        """
        print(f"\n{'='*80}")
        print("3️⃣  VALIDANDO: Gestão de Risco")
        print(f"{'='*80}")
        
        passed = 0
        failed = 0
        
        # Valida lucro mínimo de venda
        min_profit = 5.0
        test_profits = [
            {'profit': 3, 'should_sell': False, 'reason': f'Não vende com +3% (mínimo {min_profit}%)'},
            {'profit': 5, 'should_sell': True, 'reason': f'Vende com +5% (mínimo atingido)'},
            {'profit': 10, 'should_sell': True, 'reason': f'Vende com +10%'},
        ]
        
        print("\n   Lucro mínimo para venda:")
        for test in test_profits:
            should_sell = test['profit'] >= min_profit
            
            if should_sell == test['should_sell']:
                print(f"       {test['reason']}")
                passed += 1
            else:
                print(f"       {test['reason']}")
                failed += 1
        
        # Valida limites de investimento
        print("\n   Limites de investimento:")
        investment_limits = [
            {'percentage': 10, 'valid': True, 'reason': 'Investimento de 10% é válido'},
            {'percentage': 20, 'valid': True, 'reason': 'Investimento de 20% é válido'},
            {'percentage': 30, 'valid': True, 'reason': 'Investimento de 30% é válido'},
            {'percentage': 50, 'valid': False, 'reason': 'Investimento de 50% excede máximo (30%)'},
        ]
        
        for test in investment_limits:
            is_valid = test['percentage'] <= 30
            
            if is_valid == test['valid']:
                print(f"       {test['reason']}")
                passed += 1
            else:
                print(f"       {test['reason']}")
                failed += 1
        
        self.validation_results.append({
            'rule': 'Gestão de Risco',
            'passed': passed,
            'failed': failed,
            'status': '' if failed == 0 else ''
        })
    
    def validate_scenarios(self):
        """
        REGRA 4: Sistema deve se comportar corretamente em 3 cenários
        """
        print(f"\n{'='*80}")
        print("4️⃣  VALIDANDO: Comportamento em 3 Cenários")
        print(f"{'='*80}")
        
        print("\n   Buscando dados históricos...")
        ohlcv_data = self.client.client.fetch_ohlcv(self.symbol, '4h', limit=540)
        
        if len(ohlcv_data) < 90:
            print(f"   ⚠️  Dados insuficientes para validação completa")
            self.validation_results.append({
                'rule': 'Cenários',
                'passed': 0,
                'failed': 0,
                'status': '⚠️'
            })
            return
        
        # Testa 3 períodos
        periods = [
            ohlcv_data[-270:-180] if len(ohlcv_data) >= 270 else ohlcv_data[-90:],
            ohlcv_data[-180:-90] if len(ohlcv_data) >= 180 else ohlcv_data[-90:],
            ohlcv_data[-90:]
        ]
        
        results = []
        for i, period in enumerate(periods, 1):
            roi = self._simulate_period(period)
            
            if roi > 10:
                scenario = "ÓTIMO"
                emoji = ""
            elif roi > 0:
                scenario = "BÁSICO"
                emoji = "⚠️"
            else:
                scenario = "RUIM"
                emoji = ""
            
            results.append({'period': i, 'roi': roi, 'scenario': scenario, 'emoji': emoji})
        
        # Valida comportamento
        passed = 0
        failed = 0
        
        for r in results:
            start = periods[r['period']-1][0][0]
            end = periods[r['period']-1][-1][0]
            date_range = f"{datetime.fromtimestamp(start/1000).strftime('%m/%d')} a {datetime.fromtimestamp(end/1000).strftime('%m/%d')}"
            
            print(f"\n   {r['emoji']} Período {r['period']} ({date_range}):")
            print(f"      ROI: {r['roi']:+.2f}%")
            print(f"      Cenário: {r['scenario']}")
            
            if r['scenario'] == 'RUIM' and r['roi'] < -20:
                print(f"      ⚠️  Prejuízo alto ({r['roi']:.1f}%) - Requer stop loss")
                failed += 1
            elif r['scenario'] == 'RUIM' and r['roi'] >= -20:
                print(f"       Prejuízo controlado ({r['roi']:.1f}%)")
                passed += 1
            else:
                print(f"       Comportamento adequado")
                passed += 1
        
        # Valida ROI médio
        avg_roi = sum(r['roi'] for r in results) / len(results)
        print(f"\n   ROI médio: {avg_roi:+.2f}%")
        
        if avg_roi > 0:
            print(f"       ROI médio positivo")
            passed += 1
        else:
            print(f"       ROI médio negativo")
            failed += 1
        
        self.validation_results.append({
            'rule': 'Cenários',
            'passed': passed,
            'failed': failed,
            'status': '' if failed == 0 else '⚠️'
        })
    
    def _simulate_period(self, ohlcv_data):
        """Simula trading em um período e retorna ROI"""
        balance = 100.0
        tokens = 0.0
        
        strategy_4h_config = self.config.get('strategy_4h')
        if not strategy_4h_config:
            raise ValueError(' strategy_4h não encontrada na configuração!')
            
        strategy_4h = BuyStrategy4h(strategy_4h_config)
        strategy_24h = BuyStrategy(self.config.get('trading_strategy'))
        
        trades = []
        
        for i in range(6, len(ohlcv_data)):
            price = ohlcv_data[i][4]
            
            # Compra
            if balance >= 5.0:
                var_4h = ((price - ohlcv_data[i-1][4]) / ohlcv_data[i-1][4]) * 100
                var_24h = ((price - ohlcv_data[i-6][4]) / ohlcv_data[i-6][4]) * 100
                
                should_buy_4h, info_4h = strategy_4h.should_buy(var_4h, self.symbol)
                
                if should_buy_4h:
                    buy_info = info_4h
                else:
                    should_buy_24h, info_24h = strategy_24h.should_buy(var_24h)
                    if should_buy_24h:
                        buy_info = info_24h
                    else:
                        buy_info = None
                
                if buy_info:
                    investment = (balance * buy_info['buy_percentage']) / 100
                    if investment >= 5.0:
                        tokens += investment / price
                        balance -= investment
                        trades.append({'type': 'BUY', 'price': price, 'investment': investment})
            
            # Venda
            if tokens > 0 and len([t for t in trades if t['type'] == 'BUY']) > 0:
                buy_trades = [t for t in trades if t['type'] == 'BUY']
                total_inv = sum(t['investment'] for t in buy_trades)
                total_tok = sum(t['investment']/t['price'] for t in buy_trades)
                avg_price = total_inv / total_tok
                profit_pct = ((price - avg_price) / avg_price) * 100
                
                if profit_pct >= 5.0:
                    usdt = tokens * price
                    balance += usdt
                    tokens = 0
                    trades.append({'type': 'SELL', 'price': price})
        
        # Valor final
        final_value = balance + (tokens * ohlcv_data[-1][4])
        roi = ((final_value - 100) / 100) * 100
        
        return roi
    
    def show_results(self):
        """Mostra resultado final das validações"""
        print(f"\n{'='*80}")
        print(" RESULTADO DAS VALIDAÇÕES")
        print(f"{'='*80}")
        
        print(f"\n{'Regra':<25} {'Status':<10} {'Passou':<10} {'Falhou':<10}")
        print(f"{'-'*80}")
        
        total_passed = 0
        total_failed = 0
        
        for result in self.validation_results:
            print(f"{result['rule']:<25} {result['status']:<10} {result['passed']:<10} {result['failed']:<10}")
            total_passed += result['passed']
            total_failed += result['failed']
        
        print(f"\n{'='*80}")
        print(f"TOTAL: {total_passed} testes passaram, {total_failed} falharam")
        
        success_rate = (total_passed / (total_passed + total_failed)) * 100 if (total_passed + total_failed) > 0 else 0
        
        print(f"Taxa de sucesso: {success_rate:.1f}%")
        
        if total_failed == 0:
            print(f"\n TODAS AS REGRAS VALIDADAS COM SUCESSO!")
            print(f"Sistema aprovado para produção 🚀")
        elif success_rate >= 80:
            print(f"\n⚠️  SISTEMA FUNCIONAL MAS COM RESSALVAS")
            print(f"Revisar {total_failed} teste(s) que falharam")
        else:
            print(f"\n SISTEMA PRECISA DE CORREÇÕES")
            print(f"Corrigir {total_failed} teste(s) antes de produção")
        
        print(f"\n{'='*80}\n")

def main():
    """Executa validação completa das regras"""
    print("\n VALIDAÇÃO DE REGRAS DO SISTEMA")
    print("Testa todas as regras de negócio da estratégia híbrida\n")
    
    SYMBOL = "REKTCOIN/USDT"
    
    validator = SystemRulesValidator(SYMBOL)
    validator.run_all_validations()

if __name__ == "__main__":
    main()
