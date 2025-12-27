"""
API Principal - Sistema de Trading Multi-Exchange
"""

import os
import ccxt
from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime

# Import local modules
from src.security.encryption import get_encryption_service
from src.security.jwt_auth import require_auth, optional_auth
from src.validators.exchange_validator import ExchangeValidator
from src.validators.request_validator import require_params
from src.services.balance_service import get_balance_service
from src.services.balance_history_service import get_balance_history_service
from src.services.strategy_service import get_strategy_service
from src.services.position_service import get_position_service
from src.services.order_execution_service import get_order_execution_service
from src.services.notification_service import get_notification_service
from src.services.strategy_worker import get_strategy_worker
from src.utils.formatting import format_price, format_usd, format_percent
from src.utils.logger import get_logger
from src.utils.cache import get_orders_cache, get_ccxt_instances_cache
from src.config import MONGODB_URI, MONGODB_DATABASE, API_PORT

# Scheduler imports
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import atexit

# Carrega variáveis de ambiente
load_dotenv()

# Initialize logger
logger = get_logger(__name__)

# Inicializa Flask
app = Flask(__name__)

# ============================================================================
# CORS CONFIGURATION - Allow frontend access
# ============================================================================
# Configura CORS para permitir chamadas do React app
CORS(app, resources={
    r"/api/*": {
        "origins": ["*"],  # Em produção, especifique os domínios (ex: ["http://localhost:3000", "https://seu-app.com"])
        "methods": ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True
    }
})
logger.info("✅ CORS enabled - Frontend can access API")

# Configuração MongoDB usando config centralizado
def get_database():
    """Retorna conexão com MongoDB"""
    client = MongoClient(MONGODB_URI)
    return client[MONGODB_DATABASE]

# Teste de conexão
try:
    db = get_database()
    # Testa conexão
    db.command('ping')
    logger.info("MongoDB conectado com sucesso!")
except Exception as e:
    logger.error(f"Erro ao conectar MongoDB: {e}")
    db = None


# ============================================================================
# SCHEDULER INTEGRATION - Automated Balance Snapshots
# ============================================================================

def run_scheduled_snapshot():
    """
    Executa snapshot de saldos automaticamente (chamado pelo scheduler)
    """
    try:
        logger.info("=" * 80)
        logger.info(f"SCHEDULED SNAPSHOT TRIGGERED - {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        logger.info("=" * 80)
        
        # Import aqui para evitar circular imports
        from scripts.hourly_balance_snapshot import run_hourly_snapshot
        run_hourly_snapshot()
        
        logger.info("Scheduled snapshot completed successfully")
    except Exception as e:
        logger.error(f"Error in scheduled snapshot: {e}")
        import traceback
        traceback.print_exc()


def run_tokens_update():
    """
    Atualiza lista de tokens disponíveis em todas as exchanges (chamado pelo scheduler)
    """
    try:
        logger.info("=" * 80)
        logger.info(f"TOKENS UPDATE JOB TRIGGERED - {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        logger.info("=" * 80)
        
        # Import aqui para evitar circular imports
        from scripts.update_exchange_tokens import update_all_exchange_tokens
        result = update_all_exchange_tokens()
        
        if result.get('success'):
            logger.info(f"✅ Tokens update completed: {result['successful_updates']}/{result['total_exchanges']} exchanges")
        else:
            logger.error(f"❌ Tokens update failed: {result.get('error')}")
            
    except Exception as e:
        logger.error(f"Error in tokens update job: {e}")
        import traceback
        traceback.print_exc()


# Initialize BackgroundScheduler
scheduler = BackgroundScheduler(timezone='UTC')

# Add job: execute daily at midnight (00:00)
scheduler.add_job(
    func=run_scheduled_snapshot,
    trigger=CronTrigger(minute=0, hour=0),  # Daily at 00:00 UTC
    id='balance_snapshot_job',
    name='Daily Balance Snapshot at Midnight',
    replace_existing=True,
    max_instances=1
)

# Add job: update exchange tokens daily at 00:01 (1 minute after midnight)
scheduler.add_job(
    func=run_tokens_update,
    trigger=CronTrigger(minute=1, hour=0),  # Daily at 00:01 UTC
    id='tokens_update_job',
    name='Daily Tokens Update at 00:01',
    replace_existing=True,
    max_instances=1
)

# Start scheduler
scheduler.start()
logger.info("✅ Scheduler started - Balance snapshots daily at 00:00 UTC")
logger.info("✅ Scheduler started - Tokens update daily at 00:01 UTC")

# Shutdown scheduler when app exits
atexit.register(lambda: scheduler.shutdown())


# ============================================================================
# STRATEGY WORKER - Automated Trading Bot
# ============================================================================

# Initialize trading services
strategy_worker = None

def initialize_strategy_worker():
    """
    Initialize strategy worker bot for automated trading
    Runs in dry-run mode by default (can be changed via env var)
    """
    try:
        dry_run = os.getenv('STRATEGY_DRY_RUN', 'true').lower() == 'true'
        check_interval = int(os.getenv('STRATEGY_CHECK_INTERVAL', '5'))  # minutes
        
        # Initialize services
        strategy_service = get_strategy_service(db)
        position_service = get_position_service(db)
        order_execution_service = get_order_execution_service(db, dry_run=dry_run)
        notification_service = get_notification_service(db)
        
        # Create strategy worker
        global strategy_worker
        strategy_worker = get_strategy_worker(
            db=db,
            strategy_service=strategy_service,
            position_service=position_service,
            order_execution_service=order_execution_service,
            notification_service=notification_service,
            dry_run=dry_run,
            check_interval_minutes=check_interval
        )
        
        # Start worker
        strategy_worker.start()
        
        mode = "DRY-RUN" if dry_run else "LIVE"
        logger.info(f"✅ Strategy Worker started in {mode} mode (checking every {check_interval} minutes)")
        
    except Exception as e:
        logger.error(f"Error initializing strategy worker: {e}")
        import traceback
        traceback.print_exc()

# Initialize strategy worker
initialize_strategy_worker()

# Shutdown strategy worker when app exits
atexit.register(lambda: strategy_worker.stop() if strategy_worker else None)

# ============================================================================



@app.route('/health', methods=['GET'])
def health_check():
    """Health check da API"""
    # Get scheduler info
    scheduler_running = scheduler.running if scheduler else False
    next_run = None
    
    if scheduler_running:
        jobs = scheduler.get_jobs()
        if jobs:
            next_run = jobs[0].next_run_time.isoformat() if jobs[0].next_run_time else None
    
    # Get strategy worker info
    strategy_worker_running = strategy_worker.is_running if strategy_worker else False
    
    return {
        'status': 'ok',
        'message': 'API rodando',
        'database': 'connected' if db is not None else 'disconnected',
        'scheduler': {
            'running': scheduler_running,
            'next_snapshot': next_run
        },
        'strategy_worker': {
            'running': strategy_worker_running,
            'check_interval_minutes': int(os.getenv('STRATEGY_CHECK_INTERVAL', '5')),
            'dry_run_mode': os.getenv('STRATEGY_DRY_RUN', 'true').lower() == 'true'
        }
    }, 200


@app.route('/api/v1/metrics', methods=['GET'])
def get_metrics():
    """
    📊 PERFORMANCE METRICS - Cache statistics and system info
    
    Returns:
        200: System metrics and cache statistics
        500: Error getting metrics
    """
    try:
        # Get cache statistics
        from src.utils.cache import get_exchanges_cache, get_linked_exchanges_cache
        from src.services.balance_service import _balance_cache
        
        exchanges_cache = get_exchanges_cache()
        linked_cache = get_linked_exchanges_cache()
        
        # Balance cache stats (global cache)
        balance_cache_stats = _balance_cache.get_stats()
        
        return jsonify({
            'success': True,
            'timestamp': datetime.utcnow().isoformat(),
            'system': {
                'database': 'connected' if db is not None else 'disconnected',
                'scheduler_running': scheduler.running if scheduler else False,
                'strategy_worker_running': strategy_worker.is_running if strategy_worker else False
            },
            'cache': {
                'balance_cache': balance_cache_stats,
                'exchanges_cache_size': len(exchanges_cache.cache) if hasattr(exchanges_cache, 'cache') else 0,
                'linked_cache_size': len(linked_cache.cache) if hasattr(linked_cache, 'cache') else 0
            },
            'performance': {
                'max_workers': 20,
                'request_timeout': '15s',
                'summary_ttl': '10min',
                'full_ttl': '5min',
                'single_ttl': '3min'
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting metrics: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'details': str(e)
        }), 500

# Rota raiz
@app.route('/', methods=['GET'])
def index():
    """Rota raiz"""
    return {
        'message': 'Sistema de Trading Multi-Exchange',
        'version': '2.0.0',
        'endpoints': {
            'health': '/health',
            'scheduler_status': '/api/v1/scheduler/status',
            'exchanges_available': '/api/v1/exchanges/available?user_id=<user_id>',
            'exchanges_link': '/api/v1/exchanges/link',
            'exchanges_linked': '/api/v1/exchanges/linked?user_id=<user_id>',
            'exchanges_unlink': '/api/v1/exchanges/unlink',
            'balances': '/api/v1/balances?user_id=<user_id>&force_refresh=<true|false>',
            'balances_clear_cache': '/api/v1/balances/clear-cache',
            'strategies': '/api/v1/strategies?user_id=<user_id>',
            'positions': '/api/v1/positions?user_id=<user_id>',
            'notifications': '/api/v1/notifications?user_id=<user_id>',
            'manual_buy': '/api/v1/orders/buy',
            'manual_sell': '/api/v1/orders/sell',
            'jobs_status': '/api/v1/jobs/status',
            'jobs_control': '/api/v1/jobs/control'
        },
        'features': {
            'automated_snapshots': 'Daily at 00:00 UTC (balance snapshots)',
            'automated_tokens_update': 'Daily at 00:01 UTC (exchange tokens cache)',
            'automated_trading': f"Strategy Worker checking every {os.getenv('STRATEGY_CHECK_INTERVAL', '5')} minutes",
            'dry_run_mode': os.getenv('STRATEGY_DRY_RUN', 'true')
        }
    }, 200


# ============================================
# AUTHENTICATION ENDPOINTS (JWT)
# ============================================

from src.security.jwt_auth import (
    generate_access_token,
    generate_refresh_token,
    verify_token,
    require_auth
)

@app.route('/api/v1/auth/login', methods=['POST'])
def login():
    """
    🔐 Login com OAuth (Google ou Apple)
    
    Request Body:
        {
            "provider": "google" | "apple",
            "id_token": "string",  // Token OAuth do provedor
            "email": "string",
            "name": "string",
            "picture": "string" (optional)
        }
    
    Returns:
        200: {
            "success": true,
            "access_token": "jwt_token",
            "refresh_token": "jwt_refresh_token",
            "user": {
                "id": "user_id",
                "email": "email",
                "name": "name",
                "provider": "google|apple"
            }
        }
        400: Dados inválidos
        500: Erro interno
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        provider = data.get('provider')
        email = data.get('email')
        name = data.get('name')
        
        # Validações
        if not provider or provider not in ['google', 'apple']:
            return jsonify({
                'success': False,
                'error': 'Invalid provider. Must be "google" or "apple"'
            }), 400
        
        if not email or not name:
            return jsonify({
                'success': False,
                'error': 'Email and name are required'
            }), 400
        
        # TODO: Verificar id_token com Google/Apple (em produção)
        # Por enquanto, aceita qualquer token para desenvolvimento
        
        # Busca ou cria usuário no MongoDB
        users_collection = db.users
        user = users_collection.find_one({'email': email})
        
        if not user:
            # Cria novo usuário
            user_id = f"{provider}_{email.split('@')[0]}_{datetime.utcnow().timestamp()}"
            user_doc = {
                'user_id': user_id,
                'email': email,
                'name': name,
                'picture': data.get('picture'),
                'provider': provider,
                'created_at': datetime.utcnow(),
                'last_login': datetime.utcnow()
            }
            users_collection.insert_one(user_doc)
            user = user_doc
        else:
            # Atualiza last_login
            user_id = user['user_id']
            users_collection.update_one(
                {'_id': user['_id']},
                {'$set': {'last_login': datetime.utcnow()}}
            )
        
        # Gera tokens JWT
        access_token = generate_access_token(user_id, email, provider)
        refresh_token = generate_refresh_token(user_id)
        
        return jsonify({
            'success': True,
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user': {
                'id': user_id,
                'email': email,
                'name': name,
                'picture': user.get('picture'),
                'provider': provider
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error in login: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'details': str(e)
        }), 500


@app.route('/api/v1/auth/refresh', methods=['POST'])
def refresh_token_endpoint():
    """
    🔄 Renova access token usando refresh token
    
    Request Body:
        {
            "refresh_token": "jwt_refresh_token"
        }
    
    Returns:
        200: {
            "success": true,
            "access_token": "new_jwt_token"
        }
        401: Token inválido ou expirado
        500: Erro interno
    """
    try:
        data = request.get_json()
        
        if not data or 'refresh_token' not in data:
            return jsonify({
                'success': False,
                'error': 'Refresh token is required'
            }), 400
        
        refresh_token = data['refresh_token']
        
        # Verifica refresh token
        is_valid, payload, error = verify_token(refresh_token)
        
        if not is_valid:
            return jsonify({
                'success': False,
                'error': 'Invalid refresh token',
                'message': error
            }), 401
        
        # Verifica se é refresh token
        if payload.get('type') != 'refresh':
            return jsonify({
                'success': False,
                'error': 'Invalid token type',
                'message': 'Must be a refresh token'
            }), 401
        
        user_id = payload['user_id']
        
        # Busca usuário para pegar email e provider
        users_collection = db.users
        user = users_collection.find_one({'user_id': user_id})
        
        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404
        
        # Gera novo access token
        new_access_token = generate_access_token(
            user_id,
            user['email'],
            user.get('provider', 'email')
        )
        
        return jsonify({
            'success': True,
            'access_token': new_access_token
        }), 200
        
    except Exception as e:
        logger.error(f"Error refreshing token: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'details': str(e)
        }), 500


@app.route('/api/v1/auth/verify', methods=['GET'])
@require_auth
def verify_token_endpoint():
    """
    ✅ Verifica se token JWT é válido
    
    Headers:
        Authorization: Bearer <jwt_token>
    
    Returns:
        200: {
            "success": true,
            "user_id": "user_id",
            "email": "email",
            "provider": "google|apple"
        }
        401: Token inválido ou expirado
    """
    try:
        # Se chegou aqui, token é válido (decorador @require_auth)
        return jsonify({
            'success': True,
            'user_id': request.user_id,
            'email': request.user_email,
            'provider': request.auth_provider
        }), 200
    except Exception as e:
        logger.error(f"Error verifying token: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500


# ============================================
# SCHEDULER STATUS ENDPOINT
# ============================================

@app.route('/api/v1/scheduler/status', methods=['GET'])
def get_scheduler_status():
    """Get detailed scheduler status"""
    try:
        if not scheduler:
            return jsonify({
                'success': False,
                'error': 'Scheduler not initialized'
            }), 500
        
        jobs = scheduler.get_jobs()
        jobs_info = []
        
        for job in jobs:
            jobs_info.append({
                'id': job.id,
                'name': job.name,
                'next_run': job.next_run_time.isoformat() if job.next_run_time else None,
                'trigger': str(job.trigger)
            })
        
        return jsonify({
            'success': True,
            'scheduler': {
                'running': scheduler.running,
                'state': 'running' if scheduler.running else 'stopped',
                'timezone': str(scheduler.timezone),
                'jobs_count': len(jobs),
                'jobs': jobs_info
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting scheduler status: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ============================================
# HELPER FUNCTIONS
# ============================================

def invalidate_exchange_caches(user_id: str):
    """Invalidate all exchange-related caches for a user"""
    from src.utils.cache import get_exchanges_cache, get_linked_exchanges_cache
    
    exchanges_cache = get_exchanges_cache()
    linked_cache = get_linked_exchanges_cache()
    
    # Clear user-specific caches
    exchanges_cache.delete(f"available_{user_id}")
    linked_cache.delete(f"linked_{user_id}")
    
    logger.debug(f"Cache invalidated for user {user_id}")

# ============================================
# ENDPOINTS DE EXCHANGES
# ============================================

@app.route('/api/v1/exchanges/available', methods=['GET'])
def get_available_exchanges():
    """
    Lista exchanges disponíveis para vinculação (NOVA ESTRUTURA COM ARRAY)
    Retorna APENAS exchanges que o usuário NUNCA conectou (não estão no array)
    
    Query Params:
        user_id (required): ID do usuário para filtrar exchanges já vinculadas
        force_refresh (optional): true para ignorar cache
    
    Returns:
        200: Lista de exchanges nunca conectadas pelo usuário
        400: user_id não fornecido
        500: Erro ao buscar exchanges
    """
    try:
        from src.utils.cache import get_exchanges_cache
        
        # user_id é obrigatório
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'user_id is required as query parameter'
            }), 400
        
        # Check cache
        force_refresh = request.args.get('force_refresh', 'false').lower() == 'true'
        cache = get_exchanges_cache()
        cache_key = f"available_{user_id}"
        
        if not force_refresh:
            is_valid, cached_data = cache.get(cache_key)
            if is_valid:
                cached_data['from_cache'] = True
                return jsonify(cached_data), 200
        
        # Busca exchanges ativas no banco (exchanges habilitadas no sistema)
        exchanges = list(db.exchanges.find(
            {'is_active': True},
            {
                '_id': 1,
                'nome': 1,
                'url': 1,
                'pais_de_origem': 1,
                'icon': 1,
                'requires_passphrase': 1,
                'ccxt_id': 1
            }
        ).sort('nome', 1))
        
        # Buscar documento do usuário e extrair TODAS exchange_ids que já foram conectadas
        user_doc = db.user_exchanges.find_one({'user_id': user_id})
        
        linked_exchange_ids = []
        if user_doc and 'exchanges' in user_doc:
            # Todas as exchanges no array (independente de is_active)
            # Tanto ativas quanto inativas são consideradas "já conectadas"
            linked_exchange_ids = [
                ex['exchange_id']
                for ex in user_doc['exchanges']
            ]
        
        # Filtrar exchanges que NUNCA foram conectadas (não estão no array)
        exchanges = [
            ex for ex in exchanges 
            if ObjectId(ex['_id']) not in linked_exchange_ids
        ]
        
        # Converte ObjectId para string
        for exchange in exchanges:
            exchange['_id'] = str(exchange['_id'])
        
        result = {
            'success': True,
            'total': len(exchanges),
            'exchanges': exchanges,
            'from_cache': False
        }
        
        # Cache for 5 minutes
        cache.set(cache_key, result, ttl_seconds=300)
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error fetching exchanges: {str(e)}'
        }), 500

@app.route('/api/v1/exchanges/link', methods=['POST'])
@require_auth
@require_params('user_id', 'exchange_id', 'api_key', 'api_secret')
def link_exchange():
    """
    Vincula credenciais de uma exchange ao usuário
    
    Request Body:
        {
            "user_id": "string",
            "exchange_id": "string (MongoDB _id)",
            "api_key": "string",
            "api_secret": "string",
            "passphrase": "string (optional)"
        }
    
    Returns:
        201: Exchange vinculada com sucesso
        400: Dados inválidos
        401: Token inválido ou ausente / Credenciais inválidas ou sem permissão
        403: user_id do token não corresponde ao user_id do parâmetro
        500: Erro interno
    """
    try:
        # Validação de dados de entrada
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Request body is required'
            }), 400
        
        user_id = request.validated_params['user_id']
        
        # Verify user_id from token matches user_id in params
        if request.user_id != user_id:
            return jsonify({
                'success': False,
                'error': 'Unauthorized: user_id mismatch'
            }), 403
        
        exchange_id = request.validated_params['exchange_id']
        api_key = request.validated_params['api_key'].strip()
        api_secret = request.validated_params['api_secret'].strip()
        passphrase = data.get('passphrase', '').strip() or None
        
        # Validar se a exchange existe
        try:
            exchange = db.exchanges.find_one({'_id': ObjectId(exchange_id)})
        except:
            return jsonify({
                'success': False,
                'error': 'Invalid exchange_id format'
            }), 400
        
        if not exchange:
            return jsonify({
                'success': False,
                'error': 'Exchange not found'
            }), 404
        
        # Verificar se passphrase é necessária
        if exchange.get('requires_passphrase') and not passphrase:
            return jsonify({
                'success': False,
                'error': f"{exchange['nome']} requires a passphrase"
            }), 400
        
        # ============================================
        # CAMADA DE SEGURANÇA E VALIDAÇÃO
        # ============================================
        
        logger.debug(f"Validating credentials for {exchange['nome']}...")
        
        # Validar credenciais com a exchange usando CCXT
        validation_result = ExchangeValidator.validate_and_test(
            exchange_id=exchange['ccxt_id'],
            api_key=api_key,
            api_secret=api_secret,
            passphrase=passphrase
        )
        
        if not validation_result['success']:
            return jsonify({
                'success': False,
                'error': 'Credential validation failed',
                'details': validation_result['errors']
            }), 401
        
        logger.info(f"Credentials validated successfully")
        
        # ============================================
        # CRIPTOGRAFIA DAS CREDENCIAIS
        # ============================================
        
        logger.debug(f"Encrypting credentials...")
        
        encryption_service = get_encryption_service()
        encrypted_credentials = encryption_service.encrypt_credentials(
            api_key=api_key,
            api_secret=api_secret,
            passphrase=passphrase
        )
        
        logger.info(f"Credentials encrypted")
        
        # ============================================
        # SALVAR NO BANCO DE DADOS (NOVA ESTRUTURA COM ARRAY)
        # ============================================
        
        # Busca ou cria documento do usuário
        user_doc = db.user_exchanges.find_one({'user_id': user_id})
        
        # Prepara dados da exchange para adicionar/atualizar no array
        exchange_data = {
            'exchange_id': ObjectId(exchange_id),
            'api_key_encrypted': encrypted_credentials['api_key'],
            'api_secret_encrypted': encrypted_credentials['api_secret'],
            'passphrase_encrypted': encrypted_credentials.get('passphrase'),
            'is_active': True,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        
        if user_doc:
            # Verifica se exchange já está no array
            exchange_exists = False
            if 'exchanges' in user_doc:
                for idx, ex in enumerate(user_doc['exchanges']):
                    if ex['exchange_id'] == ObjectId(exchange_id):
                        exchange_exists = True
                        # Atualiza exchange existente no array
                        db.user_exchanges.update_one(
                            {'user_id': user_id},
                            {
                                '$set': {
                                    f'exchanges.{idx}.api_key_encrypted': encrypted_credentials['api_key'],
                                    f'exchanges.{idx}.api_secret_encrypted': encrypted_credentials['api_secret'],
                                    f'exchanges.{idx}.passphrase_encrypted': encrypted_credentials.get('passphrase'),
                                    f'exchanges.{idx}.is_active': True,
                                    f'exchanges.{idx}.updated_at': datetime.utcnow(),
                                    'updated_at': datetime.utcnow()
                                },
                                '$unset': {
                                    f'exchanges.{idx}.inactive_reason': '',
                                    f'exchanges.{idx}.inactive_at': ''
                                }
                            }
                        )
                        
                        # Invalidate cache
                        invalidate_exchange_caches(user_id)
                        
                        return jsonify({
                            'success': True,
                            'message': f'{exchange["nome"]} credentials updated successfully',
                            'user_id': user_id,
                            'exchange': {
                                'id': str(exchange['_id']),
                                'name': exchange['nome'],
                                'icon': exchange['icon']
                            }
                        }), 200
            
            # Se exchange não existe no array, adiciona
            if not exchange_exists:
                db.user_exchanges.update_one(
                    {'user_id': user_id},
                    {
                        '$push': {'exchanges': exchange_data},
                        '$set': {'updated_at': datetime.utcnow()}
                    }
                )
                
                # Invalidate cache
                invalidate_exchange_caches(user_id)
                
                return jsonify({
                    'success': True,
                    'message': f'{exchange["nome"]} linked successfully',
                    'user_id': user_id,
                    'exchange': {
                        'id': str(exchange['_id']),
                        'name': exchange['nome'],
                        'icon': exchange['icon']
                    }
                }), 201
        else:
            # Cria novo documento do usuário com array contendo a primeira exchange
            new_user_doc = {
                'user_id': user_id,
                'exchanges': [exchange_data],
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }
            
            db.user_exchanges.insert_one(new_user_doc)
            
            # Invalidate cache
            invalidate_exchange_caches(user_id)
            
            return jsonify({
                'success': True,
                'message': f'{exchange["nome"]} linked successfully',
                'user_id': user_id,
                'exchange': {
                    'id': str(exchange['_id']),
                    'name': exchange['nome'],
                    'icon': exchange['icon']
                }
            }), 201
        
    except Exception as e:
        logger.error(f"Error linking exchange: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'details': str(e)
        }), 500

@app.route('/api/v1/exchanges/linked', methods=['GET'])
@require_auth
@require_params('user_id')
def get_linked_exchanges():
    """
    Lista exchanges vinculadas por um usuário (NOVA ESTRUTURA COM ARRAY)
    Retorna TODAS as exchanges que o usuário já conectou alguma vez
    Campo 'status': 'active' (funcionando) ou 'inactive' (pausada/desconectada)
    
    Query Params:
        user_id (required): ID do usuário
        force_refresh (optional): true para ignorar cache
    
    Returns:
        200: Lista de exchanges vinculadas com status (active/inactive)
        400: user_id não fornecido
        401: Token inválido ou ausente
        403: user_id do token não corresponde ao user_id do parâmetro
        500: Erro ao buscar exchanges
    """
    try:
        from src.utils.cache import get_linked_exchanges_cache
        
        user_id = request.validated_params['user_id']
        
        # Verify user_id from token matches user_id in params
        if request.user_id != user_id:
            return jsonify({
                'success': False,
                'error': 'Unauthorized: user_id mismatch'
            }), 403
        
        # Check cache
        force_refresh = request.args.get('force_refresh', 'false').lower() == 'true'
        cache = get_linked_exchanges_cache()
        cache_key = f"linked_{user_id}"
        
        if not force_refresh:
            is_valid, cached_data = cache.get(cache_key)
            if is_valid:
                cached_data['from_cache'] = True
                return jsonify(cached_data), 200
        
        # Buscar documento do usuário com array de exchanges
        user_doc = db.user_exchanges.find_one({'user_id': user_id})
        
        if not user_doc or 'exchanges' not in user_doc or not user_doc['exchanges']:
            return jsonify({
                'success': True,
                'total': 0,
                'exchanges': []
            }), 200
        
        # Buscar informações de TODAS as exchanges vinculadas (ativas e inativas)
        linked_exchanges = []
        for ex_data in user_doc['exchanges']:
            exchange = db.exchanges.find_one(
                {'_id': ex_data['exchange_id']},
                {
                    '_id': 1,
                    'nome': 1,
                    'icon': 1,
                    'url': 1,
                    'ccxt_id': 1,
                    'pais_de_origem': 1
                }
            )
            
            if exchange:
                # Determina o status: active (funcionando) ou inactive (pausada)
                is_active = ex_data.get('is_active', True)
                status = 'active' if is_active else 'inactive'
                
                exchange_info = {
                    'exchange_id': str(exchange['_id']),
                    'name': exchange['nome'],
                    'icon': exchange['icon'],
                    'url': exchange['url'],
                    'ccxt_id': exchange['ccxt_id'],
                    'country': exchange['pais_de_origem'],
                    'status': status,  # 'active' ou 'inactive'
                    'linked_at': ex_data['created_at'].isoformat(),
                    'updated_at': ex_data['updated_at'].isoformat()
                }
                
                # Adiciona timestamps de disconnect/reconnect se existirem
                if 'disconnected_at' in ex_data:
                    exchange_info['disconnected_at'] = ex_data['disconnected_at'].isoformat()
                if 'reconnected_at' in ex_data:
                    exchange_info['reconnected_at'] = ex_data['reconnected_at'].isoformat()
                
                # Adiciona motivo da inativação e timestamp se exchange está inativa
                if not is_active:
                    if 'inactive_reason' in ex_data:
                        exchange_info['inactive_reason'] = ex_data['inactive_reason']
                    if 'inactive_at' in ex_data:
                        exchange_info['inactive_at'] = ex_data['inactive_at'].isoformat()
                    
                    # Adiciona credentials_status para indicar que precisa atualizar credenciais
                    exchange_info['credentials_status'] = {
                        'valid': False,
                        'action_required': 'update_credentials',
                        'message': f'Please update your credentials for {exchange["nome"]}'
                    }
                
                linked_exchanges.append(exchange_info)
        
        result = {
            'success': True,
            'total': len(linked_exchanges),
            'exchanges': linked_exchanges,
            'from_cache': False
        }
        
        # Cache for 1 minute (user-specific data changes more frequently)
        cache.set(cache_key, result, ttl_seconds=60)
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error fetching linked exchanges: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'details': str(e)
        }), 500

@app.route('/api/v1/exchanges/unlink', methods=['DELETE'])
@require_auth
@require_params('user_id', 'exchange_id')
def unlink_exchange():
    """
    Remove vínculo de uma exchange (NOVA ESTRUTURA COM ARRAY)
    
    Request Body:
        {
            "user_id": "string",
            "exchange_id": "string (MongoDB _id)"
        }
    
    Returns:
        200: Exchange desvinculada com sucesso
        400: Dados inválidos
        401: Token inválido ou ausente
        403: user_id do token não corresponde ao user_id do parâmetro
        404: Vínculo não encontrado
        500: Erro ao desvincular
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Request body is required'
            }), 400
        
        user_id = request.validated_params['user_id']
        exchange_id = request.validated_params['exchange_id']
        
        # Verify user_id from token matches user_id in params
        if request.user_id != user_id:
            return jsonify({
                'success': False,
                'error': 'Unauthorized: user_id mismatch'
            }), 403
        
        # Validar ObjectId
        try:
            exchange_object_id = ObjectId(exchange_id)
        except:
            return jsonify({
                'success': False,
                'error': 'Invalid exchange_id format'
            }), 400
        
        # Buscar documento do usuário
        user_doc = db.user_exchanges.find_one({'user_id': user_id})
        
        if not user_doc or 'exchanges' not in user_doc:
            return jsonify({
                'success': False,
                'error': 'User has no linked exchanges'
            }), 404
        
        # Encontrar índice da exchange no array
        exchange_index = None
        for idx, ex in enumerate(user_doc['exchanges']):
            if ex['exchange_id'] == exchange_object_id:
                exchange_index = idx
                break
        
        if exchange_index is None:
            return jsonify({
                'success': False,
                'error': 'Exchange not found in user\'s linked exchanges'
            }), 404
        
        # Soft delete - marcar exchange como inativa no array
        result = db.user_exchanges.update_one(
            {'user_id': user_id},
            {
                '$set': {
                    f'exchanges.{exchange_index}.is_active': False,
                    f'exchanges.{exchange_index}.updated_at': datetime.utcnow(),
                    'updated_at': datetime.utcnow()
                }
            }
        )
        
        if result.modified_count > 0:
            # Buscar nome da exchange
            exchange = db.exchanges.find_one({'_id': exchange_object_id})
            
            # Invalidate cache
            invalidate_exchange_caches(user_id)
            
            return jsonify({
                'success': True,
                'message': f'{exchange["nome"]} unlinked successfully'
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to unlink exchange'
            }), 500
        
    except Exception as e:
        logger.error(f"Error unlinking exchange: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'details': str(e)
        }), 500


