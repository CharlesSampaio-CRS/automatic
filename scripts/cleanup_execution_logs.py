#!/usr/bin/env python3
"""
Script para simplificar logs da collection ExecutionJobs.

Remove campos verbosos e mantém apenas informações essenciais.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from pymongo import MongoClient
from datetime import datetime

# Adiciona o diretório raiz ao path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

# Carrega variáveis de ambiente
load_dotenv()

def get_mongo_client():
    """Conecta ao MongoDB usando credenciais do .env"""
    mongo_uri = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
    client = MongoClient(mongo_uri)
    db_name = os.getenv('MONGODB_DATABASE', 'CryptoTradingDB')
    return client[db_name]

def simplify_execution_log(log):
    """Simplifica um log de execução"""
    
    # Extrai dados do market_info se existir
    market_info = log.get('market_info', {})
    price = market_info.get('current_price', 0)
    change_24h = market_info.get('24h_stats', {}).get('change_percent', 0)
    change_4h = market_info.get('multi_timeframe', {}).get('var_4h', 0)
    volume_24h = market_info.get('24h_stats', {}).get('volume_usdt', 0)
    
    # Extrai summary
    summary = log.get('summary', {})
    
    # Cria estrutura simplificada
    simplified = {
        "_id": log['_id'],
        "timestamp": log.get('timestamp'),
        "execution_type": log.get('execution_type', 'scheduled'),
        "pair": log.get('pair'),
        "status": log.get('status'),
        
        "summary": {
            "buy_executed": summary.get('buy_executed', False),
            "sell_executed": summary.get('sell_executed', False),
            "total_invested": float(summary.get('total_invested', 0)),
            "total_profit": float(summary.get('total_profit', 0)),
            "net_result": float(summary.get('net_result', 0))
        }
    }
    
    # Adiciona market_snapshot apenas se tiver dados
    if price > 0 or change_24h != 0:
        simplified["market_snapshot"] = {
            "price": price,
            "change_24h": change_24h,
            "change_4h": change_4h,
            "volume_24h": volume_24h
        }
    
    return simplified

def cleanup_logs(db, dry_run=True):
    """Limpa logs antigos"""
    
    collection = db['ExecutionLogs']  # Nome correto da collection
    
    # Conta documentos
    total_docs = collection.count_documents({})
    
    print("=" * 80)
    print("ANÁLISE DE LOGS EXECUTIONLOGS")
    print("=" * 80)
    print(f"Total de documentos: {total_docs}")
    print()
    
    # Pega um exemplo
    sample = collection.find_one({})
    
    if not sample:
        print("❌ Nenhum log encontrado")
        return
    
    print("📋 ESTRUTURA ATUAL (exemplo):")
    print(f"   Campos: {len(sample)} campos")
    print(f"   Tamanho estimado: ~{len(str(sample))} bytes")
    print()
    
    # Mostra campos que serão removidos
    removed_fields = []
    if 'market_info' in sample:
        market_info = sample['market_info']
        removed_fields.append(f"   - market_info.spread ({len(str(market_info.get('spread', {})))} bytes)")
        removed_fields.append(f"   - market_info.Tranding_fees ({len(str(market_info.get('Tranding_fees', {})))} bytes)")
        removed_fields.append(f"   - market_info.market_analysis ({len(str(market_info.get('market_analysis', {})))} bytes)")
        removed_fields.append(f"   - market_info.multi_timeframe (detalhes)")
    
    if 'buy_details' in sample:
        removed_fields.append(f"   - buy_details ({len(str(sample['buy_details']))} bytes)")
    
    if 'sell_details' in sample:
        removed_fields.append(f"   - sell_details ({len(str(sample['sell_details']))} bytes)")
    
    if removed_fields:
        print("🗑️  CAMPOS QUE SERÃO REMOVIDOS:")
        for field in removed_fields:
            print(field)
        print()
    
    # Simplifica um log de exemplo
    simplified_sample = simplify_execution_log(sample)
    
    print("📋 ESTRUTURA SIMPLIFICADA:")
    print(f"   Campos: {len(simplified_sample)} campos")
    print(f"   Tamanho estimado: ~{len(str(simplified_sample))} bytes")
    print(f"   Redução: ~{((len(str(sample)) - len(str(simplified_sample))) / len(str(sample)) * 100):.1f}%")
    print()
    
    if dry_run:
        print("=" * 80)
        print("⚠️  MODO DRY-RUN ATIVO")
        print("=" * 80)
        print("Nenhuma modificação será feita no banco de dados.")
        print("Execute com --apply para aplicar as mudanças.")
        print()
        return
    
    # Aplica mudanças
    print("=" * 80)
    print("🔄 APLICANDO SIMPLIFICAÇÃO")
    print("=" * 80)
    
    updated_count = 0
    
    for log in collection.find({}):
        simplified = simplify_execution_log(log)
        
        collection.replace_one(
            {'_id': log['_id']},
            simplified
        )
        
        updated_count += 1
        
        if updated_count % 10 == 0:
            print(f"Processados: {updated_count}/{total_docs}")
    
    print()
    print("=" * 80)
    print("✅ SIMPLIFICAÇÃO CONCLUÍDA")
    print("=" * 80)
    print(f"Documentos atualizados: {updated_count}")
    print(f"Estrutura simplificada e mais legível!")
    print()

def main():
    """Executa limpeza"""
    
    import argparse
    
    parser = argparse.ArgumentParser(description='Simplifica logs do ExecutionJobs')
    parser.add_argument('--apply', action='store_true', help='Aplica as mudanças (sem isso, apenas mostra preview)')
    
    args = parser.parse_args()
    
    db = get_mongo_client()
    
    print("\n🧹 SIMPLIFICAÇÃO DE LOGS EXECUTIONLOGS\n")
    
    cleanup_logs(db, dry_run=not args.apply)

if __name__ == "__main__":
    main()
