"""
JWT Authentication Middleware
Validates JWT tokens for protected API endpoints
"""

import os
import jwt
from functools import wraps
from flask import request
from src.api.response import APIResponse

# JWT Configuration
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'your-secret-key-change-in-production')
JWT_ALGORITHM = os.getenv('JWT_ALGORITHM', 'HS256')


def require_jwt(f):
    """
    Decorator para exigir autenticação JWT em endpoints
    
    Usage:
        @app.route("/protected")
        @require_jwt
        def protected_endpoint():
            return {"message": "Access granted"}
    
    O token deve ser enviado no header:
        Authorization: Bearer <token>
    
    O token JWT será validado e decodificado. Se inválido, retorna 401.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Extrai token do header Authorization
        auth_header = request.headers.get('Authorization')
        
        if not auth_header:
            return APIResponse.unauthorized(
                message="Missing Authorization header"
            )
        
        # Verifica formato: "Bearer <token>"
        parts = auth_header.split()
        
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            return APIResponse.unauthorized(
                message="Invalid Authorization header format. Expected: Bearer <token>"
            )
        
        token = parts[1]
        
        try:
            # Valida e decodifica o token JWT
            payload = jwt.decode(
                token,
                JWT_SECRET_KEY,
                algorithms=[JWT_ALGORITHM]
            )
            
            # Adiciona payload decodificado ao request para uso no endpoint
            request.jwt_payload = payload
            
            # Chama a função original
            return f(*args, **kwargs)
            
        except jwt.ExpiredSignatureError:
            return APIResponse.unauthorized(
                message="Token has expired"
            )
        except jwt.InvalidTokenError as e:
            return APIResponse.unauthorized(
                message=f"Invalid token: {str(e)}"
            )
        except Exception as e:
            return APIResponse.server_error(
                error=e,
                message="Failed to validate token"
            )
    
    return decorated_function


def get_jwt_payload():
    """
    Retorna o payload JWT decodificado do request atual
    Útil para obter informações do usuário autenticado
    
    Returns:
        dict: Payload do JWT ou None se não houver
    """
    return getattr(request, 'jwt_payload', None)