@app.route('/api/v1/exchanges/disconnect', methods=['POST'])
@require_auth
@require_params('user_id', 'exchange_id')
def disconnect_exchange():
    """
    Desconecta uma exchange (soft delete - marca como inativa)
    Alias para /unlink - mesma funcionalidade, nome mais intuitivo
    
    Request Body:
        {
            "user_id": "string",
            "exchange_id": "string (MongoDB _id)"
        }
    
    Returns:
        200: Exchange desconectada com sucesso
        400: Dados inválidos
        401: Token inválido ou ausente
        403: user_id do token não corresponde ao user_id do parâmetro
        404: Exchange não encontrada
        500: Erro ao desconectar
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Request body is required'
            }), 400
        
        user_id = request.validated_params['user_id']
        exchange_id = request.validated_params['exchange_id']
        
        # Verify user_id from token matches user_id in params
        if request.user_id != user_id:
            return jsonify({
                'success': False,
                'error': 'Unauthorized: user_id mismatch'
            }), 403
        
        # Validar ObjectId
        try:
            exchange_object_id = ObjectId(exchange_id)
        except:
            return jsonify({
                'success': False,
                'error': 'Invalid exchange_id format'
            }), 400
        
        # Buscar documento do usuário
        user_doc = db.user_exchanges.find_one({'user_id': user_id})
        
        if not user_doc or 'exchanges' not in user_doc:
            return jsonify({
                'success': False,
                'error': 'User has no linked exchanges'
            }), 404
        
        # Encontrar índice da exchange no array
        exchange_index = None
        exchange_data = None
        for idx, ex in enumerate(user_doc['exchanges']):
            if ex['exchange_id'] == exchange_object_id:
                exchange_index = idx
                exchange_data = ex
                break
        
        if exchange_index is None:
            return jsonify({
                'success': False,
                'error': 'Exchange not found in user\'s linked exchanges'
            }), 404
        
        # Verificar se já está desconectada
        if not exchange_data.get('is_active', True):
            return jsonify({
                'success': False,
                'error': 'Exchange is already disconnected'
            }), 400
        
        # Soft delete - marcar exchange como inativa
        result = db.user_exchanges.update_one(
            {'user_id': user_id},
            {
                '$set': {
                    f'exchanges.{exchange_index}.is_active': False,
                    f'exchanges.{exchange_index}.disconnected_at': datetime.utcnow(),
                    f'exchanges.{exchange_index}.updated_at': datetime.utcnow(),
                    'updated_at': datetime.utcnow()
                }
            }
        )
        
        if result.modified_count > 0:
            # Buscar nome da exchange
            exchange = db.exchanges.find_one({'_id': exchange_object_id})
            
            # Invalidate cache
            invalidate_exchange_caches(user_id)
            
            logger.info(f"✅ {exchange['nome']} disconnected for user {user_id}")
            
            return jsonify({
                'success': True,
                'message': f'{exchange["nome"]} disconnected successfully',
                'exchange': {
                    'id': exchange_id,
                    'name': exchange['nome'],
                    'is_active': False
                }
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to disconnect exchange'
            }), 500
        
    except Exception as e:
        logger.error(f"Error disconnecting exchange: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'details': str(e)
        }), 500


@app.route('/api/v1/exchanges/delete', methods=['DELETE'])
@require_auth
@require_params('user_id', 'exchange_id')
def delete_exchange():
    """
    Deleta permanentemente uma conexão de exchange (hard delete)
    ATENÇÃO: Esta ação é irreversível! Remove os dados criptografados da API.
    
    Request Body:
        {
            "user_id": "string",
            "exchange_id": "string (MongoDB _id)"
        }
    
    Returns:
        200: Exchange deletada com sucesso
        400: Dados inválidos
        401: Token inválido ou ausente
        403: user_id do token não corresponde ao user_id do parâmetro
        404: Exchange não encontrada
        500: Erro ao deletar
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Request body is required'
            }), 400
        
        user_id = request.validated_params['user_id']
        exchange_id = request.validated_params['exchange_id']
        
        # Verify user_id from token matches user_id in params
        if request.user_id != user_id:
            return jsonify({
                'success': False,
                'error': 'Unauthorized: user_id mismatch'
            }), 403
        
        # Validar ObjectId
        try:
            exchange_object_id = ObjectId(exchange_id)
        except:
            return jsonify({
                'success': False,
                'error': 'Invalid exchange_id format'
            }), 400
        
        # Buscar documento do usuário
        user_doc = db.user_exchanges.find_one({'user_id': user_id})
        
        if not user_doc or 'exchanges' not in user_doc:
            return jsonify({
                'success': False,
                'error': 'User has no linked exchanges'
            }), 404
        
        # Verificar se a exchange existe no array
        exchange_found = False
        exchange_name = None
        for ex in user_doc['exchanges']:
            if ex['exchange_id'] == exchange_object_id:
                exchange_found = True
                # Buscar nome da exchange antes de deletar
                exchange = db.exchanges.find_one({'_id': exchange_object_id})
                if exchange:
                    exchange_name = exchange['nome']
                break
        
        if not exchange_found:
            return jsonify({
                'success': False,
                'error': 'Exchange not found in user\'s linked exchanges'
            }), 404
        
        # Hard delete - remover exchange do array
        result = db.user_exchanges.update_one(
            {'user_id': user_id},
            {
                '$pull': {
                    'exchanges': {'exchange_id': exchange_object_id}
                },
                '$set': {
                    'updated_at': datetime.utcnow()
                }
            }
        )
        
        if result.modified_count > 0:
            logger.warning(f"🗑️ {exchange_name or 'Exchange'} permanently deleted for user {user_id}")
            
            return jsonify({
                'success': True,
                'message': f'{exchange_name or "Exchange"} deleted permanently',
                'warning': 'This action is irreversible. The exchange connection has been removed.'
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to delete exchange'
            }), 500
        
    except Exception as e:
        logger.error(f"Error deleting exchange: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'details': str(e)
        }), 500


