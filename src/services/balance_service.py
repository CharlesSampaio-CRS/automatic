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
from src.utils.logger import get_logger


# Initialize logger
logger = get_logger(__name__)


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
    
    def _calculate_price_changes(self, exchange, currency: str, current_price: float, quote_currency: str = 'USDT') -> Dict:
        """
        Calculate price changes for 1h, 4h, and 24h
        
        Args:
            exchange: CCXT exchange instance
            currency: Currency symbol (e.g., 'BTC')
            current_price: Current price in USD
            quote_currency: Quote currency to use for fetching data
            
        Returns:
            Dict with price changes: {'change_1h': float, 'change_4h': float, 'change_24h': float}
        """
        changes = {
            'change_1h': None,
            'change_4h': None,
            'change_24h': None
        }
        
        try:
            symbol = f"{currency}/{quote_currency}"
            
            # Try to get 24h change from ticker first (most reliable)
            try:
                ticker = exchange.fetch_ticker(symbol)
                if ticker.get('percentage') is not None:
                    changes['change_24h'] = round(float(ticker['percentage']), 2)
            except:
                pass
            
            # Try to get 1h and 4h changes from OHLCV
            try:
                # Fetch 1h data (last 2 candles)
                ohlcv_1h = exchange.fetch_ohlcv(symbol, timeframe='1h', limit=2)
                if len(ohlcv_1h) >= 2:
                    prev_close = ohlcv_1h[-2][4]  # Previous candle close
                    curr_close = ohlcv_1h[-1][4]  # Current candle close
                    
                    if prev_close > 0:
                        change_1h = ((curr_close - prev_close) / prev_close) * 100
                        changes['change_1h'] = round(change_1h, 2)
            except:
                pass
            
            try:
                # Fetch 4h data (last 2 candles)
                ohlcv_4h = exchange.fetch_ohlcv(symbol, timeframe='4h', limit=2)
                if len(ohlcv_4h) >= 2:
                    prev_close = ohlcv_4h[-2][4]
                    curr_close = ohlcv_4h[-1][4]
                    
                    if prev_close > 0:
                        change_4h = ((curr_close - prev_close) / prev_close) * 100
                        changes['change_4h'] = round(change_4h, 2)
            except:
                pass
                
        except Exception as e:
            logger.debug(f"Could not calculate price changes for {currency}: {e}")
        
        return changes
    
    def fetch_single_exchange_balance(self, link: Dict, exchange_info: Dict, include_changes: bool = False) -> Dict:
        """
        Fetch balance from a single exchange
        
        Args:
            link: User exchange link document
            exchange_info: Exchange information document
            include_changes: Whether to include price change percentages (1h, 4h, 24h)
            
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
            
            # Get list of currencies with balance > 0 first (optimization)
            currencies_with_balance = set()
            for currency, amounts in balance_data.items():
                if currency not in ['info', 'free', 'used', 'total', 'timestamp', 'datetime']:
                    if isinstance(amounts, dict):
                        total = float(amounts.get('total', 0))
                        if total > 0:
                            currencies_with_balance.add(currency)
            
            logger.debug(f"{exchange_info['nome']}: Found {len(currencies_with_balance)} currencies with balance")
            
            # Fetch tickers to get current prices (try multiple quote currencies)
            tickers = {}
            usd_brl_rate = None
            
            try:
                # OPTIMIZATION: For large exchanges (Binance, etc), only fetch tickers we need
                # This reduces API load and response time
                exchange_id_lower = exchange_info['ccxt_id'].lower()
                
                if exchange_id_lower in ['binance', 'binanceus'] and len(currencies_with_balance) > 0:
                    # Binance: fetch specific tickers for currencies we have
                    logger.debug(f"Binance optimization: fetching only needed tickers")
                    
                    for currency in currencies_with_balance:
                        if currency in ['USDT', 'USDC', 'USD']:
                            tickers[currency] = 1.0
                            continue
                        
                        # Try USDT pair first (most common on Binance)
                        for quote in ['USDT', 'BUSD', 'USDC', 'BTC', 'ETH']:
                            symbol = f"{currency}/{quote}"
                            try:
                                ticker = exchange.fetch_ticker(symbol)
                                price = ticker.get('last', 0) or ticker.get('close', 0) or 0
                                
                                if price and quote == 'USDT':
                                    tickers[currency] = float(price)
                                    break
                                elif price and quote == 'BUSD':
                                    tickers[currency] = float(price)
                                    break
                                elif price and quote == 'USDC':
                                    tickers[currency] = float(price)
                                    break
                                elif price and quote == 'BTC':
                                    # BTC pair - need BTC price in USD
                                    if 'BTC' not in tickers:
                                        try:
                                            btc_ticker = exchange.fetch_ticker('BTC/USDT')
                                            btc_price = btc_ticker.get('last', 0) or btc_ticker.get('close', 0) or 0
                                            tickers['BTC'] = float(btc_price)
                                        except:
                                            pass
                                    if 'BTC' in tickers and tickers['BTC'] > 0:
                                        tickers[currency] = float(price) * tickers['BTC']
                                        break
                                elif price and quote == 'ETH':
                                    # ETH pair - need ETH price in USD
                                    if 'ETH' not in tickers:
                                        try:
                                            eth_ticker = exchange.fetch_ticker('ETH/USDT')
                                            eth_price = eth_ticker.get('last', 0) or eth_ticker.get('close', 0) or 0
                                            tickers['ETH'] = float(eth_price)
                                        except:
                                            pass
                                    if 'ETH' in tickers and tickers['ETH'] > 0:
                                        tickers[currency] = float(price) * tickers['ETH']
                                        break
                            except:
                                continue
                else:
                    # Other exchanges: fetch all tickers (original method)
                    all_tickers = exchange.fetch_tickers()
                    
                    # Map ticker prices - try USDT, BRL, USD, USDC in order of preference
                    for symbol, ticker in all_tickers.items():
                        if '/' not in symbol:
                            continue
                        
                        base, quote = symbol.split('/')
                        price = ticker.get('last', 0) or ticker.get('close', 0) or 0
                        
                        if not price:
                            continue
                        
                        # Priority: USDT > USD > USDC (direct USD quotes)
                        if quote in ['USDT', 'USD', 'USDC']:
                            if base not in tickers:  # Only set if not already set
                                tickers[base] = float(price)
                        
                        # BRL pairs - need conversion to USD
                        elif quote == 'BRL':
                            if base not in tickers:  # Use BRL as fallback
                                # Get USD/BRL rate if not already fetched
                                if usd_brl_rate is None:
                                    try:
                                        price_feed = get_price_feed_service()
                                        usd_brl_rate = price_feed.get_usd_brl_rate()
                                    except:
                                        usd_brl_rate = 5.0  # Fallback rate
                                
                                # Convert BRL price to USD
                                tickers[base] = float(price) / usd_brl_rate
                
                logger.debug(f"Fetched {len(tickers)} ticker prices from {exchange_info['nome']}")
                
            except Exception as e:
                logger.warning(f"Could not fetch tickers from {exchange_info['nome']}: {e}")
            
            # Collect all tokens that need prices (for CoinGecko fallback)
            tokens_needing_prices = []
            
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
                        # Get price from ticker
                        price_usd = 0.0
                        
                        if currency == 'USDT' or currency == 'USDC':
                            price_usd = 1.0
                        elif currency == 'BRL':
                            # BRL needs conversion
                            if usd_brl_rate is None:
                                try:
                                    price_feed = get_price_feed_service()
                                    usd_brl_rate = price_feed.get_usd_brl_rate()
                                except:
                                    usd_brl_rate = 5.0
                            price_usd = 1.0 / usd_brl_rate
                        elif currency in tickers:
                            price_usd = float(tickers[currency])
                        else:
                            # No ticker found - will use CoinGecko fallback
                            tokens_needing_prices.append(currency)
                        
                        value_usd = total * price_usd
                        total_usd += value_usd
                        
                        # Build balance data
                        balance_data_entry = {
                            'total': total,
                            'price_usd': format_price(price_usd),
                            'value_usd': format_usd(value_usd)
                        }
                        
                        # Add price changes if requested and price was found
                        if include_changes and price_usd > 0 and currency not in ['USDT', 'USDC', 'BRL']:
                            # Determine quote currency used for this token
                            quote_currency = 'USDT'
                            if exchange_info.get('nome', '').lower() == 'novadax':
                                quote_currency = 'BRL'
                            
                            changes = self._calculate_price_changes(exchange, currency, price_usd, quote_currency)
                            
                            # Only add non-null changes
                            if changes['change_1h'] is not None:
                                balance_data_entry['change_1h'] = changes['change_1h']
                            if changes['change_4h'] is not None:
                                balance_data_entry['change_4h'] = changes['change_4h']
                            if changes['change_24h'] is not None:
                                balance_data_entry['change_24h'] = changes['change_24h']
                        
                        processed_balances[currency] = balance_data_entry
            
            # FALLBACK: Use CoinGecko for tokens without prices
            if tokens_needing_prices:
                try:
                    logger.info(f"Fetching prices from CoinGecko for {len(tokens_needing_prices)} tokens: {tokens_needing_prices}")
                    price_feed = get_price_feed_service()
                    coingecko_prices = price_feed.fetch_prices_batch(tokens_needing_prices)
                    
                    # Update balances with CoinGecko prices
                    for currency in tokens_needing_prices:
                        if currency in processed_balances and currency in coingecko_prices:
                            cg_price = coingecko_prices[currency]
                            total_amount = processed_balances[currency]['total']
                            new_value_usd = total_amount * cg_price
                            
                            # Update with CoinGecko price
                            processed_balances[currency]['price_usd'] = format_price(cg_price)
                            processed_balances[currency]['value_usd'] = format_usd(new_value_usd)
                            
                            # Update total
                            old_value = float(processed_balances[currency]['value_usd'])
                            total_usd = total_usd - old_value + new_value_usd
                            
                            logger.debug(f"Updated {currency} price from CoinGecko: ${cg_price}")
                
                except Exception as e:
                    logger.warning(f"Could not fetch fallback prices from CoinGecko: {e}")
            
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
    
    def fetch_all_balances(self, user_id: str, use_cache: bool = True, include_brl: bool = False, include_changes: bool = False) -> Dict:
        """
        Fetch balances from all linked exchanges in parallel
        
        Args:
            user_id: User ID
            use_cache: Whether to use cached data
            include_brl: Whether to include BRL conversion
            include_changes: Whether to include price changes (1h, 4h, 24h)
            
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
                    exchanges_info[ex_data['exchange_id']],
                    include_changes  # Pass include_changes parameter
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
