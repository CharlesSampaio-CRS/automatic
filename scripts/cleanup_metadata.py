#!/usr/bin/env python3
"""
Script para remover campo 'metadata' redundante da configuração.

O campo metadata.* era usado para tracking, mas isso já é feito pela collection ExecutionJobs.
Este script remove esse campo para simplificar a estrutura.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from pymongo import MongoClient

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
    return client[db_name]['BotConfigs']

def cleanup_metadata(collection):
    """Remove campo metadata da configuração"""
    
    config = collection.find_one({'pair': 'REKTCOIN/USDT'})
    
    if not config:
        print("❌ Configuração não encontrada para REKTCOIN/USDT")
        return False
    
    # Verifica se tem metadata
    if 'metadata' not in config:
        print("✅ Campo 'metadata' já não existe na configuração")
        return True
    
    print("=" * 80)
    print("CAMPO METADATA ATUAL")
    print("=" * 80)
    metadata = config.get('metadata', {})
    print(f"last_execution: {metadata.get('last_execution')}")
    print(f"status: {metadata.get('status')}")
    print(f"total_orders: {metadata.get('total_orders')}")
    print(f"total_invested: {metadata.get('total_invested')}")
    print(f"last_updated: {metadata.get('last_updated')}")
    print()
    print("⚠️  Este campo é redundante, pois ExecutionJobs já mantém esses dados.")
    print()
    
    # Remove o campo
    result = collection.update_one(
        {'pair': 'REKTCOIN/USDT'},
        {'$unset': {'metadata': ''}}
    )
    
    if result.modified_count > 0:
        print("=" * 80)
        print("✅ CAMPO 'metadata' REMOVIDO COM SUCESSO!")
        print("=" * 80)
        print("Os dados históricos permanecem seguros na collection ExecutionJobs.")
        print()
        return True
    else:
        print("⚠️  Nenhuma modificação foi necessária")
        return False

def main():
    """Executa limpeza"""
    collection = get_mongo_client()
    
    print("\n🧹 LIMPEZA DE CAMPO REDUNDANTE\n")
    
    cleanup_metadata(collection)

if __name__ == "__main__":
    main()
