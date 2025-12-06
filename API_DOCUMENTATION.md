# Multi-Exchange Balance API - Documentação Completa

## Base URL
```
http://localhost:5000
```

---

## 1. Health Check

### Endpoint
```
GET /health
```

### Descrição
Verifica se a API está rodando e conectada ao MongoDB.

### Resposta de Sucesso (200)
```json
{
  "status": "ok",
  "message": "API rodando",
  "database": "connected"
}
```

---

## 2. Listar Exchanges Disponíveis

### Endpoint
```
GET /api/v1/exchanges/available
```

### Parâmetros Query
| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| user_id | string | Sim | ID do usuário |

### Exemplo de Requisição
```bash
curl "http://localhost:5000/api/v1/exchanges/available?user_id=charles_test_user"
```

### Resposta de Sucesso (200)
```json
{
  "available_exchanges": [
    {
      "_id": "693481148b0a41e8b6acb073",
      "nome": "Binance",
      "ccxt_id": "binance",
      "icon_url": "https://example.com/binance.png",
      "description": "Maior exchange de criptomoedas do mundo"
    },
    {
      "_id": "693481148b0a41e8b6acb079",
      "nome": "NovaDAX",
      "ccxt_id": "novadax",
      "icon_url": "https://example.com/novadax.png",
      "description": "Exchange brasileira regulamentada"
    },
    {
      "_id": "693481148b0a41e8b6acb07b",
      "nome": "MEXC",
      "ccxt_id": "mexc",
      "icon_url": "https://example.com/mexc.png",
      "description": "Exchange global com diversos tokens"
    }
  ],
  "user_id": "charles_test_user"
}
```

### Resposta de Erro (400)
```json
{
  "success": false,
  "error": "user_id is required as query parameter"
}
```

---

## 3. Vincular Exchange (Link)

### Endpoint
```
POST /api/v1/exchanges/link
```

### Headers
```
Content-Type: application/json
```

### Body
```json
{
  "user_id": "charles_test_user",
  "exchange_id": "693481148b0a41e8b6acb079",
  "api_key": "your_api_key_here",
  "api_secret": "your_api_secret_here"
}
```

### Exemplo de Requisição
```bash
curl -X POST http://localhost:5000/api/v1/exchanges/link \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "charles_test_user",
    "exchange_id": "693481148b0a41e8b6acb079",
    "api_key": "test_key",
    "api_secret": "test_secret"
  }'
```

### Resposta de Sucesso (201)
```json
{
  "success": true,
  "message": "Exchange NovaDAX vinculada com sucesso",
  "exchange": {
    "exchange_id": "693481148b0a41e8b6acb079",
    "exchange_name": "NovaDAX",
    "is_active": true,
    "linked_at": "2025-12-06T20:15:30.123456"
  }
}
```

### Resposta de Erro - Campos Faltando (400)
```json
{
  "success": false,
  "error": "Missing required fields: user_id, exchange_id, api_key, api_secret"
}
```

### Resposta de Erro - Exchange ID Inválido (400)
```json
{
  "success": false,
  "error": "Invalid exchange_id format"
}
```

### Resposta de Erro - Exchange Não Encontrada (404)
```json
{
  "success": false,
  "error": "Exchange not found"
}
```

### Resposta de Erro - Já Vinculada (400)
```json
{
  "success": false,
  "error": "Exchange already linked for this user"
}
```

### Resposta de Erro - Credenciais Inválidas (401)
```json
{
  "success": false,
  "error": "Invalid API credentials. Could not authenticate with exchange."
}
```

---

## 4. Listar Exchanges Vinculadas

### Endpoint
```
GET /api/v1/exchanges/linked
```

### Parâmetros Query
| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| user_id | string | Sim | ID do usuário |

### Exemplo de Requisição
```bash
curl "http://localhost:5000/api/v1/exchanges/linked?user_id=charles_test_user"
```

### Resposta de Sucesso (200)
```json
{
  "linked_exchanges": [
    {
      "exchange_id": "693481148b0a41e8b6acb079",
      "exchange_name": "NovaDAX",
      "ccxt_id": "novadax",
      "is_active": true,
      "linked_at": "2025-12-06T20:15:30.123456",
      "last_sync": null
    },
    {
      "exchange_id": "693481148b0a41e8b6acb07b",
      "exchange_name": "MEXC",
      "ccxt_id": "mexc",
      "is_active": true,
      "linked_at": "2025-12-06T20:18:45.789012",
      "last_sync": "2025-12-06T21:00:00.000000"
    },
    {
      "exchange_id": "693481148b0a41e8b6acb073",
      "exchange_name": "Binance",
      "ccxt_id": "binance",
      "is_active": false,
      "linked_at": "2025-12-05T15:30:00.000000",
      "last_sync": "2025-12-06T10:00:00.000000"
    }
  ],
  "user_id": "charles_test_user",
  "count": 3
}
```

