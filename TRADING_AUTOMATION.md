# 🤖 Sistema de Trading Automatizado

## Visão Geral

Sistema completo de trading automatizado multi-exchange com estratégias configuráveis, execução automática de ordens e rastreamento de posições com P&L.

## 🎯 Funcionalidades

### 1. **Estratégias de Trading**
- ✅ Configuração por exchange e token
- ✅ Take Profit % (venda com lucro)
- ✅ Stop Loss % (venda para limitar perda)
- ✅ Buy Dip % (compra na queda)
- ✅ Ativação/desativação individual
- ✅ Rastreamento de execuções

### 2. **Rastreamento de Posições**
- ✅ Preço de entrada (weighted average)
- ✅ Histórico de compras e vendas
- ✅ Cálculo automático de P&L
- ✅ Sincronização com saldos atuais

### 3. **Execução Automática**
- ✅ Worker bot rodando em background
- ✅ Verificação periódica (default: 5 min)
- ✅ Ordens market e limit
- ✅ Modo DRY-RUN para testes

### 4. **Notificações**
- ✅ Execução de estratégias
- ✅ Falhas em ordens
- ✅ Criação de estratégias
- ✅ Armazenamento em MongoDB

---

## 📋 Fluxo de Funcionamento

### 1. Criação de Estratégia

```http
POST /api/v1/strategies
{
  "user_id": "user123",
  "exchange_id": "65abc...",
  "token": "BTC",
  "rules": {
    "take_profit_percent": 5.0,   // Vende quando subir 5%
    "stop_loss_percent": 2.0,     // Vende quando cair 2%
    "buy_dip_percent": 3.0        // Compra quando cair 3%
  },
  "is_active": true
}
```

### 2. Sincronização de Posição

Sistema cria automaticamente uma posição rastreando o preço de entrada:

```javascript
// Se você comprou 0.5 BTC a $45,000
{
  "token": "BTC",
  "amount": 0.5,
  "entry_price": 45000.0,
  "total_invested": 22500.0,
  "purchases": [{
    "date": "2024-01-15T10:30:00Z",
    "amount": 0.5,
    "price": 45000.0,
    "total_cost": 22500.0
  }]
}
```

### 3. Strategy Worker Monitoramento

O worker roda automaticamente a cada 5 minutos:

```
1. Busca todas as estratégias ativas
2. Para cada estratégia:
   a) Busca posição (entry_price)
   b) Busca preço atual
   c) Verifica gatilhos:
      - Take Profit: current_price >= entry_price * (1 + take_profit_percent/100)
      - Stop Loss: current_price <= entry_price * (1 - stop_loss_percent/100)
      - Buy Dip: current_price <= entry_price * (1 - buy_dip_percent/100)
   d) Se gatilho acionado: executa ordem
   e) Atualiza posição
   f) Envia notificação
```

### 4. Exemplo Prático

**Configuração:**
- Token: BTC
- Entry Price: $45,000
- Take Profit: 5% → Vende a $47,250
- Stop Loss: 2% → Vende a $44,100
- Buy Dip: 3% → Compra a $43,650

**Cenário 1 - Take Profit:**
```
Preço atual: $47,500
✅ Gatilho: TAKE_PROFIT (5.5% acima do entry)
🔴 Ação: SELL 0.5 BTC
💰 Lucro: $1,250 (5.5%)
```

**Cenário 2 - Stop Loss:**
```
Preço atual: $43,900
⚠️ Gatilho: STOP_LOSS (-2.4% abaixo do entry)
🔴 Ação: SELL 0.5 BTC
📉 Prejuízo: -$550 (-2.4%)
```

---

## 🔧 Configuração

### Variáveis de Ambiente

```bash
# MongoDB
MONGODB_URI=mongodb://localhost:27017/
MONGODB_DATABASE=MultExchange

# Strategy Worker
STRATEGY_DRY_RUN=true          # true = simula ordens, false = executa real
STRATEGY_CHECK_INTERVAL=5      # Minutos entre verificações

# Flask
PORT=5000
FLASK_ENV=development
```

### Modo DRY-RUN (Recomendado para início)

Por padrão, o sistema roda em **DRY-RUN MODE**:
- ✅ Verifica estratégias normalmente
- ✅ Detecta gatilhos
- ✅ Simula ordens SEM executar
- ✅ Cria notificações
- ✅ Logs completos de debug

Para ativar ordens reais:
```bash
STRATEGY_DRY_RUN=false
```

---

## 📡 API Endpoints

### Estratégias

```http
# Criar estratégia
POST /api/v1/strategies

# Listar estratégias
GET /api/v1/strategies?user_id=user123&is_active=true

# Detalhes da estratégia
GET /api/v1/strategies/:id

# Atualizar estratégia
PUT /api/v1/strategies/:id

# Deletar estratégia
DELETE /api/v1/strategies/:id

# Verificar gatilho manualmente
POST /api/v1/strategies/:id/check
{
  "current_price": 47500,
  "entry_price": 45000
}
```

### Posições

```http
# Listar posições
GET /api/v1/positions?user_id=user123&exchange_id=...&token=BTC

# Detalhes da posição
GET /api/v1/positions/:id

# Sincronizar posições
POST /api/v1/positions/sync
{
  "user_id": "user123",
  "exchange_id": "...",  // opcional
  "token": "BTC"         // opcional
}

# Histórico de compras/vendas
GET /api/v1/positions/:id/history
```

### Notificações

```http
# Listar notificações
GET /api/v1/notifications?user_id=user123&unread_only=true

# Marcar como lida
PUT /api/v1/notifications/:id/read

# Marcar todas como lidas
PUT /api/v1/notifications/read-all
{
  "user_id": "user123"
}

# Deletar notificação
DELETE /api/v1/notifications/:id
```

