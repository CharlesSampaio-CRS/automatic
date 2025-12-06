#!/usr/bin/env python3
"""
Script para popular a collection SupportedExchanges
Deve ser executado UMA VEZ para criar as exchanges disponíveis
"""

import sys
import os
from pathlib import Path
from pymongo import MongoClient
from dotenv import load_dotenv
from datetime import datetime

# Adiciona o diretório raiz ao path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

# Carrega variáveis do .env
load_dotenv()


def get_database():
    """Conecta ao MongoDB"""
    MONGO_URI = os.getenv('MONGODB_URI')
    DATABASE_NAME = os.getenv('MONGODB_DATABASE', 'AutomaticInvest')
    
    if not MONGO_URI:
        print("❌ Erro: MONGODB_URI não encontrada no arquivo .env")
        sys.exit(1)
    
    client = MongoClient(MONGO_URI)
    return client[DATABASE_NAME]


def seed_supported_exchanges():
    """Popula collection SupportedExchanges"""
    
    print("\n" + "="*70)
    print("🌱 POPULANDO EXCHANGES SUPORTADAS")
    print("="*70)
    
    db = get_database()
    collection = db['SupportedExchanges']
    
    # Define as 9 exchanges suportadas
    exchanges = [
        {
            "exchange_id": "binance",
            "name": "Binance",
            "icon": "🟡",
            "website": "https://www.binance.com",
            "requires_passphrase": False,
            "has_spot": True,
            "has_futures": True,
            "has_margin": True,
            "priority": 1,  # Maior exchange, mostra primeiro
            "is_active": True,
            "ccxt_id": "binance",
            "docs_url": "https://binance-docs.github.io/apidocs/spot/en/",
            "created_at": datetime.utcnow(),
            "metadata": {
                "description": "Maior exchange de criptomoedas do mundo por volume",
                "countries": ["Global"],
                "year_founded": 2017,
                "supports_brl": False
            }
        },
        {
            "exchange_id": "coinbase",
            "name": "Coinbase Advanced",
            "icon": "🔵",
            "website": "https://www.coinbase.com",
            "requires_passphrase": True,  # Coinbase requer passphrase!
            "has_spot": True,
            "has_futures": False,
            "has_margin": False,
            "priority": 2,
            "is_active": True,
            "ccxt_id": "coinbase",
            "docs_url": "https://docs.cloud.coinbase.com/",
            "created_at": datetime.utcnow(),
            "metadata": {
                "description": "Exchange americana regulamentada",
                "countries": ["USA", "Global"],
                "year_founded": 2012,
                "supports_brl": False
            }
        },
        {
            "exchange_id": "kraken",
            "name": "Kraken",
            "icon": "🟠",
            "website": "https://www.kraken.com",
            "requires_passphrase": False,
            "has_spot": True,
            "has_futures": True,
            "has_margin": True,
            "priority": 3,
            "is_active": True,
            "ccxt_id": "kraken",
            "docs_url": "https://docs.kraken.com/rest/",
            "created_at": datetime.utcnow(),
            "metadata": {
                "description": "Exchange veterana e confiável",
                "countries": ["USA", "Global"],
                "year_founded": 2011,
                "supports_brl": False
            }
        },
        {
            "exchange_id": "kucoin",
            "name": "KuCoin",
            "icon": "🟣",
            "website": "https://www.kucoin.com",
            "requires_passphrase": True,  # KuCoin requer passphrase!
            "has_spot": True,
            "has_futures": True,
            "has_margin": True,
            "priority": 4,
            "is_active": True,
            "ccxt_id": "kucoin",
            "docs_url": "https://docs.kucoin.com/",
            "created_at": datetime.utcnow(),
            "metadata": {
                "description": "Exchange com grande variedade de altcoins",
                "countries": ["Seychelles"],
                "year_founded": 2017,
                "supports_brl": False
            }
        },
        {
            "exchange_id": "okx",
            "name": "OKX",
            "icon": "⚫",
            "website": "https://www.okx.com",
            "requires_passphrase": False,
            "has_spot": True,
            "has_futures": True,
            "has_margin": True,
            "priority": 5,
            "is_active": True,
            "ccxt_id": "okx",
            "docs_url": "https://www.okx.com/docs-v5/en/",
            "created_at": datetime.utcnow(),
            "metadata": {
                "description": "Grande exchange asiática",
                "countries": ["Seychelles"],
                "year_founded": 2017,
                "supports_brl": False
            }
        },
        {
            "exchange_id": "bybit",
            "name": "Bybit",
            "icon": "🟡",
            "website": "https://www.bybit.com",
            "requires_passphrase": False,
            "has_spot": True,
            "has_futures": True,
            "has_margin": True,
            "priority": 6,
            "is_active": True,
            "ccxt_id": "bybit",
            "docs_url": "https://bybit-exchange.github.io/docs/",
            "created_at": datetime.utcnow(),
            "metadata": {
                "description": "Focada em derivativos e trading",
                "countries": ["Dubai"],
                "year_founded": 2018,
                "supports_brl": False
            }
        },
        {
            "exchange_id": "novadax",
            "name": "NovaDAX",
            "icon": "🔴",
            "website": "https://www.novadax.com.br",
            "requires_passphrase": False,
            "has_spot": True,
            "has_futures": False,
            "has_margin": False,
            "priority": 7,
            "is_active": True,
            "ccxt_id": "novadax",
            "docs_url": "https://doc.novadax.com/pt-BR/",
            "created_at": datetime.utcnow(),
            "metadata": {
                "description": "Exchange brasileira",
                "countries": ["Brasil"],
                "year_founded": 2019,
                "supports_brl": True  # Suporta BRL!
            }
        },
        {
            "exchange_id": "gateio",
            "name": "Gate.io",
            "icon": "🟧",
            "website": "https://www.gate.io",
            "requires_passphrase": False,
            "has_spot": True,
            "has_futures": True,
            "has_margin": True,
            "priority": 8,
            "is_active": True,
            "ccxt_id": "gateio",
            "docs_url": "https://www.gate.io/docs/developers/apiv4/",
            "created_at": datetime.utcnow(),
            "metadata": {
                "description": "Exchange com muitas altcoins",
                "countries": ["Cayman Islands"],
                "year_founded": 2013,
                "supports_brl": False
            }
        },
        {
            "exchange_id": "mexc",
            "name": "MEXC",
            "icon": "🔵",
            "website": "https://www.mexc.com",
            "requires_passphrase": False,
            "has_spot": True,
            "has_futures": True,
            "has_margin": False,
            "priority": 9,
            "is_active": True,
            "ccxt_id": "mexc",
            "docs_url": "https://mxcdevelop.github.io/apidocs/spot_v3_en/",
            "created_at": datetime.utcnow(),
            "metadata": {
                "description": "Exchange com listagens rápidas de novos tokens",
                "countries": ["Singapore"],
                "year_founded": 2018,
                "supports_brl": False
            }
        }
    ]
    
    print(f"\n📝 Inserindo {len(exchanges)} exchanges...\n")
    
    # Remove exchanges antigas se existirem
    deleted = collection.delete_many({})
    if deleted.deleted_count > 0:
        print(f"   🗑️  Removidas {deleted.deleted_count} exchanges antigas\n")
    
    # Insere exchanges
    for exchange in exchanges:
        result = collection.insert_one(exchange)
        icon = exchange['icon']
        name = exchange['name']
        exchange_id = exchange['exchange_id']
        passphrase = "🔑 Requer passphrase" if exchange['requires_passphrase'] else ""
        
        print(f"   {icon} {name:20} ({exchange_id:10}) {passphrase}")
    
    print("\n" + "="*70)
    print(f"✅ {len(exchanges)} EXCHANGES CADASTRADAS COM SUCESSO!")
    print("="*70)
    
    print("\n📊 RESUMO:")
    print(f"   Total: {len(exchanges)}")
    print(f"   Requerem passphrase: {sum(1 for e in exchanges if e['requires_passphrase'])}")
    print(f"   Suportam BRL: {sum(1 for e in exchanges if e['metadata'].get('supports_brl'))}")
    
    print("\n💡 PRÓXIMO PASSO:")
    print("   Use o endpoint GET /api/v1/exchanges/available")
    print("   para listar exchanges disponíveis no frontend\n")


if __name__ == "__main__":
    try:
        seed_supported_exchanges()
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
