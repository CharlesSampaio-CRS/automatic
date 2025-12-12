# 📦 Mock Data para Frontend

Esta pasta contém dados JSON completos para desenvolvimento do app mobile/web sem depender da API backend.

---

## 📁 Arquivos Disponíveis

### **1. strategies_list.json**
Lista de todas as estratégias do usuário com resumo.

**Uso:** Tela de listagem de estratégias
```typescript
// Contém 4 estratégias com diferentes estados:
// - REKTCOIN (ativa, com lucro, trailing stop ativo)
// - PEPE (ativa, com lucro, em cooldown)
// - BTC (pausada, sem execuções)
// - SHIB (ativa, com perda, próximo do circuit breaker)
```

**Campos principais:**
- `strategies[]` - Array de estratégias
- `total` - Total de estratégias
- `summary` - Resumo do portfólio

---

### **2. strategy_detail.json**
Detalhes completos de uma estratégia específica.

**Uso:** Tela de detalhes da estratégia
```typescript
// Inclui:
// - Regras completas (TP levels, trailing stop, DCA, etc)
// - Estatísticas de execução
// - Estado do trailing stop
// - Estado do cooldown
// - Posição atual (entry price, current price, PnL)
// - Próximos triggers
// - Histórico de execuções (últimas 5)
```

---

### **3. create_strategy_response.json**
Resposta da API ao criar uma nova estratégia.

**Uso:** Após submeter formulário de criação
```typescript
// Retorna estratégia criada com:
// - ID gerado
// - Regras do template aplicado
// - Tracking fields inicializados (zerados)
```

---

### **4. templates.json**
Templates disponíveis (simple, conservative, aggressive).

**Uso:** Tela de seleção de template ao criar estratégia
```typescript
// Cada template contém:
// - Nome e descrição
// - Nível de risco
// - Preview das regras
// - Lista de features
// - Comparação entre templates
```

---

### **5. balances.json**
Saldos de todas as exchanges do usuário.

**Uso:** Tela de portfolio/wallet
```typescript
// Inclui:
// - Saldos por exchange
// - Preço e valor em USD de cada ativo
// - Variação 24h e 7d
// - Indicador de estratégia ativa
// - Total do portfolio
// - Top holdings
```

---

### **6. dashboard.json**
Dados completos do dashboard principal.

**Uso:** Tela inicial do app
```typescript
// Contém:
// - Resumo do portfolio
// - Quick stats (best/worst performers)
// - Alertas (cooldown, trailing stop, circuit breaker)
// - Execuções recentes
// - Distribuição do portfolio
// - Gráfico de performance (7 dias)
```

---

### **7. jobs_status.json**
Status dos jobs de background (scheduler).

**Uso:** Tela de settings/admin
```typescript
// Mostra:
// - Balance snapshot job (4h interval)
// - Strategy worker job (5min interval)
// - Status do scheduler
// - Estatísticas de execução
```

---

### **8. exchanges.json**
Lista de exchanges conectadas e disponíveis.

**Uso:** Tela de gerenciamento de exchanges
```typescript
// Inclui:
// - Exchanges conectadas (MEXC, Binance)
// - Status de conexão
// - Total de assets e estratégias
// - Exchanges disponíveis para adicionar
```

---

## 🎨 Estrutura de Telas Sugerida

### **1. Dashboard (Home)**
```
┌─────────────────────────────────────┐
│ 📊 Portfolio: $10,663.80 (+2.1%)    │
│ 💰 Strategies PnL: +$172.87         │
│ 🎯 Active Strategies: 3/4           │
├─────────────────────────────────────┤
│ 📈 Performance Chart (7 days)       │
├─────────────────────────────────────┤
│ 🔔 Alerts (3)                       │
│ • Trailing stop ativo - REKTCOIN   │
│ • SHIB próximo do circuit breaker  │
├─────────────────────────────────────┤
│ 📋 Recent Executions                │
│ • SHIB - BUY - DCA - há 35 min     │
│ • REKTCOIN - SELL - TP - há 1h     │
└─────────────────────────────────────┘
```
**Mock:** `dashboard.json`

---

### **2. Strategies List**
```
┌─────────────────────────────────────┐
│ 🎯 Minhas Estratégias              │
│ [+ Nova Estratégia]                 │
├─────────────────────────────────────┤
│ ┌─────────────────────────────────┐ │
│ │ REKTCOIN @ MEXC           ✅    │ │
│ │ Template: Aggressive             │ │
│ │ PnL: +$245.67 (+71.4% win)      │ │
│ │ 🔥 Trailing Stop Ativo          │ │
│ │ ⏱️ Cooldown: 25 min             │ │
│ └─────────────────────────────────┘ │
│                                     │
│ ┌─────────────────────────────────┐ │
│ │ PEPE @ MEXC               ✅    │ │
│ │ Template: Conservative           │ │
│ │ PnL: +$12.50 (100% win)         │ │
│ └─────────────────────────────────┘ │
│                                     │
│ ┌─────────────────────────────────┐ │
│ │ BTC @ Binance             ⏸️    │ │
│ │ Template: Simple                 │ │
│ │ PnL: $0.00 (sem execuções)      │ │
│ └─────────────────────────────────┘ │
└─────────────────────────────────────┘
```
**Mock:** `strategies_list.json`

