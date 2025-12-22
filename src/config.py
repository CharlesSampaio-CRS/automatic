"""
Centralized Configuration
All configuration variables and constants in one place
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


# ============================================
# MongoDB Configuration
# ============================================
MONGODB_URI = os.getenv('MONGODB_URI')
MONGODB_DATABASE = os.getenv('MONGODB_DATABASE', 'MultExchange')

# Collection names
COLLECTION_EXCHANGES = 'exchanges'
COLLECTION_USER_EXCHANGES = 'user_exchanges'
COLLECTION_BALANCE_HISTORY = 'balance_history'
COLLECTION_STRATEGIES = 'strategies'
COLLECTION_ORDERS = 'orders'
COLLECTION_POSITIONS = 'positions'
COLLECTION_NOTIFICATIONS = 'notifications'
COLLECTION_JOBS = 'jobs'


# ============================================
# Cache Configuration
# ============================================
# Balance cache TTL in seconds (2 minutes)
BALANCE_CACHE_TTL = int(os.getenv('BALANCE_CACHE_TTL', '120'))

# Price cache TTL in seconds (5 minutes)
PRICE_CACHE_TTL = int(os.getenv('PRICE_CACHE_TTL', '300'))

# Exchange info cache TTL in seconds (1 hour)
EXCHANGE_INFO_CACHE_TTL = int(os.getenv('EXCHANGE_INFO_CACHE_TTL', '3600'))

# Token info cache TTL in seconds (30 minutes)
TOKEN_INFO_CACHE_TTL = int(os.getenv('TOKEN_INFO_CACHE_TTL', '1800'))


# ============================================
# FastAPI Configuration
# ============================================
# API server port
API_PORT = int(os.getenv('PORT', '8000'))

# API debug mode
API_DEBUG = os.getenv('ENV', 'development') == 'development'

# API version
API_VERSION = 'v1'
API_PREFIX = f'/api/{API_VERSION}'

# CORS origins (comma-separated in env)
CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*').split(',')

# Rate limiting
RATE_LIMIT_PER_MINUTE = int(os.getenv('RATE_LIMIT_PER_MINUTE', '60'))
RATE_LIMIT_PER_HOUR = int(os.getenv('RATE_LIMIT_PER_HOUR', '1000'))


# ============================================
# External APIs
# ============================================
# CoinGecko API
COINGECKO_API = "https://api.coingecko.com/api/v3"

# AwesomeAPI for USD/BRL
AWESOMEAPI_USDBRL = "https://economia.awesomeapi.com.br/last/USD-BRL"

# Trust Wallet Assets
TRUSTWALLET_BASE = "https://raw.githubusercontent.com/trustwallet/assets/master/blockchains"


# ============================================
# Security Configuration
# ============================================
# Encryption key (must be set in environment)
ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY')

if not ENCRYPTION_KEY:
    raise ValueError(
        "ENCRYPTION_KEY environment variable is required. "
        "Run: python scripts/generate_encryption_key.py"
    )


# ============================================
# Performance Configuration
# ============================================
# Max concurrent threads for balance fetching
MAX_WORKERS = int(os.getenv('MAX_WORKERS', '10'))

# Request timeout in seconds
REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', '10'))

# Max retries for API calls
MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))


# ============================================
# Logging Configuration
# ============================================
# Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()

# Log file path (None = console only)
LOG_FILE = os.getenv('LOG_FILE', None)


# ============================================
# Token Mappings
# ============================================
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
}


# ============================================
# Validation
# ============================================
def validate_config():
    """Validate all required configuration variables"""
    errors = []
    
    if not MONGODB_URI:
        errors.append("MONGODB_URI is required")
    
    if not ENCRYPTION_KEY:
        errors.append("ENCRYPTION_KEY is required")
    
    if errors:
        raise ValueError(f"Configuration errors: {', '.join(errors)}")


# Validate on import
validate_config()
