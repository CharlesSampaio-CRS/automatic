# 🔧 Guia de Controle de Jobs - Sistema de Trading

## 📋 Respostas às suas perguntas:

### 1️⃣ **O job de verificação vai rodar a cada quanto tempo?**

**Resposta:** O **Strategy Worker** roda a cada **5 minutos por padrão**.

```env
# Configurável via variável de ambiente
STRATEGY_CHECK_INTERVAL=5  # minutos
```

**Como funciona:**
- A cada 5 minutos, o worker verifica TODAS as estratégias ativas
- Compara preço atual vs preço de entrada
- Se detectar gatilho (take profit, stop loss, buy dip), executa ordem automaticamente
- Cria notificação para o usuário

**Logs de exemplo:**
```
[12:00:00] 🔍 Checking all active strategies...
[12:00:00] Found 3 active strategies to check
[12:00:01] ✅ Strategy check completed - Triggered: 0, Total: 3
[12:05:00] 🔍 Checking all active strategies...
[12:05:00] Found 3 active strategies to check
[12:05:02] 🎯 STRATEGY TRIGGERED! Token: BTC, Action: SELL, Reason: TAKE_PROFIT
[12:05:03] ✅ Order executed successfully!
```

**Para alterar o intervalo:**
```bash
# No .env ou na linha de comando
export STRATEGY_CHECK_INTERVAL=3  # Verifica a cada 3 minutos
export STRATEGY_CHECK_INTERVAL=10 # Verifica a cada 10 minutos
```

---

### 2️⃣ **Se o usuário quiser executar uma venda ou compra manual, tem como?**

**Resposta:** ✅ **SIM! Existem endpoints específicos para isso.**

#### **Execução Manual de Compra**

```http
POST /api/v1/orders/buy
Content-Type: application/json

{
  "user_id": "user123",
  "exchange_id": "65abc123...",
  "token": "BTC",
  "amount": 0.5,
  "order_type": "market",  // ou "limit"
  "price": 45000           // obrigatório apenas para limit orders
}
```

**Response:**
```json
{
  "success": true,
  "dry_run": true,  // Se está em modo teste
  "order": {
    "id": "ORDER_12345",
    "symbol": "BTC/USDT",
    "type": "market",
    "side": "buy",
    "amount": 0.5,
    "filled": 0.5,
    "average": 45123.45,
    "cost": 22561.73,
    "status": "closed",
    "fee": {
      "cost": 22.56,
      "currency": "USDT"
    }
  }
}
```

#### **Execução Manual de Venda**

```http
POST /api/v1/orders/sell
Content-Type: application/json

{
  "user_id": "user123",
  "exchange_id": "65abc123...",
  "token": "BTC",
  "amount": 0.3,
  "order_type": "limit",
  "price": 47000
}
```

**Tipos de ordem suportados:**
- **market:** Executa imediatamente ao preço de mercado
- **limit:** Só executa quando preço atingir o valor especificado

**Importante:**
- ✅ As ordens manuais também **atualizam automaticamente a posição**
- ✅ Se comprar, adiciona ao histórico de compras e recalcula entry price
- ✅ Se vender, calcula P&L e adiciona ao histórico de vendas
- ✅ Respeita o modo DRY-RUN configurado no sistema

---

### 3️⃣ **Tem um endpoint com a lista dos jobs?**

**Resposta:** ✅ **SIM! Endpoint criado agora!**

```http
GET /api/v1/jobs/status
```

**Response:**
```json
{
  "success": true,
  "jobs": {
    "balance_snapshot": {
      "name": "Balance Snapshot",
      "description": "Captures balance snapshots for portfolio history",
      "running": true,
      "schedule": "Every 4 hours (00:00, 04:00, 08:00, 12:00, 16:00, 20:00 UTC)",
      "next_run": "2024-12-10T16:00:00Z",
      "last_run": null
    },
    "strategy_worker": {
      "name": "Strategy Worker",
      "description": "Monitors strategies and executes automated trades",
      "running": true,
      "check_interval_minutes": 5,
      "dry_run_mode": true,
      "schedule": "Every 5 minutes"
    }
  },
  "summary": {
    "total_jobs": 2,
    "running_jobs": 2,
    "stopped_jobs": 0
  }
}
```

