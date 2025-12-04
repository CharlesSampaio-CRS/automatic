import os
import sys
import pytz
import time
import threading
from datetime import datetime
from flask import Flask, jsonify, request
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.clients.exchange import MexcClient
from src.config.bot_config import BUSINESS_HOURS_START, BUSINESS_HOURS_END, SCHEDULE_INTERVAL_HOURS
from src.utils.number_formatter import format_usdt, format_percent
from src.services.config_service import config_service
from src.services.job_manager import initialize_job_manager
from src.database.mongodb_connection import connection_mongo
from src.api.response import APIResponse  # ✨ NEW: Standardized API responses

# Carrega variáveis do arquivo .env
load_dotenv()

# Conecta ao MongoDB para logs de execução
try:
    execution_logs_db = connection_mongo("ExecutionLogs")
    print("OK MongoDB ExecutionLogs connected successfully!", flush=True)
except Exception as e:
    execution_logs_db = None
    print(f"ERROR connecting MongoDB ExecutionLogs: {e}", flush=True)

API_KEY = os.getenv('API_KEY')
API_SECRET = os.getenv('API_SECRET')

COUNTDOWN_INTERVAL_SECONDS = SCHEDULE_INTERVAL_HOURS * 3600

MSG_OUTSIDE_BUSINESS_HOURS = "Outside business hours. Order not executed."
MSG_SCHEDULED_ORDER_EXECUTED = "Order executed:"

app = Flask(__name__)

TZ = pytz.timezone("America/Sao_Paulo")

scheduler = BackgroundScheduler(timezone=TZ)

def get_current_hour():
    return datetime.now(TZ).hour

def _get_Tranding_recommendation(change_percent, spread_percent, volume):
    """
    Gera recomendação de Tranding baseada em análise técnica simples
    
    Args:
        change_percent: Variação percentual de 24h
        spread_percent: Spread percentual (diferença entre bid e ask)
        volume: Volume de 24h em USDT
    
    Returns:
        str: Recomendação textual
    """
    recommendations = []
    
    # Análise de spread
    if spread_percent < 0.3:
        recommendations.append(" Spread baixo (favorável)")
    elif spread_percent < 1.0:
        recommendations.append("⚠️ Spread médio (aceitável)")
    else:
        recommendations.append(" Spread alto (desfavorável)")
    
    # Análise de tendência
    if change_percent > 10:
        recommendations.append("📈 Forte alta (considere venda)")
    elif change_percent > 5:
        recommendations.append("📈 Alta moderada")
    elif change_percent > 0:
        recommendations.append("➡️ Leve alta")
    elif change_percent > -5:
        recommendations.append("➡️ Leve queda")
    elif change_percent > -10:
        recommendations.append("📉 Queda moderada (considere compra)")
    else:
        recommendations.append("📉 Forte queda (oportunidade?)")
    
    # Análise de liquidez
    if volume > 100000:
        recommendations.append("💧 Alta liquidez")
    elif volume > 10000:
        recommendations.append("💦 Liquidez média")
    else:
        recommendations.append("⚠️ Baixa liquidez (cuidado)")
    
    return " | ".join(recommendations)

def scheduled_order():
    """Execução AUTOMÁTICA via scheduler"""
    current_hour = get_current_hour()
    if BUSINESS_HOURS_START <= current_hour < BUSINESS_HOURS_END:
        mexc_client = MexcClient(API_KEY, API_SECRET)
        data = mexc_client.create_order(execution_type="scheduled")  #  SCHEDULED
        print(f"{MSG_SCHEDULED_ORDER_EXECUTED} {data}")
        print(f"⏰ Próxima execução em {SCHEDULE_INTERVAL_HOURS} horas")
    else:
        print(MSG_OUTSIDE_BUSINESS_HOURS)

def countdown_timer(interval):
    """
    Timer que mostra countdown até próxima execução
    NOTA: Este timer é apenas para manter a thread ativa.
    Os jobs reais são gerenciados pelo DynamicJobManager no MongoDB.
    """
    while True:
        time.sleep(interval)
        # Mantém a thread viva (jobs reais são gerenciados pelo scheduler)


# ========== HOME ==========

@app.route("/")
def home():
    """Health check"""
    return APIResponse.success(
        data={
            "name": "Maverick - Trading Bot",
            "version": "2.1.2",
            "status": "running"
        },
        message="API is running"
    )

# ========== BALANCE ==========

@app.route("/balance", methods=["GET"])
def balance():
    """
    Get total balance in USDT
    
    Returns standardized response with balance information
    """
    try:
        mexc_client = MexcClient(API_KEY, API_SECRET)
        balance_data = mexc_client.get_total_assets_in_USDT()
        
        return APIResponse.success(
            data=balance_data,
            message="Balance retrieved successfully"
        )
    except Exception as e:
        return APIResponse.server_error(
            message="Failed to retrieve balance",
            details={
                "error": str(e),
                "error_type": type(e).__name__
            }
        )

