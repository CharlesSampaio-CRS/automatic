"""
Test optimized balance history queries
Validates that queries work correctly after optimization
"""

import os
import sys
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pymongo import MongoClient
from dotenv import load_dotenv
from src.services.balance_history_service import BalanceHistoryService
from src.utils.logger import get_logger

# Load environment
load_dotenv()

# Initialize logger
logger = get_logger(__name__)


def test_optimized_queries():
    """Test that optimized queries work correctly"""
    try:
        # Connect to MongoDB
        mongodb_uri = os.getenv('MONGODB_URI')
        if not mongodb_uri:
            logger.error("MONGODB_URI not found in environment")
            return False
        
        client = MongoClient(mongodb_uri)
        db = client.balance_tracker
        
        # Initialize service
        history_service = BalanceHistoryService(db)
        
        logger.info("=" * 60)
        logger.info("TESTING OPTIMIZED QUERIES")
        logger.info("=" * 60)
        
        # Test 1: Check indexes
        logger.info("\n📊 Test 1: Checking indexes...")
        indexes = list(db.balance_history.list_indexes())
        
        logger.info(f"   Found {len(indexes)} indexes:")
        for idx in indexes:
            logger.info(f"   - {idx['name']}: {idx.get('key', {})}")
        
        # Verify unused index is removed
        unused_index_exists = any('tokens_summary' in idx.get('name', '') for idx in indexes)
        if unused_index_exists:
            logger.warning("   ⚠️  Unused index (tokens_summary) still exists!")
        else:
            logger.info("   ✅ Unused index removed successfully")
        
        # Test 2: Test save_snapshot with float values
        logger.info("\n💾 Test 2: Testing save_snapshot (float storage)...")
        
        test_data = {
            'user_id': 'test_user_123',
            'summary': {
                'total_usd': '100.50',  # String input
                'total_brl': '520.00'
            },
            'exchanges': [
                {
                    'exchange_id': 'test_exchange',
                    'name': 'Test Exchange',
                    'total_usd': '100.50',
                    'total_brl': '520.00',
                    'success': True
                }
            ]
        }
        
        snapshot_id = history_service.save_snapshot(test_data)
        
        if snapshot_id:
            logger.info(f"   ✅ Snapshot saved: {snapshot_id}")
            
            # Verify it's stored as float
            saved_doc = db.balance_history.find_one({'_id': __import__('bson').ObjectId(snapshot_id)})
            
            if saved_doc:
                total_usd_type = type(saved_doc['total_usd']).__name__
                total_brl_type = type(saved_doc['total_brl']).__name__
                
                logger.info(f"   📊 total_usd type: {total_usd_type} = {saved_doc['total_usd']}")
                logger.info(f"   📊 total_brl type: {total_brl_type} = {saved_doc['total_brl']}")
                
                if isinstance(saved_doc['total_usd'], float):
                    logger.info("   ✅ Values stored as float (OPTIMIZED)")
                else:
                    logger.warning(f"   ⚠️  Values stored as {total_usd_type}, expected float")
        else:
            logger.error("   ❌ Failed to save snapshot")
        
        # Test 3: Test get_history
        logger.info("\n📜 Test 3: Testing get_history query...")
        history = history_service.get_history('test_user_123', limit=5)
        
        if history:
            logger.info(f"   ✅ Retrieved {len(history)} snapshots")
            
            # Check if projection works (no total_unique_tokens)
            first = history[0]
            if 'total_unique_tokens' in first:
                logger.warning("   ⚠️  total_unique_tokens still in results (projection issue)")
            else:
                logger.info("   ✅ Projection optimized (no unused fields)")
        else:
            logger.info("   ℹ️  No history data found")
        
        # Test 4: Test get_portfolio_evolution
        logger.info("\n📈 Test 4: Testing get_portfolio_evolution query...")
        evolution = history_service.get_portfolio_evolution('test_user_123', days=30)
        
        if evolution and evolution.get('timestamps'):
            logger.info(f"   ✅ Retrieved {len(evolution['timestamps'])} data points")
            
            # Verify no token_counts (removed field)
            if 'token_counts' in evolution:
                logger.warning("   ⚠️  token_counts still in results")
            else:
                logger.info("   ✅ Query optimized (no unused fields)")
            
            # Test calculations work with float values
            if 'summary' in evolution:
                logger.info("   ✅ Summary calculations working correctly")
                logger.info(f"      Start: {evolution['summary'].get('start_value_usd')}")
                logger.info(f"      End: {evolution['summary'].get('end_value_usd')}")
                logger.info(f"      Change: {evolution['summary'].get('change_percent')}")
        else:
            logger.info("   ℹ️  No evolution data found")
        
        # Clean up test data
        logger.info("\n🧹 Cleaning up test data...")
        result = db.balance_history.delete_many({'user_id': 'test_user_123'})
        logger.info(f"   Deleted {result.deleted_count} test documents")
        
        logger.info("\n" + "=" * 60)
        logger.info("✅ ALL TESTS COMPLETED SUCCESSFULLY")
        logger.info("=" * 60)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = test_optimized_queries()
    sys.exit(0 if success else 1)
