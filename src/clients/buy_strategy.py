"""
Estratégia de Compra Gradativa na Queda
Compra APENAS quando o preço está caindo
Quanto MAIOR a queda, MAIOR o investimento
"""

from typing import Dict, List, Optional
from datetime import datetime

class BuyStrategy:
    """
    Gerencia compras graduais em quedas de preço
    
    Estratégia:
    - Compra APENAS na queda (NUNCA na alta)
    - Divide investimento em níveis baseados na % de queda
    - Quanto mais baixo o preço, maior a alocação
    - Mantém reserva para comprar ainda mais baixo
    """
    
    def __init__(self, Tranding_strategy: Optional[Dict] = None):
        """
        Inicializa estratégia com configuração do MongoDB
        
        Args:
            Tranding_strategy: Configuração de trading_strategy do MongoDB
                             Se None, usa níveis padrão
        """
        if Tranding_strategy and isinstance(Tranding_strategy, dict):
            # MongoDB usa estrutura: trading_strategy.buy_on_dip.thresholds
            buy_on_dip = Tranding_strategy.get('buy_on_dip', {})
            thresholds = buy_on_dip.get('thresholds', [])
            
            # Converte thresholds do MongoDB para formato de levels
            self.buy_levels = []
            for threshold in thresholds:
                # Usa variation_max como threshold (ponto de entrada)
                self.buy_levels.append({
                    "name": threshold.get('description', 'Compra'),
                    "variation_threshold": threshold.get('variation_max', 0),
                    "percentage_of_balance": threshold.get('percentage_of_balance', 0),
                    "description": threshold.get('description', '')
                })
            
            if not self.buy_levels:
                self.buy_levels = self._get_default_levels()
        else:
            self.buy_levels = self._get_default_levels()
    
    def _get_default_levels(self):
        """Retorna níveis de compra padrão"""
        return [
            {
                "name": "Compra Leve",
                "variation_threshold": -5.0,
                "percentage_of_balance": 20,
                "description": "Começa a comprar em quedas pequenas"
            },
            {
                "name": "Compra Moderada",
                "variation_threshold": -10.0,
                "percentage_of_balance": 30,
                "description": "Aumenta compra em quedas médias"
            },
            {
                "name": "Compra Forte",
                "variation_threshold": -15.0,
                "percentage_of_balance": 50,
                "description": "Compra pesado em quedas grandes"
            },
            {
                "name": "Compra Agressiva",
                "variation_threshold": -20.0,
                "percentage_of_balance": 70,
                "description": "Compra muito forte em quedas severas"
            },
            {
                "name": "Compra Máxima",
                "variation_threshold": -40.0,
                "percentage_of_balance": 100,
                "description": "All-in em quedas extremas (crash/oportunidade única)"
            }
        ]
    
    def should_buy(self, variation_24h: float) -> tuple[bool, Dict]:
        """
        Determina se deve comprar baseado na variação de 24h
        
        Args:
            variation_24h: Variação percentual do preço nas últimas 24h
        
        Returns:
            Tupla (should_buy, buy_info) onde buy_info contém:
            - level: Nível de compra ativado
            - percentage: % do saldo a investir
            - reason: Motivo da compra
            - signal_strength: Força do sinal (0-100)
        """
        # NUNCA compra em alta
        if variation_24h >= 0:
            return False, {
                "should_buy": False,
                "reason": f"Preço em alta ({variation_24h:+.1f}%) - Aguardando queda",
                "signal_strength": 0,
                "buy_percentage": 0
            }
        
        # Encontra o nível de compra apropriado
        # Quanto maior a queda (mais negativo), maior o nível de investimento
        # Exemplo: -12% deve pegar o nível de -10% (já passou de -5%, mas não chegou em -15%)
        matching_level = None
        
        # Ordena do maior threshold para o menor (-5, -10, -15, -20)
        # Pega o PRIMEIRO (maior threshold) onde a queda seja >= threshold
        # Em números negativos: -10% é maior que -15%, então -10 >= -15
        for level in sorted(self.buy_levels, key=lambda x: x['variation_threshold'], reverse=True):
            # Se variation é -12% e threshold é -10%, então -12 <= -10 (True, atingiu)
            # Se variation é -12% e threshold é -15%, então -12 <= -15 (False, não atingiu)
            if variation_24h <= level['variation_threshold']:
                matching_level = level
                # NÃO para aqui, continua procurando thresholds menores (mais negativos)
        
        if matching_level:
            signal_strength = abs(variation_24h / matching_level['variation_threshold']) * 100
            
            return True, {
                "should_buy": True,
                "level": matching_level,
                "percentage": matching_level['percentage_of_balance'],
                "reason": f"{matching_level['name']}: {variation_24h:.1f}% (investe {matching_level['percentage_of_balance']}% do saldo)",
                "signal_strength": round(signal_strength, 2),
                "buy_percentage": matching_level['percentage_of_balance']
            }
        
        # Queda não atinge nenhum nível
        return False, {
            "should_buy": False,
            "reason": f"Queda de {variation_24h:.1f}% não atinge nível mínimo",
            "signal_strength": 0,
            "buy_percentage": 0
        }
    
    def filter_symbols(self, symbol_variations: List[Dict], symbols_config: List[Dict]) -> List[Dict]:
        """
        Filtra símbolos que devem ser comprados baseado na estratégia
        
        Args:
            symbol_variations: Lista com símbolos e suas variações
            symbols_config: Configuração dos símbolos habilitados
        
        Returns:
            Lista de símbolos filtrados com informações de compra
        """
        filtered = []
        
        for variation_data in symbol_variations:
            symbol = variation_data['symbol']
            variation = variation_data['variation_24h']
            
            # Busca configuração do símbolo
            symbol_config = next((s for s in symbols_config if s['pair'] == symbol), None)
            if not symbol_config or not symbol_config.get('enabled', False):
                continue
            
            # Verifica se deve comprar
            should_buy, buy_info = self.should_buy(variation)
            
            if should_buy:
                filtered.append({
                    **variation_data,
                    'config': symbol_config,
                    'signal_strength': buy_info['signal_strength'],
                    'buy_percentage': buy_info['buy_percentage'],
                    'reason': buy_info['reason'],
                    'level': buy_info.get('level', {})
                })
        
        # Ordena por força do sinal (maior queda = maior prioridade)
        return sorted(filtered, key=lambda x: x['signal_strength'], reverse=True)
    
    def calculate_investment_amount(self, available_balance: float, buy_percentage: int) -> float:
        """
        Calcula quanto investir baseado no nível de queda
        
        Args:
            available_balance: Saldo disponível em USDT
            buy_percentage: Porcentagem do saldo a investir (0-100)
        
        Returns:
            Valor a investir em USDT
        """
        investment = (available_balance * buy_percentage) / 100
        return round(investment, 2)
    
    def get_summary(self) -> Dict:
        """
        Retorna resumo da estratégia de compra
        """
        return {
            "strategy_type": "gradual_dip_buying",
            "description": "Compra gradativa na queda - quanto mais baixo, maior a compra",
            "total_levels": len(self.buy_levels),
            "levels": [
                {
                    "name": level['name'],
                    "trigger": f"{level['variation_threshold']:+.1f}%",
                    "allocation": f"{level['percentage_of_balance']}%",
                    "description": level['description']
                }
                for level in self.buy_levels
            ],
            "rules": [
                "NUNCA compra em alta",
                "Compra APENAS na queda",
                "Quanto MAIOR a queda, MAIOR o investimento",
                "Mantém reserva para quedas maiores"
            ]
        }


