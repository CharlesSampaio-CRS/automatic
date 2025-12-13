# 📊 Ordenação de Saldos no Endpoint `/api/v1/balances`

## ✅ Ordenação Implementada

O endpoint `/api/v1/balances` agora retorna os dados **ordenados por valor em USD (do maior para o menor)**:

---

### **1. Exchanges Ordenadas por Total USD**

As exchanges são ordenadas pela maior para a menor:

```json
{
  "exchanges": [
    {
      "exchange_id": "...",
      "name": "Binance",
      "total_usd": "5831.90",  // ⬅️ Maior saldo
      "tokens": { ... }
    },
    {
      "exchange_id": "...",
      "name": "Bybit",
      "total_usd": "4831.90",  // ⬅️ Segundo maior
      "tokens": { ... }
    },
    {
      "exchange_id": "...",
      "name": "MEXC",
      "total_usd": "150.00",   // ⬅️ Menor saldo
      "tokens": { ... }
    }
  ]
}
```

---

### **2. Tokens Ordenados por Valor USD (Dentro de Cada Exchange)**

Dentro de cada exchange, os tokens são ordenados por valor USD:

**✅ Tokens com valor > $0 aparecem primeiro (do maior para o menor)**  
**✅ Tokens com valor = $0 aparecem no final**

```json
{
  "name": "MEXC",
  "total_usd": "162.47",
  "tokens": {
    "USDT": {
      "amount": "91.36",
      "price_usd": "1.00",
      "value_usd": "91.36"         // ⬅️ 1º Maior valor
    },
    "MON": {
      "amount": "3012.03",
      "price_usd": "0.0235600000",
      "value_usd": "70.96"         // ⬅️ 2º Maior valor
    },
    "MX": {
      "amount": "0.0702236900",
      "price_usd": "2.16",
      "value_usd": "0.15"          // ⬅️ 3º Menor valor (mas > $0)
    },
    "ICG": {
      "amount": "12069255.00",
      "price_usd": "0.0000000000",
      "value_usd": "0.00"          // ⬅️ 4º Sem valor (aparece por último)
    }
  }
}
```

---

## 🎯 Benefícios

### **Para o Frontend:**
✅ **Visualização Clara**: Principais ativos aparecem primeiro  
✅ **Melhor UX**: Usuário vê imediatamente seus maiores investimentos  
✅ **Performance**: Não precisa reordenar no frontend  
✅ **Consistência**: Sempre ordenado da mesma forma  
✅ **Tokens sem valor no final**: Dust/tokens sem preço não poluem a visualização principal

### **Para o Usuário:**
✅ **Foco no Importante**: Maiores valores no topo  
✅ **Decisões Rápidas**: Identifica rapidamente principais holdings  
✅ **Clareza Visual**: Portfolio organizado por relevância  
✅ **Limpeza**: Tokens "mortos" ou sem valor não atrapalham a visualização  

---

## 🧪 Testando a Ordenação

### **Exemplo de Chamada:**

```bash
curl "http://localhost:5000/api/v1/balances?user_id=charles_test_user"
```

### **Response (Ordenado):**

```json
{
  "user_id": "charles_test_user",
  "timestamp": "2024-12-13T18:30:00Z",
  "summary": {
    "total_usd": "10663.80",
    "exchanges_count": 2
  },
  "exchanges": [
    {
      "exchange_id": "693481148b0a41e8b6acb07b",
      "name": "Binance",
      "success": true,
      "total_usd": "5831.90",
      "tokens": {
        "BTC": {
          "amount": "0.15000000",
          "price_usd": "38879.33",
          "value_usd": "5831.90"
        },
        "ETH": {
          "amount": "1.50000000",
          "price_usd": "2100.50",
          "value_usd": "3150.75"
        },
        "USDT": {
          "amount": "850.00000000",
          "price_usd": "1.00",
          "value_usd": "850.00"
        }
      }
    },
    {
      "exchange_id": "693481148b0a41e8b6acb07c",
      "name": "Bybit",
      "success": true,
      "total_usd": "4831.90",
      "tokens": {
        "SOL": {
          "amount": "45.00000000",
          "price_usd": "95.50",
          "value_usd": "4297.50"
        },
        "USDT": {
          "amount": "534.40000000",
          "price_usd": "1.00",
          "value_usd": "534.40"
        }
      }
    }
  ],
  "meta": {
    "from_cache": false
  }
}
```

---

## 📱 Exemplo de Uso no Frontend

### **React Component:**

```typescript
import React, { useEffect, useState } from 'react';
import api from '../services/api';

function PortfolioBalances() {
  const [balances, setBalances] = useState(null);

  useEffect(() => {
    loadBalances();
  }, []);

  const loadBalances = async () => {
    const response = await api.get('/balances', {
      params: { user_id: 'charles_test_user' }
    });
    setBalances(response.data);
  };

  if (!balances) return <div>Carregando...</div>;

  return (
    <div className="portfolio">
      <h2>Portfolio Total: ${balances.summary.total_usd}</h2>
      
      {balances.exchanges.map(exchange => (
        <div key={exchange.exchange_id} className="exchange-card">
          <h3>{exchange.name}</h3>
          <p>Total: ${exchange.total_usd}</p>
          
          <table>
            <thead>
              <tr>
                <th>Token</th>
                <th>Quantidade</th>
                <th>Preço</th>
                <th>Valor USD</th>
              </tr>
            </thead>
            <tbody>
              {/* ✅ Tokens já vêm ordenados do maior para o menor */}
              {Object.entries(exchange.tokens).map(([token, info]) => (
                <tr key={token}>
                  <td>{token}</td>
                  <td>{info.amount}</td>
                  <td>${info.price_usd}</td>
                  <td>${info.value_usd}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}
    </div>
  );
}
```

