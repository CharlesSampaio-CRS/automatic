# 🎯 Regras de Compra e Venda Melhoradas

## ✅ O que foi implementado

### **1. Múltiplos Níveis de Take Profit**
- ❌ **Antes:** Vendia 100% ao atingir 1 único percentual
- ✅ **Agora:** Vende em múltiplos níveis com quantidades diferentes
- **Exemplo (Aggressive):**
  - 5% → Vende 30% da posição
  - 10% → Vende 40% da posição
  - 20% → Vende 30% da posição
- **Benefício:** Captura lucros progressivamente, protege ganhos

---

### **2. Trailing Stop Loss (Dinâmico)**
- ❌ **Antes:** Stop loss fixo (ex: -2%)
- ✅ **Agora:** Stop loss que "segue" o preço quando sobe
- **Como funciona:**
  1. Ativa após X% de ganho (ex: 2%)
  2. Acompanha o preço máximo alcançado
  3. Vende se cair Y% do pico (ex: 0.5%)
- **Exemplo:**
  - Comprou: $1.00
  - Subiu para: $1.05 (+5%) ✅ Trailing ativado
  - Caiu para: $1.045 (-0.5% do pico) 🔴 VENDE
- **Benefício:** Protege lucros sem limitar ganhos

---

### **3. DCA (Dollar Cost Average) - Compras Fracionadas**
- ❌ **Antes:** Comprava tudo de uma vez no dip
- ✅ **Agora:** Compra em múltiplos níveis de queda
- **Exemplo (Aggressive):**
  - -5% → Compra 50% do valor planejado
  - -10% → Compra 50% do valor planejado
- **Benefício:** Melhora preço médio se continuar caindo

---

### **4. Cooldown (Período de Espera)**
- ❌ **Antes:** Executava ordens sem pausa
- ✅ **Agora:** Aguarda tempo configurado após cada operação
- **Exemplo (Conservative):**
  - Após COMPRA: aguarda 60 minutos
  - Após VENDA: aguarda 30 minutos
- **Benefício:** Evita overtrading e decisões impulsivas

---

### **5. Circuit Breakers (Limitadores de Perda)**
- ❌ **Antes:** Sem limite de perdas
- ✅ **Agora:** Auto-pausa ao atingir limite de perda
- **Exemplo (Conservative):**
  - Perda diária: max $200
  - Perda semanal: max $500
  - Perda mensal: max $1000
- **Ação:** Estratégia é PAUSADA automaticamente
- **Benefício:** Protege capital em dias ruins

---

### **6. Trading Hours (Horário de Operação)**
- ❌ **Antes:** Operava 24/7
- ✅ **Agora:** Opera apenas em horários configurados
- **Exemplo:**
  ```json
  "trading_hours": {
    "enabled": true,
    "start_time": "09:00",
    "end_time": "18:00",
    "timezone": "America/Sao_Paulo"
  }
  ```
- **Benefício:** Evita períodos de baixa liquidez

---

### **7. Blackout Periods (Períodos de Bloqueio)**
- ❌ **Antes:** Operava durante eventos importantes
- ✅ **Agora:** Bloqueia trading em períodos específicos
- **Exemplo:**
  ```json
  "blackout_periods": [
    {
      "start": "2024-01-15T14:00:00Z",
      "end": "2024-01-15T15:00:00Z",
      "reason": "FED announcement"
    }
  ]
  ```
- **Benefício:** Evita volatilidade extrema durante eventos

---

### **8. Execução Parcial de Ordens**
- ❌ **Antes:** Sempre comprava/vendia 100%
- ✅ **Agora:** Executa quantidade exata de cada nível
- **Exemplo:**
  - TP Level 1 (5%): Vende apenas 30%
  - TP Level 2 (10%): Vende apenas 40%
- **Benefício:** Permite estratégias mais sofisticadas

---

### **9. Tracking Completo**
- ❌ **Antes:** Rastreamento básico
- ✅ **Agora:** Estatísticas detalhadas
- **Rastreia:**
  - Total de execuções (buys/sells)
  - PnL total, diário, semanal, mensal
  - Níveis de TP/DCA executados
  - Último preço, quantidade, razão
  - Estado do trailing stop
  - Estado do cooldown
- **Benefício:** Análise detalhada de performance

---

## 🔄 Como funciona agora

### **Ordem de Verificação (Priority Order):**

