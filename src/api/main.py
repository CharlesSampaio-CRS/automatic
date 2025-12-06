"""
API Principal - Sistema de Trading Multi-Exchange
"""

import os
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

# Carrega variáveis de ambiente
load_dotenv()

# Inicializa Flask
app = Flask(__name__)

# Configuração MongoDB
MONGO_URI = os.getenv('MONGODB_URI')
MONGO_DATABASE = os.getenv('MONGODB_DATABASE', 'MultExchange')

def get_database():
    """Retorna conexão com MongoDB"""
    client = MongoClient(MONGO_URI)
    return client[MONGO_DATABASE]

# Teste de conexão
try:
    db = get_database()
    # Testa conexão
    db.command('ping')
    print("✅ MongoDB conectado com sucesso!")
except Exception as e:
    print(f"❌ Erro ao conectar MongoDB: {e}")
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
        
        print(f"🔍 Validating credentials for {exchange['nome']}...")
        
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
        
        print(f"✅ Credentials validated successfully")
        
        # ============================================
        # CRIPTOGRAFIA DAS CREDENCIAIS
        # ============================================
        
        print(f"🔐 Encrypting credentials...")
        
        encryption_service = get_encryption_service()
        encrypted_credentials = encryption_service.encrypt_credentials(
            api_key=api_key,
            api_secret=api_secret,
            passphrase=passphrase
        )
        
        print(f"✅ Credentials encrypted")
        
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
        print(f"❌ Error linking exchange: {str(e)}")
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
        print(f"❌ Error fetching linked exchanges: {str(e)}")
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
        print(f"❌ Error unlinking exchange: {str(e)}")
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
        print(f"🔄 Fetching balances for user {user_id} (cache: {use_cache}, include_brl: {include_brl})...")
        result = balance_service.fetch_all_balances(user_id, use_cache=use_cache, include_brl=include_brl)
        
        num_exchanges = len(result.get('exchanges', []))
        num_tokens = len(result.get('tokens', {}))
        from_cache = result.get('meta', {}).get('from_cache', False)
        print(f"✅ Balances fetched: {num_exchanges} exchanges, {num_tokens} tokens, from_cache: {from_cache}")
        
        return jsonify(result), 200
        
    except Exception as e:
        print(f"❌ Error fetching balances: {str(e)}")
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
        
        print(f"🗑️  {message}")
        
        return jsonify({
            'success': True,
            'message': message
        }), 200
        
    except Exception as e:
        print(f"❌ Error clearing cache: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'details': str(e)
        }), 500

# ======================
# BALANCE HISTORY
# ======================

@app.route('/api/v1/balances/history', methods=['GET'])
def get_balance_history():
    """
    Get balance history for a user
    
    Query Parameters:
        - user_id (required): User ID
        - limit (optional): Max records to return (default 100)
        - skip (optional): Records to skip for pagination (default 0)
    
    Returns:
        200: List of balance snapshots
        400: Missing user_id
        500: Server error
    """
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'user_id is required'
            }), 400
        
        limit = int(request.args.get('limit', 100))
        skip = int(request.args.get('skip', 0))
        
        # Get history
        history_service = get_balance_history_service(db)
        snapshots = history_service.get_history(user_id, limit=limit, skip=skip)
        
        return jsonify({
            'success': True,
            'user_id': user_id,
            'count': len(snapshots),
            'limit': limit,
            'skip': skip,
            'snapshots': snapshots
        }), 200
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': 'Invalid limit or skip parameter'
        }), 400
    except Exception as e:
        print(f"❌ Error getting balance history: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'details': str(e)
        }), 500


@app.route('/api/v1/balances/history/latest', methods=['GET'])
def get_latest_snapshot():
    """
    Get the latest balance snapshot for a user
    
    Query Parameters:
        - user_id (required): User ID
    
    Returns:
        200: Latest snapshot
        400: Missing user_id
        404: No snapshots found
        500: Server error
    """
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'user_id is required'
            }), 400
        
        history_service = get_balance_history_service(db)
        snapshot = history_service.get_latest_snapshot(user_id)
        
        if not snapshot:
            return jsonify({
                'success': False,
                'error': 'No snapshots found for this user'
            }), 404
        
        return jsonify({
            'success': True,
            'snapshot': snapshot
        }), 200
        
    except Exception as e:
        print(f"❌ Error getting latest snapshot: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'details': str(e)
        }), 500


@app.route('/api/v1/balances/history/token/<token>', methods=['GET'])
def get_token_history(token):
    """
    Get historical data for a specific token
    
    Path Parameters:
        - token: Token symbol (e.g., BTC, ETH)
    
    Query Parameters:
        - user_id (required): User ID
        - limit (optional): Max records (default 100)
    
    Returns:
        200: Token history
        400: Missing user_id
        500: Server error
    """
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'user_id is required'
            }), 400
        
        limit = int(request.args.get('limit', 100))
        
        history_service = get_balance_history_service(db)
        history = history_service.get_token_history(user_id, token.upper(), limit=limit)
        
        return jsonify({
            'success': True,
            'user_id': user_id,
            'token': token.upper(),
            'count': len(history),
            'history': history
        }), 200
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': 'Invalid limit parameter'
        }), 400
    except Exception as e:
        print(f"❌ Error getting token history: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'details': str(e)
        }), 500


@app.route('/api/v1/balances/history/evolution', methods=['GET'])
def get_portfolio_evolution():
    """
    Get portfolio value evolution over time
    
    Query Parameters:
        - user_id (required): User ID
        - days (optional): Days to look back (default 30)
    
    Returns:
        200: Time series data with summary stats
        400: Missing user_id
        500: Server error
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
            'evolution': evolution
        }), 200
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': 'Invalid days parameter'
        }), 400
    except Exception as e:
        print(f"❌ Error getting portfolio evolution: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'details': str(e)
        }), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_ENV') == 'development'
    
    print(f"🚀 Iniciando servidor na porta {port}...")
    app.run(host='0.0.0.0', port=port, debug=debug)