---

### **3. Strategy Detail**
```
┌─────────────────────────────────────┐
│ ← REKTCOIN @ MEXC          [⏸️][🗑️]│
├─────────────────────────────────────┤
│ 📊 Performance                      │
│ Entry: $1.00 → Current: $1.25       │
│ PnL: +$245.67 (+25%)                │
│ Win Rate: 71.4% (7 sells, 5 buys)  │
├─────────────────────────────────────┤
│ 🎯 Próximos Triggers                │
│ ✅ TP Level 1: 5% EXECUTADO         │
│ ✅ TP Level 2: 10% EXECUTADO        │
│ ⏳ TP Level 3: 20% (faltam 5%)      │
│ 🔥 Trailing Stop: $1.225 (-2%)     │
├─────────────────────────────────────┤
│ ⚙️ Regras                           │
│ • Take Profit: 3 níveis             │
│ • Trailing Stop: 2% após 5%         │
│ • Stop Loss: 3%                     │
│ • DCA: 2 níveis (5%, 10%)           │
│ • Cooldown: 15/10 min               │
│ • Circuit Breaker: $1000/dia        │
├─────────────────────────────────────┤
│ 📋 Histórico (5 últimas)            │
│ • SELL TP +$66 - há 1h              │
│ • SELL TP +$40 - há 3h              │
│ • SELL TP +$15 - há 5h              │
└─────────────────────────────────────┘
```
**Mock:** `strategy_detail.json`

---

### **4. Create Strategy**
```
┌─────────────────────────────────────┐
│ ← Nova Estratégia                   │
├─────────────────────────────────────┤
│ Exchange:                           │
│ [MEXC ▼]                            │
│                                     │
│ Token:                              │
│ [DOGE_______]                       │
│                                     │
│ Template:                           │
│ ┌─────────────────────────────────┐ │
│ │ 🟢 Simple                        │ │
│ │ Estratégia básica - Baixo risco │ │
│ │ [Selecionar]                     │ │
│ └─────────────────────────────────┘ │
│                                     │
│ ┌─────────────────────────────────┐ │
│ │ 🟡 Conservative        ✓        │ │
│ │ Proteções avançadas - Médio     │ │
│ │ [Selecionado]                    │ │
│ └─────────────────────────────────┘ │
│                                     │
│ ┌─────────────────────────────────┐ │
│ │ 🔴 Aggressive                    │ │
│ │ Múltiplos níveis - Alto risco   │ │
│ │ [Selecionar]                     │ │
│ └─────────────────────────────────┘ │
│                                     │
│ [Comparar Templates]                │
│ [Criar Estratégia]                  │
└─────────────────────────────────────┘
```
**Mock:** `templates.json` + `create_strategy_response.json`

---

### **5. Portfolio/Balances**
```
┌─────────────────────────────────────┐
│ 💰 Portfolio Total                  │
│ $10,663.80 (+2.1% hoje)             │
├─────────────────────────────────────┤
│ 📊 Por Exchange                     │
│ ┌─────────────────────────────────┐ │
│ │ MEXC             $6,560.50 62%  │ │
│ │ 🎯 3 estratégias ativas          │ │
│ │ • REKTCOIN   $875                │ │
│ │ • PEPE       $85                 │ │
│ │ • SHIB       $180                │ │
│ │ • USDT       $5,420              │ │
│ └─────────────────────────────────┘ │
│                                     │
│ ┌─────────────────────────────────┐ │
│ │ Binance          $4,103.30 38%  │ │
│ │ • BTC        $637                │ │
│ │ • ETH        $1,125              │ │
│ │ • USDT       $2,340              │ │
│ └─────────────────────────────────┘ │
└─────────────────────────────────────┘
```
**Mock:** `balances.json`

---

