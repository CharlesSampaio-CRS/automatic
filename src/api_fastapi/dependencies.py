"""
FastAPI Dependencies
Reusable dependency functions for endpoints
"""

from fastapi import Depends, HTTPException, Header, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Optional, Annotated
import logging

from .database import get_database
from .constants import StatusCode, Messages, Pagination

logger = logging.getLogger(__name__)


# ============================================
# Database Dependencies
# ============================================

async def get_db() -> AsyncIOMotorDatabase:
    """
    Dependency to get database instance
    Usage: db: AsyncIOMotorDatabase = Depends(get_db)
    """
    return get_database()


# ============================================
# Authentication Dependencies
# ============================================

async def get_current_user(
    authorization: Annotated[Optional[str], Header()] = None
) -> Optional[str]:
    """
    Get current user from authorization header
    In production, this should validate JWT tokens
    
    Usage: user_id: str = Depends(get_current_user)
    """
    if not authorization:
        return None
    
    # TODO: Implement proper JWT token validation
    # For now, extract user_id from bearer token
    if authorization.startswith("Bearer "):
        token = authorization.replace("Bearer ", "")
        # In production: validate token and extract user_id
        return token
    
    return None


async def require_auth(
    user_id: Annotated[Optional[str], Depends(get_current_user)]
) -> str:
    """
    Require authentication
    Raises 401 if user is not authenticated
    
    Usage: user_id: str = Depends(require_auth)
    """
    if not user_id:
        raise HTTPException(
            status_code=StatusCode.UNAUTHORIZED,
            detail=Messages.UNAUTHORIZED
        )
    return user_id


# ============================================
# Pagination Dependencies
# ============================================

async def get_pagination(
    page: Annotated[int, Query(ge=1)] = Pagination.DEFAULT_PAGE,
    page_size: Annotated[int, Query(ge=1, le=Pagination.MAX_PAGE_SIZE)] = Pagination.DEFAULT_PAGE_SIZE
) -> dict:
    """
    Get pagination parameters
    
    Usage: pagination: dict = Depends(get_pagination)
    """
    return {
        "page": page,
        "page_size": page_size,
        "skip": (page - 1) * page_size,
        "limit": page_size
    }


# ============================================
# Validation Dependencies
# ============================================

async def validate_user_id(user_id: str) -> str:
    """
    Validate user_id format
    
    Usage: user_id: str = Depends(validate_user_id)
    """
    if not user_id or len(user_id.strip()) == 0:
        raise HTTPException(
            status_code=StatusCode.BAD_REQUEST,
            detail="Invalid user_id"
        )
    return user_id.strip()


async def validate_exchange_id(exchange_id: str) -> str:
    """
    Validate exchange_id format
    
    Usage: exchange_id: str = Depends(validate_exchange_id)
    """
    if not exchange_id or len(exchange_id.strip()) == 0:
        raise HTTPException(
            status_code=StatusCode.BAD_REQUEST,
            detail="Invalid exchange_id"
        )
    return exchange_id.strip().lower()


async def validate_symbol(symbol: str) -> str:
    """
    Validate trading symbol format
    
    Usage: symbol: str = Depends(validate_symbol)
    """
    if not symbol or len(symbol.strip()) == 0:
        raise HTTPException(
            status_code=StatusCode.BAD_REQUEST,
            detail="Invalid symbol"
        )
    return symbol.strip().upper()


# ============================================
# Query Parameter Dependencies
# ============================================

async def get_optional_filters(
    status: Optional[str] = None,
    sort_by: Optional[str] = None,
    order: Optional[str] = Query(default="desc", regex="^(asc|desc)$")
) -> dict:
    """
    Get optional filter parameters
    
    Usage: filters: dict = Depends(get_optional_filters)
    """
    filters = {}
    
    if status:
        filters["status"] = status
    
    sort_config = {}
    if sort_by:
        sort_config["field"] = sort_by
        sort_config["order"] = 1 if order == "asc" else -1
    
    return {
        "filters": filters,
        "sort": sort_config
    }


# ============================================
# Rate Limiting Dependencies
# ============================================

# TODO: Implement rate limiting with Redis
async def rate_limiter(
    user_id: Annotated[Optional[str], Depends(get_current_user)] = None
) -> None:
    """
    Rate limiting dependency
    In production, implement with Redis or similar
    
    Usage: _: None = Depends(rate_limiter)
    """
    # Placeholder for rate limiting logic
    pass


# ============================================
# Cache Dependencies
# ============================================

class CacheManager:
    """
    Cache manager for dependency injection
    In production, use Redis
    """
    
    def __init__(self):
        self._cache = {}
    
    async def get(self, key: str) -> Optional[any]:
        """Get value from cache"""
        return self._cache.get(key)
    
    async def set(self, key: str, value: any, ttl: int = 300):
        """Set value in cache with TTL"""
        self._cache[key] = value
        # TODO: Implement TTL with asyncio tasks
    
    async def delete(self, key: str):
        """Delete key from cache"""
        self._cache.pop(key, None)
    
    async def clear(self):
        """Clear all cache"""
        self._cache.clear()


# Global cache instance
cache_manager = CacheManager()


async def get_cache() -> CacheManager:
    """
    Get cache manager instance
    
    Usage: cache: CacheManager = Depends(get_cache)
    """
    return cache_manager


# ============================================
# Logging Dependencies
# ============================================

async def log_request(
    user_id: Annotated[Optional[str], Depends(get_current_user)] = None
):
    """
    Log request information
    
    Usage: _: None = Depends(log_request)
    """
    if user_id:
        logger.info(f"Request from user: {user_id}")
