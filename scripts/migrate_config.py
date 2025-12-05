#!/usr/bin/env python3
"""
Script para migrar configuração do MongoDB para estrutura simplificada.

Remove campos complexos e redundantes, mantendo apenas o essencial.
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

def show_current_config(collection):
    """Mostra configuração atual"""
    config = collection.find_one({'pair': 'REKTCOIN/USDT'})
    
    if not config:
        print("❌ Configuração não encontrada para REKTCOIN/USDT")
        return None
    
    print("=" * 80)
    print("CONFIGURAÇÃO ATUAL (COMPLEXA)")
    print("=" * 80)
    print(f"Campos principais: {len(config)} campos")
    print(f"  - strategy_4h: {len(config.get('strategy_4h', {}))} subcampos")
    print(f"  - strategy_24h: {len(config.get('strategy_24h', {}))} subcampos")
    print(f"  - trading_strategy: {len(config.get('trading_strategy', {}))} subcampos")
    print(f"  - risk_management: {len(config.get('risk_management', {}))} subcampos")
    print()
    
    return config

def migrate_to_simple_structure(collection):
    """Migra para estrutura simplificada"""
    
    old_config = collection.find_one({'pair': 'REKTCOIN/USDT'})
    
    if not old_config:
        print("❌ Configuração não encontrada!")
        return False
    
    # Extrai valores das estruturas antigas
    trading_mode = old_config.get('trading_mode', 'safe')
    
    # Buy strategy (consolida strategy_4h + trading_strategy)
    strategy_4h = old_config.get('strategy_4h', {})
    trading_strategy = old_config.get('trading_strategy', {})
    
    # Sell strategy
    sell_strategy_4h = strategy_4h.get('sell_strategy', {})
    sell_strategy_24h = old_config.get('strategy_24h', {}).get('sell_strategy', {})
    
    # Risk management
    risk_4h = strategy_4h.get('risk_management', {})
    risk_main = old_config.get('risk_management', {})
    
    # NOVA ESTRUTURA SIMPLIFICADA
    new_config = {
        "pair": "REKTCOIN/USDT",
        "enabled": old_config.get('enabled', True),
        
        "trading_mode": trading_mode,
        
        "buy_strategy": {
            "enabled": True,
            "min_drop_4h": 5.0,  # Padrão safe mode
            "min_drop_24h": trading_strategy.get('min_variation_to_buy', 6.0),
            "invest_percent_4h": 15.0,  # Padrão safe mode
            "invest_percent_24h": 20.0,  # Padrão safe mode
            "cooldown_hours": 4  # Padrão safe mode
        },
        
        "sell_strategy": {
            "enabled": True,
            "min_profit_4h": sell_strategy_4h.get('min_profit', 6.0),
            "min_profit_24h": sell_strategy_24h.get('min_profit', 8.0)
        },
        
        "risk_management": {
            "stop_loss_enabled": risk_main.get('stop_loss_enabled', False),
            "stop_loss_percent": abs(risk_4h.get('stop_loss_percent', 3.0)),
            "max_position_percent": 30.0  # Padrão safe mode
        },
        
        "schedule": old_config.get('schedule', {
            "enabled": True,
            "interval_minutes": 10
        }),
        
        "metadata": old_config.get('metadata', {})
    }
    
    print("=" * 80)
    print("NOVA CONFIGURAÇÃO (SIMPLIFICADA)")
    print("=" * 80)
    print(f"Campos principais: {len(new_config)} campos")
    print()
    print("📋 Estrutura:")
    print(f"  ✓ trading_mode: {new_config['trading_mode']}")
    print(f"  ✓ buy_strategy: {len(new_config['buy_strategy'])} campos")
    print(f"  ✓ sell_strategy: {len(new_config['sell_strategy'])} campos")
    print(f"  ✓ risk_management: {len(new_config['risk_management'])} campos")
    print()
    print("💰 Buy Strategy:")
    print(f"  - Min drop 4h: -{new_config['buy_strategy']['min_drop_4h']}%")
    print(f"  - Min drop 24h: -{new_config['buy_strategy']['min_drop_24h']}%")
    print(f"  - Invest 4h: {new_config['buy_strategy']['invest_percent_4h']}%")
    print(f"  - Invest 24h: {new_config['buy_strategy']['invest_percent_24h']}%")
    print(f"  - Cooldown: {new_config['buy_strategy']['cooldown_hours']}h")
    print()
    print("💵 Sell Strategy:")
    print(f"  - Min profit 4h: +{new_config['sell_strategy']['min_profit_4h']}%")
    print(f"  - Min profit 24h: +{new_config['sell_strategy']['min_profit_24h']}%")
    print()
    print("🛡️  Risk Management:")
    stop_status = "❌ Desativado" if not new_config['risk_management']['stop_loss_enabled'] else "✅ Ativado"
    print(f"  - Stop loss: {stop_status}")
    print(f"  - Stop loss %: -{new_config['risk_management']['stop_loss_percent']}%")
    print(f"  - Max position: {new_config['risk_management']['max_position_percent']}%")
    print()
    
    # Substitui o documento inteiro
    result = collection.replace_one(
        {'pair': 'REKTCOIN/USDT'},
        new_config
    )
    
    if result.modified_count > 0:
        print("=" * 80)
        print("✅ MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
        print("=" * 80)
        print(f"📊 Redução de complexidade:")
        print(f"   Antes: ~{len(old_config)} campos principais")
        print(f"   Depois: {len(new_config)} campos principais")
        print(f"   Economia: ~{len(old_config) - len(new_config)} campos removidos")
        print()
        return True
    else:
        print("⚠️  Nenhuma modificação necessária")
        return False

def main():
    """Executa migração"""
    collection = get_mongo_client()
    
    print("\n🔄 MIGRAÇÃO PARA ESTRUTURA SIMPLIFICADA\n")
    
    # Mostra config atual
    show_current_config(collection)
    
    # Pergunta confirmação
    print("⚠️  ATENÇÃO: Esta operação vai SUBSTITUIR a configuração atual!")
    print("   Os campos complexos (strategy_4h, strategy_24h, trading_strategy)")
    print("   serão removidos e consolidados na nova estrutura.\n")
    
    resposta = input("Deseja continuar? (sim/não): ").lower().strip()
    
    if resposta not in ['sim', 's', 'yes', 'y']:
        print("\n❌ Migração cancelada pelo usuário")
        return
    
    print()
    
    # Executa migração
    if migrate_to_simple_structure(collection):
        print("🎉 Configuração simplificada e otimizada!")
        print("   O código agora lerá a nova estrutura automaticamente.")
    else:
        print("❌ Erro na migração")

if __name__ == "__main__":
    main()
