"""
Testes de Validação das Estratégias de Compra e Venda
Valida todas as regras de negócio implementadas
"""

import sys
import os

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.clients.buy_strategy import BuyStrategy
from src.clients.sell_strategy import SellStrategy

print("\n" + "="*80)
print("🧪 TESTES DE VALIDAÇÃO - ESTRATÉGIAS DE COMPRA E VENDA")
print("="*80)

# ============================================================================
# TESTE 1: Validar que NÃO compra na ALTA
# ============================================================================
print("\n" + "="*80)
print("📊 TESTE 1: Validar regra - NUNCA comprar na ALTA")
print("="*80)

buy_strategy = BuyStrategy()

test_cases_alta = [
    {"variation": 5.0, "should_buy": False, "description": "Alta de +5%"},
    {"variation": 10.0, "should_buy": False, "description": "Alta de +10%"},
    {"variation": 20.0, "should_buy": False, "description": "Alta de +20%"},
    {"variation": 33.0, "should_buy": False, "description": "Alta de +33%"},
    {"variation": 50.0, "should_buy": False, "description": "Alta de +50%"},
]

print("\n🔍 Testando variações POSITIVAS (alta):")
print("-"*80)

alta_tests_passed = 0
alta_tests_failed = 0

for test in test_cases_alta:
    should_buy, result = buy_strategy.should_buy(test["variation"])
    expected = test["should_buy"]
    status = "✅ PASS" if should_buy == expected else "❌ FAIL"
    
    if should_buy == expected:
        alta_tests_passed += 1
    else:
        alta_tests_failed += 1
    
    print(f"{status} | {test['description']:<20} | Resultado: {should_buy:<5} | Esperado: {expected}")
    if should_buy:
        print(f"      ⚠️  ERRO: Bot tentou comprar na ALTA! Razão: {result.get('reason', 'N/A')}")

print(f"\n📊 Resultado: {alta_tests_passed}/{len(test_cases_alta)} testes passaram")

# ============================================================================
# TESTE 2: Validar compra GRADATIVA na QUEDA
# ============================================================================
print("\n" + "="*80)
print("📊 TESTE 2: Validar regra - Compra GRADATIVA na QUEDA")
print("="*80)

test_cases_queda = [
    {"variation": -3.0, "should_buy": False, "level": None, "pct": 0, "description": "Queda de -3% (muito pouco)"},
    {"variation": -5.0, "should_buy": True, "level": "Compra Leve", "pct": 20, "description": "Queda de -5%"},
    {"variation": -7.0, "should_buy": True, "level": "Compra Leve", "pct": 20, "description": "Queda de -7%"},
    {"variation": -10.0, "should_buy": True, "level": "Compra Moderada", "pct": 30, "description": "Queda de -10%"},
    {"variation": -12.0, "should_buy": True, "level": "Compra Moderada", "pct": 30, "description": "Queda de -12%"},
    {"variation": -15.0, "should_buy": True, "level": "Compra Forte", "pct": 50, "description": "Queda de -15%"},
    {"variation": -18.0, "should_buy": True, "level": "Compra Forte", "pct": 50, "description": "Queda de -18%"},
    {"variation": -20.0, "should_buy": True, "level": "Compra Máxima", "pct": 100, "description": "Queda de -20%"},
    {"variation": -25.0, "should_buy": True, "level": "Compra Máxima", "pct": 100, "description": "Queda de -25%"},
]

print("\n🔍 Testando variações NEGATIVAS (queda):")
print("-"*80)

queda_tests_passed = 0
queda_tests_failed = 0

for test in test_cases_queda:
    should_buy, result = buy_strategy.should_buy(test["variation"])
    expected_buy = test["should_buy"]
    expected_pct = test["pct"]
    
    buy_match = should_buy == expected_buy
    pct_match = result.get("buy_percentage", 0) == expected_pct if expected_buy else True
    
    test_passed = buy_match and pct_match
    status = "✅ PASS" if test_passed else "❌ FAIL"
    
    if test_passed:
        queda_tests_passed += 1
    else:
        queda_tests_failed += 1
    
    level_name = result.get('level', {}).get('name', 'N/A') if should_buy else 'N/A'
    print(f"{status} | {test['description']:<25} | Compra: {should_buy:<5} | % Saldo: {result.get('buy_percentage', 0):>3}% | Nível: {level_name}")
    
    if not test_passed:
        print(f"      ⚠️  ERRO: Esperado comprar={expected_buy}, %={expected_pct}%, mas obteve comprar={should_buy}, %={result.get('buy_percentage', 0)}%")

print(f"\n📊 Resultado: {queda_tests_passed}/{len(test_cases_queda)} testes passaram")

