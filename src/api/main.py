"""
API Principal - Sistema de Trading Multi-Exchange
"""

import os
import ccxt
from flask import Flask, jsonify, request
from dotenv import load_dotenv
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime

# Import local modules
from src.security.encryption import get_encryption_service
from src.validators.exchange_validator import ExchangeValidator
from src.services.balance_service import get_balance_service
from src.services.balance_history_service import get_balance_history_service
from src.services.strategy_service import get_strategy_service
from src.services.position_service import get_position_service
from src.services.order_execution_service import get_order_execution_service
from src.services.notification_service import get_notification_service
from src.services.strategy_worker import get_strategy_worker
from src.utils.formatting import format_price, format_usd, format_percent
from src.utils.logger import get_logger
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


# Initialize BackgroundScheduler
scheduler = BackgroundScheduler(timezone='UTC')

# Add job: execute every 4 hours at minute 0
scheduler.add_job(
    func=run_scheduled_snapshot,
    trigger=CronTrigger(minute=0, hour='*/4'),
    id='balance_snapshot_job',
    name='Balance Snapshot Every 4 Hours',
    replace_existing=True,
    max_instances=1
)

# Start scheduler
scheduler.start()
logger.info("✅ Scheduler started - Balance snapshots every 4 hours (00:00, 04:00, 08:00, 12:00, 16:00, 20:00 UTC)")

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
            'automated_snapshots': 'Every 4 hours (00:00, 04:00, 08:00, 12:00, 16:00, 20:00 UTC)',
            'automated_trading': f"Strategy Worker checking every {os.getenv('STRATEGY_CHECK_INTERVAL', '5')} minutes",
            'dry_run_mode': os.getenv('STRATEGY_DRY_RUN', 'true')
        }
    }, 200


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
# ENDPOINTS DE EXCHANGES
# ============================================

@app.route('/api/v1/exchanges/available', methods=['GET'])
def get_available_exchanges():
    """
    Lista exchanges disponíveis para vinculação (NOVA ESTRUTURA COM ARRAY)
    Exclui as exchanges já vinculadas pelo usuário
    
    Query Params:
        user_id (required): ID do usuário para filtrar exchanges já vinculadas
    
    Returns:
        200: Lista de exchanges disponíveis (não vinculadas)
        400: user_id não fornecido
        500: Erro ao buscar exchanges
    """
    try:
        # user_id é obrigatório
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'user_id is required as query parameter'
            }), 400
        
        # Busca exchanges ativas no banco
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
        
        # Buscar documento do usuário e extrair exchange_ids vinculadas ativas
        user_doc = db.user_exchanges.find_one({'user_id': user_id})
        
        linked_exchange_ids = []
        if user_doc and 'exchanges' in user_doc:
            linked_exchange_ids = [
                ex['exchange_id']
                for ex in user_doc['exchanges']
                if ex.get('is_active', True)
            ]
        
        # Filtrar exchanges que NÃO estão vinculadas
        exchanges = [
            ex for ex in exchanges 
            if ObjectId(ex['_id']) not in linked_exchange_ids
        ]
        
        # Converte ObjectId para string
        for exchange in exchanges:
            exchange['_id'] = str(exchange['_id'])
        
        return jsonify({
            'success': True,
            'total': len(exchanges),
            'exchanges': exchanges
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error fetching exchanges: {str(e)}'
        }), 500

