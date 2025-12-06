"""
API Principal - Sistema de Trading Multi-Exchange
"""

import os
from flask import Flask, jsonify
from dotenv import load_dotenv
from pymongo import MongoClient
from bson import ObjectId

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
            'exchanges_available': '/api/v1/exchanges/available',
            'exchanges_link': '/api/v1/exchanges/link (em desenvolvimento)',
            'exchanges_linked': '/api/v1/exchanges/linked (em desenvolvimento)',
            'balances': '/api/v1/balances (em desenvolvimento)'
        }
    }, 200

# ============================================
# ENDPOINTS DE EXCHANGES
# ============================================

@app.route('/api/v1/exchanges/available', methods=['GET'])
def get_available_exchanges():
    """
    Lista todas as exchanges disponíveis para vinculação
    
    Returns:
        200: Lista de exchanges disponíveis
        500: Erro ao buscar exchanges
    """
    try:
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

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_ENV') == 'development'
    
    print(f"🚀 Iniciando servidor na porta {port}...")
    app.run(host='0.0.0.0', port=port, debug=debug)