@app.route('/api/v1/exchanges/connect', methods=['POST'])
@require_auth
@require_params('user_id', 'exchange_id')
def connect_exchange():
    """
    Conecta/Reativa uma exchange desconectada (usando credenciais já salvas)
    
    Request Body:
        {
            "user_id": "string",
            "exchange_id": "string (MongoDB _id)"
        }
    
    Returns:
        200: Exchange conectada com sucesso
        400: Dados inválidos ou exchange já está ativa
        401: Token inválido ou ausente
        403: user_id do token não corresponde ao user_id do parâmetro
        404: Exchange não encontrada
        500: Erro ao conectar
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Request body is required'
            }), 400
        
        user_id = request.validated_params['user_id']
        exchange_id = request.validated_params['exchange_id']
        
        # Verify user_id from token matches user_id in params
        if request.user_id != user_id:
            return jsonify({
                'success': False,
                'error': 'Unauthorized: user_id mismatch'
            }), 403
        
        # Validar ObjectId
        try:
            exchange_object_id = ObjectId(exchange_id)
        except:
            return jsonify({
                'success': False,
                'error': 'Invalid exchange_id format'
            }), 400
        
        # Buscar documento do usuário
        user_doc = db.user_exchanges.find_one({'user_id': user_id})
        
        if not user_doc or 'exchanges' not in user_doc:
            return jsonify({
                'success': False,
                'error': 'User has no linked exchanges'
            }), 404
        
        # Encontrar índice da exchange no array
        exchange_index = None
        exchange_data = None
        for idx, ex in enumerate(user_doc['exchanges']):
            if ex['exchange_id'] == exchange_object_id:
                exchange_index = idx
                exchange_data = ex
                break
        
        if exchange_index is None:
            return jsonify({
                'success': False,
                'error': 'Exchange not found in user\'s linked exchanges'
            }), 404
        
        # Verificar se já está ativa
        if exchange_data.get('is_active', True):
            return jsonify({
                'success': False,
                'error': 'Exchange is already connected'
            }), 400
        
        # Reativar exchange
        result = db.user_exchanges.update_one(
            {'user_id': user_id},
            {
                '$set': {
                    f'exchanges.{exchange_index}.is_active': True,
                    f'exchanges.{exchange_index}.reconnected_at': datetime.utcnow(),
                    f'exchanges.{exchange_index}.updated_at': datetime.utcnow(),
                    'updated_at': datetime.utcnow()
                },
                '$unset': {
                    f'exchanges.{exchange_index}.disconnected_at': ''
                }
            }
        )
        
        if result.modified_count > 0:
            # Buscar nome da exchange
            exchange = db.exchanges.find_one({'_id': exchange_object_id})
            
            # Invalidate cache
            invalidate_exchange_caches(user_id)
            
            logger.info(f"✅ {exchange['nome']} connected for user {user_id}")
            
            return jsonify({
                'success': True,
                'message': f'{exchange["nome"]} connected successfully',
                'exchange': {
                    'id': exchange_id,
                    'name': exchange['nome'],
                    'is_active': True
                }
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to reconnect exchange'
            }), 500
        
    except Exception as e:
        logger.error(f"Error connecting exchange: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'details': str(e)
        }), 500


# ============================================
# ENDPOINTS DE BALANCES
# ============================================

@app.route('/api/v1/balances', methods=['GET'])
@require_auth
@require_params('user_id')
def get_balances():
    """
    Busca saldos de todas as exchanges vinculadas ao usuário
    Executa chamadas em paralelo para alta performance
    Retorna: total geral, total por exchange, total por token
    
    Query Params:
        user_id (required): ID do usuário
        force_refresh (optional): true para ignorar cache
        currency (optional): 'brl' para incluir conversão BRL
        include_changes (optional): true para incluir variações de preço (1h, 4h, 24h)
    
    Returns:
        200: Balances agregados
        400: user_id não fornecido
        401: Token inválido ou ausente
        403: user_id do token não corresponde ao user_id do parâmetro
        500: Erro ao buscar balances
    """
    try:
        user_id = request.validated_params['user_id']
        
        # Verify user_id from token matches user_id in params
        if request.user_id != user_id:
            return jsonify({
                'success': False,
                'error': 'Unauthorized: user_id mismatch'
            }), 403
        
        # Check if force refresh
        force_refresh = request.args.get('force_refresh', 'false').lower() == 'true'
        use_cache = not force_refresh
        
        # Check if BRL conversion requested
        include_brl = request.args.get('currency', '').lower() == 'brl'
        
        # Check if price changes requested
        include_changes = request.args.get('include_changes', 'false').lower() == 'true'
        
        # Get balance service
        balance_service = get_balance_service(db)
        
        # Fetch balances (parallelized internally)
        logger.debug(f"Fetching balances for user {user_id} (cache: {use_cache}, include_brl: {include_brl}, include_changes: {include_changes})...")
        result = balance_service.fetch_all_balances(user_id, use_cache=use_cache, include_brl=include_brl, include_changes=include_changes)
        
        num_exchanges = len(result.get('exchanges', []))
        num_tokens = len(result.get('tokens', {}))
        from_cache = result.get('meta', {}).get('from_cache', False)
        logger.info(f"Balances fetched: {num_exchanges} exchanges, {num_tokens} tokens, from_cache: {from_cache}")
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error fetching balances: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'details': str(e)
        }), 500
@app.route('/api/v1/balances/summary', methods=['GET'])
@require_auth
@require_params('user_id')
def get_balances_summary():
    """
    🚀 FAST: Get only totals from all exchanges (no token details)
    Perfect for initial page load - loads in ~1-2 seconds
    
    Query Params:
        user_id (required): ID do usuário
        force_refresh (optional): true para ignorar cache
    
    Returns:
        200: Exchange summaries with totals only
        400: user_id não fornecido
        401: Token inválido ou ausente
        403: user_id do token não corresponde ao user_id do parâmetro
        500: Erro ao buscar balances
    """
    try:
        user_id = request.validated_params['user_id']
        
        # Verify user_id from token matches user_id in params
        if request.user_id != user_id:
            return jsonify({
                'success': False,
                'error': 'Unauthorized: user_id mismatch'
            }), 403
        
        force_refresh = request.args.get('force_refresh', 'false').lower() == 'true'
        use_cache = not force_refresh
        
        balance_service = get_balance_service(db)
        
        logger.debug(f"Fetching summary for user {user_id} (cache: {use_cache})...")
        result = balance_service.fetch_exchanges_summary(user_id, use_cache=use_cache)
        
        logger.info(f"✅ Summary fetched: {result['summary']['exchanges_count']} exchanges in {result['meta']['fetch_time']}s")
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error fetching summary: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'details': str(e)
        }), 500

@app.route('/api/v1/balances/exchange/<exchange_id>', methods=['GET'])
@require_auth
@require_params('user_id')
def get_exchange_details(exchange_id):
    """
    📊 LAZY LOAD: Get detailed token list for ONE exchange
    Called when user clicks to expand exchange in UI
    
    Path Params:
        exchange_id: MongoDB _id of the exchange
    
    Query Params:
        user_id (required): ID do usuário
        include_changes (optional): true para incluir variações
    
    Returns:
        200: Detailed token list for exchange
        400: user_id não fornecido
        401: Token inválido ou ausente
        403: user_id do token não corresponde ao user_id do parâmetro
        404: Exchange not found
        500: Erro ao buscar detalhes
    """
    try:
        user_id = request.validated_params['user_id']
        
        # Verify user_id from token matches user_id in params
        if request.user_id != user_id:
            return jsonify({
                'success': False,
                'error': 'Unauthorized: user_id mismatch'
            }), 403
        
        include_changes = request.args.get('include_changes', 'false').lower() == 'true'
        
        balance_service = get_balance_service(db)
        
        logger.debug(f"Fetching details for exchange {exchange_id}...")
        result = balance_service.fetch_single_exchange_details(user_id, exchange_id, include_changes)
        
        if not result.get('success'):
            return jsonify(result), 404
        
        logger.info(f"✅ Details fetched for {result['name']}: {len(result['tokens'])} tokens")
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error fetching exchange details: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'details': str(e)
        }), 500

@app.route('/api/v1/balances/clear-cache', methods=['POST'])
@require_auth
def clear_balance_cache():
    """
    Limpa o cache de balances
    
    Request Body (optional):
        {
            "user_id": "string"  // If provided, clears only this user's cache
        }
    
    Returns:
        200: Cache cleared
        401: Token inválido ou ausente
        500: Error clearing cache
    """
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', request.user_id)  # Use user_id from JWT if not provided
        
        balance_service = get_balance_service(db)
        balance_service.clear_cache(user_id)
        
        if user_id:
            message = f"Cache cleared for user {user_id}"
        else:
            message = "All balance cache cleared"
        
        logger.info(f" {message}")
        
        return jsonify({
            'success': True,
            'message': message
        }), 200
        
    except Exception as e:
        logger.error(f"Error clearing cache: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'details': str(e)
        }), 500


# ============================================================================
# TRADING ENDPOINTS - Order Management
# ============================================================================

@app.route('/api/v1/orders/create', methods=['POST'])
@require_auth
@require_params('user_id', 'exchange_id', 'symbol', 'side', 'type', 'amount')
def create_order():
    """
    Create a new trading order
    
    Request Body:
        {
            "user_id": "string",
            "exchange_id": "string",
            "symbol": "BTC/USDT",
            "side": "buy" | "sell",
            "type": "market" | "limit" | "stop_loss" | "stop_limit" | "take_profit",
            "amount": 0.001,
            "price": 50000.0,  // Optional for market orders
            "params": {}  // Optional additional parameters
        }
    
    Returns:
        201: Order created successfully
        400: Invalid parameters or insufficient funds
        401: Token inválido ou ausente
        403: user_id do token não corresponde ao user_id do parâmetro
        500: Internal server error
    """
    try:
        data = request.get_json()
        user_id = request.validated_params['user_id']
        
        # Verify user_id from token matches user_id in params
        if request.user_id != user_id:
            return jsonify({
                'success': False,
                'error': 'Unauthorized: user_id mismatch'
            }), 403
        
        # Create order
        dry_run = os.getenv('STRATEGY_DRY_RUN', 'true').lower() == 'true'
        order_service = get_order_execution_service(db, dry_run=dry_run)
        result = order_service.create_order(
            user_id=request.validated_params['user_id'],
            exchange_id=request.validated_params['exchange_id'],
            symbol=request.validated_params['symbol'],
            side=request.validated_params['side'],
            order_type=request.validated_params['type'],
            amount=float(request.validated_params['amount']),
            price=float(data['price']) if data.get('price') else None,
            params=data.get('params', {})
        )
        
        if result['success']:
            logger.info(f"✅ Order created: {result['order_id']} - {data['symbol']} {data['side']} {data['amount']}")
            return jsonify(result), 201
        else:
            logger.warning(f"⚠️  Order creation failed: {result.get('error')}")
            return jsonify(result), 400
            
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': f'Invalid number format: {str(e)}'
        }), 400
    except Exception as e:
        logger.error(f"Error creating order: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'details': str(e)
        }), 500


@app.route('/api/v1/orders/cancel', methods=['POST'])
def cancel_order():
    """
    Cancel an existing order
    
    Request Body:
        {
            "user_id": "string",
            "order_id": "string",
            "exchange_id": "string" (optional, recommended for faster cancellation),
            "symbol": "string" (optional, e.g. "PEPE/USDT", recommended for faster cancellation)
        }
    
    Returns:
        200: Order canceled successfully
        400: Order not found or already canceled
        500: Internal server error
    """
    try:
        data = request.get_json()
        
        if 'user_id' not in data or 'order_id' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing required fields: user_id, order_id'
            }), 400
        
        # Get order execution service (use env var for dry_run)
        dry_run = os.getenv('STRATEGY_DRY_RUN', 'true').lower() == 'true'
        order_service = get_order_execution_service(db, dry_run=dry_run)
        result = order_service.cancel_order(
            user_id=data['user_id'],
            order_id=data['order_id'],
            exchange_id=data.get('exchange_id'),
            symbol=data.get('symbol')
        )
        
        if result['success']:
            logger.info(f"✅ Order canceled: {data['order_id']}")
            return jsonify(result), 200
        else:
            logger.warning(f"⚠️  Order cancellation failed: {result.get('error')}")
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Error canceling order: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'details': str(e)
        }), 500


@app.route('/api/v1/orders/cancel-all', methods=['POST'])
def cancel_all_orders():
    """
    Cancel all open orders for a user on a specific exchange
    
    Request Body:
        {
            "user_id": "string" (required),
            "exchange_id": "string" (required),
            "symbol": "string" (optional, e.g. "PEPE/USDT" - cancel only for this pair)
        }
    
    Returns:
        200: All orders canceled successfully
        400: Invalid request
        500: Internal server error
    """
    try:
        data = request.get_json()
        
        if 'user_id' not in data or 'exchange_id' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing required fields: user_id, exchange_id'
            }), 400
        
        user_id = data['user_id']
        exchange_id = data['exchange_id']
        symbol = data.get('symbol')
        
        # Get user exchange credentials
        user_exchange = db.user_exchanges.find_one({'user_id': user_id})
        
        if not user_exchange or 'exchanges' not in user_exchange:
            return jsonify({
                'success': False,
                'error': 'User has no linked exchanges'
            }), 404
        
        # Find specific exchange
        user_ex = None
        for ex in user_exchange['exchanges']:
            if str(ex['exchange_id']) == exchange_id:
                user_ex = ex
                break
        
        if not user_ex:
            return jsonify({
                'success': False,
                'error': 'Exchange not found for this user'
            }), 404
        
        # Get exchange info
        exchange_info = db.exchanges.find_one({'_id': ObjectId(exchange_id)})
        
        if not exchange_info:
            return jsonify({
                'success': False,
                'error': 'Exchange not found in database'
            }), 404
        
        ccxt_id = exchange_info.get('ccxt_id', '').lower()
        
        # Decrypt credentials
        encryption_service = get_encryption_service()
        decrypted = encryption_service.decrypt_credentials({
            'api_key': user_ex['api_key_encrypted'],
            'api_secret': user_ex['api_secret_encrypted'],
            'passphrase': user_ex.get('passphrase_encrypted')
        })
        
        # Create CCXT exchange instance
        exchange_class = getattr(ccxt, ccxt_id)
        exchange = exchange_class({
            'apiKey': decrypted['api_key'],
            'secret': decrypted['api_secret'],
            'password': decrypted.get('passphrase'),
            'enableRateLimit': True
        })
        
        # Suppress Binance warning
        if ccxt_id == 'binance':
            exchange.options['warnOnFetchOpenOrdersWithoutSymbol'] = False
        
        # Check if DRY-RUN mode
        dry_run = os.getenv('STRATEGY_DRY_RUN', 'true').lower() == 'true'
        
        # Fetch open orders
        if symbol:
            open_orders = exchange.fetch_open_orders(symbol)
        else:
            open_orders = exchange.fetch_open_orders()
        
        if not open_orders:
            return jsonify({
                'success': True,
                'message': 'No open orders to cancel',
                'canceled_count': 0,
                'orders': []
            }), 200
        
        # DRY-RUN mode
        if dry_run:
            logger.info(f"🔴 [DRY-RUN] Would cancel {len(open_orders)} orders on {exchange_info.get('nome')}")
            return jsonify({
                'success': True,
                'dry_run': True,
                'message': f'Would cancel {len(open_orders)} orders (DRY-RUN mode)',
                'canceled_count': len(open_orders),
                'orders': [{'id': order['id'], 'symbol': order['symbol'], 'status': 'simulated_cancel'} for order in open_orders]
            }), 200
        
        # Cancel all orders
        canceled_orders = []
        failed_orders = []
        
        for order in open_orders:
            try:
                order_id = order['id']
                order_symbol = order['symbol']
                
                logger.info(f"🔴 Canceling order: {order_id} ({order_symbol})")
                canceled = exchange.cancel_order(order_id, order_symbol)
                
                canceled_orders.append({
                    'id': order_id,
                    'symbol': order_symbol,
                    'status': 'canceled',
                    'amount': order.get('amount'),
                    'price': order.get('price')
                })
                
            except Exception as e:
                logger.error(f"Failed to cancel order {order.get('id')}: {e}")
                failed_orders.append({
                    'id': order.get('id'),
                    'symbol': order.get('symbol'),
                    'error': str(e)
                })
        
        logger.info(f"✅ Canceled {len(canceled_orders)} orders on {exchange_info.get('nome')}")
        
        return jsonify({
            'success': True,
            'dry_run': False,
            'message': f'Canceled {len(canceled_orders)} of {len(open_orders)} orders',
            'canceled_count': len(canceled_orders),
            'failed_count': len(failed_orders),
            'exchange': exchange_info.get('nome'),
            'canceled_orders': canceled_orders,
            'failed_orders': failed_orders
        }), 200
        
    except ccxt.AuthenticationError as e:
        logger.error(f"Authentication error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Authentication failed',
            'details': str(e)
        }), 401
    except ccxt.ExchangeError as e:
        logger.error(f"Exchange error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Exchange API error',
            'details': str(e)
        }), 400
    except Exception as e:
        logger.error(f"Error canceling all orders: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'details': str(e)
        }), 500


@app.route('/api/v1/orders/list', methods=['GET'])
def list_orders():
    """
    List orders with optional filters
    
    Query Parameters:
        - user_id: string (required)
        - exchange_id: string (optional)
        - symbol: string (optional, e.g., BTC/USDT)
        - status: string (optional, e.g., open, closed, canceled)
        - limit: int (optional, default 50, max 100)
    
    Returns:
        200: List of orders
        400: Missing required parameters
        500: Internal server error
    """
    try:
        user_id = request.args.get('user_id')
        
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'Missing required parameter: user_id'
            }), 400
        
        exchange_id = request.args.get('exchange_id')
        symbol = request.args.get('symbol')
        status = request.args.get('status')
        limit = min(int(request.args.get('limit', 50)), 100)
        
        dry_run = os.getenv('STRATEGY_DRY_RUN', 'true').lower() == 'true'
        order_service = get_order_execution_service(db, dry_run=dry_run)
        result = order_service.list_orders(
            user_id=user_id,
            exchange_id=exchange_id,
            symbol=symbol,
            status=status,
            limit=limit
        )
        
        logger.info(f"📋 Listed {result.get('count', 0)} orders for user {user_id}")
        return jsonify(result), 200
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': f'Invalid parameter format: {str(e)}'
        }), 400
    except Exception as e:
        logger.error(f"Error listing orders: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'details': str(e)
        }), 500


@app.route('/api/v1/trades/history', methods=['GET'])
def get_trades_history():
    """
    Get completed trades history
    
    Query Parameters:
        - user_id: string (required)
        - exchange_id: string (optional)
        - symbol: string (optional)
        - limit: int (optional, default 50, max 100)
    
    Returns:
        200: Trades history
        400: Missing required parameters
        500: Internal server error
    """
    try:
        user_id = request.args.get('user_id')
        
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'Missing required parameter: user_id'
            }), 400
        
        exchange_id = request.args.get('exchange_id')
        symbol = request.args.get('symbol')
        limit = min(int(request.args.get('limit', 50)), 100)
        
        dry_run = os.getenv('STRATEGY_DRY_RUN', 'true').lower() == 'true'
        order_service = get_order_execution_service(db, dry_run=dry_run)
        result = order_service.get_trades_history(
            user_id=user_id,
            exchange_id=exchange_id,
            symbol=symbol,
            limit=limit
        )
        
        logger.info(f"📊 Retrieved {result.get('count', 0)} trades for user {user_id}")
        return jsonify(result), 200
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': f'Invalid parameter format: {str(e)}'
        }), 400
    except Exception as e:
        logger.error(f"Error getting trades history: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'details': str(e)
        }), 500


@app.route('/api/v1/orders/monitor', methods=['POST'])
def monitor_orders():
    """
    Manually trigger order status monitoring
    
    Request Body (optional):
        {
            "user_id": "string",      // Monitor only this user's orders
            "exchange_id": "string",  // Monitor only orders from this exchange
            "order_id": "string"      // Monitor specific order
        }
    
    Returns:
        200: Monitoring results
        500: Internal server error
    """
    try:
        data = request.get_json() or {}
        dry_run = os.getenv('STRATEGY_DRY_RUN', 'true').lower() == 'true'
        order_service = get_order_execution_service(db, dry_run=dry_run)
        
        # If specific order_id is provided, monitor only that order
        if data.get('order_id'):
            order_id = data['order_id']
            logger.info(f"🔍 Manual monitoring triggered for order {order_id}")
            
            result = order_service.monitor_order_status(order_id)
            
            return jsonify(result), 200
        
        # Monitor by user_id and/or exchange_id
        else:
            user_id = data.get('user_id')
            exchange_id = data.get('exchange_id')
            
            # Build query filter
            from bson import ObjectId
            query = {'status': {'$in': ['open', 'partially_filled']}}
            
            if user_id:
                query['user_id'] = user_id
            
            if exchange_id:
                query['exchange_id'] = ObjectId(exchange_id)
            
            # Get filtered orders
            open_orders = list(db.orders.find(query))
            
            filter_desc = []
            if user_id:
                filter_desc.append(f"user {user_id}")
            if exchange_id:
                filter_desc.append(f"exchange {exchange_id}")
            
            filter_text = " and ".join(filter_desc) if filter_desc else "all open orders"
            logger.info(f"🔍 Manual monitoring triggered for {filter_text} ({len(open_orders)} orders)")
            
            # Monitor each order
            results = {
                'total': len(open_orders),
                'updated': 0,
                'errors': 0,
                'closed': 0,
                'orders': []
            }
            
            for order in open_orders:
                result = order_service.monitor_order_status(str(order['_id']))
                
                if result.get('success'):
                    if result.get('updated'):
                        results['updated'] += 1
                        if result.get('new_status') in ['closed', 'filled']:
                            results['closed'] += 1
                    
                    results['orders'].append({
                        'order_id': str(order['_id']),
                        'symbol': order['symbol'],
                        'status': result.get('new_status') or result.get('status'),
                        'updated': result.get('updated', False)
                    })
                else:
                    results['errors'] += 1
                    results['orders'].append({
                        'order_id': str(order['_id']),
                        'symbol': order['symbol'],
                        'error': result.get('error')
                    })
            
            logger.info(f"✅ Monitoring complete: {results['updated']} updated, {results['closed']} closed, {results['errors']} errors")
            
            return jsonify({
                'success': True,
                **results
            }), 200
        
    except Exception as e:
        logger.error(f"Error monitoring orders: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'details': str(e)
        }), 500


@app.route('/api/v1/orders/status/<order_id>', methods=['GET'])
def get_order_status(order_id):
    """
    Get current status of a specific order
    
    Path Parameters:
        - order_id: string (MongoDB ObjectId)
    
    Query Parameters:
        - refresh: boolean (optional) - Force refresh from exchange (default: false)
    
    Returns:
        200: Order status
        404: Order not found
        500: Internal server error
    """
    try:
        refresh = request.args.get('refresh', 'false').lower() == 'true'
        dry_run = os.getenv('STRATEGY_DRY_RUN', 'true').lower() == 'true'
        order_service = get_order_execution_service(db, dry_run=dry_run)
        
        # If refresh requested, update from exchange first
        if refresh:
            logger.info(f"🔄 Refreshing order status from exchange: {order_id}")
            monitor_result = order_service.monitor_order_status(order_id)
            
            if not monitor_result.get('success'):
                return jsonify({
                    'success': False,
                    'error': monitor_result.get('error', 'Failed to refresh order status')
                }), 500
        
        # Get order from database
        from bson import ObjectId
        order_doc = db.orders.find_one({'_id': ObjectId(order_id)})
        
        if not order_doc:
            return jsonify({
                'success': False,
                'error': 'Order not found'
            }), 404
        
        # Format response
        order_data = {
            'success': True,
            'order': {
                'order_id': str(order_doc['_id']),
                'exchange_order_id': order_doc['exchange_order_id'],
                'exchange_name': order_doc['exchange_name'],
                'symbol': order_doc['symbol'],
                'side': order_doc['side'],
                'type': order_doc['type'],
                'amount': order_doc['amount'],
                'price': order_doc.get('price'),
                'filled': order_doc.get('filled', 0),
                'remaining': order_doc.get('remaining', 0),
                'status': order_doc['status'],
                'created_at': order_doc['created_at'].isoformat(),
                'updated_at': order_doc['updated_at'].isoformat(),
                'last_checked_at': order_doc.get('last_checked_at').isoformat() if order_doc.get('last_checked_at') else None
            }
        }
        
        logger.info(f"📊 Order status retrieved: {order_id} - {order_doc['status']}")
        return jsonify(order_data), 200
        
    except Exception as e:
        logger.error(f"Error getting order status: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'details': str(e)
        }), 500


# ======================
# BALANCE HISTORY
# ======================

@app.route('/api/v1/history', methods=['GET'])
def get_balance_history():
    """
    Busca histórico de saldos salvos a cada hora pelo snapshot automático.
    
    Query Parameters:
        - user_id (required): ID do usuário
        - limit (optional): Máximo de registros (padrão: 168 = 7 dias)
    
    Returns:
        200: Lista de snapshots históricos
        400: user_id não fornecido
        500: Erro interno
    """
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'user_id is required'
            }), 400
        
        limit = int(request.args.get('limit', 168))  # 7 dias * 24 horas
        
        history_service = get_balance_history_service(db)
        snapshots = history_service.get_history(user_id, limit=limit, skip=0)
        
        return jsonify({
            'success': True,
            'user_id': user_id,
            'count': len(snapshots),
            'snapshots': snapshots
        }), 200
        
    except ValueError:
        return jsonify({
            'success': False,
            'error': 'Invalid limit parameter'
        }), 400
    except Exception as e:
        logger.error(f"Error getting history: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'details': str(e)
        }), 500


@app.route('/api/v1/history/evolution', methods=['GET'])
def get_portfolio_evolution():
    """
    Busca evolução do portfolio para gráficos (agregado por dia).
    Ideal para exibir tendências e variações ao longo do tempo.
    
    Query Parameters:
        - user_id (required): ID do usuário
        - days (optional): Dias para retornar (padrão: 30)
    
    Returns:
        200: Dados de evolução com sumário estatístico
        400: user_id não fornecido ou days inválido
        500: Erro interno
    """
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'user_id is required'
            }), 400
        
        days = int(request.args.get('days', 30))
        
        history_service = get_balance_history_service(db)
        evolution = history_service.get_portfolio_evolution(user_id, days=days)
        
        return jsonify({
            'success': True,
            'user_id': user_id,
            'days': days,
            'evolution': evolution
        }), 200
        
    except ValueError:
        return jsonify({
            'success': False,
            'error': 'Invalid days parameter'
        }), 400
    except Exception as e:
        logger.error(f"Error getting evolution: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'details': str(e)
        }), 500

@app.route('/api/v1/exchanges/<exchange_id>/token/<symbol>', methods=['GET'])
def get_exchange_token_info(exchange_id, symbol):
    """
    Busca informações completas de um token direto da exchange,
    incluindo contratos, variações de preço e dados do balanço do usuário.
    
    Query Parameters:
    - user_id: ID do usuário (opcional, para incluir dados do balanço)
    - quote: Moeda de cotação (USD ou USDT, padrão: USDT)
    - include_variations: true para incluir variações 1h/4h (default: false, mais rápido)
    """
    try:
        symbol = symbol.upper()
        user_id = request.args.get('user_id')
        quote = request.args.get('quote', 'USDT').upper()
        include_variations = request.args.get('include_variations', 'false').lower() == 'true'
        
        logger.debug(f"Fetching {symbol} info from exchange {exchange_id}")
        
        # Buscar informações da exchange no banco
        from bson import ObjectId
        exchange_doc = db.exchanges.find_one({'_id': ObjectId(exchange_id)})
        
        if not exchange_doc:
            return jsonify({
                'success': False,
                'error': f'Exchange not found: {exchange_id}'
            }), 404
        
        ccxt_id = exchange_doc.get('ccxt_id')
        exchange_name = exchange_doc.get('nome', ccxt_id)
        
        logger.debug(f"Exchange: {exchange_name} ({ccxt_id})")
        
        # Validar se exchange é suportada pelo CCXT
        if ccxt_id not in ccxt.exchanges:
            return jsonify({
                'success': False,
                'error': f'Exchange {ccxt_id} not supported by CCXT'
            }), 400
        
        # Inicializar exchange com timeout (OTIMIZAÇÃO: Timeout de 3s)
        exchange_class = getattr(ccxt, ccxt_id)
        exchange = exchange_class({
            'enableRateLimit': True,
            'timeout': 3000  # 3 segundos timeout
        })
        
        # Carregar mercados
        exchange.load_markets()
        
        # Tentar diferentes pares (incluindo BRL para exchanges brasileiras)
        pair = None
        for q in [quote, 'USDT', 'USD', 'BRL', 'BTC']:
            test_pair = f"{symbol}/{q}"
            if test_pair in exchange.markets:
                pair = test_pair
                quote = q
                break
        
        if not pair:
            return jsonify({
                'success': False,
                'error': f'Token {symbol} not found on {exchange_name}',
                'details': f'{exchange_name} does not have market for {symbol}'
            }), 404
        
        logger.debug(f"Trading pair: {pair}")
        
        # OTIMIZAÇÃO: Paralelizar chamadas CCXT com ThreadPoolExecutor
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        def fetch_ticker_data():
            """Buscar ticker (preço atual, volume, high/low)"""
            return exchange.fetch_ticker(pair)
        
        def fetch_ohlcv_data(timeframe):
            """Buscar OHLCV para calcular variações"""
            try:
                ohlcv = exchange.fetch_ohlcv(pair, timeframe, limit=2)
                if len(ohlcv) >= 2:
                    old_price = ohlcv[0][4]  # Close do período anterior
                    current_price = ohlcv[-1][4]  # Close atual
                    change = current_price - old_price
                    change_percent = (change / old_price * 100) if old_price > 0 else 0
                    return {
                        'timeframe': timeframe,
                        'price_change': format_price(change),
                        'price_change_percent': format_percent(change_percent)
                    }
            except Exception as e:
                logger.warning(f"Error fetching {timeframe} OHLCV: {e}")
            return None
        
        # Executar chamadas em paralelo
        ticker = None
        ohlcv_1h = None
        ohlcv_4h = None
        
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {'ticker': executor.submit(fetch_ticker_data)}
            
            # Apenas buscar variações se solicitado (OTIMIZAÇÃO: Opcional)
            if include_variations:
                futures['ohlcv_1h'] = executor.submit(fetch_ohlcv_data, '1h')
                futures['ohlcv_4h'] = executor.submit(fetch_ohlcv_data, '4h')
            
            # Coletar resultados com timeout de 4s total
            for future_name, future in futures.items():
                try:
                    result = future.result(timeout=4)
                    if future_name == 'ticker':
                        ticker = result
                    elif future_name == 'ohlcv_1h':
                        ohlcv_1h = result
                    elif future_name == 'ohlcv_4h':
                        ohlcv_4h = result
                except Exception as e:
                    logger.warning(f"Error in {future_name}: {e}")
        
        if not ticker:
            return jsonify({
                'success': False,
                'error': 'Failed to fetch ticker data'
            }), 500
        
        # Variação 24h vem do ticker (sempre disponível)
        ohlcv_24h = None
        if ticker.get('percentage') is not None:
            ohlcv_24h = {
                'price_change': format_price(ticker.get('change', 0)),
                'price_change_percent': format_percent(ticker.get('percentage', 0))
            }
        
        # 3. Buscar informações do mercado (inclui contratos quando disponível)
        market_info = exchange.markets.get(pair, {})
        
        # 4. Buscar dados de contrato/endereço
        contract_info = {}
        if 'info' in market_info:
            info = market_info['info']
            # Diferentes exchanges armazenam contratos de formas diferentes
            contract_address = (
                info.get('contractAddress') or 
                info.get('contract_address') or
                info.get('address') or
                info.get('tokenAddress') or
                info.get('token_address')
            )
            if contract_address:
                contract_info['address'] = contract_address
            
            # Buscar blockchain/network
            network = (
                info.get('network') or
                info.get('chain') or
                info.get('blockchain') or
                market_info.get('network')
            )
            if network:
                contract_info['network'] = network
        
        # 5. Buscar dados do balanço do usuário do cache (OTIMIZAÇÃO: Apenas cache, sem refresh)
        user_balance = None
        if user_id:
            try:
                # Buscar apenas do cache MongoDB (muito mais rápido)
                cached_balance = db.balance_cache.find_one(
                    {'user_id': user_id},
                    sort=[('timestamp', -1)]
                )
                
                if cached_balance:
                    for ex_balance in cached_balance.get('exchanges', []):
                        if str(ex_balance.get('exchange_id')) == exchange_id:
                            tokens = ex_balance.get('tokens', {})
                            if symbol in tokens:
                                token_data = tokens[symbol]
                                # Convert strings back to float if needed
                                amount_val = token_data.get('amount', 0)
                                if isinstance(amount_val, str):
                                    amount_val = float(amount_val)
                                value_val = token_data.get('value_usd', 0)
                                if isinstance(value_val, str):
                                    value_val = float(value_val)
                                
                                user_balance = {
                                    'amount': format_price(amount_val),
                                    'value_usd': format_usd(value_val),
                                    'last_updated': cached_balance.get('timestamp')
                                }
                            break
            except Exception as e:
                logger.warning(f"Could not fetch user balance from cache: {e}")
        
        # 6. Buscar ícone do token
        icon_url = None
        try:
            from src.services.price_feed_service import PriceFeedService
            price_service = PriceFeedService()
            icon_url = price_service.get_token_icon(
                symbol=symbol,
                contract_address=contract_info.get('address') if contract_info else None,
                network=contract_info.get('network') if contract_info else None
            )
            if icon_url:
                logger.debug(f"Icon found: {icon_url}")
        except Exception as e:
            logger.warning(f"Could not fetch token icon: {e}")
        
        # Construir resposta completa
        result = {
            'symbol': symbol,
            'quote': quote,
            'pair': pair,
            'exchange': {
                'id': exchange_id,
                'name': exchange_name,
                'ccxt_id': ccxt_id
            },
            'icon_url': icon_url,
            'price': {
                'current': format_price(ticker.get('last', 0)),
                'bid': format_price(ticker.get('bid', 0)),
                'ask': format_price(ticker.get('ask', 0)),
                'high_24h': format_price(ticker.get('high', 0)),
                'low_24h': format_price(ticker.get('low', 0))
            },
            'volume': {
                'base_24h': format_usd(ticker.get('baseVolume', 0)),
                'quote_24h': format_usd(ticker.get('quoteVolume', 0))
            },
            'change': {
                '1h': ohlcv_1h,
                '4h': ohlcv_4h,
                '24h': ohlcv_24h
            },
            'contract': contract_info if contract_info else None,
            'user_balance': user_balance,
            'market_info': {
                'active': market_info.get('active', True),
                'precision': {
                    'amount': market_info.get('precision', {}).get('amount'),
                    'price': market_info.get('precision', {}).get('price')
                },
                'limits': market_info.get('limits', {})
            },
            'timestamp': ticker.get('timestamp'),
            'datetime': ticker.get('datetime')
        }
        
        logger.info(f"Complete token info fetched: {symbol} = ${result['price']['current']}")
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error getting exchange token info: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'details': str(e)
        }), 500

@app.route('/api/v1/exchanges/<exchange_id>', methods=['GET'])
@require_auth
def get_exchange_info(exchange_id):
    """
    Busca informações detalhadas de uma exchange específica.
    
    Path Params:
        exchange_id (required): MongoDB ObjectId da exchange
    
    Query Params:
        include_fees (optional): true para incluir taxas da exchange (padrão: false)
        include_markets (optional): true para incluir lista de mercados (padrão: false)
    
    Returns:
        200: Informações da exchange
        400: exchange_id inválido
        401: Token inválido ou ausente
        404: Exchange não encontrada
        500: Erro interno
    
    Exemplo:
        GET /api/v1/exchanges/693481148b0a41e8b6acb07b
        GET /api/v1/exchanges/693481148b0a41e8b6acb07b?include_fees=true
    """
    try:
        # Valida ObjectId
        if not ObjectId.is_valid(exchange_id):
            return jsonify({
                'success': False,
                'error': 'Invalid exchange_id format'
            }), 400
        
        # Busca exchange no MongoDB
        exchange = db.exchanges.find_one({'_id': ObjectId(exchange_id)})
        
        if not exchange:
            return jsonify({
                'success': False,
                'error': f'Exchange not found: {exchange_id}'
            }), 404
        
        # Dados básicos da exchange
        exchange_info = {
            '_id': str(exchange['_id']),
            'nome': exchange.get('nome'),
            'ccxt_id': exchange.get('ccxt_id'),
            'url': exchange.get('url'),
            'icon': exchange.get('icon'),
            'pais_de_origem': exchange.get('pais_de_origem'),
            'description': exchange.get('description'),
            'is_active': exchange.get('is_active', True),
            'requires_passphrase': exchange.get('requires_passphrase', False)
        }
        
        # Parâmetros opcionais
        include_fees = request.args.get('include_fees', 'false').lower() == 'true'
        include_markets = request.args.get('include_markets', 'false').lower() == 'true'
        
        # Se solicitado, busca informações adicionais via CCXT
        if include_fees or include_markets:
            try:
                ccxt_id = exchange.get('ccxt_id')
                exchange_class = getattr(ccxt, ccxt_id)
                ccxt_exchange = exchange_class()
                
                # Carrega mercados
                ccxt_exchange.load_markets()
                
                # Inclui taxas
                if include_fees:
                    fees = ccxt_exchange.fees
                    exchange_info['fees'] = {
                        'trading': fees.get('trading', {}),
                        'funding': fees.get('funding', {})
                    }
                
                # Inclui lista de mercados
                if include_markets:
                    markets = ccxt_exchange.markets
                    exchange_info['markets'] = {
                        'total': len(markets),
                        'symbols': sorted(list(markets.keys()))[:100]  # Primeiros 100
                    }
                    
                # Informações adicionais do CCXT
                exchange_info['ccxt_info'] = {
                    'has': {
                        'fetchBalance': ccxt_exchange.has.get('fetchBalance', False),
                        'fetchTicker': ccxt_exchange.has.get('fetchTicker', False),
                        'fetchTickers': ccxt_exchange.has.get('fetchTickers', False),
                        'fetchOHLCV': ccxt_exchange.has.get('fetchOHLCV', False),
                        'fetchTrades': ccxt_exchange.has.get('fetchTrades', False),
                        'fetchOrder': ccxt_exchange.has.get('fetchOrder', False),
                        'fetchOrders': ccxt_exchange.has.get('fetchOrders', False),
                        'fetchOpenOrders': ccxt_exchange.has.get('fetchOpenOrders', False),
                        'fetchClosedOrders': ccxt_exchange.has.get('fetchClosedOrders', False),
                        'fetchMyTrades': ccxt_exchange.has.get('fetchMyTrades', False),
                        'createOrder': ccxt_exchange.has.get('createOrder', False),
                        'cancelOrder': ccxt_exchange.has.get('cancelOrder', False)
                    },
                    'timeframes': list(ccxt_exchange.timeframes.keys()) if hasattr(ccxt_exchange, 'timeframes') else [],
                    'rate_limit': ccxt_exchange.rateLimit
                }
                
            except Exception as e:
                logger.warning(f"Could not fetch CCXT data: {e}")
                exchange_info['ccxt_error'] = str(e)
        
        return jsonify({
            'success': True,
            'exchange': exchange_info
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting exchange info: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'details': str(e)
        }), 500

# ============================================
# ENDPOINTS DE ESTRATÉGIAS DE TRADING
# ============================================

def invalidate_strategy_caches(user_id: str, strategy_id: str = None):
    """Invalidate all strategy-related caches for a user"""
    from src.utils.cache import get_strategies_cache, get_single_strategy_cache
    
    strategies_cache = get_strategies_cache()
    single_cache = get_single_strategy_cache()
    
    # Invalidate user's strategies list cache (all filter variations)
    strategies_cache.clear_pattern(f"strategies_{user_id}")
    
    # If strategy_id provided, invalidate that specific strategy caches
    if strategy_id:
        single_cache.delete(f"strategy_{strategy_id}")
        single_cache.delete(f"strategy_stats_{strategy_id}_{user_id}")
    
    logger.debug(f"Strategy cache invalidated for user {user_id}" + (f", strategy {strategy_id}" if strategy_id else ""))

@app.route('/api/v1/strategies', methods=['POST'])
@require_auth
@require_params('user_id', 'exchange_id', 'token')
def create_strategy():
    """
    Cria uma nova estratégia de trading para um token em uma exchange
    
    Suporta 3 modos de criação:
    1. Template Mode (RECOMENDADO): Use "template" para estratégias prontas
    2. Custom Mode: Forneça "rules" completas
    3. Legacy Mode: Use take_profit_percent, stop_loss_percent (deprecated)
    
    Request Body (Template Mode):
        {
            "user_id": "string",
            "exchange_id": "string (MongoDB _id)",
            "token": "string (e.g., 'BTC', 'ETH')",
            "template": "simple" | "conservative" | "aggressive",
            "is_active": bool (optional, default: true)
        }
    
    Request Body (Custom Mode):
        {
            "user_id": "string",
            "exchange_id": "string (MongoDB _id)",
            "token": "string",
            "rules": {
                "take_profit_levels": [...],
                "stop_loss": {...},
                "buy_dip": {...},
                ...
            },
            "is_active": bool (optional, default: true)
        }
    
    Request Body (Legacy Mode - DEPRECATED):
        {
            "user_id": "string",
            "exchange_id": "string (MongoDB _id)",
            "token": "string",
            "take_profit_percent": float,
            "stop_loss_percent": float,
            "buy_dip_percent": float (optional)
        }
    
    Templates disponíveis:
        - simple: Estratégia básica (1 TP 5%, SL 2%, sem trailing)
        - conservative: Proteção máxima (2 TPs, trailing stop, max loss $200/dia)
        - aggressive: Máximo lucro (3 TPs, DCA ativo, max loss $1000/dia)
    
    Returns:
        201: Estratégia criada
        400: Dados inválidos
        401: Token inválido ou ausente
        403: user_id do token não corresponde ao user_id do parâmetro
        500: Erro interno
    
    Exemplos:
        Template Mode:
        {
            "user_id": "user123",
            "exchange_id": "693481148b0a41e8b6acb07b",
            "token": "REKTCOIN",
            "template": "aggressive"
        }
        
        Legacy Mode:
        {
            "user_id": "user123",
            "exchange_id": "693481148b0a41e8b6acb07b",
            "token": "BTC",
            "take_profit_percent": 5,
            "stop_loss_percent": 3
        }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Request body is required'
            }), 400
        
        user_id = request.validated_params['user_id']
        
        # Verify user_id from token matches user_id in params
        if request.user_id != user_id:
            return jsonify({
                'success': False,
                'error': 'Unauthorized: user_id mismatch'
            }), 403
        
        strategy_service = get_strategy_service(db)
        
        # Determinar modo de criação
        if 'template' in data:
            # Template Mode (RECOMENDADO)
            result = strategy_service.create_strategy(
                user_id=request.validated_params['user_id'],
                exchange_id=request.validated_params['exchange_id'],
                token=request.validated_params['token'],
                template=data['template'],
                is_active=data.get('is_active', True)
            )
        elif 'rules' in data:
            # Custom Mode
            result = strategy_service.create_strategy(
                user_id=request.validated_params['user_id'],
                exchange_id=request.validated_params['exchange_id'],
                token=request.validated_params['token'],
                rules=data['rules'],
                is_active=data.get('is_active', True)
            )
        elif 'take_profit_percent' in data:
            # Legacy Mode (DEPRECATED)
            result = strategy_service.create_strategy(
                user_id=request.validated_params['user_id'],
                exchange_id=request.validated_params['exchange_id'],
                token=request.validated_params['token'],
                take_profit_percent=data['take_profit_percent'],
                stop_loss_percent=data['stop_loss_percent'],
                buy_dip_percent=data.get('buy_dip_percent'),
                is_active=data.get('is_active', True)
            )
        else:
            return jsonify({
                'success': False,
                'error': 'Provide either "template", "rules", or "take_profit_percent" + "stop_loss_percent"'
            }), 400
        
        if result['success']:
            # Invalidate cache after creating strategy
            invalidate_strategy_caches(user_id)
            return jsonify(result), 201
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Error creating strategy: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'details': str(e)
        }), 500


