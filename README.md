# Maverick - Trading Bot

Automated bot for periodic cryptocurrency investments on MEXC exchange with dynamic configuration via REST API.

## 📁 Project Structure

```
maverick/
├── .env                          # Variáveis de ambiente (não versionar)
├── .env.example                  # Exemplo de configuração
├── .gitignore                    # Arquivos ignorados pelo Git
├── requirements.txt              # Dependências Python
├── README.md                     # Este arquivo
│
├── src/                          # Main source code
│   ├── api/                      # REST API
│   │   ├── __init__.py
│   │   └── main.py              # Main Flask application
│   │
│   ├── clients/                  # Exchange clients
│   │   ├── __init__.py
│   │   └── mexc_exchange.py     # MEXC client
│   │
│   ├── config/                   # Configurations
│   │   ├── __init__.py
│   │   ├── bot_config.py        # Configuration manager
│   │   └── settings.json        # Persistent settings
│   │
│   ├── database/                 # Database connections
│   │   ├── __init__.py
│   │   └── mongodb_connection.py
│   │
│   ├── models/                   # Data models
│   │   └── __init__.py
│   │
│   └── utils/                    # Utilities
│       └── __init__.py
│
├── tests/                        # Tests
│   ├── __init__.py
│   └── test_mexc_integration.py # MEXC integration test
│
├── scripts/                      # Utility scripts
│   └── test_api_endpoints.sh    # API endpoints test
│
└── docs/                         # Documentation
    ├── API_REFERENCE.md         # Complete API reference
    └── CLEANUP.md               # Project cleanup history
```

## Quick Start

### 1. Install dependencies
```bash
pip3 install -r requirements.txt
```

### 2. Configure environment variables
Edit the `.env` file:
```env
API_KEY=your_mexc_api_key
API_SECRET=your_mexc_api_secret
MONGODB_URI=your_mongodb_connection
```

### 3. Run
```bash
cd src/api
python3 main.py
```

API will be available at: `http://localhost:5000`

## 🧪 Testing

### MEXC integration test
```bash
python3 tests/test_mexc_integration.py
```

### API endpoints test
```bash
bash scripts/test_api_endpoints.sh
```

## 📡 API Endpoints

### Trading
- `GET /` - API status
- `GET /balance` - Check balance
- `GET /order` - Execute manual order

### Configuration
- `GET /config` - View all configurations
- `GET /config/symbols` - List symbols
- `POST /config/symbols` - Add symbol
- `PUT /config/symbols/{pair}` - Update symbol
- `DELETE /config/symbols/{pair}` - Remove symbol
- `GET /config/base-currency` - View base currency
- `PUT /config/base-currency` - Change base currency
- `GET /config/trading-params` - View parameters
- `PUT /config/trading-params` - Update parameters
- `POST /config/reset` - Reset configurations

📚 **Complete documentation**: [`docs/API_REFERENCE.md`](docs/API_REFERENCE.md)

## ⚙️ Symbol Configuration

Each symbol has:

```json
{
  "pair": "BTC/USDT",
  "enabled": true,
  "min_variation_positive": 2.0,    // Buy if goes up 2%+
  "max_variation_negative": -5.0,   // Buy if drops up to -5%
  "allocation_percentage": 25.0     // 25% of balance
}
```

### Percentages Explained

**`min_variation_positive`**: Buy when it rises
- Example: `2.0` = Buy if it rises 2% in last 24h

**`max_variation_negative`**: Buy when it falls (protection)
- Example: `-5.0` = Buy up to -5% drop
- Won't buy if it drops more than that

**`allocation_percentage`**: Balance distribution
- Example: `25.0` = 25% of total balance
- Sum of all should be ~100%

## 🔧 Technologies

- **Python 3.9+**
- **Flask** - REST API
- **CCXT** - Exchange integration
- **MongoDB** - Data persistence
- **APScheduler** - Periodic execution
- **python-dotenv** - Environment variables

##  License

Personal use project.

---

**Developed with ❤️ by Charles Roberto**
