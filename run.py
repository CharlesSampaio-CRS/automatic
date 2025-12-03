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
    # Executa a aplicação (logs estão no main.py)
    exec(open('src/api/main.py').read())

