"""
Script to populate the exchanges collection in MultExchange database
Run this once to initialize the supported exchanges
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from pymongo import MongoClient
from datetime import datetime

load_dotenv()

# MongoDB connection
MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
client = MongoClient(MONGODB_URI)

# Use MultExchange database
db = client['MultExchange']
exchanges_collection = db['exchanges']

# Exchanges data
exchanges_data = [
    {
        "nome": "Binance",
        "url": "https://binance.com",
        "pais_de_origem": "Desconhecido / Internacional",
        "icon": "https://img.icons8.com/color/96/binance.png",
        "ccxt_id": "binance",  # ID used by CCXT library
        "requires_passphrase": False,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    },
    {
        "nome": "Coinbase",
        "url": "https://coinbase.com",
        "pais_de_origem": "Estados Unidos",
        "icon": "https://img.icons8.com/color/96/coinbase.png",
        "ccxt_id": "coinbase",
        "requires_passphrase": True,  # Coinbase requires passphrase
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    },
    {
        "nome": "Kraken",
        "url": "https://kraken.com",
        "pais_de_origem": "Estados Unidos",
        "icon": "https://img.icons8.com/color/96/kraken.png",
        "ccxt_id": "kraken",
        "requires_passphrase": False,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    },
    {
        "nome": "KuCoin",
        "url": "https://kucoin.com",
        "pais_de_origem": "Seychelles",
        "icon": "https://img.icons8.com/color/96/kucoin.png",
        "ccxt_id": "kucoin",
        "requires_passphrase": True,  # KuCoin requires passphrase
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    },
    {
        "nome": "OKX",
        "url": "https://okx.com",
        "pais_de_origem": "Estados Unidos",
        "icon": "https://img.icons8.com/ios-filled/100/okx.png",
        "ccxt_id": "okx",
        "requires_passphrase": True,  # OKX requires passphrase
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    },
    {
        "nome": "Bybit",
        "url": "https://bybit.com",
        "pais_de_origem": "Emirados Árabes Unidos",
        "icon": "https://img.icons8.com/color/96/bybit.png",
        "ccxt_id": "bybit",
        "requires_passphrase": False,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    },
    {
        "nome": "NovaDAX",
        "url": "https://novadax.com.br",
        "pais_de_origem": "Brasil",
        "icon": "https://play-lh.googleusercontent.com/SpGD7EOKiJZx4GL0010wjQ8T_LbLINpFzdM84ydbUWCD0jUIh0MegGm-4hJtXHEF9lQ=w240-h480-rw",
        "ccxt_id": "novadax",
        "requires_passphrase": False,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    },
    {
        "nome": "Gate.io",
        "url": "https://gate.io",
        "pais_de_origem": "China / Internacional",
        "icon": "https://img.icons8.com/color/96/gate-io.png",
        "ccxt_id": "gateio",
        "requires_passphrase": False,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    },
    {
        "nome": "MEXC",
        "url": "https://mexc.com",
        "pais_de_origem": "Seychelles",
        "icon": "https://img.icons8.com/color/96/mexc.png",
        "ccxt_id": "mexc",
        "requires_passphrase": False,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
]

def seed_exchanges():
    """Populate exchanges collection"""
    try:
        # Clear existing data (optional - remove if you want to keep existing data)
        print("🗑️  Clearing existing exchanges...")
        exchanges_collection.delete_many({})
        
        # Insert exchanges
        print("📝 Inserting exchanges...")
        result = exchanges_collection.insert_many(exchanges_data)
        
        print(f"✅ Successfully inserted {len(result.inserted_ids)} exchanges!")
        
        # Create indexes
        print("🔍 Creating indexes...")
        exchanges_collection.create_index("nome", unique=True)
        exchanges_collection.create_index("ccxt_id", unique=True)
        exchanges_collection.create_index("is_active")
        
        print("✅ Indexes created!")
        
        # Display inserted exchanges
        print("\n📊 Inserted exchanges:")
        for exchange in exchanges_collection.find():
            print(f"  - {exchange['nome']} ({exchange['ccxt_id']}) - Passphrase: {exchange['requires_passphrase']}")
        
        print("\n🎉 Seed completed successfully!")
        
    except Exception as e:
        print(f"❌ Error seeding exchanges: {str(e)}")
        raise
    finally:
        client.close()

if __name__ == "__main__":
    print("🚀 Starting exchanges seed...\n")
    seed_exchanges()
