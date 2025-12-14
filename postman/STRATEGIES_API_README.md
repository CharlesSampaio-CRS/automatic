# Strategies API - Documentação Postman

Collection completa para gerenciamento de estratégias de trading no sistema Multi-Exchange.

## 📋 Visão Geral

Esta collection contém **6 endpoints** para criar, gerenciar e monitorar estratégias de trading automatizado.

### Endpoints Disponíveis

1. **POST /api/v1/strategies** - Criar estratégia (3 modos)
2. **GET /api/v1/strategies** - Listar estratégias do usuário
3. **GET /api/v1/strategies/:id** - Buscar estratégia específica
4. **PUT /api/v1/strategies/:id** - Atualizar estratégia
5. **DELETE /api/v1/strategies/:id** - Deletar estratégia
6. **POST /api/v1/strategies/:id/check** - Verificar triggers

## 🎯 Modos de Criação de Estratégia

### 1. Template Mode (RECOMENDADO)

Use templates pré-definidos para criar estratégias rapidamente:

```json
{
    "user_id": "charles_test_user",
    "exchange_id": "693481148b0a41e8b6acb07b",
    "token": "BTC",
    "template": "simple"
}
```

**Templates Disponíveis:**

| Template | Descrição | Take Profit | Stop Loss | Trailing | DCA |
|----------|-----------|-------------|-----------|----------|-----|
| **simple** | Estratégia básica | 1 nível (5%) | 2% | ❌ | ❌ |
| **conservative** | Proteção máxima | 2 níveis | 3% | ✅ | ❌ |
| **aggressive** | Máximo lucro | 3 níveis | 5% | ✅ | ✅ |

### 2. Custom Mode

Crie estratégias personalizadas com regras específicas:

```json
{
    "user_id": "charles_test_user",
    "exchange_id": "693481148b0a41e8b6acb07b",
    "token": "ETH",
    "rules": {
        "take_profit_levels": [
            {"percent": 3, "sell_percent": 50},
            {"percent": 7, "sell_percent": 50}
        ],
        "stop_loss": {"percent": 2, "enabled": true},
        "trailing_stop": {
            "enabled": true,
            "activation": 5,
            "distance": 2
        }
    }
}
```

### 3. Legacy Mode (DEPRECATED)

Modo legado com porcentagens simples:

```json
{
    "user_id": "charles_test_user",
    "exchange_id": "693481148b0a41e8b6acb07b",
    "token": "BTC",
    "take_profit_percent": 5,
    "stop_loss_percent": 3
}
```

## 🔧 Como Importar

### Via Postman Desktop

1. Abra o Postman
2. Click em **Import**
3. Selecione o arquivo: `Strategies_API.postman_collection.json`
4. Importe o environment: `Strategies_API.postman_environment.json`
5. Selecione o environment no dropdown (canto superior direito)

### Via Postman Web

1. Acesse https://web.postman.co
2. Click em **Import** (botão laranja)
3. Arraste os 2 arquivos JSON
4. Selecione o environment

## ⚙️ Configuração

### Variáveis do Environment

Configure estas variáveis antes de testar:

| Variável | Valor Padrão | Descrição |
|----------|--------------|-----------|
| `base_url` | `http://localhost:5000` | URL da API |
| `user_id` | `charles_test_user` | ID do usuário |
| `exchange_id` | `693481148b0a41e8b6acb07b` | ID da exchange (NovaDAX) |
| `strategy_id` | *(vazio)* | ID da estratégia (preencher após criar) |

### Ambientes

**Local Development:**
```
base_url = http://localhost:5000
```

**Production (Render):**
```
base_url = https://automatic-anfg.onrender.com
```

## 📝 Workflow Recomendado

### 1. Criar Estratégia com Template
```bash
POST /api/v1/strategies
Body: {
    "user_id": "charles_test_user",
    "exchange_id": "693481148b0a41e8b6acb07b",
    "token": "BTC",
    "template": "simple"
}
```

**Resposta:**
```json
{
    "success": true,
    "strategy_id": "674a1234567890abcdef1234",
    "strategy": { ... }
}
```

✅ **Copie o `strategy_id` e cole na variável do environment!**

### 2. Listar Estratégias do Usuário
```bash
GET /api/v1/strategies?user_id=charles_test_user
```

**Resposta:**
```json
{
    "success": true,
    "count": 2,
    "strategies": [...]
}
```

### 3. Atualizar Estratégia
```bash
PUT /api/v1/strategies/674a1234567890abcdef1234
Body: {
    "take_profit_percent": 7,
    "is_active": true
}
```

### 4. Verificar Triggers (Monitoramento)
```bash
POST /api/v1/strategies/674a1234567890abcdef1234/check
Body: {
    "current_price": 106500.00,
    "entry_price": 100000.00
}
```

**Resposta (Take Profit acionado):**
```json
{
    "should_trigger": true,
    "action": "SELL",
    "reason": "TAKE_PROFIT",
    "current_change_percent": 6.5
}
```

### 5. Deletar Estratégia
```bash
DELETE /api/v1/strategies/674a1234567890abcdef1234
```

## 🎯 Casos de Uso

### Frontend: Monitorar Posição Ativa

O frontend pode chamar o endpoint `/check` periodicamente para verificar se deve executar uma venda:

```javascript
// A cada 5 segundos
setInterval(async () => {
    const response = await fetch(
        `${API_URL}/strategies/${strategyId}/check`,
        {
            method: 'POST',
            body: JSON.stringify({
                current_price: getCurrentPrice(),
                entry_price: position.entry_price
            })
        }
    );
    
    const result = await response.json();
    
    if (result.should_trigger) {
        console.log(`${result.reason} TRIGGERED! Action: ${result.action}`);
        // Executar ordem de venda
        await executeSellOrder(position);
    }
}, 5000);
```

