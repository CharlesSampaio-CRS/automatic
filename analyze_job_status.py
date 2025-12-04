"""
Script para validar status dos jobs no MongoDB
Mostra estatísticas e últimas execuções
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.database.mongodb_connection import get_database
from datetime import datetime, timedelta
from collections import Counter

def analyze_execution_logs():
    """
    Analisa os logs de execução no MongoDB
    """
    print("\n" + "="*80)
    print("📊 ANÁLISE DOS JOBS NO MONGODB - ExecutionLogs")
    print("="*80 + "\n")
    
    # Conecta ao MongoDB
    db = get_database()
    logs_db = db['ExecutionLogs']
    
    # Conta total de logs
    total_logs = logs_db.count_documents({})
    print(f"📝 Total de execuções registradas: {total_logs}")
    
    if total_logs == 0:
        print("\n⚠️  Nenhuma execução encontrada no banco de dados!")
        return
    
    print("\n" + "-"*80)
    print("🔍 ÚLTIMAS 10 EXECUÇÕES")
    print("-"*80 + "\n")
    
    # Busca últimas 10 execuções
    recent_logs = list(logs_db.find().sort("timestamp", -1).limit(10))
    
    for i, log in enumerate(recent_logs, 1):
        timestamp = log.get('timestamp', 'N/A')
        exec_type = log.get('execution_type', 'N/A')
        executed_by = log.get('executed_by', 'N/A')
        pair = log.get('pair', 'N/A')
        
        # Summary
        summary = log.get('summary', {})
        buy_count = summary.get('buy_count', 0)
        sell_count = summary.get('sell_count', 0)
        net_result = float(summary.get('net_result', 0)) if summary.get('net_result') else 0
        
        # Status icon
        status_icon = "📈" if net_result > 0 else "📉" if net_result < 0 else "⏸️"
        exec_icon = "🤖" if executed_by == "scheduler" else "👤"
        
        print(f"{i}. {exec_icon} {timestamp}")
        print(f"   Par: {pair}")
        print(f"   Tipo: {exec_type} (executado por: {executed_by})")
        print(f"   {status_icon} Compras: {buy_count} | Vendas: {sell_count} | Resultado: ${net_result:.2f}")
        print()
    
    print("-"*80)
    print("📊 ESTATÍSTICAS GERAIS")
    print("-"*80 + "\n")
    
    # Estatísticas por tipo de execução
    all_logs = list(logs_db.find())
    
    exec_types = [log.get('execution_type', 'unknown') for log in all_logs]
    exec_by = [log.get('executed_by', 'unknown') for log in all_logs]
    pairs = [log.get('pair', 'unknown') for log in all_logs]
    
    exec_types_count = Counter(exec_types)
    exec_by_count = Counter(exec_by)
    pairs_count = Counter(pairs)
    
    print("🎯 Por Tipo de Execução:")
    for exec_type, count in exec_types_count.most_common():
        percentage = (count / total_logs) * 100
        print(f"   {exec_type}: {count} ({percentage:.1f}%)")
    
    print("\n👥 Por Executor:")
    for executor, count in exec_by_count.most_common():
        percentage = (count / total_logs) * 100
        icon = "🤖" if executor == "scheduler" else "👤" if executor == "user" else "❓"
        print(f"   {icon} {executor}: {count} ({percentage:.1f}%)")
    
    print("\n💱 Por Par:")
    for pair, count in pairs_count.most_common():
        percentage = (count / total_logs) * 100
        print(f"   {pair}: {count} ({percentage:.1f}%)")
    
    # Análise de resultados financeiros
    print("\n" + "-"*80)
    print("💰 RESULTADOS FINANCEIROS")
    print("-"*80 + "\n")
    
    total_buys = 0
    total_sells = 0
    total_invested = 0.0
    total_received = 0.0
    total_profit = 0.0
    
    profitable_trades = 0
    loss_trades = 0
    neutral_trades = 0
    
    for log in all_logs:
        summary = log.get('summary', {})
        
        total_buys += summary.get('buy_count', 0)
        total_sells += summary.get('sell_count', 0)
        total_invested += float(summary.get('total_invested', 0)) if summary.get('total_invested') else 0
        total_received += float(summary.get('total_received', 0)) if summary.get('total_received') else 0
        
        net_result = float(summary.get('net_result', 0)) if summary.get('net_result') else 0
        total_profit += net_result
        
        if net_result > 0:
            profitable_trades += 1
        elif net_result < 0:
            loss_trades += 1
        else:
            neutral_trades += 1
    
    print(f"📈 Total de Compras: {total_buys}")
    print(f"📉 Total de Vendas: {total_sells}")
    print(f"💵 Total Investido: ${total_invested:.2f} USDT")
    print(f"💰 Total Recebido: ${total_received:.2f} USDT")
    print(f"{'📈' if total_profit >= 0 else '📉'} Resultado Líquido: ${total_profit:+.2f} USDT")
    
    print(f"\n🎯 Performance:")
    print(f"   ✅ Trades Lucrativos: {profitable_trades} ({(profitable_trades/total_logs*100):.1f}%)")
    print(f"   ❌ Trades com Perda: {loss_trades} ({(loss_trades/total_logs*100):.1f}%)")
    print(f"   ⏸️  Trades Neutros: {neutral_trades} ({(neutral_trades/total_logs*100):.1f}%)")
    
    # Win rate
    if (profitable_trades + loss_trades) > 0:
        win_rate = (profitable_trades / (profitable_trades + loss_trades)) * 100
        print(f"\n🏆 Win Rate: {win_rate:.1f}%")
    
    # Análise temporal
    print("\n" + "-"*80)
    print("📅 ANÁLISE TEMPORAL")
    print("-"*80 + "\n")
    
    # Últimas 24 horas
    now = datetime.now()
    last_24h = now - timedelta(hours=24)
    
    logs_24h = [log for log in all_logs if isinstance(log.get('timestamp'), datetime) and log.get('timestamp') > last_24h]
    
    if logs_24h:
        print(f"⏰ Últimas 24 horas:")
        print(f"   Execuções: {len(logs_24h)}")
        
        buys_24h = sum(log.get('summary', {}).get('buy_count', 0) for log in logs_24h)
        sells_24h = sum(log.get('summary', {}).get('sell_count', 0) for log in logs_24h)
        profit_24h = sum(float(log.get('summary', {}).get('net_result', 0) or 0) for log in logs_24h)
        
        print(f"   Compras: {buys_24h}")
        print(f"   Vendas: {sells_24h}")
        print(f"   Resultado: ${profit_24h:+.2f} USDT")
    else:
        print("⚠️  Nenhuma execução nas últimas 24 horas")
    
    # Última execução
    print("\n" + "-"*80)
    print("⏱️  ÚLTIMA EXECUÇÃO")
    print("-"*80 + "\n")
    
    if recent_logs:
        last_log = recent_logs[0]
        timestamp = last_log.get('timestamp', 'N/A')
        exec_type = last_log.get('execution_type', 'N/A')
        executed_by = last_log.get('executed_by', 'N/A')
        pair = last_log.get('pair', 'N/A')
        
        print(f"📅 Timestamp: {timestamp}")
        print(f"💱 Par: {pair}")
        print(f"🎯 Tipo: {exec_type}")
        print(f"👥 Executado por: {executed_by}")
        
        # Detalhes da execução
        summary = last_log.get('summary', {})
        print(f"\n📊 Resumo:")
        print(f"   Compras: {summary.get('buy_count', 0)}")
        print(f"   Vendas: {summary.get('sell_count', 0)}")
        
        total_invested = float(summary.get('total_invested', 0)) if summary.get('total_invested') else 0
        total_received = float(summary.get('total_received', 0)) if summary.get('total_received') else 0
        net_result = float(summary.get('net_result', 0)) if summary.get('net_result') else 0
        
        print(f"   Investido: ${total_invested:.2f}")
        print(f"   Recebido: ${total_received:.2f}")
        print(f"   Resultado: ${net_result:+.2f}")
        
        # Market info
        market_info = last_log.get('market_info', {})
        if market_info:
            print(f"\n💹 Mercado:")
            print(f"   Preço: ${market_info.get('current_price', 0)}")
            print(f"   Variação 1h: {market_info.get('variation_1h', 0):+.2f}%")
            print(f"   Variação 24h: {market_info.get('variation_24h', 0):+.2f}%")
            print(f"   Volume 24h: ${market_info.get('volume_24h', 0):,.2f}")
    
    print("\n" + "="*80)
    print("✅ ANÁLISE COMPLETA")
    print("="*80 + "\n")


def check_collection_structure():
    """
    Verifica a estrutura de uma execução no MongoDB
    """
    print("\n" + "="*80)
    print("🔍 ESTRUTURA DE UM DOCUMENTO ExecutionLogs")
    print("="*80 + "\n")
    
    db = get_database()
    logs_db = db['ExecutionLogs']
    sample = logs_db.find_one()
    
    if not sample:
        print("⚠️  Nenhum documento encontrado para análise")
        return
    
    # Remove _id para legibilidade
    if '_id' in sample:
        del sample['_id']
    
    import json
    print(json.dumps(sample, indent=2, default=str))
    
    print("\n" + "="*80)
    print("📝 Campos Disponíveis:")
    print("="*80)
    
    def print_keys(obj, prefix=""):
        if isinstance(obj, dict):
            for key, value in obj.items():
                if isinstance(value, dict):
                    print(f"{prefix}{key}:")
                    print_keys(value, prefix + "  ")
                elif isinstance(value, list) and value and isinstance(value[0], dict):
                    print(f"{prefix}{key}: [array de objetos]")
                    print(f"{prefix}  Exemplo do primeiro item:")
                    print_keys(value[0], prefix + "    ")
                else:
                    print(f"{prefix}{key}: {type(value).__name__}")
    
    print_keys(sample)
    print()


if __name__ == "__main__":
    try:
        # Análise completa dos logs
        analyze_execution_logs()
        
        # Mostra estrutura de um documento
        print("\n" + "="*80)
        input("Pressione ENTER para ver a estrutura detalhada de um documento...")
        check_collection_structure()
        
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
