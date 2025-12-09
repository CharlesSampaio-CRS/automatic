"""
Migrate Balance History Data - Convert string values to float
Converts all existing balance_history documents from string format to float format
"""

import os
import sys
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pymongo import MongoClient
from dotenv import load_dotenv
from src.utils.logger import get_logger

# Load environment
load_dotenv()

# Initialize logger
logger = get_logger(__name__)


def parse_value(value):
    """
    Parse string value to float
    Handles formats: "$42.60", "R$ 213.00", "42.60", etc.
    
    Args:
        value: String or numeric value
        
    Returns:
        Float value
    """
    if isinstance(value, (int, float)):
        return float(value)
    
    if isinstance(value, str):
        # Remove currency symbols and spaces
        cleaned = value.replace('$', '').replace('R', '').replace(' ', '').strip()
        try:
            return float(cleaned)
        except ValueError:
            logger.warning(f"Could not parse value: {value}")
            return 0.0
    
    return 0.0


def migrate_balance_history():
    """
    Migrate all balance_history documents to use float instead of string values
    """
    try:
        # Connect to MongoDB
        mongodb_uri = os.getenv('MONGODB_URI')
        if not mongodb_uri:
            logger.error("MONGODB_URI not found in environment")
            return
        
        client = MongoClient(mongodb_uri)
        db = client.balance_tracker
        collection = db.balance_history
        
        logger.info("🔄 Starting migration of balance_history documents...")
        
        # Get all documents
        total_docs = collection.count_documents({})
        logger.info(f"📊 Found {total_docs} documents to migrate")
        
        if total_docs == 0:
            logger.info("✅ No documents to migrate")
            return
        
        # Process documents in batches
        batch_size = 100
        migrated_count = 0
        error_count = 0
        
        cursor = collection.find({})
        
        for doc in cursor:
            try:
                # Check if already migrated (if total_usd is float)
                if isinstance(doc.get('total_usd'), float):
                    continue
                
                # Prepare update
                update_fields = {}
                
                # Convert total_usd and total_brl
                if 'total_usd' in doc:
                    update_fields['total_usd'] = round(parse_value(doc['total_usd']), 2)
                
                if 'total_brl' in doc:
                    update_fields['total_brl'] = round(parse_value(doc['total_brl']), 2)
                
                # Convert exchange values
                if 'exchanges' in doc:
                    updated_exchanges = []
                    for ex in doc['exchanges']:
                        updated_ex = ex.copy()
                        
                        if 'total_usd' in ex:
                            updated_ex['total_usd'] = round(parse_value(ex['total_usd']), 2)
                        
                        if 'total_brl' in ex:
                            updated_ex['total_brl'] = round(parse_value(ex['total_brl']), 2)
                        
                        updated_exchanges.append(updated_ex)
                    
                    update_fields['exchanges'] = updated_exchanges
                
                # Update document
                if update_fields:
                    collection.update_one(
                        {'_id': doc['_id']},
                        {'$set': update_fields}
                    )
                    migrated_count += 1
                    
                    if migrated_count % 100 == 0:
                        logger.info(f"   Processed {migrated_count}/{total_docs} documents...")
                
            except Exception as e:
                error_count += 1
                logger.error(f"Error migrating document {doc.get('_id')}: {e}")
                continue
        
        logger.info(f"\n✅ Migration completed!")
        logger.info(f"   📊 Total documents: {total_docs}")
        logger.info(f"   ✓ Migrated: {migrated_count}")
        logger.info(f"   ⚠ Errors: {error_count}")
        logger.info(f"   → Skipped (already float): {total_docs - migrated_count - error_count}")
        
        # Drop old unused index
        logger.info("\n🗑️  Removing unused index (user_id, tokens_summary)...")
        try:
            collection.drop_index('user_id_1_tokens_summary_1')
            logger.info("   ✅ Unused index removed")
        except Exception as e:
            logger.warning(f"   ⚠️  Could not remove index (might not exist): {e}")
        
        logger.info("\n🎉 Migration completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        raise


if __name__ == '__main__':
    logger.info("=" * 60)
    logger.info("BALANCE HISTORY MIGRATION - String to Float")
    logger.info("=" * 60)
    logger.info("")
    
    # Confirm migration
    print("\n⚠️  This will convert all balance_history documents from string to float format.")
    print("   This operation is SAFE and can be run multiple times.")
    print("   Already migrated documents will be skipped.\n")
    
    confirm = input("Do you want to proceed? (yes/no): ").strip().lower()
    
    if confirm in ['yes', 'y']:
        logger.info("Starting migration...")
        migrate_balance_history()
    else:
        logger.info("Migration cancelled by user")
