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
            'exchanges_unlink': '/api/v1/exchanges/unlink/<link_id>',
            'balances': '/api/v1/balances (em desenvolvimento)'
        }
    }, 200

# ============================================
# ENDPOINTS DE EXCHANGES
# ============================================

@app.route('/api/v1/exchanges/available', methods=['GET'])
def get_available_exchanges():
    """
    Lista exchanges disponíveis para vinculação (excluindo as já vinculadas)
    
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
        
        # Buscar exchanges já vinculadas pelo usuário
        linked_exchange_ids = [
            link['exchange_id'] 
            for link in db.user_exchanges.find(
                {'user_id': user_id, 'is_active': True},
                {'exchange_id': 1}
            )
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
        # SALVAR NO BANCO DE DADOS
        # ============================================
        
        # Verificar se usuário já tem essa exchange vinculada
        existing_link = db.user_exchanges.find_one({
            'user_id': user_id,
            'exchange_id': ObjectId(exchange_id)
        })
        
        if existing_link:
            # Atualizar credenciais existentes
            result = db.user_exchanges.update_one(
                {'_id': existing_link['_id']},
                {
                    '$set': {
                        'api_key_encrypted': encrypted_credentials['api_key'],
                        'api_secret_encrypted': encrypted_credentials['api_secret'],
                        'passphrase_encrypted': encrypted_credentials.get('passphrase'),
                        'updated_at': datetime.utcnow(),
                        'is_active': True
                    }
                }
            )
            
            return jsonify({
                'success': True,
                'message': f'{exchange["nome"]} credentials updated successfully',
                'link_id': str(existing_link['_id']),
                'exchange': {
                    'id': str(exchange['_id']),
                    'name': exchange['nome'],
                    'icon': exchange['icon']
                }
            }), 200
        else:
            # Criar novo vínculo
            new_link = {
                'user_id': user_id,
                'exchange_id': ObjectId(exchange_id),
                'api_key_encrypted': encrypted_credentials['api_key'],
                'api_secret_encrypted': encrypted_credentials['api_secret'],
                'passphrase_encrypted': encrypted_credentials.get('passphrase'),
                'is_active': True,
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }
            
            result = db.user_exchanges.insert_one(new_link)
            
            return jsonify({
                'success': True,
                'message': f'{exchange["nome"]} linked successfully',
                'link_id': str(result.inserted_id),
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
    Lista exchanges vinculadas por um usuário
    
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
        
        # Buscar exchanges vinculadas ativas
        user_links = list(db.user_exchanges.find(
            {'user_id': user_id, 'is_active': True},
            {
                '_id': 1,
                'exchange_id': 1,
                'created_at': 1,
                'updated_at': 1
            }
        ).sort('created_at', -1))
        
        if not user_links:
            return jsonify({
                'success': True,
                'total': 0,
                'exchanges': []
            }), 200
        
        # Buscar informações das exchanges
        linked_exchanges = []
        for link in user_links:
            exchange = db.exchanges.find_one(
                {'_id': link['exchange_id']},
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
                    'link_id': str(link['_id']),
                    'exchange_id': str(exchange['_id']),
                    'name': exchange['nome'],
                    'icon': exchange['icon'],
                    'url': exchange['url'],
                    'ccxt_id': exchange['ccxt_id'],
                    'country': exchange['pais_de_origem'],
                    'linked_at': link['created_at'].isoformat(),
                    'updated_at': link['updated_at'].isoformat()
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

@app.route('/api/v1/exchanges/unlink/<link_id>', methods=['DELETE'])
def unlink_exchange(link_id):
    """
    Remove vínculo de uma exchange (soft delete)
    
    Path Params:
        link_id: ID do vínculo
    
    Returns:
        200: Exchange desvinculada com sucesso
        404: Vínculo não encontrado
        500: Erro ao desvincular
    """
    try:
        # Validar ObjectId
        try:
            link_object_id = ObjectId(link_id)
        except:
            return jsonify({
                'success': False,
                'error': 'Invalid link_id format'
            }), 400
        
        # Buscar vínculo
        link = db.user_exchanges.find_one({'_id': link_object_id})
        
        if not link:
            return jsonify({
                'success': False,
                'error': 'Link not found'
            }), 404
        
        # Soft delete - marcar como inativo
        result = db.user_exchanges.update_one(
            {'_id': link_object_id},
            {
                '$set': {
                    'is_active': False,
                    'updated_at': datetime.utcnow()
                }
            }
        )
        
        if result.modified_count > 0:
            # Buscar nome da exchange
            exchange = db.exchanges.find_one({'_id': link['exchange_id']})
            
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

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_ENV') == 'development'
    
    print(f"🚀 Iniciando servidor na porta {port}...")
    app.run(host='0.0.0.0', port=port, debug=debug)
