# API de Histórico de Saldos - Exemplos para Frontend

## Endpoint Principal

```
GET /api/v1/history/evolution
```

Este endpoint retorna a evolução do portfolio agregada por períodos, ideal para exibir em gráficos.

---

## 📊 Exemplo 1: Últimas 24 Horas

### Request
```bash
GET /api/v1/history/evolution?user_id=charles_test_user&days=1
```

### Response (200 OK)
```json
{
  "success": true,
  "user_id": "charles_test_user",
  "days": 1,
  "evolution": {
    "period": "2025-12-07T16:00:00 to 2025-12-08T16:00:00",
    "data_points": [
      {
        "timestamp": "2025-12-07T17:00:00.000Z",
        "total_usd": 162.45,
        "total_brl": 835.61
      },
      {
        "timestamp": "2025-12-07T18:00:00.000Z",
        "total_usd": 163.12,
        "total_brl": 839.05
      },
      {
        "timestamp": "2025-12-07T19:00:00.000Z",
        "total_usd": 162.89,
        "total_brl": 837.87
      },
      {
        "timestamp": "2025-12-07T20:00:00.000Z",
        "total_usd": 164.23,
        "total_brl": 844.77
      },
      {
        "timestamp": "2025-12-07T21:00:00.000Z",
        "total_usd": 163.56,
        "total_brl": 841.32
      },
      {
        "timestamp": "2025-12-07T22:00:00.000Z",
        "total_usd": 165.01,
        "total_brl": 848.78
      },
      {
        "timestamp": "2025-12-07T23:00:00.000Z",
        "total_usd": 164.78,
        "total_brl": 847.60
      },
      {
        "timestamp": "2025-12-08T00:00:00.000Z",
        "total_usd": 163.92,
        "total_brl": 843.18
      },
      {
        "timestamp": "2025-12-08T01:00:00.000Z",
        "total_usd": 164.45,
        "total_brl": 845.91
      },
      {
        "timestamp": "2025-12-08T02:00:00.000Z",
        "total_usd": 165.23,
        "total_brl": 849.91
      },
      {
        "timestamp": "2025-12-08T03:00:00.000Z",
        "total_usd": 164.89,
        "total_brl": 848.16
      },
      {
        "timestamp": "2025-12-08T04:00:00.000Z",
        "total_usd": 166.12,
        "total_brl": 854.48
      },
      {
        "timestamp": "2025-12-08T05:00:00.000Z",
        "total_usd": 165.67,
        "total_brl": 852.17
      },
      {
        "timestamp": "2025-12-08T06:00:00.000Z",
        "total_usd": 167.34,
        "total_brl": 860.76
      },
      {
        "timestamp": "2025-12-08T07:00:00.000Z",
        "total_usd": 166.89,
        "total_brl": 858.44
      },
      {
        "timestamp": "2025-12-08T08:00:00.000Z",
        "total_usd": 168.12,
        "total_brl": 864.76
      },
      {
        "timestamp": "2025-12-08T09:00:00.000Z",
        "total_usd": 167.56,
        "total_brl": 861.88
      },
      {
        "timestamp": "2025-12-08T10:00:00.000Z",
        "total_usd": 169.23,
        "total_brl": 870.47
      },
      {
        "timestamp": "2025-12-08T11:00:00.000Z",
        "total_usd": 168.45,
        "total_brl": 866.46
      },
      {
        "timestamp": "2025-12-08T12:00:00.000Z",
        "total_usd": 170.12,
        "total_brl": 875.04
      },
      {
        "timestamp": "2025-12-08T13:00:00.000Z",
        "total_usd": 169.67,
        "total_brl": 872.73
      },
      {
        "timestamp": "2025-12-08T14:00:00.000Z",
        "total_usd": 171.34,
        "total_brl": 881.32
      },
      {
        "timestamp": "2025-12-08T15:00:00.000Z",
        "total_usd": 170.89,
        "total_brl": 879.00
      },
      {
        "timestamp": "2025-12-08T16:00:00.000Z",
        "total_usd": 172.23,
        "total_brl": 885.89
      }
    ],
    "summary": {
      "period_days": 1,
      "data_points": 24,
      "start_value_usd": 162.45,
      "end_value_usd": 172.23,
      "change_usd": 9.78,
      "change_percent": 6.02,
      "min_value_usd": 162.45,
      "max_value_usd": 172.23,
      "avg_value_usd": 166.34
    }
  }
}
```

