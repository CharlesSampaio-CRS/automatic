"""
Balances Router - FastAPI
Endpoints para consulta de saldos em exchanges
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional, List
from bson import ObjectId
import logging
import asyncio
import os
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

from src.api_fastapi.models import TokenBalance, ExchangeBalance
from motor.motor_asyncio import AsyncIOMotorDatabase
from src.api_fastapi.database import get_database
from src.services.balance_service import BalanceService
from pymongo import MongoClient

logger = logging.getLogger(__name__)

router = APIRouter()



# ============================================
# BALANCES ENDPOINTS
# ============================================

@router.get("/balances")
async def get_balances_by_query(
    user_id: str = Query(..., description="ID do usuário (obrigatório)"),
    exchange_id: Optional[str] = Query(None, description="Filtrar por exchange"),
    min_value_usd: float = Query(0.0, ge=0, description="Valor mínimo em USD"),
    include_zero: bool = Query(False, description="Incluir saldos zerados"),
    force_refresh: bool = Query(False, description="Forçar atualização do cache"),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Busca saldos consolidados de um usuário (query param)
    
    Args:
        user_id: ID do usuário (obrigatório)
        exchange_id: Filtrar por exchange específica
        min_value_usd: Filtrar saldos acima deste valor
        include_zero: Incluir saldos zerados
        force_refresh: Forçar atualização (ignorar cache)
        
    Returns:
        Saldos consolidados de todas as exchanges ou de uma específica
    """
    # Redirecionar para a função principal
    return await get_user_balances_path(
        user_id=user_id,
        exchange_id=exchange_id,
        min_value_usd=min_value_usd,
        include_zero=include_zero,
        db=db
    )


