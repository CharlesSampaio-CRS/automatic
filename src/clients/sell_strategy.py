"""
Estratégia de Venda com Trailing Stop
Vende 50% no alvo inicial + 50% com trailing stop para pegar picos
"""

from typing import Dict, Tuple

class SellStrategy:
    """
    Estratégia de venda em 2 fases para maximizar lucros
    
    FASE 1 - GARANTIR LUCRO:
    - Vende 50% quando atinge +8% (lucro garantido)
    
    FASE 2 - PEGAR PICO:
    - 50% restantes com trailing stop de 4%
    - Vende quando cair 4% do pico máximo atingido
    - Sem limite de quanto pode subir!
    
    EXEMPLO:
    - +8%: Vende 50% (garante $0.52)
    - +15%: Continua segurando 50%
    - +25%: Pico! Stop em +21%
    - Cai para +21%: Vende 50% restantes
    - Resultado: $0.52 + $1.14 = $1.66 total 🚀
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
                   - trailing_stop: Configuração do trailing stop
        """
        config = config or {}
        
        # Lê trading_mode (safe ou aggressive)
        trading_mode = config.get('trading_mode', 'safe')
        
        # NOVA ESTRUTURA SIMPLIFICADA (preferencial)
        sell_config = config.get('sell_strategy', {})
        
        if sell_config:
            # Usa estrutura simplificada
            self.min_profit_4h = sell_config.get('min_profit_4h', 8.0)
            self.min_profit_24h = sell_config.get('min_profit_24h', 12.0)
        else:
            # RETROCOMPATIBILIDADE: Lê estrutura antiga
            strategy_4h = config.get('strategy_4h', {})
            trading_strategy = config.get('trading_strategy', {})
            
            self.min_profit_4h = strategy_4h.get('quick_profit_target', 8.0)
            self.min_profit_24h = trading_strategy.get('profit_target', 12.0)
        
        # Salva trading_mode para referência
        self.trading_mode = trading_mode
        
        # Lucro padrão (usa 4h por padrão)
        self.min_profit_percent = self.min_profit_4h
        
        # Configuração de stop loss (lida de risk_management)
        risk_mgmt = config.get('risk_management', {})
        self.stop_loss_enabled = risk_mgmt.get('stop_loss_enabled', True)  # Ativo por padrão
        self.stop_loss_percent = abs(risk_mgmt.get('stop_loss_percent', 3.0))
        
        # NOVO: Configuração do trailing stop
        trailing_config = config.get('trailing_stop', {})
        self.trailing_enabled = trailing_config.get('enabled', True)  # Ativo por padrão
        self.trailing_activation = trailing_config.get('activation_profit', 8.0)  # Ativa em +8%
        self.trailing_distance = trailing_config.get('distance_percent', 4.0)  # 4% do pico
        self.partial_sell_percent = trailing_config.get('partial_sell_percent', 50.0)  # Vende 50% primeiro
    
    def should_sell(self, current_price: float, buy_price: float, symbol: str = None, 
                   timeframe: str = "4h", peak_price: float = None, 
                   partial_sell_executed: bool = False) -> Tuple[bool, Dict]:
        """
        Verifica se deve vender baseado em trailing stop
        
        LÓGICA EM 2 FASES:
        
        FASE 1 (Garantir lucro):
        - Se lucro >= +8% E ainda não vendeu 50%
        - VENDE 50% da posição
        - Lucro garantido ✅
        
        FASE 2 (Pegar pico com trailing stop):
        - Após vender 50%, ativa trailing stop
        - Rastreia pico máximo
        - Vende quando cair 4% do pico
        
        Args:
            current_price: Preço atual do ativo
            buy_price: Preço de compra do ativo
            symbol: Par de trading (opcional, para logs)
            timeframe: Timeframe da estratégia ("4h" ou "24h")
            peak_price: Preço máximo atingido após partial sell (para trailing)
            partial_sell_executed: Se já vendeu 50% da posição
        
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
        
        # ====================================
        # FASE 1: VENDA PARCIAL (50%)
        # ====================================
        if self.trailing_enabled and not partial_sell_executed:
            # Verifica se atingiu o alvo de ativação do trailing
            if profit_percent >= self.trailing_activation:
                return True, {
                    "should_sell": True,
                    "reason": f"🎯 FASE 1: Lucro de {profit_percent:.2f}% atingiu {self.trailing_activation}% - Vendendo {self.partial_sell_percent}%",
                    "current_profit": profit_percent,
                    "target_profit": self.trailing_activation,
                    "sell_percentage": self.partial_sell_percent,  # Vende 50%
                    "action": "PARTIAL_SELL",
                    "phase": 1,
                    "timeframe": timeframe,
                    "next_phase": "Trailing stop ativado para 50% restantes"
                }
        
        # ====================================
        # FASE 2: TRAILING STOP (50% restantes)
        # ====================================
        if self.trailing_enabled and partial_sell_executed:
            # Precisa ter peak_price para calcular trailing
            if peak_price is None:
                peak_price = current_price
            
            # Atualiza pico se preço atual for maior
            if current_price > peak_price:
                peak_price = current_price
            
            # Calcula trailing stop (4% abaixo do pico)
            trailing_stop_price = peak_price * (1 - self.trailing_distance / 100)
            
            # Calcula lucro no pico e no trailing stop
            peak_profit = ((peak_price - buy_price) / buy_price) * 100
            trailing_profit = ((trailing_stop_price - buy_price) / buy_price) * 100
            
            # Se preço atual caiu abaixo do trailing stop, VENDE!
            if current_price <= trailing_stop_price:
                return True, {
                    "should_sell": True,
                    "reason": f"🚀 FASE 2: Trailing stop ativado! Pico: +{peak_profit:.2f}% → Atual: +{profit_percent:.2f}%",
                    "current_profit": profit_percent,
                    "peak_profit": peak_profit,
                    "trailing_stop_profit": trailing_profit,
                    "sell_percentage": 100 - self.partial_sell_percent,  # Vende 50% restantes
                    "action": "TRAILING_STOP",
                    "phase": 2,
                    "timeframe": timeframe,
                    "peak_price": peak_price,
                    "stop_price": trailing_stop_price
                }
            
            # Ainda subindo ou dentro da margem do trailing
            return False, {
                "should_sell": False,
                "reason": f"🔥 FASE 2: Segurando! Pico: +{peak_profit:.2f}% | Atual: +{profit_percent:.2f}% | Stop: +{trailing_profit:.2f}%",
                "current_profit": profit_percent,
                "peak_profit": peak_profit,
                "trailing_stop_profit": trailing_profit,
                "peak_price": peak_price,
                "phase": 2,
                "timeframe": timeframe
            }
        
        # ====================================
        # MODO LEGADO (trailing desabilitado)
        # ====================================
        if not self.trailing_enabled:
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
        trailing_status = "🟢 Ativo" if self.trailing_enabled else "🔴 Desativado"
        
        config = {
            "sell_triggers": {
                "min_profit_4h": f"{self.min_profit_4h}%",
                "min_profit_24h": f"{self.min_profit_24h}%",
                "stop_loss": f"-{self.stop_loss_percent}% ({stop_loss_status})"
            },
            "behavior": {
                "mode": "trailing_stop" if self.trailing_enabled else "simple",
                "description": "Venda em 2 fases: 50% no alvo + 50% trailing stop" if self.trailing_enabled else "Vende tudo quando atinge meta ou stop loss",
                "stop_loss_enabled": self.stop_loss_enabled,
                "timeframes": {
                    "4h_scalping": f"{self.min_profit_4h}% (operações rápidas)",
                    "24h_swing": f"{self.min_profit_24h}% (operações lentas)"
                }
            }
        }
        
        # Adiciona info do trailing stop se habilitado
        if self.trailing_enabled:
            config["trailing_stop"] = {
                "status": trailing_status,
                "activation_profit": f"+{self.trailing_activation}%",
                "distance": f"{self.trailing_distance}%",
                "partial_sell": f"{self.partial_sell_percent}%",
                "phases": {
                    "phase_1": f"Vende {self.partial_sell_percent}% em +{self.trailing_activation}%",
                    "phase_2": f"Trailing stop de {self.trailing_distance}% nos {100-self.partial_sell_percent}% restantes"
                }
            }
        
        return config
