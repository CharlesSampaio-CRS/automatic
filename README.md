# Multi-Exchange Balance API

API para gerenciar e consultar saldos de múltiplas exchanges de criptomoedas.

## 🚀 Início Rápido

### 1. Configurar Ambiente

```bash
# Instalar dependências
pip install -r requirements.txt

# Configurar variáveis de ambiente (.env)
MONGODB_URI=mongodb+srv://user:password@cluster.mongodb.net/
MONGODB_DATABASE=MultExchange
ENCRYPTION_KEY=your_encryption_key_here
```

### 2. Iniciar API

```bash
python3 run.py
```

A API estará disponível em: `http://localhost:5000`

## 📚 Documentação

Consulte [API_DOCUMENTATION.md](./API_DOCUMENTATION.md) para detalhes completos de todos os endpoints.

## 📊 Endpoints Principais

### Exchanges
- `GET /api/v1/exchanges/available` - Listar exchanges disponíveis
- `GET /api/v1/exchanges/{id}` - Detalhes de uma exchange
- `POST /api/v1/exchanges/link` - Vincular exchange
- `DELETE /api/v1/exchanges/unlink` - Desvincular exchange

### Saldos
- `GET /api/v1/balances` - Saldos atuais de todas exchanges
- `GET /api/v1/history` - Histórico de saldos
- `GET /api/v1/history/evolution` - Evolução do portfolio

## 🔧 Scripts Úteis

### Gerar Chave de Criptografia
```bash
python3 scripts/generate_encryption_key.py
```

### Popular Exchanges no MongoDB
```bash
python3 scripts/seed_exchanges.py
```

### Popular Histórico de Teste
```bash
python3 scripts/seed_balance_history.py
```

### Snapshot Horário (Automático)
```bash
# Via Daemon (recomendado para desenvolvimento)
python3 scripts/scheduler_daemon.py

# Via Cron (recomendado para produção)
crontab -e
# Adicionar: 0 * * * * cd /path/to/project && ./scripts/run_hourly_snapshot.sh
```

## 📦 Estrutura do Projeto

```
.
├── src/
│   ├── api/
│   │   └── main.py              # Endpoints da API
│   ├── services/
│   │   ├── balance_service.py   # Lógica de saldos
│   │   └── balance_history_service.py
│   ├── security/
│   │   └── encryption.py        # Criptografia de credenciais
│   └── validators/
│       └── exchange_validator.py
├── scripts/
│   ├── generate_encryption_key.py
│   ├── seed_exchanges.py
│   ├── seed_balance_history.py
│   ├── hourly_balance_snapshot.py
│   └── scheduler_daemon.py
├── run.py                        # Iniciar API
└── requirements.txt              # Dependências
```

## 🔐 Segurança

- Credenciais de exchanges são criptografadas com Fernet
- API keys nunca são expostas em logs
- Use HTTPS em produção

## 🌐 Deploy (Heroku)

```bash
git push heroku main
```

O `Procfile` já está configurado.

## 📝 Licença

Proprietary - Todos os direitos reservados
