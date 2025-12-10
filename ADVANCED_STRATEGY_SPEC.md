# 🚀 Advanced Strategy Features - Implementation Plan

## ✅ Estrutura de Rules Expandida

### **Novo formato de `rules` ao criar estratégia:**

```json
{
  "user_id": "user123",
  "exchange_id": "65abc...",
  "token": "BTC",
  "rules": {
    // === TAKE PROFIT (Múltiplos Níveis) ===
    "take_profit_levels": [
      {
        "percent": 3.0,           // +3% do entry price
        "quantity_percent": 30,    // Vende 30% da posição
        "enabled": true
      },
      {
        "percent": 5.0,           // +5% do entry price
        "quantity_percent": 40,    // Vende 40% da posição
        "enabled": true
      },
      {
        "percent": 10.0,          // +10% do entry price
        "quantity_percent": 30,    // Vende 30% da posição
        "enabled": true
      }
    ],
    
    // === STOP LOSS (Com Trailing) ===
    "stop_loss": {
      "percent": 2.0,                    // -2% do entry price (inicial)
      "enabled": true,
      "trailing_enabled": true,          // Trailing stop ativado
      "trailing_percent": 1.5,           // Sobe e mantém 1.5% abaixo do maior preço
      "trailing_activation_percent": 2.0  // Só ativa trailing após +2% de lucro
    },
    
    // === BUY DIP (Com DCA) ===
    "buy_dip": {
      "percent": 3.0,              // -3% do entry price
      "enabled": true,
      "dca_enabled": true,         // Dollar Cost Average
      "dca_splits": 3,             // Divide compra em 3 partes
      "dca_levels": [              // Níveis automáticos de DCA
        { "percent": 3.0, "quantity_percent": 33 },  // -3%: compra 33%
        { "percent": 4.0, "quantity_percent": 33 },  // -4%: compra 33%
        { "percent": 5.0, "quantity_percent": 34 }   // -5%: compra 34%
      ]
    },
    
    // === CIRCUIT BREAKERS (Proteção de Perdas) ===
    "risk_management": {
      "max_daily_loss_usd": 500,          // Pausa se perder $500/dia
      "max_weekly_loss_usd": 1500,        // Pausa se perder $1500/semana
      "max_monthly_loss_usd": 5000,       // Pausa se perder $5000/mês
      "pause_on_limit": true,              // Auto-pausa ao atingir limite
      "reset_hour_utc": 0                  // Hora de reset (meia-noite UTC)
    },
    
    // === COOLDOWN (Anti Over-Trading) ===
    "cooldown": {
      "enabled": true,
      "minutes_after_sell": 30,    // 30min após venda
      "minutes_after_buy": 15      // 15min após compra
    },
    
    // === TRADING HOURS (Horários Permitidos) ===
    "trading_hours": {
      "enabled": true,
      "timezone": "UTC",
      "allowed_hours": [8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20],
      "allowed_days": [1, 2, 3, 4, 5]  // Segunda a Sexta (0=Domingo, 6=Sábado)
    },
    
    // === BLACKOUT PERIODS (Eventos Específicos) ===
    "blackout_periods": [
      {
        "description": "FOMC Meeting",
        "start": "2024-12-15T14:00:00Z",
        "end": "2024-12-15T16:00:00Z",
        "enabled": true
      }
    ],
    
    // === VOLUME VALIDATION (Liquidez Mínima) ===
    "volume_check": {
      "enabled": true,
      "min_24h_volume_usd": 100000000,  // $100M volume/dia
      "min_1h_volume_usd": 5000000       // $5M volume/hora
    },
    
    // === TECHNICAL INDICATORS (Confirmação) ===
    "indicators": {
      "rsi": {
        "enabled": true,
        "period": 14,
        "oversold": 30,      // RSI < 30: oversold (boa pra comprar)
        "overbought": 70,    // RSI > 70: overbought (boa pra vender)
        "require_on_buy": true,   // Requer RSI < 30 para comprar
        "require_on_sell": true   // Requer RSI > 70 para vender
      },
      "ma_crossover": {
        "enabled": false,
        "fast_period": 9,
        "slow_period": 21,
        "require_on_entry": false
      }
    },
    
    // === PARTIAL EXECUTION (Gestão de Quantidade) ===
    "execution": {
      "min_order_size_usd": 10,          // Ordem mínima $10
      "max_order_size_percent": 100,     // Máx 100% da posição
      "allow_partial_fills": true        // Aceita execuções parciais
    }
  },
  "is_active": true
}
```

---

## 📊 Campos de Tracking da Estratégia

