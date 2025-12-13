# 📱 Guia Rápido - Mock Data para App

## 🎯 Arquivos Criados

```
mocks/
├── README.md (16KB)              → Guia completo de uso
├── strategies_list.json (12KB)   → Lista de estratégias
├── strategy_detail.json (5.2KB)  → Detalhes de 1 estratégia
├── create_strategy_response.json (2.8KB) → Resposta de criação
├── templates.json (5.4KB)        → 3 templates disponíveis
├── dashboard.json (5.3KB)        → Dashboard completo
├── balances.json (3.1KB)         → Portfolio/saldos
├── jobs_status.json (1.1KB)      → Status dos jobs
└── exchanges.json (2.0KB)        → Exchanges conectadas
```

---

## 🚀 Quick Start

### **1. Copie a pasta `mocks/` para seu projeto**
```bash
cp -r mocks/ /path/to/your/frontend/project/src/
```

### **2. Importe no seu código:**
```typescript
import strategiesList from './mocks/strategies_list.json';

// Ou use o MockAPI helper
import { MockAPI } from './services/mockData';

const strategies = await MockAPI.getStrategies('user_id');
```

### **3. Desenvolva as telas:**
- ✅ Dashboard → `dashboard.json`
- ✅ Lista de Estratégias → `strategies_list.json`
- ✅ Detalhes → `strategy_detail.json`
- ✅ Criar Estratégia → `templates.json`
- ✅ Portfolio → `balances.json`

---

## 📊 Dados Incluídos

### **4 Estratégias com Cenários Diferentes:**

1. **REKTCOIN (MEXC)** 🟢
   - Template: Aggressive
   - Status: Ativa
   - PnL: +$245.67 (+71.4% win rate)
   - Trailing stop: ATIVO
   - Cooldown: 25 minutos restantes
   - 2 TPs executados, aguardando TP 3

2. **PEPE (MEXC)** 🟢
   - Template: Conservative
   - Status: Ativa
   - PnL: +$12.50 (100% win rate)
   - Trailing stop: ATIVO
   - Em cooldown
   - Apenas 3 execuções (cautelosa)

3. **BTC (Binance)** ⚪
   - Template: Simple
   - Status: PAUSADA
   - PnL: $0.00 (sem execuções)
   - Estratégia nova, ainda não operou

4. **SHIB (MEXC)** 🔴
   - Template: Aggressive
   - Status: Ativa
   - PnL: -$85.30 (45.5% win rate)
   - ⚠️ Próximo do circuit breaker
   - 25 execuções (muita atividade)
   - DCA executado

---

## 🎨 Telas Recomendadas

### **Tela 1: Dashboard (Home)**
```typescript
import dashboard from './mocks/dashboard.json';

// Mostre:
- Portfolio total: $10,663.80
- PnL hoje: +$8.30
- Estratégias ativas: 3/4
- Gráfico de 7 dias
- Alertas (3):
  • Trailing stop ativo - REKTCOIN
  • SHIB próximo do circuit breaker
  • PEPE em cooldown
- Últimas 5 execuções
```

### **Tela 2: Estratégias**
```typescript
import strategiesList from './mocks/strategies_list.json';

// Card para cada estratégia mostrando:
- Token @ Exchange
- Status (ativa/pausada)
- PnL e win rate
- Indicadores (trailing stop, cooldown, alerts)
- Botões: Ver detalhes, Pausar, Deletar
```

### **Tela 3: Detalhes da Estratégia**
```typescript
import strategyDetail from './mocks/strategy_detail.json';

// Sections:
1. Performance (entry price, current, PnL, win rate)
2. Próximos Triggers (TPs, trailing stop, SL, DCA)
3. Regras Configuradas
4. Histórico de Execuções (últimas 5)
5. Gráfico de preço (opcional)
```

### **Tela 4: Criar Estratégia**
```typescript
import templates from './mocks/templates.json';

// Flow:
1. Selecionar Exchange (dropdown)
2. Digitar Token (input)
3. Escolher Template:
   - Simple (🟢 Baixo risco)
   - Conservative (🟡 Médio risco)
   - Aggressive (🔴 Alto risco)
4. [Botão] Comparar Templates
5. [Botão] Criar Estratégia
```

