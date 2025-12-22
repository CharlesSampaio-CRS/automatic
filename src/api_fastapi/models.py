"""
Pydantic Models para FastAPI
Validação automática de request/response
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from bson import ObjectId


class PyObjectId(str):
    """Custom Pydantic type para ObjectId do MongoDB"""
    
    @classmethod
    def __get_validators__(cls):
        yield cls.validate
    
    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return str(v)


# ============================================
# EXCHANGE MODELS
# ============================================

class ExchangeLink(BaseModel):
    """Request para linkar exchange"""
    user_id: str
    exchange_id: str
    api_key: str
    api_secret: str
    passphrase: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "charles_test_user",
                "exchange_id": "693481148b0a41e8b6acb073",
                "api_key": "your_api_key",
                "api_secret": "your_api_secret",
                "passphrase": "optional_passphrase"
            }
        }


class ExchangeAction(BaseModel):
    """Request para ações em exchange (connect/disconnect)"""
    user_id: str
    exchange_id: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "charles_test_user",
                "exchange_id": "693481148b0a41e8b6acb073"
            }
        }


class ExchangeResponse(BaseModel):
    """Response de informações de exchange"""
    id: str = Field(alias="_id")
    nome: str
    ccxt_id: str
    url: str
    icon: Optional[str] = None
    pais_de_origem: Optional[str] = None
    is_active: bool = True
    requires_passphrase: bool = False
    
    class Config:
        populate_by_name = True


# ============================================
# TOKEN MODELS
# ============================================

class TokenInfo(BaseModel):
    """Informações de token"""
    symbol: str
    quote: str
    pair: str
    exchange: Dict[str, str]
    icon_url: Optional[str] = None
    price: Dict[str, str]
    volume: Dict[str, str]
    change: Dict[str, Optional[Dict[str, str]]]
    contract: Optional[Dict[str, str]] = None
    user_balance: Optional[Dict[str, str]] = None
    market_info: Dict[str, Any]
    timestamp: Optional[int] = None
    datetime: Optional[str] = None


# ============================================
# BALANCE MODELS
# ============================================

class BalanceQuery(BaseModel):
    """Query parameters para balance"""
    user_id: str
    force_refresh: bool = False
    include_zero_balances: bool = False


class TokenBalance(BaseModel):
    """Balance de um token"""
    symbol: str
    amount: float
    value_usd: Optional[float] = None
    value_brl: Optional[float] = None


class ExchangeBalance(BaseModel):
    """Balance de uma exchange"""
    exchange_id: str
    exchange_name: str
    tokens: Dict[str, TokenBalance]
    total_usd: float
    total_brl: Optional[float] = None
    success: bool
    error: Optional[str] = None
    timestamp: datetime


# ============================================
# STRATEGY MODELS
# ============================================

class TradingRule(BaseModel):
    """Regra de trading"""
    indicator: str
    condition: str
    value: float
    timeframe: str = "1h"


class StrategyCreate(BaseModel):
    """Request para criar estratégia"""
    user_id: str
    name: str
    description: Optional[str] = None
    exchange_id: str
    token_symbol: str
    quote_currency: str = "USDT"
    entry_rules: List[TradingRule]
    exit_rules: List[TradingRule]
    stop_loss_percent: Optional[float] = None
    take_profit_percent: Optional[float] = None
    max_position_size_usd: float
    is_active: bool = True
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "charles_test_user",
                "name": "BTC Scalping",
                "exchange_id": "693481148b0a41e8b6acb073",
                "token_symbol": "BTC",
                "quote_currency": "USDT",
                "entry_rules": [
                    {
                        "indicator": "rsi",
                        "condition": "below",
                        "value": 30,
                        "timeframe": "15m"
                    }
                ],
                "exit_rules": [
                    {
                        "indicator": "rsi",
                        "condition": "above",
                        "value": 70,
                        "timeframe": "15m"
                    }
                ],
                "stop_loss_percent": 2.0,
                "take_profit_percent": 5.0,
                "max_position_size_usd": 100.0
            }
        }


class StrategyResponse(BaseModel):
    """Response de estratégia"""
    id: str = Field(alias="_id")
    user_id: str
    name: str
    description: Optional[str] = None
    exchange_id: str
    token_symbol: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        populate_by_name = True


# ============================================
# ORDER MODELS
# ============================================

class OrderCreate(BaseModel):
    """Request para criar ordem"""
    user_id: str
    exchange_id: str
    symbol: str
    side: str  # "buy" ou "sell"
    order_type: str = "market"  # "market" ou "limit"
    amount: float
    price: Optional[float] = None  # Requerido para limit orders
    
    @validator('side')
    def validate_side(cls, v):
        if v not in ['buy', 'sell']:
            raise ValueError('side must be "buy" or "sell"')
        return v
    
    @validator('order_type')
    def validate_order_type(cls, v):
        if v not in ['market', 'limit']:
            raise ValueError('order_type must be "market" or "limit"')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "charles_test_user",
                "exchange_id": "693481148b0a41e8b6acb073",
                "symbol": "BTC/USDT",
                "side": "buy",
                "order_type": "market",
                "amount": 0.001
            }
        }


# ============================================
# GENERIC RESPONSE MODELS
# ============================================

class SuccessResponse(BaseModel):
    """Response genérica de sucesso"""
    success: bool = True
    message: str
    data: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseModel):
    """Response genérica de erro"""
    success: bool = False
    error: str
    details: Optional[str] = None
