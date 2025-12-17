"""
Script para atualizar lista de tokens disponíveis em cada exchange
Executa diariamente às 3h da manhã via scheduler
Salva na collection tokens_exchanges do MongoDB
"""

import os
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from pymongo import MongoClient
from bson import ObjectId
import ccxt

from src.utils.logger import get_logger
from src.security.encryption import get_encryption_service
from src.config import MONGODB_URI, MONGODB_DATABASE

# Load environment variables
load_dotenv()

# Initialize logger
logger = get_logger(__name__)


def get_database():
    """Retorna conexão com MongoDB"""
    client = MongoClient(MONGODB_URI)
    return client[MONGODB_DATABASE]


def update_exchange_tokens(exchange_id: str, exchange_info: dict) -> dict:
    """
    Busca todos os tokens disponíveis em uma exchange e retorna os dados
    NÃO requer credenciais - usa API pública para listar markets
    
    Args:
        exchange_id: ID da exchange no MongoDB
        exchange_info: Informações da exchange (nome, ccxt_id, etc)
    
    Returns:
        Dictionary com tokens encontrados e metadados
    """
    try:
        logger.info(f"🔄 Updating tokens for {exchange_info['nome']}...")
        
        # Initialize exchange (SEM credenciais - API pública)
        exchange_class = getattr(ccxt, exchange_info['ccxt_id'])
        exchange = exchange_class({
            'enableRateLimit': True,
            'timeout': 30000,
            'options': {'defaultType': 'spot'}
        })
        
        # Load all markets
        logger.info(f"📥 Loading markets from {exchange_info['nome']}...")
        markets = exchange.load_markets()
        
        # Process tokens by quote currency
        tokens_by_quote = {
            'USDT': [],
            'USD': [],
            'USDC': [],
            'BUSD': [],
            'BRL': []
        }
        
        processed_bases = set()
        total_processed = 0
        
        for symbol, market in markets.items():
            # Skip inactive markets
            if not market.get('active', True):
                continue
            
            # Skip invalid symbols
            if '/' not in symbol:
                continue
            
            base, quote = symbol.split('/')
            
            # Only process supported quote currencies
            if quote not in tokens_by_quote:
                continue
            
            # Skip if already processed this base for this quote
            cache_key = f"{base}_{quote}"
            if cache_key in processed_bases:
                continue
            
            processed_bases.add(cache_key)
            
            # Add token info
            token_data = {
                'symbol': base,
                'pair': symbol,
                'quote': quote,
                'base_precision': market.get('precision', {}).get('base'),
                'quote_precision': market.get('precision', {}).get('quote'),
                'min_amount': market.get('limits', {}).get('amount', {}).get('min'),
                'max_amount': market.get('limits', {}).get('amount', {}).get('max'),
                'min_cost': market.get('limits', {}).get('cost', {}).get('min')
            }
            
            tokens_by_quote[quote].append(token_data)
            total_processed += 1
            
            # Log progress every 100 tokens
            if total_processed % 100 == 0:
                logger.info(f"   Processed {total_processed} tokens...")
        
        # Sort tokens by symbol
        for quote in tokens_by_quote:
            tokens_by_quote[quote].sort(key=lambda x: x['symbol'])
        
        # Calculate totals
        totals = {quote: len(tokens) for quote, tokens in tokens_by_quote.items()}
        
        result = {
            'exchange_id': str(exchange_id),
            'exchange_name': exchange_info['nome'],
            'exchange_ccxt_id': exchange_info['ccxt_id'],
            'tokens_by_quote': tokens_by_quote,
            'totals': totals,
            'total_tokens': total_processed,
            'updated_at': datetime.utcnow(),
            'update_status': 'success'
        }
        
        logger.info(f"✅ {exchange_info['nome']}: {total_processed} tokens found")
        for quote, count in totals.items():
            if count > 0:
                logger.info(f"   {quote}: {count} tokens")
        
        return result
        
    except ccxt.AuthenticationError as e:
        logger.error(f"❌ Authentication error for {exchange_info['nome']}: {str(e)}")
        return {
            'exchange_id': str(exchange_id),
            'exchange_name': exchange_info['nome'],
            'exchange_ccxt_id': exchange_info['ccxt_id'],
            'tokens_by_quote': {},
            'totals': {},
            'total_tokens': 0,
            'updated_at': datetime.utcnow(),
            'update_status': 'auth_error',
            'error': str(e)
        }
        
    except Exception as e:
        logger.error(f"❌ Error updating {exchange_info['nome']}: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'exchange_id': str(exchange_id),
            'exchange_name': exchange_info['nome'],
            'exchange_ccxt_id': exchange_info['ccxt_id'],
            'tokens_by_quote': {},
            'totals': {},
            'total_tokens': 0,
            'updated_at': datetime.utcnow(),
            'update_status': 'error',
            'error': str(e)
        }


