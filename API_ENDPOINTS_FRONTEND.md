# 🌐 API Endpoints - Frontend Integration

## 📍 Base URL
```
http://localhost:5000
```

---

## 🎯 Strategy Endpoints

### **1. Criar Estratégia (com Template)**
```http
POST /api/v1/strategies
Content-Type: application/json
```

**Body:**
```json
{
  "user_id": "charles_test_user",
  "exchange_id": "693481148b0a41e8b6acb07b",
  "token": "REKTCOIN",
  "template": "aggressive",
  "is_active": true
}
```

**Templates disponíveis:** `simple`, `conservative`, `aggressive`

**Response:**
```json
{
  "message": "Strategy created successfully",
  "strategy": {
    "id": "693a324fadc50a3be99c4eb7",
    "user_id": "charles_test_user",
    "exchange_id": "693481148b0a41e8b6acb07b",
    "token": "REKTCOIN",
    "is_active": true,
    "rules": {
      "take_profit_levels": [...],
      "stop_loss": {...},
      "buy_dip": {...},
      "cooldown": {...},
      "risk_management": {...}
    },
    "execution_stats": {...},
    "trailing_stop_state": {...},
    "cooldown_state": {...},
    "created_at": "2024-01-10T10:00:00Z"
  }
}
```

---

### **2. Listar Estratégias do Usuário**
```http
GET /api/v1/strategies?user_id=charles_test_user
```

**Query Parameters:**
- `user_id` (required) - ID do usuário
- `exchange_id` (optional) - Filtrar por exchange
- `token` (optional) - Filtrar por token
- `is_active` (optional) - Filtrar por status (true/false)

**Response:**
```json
{
  "strategies": [
    {
      "id": "693a324fadc50a3be99c4eb7",
      "user_id": "charles_test_user",
      "exchange_id": "693481148b0a41e8b6acb07b",
      "exchange_name": "MEXC",
      "token": "REKTCOIN",
      "is_active": true,
      "rules": {...},
      "execution_stats": {
        "total_executions": 5,
        "total_sells": 3,
        "total_buys": 2,
        "total_pnl_usd": 145.67,
        "daily_pnl_usd": 45.20,
        "executed_tp_levels": [5, 10],
        "last_execution_at": "2024-01-10T15:30:00Z"
      },
      "trailing_stop_state": {...},
      "cooldown_state": {...},
      "created_at": "2024-01-10T10:00:00Z"
    }
  ],
  "total": 1
}
```

---

### **3. Consultar Estratégia Específica**
```http
GET /api/v1/strategies/{strategy_id}
```

**Exemplo:**
```http
GET /api/v1/strategies/693a324fadc50a3be99c4eb7
```

**Response:**
```json
{
  "strategy": {
    "id": "693a324fadc50a3be99c4eb7",
    "user_id": "charles_test_user",
    "exchange_id": "693481148b0a41e8b6acb07b",
    "exchange_name": "MEXC",
    "token": "REKTCOIN",
    "is_active": true,
    "rules": {
      "take_profit_levels": [
        {"percent": 5, "quantity_percent": 30},
        {"percent": 10, "quantity_percent": 40},
        {"percent": 20, "quantity_percent": 30}
      ],
      "stop_loss": {
        "enabled": true,
        "percent": 3,
        "trailing_enabled": true,
        "trailing_percent": 2,
        "trailing_activation_percent": 5
      },
      "buy_dip": {
        "enabled": true,
        "percent": 5,
        "dca_enabled": true,
        "dca_levels": [
          {"percent": 5, "quantity_percent": 50},
          {"percent": 10, "quantity_percent": 50}
        ]
      },
      "cooldown": {
        "enabled": true,
        "after_buy_minutes": 15,
        "after_sell_minutes": 10
      },
      "risk_management": {
        "enabled": true,
        "max_daily_loss_usd": 1000,
        "max_weekly_loss_usd": 3000,
        "max_monthly_loss_usd": 10000
      }
    },
    "execution_stats": {
      "total_executions": 5,
      "total_sells": 3,
      "total_buys": 2,
      "total_pnl_usd": 145.67,
      "daily_pnl_usd": 45.20,
      "weekly_pnl_usd": 120.50,
      "monthly_pnl_usd": 145.67,
      "executed_tp_levels": [5, 10],
      "executed_dca_levels": [],
      "last_execution_at": "2024-01-10T15:30:00Z",
      "last_execution_type": "SELL",
      "last_execution_reason": "TAKE_PROFIT",
      "last_execution_price": 1.22,
      "last_execution_amount": 300
    },
    "trailing_stop_state": {
      "highest_price_seen": 1.25,
      "is_active": true,
      "last_updated": "2024-01-10T15:25:00Z"
    },
    "cooldown_state": {
      "cooldown_until": "2024-01-10T16:00:00Z",
      "last_action": "SELL",
      "last_action_at": "2024-01-10T15:30:00Z"
    },
    "created_at": "2024-01-10T10:00:00Z",
    "updated_at": "2024-01-10T15:30:00Z"
  }
}
```

---

