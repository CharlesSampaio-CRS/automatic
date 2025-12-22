"""
Response Schemas
Standardized response models for the API
"""

from pydantic import BaseModel, Field
from typing import Any, Optional, List, Dict
from datetime import datetime


# ============================================
# Base Response Models
# ============================================

class BaseResponse(BaseModel):
    """Base response model"""
    success: bool = Field(description="Indicates if the request was successful")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")


class SuccessResponse(BaseResponse):
    """Standard success response"""
    success: bool = Field(default=True)
    data: Any = Field(description="Response data")
    message: Optional[str] = Field(default=None, description="Optional success message")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": {"id": "123", "name": "Example"},
                "message": "Operation completed successfully",
                "timestamp": "2025-12-22T10:30:00Z"
            }
        }


class ErrorResponse(BaseResponse):
    """Standard error response"""
    success: bool = Field(default=False)
    error: str = Field(description="Error message")
    details: Optional[str] = Field(default=None, description="Additional error details")
    path: Optional[str] = Field(default=None, description="Request path that caused the error")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": False,
                "error": "Resource not found",
                "details": "The requested exchange does not exist",
                "path": "/api/v1/exchanges/999",
                "timestamp": "2025-12-22T10:30:00Z"
            }
        }


class PaginatedResponse(BaseResponse):
    """Paginated response model"""
    success: bool = Field(default=True)
    data: List[Any] = Field(description="List of items")
    pagination: Dict[str, Any] = Field(description="Pagination metadata")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": [{"id": "1"}, {"id": "2"}],
                "pagination": {
                    "page": 1,
                    "page_size": 20,
                    "total_items": 50,
                    "total_pages": 3
                },
                "timestamp": "2025-12-22T10:30:00Z"
            }
        }


# ============================================
# Health Check Responses
# ============================================

class HealthCheckResponse(BaseModel):
    """Health check response"""
    status: str = Field(description="Service status")
    service: str = Field(description="Service name")
    version: str = Field(description="API version")
    database: Optional[Dict[str, Any]] = Field(default=None, description="Database connection status")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "service": "Multi-Exchange Trading System",
                "version": "2.0.0",
                "database": {
                    "connected": True,
                    "name": "MultExchange"
                }
            }
        }


class MetricsResponse(BaseResponse):
    """System metrics response"""
    success: bool = Field(default=True)
    database: Dict[str, Any] = Field(description="Database metrics")
    api: Dict[str, Any] = Field(description="API information")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "database": {
                    "name": "MultExchange",
                    "size_mb": 128.5,
                    "collections": 8
                },
                "api": {
                    "version": "2.0.0",
                    "framework": "FastAPI",
                    "async": True
                },
                "timestamp": "2025-12-22T10:30:00Z"
            }
        }


# ============================================
# Exchange Responses
# ============================================

class ExchangeInfo(BaseModel):
    """Exchange information"""
    id: str = Field(description="Exchange identifier")
    name: str = Field(description="Exchange name")
    logo: Optional[str] = Field(default=None, description="Exchange logo URL")
    supported: bool = Field(description="Whether exchange is supported")


class ExchangeListResponse(BaseResponse):
    """List of exchanges response"""
    success: bool = Field(default=True)
    exchanges: List[ExchangeInfo] = Field(description="List of exchanges")


class ExchangeLinkResponse(SuccessResponse):
    """Exchange link success response"""
    data: Dict[str, Any] = Field(description="Linked exchange information")


# ============================================
# Balance Responses
# ============================================

class BalanceInfo(BaseModel):
    """Balance information"""
    asset: str = Field(description="Asset symbol")
    free: float = Field(description="Available balance")
    locked: float = Field(description="Locked balance")
    total: float = Field(description="Total balance")
    usd_value: Optional[float] = Field(default=None, description="USD value")


class BalanceResponse(BaseResponse):
    """Balance response"""
    success: bool = Field(default=True)
    balances: List[BalanceInfo] = Field(description="List of balances")
    total_usd: Optional[float] = Field(default=None, description="Total balance in USD")


# ============================================
# Strategy Responses
# ============================================

class StrategyInfo(BaseModel):
    """Strategy information"""
    id: str = Field(description="Strategy ID")
    name: str = Field(description="Strategy name")
    status: str = Field(description="Strategy status")
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: Optional[datetime] = Field(default=None, description="Last update timestamp")


class StrategyListResponse(BaseResponse):
    """List of strategies response"""
    success: bool = Field(default=True)
    strategies: List[StrategyInfo] = Field(description="List of strategies")


class StrategyDetailResponse(SuccessResponse):
    """Strategy detail response"""
    data: Dict[str, Any] = Field(description="Strategy details")


# ============================================
# Order Responses
# ============================================

class OrderInfo(BaseModel):
    """Order information"""
    id: str = Field(description="Order ID")
    symbol: str = Field(description="Trading pair")
    side: str = Field(description="Order side (buy/sell)")
    type: str = Field(description="Order type")
    price: Optional[float] = Field(default=None, description="Order price")
    amount: float = Field(description="Order amount")
    status: str = Field(description="Order status")
    created_at: datetime = Field(description="Creation timestamp")


class OrderResponse(SuccessResponse):
    """Order response"""
    data: OrderInfo = Field(description="Order information")


# ============================================
# Position Responses
# ============================================

class PositionInfo(BaseModel):
    """Position information"""
    id: str = Field(description="Position ID")
    symbol: str = Field(description="Trading pair")
    side: str = Field(description="Position side (long/short)")
    size: float = Field(description="Position size")
    entry_price: float = Field(description="Entry price")
    current_price: Optional[float] = Field(default=None, description="Current price")
    pnl: Optional[float] = Field(default=None, description="Profit/Loss")
    pnl_percentage: Optional[float] = Field(default=None, description="PnL percentage")


class PositionListResponse(BaseResponse):
    """List of positions response"""
    success: bool = Field(default=True)
    positions: List[PositionInfo] = Field(description="List of positions")
    total_pnl: Optional[float] = Field(default=None, description="Total PnL")


# ============================================
# Notification Responses
# ============================================

class NotificationInfo(BaseModel):
    """Notification information"""
    id: str = Field(description="Notification ID")
    type: str = Field(description="Notification type")
    message: str = Field(description="Notification message")
    read: bool = Field(default=False, description="Read status")
    created_at: datetime = Field(description="Creation timestamp")


class NotificationListResponse(BaseResponse):
    """List of notifications response"""
    success: bool = Field(default=True)
    notifications: List[NotificationInfo] = Field(description="List of notifications")
    unread_count: int = Field(default=0, description="Number of unread notifications")
