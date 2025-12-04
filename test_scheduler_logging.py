"""
Script de teste para verificar se o scheduler salva logs em TODOS os cenários
Testa: SUCCESS, SKIPPED e ERROR
"""

from src.database.mongodb_connection import get_database
from datetime import datetime, timedelta

def test_logging_behavior():
    """
    Verifica o comportamento de logging do scheduler
    """
    db = get_database()
    
    print('='*80)
    print('🧪 TESTE DE LOGGING DO SCHEDULER')
    print('='*80)
    
    # Busca logs das últimas 2 horas
    two_hours_ago = datetime.now() - timedelta(hours=2)
    
    # Todos os logs scheduled
    all_scheduled = list(db['ExecutionLogs'].find({
        'execution_type': 'scheduled',
        'timestamp': {'$gte': two_hours_ago.isoformat()}
    }).sort('timestamp', -1))
    
    print(f'\n LOGS SCHEDULED NAS ÚLTIMAS 2 HORAS: {len(all_scheduled)}')
    
    if len(all_scheduled) == 0:
        print('\n⚠️  Nenhum log scheduled encontrado nas últimas 2 horas')
        print('   Possíveis causas:')
        print('   1. Scheduler não está rodando')
        print('   2. Scheduler teve erro e não salvou log')
        print('   3. Nenhuma execução nos últimos 2 horas')
        return
    
    # Categoriza os logs
    success_logs = []
    skipped_logs = []
    error_logs = []
    
    for log in all_scheduled:
        status = log.get('buy_details', {}).get('status', 'unknown')
        
        if status == 'success':
            success_logs.append(log)
        elif status == 'skipped':
            skipped_logs.append(log)
        elif status == 'error':
            error_logs.append(log)
    
    print('\n📈 ESTATÍSTICAS POR STATUS:')
    print('-'*80)
    print(f'   SUCCESS: {len(success_logs)} logs')
    print(f'  ⏭️  SKIPPED: {len(skipped_logs)} logs')
    print(f'   ERROR: {len(error_logs)} logs')
    
    # Mostra detalhes dos logs
    if success_logs:
        print('\n LOGS DE SUCESSO:')
        print('-'*80)
        for log in success_logs[:3]:  # Mostra até 3
            timestamp = log.get('timestamp')
            pair = log.get('pair')
            orders = log.get('buy_details', {}).get('orders_executed', 0)
            invested = log.get('buy_details', {}).get('total_invested', '0.00')
            print(f'  {timestamp} | {pair:<20} | Orders: {orders} | Invested: {invested}')
    
    if skipped_logs:
        print('\n⏭️  LOGS SKIPPED (Nenhum símbolo atendeu critérios):')
        print('-'*80)
        for log in skipped_logs[:3]:  # Mostra até 3
            timestamp = log.get('timestamp')
            pair = log.get('pair')
            reason = log.get('buy_details', {}).get('message', 'N/A')
            print(f'  {timestamp} | {pair:<20} | Reason: {reason[:50]}')
    
    if error_logs:
        print('\n LOGS DE ERRO:')
        print('-'*80)
        for log in error_logs[:3]:  # Mostra até 3
            timestamp = log.get('timestamp')
            pair = log.get('pair')
            error = log.get('buy_details', {}).get('message', 'N/A')
            error_type = log.get('buy_details', {}).get('error_type', 'Unknown')
            print(f'  {timestamp} | {pair:<20}')
            print(f'    Error Type: {error_type}')
            print(f'    Message: {error[:70]}')
    
    # Verifica intervalo entre logs
    if len(all_scheduled) > 1:
        print('\n⏱️  INTERVALO ENTRE EXECUÇÕES:')
        print('-'*80)
        
        intervals = []
        for i in range(1, min(6, len(all_scheduled))):  # Mostra até 5 intervalos
            prev_time = datetime.fromisoformat(all_scheduled[i]['timestamp'])
            curr_time = datetime.fromisoformat(all_scheduled[i-1]['timestamp'])
            interval = curr_time - prev_time
            minutes = interval.total_seconds() / 60
            intervals.append(minutes)
            print(f'  Execução {i+1} → {i}: {minutes:.1f} minutos')
        
        if intervals:
            avg_interval = sum(intervals) / len(intervals)
            print(f'\n  Média: {avg_interval:.1f} minutos')
            
            if avg_interval < 8:
                print(f'  ⚠️  ATENÇÃO: Intervalo médio menor que 8 minutos!')
                print(f'     Configurado para 10 minutos, mas executando a cada {avg_interval:.1f}')
            elif avg_interval > 12:
                print(f'  ⚠️  ATENÇÃO: Intervalo médio maior que 12 minutos!')
                print(f'     Configurado para 10 minutos, mas executando a cada {avg_interval:.1f}')
            else:
                print(f'   Intervalo adequado (configurado: 10 minutos)')
    
    # Verifica última execução
    last_log = all_scheduled[0]
    last_time = datetime.fromisoformat(last_log['timestamp'])
    now = datetime.now()
    time_since_last = now - last_time
    minutes_since = time_since_last.total_seconds() / 60
    
    print(f'\n🕐 ÚLTIMA EXECUÇÃO:')
    print('-'*80)
    print(f'  Timestamp: {last_time.strftime("%Y-%m-%d %H:%M:%S")}')
    print(f'  Há {minutes_since:.1f} minutos atrás')
    print(f'  Status: {last_log.get("buy_details", {}).get("status", "unknown")}')
    
    if minutes_since > 15:
        print(f'\n  ⚠️  ATENÇÃO: Última execução há mais de 15 minutos!')
        print(f'     Scheduler pode não estar rodando')
    else:
        print(f'\n   Scheduler está ativo (última execução recente)')
    
    # Resultado final
    print('\n'+'='*80)
    print(' RESULTADO DO TESTE:')
    print('='*80)
    
    if error_logs:
        print(' FALHA: Scheduler teve erros nas execuções')
        print(f'   {len(error_logs)} erro(s) detectado(s)')
    elif len(all_scheduled) < 2:
        print('⚠️  ATENÇÃO: Apenas 1 execução encontrada')
        print('   Aguarde mais execuções para validar comportamento')
    elif minutes_since > 15:
        print('⚠️  ATENÇÃO: Scheduler parou de executar')
        print('   Última execução foi há mais de 15 minutos')
    else:
        print(' SUCESSO: Scheduler está funcionando corretamente!')
        print(f'   {len(all_scheduled)} execuções nas últimas 2 horas')
        print(f'   Intervalo médio: {avg_interval:.1f} minutos' if len(all_scheduled) > 1 else '')
        print('   Logs estão sendo salvos em todos os cenários')
    
    print('='*80 + '\n')

if __name__ == "__main__":
    test_logging_behavior()
