# 🕐 Automated Balance Snapshot Jobs

## 📋 Visão Geral

O sistema possui 2 scripts Python essenciais para coletar snapshots automáticos de saldos:

1. **`scheduler_daemon.py`** - Daemon do APScheduler (job principal)
2. **`hourly_balance_snapshot.py`** - Lógica de coleta de snapshots

---

## 🚀 Como Rodar em Produção

### Opção 1: Rodar como Daemon (Recomendado)

```bash
# Ativa o ambiente virtual
source .venv/bin/activate

# Roda o scheduler (fica em background)
python scripts/scheduler_daemon.py
```

O scheduler vai executar automaticamente a cada 4 horas:
- 00:00 UTC
- 04:00 UTC
- 08:00 UTC
- 12:00 UTC
- 16:00 UTC
- 20:00 UTC

### Opção 2: Rodar Manualmente (Teste)

```bash
# Ativa o ambiente virtual
source .venv/bin/activate

# Executa snapshot imediatamente
python scripts/hourly_balance_snapshot.py
```

---

## 🐳 Deploy com Docker/Systemd

### Usando Systemd (Linux)

Crie o arquivo `/etc/systemd/system/balance-scheduler.service`:

```ini
[Unit]
Description=Balance Snapshot Scheduler
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/automatic
Environment="PATH=/path/to/automatic/.venv/bin"
ExecStart=/path/to/automatic/.venv/bin/python scripts/scheduler_daemon.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Depois:
```bash
sudo systemctl enable balance-scheduler
sudo systemctl start balance-scheduler
sudo systemctl status balance-scheduler
```

### Usando Docker (Dockerfile exemplo)

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . .

RUN pip install -r requirements.txt

# Roda o scheduler como processo principal
CMD ["python", "scripts/scheduler_daemon.py"]
```

---

## 📊 O Que Cada Script Faz

### `scheduler_daemon.py` ⭐
- Usa APScheduler (não precisa de cron)
- Multi-plataforma (Windows, Linux, Mac)
- Agenda execução a cada 4 horas
- Chama `run_hourly_snapshot()` automaticamente
- Logs estruturados com timestamp

### `hourly_balance_snapshot.py` ⭐
- Busca todos os usuários ativos no MongoDB
- Para cada usuário:
  - Coleta saldos de todas exchanges vinculadas
  - Calcula totais em USD e BRL
  - Salva snapshot na collection `balance_history`
- Fornece resumo de sucesso/falha

---

## 🔍 Verificar se Está Funcionando

### Ver logs do scheduler:
```bash
# Se rodando no terminal
# Os logs aparecem diretamente na tela

# Se rodando com systemd
sudo journalctl -u balance-scheduler -f
```

### Verificar snapshots salvos no MongoDB:
```javascript
// MongoDB shell
use balance_tracker

// Ver últimos 10 snapshots
db.balance_history.find().sort({timestamp: -1}).limit(10)

// Contar snapshots de hoje
db.balance_history.countDocuments({
  timestamp: {
    $gte: new Date(new Date().setHours(0,0,0,0))
  }
})
```

---

## ⚙️ Configuração

### Variáveis de Ambiente (.env)
```bash
MONGODB_URI=mongodb://localhost:27017/
MONGODB_DATABASE=balance_tracker

# Opcional: ajustar intervalo (padrão: 4 horas)
SNAPSHOT_INTERVAL_HOURS=4
```

### Modificar Frequência

Edite `scripts/scheduler_daemon.py`:

```python
# Linha 59-60
scheduler.add_job(
    scheduled_snapshot,
    trigger=CronTrigger(minute=0, hour='*/4'),  # Mude aqui
    # Exemplos:
    # A cada 1 hora: hour='*'
    # A cada 6 horas: hour='*/6'
    # A cada 12 horas: hour='*/12'
    # Diariamente às 00:00: hour=0
)
```

---

## 🧪 Testar Imports

```bash
python3 -c "
from scripts.hourly_balance_snapshot import run_hourly_snapshot
from scripts.scheduler_daemon import main
print('✅ All imports working!')
"
```

---

## ❓ Troubleshooting

### Erro: "ModuleNotFoundError"
```bash
# Certifique-se de estar no diretório correto
cd /path/to/automatic

# E com o venv ativo
source .venv/bin/activate
```

### Erro: "Connection to MongoDB failed"
```bash
# Verifique se MongoDB está rodando
mongosh --eval "db.adminCommand('ping')"

# Verifique a variável MONGODB_URI no .env
cat .env | grep MONGODB_URI
```

### Scheduler não inicia
```bash
# Verifique se já existe outro processo rodando
ps aux | grep scheduler_daemon

# Kill se necessário
pkill -f scheduler_daemon.py
```

---

## 📝 Notas Importantes

- ✅ **100% Python** - Sem dependência de bash/cron
- ✅ **Multi-plataforma** - Funciona em Windows, Linux, Mac
- ✅ **Logs estruturados** - Usa sistema de logging centralizado
- ✅ **Intervalo otimizado** - 4 horas = 6 snapshots/dia (75% economia vs 1h)
- ✅ **Idempotente** - Seguro rodar múltiplas vezes
- ✅ **Error handling** - Continua funcionando mesmo se um usuário falhar

---

## 🔗 Arquitetura

```
scheduler_daemon.py (APScheduler)
    │
    ├─ CronTrigger(minute=0, hour='*/4')
    │
    └─► scheduled_snapshot()
         │
         └─► run_hourly_snapshot()
              │
              ├─ get_all_active_users(db)
              │
              └─ for each user:
                  ├─ BalanceService.get_balances()
                  └─ BalanceHistoryService.save_snapshot()
```

---

✅ **Sistema testado e funcional!**