### Dashboard: Exibir Estratégias Ativas

```javascript
// Buscar todas as estratégias ativas
const response = await fetch(
    `${API_URL}/strategies?user_id=${userId}&is_active=true`
);

const { strategies } = await response.json();

strategies.forEach(strategy => {
    console.log(`${strategy.token} on ${strategy.exchange_name}`);
    console.log(`TP: ${strategy.take_profit_percent}%`);
    console.log(`SL: ${strategy.stop_loss_percent}%`);
});
```

## 📊 Estrutura dos Dados

### Strategy Object

```typescript
interface Strategy {
    _id: string;              // MongoDB ObjectId
    user_id: string;          // ID do usuário
    exchange_id: string;      // ID da exchange
    exchange_name?: string;   // Nome da exchange (populate)
    token: string;            // Símbolo (BTC, ETH, etc)
    template?: string;        // simple, conservative, aggressive
    rules?: {                 // Regras personalizadas
        take_profit_levels: Array<{
            percent: number;
            sell_percent: number;
        }>;
        stop_loss: {
            percent: number;
            enabled: boolean;
        };
        buy_dip?: {
            enabled: boolean;
            percent?: number;
        };
        trailing_stop?: {
            enabled: boolean;
            activation?: number;
            distance?: number;
        };
    };
    take_profit_percent?: number;  // Legacy
    stop_loss_percent?: number;    // Legacy
    buy_dip_percent?: number;      // Legacy
    is_active: boolean;
    created_at: string;       // ISO timestamp
    updated_at: string;       // ISO timestamp
}
```

## 🔍 Filtros Disponíveis

### GET /api/v1/strategies

| Query Param | Tipo | Descrição | Exemplo |
|-------------|------|-----------|---------|
| `user_id` | string | **OBRIGATÓRIO** - ID do usuário | `charles_test_user` |
| `exchange_id` | string | Filtrar por exchange | `693481148b0a41e8b6acb07b` |
| `token` | string | Filtrar por token | `BTC` |
| `is_active` | boolean | Filtrar por status | `true` ou `false` |

**Exemplos:**

```bash
# Todas as estratégias do usuário
GET /api/v1/strategies?user_id=charles_test_user

# Apenas estratégias ativas
GET /api/v1/strategies?user_id=charles_test_user&is_active=true

# Estratégias de BTC
GET /api/v1/strategies?user_id=charles_test_user&token=BTC

# Estratégias na NovaDAX
GET /api/v1/strategies?user_id=charles_test_user&exchange_id=693481148b0a41e8b6acb07b
```

## ⚠️ Códigos de Status

| Status | Significado |
|--------|-------------|
| **200** | Sucesso (GET, PUT, DELETE) |
| **201** | Estratégia criada (POST) |
| **400** | Dados inválidos |
| **404** | Estratégia não encontrada |
| **500** | Erro interno do servidor |

## 🧪 Testando

### Pré-requisitos

1. ✅ Backend rodando (`python run.py`)
2. ✅ MongoDB conectado
3. ✅ Usuário existe no banco
4. ✅ Exchange linkada ao usuário

### Fluxo de Teste Completo

1. **Criar estratégia simple para BTC**
   - Endpoint: Create Strategy (Template Mode)
   - Copiar `strategy_id` da resposta

2. **Buscar a estratégia criada**
   - Endpoint: Get Single Strategy
   - Colar `strategy_id` na URL

3. **Listar todas as estratégias**
   - Endpoint: Get All User Strategies
   - Verificar que a estratégia aparece

4. **Simular preço subindo (Take Profit)**
   - Endpoint: Check Strategy Triggers
   - Body: `current_price: 105000, entry_price: 100000`
   - Resposta: `should_trigger: true, reason: TAKE_PROFIT`

5. **Simular preço caindo (Stop Loss)**
   - Endpoint: Check Strategy Triggers
   - Body: `current_price: 97000, entry_price: 100000`
   - Resposta: `should_trigger: true, reason: STOP_LOSS`

6. **Atualizar take profit**
   - Endpoint: Update Strategy
   - Body: `{"take_profit_percent": 10}`

7. **Desativar estratégia**
   - Endpoint: Update Strategy
   - Body: `{"is_active": false}`

8. **Deletar estratégia**
   - Endpoint: Delete Strategy

## 🐛 Troubleshooting

### Erro: "user_id is required"
- ✅ Verificar se `user_id` está no query param (GET) ou body (POST)

### Erro: "Strategy not found"
- ✅ Verificar se `strategy_id` é um ObjectId válido (24 caracteres hex)
- ✅ Confirmar que a estratégia existe no MongoDB

### Erro: "Missing required fields"
- ✅ Campos obrigatórios no POST:
  - `user_id`
  - `exchange_id`
  - `token`
  - `template` OU `rules` OU `take_profit_percent + stop_loss_percent`

### should_trigger sempre false
- ✅ Verificar se `current_price` e `entry_price` estão corretos
- ✅ Confirmar que a diferença % é suficiente para acionar TP ou SL

## 📦 Arquivos da Collection

```
postman/
├── Strategies_API.postman_collection.json    # Collection principal
├── Strategies_API.postman_environment.json   # Environment com variáveis
└── STRATEGIES_API_README.md                   # Esta documentação
```

## 🔗 Relacionado

- **Exchanges API**: Para gerenciar exchanges e credenciais
- **Balances API**: Para ver saldos e histórico
- **Positions API**: Para gerenciar posições abertas

## 📞 Suporte

- **Desenvolvedor**: Charles Roberto
- **MongoDB**: MultExchange database
- **Backend**: Flask + PyMongo

---

**Última atualização:** 30/11/2024
**Versão da API:** v1
