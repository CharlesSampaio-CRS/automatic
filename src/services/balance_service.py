"""
Balance Service - Fetch balances from multiple exchanges in parallel
Optimized for performance with concurrent execution
"""

import ccxt
from typing import Dict, List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
import time

from src.security.encryption import get_encryption_service


class BalanceCache:
    """Simple in-memory cache for balance data"""
    
    def __init__(self, ttl_seconds: int = 120):
        """
        Initialize cache
        
        Args:
            ttl_seconds: Time to live for cached data (default 2 minutes)
        """
        self.cache = {}
        self.ttl_seconds = ttl_seconds
    
    def get(self, key: str) -> Tuple[bool, any]:
        """
        Get cached data if still valid
        
        Returns:
            Tuple of (is_valid, data)
        """
        if key not in self.cache:
            return False, None
        
        cached_data, timestamp = self.cache[key]
        
        # Check if cache is still valid
        if datetime.utcnow() - timestamp < timedelta(seconds=self.ttl_seconds):
            return True, cached_data
        
        # Cache expired, remove it
        del self.cache[key]
        return False, None
    
    def set(self, key: str, data: any):
        """Set cache data with current timestamp"""
        self.cache[key] = (data, datetime.utcnow())
    
    def clear(self, key: str = None):
        """Clear cache for specific key or all cache"""
        if key:
            if key in self.cache:
                del self.cache[key]
        else:
            self.cache.clear()


# Global cache instance
_balance_cache = BalanceCache(ttl_seconds=120)  # 2 minutes cache


