"""
Tokens Router - FastAPI
Endpoints para buscar informações de tokens nas exchanges
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional
import logging
import asyncio
from bson import ObjectId

from src.api_fastapi.models import TokenInfo
from motor.motor_asyncio import AsyncIOMotorDatabase
from src.api_fastapi.database import get_database

logger = logging.getLogger(__name__)

router = APIRouter()



# ============================================
# TOKENS ENDPOINTS
# ============================================

@router.get("/tokens/{exchange_id}/{symbol}")
async def get_token_info(
    exchange_id: str,
    symbol: str,
    user_id: Optional[str] = Query(None, description="ID do usuário para usar credenciais"),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Busca informações completas de um token em uma exchange específica
    
    Args:
        exchange_id: ID da exchange (MongoDB ObjectId)
        symbol: Símbolo do token (ex: BTC, ETH, PEPE)
        user_id: ID do usuário (para usar credenciais se necessário)
        
    Returns:
        Informações detalhadas do token com preço, volume, icon, etc.
    """
    try:
        # Validar exchange_id
        if not ObjectId.is_valid(exchange_id):
            raise HTTPException(status_code=400, detail="Invalid exchange_id format")
        
        # Buscar exchange no MongoDB
        exchange = await db.exchanges.find_one({"_id": ObjectId(exchange_id)})
        
        if not exchange:
            raise HTTPException(status_code=404, detail=f"Exchange not found: {exchange_id}")
        
        ccxt_id = exchange.get("ccxt_id")
        
        # Usar serviço de preços (precisa ser async)
        from src.services.price_feed_service import PriceFeedService
        
        # Instanciar serviço
        price_service = PriceFeedService()
        
        # Buscar informações do token
        # TODO: Converter get_token_info para async
        # Por enquanto, usar run_in_executor para não bloquear
        loop = asyncio.get_event_loop()
        token_data = await loop.run_in_executor(
            None,
            price_service.get_token_info,
            ccxt_id,
            symbol,
            user_id
        )
        
        if not token_data or "error" in token_data:
            raise HTTPException(
                status_code=404,
                detail=token_data.get("error", f"Token {symbol} not found on {ccxt_id}")
            )
        
        return token_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching token info: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tokens/{exchange_id}/search")