@app.route('/api/v1/strategies/<strategy_id>', methods=['PUT'])
def update_strategy(strategy_id):
    """
    Atualiza uma estratégia existente
    
    Path Params:
        strategy_id: MongoDB ObjectId da estratégia
    
    Request Body (todos opcionais):
        {
            "take_profit_percent": float,
            "stop_loss_percent": float,
            "buy_dip_percent": float,
            "is_active": bool
        }
    
    Returns:
        200: Estratégia atualizada
        400: Dados inválidos
        404: Estratégia não encontrada
        500: Erro interno
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Request body is required'
            }), 400
        
        strategy_service = get_strategy_service(db)
        
        result = strategy_service.update_strategy(
            strategy_id=strategy_id,
            take_profit_percent=data.get('take_profit_percent'),
            stop_loss_percent=data.get('stop_loss_percent'),
            buy_dip_percent=data.get('buy_dip_percent'),
            is_active=data.get('is_active')
        )
        
        if result['success']:
            # Invalidate cache after updating (get user_id from result)
            updated_strategy = result.get('strategy', {})
            user_id = updated_strategy.get('user_id')
            if user_id:
                invalidate_strategy_caches(user_id, strategy_id)
            return jsonify(result), 200
        else:
            status_code = 404 if 'not found' in result.get('error', '').lower() else 400
            return jsonify(result), status_code
            
    except Exception as e:
        logger.error(f"Error updating strategy: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'details': str(e)
        }), 500


@app.route('/api/v1/strategies/<strategy_id>', methods=['DELETE'])
@require_auth
def delete_strategy(strategy_id):
    """
    Deleta uma estratégia
    
    Path Params:
        strategy_id: MongoDB ObjectId da estratégia
    
    Returns:
        200: Estratégia deletada
        401: Token inválido ou ausente
        403: Estratégia não pertence ao usuário autenticado
        404: Estratégia não encontrada
        500: Erro interno
    """
    try:
        strategy_service = get_strategy_service(db)
        
        # Get strategy to verify ownership
        strategy = strategy_service.get_strategy(strategy_id)
        
        if not strategy:
            return jsonify({
                'success': False,
                'error': 'Strategy not found'
            }), 404
        
        # Verify that the strategy belongs to the authenticated user
        if strategy.get('user_id') != request.user_id:
            return jsonify({
                'success': False,
                'error': 'Unauthorized: This strategy does not belong to you'
            }), 403
        
        user_id_for_cache = strategy.get('user_id')
        
        result = strategy_service.delete_strategy(strategy_id)
        
        if result['success']:
            # Invalidate cache after deleting
            if user_id_for_cache:
                invalidate_strategy_caches(user_id_for_cache, strategy_id)
            return jsonify(result), 200
        else:
            status_code = 404 if 'not found' in result.get('error', '').lower() else 400
            return jsonify(result), status_code
            
    except Exception as e:
        logger.error(f"Error deleting strategy: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'details': str(e)
        }), 500


@app.route('/api/v1/strategies/<strategy_id>', methods=['GET'])
def get_strategy(strategy_id):
    """
    Busca uma estratégia por ID
    
    Path Params:
        strategy_id: MongoDB ObjectId da estratégia
    
    Query Params:
        force_refresh (optional): Forçar atualização do cache (true/false)
    
    Returns:
        200: Estratégia encontrada
        404: Estratégia não encontrada
        500: Erro interno
    
    Cache: 180 segundos (3 minutos)
    """
    try:
        force_refresh = request.args.get('force_refresh', 'false').lower() == 'true'
        cache_key = f"strategy_{strategy_id}"
        
        # Try to get from cache
        from src.utils.cache import get_single_strategy_cache
        single_cache = get_single_strategy_cache()
        
        if not force_refresh:
            is_valid, cached_data = single_cache.get(cache_key)
            if is_valid:
                logger.debug(f"Cache HIT for strategy: {strategy_id}")
                response_data = cached_data.copy()
                response_data['from_cache'] = True
                return jsonify(response_data), 200
        
        logger.debug(f"Cache MISS for strategy: {strategy_id}")
        
        # Get from database
        strategy_service = get_strategy_service(db)
        strategy = strategy_service.get_strategy(strategy_id)
        
        if strategy:
            response_data = {
                'success': True,
                'strategy': strategy,
                'from_cache': False
            }
            
            # Store in cache
            single_cache.set(cache_key, response_data)
            
            return jsonify(response_data), 200
        else:
            return jsonify({
                'success': False,
                'error': f'Strategy not found: {strategy_id}'
            }), 404
            
    except Exception as e:
        logger.error(f"Error getting strategy: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'details': str(e)
        }), 500


@app.route('/api/v1/strategies', methods=['GET'])
@require_auth
@require_params('user_id')
def get_user_strategies():
    """
    Lista todas as estratégias de um usuário com filtros opcionais
    
    Query Params:
        user_id (required): ID do usuário
        exchange_id (optional): Filtrar por exchange
        token (optional): Filtrar por token
        is_active (optional): Filtrar por status (true/false)
        force_refresh (optional): Forçar atualização do cache (true/false)
    
    Returns:
        200: Lista de estratégias
        400: user_id não fornecido
        401: Token inválido ou ausente
        403: user_id do token não corresponde ao user_id do parâmetro
        500: Erro interno
    
    Cache: 120 segundos (2 minutos)
    
    Exemplo:
        GET /api/v1/strategies?user_id=charles_test_user
        GET /api/v1/strategies?user_id=charles_test_user&exchange_id=693481148b0a41e8b6acb07b
        GET /api/v1/strategies?user_id=charles_test_user&token=BTC&is_active=true
        GET /api/v1/strategies?user_id=charles_test_user&force_refresh=true
    """
    try:
        user_id = request.validated_params['user_id']
        
        # Verify user_id from token matches user_id in params
        if request.user_id != user_id:
            return jsonify({
                'success': False,
                'error': 'Unauthorized: user_id mismatch'
            }), 403
        
        exchange_id = request.args.get('exchange_id')
        token = request.args.get('token')
        is_active_str = request.args.get('is_active')
        is_active = None if is_active_str is None else is_active_str.lower() == 'true'
        force_refresh = request.args.get('force_refresh', 'false').lower() == 'true'
        
        # Build cache key including filters
        cache_key = f"strategies_{user_id}"
        if exchange_id:
            cache_key += f"_ex_{exchange_id}"
        if token:
            cache_key += f"_tk_{token}"
        if is_active is not None:
            cache_key += f"_act_{is_active}"
        
        # Try to get from cache
        from src.utils.cache import get_strategies_cache
        strategies_cache = get_strategies_cache()
        
        if not force_refresh:
            is_valid, cached_data = strategies_cache.get(cache_key)
            if is_valid:
                logger.debug(f"Cache HIT for strategies: {cache_key}")
                response_data = cached_data.copy()
                response_data['from_cache'] = True
                return jsonify(response_data), 200
        
        logger.debug(f"Cache MISS for strategies: {cache_key}")
        
        # Get from database
        strategy_service = get_strategy_service(db)
        strategies = strategy_service.get_user_strategies(
            user_id=user_id,
            exchange_id=exchange_id,
            token=token,
            is_active=is_active
        )
        
        response_data = {
            'success': True,
            'count': len(strategies),
            'strategies': strategies,
            'from_cache': False
        }
        
        # Store in cache
        strategies_cache.set(cache_key, response_data)
        
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"Error getting strategies: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'details': str(e)
        }), 500


@app.route('/api/v1/strategies/<strategy_id>/check', methods=['POST'])
def check_strategy_trigger(strategy_id):
    """
    Verifica se uma estratégia deve ser acionada com base no preço atual
    
    Path Params:
        strategy_id: MongoDB ObjectId da estratégia
    
    Request Body:
        {
            "current_price": float,
            "entry_price": float
        }
    
    Returns:
        200: Resultado da verificação
        400: Dados inválidos
        404: Estratégia não encontrada
        500: Erro interno
    
    Response Example:
        {
            "should_trigger": true,
            "action": "SELL",
            "reason": "TAKE_PROFIT",
            "trigger_percent": 5.0,
            "current_change_percent": 6.5,
            "strategy": {...}
        }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Request body is required'
            }), 400
        
        if 'current_price' not in data or 'entry_price' not in data:
            return jsonify({
                'success': False,
                'error': 'current_price and entry_price are required'
            }), 400
        
        strategy_service = get_strategy_service(db)
        
        result = strategy_service.check_strategy_triggers(
            strategy_id=strategy_id,
            current_price=float(data['current_price']),
            entry_price=float(data['entry_price'])
        )
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error checking strategy trigger: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'details': str(e)
        }), 500


