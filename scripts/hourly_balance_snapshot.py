"""
Balance Snapshot Script
Salva automaticamente os saldos de todos os usuários
Executado a cada 4 horas pelo scheduler (00:00, 04:00, 08:00, 12:00, 16:00, 20:00)
"""

import os
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pymongo import MongoClient
from dotenv import load_dotenv
from src.services.balance_service import BalanceService
from src.services.balance_history_service import BalanceHistoryService
from src.utils.logger import get_logger
from src.config import MONGODB_URI, MONGODB_DATABASE

# Load environment variables
load_dotenv()

# Initialize logger
logger = get_logger(__name__)


def get_all_active_users(db):
    """
    Busca todos os usuários que têm exchanges vinculadas e ativas
    
    Returns:
        List of unique user_ids
    """
    try:
        # Find all users with at least one active exchange
        users = db.user_exchanges.find(
            {
                'exchanges': {
                    '$elemMatch': {
                        'is_active': True
                    }
                }
            },
            {'user_id': 1}
        )
        
        user_ids = [user['user_id'] for user in users]
        
        print(f"📋 Found {len(user_ids)} active users")
        return user_ids
        
    except Exception as e:
        logger.error(f"Error getting active users: {e}")
        return []


def save_hourly_snapshot_for_user(balance_service, history_service, user_id: str):
    """
    Salva snapshot de saldo para um usuário específico
    
    Args:
        balance_service: BalanceService instance
        history_service: BalanceHistoryService instance
        user_id: User ID
        
    Returns:
        bool: True se salvou com sucesso
    """
    try:
        logger.info(f"Processing user: {user_id}")
        
        # Busca saldos (sem usar cache para garantir dados atualizados)
        balance_data = balance_service.fetch_all_balances(
            user_id=user_id,
            use_cache=False,     # Não usa cache
            include_brl=True     # Inclui conversão BRL
        )
        
        if not balance_data or not balance_data.get('exchanges'):
            logger.warning(f"No balance data for user {user_id}")
            return False
        
        # Salva snapshot no histórico
        snapshot_id = history_service.save_snapshot(balance_data)
        
        if snapshot_id:
            total_usd = balance_data.get('summary', {}).get('total_usd', '0.00')
            exchanges_count = balance_data.get('summary', {}).get('exchanges_count', 0)
            logger.info(f"✅ Snapshot saved: {snapshot_id} | Total: ${total_usd} | Exchanges: {exchanges_count}")
            return True
        else:
            logger.warning(f"Failed to save snapshot for user {user_id}")
            return False
            
    except Exception as e:
        logger.error(f"Error saving snapshot for user {user_id}: {e}")
        return False


def run_hourly_snapshot():
    """
    Executa snapshot de saldos para todos os usuários ativos
    (Frequência configurada no scheduler)
    """
    logger.info("=" * 80)
    logger.info(f"BALANCE SNAPSHOT - {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    logger.info("=" * 80)
    
    try:
        # Connect to MongoDB
        client = MongoClient(MONGODB_URI)
        db = client[MONGODB_DATABASE]
        
        # Test connection
        client.server_info()
        logger.info("Connected to MongoDB")
        
        # Initialize services
        balance_service = BalanceService(db)
        history_service = BalanceHistoryService(db)
        
        # Get all active users
        user_ids = get_all_active_users(db)
        
        if not user_ids:
            logger.warning("No active users found. Exiting.")
            return
        
        # Process each user
        success_count = 0
        fail_count = 0
        
        for user_id in user_ids:
            if save_hourly_snapshot_for_user(balance_service, history_service, user_id):
                success_count += 1
            else:
                fail_count += 1
        
        # Summary
        logger.info("=" * 80)
        logger.info(f"SUMMARY:")
        logger.info(f"   Success: {success_count}")
        logger.info(f"   Failed: {fail_count}")
        logger.info(f"   Total: {len(user_ids)}")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"Fatal error in hourly snapshot: {e}")
    finally:
        if 'client' in locals():
            client.close()
            logger.info("MongoDB connection closed")


if __name__ == '__main__':
    run_hourly_snapshot()
