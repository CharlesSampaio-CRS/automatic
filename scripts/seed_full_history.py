#!/usr/bin/env python3
"""
Script para popular histórico completo de 1 ano
Permite testar todos os períodos: 24h, 7d, 30d, 90d, 365d
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
        return db, client
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

def generate_price_variation(base_price, volatility=0.05, trend=0):
    """
    Gera variação de preço realista com tendência.
    
    Args:
        base_price: Preço base
        volatility: Volatilidade (padrão: 5%)
        trend: Tendência de crescimento (-1 a 1)
    
    Returns:
        Novo preço com variação aleatória e tendência
    """
    # Variação aleatória
    variation = random.uniform(-volatility, volatility)
    # Adiciona tendência
    trend_factor = trend * 0.001  # 0.1% por chamada na direção da tendência
    return base_price * (1 + variation + trend_factor)

def generate_snapshot(user_id, timestamp, total_usd, brl_rate=5.145):
    """
    Gera um snapshot de saldo.
    
    Args:
        user_id: ID do usuário
        timestamp: Data/hora do snapshot
        total_usd: Valor total em USD
        brl_rate: Taxa USD/BRL
    
    Returns:
        Documento de snapshot pronto para inserir
    """
    total_brl = round(total_usd * brl_rate, 2)
    
    # Distribui entre exchanges (70% MEXC, 30% Binance, 0% NovaDAX)
    mexc_usd = round(total_usd * 0.70, 2)
    binance_usd = round(total_usd * 0.30, 2)
    
    mexc_brl = round(mexc_usd * brl_rate, 2)
    binance_brl = round(binance_usd * brl_rate, 2)
    
    return {
        "user_id": user_id,
        "timestamp": timestamp,
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

def seed_history(db, user_id="charles_test_user", days=365):
    """
    Popula histórico com dados fictícios realistas.
    
    Estratégia:
    - Começa com $45 há 1 ano
    - Cresce gradualmente até $170 hoje
    - Com flutuações realistas
    - Simula bear/bull markets em diferentes períodos
    
    Args:
        db: Conexão com MongoDB
        user_id: ID do usuário (padrão: charles_test_user)
        days: Quantidade de dias (padrão: 365)
    """
    print(f"\n📊 Gerando histórico completo de {days} dias...")
    
    # Configuração de crescimento
    start_value = 45.67  # Valor inicial há 1 ano
    end_value = 170.23   # Valor atual
    total_growth = end_value - start_value
    
    # Data inicial: X dias atrás às 00:00
    end_date = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
    start_date = end_date - timedelta(days=days)
    
    snapshots = []
    current_time = start_date
    current_value = start_value
    
    # Taxa BRL/USD com pequena variação ao longo do tempo
    base_brl_rate = 5.145
    
    # Gera 1 snapshot por hora
    hour_count = 0
    total_hours = days * 24
    
    print(f"📅 Período: {start_date.strftime('%d/%m/%Y %H:%M')} até {end_date.strftime('%d/%m/%Y %H:%M')}")
    print(f"⏱️  Total de snapshots: {total_hours} (1 por hora)")
    print(f"💰 Valor inicial: ${start_value:.2f} USD")
    print(f"💰 Valor final: ${end_value:.2f} USD")
    print(f"📈 Crescimento total: ${total_growth:.2f} USD ({(total_growth/start_value*100):.1f}%)")
    
    while current_time <= end_date:
        # Calcula progresso (0.0 a 1.0)
        progress = hour_count / total_hours
        
        # Tendência de crescimento (não-linear, mais forte no final)
        # Simula mercado bear nos primeiros 6 meses, depois bull market
        if progress < 0.5:
            # Primeiros 6 meses: crescimento lento com volatilidade
            trend = 0.3
            volatility = 0.08
        else:
            # Últimos 6 meses: crescimento acelerado
            trend = 0.8
            volatility = 0.06
        
        # Aplica crescimento gradual
        target_value = start_value + (total_growth * progress)
        current_value = current_value * 0.95 + target_value * 0.05  # Smooth transition
        
        # Adiciona variação realista
        current_value = generate_price_variation(current_value, volatility, trend)
        
        # Garante que não ultrapasse os limites
        current_value = max(start_value * 0.8, min(current_value, end_value * 1.1))
        
        # Taxa BRL com pequena variação
        brl_rate = base_brl_rate * random.uniform(0.98, 1.02)
        
        # Gera snapshot
        snapshot = generate_snapshot(user_id, current_time, round(current_value, 2), brl_rate)
        snapshots.append(snapshot)
        
        # Próxima hora
        current_time += timedelta(hours=1)
        hour_count += 1
        
        # Progress indicator
        if hour_count % 500 == 0:
            print(f"   ⏳ Processando: {hour_count}/{total_hours} snapshots ({progress*100:.1f}%)")
    
    print(f"\n✅ {len(snapshots)} snapshots gerados")
    
    # Insere no MongoDB em lotes
    batch_size = 1000
    total_inserted = 0
    
    print(f"\n💾 Inserindo no MongoDB (lotes de {batch_size})...")
    
    try:
        for i in range(0, len(snapshots), batch_size):
            batch = snapshots[i:i + batch_size]
            result = db.balance_history.insert_many(batch)
            total_inserted += len(result.inserted_ids)
            print(f"   ✅ Inseridos {total_inserted}/{len(snapshots)} snapshots")
        
        print(f"\n✅ Total inserido: {total_inserted} registros")
        
        # Mostra resumo
        print(f"\n" + "="*60)
        print(f"📈 RESUMO DO HISTÓRICO")
        print("="*60)
        print(f"   Período: {start_date.strftime('%d/%m/%Y')} a {end_date.strftime('%d/%m/%Y')}")
        print(f"   Dias: {days}")
        print(f"   Snapshots/hora: 1")
        print(f"   Total de snapshots: {len(snapshots)}")
        print(f"   Primeiro valor: ${snapshots[0]['total_usd']:.2f} USD / R$ {snapshots[0]['total_brl']:.2f} BRL")
        print(f"   Último valor: ${snapshots[-1]['total_usd']:.2f} USD / R$ {snapshots[-1]['total_brl']:.2f} BRL")
        
        # Calcula variação
        variation_usd = snapshots[-1]['total_usd'] - snapshots[0]['total_usd']
        variation_percent = (variation_usd / snapshots[0]['total_usd']) * 100
        
        emoji = "📈" if variation_usd >= 0 else "📉"
        sign = "+" if variation_usd >= 0 else ""
        print(f"   Variação: {emoji} {sign}${variation_usd:.2f} USD ({sign}{variation_percent:.2f}%)")
        
        # Estatísticas por período
        print(f"\n📊 DADOS DISPONÍVEIS PARA TESTE:")
        print("="*60)
        
        # Últimas 24 horas
        last_24h = [s for s in snapshots if (end_date - s['timestamp']).total_seconds() <= 86400]
        if last_24h:
            var_24h = ((last_24h[-1]['total_usd'] - last_24h[0]['total_usd']) / last_24h[0]['total_usd']) * 100
            print(f"   ✅ 24h: {len(last_24h)} snapshots | Variação: {var_24h:+.2f}%")
        
        # Últimos 7 dias
        last_7d = [s for s in snapshots if (end_date - s['timestamp']).total_seconds() <= 604800]
        if last_7d:
            var_7d = ((last_7d[-1]['total_usd'] - last_7d[0]['total_usd']) / last_7d[0]['total_usd']) * 100
            print(f"   ✅ 7d: {len(last_7d)} snapshots | Variação: {var_7d:+.2f}%")
        
        # Últimos 30 dias
        last_30d = [s for s in snapshots if (end_date - s['timestamp']).total_seconds() <= 2592000]
        if last_30d:
            var_30d = ((last_30d[-1]['total_usd'] - last_30d[0]['total_usd']) / last_30d[0]['total_usd']) * 100
            print(f"   ✅ 30d: {len(last_30d)} snapshots | Variação: {var_30d:+.2f}%")
        
        # Últimos 90 dias
        last_90d = [s for s in snapshots if (end_date - s['timestamp']).total_seconds() <= 7776000]
        if last_90d:
            var_90d = ((last_90d[-1]['total_usd'] - last_90d[0]['total_usd']) / last_90d[0]['total_usd']) * 100
            print(f"   ✅ 90d: {len(last_90d)} snapshots | Variação: {var_90d:+.2f}%")
        
        # 1 ano
        var_365d = ((snapshots[-1]['total_usd'] - snapshots[0]['total_usd']) / snapshots[0]['total_usd']) * 100
        print(f"   ✅ 365d: {len(snapshots)} snapshots | Variação: {var_365d:+.2f}%")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao inserir dados: {e}")
        return False

def main():
    """Função principal."""
    print("=" * 60)
    print("🌱 SEED: Full Balance History (1 Year)")
    print("=" * 60)
    
    # Verifica se foi passado --force como argumento
    force = '--force' in sys.argv or '-f' in sys.argv
    
    # Conecta ao MongoDB
    db, client = connect_mongodb()
    
    # Pergunta se deseja limpar histórico existente
    print("\n⚠️  Este script irá:")
    print("   1. Limpar todo o histórico existente")
    print("   2. Gerar 8.760 snapshots (1 ano, 1 por hora)")
    print("   3. Permitir testar todos os períodos (24h, 7d, 30d, 90d, 365d)")
    
    if not force:
        response = input("\n🤔 Deseja continuar? (sim/não): ").strip().lower()
        
        if response != 'sim':
            print("\n❌ Operação cancelada pelo usuário")
            client.close()
            sys.exit(0)
    else:
        print("\n✅ Modo --force ativado, executando automaticamente...")
    
    # Limpa histórico existente
    print("\n🗑️  Limpando histórico existente...")
    if not clear_history(db):
        client.close()
        sys.exit(1)
    
    # Popula com dados fictícios de 1 ano
    if not seed_history(db, days=365):
        client.close()
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("✅ Seed concluído com sucesso!")
    print("=" * 60)
    
    print("\n💡 Teste os endpoints:")
    print("   # 24 horas")
    print("   curl 'http://localhost:5000/api/v1/history/evolution?user_id=charles_test_user&days=1'")
    print("\n   # 7 dias")
    print("   curl 'http://localhost:5000/api/v1/history/evolution?user_id=charles_test_user&days=7'")
    print("\n   # 30 dias")
    print("   curl 'http://localhost:5000/api/v1/history/evolution?user_id=charles_test_user&days=30'")
    print("\n   # 90 dias")
    print("   curl 'http://localhost:5000/api/v1/history/evolution?user_id=charles_test_user&days=90'")
    print("\n   # 1 ano")
    print("   curl 'http://localhost:5000/api/v1/history/evolution?user_id=charles_test_user&days=365'")
    
    print("\n   # Histórico completo (lista)")
    print("   curl 'http://localhost:5000/api/v1/history?user_id=charles_test_user&limit=168'")
    
    client.close()

if __name__ == "__main__":
    main()
