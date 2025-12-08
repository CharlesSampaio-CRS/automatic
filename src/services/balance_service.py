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
from src.services.price_feed_service import get_price_feed_service
from src.utils.formatting import format_price, format_amount, format_usd, format_brl, format_rate


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
            
            # Fetch balance and tickers for prices
            balance_data = exchange.fetch_balance()
            
            # Fetch tickers to get current prices (USDT pairs)
            tickers = {}
            try:
                all_tickers = exchange.fetch_tickers()
                # Map ticker prices (prefer USDT pairs)
                for symbol, ticker in all_tickers.items():
                    if '/USDT' in symbol:
                        base = symbol.split('/')[0]
                        tickers[base] = ticker.get('last', 0) or ticker.get('close', 0) or 0
            except Exception as e:
                print(f"⚠️  Could not fetch tickers from {exchange_info['nome']}: {e}")
            
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
                        # Get price from ticker (already in USDT)
                        price_usd = 0.0
                        if currency == 'USDT':
                            price_usd = 1.0
                        elif currency in tickers:
                            price_usd = float(tickers[currency])
                        
                        value_usd = total * price_usd
                        total_usd += value_usd
                        
                        processed_balances[currency] = {
                            'total': total,
                            'price_usd': format_price(price_usd),
                            'value_usd': format_usd(value_usd)
                        }
            
            fetch_time = time.time() - start_time
            
            result.update({
                'success': True,
                'balances': processed_balances,
                'total_usd': format_usd(total_usd),
                'fetch_time': round(fetch_time, 3)
            })
            
        except ccxt.AuthenticationError as e:
            result['error'] = f"Authentication failed: {str(e)}"
        except ccxt.ExchangeError as e:
            result['error'] = f"Exchange error: {str(e)}"
        except Exception as e:
            result['error'] = f"Error: {str(e)}"
        
        return result
    
    def fetch_all_balances(self, user_id: str, use_cache: bool = True, include_brl: bool = False) -> Dict:
        """
        Fetch balances from all linked exchanges in parallel
        
        Args:
            user_id: User ID
            use_cache: Whether to use cached data
            include_brl: Whether to include BRL conversion
            
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
        
        # Get user document with array of exchanges (NOVA ESTRUTURA)
        user_doc = self.db.user_exchanges.find_one({'user_id': user_id})
        
        if not user_doc or 'exchanges' not in user_doc or not user_doc['exchanges']:
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
        
        # Filter only active exchanges from the array
        active_exchanges = [ex for ex in user_doc['exchanges'] if ex.get('is_active', True)]
        
        if not active_exchanges:
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
        
        # Get exchange info for all active exchanges
        exchange_ids = [ex['exchange_id'] for ex in active_exchanges]
        exchanges_info = {
            ex['_id']: ex
            for ex in self.db.exchanges.find({'_id': {'$in': exchange_ids}})
        }
        
        # Fetch balances in parallel
        exchange_results = []
        
        with ThreadPoolExecutor(max_workers=min(len(active_exchanges), 10)) as executor:
            futures = {
                executor.submit(
                    self.fetch_single_exchange_balance,
                    ex_data,  # Pass exchange data from array
                    exchanges_info[ex_data['exchange_id']]
                ): ex_data
                for ex_data in active_exchanges
            }
            
            for future in as_completed(futures):
                try:
                    result = future.result()
                    exchange_results.append(result)
                except Exception as e:
                    ex_data = futures[future]
                    exchange_info = exchanges_info[ex_data['exchange_id']]
                    exchange_results.append({
                        'exchange_id': str(exchange_info['_id']),
                        'exchange_name': exchange_info['nome'],
                        'exchange_icon': exchange_info['icon'],
                        'success': False,
                        'error': f"Unexpected error: {str(e)}",
                        'balances': {},
                        'total_usd': 0.0
                    })
        
        # Aggregate balances and prepare exchange summaries with tokens grouped
        exchanges_summary = []
        total_portfolio_usd = 0.0
        
        for exchange_result in exchange_results:
            # Prepare tokens for this exchange
            exchange_tokens = {}
            
            if exchange_result['success']:
                # Convert string back to float for calculations
                exchange_total = float(exchange_result.get('total_usd', '0.0'))
                total_portfolio_usd += exchange_total
                
                # Process tokens for this exchange
                for currency, amounts in exchange_result['balances'].items():
                    # Convert strings back to float for comparison
                    amount_val = amounts['total']
                    price_val = float(amounts.get('price_usd', '0.0'))
                    value_val = float(amounts.get('value_usd', '0.0'))
                    
                    token_info = {
                        'amount': format_amount(amount_val),
                        'price_usd': format_price(price_val),
                        'value_usd': format_usd(value_val)
                    }
                    
                    # Only include tokens with value > 0 or if price is unknown but has balance
                    if value_val > 0 or (price_val == 0 and amount_val > 0):
                        exchange_tokens[currency] = token_info
                
                # Sort tokens by value_usd (descending) - convert string to float for sorting
                exchange_tokens = dict(sorted(
                    exchange_tokens.items(),
                    key=lambda x: float(x[1]['value_usd']),
                    reverse=True
                ))
            
            # Add exchange summary with its tokens
            exchange_summary = {
                'exchange_id': exchange_result.get('exchange_id', ''),
                'name': exchange_result['exchange_name'],
                'success': exchange_result['success'],
                'total_usd': format_usd(exchange_total) if exchange_result['success'] else format_usd(0),
                'tokens': exchange_tokens
            }
            
            if not exchange_result['success']:
                exchange_summary['error'] = exchange_result.get('error')
            
            exchanges_summary.append(exchange_summary)
        
        total_fetch_time = time.time() - start_time
        
        result = {
            'user_id': user_id,
            'timestamp': datetime.utcnow().isoformat(),
            'summary': {
                'total_usd': format_usd(total_portfolio_usd),
                'exchanges_count': len([e for e in exchanges_summary if e['success']])
            },
            'exchanges': exchanges_summary,
            'meta': {
                'from_cache': False
            }
        }
        
        # Add BRL conversion if requested
        if include_brl:
            price_feed = get_price_feed_service()
            usd_brl_rate = price_feed.get_usd_brl_rate()
            
            result['summary']['total_brl'] = format_brl(total_portfolio_usd * usd_brl_rate)
            result['summary']['usd_brl_rate'] = format_rate(usd_brl_rate)
            
            # Add BRL to exchanges
            for exchange in result['exchanges']:
                exchange_usd = float(exchange.get('total_usd', '0'))
                if exchange_usd > 0:
                    exchange['total_brl'] = format_brl(exchange_usd * usd_brl_rate)
            
            # Add BRL to tokens in each exchange
            for exchange in result['exchanges']:
                if 'tokens' in exchange:
                    for token_info in exchange['tokens'].values():
                        token_usd = float(token_info.get('value_usd', '0'))
                        if token_usd > 0:
                            token_info['value_brl'] = format_brl(token_usd * usd_brl_rate)
        
        # ⚠️ HISTÓRICO NÃO É MAIS SALVO AUTOMATICAMENTE
        # Agora é salvo apenas pelo script hourly_balance_snapshot.py (a cada hora)
        # Isso evita poluir o histórico com múltiplas requisições do mesmo horário
        
        # Cache the result (after price enrichment)
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
