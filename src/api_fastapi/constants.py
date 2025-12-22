"""
API Constants
Centralized constants for the FastAPI application
"""

from enum import Enum


# ============================================
# HTTP Status Codes
# ============================================

class StatusCode:
    """HTTP status code constants"""
    OK = 200
    CREATED = 201
    ACCEPTED = 202
    NO_CONTENT = 204
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    CONFLICT = 409
    UNPROCESSABLE_ENTITY = 422
    INTERNAL_SERVER_ERROR = 500
    SERVICE_UNAVAILABLE = 503


# ============================================
# Response Messages
# ============================================

class Messages:
    """Standard response messages"""
    
    # Success messages
    SUCCESS = "Operation completed successfully"
    CREATED = "Resource created successfully"
    UPDATED = "Resource updated successfully"
    DELETED = "Resource deleted successfully"
    
    # Error messages
    NOT_FOUND = "Resource not found"
    ALREADY_EXISTS = "Resource already exists"
    INVALID_INPUT = "Invalid input data"
    UNAUTHORIZED = "Authentication required"
    FORBIDDEN = "Insufficient permissions"
    INTERNAL_ERROR = "Internal server error"
    DATABASE_ERROR = "Database operation failed"
    EXTERNAL_API_ERROR = "External API request failed"
    
    # Exchange messages
    EXCHANGE_NOT_FOUND = "Exchange not found"
    EXCHANGE_NOT_LINKED = "Exchange not linked to user"
    EXCHANGE_ALREADY_LINKED = "Exchange already linked to this user"
    EXCHANGE_CONNECTION_ERROR = "Failed to connect to exchange"
    INVALID_API_CREDENTIALS = "Invalid API credentials"
    
    # Balance messages
    BALANCE_NOT_FOUND = "Balance not found"
    INSUFFICIENT_BALANCE = "Insufficient balance"
    
    # Strategy messages
    STRATEGY_NOT_FOUND = "Strategy not found"
    STRATEGY_ALREADY_EXISTS = "Strategy with this name already exists"
    INVALID_STRATEGY_RULES = "Invalid strategy rules"
    
    # Order messages
    ORDER_NOT_FOUND = "Order not found"
    ORDER_CREATION_FAILED = "Failed to create order"
    INVALID_ORDER_TYPE = "Invalid order type"
    
    # Position messages
    POSITION_NOT_FOUND = "Position not found"
    NO_OPEN_POSITIONS = "No open positions found"


# ============================================
# Trading Constants
# ============================================

class OrderType(str, Enum):
    """Order types"""
    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"


class OrderSide(str, Enum):
    """Order sides"""
    BUY = "buy"
    SELL = "sell"


class OrderStatus(str, Enum):
    """Order statuses"""
    PENDING = "pending"
    OPEN = "open"
    CLOSED = "closed"
    CANCELED = "canceled"
    FAILED = "failed"


class PositionSide(str, Enum):
    """Position sides"""
    LONG = "long"
    SHORT = "short"


class StrategyStatus(str, Enum):
    """Strategy statuses"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PAUSED = "paused"
    ARCHIVED = "archived"


# ============================================
# Cache Configuration
# ============================================

class CacheTTL:
    """Cache TTL values in seconds"""
    BALANCE = 120  # 2 minutes
    PRICE = 300    # 5 minutes
    EXCHANGE_INFO = 3600  # 1 hour
    TOKEN_INFO = 1800  # 30 minutes


# ============================================
# Pagination
# ============================================

class Pagination:
    """Pagination defaults"""
    DEFAULT_PAGE = 1
    DEFAULT_PAGE_SIZE = 20
    MAX_PAGE_SIZE = 100


# ============================================
# API Configuration
# ============================================

class APIConfig:
    """API configuration constants"""
    VERSION = "2.0.0"
    TITLE = "Multi-Exchange Trading System API"
    DESCRIPTION = "Sistema de Trading Automatizado com múltiplas exchanges"
    PREFIX = "/api/v1"
    
    # Rate limiting
    RATE_LIMIT_PER_MINUTE = 60
    RATE_LIMIT_PER_HOUR = 1000


# ============================================
# Supported Exchanges
# ============================================

SUPPORTED_EXCHANGES = [
    "binance",
    "okx",
    "bybit",
    "gate",
    "mexc",
    "bitget",
    "kucoin",
    "huobi",
    "kraken",
    "coinbase"
]


# ============================================
# Token Categories
# ============================================

TOKEN_CATEGORIES = [
    "DeFi",
    "NFT",
    "Gaming",
    "Layer1",
    "Layer2",
    "Meme",
    "AI",
    "Infrastructure",
    "Privacy",
    "Stablecoin"
]
