#!/usr/bin/env python3
"""
Script para configurar o Stop Loss no MongoDB

Uso:
    python scripts/config_stop_loss.py --enable         # Ativa o stop loss
    python scripts/config_stop_loss.py --disable        # Desativa o stop loss
    python scripts/config_stop_loss.py --percent 5      # Ajusta o percentual para 5%
    python scripts/config_stop_loss.py --status         # Mostra configuração atual
"""

import os
import sys
import argparse
from pymongo import MongoClient
from datetime import datetime
from dotenv import load_dotenv

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Carrega variáveis do .env
load_dotenv()

# Configuração do MongoDB
MONGO_URI = os.getenv('MONGODB_URI')
DATABASE_NAME = os.getenv('MONGODB_DATABASE', 'AutomaticInvest')
COLLECTION_NAME = 'BotConfigs'
PAIR = 'REKTCOIN/USDT'

if not MONGO_URI:
    print("❌ Erro: MONGODB_URI não encontrado no arquivo .env")
    sys.exit(1)

def get_db_collection():
    """Conecta ao MongoDB e retorna a collection"""
    client = MongoClient(MONGO_URI)
    db = client[DATABASE_NAME]
    return db[COLLECTION_NAME]

def show_current_config(collection):
    """Mostra a configuração atual do stop loss"""
    config = collection.find_one({'pair': PAIR})
    
    if not config:
        print(f"❌ Configuração para {PAIR} não encontrada no banco de dados.")
        return
    
    risk_mgmt = config.get('risk_management', {})
    stop_loss_enabled = risk_mgmt.get('stop_loss_enabled', True)
    stop_loss_percent = risk_mgmt.get('stop_loss_percent', 3.0)
    
    print("=" * 60)
    print(f"CONFIGURAÇÃO ATUAL - {PAIR}")
    print("=" * 60)
    print(f"Stop Loss Ativado: {'✅ SIM' if stop_loss_enabled else '❌ NÃO'}")
    print(f"Percentual de Perda: {stop_loss_percent}%")
    print(f"\nSignificado:")
    if stop_loss_enabled:
        print(f"  • Se o prejuízo atingir -{stop_loss_percent}%, o robô venderá automaticamente.")
    else:
        print(f"  • Stop loss DESATIVADO. O robô NÃO venderá por prejuízo automaticamente.")
        print(f"  ⚠️  ATENÇÃO: Isso aumenta o risco de perdas maiores!")
    print("=" * 60)

def enable_stop_loss(collection):
    """Ativa o stop loss"""
    result = collection.update_one(
        {'pair': PAIR},
        {
            '$set': {
                'risk_management.stop_loss_enabled': True,
                'metadata.last_updated': datetime.now().isoformat()
            }
        }
    )
    
    if result.modified_count > 0:
        print(f"✅ Stop loss ATIVADO para {PAIR}")
        show_current_config(collection)
    else:
        print(f"⚠️  Nenhuma alteração realizada. Verificar se o par {PAIR} existe.")

def disable_stop_loss(collection):
    """Desativa o stop loss"""
    result = collection.update_one(
        {'pair': PAIR},
        {
            '$set': {
                'risk_management.stop_loss_enabled': False,
                'metadata.last_updated': datetime.now().isoformat()
            }
        }
    )
    
    if result.modified_count > 0:
        print(f"⚠️  Stop loss DESATIVADO para {PAIR}")
        print(f"⚠️  ATENÇÃO: O robô NÃO venderá automaticamente em caso de prejuízo!")
        show_current_config(collection)
    else:
        print(f"⚠️  Nenhuma alteração realizada. Verificar se o par {PAIR} existe.")

def set_stop_loss_percent(collection, percent):
    """Define o percentual do stop loss"""
    if percent <= 0:
        print(f"❌ Erro: O percentual deve ser maior que 0.")
        return
    
    result = collection.update_one(
        {'pair': PAIR},
        {
            '$set': {
                'risk_management.stop_loss_percent': float(percent),
                'metadata.last_updated': datetime.now().isoformat()
            }
        }
    )
    
    if result.modified_count > 0:
        print(f"✅ Percentual do stop loss ajustado para {percent}% para {PAIR}")
        show_current_config(collection)
    else:
        print(f"⚠️  Nenhuma alteração realizada. Verificar se o par {PAIR} existe.")

def main():
    parser = argparse.ArgumentParser(
        description='Configura o Stop Loss no MongoDB para o bot de trading',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:
  python scripts/config_stop_loss.py --status
  python scripts/config_stop_loss.py --enable
  python scripts/config_stop_loss.py --disable
  python scripts/config_stop_loss.py --percent 5.0
  python scripts/config_stop_loss.py --enable --percent 4.0
        """
    )
    
    parser.add_argument('--enable', action='store_true', help='Ativa o stop loss')
    parser.add_argument('--disable', action='store_true', help='Desativa o stop loss')
    parser.add_argument('--percent', type=float, help='Define o percentual do stop loss (ex: 3.0 para 3%%)')
    parser.add_argument('--status', action='store_true', help='Mostra a configuração atual')
    
    args = parser.parse_args()
    
    # Se nenhum argumento foi passado, mostra o status
    if not any([args.enable, args.disable, args.percent, args.status]):
        args.status = True
    
    try:
        collection = get_db_collection()
        
        if args.status:
            show_current_config(collection)
        
        if args.enable:
            enable_stop_loss(collection)
        
        if args.disable:
            disable_stop_loss(collection)
        
        if args.percent is not None:
            set_stop_loss_percent(collection, args.percent)
        
    except Exception as e:
        print(f"❌ Erro ao conectar ao MongoDB: {e}")
        print(f"\nVerifique se:")
        print(f"  1. O MongoDB está rodando (mongodb://localhost:27017/)")
        print(f"  2. O banco de dados '{DATABASE_NAME}' existe")
        print(f"  3. A collection '{COLLECTION_NAME}' existe")

if __name__ == '__main__':
    main()
