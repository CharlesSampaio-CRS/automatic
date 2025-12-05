"""
Estratégia de Compra Temporária
"""

class BuyStrategy:
    def __init__(self, config=None):
        self.config = config or {}
    
    def should_buy_4h(self, variation_4h, symbol):
        return False, {"reason": "Not configured"}
    
    def should_buy_24h(self, variation_24h):
        return False, {"reason": "Not configured"}
    
    def calculate_position_size(self, balance, percentage):
        return balance * (percentage / 100)
