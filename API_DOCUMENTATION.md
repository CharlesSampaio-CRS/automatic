# 📚 Documentação da API - Trading System

## 🔗 Base URL
```
http://localhost:8000/api/v1
```

---

## 🏦 Endpoints de Saldos (Balances)

### 1. 💰 Buscar Saldos do Usuário

**Endpoint:** `GET /balances`

**Descrição:** Retorna todos os saldos do usuário em todas as exchanges vinculadas, com dados **REAIS** buscados via CCXT.

**Query Parameters:**
- `user_id` (obrigatório): ID do usuário
- `exchange_id` (opcional): Filtrar por exchange específica
- `min_value_usd` (opcional): Valor mínimo em USD para filtrar tokens
- `include_zero` (opcional, default: false): Incluir tokens com saldo zero
- `force_refresh` (opcional, default: false): Forçar atualização ignorando cache

**Exemplo de Request:**
```bash
GET /api/v1/balances?user_id=charles_test_user&force_refresh=true
```

**Exemplo de Response (200 OK):**
```json
{
  "success": true,
  "user_id": "charles_test_user",
  "exchanges": [
    {
      "exchange_id": "693481148b0a41e8b6acb079",
      "exchange_name": "NovaDAX",
      "ccxt_id": "novadax",
      "icon": "https://play-lh.googleusercontent.com/...",
      "balances": [
        {
          "currency": "LUNC",
          "total": 148349.35328,
          "price_usd": "0.0000401053",
          "value_usd": "5.95"
        },
        {
          "currency": "BTC",
          "total": 6.5e-09,
          "price_usd": "90135.70",
          "value_usd": "0.00"
        }
      ],
      "total_usd": 5.95,
      "success": true
    },
    {
      "exchange_id": "693481148b0a41e8b6acb07b",
      "exchange_name": "MEXC",
      "ccxt_id": "mexc",
      "icon": "https://img.icons8.com/color/96/mexc.png",
      "balances": [
        {
          "currency": "REKTCOIN",
          "total": 465128400.9661325,
          "price_usd": "0.0000002935",
          "value_usd": "136.52"
        }
      ],
      "total_usd": 199.76,
      "success": true
    },
    {
      "exchange_id": "693481148b0a41e8b6acb077",
      "exchange_name": "OKX",
      "ccxt_id": "okx",
      "icon": "https://img.icons8.com/ios-filled/100/okx.png",
      "balances": [],
      "total_usd": 0.0,
      "error": "Error: unsupported operand type(s) for +: 'NoneType' and 'str'",
      "success": false
    }
  ],
  "total_exchanges": 10,
  "total_usd": 214.86,
  "from_cache": false,
  "timestamp": "2025-12-22T15:01:07.126718"
}
```

**Campos da Resposta:**
- `success` (boolean): Status da operação
- `user_id` (string): ID do usuário
- `exchanges` (array): Lista de exchanges
  - `exchange_id` (string): ID da exchange no MongoDB
  - `exchange_name` (string): Nome da exchange
  - `ccxt_id` (string): ID da exchange no CCXT
  - `icon` (string): URL do ícone da exchange
  - `balances` (array): Lista de tokens com saldo
    - `currency` (string): Código da moeda (BTC, ETH, USDT...)
    - `total` (float): Quantidade total do token
    - `price_usd` (string): Preço unitário em USD (formatado)
    - `value_usd` (string): Valor total em USD (formatado)
  - `total_usd` (float): Total em USD desta exchange
  - `success` (boolean): Se a busca foi bem-sucedida
  - `error` (string, opcional): Mensagem de erro se falhou
- `total_exchanges` (int): Total de exchanges consultadas
- `total_usd` (float): Saldo total em USD (todas exchanges)
- `from_cache` (boolean): Se os dados vieram do cache
- `timestamp` (string): Data/hora da consulta (ISO 8601)

**Códigos de Status:**
- `200 OK`: Sucesso
- `500 Internal Server Error`: Erro no servidor

---

### 2. 📈 Histórico de Evolução

**Endpoint:** `GET /history/evolution`

**Descrição:** Retorna a evolução histórica do saldo total do usuário ao longo do tempo.

**Query Parameters:**
- `user_id` (obrigatório): ID do usuário
- `days` (opcional, default: 7): Número de dias para consultar (1-365)

