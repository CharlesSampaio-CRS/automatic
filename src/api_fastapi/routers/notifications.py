"""
Notifications Router - FastAPI
Endpoints para sistema de notificações
"""

from fastapi import APIRouter, HTTPException, Query, Depends, Body
from typing import Optional
from bson import ObjectId
from datetime import datetime
import logging
from motor.motor_asyncio import AsyncIOMotorDatabase
from src.api_fastapi.database import get_database

logger = logging.getLogger(__name__)

router = APIRouter()



# ============================================
# NOTIFICATIONS ENDPOINTS
# ============================================

@router.get("/notifications")
async def list_notifications(
    user_id: str = Query(..., description="ID do usuário"),
    is_read: Optional[bool] = Query(None, description="Filtrar por lidas/não lidas"),
    notification_type: Optional[str] = Query(None, description="Tipo de notificação"),
    limit: int = Query(50, ge=1, le=200, description="Limite de resultados"),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Lista notificações do usuário
    
    Args:
        user_id: ID do usuário
        is_read: Filtrar por status de leitura
        notification_type: Filtrar por tipo (order_filled, strategy_alert, etc)
        limit: Limite de resultados
        
    Returns:
        Lista de notificações
    """
    try:
        # Construir query
        query = {"user_id": user_id}
        
        if is_read is not None:
            query["is_read"] = is_read
        
        if notification_type:
            query["type"] = notification_type
        
        # Buscar notificações
        cursor = db.notifications.find(query).sort("created_at", -1).limit(limit)
        notifications = await cursor.to_list(length=limit)
        
        # Formatar IDs
        for notif in notifications:
            notif["_id"] = str(notif["_id"])
        
        # Contar não lidas
        unread_count = await db.notifications.count_documents({
            "user_id": user_id,
            "is_read": False
        })
        
        return {
            "success": True,
            "notifications": notifications,
            "total": len(notifications),
            "unread_count": unread_count
        }
        
    except Exception as e:
        logger.error(f"Error listing notifications: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/notifications")
async def create_notification(
    data: dict = Body(...),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Cria uma nova notificação
    
    Args:
        data: {
            "user_id": "string",
            "type": "string",
            "title": "string",
            "message": "string",
            "data": dict (optional)
        }
        
    Returns:
        Notificação criada
    """
    try:
        required_fields = ["user_id", "type", "title", "message"]
        missing = [f for f in required_fields if f not in data]
        
        if missing:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required fields: {', '.join(missing)}"
            )
        
        notification = {
            "user_id": data["user_id"],
            "type": data["type"],
            "title": data["title"],
            "message": data["message"],
            "data": data.get("data", {}),
            "is_read": False,
            "created_at": datetime.utcnow()
        }
        
        result = await db.notifications.insert_one(notification)
        notification["_id"] = str(result.inserted_id)
        
        logger.info(f"✅ Notification created for user {data['user_id']}: {data['title']}")
        
        return {
            "success": True,
            "notification": notification
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating notification: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/notifications/{notification_id}/read")
async def mark_notification_as_read(
    notification_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Marca notificação como lida
    
    Args:
        notification_id: ID da notificação
        
    Returns:
        Confirmação
    """
    try:
        if not ObjectId.is_valid(notification_id):
            raise HTTPException(status_code=400, detail="Invalid notification_id format")
        
        result = await db.notifications.update_one(
            {"_id": ObjectId(notification_id)},
            {
                "$set": {
                    "is_read": True,
                    "read_at": datetime.utcnow()
                }
            }
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Notification not found")
        
        return {
            "success": True,
            "message": "Notification marked as read"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error marking notification as read: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/notifications/read-all")
async def mark_all_as_read(
    user_id: str = Query(..., description="ID do usuário"),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Marca todas as notificações do usuário como lidas
    
    Args:
        user_id: ID do usuário
        
    Returns:
        Quantidade de notificações marcadas
    """
    try:
        result = await db.notifications.update_many(
            {
                "user_id": user_id,
                "is_read": False
            },
            {
                "$set": {
                    "is_read": True,
                    "read_at": datetime.utcnow()
                }
            }
        )
        
        return {
            "success": True,
            "message": f"{result.modified_count} notifications marked as read",
            "count": result.modified_count
        }
        
    except Exception as e:
        logger.error(f"Error marking all as read: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/notifications/{notification_id}")
async def delete_notification(
    notification_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Remove uma notificação
    
    Args:
        notification_id: ID da notificação
        
    Returns:
        Confirmação
    """
    try:
        if not ObjectId.is_valid(notification_id):
            raise HTTPException(status_code=400, detail="Invalid notification_id format")
        
        result = await db.notifications.delete_one({"_id": ObjectId(notification_id)})
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Notification not found")
        
        return {
            "success": True,
            "message": "Notification deleted"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting notification: {e}")
        raise HTTPException(status_code=500, detail=str(e))
