"""
FastAPI Application - Multi-Exchange Trading System
Migração do Flask para FastAPI com performance otimizada
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import custom modules
from src.api_fastapi.database import lifespan, get_database
from src.api_fastapi.middleware import (
    RequestLoggingMiddleware,
    SecurityHeadersMiddleware,
    setup_exception_handlers
)
from src.api_fastapi.constants import APIConfig


# ============================================
# INITIALIZE FASTAPI APP
# ============================================

app = FastAPI(
    title=APIConfig.TITLE,
    description=APIConfig.DESCRIPTION,
    version=APIConfig.VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)


# ============================================
# CONFIGURE MIDDLEWARE
# ============================================

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, especificar domínios
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom middleware
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestLoggingMiddleware)

# Setup exception handlers
setup_exception_handlers(app)


# ============================================
# HEALTH CHECK ENDPOINTS
# ============================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": APIConfig.TITLE,
        "version": APIConfig.VERSION
    }


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": f"{APIConfig.TITLE} (FastAPI)",
        "version": APIConfig.VERSION,
        "docs": "/docs",
        "redoc": "/redoc"
    }


@app.get("/api/v1/metrics")
async def get_metrics():
    """Get system metrics"""
    from fastapi import HTTPException
    
    try:
        db = get_database()
        # Get MongoDB stats
        stats = await db.command("dbStats")
        
        return {
            "success": True,
            "database": {
                "name": db.name,
                "size_mb": round(stats.get("dataSize", 0) / (1024 * 1024), 2),
                "collections": stats.get("collections", 0)
            },
            "api": {
                "version": APIConfig.VERSION,
                "framework": "FastAPI",
                "async": True
            }
        }
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# IMPORT ROUTERS
# ============================================

from src.api_fastapi.routers import (
    exchanges, 
    tokens, 
    balances, 
    strategies, 
    orders, 
    positions, 
    notifications, 
    jobs
)

# Register routers
app.include_router(exchanges.router, prefix=APIConfig.PREFIX, tags=["Exchanges"])
app.include_router(tokens.router, prefix=APIConfig.PREFIX, tags=["Tokens"])
app.include_router(balances.router, prefix=APIConfig.PREFIX, tags=["Balances"])
app.include_router(strategies.router, prefix=APIConfig.PREFIX, tags=["Strategies"])
app.include_router(orders.router, prefix=APIConfig.PREFIX, tags=["Orders"])
app.include_router(positions.router, prefix=APIConfig.PREFIX, tags=["Positions"])
app.include_router(notifications.router, prefix=APIConfig.PREFIX, tags=["Notifications"])
app.include_router(jobs.router, prefix=APIConfig.PREFIX, tags=["Jobs"])


# ============================================
# DEVELOPMENT SERVER
# ============================================

if __name__ == "__main__":
    import uvicorn
    import os
    
    port = int(os.getenv("PORT", 8000))
    
    uvicorn.run(
        "fastapi_app:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )
