# Endpoint de Monitoramento de Ordens - Exemplos de Uso

## 📊 POST /api/v1/orders/monitor

Força uma atualização manual do status das ordens (além do monitoramento automático a cada 30s).

### Funcionalidades

- ✅ Monitorar **ordem específica** por ID
- ✅ Monitorar **todas as ordens** de um usuário
- ✅ Monitorar **todas as ordens** de uma exchange
- ✅ Monitorar **ordens de um usuário em uma exchange específica**
- ✅ Monitorar **todas as ordens abertas** do sistema

---

## 1️⃣ Monitorar Ordem Específica

```bash
curl -X POST http://localhost:5000/api/v1/orders/monitor \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "67891234abcdef567890"
  }'
```

**Resposta:**
```json
{
  "success": true,
  "order_id": "67891234abcdef567890",
  "old_status": "open",
  "new_status": "filled",
  "filled": 0.001,
  "remaining": 0,
  "updated": true
}
```

---

## 2️⃣ Monitorar Todas as Ordens de um Usuário

```bash
curl -X POST http://localhost:5000/api/v1/orders/monitor \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "charles_test_user"
  }'
```

**Resposta:**
```json
{
  "success": true,
  "total": 5,
  "updated": 2,
  "closed": 1,
  "errors": 0,
  "orders": [
    {
      "order_id": "67891234abcdef567890",
      "symbol": "BTC/USDT",
      "status": "filled",
      "updated": true
    },
    {
      "order_id": "67891234abcdef567891",
      "symbol": "ETH/USDT",
      "status": "partially_filled",
      "updated": true
    },
    {
      "order_id": "67891234abcdef567892",
      "symbol": "SOL/USDT",
      "status": "open",
      "updated": false
    }
  ]
}
```

---

## 3️⃣ Monitorar Todas as Ordens de uma Exchange

```bash
curl -X POST http://localhost:5000/api/v1/orders/monitor \
  -H "Content-Type: application/json" \
  -d '{
    "exchange_id": "693481148b0a41e8b6acb079"
  }'
```

**Resposta:**
```json
{
  "success": true,
  "total": 8,
  "updated": 3,
  "closed": 2,
  "errors": 0,
  "orders": [
    {
      "order_id": "...",
      "symbol": "BTC/USDT",
      "status": "filled",
      "updated": true
    }
  ]
}
```

---

## 4️⃣ Monitorar Ordens de um Usuário em uma Exchange Específica

```bash
curl -X POST http://localhost:5000/api/v1/orders/monitor \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "charles_test_user",
    "exchange_id": "693481148b0a41e8b6acb079"
  }'
```

**Resposta:**
```json
{
  "success": true,
  "total": 3,
  "updated": 1,
  "closed": 1,
  "errors": 0,
  "orders": [
    {
      "order_id": "67891234abcdef567890",
      "symbol": "BTC/USDT",
      "status": "filled",
      "updated": true
    },
    {
      "order_id": "67891234abcdef567891",
      "symbol": "ETH/USDT",
      "status": "open",
      "updated": false
    }
  ]
}
```

---

## 5️⃣ Monitorar Todas as Ordens Abertas do Sistema

```bash
curl -X POST http://localhost:5000/api/v1/orders/monitor \
  -H "Content-Type: application/json" \
  -d '{}'
```

**Resposta:**
```json
{
  "success": true,
  "total": 15,
  "updated": 5,
  "closed": 3,
  "errors": 0,
  "orders": [ ... ]
}
```

---

## 📊 GET /api/v1/orders/status/:order_id

Busca o status atual de uma ordem específica no banco de dados.

### Sem Refresh (Dados do Banco)

```bash
curl http://localhost:5000/api/v1/orders/status/67891234abcdef567890
```

**Resposta:**
```json
{
  "success": true,
  "order": {
    "order_id": "67891234abcdef567890",
    "exchange_order_id": "12345678",
    "exchange_name": "Binance",
    "symbol": "BTC/USDT",
    "side": "buy",
    "type": "limit",
    "amount": 0.001,
    "price": 50000.00,
    "filled": 0.0005,
    "remaining": 0.0005,
    "status": "partially_filled",
    "created_at": "2025-12-22T18:00:00.000Z",
    "updated_at": "2025-12-22T18:05:30.000Z",
    "last_checked_at": "2025-12-22T18:10:00.000Z"
  }
}
```

### Com Refresh (Busca na Exchange)

```bash
curl "http://localhost:5000/api/v1/orders/status/67891234abcdef567890?refresh=true"
```

Isso força uma consulta na exchange **antes** de retornar os dados.

---

## 🔄 Fluxo Típico de Uso

### Cenário 1: Criar e Acompanhar Ordem