class BalanceService:
    """Service to fetch and aggregate balances from multiple exchanges"""
    
    def __init__(self, db):
        """Initialize service with database connection"""
        self.db = db
        self.encryption_service = get_encryption_service()
    
    def fetch_single_exchange_balance(self, link: Dict, exchange_info: Dict) -> Dict:
        """
        Fetch balance from a single exchange
        
        Args:
            link: User exchange link document
            exchange_info: Exchange information document
            
        Returns:
            Dict with balance data or error
        """
        result = {
            'exchange_id': str(exchange_info['_id']),
            'exchange_name': exchange_info['nome'],
            'exchange_icon': exchange_info['icon'],
            'success': False,
            'error': None,
            'balances': {},
            'total_usd': 0.0,
            'fetch_time': None
        }
        
        try:
            start_time = time.time()
            
            # Decrypt credentials
            decrypted = self.encryption_service.decrypt_credentials({
                'api_key': link['api_key_encrypted'],
                'api_secret': link['api_secret_encrypted'],
                'passphrase': link.get('passphrase_encrypted')
            })
            
            # Create exchange instance
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
            
            # Fetch balance
            balance_data = exchange.fetch_balance()
            
            # Process balances (only non-zero free + used)
            processed_balances = {}
            total_usd = 0.0
            
            for currency, amounts in balance_data.items():
                if currency in ['info', 'free', 'used', 'total', 'timestamp', 'datetime']:
                    continue
                
                if isinstance(amounts, dict):
                    free = float(amounts.get('free', 0))
                    used = float(amounts.get('used', 0))
                    total = float(amounts.get('total', 0))
                    
                    if total > 0:
                        processed_balances[currency] = {
                            'free': free,
                            'used': used,
                            'total': total,
                            'usd_value': 0.0  # Will be calculated later with price feed
                        }
            
            fetch_time = time.time() - start_time
            
            result.update({
                'success': True,
                'balances': processed_balances,
                'total_usd': total_usd,
                'fetch_time': round(fetch_time, 3)
            })
            
        except ccxt.AuthenticationError as e:
            result['error'] = f"Authentication failed: {str(e)}"
        except ccxt.ExchangeError as e:
            result['error'] = f"Exchange error: {str(e)}"
        except Exception as e:
            result['error'] = f"Error: {str(e)}"
        
        return result
    
    def fetch_all_balances(self, user_id: str, use_cache: bool = True) -> Dict:
        """
        Fetch balances from all linked exchanges in parallel
        
        Args:
            user_id: User ID
            use_cache: Whether to use cached data
            
        Returns:
            Dict with aggregated balance data
        """
        # Check cache first
        if use_cache:
            cache_key = f"balances_{user_id}"
            is_valid, cached_data = _balance_cache.get(cache_key)
            if is_valid:
                cached_data['from_cache'] = True
                return cached_data
        
        start_time = time.time()
        
        # Get user's linked exchanges
        user_links = list(self.db.user_exchanges.find({
            'user_id': user_id,
            'is_active': True
        }))
        
        if not user_links:
            return {
                'success': True,
                'user_id': user_id,
                'exchanges': [],
                'total_exchanges': 0,
                'total_usd': 0.0,
                'total_brl': 0.0,
                'tokens_summary': {},
                'fetch_time': 0,
                'from_cache': False,
                'timestamp': datetime.utcnow().isoformat()
            }
        
        # Get exchange info for all links
        exchange_ids = [link['exchange_id'] for link in user_links]
        exchanges_info = {
            ex['_id']: ex
            for ex in self.db.exchanges.find({'_id': {'$in': exchange_ids}})
        }
        
        # Fetch balances in parallel
        exchange_results = []
        
        with ThreadPoolExecutor(max_workers=min(len(user_links), 10)) as executor:
            futures = {
                executor.submit(
                    self.fetch_single_exchange_balance,
                    link,
                    exchanges_info[link['exchange_id']]
                ): link
                for link in user_links
            }
            
            for future in as_completed(futures):
                try:
                    result = future.result()
                    exchange_results.append(result)
                except Exception as e:
                    link = futures[future]
                    exchange_info = exchanges_info[link['exchange_id']]
                    exchange_results.append({
                        'exchange_id': str(exchange_info['_id']),
                        'exchange_name': exchange_info['nome'],
                        'exchange_icon': exchange_info['icon'],
                        'success': False,
                        'error': f"Unexpected error: {str(e)}",
                        'balances': {},
                        'total_usd': 0.0
                    })
        
        # Aggregate balances by token
        tokens_summary = {}
        total_usd = 0.0
        
        for exchange_result in exchange_results:
            if exchange_result['success']:
                for currency, amounts in exchange_result['balances'].items():
                    if currency not in tokens_summary:
                        tokens_summary[currency] = {
                            'total': 0.0,
                            'free': 0.0,
                            'used': 0.0,
                            'usd_value': 0.0,
                            'exchanges': []
                        }
                    
                    tokens_summary[currency]['total'] += amounts['total']
                    tokens_summary[currency]['free'] += amounts['free']
                    tokens_summary[currency]['used'] += amounts['used']
                    tokens_summary[currency]['exchanges'].append({
                        'name': exchange_result['exchange_name'],
                        'amount': amounts['total']
                    })
        
        # Sort tokens by total amount (descending)
        tokens_summary = dict(sorted(
            tokens_summary.items(),
            key=lambda x: x[1]['total'],
            reverse=True
        ))
        
        # TODO: Add price feed integration for USD values
        # For now, we'll use 0 for USD values
        # This will be enhanced with a price feed service
        
        total_fetch_time = time.time() - start_time
        
        result = {
            'success': True,
            'user_id': user_id,
            'exchanges': exchange_results,
            'total_exchanges': len(user_links),
            'successful_fetches': sum(1 for r in exchange_results if r['success']),
            'failed_fetches': sum(1 for r in exchange_results if not r['success']),
            'total_usd': total_usd,
            'total_brl': 0.0,  # TODO: Add BRL conversion
            'tokens_summary': tokens_summary,
            'total_unique_tokens': len(tokens_summary),
            'fetch_time': round(total_fetch_time, 3),
            'from_cache': False,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Cache the result
        if use_cache:
            cache_key = f"balances_{user_id}"
            _balance_cache.set(cache_key, result)
        
        return result
    
    def clear_cache(self, user_id: str = None):
        """Clear cache for specific user or all cache"""
        if user_id:
            cache_key = f"balances_{user_id}"
            _balance_cache.clear(cache_key)
        else:
            _balance_cache.clear()


def get_balance_service(db):
    """Factory function to create BalanceService instance"""
    return BalanceService(db)
