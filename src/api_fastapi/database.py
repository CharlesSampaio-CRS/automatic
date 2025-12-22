"""
Database Connection and Management
Handles MongoDB connection lifecycle
"""

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from contextlib import asynccontextmanager
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class DatabaseManager:
    """MongoDB connection manager"""
    
    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.db: Optional[AsyncIOMotorDatabase] = None
        self._uri = os.getenv('MONGODB_URI')
        self._database_name = os.getenv('MONGODB_DATABASE', 'MultExchange')
        
    async def connect(self):
        """Establish MongoDB connection"""
        if self.client is not None:
            logger.warning("Database already connected")
            return
            
        try:
            self.client = AsyncIOMotorClient(
                self._uri,
                maxPoolSize=50,
                minPoolSize=10,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=10000,
                socketTimeoutMS=10000
            )
            
            self.db = self.client[self._database_name]
            
            # Test connection
            await self.client.server_info()
            logger.info(f"✅ Connected to MongoDB: {self._database_name}")
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to MongoDB: {e}")
            raise
    
    async def disconnect(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            self.client = None
            self.db = None
            logger.info("✅ MongoDB connection closed")
    
    def get_database(self) -> AsyncIOMotorDatabase:
        """Get database instance"""
        if self.db is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self.db
    
    async def ping(self) -> bool:
        """Check if database connection is alive"""
        try:
            await self.client.admin.command('ping')
            return True
        except Exception as e:
            logger.error(f"Database ping failed: {e}")
            return False


# Global database manager instance
db_manager = DatabaseManager()


@asynccontextmanager
async def lifespan(app):
    """
    FastAPI lifespan context manager
    Handles startup and shutdown events
    """
    # Startup
    logger.info("🚀 Starting FastAPI application...")
    await db_manager.connect()
    logger.info("✅ FastAPI application started successfully")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down FastAPI application...")
    await db_manager.disconnect()


def get_database() -> AsyncIOMotorDatabase:
    """
    Dependency function to get database instance
    Use this in FastAPI endpoints
    """
    return db_manager.get_database()


# Collection name constants
class Collections:
    """MongoDB collection names"""
    EXCHANGES = 'exchanges'
    USER_EXCHANGES = 'user_exchanges'
    BALANCE_HISTORY = 'balance_history'
    STRATEGIES = 'strategies'
    ORDERS = 'orders'
    POSITIONS = 'positions'
    NOTIFICATIONS = 'notifications'
    JOBS = 'jobs'
