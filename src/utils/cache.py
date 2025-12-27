"""
Simple in-memory cache for API endpoints
"""

from datetime import datetime, timedelta
from typing import Any, Tuple, Optional
import threading


class SimpleCache:
    """Thread-safe in-memory cache with TTL support"""
    
    def __init__(self, default_ttl_seconds: int = 300):
        """
        Initialize cache
        
        Args:
            default_ttl_seconds: Default time to live in seconds (default: 5 minutes)
        """
        self.cache = {}
        self.default_ttl = default_ttl_seconds
        self.lock = threading.Lock()
    
    def get(self, key: str) -> Tuple[bool, Optional[Any]]:
        """
        Get cached data if still valid
        
        Args:
            key: Cache key
            
        Returns:
            Tuple of (is_valid, data)
        """
        with self.lock:
            if key not in self.cache:
                return False, None
            
            cached_data, expiry_time = self.cache[key]
            
            # Check if cache is still valid
            if datetime.utcnow() < expiry_time:
                return True, cached_data
            
            # Cache expired, remove it
            del self.cache[key]
            return False, None
    
    def set(self, key: str, data: Any, ttl_seconds: Optional[int] = None):
        """
        Set cache data with expiry time
        
        Args:
            key: Cache key
            data: Data to cache
            ttl_seconds: Time to live in seconds (uses default if not provided)
        """
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl
        expiry_time = datetime.utcnow() + timedelta(seconds=ttl)
        
        with self.lock:
            self.cache[key] = (data, expiry_time)
    
    def delete(self, key: str):
        """Delete specific cache entry"""
        with self.lock:
            if key in self.cache:
                del self.cache[key]
    
    def clear(self):
        """Clear all cache"""
        with self.lock:
            self.cache.clear()
    
    def clear_pattern(self, pattern: str):
        """
        Clear cache entries matching pattern
        
        Args:
            pattern: String pattern to match (simple substring match)
        """
        with self.lock:
            keys_to_delete = [key for key in self.cache.keys() if pattern in key]
            for key in keys_to_delete:
                del self.cache[key]
    
    def get_stats(self) -> dict:
        """Get cache statistics"""
        with self.lock:
            total_entries = len(self.cache)
            valid_entries = 0
            expired_entries = 0
            
            now = datetime.utcnow()
            for _, expiry_time in self.cache.values():
                if now < expiry_time:
                    valid_entries += 1
                else:
                    expired_entries += 1
            
            return {
                'total_entries': total_entries,
                'valid_entries': valid_entries,
                'expired_entries': expired_entries,
                'default_ttl_seconds': self.default_ttl
            }


# Global cache instances
_exchanges_cache = SimpleCache(default_ttl_seconds=300)  # 5 minutes for exchanges data
_linked_exchanges_cache = SimpleCache(default_ttl_seconds=60)  # 1 minute for user-specific data
_strategies_cache = SimpleCache(default_ttl_seconds=120)  # 2 minutes for strategies data
_single_strategy_cache = SimpleCache(default_ttl_seconds=180)  # 3 minutes for single strategy
_token_search_cache = SimpleCache(default_ttl_seconds=60)  # 1 minute for token search/prices
_ccxt_instances_cache = SimpleCache(default_ttl_seconds=300)  # 5 minutes for CCXT exchange instances
_portfolio_evolution_cache = SimpleCache(default_ttl_seconds=300)  # 5 minutes for portfolio evolution
_orders_cache = SimpleCache(default_ttl_seconds=300)  # 5 minutes for orders history


def get_exchanges_cache() -> SimpleCache:
    """Get global exchanges cache instance"""
    return _exchanges_cache


def get_linked_exchanges_cache() -> SimpleCache:
    """Get global linked exchanges cache instance"""
    return _linked_exchanges_cache


def get_strategies_cache() -> SimpleCache:
    """Get global strategies cache instance"""
    return _strategies_cache


def get_single_strategy_cache() -> SimpleCache:
    """Get global single strategy cache instance"""
    return _single_strategy_cache


def get_token_search_cache() -> SimpleCache:
    """Get global token search cache instance"""
    return _token_search_cache


def get_ccxt_instances_cache() -> SimpleCache:
    """Get global CCXT exchange instances cache (with load_markets already done)"""
    return _ccxt_instances_cache


def get_portfolio_evolution_cache() -> SimpleCache:
    """Get global portfolio evolution cache instance"""
    return _portfolio_evolution_cache


def get_orders_cache() -> SimpleCache:
    """Get global orders history cache instance"""
    return _orders_cache


def invalidate_user_caches(user_id: str, cache_type: str = 'all'):
    """
    Invalidate all caches related to a specific user
    
    Args:
        user_id: User ID to invalidate caches for
        cache_type: Type of cache to invalidate ('all', 'balances', 'strategies', 'exchanges', 'portfolio')
    """
    from src.services.balance_service import _balance_cache
    from src.utils.logger import get_logger
    
    logger = get_logger(__name__)
    logger.info(f"🗑️ Invalidating {cache_type} caches for user: {user_id}")
    
    if cache_type in ['all', 'balances']:
        # Invalidate balance caches
        _balance_cache.delete(f"summary_{user_id}")
        _balance_cache.delete(f"full_{user_id}")
        logger.debug(f"  ✅ Cleared balance caches for {user_id}")
    
    if cache_type in ['all', 'strategies']:
        # Invalidate all strategy caches for this user
        _strategies_cache.clear_pattern(f"strategies_{user_id}")
        _single_strategy_cache.clear_pattern(user_id)
        logger.debug(f"  ✅ Cleared strategy caches for {user_id}")
    
    if cache_type in ['all', 'exchanges']:
        # Invalidate exchange caches
        _exchanges_cache.delete(f"available_{user_id}")
        _linked_exchanges_cache.delete(f"linked_{user_id}")
        logger.debug(f"  ✅ Cleared exchange caches for {user_id}")
    
    if cache_type in ['all', 'portfolio']:
        # Invalidate portfolio evolution caches
        _portfolio_evolution_cache.clear_pattern(f"evolution_{user_id}")
        logger.debug(f"  ✅ Cleared portfolio caches for {user_id}")
    
    logger.info(f"✅ Cache invalidation completed for user: {user_id}")