### Resposta de Erro (400)
```json
{
  "success": false,
  "error": "user_id is required as query parameter"
}
```

### Resposta - Nenhuma Exchange Vinculada (200)
```json
{
  "linked_exchanges": [],
  "user_id": "charles_test_user",
  "count": 0
}
```

---

## 5. Desvincular Exchange (Unlink)

### Endpoint
```
DELETE /api/v1/exchanges/unlink
```

### Headers
```
Content-Type: application/json
```

### Body
```json
{
  "user_id": "charles_test_user",
  "exchange_id": "693481148b0a41e8b6acb079"
}
```

### Exemplo de Requisição
```bash
curl -X DELETE http://localhost:5000/api/v1/exchanges/unlink \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "charles_test_user",
    "exchange_id": "693481148b0a41e8b6acb079"
  }'
```

### Resposta de Sucesso (200)
```json
{
  "success": true,
  "message": "Exchange NovaDAX desvinculada com sucesso"
}
```

### Resposta de Erro - Campos Faltando (400)
```json
{
  "success": false,
  "error": "Missing required fields: user_id and exchange_id"
}
```

### Resposta de Erro - Exchange Não Encontrada (404)
```json
{
  "success": false,
  "error": "Exchange link not found"
}
```

---

## 6. Buscar Saldos de Todas as Exchanges

### Endpoint
```
GET /api/v1/balances
```

### Parâmetros Query
| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| user_id | string | Sim | ID do usuário |
| force_refresh | boolean | Não | true para ignorar cache (padrão: false) |
| currency | string | Não | 'brl' para incluir conversão BRL |

### Exemplo de Requisição
```bash
# Requisição simples
curl "http://localhost:5000/api/v1/balances?user_id=charles_test_user"

# Com force refresh (ignora cache)
curl "http://localhost:5000/api/v1/balances?user_id=charles_test_user&force_refresh=true"

# Com conversão BRL
curl "http://localhost:5000/api/v1/balances?user_id=charles_test_user&currency=brl"
```

### Resposta de Sucesso (200)
```json
{
  "user_id": "charles_test_user",
  "timestamp": "2025-12-06T21:11:43.253623",
  "summary": {
    "total_usd": 135.17,
    "exchanges_count": 3
  },
  "exchanges": [
    {
      "exchange_id": "693481148b0a41e8b6acb079",
      "name": "NovaDAX",
      "success": true,
      "total_usd": 0.0,
      "tokens": {
        "PEPE": {
          "amount": 0.6192,
          "price_usd": 0.0,
          "value_usd": 0.0
        },
        "FLOKI": {
          "amount": 0.56,
          "price_usd": 0.0,
          "value_usd": 0.0
        },
        "BONK": {
          "amount": 0.49488,
          "price_usd": 0.0,
          "value_usd": 0.0
        }
      }
    },
    {
      "exchange_id": "693481148b0a41e8b6acb07b",
      "name": "MEXC",
      "success": true,
      "total_usd": 135.17,
      "tokens": {
        "REKTCOIN": {
          "amount": 454135458.9661325,
          "price_usd": 0.000297,
          "value_usd": 135.02
        },
        "MX": {
          "amount": 0.07022369,
          "price_usd": 2.1489,
          "value_usd": 0.15
        },
        "ICG": {
          "amount": 12069255.0,
          "price_usd": 0.0,
          "value_usd": 0.0
        }
      }
    },
    {
      "exchange_id": "693481148b0a41e8b6acb073",
      "name": "Binance",
      "success": true,
      "total_usd": 0.0,
      "tokens": {
        "BRL": {
          "amount": 0.00332774,
          "price_usd": 0.0,
          "value_usd": 0.0
        }
      }
    }
  ],
  "meta": {
    "from_cache": false
  }
}
```

