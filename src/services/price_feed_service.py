"""
Price Feed Service - Fetch crypto prices in USD and BRL
Uses CoinGecko API (free tier) for crypto prices
Uses AwesomeAPI for USD/BRL conversion
"""

import requests
from typing import Dict, List, Tuple
from datetime import datetime, timedelta
import time


class PriceCache:
    """Cache for price data"""
    
    def __init__(self, ttl_seconds: int = 300):
        """
        Initialize price cache
        
        Args:
            ttl_seconds: Time to live (default 5 minutes for prices)
        """
        self.cache = {}
        self.ttl_seconds = ttl_seconds
    
    def get(self, key: str) -> Tuple[bool, any]:
        """Get cached price if still valid"""
        if key not in self.cache:
            return False, None
        
        cached_data, timestamp = self.cache[key]
        
        if datetime.utcnow() - timestamp < timedelta(seconds=self.ttl_seconds):
            return True, cached_data
        
        del self.cache[key]
        return False, None
    
    def set(self, key: str, data: any):
        """Set cache data"""
        self.cache[key] = (data, datetime.utcnow())
    
    def clear(self):
        """Clear all cache"""
        self.cache.clear()


# Global price cache
_price_cache = PriceCache(ttl_seconds=300)  # 5 minutes


class PriceFeedService:
    """Service to fetch cryptocurrency prices"""
    
    # CoinGecko API endpoints (free tier)
    COINGECKO_API = "https://api.coingecko.com/api/v3"
    AWESOMEAPI_USDBRL = "https://economia.awesomeapi.com.br/last/USD-BRL"
    
    # Common token mappings to CoinGecko IDs
    TOKEN_MAPPINGS = {
        'BTC': 'bitcoin',
        'ETH': 'ethereum',
        'USDT': 'tether',
        'USDC': 'usd-coin',
        'BNB': 'binancecoin',
        'SOL': 'solana',
        'XRP': 'ripple',
        'ADA': 'cardano',
        'DOGE': 'dogecoin',
        'TRX': 'tron',
        'DOT': 'polkadot',
        'MATIC': 'matic-network',
        'LTC': 'litecoin',
        'AVAX': 'avalanche-2',
        'UNI': 'uniswap',
        'LINK': 'chainlink',
        'ATOM': 'cosmos',
        'FTM': 'fantom',
        'ALGO': 'algorand',
        'VET': 'vechain',
        'ICP': 'internet-computer',
        'FIL': 'filecoin',
        'APT': 'aptos',
        'ARB': 'arbitrum',
        'OP': 'optimism',
        'MX': 'mx-token',
        'SHIB': 'shiba-inu',
        'PEPE': 'pepe',
        'CAKE': 'pancakeswap-token',
        'SAND': 'the-sandbox',
        'MANA': 'decentraland',
        'AXS': 'axie-infinity',
        'GALA': 'gala',
        'CHZ': 'chiliz',
        'ENJ': 'enjincoin',
        'BAT': 'basic-attention-token'
    }
    
    def __init__(self):
        """Initialize price feed service"""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Multi-Exchange Balance Tracker)',
            'Accept': 'application/json'
        })
    
    def get_usd_brl_rate(self) -> float:
        """
        Get USD to BRL conversion rate
        
        Returns:
            Current USD/BRL rate
        """
        cache_key = "usd_brl_rate"
        is_valid, cached_rate = _price_cache.get(cache_key)
        
        if is_valid:
            return cached_rate
        
        try:
            response = self.session.get(self.AWESOMEAPI_USDBRL, timeout=5)
            response.raise_for_status()
            
            data = response.json()
            rate = float(data['USDBRL']['bid'])
            
            _price_cache.set(cache_key, rate)
            return rate
            
        except Exception as e:
            print(f"⚠️  Error fetching USD/BRL rate: {e}")
            # Fallback to approximate rate if API fails
            return 5.0  # Approximate fallback
    
    def get_coingecko_id(self, token: str) -> str:
        """
        Map token symbol to CoinGecko ID
        
        Args:
            token: Token symbol (e.g., 'BTC', 'ETH')
            
        Returns:
            CoinGecko ID or None if not found
        """
        return self.TOKEN_MAPPINGS.get(token.upper())
    
    def fetch_prices_batch(self, tokens: List[str]) -> Dict[str, float]:
        """
        Fetch prices for multiple tokens in batch (more efficient)
        
        Args:
            tokens: List of token symbols
            
        Returns:
            Dict mapping token symbol to USD price
        """
        # Filter tokens that we have mappings for
        coingecko_ids = []
        token_to_id = {}
        
        for token in tokens:
            cg_id = self.get_coingecko_id(token)
            if cg_id:
                coingecko_ids.append(cg_id)
                token_to_id[cg_id] = token
        
        if not coingecko_ids:
            return {}
        
        # Check cache first
        cache_key = f"prices_batch_{'_'.join(sorted(coingecko_ids[:50]))}"  # Limit key size
        is_valid, cached_prices = _price_cache.get(cache_key)
        
        if is_valid:
            return cached_prices
        
        try:
            # CoinGecko simple price API (free tier)
            # Max 250 tokens per request
            ids_param = ','.join(coingecko_ids[:250])
            url = f"{self.COINGECKO_API}/simple/price"
            params = {
                'ids': ids_param,
                'vs_currencies': 'usd'
            }
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Map back to token symbols
            prices = {}
            for cg_id, token in token_to_id.items():
                if cg_id in data and 'usd' in data[cg_id]:
                    prices[token] = float(data[cg_id]['usd'])
            
            # Cache result
            _price_cache.set(cache_key, prices)
            
            return prices
            
        except Exception as e:
            print(f"⚠️  Error fetching prices from CoinGecko: {e}")
            return {}
    
    def get_token_price(self, token: str) -> float:
        """
        Get price for a single token
        
        Args:
            token: Token symbol
            
        Returns:
            Price in USD or 0.0 if not found
        """
        prices = self.fetch_prices_batch([token])
        return prices.get(token, 0.0)
    
    def enrich_balances_with_prices(self, balances: Dict, include_brl: bool = False, usd_brl_rate: float = None) -> Dict:
        """
        Enrich balance data with USD prices and optionally BRL values
        
        Args:
            balances: Balance data from BalanceService
            include_brl: Whether to include BRL conversion
            usd_brl_rate: Optional USD/BRL rate (fetched if not provided and include_brl=True)
            
        Returns:
            Enhanced balance data with prices
        """
        if not balances.get('success'):
            return balances
        
        # Get USD/BRL rate if BRL requested
        if include_brl:
            if usd_brl_rate is None:
                usd_brl_rate = self.get_usd_brl_rate()
        else:
            usd_brl_rate = 0.0
        
        # Collect all unique tokens
        all_tokens = set()
        for exchange in balances.get('exchanges', []):
            if exchange.get('success'):
                all_tokens.update(exchange.get('balances', {}).keys())
        
        # Fetch prices in batch
        prices = self.fetch_prices_batch(list(all_tokens))
        
        # Update exchange summaries with totals
        for exchange in balances.get('exchanges', []):
            if not exchange.get('success'):
                continue
            
            exchange_total_usd = 0.0
            
            # Calculate total USD for this exchange from tokens_summary
            for token, info in balances.get('tokens_summary', {}).items():
                for ex_info in info.get('exchanges', []):
                    if ex_info['name'] == exchange['exchange_name']:
                        price_usd = prices.get(token, 0.0)
                        value_usd = ex_info['amount'] * price_usd
                        exchange_total_usd += value_usd
            
            exchange['total_usd'] = round(exchange_total_usd, 2)
            
            if include_brl:
                exchange['total_brl'] = round(exchange_total_usd * usd_brl_rate, 2)
        
        # Update tokens summary
        total_value_usd = 0.0
        
        for token, info in balances.get('tokens_summary', {}).items():
            price_usd = prices.get(token, 0.0)
            value_usd = info['total'] * price_usd
            
            info['price_usd'] = round(price_usd, 6)
            info['value_usd'] = round(value_usd, 2)
            
            if include_brl:
                value_brl = value_usd * usd_brl_rate
                info['value_brl'] = round(value_brl, 2)
            
            total_value_usd += value_usd
        
        # Update totals
        balances['total_usd'] = round(total_value_usd, 2)
        
        if include_brl:
            balances['total_brl'] = round(total_value_usd * usd_brl_rate, 2)
            balances['usd_brl_rate'] = round(usd_brl_rate, 4)
        
        balances['prices_updated_at'] = datetime.utcnow().isoformat()
        
        return balances
    
    def clear_cache(self):
        """Clear price cache"""
        _price_cache.clear()


# Singleton instance
_price_feed_service = None

def get_price_feed_service() -> PriceFeedService:
    """Get singleton instance of price feed service"""
    global _price_feed_service
    if _price_feed_service is None:
        _price_feed_service = PriceFeedService()
    return _price_feed_service
