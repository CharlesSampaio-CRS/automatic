#!/usr/bin/env python3
"""
Atualiza configuração do MongoDB para -8% = 50%
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

from database.mongodb_connection import get_database

def update_strategy_8percent():
    """Atualiza MongoDB para incluir -8% = 50%"""
    
    db = get_database()
    collection = db['BotConfigs']
    
    print('=' * 100)
    print('🔧 ATUALIZAÇÃO: Adicionar regra -8% = 50%')
    print('=' * 100)
    
    # Busca config atual
    config = collection.find_one({'pair': 'REKTCOIN/USDT'})
    
    if not config:
        print('❌ Config não encontrada')
        return
    
    # Mostra config atual
    strategy_4h = config.get('strategy_4h', {})
    buy_strategy = strategy_4h.get('buy_strategy', {})
    current_levels = buy_strategy.get('levels', [])
    risk_mgmt = strategy_4h.get('risk_management', {})
    current_max = risk_mgmt.get('max_percentage_per_trade', 30)
    
    print(f'\n📊 NÍVEIS ATUAIS:')
    for level in current_levels:
        print(f'   {level.get("variation_threshold")}% = {level.get("percentage_of_balance")}% | {level.get("name")}')
    
    print(f'\n⚠️  max_percentage_per_trade atual: {current_max}%')
    
    # Novos níveis com -8%
    new_levels = [
        {
            "name": "Scalp Leve",
            "variation_threshold": -2.0,
            "percentage_of_balance": 5,
            "description": "Compra pequena em queda rápida de 2%"
        },
        {
            "name": "Scalp Moderado",
            "variation_threshold": -3.0,
            "percentage_of_balance": 7,
            "description": "Compra média em queda de 3%"
        },
        {
            "name": "Scalp Forte",
            "variation_threshold": -5.0,
            "percentage_of_balance": 10,
            "description": "Compra forte em queda brusca de 5%"
        },
        {
            "name": "Queda Acentuada",
            "variation_threshold": -8.0,
            "percentage_of_balance": 50,
            "description": "Compra agressiva em queda acentuada de 8% - investe 50% do saldo"
        }
    ]
    
    print(f'\n✨ NOVOS NÍVEIS PROPOSTOS:')
    for level in new_levels:
        print(f'   {level["variation_threshold"]}% = {level["percentage_of_balance"]}% | {level["name"]}')
    
    print(f'\n🔧 MUDANÇAS NECESSÁRIAS:')
    print(f'   1. Adicionar nível -8% = 50%')
    print(f'   2. Aumentar max_percentage_per_trade de {current_max}% para 50%')
    
    # Pergunta confirmação
    print(f'\n⚠️  ATENÇÃO: Isso aumenta o risco!')
    print(f'   - Com $9.01, -8% investirá $4.50 (50%)')
    print(f'   - Antes investia apenas $2.70 (30%)')
    print(f'   - Aumento de exposição: +67%')
    
    response = input(f'\n❓ Confirma atualização? (sim/não): ').strip().lower()
    
    if response != 'sim':
        print(f'\n❌ Atualização cancelada')
        return
    
    # Atualiza no MongoDB
    result = collection.update_one(
        {'pair': 'REKTCOIN/USDT'},
        {
            '$set': {
                'strategy_4h.buy_strategy.levels': new_levels,
                'strategy_4h.risk_management.max_percentage_per_trade': 50
            }
        }
    )
    
    if result.modified_count > 0:
        print(f'\n✅ Configuração atualizada com sucesso!')
        print(f'\n📊 NOVOS NÍVEIS:')
        for level in new_levels:
            print(f'   {level["variation_threshold"]}% = {level["percentage_of_balance"]}% | {level["name"]}')
        print(f'\n🔧 max_percentage_per_trade: 50%')
        print(f'\n💰 Com $9.01:')
        print(f'   -2%: Investe $0.45 (5%)')
        print(f'   -3%: Investe $0.63 (7%)')
        print(f'   -5%: Investe $0.90 (10%)')
        print(f'   -8%: Investe $4.50 (50%) ← NOVO!')
    else:
        print(f'\n⚠️  Nenhuma alteração feita (config já estava atualizada?)')
    
    print('\n' + '=' * 100)

if __name__ == '__main__':
    update_strategy_8percent()
