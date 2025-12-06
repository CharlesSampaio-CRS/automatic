#!/usr/bin/env python3
"""
Script para limpar dados antigos do balance_history
e testar nova estrutura simplificada
"""

import os
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

def clean_balance_history():
    """Remove registros antigos do balance_history"""
    
    MONGO_URI = os.getenv('MONGODB_URI')
    MONGO_DATABASE = os.getenv('MONGODB_DATABASE', 'MultExchange')
    
    client = MongoClient(MONGO_URI)
    db = client[MONGO_DATABASE]
    
    print("=" * 60)
    print("🧹 LIMPEZA DO BALANCE_HISTORY")
    print("=" * 60)
    
    # Conta documentos atuais
    count_before = db.balance_history.count_documents({})
    print(f"\n📊 Documentos atuais: {count_before}")
    
    if count_before > 0:
        print("\n⚠️  Deletando todos os registros antigos...")
        result = db.balance_history.delete_many({})
        print(f"✅ {result.deleted_count} documentos deletados")
        print("💡 Novos snapshots serão salvos na estrutura simplificada")
    else:
        print("\n✅ Collection já está vazia")
    
    # Mostra exemplo da nova estrutura
    print("\n" + "=" * 60)
    print("📄 NOVA ESTRUTURA SIMPLIFICADA")
    print("=" * 60)
    print("""
{
  "_id": ObjectId("..."),
  "user_id": "charles_test_user",
  "timestamp": ISODate("2025-12-06T..."),
  "total_usd": 135.17,
  "total_brl": 779.25,
  "exchanges": [
    {
      "exchange_id": "693481148b0a41e8b6acb079",
      "exchange_name": "NovaDAX",
      "total_usd": 85.50,
      "total_brl": 493.05,
      "success": true
    },
    {
      "exchange_id": "693481148b0a41e8b6acb07b",
      "exchange_name": "MEXC",
      "total_usd": 49.67,
      "total_brl": 286.20,
      "success": true
    }
  ]
}
    """)
    
    print("\n✅ Benefícios da nova estrutura:")
    print("   • Redução de ~70% no tamanho dos documentos")
    print("   • Foco em dados essenciais (valores totais)")
    print("   • Melhor performance em queries")
    print("   • Menor uso de espaço no MongoDB")
    
    client.close()

if __name__ == "__main__":
    try:
        clean_balance_history()
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()
