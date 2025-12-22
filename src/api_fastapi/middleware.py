"""
Custom Middleware for FastAPI Application
Handles logging, error tracking, and performance monitoring
"""

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from time import time
import logging

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log all requests and responses
    Tracks request duration and status codes
    """
    
    async def dispatch(self, request: Request, call_next):
        # Start timer
        start_time = time()
        
        # Log request
        logger.info(f"🔵 {request.method} {request.url.path}")
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate duration
            duration = time() - start_time
            duration_ms = round(duration * 1000, 2)
            
            # Log response
            status_emoji = "✅" if response.status_code < 400 else "❌"
            logger.info(
                f"{status_emoji} {request.method} {request.url.path} "
                f"-> {response.status_code} ({duration_ms}ms)"
            )
            
            # Add custom headers
            response.headers["X-Process-Time"] = str(duration_ms)
            
            return response
            
        except Exception as e:
            duration = time() - start_time
            duration_ms = round(duration * 1000, 2)
            
            logger.error(
                f"❌ {request.method} {request.url.path} "
                f"-> ERROR ({duration_ms}ms): {str(e)}",
                exc_info=True
            )
            
            # Return error response
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": "Internal server error",
                    "details": str(e)
                }
            )


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to handle errors consistently
    Ensures all errors return proper JSON responses
    """
    
    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except HTTPException as e:
            return JSONResponse(
                status_code=e.status_code,
                content={
                    "success": False,
                    "error": e.detail
                }
            )
        except Exception as e:
            logger.error(f"Unhandled exception: {e}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": "Internal server error",
                    "details": str(e)
                }
            )


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses
    """
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        return response


def setup_exception_handlers(app):
    """
    Setup custom exception handlers for the FastAPI app
    """
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handler for HTTPException"""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": exc.detail,
                "path": request.url.path
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handler for general exceptions"""
        logger.error(f"Unhandled exception on {request.url.path}: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "Internal server error",
                "details": str(exc),
                "path": request.url.path
            }
        )
