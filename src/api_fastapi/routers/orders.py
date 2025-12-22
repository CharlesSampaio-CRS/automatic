"""
Orders Router - FastAPI
Endpoints para execução de ordens de compra/venda
"""

from fastapi import APIRouter, HTTPException, Depends, Body
from typing import Optional
from bson import ObjectId
import logging
import asyncio

from src.api_fastapi.models import OrderCreate
from motor.motor_asyncio import AsyncIOMotorDatabase
from src.api_fastapi.database import get_database

logger = logging.getLogger(__name__)

router = APIRouter()



# ============================================
# ORDERS ENDPOINTS
# ============================================

@router.post("/orders/buy", status_code=201)
async def place_buy_order(
    data: OrderCreate,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Executa ordem de compra (BUY)
    
    Args:
        data: Dados da ordem (user_id, exchange_id, symbol, amount, order_type, price)
        
    Returns:
        Detalhes da ordem executada
    """
    try:
        # Validar exchange_id
        if not ObjectId.is_valid(data.exchange_id):
            raise HTTPException(status_code=400, detail="Invalid exchange_id format")
        
        # Buscar credenciais do usuário
        user_doc = await db.user_exchanges.find_one({"user_id": data.user_id})
        
        if not user_doc or "exchanges" not in user_doc:
            raise HTTPException(status_code=404, detail="User has no linked exchanges")
        
        # Encontrar exchange
        exchange_object_id = ObjectId(data.exchange_id)
        user_exchange = None
        
        for ex in user_doc["exchanges"]:
            if ex["exchange_id"] == exchange_object_id:
                user_exchange = ex
                break
        
        if not user_exchange:
            raise HTTPException(
                status_code=404,
                detail="Exchange not linked for this user"
            )
        
        if not user_exchange.get("is_active", True):
            raise HTTPException(status_code=400, detail="Exchange is disconnected")
        
        # Buscar exchange
        exchange = await db.exchanges.find_one({"_id": exchange_object_id})
        
        if not exchange:
            raise HTTPException(status_code=404, detail="Exchange not found")
        
        # Descriptografar credenciais
        from src.security.encryption import decrypt_credentials
        
        api_key, api_secret = decrypt_credentials(
            user_exchange["api_key_encrypted"],
            user_exchange["api_secret_encrypted"]
        )
        
        passphrase = None
        if user_exchange.get("passphrase_encrypted"):
            passphrase, _ = decrypt_credentials(
                user_exchange["passphrase_encrypted"],
                ""
            )
        
        # Executar ordem
        from src.services.order_execution_service import OrderExecutionService
        order_service = OrderExecutionService()
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            order_service.place_order,
            exchange.get("ccxt_id"),
            api_key,
            api_secret,
            passphrase,
            data.symbol,
            "buy",
            data.order_type,
            data.amount,
            data.price
        )
        
        if result.get("success"):
            # Salvar ordem no banco
            order_doc = {
                "user_id": data.user_id,
                "exchange_id": exchange_object_id,
                "strategy_id": ObjectId(data.strategy_id) if data.strategy_id else None,
                "symbol": data.symbol,
                "side": "buy",
                "type": data.order_type,
                "amount": data.amount,
                "price": data.price,
                "status": result.get("status", "filled"),
                "order_id": result.get("order_id"),
                "filled": result.get("filled", 0),
                "remaining": result.get("remaining", 0),
                "cost": result.get("cost", 0),
                "fee": result.get("fee"),
                "timestamp": result.get("timestamp"),
                "created_at": result.get("datetime")
            }
            
            insert_result = await db.orders.insert_one(order_doc)
            order_doc["_id"] = str(insert_result.inserted_id)
            order_doc["exchange_id"] = str(order_doc["exchange_id"])
            if order_doc.get("strategy_id"):
                order_doc["strategy_id"] = str(order_doc["strategy_id"])
            
            logger.info(f"✅ BUY order placed: {data.symbol} @ {data.amount}")
            
            return {
                "success": True,
                "message": "Buy order placed successfully",
                "order": order_doc
            }
        else:
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Failed to place buy order")
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error placing buy order: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/orders/sell", status_code=201)
async def place_sell_order(
    data: OrderCreate,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Executa ordem de venda (SELL)
    
    Args:
        data: Dados da ordem (user_id, exchange_id, symbol, amount, order_type, price)
        
    Returns:
        Detalhes da ordem executada
    """
    try:
        # Validar exchange_id
        if not ObjectId.is_valid(data.exchange_id):
            raise HTTPException(status_code=400, detail="Invalid exchange_id format")
        
        # Buscar credenciais do usuário
        user_doc = await db.user_exchanges.find_one({"user_id": data.user_id})
        
        if not user_doc or "exchanges" not in user_doc:
            raise HTTPException(status_code=404, detail="User has no linked exchanges")
        
        # Encontrar exchange
        exchange_object_id = ObjectId(data.exchange_id)
        user_exchange = None
        
        for ex in user_doc["exchanges"]:
            if ex["exchange_id"] == exchange_object_id:
                user_exchange = ex
                break
        
        if not user_exchange:
            raise HTTPException(
                status_code=404,
                detail="Exchange not linked for this user"
            )
        
        if not user_exchange.get("is_active", True):
            raise HTTPException(status_code=400, detail="Exchange is disconnected")
        
        # Buscar exchange
        exchange = await db.exchanges.find_one({"_id": exchange_object_id})
        
        if not exchange:
            raise HTTPException(status_code=404, detail="Exchange not found")
        
        # Descriptografar credenciais
        from src.security.encryption import decrypt_credentials
        
        api_key, api_secret = decrypt_credentials(
            user_exchange["api_key_encrypted"],
            user_exchange["api_secret_encrypted"]
        )
        
        passphrase = None
        if user_exchange.get("passphrase_encrypted"):
            passphrase, _ = decrypt_credentials(
                user_exchange["passphrase_encrypted"],
                ""
            )
        
        # Executar ordem
        from src.services.order_execution_service import OrderExecutionService
        order_service = OrderExecutionService()
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            order_service.place_order,
            exchange.get("ccxt_id"),
            api_key,
            api_secret,
            passphrase,
            data.symbol,
            "sell",
            data.order_type,
            data.amount,
            data.price
        )
        
        if result.get("success"):
            # Salvar ordem no banco
            order_doc = {
                "user_id": data.user_id,
                "exchange_id": exchange_object_id,
                "strategy_id": ObjectId(data.strategy_id) if data.strategy_id else None,
                "symbol": data.symbol,
                "side": "sell",
                "type": data.order_type,
                "amount": data.amount,
                "price": data.price,
                "status": result.get("status", "filled"),
                "order_id": result.get("order_id"),
                "filled": result.get("filled", 0),
                "remaining": result.get("remaining", 0),
                "cost": result.get("cost", 0),
                "fee": result.get("fee"),
                "timestamp": result.get("timestamp"),
                "created_at": result.get("datetime")
            }
            
            insert_result = await db.orders.insert_one(order_doc)
            order_doc["_id"] = str(insert_result.inserted_id)
            order_doc["exchange_id"] = str(order_doc["exchange_id"])
            if order_doc.get("strategy_id"):
                order_doc["strategy_id"] = str(order_doc["strategy_id"])
            
            logger.info(f"✅ SELL order placed: {data.symbol} @ {data.amount}")
            
            return {
                "success": True,
                "message": "Sell order placed successfully",
                "order": order_doc
            }
        else:
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Failed to place sell order")
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error placing sell order: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