### Ordens Manuais (para testes)

```http
# Executar compra
POST /api/v1/orders/buy
{
  "user_id": "user123",
  "exchange_id": "...",
  "token": "BTC",
  "amount": 0.5,
  "order_type": "market"  // ou "limit"
  // "price": 45000  (se limit)
}

# Executar venda
POST /api/v1/orders/sell
{
  "user_id": "user123",
  "exchange_id": "...",
  "token": "BTC",
  "amount": 0.5,
  "order_type": "market"
}
```

---

## 🚀 Como Usar

### 1. Inicie o Sistema

```bash
python run.py
```

Você verá:
```
✅ Scheduler started - Balance snapshots every 4 hours
✅ Strategy Worker started in DRY-RUN mode (checking every 5 minutes)
```

### 2. Crie uma Estratégia

```bash
curl -X POST http://localhost:5000/api/v1/strategies \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "exchange_id": "65abc...",
    "token": "BTC",
    "rules": {
      "take_profit_percent": 5.0,
      "stop_loss_percent": 2.0,
      "buy_dip_percent": 3.0
    },
    "is_active": true
  }'
```

### 3. Sincronize Posições

```bash
curl -X POST http://localhost:5000/api/v1/positions/sync \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123"
  }'
```

### 4. Monitore Logs

```
🔍 Checking all active strategies...
Found 1 active strategies to check
🎯 STRATEGY TRIGGERED! User: user123, Token: BTC, Action: SELL, Reason: TAKE_PROFIT
🧪 DRY-RUN: Would execute MARKET SELL: 0.5 BTC
✅ Order executed successfully! Order ID: DRY-1234...
📬 Notification created: strategy_executed for user user123
```

### 5. Verifique Notificações

```bash
curl http://localhost:5000/api/v1/notifications?user_id=user123&unread_only=true
```

---

## 📊 Cálculos de P&L

### Average Cost Basis (múltiplas compras)

```javascript
// Compra 1: 0.3 BTC a $45,000 = $13,500
// Compra 2: 0.2 BTC a $46,000 = $9,200
// Total: 0.5 BTC por $22,700

entry_price = (13500 + 9200) / (0.3 + 0.2) = $45,400
```

### Profit/Loss na Venda

```javascript
// Venda: 0.3 BTC a $47,000
total_received = 0.3 * 47000 = $14,100
cost_basis = 0.3 * 45400 = $13,620
profit = 14100 - 13620 = $480
profit_percent = (480 / 13620) * 100 = 3.52%
```

---

## 🛡️ Segurança

- ✅ Credenciais criptografadas no MongoDB
- ✅ Modo DRY-RUN por padrão
- ✅ Logs detalhados de todas as operações
- ✅ Validação de saldo antes de executar ordens
- ✅ Tratamento de erros CCXT (InsufficientFunds, InvalidOrder)

---

## 🔄 Próximos Passos

1. **Teste em DRY-RUN:** Deixe rodando por alguns dias
2. **Verifique Logs:** Confirme que gatilhos estão corretos
3. **Ajuste Percentuais:** Refine take_profit/stop_loss
4. **Ative LIVE:** Mude `STRATEGY_DRY_RUN=false`
5. **Monitore Notificações:** Configure webhooks/email

---

## ⚠️ Avisos Importantes

1. **Risco Financeiro:** Trading automatizado envolve risco de perda
2. **Teste Primeiro:** Sempre use DRY-RUN antes de ativar modo LIVE
3. **Monitore Saldo:** Verifique se há saldo suficiente para ordens
4. **Taxas de Exchange:** Considere taxas de trading nos cálculos
5. **Rate Limits:** CCXT possui rate limiting para evitar ban
6. **Volatilidade:** Crypto é volátil, ajuste stop loss adequadamente

---

## 📞 Suporte

- Logs: `logs/app.log`
- MongoDB: Collection `notifications` para histórico
- Health Check: `GET /health`
- Scheduler Status: `GET /api/v1/scheduler/status`

---

## 📈 Estrutura de Dados

### Strategy Document
```javascript
{
  "_id": ObjectId,
  "user_id": "user123",
  "exchange_id": ObjectId,
  "exchange_name": "Binance",
  "token": "BTC",
  "rules": {
    "take_profit_percent": 5.0,
    "stop_loss_percent": 2.0,
    "buy_dip_percent": 3.0
  },
  "is_active": true,
  "execution_count": 0,
  "last_execution": null,
  "created_at": ISODate,
  "updated_at": ISODate
}
```

### Position Document
```javascript
{
  "_id": ObjectId,
  "user_id": "user123",
  "exchange_id": ObjectId,
  "exchange_name": "Binance",
  "token": "BTC",
  "amount": 0.5,
  "entry_price": 45000.0,
  "total_invested": 22500.0,
  "is_active": true,
  "purchases": [
    {
      "date": ISODate,
      "amount": 0.5,
      "price": 45000.0,
      "total_cost": 22500.0,
      "order_id": "12345"
    }
  ],
  "sales": [],
  "created_at": ISODate,
  "updated_at": ISODate
}
```

### Notification Document
```javascript
{
  "_id": ObjectId,
  "user_id": "user123",
  "type": "strategy_executed",
  "title": "🔴 Estratégia Executada - BTC",
  "message": "Take Profit atingido! 🎯\n\nToken: BTC\nAção: SELL...",
  "data": {
    "strategy_id": "...",
    "order_id": "...",
    "action": "SELL",
    "reason": "TAKE_PROFIT"
  },
  "is_read": false,
  "created_at": ISODate
}
```

---

**🚀 Sistema pronto para uso! Comece em DRY-RUN e bom trading!**
