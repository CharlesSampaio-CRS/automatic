"""
═══════════════════════════════════════════════════════════════════════════
SUITE DE TESTES COMPLETA - Sistema de Trading Automatizado
═══════════════════════════════════════════════════════════════════════════

Este arquivo contém TODOS os testes do sistema unificados em um único local.

Categorias:
1. Testes de Estrutura Unificada
2. Testes de Estratégias (4h e 24h)
3. Testes de Smart Investment
4. Testes de Position Sizing
5. Testes de Cooldown e Limites
6. Testes de Venda
7. Testes de Integração

Executar: python3 test_suite.py
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from src.clients.buy_strategy import BuyStrategy
from src.clients.sell_strategy import SellStrategy
from src.clients.smart_investment_strategy import SmartInvestmentStrategy

def print_section(title):
    """Imprime uma seção formatada"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

def print_test(number, title):
    """Imprime um título de teste"""
    print(f"\n{number} TESTE: {title}")
    print("-" * 80)

def print_result(passed, message):
    """Imprime resultado do teste"""
    emoji = "✅" if passed else "❌"
    print(f"{emoji} {message}")

# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURAÇÃO DE TESTE
# ═══════════════════════════════════════════════════════════════════════════

CONFIG_COMPLETA = {
    'trading_strategy': {
        'buy_on_dip': {
            'thresholds': [
                {'variation_max': -5.0, 'percentage_of_balance': 20, 'description': 'Compra Leve'},
                {'variation_max': -10.0, 'percentage_of_balance': 30, 'description': 'Compra Moderada'},
                {'variation_max': -15.0, 'percentage_of_balance': 50, 'description': 'Compra Forte'}
            ]
        }
    },
    'strategy_4h': {
        'enabled': True,
        'buy_strategy': {
            'levels': [
                {'name': 'Nível 1', 'variation_threshold': -3.0, 'percentage_of_balance': 10},
                {'name': 'Nível 2', 'variation_threshold': -5.0, 'percentage_of_balance': 20},
                {'name': 'Nível 3', 'variation_threshold': -10.0, 'percentage_of_balance': 30}
            ]
        },
        'risk_management': {
            'cooldown_minutes': 15,
            'max_trades_per_hour': 3,
            'max_percentage_per_trade': 30.0
        },
        'quick_profit_target': 5.0
    },
    'sell_strategy': {
        'levels': [
            {'sell_percentage': 100, 'profit_target': 5.0, 'name': 'Venda Simples'}
        ]
    }
}

# ═══════════════════════════════════════════════════════════════════════════
# TESTES
# ═══════════════════════════════════════════════════════════════════════════

print_section("SUITE DE TESTES COMPLETA - Sistema de Trading")

tests_passed = 0
tests_failed = 0
tests_total = 0

# ═══════════════════════════════════════════════════════════════════════════
# CATEGORIA 1: ESTRUTURA UNIFICADA
# ═══════════════════════════════════════════════════════════════════════════

print_section("CATEGORIA 1: ESTRUTURA UNIFICADA")

# Teste 1: Inicialização de BuyStrategy
print_test("1️⃣", "Inicialização de BuyStrategy")
tests_total += 1
try:
    buy_strategy = BuyStrategy(CONFIG_COMPLETA)
    info = buy_strategy.get_strategy_info()
    
    assert info['strategy_4h']['enabled'] == True, "Strategy 4h deveria estar habilitada"
    assert len(info['strategy_4h']['levels']) == 3, "Deveria ter 3 níveis 4h"
    assert len(info['strategy_24h']['levels']) == 3, "Deveria ter 3 níveis 24h"
    assert info['strategy_4h']['risk_management']['cooldown_minutes'] == 15, "Cooldown deveria ser 15min"
    
    print(f"Strategy 4h habilitada: {info['strategy_4h']['enabled']}")
    print(f"Níveis 4h: {len(info['strategy_4h']['levels'])}")
    print(f"Níveis 24h: {len(info['strategy_24h']['levels'])}")
    print(f"Cooldown: {info['strategy_4h']['risk_management']['cooldown_minutes']} min")
    
    print_result(True, "PASSOU: BuyStrategy inicializada corretamente")
    tests_passed += 1
