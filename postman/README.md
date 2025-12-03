# 📮 Postman Collection - Bot Trading MEXC

Collection completa do Postman com todos os endpoints da API do Bot de Trading Automático.

## 📦 Arquivos

- **`Bot_Trading_MEXC_API.postman_collection.json`** - Collection principal com todos os endpoints
- **`Bot_Trading_MEXC_Local.postman_environment.json`** - Environment para desenvolvimento local
- **`Bot_Trading_MEXC_Production.postman_environment.json`** - Environment para produção

## 🚀 Como Importar no Postman

### Método 1: Interface do Postman

1. Abra o Postman
2. Clique em **Import** (canto superior esquerdo)
3. Selecione **File** ou arraste os arquivos:
   - `Bot_Trading_MEXC_API.postman_collection.json`
   - `Bot_Trading_MEXC_Local.postman_environment.json`
   - `Bot_Trading_MEXC_Production.postman_environment.json`
4. Clique em **Import**

### Método 2: Via CLI (se tiver Postman CLI)

```bash
postman collection import Bot_Trading_MEXC_API.postman_collection.json
postman environment import Bot_Trading_MEXC_Local.postman_environment.json
```

## ⚙️ Configuração

### Selecionar Environment

1. No canto superior direito do Postman
2. Clique no dropdown de **Environments**
3. Selecione: **Bot Trading MEXC - Local** (para testes locais)

### Variáveis Disponíveis

| Variável | Valor Padrão | Descrição |
|----------|--------------|-----------|
| `base_url` | `http://localhost:5000` | URL base da API |
| `symbol` | `BTC/USDT` | Símbolo para testes |

### Personalizar Variáveis

1. Clique no ícone de **olho** (👁️) no canto superior direito
2. Clique em **Edit** ao lado do environment
3. Modifique os valores conforme necessário
4. Clique em **Save**

## 📚 Estrutura da Collection

### 1. **Trading** (3 endpoints)
- ✅ Status da API
- 💰 Consultar Saldo
- 🛒 Executar Ordem Manual

### 2. **Configuração** (2 endpoints)
- 📋 Ver Todas Configurações
- 🔄 Reset Configurações

### 3. **Símbolos** (5 endpoints)
- 📊 Listar Todos Símbolos
- 🔍 Ver Símbolo Específico
- ➕ Adicionar Símbolo
- ✏️ Atualizar Símbolo
- ❌ Remover Símbolo

### 4. **Moeda Base** (2 endpoints)
- 💵 Ver Moeda Base
- 🔄 Atualizar Moeda Base

### 5. **Parâmetros de Trading** (2 endpoints)
- 📊 Ver Parâmetros
- ✏️ Atualizar Parâmetros

## 🧪 Exemplos de Uso

### 1. Verificar Status da API

**Request:**
```
GET {{base_url}}/
```

**Response:**
```json
{
  "message": "API is running!"
}
```

### 2. Adicionar Novo Símbolo

**Request:**
```
POST {{base_url}}/config/symbols
Content-Type: application/json

{
  "pair": "BTC/USDT",
  "enabled": true,
  "min_variation_positive": 2.0,
  "max_variation_negative": -5.0,
  "allocation_percentage": 25.0
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Símbolo BTC/USDT adicionado com sucesso",
  "symbol": {...}
}
```

### 3. Listar Todos os Símbolos

**Request:**
```
GET {{base_url}}/config/symbols
```

**Response:**
```json
{
  "status": "success",
  "total": 3,
  "enabled": 2,
  "symbols": [
    {
      "pair": "GROK/USDT",
      "enabled": true,
      "min_variation_positive": 2.0,
      "max_variation_negative": -5.0,
      "allocation_percentage": 33.33
    },
    ...
  ]
}
```

### 4. Atualizar Símbolo

**Request:**
```
PUT {{base_url}}/config/symbols/BTC/USDT
Content-Type: application/json

{
  "enabled": false,
  "allocation_percentage": 30.0
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Símbolo BTC/USDT atualizado com sucesso",
  "symbol": {...}
}
```

### 5. Consultar Saldo

**Request:**
```
GET {{base_url}}/balance
```

**Response:**
```json
{
  "total_assets_usdt": 100.50,
  "available_usdt": 50.25,
  "total_usdt": 150.75,
  "date": "2025-12-02T10:30:00-03:00",
  "tokens": [...]
}
```

## 🔧 Dicas de Uso

### Usar Variáveis nas Requests

Nas requests, use `{{variable_name}}` para referenciar variáveis:

```
GET {{base_url}}/config/symbols/{{symbol}}
```

### Salvar Responses como Exemplos

1. Execute uma request
2. Clique em **Save Response**
3. Dê um nome ao exemplo
4. Agora outros usuários podem ver exemplos de respostas

### Criar Testes Automatizados

No Postman, vá até a aba **Tests** e adicione:

```javascript
// Verificar se a resposta é 200 OK
pm.test("Status code is 200", function () {
    pm.response.to.have.status(200);
});

// Verificar estrutura da resposta
pm.test("Response has status field", function () {
    var jsonData = pm.response.json();
    pm.expect(jsonData).to.have.property('status');
});

// Salvar variável para próxima request
pm.test("Save symbol from response", function () {
    var jsonData = pm.response.json();
    pm.environment.set("symbol", jsonData.symbol.pair);
});
```

### Executar Collection Inteira

1. Clique nos **3 pontos** ao lado da collection
2. Selecione **Run collection**
3. Configure ordem e delays
4. Clique em **Run**

## 🔄 Workflow Recomendado

### Configuração Inicial

1. ✅ **Status da API** - Verificar se está rodando
2. 📋 **Ver Todas Configurações** - Ver configuração atual
3. 📊 **Listar Todos Símbolos** - Ver símbolos existentes

### Adicionar Novo Símbolo

1. ➕ **Adicionar Símbolo** - Criar novo
2. 🔍 **Ver Símbolo Específico** - Confirmar adição
3. 📊 **Listar Todos Símbolos** - Ver lista atualizada

### Testar Trading

1. 💰 **Consultar Saldo** - Ver saldo disponível
2. 🛒 **Executar Ordem Manual** - Testar execução
3. 💰 **Consultar Saldo** - Verificar mudanças

## 📝 Notas Importantes

- ⚠️ **Certifique-se de que o bot está rodando** antes de testar
- 🔧 **Use o environment correto** (Local ou Production)
- 💾 **Salve alterações** nas variáveis quando modificar
- 🧪 **Teste em Local** antes de usar em Production
- 📊 **Monitore os logs** do bot durante os testes

## 🆘 Troubleshooting

### "Could not get any response"

```bash
# Verificar se o bot está rodando
curl http://localhost:5000/

# Iniciar o bot se não estiver rodando
python3 run.py
```

### "Error: connect ECONNREFUSED"

- Verifique se a porta está correta (padrão: 5000)
- Verifique se não há firewall bloqueando
- Teste com `curl` no terminal primeiro

### Símbolo não funciona

- Certifique-se de usar o formato correto: `BTC/USDT`
- URL encode se necessário: `BTC%2FUSDT`
- Verifique se o símbolo existe na MEXC

## 📚 Recursos Adicionais

- 📖 [Documentação Completa da API](../docs/API_REFERENCE.md)
- 🚀 [Comandos Úteis](../COMMANDS.md)
- 📘 [README Principal](../README.md)

---

**Desenvolvido com ❤️ para facilitar o desenvolvimento**