**Exemplo de Request:**
```bash
GET /api/v1/history/evolution?user_id=charles_test_user&days=30
```

**Exemplo de Response (200 OK):**
```json
{
  "success": true,
  "user_id": "charles_test_user",
  "days": 7,
  "data_points": 6,
  "evolution": [
    {
      "timestamp": "2025-12-16T00:00:00",
      "total_usd": 108.68,
      "total_brl": 543.4,
      "exchanges_count": 4
    },
    {
      "timestamp": "2025-12-17T00:00:00",
      "total_usd": 139.9,
      "total_brl": 658.0,
      "exchanges_count": 4
    },
    {
      "timestamp": "2025-12-18T03:00:13.918000",
      "total_usd": 181.16,
      "total_brl": 999.77,
      "exchanges_count": 9
    }
  ],
  "start_date": "2025-12-15T15:10:20.126175",
  "end_date": "2025-12-22T15:10:20.153619"
}
```

**Campos da Resposta:**
- `success` (boolean): Status da operação
- `user_id` (string): ID do usuário
- `days` (int): Número de dias consultados
- `data_points` (int): Quantidade de pontos de dados
- `evolution` (array): Lista com histórico
  - `timestamp` (string): Data/hora do snapshot (ISO 8601)
  - `total_usd` (float): Saldo total em USD
  - `total_brl` (float): Saldo total em BRL
  - `exchanges_count` (int): Número de exchanges ativas
- `start_date` (string): Data inicial do período (ISO 8601)
- `end_date` (string): Data final do período (ISO 8601)

**Códigos de Status:**
- `200 OK`: Sucesso
- `500 Internal Server Error`: Erro no servidor

---

## 🏢 Endpoints de Exchanges

### 3. 📋 Listar Exchanges Disponíveis

**Endpoint:** `GET /exchanges/available`

**Descrição:** Lista todas as exchanges disponíveis para integração.

**Query Parameters:**
- `user_id` (obrigatório): ID do usuário

**Exemplo de Request:**
```bash
GET /api/v1/exchanges/available?user_id=charles_test_user
```

**Exemplo de Response (200 OK):**
```json
{
  "success": true,
  "exchanges": [
    {
      "id": "693481148b0a41e8b6acb073",
      "name": "Binance",
      "ccxt_id": "binance",
      "icon": "https://img.icons8.com/color/96/binance.png",
      "is_linked": true,
      "supports_spot": true,
      "supports_futures": true
    },
    {
      "id": "693481148b0a41e8b6acb079",
      "name": "NovaDAX",
      "ccxt_id": "novadax",
      "icon": "https://play-lh.googleusercontent.com/...",
      "is_linked": true,
      "supports_spot": true,
      "supports_futures": false
    }
  ],
  "total": 11
}
```

---

### 4. 🔗 Exchanges Vinculadas do Usuário

**Endpoint:** `GET /exchanges/linked`

**Descrição:** Lista exchanges vinculadas ao usuário.

**Query Parameters:**
- `user_id` (obrigatório): ID do usuário

**Exemplo de Request:**
```bash
GET /api/v1/exchanges/linked?user_id=charles_test_user
```

**Exemplo de Response (200 OK):**
```json
{
  "success": true,
  "user_id": "charles_test_user",
  "exchanges": [
    {
      "exchange_id": "693481148b0a41e8b6acb073",
      "exchange_name": "Binance",
      "ccxt_id": "binance",
      "icon": "https://img.icons8.com/color/96/binance.png",
      "is_active": true,
      "linked_at": "2025-12-10T10:30:00"
    }
  ],
  "total_linked": 10
}
```

---

## 📊 Endpoints de Estratégias

### 5. 📝 Listar Templates de Estratégias

**Endpoint:** `GET /strategies/templates/list`

**Descrição:** Lista templates pré-configurados de estratégias de trading.

**Query Parameters:**
- `user_id` (obrigatório): ID do usuário

**Exemplo de Request:**
```bash
GET /api/v1/strategies/templates/list?user_id=charles_test_user
```

