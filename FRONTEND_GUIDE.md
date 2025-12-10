# 🎨 Frontend Integration Guide

Guia completo para integração do frontend com a API de Trading Automatizado.

---

## 📦 Arquivos para o Frontend

1. **API_EXAMPLES.json** - Exemplos de requests/responses de todos os endpoints
2. **api-client.ts** - Client TypeScript pronto para uso (React/Vue/Angular)

---

## 🚀 Quick Start

### 1. Copie o Client TypeScript

```bash
# Copie o arquivo api-client.ts para seu projeto frontend
cp api-client.ts src/services/
```

### 2. Use no seu componente

```typescript
import { TradingApiClient } from '@/services/api-client';

const api = new TradingApiClient('http://localhost:5000');

// Buscar estratégias
const { strategies } = await api.listStrategies({
  user_id: 'user123',
  is_active: true
});
```

---

## 📱 Principais Componentes para Implementar

### 1. **Dashboard de Estratégias**

```typescript
// StrategiesPage.tsx (React)
import { useEffect, useState } from 'react';
import { TradingApiClient, Strategy } from '@/services/api-client';

export function StrategiesPage() {
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const api = new TradingApiClient();
  
  useEffect(() => {
    loadStrategies();
  }, []);
  
  const loadStrategies = async () => {
    const response = await api.listStrategies({
      user_id: getCurrentUserId(),
      is_active: true
    });
    
    if (response.success) {
      setStrategies(response.strategies);
    }
  };
  
  return (
    <div>
      <h1>Minhas Estratégias</h1>
      {strategies.map(strategy => (
        <StrategyCard 
          key={strategy._id}
          strategy={strategy}
          onDelete={() => handleDelete(strategy._id)}
        />
      ))}
    </div>
  );
}
```

**Card de Estratégia:**
```tsx
interface StrategyCardProps {
  strategy: Strategy;
  onDelete: () => void;
}

function StrategyCard({ strategy, onDelete }: StrategyCardProps) {
  return (
    <div className="strategy-card">
      <div className="header">
        <h3>{strategy.token}</h3>
        <span className={strategy.is_active ? 'active' : 'inactive'}>
          {strategy.is_active ? '✅ Ativa' : '⏸️ Pausada'}
        </span>
      </div>
      
      <div className="exchange">
        📊 {strategy.exchange_name}
      </div>
      
      <div className="rules">
        <div className="rule">
          <span>🎯 Take Profit:</span>
          <strong>+{strategy.rules.take_profit_percent}%</strong>
        </div>
        <div className="rule">
          <span>⚠️ Stop Loss:</span>
          <strong>-{strategy.rules.stop_loss_percent}%</strong>
        </div>
        <div className="rule">
          <span>📉 Buy Dip:</span>
          <strong>-{strategy.rules.buy_dip_percent}%</strong>
        </div>
      </div>
      
      <div className="stats">
        <div>Execuções: {strategy.execution_count}</div>
        {strategy.last_execution && (
          <div>Última: {formatDate(strategy.last_execution)}</div>
        )}
      </div>
      
      <div className="actions">
        <button onClick={() => handleEdit(strategy._id)}>
          ✏️ Editar
        </button>
        <button onClick={onDelete}>
          🗑️ Deletar
        </button>
      </div>
    </div>
  );
}
```

---

### 2. **Formulário de Nova Estratégia**

