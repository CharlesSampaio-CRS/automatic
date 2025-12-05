"""
Estratégia de Compra Simplificada
Detecta quedas e compra com gestão de risco
"""

from typing import Dict, Tuple
from datetime import datetime, timedelta

class BuyStrategy:
    """
    Estratégia de compra baseada em quedas de preço
    
    REGRA SIMPLES:
    - Compra quando preço cai X% ou mais
    - Máximo 30% do saldo por operação (gestão de risco)
    - Cooldown entre compras do mesmo token
    """
    
    def __init__(self, config: Dict = None):
        """
        Inicializa estratégia de compra
        
        Args:
            config: Configuração do MongoDB com:
                   - buy_strategy: Nova estrutura simplificada (preferencial)
                   - trading_mode: Modo safe ou aggressive
                   - strategy_4h/trading_strategy: Estrutura antiga (retrocompatibilidade)
        """
        config = config or {}
        
        # Lê trading_mode (safe ou aggressive)
        trading_mode = config.get('trading_mode', 'safe')
        
        # NOVA ESTRUTURA SIMPLIFICADA (preferencial)
        buy_config = config.get('buy_strategy', {})
        
        if buy_config:
            # Usa estrutura simplificada
            self.min_drop_4h = abs(buy_config.get('min_drop_4h', 5.0))
            self.min_drop_24h = abs(buy_config.get('min_drop_24h', 6.0))
            self.invest_percent_4h = buy_config.get('invest_percent_4h', 15.0)
            self.invest_percent_24h = buy_config.get('invest_percent_24h', 20.0)
            self.cooldown_hours = buy_config.get('cooldown_hours', 4)
        else:
            # RETROCOMPATIBILIDADE: Lê estrutura antiga
            strategy_4h = config.get('strategy_4h', {})
            trading_strategy = config.get('trading_strategy', {})
            
            self.min_drop_4h = abs(strategy_4h.get('min_variation_to_buy', 5.0))
            self.min_drop_24h = abs(trading_strategy.get('min_variation_to_buy', 6.0))
            self.invest_percent_4h = strategy_4h.get('investment_percentage', 15.0)
            self.invest_percent_24h = trading_strategy.get('investment_percentage', 20.0)
            self.cooldown_hours = 4
        
        # Salva trading_mode para referência
        self.trading_mode = trading_mode
        
        # Limites de segurança (lidos de risk_management ou padrão)
        risk_mgmt = config.get('risk_management', {})
        self.max_position_percent = risk_mgmt.get('max_position_percent', 30.0)
        self.min_investment = 5.0  # Mínimo $5 por operação
        
        # Cooldown entre compras do mesmo token
        self.last_buy_times = {}  # {symbol: datetime}
    
    def should_buy_4h(self, variation_4h: float, symbol: str) -> Tuple[bool, Dict]:
        """
        Verifica se deve comprar baseado em variação de 4h (compra rápida)
        
        Args:
            variation_4h: Variação percentual em 4h (ex: -5.5)
            symbol: Par de trading (ex: "BTC/USDT")
        
        Returns:
            (should_buy, info_dict)
        """
        # Verifica cooldown
        if not self._check_cooldown(symbol):
            last_buy = self.last_buy_times.get(symbol)
            hours_ago = (datetime.now() - last_buy).total_seconds() / 3600
            return False, {
                "should_buy": False,
                "reason": f"Cooldown ativo (última compra há {hours_ago:.1f}h)",
                "cooldown_hours": self.cooldown_hours,
                "variation": variation_4h
            }
        
        # Verifica se caiu o suficiente
        if variation_4h <= -self.min_drop_4h:
            return True, {
                "should_buy": True,
                "reason": f"Queda de {variation_4h:.2f}% detectada (mínimo: -{self.min_drop_4h}%)",
                "variation": variation_4h,
                "invest_percent": self.invest_percent_4h,
                "timeframe": "4h"
            }
        
        return False, {
            "should_buy": False,
            "reason": f"Queda insuficiente: {variation_4h:.2f}% (necessário: -{self.min_drop_4h}%)",
            "variation": variation_4h
        }
    
    def should_buy_24h(self, variation_24h: float, symbol: str) -> Tuple[bool, Dict]:
        """
        Verifica se deve comprar baseado em variação de 24h (compra lenta)
        
        Args:
            variation_24h: Variação percentual em 24h (ex: -8.5)
            symbol: Par de trading (ex: "BTC/USDT")
        
        Returns:
            (should_buy, info_dict)
        """
        # Verifica cooldown
        if not self._check_cooldown(symbol):
            last_buy = self.last_buy_times.get(symbol)
            hours_ago = (datetime.now() - last_buy).total_seconds() / 3600
            return False, {
                "should_buy": False,
                "reason": f"Cooldown ativo (última compra há {hours_ago:.1f}h)",
                "cooldown_hours": self.cooldown_hours,
                "variation": variation_24h
            }
        
        # Verifica se caiu o suficiente
        if variation_24h <= -self.min_drop_24h:
            return True, {
                "should_buy": True,
                "reason": f"Queda de {variation_24h:.2f}% detectada (mínimo: -{self.min_drop_24h}%)",
                "variation": variation_24h,
                "invest_percent": self.invest_percent_24h,
                "timeframe": "24h"
            }
        
        return False, {
            "should_buy": False,
            "reason": f"Queda insuficiente: {variation_24h:.2f}% (necessário: -{self.min_drop_24h}%)",
            "variation": variation_24h
        }
    
    def calculate_position_size(self, balance: float, percentage: float) -> float:
        """
        Calcula tamanho da posição com limites de segurança
        
        SEGURANÇA:
        - Nunca mais que 30% do saldo
        - Mínimo $5 por operação
        
        Args:
            balance: Saldo disponível em USDT
            percentage: Percentual sugerido pela estratégia
        
        Returns:
            Valor em USDT a investir
        """
        # Aplica limite máximo de 30%
        safe_percentage = min(percentage, self.max_position_percent)
        
        # Calcula investimento
        investment = (balance * safe_percentage) / 100
        
        # Verifica mínimo
        if investment < self.min_investment:
            return 0.0
        
        return investment
    
    def register_buy(self, symbol: str):
        """Registra compra para controle de cooldown"""
        self.last_buy_times[symbol] = datetime.now()
    
    def _check_cooldown(self, symbol: str) -> bool:
        """Verifica se cooldown já passou"""
        if symbol not in self.last_buy_times:
            return True
        
        last_buy = self.last_buy_times[symbol]
        time_passed = datetime.now() - last_buy
        
        return time_passed >= timedelta(hours=self.cooldown_hours)
    
    def get_config(self) -> Dict:
        """Retorna configuração atual da estratégia"""
        return {
            "buy_triggers": {
                "min_drop_4h": f"-{self.min_drop_4h}%",
                "min_drop_24h": f"-{self.min_drop_24h}%"
            },
            "investment": {
                "percent_4h": f"{self.invest_percent_4h}%",
                "percent_24h": f"{self.invest_percent_24h}%",
                "max_position": f"{self.max_position_percent}%",
                "min_investment": f"${self.min_investment}"
            },
            "risk_management": {
                "cooldown_hours": self.cooldown_hours,
                "max_position_percent": self.max_position_percent
            }
        }
