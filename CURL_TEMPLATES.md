# 🚀 CURLS PRONTOS - Templates de Estratégia

## 📋 Passo 1: Pegar ID da Exchange MEXC

```bash
curl http://localhost:5000/api/v1/exchanges | jq '.exchanges[] | select(.nome=="MEXC") | {id: ._id, nome: .nome}'
```

**Copie o `id` retornado e substitua `<MEXC_ID>` nos comandos abaixo!**

---

## 1️⃣ ESTRATÉGIA SIMPLE (Básica)

**Características:**
- ✅ Take Profit: 5% (vende 100%)
- ✅ Stop Loss: 2%
- ✅ Buy Dip: 3%
- ❌ Trailing Stop
- ❌ DCA
- ❌ Cooldown
- ❌ Max Loss Diário

### REKTCOIN (MEXC)
```bash
curl -X POST http://localhost:5000/api/v1/strategies \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "exchange_id": "<MEXC_ID>",
    "token": "REKTCOIN",
    "template": "simple"
  }'
```

---

## 2️⃣ ESTRATÉGIA CONSERVATIVE (Proteção Máxima)

**Características:**
- ✅ Take Profit Duplo:
  - 2% → vende 50%
  - 4% → vende 50%
- ✅ Stop Loss: 1%
- ✅ Trailing Stop: 0.5% (ativa após +1%)
- ✅ Buy Dip: 2%
- ✅ Max Loss: $200/dia, $500/semana
- ✅ Cooldown: 60min após venda, 30min após compra
- ✅ Volume mínimo: $50M/dia
- ❌ DCA

### REKTCOIN (MEXC)
```bash
curl -X POST http://localhost:5000/api/v1/strategies \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "exchange_id": "<MEXC_ID>",
    "token": "REKTCOIN",
    "template": "conservative"
  }'
```

---

## 3️⃣ ESTRATÉGIA AGGRESSIVE (Máximo Lucro)

**Características:**
- ✅ Take Profit Triplo:
  - 5% → vende 30%
  - 10% → vende 40%
  - 20% → vende 30%
- ✅ Stop Loss: 3%
- ✅ Trailing Stop: 2% (ativa após +3%)
- ✅ Buy Dip: 5%
- ✅ DCA em 2 níveis:
  - -5% → compra 50%
  - -8% → compra 50%
- ✅ Max Loss: $1000/dia, $3000/semana
- ✅ Cooldown: 15min após venda, 10min após compra
- ✅ Volume mínimo: $100M/dia

### REKTCOIN (MEXC)
```bash
curl -X POST http://localhost:5000/api/v1/strategies \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "exchange_id": "<MEXC_ID>",
    "token": "REKTCOIN",
    "template": "aggressive"
  }'
```

---

## 📊 Verificar Estratégias Criadas

### Listar todas do usuário
```bash
curl "http://localhost:5000/api/v1/strategies?user_id=user123"
```

### Listar do usuário na MEXC
```bash
curl "http://localhost:5000/api/v1/strategies?user_id=user123&exchange_id=<MEXC_ID>"
```

### Listar REKTCOIN especificamente
```bash
curl "http://localhost:5000/api/v1/strategies?user_id=user123&exchange_id=<MEXC_ID>&token=REKTCOIN"
```

---

## 🗑️ Deletar Estratégia

```bash
curl -X DELETE "http://localhost:5000/api/v1/strategies/<STRATEGY_ID>"
```

---

## 📋 Comparação dos Templates

| Feature | SIMPLE | CONSERVATIVE | AGGRESSIVE |
|---------|--------|--------------|------------|
| **Take Profit Levels** | 1 (5%) | 2 (2%, 4%) | 3 (5%, 10%, 20%) |
| **Stop Loss** | 2% | 1% | 3% |
| **Trailing Stop** | ❌ | ✅ 0.5% | ✅ 2% |
| **Buy Dip** | 3% | 2% | 5% |
| **DCA** | ❌ | ❌ | ✅ 2 níveis |
| **Max Daily Loss** | - | $200 | $1000 |
| **Max Weekly Loss** | - | $500 | $3000 |
| **Cooldown Sell** | - | 60min | 15min |
| **Cooldown Buy** | - | 30min | 10min |
| **Min 24h Volume** | - | $50M | $100M |
| **Risk Level** | 🟢 Baixo | 🟡 Médio | 🔴 Alto |
| **Ideal Para** | Iniciantes | Conservadores | Experientes |

---

## 🎯 Escolha seu Template

### Use **SIMPLE** se:
- 🆕 Você é iniciante
- 🎯 Quer algo direto e simples
- 📊 Não quer se preocupar com configurações avançadas

### Use **CONSERVATIVE** se:
- 🛡️ Proteção é sua prioridade
- 💰 Prefere lucros menores e mais seguros
- ⏰ Pode esperar mais tempo entre trades
- 📉 Quer limitar perdas diárias

### Use **AGGRESSIVE** se:
- 🚀 Busca máximo lucro
- 💪 Tem experiência com trading
- 📈 Aceita mais risco
- 💰 Tem capital para DCA (médias)

---

## 🔧 Exemplo Completo (Copy & Paste)

```bash
# 1. Pegar ID da MEXC
MEXC_ID=$(curl -s http://localhost:5000/api/v1/exchanges | jq -r '.exchanges[] | select(.nome=="MEXC") | ._id')

# 2. Criar estratégia AGGRESSIVE para REKTCOIN
curl -X POST http://localhost:5000/api/v1/strategies \
  -H "Content-Type: application/json" \
  -d "{
    \"user_id\": \"user123\",
    \"exchange_id\": \"$MEXC_ID\",
    \"token\": \"REKTCOIN\",
    \"template\": \"aggressive\"
  }" | jq '.'

# 3. Listar para confirmar
curl -s "http://localhost:5000/api/v1/strategies?user_id=user123&token=REKTCOIN" | jq '.strategies[]'
```

---

## ✅ Pronto para Testar!

Execute o script automatizado:
```bash
./scripts/test_strategy_templates.sh
```

Ou use os curls individuais acima! 🚀
