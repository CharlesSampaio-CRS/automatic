"""
Estratégia de Compra para Variação de 4 Horas (Scalping)
Compra em quedas rápidas dentro de 4 horas
"""

from typing import Dict, Optional
from datetime import datetime, timedelta

class BuyStrategy4h:
    """
    Gerencia compras rápidas baseadas em variação de 4 horas
    
    Estratégia:
    - Monitora variação de preço em 4 horas
    - Compra em quedas rápidas (scalping)
    - Usa níveis mais agressivos que a estratégia 24h
    - Mantém cooldown para evitar overtrading
    - Position sizing menor para gerenciar risco
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
            
            # MongoDB usa estrutura: strategy_4h.buy_strategy.levels
            buy_strategy = strategy_4h.get('buy_strategy', {})
            self.buy_levels = buy_strategy.get('levels', [])
            
            # Configurações de gestão de risco
            risk_mgmt = strategy_4h.get('risk_management', {})
            self.stop_loss_percent = risk_mgmt.get('stop_loss_percent', -3.0)
            self.cooldown_minutes = risk_mgmt.get('cooldown_minutes', 15)
            self.max_trades_per_hour = risk_mgmt.get('max_trades_per_hour', 3)
            # MongoDB usa 'max_percentage_per_trade', não 'max_position_size_percent'
            self.max_position_size_percent = risk_mgmt.get('max_percentage_per_trade', 30.0)
            
            if not self.buy_levels:
                self.buy_levels = self._get_default_levels()
        else:
            self.enabled = False
            self.buy_levels = self._get_default_levels()
            self.stop_loss_percent = -3.0
            self.cooldown_minutes = 15
            self.max_trades_per_hour = 3
            self.max_position_size_percent = 30.0
        
        # Rastreamento de trades recentes
        self.recent_trades = []
    
    def _get_default_levels(self):
        """Retorna níveis de compra padrão para 4h (mais agressivos que 24h)"""
        return [
            {
                "name": "Scalp Leve",
                "variation_threshold": -2.0,
                "percentage_of_balance": 5,
                "description": "Compra pequena em queda rápida de 2%"
            },
            {
                "name": "Scalp Moderado",
                "variation_threshold": -3.0,
                "percentage_of_balance": 7,
                "description": "Compra média em queda de 3%"
            },
            {
                "name": "Scalp Forte",
                "variation_threshold": -5.0,
                "percentage_of_balance": 10,
                "description": "Compra forte em queda brusca de 5%"
            },
            {
                "name": "Queda Acentuada",
                "variation_threshold": -8.0,
                "percentage_of_balance": 50,
                "description": "Compra agressiva em queda acentuada de 8% - investe 50% do saldo"
            }
        ]
    
    def _clean_old_trades(self):
        """Remove trades com mais de 1 hora do rastreamento"""
        now = datetime.now()
        one_hour_ago = now - timedelta(hours=1)
        self.recent_trades = [
            trade for trade in self.recent_trades 
            if trade['timestamp'] > one_hour_ago
        ]
    
    def _is_in_cooldown(self, symbol: str) -> bool:
        """
        Verifica se o símbolo está em período de cooldown
        
        Args:
            symbol: Par de trading (ex: REKTCOIN/USDT)
        
        Returns:
            True se em cooldown, False caso contrário
        """
        self._clean_old_trades()
        
        now = datetime.now()
        cooldown_threshold = now - timedelta(minutes=self.cooldown_minutes)
        
        # Verifica se há algum trade recente dentro do cooldown
        for trade in self.recent_trades:
            if trade['symbol'] == symbol and trade['timestamp'] > cooldown_threshold:
                return True
        
        return False
    
    def _has_exceeded_trade_limit(self, symbol: str) -> bool:
        """
        Verifica se excedeu limite de trades por hora
        
        Args:
            symbol: Par de trading (ex: REKTCOIN/USDT)
        
        Returns:
            True se excedeu limite, False caso contrário
        """
        self._clean_old_trades()
        
        # Conta trades deste símbolo na última hora
        symbol_trades = [
            trade for trade in self.recent_trades 
            if trade['symbol'] == symbol
        ]
        
        return len(symbol_trades) >= self.max_trades_per_hour
    
    def _register_trade(self, symbol: str):
        """
        Registra um novo trade para controle de cooldown e limites
        
        Args:
            symbol: Par de trading (ex: REKTCOIN/USDT)
        """
        self.recent_trades.append({
            'symbol': symbol,
            'timestamp': datetime.now()
        })
    
    def should_buy(self, variation_4h: float, symbol: str) -> tuple[bool, Dict]:
        """
        Determina se deve comprar baseado na variação de 4h
        
        Args:
            variation_4h: Variação percentual do preço nas últimas 4 horas
            symbol: Par de trading (ex: REKTCOIN/USDT)
        
        Returns:
            Tupla (should_buy, buy_info) onde buy_info contém:
            - level: Nível de compra ativado
            - percentage: % do saldo a investir (limitado por max_position_size_percent)
            - reason: Motivo da compra ou recusa
            - signal_strength: Força do sinal (0-100)
            - strategy: '1h' para identificar a estratégia
        """
        # Verifica se estratégia está habilitada
        if not self.enabled:
            return False, {
                "should_buy": False,
                "reason": "Estratégia 1h desabilitada",
                "signal_strength": 0,
                "buy_percentage": 0,
                "strategy": "1h"
            }
        
        # NUNCA compra em alta
        if variation_4h >= 0:
            return False, {
                "should_buy": False,
                "reason": f"Preço em alta 4h ({variation_4h:+.1f}%) - Aguardando queda",
                "signal_strength": 0,
                "buy_percentage": 0,
                "strategy": "1h"
            }
        
        # Verifica cooldown
        if self._is_in_cooldown(symbol):
            return False, {
                "should_buy": False,
                "reason": f"Em cooldown ({self.cooldown_minutes}min) - Aguardando",
                "signal_strength": 0,
                "buy_percentage": 0,
                "strategy": "1h"
            }
        
        # Verifica limite de trades por hora
        if self._has_exceeded_trade_limit(symbol):
            return False, {
                "should_buy": False,
                "reason": f"Limite de {self.max_trades_per_hour} trades/hora atingido",
                "signal_strength": 0,
                "buy_percentage": 0,
                "strategy": "1h"
            }
        
        # Encontra o nível de compra apropriado
        # Ordena do MENOR para o MAIOR (mais negativo para menos negativo)
        # Ex: -10, -5, -3
        matching_level = None
        sorted_levels = sorted(self.buy_levels, key=lambda x: x['variation_threshold'])
        
        # Pega o PRIMEIRO nível que a variação atingiu (mais restritivo/maior investimento)
        # Se variação é -7%, atinge -3% e -5%, mas devemos usar -5% (maior investimento)
        # Se variação é -11%, atinge todos, mas devemos usar -10% (maior investimento)
        for level in sorted_levels:
            threshold = level['variation_threshold']
            if variation_4h <= threshold:
                matching_level = level
                break  # QUEBRA aqui para pegar o primeiro que atende
        
        # Se não encontrou nível, queda não foi suficiente
        if not matching_level:
            return False, {
                "should_buy": False,
                "reason": f"Queda 4h ({variation_4h:.1f}%) insuficiente para níveis configurados",
                "signal_strength": 0,
                "buy_percentage": 0,
                "strategy": "1h"
            }
        
        # Limita o percentual ao máximo configurado
        buy_percentage = min(
            matching_level['percentage_of_balance'],
            self.max_position_size_percent
        )
        
        # Calcula força do sinal (0-100)
        # Quanto maior a queda, maior a força
        max_drop = min([level['variation_threshold'] for level in self.buy_levels])
        signal_strength = min(100, int((abs(variation_4h) / abs(max_drop)) * 100))
        
        # Registra o trade
        self._register_trade(symbol)
        
        return True, {
            "should_buy": True,
            "level": matching_level['name'],
            "percentage": buy_percentage,
            "buy_percentage": buy_percentage,
            "reason": f"Queda rápida 4h: {variation_4h:.2f}% → {matching_level['description']}",
            "signal_strength": signal_strength,
            "variation_4h": variation_4h,
            "threshold": matching_level['variation_threshold'],
            "strategy": "1h"
        }
    
    def calculate_position_size(self, available_balance: float, buy_percentage: float) -> float:
        """
        Calcula o tamanho da posição baseado no saldo disponível
        
        Args:
            available_balance: Saldo disponível em USDT
            buy_percentage: Percentual do saldo a investir
        
        Returns:
            Valor em USDT a investir
        """
        if available_balance <= 0 or buy_percentage <= 0:
            return 0.0
        
        # Limita ao máximo configurado
        effective_percentage = min(buy_percentage, self.max_position_size_percent)
        
        position_size = (available_balance * effective_percentage) / 100
        
        return position_size
    
    def get_strategy_info(self) -> Dict:
        """
        Retorna informações sobre a estratégia
        
        Returns:
            Dicionário com configurações atuais
        """
        return {
            "enabled": self.enabled,
            "levels": self.buy_levels,
            "risk_management": {
                "stop_loss_percent": self.stop_loss_percent,
                "cooldown_minutes": self.cooldown_minutes,
                "max_trades_per_hour": self.max_trades_per_hour,
                "max_position_size_percent": self.max_position_size_percent
            },
            "recent_trades_count": len(self.recent_trades)
        }
