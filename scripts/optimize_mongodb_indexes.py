#!/usr/bin/env python3
"""
Script para criar índices otimizados no MongoDB
Melhora performance e reduz uso de recursos
"""

import os
import sys
from dotenv import load_dotenv
from pymongo import MongoClient, ASCENDING, DESCENDING

# Carrega variáveis de ambiente
load_dotenv()

def index_exists(collection, index_name):
    """Verifica se um índice já existe"""
    indexes = list(collection.list_indexes())
    return any(idx.get('name') == index_name for idx in indexes)

def index_exists_on_field(collection, field_name):
    """Verifica se já existe algum índice neste campo"""
    indexes = list(collection.list_indexes())
    for idx in indexes:
        keys = idx.get('key', {})
        if field_name in keys:
            return True, idx.get('name')
    return False, None

def create_indexes():
    """Cria índices otimizados para melhor performance"""
    
    # Conecta ao MongoDB
    MONGO_URI = os.getenv('MONGODB_URI')
    MONGO_DATABASE = os.getenv('MONGODB_DATABASE', 'MultExchange')
    
    client = MongoClient(MONGO_URI)
    db = client[MONGO_DATABASE]
    
    print("🔧 Criando índices otimizados...\n")
    
    # ============================================
    # COLLECTION: user_exchanges
    # ============================================
    print("📊 Otimizando collection 'user_exchanges'...")
    
    # Índice 1: Busca rápida por usuário e status ativo
    # Usado em: GET /api/v1/exchanges/linked, GET /api/v1/balances
    if not index_exists(db.user_exchanges, "idx_user_active"):
        db.user_exchanges.create_index(
            [
                ("user_id", ASCENDING),
                ("is_active", ASCENDING)
            ],
            name="idx_user_active",
            background=True
        )
        print("  ✅ Índice criado: user_id + is_active")
    else:
        print("  ⏭️  Índice já existe: user_id + is_active")
    
    # Índice 2: Busca por exchange_id
    # Usado internamente para queries relacionadas a exchanges específicas
    if not index_exists(db.user_exchanges, "idx_exchange"):
        db.user_exchanges.create_index(
            [("exchange_id", ASCENDING)],
            name="idx_exchange",
            background=True
        )
        print("  ✅ Índice criado: exchange_id")
    else:
        print("  ⏭️  Índice já existe: exchange_id")
    
    # Índice 3: Unique constraint - impede duplicatas
    # Garante que um usuário não vincule a mesma exchange duas vezes
    if not index_exists(db.user_exchanges, "idx_user_exchange_unique"):
        try:
            db.user_exchanges.create_index(
                [
                    ("user_id", ASCENDING),
                    ("exchange_id", ASCENDING),
                    ("is_active", ASCENDING)
                ],
                name="idx_user_exchange_unique",
                unique=True,
                partialFilterExpression={"is_active": True},
                background=True
            )
            print("  ✅ Índice único criado: user_id + exchange_id (previne duplicatas)")
        except Exception as e:
            print(f"  ⚠️  Não foi possível criar índice único: {e}")
    else:
        print("  ⏭️  Índice já existe: user_id + exchange_id")
    
    # ============================================
    # COLLECTION: exchanges
    # ============================================
    print("\n📊 Otimizando collection 'exchanges'...")
    
    # Índice para exchanges ativas
    exists, existing_name = index_exists_on_field(db.exchanges, "is_active")
    if not exists:
        db.exchanges.create_index(
            [("is_active", ASCENDING)],
            name="idx_active_exchanges",
            background=True
        )
        print("  ✅ Índice criado: is_active")
    else:
        print(f"  ⏭️  Índice já existe no campo is_active: {existing_name}")
    
    # Índice para busca por CCXT ID
    exists, existing_name = index_exists_on_field(db.exchanges, "ccxt_id")
    if not exists:
        try:
            db.exchanges.create_index(
                [("ccxt_id", ASCENDING)],
                name="idx_ccxt_id",
                unique=True,
                background=True
            )
            print("  ✅ Índice único criado: ccxt_id")
        except Exception as e:
            print(f"  ⚠️  Índice ccxt_id: {e}")
    else:
        print(f"  ⏭️  Índice já existe no campo ccxt_id: {existing_name}")
    
    # ============================================
    # COLLECTION: balance_history
    # ============================================
    print("\n📊 Otimizando collection 'balance_history'...")
    
    # Índice 1: Busca por usuário e data (para histórico)
    if not index_exists(db.balance_history, "idx_user_timestamp"):
        # Verifica se já existe índice similar
        indexes = list(db.balance_history.list_indexes())
        has_similar = False
        for idx in indexes:
            keys = idx.get('key', {})
            if 'user_id' in keys and 'timestamp' in keys:
                print(f"  ⏭️  Índice similar já existe: {idx.get('name')}")
                has_similar = True
                break
        
        if not has_similar:
            db.balance_history.create_index(
                [
                    ("user_id", ASCENDING),
                    ("timestamp", DESCENDING)
                ],
                name="idx_user_timestamp",
                background=True
            )
            print("  ✅ Índice criado: user_id + timestamp (desc)")
    else:
        print("  ⏭️  Índice já existe: user_id + timestamp")
    
    # Índice 2: TTL - Auto-exclusão de dados antigos (opcional)
    # Descomente se quiser excluir histórico após X dias
    # if not index_exists(db.balance_history, "idx_ttl_history"):
    #     db.balance_history.create_index(
    #         [("timestamp", ASCENDING)],
    #         name="idx_ttl_history",
    #         expireAfterSeconds=90 * 24 * 60 * 60,  # 90 dias
    #         background=True
    #     )
    #     print("  ✅ Índice TTL criado: auto-exclusão após 90 dias")
    # else:
    #     print("  ⏭️  Índice TTL já existe")
    
    # ============================================
    # Estatísticas
    # ============================================
    print("\n" + "="*50)
    print("📈 Estatísticas das Collections:")
    print("="*50)
    
    for collection_name in ['user_exchanges', 'exchanges', 'balance_history']:
        if collection_name in db.list_collection_names():
            stats = db.command("collstats", collection_name)
            indexes = db[collection_name].list_indexes()
            
            print(f"\n🗂️  {collection_name}:")
            print(f"   Documentos: {stats.get('count', 0):,}")
            print(f"   Tamanho: {stats.get('size', 0):,} bytes")
            print(f"   Tamanho médio: {stats.get('avgObjSize', 0):.2f} bytes")
            print(f"   Índices: {len(list(indexes))}")
    
    print("\n✅ Otimização concluída com sucesso!")
    print("\n💡 Dicas adicionais:")
    print("   • Os índices são criados em background (não bloqueiam)")
    print("   • Use explain() nas queries para verificar uso dos índices")
    print("   • Monitore o uso de memória dos índices no MongoDB Atlas")
    
    client.close()

if __name__ == "__main__":
    try:
        create_indexes()
    except Exception as e:
        print(f"\n❌ Erro ao criar índices: {e}")
        sys.exit(1)
