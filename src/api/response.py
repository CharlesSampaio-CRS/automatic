"""
Standard API Response Module

Provides consistent response format for all API endpoints
"""

from flask import jsonify
from datetime import datetime
import pytz

TZ = pytz.timezone("America/Sao_Paulo")


class APIResponse:
    """Standard API response formatter"""
    
    @staticmethod
    def success(data=None, message="Success", meta=None):
        """
        Success response
        
        Args:
            data: Response data (any type)
            message: Success message
            meta: Additional metadata (pagination, etc)
        
        Returns:
            Flask jsonify response with 200 status
        """
        response = {
            "success": True,
            "message": message,
            "data": data,
            "timestamp": datetime.now(TZ).isoformat(),
            "error": None
        }
        
        if meta:
            response["meta"] = meta
        
        return jsonify(response), 200
    
    @staticmethod
    def error(message="Error occurred", status_code=400, error_type=None, details=None):
        """
        Error response
        
        Args:
            message: Error message
            status_code: HTTP status code
            error_type: Type of error (validation, not_found, server_error, etc)
            details: Additional error details
        
        Returns:
            Flask jsonify response with specified status code
        """
        response = {
            "success": False,
            "message": message,
            "data": None,
            "timestamp": datetime.now(TZ).isoformat(),
            "error": {
                "type": error_type or "error",
                "message": message,
                "details": details
            }
        }
        
        return jsonify(response), status_code
    
    @staticmethod
    def not_found(resource="Resource", details=None):
        """
        Not found response (404)
        
        Args:
            resource: Resource name
            details: Additional details
        
        Returns:
            Flask jsonify response with 404 status
        """
        return APIResponse.error(
            message=f"{resource} not found",
            status_code=404,
            error_type="not_found",
            details=details
        )
    
    @staticmethod
    def validation_error(message="Validation failed", details=None):
        """
        Validation error response (400)
        
        Args:
            message: Validation error message
            details: Validation error details (field errors, etc)
        
        Returns:
            Flask jsonify response with 400 status
        """
        return APIResponse.error(
            message=message,
            status_code=400,
            error_type="validation_error",
            details=details
        )
    
    @staticmethod
    def server_error(message="Internal server error", details=None):
        """
        Server error response (500)
        
        Args:
            message: Error message
            details: Error details
        
        Returns:
            Flask jsonify response with 500 status
        """
        return APIResponse.error(
            message=message,
            status_code=500,
            error_type="server_error",
            details=details
        )
    
    @staticmethod
    def unauthorized(message="Unauthorized", details=None):
        """
        Unauthorized response (401)
        
        Args:
            message: Error message
            details: Error details
        
        Returns:
            Flask jsonify response with 401 status
        """
        return APIResponse.error(
            message=message,
            status_code=401,
            error_type="unauthorized",
            details=details
        )
    
    @staticmethod
    def forbidden(message="Forbidden", details=None):
        """
        Forbidden response (403)
        
        Args:
            message: Error message
            details: Error details
        
        Returns:
            Flask jsonify response with 403 status
        """
        return APIResponse.error(
            message=message,
            status_code=403,
            error_type="forbidden",
            details=details
        )


# Response format examples:
"""
SUCCESS RESPONSE:
{
    "success": true,
    "message": "Balance retrieved successfully",
    "data": {
        "total_balance": 1000.50,
        "available_balance": 950.25,
        "in_order": 50.25
    },
    "timestamp": "2025-12-04T10:30:00-03:00",
    "error": null,
    "meta": {
        "currency": "USDT"
    }
}

ERROR RESPONSE:
{
    "success": false,
    "message": "Configuration not found",
    "data": null,
    "timestamp": "2025-12-04T10:30:00-03:00",
    "error": {
        "type": "not_found",
        "message": "Configuration not found",
        "details": {
            "pair": "BTC/USDT",
            "reason": "No configuration exists for this pair"
        }
    }
}

VALIDATION ERROR RESPONSE:
{
    "success": false,
    "message": "Validation failed",
    "data": null,
    "timestamp": "2025-12-04T10:30:00-03:00",
    "error": {
        "type": "validation_error",
        "message": "Validation failed",
        "details": {
            "fields": {
                "pair": "Required field missing",
                "interval_hours": "Must be between 1 and 24"
            }
        }
    }
}
"""