### **Tela 5: Portfolio**
```typescript
import balances from './mocks/balances.json';

// Mostre:
- Total: $10,663.80 (+2.1% hoje)
- Por Exchange:
  • MEXC: $6,560.50 (62%)
  • Binance: $4,103.30 (38%)
- Assets por exchange
- Indicador de estratégia ativa
- PnL da estratégia (se houver)
```

### **Tela 6: Settings**
```typescript
import jobsStatus from './mocks/jobs_status.json';
import exchanges from './mocks/exchanges.json';

// Sections:
1. Background Jobs
   - Balance Snapshot (4h)
   - Strategy Worker (5min)
2. Exchanges Conectadas
   - MEXC ✅
   - Binance ✅
   - [+] Adicionar
```

---

## 💡 Dicas de Implementação

### **1. Toggle Mock/Real API:**
```typescript
const API_BASE_URL = __DEV__ 
  ? 'mock' 
  : 'http://your-api.com';

export const api = __DEV__ ? MockAPI : RealAPI;
```

### **2. Estados da UI:**
- ✅ Loading → Usar skeleton/shimmer
- ✅ Empty → "Nenhuma estratégia criada"
- ✅ Error → "Erro ao carregar dados"
- ✅ Success → Mostrar dados

### **3. Cores por Status:**
- 🟢 Verde: Ativa + Lucro
- 🟡 Amarelo: Ativa + Neutro
- 🔴 Vermelho: Ativa + Perda
- ⚪ Cinza: Pausada

### **4. Badges/Indicators:**
- 🔥 Trailing Stop Ativo
- ⏱️ Em Cooldown (X minutos)
- ⚠️ Próximo do Circuit Breaker
- ✅ TP Level Executado
- 📈 DCA Executado

---

## 🎯 Campos Importantes

### **Para Cards de Estratégia:**
```typescript
{
  token: "REKTCOIN",
  exchange_name: "MEXC",
  is_active: true,
  execution_stats: {
    total_pnl_usd: 245.67,
    daily_pnl_usd: 45.20
  },
  performance: {
    win_rate: 71.4
  },
  trailing_stop_state: {
    is_active: true
  },
  cooldown_state: {
    cooldown_until: "2024-12-12T16:00:00Z"
  }
}
```

### **Para Dashboard Summary:**
```typescript
{
  total_portfolio_value_usd: 10663.80,
  portfolio_change_24h: 2.1,
  active_strategies: 3,
  total_strategies_pnl_usd: 172.87,
  today_pnl_usd: 8.30
}
```

---

## ✅ Checklist para o App

- [ ] Implementar Dashboard
- [ ] Implementar Lista de Estratégias
- [ ] Implementar Detalhes da Estratégia
- [ ] Implementar Criar Estratégia (template selection)
- [ ] Implementar Portfolio/Balances
- [ ] Implementar Settings/Jobs
- [ ] Implementar Exchanges Management
- [ ] Adicionar Pull-to-Refresh
- [ ] Adicionar Infinite Scroll (histórico)
- [ ] Adicionar Search/Filter
- [ ] Adicionar Notificações
- [ ] Adicionar Gráficos
- [ ] Adicionar Dark Mode

---

## 📞 Integração com API Real

Quando a API estiver pronta, basta trocar:

```typescript
// ANTES (mock)
const data = await MockAPI.getStrategies(userId);

// DEPOIS (real)
const data = await fetch(`${API_BASE_URL}/api/v1/strategies?user_id=${userId}`)
  .then(r => r.json());
```

**A estrutura dos dados é IDÊNTICA!** ✅

---

**🎉 Tudo pronto para desenvolver o app!**

📁 **52KB de dados mock**
📊 **4 estratégias + 8 assets + 2 exchanges**
🎨 **6 telas completas mapeadas**
💻 **Código TypeScript de exemplo incluído**
