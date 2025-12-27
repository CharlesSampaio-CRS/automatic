"""
📋 Request Validators

Funções helper para validar parâmetros obrigatórios em requisições
Garante que user_id e exchange_id sejam sempre fornecidos quando necessário
"""

from flask import jsonify, request
from typing import Tuple, Optional, Dict, Any
from functools import wraps


def validate_required_params(*param_names) -> Tuple[bool, Optional[Dict[str, Any]], Optional[tuple]]:
    """
    Valida se parâmetros obrigatórios estão presentes na query string ou JSON body
    
    Args:
        *param_names: Nomes dos parâmetros obrigatórios
    
    Returns:
        Tuple (is_valid, params_dict, error_response)
        - is_valid: True se todos os parâmetros estão presentes
        - params_dict: Dicionário com os valores dos parâmetros
        - error_response: Tuple (json_response, status_code) se inválido, None se válido
    
    Exemplo:
        is_valid, params, error = validate_required_params('user_id', 'exchange_id')
        if not is_valid:
            return error
        
        user_id = params['user_id']
        exchange_id = params['exchange_id']
    """
    params = {}
    missing = []
    
    # Tenta pegar de query params (GET)
    for param in param_names:
        value = request.args.get(param)
        
        # Se não encontrou na query, tenta no JSON body (POST/PUT/DELETE)
        if value is None and request.is_json:
            json_data = request.get_json()
            value = json_data.get(param) if json_data else None
        
        if value is None or value == '':
            missing.append(param)
        else:
            params[param] = value
    
    if missing:
        error_response = (
            jsonify({
                'success': False,
                'error': 'Missing required parameters',
                'missing': missing,
                'message': f"Required parameters: {', '.join(missing)}"
            }),
            400
        )
        return False, None, error_response
    
    return True, params, None


def require_params(*param_names):
    """
    Decorator para validar parâmetros obrigatórios automaticamente
    
    Adiciona os parâmetros validados ao request context para uso na rota
    
    Uso:
        @app.route('/api/v1/endpoint')
        @require_params('user_id', 'exchange_id')
        def my_endpoint():
            user_id = request.validated_params['user_id']
            exchange_id = request.validated_params['exchange_id']
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            is_valid, params, error = validate_required_params(*param_names)
            
            if not is_valid:
                return error
            
            # Adiciona parâmetros validados ao request para uso na rota
            request.validated_params = params
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


def validate_user_id() -> Tuple[bool, Optional[str], Optional[tuple]]:
    """
    Valida se user_id está presente (helper específico mais usado)
    
    Returns:
        Tuple (is_valid, user_id, error_response)
    
    Exemplo:
        is_valid, user_id, error = validate_user_id()
        if not is_valid:
            return error
    """
    is_valid, params, error = validate_required_params('user_id')
    
    if not is_valid:
        return False, None, error
    
    return True, params['user_id'], None


def validate_user_and_exchange() -> Tuple[bool, Optional[str], Optional[str], Optional[tuple]]:
    """
    Valida se user_id e exchange_id estão presentes (helper específico)
    
    Returns:
        Tuple (is_valid, user_id, exchange_id, error_response)
    
    Exemplo:
        is_valid, user_id, exchange_id, error = validate_user_and_exchange()
        if not is_valid:
            return error
    """
    is_valid, params, error = validate_required_params('user_id', 'exchange_id')
    
    if not is_valid:
        return False, None, None, error
    
    return True, params['user_id'], params['exchange_id'], None


# Aliases para retrocompatibilidade
require_user_id = lambda: require_params('user_id')
require_user_and_exchange = lambda: require_params('user_id', 'exchange_id')
