#!/usr/bin/env python3
"""
Script de inicialização da API
"""
import sys
import os
from dotenv import load_dotenv

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Carrega variáveis de ambiente
load_dotenv()

# Importa e executa a aplicação
from src.api.main import app

# Expõe app para Gunicorn (necessário para produção)
# Gunicorn usa: gunicorn run:app
application = app

if __name__ == "__main__":
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_ENV') == 'development'
    
    print(f"🚀 Iniciando API na porta {port}...")
    print(f"📝 Debug mode: {'ON' if debug else 'OFF'}")
    
    app.run(host='0.0.0.0', port=port, debug=debug)
