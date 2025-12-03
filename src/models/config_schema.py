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
    "Tranding_strategy": {
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
    
    # Estratégia de 1 hora (Scalping)
    "strategy_1h": {
        "enabled": "boolean",  # Ativa/desativa estratégia de 1h
        "levels": [
            {
                "name": "string",
                "variation_threshold": "number",    # Ex: -2.0 para -2%
                "percentage_of_balance": "number",  # Ex: 5 para 5%
                "description": "string"
            }
        ],
        "risk_management": {
            "stop_loss_percent": "number",          # Ex: -3.0 para -3%
            "cooldown_minutes": "number",           # Ex: 15 minutos
            "max_trades_per_hour": "number",        # Ex: 3 trades
            "max_position_size_percent": "number"   # Ex: 10 para 10%
        }
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
    
    "Tranding_strategy": {
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
    
    "strategy_1h": {
        "enabled": False,  # Desabilitado por padrão
        "levels": [
            {
                "name": "Scalp Leve",
                "variation_threshold": -2.0,
                "percentage_of_balance": 5,
                "description": "Compra pequena em queda rápida de 2%"
            },
            {
                "name": "Scalp Moderado",
                "variation_threshold": -3.0,
                "percentage_of_balance": 7,
                "description": "Compra média em queda de 3%"
            },
            {
                "name": "Scalp Forte",
                "variation_threshold": -5.0,
                "percentage_of_balance": 10,
                "description": "Compra forte em queda brusca de 5%"
            }
        ],
        "risk_management": {
            "stop_loss_percent": -3.0,
            "cooldown_minutes": 15,
            "max_trades_per_hour": 3,
            "max_position_size_percent": 10.0
        }
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
    required_fields = ["pair", "enabled", "schedule", "limits", "Tranding_strategy"]
    
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
    
    # Valida strategy_1h (se existir)
    if "strategy_1h" in config:
        strategy_1h = config["strategy_1h"]
        
        # Valida levels
        if "levels" in strategy_1h and strategy_1h["levels"]:
            for level in strategy_1h["levels"]:
                if level.get("variation_threshold", 0) >= 0:
                    return False, "variation_threshold deve ser negativo (ex: -2.0)"
                
                if not (0 < level.get("percentage_of_balance", 0) <= 100):
                    return False, "percentage_of_balance deve estar entre 0 e 100"
        
        # Valida risk_management
        if "risk_management" in strategy_1h:
            risk_mgmt = strategy_1h["risk_management"]
            
            if risk_mgmt.get("stop_loss_percent", 0) >= 0:
                return False, "stop_loss_percent deve ser negativo (ex: -3.0)"
            
            if risk_mgmt.get("cooldown_minutes", 0) < 0:
                return False, "cooldown_minutes deve ser >= 0"
            
            if risk_mgmt.get("max_trades_per_hour", 0) < 1:
                return False, "max_trades_per_hour deve ser >= 1"
            
            if not (0 < risk_mgmt.get("max_position_size_percent", 0) <= 100):
                return False, "max_position_size_percent deve estar entre 0 e 100"
    
    return True, None