@app.route('/api/v1/strategies/<strategy_id>/stats', methods=['GET'])
def get_strategy_stats(strategy_id):
    """
    Busca estatísticas de execução de uma estratégia
    
    Path Params:
        strategy_id: MongoDB ObjectId da estratégia
    
    Query Params:
        user_id (required): ID do usuário (para segurança)
        force_refresh (optional): Forçar atualização do cache (true/false)
    
    Returns:
        200: Estatísticas da estratégia
        400: user_id não fornecido
        403: Estratégia não pertence ao usuário
        404: Estratégia não encontrada
        500: Erro interno
    
    Cache: 180 segundos (3 minutos)
    
    Response Example:
        {
            "success": true,
            "stats": {
                "total_executions": 15,
                "total_buys": 8,
                "total_sells": 7,
                "last_execution_at": "2024-12-14T10:30:00.000Z",
                "last_execution_type": "SELL",
                "last_execution_reason": "TAKE_PROFIT",
                "last_execution_price": 106500.00,
                "last_execution_amount": 0.005,
                "total_pnl_usd": 1250.50,
                "daily_pnl_usd": 125.00,
                "weekly_pnl_usd": 450.00,
                "monthly_pnl_usd": 1250.50,
                "win_rate": 71.4,
                "avg_profit_per_trade": 178.64
            },
            "strategy_info": {
                "_id": "674a1234567890abcdef1234",
                "token": "BTC",
                "exchange_name": "NovaDAX",
                "is_active": true,
                "created_at": "2024-11-30T10:00:00.000Z"
            }
        }
    """
    try:
        user_id = request.args.get('user_id')
        
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'user_id is required as query parameter'
            }), 400
        
        force_refresh = request.args.get('force_refresh', 'false').lower() == 'true'
        cache_key = f"strategy_stats_{strategy_id}_{user_id}"
        
        # Try to get from cache
        from src.utils.cache import get_single_strategy_cache
        single_cache = get_single_strategy_cache()
        
        if not force_refresh:
            is_valid, cached_data = single_cache.get(cache_key)
            if is_valid:
                logger.debug(f"Cache HIT for strategy stats: {strategy_id}")
                response_data = cached_data.copy()
                response_data['from_cache'] = True
                return jsonify(response_data), 200
        
        logger.debug(f"Cache MISS for strategy stats: {strategy_id}")
        
        # Get strategy from database
        strategy_service = get_strategy_service(db)
        strategy = strategy_service.get_strategy(strategy_id)
        
        if not strategy:
            return jsonify({
                'success': False,
                'error': f'Strategy not found: {strategy_id}'
            }), 404
        
        # Security check: verify strategy belongs to user
        if strategy.get('user_id') != user_id:
            return jsonify({
                'success': False,
                'error': 'Strategy does not belong to this user'
            }), 403
        
        # Extract execution stats
        exec_stats = strategy.get('execution_stats', {})
        
        # Calculate additional metrics
        total_sells = exec_stats.get('total_sells', 0)
        total_pnl = exec_stats.get('total_pnl_usd', 0)
        
        # Win rate (simplified: sells with profit / total sells)
        win_rate = 0
        if total_sells > 0 and total_pnl > 0:
            # Rough estimate assuming average distribution
            win_rate = round((total_pnl / abs(total_pnl)) * 100, 2) if total_pnl != 0 else 0
        
        # Average profit per trade
        avg_profit = round(total_pnl / total_sells, 2) if total_sells > 0 else 0
        
        response_data = {
            'success': True,
            'stats': {
                'total_executions': exec_stats.get('total_executions', 0),
                'total_buys': exec_stats.get('total_buys', 0),
                'total_sells': exec_stats.get('total_sells', 0),
                'last_execution_at': exec_stats.get('last_execution_at'),
                'last_execution_type': exec_stats.get('last_execution_type'),
                'last_execution_reason': exec_stats.get('last_execution_reason'),
                'last_execution_price': exec_stats.get('last_execution_price'),
                'last_execution_amount': exec_stats.get('last_execution_amount'),
                'total_pnl_usd': round(total_pnl, 2),
                'daily_pnl_usd': round(exec_stats.get('daily_pnl_usd', 0), 2),
                'weekly_pnl_usd': round(exec_stats.get('weekly_pnl_usd', 0), 2),
                'monthly_pnl_usd': round(exec_stats.get('monthly_pnl_usd', 0), 2),
                'win_rate': win_rate,
                'avg_profit_per_trade': avg_profit
            },
            'strategy_info': {
                '_id': str(strategy['_id']),
                'token': strategy.get('token'),
                'exchange_name': strategy.get('exchange_name'),
                'is_active': strategy.get('is_active', True),
                'created_at': strategy.get('created_at')
            },
            'from_cache': False
        }
        
        # Store in cache
        single_cache.set(cache_key, response_data)
        
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"Error getting strategy stats: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'details': str(e)
        }), 500