**Informações retornadas:**
- ✅ Status de cada job (rodando ou parado)
- ✅ Intervalo de execução
- ✅ Próxima execução agendada
- ✅ Modo DRY-RUN ativo ou não
- ✅ Resumo geral do sistema

---

### 4️⃣ **Tem endpoint para ligar e desligar esses jobs?**

**Resposta:** ✅ **SIM! Controle completo criado agora!**

#### **Controlar Jobs (Start/Stop/Restart)**

```http
POST /api/v1/jobs/control
Content-Type: application/json

{
  "job": "strategy_worker",
  "action": "stop"
}
```

**Parâmetros:**
- `job`: 
  - `"strategy_worker"` - Bot de estratégias
  - `"balance_snapshot"` - Snapshot de saldos
- `action`:
  - `"start"` - Iniciar job
  - `"stop"` - Parar job
  - `"restart"` - Reiniciar job

**Response:**
```json
{
  "success": true,
  "message": "Strategy Worker stopped successfully",
  "job": "strategy_worker",
  "action": "stop",
  "new_status": "stopped"
}
```

#### **Exemplos de Uso:**

**Parar o Strategy Worker (pausar trading automático):**
```bash
curl -X POST http://localhost:5000/api/v1/jobs/control \
  -H "Content-Type: application/json" \
  -d '{
    "job": "strategy_worker",
    "action": "stop"
  }'
```

**Reiniciar o Strategy Worker:**
```bash
curl -X POST http://localhost:5000/api/v1/jobs/control \
  -H "Content-Type: application/json" \
  -d '{
    "job": "strategy_worker",
    "action": "restart"
  }'
```

**Parar os snapshots de saldo:**
```bash
curl -X POST http://localhost:5000/api/v1/jobs/control \
  -H "Content-Type: application/json" \
  -d '{
    "job": "balance_snapshot",
    "action": "stop"
  }'
```

---

### 5️⃣ **BONUS: Trigger Manual de Jobs**

Você também pode **forçar a execução imediata** de um job (fora do schedule):

```http
POST /api/v1/jobs/trigger/<job_name>
```

**Exemplos:**

**Forçar verificação de estratégias AGORA:**
```bash
curl -X POST http://localhost:5000/api/v1/jobs/trigger/strategy_worker
```

**Response:**
```json
{
  "success": true,
  "message": "Strategy Worker check triggered successfully",
  "job": "strategy_worker",
  "triggered_at": "2024-12-10T14:35:00Z"
}
```

**Forçar snapshot de saldos AGORA:**
```bash
curl -X POST http://localhost:5000/api/v1/jobs/trigger/balance_snapshot
```

---

## 🎛️ Resumo dos Endpoints de Controle

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/api/v1/jobs/status` | GET | Lista todos os jobs e seus status |
| `/api/v1/jobs/control` | POST | Start/Stop/Restart de jobs individuais |
| `/api/v1/jobs/trigger/:job` | POST | Executa job manualmente (fora do schedule) |
| `/api/v1/orders/buy` | POST | Execução manual de compra |
| `/api/v1/orders/sell` | POST | Execução manual de venda |

---

## 🎯 Casos de Uso Práticos

### **Caso 1: Pausar trading temporariamente**
```bash
# Parar o strategy worker
curl -X POST http://localhost:5000/api/v1/jobs/control \
  -d '{"job": "strategy_worker", "action": "stop"}'

# Verificar status
curl http://localhost:5000/api/v1/jobs/status
```

### **Caso 2: Vender manualmente antes de uma queda**
```bash
# Executar venda manual
curl -X POST http://localhost:5000/api/v1/orders/sell \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "exchange_id": "65abc...",
    "token": "BTC",
    "amount": 0.5,
    "order_type": "market"
  }'
```

### **Caso 3: Testar estratégias forçando verificação**
```bash
# Forçar verificação de estratégias imediatamente
curl -X POST http://localhost:5000/api/v1/jobs/trigger/strategy_worker