```
1️⃣ COOLDOWN - Está em período de espera?
   ❌ SIM → Não executa nada
   ✅ NÃO → Continua...

2️⃣ CIRCUIT BREAKERS - Atingiu limite de perda?
   ❌ SIM → Auto-pausa estratégia
   ✅ NÃO → Continua...

3️⃣ TRADING HOURS - Está no horário de operação?
   ❌ NÃO → Aguarda horário
   ✅ SIM → Continua...

4️⃣ BLACKOUT PERIODS - Está em período bloqueado?
   ❌ SIM → Aguarda fim do período
   ✅ NÃO → Continua...

5️⃣ TRAILING STOP - Stop dinâmico foi atingido?
   ✅ SIM → VENDE 100% (prioridade máxima)
   ❌ NÃO → Continua...

6️⃣ TAKE PROFIT LEVELS - Algum nível foi atingido?
   ✅ SIM → VENDE X% (conforme configuração)
   ❌ NÃO → Continua...

7️⃣ STOP LOSS - Stop loss fixo foi atingido?
   ✅ SIM → VENDE 100%
   ❌ NÃO → Continua...

8️⃣ DCA LEVELS - Preço caiu para algum nível DCA?
   ✅ SIM → COMPRA X% (conforme configuração)
   ❌ NÃO → Aguarda próxima verificação
```

---

## 📊 Comparação: Antes vs Agora

### **Template AGGRESSIVE**

#### ❌ **Antes:**
```
Comprou em: $1.00

Cenário 1: Preço vai para $1.05 (+5%)
→ VENDE 100% ao atingir 5%

Cenário 2: Preço vai para $1.20 (+20%) e volta para $0.98
→ Não vendeu nada, perdeu oportunidade de $0.20

Cenário 3: Preço cai para $0.97 (-3%)
→ VENDE 100% no stop loss
```

#### ✅ **Agora:**
```
Comprou em: $1.00

Cenário 1: Preço vai para $1.05 (+5%)
→ VENDE 30% ao atingir 5%
→ Mantém 70% para próximos níveis (10%, 20%)

Cenário 2: Preço vai para $1.20 (+20%) e volta para $1.188
→ VENDEU 30% em $1.05
→ VENDEU 40% em $1.10
→ VENDEU 30% em $1.20
→ Trailing stop ativado em $1.20
→ VENDE resto quando cai 2% do pico ($1.176)
→ Lucro protegido!

Cenário 3: Preço cai para $0.95 (-5%)
→ COMPRA 50% (DCA Level 1)
→ Se cair para $0.90 (-10%), COMPRA +50%
→ Preço médio melhorado!
```

---

## 🎮 Uso Prático

### **1. Criar estratégia com template:**
```bash
curl -X POST http://localhost:5000/api/v1/strategies \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "charles_test_user",
    "exchange_id": "693481148b0a41e8b6acb07b",
    "token": "REKTCOIN",
    "template": "aggressive",
    "is_active": true
  }'
```

### **2. Verificar execuções:**
```bash
curl http://localhost:5000/api/v1/strategies/{strategy_id}
```

**Retorna:**
```json
{
  "execution_stats": {
    "total_executions": 5,
    "total_sells": 3,
    "total_buys": 2,
    "total_pnl_usd": 145.67,
    "daily_pnl_usd": 45.20,
    "executed_tp_levels": [5, 10],
    "executed_dca_levels": [5],
    "last_execution_at": "2024-01-10T15:30:00Z",
    "last_execution_type": "SELL",
    "last_execution_reason": "TAKE_PROFIT"
  },
  "trailing_stop_state": {
    "highest_price_seen": 1.25,
    "is_active": true,
    "last_updated": "2024-01-10T15:25:00Z"
  },
  "cooldown_state": {
    "cooldown_until": "2024-01-10T16:00:00Z",
    "last_action": "SELL",
    "last_action_at": "2024-01-10T15:30:00Z"
  }
}
```

---

## 🚀 Benefícios Gerais

### **Segurança:**
- ✅ Circuit breakers protegem capital
- ✅ Stop loss + trailing stop dupla proteção
- ✅ Cooldown evita overtrading
- ✅ Blackout evita eventos de alto risco

### **Lucratividade:**
- ✅ Múltiplos TPs capturam lucros progressivamente
- ✅ Trailing stop maximiza ganhos sem limitar upside
- ✅ DCA melhora preço médio em quedas
- ✅ Execução parcial permite estratégias sofisticadas

### **Controle:**
- ✅ Trading hours define quando operar
- ✅ Tracking completo para análise
- ✅ Auto-pausa em perdas excessivas
- ✅ Transparência total das execuções

---

## 📝 Notas Importantes

1. **DRY-RUN Mode:** Todas as ordens são simuladas quando `STRATEGY_DRY_RUN=true`
2. **Frequência:** Strategy Worker verifica a cada 5 minutos
3. **Prioridade:** Trailing stop tem prioridade sobre TPs normais
4. **Execução:** Níveis de TP/DCA são executados apenas 1 vez
5. **Auto-Pause:** Circuit breakers pausam estratégia automaticamente

---

## 🔧 Próximos Passos (Opcional)

- [ ] Adicionar indicadores RSI (estrutura já pronta)
- [ ] Implementar validação de volume (desabilitado por padrão)
- [ ] Dashboard de performance por estratégia
- [ ] Notificações push para execuções importantes
- [ ] Backtest de estratégias com dados históricos

---

**✅ Sistema está pronto para uso com todas as melhorias implementadas!**
