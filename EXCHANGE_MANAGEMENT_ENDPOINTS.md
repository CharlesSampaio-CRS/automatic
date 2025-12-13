# 🔌 Exchange Management Endpoints

## Endpoints para Gerenciar Conexões de Exchanges

---

## 1. 🔌 Desconectar Exchange (Soft Delete)

**Endpoint:** `POST /api/v1/exchanges/disconnect`

**Descrição:** Desconecta temporariamente uma exchange, mantendo os dados criptografados. Pode ser reconectada depois.

**Request Body:**
```json
{
  "user_id": "charles_test_user",
  "exchange_id": "693481148b0a41e8b6acb07b"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "MEXC disconnected successfully",
  "exchange": {
    "id": "693481148b0a41e8b6acb07b",
    "name": "MEXC",
    "is_active": false
  }
}
```

**Erros Possíveis:**
- `400`: Dados inválidos ou exchange já está desconectada
- `404`: Exchange não encontrada
- `500`: Erro interno

---

## 2. 🗑️ Deletar Exchange (Hard Delete)

**Endpoint:** `DELETE /api/v1/exchanges/delete`

**Descrição:** **Remove permanentemente** uma conexão de exchange. ⚠️ **AÇÃO IRREVERSÍVEL!**

**Request Body:**
```json
{
  "user_id": "charles_test_user",
  "exchange_id": "693481148b0a41e8b6acb07b"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "MEXC deleted permanently",
  "warning": "This action is irreversible. The exchange connection has been removed."
}
```

**Erros Possíveis:**
- `400`: Dados inválidos
- `404`: Exchange não encontrada
- `500`: Erro interno

---

## 3. 🔄 Reconectar Exchange

**Endpoint:** `POST /api/v1/exchanges/reconnect`

**Descrição:** Reativa uma exchange desconectada.

**Request Body:**
```json
{
  "user_id": "charles_test_user",
  "exchange_id": "693481148b0a41e8b6acb07b"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "MEXC reconnected successfully",
  "exchange": {
    "id": "693481148b0a41e8b6acb07b",
    "name": "MEXC",
    "is_active": true
  }
}
```

**Erros Possíveis:**
- `400`: Dados inválidos ou exchange já está ativa
- `404`: Exchange não encontrada
- `500`: Erro interno

---

## 📊 Comparação: Disconnect vs Delete

| Característica | Disconnect (Soft Delete) | Delete (Hard Delete) |
|---------------|--------------------------|----------------------|
| **Reversível** | ✅ Sim (use reconnect) | ❌ Não |
| **Dados mantidos** | ✅ API Key criptografada mantida | ❌ Tudo removido |
| **Aparece em /balances** | ❌ Não (is_active=false) | ❌ Não (removido) |
| **Uso recomendado** | Desativar temporariamente | Remover definitivamente |

---

## 🧪 Exemplos de Uso

### **JavaScript/Fetch:**

```javascript
// 1. Desconectar exchange
async function disconnectExchange(userId, exchangeId) {
  const response = await fetch('http://localhost:5000/api/v1/exchanges/disconnect', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      user_id: userId,
      exchange_id: exchangeId
    })
  });
  
  return await response.json();
}

// 2. Deletar exchange (IRREVERSÍVEL)
async function deleteExchange(userId, exchangeId) {
  const confirmed = confirm('⚠️ ATENÇÃO: Esta ação é IRREVERSÍVEL! Deseja realmente deletar esta exchange?');
  
  if (!confirmed) return;
  
  const response = await fetch('http://localhost:5000/api/v1/exchanges/delete', {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      user_id: userId,
      exchange_id: exchangeId
    })
  });
  
  return await response.json();
}

// 3. Reconectar exchange
async function reconnectExchange(userId, exchangeId) {
  const response = await fetch('http://localhost:5000/api/v1/exchanges/reconnect', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      user_id: userId,
      exchange_id: exchangeId
    })
  });
  
  return await response.json();
}

// Uso:
disconnectExchange('charles_test_user', '693481148b0a41e8b6acb07b')
  .then(result => console.log('Exchange desconectada:', result));
```

---

### **React Component:**

```typescript
import React, { useState } from 'react';
import api from '../services/api';

interface Exchange {
  id: string;
  name: string;
  is_active: boolean;
}

interface ExchangeCardProps {
  exchange: Exchange;
  userId: string;
  onUpdate: () => void;
}

function ExchangeCard({ exchange, userId, onUpdate }: ExchangeCardProps) {
  const [loading, setLoading] = useState(false);

  const handleDisconnect = async () => {
    if (!confirm(`Desconectar ${exchange.name}?`)) return;
    
    setLoading(true);
    try {
      await api.post('/exchanges/disconnect', {
        user_id: userId,
        exchange_id: exchange.id
      });
      alert(`${exchange.name} desconectada com sucesso!`);
      onUpdate();
    } catch (error) {
      alert(`Erro ao desconectar: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!confirm(`⚠️ ATENÇÃO: Deletar PERMANENTEMENTE ${exchange.name}?\n\nEsta ação é IRREVERSÍVEL!`)) return;
    
    setLoading(true);
    try {
      await api.delete('/exchanges/delete', {
        data: {
          user_id: userId,
          exchange_id: exchange.id
        }
      });
      alert(`${exchange.name} deletada permanentemente!`);
      onUpdate();
    } catch (error) {
      alert(`Erro ao deletar: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleReconnect = async () => {
    setLoading(true);
    try {
      await api.post('/exchanges/reconnect', {
        user_id: userId,
        exchange_id: exchange.id
      });
      alert(`${exchange.name} reconectada com sucesso!`);
      onUpdate();
    } catch (error) {
      alert(`Erro ao reconectar: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="exchange-card">
      <h3>{exchange.name}</h3>
      <span className={exchange.is_active ? 'status-active' : 'status-inactive'}>
        {exchange.is_active ? '✅ Conectada' : '⏸️ Desconectada'}
      </span>

      <div className="actions">
        {exchange.is_active ? (
          <>
            <button onClick={handleDisconnect} disabled={loading}>
              🔌 Desconectar
            </button>
            <button onClick={handleDelete} disabled={loading} className="danger">
              🗑️ Deletar
            </button>
          </>
        ) : (
          <>
            <button onClick={handleReconnect} disabled={loading}>
              🔄 Reconectar
            </button>
            <button onClick={handleDelete} disabled={loading} className="danger">
              🗑️ Deletar
            </button>
          </>
        )}
      </div>
    </div>
  );
}
```

---

### **curl Examples:**

```bash
# 1. Desconectar MEXC
curl -X POST http://localhost:5000/api/v1/exchanges/disconnect \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "charles_test_user",
    "exchange_id": "693481148b0a41e8b6acb07b"
  }'