# ============================================
# TOKEN SEARCH ENDPOINT
# ============================================

@app.route('/api/v1/tokens/search', methods=['GET'])
def search_token():
    """
    🔍 Busca informações de um token em uma exchange específica
    Verifica se o par existe e retorna dados como preço, volume, variação, etc.
    
    Query Params:
        user_id (required): ID do usuário
        exchange_id (required): MongoDB ObjectId da exchange
        token (required): Símbolo do token (ex: PEPE, BTC, ETH)
        quote (optional): Moeda de cotação (default: USDT, tenta USD, USDC, BUSD)
    
    Returns:
        200: Dados do token encontrado
        400: Parâmetros faltando
        404: Token/par não encontrado na exchange
        500: Erro interno
    
    Response Example:
        {
            "success": true,
            "token": "PEPE",
            "exchange": {
                "id": "693481148b0a41e8b6acb07b",
                "name": "Binance",
                "ccxt_id": "binance"
            },
            "pair": "PEPE/USDT",
            "ticker": {
                "symbol": "PEPE/USDT",
                "last": 0.00001234,
                "bid": 0.00001233,
                "ask": 0.00001235,
                "high": 0.00001250,
                "low": 0.00001200,
                "volume": 1234567890.50,
                "change": 5.67,
                "percentage": 5.67,
                "timestamp": 1702835400000
            },
            "usd_price": 0.00001234
        }
    """
    try:
        user_id = request.args.get('user_id')
        exchange_id = request.args.get('exchange_id')
        token = request.args.get('token', '').upper().strip()
        preferred_quote = request.args.get('quote', 'USDT').upper()
        force_refresh = request.args.get('force_refresh', 'false').lower() == 'true'
        
        # Validate required params
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'user_id is required as query parameter'
            }), 400
        
        if not exchange_id:
            return jsonify({
                'success': False,
                'error': 'exchange_id is required as query parameter'
            }), 400
        
        if not token:
            return jsonify({
                'success': False,
                'error': 'token is required as query parameter'
            }), 400
        
        # Check cache first (unless force_refresh is true)
        from src.utils.cache import get_token_search_cache
        token_cache = get_token_search_cache()
        cache_key = f"token_search_{user_id}_{exchange_id}_{token}_{preferred_quote}"
        
        if not force_refresh:
            is_valid, cached_data = token_cache.get(cache_key)
            if is_valid:
                logger.debug(f"💾 Cache HIT for token search: {token} on exchange {exchange_id}")
                cached_response = cached_data.copy()
                cached_response['from_cache'] = True
                return jsonify(cached_response), 200
        
        logger.debug(f"🔍 Cache MISS for token search: {token} on exchange {exchange_id}")
        
        # Get exchange info from database
        try:
            exchange_info = db.exchanges.find_one({'_id': ObjectId(exchange_id)})
        except:
            return jsonify({
                'success': False,
                'error': 'Invalid exchange_id format'
            }), 400
        
        if not exchange_info:
            return jsonify({
                'success': False,
                'error': f'Exchange not found: {exchange_id}'
            }), 404
        
        # Get user exchange credentials
        user_doc = db.user_exchanges.find_one({'user_id': user_id})
        
        if not user_doc or 'exchanges' not in user_doc:
            return jsonify({
                'success': False,
                'error': 'User has no linked exchanges'
            }), 404
        
        # Find this specific exchange link
        exchange_link = None
        for ex in user_doc['exchanges']:
            if str(ex['exchange_id']) == exchange_id:
                exchange_link = ex
                break
        
        if not exchange_link:
            return jsonify({
                'success': False,
                'error': f'Exchange {exchange_info["nome"]} not linked to this user'
            }), 404
        
        # Decrypt credentials
        encryption_service = get_encryption_service()
        decrypted = encryption_service.decrypt_credentials({
            'api_key': exchange_link['api_key_encrypted'],
            'api_secret': exchange_link['api_secret_encrypted'],
            'passphrase': exchange_link.get('passphrase_encrypted')
        })
        
        # Create exchange instance
        exchange_class = getattr(ccxt, exchange_info['ccxt_id'])
        config = {
            'apiKey': decrypted['api_key'],
            'secret': decrypted['api_secret'],
            'enableRateLimit': True,
            'timeout': 10000,
            'options': {'defaultType': 'spot'}
        }
        
        if decrypted.get('passphrase'):
            config['password'] = decrypted['passphrase']
        
        exchange = exchange_class(config)
        
        # Try to find the trading pair
        # Priority order: USDT, USD, USDC, BUSD
        quote_currencies = [preferred_quote]
        if preferred_quote not in ['USDT', 'USD', 'USDC', 'BUSD']:
            quote_currencies.extend(['USDT', 'USD', 'USDC', 'BUSD'])
        else:
            # Add other common quotes if preferred not found
            for q in ['USDT', 'USD', 'USDC', 'BUSD']:
                if q not in quote_currencies:
                    quote_currencies.append(q)
        
        ticker = None
        pair = None
        
        logger.info(f"🔍 Searching for {token} in {exchange_info['nome']}...")
        
        for quote in quote_currencies:
            symbol = f"{token}/{quote}"
            try:
                logger.debug(f"Trying pair: {symbol}")
                ticker = exchange.fetch_ticker(symbol)
                pair = symbol
                logger.info(f"✅ Found pair: {pair}")
                break
            except ccxt.BadSymbol as e:
                logger.debug(f"Pair {symbol} not found: {str(e)}")
                continue
            except Exception as e:
                logger.debug(f"Error fetching {symbol}: {str(e)}")
                continue
        
        if not ticker or not pair:
            return jsonify({
                'success': False,
                'error': f'Token {token} not found in {exchange_info["nome"]}',
                'message': f'Tried pairs: {", ".join([f"{token}/{q}" for q in quote_currencies])}',
                'exchange': {
                    'id': str(exchange_info['_id']),
                    'name': exchange_info['nome'],
                    'ccxt_id': exchange_info['ccxt_id']
                }
            }), 404
        
        # Get USD price
        usd_price = None
        quote_used = pair.split('/')[1]
        
        if quote_used in ['USDT', 'USDC', 'USD', 'BUSD']:
            # Already in USD equivalent
            usd_price = ticker.get('last', 0) or ticker.get('close', 0)
        else:
            # Need to convert (future enhancement)
            usd_price = ticker.get('last', 0) or ticker.get('close', 0)
        
        # Build response
        response = {
            'success': True,
            'token': token,
            'exchange': {
                'id': str(exchange_info['_id']),
                'name': exchange_info['nome'],
                'ccxt_id': exchange_info['ccxt_id'],
                'icon': exchange_info.get('icon')
            },
            'pair': pair,
            'quote_currency': quote_used,
            'ticker': {
                'symbol': ticker.get('symbol'),
                'last': ticker.get('last'),
                'bid': ticker.get('bid'),
                'ask': ticker.get('ask'),
                'high': ticker.get('high'),
                'low': ticker.get('low'),
                'volume': ticker.get('baseVolume'),
                'quoteVolume': ticker.get('quoteVolume'),
                'change': ticker.get('change'),
                'percentage': ticker.get('percentage'),
                'timestamp': ticker.get('timestamp'),
                'datetime': ticker.get('datetime')
            },
            'usd_price': float(usd_price) if usd_price else None,
            'from_cache': False
        }
        
        # Store in cache (TTL: 60 seconds)
        token_cache.set(cache_key, response)
        
        logger.info(f"✅ Token search successful: {token} = ${usd_price:.8f} (cached for 60s)")
        
        return jsonify(response), 200
        
    except ccxt.AuthenticationError as e:
        logger.error(f"Authentication error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Authentication failed with exchange',
            'details': str(e)
        }), 401
        
    except ccxt.ExchangeError as e:
        logger.error(f"Exchange error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Exchange error',
            'details': str(e)
        }), 500
        
    except Exception as e:
        logger.error(f"Error searching token: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'details': str(e)
        }), 500


@app.route('/api/v1/tokens/available', methods=['GET'])
def get_available_tokens():
    """
    Lista tokens disponíveis em uma exchange (do cache MongoDB - super rápido!)
    📝 UNIVERSAL: Serve para TODOS os usuários (não precisa de credenciais)
    
    Query Params:
        exchange_id (required): MongoDB ObjectId da exchange
        quote (optional): Filtrar por moeda de cotação (USDT, USD, USDC, BUSD, BRL)
    
    Returns:
        200: Lista de tokens do cache MongoDB
        400: Parâmetros inválidos
        404: Exchange não encontrada
        503: Cache não disponível (precisa rodar update job)
    
    Response Example:
        {
            "success": true,
            "exchange": {
                "id": "...",
                "name": "Binance",
                "ccxt_id": "binance"
            },
            "quote_filter": "USDT",
            "total_tokens": 150,
            "tokens": [
                {
                    "symbol": "BTC",
                    "pair": "BTC/USDT",
                    "quote": "USDT",
                    "min_amount": 0.00001,
                    "max_amount": 9000.0,
                    "min_cost": 10.0
                }
            ],
            "updated_at": "2024-12-17T03:00:00.000Z",
            "cache_age_hours": 14.5,
            "from_cache": true
        }
    """
    try:
        # Get parameters
        exchange_id = request.args.get('exchange_id')
        quote_filter = request.args.get('quote', '').upper()
        
        # Validate required parameters
        if not exchange_id:
            return jsonify({
                'success': False,
                'error': 'exchange_id is required as query parameter'
            }), 400
        
        # Validate quote filter if provided
        valid_quotes = ['USDT', 'USD', 'USDC', 'BUSD', 'BRL', '']
        if quote_filter not in valid_quotes:
            return jsonify({
                'success': False,
                'error': f'Invalid quote filter. Must be one of: {", ".join([q for q in valid_quotes if q])}'
            }), 400
        
        # Get cached tokens from MongoDB (UNIVERSAL - no user_id needed)
        tokens_exchanges_collection = db.tokens_exchanges
        cached_data = tokens_exchanges_collection.find_one({
            'exchange_id': exchange_id
        })
        
        if not cached_data:
            # No cache available - need to run update job
            return jsonify({
                'success': False,
                'error': 'Token list not available in cache',
                'message': 'Please run the token update job first or wait for the nightly update',
                'hint': 'Run: python scripts/update_exchange_tokens.py'
            }), 503
        
        # Check if update was successful
        if cached_data.get('update_status') != 'success':
            return jsonify({
                'success': False,
                'error': f"Last update failed: {cached_data.get('error', 'Unknown error')}",
                'updated_at': cached_data.get('updated_at')
            }), 503
        
        # Get exchange info
        exchange_info = db.exchanges.find_one({'_id': ObjectId(exchange_id)})
        
        if not exchange_info:
            return jsonify({
                'success': False,
                'error': 'Exchange not found'
            }), 404
        
        # Filter tokens by quote if specified
        tokens_by_quote = cached_data.get('tokens_by_quote', {})
        
        if quote_filter:
            # Return only specified quote
            tokens_list = tokens_by_quote.get(quote_filter, [])
        else:
            # Return all quotes
            tokens_list = []
            for quote, tokens in tokens_by_quote.items():
                tokens_list.extend(tokens)
        
        # Calculate cache age
        updated_at = cached_data.get('updated_at')
        cache_age_hours = None
        if updated_at:
            cache_age = datetime.utcnow() - updated_at
            cache_age_hours = round(cache_age.total_seconds() / 3600, 1)
        
        # Build response
        response = {
            'success': True,
            'exchange': {
                'id': str(exchange_info['_id']),
                'name': exchange_info['nome'],
                'ccxt_id': exchange_info['ccxt_id'],
                'icon': exchange_info.get('icon')
            },
            'quote_filter': quote_filter or 'all',
            'total_tokens': len(tokens_list),
            'tokens': tokens_list,
            'updated_at': updated_at.isoformat() if updated_at else None,
            'cache_age_hours': cache_age_hours,
            'from_cache': True
        }
        
        logger.info(f"✅ Returned {len(tokens_list)} cached tokens for {exchange_info['nome']} (age: {cache_age_hours}h)")
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Error getting available tokens: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'details': str(e)
        }), 500


# ============================================
# POSITION ENDPOINTS
# ============================================

@app.route('/api/v1/positions', methods=['GET'])
def get_positions():
    """
    Lista todas as posições do usuário
    
    Query Params:
        user_id (required): ID do usuário
        exchange_id (optional): Filtrar por exchange
        token (optional): Filtrar por token
        is_active (optional): Filtrar por status (true/false)
    
    Returns:
        200: Lista de posições
        400: Parâmetros inválidos
        500: Erro interno
    
    Response Example:
        {
            "success": true,
            "positions": [
                {
                    "_id": "...",
                    "user_id": "user123",
                    "exchange_id": "...",
                    "exchange_name": "Binance",
                    "token": "BTC",
                    "amount": 0.5,
                    "entry_price": 45000.0,
                    "total_invested": 22500.0,
                    "is_active": true,
                    "purchases": [...],
                    "sales": [...],
                    "created_at": "...",
                    "updated_at": "..."
                }
            ]
        }
    """
    try:
        user_id = request.args.get('user_id')
        
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'user_id is required'
            }), 400
        
        # Optional filters
        filters = {}
        if 'exchange_id' in request.args:
            filters['exchange_id'] = request.args.get('exchange_id')
        if 'token' in request.args:
            filters['token'] = request.args.get('token')
        if 'is_active' in request.args:
            filters['is_active'] = request.args.get('is_active').lower() == 'true'
        
        position_service = get_position_service(db)
        positions = position_service.get_user_positions(user_id, filters=filters)
        
        return jsonify({
            'success': True,
            'positions': positions
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting positions: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'details': str(e)
        }), 500


@app.route('/api/v1/positions/<position_id>', methods=['GET'])
def get_position_detail(position_id):
    """
    Busca detalhes de uma posição específica
    
    Path Params:
        position_id: MongoDB ObjectId da posição
    
    Returns:
        200: Detalhes da posição
        404: Posição não encontrada
        500: Erro interno
    """
    try:
        from bson import ObjectId
        
        position_service = get_position_service(db)
        position = db.user_positions.find_one({'_id': ObjectId(position_id)})
        
        if not position:
            return jsonify({
                'success': False,
                'error': 'Position not found'
            }), 404
        
        # Convert ObjectId to string
        position['_id'] = str(position['_id'])
        position['exchange_id'] = str(position['exchange_id'])
        
        return jsonify({
            'success': True,
            'position': position
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting position detail: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'details': str(e)
        }), 500


@app.route('/api/v1/positions/sync', methods=['POST'])
def sync_positions():
    """
    Sincroniza posições a partir dos saldos atuais
    Cria posições para tokens que ainda não têm histórico de compra
    
    Request Body:
        {
            "user_id": "user123",
            "exchange_id": "...",  (optional)
            "token": "BTC"  (optional)
        }
    
    Returns:
        200: Posições sincronizadas
        400: Dados inválidos
        500: Erro interno
    """
    try:
        data = request.get_json()
        
        if not data or 'user_id' not in data:
            return jsonify({
                'success': False,
                'error': 'user_id is required'
            }), 400
        
        user_id = data['user_id']
        exchange_id = data.get('exchange_id')
        token = data.get('token')
        
        position_service = get_position_service(db)
        
        if exchange_id and token:
            # Sync specific position
            result = position_service.sync_from_balance(user_id, exchange_id, token)
            return jsonify({
                'success': True,
                'message': 'Position synced',
                'position': result
            }), 200
        else:
            # Sync all positions from balances
            balance_service = get_balance_service(db)
            balances = balance_service.fetch_all_balances(
                user_id=user_id,
                exchange_ids=[exchange_id] if exchange_id else None,
                include_changes=False
            )
            
            synced_count = 0
            for balance in balances:
                ex_id = balance['exchange_id']
                for asset in balance['balances']:
                    if asset['free'] > 0:
                        position_service.sync_from_balance(user_id, ex_id, asset['asset'])
                        synced_count += 1
            
            return jsonify({
                'success': True,
                'message': f'Synced {synced_count} positions'
            }), 200
        
    except Exception as e:
        logger.error(f"Error syncing positions: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'details': str(e)
        }), 500


@app.route('/api/v1/positions/<position_id>/history', methods=['GET'])
def get_position_history(position_id):
    """
    Busca histórico de compras e vendas de uma posição
    
    Path Params:
        position_id: MongoDB ObjectId da posição
    
    Returns:
        200: Histórico de transações
        404: Posição não encontrada
        500: Erro interno
    """
    try:
        from bson import ObjectId
        
        position = db.user_positions.find_one({'_id': ObjectId(position_id)})
        
        if not position:
            return jsonify({
                'success': False,
                'error': 'Position not found'
            }), 404
        
        return jsonify({
            'success': True,
            'history': {
                'purchases': position.get('purchases', []),
                'sales': position.get('sales', [])
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting position history: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'details': str(e)
        }), 500


# ============================================
# NOTIFICATION ENDPOINTS
# ============================================

@app.route('/api/v1/notifications', methods=['GET'])
def get_notifications():
    """
    Lista notificações do usuário
    
    Query Params:
        user_id (required): ID do usuário
        unread_only (optional): Apenas não lidas (true/false)
        type (optional): Filtrar por tipo
        limit (optional): Limite de resultados (default: 50)
    
    Returns:
        200: Lista de notificações
        400: Parâmetros inválidos
        500: Erro interno
    """
    try:
        user_id = request.args.get('user_id')
        
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'user_id is required'
            }), 400
        
        unread_only = request.args.get('unread_only', 'false').lower() == 'true'
        notification_type = request.args.get('type')
        limit = int(request.args.get('limit', 50))
        
        notification_service = get_notification_service(db)
        notifications = notification_service.get_user_notifications(
            user_id=user_id,
            unread_only=unread_only,
            notification_type=notification_type,
            limit=limit
        )
        
        return jsonify({
            'success': True,
            'notifications': notifications
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting notifications: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'details': str(e)
        }), 500


