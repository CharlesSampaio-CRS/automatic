# 📮 Postman Collection - Bot Trading MEXC v2.0

## 🚀 Como Importar

1. Abra o Postman
2. Clique em **Import**
3. Selecione o arquivo `Bot_Trading.postman_collection.json`
4. A collection será importada com todos os endpoints organizados

---

## 📋 Estrutura da Collection

### 🏥 **Health Check**
- `GET /` - Verifica se a API está rodando

### 💰 **Balance**
- `GET /balance` - Consulta saldo total em USDT

### � **Order**
- `POST /order` - Executa ordem manual

### ⚙️ **Configs (MongoDB)**
- `GET /configs` - Lista todas as configs
- `GET /configs?enabled_only=true` - Lista apenas configs habilitadas
- `GET /configs/{pair}` - Busca config por par (ex: REKT/USDT)
- `POST /configs` - Cria nova config
- `PUT /configs/{pair}` - Atualiza config (parcial)
- `DELETE /configs/{pair}` - Deleta config

### 🤖 **Jobs (Scheduler)**
- `GET /jobs` - Lista todos os jobs ativos
- `POST /jobs` com `action: reload` - Recarrega do MongoDB
- `POST /jobs` com `action: start` - Inicia jobs específicos
- `POST /jobs` com `action: stop` - Para jobs específicos ou todos

---

## 🔧 Configuração

### Variável de Ambiente

A collection já vem configurada com a variável:

```
base_url = http://localhost:5000
```

Para alterar:
1. Clique no nome da collection
2. Vá em **Variables**
3. Edite o valor de `base_url`
---

## 🎯 Fluxo de Uso Recomendado

### 1️⃣ **Verificar Status**
```
GET /
GET /balance
```

### 2️⃣ **Criar Configuração**
```
POST /configs
Body: {JSON completo}
```

### 3️⃣ **Recarregar Jobs**
```
POST /jobs
Body: {"action": "reload"}
```

### 4️⃣ **Verificar Jobs Ativos**
```
GET /jobs
```

### 5️⃣ **Testar Ordem Manual**
```
POST /order
Body: {"pair": "ETH/USDT"}
```

### 6️⃣ **Atualizar Config**
```
PUT /configs/ETH%2FUSDT
Body: {"schedule": {"interval_hours": 4}}
```

### 7️⃣ **Recarregar Novamente**
```
POST /jobs
Body: {"action": "reload"}
```

---

## 📝 Exemplos de Body

### Criar Config Completa
```json
{
  "pair": "BTC/USDT",
  "enabled": true,
  "schedule": {
    "interval_hours": 4,
    "business_hours_start": 9,
    "business_hours_end": 23,
    "enabled": true
  },
  "limits": {
    "min_value_per_order": 20,
    "allocation_percentage": 30
  },
  "trading_strategy": {
    "type": "buy_levels",
    "min_price_variation": 1.0,
    "levels": [
      {"price_drop_percent": 1.0, "allocation_percent": 20},
      {"price_drop_percent": 3.0, "allocation_percent": 30},
      {"price_drop_percent": 5.0, "allocation_percent": 50}
    ]
  },
  "sell_strategy": {
    "type": "profit_levels",
    "levels": [
      {"profit_percent": 2.0, "sell_percent": 30},
      {"profit_percent": 5.0, "sell_percent": 50},
      {"profit_percent": 10.0, "sell_percent": 100}
    ]
  }
}
```

### Atualizar Apenas Intervalo
```json
{
  "schedule": {
    "interval_hours": 3
  }
}
```

### Desabilitar Símbolo
```json
{
  "enabled": false
}
```

---

## 🔍 Observações Importantes

### URL Encoding
Quando usar pares com `/` na URL, use `%2F`:
- ✅ Correto: `/configs/REKT%2FUSDT`
- ❌ Errado: `/configs/REKT/USDT`

### Actions do Jobs
O endpoint `POST /jobs` aceita 3 actions:

1. **reload** - Recarrega todos do MongoDB
   ```json
   {"action": "reload"}
   ```

2. **start** - Inicia específicos (requer pairs)
   ```json
   {"action": "start", "pairs": ["REKT/USDT", "BTC/USDT"]}
   ```

3. **stop** - Para específicos ou todos
   ```json
   {"action": "stop", "pairs": ["REKT/USDT"]}
   ```
   ou
   ```json
   {"action": "stop"}
   ```

### Após Mudanças no MongoDB
**SEMPRE** use `POST /jobs {"action": "reload"}` para aplicar as mudanças!

---

## 📚 Documentação Completa

Para mais detalhes, consulte:
- `API_DOCS.md` - Documentação completa da API
- `API_CHANGELOG.txt` - Resumo das mudanças

---

## ✨ Features da Collection v2.0

- ✅ Organizada por domínios (Health, Balance, Order, Configs, Jobs)
- ✅ Exemplos de body pré-configurados
- ✅ Descrições em cada request
- ✅ Variável `base_url` configurável
- ✅ Cobertura completa da API v2.0
- ✅ Suporte a MongoDB e Jobs Dinâmicos