### **4. Pausar/Ativar Estratégia**
```http
PATCH /api/v1/strategies/{strategy_id}/toggle
Content-Type: application/json
```

**Body:**
```json
{
  "is_active": false
}
```

**Response:**
```json
{
  "message": "Strategy status updated",
  "strategy": {
    "id": "693a324fadc50a3be99c4eb7",
    "is_active": false,
    "updated_at": "2024-01-10T16:00:00Z"
  }
}
```

---

### **5. Atualizar Estratégia**
```http
PUT /api/v1/strategies/{strategy_id}
Content-Type: application/json
```

**Body (exemplo - atualizar risk management):**
```json
{
  "rules": {
    "risk_management": {
      "enabled": true,
      "max_daily_loss_usd": 500
    }
  }
}
```

**Response:**
```json
{
  "message": "Strategy updated successfully",
  "strategy": {...}
}
```

---

### **6. Deletar Estratégia**
```http
DELETE /api/v1/strategies/{strategy_id}
```

**Response:**
```json
{
  "message": "Strategy deleted successfully"
}
```

---

## 🔄 Jobs Control Endpoints

### **7. Status dos Jobs**
```http
GET /api/v1/jobs/status
```

**Response:**
```json
{
  "jobs": [
    {
      "id": "balance_snapshot_job",
      "name": "Balance Snapshot",
      "next_run_time": "2024-01-10T18:00:00Z",
      "interval": "4 hours"
    },
    {
      "id": "strategy_worker_job",
      "name": "Strategy Worker",
      "next_run_time": "2024-01-10T16:05:00Z",
      "interval": "5 minutes"
    }
  ],
  "scheduler_running": true
}
```

---

### **8. Controlar Jobs**
```http
POST /api/v1/jobs/control
Content-Type: application/json
```

**Body:**
```json
{
  "job_id": "strategy_worker_job",
  "action": "pause"
}
```

**Actions:** `start`, `stop`, `pause`, `resume`, `restart`

**Response:**
```json
{
  "message": "Job paused successfully",
  "job_id": "strategy_worker_job",
  "status": "paused"
}
```

---

### **9. Executar Job Manualmente**
```http
POST /api/v1/jobs/trigger/strategy_worker
```

**Response:**
```json
{
  "message": "Job triggered successfully",
  "job_id": "strategy_worker_job",
  "execution_time": "2024-01-10T16:00:00Z"
}
```

---

## 💰 Balance Endpoints

### **10. Consultar Saldos**
```http
GET /api/v1/balances?user_id=charles_test_user
```

**Query Parameters:**
- `user_id` (required)
- `exchange_ids` (optional) - Comma-separated IDs
- `include_changes` (optional) - true/false

**Response:**
```json
{
  "balances": [
    {
      "exchange_id": "693481148b0a41e8b6acb07b",
      "exchange_name": "MEXC",
      "balances": [
        {
          "asset": "REKTCOIN",
          "free": 1000,
          "locked": 0,
          "total": 1000,
          "price_usd": 1.25,
          "value_usd": 1250.00,
          "change_24h": 5.2
        }
      ],
      "total_value_usd": 1250.00,
      "last_updated": "2024-01-10T16:00:00Z"
    }
  ],
  "total_portfolio_value_usd": 1250.00
}
```

---

## 🏥 Health Check

### **11. Status da API**
```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "features": [
    "Multi-exchange balance tracking",
    "Automated trading strategies",
    "Advanced strategy rules (TP levels, trailing stop, DCA)",
    "Jobs control system",
    "Circuit breakers and risk management"
  ],
  "database": "connected",
  "scheduler": "running",
  "strategy_worker": {
    "enabled": true,
    "dry_run": true,
    "interval_minutes": 5,
    "active_strategies": 1
  }
}
```

---

## 📝 Exemplos de Uso - Frontend

### **React/TypeScript Example:**

```typescript
// api/strategies.ts
const API_BASE_URL = 'http://localhost:5000/api/v1';

interface Strategy {
  id: string;
  user_id: string;
  exchange_id: string;
  exchange_name: string;
  token: string;
  is_active: boolean;
  rules: any;
  execution_stats: any;
  trailing_stop_state: any;
  cooldown_state: any;
  created_at: string;
}

// 1. Criar estratégia
export async function createStrategy(data: {
  user_id: string;
  exchange_id: string;
  token: string;
  template: 'simple' | 'conservative' | 'aggressive';
  is_active: boolean;
}): Promise<Strategy> {
  const response = await fetch(`${API_BASE_URL}/strategies`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  
  const result = await response.json();
  return result.strategy;
}

// 2. Listar estratégias
export async function listStrategies(userId: string): Promise<Strategy[]> {
  const response = await fetch(
    `${API_BASE_URL}/strategies?user_id=${userId}`
  );
  
  const result = await response.json();
  return result.strategies;
}

// 3. Consultar estratégia
export async function getStrategy(strategyId: string): Promise<Strategy> {
  const response = await fetch(`${API_BASE_URL}/strategies/${strategyId}`);
  const result = await response.json();
  return result.strategy;
}

// 4. Pausar/Ativar
export async function toggleStrategy(
  strategyId: string, 
  isActive: boolean
): Promise<void> {
  await fetch(`${API_BASE_URL}/strategies/${strategyId}/toggle`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ is_active: isActive })
  });
}

// 5. Deletar
export async function deleteStrategy(strategyId: string): Promise<void> {
  await fetch(`${API_BASE_URL}/strategies/${strategyId}`, {
    method: 'DELETE'
  });
}
```

