"""
Verifica os logs de execução no MongoDB
Mostra como os dados estão sendo salvos
"""

import sys
sys.path.append('/Users/charles.roberto/Documents/projects/crs-saturno/automatic')

from src.database.mongodb_connection import get_database
from datetime import datetime
import json

def check_logs():
    """Verifica os últimos logs de execução"""
    print("\n" + "="*80)
    print("📊 VERIFICANDO LOGS DE EXECUÇÃO NO MONGODB")
    print("="*80 + "\n")
    
    try:
        # Conecta ao MongoDB
        db = get_database()
        logs_db = db["ExecutionLogs"]
        
        # Busca os últimos 10 logs
        logs = list(logs_db.find().sort("timestamp", -1).limit(10))
        
        print(f"✅ Encontrados {len(logs)} logs recentes\n")
        
        for i, log in enumerate(logs, 1):
            print(f"\n{'='*80}")
            print(f"LOG #{i}")
            print(f"{'='*80}")
            
            # Informações básicas
            timestamp = log.get('timestamp', 'N/A')
            pair = log.get('pair', 'N/A')
            execution_type = log.get('execution_type', 'N/A')
            executed_by = log.get('executed_by', 'N/A')
            
            print(f"📅 Timestamp: {timestamp}")
            print(f"💱 Par: {pair}")
            print(f"🔧 Tipo: {execution_type}")
            print(f"👤 Executado por: {executed_by}")
            
            # Summary
            summary = log.get('summary', {})
            if summary:
                print(f"\n📊 RESUMO:")
                buy_total = float(summary.get('buy_total', 0)) if summary.get('buy_total') else 0
                sell_total = float(summary.get('sell_total', 0)) if summary.get('sell_total') else 0
                profit = float(summary.get('profit', 0)) if summary.get('profit') else 0
                net_result = summary.get('net_result', 0)
                
                # Trata net_result que pode ser string ou número
                if isinstance(net_result, str):
                    try:
                        net_result = float(net_result) if net_result else 0
                    except:
                        net_result = 0
                else:
                    net_result = float(net_result) if net_result else 0
                
                print(f"   Comprado: ${buy_total:.2f}")
                print(f"   Vendido: ${sell_total:.2f}")
                print(f"   Lucro: ${profit:.2f}")
                print(f"   Resultado Líquido: ${net_result:.2f}")
            
            # Buy details
            buy_details = log.get('buy_details', {})
            if buy_details and buy_details.get('executed'):
                print(f"\n💰 COMPRA EXECUTADA:")
                print(f"   Quantidade: {buy_details.get('amount', 0)}")
                print(f"   Preço: ${buy_details.get('price', 0):.10f}")
                print(f"   Total: ${buy_details.get('total', 0):.2f}")
                print(f"   Saldo disponível: ${buy_details.get('available_balance', 0):.2f}")
                print(f"   Razão: {buy_details.get('reason', 'N/A')}")
            
            # Sell details
            sell_details = log.get('sell_details', {})
            if sell_details and sell_details.get('executed'):
                print(f"\n💸 VENDA EXECUTADA:")
                print(f"   Quantidade: {sell_details.get('amount', 0)}")
                print(f"   Preço: ${sell_details.get('price', 0):.10f}")
                print(f"   Total: ${sell_details.get('total', 0):.2f}")
                print(f"   Lucro: ${sell_details.get('profit', 0):.2f}")
            
            # Market info
            market_info = log.get('market_info', {})
            if market_info:
                print(f"\n📈 INFO DO MERCADO:")
                print(f"   Preço atual: ${market_info.get('current_price', 0):.10f}")
                print(f"   Variação 1h: {market_info.get('change_1h', 0):+.2f}%")
                print(f"   Variação 24h: {market_info.get('change_24h', 0):+.2f}%")
                
                multi = market_info.get('multi_timeframe', {})
                if multi:
                    print(f"   Multi-timeframe:")
                    print(f"      5m: {multi.get('var_5m', 0):+.2f}%")
                    print(f"      15m: {multi.get('var_15m', 0):+.2f}%")
                    print(f"      30m: {multi.get('var_30m', 0):+.2f}%")
                    print(f"      4h: {multi.get('var_4h', 0):+.2f}%")
            
            # Schedule info (se agendado)
            schedule_info = log.get('schedule_info', {})
            if schedule_info:
                print(f"\n⏰ INFO DO AGENDAMENTO:")
                print(f"   Próxima execução: {schedule_info.get('next_execution', 'N/A')}")
                print(f"   Intervalo: {schedule_info.get('interval_minutes', 0)} minutos")
            
            # Estrutura completa (JSON)
            print(f"\n🔍 ESTRUTURA COMPLETA (JSON):")
            # Remove _id para facilitar leitura
            log_copy = dict(log)
            if '_id' in log_copy:
                log_copy['_id'] = str(log_copy['_id'])
            print(json.dumps(log_copy, indent=2, default=str))
        
        print("\n" + "="*80)
        print("✅ VERIFICAÇÃO COMPLETA")
        print("="*80 + "\n")
        
        # Análise de padrões
        print("\n" + "="*80)
        print("📊 ANÁLISE DOS DADOS")
        print("="*80 + "\n")
        
        # Conta tipos de execução
        manual_count = sum(1 for log in logs if log.get('execution_type') == 'manual')
        scheduled_count = sum(1 for log in logs if log.get('execution_type') == 'scheduled')
        
        print(f"Tipos de Execução:")
        print(f"   👤 Manual: {manual_count}")
        print(f"   ⏰ Agendado: {scheduled_count}")
        
        # Conta execuções com compra/venda
        buy_executed = sum(1 for log in logs if log.get('buy_details', {}).get('executed'))
        sell_executed = sum(1 for log in logs if log.get('sell_details', {}).get('executed'))
        no_action = len(logs) - buy_executed - sell_executed
        
        print(f"\nAções Executadas:")
        print(f"   💰 Compras: {buy_executed}")
        print(f"   💸 Vendas: {sell_executed}")
        print(f"   ⏸️  Sem ação: {no_action}")
        
        # Total de lucro/prejuízo
        total_profit = sum(log.get('summary', {}).get('net_result', 0) for log in logs)
        print(f"\nResultado Líquido Total: ${total_profit:.2f}")
        
    except Exception as e:
        print(f"❌ ERRO ao verificar logs: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    check_logs()