@app.route('/api/v1/exchanges/link', methods=['POST'])
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
        401: Credenciais inválidas ou sem permissão
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
        
        # Campos obrigatórios
        required_fields = ['user_id', 'exchange_id', 'api_key', 'api_secret']
        missing_fields = [field for field in required_fields if not data.get(field)]
        
        if missing_fields:
            return jsonify({
                'success': False,
                'error': f'Missing required fields: {", ".join(missing_fields)}'
            }), 400
        
        user_id = data['user_id']
        exchange_id = data['exchange_id']
        api_key = data['api_key'].strip()
        api_secret = data['api_secret'].strip()
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
                                }
                            }
                        )
                        
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
def get_linked_exchanges():
    """
    Lista exchanges vinculadas por um usuário (NOVA ESTRUTURA COM ARRAY)
    
    Query Params:
        user_id (required): ID do usuário
    
    Returns:
        200: Lista de exchanges vinculadas (sem expor credenciais)
        400: user_id não fornecido
        500: Erro ao buscar exchanges
    """
    try:
        user_id = request.args.get('user_id')
        
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'user_id is required as query parameter'
            }), 400
        
        # Buscar documento do usuário com array de exchanges
        user_doc = db.user_exchanges.find_one({'user_id': user_id})
        
        if not user_doc or 'exchanges' not in user_doc or not user_doc['exchanges']:
            return jsonify({
                'success': True,
                'total': 0,
                'exchanges': []
            }), 200
        
        # Buscar informações das exchanges ativas
        linked_exchanges = []
        for ex_data in user_doc['exchanges']:
            # Filtra apenas exchanges ativas
            if not ex_data.get('is_active', True):
                continue
                
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
                linked_exchanges.append({
                    'exchange_id': str(exchange['_id']),
                    'name': exchange['nome'],
                    'icon': exchange['icon'],
                    'url': exchange['url'],
                    'ccxt_id': exchange['ccxt_id'],
                    'country': exchange['pais_de_origem'],
                    'linked_at': ex_data['created_at'].isoformat(),
                    'updated_at': ex_data['updated_at'].isoformat()
                })
        
        return jsonify({
            'success': True,
            'total': len(linked_exchanges),
            'exchanges': linked_exchanges
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching linked exchanges: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'details': str(e)
        }), 500

@app.route('/api/v1/exchanges/unlink', methods=['DELETE'])
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
        
        user_id = data.get('user_id')
        exchange_id = data.get('exchange_id')
        
        if not user_id or not exchange_id:
            return jsonify({
                'success': False,
                'error': 'user_id and exchange_id are required'
            }), 400
        
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

# ============================================
# ENDPOINTS DE BALANCES
# ============================================

@app.route('/api/v1/balances', methods=['GET'])
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
        500: Erro ao buscar balances
    """
    try:
        user_id = request.args.get('user_id')
        
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'user_id is required as query parameter'
            }), 400
        
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
@app.route('/api/v1/balances/clear-cache', methods=['POST'])
def clear_balance_cache():
    """
    Limpa o cache de balances
    
    Request Body (optional):
        {
            "user_id": "string"  // If provided, clears only this user's cache
        }
    
    Returns:
        200: Cache cleared
        500: Error clearing cache
    """
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id')
        
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
    """
    try:
        symbol = symbol.upper()
        user_id = request.args.get('user_id')
        quote = request.args.get('quote', 'USDT').upper()
        
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
        
        # Inicializar exchange
        exchange_class = getattr(ccxt, ccxt_id)
        exchange = exchange_class({'enableRateLimit': True})
        
        # Carregar mercados
        exchange.load_markets()
        
        # Tentar diferentes pares
        pair = None
        for q in [quote, 'USDT', 'USD', 'BTC']:
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
        
        # 1. Buscar ticker (preço atual, volume, high/low)
        ticker = exchange.fetch_ticker(pair)
        
        # 2. Buscar OHLCV para calcular variações
        def calculate_price_change(timeframe, limit=2):
            try:
                ohlcv = exchange.fetch_ohlcv(pair, timeframe, limit=limit)
                if len(ohlcv) >= 2:
                    old_price = ohlcv[0][4]  # Close do período anterior
                    current_price = ohlcv[-1][4]  # Close atual
                    change = current_price - old_price
                    change_percent = (change / old_price * 100) if old_price > 0 else 0
                    return {
                        'price_change': format_price(change),
                        'price_change_percent': format_percent(change_percent)
                    }
            except:
                pass
            return None
        
        ohlcv_1h = calculate_price_change('1h')
        ohlcv_4h = calculate_price_change('4h')
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
        
        # 5. Buscar dados do balanço do usuário (se user_id fornecido)
        user_balance = None
        if user_id:
            user_doc = db.users.find_one({'user_id': user_id})
            if user_doc and 'linked_exchanges' in user_doc:
                for linked_ex in user_doc['linked_exchanges']:
                    if str(linked_ex.get('exchange_id')) == exchange_id:
                        # Buscar último balanço
                        from src.services.balance_service import BalanceService
                        balance_service = BalanceService()
                        
                        try:
                            balances = balance_service.get_balances(user_id, force_refresh=False)
                            for ex_balance in balances.get('exchanges', []):
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
                                            'last_updated': balances.get('timestamp')
                                        }
                                    break
                        except Exception as e:
                            logger.warning(f"Could not fetch user balance: {e}")
        
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

