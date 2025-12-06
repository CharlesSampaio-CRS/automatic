#!/usr/bin/env python3
"""
Script para atualizar índices do MongoDB para nova estrutura (array de exchanges)
"""

import os
import sys
from dotenv import load_dotenv
from pymongo import MongoClient, ASCENDING, DESCENDING

# Carrega variáveis de ambiente
load_dotenv()

def update_indexes():
    """Atualiza índices para nova estrutura com array"""
    
    # Conecta ao MongoDB
    MONGO_URI = os.getenv('MONGODB_URI')
    MONGO_DATABASE = os.getenv('MONGODB_DATABASE', 'MultExchange')
    
    client = MongoClient(MONGO_URI)
    db = client[MONGO_DATABASE]
    
    print("=" * 60)
    print("🔧 ATUALIZANDO ÍNDICES PARA NOVA ESTRUTURA")
    print("=" * 60)
    
    # Remove índices antigos da estrutura anterior
    print("\n📊 Removendo índices antigos...")
    
    old_indexes = ['idx_user_active', 'idx_exchange', 'idx_user_exchange_unique']
    
    for idx_name in old_indexes:
        try:
            db.user_exchanges.drop_index(idx_name)
            print(f"  ✅ Índice removido: {idx_name}")
        except Exception as e:
            if "index not found" in str(e).lower():
                print(f"  ⏭️  Índice não encontrado: {idx_name}")
            else:
                print(f"  ⚠️  Erro ao remover {idx_name}: {e}")
    
    # Cria novos índices para estrutura com array
    print("\n📊 Criando novos índices otimizados...")
    
    # Índice 1: Busca rápida por user_id (único por usuário)
    try:
        db.user_exchanges.create_index(
            [("user_id", ASCENDING)],
            name="idx_user_id",
            unique=True,
            background=True
        )
        print("  ✅ Índice criado: user_id (único)")
    except Exception as e:
        print(f"  ⚠️  Erro ao criar índice user_id: {e}")
    
    # Índice 2: Busca em array de exchanges por exchange_id
    try:
        db.user_exchanges.create_index(
            [("exchanges.exchange_id", ASCENDING)],
            name="idx_exchanges_exchange_id",
            background=True
        )
        print("  ✅ Índice criado: exchanges.exchange_id")
    except Exception as e:
        print(f"  ⚠️  Erro ao criar índice exchanges.exchange_id: {e}")
    
    # Índice 3: Busca em array por is_active
    try:
        db.user_exchanges.create_index(
            [("exchanges.is_active", ASCENDING)],
            name="idx_exchanges_is_active",
            background=True
        )
        print("  ✅ Índice criado: exchanges.is_active")
    except Exception as e:
        print(f"  ⚠️  Erro ao criar índice exchanges.is_active: {e}")
    
    # Índice 4: Busca por updated_at para ordenação
    try:
        db.user_exchanges.create_index(
            [("updated_at", DESCENDING)],
            name="idx_updated_at",
            background=True
        )
        print("  ✅ Índice criado: updated_at")
    except Exception as e:
        print(f"  ⚠️  Erro ao criar índice updated_at: {e}")
    
    # Estatísticas
    print("\n" + "=" * 60)
    print("📈 Estatísticas da Collection user_exchanges:")
    print("=" * 60)
    
    try:
        stats = db.command("collstats", "user_exchanges")
        indexes = list(db.user_exchanges.list_indexes())
        
        print(f"\n   Documentos: {stats.get('count', 0):,}")
        print(f"   Tamanho: {stats.get('size', 0):,} bytes")
        print(f"   Tamanho médio: {stats.get('avgObjSize', 0):.2f} bytes")
        print(f"   Índices ativos: {len(indexes)}")
        
        print(f"\n   Lista de índices:")
        for idx in indexes:
            keys = ", ".join([f"{k}: {v}" for k, v in idx.get('key', {}).items()])
            unique = " (UNIQUE)" if idx.get('unique', False) else ""
            print(f"      • {idx.get('name')}: {keys}{unique}")
        
        # Calcula total de exchanges vinculadas
        pipeline = [
            {'$project': {'exchange_count': {'$size': '$exchanges'}}},
            {'$group': {'_id': None, 'total': {'$sum': '$exchange_count'}}}
        ]
        result = list(db.user_exchanges.aggregate(pipeline))
        if result:
            print(f"\n   Total de exchanges vinculadas: {result[0]['total']}")
    
    except Exception as e:
        print(f"   ⚠️  Erro ao obter estatísticas: {e}")
    
    print("\n✅ Atualização de índices concluída!")
    
    client.close()

if __name__ == "__main__":
    try:
        update_indexes()
    except Exception as e:
        print(f"\n❌ Erro ao atualizar índices: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