```tsx
function CreateStrategyForm() {
  const [formData, setFormData] = useState({
    exchange_id: '',
    token: '',
    take_profit_percent: 5.0,
    stop_loss_percent: 2.0,
    buy_dip_percent: 3.0
  });
  
  const api = new TradingApiClient();
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    const response = await api.createStrategy({
      user_id: getCurrentUserId(),
      exchange_id: formData.exchange_id,
      token: formData.token,
      rules: {
        take_profit_percent: formData.take_profit_percent,
        stop_loss_percent: formData.stop_loss_percent,
        buy_dip_percent: formData.buy_dip_percent
      },
      is_active: true
    });
    
    if (response.success) {
      alert('Estratégia criada com sucesso! 🎉');
      // Redirecionar ou atualizar lista
    } else {
      alert(`Erro: ${response.error}`);
    }
  };
  
  return (
    <form onSubmit={handleSubmit}>
      <h2>Nova Estratégia</h2>
      
      <label>
        Exchange:
        <select 
          value={formData.exchange_id}
          onChange={e => setFormData({...formData, exchange_id: e.target.value})}
          required
        >
          <option value="">Selecione...</option>
          {/* Popular com exchanges linkadas */}
        </select>
      </label>
      
      <label>
        Token:
        <input 
          type="text"
          value={formData.token}
          onChange={e => setFormData({...formData, token: e.target.value.toUpperCase()})}
          placeholder="BTC, ETH, etc"
          required
        />
      </label>
      
      <label>
        🎯 Take Profit (%):
        <input 
          type="number"
          step="0.1"
          value={formData.take_profit_percent}
          onChange={e => setFormData({...formData, take_profit_percent: parseFloat(e.target.value)})}
          required
        />
        <small>Vende quando o preço subir este %</small>
      </label>
      
      <label>
        ⚠️ Stop Loss (%):
        <input 
          type="number"
          step="0.1"
          value={formData.stop_loss_percent}
          onChange={e => setFormData({...formData, stop_loss_percent: parseFloat(e.target.value)})}
          required
        />
        <small>Vende quando o preço cair este %</small>
      </label>
      
      <label>
        📉 Buy Dip (%):
        <input 
          type="number"
          step="0.1"
          value={formData.buy_dip_percent}
          onChange={e => setFormData({...formData, buy_dip_percent: parseFloat(e.target.value)})}
          required
        />
        <small>Compra quando o preço cair este %</small>
      </label>
      
      <button type="submit">Criar Estratégia</button>
    </form>
  );
}
```

---

### 3. **Dashboard de Posições com P&L**

```tsx
function PositionsPage() {
  const [positions, setPositions] = useState<Position[]>([]);
  const [currentPrices, setCurrentPrices] = useState<Record<string, number>>({});
  const api = new TradingApiClient();
  
  useEffect(() => {
    loadPositions();
    loadCurrentPrices();
  }, []);
  
  const loadPositions = async () => {
    const response = await api.listPositions({
      user_id: getCurrentUserId(),
      is_active: true
    });
    
    if (response.success) {
      setPositions(response.positions);
    }
  };
  
  const loadCurrentPrices = async () => {
    const response = await api.getBalances({
      user_id: getCurrentUserId(),
      include_changes: true
    });
    
    if (response.success) {
      const prices: Record<string, number> = {};
      response.balances.forEach(exchange => {
        exchange.balances.forEach(asset => {
          prices[asset.asset] = asset.price_usd;
        });
      });
      setCurrentPrices(prices);
    }
  };
  
  return (
    <div>
      <h1>Minhas Posições</h1>
      
      {positions.map(position => {
        const currentPrice = currentPrices[position.token] || position.entry_price;
        const { pnl, pnlPercent } = calculatePnL(position, currentPrice);
        
        return (
          <PositionCard 
            key={position._id}
            position={position}
            currentPrice={currentPrice}
            pnl={pnl}
            pnlPercent={pnlPercent}
          />
        );
      })}
    </div>
  );
}
```

**Card de Posição:**
```tsx
interface PositionCardProps {
  position: Position;
  currentPrice: number;
  pnl: number;
  pnlPercent: number;
}

function PositionCard({ position, currentPrice, pnl, pnlPercent }: PositionCardProps) {
  const isProfitable = pnl >= 0;
  
  return (
    <div className="position-card">
      <div className="header">
        <h3>{position.token}</h3>
        <span className="exchange">{position.exchange_name}</span>
      </div>
      
      <div className="amounts">
        <div>
          <label>Quantidade:</label>
          <strong>{position.amount} {position.token}</strong>
        </div>
        <div>
          <label>Preço de Entrada:</label>
          <strong>{formatCurrency(position.entry_price)}</strong>
        </div>
        <div>
          <label>Preço Atual:</label>
          <strong>{formatCurrency(currentPrice)}</strong>
        </div>
      </div>
      
      <div className="investment">
        <div>
          <label>Investido:</label>
          <strong>{formatCurrency(position.total_invested)}</strong>
        </div>
        <div>
          <label>Valor Atual:</label>
          <strong>{formatCurrency(position.amount * currentPrice)}</strong>
        </div>
      </div>
      
      <div className={`pnl ${isProfitable ? 'profit' : 'loss'}`}>
        <div className="pnl-amount">
          {isProfitable ? '📈' : '📉'} {formatCurrency(Math.abs(pnl))}
        </div>
        <div className="pnl-percent">
          {formatPercent(pnlPercent)}
        </div>
      </div>
      
      <div className="history">
        <div>
          <span>Compras: {position.purchases.length}</span>
          <span>Vendas: {position.sales.length}</span>
        </div>
        <button onClick={() => viewHistory(position._id)}>
          📊 Ver Histórico
        </button>
      </div>
    </div>
  );
}
```