@app.route('/api/v1/notifications/<notification_id>/read', methods=['PUT'])
def mark_notification_read(notification_id):
    """
    Marca notificação como lida
    
    Path Params:
        notification_id: MongoDB ObjectId da notificação
    
    Returns:
        200: Notificação marcada como lida
        404: Notificação não encontrada
        500: Erro interno
    """
    try:
        notification_service = get_notification_service(db)
        success = notification_service.mark_as_read(notification_id)
        
        if not success:
            return jsonify({
                'success': False,
                'error': 'Notification not found'
            }), 404
        
        return jsonify({
            'success': True,
            'message': 'Notification marked as read'
        }), 200
        
    except Exception as e:
        logger.error(f"Error marking notification as read: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'details': str(e)
        }), 500


@app.route('/api/v1/notifications/read-all', methods=['PUT'])
def mark_all_notifications_read():
    """
    Marca todas as notificações do usuário como lidas
    
    Request Body:
        {
            "user_id": "user123"
        }
    
    Returns:
        200: Notificações marcadas
        400: Dados inválidos
        500: Erro interno
    """
    try:
        data = request.get_json()
        
        if not data or 'user_id' not in data:
            return jsonify({
                'success': False,
                'error': 'user_id is required'
            }), 400
        
        notification_service = get_notification_service(db)
        count = notification_service.mark_all_as_read(data['user_id'])
        
        return jsonify({
            'success': True,
            'message': f'{count} notifications marked as read'
        }), 200
        
    except Exception as e:
        logger.error(f"Error marking all notifications as read: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'details': str(e)
        }), 500


@app.route('/api/v1/notifications/<notification_id>', methods=['DELETE'])
def delete_notification(notification_id):
    """
    Deleta notificação
    
    Path Params:
        notification_id: MongoDB ObjectId da notificação
    
    Returns:
        200: Notificação deletada
        404: Notificação não encontrada
        500: Erro interno
    """
    try:
        notification_service = get_notification_service(db)
        success = notification_service.delete_notification(notification_id)
        
        if not success:
            return jsonify({
                'success': False,
                'error': 'Notification not found'
            }), 404
        
        return jsonify({
            'success': True,
            'message': 'Notification deleted'
        }), 200
        
    except Exception as e:
        logger.error(f"Error deleting notification: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'details': str(e)
        }), 500


# ============================================
# MANUAL ORDER EXECUTION ENDPOINTS (for testing/manual trades)
# ============================================

@app.route('/api/v1/orders/sell', methods=['POST'])
def execute_sell_order():
    """
    Executa ordem de venda manualmente
    
    Request Body:
        {
            "user_id": "user123",
            "exchange_id": "...",
            "token": "BTC",
            "amount": 0.5,
            "order_type": "market" | "limit",
            "price": 45000.0  (required for limit orders)
        }
    
    Returns:
        200: Ordem executada
        400: Dados inválidos
        500: Erro interno
    """
    try:
        data = request.get_json()
        
        required_fields = ['user_id', 'exchange_id', 'token', 'amount', 'order_type']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'{field} is required'
                }), 400
        
        # Get order execution service (use env var for dry_run)
        dry_run = os.getenv('STRATEGY_DRY_RUN', 'true').lower() == 'true'
        order_service = get_order_execution_service(db, dry_run=dry_run)
        
        if data['order_type'] == 'market':
            result = order_service.execute_market_sell(
                user_id=data['user_id'],
                exchange_id=data['exchange_id'],
                token=data['token'],
                amount=float(data['amount'])
            )
        elif data['order_type'] == 'limit':
            if 'price' not in data:
                return jsonify({
                    'success': False,
                    'error': 'price is required for limit orders'
                }), 400
            
            result = order_service.execute_limit_sell(
                user_id=data['user_id'],
                exchange_id=data['exchange_id'],
                token=data['token'],
                amount=float(data['amount']),
                price=float(data['price'])
            )
        else:
            return jsonify({
                'success': False,
                'error': 'order_type must be "market" or "limit"'
            }), 400
        
        # Update position if successful
        if result['success'] and not result.get('dry_run'):
            position_service = get_position_service(db)
            order = result['order']
            
            if order.get('filled'):
                position_service.record_sell(
                    user_id=data['user_id'],
                    exchange_id=data['exchange_id'],
                    token=data['token'],
                    amount=order['filled'],
                    price=order.get('average', order.get('price')),
                    total_received=order.get('cost'),
                    order_id=order['id']
                )
        
        return jsonify(result), 200 if result['success'] else 400
        
    except Exception as e:
        logger.error(f"Error executing sell order: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'details': str(e)
        }), 500


@app.route('/api/v1/orders/buy', methods=['POST'])
def execute_buy_order():
    """
    Executa ordem de compra manualmente
    
    Request Body:
        {
            "user_id": "user123",
            "exchange_id": "...",
            "token": "BTC",
            "amount": 0.5,
            "order_type": "market" | "limit",
            "price": 45000.0  (required for limit orders)
        }
    
    Returns:
        200: Ordem executada
        400: Dados inválidos
        500: Erro interno
    """
    try:
        data = request.get_json()
        
        required_fields = ['user_id', 'exchange_id', 'token', 'amount', 'order_type']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'{field} is required'
                }), 400
        
        # Get order execution service (use env var for dry_run)
        dry_run = os.getenv('STRATEGY_DRY_RUN', 'true').lower() == 'true'
        order_service = get_order_execution_service(db, dry_run=dry_run)
        
        if data['order_type'] == 'market':
            result = order_service.execute_market_buy(
                user_id=data['user_id'],
                exchange_id=data['exchange_id'],
                token=data['token'],
                amount=float(data['amount'])
            )
        elif data['order_type'] == 'limit':
            if 'price' not in data:
                return jsonify({
                    'success': False,
                    'error': 'price is required for limit orders'
                }), 400
            
            result = order_service.execute_limit_buy(
                user_id=data['user_id'],
                exchange_id=data['exchange_id'],
                token=data['token'],
                amount=float(data['amount']),
                price=float(data['price'])
            )
        else:
            return jsonify({
                'success': False,
                'error': 'order_type must be "market" or "limit"'
            }), 400
        
        # Update position if successful
        if result['success'] and not result.get('dry_run'):
            position_service = get_position_service(db)
            order = result['order']
            
            if order.get('filled'):
                position_service.record_buy(
                    user_id=data['user_id'],
                    exchange_id=data['exchange_id'],
                    token=data['token'],
                    amount=order['filled'],
                    price=order.get('average', order.get('price')),
                    total_cost=order.get('cost'),
                    order_id=order['id']
                )
        
        return jsonify(result), 200 if result['success'] else 400
        
    except Exception as e:
        logger.error(f"Error executing buy order: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'details': str(e)
        }), 500


@app.route('/api/v1/exchanges/<exchange_id>/markets', methods=['GET'])
def get_exchange_markets(exchange_id):
    """
    Lista todos os pares de trading disponíveis na exchange
    
    Query Parameters:
        user_id: string (required) - ID do usuário
        quote: string (optional) - Filtrar por moeda de cotação (ex: USDT, BTC)
        search: string (optional) - Buscar por token (ex: DOGE, ETH)
    
    Returns:
        200: Lista de mercados disponíveis
        400: Parâmetros inválidos
        500: Erro interno
    """
    try:
        user_id = request.args.get('user_id')
        quote_filter = request.args.get('quote', 'USDT')  # Default USDT
        search_term = request.args.get('search', '').upper()
        
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'user_id is required'
            }), 400
        
        # Get user exchange credentials
        user_exchange = db.user_exchanges.find_one({'user_id': user_id})
        
        if not user_exchange or 'exchanges' not in user_exchange:
            return jsonify({
                'success': False,
                'error': 'User has no linked exchanges'
            }), 404
        
        # Find specific exchange
        user_ex = None
        for ex in user_exchange['exchanges']:
            if str(ex['exchange_id']) == exchange_id:
                user_ex = ex
                break
        
        if not user_ex:
            return jsonify({
                'success': False,
                'error': 'Exchange not found for this user'
            }), 404
        
        # Get exchange info
        exchange_info = db.exchanges.find_one({'_id': ObjectId(exchange_id)})
        
        if not exchange_info:
            return jsonify({
                'success': False,
                'error': 'Exchange not found in database'
            }), 404
        
        ccxt_id = exchange_info.get('ccxt_id', '').lower()
        
        # Decrypt credentials
        encryption_service = get_encryption_service()
        decrypted = encryption_service.decrypt_credentials({
            'api_key': user_ex['api_key_encrypted'],
            'api_secret': user_ex['api_secret_encrypted'],
            'passphrase': user_ex.get('passphrase_encrypted')
        })
        
        # Fix PEM format for Coinbase (decrypt → fix \n → use)
        if ccxt_id == 'coinbase':
            if decrypted['api_secret'] and '\\n' in decrypted['api_secret']:
                decrypted['api_secret'] = decrypted['api_secret'].replace('\\n', '\n')
                logger.info("🔧 Fixed PEM format for Coinbase (replaced \\n with real newlines)")
        
        # Create CCXT exchange instance
        exchange_class = getattr(ccxt, ccxt_id)
        exchange = exchange_class({
            'apiKey': decrypted['api_key'],
            'secret': decrypted['api_secret'],
            'password': decrypted.get('passphrase'),
            'enableRateLimit': True
        })
        
        # Load markets
        markets = exchange.load_markets()
        
        # Filter markets
        filtered_markets = []
        for symbol, market in markets.items():
            # Filter by quote currency (USDT, BTC, etc)
            if quote_filter and not symbol.endswith(f'/{quote_filter}'):
                continue
            
            # Filter by search term
            if search_term and search_term not in symbol:
                continue
            
            # Only active markets
            if not market.get('active', True):
                continue
            
            filtered_markets.append({
                'symbol': symbol,
                'base': market['base'],
                'quote': market['quote'],
                'active': market.get('active', True),
                'limits': {
                    'amount': {
                        'min': market['limits']['amount'].get('min'),
                        'max': market['limits']['amount'].get('max')
                    },
                    'price': {
                        'min': market['limits']['price'].get('min'),
                        'max': market['limits']['price'].get('max')
                    },
                    'cost': {
                        'min': market['limits']['cost'].get('min'),
                        'max': market['limits']['cost'].get('max')
                    }
                }
            })
        
        # Sort by symbol
        filtered_markets.sort(key=lambda x: x['symbol'])
        
        logger.info(f"📊 Listed {len(filtered_markets)} markets from {exchange_info.get('nome')} (quote: {quote_filter})")
        
        return jsonify({
            'success': True,
            'count': len(filtered_markets),
            'exchange': exchange_info.get('nome'),
            'exchange_id': exchange_id,
            'quote_filter': quote_filter,
            'markets': filtered_markets
        }), 200
        
    except ccxt.AuthenticationError as e:
        logger.error(f"Authentication error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Authentication failed',
            'details': str(e)
        }), 401
    except ccxt.ExchangeError as e:
        logger.error(f"Exchange error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Exchange API error',
            'details': str(e)
        }), 400
    except Exception as e:
        logger.error(f"Error fetching markets: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'details': str(e)
        }), 500


@app.route('/api/v1/exchanges/<exchange_id>/balance/<token>', methods=['GET'])
def check_token_balance(exchange_id, token):
    """
    Verifica o saldo disponível de um token específico para venda
    
    Parameters:
        exchange_id: string (path) - ID da exchange no MongoDB
        token: string (path) - Símbolo do token (ex: BTC, ETH, DOGE)
    
    Query Parameters:
        user_id: string (required) - ID do usuário
    
    Returns:
        JSON com saldo disponível, bloqueado e total do token
        
    Example:
        GET /api/v1/exchanges/693481148b0a41e8b6acb07b/balance/DOGE?user_id=charles_test_user
    """
    try:
        user_id = request.args.get('user_id')
        
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'user_id é obrigatório'
            }), 400
        
        logger.info(f"Checking balance for token {token} on exchange {exchange_id} for user {user_id}")
        
        # Buscar informações da exchange no MongoDB
        try:
            exchange_obj_id = ObjectId(exchange_id)
        except:
            return jsonify({
                'success': False,
                'error': 'exchange_id inválido'
            }), 400
        
        exchange_info = db.exchanges.find_one({'_id': exchange_obj_id})
        
        if not exchange_info:
            return jsonify({
                'success': False,
                'error': 'Exchange não encontrada'
            }), 404
        
        # Buscar credenciais do usuário
        user_doc = db.user_exchanges.find_one({'user_id': user_id})
        
        if not user_doc or 'exchanges' not in user_doc:
            return jsonify({
                'success': False,
                'error': 'Usuário não possui exchanges vinculadas'
            }), 404
        
        # Encontrar a exchange específica
        exchange_link = None
        for ex in user_doc['exchanges']:
            if str(ex['exchange_id']) == exchange_id:
                exchange_link = ex
                break
        
        if not exchange_link:
            return jsonify({
                'success': False,
                'error': f'Exchange {exchange_info["nome"]} não está vinculada a este usuário'
            }), 404
        
        ccxt_id = exchange_info.get('ccxt_id', '').lower()
        
        # Descriptografar credenciais
        encryption_service = get_encryption_service()
        decrypted = encryption_service.decrypt_credentials({
            'api_key': exchange_link['api_key_encrypted'],
            'api_secret': exchange_link['api_secret_encrypted'],
            'password': exchange_link.get('passphrase_encrypted')
        })
        
        # Fix para Coinbase: substituir \n por quebra de linha real
        if ccxt_id == 'coinbase':
            if decrypted['api_secret'] and '\\n' in decrypted['api_secret']:
                decrypted['api_secret'] = decrypted['api_secret'].replace('\\n', '\n')
        
        # Criar instância da exchange
        exchange_class = getattr(ccxt, ccxt_id)
        exchange = exchange_class({
            'apiKey': decrypted['api_key'],
            'secret': decrypted['api_secret'],
            'password': decrypted.get('password'),
            'enableRateLimit': True,
        })
        
        # Buscar saldo completo da exchange
        balance = exchange.fetch_balance()
        
        # Normalizar o símbolo do token (uppercase)
        token = token.upper()
        
        # Verificar se o token existe no saldo
        if token not in balance:
            return jsonify({
                'success': True,
                'token': token,
                'exchange': exchange_info.get('nome'),
                'exchange_id': exchange_id,
                'available': 0.0,
                'used': 0.0,
                'total': 0.0,
                'can_sell': False,
                'message': f'Você não possui {token} nesta exchange'
            }), 200
        
        token_balance = balance[token]
        
        # Obter valores de saldo
        total = float(token_balance.get('total', 0))
        free = float(token_balance.get('free', 0))
        used = float(token_balance.get('used', 0))
        
        # Determinar se pode vender (tem saldo livre disponível)
        can_sell = free > 0
        
        return jsonify({
            'success': True,
            'token': token,
            'exchange': exchange_info.get('nome'),
            'exchange_id': exchange_id,
            'balance': {
                'available': free,      # Disponível para trading
                'used': used,           # Bloqueado em ordens
                'total': total          # Total (available + used)
            },
            'can_sell': can_sell,
            'message': f'Você possui {free} {token} disponível para venda' if can_sell else f'Sem saldo disponível de {token}'
        }), 200
        
    except ccxt.AuthenticationError as e:
        logger.error(f"Authentication error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Falha na autenticação',
            'details': str(e)
        }), 401
    except ccxt.ExchangeError as e:
        logger.error(f"Exchange error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Erro na API da exchange',
            'details': str(e)
        }), 400
    except Exception as e:
        logger.error(f"Error checking token balance: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': 'Erro interno do servidor',
            'details': str(e)
        }), 500


