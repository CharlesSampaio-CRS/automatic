"""
API Principal - Sistema de Trading Multi-Exchange
"""

import os
from flask import Flask
from dotenv import load_dotenv
from pymongo import MongoClient

# Carrega variáveis de ambiente
load_dotenv()

# Inicializa Flask
app = Flask(__name__)

# Configuração MongoDB
MONGO_URI = os.getenv('MONGODB_URI')
MONGO_DATABASE = os.getenv('MONGODB_DATABASE', 'AutomaticAllExchange')

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
            'exchanges': '/api/v1/exchanges (em desenvolvimento)',
            'balances': '/api/v1/balances (em desenvolvimento)'
        }
    }, 200

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_ENV') == 'development'
    
    print(f"🚀 Iniciando servidor na porta {port}...")
    app.run(host='0.0.0.0', port=port, debug=debug)