### Resposta com Erro em uma Exchange (200)
```json
{
  "user_id": "charles_test_user",
  "timestamp": "2025-12-06T21:15:00.000000",
  "summary": {
    "total_usd": 135.17,
    "exchanges_count": 2
  },
  "exchanges": [
    {
      "exchange_id": "693481148b0a41e8b6acb079",
      "name": "NovaDAX",
      "success": false,
      "total_usd": 0.0,
      "tokens": {},
      "error": "Authentication failed: Invalid API credentials"
    },
    {
      "exchange_id": "693481148b0a41e8b6acb07b",
      "name": "MEXC",
      "success": true,
      "total_usd": 135.17,
      "tokens": {
        "REKTCOIN": {
          "amount": 454135458.9661325,
          "price_usd": 0.000297,
          "value_usd": 135.02
        }
      }
    }
  ],
  "meta": {
    "from_cache": false
  }
}
```

### Resposta de Erro (400)
```json
{
  "success": false,
  "error": "user_id is required as query parameter"
}
```

### Resposta - Nenhuma Exchange Vinculada (404)
```json
{
  "success": false,
  "error": "No linked exchanges found for user"
}
```

---

## 7. Limpar Cache de Saldos

### Endpoint
```
POST /api/v1/balances/clear-cache
```

### Headers
```
Content-Type: application/json
```

### Body
```json
{
  "user_id": "charles_test_user"
}
```

### Exemplo de Requisição
```bash
curl -X POST http://localhost:5000/api/v1/balances/clear-cache \
  -H "Content-Type: application/json" \
  -d '{"user_id": "charles_test_user"}'
```

### Resposta de Sucesso (200)
```json
{
  "success": true,
  "message": "Cache cleared successfully"
}
```

### Resposta de Erro (400)
```json
{
  "success": false,
  "error": "user_id is required"
}
```

---

## 8. Histórico de Saldos

### Endpoint
```
GET /api/v1/balances/history
```

### Parâmetros Query
| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| user_id | string | Sim | ID do usuário |
| start_date | string | Não | Data inicial (ISO 8601: 2025-12-01T00:00:00Z) |
| end_date | string | Não | Data final (ISO 8601: 2025-12-06T23:59:59Z) |
| limit | integer | Não | Número máximo de registros (padrão: 100) |

### Exemplo de Requisição
```bash
# Últimos 100 registros
curl "http://localhost:5000/api/v1/balances/history?user_id=charles_test_user"

# Com filtro de data
curl "http://localhost:5000/api/v1/balances/history?user_id=charles_test_user&start_date=2025-12-01T00:00:00Z&end_date=2025-12-06T23:59:59Z"

# Com limite específico
curl "http://localhost:5000/api/v1/balances/history?user_id=charles_test_user&limit=50"
```

### Resposta de Sucesso (200)
```json
{
  "user_id": "charles_test_user",
  "history": [
    {
      "_id": "675359a1d1b531c27dcf78e2",
      "user_id": "charles_test_user",
      "timestamp": "2025-12-06T21:00:00.000000",
      "total_usd": 135.17,
      "total_brl": 685.32,
      "exchanges": [
        {
          "exchange_id": "693481148b0a41e8b6acb079",
          "exchange_name": "NovaDAX",
          "total_usd": 0.0,
          "total_brl": 0.0,
          "success": true
        },
        {
          "exchange_id": "693481148b0a41e8b6acb07b",
          "exchange_name": "MEXC",
          "total_usd": 135.17,
          "total_brl": 685.32,
          "success": true
        }
      ]
    },
    {
      "_id": "675350a1d1b531c27dcf78e1",
      "user_id": "charles_test_user",
      "timestamp": "2025-12-06T20:00:00.000000",
      "total_usd": 134.89,
      "total_brl": 683.91,
      "exchanges": [
        {
          "exchange_id": "693481148b0a41e8b6acb079",
          "exchange_name": "NovaDAX",
          "total_usd": 0.0,
          "total_brl": 0.0,
          "success": true
        },
        {
          "exchange_id": "693481148b0a41e8b6acb07b",
          "exchange_name": "MEXC",
          "total_usd": 134.89,
          "total_brl": 683.91,
          "success": true
        }
      ]
    }
  ],
  "count": 2,
  "start_date": "2025-12-06T00:00:00Z",
  "end_date": "2025-12-06T23:59:59Z"
}
```

### Resposta de Erro (400)
```json
{
  "success": false,
  "error": "user_id is required as query parameter"
}
```

---

## 9. Último Snapshot de Saldo

### Endpoint
```
GET /api/v1/balances/history/latest
```

### Parâmetros Query
| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| user_id | string | Sim | ID do usuário |

### Exemplo de Requisição
```bash
curl "http://localhost:5000/api/v1/balances/history/latest?user_id=charles_test_user"
```

