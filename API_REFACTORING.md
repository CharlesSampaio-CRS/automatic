# 🎨 API Refactoring - Standardized Response Format

## 📋 Overview

Refatoração da API para padrão consistente que facilita consumo por frontend Electron.

---

## 🎯 Padrão de Resposta Padronizado

### ✅ Resposta de Sucesso

```typescript
interface SuccessResponse<T> {
  success: true;
  message: string;           // Ex: "Balance retrieved successfully"
  data: T;                   // Dados da resposta (type-safe)
  timestamp: string;         // ISO 8601 (America/Sao_Paulo)
  error: null;
  meta?: {                   // Metadados opcionais (paginação, etc)
    [key: string]: any;
  };
}
```

### ❌ Resposta de Erro

```typescript
interface ErrorResponse {
  success: false;
  message: string;           // Ex: "Configuration not found"
  data: null;
  timestamp: string;         // ISO 8601 (America/Sao_Paulo)
  error: {
    type: string;            // Ex: "not_found", "validation_error", "server_error"
    message: string;         // Mensagem do erro
    details?: any;           // Detalhes adicionais (opcional)
  };
}
```

---

## 📚 Exemplos de Resposta por Endpoint

### 1. GET `/api/v1/health` - Health Check

**Success Response:**
```json
{
  "success": true,
  "message": "API is running",
  "data": {
    "status": "healthy",
    "version": "2.1.2",
    "uptime": 3600,
    "mongodb": {
      "connected": true,
      "database": "TradingBot"
    },
    "scheduler": {
      "running": true,
      "active_jobs": 3
    }
  },
  "timestamp": "2025-12-04T10:30:00-03:00",
  "error": null
}
```

### 2. GET `/api/v1/balance` - Get Balance

**Success Response:**
```json
{
  "success": true,
  "message": "Balance retrieved successfully",
  "data": {
    "total_balance": "1000.50",
    "available_balance": "950.25",
    "in_order": "50.25",
    "currency": "USDT"
  },
  "timestamp": "2025-12-04T10:30:00-03:00",
  "error": null
}
```

**Error Response:**
```json
{
  "success": false,
  "message": "Failed to retrieve balance",
  "data": null,
  "timestamp": "2025-12-04T10:30:00-03:00",
  "error": {
    "type": "api_error",
    "message": "MEXC API connection failed",
    "details": {
      "error_code": "TIMEOUT",
      "retry_after": 60
    }
  }
}
```

### 3. GET `/api/v1/price/:pair` - Get Pair Price

**Success Response:**
```json
{
  "success": true,
  "message": "Price retrieved successfully",
  "data": {
    "pair": "REKT/USDT",
    "current_price": "0.00001234",
    "bid_price": "0.00001233",
    "ask_price": "0.00001235",
    "spread": {
      "value": "0.00000002",
      "percent": 0.1622,
      "status": "LOW"
    },
    "24h_stats": {
      "high": "0.00001456",
      "low": "0.00001123",
      "open": "0.00001200",
      "close": "0.00001234",
      "change": "0.00000034",
      "change_percent": 2.83,
      "volume_usdt": 45678.90,
      "volatility": 29.65
    },
    "market_analysis": {
      "trend": "UP",
      "momentum": "WEAK",
      "liquidity": "MEDIUM",
      "recommendation": "Spread LOW | UP | MEDIUM"
    }
  },
  "timestamp": "2025-12-04T10:30:00-03:00",
  "error": null
}
```

### 4. GET `/api/v1/configs` - List Configurations

**Success Response:**
```json
{
  "success": true,
  "message": "Configurations retrieved successfully",
  "data": [
    {
      "pair": "REKT/USDT",
      "enabled": true,
      "schedule": {
        "interval_minutes": 10,
        "business_hours_start": 9,
        "business_hours_end": 23,
        "enabled": true
      },
      "limits": {
        "min_value_per_order": 20,
        "allocation_percentage": 30
      },
      "metadata": {
        "created_at": "2025-12-01T08:00:00-03:00",
        "updated_at": "2025-12-04T10:00:00-03:00",
        "last_execution": "2025-12-04T10:20:00-03:00",
        "total_orders": 15,
        "total_invested": "450.00",
        "status": "active"
      }
    }
  ],
  "timestamp": "2025-12-04T10:30:00-03:00",
  "error": null,
  "meta": {
    "total": 3,
    "enabled": 2,
    "disabled": 1
  }
}
```