except Exception as e:
    print_result(False, f"FALHOU: {e}")
    tests_failed += 1

# Teste 2: Inicialização de SellStrategy
print_test("2️⃣", "Inicialização de SellStrategy")
tests_total += 1
try:
    sell_strategy = SellStrategy(CONFIG_COMPLETA)
    info = sell_strategy.get_strategy_info()
    
    assert info['mode'] == 'simple', "Modo deveria ser 'simple'"
    assert info['quick_sell']['enabled'] == True, "Quick sell deveria estar habilitada"
    assert info['quick_sell']['profit_target'] == 5.0, "Profit target deveria ser 5%"
    
    print(f"Modo: {info['mode']}")
    print(f"Quick sell: {info['quick_sell']['enabled']}")
    print(f"Profit target: {info['quick_sell']['profit_target']}%")
    
    print_result(True, "PASSOU: SellStrategy inicializada corretamente")
    tests_passed += 1
except Exception as e:
    print_result(False, f"FALHOU: {e}")
    tests_failed += 1

# ═══════════════════════════════════════════════════════════════════════════
# CATEGORIA 2: ESTRATÉGIAS DE COMPRA
# ═══════════════════════════════════════════════════════════════════════════

print_section("CATEGORIA 2: ESTRATÉGIAS DE COMPRA")

# Teste 3: Strategy 4h - Queda -4% (Nível 1)
print_test("3️⃣", "Strategy 4h - Queda -4% deve ativar Nível 1 (10%)")
tests_total += 1
try:
    should_buy, info = buy_strategy.should_buy_4h(-4.0, "TEST/USDT")
    
    assert should_buy == True, "Deveria comprar com -4%"
    assert info['buy_percentage'] == 10, "Deveria ser 10%"
    assert info['level'] == 'Nível 1', "Deveria ser Nível 1"
    assert info['strategy'] == '4h', "Estratégia deveria ser 4h"
    
    print(f"Variação: -4.0%")
    print(f"Deve comprar: {should_buy}")
    print(f"Nível: {info['level']}")
    print(f"Percentual: {info['buy_percentage']}%")
    
    print_result(True, "PASSOU: Ativou Nível 1 da estratégia 4h")
    tests_passed += 1
except Exception as e:
    print_result(False, f"FALHOU: {e}")
    tests_failed += 1

# Teste 4: Strategy 4h - Queda -6% (Nível 2)
print_test("4️⃣", "Strategy 4h - Queda -6% deve ativar Nível 2 (20%)")
tests_total += 1
try:
    # Limpa trades anteriores para evitar cooldown
    buy_strategy.recent_trades = []
    
    should_buy, info = buy_strategy.should_buy_4h(-6.0, "TEST2/USDT")
    
    assert should_buy == True, "Deveria comprar com -6%"
    assert info['buy_percentage'] == 20, "Deveria ser 20%"
    assert info['level'] == 'Nível 2', "Deveria ser Nível 2"
    
    print(f"Variação: -6.0%")
    print(f"Nível: {info['level']}")
    print(f"Percentual: {info['buy_percentage']}%")
    
    print_result(True, "PASSOU: Ativou Nível 2 da estratégia 4h")
    tests_passed += 1
except Exception as e:
    print_result(False, f"FALHOU: {e}")
    tests_failed += 1

# Teste 5: Strategy 4h - Queda -12% (Nível 3)
print_test("5️⃣", "Strategy 4h - Queda -12% deve ativar Nível 3 (30%)")
tests_total += 1
try:
    buy_strategy.recent_trades = []
    
    should_buy, info = buy_strategy.should_buy_4h(-12.0, "TEST3/USDT")
    
    assert should_buy == True, "Deveria comprar com -12%"
    assert info['buy_percentage'] == 30, "Deveria ser 30%"
    assert info['level'] == 'Nível 3', "Deveria ser Nível 3"
    
    print(f"Variação: -12.0%")
    print(f"Nível: {info['level']}")
    print(f"Percentual: {info['buy_percentage']}%")
    
    print_result(True, "PASSOU: Ativou Nível 3 da estratégia 4h")
    tests_passed += 1
