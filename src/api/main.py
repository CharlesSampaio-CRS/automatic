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
from src.utils.formatting import format_price, format_usd, format_percent
from src.utils.logger import get_logger
from src.config import MONGODB_URI, MONGODB_DATABASE, API_PORT

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

# Rota de health check
@app.route('/health', methods=['GET'])
def health_check():
    """Health check da API"""
    return {
        'status': 'ok',
        'message': 'API rodando',
        'database': 'connected' if db is not None else 'disconnected'
    }, 200

# Rota raiz
@app.route('/', methods=['GET'])
def index():
    """Rota raiz"""
    return {
        'message': 'Sistema de Trading Multi-Exchange',
        'version': '1.0.0',
        'endpoints': {
            'health': '/health',
            'exchanges_available': '/api/v1/exchanges/available?user_id=<user_id>',
            'exchanges_link': '/api/v1/exchanges/link',
            'exchanges_linked': '/api/v1/exchanges/linked?user_id=<user_id>',
            'exchanges_unlink': '/api/v1/exchanges/unlink',
            'balances': '/api/v1/balances?user_id=<user_id>&force_refresh=<true|false>',
            'balances_clear_cache': '/api/v1/balances/clear-cache'
        }
    }, 200

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
        
        # Get balance service
        balance_service = get_balance_service(db)
        
        # Fetch balances (parallelized internally)
        logger.debug(f"Fetching balances for user {user_id} (cache: {use_cache}, include_brl: {include_brl})...")
        result = balance_service.fetch_all_balances(user_id, use_cache=use_cache, include_brl=include_brl)
        
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

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_ENV') == 'development'
    
    logger.info(f"Iniciando servidor na porta {port}...")
    app.run(host='0.0.0.0', port=port, debug=debug)