@app.route('/api/v1/orders/open', methods=['GET'])
@require_auth
@require_params('user_id', 'exchange_id')
def get_open_orders():
    """
    Consulta ordens abertas diretamente na exchange via CCXT
    
    ⚡ SEM CACHE: Dados sempre frescos e em tempo real
    🛡️  RATE LIMIT: Máximo 1 consulta por segundo por user+exchange
    
    Query Parameters:
        user_id: string (required) - ID do usuário
        exchange_id: string (required) - ID da exchange
        symbol: string (optional) - Par específico (ex: ETH/USDT)
    
    Returns:
        200: Lista de ordens abertas
        400: Parâmetros inválidos
        401: Token inválido ou ausente
        403: user_id do token não corresponde ao user_id do parâmetro
        429: Too many requests (rate limit)
        500: Erro interno
        
    Performance:
        - ~1-3s (depende da exchange, sempre busca dados frescos)
    """
    try:
        user_id = request.validated_params['user_id']
        exchange_id = request.validated_params['exchange_id']
        symbol = request.args.get('symbol')
        
        # Verify user_id from token matches user_id in params
        if request.user_id != user_id:
            return jsonify({
                'success': False,
                'error': 'Unauthorized: user_id mismatch'
            }), 403
        
        # 🛡️  RATE LIMIT: Evita chamadas excessivas (máx 1 por segundo por user+exchange)
        rate_limit_key = f"rate_limit:open_orders:{user_id}:{exchange_id}"
        orders_cache = get_orders_cache()
        
        is_valid, last_request_time = orders_cache.get(rate_limit_key)
        if is_valid and last_request_time:
            time_since_last = datetime.utcnow().timestamp() - last_request_time
            if time_since_last < 1.0:  # Menos de 1 segundo desde última requisição
                wait_time = 1.0 - time_since_last
                logger.warning(f"⚠️  Rate limit hit for {exchange_id} - wait {wait_time:.2f}s")
                return jsonify({
                    'success': False,
                    'error': 'Rate limit exceeded',
                    'message': f'Please wait {wait_time:.1f}s before next request',
                    'retry_after': wait_time
                }), 429
        
        # Marca timestamp da requisição atual
        orders_cache.set(rate_limit_key, datetime.utcnow().timestamp(), ttl_seconds=2)
        
        logger.info(f"🔄 Fetching fresh open orders from exchange API for {exchange_id}")
        
        # Get user exchange credentials
        user_exchange = db.user_exchanges.find_one({'user_id': user_id})
        
        if not user_exchange or 'exchanges' not in user_exchange:
            return jsonify({
                'success': False,
                'error': 'User has no linked exchanges'
            }), 404
        
        # Find specific exchange
        user_ex = None
        for ex in user_exchange['exchanges']:
            if str(ex['exchange_id']) == exchange_id:
                user_ex = ex
                break
        
        if not user_ex:
            return jsonify({
                'success': False,
                'error': 'Exchange not found for this user'
            }), 404
        
        # Get exchange info
        exchange_info = db.exchanges.find_one({'_id': ObjectId(exchange_id)})
        
        if not exchange_info:
            return jsonify({
                'success': False,
                'error': 'Exchange not found in database'
            }), 404
        
        ccxt_id = exchange_info.get('ccxt_id', '').lower()
        
        # Try to get CCXT instance from cache to avoid re-decryption
        ccxt_cache_key = f"ccxt_instance:{user_id}:{exchange_id}"
        ccxt_cache = get_ccxt_instances_cache()
        is_cached, exchange = ccxt_cache.get(ccxt_cache_key)
        
        if not is_cached or not exchange:
            # Decrypt credentials only if not cached
            encryption_service = get_encryption_service()
            decrypted = encryption_service.decrypt_credentials({
                'api_key': user_ex['api_key_encrypted'],
                'api_secret': user_ex['api_secret_encrypted'],
                'passphrase': user_ex.get('passphrase_encrypted')
            })
            
            # Fix PEM format for Coinbase (decrypt → fix \n → use)
            if ccxt_id == 'coinbase':
                if decrypted['api_secret'] and '\\n' in decrypted['api_secret']:
                    decrypted['api_secret'] = decrypted['api_secret'].replace('\\n', '\n')
                    logger.info("🔧 Fixed PEM format for Coinbase (replaced \\n with real newlines)")
            
            # Create CCXT exchange instance
            exchange_class = getattr(ccxt, ccxt_id)
            exchange = exchange_class({
                'apiKey': decrypted['api_key'],
                'secret': decrypted['api_secret'],
                'password': decrypted.get('passphrase'),
                'enableRateLimit': True,
                'options': {
                    'warnOnFetchOpenOrdersWithoutSymbol': False  # Suppress warning for Binance
                }
            })
            
            # Cache the CCXT instance for 5 minutes
            ccxt_cache.set(ccxt_cache_key, exchange)
            logger.info(f"🔒 Cached CCXT instance for {ccxt_id}")
        else:
            logger.info(f"⚡ Reusing cached CCXT instance for {ccxt_id}")
        
        # Always ensure Binance warning is suppressed (in case it was reset)
        if ccxt_id == 'binance':
            if not hasattr(exchange, 'options'):
                exchange.options = {}
            exchange.options['warnOnFetchOpenOrdersWithoutSymbol'] = False
            logger.debug(f"🔕 Binance warning suppressed: {exchange.options.get('warnOnFetchOpenOrdersWithoutSymbol')}")
        
        # Check if exchange supports fetching open orders
        if not exchange.has.get('fetchOpenOrders', False):
            logger.warning(f"⚠️  {exchange_info.get('nome')} does not support fetching open orders")
            return jsonify({
                'success': True,
                'count': 0,
                'exchange': exchange_info.get('nome'),
                'exchange_id': exchange_id,
                'orders': [],
                'from_cache': False,
                'not_supported': True,
                'message': 'Exchange does not support fetching open orders'
            }), 200
        
        # Fetch open orders with timeout protection
        logger.info(f"🔍 Fetching open orders from {exchange_info.get('nome')} (symbol: {symbol or 'all'})")
        try:
            if symbol:
                open_orders = exchange.fetch_open_orders(symbol)
            else:
                open_orders = exchange.fetch_open_orders()
        except ccxt.NotSupported as e:
            logger.warning(f"⚠️  {exchange_info.get('nome')} does not support fetch_open_orders: {str(e)}")
            return jsonify({
                'success': True,
                'count': 0,
                'exchange': exchange_info.get('nome'),
                'exchange_id': exchange_id,
                'orders': [],
                'from_cache': False,
                'not_supported': True,
                'message': f'Feature not supported: {str(e)}'
            }), 200
        except (ccxt.RequestTimeout, ccxt.NetworkError) as e:
            logger.error(f"⚠️  Network/Timeout error for {exchange_info.get('nome')}: {str(e)}")
            # Return empty orders instead of error (graceful degradation)
            return jsonify({
                'success': True,
                'count': 0,
                'exchange': exchange_info.get('nome'),
                'exchange_id': exchange_id,
                'orders': [],
                'from_cache': False,
                'network_error': True,
                'message': 'Network error, will retry later'
            }), 200
        
        logger.info(f"📋 Fetched {len(open_orders)} open orders from {exchange_info.get('nome')} for user {user_id}")
        
        response_data = {
            'success': True,
            'count': len(open_orders),
            'exchange': exchange_info.get('nome'),
            'exchange_id': exchange_id,
            'orders': open_orders,
            'from_cache': False,
            'cached_at': datetime.utcnow().isoformat()
        }
        
        return jsonify(response_data), 200
        
    except ccxt.AuthenticationError as e:
        logger.error(f"❌ Authentication error for {exchange_id}: {str(e)}")
        # Return empty orders with auth error flag (don't break the sync flow)
        return jsonify({
            'success': True,  # Still "success" to not break frontend flow
            'count': 0,
            'exchange_id': exchange_id,
            'orders': [],
            'from_cache': False,
            'auth_error': True,
            'message': 'Authentication failed - please check API credentials'
        }), 200
    except ccxt.ExchangeError as e:
        error_msg = str(e)
        
        # Special case: Binance warning treated as error
        if 'warnOnFetchOpenOrdersWithoutSymbol' in error_msg:
            logger.warning(f"⚠️  Binance rate limit warning (non-blocking): {error_msg[:100]}...")
            # Try to fetch anyway, this is just a warning
            try:
                if symbol:
                    open_orders = exchange.fetch_open_orders(symbol)
                else:
                    open_orders = exchange.fetch_open_orders()
                
                response_data = {
                    'success': True,
                    'count': len(open_orders),
                    'exchange': exchange_info.get('nome'),
                    'exchange_id': exchange_id,
                    'orders': open_orders,
                    'from_cache': False,
                    'cached_at': datetime.utcnow().isoformat()
                }
                
                return jsonify(response_data), 200
            except:
                pass  # If retry fails, continue with graceful degradation below
        
        logger.error(f"❌ Exchange error for {exchange_id}: {error_msg}")
        # Return empty orders instead of error (graceful degradation)
        return jsonify({
            'success': True,
            'count': 0,
            'exchange_id': exchange_id,
            'orders': [],
            'from_cache': False,
            'exchange_error': True,
            'message': f'Exchange error: {error_msg}'
        }), 200
    except Exception as e:
        logger.error(f"❌ Unexpected error fetching open orders for {exchange_id}: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        # Return empty orders instead of 500 error (don't break frontend)
        return jsonify({
            'success': True,
            'count': 0,
            'exchange_id': exchange_id,
            'orders': [],
            'from_cache': False,
            'error': True,
            'message': 'Unexpected error - will retry later'
        }), 200


@app.route('/api/v1/orders/history', methods=['GET'])
def get_orders_history():
    """
    Consulta histórico de ordens (fechadas/canceladas) diretamente na exchange via CCXT
    
    Query Parameters:
        user_id: string (required) - ID do usuário
        exchange_id: string (required) - ID da exchange
        symbol: string (required) - Par específico (ex: BTC/USDT, DOGE/USDT)
        limit: int (optional, default: 100, max: 500) - Número de ordens
    
    Returns:
        200: Lista de ordens históricas
        400: Parâmetros inválidos
        500: Erro interno
    
    Example:
        GET /api/v1/orders/history?user_id=charles_test_user&exchange_id=693481148b0a41e8b6acb07b&symbol=DOGE/USDT&limit=50
    """
    try:
        user_id = request.args.get('user_id')
        exchange_id = request.args.get('exchange_id')
        symbol = request.args.get('symbol')
        limit = min(int(request.args.get('limit', 100)), 500)
        
        if not user_id or not exchange_id:
            return jsonify({
                'success': False,
                'error': 'user_id e exchange_id são obrigatórios'
            }), 400
        
        if not symbol:
            return jsonify({
                'success': False,
                'error': 'symbol é obrigatório (ex: BTC/USDT, DOGE/USDT). A MEXC exige um par específico para buscar histórico.'
            }), 400
        
        logger.info(f"Fetching order history from exchange {exchange_id} for user {user_id}")
        
        # Buscar informações da exchange
        try:
            exchange_obj_id = ObjectId(exchange_id)
        except:
            return jsonify({
                'success': False,
                'error': 'exchange_id inválido'
            }), 400
        
        exchange_info = db.exchanges.find_one({'_id': exchange_obj_id})
        
        if not exchange_info:
            return jsonify({
                'success': False,
                'error': 'Exchange não encontrada'
            }), 404
        
        # Buscar credenciais do usuário
        user_doc = db.user_exchanges.find_one({'user_id': user_id})
        
        if not user_doc or 'exchanges' not in user_doc:
            return jsonify({
                'success': False,
                'error': 'Usuário não possui exchanges vinculadas'
            }), 404
        
        # Encontrar a exchange específica
        exchange_link = None
        for ex in user_doc['exchanges']:
            if str(ex['exchange_id']) == exchange_id:
                exchange_link = ex
                break
        
        if not exchange_link:
            return jsonify({
                'success': False,
                'error': f'Exchange {exchange_info["nome"]} não está vinculada a este usuário'
            }), 404
        
        ccxt_id = exchange_info.get('ccxt_id', '').lower()
        
        # Descriptografar credenciais
        encryption_service = get_encryption_service()
        decrypted = encryption_service.decrypt_credentials({
            'api_key': exchange_link['api_key_encrypted'],
            'api_secret': exchange_link['api_secret_encrypted'],
            'password': exchange_link.get('passphrase_encrypted')
        })
        
        # Fix PEM format for Coinbase
        if ccxt_id == 'coinbase':
            if decrypted['api_secret'] and '\\n' in decrypted['api_secret']:
                decrypted['api_secret'] = decrypted['api_secret'].replace('\\n', '\n')
        
        # Criar instância CCXT
        exchange_class = getattr(ccxt, ccxt_id)
        exchange = exchange_class({
            'apiKey': decrypted['api_key'],
            'secret': decrypted['api_secret'],
            'password': decrypted.get('passphrase'),
            'enableRateLimit': True
        })
        
        # Buscar ordens fechadas
        if symbol:
            closed_orders = exchange.fetch_closed_orders(symbol, limit=limit)
        else:
            closed_orders = exchange.fetch_closed_orders(limit=limit)
        
        logger.info(f"📋 Fetched {len(closed_orders)} closed orders from {exchange_info.get('nome')}")
        
        response_data = {
            'success': True,
            'count': len(closed_orders),
            'exchange': exchange_info.get('nome'),
            'exchange_id': exchange_id,
            'symbol': symbol,
            'limit': limit,
            'orders': closed_orders
        }
        
        return jsonify(response_data), 200
        
    except ccxt.AuthenticationError as e:
        logger.error(f"Authentication error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Falha na autenticação',
            'details': str(e)
        }), 401
    except ccxt.ExchangeError as e:
        logger.error(f"Exchange error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Erro na API da exchange',
            'details': str(e)
        }), 400
    except Exception as e:
        logger.error(f"Error fetching orders history: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': 'Erro interno do servidor',
            'details': str(e)
        }), 500


# ============================================
# JOBS CONTROL ENDPOINTS
# ============================================

@app.route('/api/v1/jobs/status', methods=['GET'])
def get_jobs_status():
    """
    Retorna status detalhado de todos os jobs em execução
    
    Returns:
        200: Status dos jobs
        500: Erro interno
    
    Response Example:
        {
            "success": true,
            "jobs": {
                "balance_snapshot": {
                    "name": "Balance Snapshot",
                    "running": true,
                    "schedule": "Every 4 hours",
                    "next_run": "2024-12-10T16:00:00Z",
                    "last_run": "2024-12-10T12:00:00Z"
                },
                "strategy_worker": {
                    "name": "Strategy Worker",
                    "running": true,
                    "check_interval_minutes": 5,
                    "dry_run_mode": true,
                    "last_check": "2024-12-10T14:35:00Z"
                }
            }
        }
    """
    try:
        jobs_status = {
            'balance_snapshot': {
                'name': 'Balance Snapshot',
                'description': 'Captures balance snapshots for portfolio history',
                'running': scheduler.running if scheduler else False,
                'schedule': 'Every 4 hours (00:00, 04:00, 08:00, 12:00, 16:00, 20:00 UTC)',
                'next_run': None,
                'last_run': None
            },
            'strategy_worker': {
                'name': 'Strategy Worker',
                'description': 'Monitors strategies and executes automated trades',
                'running': strategy_worker.is_running if strategy_worker else False,
                'check_interval_minutes': int(os.getenv('STRATEGY_CHECK_INTERVAL', '5')),
                'dry_run_mode': os.getenv('STRATEGY_DRY_RUN', 'true').lower() == 'true',
                'schedule': f"Every {os.getenv('STRATEGY_CHECK_INTERVAL', '5')} minutes"
            }
        }
        
        # Get scheduler job info
        if scheduler and scheduler.running:
            jobs = scheduler.get_jobs()
            if jobs:
                job = jobs[0]
                if job.next_run_time:
                    jobs_status['balance_snapshot']['next_run'] = job.next_run_time.isoformat()
        
        return jsonify({
            'success': True,
            'jobs': jobs_status,
            'summary': {
                'total_jobs': 2,
                'running_jobs': sum(1 for j in jobs_status.values() if j['running']),
                'stopped_jobs': sum(1 for j in jobs_status.values() if not j['running'])
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting jobs status: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'details': str(e)
        }), 500


@app.route('/api/v1/jobs/control', methods=['POST'])
def control_jobs():
    """
    Controla (start/stop/restart) jobs individuais
    
    Request Body:
        {
            "job": "strategy_worker" | "balance_snapshot",
            "action": "start" | "stop" | "restart"
        }
    
    Returns:
        200: Ação executada com sucesso
        400: Parâmetros inválidos
        500: Erro interno
    
    Response Example:
        {
            "success": true,
            "message": "Strategy Worker stopped successfully",
            "job": "strategy_worker",
            "action": "stop",
            "new_status": "stopped"
        }
    """
    try:
        data = request.get_json()
        
        if not data or 'job' not in data or 'action' not in data:
            return jsonify({
                'success': False,
                'error': 'job and action are required',
                'valid_jobs': ['strategy_worker', 'balance_snapshot'],
                'valid_actions': ['start', 'stop', 'restart']
            }), 400
        
        job_name = data['job']
        action = data['action']
        
        if job_name not in ['strategy_worker', 'balance_snapshot']:
            return jsonify({
                'success': False,
                'error': 'Invalid job name',
                'valid_jobs': ['strategy_worker', 'balance_snapshot']
            }), 400
        
        if action not in ['start', 'stop', 'restart']:
            return jsonify({
                'success': False,
                'error': 'Invalid action',
                'valid_actions': ['start', 'stop', 'restart']
            }), 400
        
        # Execute action
        if job_name == 'strategy_worker':
            if action == 'start':
                if strategy_worker and not strategy_worker.is_running:
                    strategy_worker.start()
                    message = "Strategy Worker started successfully"
                    new_status = "running"
                else:
                    message = "Strategy Worker is already running"
                    new_status = "running"
            
            elif action == 'stop':
                if strategy_worker and strategy_worker.is_running:
                    strategy_worker.stop()
                    message = "Strategy Worker stopped successfully"
                    new_status = "stopped"
                else:
                    message = "Strategy Worker is already stopped"
                    new_status = "stopped"
            
            elif action == 'restart':
                if strategy_worker:
                    if strategy_worker.is_running:
                        strategy_worker.stop()
                    strategy_worker.start()
                    message = "Strategy Worker restarted successfully"
                    new_status = "running"
                else:
                    return jsonify({
                        'success': False,
                        'error': 'Strategy Worker not initialized'
                    }), 500
        
        elif job_name == 'balance_snapshot':
            if action == 'start':
                if scheduler and not scheduler.running:
                    scheduler.start()
                    message = "Balance Snapshot Scheduler started successfully"
                    new_status = "running"
                else:
                    message = "Balance Snapshot Scheduler is already running"
                    new_status = "running"
            
            elif action == 'stop':
                if scheduler and scheduler.running:
                    scheduler.pause()
                    message = "Balance Snapshot Scheduler stopped successfully"
                    new_status = "stopped"
                else:
                    message = "Balance Snapshot Scheduler is already stopped"
                    new_status = "stopped"
            
            elif action == 'restart':
                if scheduler:
                    if scheduler.running:
                        scheduler.pause()
                    scheduler.resume()
                    message = "Balance Snapshot Scheduler restarted successfully"
                    new_status = "running"
                else:
                    return jsonify({
                        'success': False,
                        'error': 'Scheduler not initialized'
                    }), 500
        
        logger.info(f"Job control: {job_name} - {action} - {message}")
        
        return jsonify({
            'success': True,
            'message': message,
            'job': job_name,
            'action': action,
            'new_status': new_status
        }), 200
        
    except Exception as e:
        logger.error(f"Error controlling job: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'details': str(e)
        }), 500


@app.route('/api/v1/jobs/trigger/<job_name>', methods=['POST'])
def trigger_job_manually(job_name):
    """
    Dispara execução manual de um job (fora do schedule)
    
    Path Params:
        job_name: Nome do job (strategy_worker | balance_snapshot)
    
    Returns:
        200: Job disparado com sucesso
        400: Job inválido
        500: Erro interno
    
    Response Example:
        {
            "success": true,
            "message": "Balance Snapshot triggered manually",
            "job": "balance_snapshot"
        }
    """
    try:
        if job_name not in ['strategy_worker', 'balance_snapshot']:
            return jsonify({
                'success': False,
                'error': 'Invalid job name',
                'valid_jobs': ['strategy_worker', 'balance_snapshot']
            }), 400
        
        if job_name == 'balance_snapshot':
            logger.info("🔧 Manual trigger: Balance Snapshot")
            run_scheduled_snapshot()
            message = "Balance Snapshot triggered successfully"
        
        elif job_name == 'strategy_worker':
            if strategy_worker and strategy_worker.is_running:
                logger.info("🔧 Manual trigger: Strategy Worker")
                strategy_worker._check_all_strategies()
                message = "Strategy Worker check triggered successfully"
            else:
                return jsonify({
                    'success': False,
                    'error': 'Strategy Worker is not running'
                }), 400
        
        return jsonify({
            'success': True,
            'message': message,
            'job': job_name,
            'triggered_at': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error triggering job: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'details': str(e)
        }), 500


# ============================================



if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_ENV') == 'development'
    
    logger.info(f"Iniciando servidor na porta {port}...")
    app.run(host='0.0.0.0', port=port, debug=debug)

