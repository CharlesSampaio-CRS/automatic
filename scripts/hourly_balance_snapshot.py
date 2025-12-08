"""
Hourly Balance Snapshot Script
Salva automaticamente os saldos de todos os usuários a cada hora fechada (00:00, 01:00, 02:00, etc.)
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

# Load environment variables
load_dotenv()

MONGODB_URI = os.getenv('MONGODB_URI')
MONGODB_DATABASE = os.getenv('MONGODB_DATABASE', 'MultExchange')


def get_all_active_users(db):
    """
    Busca todos os usuários que têm exchanges vinculadas e ativas
    
    Returns:
        List of unique user_ids
    """
    try:
        pipeline = [
            {
                '$match': {
                    'is_active': True
                }
            },
            {
                '$group': {
                    '_id': '$user_id'
                }
            }
        ]
        
        users = db.user_exchanges.aggregate(pipeline)
        user_ids = [user['_id'] for user in users]
        
        print(f"📋 Found {len(user_ids)} active users")
        return user_ids
        
    except Exception as e:
        print(f"❌ Error getting active users: {e}")
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
        print(f"\n👤 Processing user: {user_id}")
        
        # Busca saldos (sem usar cache para garantir dados atualizados)
        balance_data = balance_service.get_balances(
            user_id=user_id,
            force_refresh=True,  # Sempre busca dados novos
            use_cache=False,     # Não usa cache
            include_currency='brl'
        )
        
        if not balance_data:
            print(f"⚠️  No balance data for user {user_id}")
            return False
        
        # Salva snapshot no histórico
        snapshot_id = history_service.save_snapshot(balance_data)
        
        if snapshot_id:
            total_usd = balance_data.get('summary', {}).get('total_usd', '0.00')
            exchanges_count = len([ex for ex in balance_data.get('exchanges', []) if ex.get('success')])
            print(f"✅ Snapshot saved: {snapshot_id} | Total: ${total_usd} | Exchanges: {exchanges_count}")
            return True
        else:
            print(f"⚠️  Failed to save snapshot for user {user_id}")
            return False
            
    except Exception as e:
        print(f"❌ Error saving snapshot for user {user_id}: {e}")
        return False


def run_hourly_snapshot():
    """
    Executa snapshot horário para todos os usuários ativos
    """
    print("=" * 80)
    print(f"🕐 HOURLY BALANCE SNAPSHOT - {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("=" * 80)
    
    try:
        # Connect to MongoDB
        client = MongoClient(MONGODB_URI)
        db = client[MONGODB_DATABASE]
        
        # Test connection
        client.server_info()
        print("✅ Connected to MongoDB")
        
        # Initialize services
        balance_service = BalanceService(db)
        history_service = BalanceHistoryService(db)
        
        # Get all active users
        user_ids = get_all_active_users(db)
        
        if not user_ids:
            print("⚠️  No active users found. Exiting.")
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
        print("\n" + "=" * 80)
        print(f"📊 SUMMARY:")
        print(f"   ✅ Success: {success_count}")
        print(f"   ❌ Failed: {fail_count}")
        print(f"   📋 Total: {len(user_ids)}")
        print("=" * 80)
        
    except Exception as e:
        print(f"❌ Fatal error in hourly snapshot: {e}")
    finally:
        if 'client' in locals():
            client.close()
            print("🔌 MongoDB connection closed")


if __name__ == '__main__':
    run_hourly_snapshot()