### Resposta de Sucesso (200)
```json
{
  "user_id": "charles_test_user",
  "latest_snapshot": {
    "_id": "675359a1d1b531c27dcf78e2",
    "user_id": "charles_test_user",
    "timestamp": "2025-12-06T21:00:00.000000",
    "total_usd": 135.17,
    "total_brl": 685.32,
    "exchanges": [
      {
        "exchange_id": "693481148b0a41e8b6acb079",
        "exchange_name": "NovaDAX",
        "total_usd": 0.0,
        "total_brl": 0.0,
        "success": true
      },
      {
        "exchange_id": "693481148b0a41e8b6acb07b",
        "exchange_name": "MEXC",
        "total_usd": 135.17,
        "total_brl": 685.32,
        "success": true
      }
    ]
  }
}
```

### Resposta - Sem Histórico (404)
```json
{
  "success": false,
  "error": "No history found for user"
}
```

---

## 10. Histórico de Token Específico

### Endpoint
```
GET /api/v1/balances/history/token/{token}
```

### Parâmetros Path
| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| token | string | Sim | Símbolo do token (ex: REKTCOIN, BTC, ETH) |

### Parâmetros Query
| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| user_id | string | Sim | ID do usuário |
| start_date | string | Não | Data inicial (ISO 8601) |
| end_date | string | Não | Data final (ISO 8601) |
| limit | integer | Não | Número máximo de registros (padrão: 100) |

### Exemplo de Requisição
```bash
curl "http://localhost:5000/api/v1/balances/history/token/REKTCOIN?user_id=charles_test_user"
```

### Resposta de Sucesso (200)
```json
{
  "user_id": "charles_test_user",
  "token": "REKTCOIN",
  "history": [
    {
      "timestamp": "2025-12-06T21:00:00.000000",
      "amount": 454135458.9661325,
      "price_usd": 0.000297,
      "value_usd": 135.02,
      "exchange_name": "MEXC"
    },
    {
      "timestamp": "2025-12-06T20:00:00.000000",
      "amount": 454135458.9661325,
      "price_usd": 0.000296,
      "value_usd": 134.42,
      "exchange_name": "MEXC"
    }
  ],
  "count": 2
}
```

### Resposta - Token Não Encontrado (404)
```json
{
  "success": false,
  "error": "No history found for token REKTCOIN"
}
```

---

## 11. Evolução do Portfolio

### Endpoint
```
GET /api/v1/balances/history/evolution
```

### Parâmetros Query
| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| user_id | string | Sim | ID do usuário |
| period | string | Não | Período: '24h', '7d', '30d', '90d', '1y' (padrão: 7d) |

### Exemplo de Requisição
```bash
# Últimos 7 dias (padrão)
curl "http://localhost:5000/api/v1/balances/history/evolution?user_id=charles_test_user"

# Últimas 24 horas
curl "http://localhost:5000/api/v1/balances/history/evolution?user_id=charles_test_user&period=24h"

# Últimos 30 dias
curl "http://localhost:5000/api/v1/balances/history/evolution?user_id=charles_test_user&period=30d"
```

### Resposta de Sucesso (200)
```json
{
  "user_id": "charles_test_user",
  "period": "7d",
  "data_points": [
    {
      "timestamp": "2025-11-30T00:00:00.000000",
      "total_usd": 128.45,
      "total_brl": 651.23
    },
    {
      "timestamp": "2025-12-01T00:00:00.000000",
      "total_usd": 129.87,
      "total_brl": 658.42
    },
    {
      "timestamp": "2025-12-02T00:00:00.000000",
      "total_usd": 131.23,
      "total_brl": 665.33
    },
    {
      "timestamp": "2025-12-03T00:00:00.000000",
      "total_usd": 132.56,
      "total_brl": 672.07
    },
    {
      "timestamp": "2025-12-04T00:00:00.000000",
      "total_usd": 133.89,
      "total_brl": 678.81
    },
    {
      "timestamp": "2025-12-05T00:00:00.000000",
      "total_usd": 134.12,
      "total_brl": 679.97
    },
    {
      "timestamp": "2025-12-06T00:00:00.000000",
      "total_usd": 135.17,
      "total_brl": 685.32
    }
  ],
  "summary": {
    "start_value_usd": 128.45,
    "end_value_usd": 135.17,
    "change_usd": 6.72,
    "change_percent": 5.23,
    "start_value_brl": 651.23,
    "end_value_brl": 685.32,
    "change_brl": 34.09,
    "highest_value_usd": 135.17,
    "lowest_value_usd": 128.45
  }
}
```

