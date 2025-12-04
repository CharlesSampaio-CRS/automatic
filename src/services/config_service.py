"""
Serviço de Gerenciamento de Configurações no MongoDB

Gerencia CRUD de configurações por símbolo (criptomoeda)
"""

import os
import sys
from datetime import datetime
from typing import Dict, List, Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.database.mongodb_connection import connection_mongo
from src.models.config_schema import validate_config, EXAMPLE_CONFIG

# Collection de configurações
CONFIG_COLLECTION = "BotConfigs"


class ConfigService:
    """Serviço para gerenciar configurações de símbolos no MongoDB"""
    
    def __init__(self):
        """Inicializa conexão com MongoDB"""
        self.collection = None
        try:
            self.collection = connection_mongo(CONFIG_COLLECTION)
            # Conectado silenciosamente
        except Exception as e:
            print(f"! Erro ConfigService: {e}")
    
    def create_symbol_config(self, config: Dict) -> tuple[bool, str, Optional[Dict]]:
        """
        Cria nova configuração para um símbolo
        
        Args:
            config: Dicionário com configuração do símbolo
        
        Returns:
            (success, message, config_id)
        """
        if self.collection is None:
            return False, "MongoDB não disponível", None
        
        # Valida configuração
        is_valid, error = validate_config(config)
        if not is_valid:
            return False, f"Configuração inválida: {error}", None
        
        # Verifica se já existe
        pair = config.get("pair")
        existing = self.collection.find_one({"pair": pair})
        if existing:
            return False, f"Configuração para {pair} já existe. Use update.", None
        
        # Adiciona timestamps
        config["created_at"] = datetime.now()
        config["updated_at"] = datetime.now()
        
        # Inicializa metadata se não existir
        if "metadata" not in config:
            config["metadata"] = {
                "last_execution": None,
                "total_orders": 0,
                "total_invested": 0.0,
                "status": "active"
            }
        
        try:
            result = self.collection.insert_one(config)
            config_with_id = {**config, "_id": str(result.inserted_id)}
            return True, f"Configuração criada para {pair}", config_with_id
        except Exception as e:
            return False, f"Erro ao salvar: {e}", None
    
    def update_symbol_config(self, pair: str, updates: Dict) -> tuple[bool, str]:
        """
        Atualiza configuração de um símbolo
        
        Args:
            pair: Par da criptomoeda (ex: "REKTCOIN/USDT")
            updates: Campos a atualizar
        
        Returns:
            (success, message)
        """
        if self.collection is None:
            return False, "MongoDB não disponível"
        
        # Busca configuração existente
        existing = self.collection.find_one({"pair": pair})
        if not existing:
            return False, f"Configuração para {pair} não encontrada"
        
        # Merge das atualizações
        updated_config = {**existing, **updates}
        updated_config["updated_at"] = datetime.now()
        
        # Valida configuração atualizada
        is_valid, error = validate_config(updated_config)
        if not is_valid:
            return False, f"Configuração inválida após update: {error}"
        
        try:
            self.collection.update_one(
                {"pair": pair},
                {"$set": {**updates, "updated_at": datetime.now()}}
            )
            return True, f"Configuração de {pair} atualizada"
        except Exception as e:
            return False, f"Erro ao atualizar: {e}"
    
    def get_symbol_config(self, pair: str) -> Optional[Dict]:
        """
        Busca configuração de um símbolo
        
        Args:
            pair: Par da criptomoeda
        
        Returns:
            Configuração ou None
        """
        if self.collection is None:
            return None
        
        try:
            config = self.collection.find_one({"pair": pair})
            if config:
                config["_id"] = str(config["_id"])
            return config
        except Exception as e:
            print(f" Erro ao buscar configuração: {e}")
            return None
    
    def get_all_configs(self, enabled_only: bool = False) -> List[Dict]:
        """
        Lista todas as configurações
        
        Args:
            enabled_only: Se True, retorna apenas símbolos habilitados
        
        Returns:
            Lista de configurações
        """
        if self.collection is None:
            return []
        
        try:
            query = {"enabled": True} if enabled_only else {}
            configs = list(self.collection.find(query))
            
            # Converte ObjectId para string
            for config in configs:
                config["_id"] = str(config["_id"])
            
            return configs
        except Exception as e:
            print(f" Erro ao listar configurações: {e}")
            return []
    
    def delete_symbol_config(self, pair: str) -> tuple[bool, str]:
        """
        Remove configuração de um símbolo
        
        Args:
            pair: Par da criptomoeda
        
        Returns:
            (success, message)
        """
        if self.collection is None:
            return False, "MongoDB não disponível"
        
        try:
            result = self.collection.delete_one({"pair": pair})
            if result.deleted_count > 0:
                return True, f"Configuração de {pair} removida"
            else:
                return False, f"Configuração de {pair} não encontrada"
        except Exception as e:
            return False, f"Erro ao deletar: {e}"
    
    def toggle_symbol(self, pair: str, enabled: bool) -> tuple[bool, str]:
        """
        Habilita/desabilita um símbolo
        
        Args:
            pair: Par da criptomoeda
            enabled: True para habilitar, False para desabilitar
        
        Returns:
            (success, message)
        """
        return self.update_symbol_config(pair, {"enabled": enabled})
    
    def update_metadata(self, pair: str, metadata_updates: Dict) -> tuple[bool, str]:
        """
        Atualiza metadata de um símbolo (após execução)
        
        Args:
            pair: Par da criptomoeda
            metadata_updates: Campos de metadata a atualizar
        
        Returns:
            (success, message)
        """
        if self.collection is None:
            return False, "MongoDB não disponível"
        
        try:
            # Busca metadata atual
            config = self.collection.find_one({"pair": pair})
            if not config:
                return False, f"Configuração de {pair} não encontrada"
            
            current_metadata = config.get("metadata", {})
            updated_metadata = {**current_metadata, **metadata_updates}
            
            self.collection.update_one(
                {"pair": pair},
                {"$set": {
                    "metadata": updated_metadata,
                    "updated_at": datetime.now()
                }}
            )
            return True, f"Metadata de {pair} atualizada"
        except Exception as e:
            return False, f"Erro ao atualizar metadata: {e}"
    
    def get_enabled_symbols(self) -> List[str]:
        """
        Retorna lista de pares habilitados
        
        Returns:
            Lista de pares (ex: ["REKTCOIN/USDT", "BTC/USDT"])
        """
        configs = self.get_all_configs(enabled_only=True)
        return [config["pair"] for config in configs if config.get("schedule", {}).get("enabled", True)]


# Instância global
config_service = ConfigService()
