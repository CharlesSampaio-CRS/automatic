"""
Script para verificar logs do scheduler no MongoDB
"""

from src.database.mongodb_connection import get_database
from datetime import datetime
import json

db = get_database()

print(' ANÁLISE DE LOGS DO SCHEDULER')
print('='*80)

# Busca o último log 'scheduled'
scheduled_log = db['ExecutionLogs'].find_one({'execution_type': 'scheduled'}, sort=[('_id', -1)])

if scheduled_log:
    print('\n ÚLTIMO LOG SCHEDULED ENCONTRADO:')
    print('-'*80)
    print(f'Timestamp: {scheduled_log.get("timestamp")}')
    print(f'Pair: {scheduled_log.get("pair")}')
    print(f'Executed by: {scheduled_log.get("executed_by")}')
    
    if 'buy_details' in scheduled_log:
        buy = scheduled_log['buy_details']
        print(f'\nCompra:')
        print(f'  Status: {buy.get("status")}')
        print(f'  Orders: {buy.get("orders_executed")}')
        print(f'  Invested: {buy.get("total_invested")}')
    
    print(f'\n📄 Documento completo:')
    print(json.dumps(scheduled_log, indent=2, default=str))
else:
    print('\n Nenhum log scheduled encontrado')

print('\n\n ESTATÍSTICAS POR TIPO:')
print('='*80)

total = db['ExecutionLogs'].count_documents({})
manual = db['ExecutionLogs'].count_documents({'execution_type': 'manual'})
scheduled = db['ExecutionLogs'].count_documents({'execution_type': 'scheduled'})

print(f'Total de logs: {total}')
print(f'Logs MANUAL: {manual} ({manual/total*100:.1f}%)')
print(f'Logs SCHEDULED: {scheduled} ({scheduled/total*100:.1f}%)')

print('\n\n ÚLTIMOS 10 LOGS (TODOS):')
print('='*80)

logs = db['ExecutionLogs'].find().sort('_id', -1).limit(10)

for i, log in enumerate(logs, 1):
    exec_type = log.get('execution_type', 'N/A')
    timestamp = log.get('timestamp', 'N/A')
    pair = log.get('pair', 'N/A')
    
    print(f'{i}. {timestamp} | Type: {exec_type:<10} | Pair: {pair}')

print('\n\n PROBLEMA DETECTADO:')
print('='*80)

if manual > scheduled * 10:
    print('⚠️  ATENÇÃO: Quantidade de logs MANUAL muito maior que SCHEDULED!')
    print(f'   Ratio: {manual} manual vs {scheduled} scheduled')
    print('   Isso indica que o scheduler pode não estar salvando corretamente')
    print('\n💡 POSSÍVEIS CAUSAS:')
    print('   1. Scheduler não está passando execution_type="scheduled"')
    print('   2. Scheduler está chamando endpoint manual em vez de criar ordem diretamente')
    print('   3. Há duas instâncias do scheduler rodando')
elif scheduled > 0:
    print(' Scheduler está salvando logs corretamente')
else:
    print(' Nenhum log scheduled encontrado - Scheduler pode não estar funcionando')