except Exception as e:
    print_result(False, f"FALHOU: {e}")
    tests_failed += 1

# Teste 6: Strategy 4h - Rejeita alta
print_test("6️⃣", "Strategy 4h - Deve rejeitar preço em alta")
tests_total += 1
try:
    should_buy, info = buy_strategy.should_buy_4h(+2.5, "TEST/USDT")
    
    assert should_buy == False, "Não deveria comprar em alta"
    assert "alta" in info['reason'].lower(), "Motivo deveria mencionar 'alta'"
    
    print(f"Variação: +2.5%")
    print(f"Deve comprar: {should_buy}")
    print(f"Motivo: {info['reason']}")
    
    print_result(True, "PASSOU: Rejeitou compra em alta")
    tests_passed += 1
except Exception as e:
    print_result(False, f"FALHOU: {e}")
    tests_failed += 1

# Teste 7: Strategy 4h - Rejeita queda insuficiente
print_test("7️⃣", "Strategy 4h - Deve rejeitar queda insuficiente (-2%)")
tests_total += 1
try:
    should_buy, info = buy_strategy.should_buy_4h(-2.0, "TEST/USDT")
    
    assert should_buy == False, "Não deveria comprar com -2%"
    assert "insuficiente" in info['reason'].lower(), "Motivo deveria mencionar 'insuficiente'"
    
    print(f"Variação: -2.0%")
    print(f"Deve comprar: {should_buy}")
    print(f"Motivo: {info['reason']}")
    
    print_result(True, "PASSOU: Rejeitou queda insuficiente")
    tests_passed += 1
except Exception as e:
    print_result(False, f"FALHOU: {e}")
    tests_failed += 1

# Teste 8: Strategy 24h - Queda -6%
print_test("8️⃣", "Strategy 24h - Queda -6% deve ativar Compra Leve (20%)")
tests_total += 1
try:
    should_buy, info = buy_strategy.should_buy_24h(-6.0)
    
    assert should_buy == True, "Deveria comprar com -6%"
    assert info['buy_percentage'] == 20, "Deveria ser 20%"
    assert info['strategy'] == '24h', "Estratégia deveria ser 24h"
    
    print(f"Variação: -6.0%")
    print(f"Nível: {info['level']}")
    print(f"Percentual: {info['buy_percentage']}%")
    
    print_result(True, "PASSOU: Ativou estratégia 24h")
    tests_passed += 1
except Exception as e:
    print_result(False, f"FALHOU: {e}")
    tests_failed += 1

# ═══════════════════════════════════════════════════════════════════════════
# CATEGORIA 3: SMART INVESTMENT STRATEGY
# ═══════════════════════════════════════════════════════════════════════════

print_section("CATEGORIA 3: SMART INVESTMENT STRATEGY")

# Teste 9: Smart Strategy - Saldo baixo ($6.30)
print_test("9️⃣", "Smart Strategy - Saldo baixo ($6.30) deve usar 100%")
tests_total += 1
try:
    smart_strategy = SmartInvestmentStrategy()
    adjusted_pct = smart_strategy.get_adjusted_percentage(6.30, 20.0)
    
    assert adjusted_pct == 100.0, "Deveria ajustar para 100%"
    
    print(f"Saldo: $6.30")
    print(f"Percentual original: 20%")
    print(f"Percentual ajustado: {adjusted_pct}%")
    
    print_result(True, "PASSOU: Ajustou para 100% com saldo baixo")
    tests_passed += 1
except Exception as e:
    print_result(False, f"FALHOU: {e}")
    tests_failed += 1

# Teste 10: Smart Strategy - Saldo alto ($50)
print_test("🔟", "Smart Strategy - Saldo alto ($50) deve manter percentual")
tests_total += 1
try:
    adjusted_pct = smart_strategy.get_adjusted_percentage(50.0, 20.0)
    
    assert adjusted_pct == 20.0, "Deveria manter 20%"
    
    print(f"Saldo: $50.00")
    print(f"Percentual original: 20%")
    print(f"Percentual ajustado: {adjusted_pct}%")
    
    print_result(True, "PASSOU: Manteve percentual com saldo alto")
    tests_passed += 1