# Ver logs para confirmar
tail -f logs/app.log
```

### **Caso 4: Reativar trading após manutenção**
```bash
# Reiniciar strategy worker
curl -X POST http://localhost:5000/api/v1/jobs/control \
  -d '{"job": "strategy_worker", "action": "restart"}'
```

---

## 📊 Interface para Frontend

### **Dashboard de Jobs (React/Vue)**

```typescript
import { TradingApiClient } from '@/services/api-client';

function JobsControlPanel() {
  const [jobsStatus, setJobsStatus] = useState<any>(null);
  const api = new TradingApiClient();
  
  useEffect(() => {
    loadJobsStatus();
  }, []);
  
  const loadJobsStatus = async () => {
    const response = await api.getJobsStatus();
    if (response.success) {
      setJobsStatus(response.jobs);
    }
  };
  
  const controlJob = async (job: string, action: string) => {
    await api.controlJob({ job, action });
    loadJobsStatus();
  };
  
  return (
    <div className="jobs-panel">
      <h2>Controle de Jobs</h2>
      
      {/* Strategy Worker */}
      <div className="job-card">
        <h3>🤖 Strategy Worker</h3>
        <div className="status">
          Status: {jobsStatus?.strategy_worker.running ? '🟢 Rodando' : '🔴 Parado'}
        </div>
        <div className="info">
          Intervalo: {jobsStatus?.strategy_worker.check_interval_minutes} min
        </div>
        <div className="info">
          Modo: {jobsStatus?.strategy_worker.dry_run_mode ? '🧪 DRY-RUN' : '💰 LIVE'}
        </div>
        
        <div className="actions">
          <button onClick={() => controlJob('strategy_worker', 'start')}>
            ▶️ Start
          </button>
          <button onClick={() => controlJob('strategy_worker', 'stop')}>
            ⏸️ Stop
          </button>
          <button onClick={() => controlJob('strategy_worker', 'restart')}>
            🔄 Restart
          </button>
          <button onClick={() => api.triggerJob('strategy_worker')}>
            ⚡ Trigger Now
          </button>
        </div>
      </div>
      
      {/* Balance Snapshot */}
      <div className="job-card">
        <h3>📸 Balance Snapshot</h3>
        <div className="status">
          Status: {jobsStatus?.balance_snapshot.running ? '🟢 Rodando' : '🔴 Parado'}
        </div>
        <div className="info">
          Schedule: {jobsStatus?.balance_snapshot.schedule}
        </div>
        <div className="info">
          Next Run: {jobsStatus?.balance_snapshot.next_run}
        </div>
        
        <div className="actions">
          <button onClick={() => controlJob('balance_snapshot', 'start')}>
            ▶️ Start
          </button>
          <button onClick={() => controlJob('balance_snapshot', 'stop')}>
            ⏸️ Stop
          </button>
          <button onClick={() => api.triggerJob('balance_snapshot')}>
            ⚡ Trigger Now
          </button>
        </div>
      </div>
    </div>
  );
}
```

---

## ⚠️ Notas Importantes

1. **Segurança:** Adicione autenticação/autorização nos endpoints de controle em produção
2. **Logs:** Todas as ações de controle são registradas nos logs do sistema
3. **DRY-RUN Mode:** Ordens manuais também respeitam o modo DRY-RUN configurado
4. **Persistência:** Jobs são reiniciados automaticamente quando o Flask reinicia
5. **Race Conditions:** Stop/Start é seguro, mas evite múltiplas requisições simultâneas

---

## ✅ Checklist de Implementação no Frontend

- [ ] Criar painel de status de jobs
- [ ] Botões para Start/Stop/Restart
- [ ] Indicador visual de status (verde/vermelho)
- [ ] Botão de trigger manual
- [ ] Formulário de execução manual de ordem
- [ ] Confirmação antes de parar jobs
- [ ] Refresh automático de status (polling)
- [ ] Toast notifications para ações de controle

---

**🎉 Sistema de controle completo implementado!**

Agora você tem controle total sobre:
- ✅ Status de todos os jobs
- ✅ Start/Stop/Restart individual
- ✅ Trigger manual fora do schedule
- ✅ Execução manual de ordens buy/sell
- ✅ Monitoramento em tempo real