@router.get("/balances/{user_id}")
async def get_user_balances_path(
    user_id: str,
    exchange_id: Optional[str] = Query(None, description="Filtrar por exchange"),
    min_value_usd: float = Query(0.0, ge=0, description="Valor mínimo em USD"),
    include_zero: bool = Query(False, description="Incluir saldos zerados"),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Busca saldos consolidados REAIS de um usuário usando CCXT
    
    Args:
        user_id: ID do usuário
        exchange_id: Filtrar por exchange específica
        min_value_usd: Filtrar saldos acima deste valor
        include_zero: Incluir saldos zerados
        
    Returns:
        Saldos consolidados de todas as exchanges ou de uma específica
    """
    try:
        # Buscar documento do usuário no banco (async)
        user_doc = await db.user_exchanges.find_one({"user_id": user_id})
        
        if not user_doc or 'exchanges' not in user_doc or not user_doc['exchanges']:
            return {
                "success": True,
                "user_id": user_id,
                "exchanges": [],
                "total_exchanges": 0,
                "total_usd": 0.0,
                "from_cache": False,
                "timestamp": datetime.utcnow().isoformat(),
                "message": "Nenhuma exchange vinculada para este usuário"
            }
        
        # Filtrar apenas exchanges ativas (e opcionalmente por exchange_id)
        active_exchanges = [
            ex for ex in user_doc['exchanges'] 
            if ex.get('is_active', True) and (not exchange_id or str(ex['exchange_id']) == exchange_id)
        ]
        
        if not active_exchanges:
            return {
                "success": True,
                "user_id": user_id,
                "exchanges": [],
                "total_exchanges": 0,
                "total_usd": 0.0,
                "from_cache": False,
                "timestamp": datetime.utcnow().isoformat(),
                "message": "Nenhuma exchange ativa encontrada"
            }
        
        # Buscar informações das exchanges no banco
        # exchange_id pode ser ObjectId ou string, normalizar para ObjectId
        exchange_ids_list = []
        for ex in active_exchanges:
            eid = ex['exchange_id']
            if isinstance(eid, str):
                exchange_ids_list.append(ObjectId(eid))
            else:
                exchange_ids_list.append(eid)
        
        exchanges_cursor = db.exchanges.find({"_id": {"$in": exchange_ids_list}})
        exchanges_info = {ex['_id']: ex async for ex in exchanges_cursor}
        
        # Buscar saldos reais usando CCXT (em paralelo via ThreadPoolExecutor)
        exchanges_data = []
        total_global_usd = 0.0
        
        # Criar BalanceService com PyMongo (sync)
        mongo_client = MongoClient(os.getenv('MONGO_URI', 'mongodb://localhost:27017'))
        mongo_db = mongo_client['MultExchange']
        balance_service = BalanceService(mongo_db)
        
        # Função para buscar saldos de uma exchange (sync - roda em thread)
        def fetch_exchange_balance_sync(ex_data, exchange_info):
            return balance_service.fetch_single_exchange_balance(
                ex_data, 
                exchange_info, 
                include_changes=False
            )
        
        # Executar busca de saldos em paralelo
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor(max_workers=len(active_exchanges)) as executor:
            tasks = [
                loop.run_in_executor(
                    executor,
                    fetch_exchange_balance_sync,
                    ex_data,
                    exchanges_info.get(ex_data['exchange_id'], {})
                )
                for ex_data in active_exchanges
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Processar resultados
        for i, result in enumerate(results):
            ex_data = active_exchanges[i]
            exchange_id_curr = ex_data['exchange_id']
            exchange_info = exchanges_info.get(exchange_id_curr, {})
            
            if isinstance(result, Exception):
                logger.error(f"❌ Error fetching balances for {exchange_info.get('nome', exchange_id_curr)}: {result}")
                exchange_entry = {
                    "exchange_id": str(exchange_id_curr),  # Converter ObjectId para string
                    "exchange_name": exchange_info.get('nome', 'Desconhecida'),
                    "ccxt_id": exchange_info.get('ccxt_id', ''),
                    "icon": exchange_info.get('icon', ''),
                    "balances": [],
                    "total_usd": 0.0,
                    "error": str(result),
                    "success": False
                }
            elif result.get('success'):
                # Converter balances dict para lista
                balances_dict = result.get('balances', {})
                balances_list = []
                
                for currency, balance_data in balances_dict.items():
                    # Remover campos internos (_price_raw, _value_raw)
                    clean_balance = {k: v for k, v in balance_data.items() if not k.startswith('_')}
                    clean_balance['currency'] = currency
                    
                    # Aplicar filtros
                    value_usd_str = clean_balance.get('value_usd', '$0.00')
                    value_usd = float(value_usd_str.replace('$', '').replace(',', ''))
                    
                    if min_value_usd and value_usd < min_value_usd:
                        continue
                    
                    if not include_zero and clean_balance.get('total', 0) == 0:
                        continue
                    
                    balances_list.append(clean_balance)
                
                # Extrair total_usd (formato "$123.45" -> 123.45)
                total_usd_str = result.get('total_usd', '$0.00')
                total_usd = float(total_usd_str.replace('$', '').replace(',', ''))
                total_global_usd += total_usd
                
                exchange_entry = {
                    "exchange_id": str(exchange_id_curr),  # Converter ObjectId para string
                    "exchange_name": exchange_info.get('nome', 'Desconhecida'),
                    "ccxt_id": exchange_info.get('ccxt_id', ''),
                    "icon": exchange_info.get('icon', ''),
                    "balances": balances_list,
                    "total_usd": total_usd,
                    "success": True
                }
            else:
                # Falha na busca
                exchange_entry = {
                    "exchange_id": str(exchange_id_curr),  # Converter ObjectId para string
                    "exchange_name": exchange_info.get('nome', 'Desconhecida'),
                    "ccxt_id": exchange_info.get('ccxt_id', ''),
                    "icon": exchange_info.get('icon', ''),
                    "balances": [],
                    "total_usd": 0.0,
                    "error": result.get('error', 'Unknown error'),
                    "success": False
                }
            
            exchanges_data.append(exchange_entry)
        
        return {
            "success": True,
            "user_id": user_id,
            "exchanges": exchanges_data,
            "total_exchanges": len(exchanges_data),
            "total_usd": total_global_usd,
            "from_cache": False,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        logger.error(f"❌ Error fetching balances for {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching balances: {str(e)}")


# ============================================
# BALANCE HISTORY ENDPOINTS
# ============================================


@router.get("/history/evolution")
async def get_balance_evolution(
    user_id: str = Query(..., description="ID do usuário"),
    days: int = Query(7, ge=1, le=365, description="Número de dias para consultar"),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Retorna a evolução do saldo total do usuário ao longo do tempo
    
    Args:
        user_id: ID do usuário
        days: Número de dias para consultar (1-365)
        
    Returns:
        Lista com histórico de evolução do saldo
    """
    try:
        # Calcular data inicial
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Buscar histórico de saldos
        query = {
            "user_id": user_id,
            "timestamp": {"$gte": start_date}
        }
        
        cursor = db.balance_history.find(query).sort("timestamp", 1)
        history_records = await cursor.to_list(length=1000)
        
        # Formatar dados para o frontend
        evolution_data = []
        for record in history_records:
            evolution_data.append({
                "timestamp": record.get("timestamp").isoformat() if record.get("timestamp") else None,
                "total_usd": record.get("total_usd", 0.0),
                "total_brl": record.get("total_brl", 0.0),
                "exchanges_count": len(record.get("exchanges", []))
            })
        
        return {
            "success": True,
            "user_id": user_id,
            "days": days,
            "data_points": len(evolution_data),
            "evolution": evolution_data,
            "start_date": start_date.isoformat(),
            "end_date": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        logger.error(f"❌ Error fetching balance evolution for {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching balance evolution: {str(e)}")



@router.get("/balances/{user_id}/{exchange_id}")
async def get_exchange_balances(
    user_id: str,
    exchange_id: str,
    include_zero: bool = Query(False, description="Incluir saldos zerados"),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Busca saldos de uma exchange específica
    
    Args:
        user_id: ID do usuário
        exchange_id: ID da exchange
        include_zero: Incluir saldos zerados
        
    Returns:
        Saldos detalhados da exchange
    """
    try:
        # Usar BalanceService
        from src.services.balance_service import BalanceService
        
        balance_service = BalanceService(db)
        
        # Buscar saldos de uma exchange específica
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            balance_service.fetch_single_exchange_details,
            user_id,
            exchange_id,
            False  # include_changes
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error fetching exchange balances: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/balances/{user_id}/{exchange_id}_old")
async def get_exchange_balances_old(
    user_id: str,
    exchange_id: str,
    include_zero: bool = Query(False, description="Incluir saldos zerados"),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Busca saldos de uma exchange específica
    
    Args:
        user_id: ID do usuário
        exchange_id: ID da exchange
        include_zero: Incluir saldos zerados
        
    Returns:
        Saldos detalhados da exchange
    """
    try:
        # Validar exchange_id
        if not ObjectId.is_valid(exchange_id):
            raise HTTPException(status_code=400, detail="Invalid exchange_id format")
        
        exchange_object_id = ObjectId(exchange_id)
        
        # Buscar exchange linkada
        user_doc = await db.user_exchanges.find_one({"user_id": user_id})
        
        if not user_doc or "exchanges" not in user_doc:
            raise HTTPException(status_code=404, detail="User has no linked exchanges")
        
        # Encontrar exchange
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
        
        # Buscar detalhes da exchange
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
        
        # Buscar saldos
        from src.services.balance_service import BalanceService
        balance_service = BalanceService(db)
        
        loop = asyncio.get_event_loop()
        balance_data = await loop.run_in_executor(
            None,
            balance_service.fetch_balances,
            exchange.get("ccxt_id"),
            api_key,
            api_secret,
            passphrase
        )
        
        if not balance_data.get("success"):
            raise HTTPException(
                status_code=500,
                detail=balance_data.get("error", "Failed to fetch balances")
            )
        
        balances = balance_data.get("balances", [])
        
        # Aplicar filtro de zero
        if not include_zero:
            balances = [b for b in balances if b.get("total", 0.0) > 0]
        
        # Calcular total
        total_value_usd = sum(b.get("value_usd", 0.0) for b in balances)
        
        return {
            "success": True,
            "user_id": user_id,
            "exchange_id": exchange_id,
            "exchange_name": exchange.get("nome"),
            "ccxt_id": exchange.get("ccxt_id"),
            "balances": balances,
            "total_value_usd": round(total_value_usd, 2),
            "total_assets": len(balances)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching exchange balances: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/balances/{user_id}/asset/{symbol}")
async def get_asset_balance(
    user_id: str,
    symbol: str,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Busca saldo de um ativo específico em todas as exchanges
    
    Args:
        user_id: ID do usuário
        symbol: Símbolo do ativo (ex: BTC, ETH, USDT)
        
    Returns:
        Saldo do ativo consolidado em todas as exchanges
    """
    try:
        # Buscar exchanges linkadas
        user_doc = await db.user_exchanges.find_one({"user_id": user_id})
        
        if not user_doc or "exchanges" not in user_doc:
            return {
                "success": True,
                "user_id": user_id,
                "symbol": symbol,
                "exchanges": [],
                "total_balance": 0.0,
                "total_value_usd": 0.0
            }
        
        # Filtrar exchanges ativas
        active_exchanges = [
            ex for ex in user_doc.get("exchanges", [])
            if ex.get("is_active", True)
        ]
        
        from src.services.balance_service import BalanceService
        balance_service = BalanceService(db)
        
        symbol_upper = symbol.upper()
        asset_balances = []
        total_balance = 0.0
        total_value_usd = 0.0
        
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
            
            # Buscar saldos
            loop = asyncio.get_event_loop()
            balance_data = await loop.run_in_executor(
                None,
                balance_service.fetch_balances,
                exchange.get("ccxt_id"),
                api_key,
                api_secret,
                passphrase
            )
            
            if balance_data.get("success"):
                balances = balance_data.get("balances", [])
                
                # Procurar o ativo
                for bal in balances:
                    if bal.get("currency", "").upper() == symbol_upper:
                        asset_balances.append({
                            "exchange_id": str(ex_id),
                            "exchange_name": exchange.get("nome"),
                            "free": bal.get("free", 0.0),
                            "used": bal.get("used", 0.0),
                            "total": bal.get("total", 0.0),
                            "value_usd": bal.get("value_usd", 0.0)
                        })
                        
                        total_balance += bal.get("total", 0.0)
                        total_value_usd += bal.get("value_usd", 0.0)
                        break
        
        return {
            "success": True,
            "user_id": user_id,
            "symbol": symbol,
            "exchanges": asset_balances,
            "total_balance": total_balance,
            "total_value_usd": round(total_value_usd, 2),
            "exchanges_with_balance": len(asset_balances)
        }
        
    except Exception as e:
        logger.error(f"Error fetching asset balance: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/balances/{user_id}/history")
async def get_balance_history(
    user_id: str,
    exchange_id: Optional[str] = Query(None, description="Filtrar por exchange"),
    start_date: Optional[str] = Query(None, description="Data inicial (ISO format)"),
    end_date: Optional[str] = Query(None, description="Data final (ISO format)"),
    limit: int = Query(30, ge=1, le=365, description="Limite de registros"),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Busca histórico de snapshots de saldo
    
    Args:
        user_id: ID do usuário
        exchange_id: Filtrar por exchange
        start_date: Data inicial
        end_date: Data final
        limit: Limite de registros
        
    Returns:
        Histórico de saldos em ordem cronológica
    """
    try:
        # Construir query
        query = {"user_id": user_id}
        
        if exchange_id:
            if not ObjectId.is_valid(exchange_id):
                raise HTTPException(status_code=400, detail="Invalid exchange_id format")
            query["exchange_id"] = ObjectId(exchange_id)
        
        if start_date or end_date:
            date_filter = {}
            
            if start_date:
                from datetime import datetime
                date_filter["$gte"] = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            
            if end_date:
                from datetime import datetime
                date_filter["$lte"] = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            
            query["timestamp"] = date_filter
        
        # Buscar histórico
        cursor = db.balance_history.find(query).sort("timestamp", -1).limit(limit)
        history = await cursor.to_list(length=limit)
        
        # Formatar resposta
        formatted_history = []
        
        for record in history:
            # Buscar nome da exchange
            exchange = await db.exchanges.find_one({"_id": record.get("exchange_id")})
            
            formatted_history.append({
                "id": str(record.get("_id")),
                "exchange_id": str(record.get("exchange_id")),
                "exchange_name": exchange.get("nome") if exchange else "Unknown",
                "timestamp": record.get("timestamp").isoformat() if record.get("timestamp") else None,
                "total_value_usd": record.get("total_value_usd", 0.0),
                "assets_count": len(record.get("balances", [])),
                "top_assets": record.get("balances", [])[:5]  # Top 5 assets
            })
        
        return {
            "success": True,
            "user_id": user_id,
            "history": formatted_history,
            "total_records": len(formatted_history),
            "filters": {
                "exchange_id": exchange_id,
                "start_date": start_date,
                "end_date": end_date,
                "limit": limit
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching balance history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/balances/{user_id}/summary")
async def get_balance_summary(
    user_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Retorna resumo consolidado dos saldos do usuário
    
    Args:
        user_id: ID do usuário
        
    Returns:
        Resumo com valor total, distribuição por exchange, top assets
    """
    try:
        # Buscar exchanges linkadas
        user_doc = await db.user_exchanges.find_one({"user_id": user_id})
        
        if not user_doc or "exchanges" not in user_doc:
            return {
                "success": True,
                "user_id": user_id,
                "total_value_usd": 0.0,
                "exchanges_count": 0,
                "exchanges": [],
                "top_assets": []
            }
        
        # Buscar saldos de todas as exchanges ativas
        from src.services.balance_service import BalanceService
        balance_service = BalanceService(db)
        
        active_exchanges = [
            ex for ex in user_doc.get("exchanges", [])
            if ex.get("is_active", True)
        ]
        
        all_assets = {}
        exchanges_summary = []
        total_value_usd = 0.0
        
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
            
            # Buscar saldos
            loop = asyncio.get_event_loop()
            balance_data = await loop.run_in_executor(
                None,
                balance_service.fetch_balances,
                exchange.get("ccxt_id"),
                api_key,
                api_secret,
                passphrase
            )
            
            if balance_data.get("success"):
                balances = balance_data.get("balances", [])
                exchange_value = sum(b.get("value_usd", 0.0) for b in balances)
                
                exchanges_summary.append({
                    "exchange_id": str(ex_id),
                    "exchange_name": exchange.get("nome"),
                    "total_value_usd": exchange_value,
                    "assets_count": len(balances)
                })
                
                total_value_usd += exchange_value
                
                # Consolidar ativos
                for bal in balances:
                    symbol = bal.get("currency", "")
                    amount = bal.get("total", 0.0)
                    value_usd = bal.get("value_usd", 0.0)
                    
                    if symbol in all_assets:
                        all_assets[symbol]["total"] += amount
                        all_assets[symbol]["value_usd"] += value_usd
                    else:
                        all_assets[symbol] = {
                            "symbol": symbol,
                            "total": amount,
                            "value_usd": value_usd
                        }
        
        # Top 10 assets por valor
        top_assets = sorted(
            all_assets.values(),
            key=lambda x: x["value_usd"],
            reverse=True
        )[:10]
        
        return {
            "success": True,
            "user_id": user_id,
            "total_value_usd": round(total_value_usd, 2),
            "exchanges_count": len(exchanges_summary),
            "exchanges": exchanges_summary,
            "top_assets": top_assets,
            "total_assets": len(all_assets)
        }
        
    except Exception as e:
        logger.error(f"Error fetching balance summary: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