# ========== PRICE ==========

@app.route("/price", methods=["GET"])
def get_price_by_params():
    """
    Get current price of a trading pair (via query params)
    
    Query params:
        - pair: Trading pair (ex: REKT/USDT, BTC/USDT)
    
    Example: GET /price?pair=REKT/USDT
    """
    try:
        pair = request.args.get('pair')
        
        if not pair:
            return APIResponse.validation_error(
                message="Query param 'pair' is required",
                details={
                    "example": "/price?pair=REKT/USDT",
                    "required_params": ["pair"]
                }
            )
        
        pair_formatted = pair.upper()
        mexc_client = MexcClient(API_KEY, API_SECRET)
        ticker = mexc_client.client.fetch_ticker(pair_formatted)
        
        price_data = {
            "pair": pair_formatted,
            "current": ticker.get('last'),
            "bid": ticker.get('bid'),
            "ask": ticker.get('ask'),
            "high_24h": ticker.get('high'),
            "low_24h": ticker.get('low'),
            "volume_24h": ticker.get('baseVolume'),
            "change_24h": ticker.get('percentage')
        }
        
        return APIResponse.success(
            data=price_data,
            message="Price retrieved successfully"
        )
    except Exception as e:
        return APIResponse.server_error(
            message="Failed to retrieve price",
            details={
                "pair": pair if 'pair' in locals() else None,
                "error": str(e),
                "error_type": type(e).__name__
            }
        )

@app.route("/price/<pair>", methods=["GET"])
def get_price_by_path(pair):
    """
    Get current price of a trading pair (via path)
    
    Path param:
        - pair: Trading pair (ex: REKT-USDT or REKT/USDT)
    
    Example: GET /price/REKT-USDT
    """
    try:
        # Accepts both REKT-USDT and REKT/USDT (encoded as REKT%2FUSDT)
        pair_formatted = pair.replace('%2F', '/').replace('-', '/').upper()
        
        mexc_client = MexcClient(API_KEY, API_SECRET)
        ticker = mexc_client.client.fetch_ticker(pair_formatted)
        
        price_data = {
            "pair": pair_formatted,
            "current": ticker.get('last'),
            "bid": ticker.get('bid'),
            "ask": ticker.get('ask'),
            "high_24h": ticker.get('high'),
            "low_24h": ticker.get('low'),
            "volume_24h": ticker.get('baseVolume'),
            "change_24h": ticker.get('percentage')
        }
        
        return APIResponse.success(
            data=price_data,
            message="Price retrieved successfully"
        )
    except Exception as e:
        return APIResponse.server_error(
            message=f"Failed to retrieve price for {pair}",
            details={
                "pair": pair,
                "pair_formatted": pair_formatted if 'pair_formatted' in locals() else None,
                "error": str(e),
                "error_type": type(e).__name__
            }
        )