except Exception as e:
    print_result(False, f"FALHOU: {e}")
    tests_failed += 1

# ═══════════════════════════════════════════════════════════════════════════
# CATEGORIA 4: POSITION SIZING
# ═══════════════════════════════════════════════════════════════════════════

print_section("CATEGORIA 4: POSITION SIZING")

# Teste 11: Position Size - Saldo baixo com 100%
print_test("1️⃣1️⃣", "Position Size - $6.30 com 100% deve investir $6.30")
tests_total += 1
try:
    position = buy_strategy.calculate_position_size(6.30, 100.0)
    
    assert position == 6.30, f"Deveria ser $6.30, mas foi ${position:.2f}"
    
    print(f"Saldo: $6.30")
    print(f"Percentual: 100%")
    print(f"Position size: ${position:.2f}")
    
    print_result(True, "PASSOU: Investiu 100% do saldo baixo")
    tests_passed += 1
except Exception as e:
    print_result(False, f"FALHOU: {e}")
    tests_failed += 1

# Teste 12: Position Size - Saldo alto com 10%
print_test("1️⃣2️⃣", "Position Size - $50 com 10% deve investir $5")
tests_total += 1
try:
    position = buy_strategy.calculate_position_size(50.0, 10.0)
    
    assert position == 5.0, f"Deveria ser $5.00, mas foi ${position:.2f}"
    
    print(f"Saldo: $50.00")
    print(f"Percentual: 10%")
    print(f"Position size: ${position:.2f}")
    
    print_result(True, "PASSOU: Aplicou percentual corretamente")
    tests_passed += 1
except Exception as e:
    print_result(False, f"FALHOU: {e}")
    tests_failed += 1

# Teste 13: Position Size - Limite de 30%
print_test("1️⃣3️⃣", "Position Size - $100 com 50% deve limitar a 30% ($30)")
tests_total += 1
try:
    position = buy_strategy.calculate_position_size(100.0, 50.0)
    
    assert position == 30.0, f"Deveria ser $30.00, mas foi ${position:.2f}"
    
    print(f"Saldo: $100.00")
    print(f"Percentual solicitado: 50%")
    print(f"Limite max: 30%")
    print(f"Position size: ${position:.2f}")
    
    print_result(True, "PASSOU: Aplicou limite de 30%")
    tests_passed += 1
except Exception as e:
    print_result(False, f"FALHOU: {e}")
    tests_failed += 1

# ═══════════════════════════════════════════════════════════════════════════
# CATEGORIA 5: COOLDOWN E LIMITES
# ═══════════════════════════════════════════════════════════════════════════

print_section("CATEGORIA 5: COOLDOWN E LIMITES")

# Teste 14: Cooldown - Bloqueia segunda compra
print_test("1️⃣4️⃣", "Cooldown - Deve bloquear segunda compra do mesmo par")
tests_total += 1
try:
    buy_strategy.recent_trades = []
    
    # Primeira compra
    should_buy1, info1 = buy_strategy.should_buy_4h(-5.0, "COOLDOWN/USDT")
    
    # Segunda compra (deve bloquear)
    should_buy2, info2 = buy_strategy.should_buy_4h(-8.0, "COOLDOWN/USDT")
    
    assert should_buy1 == True, "Primeira compra deveria passar"
    assert should_buy2 == False, "Segunda compra deveria ser bloqueada"
    assert "cooldown" in info2['reason'].lower(), "Motivo deveria mencionar cooldown"
    
    print(f"Primeira compra (-5%): {should_buy1}")
    print(f"Segunda compra (-8%): {should_buy2}")
    print(f"Motivo bloqueio: {info2['reason']}")
    
    print_result(True, "PASSOU: Cooldown funcionando")
    tests_passed += 1
except Exception as e:
    print_result(False, f"FALHOU: {e}")
    tests_failed += 1