---

## 🔍 Detalhes Técnicos

### **Ordenação de Exchanges:**

```python
# src/services/balance_service.py (linha ~559)

exchanges_summary = sorted(
    exchanges_summary,
    key=lambda x: float(x.get('total_usd', '0.0')) if x.get('success') else 0,
    reverse=True  # Maior para menor
)
```

### **Ordenação de Tokens:**

```python
# src/services/balance_service.py (linha ~520)

# 1. Calcula valor REAL (antes da formatação)
real_value = amount_val * price_val

# 2. Ordena por valor REAL (não formatado)
tokens_with_values.sort(
    key=lambda x: x['real_value'],
    reverse=True  # Maior para menor
)

# 3. Depois formata para exibição
token_info = {
    'amount': format_amount(amount_val),
    'price_usd': format_price(price_val),
    'value_usd': format_usd(value_val)
}
```

**Por que usar `real_value` ao invés de `value_usd` formatado?**

❌ **Problema com valor formatado:**
```python
# Valores muito pequenos são arredondados para "0.00"
REKTCOIN: price=$0.0000004282, amount=0.9661
value_usd formatado = "0.00"  # ❌ Perde precisão!
```

✅ **Solução com valor real:**
```python
# Mantém precisão para ordenação
REKTCOIN: real_value = 0.0000004136
# Ordena corretamente: USDT ($91.36) > MON ($70.96) > MX ($0.15) > REKTCOIN ($0.0000004136) > ICG ($0)
```

**Resultado:**
1. USDT ($91.36) - maior valor
2. MON ($70.96) 
3. MX ($0.15)
4. REKTCOIN ($0.00 exibido, mas real_value = $0.0000004136) - tem valor, só é muito pequeno
5. ICG ($0.00 exibido, real_value = $0) - sem valor real

---

## 📊 Variações com Price Changes

Se você incluir `include_changes=true`, os tokens também incluem variações de preço:

```bash
curl "http://localhost:5000/api/v1/balances?user_id=charles_test_user&include_changes=true"
```

**Response:**

```json
{
  "tokens": {
    "BTC": {
      "amount": "0.15000000",
      "price_usd": "38879.33",
      "value_usd": "5831.90",
      "change_1h": 0.5,      // ⬅️ +0.5% na última hora
      "change_4h": 1.2,      // ⬅️ +1.2% nas últimas 4 horas
      "change_24h": -2.3     // ⬅️ -2.3% nas últimas 24 horas
    }
  }
}
```

---

## 🔍 Filtrando Tokens com Valor $0 (Opcional no Frontend)

Se você quiser **ocultar** tokens sem valor no frontend:

```typescript
function PortfolioBalances() {
  const [showZeroBalance, setShowZeroBalance] = useState(false);

  const filterTokens = (tokens) => {
    if (showZeroBalance) {
      return tokens; // Mostra todos
    }
    
    // Filtra apenas tokens com valor > $0
    return Object.fromEntries(
      Object.entries(tokens).filter(([_, info]) => 
        parseFloat(info.value_usd) > 0
      )
    );
  };

  return (
    <div>
      <label>
        <input 
          type="checkbox" 
          checked={showZeroBalance}
          onChange={(e) => setShowZeroBalance(e.target.checked)}
        />
        Mostrar tokens com valor $0
      </label>

      {balances.exchanges.map(exchange => (
        <div key={exchange.exchange_id}>
          <h3>{exchange.name}</h3>
          {Object.entries(filterTokens(exchange.tokens)).map(([token, info]) => (
            <div key={token}>
              {token}: ${info.value_usd}
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}
```

---

## ✅ Checklist

- [x] Exchanges ordenadas por total_usd (maior → menor)
- [x] Tokens ordenados por value_usd (maior → menor) dentro de cada exchange
- [x] Tokens com valor > $0 aparecem primeiro
- [x] Tokens com valor = $0 aparecem no final (não poluem a visualização principal)
- [x] Valores formatados corretamente (8 casas decimais para quantidade, 2 para USD)
- [x] Price changes incluídos quando solicitado
- [x] Documentação completa com exemplos

---

## 📊 Exemplo Real do Seu Retorno

```json
{
  "exchanges": [
    {
      "name": "MEXC",
      "total_usd": "162.47",
      "tokens": {
        "USDT": { "value_usd": "91.36" },   // ✅ Maior
        "MON": { "value_usd": "70.96" },    // ✅ Segundo
        "MX": { "value_usd": "0.15" },      // ✅ Terceiro
        "ICG": { "value_usd": "0.00" }      // ⬇️ Sem valor (por último)
      }
    },
    {
      "name": "NovaDAX",
      "total_usd": "6.53",
      "tokens": {
        "LUNC": { "value_usd": "6.53" },    // ✅ Único com valor
        "AIBB": { "value_usd": "0.00" },    // ⬇️ Sem valor
        "AIDOGE": { "value_usd": "0.00" },  // ⬇️ Sem valor
        "BABYDOGE2": { "value_usd": "0.00" }// ⬇️ Sem valor
      }
    },
    {
      "name": "Binance",
      "total_usd": "0.00",
      "tokens": {}                          // ⬇️ Sem tokens
    }
  ]
}
```

**✅ Ordenação perfeita:**
1. Exchanges por total (MEXC → NovaDAX → Binance)
2. Tokens por valor (tokens com $ > 0 primeiro, depois $0)
3. Dentro de cada grupo, do maior para o menor

---

**🎉 Pronto! Agora o endpoint retorna os dados sempre ordenados do maior para o menor saldo, com tokens sem valor no final!**
