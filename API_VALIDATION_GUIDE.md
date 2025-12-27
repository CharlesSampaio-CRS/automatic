# 📋 Endpoints API - Validação de Parâmetros Obrigatórios

## ✅ Endpoints que EXIGEM user_id

### Balances
- `GET /api/v1/balances?user_id=<required>`
- `GET /api/v1/balances/summary?user_id=<required>`
- `GET /api/v1/balances/exchange/<exchange_id>?user_id=<required>`
- `GET /api/v1/history/evolution?user_id=<required>`

### Exchanges
- `GET /api/v1/exchanges/available?user_id=<required>`
- `GET /api/v1/exchanges/linked?user_id=<required>`
- `POST /api/v1/exchanges/link` (user_id no body)
- `DELETE /api/v1/exchanges/unlink` (user_id no body)
- `POST /api/v1/exchanges/disconnect` (user_id no body)
- `DELETE /api/v1/exchanges/delete` (user_id no body)
- `POST /api/v1/exchanges/connect` (user_id no body)

### Token Info
- `GET /api/v1/tokens/search?user_id=<required>&exchange_id=<required>`
- `GET /api/v1/exchanges/<exchange_id>/token/<symbol>?user_id=<required>`
- `GET /api/v1/exchanges/<exchange_id>?user_id=<optional>`

## ✅ Endpoints que EXIGEM user_id + exchange_id

### Orders (Trading)
- `GET /api/v1/orders/open?user_id=<required>&exchange_id=<required>`
- `GET /api/v1/orders/history?user_id=<required>&exchange_id=<required>`
- `POST /api/v1/orders/buy` (user_id + exchange_id no body)
- `POST /api/v1/orders/sell` (user_id + exchange_id no body)
- `POST /api/v1/orders/cancel` (user_id + order_id no body, exchange_id opcional)
- `POST /api/v1/orders/cancel-all` (user_id + exchange_id no body)
- `POST /api/v1/orders/edit` (user_id + exchange_id + order_id no body)

### Exchange Data
- `GET /api/v1/exchanges/<exchange_id>/balance/<token>?user_id=<required>`
- `GET /api/v1/exchanges/<exchange_id>/markets?user_id=<required>`

## 🔓 Endpoints Públicos (SEM autenticação)

### Health & Status
- `GET /health`
- `GET /`
- `GET /api/v1/metrics`
- `GET /api/v1/scheduler/status`

### Authentication
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `GET /api/v1/auth/verify` (requer JWT token no header)

## 📝 Regras de Validação

### Backend (Flask)
1. **TODOS** os endpoints de balances, exchanges, orders, tokens devem validar `user_id`
2. Endpoints de trading devem validar `user_id` + `exchange_id`
3. Usar decorator `@require_params('user_id')` ou `@require_params('user_id', 'exchange_id')`
4. Retornar HTTP 400 se parâmetros obrigatórios faltarem

### Frontend (React/TypeScript)
1. **NUNCA** fazer chamadas sem `user_id`
2. Chamadas de trading sempre incluir `exchange_id`
3. TypeScript garante tipos corretos (userId: string obrigatório)
4. Tratar erro 400 de missing parameters graciosamente

## 🔐 Autenticação JWT (Futuro)

Endpoints protegidos podem usar:
```python
@require_auth  # Valida JWT token
@require_params('user_id')  # Valida parâmetros
def my_endpoint():
    user_id_from_token = request.user_id  # Do JWT
    user_id_from_params = request.validated_params['user_id']  # Dos params
    
    # Verificar se são iguais (segurança)
    if user_id_from_token != user_id_from_params:
        return jsonify({'error': 'Unauthorized'}), 403
```

## ❌ Endpoints Removidos/Deprecated

Nenhum endpoint foi removido ainda. Todos estão ativos.

## 🆕 Endpoints Faltantes

Verificar se frontend usa algum endpoint que não existe no backend:
- [ ] Revisar api.ts completo
- [ ] Comparar com endpoints em main.py
- [ ] Adicionar endpoints faltantes se necessário