@app.route('/api/v1/strategies', methods=['POST'])
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
        
        # Campos obrigatórios básicos
        required_fields = ['user_id', 'exchange_id', 'token']
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            return jsonify({
                'success': False,
                'error': f'Missing required fields: {", ".join(missing_fields)}'
            }), 400
        
        strategy_service = get_strategy_service(db)
        
        # Determinar modo de criação
        if 'template' in data:
            # Template Mode (RECOMENDADO)
            result = strategy_service.create_strategy(
                user_id=data['user_id'],
                exchange_id=data['exchange_id'],
                token=data['token'],
                template=data['template'],
                is_active=data.get('is_active', True)
            )
        elif 'rules' in data:
            # Custom Mode
            result = strategy_service.create_strategy(
                user_id=data['user_id'],
                exchange_id=data['exchange_id'],
                token=data['token'],
                rules=data['rules'],
                is_active=data.get('is_active', True)
            )
        elif 'take_profit_percent' in data:
            # Legacy Mode (DEPRECATED)
            result = strategy_service.create_strategy(
                user_id=data['user_id'],
                exchange_id=data['exchange_id'],
                token=data['token'],
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
def delete_strategy(strategy_id):
    """
    Deleta uma estratégia
    
    Path Params:
        strategy_id: MongoDB ObjectId da estratégia
    
    Returns:
        200: Estratégia deletada
        404: Estratégia não encontrada
        500: Erro interno
    """
    try:
        strategy_service = get_strategy_service(db)
        result = strategy_service.delete_strategy(strategy_id)
        
        if result['success']:
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
    
    Returns:
        200: Estratégia encontrada
        404: Estratégia não encontrada
        500: Erro interno
    """
    try:
        strategy_service = get_strategy_service(db)
        strategy = strategy_service.get_strategy(strategy_id)
        
        if strategy:
            return jsonify({
                'success': True,
                'strategy': strategy
            }), 200
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
def get_user_strategies():
    """
    Lista todas as estratégias de um usuário com filtros opcionais
    
    Query Params:
        user_id (required): ID do usuário
        exchange_id (optional): Filtrar por exchange
        token (optional): Filtrar por token
        is_active (optional): Filtrar por status (true/false)
    
    Returns:
        200: Lista de estratégias
        400: user_id não fornecido
        500: Erro interno
    
    Exemplo:
        GET /api/v1/strategies?user_id=charles_test_user
        GET /api/v1/strategies?user_id=charles_test_user&exchange_id=693481148b0a41e8b6acb07b
        GET /api/v1/strategies?user_id=charles_test_user&token=BTC&is_active=true
    """
    try:
        user_id = request.args.get('user_id')
        
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'user_id is required as query parameter'
            }), 400
        
        exchange_id = request.args.get('exchange_id')
        token = request.args.get('token')
        is_active_str = request.args.get('is_active')
        is_active = None if is_active_str is None else is_active_str.lower() == 'true'
        
        strategy_service = get_strategy_service(db)
        strategies = strategy_service.get_user_strategies(
            user_id=user_id,
            exchange_id=exchange_id,
            token=token,
            is_active=is_active
        )
        
        return jsonify({
            'success': True,
            'count': len(strategies),
            'strategies': strategies
        }), 200
        
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

# ============================================


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