---

## Estrutura de Dados

### Exchange Object
```typescript
{
  _id: string;              // MongoDB ObjectId
  nome: string;             // Nome da exchange
  ccxt_id: string;          // ID da exchange no CCXT
  icon_url?: string;        // URL do ícone
  description?: string;     // Descrição da exchange
}
```

### Linked Exchange Object
```typescript
{
  exchange_id: string;      // MongoDB ObjectId da exchange
  exchange_name: string;    // Nome da exchange
  ccxt_id: string;          // ID CCXT
  is_active: boolean;       // Se está ativa
  linked_at: string;        // ISO 8601 timestamp
  last_sync?: string;       // ISO 8601 timestamp ou null
}
```

### Token Object
```typescript
{
  amount: number;           // Quantidade do token (8 casas decimais)
  price_usd: number;        // Preço em USD (6 casas decimais)
  value_usd: number;        // Valor total em USD (2 casas decimais)
}
```

### Exchange Balance Object
```typescript
{
  exchange_id: string;      // MongoDB ObjectId
  name: string;             // Nome da exchange
  success: boolean;         // Se a busca foi bem-sucedida
  total_usd: number;        // Total em USD
  tokens: {                 // Objeto com tokens
    [symbol: string]: TokenObject
  };
  error?: string;           // Mensagem de erro (se success = false)
}
```

---

## Códigos de Status HTTP

| Código | Descrição |
|--------|-----------|
| 200 | Sucesso |
| 201 | Criado com sucesso |
| 400 | Requisição inválida (parâmetros faltando ou inválidos) |
| 401 | Não autorizado (credenciais inválidas) |
| 404 | Recurso não encontrado |
| 500 | Erro interno do servidor |

---

## Notas Importantes

1. **Timestamps**: Todos os timestamps seguem o formato ISO 8601 (ex: `2025-12-06T21:11:43.253623`)

2. **Cache**: A API usa cache de 5 minutos por padrão. Use `force_refresh=true` para ignorar.

3. **Tokens com Valor Zero**: Tokens com `value_usd = 0` e `price_usd = 0` são incluídos na resposta, mas podem ser filtrados no frontend.

4. **Execução Paralela**: O endpoint `/api/v1/balances` busca saldos de todas as exchanges em paralelo para melhor performance.

5. **Erros Parciais**: Se uma exchange falhar, as outras ainda retornam dados. O campo `success` indica o status individual.

6. **MongoDB ObjectId**: Os IDs das exchanges seguem o formato ObjectId do MongoDB (24 caracteres hexadecimais).

7. **Criptografia**: As credenciais (API keys e secrets) são armazenadas criptografadas no MongoDB usando Fernet.

8. **Rate Limiting**: Algumas exchanges têm rate limiting. Use cache quando possível.

---

## Ambiente de Desenvolvimento

### Variáveis de Ambiente (.env)
```bash
MONGODB_URI=mongodb+srv://user:password@cluster.mongodb.net/
MONGODB_DATABASE=MultExchange
ENCRYPTION_KEY=your_fernet_encryption_key_here
```

### Portas
- **API**: 5000
- **MongoDB**: 27017 (local) ou cloud (Atlas)

---

## Exemplo de Fluxo Completo

```bash
# 1. Verificar saúde da API
curl http://localhost:5000/health

# 2. Listar exchanges disponíveis
curl "http://localhost:5000/api/v1/exchanges/available?user_id=charles_test_user"

# 3. Vincular uma exchange
curl -X POST http://localhost:5000/api/v1/exchanges/link \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "charles_test_user",
    "exchange_id": "693481148b0a41e8b6acb07b",
    "api_key": "your_api_key",
    "api_secret": "your_api_secret"
  }'

# 4. Listar exchanges vinculadas
curl "http://localhost:5000/api/v1/exchanges/linked?user_id=charles_test_user"

# 5. Buscar saldos
curl "http://localhost:5000/api/v1/balances?user_id=charles_test_user"

# 6. Buscar histórico
curl "http://localhost:5000/api/v1/balances/history?user_id=charles_test_user&limit=10"

# 7. Buscar evolução (últimos 7 dias)
curl "http://localhost:5000/api/v1/balances/history/evolution?user_id=charles_test_user&period=7d"

# 8. Desvincular exchange
curl -X DELETE http://localhost:5000/api/v1/exchanges/unlink \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "charles_test_user",
    "exchange_id": "693481148b0a41e8b6acb07b"
  }'
```