**Uso no Frontend:**
- Gráfico de linha com 24 pontos (1 por hora)
- Ideal para mostrar variações intraday
- Atualizar a cada hora

---

## 📊 Exemplo 2: Últimos 7 Dias

### Request
```bash
GET /api/v1/history/evolution?user_id=charles_test_user&days=7
```

### Response (200 OK)
```json
{
  "success": true,
  "user_id": "charles_test_user",
  "days": 7,
  "evolution": {
    "period": "2025-12-01T16:00:00 to 2025-12-08T16:00:00",
    "data_points": [
      {
        "date": "2025-12-01",
        "total_usd": 148.23,
        "total_brl": 762.58,
        "snapshots_count": 24
      },
      {
        "date": "2025-12-02",
        "total_usd": 151.67,
        "total_brl": 780.29,
        "snapshots_count": 24
      },
      {
        "date": "2025-12-03",
        "total_usd": 153.45,
        "total_brl": 789.45,
        "snapshots_count": 24
      },
      {
        "date": "2025-12-04",
        "total_usd": 156.89,
        "total_brl": 807.16,
        "snapshots_count": 24
      },
      {
        "date": "2025-12-05",
        "total_usd": 159.12,
        "total_brl": 818.63,
        "snapshots_count": 24
      },
      {
        "date": "2025-12-06",
        "total_usd": 162.34,
        "total_brl": 835.19,
        "snapshots_count": 24
      },
      {
        "date": "2025-12-07",
        "total_usd": 165.78,
        "total_brl": 852.90,
        "snapshots_count": 24
      },
      {
        "date": "2025-12-08",
        "total_usd": 170.23,
        "total_brl": 875.78,
        "snapshots_count": 17
      }
    ],
    "summary": {
      "period_days": 7,
      "data_points": 8,
      "start_value_usd": 148.23,
      "end_value_usd": 170.23,
      "change_usd": 22.00,
      "change_percent": 14.84,
      "min_value_usd": 148.23,
      "max_value_usd": 170.23,
      "avg_value_usd": 158.46
    }
  }
}
```

**Uso no Frontend:**
- Gráfico de linha/barra com 8 pontos (1 por dia)
- Mostra tendência semanal
- Ideal para visão geral recente

---

## 📊 Exemplo 3: Últimos 30 Dias

### Request
```bash
GET /api/v1/history/evolution?user_id=charles_test_user&days=30
```