@app.route("/prices", methods=["POST"])
def get_multiple_prices():
    """
    Get prices for multiple trading pairs
    
    Body JSON:
    {
        "pairs": ["REKT/USDT", "BTC/USDT", "ETH/USDT"]
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'pairs' not in data:
            return APIResponse.validation_error(
                message="Field 'pairs' is required",
                details={
                    "required_fields": ["pairs"],
                    "example": {"pairs": ["REKT/USDT", "BTC/USDT"]}
                }
            )
        
        pairs = data['pairs']
        
        if not isinstance(pairs, list):
            return APIResponse.validation_error(
                message="Field 'pairs' must be an array",
                details={
                    "received_type": type(pairs).__name__,
                    "expected_type": "array"
                }
            )
        
        mexc_client = MexcClient(API_KEY, API_SECRET)
        prices = {}
        errors = {}
        
        for pair in pairs:
            try:
                pair_formatted = pair.upper()
                ticker = mexc_client.client.fetch_ticker(pair_formatted)
                
                prices[pair_formatted] = {
                    "current": ticker.get('last'),
                    "bid": ticker.get('bid'),
                    "ask": ticker.get('ask'),
                    "high_24h": ticker.get('high'),
                    "low_24h": ticker.get('low'),
                    "volume_24h": ticker.get('baseVolume'),
                    "change_24h": ticker.get('percentage')
                }
            except Exception as e:
                errors[pair_formatted if 'pair_formatted' in locals() else pair] = str(e)
        
        response_data = {
            "prices": prices,
            "total_requested": len(pairs),
            "total_success": len(prices),
            "total_errors": len(errors)
        }
        
        if errors:
            response_data["errors"] = errors
        
        return APIResponse.success(
            data=response_data,
            message=f"Prices retrieved: {len(prices)}/{len(pairs)} successful"
        )
        
    except Exception as e:
        return APIResponse.server_error(
            message="Failed to retrieve prices",
            details={
                "error": str(e),
                "error_type": type(e).__name__
            }
        )

# ========== ORDER ==========

@app.route("/order", methods=["POST"])
def order():
    """
    Executa ordem MANUAL completa (BUY + SELL) para um símbolo específico
    
    Comportamento:
    1. Executa COMPRA se houver saldo USDT disponível e condições forem atendidas
    2. Verifica HOLDINGS e executa VENDA se condições de lucro forem atendidas
    3. Retorna resultados combinados de compra e venda
    
    Body JSON:
    {
        "pair": "REKT/USDT"           // opcional - par específico para operar
    }
    
    Response:
    {
        "status": "success",
        "buy_result": { ... },      // Resultado da compra
        "sell_result": { ... },     // Resultado da venda
        "execution_type": "manual",
        "summary": { ... }          // Resumo consolidado
    }
    """
    try:
        data = request.get_json() or {}
        pair = data.get('pair')
        
        # Busca configuração do MongoDB se pair fornecido
        config = None
        if pair:
            config = config_service.get_symbol_config(pair.upper())
            if not config:
                return jsonify({
                    "status": "error",
                    "message": f"Configuração de {pair.upper()} não encontrada no MongoDB"
                }), 404
        
        # Inicializa cliente MEXC com config
        mexc_client = MexcClient(API_KEY, API_SECRET, config)
        
        # Header
        print(f"\n{'='*80}")
        print(f"EXECUÇÃO MANUAL" + (f" - {pair.upper()}" if pair else ""))
        print(f"{'='*80}\n")
        
        # Etapa 1: Compra
        print("[1/3] Verificando oportunidades de compra...")
        buy_result = mexc_client.create_order(execution_type="manual")
        
        # Etapa 2: Venda
        print("\n[2/3] Verificando oportunidades de venda...")
        sell_result = mexc_client.check_and_execute_sells(symbol=pair)
        
        # Etapa 3: Informações de mercado
        print("\n[3/3] Coletando informações de mercado...")
        market_info = {}
        
        if pair:
            try:
                # Busca informações detalhadas do par
                ticker = mexc_client.client.fetch_ticker(pair.upper())
                
                # Calcula taxas
                last_price = float(ticker.get('last', 0))
                bid_price = float(ticker.get('bid', 0))
                ask_price = float(ticker.get('ask', 0))
                spread = ask_price - bid_price if ask_price and bid_price else 0
                spread_percent = (spread / last_price * 100) if last_price > 0 else 0
                
                # Volume e variação 24h
                volume_24h = float(ticker.get('quoteVolume', 0))
                high_24h = float(ticker.get('high', 0))
                low_24h = float(ticker.get('low', 0))
                open_24h = float(ticker.get('open', 0))
                change_24h = last_price - open_24h if open_24h > 0 else 0
                
                # Calcula variação de 24h usando OHLCV (mais preciso)
                change_percent_24h = mexc_client.get_variation_24h(pair.upper())
                if change_percent_24h is None:
                    # Fallback para o cálculo do ticker
                    change_percent_24h = ((last_price - open_24h) / open_24h * 100) if open_24h > 0 else 0
                
                # Calcula variação de 1 hora usando a função corrigida
                change_percent_1h = mexc_client.get_variation_1h(pair.upper())
                if change_percent_1h is None:
                    change_percent_1h = 0
                
                # Busca variações em múltiplos timeframes
                multi_variations = mexc_client.get_multi_timeframe_variations(pair.upper())
                
                market_info = {
                    "pair": pair.upper(),
                    "current_price": last_price,
                    "bid_price": bid_price,
                    "ask_price": ask_price,
                    "spread": {
                        "value": round(spread, 10),
                        "percent": round(spread_percent, 4),
                        "status": "🟢 Baixo" if spread_percent < 0.5 else "🟡 Médio" if spread_percent < 1.0 else "🔴 Alto"
                    },
                    "24h_stats": {
                        "high": high_24h,
                        "low": low_24h,
                        "open": open_24h,
                        "change": change_24h,
                        "change_percent": round(change_percent_24h, 2),
                        "volume_usdt": round(volume_24h, 2),
                        "volatility": round(((high_24h - low_24h) / low_24h * 100), 2) if low_24h > 0 else 0
                    },
                    "1h_stats": {
                        "change_percent": round(change_percent_1h, 2)
                    },
                    "multi_timeframe": multi_variations if multi_variations else {},
                    "Tranding_fees": {
                        "maker_fee": 0.0,  # MEXC: 0% maker fee
                        "taker_fee": 0.0,  # MEXC: 0% taker fee
                        "estimated_buy_cost": round(last_price * 1.0000, 10),  # Sem taxa
                        "estimated_sell_return": round(last_price * 1.0000, 10)  # Sem taxa
                    },
                    "market_analysis": {
                        "trend": "📈 Alta" if change_percent_24h > 0 else "📉 Queda" if change_percent_24h < 0 else "➡️ Lateral",
                        "momentum": "🔥 Forte" if abs(change_percent_24h) > 10 else "⚡ Moderado" if abs(change_percent_24h) > 5 else "😴 Fraco",
                        "liquidity": "💧 Alta" if volume_24h > 100000 else "💦 Média" if volume_24h > 10000 else "💧 Baixa",
                        "recommendation": _get_Tranding_recommendation(change_percent_24h, spread_percent, volume_24h)
                    }
                }
                
                print(f"   > Preço: ${last_price:.10f}")
                print(f"   > Variação 1h: {change_percent_1h:+.2f}% | 24h: {change_percent_24h:+.2f}%")
                if multi_variations:
                    print(f"   > Multi-timeframe: 5m: {multi_variations.get('var_5m', 'N/A'):+}% | 15m: {multi_variations.get('var_15m', 'N/A'):+}% | 30m: {multi_variations.get('var_30m', 'N/A'):+}% | 4h: {multi_variations.get('var_4h', 'N/A'):+}%")
                print(f"   > Volume 24h: ${volume_24h:,.0f}")
                
            except Exception as e:
                print(f"   ! Erro: {e}")
                market_info = {
                    "error": str(e),
                    "message": "Não foi possível obter informações de mercado"
                }
        
        # Resumo final
        summary = {
            "buy_executed": buy_result.get('status') == 'success',
            "sell_executed": sell_result.get('status') == 'success',
            "total_invested": buy_result.get('total_invested', 0) if buy_result.get('status') == 'success' else 0,
            "total_profit": sell_result.get('total_profit', 0) if sell_result.get('status') == 'success' else 0,
            "net_result": (sell_result.get('total_profit', 0) if sell_result.get('status') == 'success' else 0) - 
                          (buy_result.get('total_invested', 0) if buy_result.get('status') == 'success' else 0)
        }
        
        print(f"\n{'='*80}")
        print(f"RESUMO: ", end="")
        results = []
        if summary['buy_executed']:
            results.append(f"Compra: ${summary['total_invested']:.2f}")
        if summary['sell_executed']:
            results.append(f"Venda: ${summary['total_profit']:.2f}")
        if not results:
            results.append("Nenhuma operação executada")
        print(" | ".join(results))
        if summary['net_result'] != 0:
            print(f"   Resultado líquido: ${summary['net_result']:.2f}")
        print(f"{'='*80}\n")
        
        # Salva log de execução completo no MongoDB
        if execution_logs_db is not None:
            try:
                execution_log = {
                    "execution_type": "manual",
                    "executed_by": "user",
                    "timestamp": datetime.now().isoformat(),
                    "pair": pair if pair else "all",
                    
                    # Resumo da execução (valores formatados)
                    "summary": {
                        "buy_executed": summary['buy_executed'],
                        "sell_executed": summary['sell_executed'],
                        "total_invested": format_usdt(summary['total_invested']),
                        "total_profit": format_usdt(summary['total_profit']),
                        "net_result": format_usdt(summary['net_result'])
                    },
                    
                    # Resultado da compra
                    "buy_details": {
                        "status": buy_result.get('status'),
                        "message": buy_result.get('message'),
                        "symbols_analyzed": buy_result.get('symbols_analyzed', 0),
                        "orders_executed": buy_result.get('orders_executed', 0),
                        "total_invested": format_usdt(buy_result.get('total_invested', 0))
                    } if buy_result.get('status') else None,
                    
                    # Resultado da venda
                    "sell_details": {
                        "status": sell_result.get('status'),
                        "message": sell_result.get('message'),
                        "holdings_checked": sell_result.get('holdings_checked', 0),
                        "sells_executed": len(sell_result.get('sells_executed', [])),
                        "total_profit": format_usdt(sell_result.get('total_profit', 0))
                    } if sell_result.get('status') else None,
                    
                    # Informações de mercado
                    "market_info": market_info if market_info and 'error' not in market_info else None
                }
                
                execution_logs_db.insert_one(execution_log)
                print(f"   > Log de execução salvo no banco")
            except Exception as log_error:
                print(f"   ! Erro ao salvar log: {log_error}")
        
        return jsonify({
            "status": "success",
            "buy_result": buy_result,
            "sell_result": sell_result,
            "market_info": market_info,
            "execution_type": "manual",
            "summary": summary,
            "message": "Ordem manual executada - Compra e Venda verificadas"
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            "status": "error",
            "message": f"Erro ao executar ordem: {str(e)}"
        }), 500


# ========== CONFIGS ==========

@app.route("/configs", methods=["GET"])
def get_all_configs():
    """
    Lista TODAS as configurações de símbolos (MongoDB)
    
    Query params:
        - enabled_only: true/false (default: false)
    
    Response:
    {
        "status": "success",
        "total": 2,
        "configs": [ {...}, {...} ]
    }
    """
    enabled_only = request.args.get('enabled_only', 'false').lower() == 'true'
    configs = config_service.get_all_configs(enabled_only=enabled_only)
    
    return jsonify({
        "status": "success",
        "total": len(configs),
        "configs": configs
    })

@app.route("/configs/<pair>", methods=["GET"])
def get_config_by_pair(pair):
    """
    Busca configuração de um símbolo específico (MongoDB)
    
    Exemplo: GET /configs/REKT/USDT
    
    Response:
    {
        "status": "success",
        "config": { ... }
    }
    """
    # Substitui / por barra para URL encoding
    pair_formatted = pair.replace('%2F', '/').upper()
    
    config = config_service.get_symbol_config(pair_formatted)
    
    if config:
        return jsonify({
            "status": "success",
            "config": config
        })
    else:
        return jsonify({
            "status": "error",
            "message": f"Configuração de {pair_formatted} não encontrada"
        }), 404

@app.route("/configs", methods=["POST"])
def create_config():
    """
    Cria nova configuração para um símbolo (MongoDB)
    
    Body JSON exemplo:
    {
        "pair": "BTC/USDT",
        "enabled": true,
        "schedule": {
            "interval_hours": 4,
            "business_hours_start": 9,
            "business_hours_end": 23,
            "enabled": true
        },
        "limits": {
            "min_value_per_order": 20,
            "allocation_percentage": 30
        },
        "Tranding_strategy": {
            "type": "buy_levels",
            "min_price_variation": 1.0,
            "levels": [
                {"price_drop_percent": 1.0, "allocation_percent": 20},
                {"price_drop_percent": 3.0, "allocation_percent": 30}
            ]
        },
        "sell_strategy": {
            "type": "profit_levels",
            "levels": [
                {"profit_percent": 2.0, "sell_percent": 30},
                {"profit_percent": 5.0, "sell_percent": 50}
            ]
        }
    }
    
    Response:
    {
        "status": "success",
        "message": "Configuração criada com sucesso",
        "config": { ... }
    }
    """
    data = request.get_json()
    
    if not data:
        return jsonify({
            "status": "error",
            "message": "Body JSON é obrigatório"
        }), 400
    
    success, message, config = config_service.create_symbol_config(data)
    
    if success:
        return jsonify({
            "status": "success",
            "message": message,
            "config": config
        }), 201
    else:
        return jsonify({
            "status": "error",
            "message": message
        }), 400

@app.route("/configs/<pair>", methods=["PUT"])
def update_config_by_pair(pair):
    """
    Atualiza configuração de um símbolo (MongoDB)
    
    Exemplo: PUT /configs/REKT/USDT
    
    Body JSON (parcial):
    {
        "enabled": false,
        "schedule": {
            "interval_hours": 6
        }
    }
    
    Response:
    {
        "status": "success",
        "message": "Configuração atualizada",
        "config": { ... }
    }
    """
    data = request.get_json()
    
    if not data:
        return jsonify({
            "status": "error",
            "message": "Body JSON é obrigatório"
        }), 400
    
    pair_formatted = pair.replace('%2F', '/').upper()
    success, message = config_service.update_symbol_config(pair_formatted, data)
    
    if success:
        updated_config = config_service.get_symbol_config(pair_formatted)
        return jsonify({
            "status": "success",
            "message": message,
            "config": updated_config
        })
    else:
        return jsonify({
            "status": "error",
            "message": message
        }), 404

@app.route("/configs/<pair>", methods=["DELETE"])
def delete_config_by_pair(pair):
    """
    Remove configuração de um símbolo (MongoDB)
    
    Exemplo: DELETE /configs/REKT/USDT
    
    Response:
    {
        "status": "success",
        "message": "Configuração removida"
    }
    """
    pair_formatted = pair.replace('%2F', '/').upper()
    success, message = config_service.delete_symbol_config(pair_formatted)
    
    if success:
        return jsonify({
            "status": "success",
            "message": message
        })
    else:
        return jsonify({
            "status": "error",
            "message": message
        }), 404

# ========== ESTRATÉGIA 1H ==========

@app.route("/configs/<pair>/strategy-1h", methods=["GET"])
def get_strategy_1h_config(pair):
    """
    Retorna configuração da estratégia de 1h para um símbolo
    
    Exemplo: GET /configs/REKT/USDT/strategy-1h
    
    Response:
    {
        "status": "success",
        "pair": "REKT/USDT",
        "strategy_1h": {
            "enabled": true,
            "levels": [...],
            "risk_management": {...}
        }
    }
    """
    pair_formatted = pair.replace('%2F', '/').upper()
    
    # Busca configuração do símbolo
    config = config_service.get_symbol_config(pair_formatted)
    
    if not config:
        return jsonify({
            "status": "error",
            "message": f"Configuração não encontrada para {pair_formatted}"
        }), 404
    
    strategy_1h = config.get('strategy_1h', {
        "enabled": False,
        "levels": [],
        "risk_management": {}
    })
    
    return jsonify({
        "status": "success",
        "pair": pair_formatted,
        "strategy_1h": strategy_1h
    })

@app.route("/configs/<pair>/strategy-1h", methods=["PUT"])
def update_strategy_1h_config(pair):
    """
    Atualiza configuração da estratégia de 1h para um símbolo
    
    Exemplo: PUT /configs/REKT/USDT/strategy-1h
    Body:
    {
        "enabled": true,
        "levels": [
            {
                "name": "Scalp Leve",
                "variation_threshold": -2.0,
                "percentage_of_balance": 5,
                "description": "Compra pequena em queda rápida de 2%"
            }
        ],
        "risk_management": {
            "stop_loss_percent": -3.0,
            "cooldown_minutes": 15,
            "max_trades_per_hour": 3,
            "max_position_size_percent": 10.0
        }
    }
    
    Response:
    {
        "status": "success",
        "message": "Estratégia 1h atualizada",
        "pair": "REKT/USDT",
        "strategy_1h": {...}
    }
    """
    pair_formatted = pair.replace('%2F', '/').upper()
    data = request.get_json()
    
    # Busca configuração atual
    config = config_service.get_symbol_config(pair_formatted)
    
    if not config:
        return jsonify({
            "status": "error",
            "message": f"Configuração não encontrada para {pair_formatted}"
        }), 404
    
    # Valida campos obrigatórios
    if 'enabled' not in data:
        return jsonify({
            "status": "error",
            "message": "Campo 'enabled' é obrigatório"
        }), 400
    
    # Atualiza strategy_1h
    strategy_1h = {
        "enabled": data.get('enabled', False),
        "levels": data.get('levels', []),
        "risk_management": data.get('risk_management', {})
    }
    
    # Valida configuração usando schema
    from src.models.config_schema import validate_config
    config_copy = config.copy()
    config_copy['strategy_1h'] = strategy_1h
    
    is_valid, error_msg = validate_config(config_copy)
    if not is_valid:
        return jsonify({
            "status": "error",
            "message": f"Configuração inválida: {error_msg}"
        }), 400
    
    # Atualiza no MongoDB
    success, message = config_service.update_symbol_config(pair_formatted, {
        'strategy_1h': strategy_1h
    })
    
    if success:
        return jsonify({
            "status": "success",
            "message": "Estratégia 1h atualizada com sucesso",
            "pair": pair_formatted,
            "strategy_1h": strategy_1h
        })
    else:
        return jsonify({
            "status": "error",
            "message": message
        }), 500

@app.route("/configs/<pair>/strategy-1h/toggle", methods=["POST"])
def toggle_strategy_1h(pair):
    """
    Liga/desliga rapidamente a estratégia de 1h para um símbolo
    
    Exemplo: POST /configs/REKT/USDT/strategy-1h/toggle
    Body:
    {
        "enabled": true
    }
    
    Response:
    {
        "status": "success",
        "message": "Estratégia 1h ativada",
        "pair": "REKT/USDT",
        "enabled": true
    }
    """
    pair_formatted = pair.replace('%2F', '/').upper()
    data = request.get_json()
    
    if 'enabled' not in data:
        return jsonify({
            "status": "error",
            "message": "Campo 'enabled' é obrigatório"
        }), 400
    
    enabled = bool(data['enabled'])
    
    # Busca configuração atual
    config = config_service.get_symbol_config(pair_formatted)
    
    if not config:
        return jsonify({
            "status": "error",
            "message": f"Configuração não encontrada para {pair_formatted}"
        }), 404
    
    # Atualiza apenas o campo enabled
    strategy_1h = config.get('strategy_1h', {})
    strategy_1h['enabled'] = enabled
    
    success, message = config_service.update_symbol_config(pair_formatted, {
        'strategy_1h': strategy_1h
    })
    
    if success:
        action = "ativada" if enabled else "desativada"
        return jsonify({
            "status": "success",
            "message": f"Estratégia 1h {action} com sucesso",
            "pair": pair_formatted,
            "enabled": enabled
        })
    else:
        return jsonify({
            "status": "error",
            "message": message
        }), 500

# ========== JOBS ==========

@app.route("/health", methods=["GET"])
def health_check():
    """Health check completo do sistema"""
    from src.services.job_manager import job_manager
    
    checks = {}
    is_healthy = True
    is_degraded = False
    
    # 1. Verifica Scheduler
    try:
        scheduler_running = scheduler.running
        scheduler_state = str(scheduler.state)
        checks["scheduler"] = {
            "status": "ok" if scheduler_running else "error",
            "running": scheduler_running,
            "state": scheduler_state
        }
        if not scheduler_running:
            is_healthy = False
    except Exception as e:
        checks["scheduler"] = {
            "status": "error",
            "error": str(e)
        }
        is_healthy = False
    
    # 2. Verifica MongoDB ExecutionLogs
    try:
        if execution_logs_db is not None:
            # Tenta fazer uma operação simples
            execution_logs_db.count_documents({}, limit=1)
            checks["mongodb_logs"] = {
                "status": "ok",
                "connected": True
            }
        else:
            checks["mongodb_logs"] = {
                "status": "error",
                "connected": False,
                "message": "execution_logs_db is None"
            }
            is_degraded = True
    except Exception as e:
        checks["mongodb_logs"] = {
            "status": "error",
            "error": str(e)
        }
        is_degraded = True
    
    # 3. Verifica Jobs Ativos
    try:
        if job_manager:
            jobs_status = job_manager.get_active_jobs_status()
            total_jobs = jobs_status.get('total_jobs', 0)
            checks["jobs"] = {
                "status": "ok" if total_jobs > 0 else "warning",
                "total_active": total_jobs,
                "jobs_list": [j['pair'] for j in jobs_status.get('jobs', [])]
            }
            if total_jobs == 0:
                is_degraded = True
        else:
            checks["jobs"] = {
                "status": "error",
                "message": "job_manager not initialized"
            }
            is_healthy = False
    except Exception as e:
        checks["jobs"] = {
            "status": "error",
            "error": str(e)
        }
        is_degraded = True
    
    # 4. Verifica API Keys
    try:
        api_key_set = bool(API_KEY and len(API_KEY) > 10)
        api_secret_set = bool(API_SECRET and len(API_SECRET) > 10)
        checks["api_credentials"] = {
            "status": "ok" if (api_key_set and api_secret_set) else "error",
            "api_key_set": api_key_set,
            "api_secret_set": api_secret_set
        }
        if not (api_key_set and api_secret_set):
            is_healthy = False
    except Exception as e:
        checks["api_credentials"] = {
            "status": "error",
            "error": str(e)
        }
        is_healthy = False
    
    # Determina status final
    if not is_healthy:
        overall_status = "unhealthy"
    elif is_degraded:
        overall_status = "degraded"
    else:
        overall_status = "healthy"
    
    health_data = {
        "status": overall_status,
        "version": SYSTEM_VERSION,
        "build_date": SYSTEM_BUILD_DATE,
        "checks": checks
    }
    
    # Usa resposta padronizada
    if overall_status == "unhealthy":
        return APIResponse.error(
            message="System is unhealthy",
            status_code=503,
            error_type="service_unavailable",
            details=health_data
        )
    elif overall_status == "degraded":
        return APIResponse.success(
            data=health_data,
            message="System is running with some degraded services"
        )
    else:
        return APIResponse.success(
            data=health_data,
            message="System is healthy"
        )


@app.route("/jobs", methods=["GET"])
def get_all_jobs():
    """Lista todos os jobs ativos"""
    from src.services.job_manager import job_manager
    
    if not job_manager:
        return jsonify({
            "status": "error",
            "message": "Job manager não inicializado"
        }), 500
    
    status = job_manager.get_active_jobs_status()
    
    return jsonify({
        "status": "success",
        **status
    })

@app.route("/jobs", methods=["POST"])
def manage_jobs():
    """Gerencia jobs com actions: start, stop ou reload"""
    from src.services.job_manager import job_manager
    
    if not job_manager:
        return jsonify({
            "status": "error",
            "message": "Job manager não inicializado"
        }), 500
    
    data = request.get_json()
    
    if not data or 'action' not in data:
        return jsonify({
            "status": "error",
            "message": "Campo 'action' é obrigatório (start, stop, reload)"
        }), 400
    
    action = data['action'].lower()
    pairs = data.get('pairs', [])
    
    # RELOAD: Recarrega todos os jobs do MongoDB
    if action == 'reload':
        added, removed = job_manager.reload_all_jobs()
        return jsonify({
            "status": "success",
            "message": "Jobs recarregados do MongoDB",
            "details": {
                "jobs_added": added,
                "jobs_removed": removed
            }
        })
    
    # START: Inicia jobs
    elif action == 'start':
        if not pairs:
            return jsonify({
                "status": "error",
                "message": "Campo 'pairs' é obrigatório para action=start"
            }), 400
        
        results = []
        for pair in pairs:
            pair_formatted = pair.upper()
            success, message = job_manager.add_job_for_symbol(pair_formatted)
            results.append({
                "pair": pair_formatted,
                "success": success,
                "message": message
            })
        
        success_count = sum(1 for r in results if r['success'])
        
        return jsonify({
            "status": "success" if success_count > 0 else "error",
            "message": f"{success_count}/{len(pairs)} jobs iniciados",
            "details": results
        })
    
    # STOP: Para jobs
    elif action == 'stop':
        # Se não especificar pairs, para TODOS
        if not pairs:
            status = job_manager.get_active_jobs_status()
            pairs = [job['pair'] for job in status.get('jobs', [])]
        
        if not pairs:
            return jsonify({
                "status": "success",
                "message": "Nenhum job ativo para parar"
            })
        
        results = []
        for pair in pairs:
            pair_formatted = pair.upper()
            success, message = job_manager.remove_job_for_symbol(pair_formatted)
            results.append({
                "pair": pair_formatted,
                "success": success,
                "message": message
            })
        
        success_count = sum(1 for r in results if r['success'])
        
        return jsonify({
            "status": "success" if success_count > 0 else "error",
            "message": f"{success_count}/{len(pairs)} jobs parados",
            "details": results
        })
    
    else:
        return jsonify({
            "status": "error",
            "message": f"Action inválida: {action}. Use: start, stop ou reload"
        }), 400

# ========== FIM DOS ENDPOINTS ==========

# Versão do sistema
SYSTEM_VERSION = "1.0.0"
SYSTEM_BUILD_DATE = "2025-12-03"

# ========== INICIALIZAÇÃO (RODA EM LOCAL E PRODUÇÃO) ==========
print("\n" + "="*80, flush=True)
print("MAVERICK - Automatic Trading Bot", flush=True)
print("="*80, flush=True)
print(f"VERSION: {SYSTEM_VERSION}", flush=True)
print(f"BUILD:   {SYSTEM_BUILD_DATE}", flush=True)
print(f"TZ:      {TZ}", flush=True)
print(f"TIME:    {datetime.now(TZ).strftime('%d/%m/%Y %H:%M:%S')}", flush=True)
print("="*80, flush=True)

# Inicializa scheduler
try:
    scheduler.start()
    print("OK Scheduler started successfully", flush=True)
    print(f"   State: {scheduler.state}", flush=True)
    print(f"   Running: {scheduler.running}", flush=True)
except Exception as e:
    print(f"ERROR starting Scheduler: {e}", flush=True)
    import traceback
    traceback.print_exc()

# Inicializa job manager
job_mgr = initialize_job_manager(scheduler, API_KEY, API_SECRET)
print("OK Job Manager initialized", flush=True)

# Carrega jobs do MongoDB
added, removed = job_mgr.reload_all_jobs()

print("\n" + "="*80, flush=True)
print("CONFIGURED JOBS", flush=True)
print("="*80, flush=True)

if added == 0:
    print("WARNING No jobs found", flush=True)
    print("INFO Configure via: POST /configs", flush=True)
else:
    print(f"OK {added} active job{'s' if added != 1 else ''}\n", flush=True)
    
    status = job_mgr.get_active_jobs_status()
    for idx, job_info in enumerate(status.get('jobs', []), 1):
        pair = job_info['pair']
        interval_minutes = job_info.get('interval_minutes')
        interval_hours = job_info.get('interval_hours')
        next_run = job_info.get('next_run')
        
        # Formata intervalo
        if interval_minutes:
            interval_display = f"{interval_minutes} min"
        elif interval_hours:
            interval_display = f"{interval_hours}h"
        else:
            interval_display = "?"
        
        print(f"{idx}. PAIR {pair}", flush=True)
        print(f"   INTERVAL: {interval_display}", flush=True)
        if next_run:
            # Formata next_run
            if isinstance(next_run, str):
                # Se for string, tenta converter
                try:
                    next_run_dt = datetime.fromisoformat(next_run.replace('Z', '+00:00'))
                    print(f"   NEXT: {next_run_dt.strftime('%d/%m/%Y %H:%M:%S')}", flush=True)
                except:
                    print(f"   NEXT: {next_run}", flush=True)
            elif hasattr(next_run, 'strftime'):
                print(f"   NEXT: {next_run.strftime('%d/%m/%Y %H:%M:%S')}", flush=True)
            else:
                print(f"   NEXT: {next_run}", flush=True)
        print(flush=True)

print("="*80, flush=True)
print("MAVERICK BOT READY!", flush=True)
print("="*80 + "\n", flush=True)

# Inicia timer de countdown (mantém thread viva)
timer_thread = threading.Thread(target=countdown_timer, args=(COUNTDOWN_INTERVAL_SECONDS,))
timer_thread.daemon = True
timer_thread.start()

# ========== APENAS PARA DESENVOLVIMENTO LOCAL ==========
if __name__ == "__main__":
    # Carrega configurações do .env para rodar localmente
    flask_host = os.getenv('FLASK_HOST', '0.0.0.0')
    flask_port = int(os.getenv('FLASK_PORT', 5000))
    flask_debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    print(f"🌐 Servidor local: http://{flask_host}:{flask_port}", flush=True)
    print(f"🔧 Debug mode: {flask_debug}\n", flush=True)
    
    app.run(debug=flask_debug, host=flask_host, port=flask_port)