# Teste 15: Cooldown - Permite compra de par diferente
print_test("1️⃣5️⃣", "Cooldown - Deve permitir compra de par diferente")
tests_total += 1
try:
    buy_strategy.recent_trades = []
    
    # Compra par 1
    should_buy1, info1 = buy_strategy.should_buy_4h(-5.0, "PAR1/USDT")
    
    # Compra par 2 (deve permitir)
    should_buy2, info2 = buy_strategy.should_buy_4h(-5.0, "PAR2/USDT")
    
    assert should_buy1 == True, "Primeira compra deveria passar"
    assert should_buy2 == True, "Segunda compra de par diferente deveria passar"
    
    print(f"Compra PAR1/USDT: {should_buy1}")
    print(f"Compra PAR2/USDT: {should_buy2}")
    
    print_result(True, "PASSOU: Permite compra de pares diferentes")
    tests_passed += 1
except Exception as e:
    print_result(False, f"FALHOU: {e}")
    tests_failed += 1

# ═══════════════════════════════════════════════════════════════════════════
# CATEGORIA 6: ESTRATÉGIAS DE VENDA
# ═══════════════════════════════════════════════════════════════════════════

print_section("CATEGORIA 6: ESTRATÉGIAS DE VENDA")

# Teste 16: Venda - Lucro 6% (deve vender)
print_test("1️⃣6️⃣", "Venda - Lucro 6% deve ativar venda")
tests_total += 1
try:
    should_sell, info = sell_strategy.should_sell(1.06, 1.0, "TEST/USDT")
    
    assert should_sell == True, "Deveria vender com 6% de lucro"
    assert round(info['current_profit'], 2) == 6.0, f"Lucro deveria ser 6%, mas foi {info['current_profit']:.2f}%"
    assert info['sell_percentage'] == 100, "Deveria vender 100%"
    
    print(f"Preço compra: $1.00")
    print(f"Preço atual: $1.06")
    print(f"Lucro: {info['current_profit']:.2f}%")
    print(f"Deve vender: {should_sell}")
    print(f"Percentual venda: {info['sell_percentage']}%")
    
    print_result(True, "PASSOU: Ativou venda com lucro >= 5%")
    tests_passed += 1
except Exception as e:
    print_result(False, f"FALHOU: {e}")
    tests_failed += 1

# Teste 17: Venda - Lucro 3% (não deve vender)
print_test("1️⃣7️⃣", "Venda - Lucro 3% não deve ativar venda")
tests_total += 1
try:
    should_sell, info = sell_strategy.should_sell(1.03, 1.0, "TEST/USDT")
    
    assert should_sell == False, "Não deveria vender com 3% de lucro"
    assert round(info['current_profit'], 2) == 3.0, f"Lucro deveria ser 3%, mas foi {info['current_profit']:.2f}%"
    
    print(f"Preço compra: $1.00")
    print(f"Preço atual: $1.03")
    print(f"Lucro: {info['current_profit']:.2f}%")
    print(f"Deve vender: {should_sell}")
    print(f"Motivo: {info['reason']}")
    
    print_result(True, "PASSOU: Aguardando lucro >= 5%")
    tests_passed += 1
except Exception as e:
    print_result(False, f"FALHOU: {e}")
    tests_failed += 1

# Teste 18: Venda - Lucro exatamente 5%
print_test("1️⃣8️⃣", "Venda - Lucro exatamente 5% deve ativar venda")
tests_total += 1
try:
    should_sell, info = sell_strategy.should_sell(1.05, 1.0, "TEST/USDT")
    
    assert should_sell == True, "Deveria vender com exatamente 5%"
    assert round(info['current_profit'], 2) == 5.0, f"Lucro deveria ser 5%, mas foi {info['current_profit']:.2f}%"
    
    print(f"Preço compra: $1.00")
    print(f"Preço atual: $1.05")
    print(f"Lucro: {info['current_profit']:.2f}%")
    print(f"Deve vender: {should_sell}")
    
    print_result(True, "PASSOU: Vendeu com lucro exato de 5%")
    tests_passed += 1
