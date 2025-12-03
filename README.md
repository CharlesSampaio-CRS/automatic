# 🚀 Maverick - Tranding Bot

Bot automatizado para realizar investimentos periódicos em criptomoedas na exchange MEXC com configuração dinâmica via API REST.

## 📁 Estrutura do Projeto

```
maverick/
├── .env                          # Variáveis de ambiente (não versionar)
├── .env.example                  # Exemplo de configuração
├── .gitignore                    # Arquivos ignorados pelo Git
├── requirements.txt              # Dependências Python
├── README.md                     # Este arquivo
│
├── src/                          # Código fonte principal
│   ├── api/                      # API REST
│   │   ├── __init__.py
│   │   └── main.py              # Aplicação Flask principal
│   │
│   ├── clients/                  # Clientes de exchanges
│   │   ├── __init__.py
│   │   └── mexc_exchange.py     # Cliente MEXC
│   │
│   ├── config/                   # Configurações
│   │   ├── __init__.py
│   │   ├── bot_config.py        # Gerenciador de configurações
│   │   └── settings.json        # Configurações persistentes
│   │
│   ├── database/                 # Conexões de banco de dados
│   │   ├── __init__.py
│   │   └── mongodb_connection.py
│   │
│   ├── models/                   # Modelos de dados
│   │   └── __init__.py
│   │
│   └── utils/                    # Utilitários
│       └── __init__.py
│
├── tests/                        # Testes
│   ├── __init__.py
│   └── test_mexc_integration.py # Teste de integração MEXC
│
├── scripts/                      # Scripts utilitários
│   └── test_api_endpoints.sh    # Teste de endpoints da API
│
└── docs/                         # Documentação
    ├── API_REFERENCE.md         # Referência completa da API
    └── CLEANUP.md               # Histórico de limpeza do projeto
```

## 🚀 Quick Start

### 1. Instalar dependências
```bash
pip3 install -r requirements.txt
```

### 2. Configurar variáveis de ambiente
Edite o arquivo `.env`:
```env
API_KEY=sua_api_key_da_mexc
API_SECRET=seu_api_secret_da_mexc
MONGODB_URI=sua_conexao_mongodb
```

### 3. Executar
```bash
cd src/api
python3 main.py
```

A API estará disponível em: `http://localhost:5000`

## 🧪 Testar

### Teste de integração MEXC
```bash
python3 tests/test_mexc_integration.py
```

### Teste de endpoints da API
```bash
bash scripts/test_api_endpoints.sh
```

## 📡 API Endpoints

### Tranding
- `GET /` - Status da API
- `GET /balance` - Consultar saldo
- `GET /order` - Executar ordem manual

### Configuração
- `GET /config` - Ver todas as configurações
- `GET /config/symbols` - Listar símbolos
- `POST /config/symbols` - Adicionar símbolo
- `PUT /config/symbols/{pair}` - Atualizar símbolo
- `DELETE /config/symbols/{pair}` - Remover símbolo
- `GET /config/base-currency` - Ver moeda base
- `PUT /config/base-currency` - Alterar moeda base
- `GET /config/Tranding-params` - Ver parâmetros
- `PUT /config/Tranding-params` - Atualizar parâmetros
- `POST /config/reset` - Resetar configurações

📚 **Documentação completa**: [`docs/API_REFERENCE.md`](docs/API_REFERENCE.md)

## ⚙️ Configuração de Símbolos

Cada símbolo possui:

```json
{
  "pair": "BTC/USDT",
  "enabled": true,
  "min_variation_positive": 2.0,    // Comprar se subir 2%+
  "max_variation_negative": -5.0,   // Comprar se cair até -5%
  "allocation_percentage": 25.0     // 25% do saldo
}
```

### Percentuais Explicados

**`min_variation_positive`**: Comprar quando sobe
- Exemplo: `2.0` = Comprar se subir 2% nas últimas 24h

**`max_variation_negative`**: Comprar quando cai (proteção)
- Exemplo: `-5.0` = Comprar até -5% de queda
- Não compra se cair mais que isso

**`allocation_percentage`**: Distribuição do saldo
- Exemplo: `25.0` = 25% do saldo total
- Soma de todos deve ser ~100%

## 🔧 Tecnologias

- **Python 3.9+**
- **Flask** - API REST
- **CCXT** - Integração com exchanges
- **MongoDB** - Persistência de dados
- **APScheduler** - Execução periódica
- **python-dotenv** - Variáveis de ambiente

## 📝 Licença

Projeto de uso pessoal.

---

**Desenvolvido com ❤️ por Charles Roberto**
