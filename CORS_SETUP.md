# 🔗 CORS Habilitado - Testando API do React

## ✅ Configuração Adicionada

```python
# src/api/main.py

from flask_cors import CORS

# Configura CORS para permitir chamadas do React app
CORS(app, resources={
    r"/api/*": {
        "origins": ["*"],  # Em produção, especifique os domínios
        "methods": ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True
    }
})
```

---

## 🧪 Testando do React App

### **1. Fetch API (Vanilla JavaScript)**

```javascript
// Exemplo: Buscar estratégias
async function getStrategies(userId) {
  try {
    const response = await fetch(
      `http://localhost:5000/api/v1/strategies?user_id=${userId}`,
      {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      }
    );

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    console.log('Strategies:', data);
    return data;
  } catch (error) {
    console.error('Error fetching strategies:', error);
    throw error;
  }
}

// Testar
getStrategies('charles_test_user');
```

---

### **2. Axios (React)**

```bash
# Instalar axios
npm install axios
```

```javascript
// services/api.js
import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:5000/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
});

// GET - Listar estratégias
export const getStrategies = async (userId) => {
  const response = await api.get('/strategies', {
    params: { user_id: userId }
  });
  return response.data;
};

// POST - Criar estratégia
export const createStrategy = async (data) => {
  const response = await api.post('/strategies', data);
  return response.data;
};

// PUT - Atualizar estratégia
export const updateStrategy = async (strategyId, data) => {
  const response = await api.put(`/strategies/${strategyId}`, data);
  return response.data;
};

// DELETE - Deletar estratégia
export const deleteStrategy = async (strategyId) => {
  const response = await api.delete(`/strategies/${strategyId}`);
  return response.data;
};

// PATCH - Pausar/Ativar estratégia
export const toggleStrategy = async (strategyId, isActive) => {
  const response = await api.patch(`/strategies/${strategyId}/toggle`, {
    is_active: isActive
  });
  return response.data;
};

export default api;
```

---

### **3. React Component Example**

```javascript
// components/StrategiesList.jsx
import React, { useState, useEffect } from 'react';
import { getStrategies, createStrategy, toggleStrategy } from '../services/api';

function StrategiesList() {
  const [strategies, setStrategies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Carregar estratégias ao montar
  useEffect(() => {
    loadStrategies();
  }, []);

  const loadStrategies = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const data = await getStrategies('charles_test_user');
      setStrategies(data.strategies || []);
    } catch (err) {
      setError(err.message);
      console.error('Error loading strategies:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateStrategy = async () => {
    try {
      const newStrategy = {
        user_id: 'charles_test_user',
        exchange_id: '693481148b0a41e8b6acb07b',
        token: 'DOGE',
        template: 'aggressive',
        is_active: true
      };

      await createStrategy(newStrategy);
      loadStrategies(); // Recarregar lista
      alert('Estratégia criada com sucesso!');
    } catch (err) {
      alert(`Erro ao criar estratégia: ${err.message}`);
    }
  };

  const handleToggle = async (strategyId, currentStatus) => {
    try {
      await toggleStrategy(strategyId, !currentStatus);
      loadStrategies(); // Recarregar lista
    } catch (err) {
      alert(`Erro ao atualizar status: ${err.message}`);
    }
  };

  if (loading) return <div>Carregando...</div>;
  if (error) return <div>Erro: {error}</div>;

  return (
    <div className="strategies-list">
      <h2>Minhas Estratégias</h2>
      <button onClick={handleCreateStrategy}>+ Nova Estratégia</button>

      {strategies.length === 0 ? (
        <p>Nenhuma estratégia encontrada</p>
      ) : (
        strategies.map(strategy => (
          <div key={strategy.id} className="strategy-card">
            <h3>{strategy.token} @ {strategy.exchange_name}</h3>
            <p>Status: {strategy.is_active ? '✅ Ativa' : '⏸️ Pausada'}</p>
            <p>PnL: ${strategy.execution_stats?.total_pnl_usd || 0}</p>
            <p>Win Rate: {strategy.performance?.win_rate || 0}%</p>
            
            <button onClick={() => handleToggle(strategy.id, strategy.is_active)}>
              {strategy.is_active ? 'Pausar' : 'Ativar'}
            </button>
          </div>
        ))
      )}
    </div>
  );
}

export default StrategiesList;
```

---

### **4. TypeScript + React Hook**

```typescript
// hooks/useStrategies.ts
import { useState, useEffect } from 'react';
import { getStrategies } from '../services/api';

interface Strategy {
  id: string;
  user_id: string;
  exchange_id: string;
  exchange_name: string;
  token: string;
  is_active: boolean;
  rules: any;
  execution_stats: any;
  performance: any;
}

export function useStrategies(userId: string) {
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadStrategies = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const data = await getStrategies(userId);
      setStrategies(data.strategies || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (userId) {
      loadStrategies();
    }
  }, [userId]);

  return {
    strategies,
    loading,
    error,
    refetch: loadStrategies
  };
}
```

```typescript
// Component usando o hook
import React from 'react';
import { useStrategies } from '../hooks/useStrategies';

