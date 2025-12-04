"""
Estratégia Inteligente de Investimento
Maximiza lucro ajustando percentuais baseado no saldo disponível
"""

from typing import Dict, Tuple
from src.config.bot_config import SMALL_BALANCE_THRESHOLD, SMALL_BALANCE_USE_FULL, MIN_VALUE_PER_SYMBOL

class SmartInvestmentStrategy:
    """
    Estratégia inteligente que ajusta investimento baseado no saldo
    
    Lógica:
    - Saldo < $10: Usa 100% do saldo (ignora percentuais) para maximizar ganhos
    - Saldo >= $10: Usa percentuais da estratégia (gestão de risco)
    
    Exemplo com $9.01:
        Estratégia diz: "Investe 50%"
        Smart Strategy diz: "Saldo baixo! Investe 100% ($9.01) para maximizar lucro"
    
    Exemplo com $50.00:
        Estratégia diz: "Investe 50%"
        Smart Strategy diz: "Saldo bom, investe 50% ($25.00) com gestão de risco"
    """
    
    def __init__(self, 
                 small_balance_threshold: float = SMALL_BALANCE_THRESHOLD,
                 use_full_on_small: bool = SMALL_BALANCE_USE_FULL):
        """
        Inicializa estratégia inteligente
        
        Args:
            small_balance_threshold: Limite para considerar saldo "pequeno" (default: $10)
            use_full_on_small: Se True, usa 100% quando saldo < threshold
        """
        self.small_balance_threshold = small_balance_threshold
        self.use_full_on_small = use_full_on_small
    
    def calculate_smart_investment(self, 
                                   available_balance: float,
                                   strategy_percentage: float,
                                   strategy_name: str = "unknown") -> Tuple[float, Dict]:
        """
        Calcula investimento inteligente baseado no saldo
        
        Args:
            available_balance: Saldo USDT disponível
            strategy_percentage: Percentual sugerido pela estratégia (ex: 50 para 50%)
            strategy_name: Nome da estratégia (4h ou 24h) para logging
        
        Returns:
            Tupla (investment_amount, info) onde:
            - investment_amount: Valor em USDT a investir
            - info: Dicionário com detalhes da decisão
        """
        
        # Se não tem saldo, não investe
        if available_balance <= 0:
            return 0.0, {
                "investment": 0.0,
                "original_percentage": strategy_percentage,
                "adjusted_percentage": 0,
                "reason": "Saldo insuficiente",
                "is_small_balance": False,
                "used_smart_logic": False
            }
        
        # Verifica se é saldo pequeno
        is_small_balance = available_balance < self.small_balance_threshold
        
        # Se saldo pequeno E flag habilitada: usa 100%
        if is_small_balance and self.use_full_on_small:
            # Garante que respeita o mínimo por símbolo
            investment = available_balance
            
            # Se investimento calculado for menor que mínimo, retorna 0
            if investment < MIN_VALUE_PER_SYMBOL:
                return 0.0, {
                    "investment": 0.0,
                    "original_percentage": strategy_percentage,
                    "adjusted_percentage": 0,
                    "reason": f"Investimento (${investment:.2f}) menor que mínimo (${MIN_VALUE_PER_SYMBOL})",
                    "is_small_balance": True,
                    "used_smart_logic": True
                }
            
            return investment, {
                "investment": investment,
                "original_percentage": strategy_percentage,
                "adjusted_percentage": 100,
                "reason": f"🎯 SALDO PEQUENO (<${self.small_balance_threshold}) - Usando 100% para maximizar lucro",
                "is_small_balance": True,
                "used_smart_logic": True,
                "strategy": strategy_name
            }
        
        # Saldo normal: usa percentual da estratégia
        investment = (available_balance * strategy_percentage) / 100
        
        # Se investimento calculado for menor que mínimo, retorna 0
        if investment < MIN_VALUE_PER_SYMBOL:
            return 0.0, {
                "investment": 0.0,
                "original_percentage": strategy_percentage,
                "adjusted_percentage": strategy_percentage,
                "reason": f"Investimento (${investment:.2f}) menor que mínimo (${MIN_VALUE_PER_SYMBOL})",
                "is_small_balance": False,
                "used_smart_logic": False
            }
        
        return investment, {
            "investment": investment,
            "original_percentage": strategy_percentage,
            "adjusted_percentage": strategy_percentage,
            "reason": f"Saldo normal (>=${self.small_balance_threshold}) - Usando {strategy_percentage}% da estratégia",
            "is_small_balance": False,
            "used_smart_logic": False,
            "strategy": strategy_name
        }
    
    def get_adjusted_percentage(self, 
                                available_balance: float,
                                strategy_percentage: float) -> float:
        """
        Retorna apenas o percentual ajustado
        
        Args:
            available_balance: Saldo USDT disponível
            strategy_percentage: Percentual sugerido pela estratégia
        
        Returns:
            Percentual ajustado (0-100)
        """
        is_small_balance = available_balance < self.small_balance_threshold
        
        if is_small_balance and self.use_full_on_small:
            return 100.0
        
        return strategy_percentage
    
    def should_use_full_balance(self, available_balance: float) -> bool:
        """
        Verifica se deve usar saldo completo
        
        Args:
            available_balance: Saldo USDT disponível
        
        Returns:
            True se deve usar 100%, False caso contrário
        """
        return (available_balance < self.small_balance_threshold and 
                self.use_full_on_small)
    
    def get_info(self) -> Dict:
        """
        Retorna informações sobre a estratégia
        
        Returns:
            Dicionário com configurações atuais
        """
        return {
            "name": "Smart Investment Strategy",
            "description": "Ajusta investimento baseado no saldo para maximizar lucro",
            "small_balance_threshold": self.small_balance_threshold,
            "use_full_on_small": self.use_full_on_small,
            "logic": {
                "small_balance": f"Saldo < ${self.small_balance_threshold}: Usa 100%",
                "normal_balance": f"Saldo >= ${self.small_balance_threshold}: Usa % da estratégia"
            }
        }
