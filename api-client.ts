/**
 * API Client Types - Sistema de Trading Multi-Exchange
 * Use estes tipos no seu frontend (TypeScript/JavaScript)
 */

// ============================================================================
// BASE TYPES
// ============================================================================

export interface ApiResponse<T> {
  success: boolean;
  error?: string;
  details?: string;
  [key: string]: any;
}

// ============================================================================
// STRATEGY TYPES
// ============================================================================

export interface StrategyRules {
  take_profit_percent: number;  // % para venda com lucro (ex: 5.0 = vende quando subir 5%)
  stop_loss_percent: number;    // % para venda com perda (ex: 2.0 = vende quando cair 2%)
  buy_dip_percent: number;      // % para compra na queda (ex: 3.0 = compra quando cair 3%)
}

export interface Strategy {
  _id: string;
  user_id: string;
  exchange_id: string;
  exchange_name: string;
  token: string;
  rules: StrategyRules;
  is_active: boolean;
  execution_count: number;
  last_execution: string | null;
  created_at: string;
  updated_at: string;
}

export interface CreateStrategyRequest {
  user_id: string;
  exchange_id: string;
  token: string;
  rules: StrategyRules;
  is_active?: boolean;
}

export interface UpdateStrategyRequest {
  rules?: StrategyRules;
  is_active?: boolean;
}

export interface CheckTriggerRequest {
  current_price: number;
  entry_price: number;
}

export interface CheckTriggerResponse {
  should_trigger: boolean;
  action?: 'BUY' | 'SELL';
  reason?: 'TAKE_PROFIT' | 'STOP_LOSS' | 'BUY_DIP';
  trigger_percent?: number;
  current_change_percent?: number;
  strategy: Partial<Strategy>;
}

// ============================================================================
// POSITION TYPES
// ============================================================================

export interface Purchase {
  date: string;
  amount: number;
  price: number;
  total_cost: number;
  order_id: string;
}

export interface Sale {
  date: string;
  amount: number;
  price: number;
  total_received: number;
  entry_price: number;
  profit_loss: number;
  profit_loss_percent: number;
  order_id: string;
}

export interface Position {
  _id: string;
  user_id: string;
  exchange_id: string;
  exchange_name: string;
  token: string;
  amount: number;
  entry_price: number;        // Preço médio ponderado de entrada
  total_invested: number;     // Total investido em USD
  is_active: boolean;
  purchases: Purchase[];
  sales: Sale[];
  created_at: string;
  updated_at: string;
}

export interface SyncPositionRequest {
  user_id: string;
  exchange_id?: string;
  token?: string;
}

export interface PositionHistory {
  purchases: Purchase[];
  sales: Sale[];
}

// ============================================================================
// NOTIFICATION TYPES
// ============================================================================

export type NotificationType = 'strategy_executed' | 'strategy_created' | 'order_failed';

export interface NotificationData {
  strategy_id?: string;
  order_id?: string;
  token?: string;
  exchange_id?: string;
  action?: 'BUY' | 'SELL';
  reason?: 'TAKE_PROFIT' | 'STOP_LOSS' | 'BUY_DIP';
  amount?: number;
  price?: number;
  status?: string;
  error?: string;
  rules?: StrategyRules;
}

export interface Notification {
  _id: string;
  user_id: string;
  type: NotificationType;
  title: string;
  message: string;
  data: NotificationData;
  is_read: boolean;
  created_at: string;
  read_at?: string;
}

export interface MarkAllReadRequest {
  user_id: string;
}

// ============================================================================
// ORDER TYPES
// ============================================================================

export type OrderType = 'market' | 'limit';
export type OrderSide = 'buy' | 'sell';
export type OrderStatus = 'simulated' | 'open' | 'closed' | 'canceled' | 'expired';

export interface Order {
  id: string;
  symbol: string;
  type: OrderType;
  side: OrderSide;
  amount: number;
  price?: number;
  average?: number;
  filled?: number;
  remaining?: number;
  cost?: number;
  status: OrderStatus;
  timestamp?: string;
  datetime?: string;
  fee?: any;
}

export interface ExecuteOrderRequest {
  user_id: string;
  exchange_id: string;
  token: string;
  amount: number;
  order_type: OrderType;
  price?: number;  // Obrigatório para limit orders
}

export interface OrderResponse {
  success: boolean;
  dry_run?: boolean;
  order?: Order;
  error?: string;
  details?: string;
}

// ============================================================================
// BALANCE TYPES
// ============================================================================

export interface Asset {
  asset: string;
  free: number;
  used: number;
  total: number;
  price_usd: number;
  value_usd: number;
  change_1h?: number;
  change_4h?: number;
  change_24h?: number;
}

