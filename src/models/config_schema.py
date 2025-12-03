"""
Schema de Configuração para MongoDB

Cada símbolo (criptomoeda) terá sua própria configuração e job independente
"""

from datetime import datetime
from typing import Dict, List, Optional

# Schema para configuração de um símbolo
SYMBOL_CONFIG_SCHEMA = {
    "pair": "string",           # Ex: "REKTCOIN/USDT", "BTC/USDT"
    "enabled": "boolean",       # Job ativo ou pausado
    "created_at": "datetime",
    "updated_at": "datetime",
    
    # Schedule específico do símbolo
    "schedule": {
        "interval_hours": "number",      # Intervalo entre execuções
        "business_hours_start": "number", # Hora de início (0-23)
        "business_hours_end": "number",   # Hora de fim (0-23)
        "enabled": "boolean"              # Schedule ativo
    },
    
    # Limites de operação
    "limits": {
        "min_value_per_order": "number",     # Mínimo por ordem
        "max_value_per_order": "number",     # Máximo por ordem (opcional)
        "allocation_percentage": "number"    # % do saldo total para essa moeda
    },
    
    # Estratégia de compra específica
    "trading_strategy": {
        "buy_on_dip": "boolean",
        "buy_strategy_type": "string",  # "gradual_dip", "fixed", etc
        "buy_levels": [
            {
                "name": "string",
                "variation_threshold": "number",    # Ex: -5.0
                "percentage_of_balance": "number",  # Ex: 20
                "description": "string"
            }
        ]
    },
    
    # Estratégia de venda específica
    "sell_strategy": {
        "enabled": "boolean",
        "type": "string",  # "progressive", "fixed"
        "levels": [
            {
                "name": "string",
                "sell_percentage": "number",    # % da posição a vender
                "profit_target": "number",      # % de lucro alvo
                "description": "string"
            }
        ],
        "check_interval_minutes": "number",
        "auto_execute": "boolean",
        "notify_on_target": "boolean"
    },
    
    # Metadados
    "metadata": {
        "last_execution": "datetime",
        "total_orders": "number",
        "total_invested": "number",
        "status": "string"  # "active", "paused", "error"
    }
}

# Exemplo de documento completo
EXAMPLE_CONFIG = {
    "pair": "REKTCOIN/USDT",
    "enabled": True,
    "created_at": datetime.now(),
    "updated_at": datetime.now(),
    
    "schedule": {
        "interval_hours": 2,
        "business_hours_start": 9,
        "business_hours_end": 23,
        "enabled": True
    },
    
    "limits": {
        "min_value_per_order": 10,
        "max_value_per_order": 100,
        "allocation_percentage": 50
    },
    
    "trading_strategy": {
        "buy_on_dip": True,
        "buy_strategy_type": "gradual_dip",
        "buy_levels": [
            {
                "name": "Compra Leve",
                "variation_threshold": -5.0,
                "percentage_of_balance": 20,
                "description": "Começa a comprar em quedas pequenas"
            },
            {
                "name": "Compra Moderada",
                "variation_threshold": -10.0,
                "percentage_of_balance": 30,
                "description": "Aumenta compra em quedas médias"
            },
            {
                "name": "Compra Forte",
                "variation_threshold": -15.0,
                "percentage_of_balance": 50,
                "description": "Compra pesado em quedas grandes"
            },
            {
                "name": "Compra Máxima",
                "variation_threshold": -20.0,
                "percentage_of_balance": 100,
                "description": "All-in nas quedas extremas"
            }
        ]
    },
    
    "sell_strategy": {
        "enabled": True,
        "type": "progressive",
        "levels": [
            {
                "name": "Nível 1 - Lucro Seguro",
                "sell_percentage": 33,
                "profit_target": 15.0,
                "description": "Garante lucro inicial"
            },
            {
                "name": "Nível 2 - Lucro Médio",
                "sell_percentage": 33,
                "profit_target": 20.0,
                "description": "Dobra o lucro realizado"
            },
            {
                "name": "Nível 3 - Lucro Máximo",
                "sell_percentage": 34,
                "profit_target": 25.0,
                "description": "Maximiza ganhos se continuar subindo"
            }
        ],
        "check_interval_minutes": 30,
        "auto_execute": False,
        "notify_on_target": True
    },
    
    "metadata": {
        "last_execution": None,
        "total_orders": 0,
        "total_invested": 0.0,
        "status": "active"
    }
}

def validate_config(config: Dict) -> tuple[bool, Optional[str]]:
    """
    Valida uma configuração de símbolo
    
    Returns:
        (is_valid, error_message)
    """
    required_fields = ["pair", "enabled", "schedule", "limits", "trading_strategy"]
    
    for field in required_fields:
        if field not in config:
            return False, f"Campo obrigatório ausente: {field}"
    
    # Valida schedule
    schedule = config.get("schedule", {})
    if schedule.get("interval_hours", 0) < 1:
        return False, "interval_hours deve ser >= 1"
    
    if not (0 <= schedule.get("business_hours_start", -1) <= 23):
        return False, "business_hours_start deve estar entre 0 e 23"
    
    if not (0 <= schedule.get("business_hours_end", -1) <= 23):
        return False, "business_hours_end deve estar entre 0 e 23"
    
    # Valida limits
    limits = config.get("limits", {})
    if limits.get("min_value_per_order", 0) <= 0:
        return False, "min_value_per_order deve ser > 0"
    
    if not (0 < limits.get("allocation_percentage", 0) <= 100):
        return False, "allocation_percentage deve estar entre 0 e 100"
    
    return True, None