### 5. POST `/api/v1/configs` - Create Configuration

**Success Response:**
```json
{
  "success": true,
  "message": "Configuration created successfully",
  "data": {
    "pair": "BTC/USDT",
    "enabled": true,
    "schedule": {
      "interval_hours": 4,
      "business_hours_start": 9,
      "business_hours_end": 23,
      "enabled": true
    },
    "limits": {
      "min_value_per_order": 50,
      "allocation_percentage": 20
    },
    "metadata": {
      "created_at": "2025-12-04T10:30:00-03:00",
      "status": "created"
    }
  },
  "timestamp": "2025-12-04T10:30:00-03:00",
  "error": null
}
```

**Validation Error Response:**
```json
{
  "success": false,
  "message": "Validation failed",
  "data": null,
  "timestamp": "2025-12-04T10:30:00-03:00",
  "error": {
    "type": "validation_error",
    "message": "Validation failed",
    "details": {
      "fields": {
        "pair": "Required field missing",
        "interval_hours": "Must be between 1 and 24",
        "allocation_percentage": "Must be between 1 and 100"
      }
    }
  }
}
```

### 6. PUT `/api/v1/configs/:pair` - Update Configuration

**Success Response:**
```json
{
  "success": true,
  "message": "Configuration updated successfully",
  "data": {
    "pair": "REKT/USDT",
    "enabled": true,
    "schedule": {
      "interval_minutes": 15,
      "business_hours_start": 9,
      "business_hours_end": 23,
      "enabled": true
    },
    "metadata": {
      "updated_at": "2025-12-04T10:30:00-03:00"
    }
  },
  "timestamp": "2025-12-04T10:30:00-03:00",
  "error": null
}
```

**Not Found Response:**
```json
{
  "success": false,
  "message": "Configuration not found",
  "data": null,
  "timestamp": "2025-12-04T10:30:00-03:00",
  "error": {
    "type": "not_found",
    "message": "Configuration not found",
    "details": {
      "pair": "BTC/USDT",
      "reason": "No configuration exists for this pair"
    }
  }
}
```

### 7. POST `/api/v1/order` - Execute Order

**Success Response:**
```json
{
  "success": true,
  "message": "Order executed successfully",
  "data": {
    "execution_type": "manual",
    "executed_by": "api",
    "timestamp": "2025-12-04T10:30:00-03:00",
    "summary": {
      "buy_executed": true,
      "sell_executed": true,
      "total_invested": "50.00",
      "total_profit": "2.50",
      "net_result": "2.50"
    },
    "buy_details": {
      "orders_executed": 1,
      "total_invested": "50.00"
    },
    "sell_details": {
      "orders_executed": 1,
      "total_profit": "2.50"
    }
  },
  "timestamp": "2025-12-04T10:30:00-03:00",
  "error": null
}
```

### 8. GET `/api/v1/jobs` - List Jobs

**Success Response:**
```json
{
  "success": true,
  "message": "Jobs retrieved successfully",
  "data": [
    {
      "job_id": "job_REKT_USDT",
      "pair": "REKT/USDT",
      "status": "active",
      "schedule": {
        "interval": "10 min",
        "next_run": "2025-12-04T10:40:00-03:00",
        "next_run_formatted": "04/12/2025 10:40:00"
      },
      "metadata": {
        "last_execution": "2025-12-04T10:30:00-03:00",
        "total_executions": 145,
        "total_orders": 15,
        "total_invested": "450.00"
      }
    }
  ],
  "timestamp": "2025-12-04T10:30:00-03:00",
  "error": null,
  "meta": {
    "total_jobs": 3,
    "active_jobs": 2,
    "paused_jobs": 1
  }
}
```

