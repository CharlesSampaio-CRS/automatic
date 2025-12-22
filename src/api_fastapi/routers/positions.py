"""
Positions Router - FastAPI
Endpoints para gerenciar posições abertas
"""

from fastapi import APIRouter, HTTPException, Query, Depends, Body
from typing import Optional
from bson import ObjectId
from datetime import datetime
import logging
import asyncio
from motor.motor_asyncio import AsyncIOMotorDatabase
from src.api_fastapi.database import get_database

logger = logging.getLogger(__name__)

router = APIRouter()



# ============================================
# POSITIONS ENDPOINTS
# ============================================

@router.get("/positions")
async def list_positions(
    user_id: str = Query(..., description="ID do usuário"),
    exchange_id: Optional[str] = Query(None, description="Filtrar por exchange"),
    symbol: Optional[str] = Query(None, description="Filtrar por símbolo"),
    is_open: Optional[bool] = Query(None, description="Filtrar por posições abertas"),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Lista posições do usuário
    
    Args:
        user_id: ID do usuário
        exchange_id: Filtrar por exchange
        symbol: Filtrar por símbolo
        is_open: Apenas posições abertas
        
    Returns:
        Lista de posições
    """
    try:
        # Construir query
        query = {"user_id": user_id}
        
        if exchange_id:
            if not ObjectId.is_valid(exchange_id):
                raise HTTPException(status_code=400, detail="Invalid exchange_id format")
            query["exchange_id"] = ObjectId(exchange_id)
        
        if symbol:
            query["symbol"] = symbol.upper()
        
        if is_open is not None:
            query["is_open"] = is_open
        
        # Buscar posições
        cursor = db.positions.find(query).sort("opened_at", -1)
        positions = await cursor.to_list(length=1000)
        
        # Enriquecer com dados de exchange
        for position in positions:
            exchange = await db.exchanges.find_one({"_id": position.get("exchange_id")})
            position["exchange_name"] = exchange.get("nome") if exchange else "Unknown"
            position["_id"] = str(position["_id"])
            position["exchange_id"] = str(position["exchange_id"])
            if position.get("strategy_id"):
                position["strategy_id"] = str(position["strategy_id"])
        
        return {
            "success": True,
            "positions": positions,
            "total": len(positions)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing positions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/positions/{position_id}")
async def get_position(
    position_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Busca detalhes de uma posição específica
    
    Args:
        position_id: ID da posição
        
    Returns:
        Detalhes da posição
    """
    try:
        if not ObjectId.is_valid(position_id):
            raise HTTPException(status_code=400, detail="Invalid position_id format")
        
        position = await db.positions.find_one({"_id": ObjectId(position_id)})
        
        if not position:
            raise HTTPException(status_code=404, detail=f"Position not found: {position_id}")
        
        # Enriquecer com dados de exchange
        exchange = await db.exchanges.find_one({"_id": position.get("exchange_id")})
        
        position["_id"] = str(position["_id"])
        position["exchange_id"] = str(position["exchange_id"])
        if position.get("strategy_id"):
            position["strategy_id"] = str(position["strategy_id"])
        position["exchange_name"] = exchange.get("nome") if exchange else "Unknown"
        
        return {
            "success": True,
            "position": position
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting position: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/positions/sync")
async def sync_positions(
    data: dict = Body(...),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Sincroniza posições abertas com a exchange
    
    Args:
        data: {"user_id": "string", "exchange_id": "string (optional)"}
        
    Returns:
        Posições sincronizadas
    """
    try:
        user_id = data.get("user_id")
        exchange_id = data.get("exchange_id")
        
        if not user_id:
            raise HTTPException(status_code=400, detail="user_id is required")
        
        # Buscar exchanges do usuário
        user_doc = await db.user_exchanges.find_one({"user_id": user_id})
        
        if not user_doc or "exchanges" not in user_doc:
            raise HTTPException(status_code=404, detail="User has no linked exchanges")
        
        # Filtrar exchanges
        user_exchanges = user_doc.get("exchanges", [])
        
        if exchange_id:
            try:
                exchange_object_id = ObjectId(exchange_id)
                user_exchanges = [
                    ex for ex in user_exchanges 
                    if ex.get("exchange_id") == exchange_object_id
                ]
            except:
                raise HTTPException(status_code=400, detail="Invalid exchange_id format")
        
        # Filtrar exchanges ativas
        active_exchanges = [ex for ex in user_exchanges if ex.get("is_active", True)]
        
        if not active_exchanges:
            return {
                "success": True,
                "message": "No active exchanges found",
                "synced_positions": []
            }
        
        # Sincronizar posições de cada exchange
        from src.services.position_service import PositionService
        position_service = PositionService()
        
        all_synced_positions = []
        
        for user_ex in active_exchanges:
            ex_id = user_ex.get("exchange_id")
            
            # Buscar exchange
            exchange = await db.exchanges.find_one({"_id": ex_id})
            
            if not exchange:
                continue
            
            # Descriptografar credenciais
            from src.security.encryption import decrypt_credentials
            
            api_key, api_secret = decrypt_credentials(
                user_ex["api_key_encrypted"],
                user_ex["api_secret_encrypted"]
            )
            
            passphrase = None
            if user_ex.get("passphrase_encrypted"):
                passphrase, _ = decrypt_credentials(
                    user_ex["passphrase_encrypted"],
                    ""
                )
            
            # Sincronizar
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                position_service.sync_positions,
                user_id,
                str(ex_id),
                exchange.get("ccxt_id"),
                api_key,
                api_secret,
                passphrase
            )
            
            if result.get("success"):
                all_synced_positions.extend(result.get("positions", []))
        
        return {
            "success": True,
            "synced_positions": all_synced_positions,
            "total": len(all_synced_positions)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error syncing positions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/positions/{position_id}/history")
async def get_position_history(
    position_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Busca histórico de uma posição (ordens relacionadas)
    
    Args:
        position_id: ID da posição
        
    Returns:
        Histórico de ordens da posição
    """
    try:
        if not ObjectId.is_valid(position_id):
            raise HTTPException(status_code=400, detail="Invalid position_id format")
        
        # Buscar posição
        position = await db.positions.find_one({"_id": ObjectId(position_id)})
        
        if not position:
            raise HTTPException(status_code=404, detail=f"Position not found: {position_id}")
        
        # Buscar ordens relacionadas
        orders_cursor = db.orders.find({
            "user_id": position.get("user_id"),
            "exchange_id": position.get("exchange_id"),
            "symbol": position.get("symbol")
        }).sort("timestamp", 1)
        
        orders = await orders_cursor.to_list(length=1000)
        
        # Formatar ordens
        for order in orders:
            order["_id"] = str(order["_id"])
            order["exchange_id"] = str(order["exchange_id"])
            if order.get("strategy_id"):
                order["strategy_id"] = str(order["strategy_id"])
        
        return {
            "success": True,
            "position_id": position_id,
            "symbol": position.get("symbol"),
            "orders": orders,
            "total_orders": len(orders)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting position history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/positions/{position_id}/close")
async def close_position(
    position_id: str,
    data: dict = Body(...),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Fecha uma posição aberta
    
    Args:
        position_id: ID da posição
        data: {"user_id": "string", "price": float (optional)}
        
    Returns:
        Posição fechada
    """
    try:
        if not ObjectId.is_valid(position_id):
            raise HTTPException(status_code=400, detail="Invalid position_id format")
        
        user_id = data.get("user_id")
        close_price = data.get("price")
        
        if not user_id:
            raise HTTPException(status_code=400, detail="user_id is required")
        
        # Buscar posição
        position = await db.positions.find_one({"_id": ObjectId(position_id)})
        
        if not position:
            raise HTTPException(status_code=404, detail=f"Position not found: {position_id}")
        
        if position.get("user_id") != user_id:
            raise HTTPException(status_code=403, detail="Unauthorized")
        
        if not position.get("is_open", True):
            raise HTTPException(status_code=400, detail="Position is already closed")
        
        # Calcular P&L
        entry_price = position.get("entry_price", 0)
        amount = position.get("amount", 0)
        
        if not close_price:
            # Buscar preço atual do mercado
            from src.services.price_feed_service import PriceFeedService
            price_service = PriceFeedService()
            
            exchange = await db.exchanges.find_one({"_id": position.get("exchange_id")})
            
            loop = asyncio.get_event_loop()
            token_data = await loop.run_in_executor(
                None,
                price_service.get_token_info,
                exchange.get("ccxt_id"),
                position.get("symbol"),
                user_id
            )
            
            close_price = token_data.get("current_price", entry_price)
        
        profit_loss = (close_price - entry_price) * amount
        profit_loss_percent = ((close_price - entry_price) / entry_price * 100) if entry_price > 0 else 0
        
        # Atualizar posição
        update_data = {
            "is_open": False,
            "closed_at": datetime.utcnow(),
            "close_price": close_price,
            "profit_loss": profit_loss,
            "profit_loss_percent": profit_loss_percent
        }
        
        await db.positions.update_one(
            {"_id": ObjectId(position_id)},
            {"$set": update_data}
        )
        
        # Buscar posição atualizada
        updated_position = await db.positions.find_one({"_id": ObjectId(position_id)})
        updated_position["_id"] = str(updated_position["_id"])
        updated_position["exchange_id"] = str(updated_position["exchange_id"])
        if updated_position.get("strategy_id"):
            updated_position["strategy_id"] = str(updated_position["strategy_id"])
        
        logger.info(f"✅ Position {position_id} closed. P&L: {profit_loss:.2f}")
        
        return {
            "success": True,
            "message": "Position closed successfully",
            "position": updated_position
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error closing position: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