export interface ExchangeBalance {
  exchange_id: string;
  exchange_name: string;
  balances: Asset[];
  total_usd: number;
}

export interface BalancesResponse {
  success: boolean;
  balances: ExchangeBalance[];
  total_usd: number;
}

// ============================================================================
// API CLIENT CLASS
// ============================================================================

export class TradingApiClient {
  private baseUrl: string;
  
  constructor(baseUrl: string = 'http://localhost:5000') {
    this.baseUrl = baseUrl;
  }
  
  // Helper method for making requests
  private async request<T>(
    endpoint: string,
    options?: RequestInit
  ): Promise<T> {
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
      ...options,
    });
    
    return response.json();
  }
  
  // ============================================================================
  // STRATEGIES
  // ============================================================================
  
  async createStrategy(data: CreateStrategyRequest): Promise<ApiResponse<{ strategy: Strategy }>> {
    return this.request('/api/v1/strategies', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }
  
  async listStrategies(params: {
    user_id: string;
    exchange_id?: string;
    token?: string;
    is_active?: boolean;
  }): Promise<ApiResponse<{ strategies: Strategy[] }>> {
    const query = new URLSearchParams(params as any).toString();
    return this.request(`/api/v1/strategies?${query}`);
  }
  
  async getStrategy(id: string): Promise<ApiResponse<{ strategy: Strategy }>> {
    return this.request(`/api/v1/strategies/${id}`);
  }
  
  async updateStrategy(id: string, data: UpdateStrategyRequest): Promise<ApiResponse<{}>> {
    return this.request(`/api/v1/strategies/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }
  
  async deleteStrategy(id: string): Promise<ApiResponse<{}>> {
    return this.request(`/api/v1/strategies/${id}`, {
      method: 'DELETE',
    });
  }
  
  async checkStrategyTrigger(
    id: string,
    data: CheckTriggerRequest
  ): Promise<CheckTriggerResponse> {
    return this.request(`/api/v1/strategies/${id}/check`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }
  
  // ============================================================================
  // POSITIONS
  // ============================================================================
  
  async listPositions(params: {
    user_id: string;
    exchange_id?: string;
    token?: string;
    is_active?: boolean;
  }): Promise<ApiResponse<{ positions: Position[] }>> {
    const query = new URLSearchParams(params as any).toString();
    return this.request(`/api/v1/positions?${query}`);
  }
  
  async getPosition(id: string): Promise<ApiResponse<{ position: Position }>> {
    return this.request(`/api/v1/positions/${id}`);
  }
  
  async syncPositions(data: SyncPositionRequest): Promise<ApiResponse<any>> {
    return this.request('/api/v1/positions/sync', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }
  
  async getPositionHistory(id: string): Promise<ApiResponse<{ history: PositionHistory }>> {
    return this.request(`/api/v1/positions/${id}/history`);
  }
  
  // ============================================================================
  // NOTIFICATIONS
  // ============================================================================
  
  async listNotifications(params: {
    user_id: string;
    unread_only?: boolean;
    type?: NotificationType;
    limit?: number;
  }): Promise<ApiResponse<{ notifications: Notification[] }>> {
    const query = new URLSearchParams(params as any).toString();
    return this.request(`/api/v1/notifications?${query}`);
  }
  
  async markNotificationRead(id: string): Promise<ApiResponse<{}>> {
    return this.request(`/api/v1/notifications/${id}/read`, {
      method: 'PUT',
    });
  }
  
  async markAllNotificationsRead(data: MarkAllReadRequest): Promise<ApiResponse<{}>> {
    return this.request('/api/v1/notifications/read-all', {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }
  
  async deleteNotification(id: string): Promise<ApiResponse<{}>> {
    return this.request(`/api/v1/notifications/${id}`, {
      method: 'DELETE',
    });
  }
  
  // ============================================================================
  // ORDERS
  // ============================================================================
  
  async executeBuyOrder(data: ExecuteOrderRequest): Promise<OrderResponse> {
    return this.request('/api/v1/orders/buy', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }
  
  async executeSellOrder(data: ExecuteOrderRequest): Promise<OrderResponse> {
    return this.request('/api/v1/orders/sell', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }
  
  // ============================================================================
  // BALANCES
  // ============================================================================
  
  async getBalances(params: {
    user_id: string;
    force_refresh?: boolean;
    include_changes?: boolean;
  }): Promise<BalancesResponse> {
    const query = new URLSearchParams(params as any).toString();
    return this.request(`/api/v1/balances?${query}`);
  }
  
  // ============================================================================
  // SYSTEM
  // ============================================================================
  
  async healthCheck(): Promise<any> {
    return this.request('/health');
  }
  
  async getSystemInfo(): Promise<any> {
    return this.request('/');
  }
}

// ============================================================================
// USAGE EXAMPLES
// ============================================================================

/**
 * Exemplo de uso no React/Vue/Angular:
 * 
 * import { TradingApiClient, Strategy } from './api-client';
 * 
 * const api = new TradingApiClient('http://localhost:5000');
 * 
 * // Criar estratégia
 * const response = await api.createStrategy({
 *   user_id: 'user123',
 *   exchange_id: '65abc...',
 *   token: 'BTC',
 *   rules: {
 *     take_profit_percent: 5.0,
 *     stop_loss_percent: 2.0,
 *     buy_dip_percent: 3.0
 *   }
 * });
 * 
 * if (response.success) {
 *   console.log('Estratégia criada:', response.strategy);
 * }
 * 
 * // Listar estratégias
 * const strategies = await api.listStrategies({
 *   user_id: 'user123',
 *   is_active: true
 * });
 * 
 * // Listar posições com P&L
 * const positions = await api.listPositions({
 *   user_id: 'user123'
 * });
 * 
 * positions.positions.forEach(pos => {
 *   console.log(`${pos.token}: Entry $${pos.entry_price}`);
 *   
 *   pos.sales.forEach(sale => {
 *     console.log(`  Venda: ${sale.profit_loss_percent.toFixed(2)}% P&L`);
 *   });
 * });
 * 
 * // Listar notificações não lidas
 * const notifications = await api.listNotifications({
 *   user_id: 'user123',
 *   unread_only: true
 * });
 * 
 * // Executar ordem manual (em DRY-RUN por padrão)
 * const order = await api.executeSellOrder({
 *   user_id: 'user123',
 *   exchange_id: '65abc...',
 *   token: 'BTC',
 *   amount: 0.1,
 *   order_type: 'market'
 * });
 * 
 * if (order.dry_run) {
 *   console.log('Ordem simulada:', order.order);
 * }
 */

// ============================================================================
// REACT HOOKS EXAMPLES
// ============================================================================

/**
 * Custom React Hooks para facilitar o uso:
 * 
 * // useStrategies.ts
 * import { useState, useEffect } from 'react';
 * import { TradingApiClient, Strategy } from './api-client';
 * 
 * export function useStrategies(userId: string) {
 *   const [strategies, setStrategies] = useState<Strategy[]>([]);
 *   const [loading, setLoading] = useState(true);
 *   const api = new TradingApiClient();
 *   
 *   useEffect(() => {
 *     const fetchStrategies = async () => {
 *       const response = await api.listStrategies({ user_id: userId });
 *       if (response.success) {
 *         setStrategies(response.strategies);
 *       }
 *       setLoading(false);
 *     };
 *     
 *     fetchStrategies();
 *   }, [userId]);
 *   
 *   return { strategies, loading };
 * }
 * 
 * // Uso no componente:
 * function StrategiesPage() {
 *   const { strategies, loading } = useStrategies('user123');
 *   
 *   if (loading) return <div>Carregando...</div>;
 *   
 *   return (
 *     <div>
 *       {strategies.map(strategy => (
 *         <StrategyCard key={strategy._id} strategy={strategy} />
 *       ))}
 *     </div>
 *   );
 * }
 */

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

export const formatCurrency = (value: number): string => {
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'USD',
  }).format(value);
};

export const formatPercent = (value: number): string => {
  const sign = value >= 0 ? '+' : '';
  return `${sign}${value.toFixed(2)}%`;
};

export const getNotificationIcon = (type: NotificationType): string => {
  const icons = {
    strategy_executed: '🎯',
    strategy_created: '✅',
    order_failed: '❌',
  };
  return icons[type] || '📬';
};

export const getTriggerReasonText = (reason: string): string => {
  const texts = {
    TAKE_PROFIT: 'Take Profit atingido! 🎯',
    STOP_LOSS: 'Stop Loss acionado ⚠️',
    BUY_DIP: 'Oportunidade de compra detectada 📉',
  };
  return texts[reason as keyof typeof texts] || reason;
};

export const calculatePnL = (position: Position, currentPrice: number): {
  pnl: number;
  pnlPercent: number;
} => {
  const currentValue = position.amount * currentPrice;
  const pnl = currentValue - position.total_invested;
  const pnlPercent = (pnl / position.total_invested) * 100;
  
  return { pnl, pnlPercent };
};

export default TradingApiClient;