# Response:
# {
#   "success": true,
#   "message": "MEXC disconnected successfully",
#   "exchange": {
#     "id": "693481148b0a41e8b6acb07b",
#     "name": "MEXC",
#     "is_active": false
#   }
# }


# 2. Deletar MEXC (IRREVERSÍVEL)
curl -X DELETE http://localhost:5000/api/v1/exchanges/delete \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "charles_test_user",
    "exchange_id": "693481148b0a41e8b6acb07b"
  }'

# Response:
# {
#   "success": true,
#   "message": "MEXC deleted permanently",
#   "warning": "This action is irreversible. The exchange connection has been removed."
# }


# 3. Reconectar MEXC
curl -X POST http://localhost:5000/api/v1/exchanges/reconnect \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "charles_test_user",
    "exchange_id": "693481148b0a41e8b6acb07b"
  }'

# Response:
# {
#   "success": true,
#   "message": "MEXC reconnected successfully",
#   "exchange": {
#     "id": "693481148b0a41e8b6acb07b",
#     "name": "MEXC",
#     "is_active": true
#   }
# }
```

---

## 🔄 Fluxo de Estados

```
┌─────────────┐
│  Conectada  │ (is_active: true)
│   ✅ Ativa  │
└──────┬──────┘
       │
       │ POST /disconnect
       ▼
┌─────────────┐
│Desconectada │ (is_active: false)
│  ⏸️ Pausada  │
└──────┬──────┘
       │
       ├─── POST /reconnect ───► Volta para "Conectada"
       │
       └─── DELETE /delete ────► 🗑️ REMOVIDA PERMANENTEMENTE
```

---

## 📝 Estrutura do MongoDB

### **Antes de desconectar:**
```json
{
  "user_id": "charles_test_user",
  "exchanges": [
    {
      "exchange_id": ObjectId("693481148b0a41e8b6acb07b"),
      "api_key_encrypted": "...",
      "api_secret_encrypted": "...",
      "is_active": true,
      "linked_at": "2024-12-13T10:00:00Z",
      "updated_at": "2024-12-13T10:00:00Z"
    }
  ]
}
```

### **Após desconectar:**
```json
{
  "user_id": "charles_test_user",
  "exchanges": [
    {
      "exchange_id": ObjectId("693481148b0a41e8b6acb07b"),
      "api_key_encrypted": "...",  // ✅ Mantido
      "api_secret_encrypted": "...",  // ✅ Mantido
      "is_active": false,  // ⬅️ MUDOU
      "linked_at": "2024-12-13T10:00:00Z",
      "disconnected_at": "2024-12-13T15:30:00Z",  // ⬅️ NOVO
      "updated_at": "2024-12-13T15:30:00Z"
    }
  ]
}
```

### **Após deletar:**
```json
{
  "user_id": "charles_test_user",
  "exchanges": []  // ⬅️ ARRAY VAZIO - Exchange removida!
}
```

---

## ⚠️ Avisos Importantes

### **Disconnect:**
- ✅ Mantém dados criptografados
- ✅ Pode ser desfeito com `/reconnect`
- ✅ Exchange não aparece em `/balances`
- ✅ Recomendado para pausas temporárias

### **Delete:**
- ❌ **IRREVERSÍVEL** - não pode ser desfeito
- ❌ Remove API Key e Secret criptografados
- ❌ Remove histórico de conexão
- ⚠️ Use apenas quando tiver certeza absoluta
- ⚠️ Usuário precisará fazer `/link` novamente para reconectar

---

## 🎯 Casos de Uso

| Situação | Ação Recomendada |
|----------|------------------|
| Pausar trading temporariamente | ✅ **Disconnect** |
| Trocar API keys | ❌ **Delete** + novo `/link` |
| Testar sem uma exchange | ✅ **Disconnect** |
| Remover exchange definitivamente | ❌ **Delete** |
| Desabilitar temporariamente | ✅ **Disconnect** |
| Usuário vendeu todos os ativos | ❌ **Delete** (opcional) |

---

## ✅ Checklist de Implementação

- [x] Endpoint `/disconnect` (soft delete)
- [x] Endpoint `/delete` (hard delete)
- [x] Endpoint `/reconnect` (reativar)
- [x] Validação de `user_id` e `exchange_id`
- [x] Logs de auditoria
- [x] Mensagens de erro descritivas
- [x] Timestamps (`disconnected_at`, `reconnected_at`)
- [x] Documentação completa
- [x] Exemplos em JavaScript, React e curl

---

**🎉 Pronto para uso!**
