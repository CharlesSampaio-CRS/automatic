"""
Estratégia de Venda para Variação de 4 Horas (Scalping)
Vende rápido em alvos menores de lucro
"""

from typing import Dict, List, Optional
from datetime import datetime

class SellStrategy4h:
    """
    Gerencia vendas rápidas baseadas em alvos de lucro de curto prazo
    
    Estratégia:
    - Alvos de lucro menores que estratégia 24h (scalping)
    - Stop loss mais apertado
    - Vende 100% da posição (não usa scaling out)
    - Foco em lucros rápidos e pequenos
    """
    
    def __init__(self, strategy_4h: Optional[Dict] = None):
        """
        Inicializa estratégia com configuração do MongoDB
        
        Args:
            strategy_4h: Configuração de strategy_4h do MongoDB
                        Se None, usa níveis padrão
        """
        if strategy_4h and isinstance(strategy_4h, dict):
            self.enabled = strategy_4h.get('enabled', False)
            self.sell_levels = strategy_4h.get('levels', [])
            
            # Configurações de gestão de risco
            risk_mgmt = strategy_4h.get('risk_management', {})
            self.stop_loss_percent = risk_mgmt.get('stop_loss_percent', -3.0)
            
            if not self.sell_levels:
                self.sell_levels = self._get_default_levels()
        else:
            self.enabled = False
            self.sell_levels = self._get_default_levels()
            self.stop_loss_percent = -3.0
    
    def _get_default_levels(self):
        """Retorna níveis de venda padrão para 4h (mais conservadores que 24h)"""
        return [
            {
                "name": "Scalp Rápido",
                "profit_target": 1.0,
                "sell_percentage": 100,
                "description": "Vende tudo com 1% de lucro"
            },
            {
                "name": "Scalp Médio",
                "profit_target": 2.0,
                "sell_percentage": 100,
                "description": "Vende tudo com 2% de lucro"
            },
            {
                "name": "Scalp Forte",
                "profit_target": 3.0,
                "sell_percentage": 100,
                "description": "Vende tudo com 3% de lucro"
            }
        ]
    
    def get_min_profit_for_symbol(self, symbol: str) -> float:
        """
        Retorna o lucro mínimo configurado para o símbolo
        Usa o primeiro nível (mais conservador)
        
        Args:
            symbol: Par de trading (ex: REKTCOIN/USDT)
        
        Returns:
            Percentual de lucro mínimo (ex: 1.0 para 1%)
        """
        if self.sell_levels and len(self.sell_levels) > 0:
            return self.sell_levels[0]["profit_target"]
        return 1.0  # Padrão: 1% de lucro mínimo para scalping
    
    def should_sell(self, current_price: float, buy_price: float, symbol: str) -> tuple[bool, Dict]:
        """
        Verifica se deve vender baseado no lucro atual ou stop loss
        
        Args:
            current_price: Preço atual do ativo
            buy_price: Preço de compra do ativo
            symbol: Par de trading (ex: REKTCOIN/USDT)
        
        Returns:
            Tupla (should_sell, sell_info) com informações da decisão
        """
        # Verifica se estratégia está habilitada
        if not self.enabled:
            return False, {
                "should_sell": False,
                "reason": "Estratégia 4h desabilitada",
                "profit_percent": 0.0,
                "strategy": "4h"
            }
        
        if buy_price <= 0:
            return False, {
                "should_sell": False,
                "reason": "Preço de compra inválido",
                "profit_percent": 0.0,
                "strategy": "4h"
            }
        
        # Calcula lucro/prejuízo percentual
        profit_percent = ((current_price - buy_price) / buy_price) * 100
        
        # Verifica STOP LOSS primeiro
        if profit_percent <= self.stop_loss_percent:
            return True, {
                "should_sell": True,
                "reason": f"🛑 STOP LOSS ativado: {profit_percent:.2f}% (limite: {self.stop_loss_percent}%)",
                "profit_percent": profit_percent,
                "sell_percentage": 100,
                "level": "Stop Loss",
                "is_stop_loss": True,
                "strategy": "4h"
            }
        
        # Busca lucro mínimo configurado
        min_profit = self.get_min_profit_for_symbol(symbol)
        
        # Verifica se atingiu alvo de lucro
        if profit_percent >= min_profit:
            # Encontra o nível específico atingido
            matching_level = None
            for level in sorted(self.sell_levels, key=lambda x: x['profit_target']):
                if profit_percent >= level['profit_target']:
                    matching_level = level
            
            if matching_level:
                return True, {
                    "should_sell": True,
                    "reason": f"✅ Alvo atingido: {profit_percent:.2f}% → {matching_level['description']}",
                    "profit_percent": profit_percent,
                    "sell_percentage": matching_level['sell_percentage'],
                    "level": matching_level['name'],
                    "profit_target": matching_level['profit_target'],
                    "is_stop_loss": False,
                    "strategy": "4h"
                }
        
        # Não vende ainda
        return False, {
            "should_sell": False,
            "reason": f"Lucro atual {profit_percent:.2f}% < Alvo {min_profit}%",
            "profit_percent": profit_percent,
            "strategy": "4h"
        }
    
    def calculate_sell_amount(self, amount_held: float, sell_percentage: float) -> float:
        """
        Calcula quantidade a vender
        
        Args:
            amount_held: Quantidade total mantida
            sell_percentage: Percentual a vender (sempre 100% no scalping)
        
        Returns:
            Quantidade a vender
        """
        if amount_held <= 0 or sell_percentage <= 0:
            return 0.0
        
        # No scalping, sempre vende tudo (100%)
        return amount_held
    
    def calculate_profit(self, buy_price: float, sell_price: float, 
                        amount: float, fee_percent: float = 0.1) -> Dict:
        """
        Calcula lucro líquido da operação
        
        Args:
            buy_price: Preço de compra
            sell_price: Preço de venda
            amount: Quantidade negociada
            fee_percent: Percentual de taxa (padrão 0.1%)
        
        Returns:
            Dicionário com informações de lucro
        """
        if buy_price <= 0 or sell_price <= 0 or amount <= 0:
            return {
                "gross_profit_usdt": 0.0,
                "net_profit_usdt": 0.0,
                "profit_percent": 0.0,
                "fees_usdt": 0.0
            }
        
        # Valores brutos
        buy_value = buy_price * amount
        sell_value = sell_price * amount
        gross_profit = sell_value - buy_value
        
        # Calcula taxas (aplicadas na compra E na venda)
        buy_fee = buy_value * (fee_percent / 100)
        sell_fee = sell_value * (fee_percent / 100)
        total_fees = buy_fee + sell_fee
        
        # Lucro líquido
        net_profit = gross_profit - total_fees
        
        # Percentual de lucro sobre investimento
        profit_percent = (net_profit / buy_value) * 100 if buy_value > 0 else 0.0
        
        return {
            "buy_value_usdt": buy_value,
            "sell_value_usdt": sell_value,
            "gross_profit_usdt": gross_profit,
            "net_profit_usdt": net_profit,
            "profit_percent": profit_percent,
            "fees_usdt": total_fees,
            "buy_fee_usdt": buy_fee,
            "sell_fee_usdt": sell_fee
        }
    
    def get_strategy_info(self) -> Dict:
        """
        Retorna informações sobre a estratégia
        
        Returns:
            Dicionário com configurações atuais
        """
        return {
            "enabled": self.enabled,
            "levels": self.sell_levels,
            "risk_management": {
                "stop_loss_percent": self.stop_loss_percent
            },
            "strategy_type": "scalping",
            "sell_mode": "all_at_once"  # Sempre vende 100%
        }