except Exception as e:
    print_result(False, f"FALHOU: {e}")
    tests_failed += 1

# ═══════════════════════════════════════════════════════════════════════════
# CATEGORIA 7: INTEGRAÇÃO
# ═══════════════════════════════════════════════════════════════════════════

print_section("CATEGORIA 7: INTEGRAÇÃO")

# Teste 19: Importação exchange.py
print_test("1️⃣9️⃣", "Integração - exchange.py importa corretamente")
tests_total += 1
try:
    from src.clients.exchange import MexcClient
    
    print("Importação bem-sucedida")
    
    print_result(True, "PASSOU: exchange.py integra com estrutura unificada")
    tests_passed += 1
except ImportError as e:
    print_result(False, f"FALHOU: {e}")
    tests_failed += 1

# Teste 20: Fluxo completo (compra + venda)
print_test("2️⃣0️⃣", "Fluxo completo - Simula compra e venda")
tests_total += 1
try:
    # Reset estado
    buy_strategy.recent_trades = []
    
    # 1. Detecta queda
    should_buy, buy_info = buy_strategy.should_buy_4h(-5.0, "FLOW/USDT")
    assert should_buy == True, "Deveria detectar oportunidade de compra"
    
    # 2. Ajusta percentual com Smart Strategy
    adjusted_pct = smart_strategy.get_adjusted_percentage(6.30, buy_info['buy_percentage'])
    assert adjusted_pct == 100.0, "Deveria ajustar para 100%"
    
    # 3. Calcula position size
    position = buy_strategy.calculate_position_size(6.30, adjusted_pct)
    assert position == 6.30, "Deveria investir $6.30"
    
    # 4. Simula compra a $1.00
    buy_price = 1.0
    amount_bought = position / buy_price
    
    # 5. Preço sobe para $1.06 (lucro 6%)
    current_price = 1.06
    
    # 6. Verifica venda
    should_sell, sell_info = sell_strategy.should_sell(current_price, buy_price, "FLOW/USDT")
    assert should_sell == True, "Deveria ativar venda"
    
    # 7. Calcula lucro
    sell_value = amount_bought * current_price
    profit = sell_value - position
    profit_pct = (profit / position) * 100
    
    print(f"1. Queda detectada: -5.0%")
    print(f"2. Percentual ajustado: {adjusted_pct}%")
    print(f"3. Investimento: ${position:.2f}")
    print(f"4. Preço compra: ${buy_price:.2f}")
    print(f"5. Preço venda: ${current_price:.2f}")
    print(f"6. Lucro: ${profit:.2f} ({profit_pct:.2f}%)")
    
    print_result(True, "PASSOU: Fluxo completo funcionando")
    tests_passed += 1
except Exception as e:
    print_result(False, f"FALHOU: {e}")
    tests_failed += 1

# ═══════════════════════════════════════════════════════════════════════════
# RESUMO FINAL
# ═══════════════════════════════════════════════════════════════════════════

print_section("RESUMO FINAL")

success_rate = (tests_passed / tests_total * 100) if tests_total > 0 else 0

print(f"\n📊 ESTATÍSTICAS:")
print(f"   Total de testes: {tests_total}")
print(f"   ✅ Passaram: {tests_passed}")
print(f"   ❌ Falharam: {tests_failed}")
print(f"   📈 Taxa de sucesso: {success_rate:.1f}%")

if tests_failed == 0:
    print("\n" + "=" * 80)
    print("🎉 TODOS OS TESTES PASSARAM! 🎉")
    print("=" * 80)
    print("\n✅ Sistema validado e pronto para uso!")
    print("\n📁 Estrutura:")
    print("   ✅ buy_strategy.py (unificado)")
    print("   ✅ sell_strategy.py (unificado)")
    print("   ✅ smart_investment_strategy.py")
    print("   ✅ exchange.py (integrado)")
else:
    print("\n" + "=" * 80)
    print("⚠️  ALGUNS TESTES FALHARAM")
    print("=" * 80)
    print(f"\n❌ {tests_failed} teste(s) precisam de atenção")
    exit(1)