# ============================================================================
# TESTE 3: Validar que quanto MAIOR a queda, MAIOR o investimento
# ============================================================================
print("\n" + "="*80)
print("📊 TESTE 3: Validar regra - Quanto MAIOR a queda, MAIOR o investimento")
print("="*80)

quedas_ordenadas = [-5.0, -10.0, -15.0, -20.0]
percentuais_esperados = [20, 30, 50, 100]

print("\n🔍 Validando progressão do investimento:")
print("-"*80)

progressao_tests_passed = 0
progressao_tests_failed = 0

percentual_anterior = 0
for i, (queda, pct_esperado) in enumerate(zip(quedas_ordenadas, percentuais_esperados), 1):
    should_buy, result = buy_strategy.should_buy(queda)
    pct_obtido = result.get("buy_percentage", 0)
    
    # Valida que o percentual aumentou
    aumentou = pct_obtido > percentual_anterior
    correto = pct_obtido == pct_esperado
    
    status = "✅ PASS" if aumentou and correto else "❌ FAIL"
    
    if aumentou and correto:
        progressao_tests_passed += 1
    else:
        progressao_tests_failed += 1
    
    print(f"{status} | Nível {i}: Queda {queda:>6.1f}% → Investe {pct_obtido:>3}% (esperado: {pct_esperado}%) | Aumentou: {aumentou}")
    
    if not correto:
        print(f"      ⚠️  ERRO: Esperado {pct_esperado}%, obteve {pct_obtido}%")
    
    percentual_anterior = pct_obtido

print(f"\n📊 Resultado: {progressao_tests_passed}/{len(quedas_ordenadas)} testes passaram")

# ============================================================================
# TESTE 4: Validar estratégia de VENDA PROGRESSIVA
# ============================================================================
print("\n" + "="*80)
print("📊 TESTE 4: Validar regra - Venda PROGRESSIVA em níveis")
print("="*80)

sell_strategy = SellStrategy()

# Simula uma compra
buy_price = 0.00000031721
amount_bought = 340000000
investment = 107.85

sell_targets = sell_strategy.calculate_sell_targets(buy_price, amount_bought, investment)

print("\n🔍 Validando níveis de venda:")
print("-"*80)

venda_tests_passed = 0
venda_tests_failed = 0

expected_levels = [
    {"level": 1, "percentage": 33, "profit_target": 10.0},
    {"level": 2, "percentage": 33, "profit_target": 15.0},
    {"level": 3, "percentage": 34, "profit_target": 20.0},
]

for expected, actual in zip(expected_levels, sell_targets):
    level_match = expected["level"] == actual["level"]
    pct_match = expected["percentage"] == actual["sell_percentage"]
    profit_match = expected["profit_target"] == actual["profit_target_pct"]
    
    test_passed = level_match and pct_match and profit_match
    status = "✅ PASS" if test_passed else "❌ FAIL"
    
    if test_passed:
        venda_tests_passed += 1
    else:
        venda_tests_failed += 1
    
    print(f"{status} | {actual['name']:<25} | Vende: {actual['sell_percentage']:>2}% em +{actual['profit_target_pct']:>4.1f}% | Preço: ${actual['target_price']:.8f}")
    
    if not test_passed:
        print(f"      ⚠️  ERRO: Esperado {expected['percentage']}% em +{expected['profit_target']}%, obteve {actual['sell_percentage']}% em +{actual['profit_target_pct']}%")

print(f"\n📊 Resultado: {venda_tests_passed}/{len(expected_levels)} testes passaram")

# ============================================================================
# TESTE 5: Validar que soma das vendas = 100%
# ============================================================================
print("\n" + "="*80)
print("📊 TESTE 5: Validar regra - Soma das vendas = 100%")
print("="*80)

total_sell_pct = sum(t["sell_percentage"] for t in sell_targets)
expected_total = 100

status = "✅ PASS" if total_sell_pct == expected_total else "❌ FAIL"
soma_test_passed = total_sell_pct == expected_total

print(f"\n{status} | Soma das porcentagens de venda: {total_sell_pct}% (esperado: {expected_total}%)")

if not soma_test_passed:
    print(f"      ⚠️  ERRO: A soma das vendas deveria ser {expected_total}%, mas é {total_sell_pct}%")

# ============================================================================
# TESTE 6: Validar que preços de venda são CRESCENTES
# ============================================================================
print("\n" + "="*80)
print("📊 TESTE 6: Validar regra - Preços de venda são CRESCENTES")
print("="*80)

print("\n🔍 Validando ordem crescente dos preços:")
print("-"*80)

ordem_tests_passed = 0
ordem_tests_failed = 0