def update_all_exchange_tokens():
    """
    Atualiza tokens de TODAS as exchanges ativas no sistema
    NÃO precisa de credenciais - usa API pública
    Cada exchange é atualizada UMA VEZ (universal para todos os usuários)
    """
    logger.info("=" * 80)
    logger.info("🚀 STARTING EXCHANGE TOKENS UPDATE JOB")
    logger.info(f"⏰ Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    logger.info("=" * 80)
    
    try:
        db = get_database()
        
        exchanges_collection = db.exchanges
        tokens_exchanges_collection = db.tokens_exchanges
        
        # Find all ACTIVE exchanges (no need for user exchanges)
        all_exchanges = list(exchanges_collection.find({'is_active': True}))
        
        if not all_exchanges:
            logger.warning("⚠️  No active exchanges found")
            return {
                'success': True,
                'total_exchanges': 0,
                'successful_updates': 0,
                'failed_updates': 0
            }
        
        logger.info(f"� Found {len(all_exchanges)} active exchanges to update")
        logger.info("")
        
        total_exchanges = len(all_exchanges)
        successful_updates = 0
        failed_updates = 0
        
        for exchange_info in all_exchanges:
            exchange_id = str(exchange_info['_id'])
            
            # Update tokens for this exchange (no credentials needed!)
            result = update_exchange_tokens(
                exchange_id=exchange_id,
                exchange_info=exchange_info
            )
            
            # Save to MongoDB (upsert) - ONE entry per exchange
            tokens_exchanges_collection.update_one(
                {
                    'exchange_id': exchange_id
                },
                {
                    '$set': result
                },
                upsert=True
            )
            
            if result['update_status'] == 'success':
                successful_updates += 1
                logger.info(f"💾 Saved to MongoDB: {result['total_tokens']} tokens")
            else:
                failed_updates += 1
                logger.error(f"❌ Failed to update: {result.get('error', 'Unknown error')}")
            
            logger.info("")  # Empty line between exchanges
        
        # Summary
        logger.info("\n" + "=" * 80)
        logger.info("📊 UPDATE SUMMARY")
        logger.info(f"   Total exchanges processed: {total_exchanges}")
        logger.info(f"   ✅ Successful: {successful_updates}")
        logger.info(f"   ❌ Failed: {failed_updates}")
        logger.info("=" * 80)
        
        return {
            'success': True,
            'total_exchanges': total_exchanges,
            'successful_updates': successful_updates,
            'failed_updates': failed_updates
        }
        
    except Exception as e:
        logger.error(f"❌ Fatal error in update job: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e)
        }


if __name__ == '__main__':
    """
    Executa atualização manual
    """
    print("🚀 Starting manual exchange tokens update...")
    result = update_all_exchange_tokens()
    
    if result.get('success'):
        print(f"\n✅ Update completed successfully!")
        print(f"   Processed: {result['total_exchanges']} exchanges")
        print(f"   Success: {result['successful_updates']}")
        print(f"   Failed: {result['failed_updates']}")
    else:
        print(f"\n❌ Update failed: {result.get('error')}")
        sys.exit(1)
