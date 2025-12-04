#!/usr/bin/env python3
"""
Demonstração da Estratégia Inteligente de Investimento
Mostra como o bot se comporta com diferentes saldos
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

from clients.smart_investment_strategy import SmartInvestmentStrategy
from config.bot_config import MIN_VALUE_PER_SYMBOL, SMALL_BALANCE_THRESHOLD

def demo_smart_strategy():
    """Demonstra a estratégia inteligente com diferentes cenários"""
    
    print('=' * 100)
    print('🎯 ESTRATÉGIA INTELIGENTE DE INVESTIMENTO')
    print('=' * 100)
    
    # Cria estratégia
    smart = SmartInvestmentStrategy()
    
    print(f'\n📋 CONFIGURAÇÃO:')
    print(f'   Limite para "saldo pequeno": ${SMALL_BALANCE_THRESHOLD}')
    print(f'   Valor mínimo por trade: ${MIN_VALUE_PER_SYMBOL}')
    print(f'   Lógica: Se saldo < ${SMALL_BALANCE_THRESHOLD} → Usa 100%')
    print(f'   Lógica: Se saldo >= ${SMALL_BALANCE_THRESHOLD} → Usa % da estratégia')
    
    # Cenários de teste
    scenarios = [
        # (saldo, percentual_estrategia, estrategia_nome)
        (2.50, 50, "4h -8%"),      # Saldo muito baixo
        (5.00, 50, "4h -8%"),      # Saldo baixo
        (9.01, 50, "4h -8%"),      # Saldo atual do usuário
        (9.99, 50, "4h -8%"),      # Quase $10
        (10.00, 50, "4h -8%"),     # Exatamente $10
        (15.00, 50, "4h -8%"),     # Acima de $10
        (50.00, 50, "4h -8%"),     # Saldo bom
        (100.00, 50, "4h -8%"),    # Saldo alto
        (9.01, 10, "4h -5%"),      # Saldo baixo, percentual menor
        (50.00, 10, "4h -5%"),     # Saldo bom, percentual menor
    ]
    
    print('\n' + '=' * 100)
    print('📊 SIMULAÇÕES:')
    print('=' * 100)
    
    for i, (balance, percentage, strategy) in enumerate(scenarios, 1):
        investment, info = smart.calculate_smart_investment(balance, percentage, strategy)
        
        is_small = info['is_small_balance']
        used_smart = info['used_smart_logic']
        original_pct = info['original_percentage']
        adjusted_pct = info['adjusted_percentage']
        
        emoji = "🎯" if used_smart else "💰"
        status = "SALDO BAIXO" if is_small else "SALDO NORMAL"
        
        print(f'\n{emoji} Cenário {i}: ${balance:.2f} | {strategy}')
        print(f'   Status: {status}')
        print(f'   Estratégia sugere: {original_pct}%')
        
        if used_smart:
            print(f'   ⚡ Smart ajusta para: {adjusted_pct}% (100% para maximizar lucro!)')
        else:
            print(f'   ✅ Mantém: {adjusted_pct}%')
        
        print(f'   💵 Investimento: ${investment:.2f}')
        
        if investment >= MIN_VALUE_PER_SYMBOL:
            print(f'   ✅ PASSA: ${investment:.2f} >= ${MIN_VALUE_PER_SYMBOL} (ordem executada)')
        else:
            print(f'   ❌ BLOQUEADO: ${investment:.2f} < ${MIN_VALUE_PER_SYMBOL}')
    
    print('\n' + '=' * 100)
    print('📈 COMPARAÇÃO: ANTES vs DEPOIS')
    print('=' * 100)
    
    # Exemplo prático com saldo atual do usuário
    user_balance = 9.01
    strategy_pct = 50
    
    # ANTES (sem smart strategy)
    old_investment = (user_balance * strategy_pct) / 100
    
    # DEPOIS (com smart strategy)
    new_investment, info = smart.calculate_smart_investment(user_balance, strategy_pct, "4h -8%")
    
    print(f'\nSaldo: ${user_balance}')
    print(f'Estratégia diz: "Investe {strategy_pct}%"')
    print(f'')
    print(f'❌ ANTES (sem smart):')
    print(f'   Investimento: ${old_investment:.2f}')
    print(f'   Sobra no saldo: ${user_balance - old_investment:.2f}')
    print(f'   Lucro potencial com 10%: ${old_investment * 0.10:.2f}')
    print(f'')
    print(f'✅ DEPOIS (com smart):')
    print(f'   Investimento: ${new_investment:.2f}')
    print(f'   Sobra no saldo: ${user_balance - new_investment:.2f}')
    print(f'   Lucro potencial com 10%: ${new_investment * 0.10:.2f}')
    print(f'')
    print(f'📊 DIFERENÇA:')
    difference = new_investment - old_investment
    profit_difference = (new_investment * 0.10) - (old_investment * 0.10)
    print(f'   +${difference:.2f} investido ({(difference/old_investment)*100:.1f}% a mais)')
    print(f'   +${profit_difference:.2f} de lucro potencial ({(profit_difference/(old_investment*0.10))*100:.1f}% a mais)')
    
    print('\n' + '=' * 100)
    print('🎯 CONCLUSÃO:')
    print('=' * 100)
    print(f'Com saldo < ${SMALL_BALANCE_THRESHOLD}:')
    print(f'   ✅ Bot usa 100% do saldo para MAXIMIZAR LUCRO')
    print(f'   ✅ Ignora percentuais da estratégia')
    print(f'   ✅ Aproveita melhor oportunidades')
    print(f'')
    print(f'Com saldo >= ${SMALL_BALANCE_THRESHOLD}:')
    print(f'   ✅ Bot usa percentuais da estratégia')
    print(f'   ✅ Mantém gestão de risco')
    print(f'   ✅ Diversifica investimentos')
    print('\n' + '=' * 100)

if __name__ == '__main__':
    demo_smart_strategy()
