"""
Exchanges Router - FastAPI
Endpoints para gerenciamento de exchanges
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional
from bson import ObjectId
from datetime import datetime
import logging
from motor.motor_asyncio import AsyncIOMotorDatabase

from src.api_fastapi.models import (
    ExchangeLink,
    ExchangeAction,
    ExchangeResponse,
    SuccessResponse,
    ErrorResponse
)
from src.api_fastapi.database import get_database

logger = logging.getLogger(__name__)

router = APIRouter()


def convert_objectid(document):
    """Converte ObjectId para string em documentos do MongoDB"""
    if isinstance(document, list):
        return [convert_objectid(doc) for doc in document]
    
    if isinstance(document, dict):
        for key, value in document.items():
            if isinstance(value, ObjectId):
                document[key] = str(value)
            elif isinstance(value, dict):
                document[key] = convert_objectid(value)
            elif isinstance(value, list):
                document[key] = convert_objectid(value)
    
    return document


# ============================================
# EXCHANGES ENDPOINTS
# ============================================

@router.get("/exchanges/available", response_model=List[ExchangeResponse])
async def get_available_exchanges(
    db=Depends(get_database)
):
    """
    Lista todas as exchanges disponíveis no sistema
    
    Returns:
        List de exchanges disponíveis
    """
    try:
        exchanges = await db.exchanges.find(
            {"is_active": True}
        ).sort("nome", 1).to_list(length=100)
        
        # Converter ObjectId para string
        return convert_objectid(exchanges)
        
    except Exception as e:
        logger.error(f"Error fetching available exchanges: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/exchanges/linked")
async def get_linked_exchanges(
    user_id: str = Query(..., description="ID do usuário"),
    db=Depends(get_database)
):
    """
    Lista exchanges linkadas de um usuário
    
    Args:
        user_id: ID do usuário
        
    Returns:
        Lista de exchanges linkadas
    """
    try:
        # Buscar documento do usuário
        user_doc = await db.user_exchanges.find_one({"user_id": user_id})
        
        if not user_doc or "exchanges" not in user_doc:
            return {
                "success": True,
                "exchanges": [],
                "message": "No linked exchanges found"
            }
        
        # Buscar detalhes de cada exchange
        exchanges_with_details = []
        
        for user_exchange in user_doc.get("exchanges", []):
            exchange_id = user_exchange.get("exchange_id")
            
            # Buscar detalhes da exchange
            exchange = await db.exchanges.find_one({"_id": exchange_id})
            
            if exchange:
                exchanges_with_details.append({
                    "exchange_id": str(exchange_id),
                    "nome": exchange.get("nome"),
                    "ccxt_id": exchange.get("ccxt_id"),
                    "url": exchange.get("url"),
                    "icon": exchange.get("icon"),
                    "is_active": user_exchange.get("is_active", True),
                    "linked_at": user_exchange.get("linked_at"),
                    "updated_at": user_exchange.get("updated_at")
                })
        
        return {
            "success": True,
            "exchanges": exchanges_with_details,
            "total": len(exchanges_with_details)
        }
        
    except Exception as e:
        logger.error(f"Error fetching linked exchanges: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/exchanges/link")
async def link_exchange(
    data: ExchangeLink,
    db=Depends(get_database)
):
    """
    Vincula uma exchange para um usuário
    
    Args:
        data: Dados de vínculo (user_id, exchange_id, api_key, api_secret)
        
    Returns:
        Confirmação de vínculo
    """
    try:
        # Validar ObjectId
        try:
            exchange_object_id = ObjectId(data.exchange_id)
        except:
            raise HTTPException(status_code=400, detail="Invalid exchange_id format")
        
        # Buscar exchange
        exchange = await db.exchanges.find_one({"_id": exchange_object_id})
        
        if not exchange:
            raise HTTPException(status_code=404, detail="Exchange not found")
        
        # Criptografar credenciais (importar de src.security.encryption)
        from src.security.encryption import encrypt_credentials
        
        encrypted_key, encrypted_secret = encrypt_credentials(
            data.api_key,
            data.api_secret
        )
        
        encrypted_passphrase = None
        if data.passphrase:
            encrypted_passphrase, _ = encrypt_credentials(data.passphrase, "")
        
        # Verificar se usuário já existe
        user_doc = await db.user_exchanges.find_one({"user_id": data.user_id})
        
        now = datetime.utcnow()
        
        if user_doc:
            # Verificar se exchange já está linkada
            for ex in user_doc.get("exchanges", []):
                if ex.get("exchange_id") == exchange_object_id:
                    raise HTTPException(
                        status_code=400,
                        detail="Exchange already linked for this user"
                    )
            
            # Adicionar exchange ao array
            await db.user_exchanges.update_one(
                {"user_id": data.user_id},
                {
                    "$push": {
                        "exchanges": {
                            "exchange_id": exchange_object_id,
                            "api_key_encrypted": encrypted_key,
                            "api_secret_encrypted": encrypted_secret,
                            "passphrase_encrypted": encrypted_passphrase,
                            "is_active": True,
                            "linked_at": now,
                            "updated_at": now
                        }
                    },
                    "$set": {"updated_at": now}
                }
            )
        else:
            # Criar novo documento
            await db.user_exchanges.insert_one({
                "user_id": data.user_id,
                "exchanges": [{
                    "exchange_id": exchange_object_id,
                    "api_key_encrypted": encrypted_key,
                    "api_secret_encrypted": encrypted_secret,
                    "passphrase_encrypted": encrypted_passphrase,
                    "is_active": True,
                    "linked_at": now,
                    "updated_at": now
                }],
                "created_at": now,
                "updated_at": now
            })
        
        logger.info(f"✅ {exchange['nome']} linked for user {data.user_id}")
        
        return {
            "success": True,
            "message": f"{exchange['nome']} linked successfully",
            "exchange": {
                "id": data.exchange_id,
                "name": exchange["nome"],
                "ccxt_id": exchange["ccxt_id"]
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error linking exchange: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/exchanges/connect")
async def connect_exchange(
    data: ExchangeAction,
    db=Depends(get_database)
):
    """
    Ativa/Reconecta uma exchange desconectada
    
    Args:
        data: user_id e exchange_id
        
    Returns:
        Confirmação de ativação
    """
    try:
        exchange_object_id = ObjectId(data.exchange_id)
        
        # Buscar documento do usuário
        user_doc = await db.user_exchanges.find_one({"user_id": data.user_id})
        
        if not user_doc or "exchanges" not in user_doc:
            raise HTTPException(status_code=404, detail="User has no linked exchanges")
        
        # Encontrar índice da exchange
        exchange_index = None
        exchange_data = None
        
        for idx, ex in enumerate(user_doc["exchanges"]):
            if ex["exchange_id"] == exchange_object_id:
                exchange_index = idx
                exchange_data = ex
                break
        
        if exchange_index is None:
            raise HTTPException(
                status_code=404,
                detail="Exchange not found in user's linked exchanges"
            )
        
        # Verificar se já está ativa
        if exchange_data.get("is_active", True):
            raise HTTPException(status_code=400, detail="Exchange is already connected")
        
        # Ativar exchange
        await db.user_exchanges.update_one(
            {"user_id": data.user_id},
            {
                "$set": {
                    f"exchanges.{exchange_index}.is_active": True,
                    f"exchanges.{exchange_index}.reconnected_at": datetime.utcnow(),
                    f"exchanges.{exchange_index}.updated_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                },
                "$unset": {
                    f"exchanges.{exchange_index}.disconnected_at": ""
                }
            }
        )
        
        # Buscar nome da exchange
        exchange = await db.exchanges.find_one({"_id": exchange_object_id})
        
        logger.info(f"✅ {exchange['nome']} activated for user {data.user_id}")
        
        return {
            "success": True,
            "message": f"{exchange['nome']} connected successfully",
            "exchange": {
                "id": data.exchange_id,
                "name": exchange["nome"],
                "is_active": True
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error connecting exchange: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/exchanges/disconnect")
async def disconnect_exchange(
    data: ExchangeAction,
    db=Depends(get_database)
):
    """
    Desconecta uma exchange (soft delete)
    
    Args:
        data: user_id e exchange_id
        
    Returns:
        Confirmação de desconexão
    """
    try:
        exchange_object_id = ObjectId(data.exchange_id)
        
        # Buscar documento do usuário
        user_doc = await db.user_exchanges.find_one({"user_id": data.user_id})
        
        if not user_doc or "exchanges" not in user_doc:
            raise HTTPException(status_code=404, detail="User has no linked exchanges")
        
        # Encontrar índice da exchange
        exchange_index = None
        exchange_data = None
        
        for idx, ex in enumerate(user_doc["exchanges"]):
            if ex["exchange_id"] == exchange_object_id:
                exchange_index = idx
                exchange_data = ex
                break
        
        if exchange_index is None:
            raise HTTPException(
                status_code=404,
                detail="Exchange not found in user's linked exchanges"
            )
        
        # Verificar se já está desconectada
        if not exchange_data.get("is_active", True):
            raise HTTPException(status_code=400, detail="Exchange is already disconnected")
        
        # Desativar exchange
        await db.user_exchanges.update_one(
            {"user_id": data.user_id},
            {
                "$set": {
                    f"exchanges.{exchange_index}.is_active": False,
                    f"exchanges.{exchange_index}.disconnected_at": datetime.utcnow(),
                    f"exchanges.{exchange_index}.updated_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        # Buscar nome da exchange
        exchange = await db.exchanges.find_one({"_id": exchange_object_id})
        
        logger.info(f"✅ {exchange['nome']} disconnected for user {data.user_id}")
        
        return {
            "success": True,
            "message": f"{exchange['nome']} disconnected successfully",
            "exchange": {
                "id": data.exchange_id,
                "name": exchange["nome"],
                "is_active": False
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error disconnecting exchange: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/exchanges/{exchange_id}")
async def get_exchange_info(
    exchange_id: str,
    include_fees: bool = Query(False, description="Incluir taxas da exchange"),
    include_markets: bool = Query(False, description="Incluir lista de mercados"),
    db=Depends(get_database)
):
    """
    Busca informações detalhadas de uma exchange
    
    Args:
        exchange_id: ID da exchange
        include_fees: Incluir taxas
        include_markets: Incluir mercados
        
    Returns:
        Informações da exchange
    """
    try:
        # Validar ObjectId
        if not ObjectId.is_valid(exchange_id):
            raise HTTPException(status_code=400, detail="Invalid exchange_id format")
        
        # Buscar exchange
        exchange = await db.exchanges.find_one({"_id": ObjectId(exchange_id)})
        
        if not exchange:
            raise HTTPException(status_code=404, detail=f"Exchange not found: {exchange_id}")
        
        # Dados básicos
        exchange_info = {
            "_id": str(exchange["_id"]),
            "nome": exchange.get("nome"),
            "ccxt_id": exchange.get("ccxt_id"),
            "url": exchange.get("url"),
            "icon": exchange.get("icon"),
            "pais_de_origem": exchange.get("pais_de_origem"),
            "is_active": exchange.get("is_active", True),
            "requires_passphrase": exchange.get("requires_passphrase", False)
        }
        
        # Se solicitado, buscar info adicional via CCXT
        if include_fees or include_markets:
            import ccxt
            
            ccxt_id = exchange.get("ccxt_id")
            exchange_class = getattr(ccxt, ccxt_id)
            ccxt_exchange = exchange_class()
            
            ccxt_exchange.load_markets()
            
            if include_fees:
                exchange_info["fees"] = {
                    "trading": ccxt_exchange.fees.get("trading", {}),
                    "funding": ccxt_exchange.fees.get("funding", {})
                }
            
            if include_markets:
                markets = ccxt_exchange.markets
                exchange_info["markets"] = {
                    "total": len(markets),
                    "symbols": sorted(list(markets.keys()))[:100]
                }
        
        return {
            "success": True,
            "exchange": exchange_info
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting exchange info: {e}")
        raise HTTPException(status_code=500, detail=str(e))
