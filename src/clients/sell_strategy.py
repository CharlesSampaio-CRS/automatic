"""
Estratégia de Venda Unificada
Suporta vendas progressivas (scaling out) e vendas rápidas (scalping)
"""

from typing import Dict, List, Optional
from datetime import datetime


class SellStrategy:
    """
    Estratégia de venda unificada
    
    ESTRATÉGIAS DISPONÍVEIS:
    1. Venda progressiva (scaling out): Vende em partes conforme lucro aumenta
    2. Venda simples: Vende tudo quando atinge lucro mínimo
    
    Por padrão, usa VENDA SIMPLES com lucro mínimo de 5%
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Inicializa estratégia com configuração do MongoDB
        
        Args:
            config: Configuração completa do MongoDB contendo:
                   - sell_strategy: Níveis de venda progressiva (opcional)
                   - strategy_4h: Configuração de venda rápida (opcional)
        """
        # Inicializa venda progressiva (se disponível)
        if config and 'sell_strategy' in config:
            self._init_progressive_sell(config['sell_strategy'])
        else:
            self._init_progressive_sell_defaults()
        
        # Inicializa venda rápida (se disponível)
        if config and 'strategy_4h' in config:
            self._init_quick_sell(config['strategy_4h'])
        else:
            self._init_quick_sell_defaults()
        
        # Modo de operação: 'simple' ou 'progressive'
        # Simple = vende tudo quando atinge lucro mínimo
        # Progressive = vende em partes conforme lucro aumenta
        self.mode = 'simple'  # Padrão: venda simples
    
    # ========================================================================
    # INICIALIZAÇÃO - VENDA PROGRESSIVA (SCALING OUT)
    # ========================================================================
    
    def _init_progressive_sell(self, sell_strategy: Dict):
        """Inicializa venda progressiva a partir do MongoDB"""
        levels_config = sell_strategy.get('levels', [])
        
        self.progressive_levels = []
        for level in levels_config:
            self.progressive_levels.append({
                "percentage": level.get('sell_percent', level.get('sell_percentage', 33)),
                "profit_target": level.get('profit_percent', level.get('profit_target', 5.0)),
                "name": level.get('name', f"Nível {len(self.progressive_levels) + 1}"),
                "description": level.get('description', '')
            })
        
        if not self.progressive_levels:
            self.progressive_levels = self._get_default_progressive_levels()
    
    def _init_progressive_sell_defaults(self):
        """Inicializa venda progressiva com valores padrão"""
        self.progressive_levels = self._get_default_progressive_levels()
    
    def _get_default_progressive_levels(self):
        """Níveis padrão para venda progressiva"""
        return [
            {"percentage": 33, "profit_target": 5.0,  "name": "Nível 1 - Lucro Seguro"},
            {"percentage": 33, "profit_target": 10.0, "name": "Nível 2 - Lucro Médio"},
            {"percentage": 34, "profit_target": 15.0, "name": "Nível 3 - Lucro Máximo"}
        ]
    
    # ========================================================================
    # INICIALIZAÇÃO - VENDA RÁPIDA (SCALPING)
    # ========================================================================
    
    def _init_quick_sell(self, strategy_4h: Dict):
        """Inicializa venda rápida a partir do MongoDB"""
        self.quick_sell_enabled = strategy_4h.get('enabled', False)
        
        # Lucro alvo para venda rápida (padrão: 5%)
        self.quick_profit_target = strategy_4h.get('quick_profit_target', 5.0)
        
        # Stop loss (padrão: -3%)
        risk_mgmt = strategy_4h.get('risk_management', {})
        self.stop_loss_percent = risk_mgmt.get('stop_loss_percent', -3.0)
    
    def _init_quick_sell_defaults(self):
        """Inicializa venda rápida com valores padrão"""
        self.quick_sell_enabled = False
        self.quick_profit_target = 5.0
        self.stop_loss_percent = -3.0
    
    # ========================================================================
    # VENDA SIMPLES (PADRÃO)
    # ========================================================================
    
    def get_min_profit_for_symbol(self, symbol: str) -> float:
        """
        Retorna o lucro mínimo configurado para o símbolo
        
        Args:
            symbol: Par de trading (ex: REKTCOIN/USDT)
        
        Returns:
            Percentual de lucro mínimo (ex: 5.0 para 5%)
        """
        # Se venda rápida está habilitada, usa seu lucro alvo
        if self.quick_sell_enabled:
            return self.quick_profit_target
        
        # Caso contrário, usa o primeiro nível progressivo
        if self.progressive_levels and len(self.progressive_levels) > 0:
            return self.progressive_levels[0]["profit_target"]
        
        return 5.0  # Padrão: 5%
    
    def should_sell(self, current_price: float, buy_price: float, symbol: str) -> tuple[bool, Dict]:
        """
        Verifica se deve vender baseado no lucro atual
        
        VENDA SIMPLES (padrão):
        - Vende 100% da posição quando lucro >= lucro mínimo
        - Lucro mínimo: 5% (configurável)
        
        Args:
            current_price: Preço atual do ativo
            buy_price: Preço de compra do ativo
            symbol: Par de trading (ex: REKTCOIN/USDT)
        
        Returns:
            (deve_vender, info_dict)
        """
        if buy_price <= 0:
            return False, {
                "should_sell": False,
                "reason": "Preço de compra inválido",
                "current_profit": 0.0,
                "target_profit": 0.0
            }
        
        # Calcula lucro percentual
        profit_percent = ((current_price - buy_price) / buy_price) * 100
        
        # Busca lucro mínimo configurado
        min_profit = self.get_min_profit_for_symbol(symbol)
        
        # Decide se vende
        if profit_percent >= min_profit:
            return True, {
                "should_sell": True,
                "reason": f"Lucro de {profit_percent:.2f}% atingiu meta de {min_profit:.1f}%",
                "current_profit": profit_percent,
                "target_profit": min_profit,
                "sell_percentage": 100  # Vende tudo
            }
        else:
            return False, {
                "should_sell": False,
                "reason": f"Lucro de {profit_percent:.2f}% ainda não atingiu meta de {min_profit:.1f}%",
                "current_profit": profit_percent,
                "target_profit": min_profit
            }
    
    # ========================================================================
    # VENDA PROGRESSIVA (SCALING OUT)
    # ========================================================================
    
    def set_mode_progressive(self):
        """Ativa modo de venda progressiva"""
        self.mode = 'progressive'
    
    def set_mode_simple(self):
        """Ativa modo de venda simples (padrão)"""
        self.mode = 'simple'
    
    def calculate_sell_targets(self, buy_price: float, amount_bought: float, 
                               investment_value: float) -> List[Dict]:
        """
        Calcula os alvos de venda em múltiplos níveis (VENDA PROGRESSIVA)
        
        Args:
            buy_price: Preço de compra
            amount_bought: Quantidade comprada
            investment_value: Valor investido em USDT
        
        Returns:
            Lista de alvos de venda com preços e quantidades
        """
        targets = []
        
        for level in self.progressive_levels:
            # Calcula quantidade a vender neste nível
            sell_amount = (amount_bought * level["percentage"]) / 100
            
            # Calcula preço alvo (buy_price + lucro%)
            target_price = buy_price * (1 + level["profit_target"] / 100)
            
            # Calcula valor que vai receber
            usdt_received = sell_amount * target_price
            
            # Calcula lucro deste nível
            invested_in_level = (investment_value * level["percentage"]) / 100
            profit_usdt = usdt_received - invested_in_level
            profit_pct = level["profit_target"]
            
            targets.append({
                "level": len(targets) + 1,
                "name": level["name"],
                "sell_percentage": level["percentage"],
                "sell_amount": round(sell_amount, 8),
                "target_price": round(target_price, 8),
                "profit_target_pct": profit_pct,
                "usdt_received": round(usdt_received, 2),
                "profit_usdt": round(profit_usdt, 2),
                "invested_in_level": round(invested_in_level, 2),
                "executed": False,
                "execution_date": None,
                "actual_price": None,
                "actual_profit": None
            })
        
        return targets
    
    def check_sell_opportunities(self, current_price: float, 
                                  sell_targets: List[Dict]) -> List[Dict]:
        """
        Verifica quais níveis de venda devem ser executados (VENDA PROGRESSIVA)
        
        Args:
            current_price: Preço atual do ativo
            sell_targets: Lista de alvos de venda
        
        Returns:
            Lista de vendas a executar
        """
        opportunities = []
        
        for target in sell_targets:
            # Pula níveis já executados
            if target.get('executed', False):
                continue
            
            # Verifica se preço atual atingiu o alvo
            if current_price >= target['target_price']:
                opportunities.append(target)
        
        return opportunities
    
    # ========================================================================
    # STOP LOSS
    # ========================================================================
    
    def should_stop_loss(self, current_price: float, buy_price: float) -> tuple[bool, Dict]:
        """
        Verifica se deve acionar stop loss
        
        Args:
            current_price: Preço atual
            buy_price: Preço de compra
        
        Returns:
            (deve_stop_loss, info_dict)
        """
        if buy_price <= 0:
            return False, {"should_stop": False, "reason": "Preço de compra inválido"}
        
        # Calcula prejuízo percentual
        loss_percent = ((current_price - buy_price) / buy_price) * 100
        
        # Verifica se atingiu stop loss
        if loss_percent <= self.stop_loss_percent:
            return True, {
                "should_stop": True,
                "reason": f"Stop loss ativado: prejuízo de {loss_percent:.2f}%",
                "current_loss": loss_percent,
                "stop_loss_threshold": self.stop_loss_percent
            }
        
        return False, {
            "should_stop": False,
            "reason": "Prejuízo ainda não atingiu stop loss",
            "current_loss": loss_percent,
            "stop_loss_threshold": self.stop_loss_percent
        }
    
    # ========================================================================
    # INFORMAÇÕES
    # ========================================================================
    
    def get_strategy_info(self) -> Dict:
        """Retorna informações da estratégia de venda"""
        return {
            "mode": self.mode,
            "quick_sell": {
                "enabled": self.quick_sell_enabled,
                "profit_target": self.quick_profit_target,
                "stop_loss": self.stop_loss_percent
            },
            "progressive_sell": {
                "levels": self.progressive_levels
            }
        }
