"""
Script para popular o histórico de saldos com dados fictícios.
Limpa a collection balance_history e insere snapshots dos últimos 5 dias.

Uso:
    python scripts/seed_balance_history.py

O script cria:
- 1 snapshot por hora (00:00, 01:00, 02:00, ..., 23:00)
- Para os últimos 5 dias (120 registros totais)
- Com variação realista nos valores (simula flutuações de mercado)
- Para o usuário 'charles_test_user'
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
import random

# Adiciona o diretório raiz ao path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from pymongo import MongoClient
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

MONGODB_URI = os.getenv('MONGODB_URI')
MONGODB_DATABASE = os.getenv('MONGODB_DATABASE', 'MultExchange')

def connect_mongodb():
    """Conecta ao MongoDB."""
    try:
        client = MongoClient(MONGODB_URI)
        db = client[MONGODB_DATABASE]
        # Testa conexão
        client.admin.command('ping')
        print(f"✅ Conectado ao MongoDB: {MONGODB_DATABASE}")
        return db
    except Exception as e:
        print(f"❌ Erro ao conectar ao MongoDB: {e}")
        sys.exit(1)

def clear_history(db):
    """Limpa a collection balance_history."""
    try:
        result = db.balance_history.delete_many({})
        print(f"🗑️  Removidos {result.deleted_count} registros de histórico")
        return True
    except Exception as e:
        print(f"❌ Erro ao limpar histórico: {e}")
        return False

def generate_price_variation(base_price, volatility=0.05):
    """
    Gera variação de preço realista.
    
    Args:
        base_price: Preço base
        volatility: Volatilidade (padrão: 5%)
    
    Returns:
        Novo preço com variação aleatória
    """
    variation = random.uniform(-volatility, volatility)
    return base_price * (1 + variation)

def generate_snapshot(user_id, timestamp, base_values):
    """
    Gera um snapshot de saldo com valores fictícios.
    
    Args:
        user_id: ID do usuário
        timestamp: Data/hora do snapshot
        base_values: Valores base para variação
    
    Returns:
        Documento de snapshot pronto para inserir
    """
    # Simula flutuação no total_usd (±10% de variação)
    total_usd = round(generate_price_variation(base_values['total_usd'], 0.10), 2)
    
    # BRL/USD: taxa entre 5.0 e 5.2
    brl_rate = random.uniform(5.0, 5.2)
    total_brl = round(total_usd * brl_rate, 2)
    
    # Distribui o valor entre exchanges (70% MEXC, 30% Binance, 0% NovaDAX)
    mexc_usd = round(total_usd * 0.70, 2)
    binance_usd = round(total_usd * 0.30, 2)
    
    mexc_brl = round(mexc_usd * brl_rate, 2)
    binance_brl = round(binance_usd * brl_rate, 2)
    
    return {
        "user_id": user_id,
        "timestamp": timestamp.isoformat(),
        "total_usd": total_usd,
        "total_brl": total_brl,
        "exchanges": [
            {
                "exchange_id": "693481148b0a41e8b6acb079",
                "exchange_name": "NovaDAX",
                "total_usd": 0.0,
                "total_brl": 0.0,
                "success": True
            },
            {
                "exchange_id": "693481148b0a41e8b6acb07b",
                "exchange_name": "MEXC",
                "total_usd": mexc_usd,
                "total_brl": mexc_brl,
                "success": True
            },
            {
                "exchange_id": "693481148b0a41e8b6acb073",
                "exchange_name": "Binance",
                "total_usd": binance_usd,
                "total_brl": binance_brl,
                "success": True
            }
        ]
    }

def seed_history(db, user_id="charles_test_user", days=5):
    """
    Popula histórico com dados fictícios.
    
    Args:
        db: Conexão com MongoDB
        user_id: ID do usuário (padrão: charles_test_user)
        days: Quantidade de dias (padrão: 5)
    """
    print(f"\n📊 Gerando dados fictícios para {days} dias...")
    
    # Valores base para variação
    base_values = {
        'total_usd': 135.0  # Valor base em USD
    }
    
    # Data inicial: X dias atrás às 00:00
    end_date = datetime.now().replace(minute=0, second=0, microsecond=0)
    start_date = end_date - timedelta(days=days)
    
    snapshots = []
    current_time = start_date
    
    # Gera 1 snapshot por hora
    while current_time <= end_date:
        snapshot = generate_snapshot(user_id, current_time, base_values)
        snapshots.append(snapshot)
        current_time += timedelta(hours=1)
    
    print(f"✅ {len(snapshots)} snapshots gerados")
    
    # Insere no MongoDB
    try:
        result = db.balance_history.insert_many(snapshots)
        print(f"✅ {len(result.inserted_ids)} registros inseridos com sucesso!")
        
        # Mostra resumo
        print(f"\n📈 Resumo:")
        print(f"   Período: {start_date.strftime('%d/%m/%Y %H:%M')} até {end_date.strftime('%d/%m/%Y %H:%M')}")
        print(f"   Total de snapshots: {len(snapshots)}")
        print(f"   Primeiro valor: ${snapshots[0]['total_usd']:.2f} USD / R$ {snapshots[0]['total_brl']:.2f} BRL")
        print(f"   Último valor: ${snapshots[-1]['total_usd']:.2f} USD / R$ {snapshots[-1]['total_brl']:.2f} BRL")
        
        # Calcula variação
        variation_usd = snapshots[-1]['total_usd'] - snapshots[0]['total_usd']
        variation_percent = (variation_usd / snapshots[0]['total_usd']) * 100
        
        emoji = "📈" if variation_usd >= 0 else "📉"
        sign = "+" if variation_usd >= 0 else ""
        print(f"   Variação: {emoji} {sign}${variation_usd:.2f} USD ({sign}{variation_percent:.2f}%)")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao inserir dados: {e}")
        return False

def main():
    """Função principal."""
    print("=" * 60)
    print("🌱 SEED: Balance History - Dados Fictícios")
    print("=" * 60)
    
    # Conecta ao MongoDB
    db = connect_mongodb()
    
    # Limpa histórico existente
    print("\n🗑️  Limpando histórico existente...")
    if not clear_history(db):
        sys.exit(1)
    
    # Popula com dados fictícios
    if not seed_history(db, days=5):
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("✅ Seed concluído com sucesso!")
    print("=" * 60)
    print("\n💡 Teste os endpoints:")
    print("   GET /api/v1/balances/history?user_id=charles_test_user")
    print("   GET /api/v1/balances/history/latest?user_id=charles_test_user")
    print("   GET /api/v1/balances/history/evolution?user_id=charles_test_user&period=7d")

if __name__ == "__main__":
    main()