---

### 4. **Central de Notificações**

```tsx
function NotificationsPanel() {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const api = new TradingApiClient();
  
  useEffect(() => {
    loadNotifications();
    
    // Poll a cada 30 segundos
    const interval = setInterval(loadNotifications, 30000);
    return () => clearInterval(interval);
  }, []);
  
  const loadNotifications = async () => {
    const response = await api.listNotifications({
      user_id: getCurrentUserId(),
      limit: 50
    });
    
    if (response.success) {
      setNotifications(response.notifications);
      setUnreadCount(response.notifications.filter(n => !n.is_read).length);
    }
  };
  
  const markAsRead = async (id: string) => {
    await api.markNotificationRead(id);
    loadNotifications();
  };
  
  const markAllAsRead = async () => {
    await api.markAllNotificationsRead({
      user_id: getCurrentUserId()
    });
    loadNotifications();
  };
  
  return (
    <div className="notifications-panel">
      <div className="header">
        <h2>Notificações</h2>
        <span className="badge">{unreadCount}</span>
        {unreadCount > 0 && (
          <button onClick={markAllAsRead}>
            Marcar todas como lidas
          </button>
        )}
      </div>
      
      <div className="list">
        {notifications.map(notification => (
          <NotificationItem 
            key={notification._id}
            notification={notification}
            onMarkRead={() => markAsRead(notification._id)}
          />
        ))}
      </div>
    </div>
  );
}
```

**Item de Notificação:**
```tsx
function NotificationItem({ notification, onMarkRead }: NotificationItemProps) {
  const getIcon = () => {
    switch (notification.type) {
      case 'strategy_executed':
        return notification.data.action === 'SELL' ? '🔴' : '🟢';
      case 'strategy_created':
        return '✅';
      case 'order_failed':
        return '❌';
      default:
        return '📬';
    }
  };
  
  return (
    <div className={`notification ${notification.is_read ? 'read' : 'unread'}`}>
      <div className="icon">{getIcon()}</div>
      
      <div className="content">
        <h4>{notification.title}</h4>
        <p>{notification.message}</p>
        <div className="meta">
          <span>{formatDate(notification.created_at)}</span>
          {notification.data.token && (
            <span className="token">{notification.data.token}</span>
          )}
        </div>
      </div>
      
      {!notification.is_read && (
        <button onClick={onMarkRead} className="mark-read">
          ✓
        </button>
      )}
    </div>
  );
}
```

---

### 5. **Painel de Controle Manual de Ordens**

