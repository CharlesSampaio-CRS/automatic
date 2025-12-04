"""
Configurações Estáticas do Bot

NOTA IMPORTANTE:
Este arquivo contém apenas constantes básicas para compatibilidade.
Todas as configurações dinâmicas (pares, intervalos, horários) são 
gerenciadas pelo MongoDB na collection 'BotConfigs'.

O MongoDB é a única fonte de verdade para:
- Pares de Tranding (pair)
- Intervalos de execução (schedule.interval_minutes)
- Estado de habilitação (enabled)
- Horários de negociação (schedule.business_hours_*) [DEPRECATED - bot roda 24/7]
"""

# ===== CONSTANTES BÁSICAS (Hardcoded) =====
# Usadas apenas para validações mínimas e fallback

MIN_VALUE_PER_CREATE_ORDER = 5   # Valor mínimo total de saldo para iniciar operações (USDT) - Reduzido para permitir saldos baixos
MIN_VALUE_PER_SYMBOL = 2          # Valor mínimo por símbolo/trade individual (USDT) - Reduzido para permitir trades com saldo baixo
BASE_CURRENCY = "USDT"            # Moeda base para todas as operações

# ===== CONSTANTES LEGADAS (Deprecated) =====
# Mantidas apenas para compatibilidade com código antigo
# NÃO SÃO MAIS USADAS! MongoDB sobrescreve tudo.

SYMBOLS = []  # Lista vazia - MongoDB define os pares ativos
BUSINESS_HOURS_START = 9  # Ignorado - bot roda 24/7
BUSINESS_HOURS_END = 23   # Ignorado - bot roda 24/7
SCHEDULE_INTERVAL_HOURS = 2  # Ignorado - MongoDB usa interval_minutes

# ===== CLASSE LEGADA (Deprecated) =====
# Mantida apenas para não quebrar testes antigos
# NÃO USE EM CÓDIGO NOVO!

class BotConfig:
    """
    CLASSE LEGADA - NÃO USAR!
    
    Esta classe era usada para ler settings.json.
    Agora todas as configurações vêm do MongoDB.
    
    Use src.services.config_service para acessar MongoDB.
    """
    
    def __init__(self):
        # Inicializado silenciosamente
        self.config = {
            "min_value_per_create_order": MIN_VALUE_PER_CREATE_ORDER,
            "min_value_per_symbol": MIN_VALUE_PER_SYMBOL,
            "base_currency": BASE_CURRENCY,
            "symbols": [],  # Vazio - use MongoDB
        }
    
    def get(self, key: str, default=None):
        """Retorna valores básicos - MongoDB sobrescreve em produção"""
        return self.config.get(key, default)
    
    def get_enabled_symbols(self):
        """Retorna lista vazia - MongoDB define os pares"""
        return []
    
    def get_symbol_config(self, pair: str):
        """Não implementado - use MongoDB"""
        return None

# Instância global (apenas para compatibilidade)
bot_config = BotConfig()