### Response (200 OK)
```json
{
  "success": true,
  "user_id": "charles_test_user",
  "days": 30,
  "evolution": {
    "period": "2025-11-08T16:00:00 to 2025-12-08T16:00:00",
    "data_points": [
      {
        "date": "2025-11-08",
        "total_usd": 125.45,
        "total_brl": 645.32,
        "snapshots_count": 24
      },
      {
        "date": "2025-11-09",
        "total_usd": 127.89,
        "total_brl": 657.87,
        "snapshots_count": 24
      },
      {
        "date": "2025-11-10",
        "total_usd": 129.12,
        "total_brl": 664.20,
        "snapshots_count": 24
      },
      {
        "date": "2025-11-11",
        "total_usd": 131.67,
        "total_brl": 677.31,
        "snapshots_count": 24
      },
      {
        "date": "2025-11-12",
        "total_usd": 128.34,
        "total_brl": 660.19,
        "snapshots_count": 24
      },
      {
        "date": "2025-11-13",
        "total_usd": 132.45,
        "total_brl": 681.32,
        "snapshots_count": 24
      },
      {
        "date": "2025-11-14",
        "total_usd": 135.78,
        "total_brl": 698.45,
        "snapshots_count": 24
      },
      {
        "date": "2025-11-15",
        "total_usd": 133.23,
        "total_brl": 685.33,
        "snapshots_count": 24
      },
      {
        "date": "2025-11-16",
        "total_usd": 137.89,
        "total_brl": 709.29,
        "snapshots_count": 24
      },
      {
        "date": "2025-11-17",
        "total_usd": 139.45,
        "total_brl": 717.32,
        "snapshots_count": 24
      },
      {
        "date": "2025-11-18",
        "total_usd": 142.12,
        "total_brl": 731.06,
        "snapshots_count": 24
      },
      {
        "date": "2025-11-19",
        "total_usd": 138.67,
        "total_brl": 713.32,
        "snapshots_count": 24
      },
      {
        "date": "2025-11-20",
        "total_usd": 143.34,
        "total_brl": 737.33,
        "snapshots_count": 24
      },
      {
        "date": "2025-11-21",
        "total_usd": 145.89,
        "total_brl": 750.45,
        "snapshots_count": 24
      },
      {
        "date": "2025-11-22",
        "total_usd": 141.23,
        "total_brl": 726.47,
        "snapshots_count": 24
      },
      {
        "date": "2025-11-23",
        "total_usd": 147.56,
        "total_brl": 759.03,
        "snapshots_count": 24
      },
      {
        "date": "2025-11-24",
        "total_usd": 149.12,
        "total_brl": 767.06,
        "snapshots_count": 24
      },
      {
        "date": "2025-11-25",
        "total_usd": 152.45,
        "total_brl": 784.19,
        "snapshots_count": 24
      },
      {
        "date": "2025-11-26",
        "total_usd": 148.89,
        "total_brl": 765.87,
        "snapshots_count": 24
      },
      {
        "date": "2025-11-27",
        "total_usd": 154.23,
        "total_brl": 793.35,
        "snapshots_count": 24
      },
      {
        "date": "2025-11-28",
        "total_usd": 156.78,
        "total_brl": 806.46,
        "snapshots_count": 24
      },
      {
        "date": "2025-11-29",
        "total_usd": 153.34,
        "total_brl": 788.76,
        "snapshots_count": 24
      },
      {
        "date": "2025-11-30",
        "total_usd": 158.67,
        "total_brl": 816.19,
        "snapshots_count": 24
      },
      {
        "date": "2025-12-01",
        "total_usd": 148.23,
        "total_brl": 762.58,
        "snapshots_count": 24
      },
      {
        "date": "2025-12-02",
        "total_usd": 151.67,
        "total_brl": 780.29,
        "snapshots_count": 24
      },
      {
        "date": "2025-12-03",
        "total_usd": 153.45,
        "total_brl": 789.45,
        "snapshots_count": 24
      },
      {
        "date": "2025-12-04",
        "total_usd": 156.89,
        "total_brl": 807.16,
        "snapshots_count": 24
      },
      {
        "date": "2025-12-05",
        "total_usd": 159.12,
        "total_brl": 818.63,
        "snapshots_count": 24
      },
      {
        "date": "2025-12-06",
        "total_usd": 162.34,
        "total_brl": 835.19,
        "snapshots_count": 24
      },
      {
        "date": "2025-12-07",
        "total_usd": 165.78,
        "total_brl": 852.90,
        "snapshots_count": 24
      },
      {
        "date": "2025-12-08",
        "total_usd": 170.23,
        "total_brl": 875.78,
        "snapshots_count": 17
      }
    ],
    "summary": {
      "period_days": 30,
      "data_points": 31,
      "start_value_usd": 125.45,
      "end_value_usd": 170.23,
      "change_usd": 44.78,
      "change_percent": 35.69,
      "min_value_usd": 125.45,
      "max_value_usd": 170.23,
      "avg_value_usd": 147.84
    }
  }
}
```

**Uso no Frontend:**
- Gráfico de linha com 31 pontos (1 por dia)
- Visão mensal completa
- Mostra tendências de médio prazo

---

## 📊 Exemplo 4: Últimos 90 Dias

### Request
```bash
GET /api/v1/history/evolution?user_id=charles_test_user&days=90
```

### Response (200 OK)
```json
{
  "success": true,
  "user_id": "charles_test_user",
  "days": 90,
  "evolution": {
    "period": "2025-09-09T16:00:00 to 2025-12-08T16:00:00",
    "data_points": [
      {
        "date": "2025-09-09",
        "total_usd": 95.23,
        "total_brl": 489.93,
        "snapshots_count": 24
      },
      {
        "date": "2025-09-10",
        "total_usd": 97.45,
        "total_brl": 501.34,
        "snapshots_count": 24
      },
      {
        "date": "2025-09-11",
        "total_usd": 99.12,
        "total_brl": 509.93,
        "snapshots_count": 24
      },
      {
        "date": "2025-09-12",
        "total_usd": 96.78,
        "total_brl": 497.89,
        "snapshots_count": 24
      },
      {
        "date": "2025-09-13",
        "total_usd": 101.34,
        "total_brl": 521.40,
        "snapshots_count": 24
      },
      // ... (86 pontos de dados diários omitidos para brevidade)
      {
        "date": "2025-12-06",
        "total_usd": 162.34,
        "total_brl": 835.19,
        "snapshots_count": 24
      },
      {
        "date": "2025-12-07",
        "total_usd": 165.78,
        "total_brl": 852.90,
        "snapshots_count": 24
      },
      {
        "date": "2025-12-08",
        "total_usd": 170.23,
        "total_brl": 875.78,
        "snapshots_count": 17
      }
    ],
    "summary": {
      "period_days": 90,
      "data_points": 91,
      "start_value_usd": 95.23,
      "end_value_usd": 170.23,
      "change_usd": 75.00,
      "change_percent": 78.76,
      "min_value_usd": 92.45,
      "max_value_usd": 170.23,
      "avg_value_usd": 131.34
    }
  }
}
```