```tsx
function ManualOrderPanel() {
  const [orderType, setOrderType] = useState<'buy' | 'sell'>('buy');
  const [formData, setFormData] = useState({
    exchange_id: '',
    token: '',
    amount: 0,
    order_type: 'market' as 'market' | 'limit',
    price: 0
  });
  
  const api = new TradingApiClient();
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    const executeOrder = orderType === 'buy' 
      ? api.executeBuyOrder.bind(api)
      : api.executeSellOrder.bind(api);
    
    const response = await executeOrder({
      user_id: getCurrentUserId(),
      ...formData
    });
    
    if (response.success) {
      if (response.dry_run) {
        alert('⚠️ MODO DRY-RUN: Ordem simulada com sucesso!');
      } else {
        alert('✅ Ordem executada com sucesso!');
      }
    } else {
      alert(`❌ Erro: ${response.error}`);
    }
  };
  
  return (
    <div className="manual-order-panel">
      <h2>Execução Manual de Ordem</h2>
      
      <div className="order-type-selector">
        <button 
          className={orderType === 'buy' ? 'active' : ''}
          onClick={() => setOrderType('buy')}
        >
          🟢 Comprar
        </button>
        <button 
          className={orderType === 'sell' ? 'active' : ''}
          onClick={() => setOrderType('sell')}
        >
          🔴 Vender
        </button>
      </div>
      
      <form onSubmit={handleSubmit}>
        {/* Campos do formulário... */}
        
        <div className="warning">
          ⚠️ Sistema em modo DRY-RUN - Ordens serão simuladas
        </div>
        
        <button type="submit">
          {orderType === 'buy' ? '🟢 Executar Compra' : '🔴 Executar Venda'}
        </button>
      </form>
    </div>
  );
}
```

---

## 🎨 Sugestões de Design

### Cores por Status

```css
/* Estratégias */
.strategy.active { border-left: 4px solid #10b981; }
.strategy.inactive { border-left: 4px solid #6b7280; }

/* P&L */
.pnl.profit { color: #10b981; background: #d1fae5; }
.pnl.loss { color: #ef4444; background: #fee2e2; }

/* Notificações */
.notification.unread { background: #fef3c7; }
.notification.strategy_executed { border-left: 3px solid #3b82f6; }
.notification.order_failed { border-left: 3px solid #ef4444; }

/* Badges */
.badge.unread { background: #ef4444; color: white; }
```

---

## 📊 Indicadores Visuais Importantes

### 1. **Status da Estratégia**
- ✅ Verde: Ativa e funcionando
- ⏸️ Cinza: Pausada
- 🎯 Badge: Número de execuções

### 2. **P&L em Tempo Real**
- 📈 Verde: Lucro
- 📉 Vermelho: Prejuízo
- % e valor absoluto lado a lado

### 3. **Notificações com Prioridade**
- 🔴 Alta: Estratégia executada, ordem falhou
- 🟡 Média: Nova estratégia criada
- Badge com contador não lido

---

## 🔄 Atualização em Tempo Real

### WebSocket (Futuro)
```typescript
// Exemplo de implementação futura
const socket = new WebSocket('ws://localhost:5000/ws');

socket.onmessage = (event) => {
  const notification = JSON.parse(event.data);
  
  // Adicionar notificação na lista
  setNotifications(prev => [notification, ...prev]);
  
  // Toastr/Toast notification
  showToast(notification.title, notification.type);
};
```

### Polling (Atual)
```typescript
// Poll notificações a cada 30s
useEffect(() => {
  const interval = setInterval(loadNotifications, 30000);
  return () => clearInterval(interval);
}, []);
```

---

## 📱 Responsividade

```css
/* Mobile First */
.strategy-card {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

@media (min-width: 768px) {
  .strategies-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 1.5rem;
  }
}

@media (min-width: 1024px) {
  .strategies-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}
```

---

## ✅ Checklist de Implementação

- [ ] Criar componente StrategiesPage
- [ ] Criar componente CreateStrategyForm
- [ ] Criar componente PositionsPage com cálculo de P&L
- [ ] Criar componente NotificationsPanel com polling
- [ ] Criar componente ManualOrderPanel
- [ ] Implementar formatação de moeda e percentual
- [ ] Adicionar toast notifications
- [ ] Implementar confirmação de deleção
- [ ] Adicionar loading states
- [ ] Adicionar error handling
- [ ] Testar responsividade mobile
- [ ] Implementar dark mode (opcional)

---

## 🚀 Pronto para Usar!

Todos os exemplos acima são funcionais e prontos para serem adaptados ao seu framework favorito (React, Vue, Angular, Svelte).

**Arquivos importantes:**
- `API_EXAMPLES.json` - Referência completa de JSON
- `api-client.ts` - Client TypeScript pronto
- Esta doc - Guia de implementação

**Próximos passos:**
1. Copie o `api-client.ts` para seu projeto
2. Implemente os componentes sugeridos
3. Customize o design conforme sua marca
4. Teste em modo DRY-RUN
5. Deploy! 🚀