```json
{
  "_id": "65xyz...",
  "user_id": "user123",
  "exchange_id": "65abc...",
  "exchange_name": "Binance",
  "token": "BTC",
  "rules": { /* ver acima */ },
  "is_active": true,
  
  // === EXECUTION TRACKING ===
  "execution_stats": {
    "total_executions": 0,
    "total_sells": 0,
    "total_buys": 0,
    "last_execution_at": null,
    "last_execution_type": null,  // "SELL" | "BUY"
    "last_execution_reason": null // "TAKE_PROFIT_L1" | "STOP_LOSS" | etc
  },
  
  // === PROFIT/LOSS TRACKING ===
  "performance": {
    "total_profit_usd": 0,
    "total_loss_usd": 0,
    "win_rate": 0,
    "daily_pnl": 0,
    "weekly_pnl": 0,
    "monthly_pnl": 0
  },
  
  // === TRAILING STOP STATE ===
  "trailing_stop_state": {
    "is_active": false,
    "highest_price": null,
    "current_stop_price": null,
    "activated_at": null
  },
  
  // === COOLDOWN STATE ===
  "cooldown_state": {
    "is_cooling": false,
    "cooldown_until": null,
    "last_action": null
  },
  
  // === TIMESTAMPS ===
  "created_at": "2024-12-10T10:00:00Z",
  "updated_at": "2024-12-10T10:00:00Z",
  "last_checked_at": "2024-12-10T14:30:00Z"
}
```

---

## 🔧 Métodos do StrategyService Atualizados

### **1. create_strategy(user_id, exchange_id, token, rules, is_active)**
- Valida todos os campos de rules
- Cria índices necessários
- Inicializa tracking fields

### **2. check_strategy_triggers(strategy_id, current_price, entry_price, position, market_data)**
- **Parâmetros adicionais:**
  - `position`: Objeto Position com quantidade atual
  - `market_data`: { volume_24h, volume_1h, rsi, ma_fast, ma_slow }

- **Verificações em ordem:**
  1. ✅ Trading Hours - Está no horário permitido?
  2. ✅ Blackout Period - Está em período de blackout?
  3. ✅ Cooldown - Ainda em cooldown?
  4. ✅ Circuit Breaker - Atingiu limite de perda?
  5. ✅ Volume Check - Volume suficiente?
  6. ✅ RSI Check - Condições técnicas OK?
  7. ✅ Trailing Stop - Verificar se ativado e se atingiu
  8. ✅ Stop Loss - Verificar stop loss fixo
  9. ✅ Take Profit Levels - Qual nível atingiu?
  10. ✅ Buy Dip Levels - Qual nível de DCA atingiu?

- **Retorno:**
```json
{
  "should_trigger": true,
  "action": "SELL",
  "reason": "TAKE_PROFIT_L2",
  "trigger_price": 47250.0,
  "quantity_percent": 40,
  "validations": {
    "trading_hours": true,
    "blackout_period": true,
    "cooldown": true,
    "circuit_breaker": true,
    "volume": true,
    "rsi": true
  },
  "metadata": {
    "current_rsi": 72,
    "volume_24h": 150000000,
    "take_profit_level": 2
  }
}
```

### **3. update_trailing_stop(strategy_id, current_price)**
- Atualiza highest_price se necessário
- Recalcula current_stop_price
- Ativa trailing se atingiu activation_percent

### **4. record_execution(strategy_id, action, reason, quantity, price, pnl)**
- Atualiza execution_stats
- Atualiza performance (daily_pnl, weekly_pnl, etc)
- Inicia cooldown
- Verifica circuit breakers

### **5. check_circuit_breaker(strategy_id)**
- Verifica se atingiu max_daily_loss
- Verifica se atingiu max_weekly_loss
- Auto-pausa estratégia se necessário
- Retorna status

### **6. reset_daily_stats(strategy_id)**
- Reseta daily_pnl
- Chamado automaticamente à meia-noite UTC

---

## 🎯 Implementação por Fases

### **FASE 1: Core Enhancements (Prioridade ALTA)** ✅
1. Múltiplos Take Profit Levels
2. Trailing Stop Loss
3. Circuit Breakers (max daily/weekly loss)
4. Cooldown Period

### **FASE 2: Risk Management (Prioridade ALTA)** ✅
5. Trading Hours
6. Blackout Periods
7. Volume Validation
8. DCA on Buy Dip

### **FASE 3: Technical Analysis (Prioridade MÉDIA)** 
9. RSI Integration
10. MA Crossover (futuro)
11. MACD (futuro)

### **FASE 4: Advanced (Prioridade BAIXA)**
12. Stop Loss Levels (múltiplos, como TP)
13. Position sizing dinâmico
14. Kelly Criterion
15. Martingale (opcional)

---

## 📝 Compatibilidade com API Antiga

Para manter compatibilidade, suportaremos ambos os formatos:

**Formato Simples (Antigo):**
```json
{
  "take_profit_percent": 5.0,
  "stop_loss_percent": 2.0,
  "buy_dip_percent": 3.0
}
```

**Conversão automática para:**
```json
{
  "take_profit_levels": [
    { "percent": 5.0, "quantity_percent": 100, "enabled": true }
  ],
  "stop_loss": {
    "percent": 2.0,
    "enabled": true,
    "trailing_enabled": false
  },
  "buy_dip": {
    "percent": 3.0,
    "enabled": true,
    "dca_enabled": false
  }
}
```

---

## 🚀 Começar Implementação?

Ordem sugerida:
1. ✅ Criar helpers de validação
2. ✅ Atualizar create_strategy com novo schema
3. ✅ Implementar check_strategy_triggers avançado
4. ✅ Adicionar trailing stop logic
5. ✅ Implementar circuit breakers
6. ✅ Adicionar trading hours check
7. ✅ Integrar tudo no strategy_worker
8. ✅ Testes completos

Vamos começar? 🎯
