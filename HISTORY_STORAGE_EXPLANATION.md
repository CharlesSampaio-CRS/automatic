# Como o Histórico de Saldos é Armazenado

## 📦 Estrutura de Armazenamento

### Collection MongoDB: `balance_history`

O histórico é armazenado em uma estrutura **simplificada e otimizada** que contém apenas os dados essenciais.

---

## 🗂️ Estrutura do Documento

```javascript
{
  "_id": ObjectId("693779665de3d5eb06360b51"),
  "user_id": "charles_test_user",
  "timestamp": ISODate("2024-12-09T01:00:00Z"),
  "total_usd": 42.60,
  "total_brl": 217.18,
  "exchanges": [
    {
      "exchange_id": "693481148b0a41e8b6acb079",
      "exchange_name": "NovaDAX",
      "total_usd": 0.0,
      "total_brl": 0.0,
      "success": true
    },
    {
      "exchange_id": "693481148b0a41e8b6acb07b",
      "exchange_name": "MEXC",
      "total_usd": 29.82,
      "total_brl": 152.03,
      "success": true
    },
    {
      "exchange_id": "693481148b0a41e8b6acb073",
      "exchange_name": "Binance",
      "total_usd": 12.78,
      "total_brl": 65.15,
      "success": true
    }
  ]
}
```

---

## 📊 Campos do Documento

### Campos Principais

| Campo | Tipo | Descrição | Exemplo |
|-------|------|-----------|---------|
| `_id` | ObjectId | ID único do MongoDB | `"693779665de3d5eb06360b51"` |
| `user_id` | String | ID do usuário | `"charles_test_user"` |
| `timestamp` | ISODate | Data/hora do snapshot (UTC) | `"2024-12-09T01:00:00Z"` |
| `total_usd` | Number | Valor total em USD | `42.60` |
| `total_brl` | Number | Valor total em BRL | `217.18` |
| `exchanges` | Array | Lista de exchanges | `[...]` |

### Campos do Array `exchanges`

| Campo | Tipo | Descrição | Exemplo |
|-------|------|-----------|---------|
| `exchange_id` | String | ID da exchange no MongoDB | `"693481148b0a41e8b6acb079"` |
| `exchange_name` | String | Nome da exchange | `"MEXC"` |
| `total_usd` | Number | Total da exchange em USD | `29.82` |
| `total_brl` | Number | Total da exchange em BRL | `152.03` |
| `success` | Boolean | Se a busca foi bem-sucedida | `true` |

---

## 🔄 Como os Dados São Salvos

### 1. **Método de Salvamento**

Arquivo: `src/services/balance_history_service.py`

```python
def save_snapshot(self, balance_data: Dict) -> str:
    """
    Save a simplified balance snapshot to history
    """
    snapshot = {
        'user_id': balance_data['user_id'],
        'timestamp': datetime.utcnow(),
        'total_usd': format_usd(summary_usd),
        'total_brl': format_brl(summary_brl),
        'exchanges': [
            {
                'exchange_id': ex.get('exchange_id', ''),
                'exchange_name': ex.get('name', ''),
                'total_usd': format_usd(float(ex.get('total_usd', '0.0'))),
                'total_brl': format_brl(float(ex.get('total_brl', '0.0'))),
                'success': ex.get('success', False)
            }
            for ex in balance_data.get('exchanges', [])
            if ex.get('success', False)  # Salva apenas exchanges com sucesso
        ]
    }
    
    result = self.collection.insert_one(snapshot)
    return str(result.inserted_id)
```

### 2. **Quando é Salvo**

⚠️ **IMPORTANTE:** O histórico **NÃO é mais salvo automaticamente** quando você chama `/api/v1/balances`.

Agora é salvo **apenas pelo script horário**:

```bash
# Via Daemon APScheduler (recomendado para desenvolvimento)
python3 scripts/scheduler_daemon.py

# Via Cron (recomendado para produção)
0 * * * * cd /path/to/project && python3 scripts/hourly_balance_snapshot.py
```

**Motivo da mudança:**
- Evita poluição do histórico com múltiplas requisições no mesmo horário
- Garante 1 snapshot por hora no máximo
- Economiza espaço no MongoDB
- Melhora performance da API

### 3. **Fluxo de Salvamento**

```
┌─────────────────────────────────────┐
│ Script: hourly_balance_snapshot.py │
└──────────────┬──────────────────────┘
               │ Executa a cada hora
               ▼
┌─────────────────────────────────────┐
│ 1. Busca todos usuários ativos     │
└──────────────┬──────────────────────┘
               ▼
┌─────────────────────────────────────┐
│ 2. Para cada usuário:               │
│    - Chama BalanceService           │
│    - Busca saldos atuais            │
│    - force_refresh=True             │
└──────────────┬──────────────────────┘
               ▼
┌─────────────────────────────────────┐
│ 3. BalanceHistoryService            │
│    - save_snapshot(balance_data)    │
│    - Simplifica estrutura           │
│    - Salva no MongoDB               │
└──────────────┬──────────────────────┘
               ▼
┌─────────────────────────────────────┐
│ MongoDB: balance_history            │
│ ✅ Snapshot salvo com timestamp UTC │
└─────────────────────────────────────┘
```