### **React Component Example:**

```typescript
// components/StrategyList.tsx
import { useEffect, useState } from 'react';
import { listStrategies, toggleStrategy, deleteStrategy } from '../api/strategies';

export function StrategyList({ userId }: { userId: string }) {
  const [strategies, setStrategies] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadStrategies();
  }, [userId]);

  async function loadStrategies() {
    setLoading(true);
    try {
      const data = await listStrategies(userId);
      setStrategies(data);
    } catch (error) {
      console.error('Error loading strategies:', error);
    } finally {
      setLoading(false);
    }
  }

  async function handleToggle(strategyId: string, currentStatus: boolean) {
    await toggleStrategy(strategyId, !currentStatus);
    loadStrategies();
  }

  async function handleDelete(strategyId: string) {
    if (confirm('Deletar estratégia?')) {
      await deleteStrategy(strategyId);
      loadStrategies();
    }
  }

  if (loading) return <div>Carregando...</div>;

  return (
    <div>
      <h2>Minhas Estratégias</h2>
      {strategies.map(strategy => (
        <div key={strategy.id} className="strategy-card">
          <h3>{strategy.token} @ {strategy.exchange_name}</h3>
          <p>Status: {strategy.is_active ? '✅ Ativa' : '⏸️ Pausada'}</p>
          <p>PnL Total: ${strategy.execution_stats.total_pnl_usd}</p>
          <p>Execuções: {strategy.execution_stats.total_executions}</p>
          
          <button onClick={() => handleToggle(strategy.id, strategy.is_active)}>
            {strategy.is_active ? 'Pausar' : 'Ativar'}
          </button>
          <button onClick={() => handleDelete(strategy.id)}>
            Deletar
          </button>
        </div>
      ))}
    </div>
  );
}
```

---

## 🎨 UI Recommendations

### **Dashboard Principal:**
```
📊 Portfolio Total: $1,250.00
┌────────────────────────────────────┐
│ 🎯 Estratégias Ativas: 3          │
│ 💰 PnL Hoje: +$45.20               │
│ 📈 PnL Total: +$145.67             │
│ ⚡ Última Execução: há 5 min       │
└────────────────────────────────────┘
```

### **Card de Estratégia:**
```
┌─────────────────────────────────────────────┐
│ REKTCOIN @ MEXC                      ✅ ATIVA│
├─────────────────────────────────────────────┤
│ Template: Aggressive                        │
│ Entry: $1.00 → Current: $1.25 (+25%)       │
│                                             │
│ 📊 Performance:                             │
│   • Execuções: 5 (3 sells, 2 buys)        │
│   • PnL Total: +$145.67                    │
│   • PnL Hoje: +$45.20                      │
│                                             │
│ 🎯 Próximos Triggers:                       │
│   • TP Level 3: 20% (faltam 5%)           │
│   • Trailing Stop: Ativo em $1.25         │
│   • DCA Level 2: -10%                      │
│                                             │
│ ⏱️ Cooldown: 5 min restantes               │
│                                             │
│ [⏸️ Pausar] [✏️ Editar] [🗑️ Deletar]      │
└─────────────────────────────────────────────┘
```

---

## 🚨 Error Handling

Todos os endpoints retornam erros no formato:

```json
{
  "error": "Strategy not found",
  "code": "STRATEGY_NOT_FOUND",
  "status": 404
}
```

**HTTP Status Codes:**
- `200` - Success
- `201` - Created
- `400` - Bad Request (validação falhou)
- `404` - Not Found
- `500` - Internal Server Error

---

## 🔐 CORS

Para testar localmente no frontend:

```javascript
// No frontend, não precisa configurar nada especial
// O backend já tem CORS habilitado para localhost
```

Se precisar configurar CORS no backend:
```python
# src/api/main.py (já configurado)
from flask_cors import CORS
CORS(app)
```

---

## ✅ Checklist de Integração

- [ ] Configurar `API_BASE_URL` no frontend
- [ ] Criar serviço/API client para strategies
- [ ] Criar componentes de listagem de estratégias
- [ ] Criar formulário de criação (com templates)
- [ ] Adicionar botões de pausar/ativar
- [ ] Adicionar botão de deletar
- [ ] Mostrar execution_stats em cards
- [ ] Mostrar trailing_stop_state (se ativo)
- [ ] Mostrar cooldown_state (se em cooldown)
- [ ] Adicionar polling ou WebSocket para updates em tempo real
- [ ] Adicionar notificações de execução
- [ ] Criar gráficos de PnL

---

**🚀 Todas as URLs estão prontas para consumo!**