### 9. POST `/api/v1/jobs` - Manage Jobs

**Success Response (Reload):**
```json
{
  "success": true,
  "message": "Jobs reloaded successfully",
  "data": {
    "action": "reload",
    "jobs_loaded": 3,
    "jobs_started": 2,
    "jobs_stopped": 1
  },
  "timestamp": "2025-12-04T10:30:00-03:00",
  "error": null
}
```

**Success Response (Start):**
```json
{
  "success": true,
  "message": "Jobs started successfully",
  "data": {
    "action": "start",
    "pairs": ["REKT/USDT", "BTC/USDT"],
    "jobs_started": 2,
    "next_executions": {
      "REKT/USDT": "2025-12-04T10:40:00-03:00",
      "BTC/USDT": "2025-12-04T14:30:00-03:00"
    }
  },
  "timestamp": "2025-12-04T10:30:00-03:00",
  "error": null
}
```

---

## 🏗️ Estrutura de Arquivos Refatorada

```
src/
├── api/
│   ├── __init__.py
│   ├── main.py              # Main Flask app
│   ├── response.py          # ✨ NEW: Standard response formatter
│   ├── routes/              # ✨ NEW: Organized routes
│   │   ├── __init__.py
│   │   ├── health.py        # Health check routes
│   │   ├── balance.py       # Balance routes
│   │   ├── price.py         # Price routes
│   │   ├── order.py         # Order execution routes
│   │   ├── configs.py       # Configuration routes
│   │   ├── strategy.py      # Strategy routes
│   │   └── jobs.py          # Job management routes
│   └── middleware/          # ✨ NEW: Middleware
│       ├── __init__.py
│       ├── error_handler.py # Global error handler
│       └── cors.py          # CORS configuration
├── clients/
├── config/
├── database/
├── models/
├── services/
└── utils/
```

---

## 🔧 Vantagens da Refatoração

### 1. **Consistência** ✅
- Todas as respostas seguem o mesmo formato
- Fácil de parsear no frontend
- Type-safe com TypeScript

### 2. **Error Handling** ✅
- Erros padronizados com tipos
- Detalhes estruturados
- Códigos HTTP apropriados

### 3. **Organização** ✅
- Rotas separadas por domínio
- Código mais limpo e manutenível
- Fácil adicionar novas features

### 4. **Frontend Electron** ✅
- Interface TypeScript definida
- Tratamento de erro consistente
- Fácil criar interceptors
- Suporte a retry e caching

### 5. **Debugging** ✅
- Timestamp em todas as respostas
- Tipo de erro identificado
- Detalhes estruturados

---

## 🚀 Próximos Passos

1. ✅ **Criar módulo de resposta padronizada** (`response.py`)
2. ⏳ **Refatorar endpoints existentes** para usar novo padrão
3. ⏳ **Criar tipos TypeScript** para o frontend Electron
4. ⏳ **Adicionar middleware** de error handling global
5. ⏳ **Configurar CORS** apropriadamente
6. ⏳ **Adicionar versionamento** da API (`/api/v1`)
7. ⏳ **Criar documentação OpenAPI** (Swagger)

---

## 📝 TypeScript Types para Frontend

```typescript
// types/api.ts

export interface APIResponse<T = any> {
  success: boolean;
  message: string;
  data: T | null;
  timestamp: string;
  error: APIError | null;
  meta?: Record<string, any>;
}

export interface APIError {
  type: string;
  message: string;
  details?: any;
}

// Specific data types
export interface Balance {
  total_balance: string;
  available_balance: string;
  in_order: string;
  currency: string;
}

export interface Config {
  pair: string;
  enabled: boolean;
  schedule: Schedule;
  limits: Limits;
  metadata?: Metadata;
}

export interface Job {
  job_id: string;
  pair: string;
  status: string;
  schedule: JobSchedule;
  metadata?: JobMetadata;
}

// ... more types
```

---

**Status**: ✅ **Módulo de Resposta Criado**  
**Next**: Refatorar endpoints para usar novo padrão  
**Version**: v2.2.0  
**Date**: December 4, 2025
