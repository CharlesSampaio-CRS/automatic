#!/usr/bin/env python3
"""
Script de Migração: Múltiplos Documentos → Documento Único com Array
Converte a estrutura atual para ter um único documento por usuário
com array de exchanges vinculadas
"""

import os
import sys
from dotenv import load_dotenv
from pymongo import MongoClient
from datetime import datetime

# Carrega variáveis de ambiente
load_dotenv()

def migrate_data():
    """Migra dados da estrutura antiga para nova estrutura"""
    
    # Conecta ao MongoDB
    MONGO_URI = os.getenv('MONGODB_URI')
    MONGO_DATABASE = os.getenv('MONGODB_DATABASE', 'MultExchange')
    
    client = MongoClient(MONGO_URI)
    db = client[MONGO_DATABASE]
    
    print("=" * 60)
    print("🔄 MIGRAÇÃO: Múltiplos Documentos → Array de Exchanges")
    print("=" * 60)
    
    # Backup da collection antiga
    backup_collection = f"user_exchanges_backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
    print(f"\n📦 Criando backup: {backup_collection}")
    
    # Cria backup
    old_docs = list(db.user_exchanges.find())
    if old_docs:
        db[backup_collection].insert_many(old_docs)
        print(f"✅ Backup criado com {len(old_docs)} documentos")
    else:
        print("ℹ️  Nenhum documento para fazer backup")
    
    # Agrupa documentos por user_id
    print(f"\n📊 Analisando dados atuais...")
    
    pipeline = [
        {
            '$group': {
                '_id': '$user_id',
                'exchanges': {
                    '$push': {
                        'exchange_id': '$exchange_id',
                        'api_key_encrypted': '$api_key_encrypted',
                        'api_secret_encrypted': '$api_secret_encrypted',
                        'passphrase_encrypted': '$passphrase_encrypted',
                        'is_active': '$is_active',
                        'created_at': '$created_at',
                        'updated_at': '$updated_at'
                    }
                }
            }
        }
    ]
    
    grouped_data = list(db.user_exchanges.aggregate(pipeline))
    
    if not grouped_data:
        print("ℹ️  Nenhum dado para migrar")
        client.close()
        return
    
    print(f"✅ Encontrados {len(grouped_data)} usuários com exchanges vinculadas")
    
    # Cria nova collection temporária
    temp_collection = "user_exchanges_new"
    
    print(f"\n🔨 Criando nova estrutura em '{temp_collection}'...")
    
    # Remove collection temporária se existir
    if temp_collection in db.list_collection_names():
        db[temp_collection].drop()
    
    # Cria documentos na nova estrutura
    new_documents = []
    for user_data in grouped_data:
        new_doc = {
            'user_id': user_data['_id'],
            'exchanges': user_data['exchanges'],
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        new_documents.append(new_doc)
    
    if new_documents:
        db[temp_collection].insert_many(new_documents)
        print(f"✅ {len(new_documents)} documentos criados na nova estrutura")
        
        # Mostra exemplo da nova estrutura
        example = db[temp_collection].find_one()
        print(f"\n📄 Exemplo da nova estrutura:")
        print(f"   user_id: {example['user_id']}")
        print(f"   total de exchanges: {len(example['exchanges'])}")
        for i, ex in enumerate(example['exchanges'][:2]):  # Mostra até 2
            print(f"   exchange[{i}]: {ex['exchange_id']}")
    
    # Pergunta se deseja aplicar a migração
    print("\n" + "=" * 60)
    print("⚠️  ATENÇÃO: A próxima etapa irá:")
    print("   1. Renomear 'user_exchanges' para 'user_exchanges_old'")
    print("   2. Renomear 'user_exchanges_new' para 'user_exchanges'")
    print("   3. O backup estará em:", backup_collection)
    print("=" * 60)
    
    response = input("\n🤔 Deseja aplicar a migração? (sim/não): ").strip().lower()
    
    if response == 'sim':
        print("\n🔄 Aplicando migração...")
        
        # Renomeia collection antiga
        db.user_exchanges.rename('user_exchanges_old', dropTarget=True)
        print("✅ Collection antiga renomeada para 'user_exchanges_old'")
        
        # Renomeia nova collection
        db[temp_collection].rename('user_exchanges')
        print("✅ Nova collection ativada como 'user_exchanges'")
        
        print("\n✅ MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
        print("\n📊 Estatísticas finais:")
        count = db.user_exchanges.count_documents({})
        print(f"   Usuários: {count}")
        
        # Conta total de exchanges
        pipeline = [
            {'$project': {'exchange_count': {'$size': '$exchanges'}}},
            {'$group': {'_id': None, 'total': {'$sum': '$exchange_count'}}}
        ]
        result = list(db.user_exchanges.aggregate(pipeline))
        if result:
            print(f"   Total de exchanges vinculadas: {result[0]['total']}")
        
        print(f"\n💡 Para reverter a migração:")
        print(f"   1. db.user_exchanges.drop()")
        print(f"   2. db.user_exchanges_old.rename('user_exchanges')")
        
    else:
        print("\n❌ Migração cancelada")
        print(f"   A collection temporária '{temp_collection}' foi mantida para análise")
    
    client.close()

if __name__ == "__main__":
    try:
        migrate_data()
    except Exception as e:
        print(f"\n❌ Erro durante migração: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