**Uso no Frontend:**
- Gráfico com 91 pontos (pode ser renderizado com menos pontos usando sampling)
- Visão trimestral
- Ideal para análise de performance de médio prazo

---

## 📊 Exemplo 5: Último Ano (365 dias)

### Request
```bash
GET /api/v1/history/evolution?user_id=charles_test_user&days=365
```

### Response (200 OK)
```json
{
  "success": true,
  "user_id": "charles_test_user",
  "days": 365,
  "evolution": {
    "period": "2024-12-08T16:00:00 to 2025-12-08T16:00:00",
    "data_points": [
      {
        "month": "2024-12",
        "total_usd": 45.67,
        "total_brl": 234.95,
        "snapshots_count": 552,
        "avg_daily": 45.67
      },
      {
        "month": "2025-01",
        "total_usd": 52.34,
        "total_brl": 269.28,
        "snapshots_count": 744,
        "avg_daily": 52.34
      },
      {
        "month": "2025-02",
        "total_usd": 58.89,
        "total_brl": 303.00,
        "snapshots_count": 672,
        "avg_daily": 58.89
      },
      {
        "month": "2025-03",
        "total_usd": 65.23,
        "total_brl": 335.63,
        "snapshots_count": 744,
        "avg_daily": 65.23
      },
      {
        "month": "2025-04",
        "total_usd": 72.45,
        "total_brl": 372.72,
        "snapshots_count": 720,
        "avg_daily": 72.45
      },
      {
        "month": "2025-05",
        "total_usd": 79.12,
        "total_brl": 407.04,
        "snapshots_count": 744,
        "avg_daily": 79.12
      },
      {
        "month": "2025-06",
        "total_usd": 85.67,
        "total_brl": 440.75,
        "snapshots_count": 720,
        "avg_daily": 85.67
      },
      {
        "month": "2025-07",
        "total_usd": 92.34,
        "total_brl": 475.07,
        "snapshots_count": 744,
        "avg_daily": 92.34
      },
      {
        "month": "2025-08",
        "total_usd": 98.78,
        "total_brl": 508.23,
        "snapshots_count": 744,
        "avg_daily": 98.78
      },
      {
        "month": "2025-09",
        "total_usd": 105.45,
        "total_brl": 542.55,
        "snapshots_count": 720,
        "avg_daily": 105.45
      },
      {
        "month": "2025-10",
        "total_usd": 125.89,
        "total_brl": 647.60,
        "snapshots_count": 744,
        "avg_daily": 125.89
      },
      {
        "month": "2025-11",
        "total_usd": 145.67,
        "total_brl": 749.40,
        "snapshots_count": 720,
        "avg_daily": 145.67
      },
      {
        "month": "2025-12",
        "total_usd": 170.23,
        "total_brl": 875.78,
        "snapshots_count": 185,
        "avg_daily": 165.12
      }
    ],
    "summary": {
      "period_days": 365,
      "data_points": 13,
      "start_value_usd": 45.67,
      "end_value_usd": 170.23,
      "change_usd": 124.56,
      "change_percent": 272.78,
      "min_value_usd": 45.67,
      "max_value_usd": 170.23,
      "avg_value_usd": 92.30
    }
  }
}
```

**Uso no Frontend:**
- Gráfico com 13 pontos (1 por mês)
- Visão anual completa
- Ideal para relatórios e análise de performance de longo prazo
- Pode ser exibido como gráfico de barras ou linha

---

## 🎨 Recomendações de UI/UX

### 1. **Selector de Período**
```jsx
<ButtonGroup>
  <Button onClick={() => setPeriod(1)}>24h</Button>
  <Button onClick={() => setPeriod(7)}>7d</Button>
  <Button onClick={() => setPeriod(30)}>30d</Button>
  <Button onClick={() => setPeriod(90)}>90d</Button>
  <Button onClick={() => setPeriod(365)}>1y</Button>
</ButtonGroup>
```