**Exemplo de Response (200 OK):**
```json
{
  "success": true,
  "templates": [
    {
      "name": "simple",
      "display_name": "Estratégia Simples",
      "description": "Estratégia básica com baixo risco",
      "risk_level": "low",
      "recommended_for": "Iniciantes",
      "features": [
        "1 Take Profit fixo (5%)",
        "Stop Loss fixo (2%)",
        "Sem trailing",
        "Ideal para começar"
      ],
      "rules": {
        "take_profit": {
          "enabled": true,
          "levels": [
            {"percentage": 5, "exit_percentage": 100}
          ]
        },
        "stop_loss": {
          "enabled": true,
          "percentage": 2,
          "trailing": false
        }
      }
    },
    {
      "name": "conservative",
      "display_name": "Estratégia Conservadora",
      "description": "Estratégia com risco controlado",
      "risk_level": "low-medium",
      "recommended_for": "Investidores moderados",
      "features": [
        "2 Take Profits (2% e 4%)",
        "Stop Loss com trailing",
        "Proteção ativa",
        "Risco médio"
      ]
    },
    {
      "name": "aggressive",
      "display_name": "Estratégia Agressiva",
      "description": "Estratégia para altos ganhos",
      "risk_level": "high",
      "recommended_for": "Traders experientes",
      "features": [
        "3 Take Profits (5%, 10%, 20%)",
        "Stop Loss trailing",
        "DCA habilitado",
        "Alto risco/retorno"
      ]
    }
  ],
  "total_templates": 3
}
```

---

## 🪙 Endpoints de Tokens

### 6. 🔍 Informações de Token

**Endpoint:** `GET /tokens/{exchange_id}/{symbol}`

**Descrição:** Retorna informações detalhadas de um token específico (preço, market cap, etc).

**Path Parameters:**
- `exchange_id` (string): ID da exchange
- `symbol` (string): Símbolo do token (BTC, ETH, etc)

**Query Parameters:**
- `user_id` (obrigatório): ID do usuário

**Exemplo de Request:**
```bash
GET /api/v1/tokens/693481148b0a41e8b6acb073/BTC?user_id=charles_test_user
```

**Exemplo de Response (200 OK):**
```json
{
  "symbol": "BTC",
  "name": "Bitcoin",
  "price_usd": 90135.70,
  "price_brl": 498000.00,
  "market_cap": 1750000000000,
  "volume_24h": 35000000000,
  "change_24h": 2.5,
  "ath": 108000.00,
  "atl": 67.81,
  "icon": "https://assets.coingecko.com/coins/images/1/large/bitcoin.png",
  "description": "Bitcoin é a primeira criptomoeda descentralizada...",
  "categories": ["Cryptocurrency", "Store of Value"],
  "links": {
    "homepage": "https://bitcoin.org",
    "whitepaper": "https://bitcoin.org/bitcoin.pdf"
  }
}
```

---

## 🎯 Endpoints de Posições

### 7. 📍 Listar Posições Ativas

**Endpoint:** `GET /positions`

**Descrição:** Lista todas as posições ativas do usuário.

**Query Parameters:**
- `user_id` (obrigatório): ID do usuário
- `exchange_id` (opcional): Filtrar por exchange
- `status` (opcional): Filtrar por status (open, closed, etc)

**Exemplo de Request:**
```bash
GET /api/v1/positions?user_id=charles_test_user&status=open
```

**Exemplo de Response (200 OK):**
```json
{
  "success": true,
  "positions": [
    {
      "position_id": "pos_12345",
      "exchange_id": "693481148b0a41e8b6acb073",
      "exchange_name": "Binance",
      "symbol": "BTC/USDT",
      "side": "buy",
      "entry_price": 88500.00,
      "current_price": 90135.70,
      "quantity": 0.01,
      "pnl_usd": 16.36,
      "pnl_percentage": 1.85,
      "status": "open",
      "opened_at": "2025-12-22T10:00:00"
    }
  ],
  "total_positions": 1,
  "total_pnl_usd": 16.36
}
```

---

## 🔔 Endpoints de Notificações

### 8. 📬 Listar Notificações

**Endpoint:** `GET /notifications`

**Descrição:** Lista notificações do usuário.

**Query Parameters:**
- `user_id` (obrigatório): ID do usuário
- `unread_only` (opcional, default: false): Apenas não lidas
- `limit` (opcional, default: 50): Limite de resultados