def example_usage():
    """
    Exemplo de uso da estratégia de compra
    """
    print("\n" + "="*80)
    print(" ESTRATÉGIA DE COMPRA GRADATIVA NA QUEDA - Exemplo")
    print("="*80)
    
    strategy = BuyStrategy()
    
    print(f"\n RESUMO DA ESTRATÉGIA:")
    summary = strategy.get_summary()
    print(f"   Tipo: {summary['description']}")
    print(f"   Total de Níveis: {summary['total_levels']}")
    
    print(f"\n💰 NÍVEIS DE COMPRA:")
    for level in summary['levels']:
        print(f"   • {level['name']}: Queda {level['trigger']} → Investe {level['allocation']}")
    
    print(f"\n📈 REGRAS:")
    for rule in summary['rules']:
        print(f"    {rule}")
    
    # Testa diferentes cenários
    scenarios = [
        (5.0, "Alta"),
        (0.5, "Pequena alta"),
        (-3.0, "Queda leve"),
        (-7.0, "Queda moderada"),
        (-12.0, "Queda significativa"),
        (-18.0, "Queda forte"),
        (-25.0, "Queda extrema")
    ]
    
    print(f"\n🧪 TESTES DE CENÁRIOS:")
    print("="*80)
    
    balance = 100.0
    
    for variation, description in scenarios:
        should_buy, info = strategy.should_buy(variation)
        
        print(f"\n {description}: {variation:+.1f}%")
        print(f"   Decisão: {'🟢 COMPRAR' if should_buy else '⏸️  AGUARDAR'}")
        print(f"   {info['reason']}")
        
        if should_buy:
            investment = strategy.calculate_investment_amount(balance, info['buy_percentage'])
            remaining = balance - investment
            print(f"   💰 Investe: ${investment:.2f} USDT ({info['buy_percentage']}% do saldo)")
            print(f"   💵 Reserva: ${remaining:.2f} USDT para quedas maiores")
            print(f"    Força do Sinal: {info['signal_strength']:.1f}%")
    
    print("\n" + "="*80)


if __name__ == "__main__":
    example_usage()
