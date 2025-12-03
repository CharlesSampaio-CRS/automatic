#!/usr/bin/env python3
"""
Script de inicialização do bot de trading
"""
import sys
import os

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Importa e executa a aplicação principal
from src.api.main import app
from dotenv import load_dotenv

load_dotenv()

if __name__ == "__main__":
    # Carrega configurações do .env
    flask_host = os.getenv('FLASK_HOST', '0.0.0.0')
    flask_port = int(os.getenv('FLASK_PORT', 5000))
    flask_debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    print("=" * 60)
    print("🤖 Bot de Trading Automático - MEXC")
    print("=" * 60)
    print(f"🌐 Host: {flask_host}")
    print(f"🔌 Port: {flask_port}")
    print(f"🐛 Debug: {flask_debug}")
    print("=" * 60)
    print()
    
    # Executa a aplicação (a lógica já está no main.py)
    exec(open('src/api/main.py').read())
