#!/usr/bin/env python3
"""
Verifica saldo e simula investimento com -8%
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

from clients.nova_client import NovaClient
from config.bot_config import MIN_VALUE_PER_SYMBOL, MIN_VALUE_PER_CREATE_ORDER

def check_balance():
    """Verifica saldo e simula investimento"""
    
    print('=' * 100)
    print('💰 VERIFICAÇÃO DE SALDO E SIMULAÇÃO')
    print('=' * 100)
    
    # Config atual
    print(f'\n📋 Configurações:')
    print(f'   MIN_VALUE_PER_CREATE_ORDER: ${MIN_VALUE_PER_CREATE_ORDER}')
    print(f'   MIN_VALUE_PER_SYMBOL: ${MIN_VALUE_PER_SYMBOL}')
    
    # Saldo atual
    try:
        client = NovaClient()
        balance_info = client.get_balance()
        usdt_balance = next((b for b in balance_info if b.get('currency') == 'USDT'), None)
        
        if usdt_balance:
            available = float(usdt_balance.get('available', 0))
            frozen = float(usdt_balance.get('frozen', 0))
            total = available + frozen
            
            print(f'\n💵 Saldo USDT:')
            print(f'   Disponível: ${available:.2f}')
            print(f'   Congelado: ${frozen:.2f}')
            print(f'   Total: ${total:.2f}')
            
            # Check 1: Passa o mínimo geral?
            print(f'\n✅ Check 1: Saldo >= MIN_VALUE_PER_CREATE_ORDER?')
            print(f'   ${available:.2f} >= ${MIN_VALUE_PER_CREATE_ORDER}?')
            if available >= MIN_VALUE_PER_CREATE_ORDER:
                print(f'   ✅ SIM - Pode operar')
            else:
                print(f'   ❌ NÃO - Bloqueado!')
                print(f'   Faltam: ${MIN_VALUE_PER_CREATE_ORDER - available:.2f}')
            
            # Simula investimentos com -8% (50%)
            print(f'\n🧮 SIMULAÇÃO: Regra -8% = 50% do saldo')
            investment_50 = available * 0.50
            
            print(f'   Saldo disponível: ${available:.2f}')
            print(f'   Investimento (50%): ${investment_50:.2f}')
            print(f'   MIN_VALUE_PER_SYMBOL: ${MIN_VALUE_PER_SYMBOL}')
            
            print(f'\n✅ Check 2: Investimento >= MIN_VALUE_PER_SYMBOL?')
            print(f'   ${investment_50:.2f} >= ${MIN_VALUE_PER_SYMBOL}?')
            if investment_50 >= MIN_VALUE_PER_SYMBOL:
                print(f'   ✅ SIM - Ordem seria executada')
            else:
                print(f'   ❌ NÃO - Ordem seria rejeitada')
                print(f'   Faltam: ${MIN_VALUE_PER_SYMBOL - investment_50:.2f}')
            
            # Calcula saldo mínimo necessário
            min_balance_needed = MIN_VALUE_PER_SYMBOL / 0.50  # Para investir 50%
            
            print(f'\n💡 SOLUÇÃO:')
            print(f'   Para executar -8% (50%), você precisa de:')
            print(f'   Saldo mínimo: ${min_balance_needed:.2f}')
            print(f'   Cálculo: MIN_VALUE_PER_SYMBOL / 0.50 = ${MIN_VALUE_PER_SYMBOL} / 0.50 = ${min_balance_needed:.2f}')
            
            if available < min_balance_needed:
                print(f'\n   ❌ Seu saldo atual: ${available:.2f}')
                print(f'   ❌ Saldo necessário: ${min_balance_needed:.2f}')
                print(f'   ❌ Você precisa depositar: ${min_balance_needed - available:.2f}')
            else:
                print(f'\n   ✅ Seu saldo é suficiente!')
                
        else:
            print('❌ Saldo USDT não encontrado')
            
    except Exception as e:
        print(f'❌ Erro ao buscar saldo: {e}')
        import traceback
        traceback.print_exc()
    
    print('\n' + '=' * 100)

if __name__ == '__main__':
    check_balance()
