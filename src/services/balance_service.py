"""
Balance Service - Fetch balances from multiple exchanges in parallel
Optimized for performance with concurrent execution
"""

import os
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
_balance_cache = BalanceCache(ttl_seconds=300)  # 5 minutes cache (optimized for performance)


class BalanceService:
    """Service to fetch and aggregate balances from multiple exchanges"""
    
    def __init__(self, db):
        """Initialize service with database connection"""
        self.db = db
        self.encryption_service = get_encryption_service()
    
    def _calculate_price_changes(self, exchange, currency: str, current_price: float, quote_currency: str = 'USDT') -> Dict:
        """
        Calculate price changes for 24h (OPTIMIZED - removed 1h/4h for performance)
        
        Args:
            exchange: CCXT exchange instance
            currency: Currency symbol (e.g., 'BTC')
            current_price: Current price in USD
            quote_currency: Quote currency to use for fetching data
            
        Returns:
            Dict with price changes: {'change_24h': float}
        """
        changes = {
            'change_24h': None
        }
        
        try:
            symbol = f"{currency}/{quote_currency}"
            
            # Get 24h change from ticker (most efficient - single call)
            try:
                ticker = exchange.fetch_ticker(symbol)
                if ticker.get('percentage') is not None:
                    changes['change_24h'] = round(float(ticker['percentage']), 2)
            except:
                pass
                
        except Exception as e:
            logger.debug(f"Could not calculate price changes for {currency}: {e}")
        
        return changes
    
    def fetch_exchange_total_only(self, link: Dict, exchange_info: Dict) -> Dict:
        """
        Fetch ONLY total balance from exchange (ultra-fast for listing)
        
        Args:
            link: User exchange link document
            exchange_info: Exchange information document
            
        Returns:
            Dict with only total_usd (no token details)
        """
        result = {
            'exchange_id': str(exchange_info['_id']),
            'exchange_name': exchange_info['nome'],
            'exchange_icon': exchange_info['icon'],
            'success': False,
            'error': None,
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
                'timeout': 10000,
                'options': {'defaultType': 'spot'}
            }
            
            # Bybit specific configuration
            if exchange_info['ccxt_id'].lower() == 'bybit':
                config['options'].update({
                    'defaultType': 'spot',
                    'accountType': 'unified',
                    'fetchBalance': {'type': 'spot'}
                })
                proxy_url = os.getenv('BYBIT_PROXY_URL')
                if proxy_url:
                    config['proxies'] = {'http': proxy_url, 'https': proxy_url}
            
            if decrypted.get('passphrase'):
                config['password'] = decrypted['passphrase']
            
            exchange = exchange_class(config)
            
            # Fetch balance (structure with amounts)
            balance_data = exchange.fetch_balance()
            
            # Get list of currencies with balance > 0
            currencies_with_balance = {}
            for currency, amounts in balance_data.items():
                if currency not in ['info', 'free', 'used', 'total', 'timestamp', 'datetime']:
                    if isinstance(amounts, dict):
                        total = float(amounts.get('total', 0))
                        if total > 0:
                            currencies_with_balance[currency] = total
            
            logger.debug(f"{exchange_info['nome']}: Found {len(currencies_with_balance)} currencies with balance")
            
            # Calculate total using same logic as fetch_single_exchange_balance (ACCURATE)
            total_usd = 0.0
            tickers = {}
            usd_brl_rate = None
            
            # Fetch tickers from exchange (MOST ACCURATE - real-time prices)
            try:
                if len(currencies_with_balance) > 0:
                    logger.debug(f"{exchange_info['nome']}: Fetching only {len(currencies_with_balance)} needed tickers")
                    
                    for currency in list(currencies_with_balance.keys()):
                        # Stablecoins don't need price lookup
                        if currency in ['USDT', 'USDC', 'USD', 'BUSD']:
                            tickers[currency] = 1.0
                            continue
                        
                        # Try common quote currencies in order of preference
                        # NovaDAX: Try BRL first (it's a Brazilian exchange)
                        if exchange_info.get('nome', '').lower() == 'novadax':
                            quote_currencies = ['BRL', 'USDT', 'USDC', 'USD', 'BUSD', 'BTC', 'ETH']
                        else:
                            quote_currencies = ['USDT', 'USDC', 'USD', 'BUSD', 'BRL', 'BTC', 'ETH']
                        
                        for quote in quote_currencies:
                            symbol = f"{currency}/{quote}"
                            try:
                                ticker = exchange.fetch_ticker(symbol)
                                price = ticker.get('last', 0) or ticker.get('close', 0) or 0
                                
                                if not price:
                                    continue
                                
                                # Direct USD quotes (USDT, USDC, USD, BUSD)
                                if quote in ['USDT', 'USDC', 'USD', 'BUSD']:
                                    tickers[currency] = float(price)
                                    break
                                
                                # BRL pairs - need conversion to USD
                                elif quote == 'BRL':
                                    if usd_brl_rate is None:
                                        try:
                                            price_feed = get_price_feed_service()
                                            usd_brl_rate = price_feed.get_usd_brl_rate()
                                        except:
                                            usd_brl_rate = 5.0  # Fallback rate
                                    tickers[currency] = float(price) / usd_brl_rate
                                    break
                                
                                # BTC pair - need BTC price in USD
                                elif quote == 'BTC':
                                    if 'BTC' not in tickers:
                                        try:
                                            btc_ticker = exchange.fetch_ticker('BTC/USDT')
                                            btc_price = btc_ticker.get('last', 0) or btc_ticker.get('close', 0) or 0
                                            if btc_price:
                                                tickers['BTC'] = float(btc_price)
                                        except:
                                            pass
                                    if 'BTC' in tickers and tickers['BTC'] > 0:
                                        tickers[currency] = float(price) * tickers['BTC']
                                        break
                                
                                # ETH pair - need ETH price in USD
                                elif quote == 'ETH':
                                    if 'ETH' not in tickers:
                                        try:
                                            eth_ticker = exchange.fetch_ticker('ETH/USDT')
                                            eth_price = eth_ticker.get('last', 0) or eth_ticker.get('close', 0) or 0
                                            if eth_price:
                                                tickers['ETH'] = float(eth_price)
                                        except:
                                            pass
                                    if 'ETH' in tickers and tickers['ETH'] > 0:
                                        tickers[currency] = float(price) * tickers['ETH']
                                        break
                            except:
                                continue  # Try next quote currency
                
                logger.debug(f"Fetched {len(tickers)} ticker prices from {exchange_info['nome']}")
                
            except Exception as e:
                logger.warning(f"Could not fetch tickers from {exchange_info['nome']}: {e}")
            
            # Collect tokens that need CoinGecko fallback
            tokens_needing_prices = []
            
            # Calculate total with tickers
            for currency, amount in currencies_with_balance.items():
                if currency in tickers:
                    price_usd = tickers[currency]
                    value_usd = amount * price_usd
                    total_usd += value_usd
                    logger.debug(f"  {currency}: {amount:.4f} × ${price_usd:.6f} = ${value_usd:.2f}")
                else:
                    # No ticker found - will use CoinGecko fallback
                    tokens_needing_prices.append(currency)
            
            # FALLBACK: Use CoinGecko for tokens without tickers
            if tokens_needing_prices:
                # Filter out fiat currencies (BRL, EUR, etc) - they shouldn't go to CoinGecko
                fiat_currencies = ['BRL', 'USD', 'EUR', 'GBP', 'JPY', 'CNY', 'ARS', 'MXN']
                tokens_for_coingecko = [t for t in tokens_needing_prices if t not in fiat_currencies]
                
                if tokens_for_coingecko:
                    try:
                        logger.info(f"Fetching prices from CoinGecko for {len(tokens_for_coingecko)} tokens: {tokens_for_coingecko}")
                        price_feed = get_price_feed_service()
                        coingecko_prices = price_feed.fetch_prices_batch(tokens_for_coingecko)
                        
                        for currency in tokens_for_coingecko:
                            if currency in coingecko_prices and currency in currencies_with_balance:
                                cg_price = coingecko_prices[currency]
                                amount = currencies_with_balance[currency]
                                value_usd = amount * cg_price
                                total_usd += value_usd
                                logger.debug(f"  {currency}: {amount:.4f} × ${cg_price:.6f} = ${value_usd:.2f} (CoinGecko)")
                        
                    except Exception as e:
                        logger.warning(f"Could not fetch fallback prices from CoinGecko: {e}")
            
            logger.info(f"📊 {exchange_info['nome']}: Total = ${total_usd:.2f}")
            
            fetch_time = time.time() - start_time
            
            result.update({
                'success': True,
                'total_usd': format_usd(total_usd),
                'fetch_time': round(fetch_time, 3),
                'token_count': len(currencies_with_balance)  # Number of tokens found
            })
            
        except Exception as e:
            error_msg = str(e)
            if '403' in error_msg and 'CloudFront' in error_msg:
                result['error'] = f"🌍 Geo-blocked"
                logger.error(f"🌍 {exchange_info['nome']}: GEO-BLOCKED")
            else:
                result['error'] = f"Error: {error_msg[:100]}"
                logger.error(f"❌ {exchange_info['nome']}: {error_msg[:100]}")
        
        return result
    
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
                'timeout': 10000,  # 10 second timeout to prevent hanging
                'options': {'defaultType': 'spot'}
            }
            
            # Bybit specific configuration for Unified Trading Account
            if exchange_info['ccxt_id'].lower() == 'bybit':
                config['options'].update({
                    'defaultType': 'spot',
                    'accountType': 'unified',  # Use unified trading account
                    'fetchBalance': {
                        'type': 'spot'  # Explicitly fetch spot balances
                    }
                })
                # Add proxy settings to bypass geo-blocking (if PROXY_URL is set)
                proxy_url = os.getenv('BYBIT_PROXY_URL')
                if proxy_url:
                    config['proxies'] = {
                        'http': proxy_url,
                        'https': proxy_url
                    }
                    logger.debug(f"Bybit: Using proxy to bypass geo-restrictions")
                
                logger.debug("Bybit: Using unified account configuration for spot trading")
            
            if decrypted.get('passphrase'):
                config['password'] = decrypted['passphrase']
            
            exchange = exchange_class(config)
            
            # Fetch balance and tickers for prices
            balance_data = exchange.fetch_balance()
            
            # DEBUG: Log raw balance structure for Bybit
            if exchange_info['ccxt_id'].lower() == 'bybit':
                logger.info(f"🔍 Bybit raw balance keys: {list(balance_data.keys())[:10]}")
                if 'info' in balance_data:
                    logger.debug(f"Bybit balance.info keys: {list(balance_data['info'].keys()) if isinstance(balance_data['info'], dict) else 'not a dict'}")
            
            # Get list of currencies with balance > 0 first (optimization)
            currencies_with_balance = set()
            for currency, amounts in balance_data.items():
                if currency not in ['info', 'free', 'used', 'total', 'timestamp', 'datetime']:
                    if isinstance(amounts, dict):
                        total = float(amounts.get('total', 0))
                        if total > 0:
                            currencies_with_balance.add(currency)
                            # DEBUG: Log Bybit balances found
                            if exchange_info['ccxt_id'].lower() == 'bybit':
                                logger.info(f"🔍 Bybit token found: {currency} = {total}")
            
            logger.debug(f"{exchange_info['nome']}: Found {len(currencies_with_balance)} currencies with balance")
            
            # Fetch tickers to get current prices (OPTIMIZED - fetch only needed tickers)
            tickers = {}
            usd_brl_rate = None
            
            try:
                # OPTIMIZATION: For ALL exchanges, only fetch tickers we need
                # This drastically reduces API load and response time
                
                if len(currencies_with_balance) > 0:
                    logger.debug(f"{exchange_info['nome']}: Fetching only {len(currencies_with_balance)} needed tickers")
                    
                    for currency in currencies_with_balance:
                        # Stablecoins don't need price lookup
                        if currency in ['USDT', 'USDC', 'USD', 'BUSD']:
                            tickers[currency] = 1.0
                            continue
                        
                        # Try common quote currencies in order of preference
                        # NovaDAX: Try BRL first (it's a Brazilian exchange)
                        if exchange_info.get('nome', '').lower() == 'novadax':
                            quote_currencies = ['BRL', 'USDT', 'USDC', 'USD', 'BUSD', 'BTC', 'ETH']
                        else:
                            quote_currencies = ['USDT', 'USDC', 'USD', 'BUSD', 'BRL', 'BTC', 'ETH']
                        
                        for quote in quote_currencies:
                            symbol = f"{currency}/{quote}"
                            try:
                                ticker = exchange.fetch_ticker(symbol)
                                price = ticker.get('last', 0) or ticker.get('close', 0) or 0
                                
                                if not price:
                                    continue
                                
                                # Direct USD quotes (USDT, USDC, USD, BUSD)
                                if quote in ['USDT', 'USDC', 'USD', 'BUSD']:
                                    tickers[currency] = float(price)
                                    break
                                
                                # BRL pairs - need conversion to USD
                                elif quote == 'BRL':
                                    if usd_brl_rate is None:
                                        try:
                                            price_feed = get_price_feed_service()
                                            usd_brl_rate = price_feed.get_usd_brl_rate()
                                        except:
                                            usd_brl_rate = 5.0  # Fallback rate
                                    tickers[currency] = float(price) / usd_brl_rate
                                    break
                                
                                # BTC pair - need BTC price in USD
                                elif quote == 'BTC':
                                    if 'BTC' not in tickers:
                                        try:
                                            btc_ticker = exchange.fetch_ticker('BTC/USDT')
                                            btc_price = btc_ticker.get('last', 0) or btc_ticker.get('close', 0) or 0
                                            if btc_price:
                                                tickers['BTC'] = float(btc_price)
                                        except:
                                            pass
                                    if 'BTC' in tickers and tickers['BTC'] > 0:
                                        tickers[currency] = float(price) * tickers['BTC']
                                        break
                                
                                # ETH pair - need ETH price in USD
                                elif quote == 'ETH':
                                    if 'ETH' not in tickers:
                                        try:
                                            eth_ticker = exchange.fetch_ticker('ETH/USDT')
                                            eth_price = eth_ticker.get('last', 0) or eth_ticker.get('close', 0) or 0
                                            if eth_price:
                                                tickers['ETH'] = float(eth_price)
                                        except:
                                            pass
                                    if 'ETH' in tickers and tickers['ETH'] > 0:
                                        tickers[currency] = float(price) * tickers['ETH']
                                        break
                            except:
                                continue  # Try next quote currency
                
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
                        
                        # Build balance data (store raw values for sorting later)
                        balance_data_entry = {
                            'total': total,  # Keep as float for sorting
                            'price_usd': format_price(price_usd),
                            'value_usd': format_usd(value_usd),
                            '_price_raw': price_usd,  # Store raw price for sorting
                            '_value_raw': value_usd   # Store raw value for sorting
                        }
                        
                        # Add 24h price change ONLY if explicitly requested (performance optimization)
                        if include_changes and price_usd > 0 and currency not in ['USDT', 'USDC', 'BRL', 'BUSD']:
                            # Determine quote currency used for this token
                            quote_currency = 'USDT'
                            if exchange_info.get('nome', '').lower() == 'novadax':
                                quote_currency = 'BRL'
                            
                            changes = self._calculate_price_changes(exchange, currency, price_usd, quote_currency)
                            
                            # Add 24h change (only field returned now for performance)
                            if changes['change_24h'] is not None:
                                balance_data_entry['change_24h'] = changes['change_24h']
                        
                        processed_balances[currency] = balance_data_entry
            
            # FALLBACK: Use CoinGecko for tokens without prices
            if tokens_needing_prices:
                # Filter out fiat currencies (BRL, EUR, etc) - they shouldn't go to CoinGecko
                fiat_currencies = ['BRL', 'USD', 'EUR', 'GBP', 'JPY', 'CNY', 'ARS', 'MXN']
                tokens_for_coingecko = [t for t in tokens_needing_prices if t not in fiat_currencies]
                
                if tokens_for_coingecko:
                    try:
                        logger.info(f"Fetching prices from CoinGecko for {len(tokens_for_coingecko)} tokens: {tokens_for_coingecko}")
                        price_feed = get_price_feed_service()
                        coingecko_prices = price_feed.fetch_prices_batch(tokens_for_coingecko)
                        
                        # Update balances with CoinGecko prices
                        for currency in tokens_for_coingecko:
                            if currency in processed_balances and currency in coingecko_prices:
                                cg_price = coingecko_prices[currency]
                                total_amount = processed_balances[currency]['total']
                                new_value_usd = total_amount * cg_price
                                
                                # Update with CoinGecko price (keep raw values)
                                old_value = processed_balances[currency].get('_value_raw', 0.0)
                                processed_balances[currency]['price_usd'] = format_price(cg_price)
                                processed_balances[currency]['value_usd'] = format_usd(new_value_usd)
                                processed_balances[currency]['_price_raw'] = cg_price
                                processed_balances[currency]['_value_raw'] = new_value_usd
                                
                                # Update total
                                total_usd = total_usd - old_value + new_value_usd
                                
                                logger.debug(f"Updated {currency} price from CoinGecko: ${cg_price}")
                        
                    except Exception as e:
                        logger.warning(f"Could not fetch fallback prices from CoinGecko: {e}")
            
            # ✅ SORT balances by real value BEFORE returning
            # Convert to list with real values for sorting
            balances_list = []
            for currency, balance_entry in processed_balances.items():
                # Use stored raw value for accurate sorting
                real_value = balance_entry.get('_value_raw', 0.0)
                balances_list.append((currency, balance_entry, real_value))
                logger.debug(f"Sort prep: {currency} = ${real_value}")
            
            # Sort by real_value (descending)
            balances_list.sort(key=lambda x: x[2], reverse=True)
            logger.debug(f"✅ Sorted order: {[f'{c}=${v:.2f}' for c, _, v in balances_list[:5]]}")
            
            # Rebuild dict in sorted order (KEEP raw values for now, will be cleaned in fetch_all_balances)
            processed_balances = {currency: balance_entry for currency, balance_entry, _ in balances_list}
            
            # DEBUG: Log order after sorting
            logger.info(f"📊 {exchange_info['nome']} sorted tokens: {list(processed_balances.keys())[:5]}")
            
            fetch_time = time.time() - start_time
            
            result.update({
                'success': True,
                'balances': processed_balances,
                'total_usd': format_usd(total_usd),
                'fetch_time': round(fetch_time, 3)
            })
            
        except ccxt.AuthenticationError as e:
            result['error'] = f"Authentication failed: {str(e)}"
            logger.error(f"❌ {exchange_info['nome']}: Authentication error - {str(e)}")
        except ccxt.ExchangeError as e:
            error_msg = str(e)
            result['error'] = f"Exchange error: {error_msg}"
            logger.error(f"❌ {exchange_info['nome']}: Exchange error - {error_msg}")
        except Exception as e:
            error_msg = str(e)
            
            # Special handling for geo-blocking errors
            if '403' in error_msg and ('CloudFront' in error_msg or 'configured to block access from your country' in error_msg):
                result['error'] = f"🌍 Geo-blocked: {exchange_info['nome']} is blocking access from your region. Consider using a VPN or proxy."
                logger.error(f"🌍 {exchange_info['nome']}: GEO-BLOCKED - Access denied from current region")
                logger.info(f"💡 Solution: Set BYBIT_PROXY_URL in .env to use a proxy server")
            else:
                result['error'] = f"Error: {error_msg}"
                logger.error(f"❌ {exchange_info['nome']}: Unexpected error - {error_msg}")
        
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
                
                # Use tokens directly from exchange_result (already sorted and formatted)
                # Just remove internal fields (_value_raw, _price_raw) and rename 'total' to 'amount'
                for currency, amounts in exchange_result['balances'].items():
                    # Clean up and format: remove internal fields, rename total to amount
                    token_info = {}
                    for k, v in amounts.items():
                        if k.startswith('_'):
                            continue  # Skip internal fields
                        elif k == 'total':
                            token_info['amount'] = format_amount(v)  # Rename total -> amount and format
                        else:
                            token_info[k] = v  # Keep price_usd, value_usd, change_* as-is (already formatted)
                    
                    exchange_tokens[currency] = token_info
            
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
        
        # ✅ SORT: Order exchanges by total_usd (highest to lowest)
        exchanges_summary = sorted(
            exchanges_summary,
            key=lambda x: float(x.get('total_usd', '0.0')) if x.get('success') else 0,
            reverse=True
        )
        
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
    
    def fetch_exchanges_summary(self, user_id: str, use_cache: bool = True) -> Dict:
        """
        Fetch ONLY totals from all exchanges (ultra-fast for listing)
        Perfect for initial load - no token details
        
        Args:
            user_id: User ID
            use_cache: Whether to use cached data
            
        Returns:
            Dict with exchange summaries (totals only, no tokens)
        """
        # Check cache first
        if use_cache:
            cache_key = f"summary_{user_id}"
            is_valid, cached_data = _balance_cache.get(cache_key)
            if is_valid:
                cached_data['from_cache'] = True
                return cached_data
        
        start_time = time.time()
        
        # Get user exchanges
        user_doc = self.db.user_exchanges.find_one({'user_id': user_id})
        
        if not user_doc or 'exchanges' not in user_doc:
            return {
                'success': True,
                'user_id': user_id,
                'exchanges': [],
                'summary': {'total_usd': '0.00', 'exchanges_count': 0},
                'meta': {'from_cache': False, 'fetch_time': 0}
            }
        
        active_exchanges = [ex for ex in user_doc['exchanges'] if ex.get('is_active', True)]
        
        if not active_exchanges:
            return {
                'success': True,
                'user_id': user_id,
                'exchanges': [],
                'summary': {'total_usd': '0.00', 'exchanges_count': 0},
                'meta': {'from_cache': False, 'fetch_time': 0}
            }
        
        # Get exchange info
        exchange_ids = [ex['exchange_id'] for ex in active_exchanges]
        exchanges_info = {
            ex['_id']: ex
            for ex in self.db.exchanges.find({'_id': {'$in': exchange_ids}})
        }
        
        # Fetch totals in parallel (FAST - no token details!)
        exchange_results = []
        
        with ThreadPoolExecutor(max_workers=min(len(active_exchanges), 10)) as executor:
            futures = {
                executor.submit(
                    self.fetch_exchange_total_only,
                    ex_data,
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
                        'error': f"Error: {str(e)}",
                        'total_usd': '0.00'
                    })
        
        # Build summary
        total_portfolio_usd = 0.0
        exchanges_summary = []
        
        for result in exchange_results:
            if result['success']:
                total_usd = float(result.get('total_usd', '0.0'))
                total_portfolio_usd += total_usd
            
            exchanges_summary.append({
                'exchange_id': result['exchange_id'],
                'name': result['exchange_name'],
                'icon': result.get('exchange_icon'),
                'success': result['success'],
                'total_usd': result.get('total_usd', '0.00'),
                'error': result.get('error'),
                'has_details': False  # Flag: details not loaded yet
            })
        
        # Sort by total
        exchanges_summary = sorted(
            exchanges_summary,
            key=lambda x: float(x.get('total_usd', '0.0')),
            reverse=True
        )
        
        fetch_time = time.time() - start_time
        
        result = {
            'success': True,
            'user_id': user_id,
            'timestamp': datetime.utcnow().isoformat(),
            'summary': {
                'total_usd': format_usd(total_portfolio_usd),
                'exchanges_count': len([e for e in exchanges_summary if e['success']])
            },
            'exchanges': exchanges_summary,
            'meta': {
                'from_cache': False,
                'fetch_time': round(fetch_time, 3),
                'type': 'summary_only'  # Indicates this is lightweight version
            }
        }
        
        # Cache summary
        if use_cache:
            cache_key = f"summary_{user_id}"
            _balance_cache.set(cache_key, result)
        
        logger.info(f"✅ Summary fetched in {fetch_time:.2f}s: {len(exchanges_summary)} exchanges, total ${total_portfolio_usd:.2f}")
        
        return result
    
    def fetch_single_exchange_details(self, user_id: str, exchange_id: str, include_changes: bool = False) -> Dict:
        """
        Fetch detailed token list for ONE specific exchange
        Used when user clicks to expand exchange details
        
        Args:
            user_id: User ID
            exchange_id: Exchange MongoDB _id
            include_changes: Whether to include price changes
            
        Returns:
            Dict with detailed token list for the exchange
        """
        from bson import ObjectId
        
        # Check cache first
        cache_key = f"exchange_{user_id}_{exchange_id}"
        is_valid, cached_data = _balance_cache.get(cache_key)
        if is_valid:
            cached_data['from_cache'] = True
            return cached_data
        
        # Get user exchange link
        user_doc = self.db.user_exchanges.find_one({'user_id': user_id})
        
        if not user_doc or 'exchanges' not in user_doc:
            return {'success': False, 'error': 'User not found'}
        
        # Find specific exchange link
        exchange_link = None
        for ex in user_doc['exchanges']:
            if str(ex['exchange_id']) == exchange_id:
                exchange_link = ex
                break
        
        if not exchange_link:
            return {'success': False, 'error': 'Exchange not linked'}
        
        # Get exchange info
        try:
            exchange_info = self.db.exchanges.find_one({'_id': ObjectId(exchange_id)})
        except:
            return {'success': False, 'error': 'Invalid exchange ID'}
        
        if not exchange_info:
            return {'success': False, 'error': 'Exchange not found'}
        
        # Fetch full details for this exchange
        logger.info(f"📊 Fetching details for {exchange_info['nome']}...")
        result = self.fetch_single_exchange_balance(exchange_link, exchange_info, include_changes)
        
        # Transform to API format
        if result['success']:
            tokens = {}
            for currency, amounts in result['balances'].items():
                token_info = {}
                for k, v in amounts.items():
                    if k.startswith('_'):
                        continue
                    elif k == 'total':
                        token_info['amount'] = format_amount(v)
                    else:
                        token_info[k] = v
                tokens[currency] = token_info
            
            response = {
                'success': True,
                'exchange_id': result['exchange_id'],
                'name': result['exchange_name'],
                'icon': result.get('exchange_icon'),
                'total_usd': result['total_usd'],
                'tokens': tokens,
                'meta': {
                    'from_cache': False,
                    'fetch_time': result.get('fetch_time', 0)
                }
            }
        else:
            response = {
                'success': False,
                'exchange_id': result['exchange_id'],
                'name': result['exchange_name'],
                'error': result.get('error'),
                'tokens': {}
            }
        
        # Cache details
        _balance_cache.set(cache_key, response)
        
        return response
    
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