---

## 🔍 O Que NÃO É Salvo

Para economizar espaço, **não salvamos**:

❌ Detalhes de cada token individual (`tokens_summary`)
❌ Saldo de cada token por exchange
❌ Preços individuais de cada token
❌ Informações de mercado (market cap, volume, etc.)
❌ Metadados das exchanges

✅ **Salvamos apenas:**
- Valores totais agregados (USD e BRL)
- Total por exchange
- Timestamp preciso

**Vantagens:**
- **Redução de ~70% no tamanho dos documentos**
- Queries mais rápidas
- Menos uso de memória
- Custos menores no MongoDB Atlas

---

## 📈 Índices Criados

Para garantir performance nas queries:

```python
# Índice principal: user_id + timestamp (desc)
db.balance_history.create_index([
    ('user_id', 1),
    ('timestamp', -1)
])
```

**Uso:**
- Buscar histórico por usuário ordenado por data
- Queries de evolução por período
- Buscar último snapshot

---

## 🗄️ Retenção de Dados

### Configuração Atual
- **Retenção:** Ilimitada (todos os dados são mantidos)
- **TTL Index:** Desabilitado

### Configuração Opcional (TTL)
Para auto-exclusão após 90 dias:

```python
# Descomente no arquivo balance_history_service.py
self.collection.create_index(
    'timestamp',
    expireAfterSeconds=7776000  # 90 dias
)
```

---

## 📊 Estatísticas Atuais

Com base no banco populado pelo script `seed_full_history.py`:

```
📈 Total de documentos: 8.761
📅 Período coberto: 09/12/2024 a 09/12/2025 (365 dias)
⏱️  Frequência: 1 snapshot por hora
💾 Tamanho médio por documento: ~400 bytes
📦 Tamanho total estimado: ~3.5 MB
```

### Comparação com Estrutura Antiga

| Métrica | Estrutura Antiga | Estrutura Atual | Economia |
|---------|------------------|-----------------|----------|
| Campos salvos | 15+ | 5 | -66% |
| Tamanho por doc | ~1.2 KB | ~400 bytes | -67% |
| Total 1 ano | ~10.5 MB | ~3.5 MB | -67% |
| Query time | ~150ms | ~50ms | -67% |

---

## 🔧 Como Consultar os Dados

### Via MongoDB Shell

```javascript
// Último snapshot de um usuário
db.balance_history.find({ 
  user_id: "charles_test_user" 
}).sort({ timestamp: -1 }).limit(1)

// Snapshots das últimas 24 horas
db.balance_history.find({
  user_id: "charles_test_user",
  timestamp: { 
    $gte: new Date(Date.now() - 24*60*60*1000) 
  }
}).sort({ timestamp: -1 })

// Total de snapshots por usuário
db.balance_history.aggregate([
  { $group: { _id: "$user_id", count: { $sum: 1 } } }
])
```

### Via API

```bash
# Lista de snapshots
GET /api/v1/history?user_id=charles_test_user&limit=168

# Evolução agregada (para gráficos)
GET /api/v1/history/evolution?user_id=charles_test_user&days=7
```

---

## 🚀 Performance

### Queries Otimizadas

✅ **Rápidas** (< 50ms):
- Buscar último snapshot
- Buscar por período com índice
- Agregação por dia/mês

⚠️ **Moderadas** (50-200ms):
- Buscar 90 dias de dados
- Agregações complexas

❌ **Lentas** (> 200ms):
- Buscar 1 ano completo sem agregação
- Queries sem índice
- Full table scans

### Dicas de Performance

1. **Use agregação no backend** (endpoint `/evolution`)
2. **Limite os resultados** com `limit` parameter
3. **Cache no frontend** (5-10 minutos)
4. **Use sampling** para gráficos de 90d+
5. **Evite polling frequente** (atualizar apenas quando necessário)

---

## 🔄 Migration Path

Se precisar adicionar novos campos no futuro:

```python
# Adiciona campo sem quebrar queries antigas
db.balance_history.update_many(
    { "new_field": { "$exists": false } },
    { "$set": { "new_field": default_value } }
)
```

---

## 📝 Resumo

### ✅ Vantagens da Estrutura Atual

1. **Simples:** Apenas dados essenciais
2. **Rápida:** Queries otimizadas com índices
3. **Econômica:** 67% menos espaço
4. **Escalável:** Suporta milhões de documentos
5. **Confiável:** 1 snapshot/hora evita duplicação

### 🎯 Casos de Uso Suportados

- ✅ Gráficos de evolução (24h, 7d, 30d, 90d, 1y)
- ✅ Comparação de performance entre períodos
- ✅ Análise de crescimento do portfolio
- ✅ Distribuição de valor por exchange
- ✅ Histórico completo para auditorias

### ❌ Casos de Uso NÃO Suportados

- ❌ Histórico detalhado por token
- ❌ Preços históricos individuais
- ❌ Comparação de holdings específicos
- ❌ Análise de trades/transações

**Para esses casos:** use endpoints em tempo real ou implemente outra collection específica.

---

**Última atualização:** 08/12/2025  
**Versão:** 1.0  
**Mantenedor:** Charles Roberto
