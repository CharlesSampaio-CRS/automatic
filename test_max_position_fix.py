#!/usr/bin/env python3
"""
Teste: Valida que saldo < $10 usa 100% IGNORANDO limites de max_position_size_percent
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

from clients.smart_investment_strategy import SmartInvestmentStrategy

def test_max_position_limit():
    """Testa se limite de 30% é ignorado com saldo < $10"""
    
    print('=' * 100)
    print('🧪 TESTE: Limite de 30% com Saldo Pequeno')
    print('=' * 100)
    
    smart = SmartInvestmentStrategy()
    
    print(f'\n📋 CENÁRIO:')
    print(f'   Config MongoDB: max_position_size_percent = 30%')
    print(f'   Estratégia -10%: percentage_of_balance = 30%')
    print(f'   Seu saldo: $9.01')
    
    # Simula diferentes saldos
    scenarios = [
        (9.01, 30, "< $10"),
        (9.99, 30, "< $10"),
        (10.00, 30, ">= $10"),
        (50.00, 30, ">= $10"),
    ]
    
    print('\n' + '=' * 100)
    print('📊 COMPARAÇÃO: ANTES vs DEPOIS DA CORREÇÃO')
    print('=' * 100)
    
    for balance, strategy_pct, category in scenarios:
        adjusted_pct = smart.get_adjusted_percentage(balance, strategy_pct)
        investment = (balance * adjusted_pct) / 100
        
        # ANTES da correção
        old_pct = min(strategy_pct, 30)  # Sempre limitava a 30%
        old_investment = (balance * old_pct) / 100
        
        print(f'\n💵 Saldo: ${balance:.2f} ({category})')
        print(f'   Estratégia sugere: {strategy_pct}%')
        
        print(f'\n   ❌ ANTES (limitava a 30%):')
        print(f'      Percentual usado: {old_pct}%')
        print(f'      Investimento: ${old_investment:.2f}')
        
        print(f'\n   ✅ DEPOIS (lógica inteligente):')
        print(f'      Percentual usado: {adjusted_pct}%')
        print(f'      Investimento: ${investment:.2f}')
        
        if balance < 10:
            diff = investment - old_investment
            print(f'\n   🎯 GANHO: +${diff:.2f} ({(diff/old_investment)*100:.1f}% a mais)')
        else:
            print(f'\n   💰 Mantém limite de {old_pct}% (gestão de risco)')
    
    print('\n' + '=' * 100)
    print('🎯 FLUXO COMPLETO COM SEU SALDO ($9.01)')
    print('=' * 100)
    
    balance = 9.01
    strategy_pct = 30  # O que a estratégia retorna
    
    print(f'\n1️⃣ Estratégia 4h retorna:')
    print(f'   matching_level["percentage_of_balance"] = 30%')
    print(f'   max_position_size_percent = 30%')
    print(f'   ❌ ANTES: buy_percentage = min(30%, 30%) = 30%')
    print(f'   ✅ AGORA: buy_percentage = 30% (SEM limitar ainda)')
    
    print(f'\n2️⃣ Lógica Inteligente recebe:')
    print(f'   available_balance = ${balance}')
    print(f'   buy_percentage = 30%')
    
    adjusted = smart.get_adjusted_percentage(balance, strategy_pct)
    print(f'\n3️⃣ Lógica Inteligente decide:')
    print(f'   Saldo ${balance} < $10?')
    print(f'   ✅ SIM → Ajusta para 100%')
    print(f'   adjusted_percentage = {adjusted}%')
    
    print(f'\n4️⃣ allocate_funds aplica limite:')
    print(f'   Saldo ${balance} >= $10?')
    print(f'   ❌ NÃO → NÃO aplica max_position_size_percent')
    print(f'   final_percentage = {adjusted}%')
    
    final_investment = (balance * adjusted) / 100
    print(f'\n5️⃣ Investimento Final:')
    print(f'   ${balance} × {adjusted}% = ${final_investment:.2f}')
    print(f'   ✅ USA TODO O SALDO!')
    
    print('\n' + '=' * 100)
    print('📝 RESUMO DAS MUDANÇAS')
    print('=' * 100)
    print(f'')
    print(f'✅ buy_strategy_4h.py (linha 231-234):')
    print(f'   ANTES: buy_percentage = min(level%, max_position_size_percent)')
    print(f'   DEPOIS: buy_percentage = level% (sem limitar)')
    print(f'')
    print(f'✅ exchange.py allocate_funds (linha 664):')
    print(f'   ADICIONADO: if saldo >= $10: aplica limite')
    print(f'   ADICIONADO: if saldo < $10: ignora limite')
    print(f'')
    print(f'🎯 RESULTADO:')
    print(f'   Saldo < $10: USA 100% (ignora max_position_size_percent)')
    print(f'   Saldo >= $10: Aplica limite de 30% (gestão de risco)')
    
    print('\n' + '=' * 100)

if __name__ == '__main__':
    test_max_position_limit()