```bash
# 1. Criar ordem
ORDER_RESPONSE=$(curl -X POST http://localhost:5000/api/v1/orders/create \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "charles_test_user",
    "exchange_id": "693481148b0a41e8b6acb079",
    "symbol": "BTC/USDT",
    "side": "buy",
    "type": "limit",
    "amount": 0.001,
    "price": 50000.00
  }')

ORDER_ID=$(echo $ORDER_RESPONSE | jq -r '.order_id')
echo "✅ Order created: $ORDER_ID"

# 2. Aguardar alguns segundos
sleep 5

# 3. Verificar status (forçando refresh da exchange)
curl "http://localhost:5000/api/v1/orders/status/$ORDER_ID?refresh=true"

# 4. Se não completada, monitorar periodicamente
while true; do
  STATUS=$(curl -s "http://localhost:5000/api/v1/orders/status/$ORDER_ID" | jq -r '.order.status')
  echo "Status: $STATUS"
  
  if [ "$STATUS" = "filled" ] || [ "$STATUS" = "closed" ]; then
    echo "✅ Order completed!"
    break
  fi
  
  if [ "$STATUS" = "canceled" ] || [ "$STATUS" = "expired" ]; then
    echo "❌ Order not executed"
    break
  fi
  
  sleep 10
done
```

### Cenário 2: Monitorar Ordens de uma Exchange

```bash
# Monitorar todas as ordens abertas da Binance
curl -X POST http://localhost:5000/api/v1/orders/monitor \
  -H "Content-Type: application/json" \
  -d '{
    "exchange_id": "693481148b0a41e8b6acb079"
  }'
```

### Cenário 3: Dashboard de Ordens Ativas

```bash
# 1. Listar ordens abertas
curl "http://localhost:5000/api/v1/orders/list?user_id=charles_test_user&status=open"

# 2. Forçar atualização de todas
curl -X POST http://localhost:5000/api/v1/orders/monitor \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "charles_test_user"
  }'

# 3. Listar novamente para ver mudanças
curl "http://localhost:5000/api/v1/orders/list?user_id=charles_test_user&status=open"
```

---

## ⚙️ Comparação: Monitoramento Automático vs Manual

| Característica | Automático (Background) | Manual (Endpoint) |
|----------------|------------------------|-------------------|
| **Frequência** | A cada 30 segundos | Sob demanda |
| **Escopo** | Todas as ordens abertas | Filtrado (user/exchange/order) |
| **Uso** | Sempre ativo | Chamado quando necessário |
| **Performance** | Rate limited (0.5s entre ordens) | Imediato |
| **Ideal para** | Manter sistema atualizado | Atualizações urgentes |

---

## 💡 Casos de Uso

### 1. **Interface de Trading em Tempo Real**
- Usuário cria ordem
- Frontend chama `/orders/monitor` com `order_id`
- Atualiza UI com status em tempo real

### 2. **Dashboard de Exchange Manager**
- Admin quer ver todas as ordens de uma exchange
- Chama `/orders/monitor` com `exchange_id`
- Vê resumo de quantas foram atualizadas/completadas

### 3. **Relatório de Usuário**
- Sistema gera relatório de ordens do usuário
- Chama `/orders/monitor` com `user_id`
- Garante dados mais recentes antes de gerar relatório

### 4. **Webhook/Alert System**
- Sistema externo precisa verificar ordem específica
- Chama `/orders/status/:id?refresh=true`
- Obtém status atualizado da exchange

---

## 🚀 Exemplo Completo em JavaScript

```javascript
// Criar ordem e monitorar até conclusão
async function createAndMonitorOrder(orderData) {
  // 1. Criar ordem
  const createResponse = await fetch('http://localhost:5000/api/v1/orders/create', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(orderData)
  });
  
  const order = await createResponse.json();
  
  if (!order.success) {
    throw new Error(order.error);
  }
  
  console.log('✅ Order created:', order.order_id);
  
  // 2. Monitorar até completar
  while (true) {
    // Aguardar 5 segundos
    await new Promise(resolve => setTimeout(resolve, 5000));
    
    // Verificar status
    const statusResponse = await fetch(
      `http://localhost:5000/api/v1/orders/status/${order.order_id}?refresh=true`
    );
    
    const status = await statusResponse.json();
    
    console.log(`📊 Status: ${status.order.status} (filled: ${status.order.filled})`);
    
    // Verificar se completou
    if (['filled', 'closed', 'canceled', 'expired'].includes(status.order.status)) {
      console.log(`✅ Order ${status.order.status}`);
      return status.order;
    }
  }
}

// Uso
const orderData = {
  user_id: 'charles_test_user',
  exchange_id: '693481148b0a41e8b6acb079',
  symbol: 'BTC/USDT',
  side: 'buy',
  type: 'limit',
  amount: 0.001,
  price: 50000.00
};

createAndMonitorOrder(orderData)
  .then(finalOrder => console.log('Final order:', finalOrder))
  .catch(err => console.error('Error:', err));
```

---

## 📝 Notas Importantes

1. **Rate Limiting**: O monitoramento manual respeita rate limits da exchange via CCXT

2. **Background vs Manual**: O monitoramento automático continua rodando a cada 30s independentemente das chamadas manuais

3. **Performance**: Para monitorar muitas ordens de uma vez, é mais eficiente usar filtros (user_id ou exchange_id) do que chamar ordem por ordem

4. **Caching**: O endpoint `/orders/status/:id` sem `refresh=true` retorna dados do banco (mais rápido), com `refresh=true` consulta a exchange (dados atualizados)

---

✅ **Sistema pronto para uso!** 🚀
