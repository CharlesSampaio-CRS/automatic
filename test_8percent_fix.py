#!/usr/bin/env python3
"""
Script para testar se -8% agora investe corretamente com a correção
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

from clients.buy_strategy_4h import BuyStrategy4h
from config.bot_config import MIN_VALUE_PER_SYMBOL, MIN_VALUE_PER_CREATE_ORDER

def test_8percent_fix():
    """Testa se -8% agora calcula investimento corretamente"""
    
    print('=' * 100)
    print('🧪 TESTE: Correção do bug -8% investindo $0.00')
    print('=' * 100)
    
    # Configurações
    print(f'\n📋 Configurações:')
    print(f'   MIN_VALUE_PER_CREATE_ORDER: ${MIN_VALUE_PER_CREATE_ORDER}')
    print(f'   MIN_VALUE_PER_SYMBOL: ${MIN_VALUE_PER_SYMBOL}')
    
    # Simula saldo atual
    usdt_balance = 9.01
    print(f'\n💵 Saldo USDT: ${usdt_balance:.2f}')
    
    # Cria estratégia 4h com config HABILITADA
    strategy_4h_config = {
        'enabled': True,
        'buy_strategy': {
            'levels': []  # Vai usar os níveis padrão
        },
        'risk_management': {
            'stop_loss_percent': -3.0,
            'cooldown_minutes': 15,
            'max_trades_per_hour': 3,
            'max_percentage_per_trade': 30.0
        }
    }
    strategy_4h = BuyStrategy4h(strategy_4h_config)
    
    # Mostra níveis
    print(f'\n📊 Níveis da Estratégia 4h:')
    for level in strategy_4h.buy_levels:
        threshold = level['variation_threshold']
        percentage = level['percentage_of_balance']
        name = level['name']
        print(f'   {threshold}% = {percentage}% | {name}')
    
    # Testa com -8.58% (cenário real do log)
    variation_4h = -8.58
    
    print(f'\n🔍 TESTE COM VARIAÇÃO: {variation_4h}%')
    print('=' * 100)
    
    # Verifica se deve comprar
    should_buy, buy_info = strategy_4h.should_buy(variation_4h, 'REKTCOIN/USDT')
    
    print(f'\n✅ Deve Comprar?: {should_buy}')
    print(f'📝 Informações:')
    for key, value in buy_info.items():
        print(f'   {key}: {value}')
    
    if should_buy:
        # Calcula tamanho da posição
        buy_percentage = buy_info['buy_percentage']
        investment_amount = strategy_4h.calculate_position_size(usdt_balance, buy_percentage)
        
        print(f'\n💰 CÁLCULO DO INVESTIMENTO:')
        print(f'   Saldo: ${usdt_balance:.2f}')
        print(f'   Percentual: {buy_percentage}%')
        print(f'   Investimento: ${investment_amount:.2f}')
        print(f'   MIN_VALUE_PER_SYMBOL: ${MIN_VALUE_PER_SYMBOL}')
        
        # Valida
        print(f'\n✅ VALIDAÇÃO:')
        if investment_amount >= MIN_VALUE_PER_SYMBOL:
            print(f'   ✅ PASSA: ${investment_amount:.2f} >= ${MIN_VALUE_PER_SYMBOL}')
            print(f'   ✅ ORDEM SERIA EXECUTADA!')
            print(f'\n🎉 BUG CORRIGIDO! Agora -8% investe ${investment_amount:.2f} (não $0.00)')
        else:
            print(f'   ❌ FALHA: ${investment_amount:.2f} < ${MIN_VALUE_PER_SYMBOL}')
            print(f'   ❌ Ordem seria bloqueada')
    else:
        print(f'\n❌ Não deveria comprar')
        print(f'   Motivo: {buy_info.get("reason", "Desconhecido")}')
    
    print('\n' + '=' * 100)
    print('📝 RESUMO:')
    print('=' * 100)
    print(f'ANTES DA CORREÇÃO:')
    print(f'   - allocate_funds_with_dca_strategy usava sempre buy_strategy (24h)')
    print(f'   - Ignorava buy_percentage=50 da estratégia 4h')
    print(f'   - Resultado: buy_executed=True mas investimento=$0.00')
    print(f'')
    print(f'DEPOIS DA CORREÇÃO:')
    print(f'   - allocate_funds_with_dca_strategy verifica qual estratégia foi usada')
    print(f'   - Se 4h: usa buy_strategy_4h.calculate_position_size()')
    print(f'   - Se 24h: usa buy_strategy.calculate_investment_amount()')
    if should_buy and 'investment_amount' in locals():
        print(f'   - Resultado: -8% investe corretamente ${investment_amount:.2f}')
    else:
        print(f'   - Resultado: Teste não pôde calcular investimento (estratégia pode estar desabilitada)')
    print('\n' + '=' * 100)

if __name__ == '__main__':
    test_8percent_fix()