for i in range(len(sell_targets) - 1):
    current = sell_targets[i]
    next_level = sell_targets[i + 1]
    
    is_ascending = current["target_price"] < next_level["target_price"]
    status = "✅ PASS" if is_ascending else "❌ FAIL"
    
    if is_ascending:
        ordem_tests_passed += 1
    else:
        ordem_tests_failed += 1
    
    print(f"{status} | Nível {i+1} (${current['target_price']:.8f}) < Nível {i+2} (${next_level['target_price']:.8f}) = {is_ascending}")
    
    if not is_ascending:
        print(f"      ⚠️  ERRO: Preço do nível {i+2} deveria ser MAIOR que nível {i+1}")

print(f"\n📊 Resultado: {ordem_tests_passed}/{len(sell_targets)-1} testes passaram")

# ============================================================================
# TESTE 7: Validar cálculo de lucro
# ============================================================================
print("\n" + "="*80)
print("📊 TESTE 7: Validar regra - Cálculo de lucro está correto")
print("="*80)

print("\n🔍 Validando cálculos de lucro:")
print("-"*80)

lucro_tests_passed = 0
lucro_tests_failed = 0

for target in sell_targets:
    # Calcula lucro esperado manualmente (usando valores ANTES de arredondar)
    invested_in_level = (investment * target["sell_percentage"]) / 100
    amount_to_sell = (amount_bought * target["sell_percentage"]) / 100
    # Usa o preço SEM arredondar para cálculo preciso
    target_price_full = buy_price * (1 + target["profit_target_pct"] / 100)
    usdt_received = amount_to_sell * target_price_full
    expected_profit = usdt_received - invested_in_level
    
    # Compara com o calculado (com tolerância para arredondamento)
    profit_match = abs(target["profit_usdt"] - expected_profit) < 0.01  # Tolerância de 1 centavo
    status = "✅ PASS" if profit_match else "❌ FAIL"
    
    if profit_match:
        lucro_tests_passed += 1
    else:
        lucro_tests_failed += 1
    
    print(f"{status} | {target['name']:<25} | Investido: ${invested_in_level:.2f} | Recebe: ${target['usdt_received']:.2f} | Lucro: ${target['profit_usdt']:.2f}")
    
    if not profit_match:
        print(f"      ⚠️  ERRO: Lucro esperado ${expected_profit:.2f}, obteve ${target['profit_usdt']:.2f}")

print(f"\n📊 Resultado: {lucro_tests_passed}/{len(sell_targets)} testes passaram")

# ============================================================================
# RESUMO FINAL
# ============================================================================
print("\n" + "="*80)
print("📊 RESUMO FINAL DOS TESTES")
print("="*80)

total_tests = (
    len(test_cases_alta) + 
    len(test_cases_queda) + 
    len(quedas_ordenadas) + 
    len(expected_levels) + 
    1 +  # teste soma
    (len(sell_targets) - 1) +  # teste ordem
    len(sell_targets)  # teste lucro
)

total_passed = (
    alta_tests_passed + 
    queda_tests_passed + 
    progressao_tests_passed + 
    venda_tests_passed + 
    (1 if soma_test_passed else 0) +
    ordem_tests_passed +
    lucro_tests_passed
)

total_failed = total_tests - total_passed

print(f"\n   Total de Testes: {total_tests}")
print(f"   ✅ Passaram: {total_passed} ({(total_passed/total_tests)*100:.1f}%)")
print(f"   ❌ Falharam: {total_failed} ({(total_failed/total_tests)*100:.1f}%)")

print("\n📋 REGRAS VALIDADAS:")
print("-"*80)
print(f"   {'✅' if alta_tests_passed == len(test_cases_alta) else '❌'} 1. NUNCA comprar na ALTA")
print(f"   {'✅' if queda_tests_passed == len(test_cases_queda) else '❌'} 2. Comprar APENAS na QUEDA")
print(f"   {'✅' if progressao_tests_passed == len(quedas_ordenadas) else '❌'} 3. Quanto MAIOR a queda, MAIOR o investimento")
print(f"   {'✅' if venda_tests_passed == len(expected_levels) else '❌'} 4. Venda PROGRESSIVA em 3 níveis")
print(f"   {'✅' if soma_test_passed else '❌'} 5. Soma das vendas = 100%")
print(f"   {'✅' if ordem_tests_passed == (len(sell_targets)-1) else '❌'} 6. Preços de venda CRESCENTES")
print(f"   {'✅' if lucro_tests_passed == len(sell_targets) else '❌'} 7. Cálculos de lucro CORRETOS")

if total_failed == 0:
    print("\n" + "="*80)
    print("="*80)
    print("✅ Todas as regras de negócio estão implementadas corretamente!")
    print("✅ Compra APENAS na queda, de forma gradativa")
    print("✅ Vende de forma progressiva em múltiplos níveis")
    print("="*80)
else:
    print("\n" + "="*80)
    print(f"⚠️  {total_failed} TESTE(S) FALHARAM!")
    print("="*80)
    print("\n❌ Revise o código antes de colocar em produção!")
    print("="*80)

print()