### **6. Settings/Jobs**
```
┌─────────────────────────────────────┐
│ ⚙️ Configurações                    │
├─────────────────────────────────────┤
│ 🔄 Background Jobs                  │
│                                     │
│ ┌─────────────────────────────────┐ │
│ │ Balance Snapshot      ✅ Running│ │
│ │ Próximo: 18:00 (em 55 min)      │ │
│ │ Última: 14:00 (sucesso)         │ │
│ │ [⏸️ Pausar] [▶️ Executar]       │ │
│ └─────────────────────────────────┘ │
│                                     │
│ ┌─────────────────────────────────┐ │
│ │ Strategy Worker       ✅ Running│ │
│ │ Próximo: 17:10 (em 5 min)       │ │
│ │ Última: 17:05 (1 exec)          │ │
│ │ [⏸️ Pausar] [▶️ Executar]       │ │
│ └─────────────────────────────────┘ │
├─────────────────────────────────────┤
│ 🔗 Exchanges Conectadas             │
│ • MEXC - Conectada ✅               │
│ • Binance - Conectada ✅            │
│ [+ Adicionar Exchange]              │
└─────────────────────────────────────┘
```
**Mock:** `jobs_status.json` + `exchanges.json`

---

## 💻 Como Usar no Código

### **React Native / React Example:**

```typescript
// services/mockData.ts
import strategiesList from './mocks/strategies_list.json';
import strategyDetail from './mocks/strategy_detail.json';
import dashboard from './mocks/dashboard.json';
import templates from './mocks/templates.json';
import balances from './mocks/balances.json';
import jobsStatus from './mocks/jobs_status.json';
import exchanges from './mocks/exchanges.json';

export const MockAPI = {
  // Dashboard
  getDashboard: () => Promise.resolve(dashboard.dashboard),
  
  // Strategies
  getStrategies: (userId: string) => Promise.resolve(strategiesList),
  getStrategy: (id: string) => Promise.resolve(strategyDetail),
  createStrategy: (data: any) => Promise.resolve(createStrategyResponse),
  
  // Templates
  getTemplates: () => Promise.resolve(templates),
  
  // Balances
  getBalances: (userId: string) => Promise.resolve(balances),
  
  // Jobs
  getJobsStatus: () => Promise.resolve(jobsStatus),
  
  // Exchanges
  getExchanges: (userId: string) => Promise.resolve(exchanges)
};

// Hook para usar em desenvolvimento
export const useMockData = () => {
  const isDevelopment = __DEV__;
  return {
    useMock: isDevelopment,
    api: isDevelopment ? MockAPI : RealAPI
  };
};
```

### **Componente Example:**

```typescript
// screens/StrategiesScreen.tsx
import { useMockData } from '../services/mockData';

export function StrategiesScreen() {
  const { api } = useMockData();
  const [strategies, setStrategies] = useState([]);

  useEffect(() => {
    loadStrategies();
  }, []);

  async function loadStrategies() {
    const data = await api.getStrategies('charles_test_user');
    setStrategies(data.strategies);
  }

  return (
    <FlatList
      data={strategies}
      renderItem={({ item }) => <StrategyCard strategy={item} />}
    />
  );
}
```

---

## 🎯 Cenários de Teste Cobertos

### **1. Estratégia com Lucro (REKTCOIN)**
- ✅ Trailing stop ativo
- ✅ Em cooldown
- ✅ 2 níveis de TP executados
- ✅ PnL positivo
- ✅ Win rate alto (71.4%)

### **2. Estratégia Conservadora (PEPE)**
- ✅ Template conservative
- ✅ Win rate 100%
- ✅ Poucos trades (3)
- ✅ PnL pequeno mas positivo

### **3. Estratégia Pausada (BTC)**
- ✅ is_active = false
- ✅ Sem execuções
- ✅ Tracking zerado
- ✅ Template simple

### **4. Estratégia com Perda (SHIB)**
- ✅ PnL negativo
- ✅ Próximo do circuit breaker
- ✅ Win rate baixo (45.5%)
- ✅ Múltiplas execuções (25)
- ✅ DCA executado

---

## 📊 Dados Estatísticos Realistas

Todos os JSONs contêm dados realistas:
- ✅ Preços de mercado reais
- ✅ Timestamps recentes
- ✅ Win rates variados (45% a 100%)
- ✅ PnL positivos e negativos
- ✅ Diferentes estados de cooldown
- ✅ Trailing stops ativos/inativos
- ✅ Circuit breakers próximos/distantes

---

## 🚀 Próximos Passos

1. Copie a pasta `mocks/` para seu projeto frontend
2. Importe os JSONs nos seus serviços
3. Crie um toggle dev/prod para usar mock ou API real
4. Desenvolva as telas usando os dados mock
5. Quando a API estiver pronta, troque para chamadas reais

---

## ✅ Checklist de Telas

- [ ] Dashboard (home)
- [ ] Strategies List
- [ ] Strategy Detail
- [ ] Create Strategy (template selection)
- [ ] Portfolio/Balances
- [ ] Settings/Jobs
- [ ] Exchanges Management

**Todos os dados necessários estão prontos! 🎉**
