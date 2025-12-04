"""
Teste da nova regra de compra: -8% = 50% do saldo
"""

import sys
sys.path.append('/Users/charles.roberto/Documents/projects/crs-saturno/automatic')

from src.clients.buy_strategy_4h import BuyStrategy4h

def test_8percent_rule():
    """
    Testa a regra de compra para quedas >= -8%
    """
    print("\n" + "="*80)
    print("🧪 TESTE DA NOVA REGRA: -8% = 50% DO SALDO")
    print("="*80 + "\n")
    
    # Cria estratégia com configuração simulada do MongoDB
    strategy_4h_config = {
        'enabled': True,  # IMPORTANTE: Habilitar a estratégia
        'buy_strategy': {
            'levels': []  # Vazio = usa níveis padrão
        },
        'risk_management': {
            'stop_loss_percent': -3.0,
            'cooldown_minutes': 15,
            'max_trades_per_hour': 3,
            'max_percentage_per_trade': 50  # Permite até 50%
        }
    }
    
    strategy = BuyStrategy4h(strategy_4h_config)
    
    print("📋 Níveis de compra configurados:")
    for i, level in enumerate(strategy.buy_levels, 1):
        print(f"   {i}. {level['name']}")
        print(f"      Threshold: {level['variation_threshold']}%")
        print(f"      Investir: {level['percentage_of_balance']}%")
        print(f"      Descrição: {level['description']}")
        print()
    
    # Testa diferentes cenários
    test_cases = [
        {"variation": -2.0, "expected_level": "Scalp Leve", "expected_pct": 5},
        {"variation": -3.5, "expected_level": "Scalp Moderado", "expected_pct": 7},
        {"variation": -5.2, "expected_level": "Scalp Forte", "expected_pct": 10},
        {"variation": -8.0, "expected_level": "Queda Acentuada", "expected_pct": 50},
        {"variation": -8.1, "expected_level": "Queda Acentuada", "expected_pct": 50},
        {"variation": -10.0, "expected_level": "Queda Acentuada", "expected_pct": 50},
        {"variation": -7.9, "expected_level": "Scalp Forte", "expected_pct": 10},
        {"variation": -1.5, "expected_level": None, "expected_pct": 0},
        {"variation": 2.0, "expected_level": None, "expected_pct": 0},
    ]
    
    print("="*80)
    print("🎯 TESTANDO CENÁRIOS")
    print("="*80 + "\n")
    
    for i, test in enumerate(test_cases, 1):
        variation = test["variation"]
        expected_level = test["expected_level"]
        expected_pct = test["expected_pct"]
        
        print(f"Teste {i}: Variação 4h = {variation:+.1f}%")
        
        should_buy, buy_info = strategy.should_buy(variation, "TEST/USDT")
        
        if should_buy:
            level = buy_info.get('level', 'N/A')
            pct = buy_info.get('buy_percentage', 0)
            reason = buy_info.get('reason', 'N/A')
            
            print(f"   ✅ COMPRA ATIVADA")
            print(f"   Nível: {level}")
            print(f"   Percentual: {pct}%")
            print(f"   Motivo: {reason}")
            
            # Valida resultado esperado
            if expected_level:
                if level == expected_level and pct == expected_pct:
                    print(f"   ✅ CORRETO! (Esperado: {expected_level} - {expected_pct}%)")
                else:
                    print(f"   ❌ ERRO! Esperado: {expected_level} - {expected_pct}%, Recebido: {level} - {pct}%")
            else:
                print(f"   ❌ ERRO! Não deveria comprar neste caso")
        else:
            reason = buy_info.get('reason', 'N/A')
            print(f"   ⏸️  COMPRA NÃO ATIVADA")
            print(f"   Motivo: {reason}")
            
            # Valida resultado esperado
            if expected_level is None:
                print(f"   ✅ CORRETO! Não deve comprar")
            else:
                print(f"   ❌ ERRO! Deveria ativar: {expected_level} - {expected_pct}%")
        
        print()
    
    # Teste com saldo real
    print("="*80)
    print("💰 SIMULAÇÃO COM SALDO REAL")
    print("="*80 + "\n")
    
    balance = 22.60  # Saldo atual aproximado
    variation = -8.1  # Queda atual
    
    should_buy, buy_info = strategy.should_buy(variation, "REKT/USDT")
    
    if should_buy:
        pct = buy_info.get('buy_percentage', 0)
        investment = strategy.calculate_position_size(balance, pct)
        
        print(f"Saldo disponível: ${balance:.2f} USDT")
        print(f"Variação 4h: {variation:+.1f}%")
        print(f"Nível ativado: {buy_info.get('level', 'N/A')}")
        print(f"Percentual: {pct}%")
        print(f"Valor a investir: ${investment:.2f} USDT")
        print(f"\nCom MIN_VALUE_PER_SYMBOL = $2.00:")
        print(f"   ${investment:.2f} {'>' if investment >= 2.0 else '<'} $2.00 = {'✅ EXECUTARÁ!' if investment >= 2.0 else '❌ BLOQUEADO'}")
    else:
        print(f"❌ Compra não seria executada")
        print(f"Motivo: {buy_info.get('reason', 'N/A')}")
    
    print("\n" + "="*80)
    print("✅ TESTE COMPLETO")
    print("="*80 + "\n")


if __name__ == "__main__":
    test_8percent_rule()
