"""
🔐 JWT Authentication Module

Implementação de autenticação JWT para API
Baseado no padrão Kong para geração e validação de tokens

Funcionalidades:
- Geração de JWT tokens
- Validação de tokens
- Refresh tokens
- OAuth integration (Google/Apple)
"""

import jwt
import os
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify
from typing import Dict, Optional, Tuple

# Secret key para assinar tokens (em produção, usar variável de ambiente)
JWT_SECRET = os.getenv('JWT_SECRET', 'nQv?J/&dNnB*qni@@KonG')
JWT_ALGORITHM = 'HS256'
JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)  # Token expira em 24h
JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)  # Refresh expira em 30 dias


def generate_access_token(user_id: str, email: str, provider: str = 'email') -> str:
    """
    Gera token JWT de acesso
    
    Args:
        user_id: ID único do usuário
        email: Email do usuário
        provider: Provedor de autenticação ('google', 'apple', 'email')
    
    Returns:
        Token JWT string
    """
    payload = {
        'user_id': user_id,
        'email': email,
        'provider': provider,
        'exp': datetime.utcnow() + JWT_ACCESS_TOKEN_EXPIRES,
        'iat': datetime.utcnow(),
        'type': 'access'
    }
    
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token


def generate_refresh_token(user_id: str) -> str:
    """
    Gera token JWT de refresh
    
    Args:
        user_id: ID único do usuário
    
    Returns:
        Refresh token JWT string
    """
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + JWT_REFRESH_TOKEN_EXPIRES,
        'iat': datetime.utcnow(),
        'type': 'refresh'
    }
    
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token


def verify_token(token: str) -> Tuple[bool, Optional[Dict], Optional[str]]:
    """
    Verifica e decodifica token JWT
    
    Args:
        token: Token JWT string
    
    Returns:
        Tuple (is_valid, payload, error_message)
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return True, payload, None
    except jwt.ExpiredSignatureError:
        return False, None, 'Token expired'
    except jwt.InvalidTokenError as e:
        return False, None, f'Invalid token: {str(e)}'


def require_auth(f):
    """
    Decorator para proteger rotas que exigem autenticação
    
    Extrai token do header Authorization: Bearer <token>
    Adiciona user_id ao request context se válido
    
    Uso:
        @app.route('/api/v1/protected')
        @require_auth
        def protected_route():
            user_id = request.user_id  # Disponível após decorador
            ...
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Extrai token do header
        auth_header = request.headers.get('Authorization')
        
        if not auth_header:
            return jsonify({
                'success': False,
                'error': 'No authorization header',
                'message': 'Authorization header is required'
            }), 401
        
        # Formato esperado: "Bearer <token>"
        parts = auth_header.split()
        
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            return jsonify({
                'success': False,
                'error': 'Invalid authorization header',
                'message': 'Format: Authorization: Bearer <token>'
            }), 401
        
        token = parts[1]
        
        # Verifica token
        is_valid, payload, error = verify_token(token)
        
        if not is_valid:
            return jsonify({
                'success': False,
                'error': 'Invalid token',
                'message': error
            }), 401
        
        # Adiciona user_id ao request para uso na rota
        request.user_id = payload['user_id']
        request.user_email = payload.get('email')
        request.auth_provider = payload.get('provider')
        
        return f(*args, **kwargs)
    
    return decorated_function


def optional_auth(f):
    """
    Decorator para rotas que funcionam com ou sem autenticação
    
    Se token válido, adiciona user_id ao request
    Se não, continua sem autenticação
    
    Uso:
        @app.route('/api/v1/public-or-private')
        @optional_auth
        def flexible_route():
            user_id = getattr(request, 'user_id', None)
            if user_id:
                # User autenticado
            else:
                # User anônimo
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        if auth_header:
            parts = auth_header.split()
            
            if len(parts) == 2 and parts[0].lower() == 'bearer':
                token = parts[1]
                is_valid, payload, _ = verify_token(token)
                
                if is_valid:
                    request.user_id = payload['user_id']
                    request.user_email = payload.get('email')
                    request.auth_provider = payload.get('provider')
        
        return f(*args, **kwargs)
    
    return decorated_function
