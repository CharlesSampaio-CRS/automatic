"""
Order Execution Service - Execute trading orders via CCXT
Supports market and limit orders with dry-run mode for testing
"""

import ccxt
from typing import Dict, Optional
from datetime import datetime
from src.security.encryption import get_encryption_service
from src.utils.logger import get_logger


# Initialize logger
logger = get_logger(__name__)


class OrderExecutionService:
    """Service to execute trading orders on exchanges"""
    
    def __init__(self, db, dry_run: bool = False):
        """
        Initialize order execution service
        
        Args:
            db: MongoDB database connection
            dry_run: If True, simulates orders without executing (for testing)
        """
        self.db = db
        self.dry_run = dry_run
        self.encryption_service = get_encryption_service()
        
        if dry_run:
            logger.warning("⚠️  DRY-RUN MODE ENABLED - Orders will be simulated, not executed")
    
    def _get_exchange_instance(self, user_id: str, exchange_id: str):
        """
        Get authenticated CCXT exchange instance
        
        Args:
            user_id: User ID
            exchange_id: Exchange MongoDB ObjectId
            
        Returns:
            CCXT exchange instance or None
        """
        try:
            # Get user's exchange credentials
            user_doc = self.db.user_exchanges.find_one({'user_id': user_id})
            
            if not user_doc or 'exchanges' not in user_doc:
                raise Exception(f"User {user_id} has no linked exchanges")
            
            # Find the specific exchange in the array
            ex_data = None
            for ex in user_doc['exchanges']:
                if str(ex['exchange_id']) == exchange_id and ex.get('is_active', True):
                    ex_data = ex
                    break
            
            if not ex_data:
                raise Exception(f"Exchange {exchange_id} not found or inactive for user {user_id}")
            
            # Get exchange info
            from bson import ObjectId
            exchange_info = self.db.exchanges.find_one({'_id': ObjectId(exchange_id)})
            
            if not exchange_info:
                raise Exception(f"Exchange info not found: {exchange_id}")
            
            # Decrypt credentials
            decrypted = self.encryption_service.decrypt_credentials({
                'api_key': ex_data['api_key_encrypted'],
                'api_secret': ex_data['api_secret_encrypted'],
                'passphrase': ex_data.get('passphrase_encrypted')
            })
            
            # Create CCXT exchange instance
            exchange_class = getattr(ccxt, exchange_info['ccxt_id'])
            config = {
                'apiKey': decrypted['api_key'],
                'secret': decrypted['api_secret'],
                'enableRateLimit': True,
                'options': {'defaultType': 'spot'}
            }
            
            if decrypted.get('passphrase'):
                config['password'] = decrypted['passphrase']
            
            exchange = exchange_class(config)
            
            return exchange
            
        except Exception as e:
            logger.error(f"Error creating exchange instance: {e}")
            raise
    
    def execute_market_sell(
        self,
        user_id: str,
        exchange_id: str,
        token: str,
        amount: float,
        quote_currency: str = 'USDT'
    ) -> Dict:
        """
        Execute a market sell order (sell at current market price)
        
        Args:
            user_id: User ID
            exchange_id: Exchange MongoDB ObjectId
            token: Token to sell (e.g., 'BTC')
            amount: Amount to sell
            quote_currency: Quote currency (default: USDT)
            
        Returns:
            Dict with order result
        """
        try:
            symbol = f"{token}/{quote_currency}"
            
            if self.dry_run:
                logger.info(f"🧪 DRY-RUN: Would execute MARKET SELL: {amount} {token} ({symbol})")
                return {
                    'success': True,
                    'dry_run': True,
                    'order': {
                        'id': f'DRY-{datetime.utcnow().timestamp()}',
                        'symbol': symbol,
                        'type': 'market',
                        'side': 'sell',
                        'amount': amount,
                        'price': None,
                        'status': 'simulated',
                        'timestamp': datetime.utcnow().isoformat()
                    }
                }
            
            # Get exchange instance
            exchange = self._get_exchange_instance(user_id, exchange_id)
            
            # Execute market sell order
            logger.info(f"🔴 Executing MARKET SELL: {amount} {token} ({symbol})")
            order = exchange.create_market_sell_order(symbol, amount)
            
            logger.info(f"✅ Order executed: {order['id']} - Status: {order['status']}")
            
            return {
                'success': True,
                'dry_run': False,
                'order': {
                    'id': order['id'],
                    'symbol': order['symbol'],
                    'type': order['type'],
                    'side': order['side'],
                    'amount': order['amount'],
                    'price': order.get('price'),
                    'average': order.get('average'),
                    'filled': order.get('filled'),
                    'remaining': order.get('remaining'),
                    'cost': order.get('cost'),
                    'status': order['status'],
                    'timestamp': order.get('timestamp'),
                    'datetime': order.get('datetime'),
                    'fee': order.get('fee')
                }
            }
            
        except ccxt.InsufficientFunds as e:
            logger.error(f"Insufficient funds: {e}")
            return {
                'success': False,
                'error': 'Insufficient funds',
                'details': str(e)
            }
        except ccxt.InvalidOrder as e:
            logger.error(f"Invalid order: {e}")
            return {
                'success': False,
                'error': 'Invalid order',
                'details': str(e)
            }
        except Exception as e:
            logger.error(f"Error executing market sell: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def execute_market_buy(
        self,
        user_id: str,
        exchange_id: str,
        token: str,
        amount: float,
        quote_currency: str = 'USDT'
    ) -> Dict:
        """
        Execute a market buy order (buy at current market price)
        
        Args:
            user_id: User ID
            exchange_id: Exchange MongoDB ObjectId
            token: Token to buy (e.g., 'BTC')
            amount: Amount to buy
            quote_currency: Quote currency (default: USDT)
            
        Returns:
            Dict with order result
        """
        try:
            symbol = f"{token}/{quote_currency}"
            
            if self.dry_run:
                logger.info(f"🧪 DRY-RUN: Would execute MARKET BUY: {amount} {token} ({symbol})")
                return {
                    'success': True,
                    'dry_run': True,
                    'order': {
                        'id': f'DRY-{datetime.utcnow().timestamp()}',
                        'symbol': symbol,
                        'type': 'market',
                        'side': 'buy',
                        'amount': amount,
                        'price': None,
                        'status': 'simulated',
                        'timestamp': datetime.utcnow().isoformat()
                    }
                }
            
            # Get exchange instance
            exchange = self._get_exchange_instance(user_id, exchange_id)
            
            # Execute market buy order
            logger.info(f"🟢 Executing MARKET BUY: {amount} {token} ({symbol})")
            order = exchange.create_market_buy_order(symbol, amount)
            
            logger.info(f"✅ Order executed: {order['id']} - Status: {order['status']}")
            
            return {
                'success': True,
                'dry_run': False,
                'order': {
                    'id': order['id'],
                    'symbol': order['symbol'],
                    'type': order['type'],
                    'side': order['side'],
                    'amount': order['amount'],
                    'price': order.get('price'),
                    'average': order.get('average'),
                    'filled': order.get('filled'),
                    'remaining': order.get('remaining'),
                    'cost': order.get('cost'),
                    'status': order['status'],
                    'timestamp': order.get('timestamp'),
                    'datetime': order.get('datetime'),
                    'fee': order.get('fee')
                }
            }
            
        except ccxt.InsufficientFunds as e:
            logger.error(f"Insufficient funds: {e}")
            return {
                'success': False,
                'error': 'Insufficient funds',
                'details': str(e)
            }
        except ccxt.InvalidOrder as e:
            logger.error(f"Invalid order: {e}")
            return {
                'success': False,
                'error': 'Invalid order',
                'details': str(e)
            }
        except Exception as e:
            logger.error(f"Error executing market buy: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def execute_limit_sell(
        self,
        user_id: str,
        exchange_id: str,
        token: str,
        amount: float,
        price: float,
        quote_currency: str = 'USDT'
    ) -> Dict:
        """
        Execute a limit sell order (sell only at specified price or better)
        
        Args:
            user_id: User ID
            exchange_id: Exchange MongoDB ObjectId
            token: Token to sell
            amount: Amount to sell
            price: Limit price
            quote_currency: Quote currency (default: USDT)
            
        Returns:
            Dict with order result
        """
        try:
            symbol = f"{token}/{quote_currency}"
            
            if self.dry_run:
                logger.info(f"🧪 DRY-RUN: Would execute LIMIT SELL: {amount} {token} at ${price} ({symbol})")
                return {
                    'success': True,
                    'dry_run': True,
                    'order': {
                        'id': f'DRY-{datetime.utcnow().timestamp()}',
                        'symbol': symbol,
                        'type': 'limit',
                        'side': 'sell',
                        'amount': amount,
                        'price': price,
                        'status': 'simulated',
                        'timestamp': datetime.utcnow().isoformat()
                    }
                }
            
            # Get exchange instance
            exchange = self._get_exchange_instance(user_id, exchange_id)
            
            # Execute limit sell order
            logger.info(f"🔴 Executing LIMIT SELL: {amount} {token} at ${price} ({symbol})")
            order = exchange.create_limit_sell_order(symbol, amount, price)
            
            logger.info(f"✅ Order placed: {order['id']} - Status: {order['status']}")
            
            return {
                'success': True,
                'dry_run': False,
                'order': {
                    'id': order['id'],
                    'symbol': order['symbol'],
                    'type': order['type'],
                    'side': order['side'],
                    'amount': order['amount'],
                    'price': order.get('price'),
                    'average': order.get('average'),
                    'filled': order.get('filled'),
                    'remaining': order.get('remaining'),
                    'cost': order.get('cost'),
                    'status': order['status'],
                    'timestamp': order.get('timestamp'),
                    'datetime': order.get('datetime'),
                    'fee': order.get('fee')
                }
            }
            
        except Exception as e:
            logger.error(f"Error executing limit sell: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def execute_limit_buy(
        self,
        user_id: str,
        exchange_id: str,
        token: str,
        amount: float,
        price: float,
        quote_currency: str = 'USDT'
    ) -> Dict:
        """
        Execute a limit buy order (buy only at specified price or better)
        
        Args:
            user_id: User ID
            exchange_id: Exchange MongoDB ObjectId
            token: Token to buy
            amount: Amount to buy
            price: Limit price
            quote_currency: Quote currency (default: USDT)
            
        Returns:
            Dict with order result
        """
        try:
            symbol = f"{token}/{quote_currency}"
            
            if self.dry_run:
                logger.info(f"🧪 DRY-RUN: Would execute LIMIT BUY: {amount} {token} at ${price} ({symbol})")
                return {
                    'success': True,
                    'dry_run': True,
                    'order': {
                        'id': f'DRY-{datetime.utcnow().timestamp()}',
                        'symbol': symbol,
                        'type': 'limit',
                        'side': 'buy',
                        'amount': amount,
                        'price': price,
                        'status': 'simulated',
                        'timestamp': datetime.utcnow().isoformat()
                    }
                }
            
            # Get exchange instance
            exchange = self._get_exchange_instance(user_id, exchange_id)
            
            # Execute limit buy order
            logger.info(f"🟢 Executing LIMIT BUY: {amount} {token} at ${price} ({symbol})")
            order = exchange.create_limit_buy_order(symbol, amount, price)
            
            logger.info(f"✅ Order placed: {order['id']} - Status: {order['status']}")
            
            return {
                'success': True,
                'dry_run': False,
                'order': {
                    'id': order['id'],
                    'symbol': order['symbol'],
                    'type': order['type'],
                    'side': order['side'],
                    'amount': order['amount'],
                    'price': order.get('price'),
                    'average': order.get('average'),
                    'filled': order.get('filled'),
                    'remaining': order.get('remaining'),
                    'cost': order.get('cost'),
                    'status': order['status'],
                    'timestamp': order.get('timestamp'),
                    'datetime': order.get('datetime'),
                    'fee': order.get('fee')
                }
            }
            
        except Exception as e:
            logger.error(f"Error executing limit buy: {e}")
            return {
                'success': False,
                'error': str(e)
            }


def get_order_execution_service(db, dry_run: bool = False):
    """Factory function to create OrderExecutionService instance"""
    return OrderExecutionService(db, dry_run=dry_run)
