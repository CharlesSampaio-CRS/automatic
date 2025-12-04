"""
Script para criar um resumo visual dos logs no formato do frontend
"""

import sys
sys.path.append('/Users/charles.roberto/Documents/projects/crs-saturno/automatic')

from src.database.mongodb_connection import get_database
from datetime import datetime

def format_timestamp(timestamp_str):
    """Formata timestamp para exibição"""
    try:
        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        return dt.strftime("%d/%m/%Y, %H:%M")
    except:
        return timestamp_str

def get_execution_icon(execution_type):
    """Retorna ícone baseado no tipo de execução"""
    if execution_type == 'manual':
        return '👤 Manual'
    elif execution_type == 'scheduled':
        return '⏰ Agendado'
    else:
        return '❓ Desconhecido'

def get_net_result_value(summary):
    """Extrai valor do net_result"""
    net_result = summary.get('net_result', '0.00')
    try:
        if isinstance(net_result, str):
            return float(net_result) if net_result else 0.0
        return float(net_result)
    except:
        return 0.0

def show_frontend_view():
    """Mostra como o frontend está vendo os dados"""
    print("\n" + "="*80)
    print("📱 VISUALIZAÇÃO DO FRONTEND - ATIVIDADE RECENTE")
    print("="*80 + "\n")
    
    try:
        db = get_database()
        logs_db = db["ExecutionLogs"]
        
        # Busca últimos 20 logs
        logs = list(logs_db.find().sort("timestamp", -1).limit(20))
        
        print(f"{'Par':<20} {'Data/Hora':<20} {'Tipo':<20} {'Resultado':<15}")
        print("-" * 80)
        
        for log in logs:
            pair = log.get('pair', 'N/A')
            timestamp = format_timestamp(log.get('timestamp', ''))
            execution_type = get_execution_icon(log.get('execution_type', 'unknown'))
            summary = log.get('summary', {})
            net_result = get_net_result_value(summary)
            
            result_str = f"${net_result:+.2f}" if net_result != 0 else "0.00"
            
            print(f"{pair:<20} {timestamp:<20} {execution_type:<20} {result_str:<15}")
        
        print("\n" + "="*80)
        print("📊 ANÁLISE DETALHADA")
        print("="*80 + "\n")
        
        # Análise por tipo
        manual_count = sum(1 for log in logs if log.get('execution_type') == 'manual')
        scheduled_count = sum(1 for log in logs if log.get('execution_type') == 'scheduled')
        
        # Análise por ação
        buys = sum(1 for log in logs if log.get('summary', {}).get('buy_executed', False))
        sells = sum(1 for log in logs if log.get('summary', {}).get('sell_executed', False))
        no_action = len(logs) - buys - sells
        
        # Resultado financeiro
        total_invested = sum(
            float(log.get('summary', {}).get('total_invested', 0) or 0) 
            for log in logs
        )
        total_profit = sum(
            float(log.get('summary', {}).get('total_profit', 0) or 0) 
            for log in logs
        )
        net_results = [get_net_result_value(log.get('summary', {})) for log in logs]
        total_net = sum(net_results)
        
        print(f"📈 Estatísticas:")
        print(f"   Total de execuções: {len(logs)}")
        print(f"   👤 Manuais: {manual_count}")
        print(f"   ⏰ Agendadas: {scheduled_count}")
        print()
        print(f"💰 Ações:")
        print(f"   Compras executadas: {buys}")
        print(f"   Vendas executadas: {sells}")
        print(f"   Sem ação: {no_action}")
        print()
        print(f"💵 Financeiro:")
        print(f"   Total investido: ${total_invested:.2f}")
        print(f"   Total lucro: ${total_profit:.2f}")
        print(f"   Resultado líquido: ${total_net:+.2f}")
        
        # Mostra último log com detalhes
        if logs:
            print("\n" + "="*80)
            print("🔍 ÚLTIMO LOG DETALHADO")
            print("="*80 + "\n")
            
            last_log = logs[0]
            
            print(f"Par: {last_log.get('pair')}")
            print(f"Timestamp: {format_timestamp(last_log.get('timestamp'))}")
            print(f"Tipo: {get_execution_icon(last_log.get('execution_type'))}")
            
            summary = last_log.get('summary', {})
            print(f"\nResumo:")
            print(f"   Compra executada: {'✅ Sim' if summary.get('buy_executed') else '❌ Não'}")
            print(f"   Venda executada: {'✅ Sim' if summary.get('sell_executed') else '❌ Não'}")
            print(f"   Total investido: ${summary.get('total_invested', '0.00')}")
            print(f"   Total lucro: ${summary.get('total_profit', '0.00')}")
            print(f"   Resultado líquido: ${get_net_result_value(summary):+.2f}")
            
            # Buy details
            buy_details = last_log.get('buy_details', {})
            if buy_details:
                print(f"\nDetalhes da Compra:")
                print(f"   Status: {buy_details.get('status', 'N/A')}")
                print(f"   Mensagem: {buy_details.get('message', 'N/A')}")
                print(f"   Símbolos analisados: {buy_details.get('symbols_analyzed', 0)}")
                print(f"   Ordens executadas: {buy_details.get('orders_executed', 0)}")
            
            # Sell details
            sell_details = last_log.get('sell_details', {})
            if sell_details:
                print(f"\nDetalhes da Venda:")
                print(f"   Status: {sell_details.get('status', 'N/A')}")
                print(f"   Mensagem: {sell_details.get('message', 'N/A')}")
                print(f"   Holdings verificados: {sell_details.get('holdings_checked', 0)}")
                print(f"   Vendas executadas: {sell_details.get('sells_executed', 0)}")
            
            # Market info
            market_info = last_log.get('market_info', {})
            if market_info:
                print(f"\nInfo do Mercado:")
                print(f"   Preço atual: ${market_info.get('current_price', 0):.10f}")
                
                stats_24h = market_info.get('24h_stats', {})
                if stats_24h:
                    print(f"   Variação 24h: {stats_24h.get('change_percent', 0):+.2f}%")
                    print(f"   Volume 24h: ${stats_24h.get('volume_usdt', 0):,.2f}")
                
                analysis = market_info.get('market_analysis', {})
                if analysis:
                    print(f"   Tendência: {analysis.get('trend', 'N/A')}")
                    print(f"   Momentum: {analysis.get('momentum', 'N/A')}")
                    print(f"   Liquidez: {analysis.get('liquidity', 'N/A')}")
        
        print("\n" + "="*80)
        
    except Exception as e:
        print(f"❌ ERRO: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    show_frontend_view()