### 2. **Formatação de Valores**
- **USD**: `$170.23` ou `$170`
- **BRL**: `R$ 875,78` ou `R$ 876`
- **Percentual**: `+14.84%` (verde) ou `-5.23%` (vermelho)

### 3. **Granularidade do Gráfico**
- **24h**: Mostrar todos os 24 pontos (hora a hora)
- **7d**: Mostrar 7-8 pontos (dia a dia)
- **30d**: Mostrar 30 pontos ou sampling para 15 pontos
- **90d**: Sampling para 20-30 pontos (não renderizar todos os 90)
- **1y**: Mostrar 12 pontos (mês a mês)

### 4. **Indicadores Visuais**
```jsx
<Card>
  <Metric>
    <Value>$170.23</Value>
    <Change positive={summary.change_percent > 0}>
      {summary.change_percent > 0 ? '↑' : '↓'} 
      {Math.abs(summary.change_percent)}%
    </Change>
  </Metric>
  <Period>Últimos {days} dias</Period>
</Card>
```

### 5. **Tooltip no Hover**
```jsx
{
  timestamp: "08/12/2025 16:00",
  value: "$172.23",
  valueBRL: "R$ 885,89",
  change: "+6.02%"
}
```

---

## 🔧 Integração no Frontend

### React/Next.js Example
```javascript
import { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';

const BalanceHistory = ({ userId }) => {
  const [period, setPeriod] = useState(7);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const fetchHistory = async () => {
      setLoading(true);
      try {
        const response = await fetch(
          `/api/v1/history/evolution?user_id=${userId}&days=${period}`
        );
        const result = await response.json();
        setData(result.evolution);
      } catch (error) {
        console.error('Error fetching history:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchHistory();
  }, [userId, period]);

  if (loading) return <div>Loading...</div>;
  if (!data) return null;

  return (
    <div>
      {/* Period Selector */}
      <div className="period-selector">
        {[1, 7, 30, 90, 365].map(days => (
          <button
            key={days}
            onClick={() => setPeriod(days)}
            className={period === days ? 'active' : ''}
          >
            {days === 1 ? '24h' : days === 365 ? '1y' : `${days}d`}
          </button>
        ))}
      </div>

      {/* Summary Stats */}
      <div className="stats">
        <div className="stat">
          <span className="label">Current Value</span>
          <span className="value">${data.summary.end_value_usd}</span>
        </div>
        <div className="stat">
          <span className="label">Change</span>
          <span className={data.summary.change_percent >= 0 ? 'positive' : 'negative'}>
            {data.summary.change_percent >= 0 ? '+' : ''}
            {data.summary.change_percent.toFixed(2)}%
          </span>
        </div>
      </div>

      {/* Chart */}
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={data.data_points}>
          <XAxis 
            dataKey={period === 1 ? 'timestamp' : 'date'} 
            tickFormatter={(value) => {
              const date = new Date(value);
              return period === 1 
                ? date.getHours() + ':00'
                : date.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' });
            }}
          />
          <YAxis />
          <Tooltip 
            formatter={(value) => `$${value.toFixed(2)}`}
            labelFormatter={(label) => new Date(label).toLocaleString('pt-BR')}
          />
          <Line 
            type="monotone" 
            dataKey="total_usd" 
            stroke="#8884d8" 
            strokeWidth={2}
            dot={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

export default BalanceHistory;
```

---

## ⚠️ Notas Importantes

1. **Caching**: O backend já tem cache de 2 minutos nos saldos. Para histórico, considere cache no frontend de 5-10 minutos.

2. **Polling**: Não faça polling frequente do histórico. Atualize apenas quando:
   - Usuário trocar de período
   - Usuário fazer refresh manual
   - A cada 5-10 minutos (se necessário)

3. **Performance**: Para gráficos de 90 dias e 1 ano, considere usar sampling (reduzir número de pontos) para melhor performance de renderização.

4. **Timezone**: Todos os timestamps são em UTC. Converta para timezone local no frontend se necessário.

5. **Dados ausentes**: Se não houver dados históricos suficientes, o `data_points` será menor que o esperado.

---

## 📞 Endpoints Relacionados

### Histórico Completo (Lista de Snapshots)
```bash
GET /api/v1/history?user_id=charles_test_user&limit=168
```
Retorna lista completa de snapshots (útil para tabelas detalhadas).

### Saldo Atual
```bash
GET /api/v1/balances?user_id=charles_test_user
```
Retorna saldo em tempo real (não vem do histórico).

---

**Documento criado em:** 08/12/2025  
**Versão da API:** 1.0  
**Mantenedor:** Charles Roberto
