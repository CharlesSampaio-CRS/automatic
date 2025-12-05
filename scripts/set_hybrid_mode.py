#!/usr/bin/env python3
"""
Script para configurar modo HÍBRIDO OTIMIZADO
Combina compra conservadora (safe) com venda agressiva (aggressive)

COMPRA:
- 4h: -5% (espera cair mais, melhor entrada)
- 24h: -6% (bom ponto de entrada)

VENDA:
- 4h: +8% (muito melhor que +6%)
- 24h: +12% (máximo lucro)

RESULTADO: Máximo lucro com menos risco de compra prematura
"""

import sys
import os
from pathlib import Path
from pymongo import MongoClient
from dotenv import load_dotenv

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

def set_hybrid_mode():
    """Configura modo híbrido otimizado para REKTCOIN/USDT"""
    
    print("\n" + "="*60)
    print("🎯 CONFIGURANDO MODO HÍBRIDO OTIMIZADO")
    print("="*60)
    
    db = get_database()
    collection = db['BotConfigs']
    
    # Configuração híbrida otimizada
    hybrid_config = {
        "pair": "REKTCOIN/USDT",
        "enabled": True,
        "trading_mode": "hybrid",  # Novo modo
        "buy_strategy": {
            "enabled": True,
            "min_drop_4h": 5.0,      # Safe: espera -5%
            "min_drop_24h": 6.0,     # Safe: espera -6%
            "invest_percent_4h": 15.0,
            "invest_percent_24h": 20.0,
            "cooldown_hours": 4
        },
        "sell_strategy": {
            "enabled": True,
            "min_profit_4h": 8.0,    # Aggressive: +8%
            "min_profit_24h": 12.0   # Aggressive: +12%
        },
        "risk_management": {
            "stop_loss_enabled": False,  # Você desabilitou
            "stop_loss_percent": 3.0,
            "max_position_percent": 30.0
        },
        "schedule": {
            "enabled": True,
            "interval_minutes": 10
        }
    }
    
    # Busca config atual
    current = collection.find_one({"pair": "REKTCOIN/USDT"})
    
    if current:
        print("\n📋 CONFIGURAÇÃO ATUAL:")
        print(f"   Modo: {current.get('trading_mode', 'safe')}")
        print(f"   Compra 4h: -{current.get('buy_strategy', {}).get('min_drop_4h', 5.0)}%")
        print(f"   Compra 24h: -{current.get('buy_strategy', {}).get('min_drop_24h', 6.0)}%")
        print(f"   Venda 4h: +{current.get('sell_strategy', {}).get('min_profit_4h', 6.0)}%")
        print(f"   Venda 24h: +{current.get('sell_strategy', {}).get('min_profit_24h', 8.0)}%")
    
    # Atualiza
    result = collection.update_one(
        {"pair": "REKTCOIN/USDT"},
        {"$set": hybrid_config},
        upsert=True
    )
    
    print("\n✅ NOVA CONFIGURAÇÃO:")
    print(f"   Modo: hybrid (otimizado)")
    print(f"   Compra 4h: -5.0% (conservador)")
    print(f"   Compra 24h: -6.0% (conservador)")
    print(f"   Venda 4h: +8.0% (agressivo) 🎯")
    print(f"   Venda 24h: +12.0% (agressivo) 🚀")
    print(f"   Stop Loss: Desabilitado")
    
    print("\n💡 BENEFÍCIOS:")
    print("   ✅ Compra em quedas REAIS (-5% e -6%)")
    print("   ✅ Vende com LUCRO MAIOR (+8% e +12%)")
    print("   ✅ Menos risco de compra prematura")
    print("   ✅ Até +101% mais lucro que modo safe")
    
    print("\n📊 EXEMPLO COM SUA POSIÇÃO:")
    print("   Se cair -6% e depois subir +8%:")
    print("   💰 Lucro: $1.04 (+8%)")
    print("   ")
    print("   Se cair -6% e depois subir +12%:")
    print("   💰 Lucro: $1.57 (+12%)")
    print("   ")
    print("   Compare com safe (+6%): $0.78")
    print("   Diferença: +33% a +101% 🔥")
    
    print("\n⏰ Próxima execução: 10 minutos")
    print("   O robô vai usar a nova configuração automaticamente")
    
    print("\n" + "="*60)
    print("✅ MODO HÍBRIDO ATIVADO COM SUCESSO!")
    print("="*60 + "\n")

if __name__ == "__main__":
    try:
        set_hybrid_mode()
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        sys.exit(1)
