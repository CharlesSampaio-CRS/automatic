"""
Strategies Router - FastAPI
Endpoints para gerenciamento de estratégias de trading
"""

from fastapi import APIRouter, HTTPException, Query, Depends, Body
from typing import Optional, List
from bson import ObjectId
from datetime import datetime
import logging

from src.api_fastapi.models import StrategyCreate, StrategyResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from src.api_fastapi.database import get_database

logger = logging.getLogger(__name__)

router = APIRouter()



async def get_strategy_service(db: AsyncIOMotorDatabase = Depends(get_database)):
    """Get strategy service instance"""
    from src.services.strategy_service import StrategyService
    return StrategyService(db)


def invalidate_strategy_caches(user_id: str):
    """Invalida caches relacionados a strategies"""
    try:
        from src.utils.cache import get_strategies_cache
        cache = get_strategies_cache()
        cache.invalidate_pattern(f"*{user_id}*")
    except Exception as e:
        logger.warning(f"Failed to invalidate cache: {e}")


# ============================================
# STRATEGIES ENDPOINTS
# ============================================

@router.get("/strategies")
async def list_strategies(
    user_id: str = Query(..., description="ID do usuário"),
    exchange_id: Optional[str] = Query(None, description="Filtrar por exchange"),
    token: Optional[str] = Query(None, description="Filtrar por token"),
    is_active: Optional[bool] = Query(None, description="Filtrar por status"),
    force_refresh: bool = Query(False, description="Forçar atualização do cache"),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Lista estratégias do usuário com filtros opcionais
    
    Args:
        user_id: ID do usuário
        exchange_id: Filtrar por exchange
        token: Filtrar por token
        is_active: Filtrar por status (ativo/inativo)
        force_refresh: Ignorar cache
        
    Returns:
        Lista de estratégias do usuário
    """
    try:
        # Check cache
        from src.utils.cache import get_strategies_cache
        cache = get_strategies_cache()
        cache_key = f"list_{user_id}_{exchange_id}_{token}_{is_active}"
        
        if not force_refresh:
            is_valid, cached_data = cache.get(cache_key)
            if is_valid:
                cached_data['from_cache'] = True
                return cached_data
        
        # Construir query
        query = {"user_id": user_id}
        
        if exchange_id:
            if not ObjectId.is_valid(exchange_id):
                raise HTTPException(status_code=400, detail="Invalid exchange_id format")
            query["exchange_id"] = ObjectId(exchange_id)
        
        if token:
            query["token"] = token.upper()
        
        if is_active is not None:
            query["is_active"] = is_active
        
        # Buscar estratégias
        cursor = db.strategies.find(query).sort("created_at", -1)
        strategies = await cursor.to_list(length=1000)
        
        # Enriquecer com dados de exchange
        for strategy in strategies:
            exchange = await db.exchanges.find_one({"_id": strategy.get("exchange_id")})
            strategy["exchange_name"] = exchange.get("nome") if exchange else "Unknown"
            strategy["exchange_ccxt_id"] = exchange.get("ccxt_id") if exchange else None
            strategy["_id"] = str(strategy["_id"])
            strategy["exchange_id"] = str(strategy["exchange_id"])
        
        result = {
            "success": True,
            "strategies": strategies,
            "total": len(strategies),
            "from_cache": False
        }
        
        # Cache for 2 minutes
        cache.set(cache_key, result, ttl_seconds=120)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing strategies: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/strategies", status_code=201)
async def create_strategy(
    data: StrategyCreate,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Cria uma nova estratégia de trading
    
    Três modos suportados:
    1. Template Mode (RECOMENDADO): Usa template pré-configurado
    2. Custom Mode: Regras customizadas
    3. Legacy Mode: Take profit + Stop loss simples
    
    Args:
        data: Dados da estratégia
        
    Returns:
        Estratégia criada
    """
    try:
        import asyncio
        
        strategy_service = get_strategy_service()
        
        # Determinar modo de criação
        if data.template:
            # Template Mode
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                strategy_service.create_strategy,
                data.user_id,
                data.exchange_id,
                data.token,
                None,  # take_profit_percent
                None,  # stop_loss_percent
                None,  # buy_dip_percent
                data.template,
                None,  # rules
                data.is_active
            )
        elif data.rules:
            # Custom Mode
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                strategy_service.create_strategy,
                data.user_id,
                data.exchange_id,
                data.token,
                None,  # take_profit_percent
                None,  # stop_loss_percent
                None,  # buy_dip_percent
                None,  # template
                data.rules.dict() if data.rules else None,
                data.is_active
            )
        elif data.take_profit_percent and data.stop_loss_percent:
            # Legacy Mode
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                strategy_service.create_strategy,
                data.user_id,
                data.exchange_id,
                data.token,
                data.take_profit_percent,
                data.stop_loss_percent,
                data.buy_dip_percent,
                None,  # template
                None,  # rules
                data.is_active
            )
        else:
            raise HTTPException(
                status_code=400,
                detail='Provide either "template", "rules", or "take_profit_percent" + "stop_loss_percent"'
            )
        
        if result.get('success'):
            # Invalidate cache
            invalidate_strategy_caches(data.user_id)
            return result
        else:
            raise HTTPException(status_code=400, detail=result.get('error', 'Failed to create strategy'))
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating strategy: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/strategies/{strategy_id}")
async def get_strategy(
    strategy_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Busca detalhes de uma estratégia específica
    
    Args:
        strategy_id: ID da estratégia
        
    Returns:
        Detalhes completos da estratégia
    """
    try:
        if not ObjectId.is_valid(strategy_id):
            raise HTTPException(status_code=400, detail="Invalid strategy_id format")
        
        strategy = await db.strategies.find_one({"_id": ObjectId(strategy_id)})
        
        if not strategy:
            raise HTTPException(status_code=404, detail=f"Strategy not found: {strategy_id}")
        
        # Enriquecer com dados de exchange
        exchange = await db.exchanges.find_one({"_id": strategy.get("exchange_id")})
        
        strategy["_id"] = str(strategy["_id"])
        strategy["exchange_id"] = str(strategy["exchange_id"])
        strategy["exchange_name"] = exchange.get("nome") if exchange else "Unknown"
        strategy["exchange_ccxt_id"] = exchange.get("ccxt_id") if exchange else None
        
        return {
            "success": True,
            "strategy": strategy
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting strategy: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/strategies/{strategy_id}")
async def update_strategy(
    strategy_id: str,
    data: dict = Body(...),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Atualiza uma estratégia existente
    
    Args:
        strategy_id: ID da estratégia
        data: Campos a atualizar
        
    Returns:
        Estratégia atualizada
    """
    try:
        if not ObjectId.is_valid(strategy_id):
            raise HTTPException(status_code=400, detail="Invalid strategy_id format")
        
        strategy = await db.strategies.find_one({"_id": ObjectId(strategy_id)})
        
        if not strategy:
            raise HTTPException(status_code=404, detail=f"Strategy not found: {strategy_id}")
        
        # Campos permitidos para atualização
        allowed_fields = [
            'is_active', 'rules', 'take_profit_percent', 'stop_loss_percent',
            'buy_dip_percent', 'max_daily_loss', 'max_position_size'
        ]
        
        update_data = {k: v for k, v in data.items() if k in allowed_fields}
        
        if not update_data:
            raise HTTPException(status_code=400, detail="No valid fields to update")
        
        update_data['updated_at'] = datetime.utcnow()
        
        # Atualizar estratégia
        result = await db.strategies.update_one(
            {"_id": ObjectId(strategy_id)},
            {"$set": update_data}
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=400, detail="No changes made")
        
        # Buscar estratégia atualizada
        updated_strategy = await db.strategies.find_one({"_id": ObjectId(strategy_id)})
        updated_strategy["_id"] = str(updated_strategy["_id"])
        updated_strategy["exchange_id"] = str(updated_strategy["exchange_id"])
        
        # Invalidate cache
        invalidate_strategy_caches(strategy.get("user_id"))
        
        logger.info(f"✅ Strategy {strategy_id} updated")
        
        return {
            "success": True,
            "message": "Strategy updated successfully",
            "strategy": updated_strategy
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating strategy: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/strategies/{strategy_id}")
async def delete_strategy(
    strategy_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Remove uma estratégia
    
    Args:
        strategy_id: ID da estratégia
        
    Returns:
        Confirmação de remoção
    """
    try:
        if not ObjectId.is_valid(strategy_id):
            raise HTTPException(status_code=400, detail="Invalid strategy_id format")
        
        strategy = await db.strategies.find_one({"_id": ObjectId(strategy_id)})
        
        if not strategy:
            raise HTTPException(status_code=404, detail=f"Strategy not found: {strategy_id}")
        
        # Deletar estratégia
        result = await db.strategies.delete_one({"_id": ObjectId(strategy_id)})
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=500, detail="Failed to delete strategy")
        
        # Invalidate cache
        invalidate_strategy_caches(strategy.get("user_id"))
        
        logger.info(f"✅ Strategy {strategy_id} deleted")
        
        return {
            "success": True,
            "message": "Strategy deleted successfully",
            "strategy_id": strategy_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting strategy: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/strategies/{strategy_id}/check")
async def check_strategy(
    strategy_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Verifica condições de uma estratégia (dry run)
    
    Args:
        strategy_id: ID da estratégia
        
    Returns:
        Resultado da verificação (sinais de compra/venda)
    """
    try:
        import asyncio
        
        if not ObjectId.is_valid(strategy_id):
            raise HTTPException(status_code=400, detail="Invalid strategy_id format")
        
        strategy = await db.strategies.find_one({"_id": ObjectId(strategy_id)})
        
        if not strategy:
            raise HTTPException(status_code=404, detail=f"Strategy not found: {strategy_id}")
        
        # Usar strategy worker para checar
        from src.services.strategy_worker import StrategyWorker
        worker = StrategyWorker()
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            worker.check_strategy,
            str(strategy["_id"])
        )
        
        return {
            "success": True,
            "strategy_id": strategy_id,
            "check_result": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking strategy: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/strategies/{strategy_id}/stats")
async def get_strategy_stats(
    strategy_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Busca estatísticas de uma estratégia
    
    Args:
        strategy_id: ID da estratégia
        
    Returns:
        Estatísticas de performance (P&L, win rate, etc)
    """
    try:
        if not ObjectId.is_valid(strategy_id):
            raise HTTPException(status_code=400, detail="Invalid strategy_id format")
        
        strategy = await db.strategies.find_one({"_id": ObjectId(strategy_id)})
        
        if not strategy:
            raise HTTPException(status_code=404, detail=f"Strategy not found: {strategy_id}")
        
        # Buscar ordens relacionadas à estratégia
        orders_cursor = db.orders.find({"strategy_id": ObjectId(strategy_id)})
        orders = await orders_cursor.to_list(length=10000)
        
        # Calcular estatísticas
        total_orders = len(orders)
        filled_orders = [o for o in orders if o.get("status") == "filled"]
        
        total_profit_loss = sum(o.get("profit_loss", 0) for o in filled_orders)
        winning_trades = [o for o in filled_orders if o.get("profit_loss", 0) > 0]
        losing_trades = [o for o in filled_orders if o.get("profit_loss", 0) < 0]
        
        win_rate = (len(winning_trades) / len(filled_orders) * 100) if filled_orders else 0
        
        avg_win = sum(o.get("profit_loss", 0) for o in winning_trades) / len(winning_trades) if winning_trades else 0
        avg_loss = sum(o.get("profit_loss", 0) for o in losing_trades) / len(losing_trades) if losing_trades else 0
        
        stats = {
            "strategy_id": strategy_id,
            "total_orders": total_orders,
            "filled_orders": len(filled_orders),
            "pending_orders": total_orders - len(filled_orders),
            "profit_loss": round(total_profit_loss, 2),
            "win_rate": round(win_rate, 2),
            "winning_trades": len(winning_trades),
            "losing_trades": len(losing_trades),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "is_active": strategy.get("is_active", False),
            "created_at": strategy.get("created_at"),
            "last_check": strategy.get("last_check")
        }
        
        return {
            "success": True,
            "stats": stats
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting strategy stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/strategies/templates/list")
async def list_templates():
    """
    Lista templates de estratégias disponíveis
    
    Returns:
        Lista de templates com suas configurações
    """
    try:
        from src.services.strategy_service import STRATEGY_TEMPLATES
        from src.validators.strategy_rules_validator import StrategyRulesValidator
        
        templates = []
        
        for name, config in STRATEGY_TEMPLATES.items():
            # Buscar as regras do template
            rules = StrategyRulesValidator.get_template_rules(name)
            
            templates.append({
                "name": name,
                "display_name": config.get("name", name),
                "description": config.get("description", ""),
                "risk_level": config.get("risk_level", "unknown"),
                "recommended_for": config.get("recommended_for", ""),
                "features": config.get("features", []),
                "rules": rules
            })
        
        return {
            "success": True,
            "templates": templates,
            "total": len(templates)
        }
        
    except Exception as e:
        logger.error(f"Error listing templates: {e}")
        raise HTTPException(status_code=500, detail=str(e))
