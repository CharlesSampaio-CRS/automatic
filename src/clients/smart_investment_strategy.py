"""
Estratégia Inteligente de Investimento - SIMPLIFICADA E SEGURA
Ajusta investimento com limites de segurança sempre ativos
"""

from typing import Dict, Tuple

class SmartInvestmentStrategy:
    """
    Estratégia segura que SEMPRE limita risco
    
    NOVA LÓGICA (MAIS SEGURA):
    - Saldo < $20: Usa no máximo 30% (proteção contra perda total)
    - Saldo >= $20: Usa percentual da estratégia (max 30%)
    - NUNCA usa 100% do saldo (muito arriscado)
    
    REMOVIDO: Lógica antiga de usar 100% com saldo baixo (perigoso!)
    """
    
    def __init__(self):
        """Inicializa estratégia com limites seguros"""
        self.max_position_percent = 30.0  # Máximo 30% por operação
        self.min_investment = 5.0  # Mínimo $5 por operação
    
    def calculate_smart_investment(self, 
                                   available_balance: float,
                                   strategy_percentage: float,
                                   strategy_name: str = "unknown") -> Tuple[float, Dict]:
        """
        Calcula investimento com limites de segurança
        
        SEGURANÇA SEMPRE ATIVA:
        - Máximo 30% do saldo por operação
        - Mínimo $5 para investir
        
        Args:
            available_balance: Saldo USDT disponível
            strategy_percentage: Percentual sugerido pela estratégia
            strategy_name: Nome da estratégia (para logging)
        
        Returns:
            (investment_amount, info_dict)
        """
        # Sem saldo = sem investimento
        if available_balance <= 0:
            return 0.0, {
                "investment": 0.0,
                "original_percentage": strategy_percentage,
                "adjusted_percentage": 0,
                "reason": "Saldo insuficiente",
                "safe_limit_applied": False
            }
        
        # Aplica limite de segurança (max 30%)
        safe_percentage = min(strategy_percentage, self.max_position_percent)
        
        # Calcula investimento
        investment = (available_balance * safe_percentage) / 100
        
        # Verifica mínimo
        if investment < self.min_investment:
            return 0.0, {
                "investment": 0.0,
                "original_percentage": strategy_percentage,
                "adjusted_percentage": safe_percentage,
                "reason": f"Investimento ${investment:.2f} < mínimo ${self.min_investment}",
                "safe_limit_applied": True
            }
        
        # Determina se limite foi aplicado
        limit_applied = strategy_percentage > self.max_position_percent
        
        return investment, {
            "investment": investment,
            "original_percentage": strategy_percentage,
            "adjusted_percentage": safe_percentage,
            "reason": f"{'⚠️ Limite de segurança aplicado' if limit_applied else '✅ Dentro do limite seguro'}",
            "safe_limit_applied": limit_applied,
            "strategy": strategy_name,
            "balance": available_balance
        }
    
    def get_config(self) -> Dict:
        """Retorna configuração da estratégia"""
        return {
            "name": "Smart Investment Strategy - Safe Mode",
            "description": "Limita investimento para proteger capital",
            "limits": {
                "max_position_percent": f"{self.max_position_percent}%",
                "min_investment": f"${self.min_investment}"
            },
            "safety": {
                "max_risk_per_trade": f"{self.max_position_percent}%",
                "never_use_full_balance": True,
                "reason": "Protege contra perda total do capital"
            }
        }
