import os
from pymongo import MongoClient
from dotenv import load_dotenv

# Carrega variáveis do arquivo .env
load_dotenv()

# Pega as variáveis do .env
MONGODB_URI = os.getenv('MONGODB_URI')
MONGODB_DATABASE = os.getenv('MONGODB_DATABASE', 'AutomaticInvest')

# Validação
if not MONGODB_URI:
    raise ValueError("MONGODB_URI não encontrado no arquivo .env")

try:
    client = MongoClient(MONGODB_URI)
    db = client[MONGODB_DATABASE]
    # Conectado silenciosamente
except Exception as e:
    print(f"! Erro MongoDB: {e}")
    raise

def connection_mongo(collection):
    """
    Retorna uma conexão para a coleção especificada
    
    Args:
        collection (str): Nome da coleção
        
    Returns:
        Collection: Objeto de coleção do MongoDB
    """
    return db[collection]

def get_database():
    """
    Retorna o objeto do banco de dados MongoDB
    
    Returns:
        Database: Objeto do banco de dados MongoDB
    """
    return db