function StrategiesPage() {
  const { strategies, loading, error, refetch } = useStrategies('charles_test_user');

  if (loading) return <div>Carregando...</div>;
  if (error) return <div>Erro: {error}</div>;

  return (
    <div>
      <h1>Estratégias</h1>
      <button onClick={refetch}>🔄 Atualizar</button>
      
      {strategies.map(strategy => (
        <div key={strategy.id}>
          <h3>{strategy.token}</h3>
          <p>Status: {strategy.is_active ? '✅' : '⏸️'}</p>
        </div>
      ))}
    </div>
  );
}
```

---

## 🧪 Teste Rápido no Console do Navegador

Abra o console do navegador (F12) e execute:

```javascript
// Teste 1: Health Check
fetch('http://localhost:5000/health')
  .then(r => r.json())
  .then(console.log);

// Teste 2: Listar Estratégias
fetch('http://localhost:5000/api/v1/strategies?user_id=charles_test_user')
  .then(r => r.json())
  .then(console.log);

// Teste 3: Criar Estratégia
fetch('http://localhost:5000/api/v1/strategies', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    user_id: 'charles_test_user',
    exchange_id: '693481148b0a41e8b6acb07b',
    token: 'DOGE',
    template: 'aggressive'
  })
})
  .then(r => r.json())
  .then(console.log);

// Teste 4: Buscar Dashboard
fetch('http://localhost:5000/api/v1/balances?user_id=charles_test_user')
  .then(r => r.json())
  .then(console.log);
```

---

## 🔒 Configuração de Segurança para Produção

Quando colocar em produção, **SEMPRE** especifique os domínios permitidos:

```python
# NÃO USE EM PRODUÇÃO:
"origins": ["*"]  # ❌ Permite qualquer origem

# USE EM PRODUÇÃO:
"origins": [
    "http://localhost:3000",           # Desenvolvimento local
    "http://localhost:3001",           # Desenvolvimento local (alt)
    "https://seu-app.vercel.app",      # Produção Vercel
    "https://seu-app.netlify.app",     # Produção Netlify
    "https://www.seu-dominio.com",     # Seu domínio
]  # ✅ Apenas origens específicas
```

---

## 📋 Variáveis de Ambiente Recomendadas

```bash
# .env
FLASK_ENV=development
API_PORT=5000

# CORS Origins (separar por vírgula)
CORS_ORIGINS=http://localhost:3000,http://localhost:3001,https://seu-app.com
```

```python
# Atualizar main.py para usar env var
import os

cors_origins = os.getenv('CORS_ORIGINS', '*').split(',')

CORS(app, resources={
    r"/api/*": {
        "origins": cors_origins,
        "methods": ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True
    }
})
```

---

## ✅ Checklist

- [x] flask-cors instalado
- [x] CORS configurado no main.py
- [x] Wildcard (*) para desenvolvimento
- [ ] Configurar origins específicas para produção
- [ ] Testar do React app
- [ ] Verificar headers no navegador (Network tab)

---

## 🐛 Troubleshooting

### **Erro: "CORS policy: No 'Access-Control-Allow-Origin'"**

**Solução:** Certifique-se que o servidor está rodando e CORS foi configurado.

```bash
# Reinicie o servidor
python3 run.py
```

### **Erro: "Network Error" ou "Failed to fetch"**

**Solução:** Verifique se a URL está correta e o servidor está rodando.

```bash
# Verifique se está rodando
curl http://localhost:5000/health
```

### **Erro: "Unexpected token < in JSON"**

**Solução:** A API retornou HTML ao invés de JSON (geralmente erro 404 ou 500).

```javascript
// Adicione tratamento de erro
const response = await fetch(url);
if (!response.ok) {
  const text = await response.text();
  console.error('Response:', text);
  throw new Error(`HTTP ${response.status}: ${text}`);
}
```

---

**🎉 CORS configurado e pronto para testes do React app!**