async def search_tokens(
    exchange_id: str,
    query: str = Query(..., min_length=1, description="Termo de busca (mínimo 1 caractere)"),
    limit: int = Query(20, ge=1, le=100, description="Limite de resultados (1-100)"),
    user_id: Optional[str] = Query(None, description="ID do usuário"),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Busca tokens em uma exchange por nome ou símbolo
    
    Args:
        exchange_id: ID da exchange
        query: Termo de busca
        limit: Quantidade máxima de resultados
        user_id: ID do usuário (para usar credenciais)
        
    Returns:
        Lista de tokens que correspondem à busca
    """
    try:
        # Validar exchange_id
        if not ObjectId.is_valid(exchange_id):
            raise HTTPException(status_code=400, detail="Invalid exchange_id format")
        
        # Buscar exchange
        exchange = await db.exchanges.find_one({"_id": ObjectId(exchange_id)})
        
        if not exchange:
            raise HTTPException(status_code=404, detail=f"Exchange not found: {exchange_id}")
        
        ccxt_id = exchange.get("ccxt_id")
        
        # Usar CCXT async support
        import ccxt.async_support as ccxt_async
        
        # Obter classe da exchange
        exchange_class = getattr(ccxt_async, ccxt_id)
        
        # Instanciar exchange
        ccxt_exchange = exchange_class()
        
        # Se tiver user_id, buscar credenciais
        if user_id:
            user_doc = await db.user_exchanges.find_one({"user_id": user_id})
            
            if user_doc and "exchanges" in user_doc:
                for user_ex in user_doc["exchanges"]:
                    if user_ex["exchange_id"] == ObjectId(exchange_id):
                        # Descriptografar credenciais
                        from src.security.encryption import decrypt_credentials
                        
                        api_key = decrypt_credentials(
                            user_ex["api_key_encrypted"],
                            user_ex["api_secret_encrypted"]
                        )[0]
                        
                        api_secret = decrypt_credentials(
                            user_ex["api_key_encrypted"],
                            user_ex["api_secret_encrypted"]
                        )[1]
                        
                        ccxt_exchange.apiKey = api_key
                        ccxt_exchange.secret = api_secret
                        
                        if user_ex.get("passphrase_encrypted"):
                            passphrase = decrypt_credentials(
                                user_ex["passphrase_encrypted"],
                                ""
                            )[0]
                            ccxt_exchange.password = passphrase
                        
                        break
        
        try:
            # Carregar mercados
            await ccxt_exchange.load_markets()
            
            # Buscar tokens
            query_upper = query.upper()
            
            matching_tokens = []
            
            for symbol, market in ccxt_exchange.markets.items():
                base = market.get("base", "")
                quote = market.get("quote", "")
                
                # Verificar se query está no símbolo
                if query_upper in base or query_upper in symbol:
                    matching_tokens.append({
                        "symbol": base,
                        "pair": symbol,
                        "quote": quote,
                        "base": base,
                        "active": market.get("active", False)
                    })
                
                if len(matching_tokens) >= limit:
                    break
            
            return {
                "success": True,
                "exchange": ccxt_id,
                "query": query,
                "results": matching_tokens[:limit],
                "total": len(matching_tokens)
            }
            
        finally:
            # Fechar conexão
            await ccxt_exchange.close()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching tokens: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tokens/{exchange_id}/list")
async def list_all_tokens(
    exchange_id: str,
    quote_currency: Optional[str] = Query(None, description="Filtrar por moeda de cotação (ex: USDT, BTC)"),
    active_only: bool = Query(True, description="Apenas tokens ativos"),
    user_id: Optional[str] = Query(None),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Lista todos os tokens disponíveis em uma exchange
    
    Args:
        exchange_id: ID da exchange
        quote_currency: Filtrar por moeda de cotação
        active_only: Apenas tokens ativos
        user_id: ID do usuário
        
    Returns:
        Lista completa de tokens
    """
    try:
        # Validar exchange_id
        if not ObjectId.is_valid(exchange_id):
            raise HTTPException(status_code=400, detail="Invalid exchange_id format")
        
        # Buscar exchange
        exchange = await db.exchanges.find_one({"_id": ObjectId(exchange_id)})
        
        if not exchange:
            raise HTTPException(status_code=404, detail=f"Exchange not found: {exchange_id}")
        
        ccxt_id = exchange.get("ccxt_id")
        
        # Usar CCXT async support
        import ccxt.async_support as ccxt_async
        
        # Obter classe da exchange
        exchange_class = getattr(ccxt_async, ccxt_id)
        ccxt_exchange = exchange_class()
        
        # Se tiver user_id, buscar credenciais
        if user_id:
            user_doc = await db.user_exchanges.find_one({"user_id": user_id})
            
            if user_doc and "exchanges" in user_doc:
                for user_ex in user_doc["exchanges"]:
                    if user_ex["exchange_id"] == ObjectId(exchange_id):
                        from src.security.encryption import decrypt_credentials
                        
                        api_key, api_secret = decrypt_credentials(
                            user_ex["api_key_encrypted"],
                            user_ex["api_secret_encrypted"]
                        )
                        
                        ccxt_exchange.apiKey = api_key
                        ccxt_exchange.secret = api_secret
                        
                        if user_ex.get("passphrase_encrypted"):
                            passphrase, _ = decrypt_credentials(
                                user_ex["passphrase_encrypted"],
                                ""
                            )
                            ccxt_exchange.password = passphrase
                        
                        break
        
        try:
            # Carregar mercados
            await ccxt_exchange.load_markets()
            
            # Processar tokens
            tokens = []
            seen_bases = set()
            
            for symbol, market in ccxt_exchange.markets.items():
                base = market.get("base", "")
                quote = market.get("quote", "")
                is_active = market.get("active", False)
                
                # Aplicar filtros
                if active_only and not is_active:
                    continue
                
                if quote_currency and quote != quote_currency.upper():
                    continue
                
                # Evitar duplicatas
                if base in seen_bases:
                    continue
                
                seen_bases.add(base)
                
                tokens.append({
                    "symbol": base,
                    "quote": quote,
                    "active": is_active,
                    "pair": symbol
                })
            
            # Ordenar por símbolo
            tokens.sort(key=lambda x: x["symbol"])
            
            return {
                "success": True,
                "exchange": ccxt_id,
                "tokens": tokens,
                "total": len(tokens),
                "filters": {
                    "quote_currency": quote_currency,
                    "active_only": active_only
                }
            }
            
        finally:
            await ccxt_exchange.close()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing tokens: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
