# JWT Authentication Guide

## Overview

All API endpoints are protected with JWT (JSON Web Token) authentication, **except the `/health` endpoint** which is public for monitoring purposes.

## Authentication Flow

1. Obtain a JWT token from the authentication API (external service)
2. Include the token in the `Authorization` header of every request
3. The token will be validated before processing the request

## How to Use

### Header Format

```
Authorization: Bearer <your-jwt-token>
```

### Example Request

```bash
curl -X GET https://your-api.com/balance \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### Example with Postman

1. Go to the **Authorization** tab
2. Select **Bearer Token** type
3. Paste your JWT token in the Token field

## Configuration

### Environment Variables

Add these to your `.env` file:

```env
# JWT Configuration
JWT_SECRET_KEY=your-super-secret-key-change-this-in-production
JWT_ALGORITHM=HS256
```

⚠️ **IMPORTANT**: Change the `JWT_SECRET_KEY` to a strong random string in production!

### Generating a Strong Secret Key

```python
import secrets
print(secrets.token_urlsafe(32))
```

## Protected Endpoints

All endpoints require JWT authentication except `/health`:

### ✅ Protected Endpoints (Require JWT)
- `GET /` - API home
- `GET /balance` - Get USDT balance
- `GET /price` - Get price (query params)
- `GET /price/:pair` - Get price (path param)
- `POST /prices` - Get multiple prices
- `POST /order` - Execute manual order
- `GET /configs` - List all configurations
- `POST /configs` - Create configuration
- `GET /configs/:pair` - Get specific configuration
- `PUT /configs/:pair` - Update configuration
- `DELETE /configs/:pair` - Delete configuration
- `GET /configs/:pair/strategy-1h` - Get 1h strategy
- `PUT /configs/:pair/strategy-1h` - Update 1h strategy
- `POST /configs/:pair/strategy-1h/toggle` - Toggle strategy
- `GET /jobs` - List active jobs
- `POST /jobs` - Manage jobs

### 🌍 Public Endpoints (No JWT Required)
- `GET /health` - System health check

## Error Responses

### 401 Unauthorized - Missing Token

```json
{
  "success": false,
  "message": "Missing Authorization header",
  "data": null,
  "timestamp": "2025-12-04T10:30:00-03:00",
  "error": {
    "type": "unauthorized",
    "message": "Missing Authorization header",
    "details": null
  }
}
```

### 401 Unauthorized - Invalid Format

```json
{
  "success": false,
  "message": "Invalid Authorization header format. Expected: Bearer <token>",
  "data": null,
  "timestamp": "2025-12-04T10:30:00-03:00",
  "error": {
    "type": "unauthorized",
    "message": "Invalid Authorization header format. Expected: Bearer <token>",
    "details": null
  }
}
```

### 401 Unauthorized - Expired Token

```json
{
  "success": false,
  "message": "Token has expired",
  "data": null,
  "timestamp": "2025-12-04T10:30:00-03:00",
  "error": {
    "type": "unauthorized",
    "message": "Token has expired",
    "details": null
  }
}
```

### 401 Unauthorized - Invalid Token

```json
{
  "success": false,
  "message": "Invalid token: <error details>",
  "data": null,
  "timestamp": "2025-12-04T10:30:00-03:00",
  "error": {
    "type": "unauthorized",
    "message": "Invalid token: <error details>",
    "details": null
  }
}
```

## JWT Payload Structure

The JWT token can contain any payload. Example:

```json
{
  "sub": "user123",
  "name": "John Doe",
  "email": "john@example.com",
  "iat": 1638360000,
  "exp": 1638363600
}
```

The payload is accessible in the endpoint via `request.jwt_payload`:

```python
from src.middleware.auth import get_jwt_payload

@app.route("/profile")
@require_jwt
def get_profile():
    payload = get_jwt_payload()
    user_id = payload.get('sub')
    return {"user_id": user_id}
```

## Security Best Practices

1. **Never commit secrets**: Keep `JWT_SECRET_KEY` out of version control
2. **Use HTTPS**: Always use HTTPS in production to prevent token interception
3. **Token expiration**: Set appropriate expiration times (recommended: 1-24 hours)
4. **Rotate keys**: Periodically rotate your JWT secret key
5. **Validate claims**: Always validate token claims (exp, iat, iss, etc.)

## Implementation Details

### Decorator Usage

The `@require_jwt` decorator is applied to protected endpoints:

```python
from src.middleware.auth import require_jwt

@app.route("/protected")
@require_jwt
def protected_endpoint():
    return APIResponse.success(
        data={"message": "Access granted"},
        message="Protected resource accessed"
    )
```

### Middleware Flow

1. Request received
2. Decorator extracts `Authorization` header
3. Validates format: `Bearer <token>`
4. Decodes and validates JWT using `JWT_SECRET_KEY`
5. Checks expiration (`exp` claim)
6. Attaches decoded payload to `request.jwt_payload`
7. Calls the original endpoint function
8. Returns 401 if any validation fails

## Testing

### Test with Valid Token

```bash
# Generate a test token (Python)
import jwt
import datetime

payload = {
    "sub": "test_user",
    "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)
}
token = jwt.encode(payload, "your-secret-key", algorithm="HS256")
print(token)

# Test the API
curl -X GET http://localhost:5000/balance \
  -H "Authorization: Bearer ${token}"
```

### Test without Token

```bash
curl -X GET http://localhost:5000/balance
# Expected: 401 Unauthorized - Missing Authorization header
```

### Test with Invalid Token

```bash
curl -X GET http://localhost:5000/balance \
  -H "Authorization: Bearer invalid-token"
# Expected: 401 Unauthorized - Invalid token
```

## Troubleshooting

### Common Issues

1. **"Não foi possível resolver a importação 'jwt'"**
   - Solution: Install PyJWT with `pip install PyJWT==2.9.0`

2. **"Token has expired"**
   - Solution: Generate a new token with a valid expiration time

3. **"Invalid token"**
   - Verify the secret key matches between token generation and validation
   - Ensure the algorithm (HS256) is correct

4. **"Missing Authorization header"**
   - Add the `Authorization: Bearer <token>` header to your request

## Migration from Non-Authenticated API

If you're migrating from a non-authenticated API:

1. Update all client applications to include JWT tokens
2. Obtain tokens from your authentication service
3. Add `Authorization: Bearer <token>` to all requests (except `/health`)
4. Test each endpoint to ensure authentication works
5. Monitor 401 errors in logs for failed authentication attempts

## Dependencies

- **PyJWT**: 2.9.0
- **Flask**: 3.1.0

Install with:
```bash
pip install PyJWT==2.9.0
```
