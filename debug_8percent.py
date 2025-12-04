#!/usr/bin/env python3
"""
Script para diagnosticar por que -8% não executou compra
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

from database.mongodb_connection import get_database
from datetime import datetime, timedelta
import json

def debug_8percent():
    """Analisa por que -8% não executou compra"""
    
    db = get_database()
    collection = db['ExecutionLogs']
    
    # Busca os últimos 10 logs
    recent_logs = list(collection.find().sort('timestamp', -1).limit(10))
    
    print('=' * 100)
    print('🔍 DIAGNÓSTICO: Por que -8% não executou compra?')
    print('=' * 100)
    
    print(f'\n📊 Total de logs encontrados: {len(recent_logs)}\n')
    
    for i, log in enumerate(recent_logs, 1):
        timestamp = log.get('timestamp', 'N/A')
        status = log.get('status', 'N/A')
        pair = log.get('pair', 'N/A')
        execution_type = log.get('execution_type', 'N/A')
        
        summary = log.get('summary', {})
        buy_executed = summary.get('buy_executed', False)
        total_invested = summary.get('total_invested', '0.00')
        
        buy_details = log.get('buy_details', {})
        buy_status = buy_details.get('status', 'N/A')
        buy_message = buy_details.get('message', 'Sem mensagem')
        
        market = log.get('market_info', {})
        multi_tf = market.get('multi_timeframe', {})
        var_4h = multi_tf.get('var_4h', 'N/A')
        current_price = market.get('current_price', 'N/A')
        
        # Destaca se teve -8% ou mais
        highlight = '🔴 ALERTA -8%!' if isinstance(var_4h, (int, float)) and var_4h <= -8 else ''
        
        print(f'\n{"=" * 100}')
        print(f'[{i}] {timestamp} | {execution_type.upper()} | Status: {status} {highlight}')
        print(f'{"=" * 100}')
        print(f'📈 Par: {pair}')
        print(f'📉 Variação 4h: {var_4h}%')
        print(f'💵 Preço: {current_price}')
        print(f'✅ Buy Executed: {buy_executed}')
        print(f'📝 Buy Status: {buy_status}')
        print(f'💰 Investido: ${total_invested}')
        
        if buy_message:
            print(f'💬 Mensagem: {buy_message}')
        
        # Se teve -8% mas não comprou, mostrar detalhes
        if isinstance(var_4h, (int, float)) and var_4h <= -8 and not buy_executed:
            print(f'\n🚨 PROBLEMA DETECTADO!')
            print(f'   Variação: {var_4h}% (trigger: -8%)')
            print(f'   Status compra: {buy_status}')
            print(f'   Mensagem: {buy_message}')
            print(f'   Buy Details completo:')
            for key, value in buy_details.items():
                print(f'      {key}: {value}')
    
    print('\n' + '=' * 100)
    print('🔧 VERIFICANDO CONFIGURAÇÕES ATUAIS')
    print('=' * 100)
    
    # Importa e mostra config
    from config.bot_config import MIN_VALUE_PER_SYMBOL, MIN_VALUE_PER_CREATE_ORDER
    from clients.nova_client import NovaClient
    
    print(f'\n💵 MIN_VALUE_PER_SYMBOL: ${MIN_VALUE_PER_SYMBOL}')
    print(f'💵 MIN_VALUE_PER_CREATE_ORDER: ${MIN_VALUE_PER_CREATE_ORDER}')
    
    # Pega saldo atual
    try:
        client = NovaClient()
        balance_info = client.get_balance()
        usdt_balance = next((b for b in balance_info if b.get('currency') == 'USDT'), None)
        
        if usdt_balance:
            available = float(usdt_balance.get('available', 0))
            print(f'\n💰 Saldo USDT Disponível: ${available:.2f}')
            
            # Simula quanto investiria com -8% (50%)
            investment_50 = available * 0.50
            print(f'\n🧮 SIMULAÇÃO COM -8% (50% do saldo):')
            print(f'   Saldo: ${available:.2f}')
            print(f'   Investimento (50%): ${investment_50:.2f}')
            print(f'   MIN_VALUE_PER_SYMBOL: ${MIN_VALUE_PER_SYMBOL}')
            
            if investment_50 < MIN_VALUE_PER_SYMBOL:
                print(f'   ❌ BLOQUEADO: ${investment_50:.2f} < ${MIN_VALUE_PER_SYMBOL} (mínimo)')
            else:
                print(f'   ✅ PASSA: ${investment_50:.2f} >= ${MIN_VALUE_PER_SYMBOL}')
    except Exception as e:
        print(f'\n❌ Erro ao verificar saldo: {e}')
    
    print('\n' + '=' * 100)
    print('📋 VERIFICANDO ESTRATÉGIA 4H')
    print('=' * 100)
    
    try:
        from clients.buy_strategy_4h import BuyStrategy4h
        strategy = BuyStrategy4h()
        
        print(f'\nNíveis da estratégia 4h:')
        for level in strategy.levels:
            print(f'   {level["variation_threshold"]}% = {level["percentage_of_balance"]}% | {level["name"]}')
    except Exception as e:
        print(f'❌ Erro ao carregar estratégia: {e}')

if __name__ == '__main__':
    debug_8percent()