**Exemplo de Request:**
```bash
GET /api/v1/notifications?user_id=charles_test_user&unread_only=true
```

**Exemplo de Response (200 OK):**
```json
{
  "success": true,
  "notifications": [
    {
      "id": "notif_123",
      "type": "take_profit_hit",
      "title": "Take Profit Atingido!",
      "message": "BTC/USDT atingiu TP1 (5%) na Binance",
      "priority": "high",
      "read": false,
      "created_at": "2025-12-22T14:30:00"
    },
    {
      "id": "notif_124",
      "type": "balance_change",
      "title": "Saldo Atualizado",
      "message": "Seu saldo total aumentou 2.5%",
      "priority": "medium",
      "read": false,
      "created_at": "2025-12-22T12:00:00"
    }
  ],
  "total": 2,
  "unread_count": 2
}
```

---

## 🔧 Informações Gerais

### Autenticação
Atualmente não há autenticação implementada. O `user_id` é passado como query parameter.

### Formato de Datas
Todas as datas seguem o padrão **ISO 8601**: `YYYY-MM-DDTHH:MM:SS.ssssss`

### Códigos de Status HTTP
- `200 OK`: Sucesso
- `400 Bad Request`: Parâmetros inválidos
- `404 Not Found`: Recurso não encontrado
- `500 Internal Server Error`: Erro no servidor

### Rate Limiting
Não implementado ainda. Recomenda-se usar `force_refresh=false` para aproveitar o cache.

### CORS
CORS habilitado para todas as origens (`*`).

### Cache
- Saldos: Cache de 5 minutos (pode ser ignorado com `force_refresh=true`)
- Preços: Cache de 5 minutos
- Histórico: Sem cache

---

## 📝 Exemplos de Integração Frontend

### React/JavaScript Example

```javascript
// Buscar saldos do usuário
const fetchBalances = async (userId, forceRefresh = false) => {
  const response = await fetch(
    `http://localhost:8000/api/v1/balances?user_id=${userId}&force_refresh=${forceRefresh}`
  );
  const data = await response.json();
  
  if (data.success) {
    console.log('Total USD:', data.total_usd);
    console.log('Exchanges:', data.exchanges.length);
    return data;
  } else {
    throw new Error('Failed to fetch balances');
  }
};

// Buscar evolução histórica
const fetchEvolution = async (userId, days = 7) => {
  const response = await fetch(
    `http://localhost:8000/api/v1/history/evolution?user_id=${userId}&days=${days}`
  );
  const data = await response.json();
  
  if (data.success) {
    // Usar data.evolution para criar gráfico
    return data.evolution;
  }
};

// Usar
fetchBalances('charles_test_user', true)
  .then(data => console.log(data))
  .catch(err => console.error(err));
```

### Axios Example

```javascript
import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000/api/v1',
  timeout: 30000, // 30 segundos para CCXT
});

// Buscar saldos
const getBalances = (userId) => {
  return api.get('/balances', {
    params: {
      user_id: userId,
      force_refresh: true
    }
  });
};

// Buscar evolução
const getEvolution = (userId, days) => {
  return api.get('/history/evolution', {
    params: {
      user_id: userId,
      days: days
    }
  });
};

// Usar
getBalances('charles_test_user')
  .then(response => {
    console.log('Saldos:', response.data);
  })
  .catch(error => {
    console.error('Erro:', error);
  });
```

---

## 🚀 Performance

### Tempo de Resposta Médio
- `/balances` (sem cache): **12-20 segundos** (busca real via CCXT em 10 exchanges)
- `/balances` (com cache): **< 100ms**
- `/history/evolution`: **< 50ms**
- Outros endpoints: **< 100ms**

### Otimizações
- Busca paralela de exchanges (ThreadPoolExecutor)
- Cache de 5 minutos para saldos
- Timeout de 5 segundos por exchange
- Skip de tokens com saldo zero

---

## 📞 Suporte

Para dúvidas ou problemas:
- Logs do servidor: Terminal onde o uvicorn está rodando
- Erros detalhados: Incluídos no campo `error` da resposta
- Debug: Ativar logs com `--log-level debug`

---

**Última atualização:** 22 de dezembro de 2025  
**Versão da API:** 1.0  
**Status:** ✅ Produção (dados reais via CCXT)
