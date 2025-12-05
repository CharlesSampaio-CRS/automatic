"""
Estratégia de Venda Simplificada
Vende quando atinge lucro mínimo ou aciona stop loss
"""

from typing import Dict, Tuple

class SellStrategy:
    """
    Estratégia de venda simples e eficiente
    
    REGRAS OTIMIZADAS:
    1. Scalping (4h): Lucro >= 6% → VENDE 100%
    2. Swing (24h): Lucro >= 8% → VENDE 100%
    3. Stop loss: -3% (proteção sempre ativa)
    """
    
    def __init__(self, config: Dict = None):
        """
        Inicializa estratégia de venda
        
        Args:
            config: Configuração do MongoDB com:
                   - sell_strategy: Nova estrutura simplificada (preferencial)
                   - trading_mode: Modo safe ou aggressive
                   - strategy_4h/trading_strategy: Estrutura antiga (retrocompatibilidade)
                   - risk_management: Configuração de stop loss
        """
        config = config or {}
        
        # Lê trading_mode (safe ou aggressive)
        trading_mode = config.get('trading_mode', 'safe')
        
        # NOVA ESTRUTURA SIMPLIFICADA (preferencial)
        sell_config = config.get('sell_strategy', {})
        
        if sell_config:
            # Usa estrutura simplificada
            self.min_profit_4h = sell_config.get('min_profit_4h', 6.0)
            self.min_profit_24h = sell_config.get('min_profit_24h', 8.0)
        else:
            # RETROCOMPATIBILIDADE: Lê estrutura antiga
            strategy_4h = config.get('strategy_4h', {})
            trading_strategy = config.get('trading_strategy', {})
            
            self.min_profit_4h = strategy_4h.get('quick_profit_target', 6.0)
            self.min_profit_24h = trading_strategy.get('profit_target', 8.0)
        
        # Salva trading_mode para referência
        self.trading_mode = trading_mode
        
        # Lucro padrão (usa 4h por padrão)
        self.min_profit_percent = self.min_profit_4h
        
        # Configuração de stop loss (lida de risk_management)
        risk_mgmt = config.get('risk_management', {})
        self.stop_loss_enabled = risk_mgmt.get('stop_loss_enabled', True)  # Ativo por padrão
        self.stop_loss_percent = abs(risk_mgmt.get('stop_loss_percent', 3.0))
    
    def should_sell(self, current_price: float, buy_price: float, symbol: str = None, 
                   timeframe: str = "4h") -> Tuple[bool, Dict]:
        """
        Verifica se deve vender baseado no lucro atual
        
        Args:
            current_price: Preço atual do ativo
            buy_price: Preço de compra do ativo
            symbol: Par de trading (opcional, para logs)
            timeframe: Timeframe da estratégia ("4h" ou "24h")
        
        Returns:
            (should_sell, info_dict)
        """
        if buy_price <= 0:
            return False, {
                "should_sell": False,
                "reason": "Preço de compra inválido",
                "current_profit": 0.0
            }
        
        # Calcula lucro/prejuízo percentual
        profit_percent = ((current_price - buy_price) / buy_price) * 100
        
        # Define lucro mínimo baseado no timeframe
        if timeframe == "24h":
            min_profit = self.min_profit_24h
        else:  # "4h" ou outro
            min_profit = self.min_profit_4h
        
        # Verifica se atingiu lucro mínimo
        if profit_percent >= min_profit:
            return True, {
                "should_sell": True,
                "reason": f"✅ Lucro de {profit_percent:.2f}% atingiu meta de {min_profit}% ({timeframe})",
                "current_profit": profit_percent,
                "target_profit": min_profit,
                "sell_percentage": 100,
                "action": "TAKE_PROFIT",
                "timeframe": timeframe
            }
        
        # Verifica stop loss (APENAS SE HABILITADO)
        if self.stop_loss_enabled and profit_percent <= -self.stop_loss_percent:
            return True, {
                "should_sell": True,
                "reason": f"🛑 Stop loss ativado: prejuízo de {profit_percent:.2f}%",
                "current_profit": profit_percent,
                "stop_loss": -self.stop_loss_percent,
                "sell_percentage": 100,
                "action": "STOP_LOSS",
                "timeframe": timeframe
            }
        
        # Aguardando lucro
        return False, {
            "should_sell": False,
            "reason": f"Aguardando: lucro atual {profit_percent:.2f}% (meta: {min_profit}% {timeframe})",
            "current_profit": profit_percent,
            "target_profit": min_profit,
            "timeframe": timeframe
        }
    
    def get_config(self) -> Dict:
        """Retorna configuração atual da estratégia"""
        stop_loss_status = "🟢 Ativo" if self.stop_loss_enabled else "🔴 Desativado"
        return {
            "sell_triggers": {
                "min_profit_4h": f"{self.min_profit_4h}%",
                "min_profit_24h": f"{self.min_profit_24h}%",
                "stop_loss": f"-{self.stop_loss_percent}% ({stop_loss_status})"
            },
            "behavior": {
                "mode": "simple",
                "sell_amount": "100%",
                "description": "Vende tudo quando atinge meta ou stop loss",
                "stop_loss_enabled": self.stop_loss_enabled,
                "timeframes": {
                    "4h_scalping": f"{self.min_profit_4h}% (operações rápidas)",
                    "24h_swing": f"{self.min_profit_24h}% (operações lentas)"
                }
            }
        }
