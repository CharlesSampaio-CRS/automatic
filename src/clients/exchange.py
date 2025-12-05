import ccxt
from datetime import datetime
import sys
import os
import requests
from typing import Optional, Dict

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.config.bot_config import MIN_VALUE_PER_CREATE_ORDER, MIN_VALUE_PER_SYMBOL, SYMBOLS, BASE_CURRENCY
from src.utils.number_formatter import format_price, format_amount, format_usdt, format_percent

# Importa estratégias unificadas de compra e venda
from src.clients.buy_strategy import BuyStrategy
from src.clients.sell_strategy import SellStrategy

# Importa estratégia inteligente de investimento
from src.clients.smart_investment_strategy import SmartInvestmentStrategy

# Importa conexão do MongoDB
try:
    from src.database.mongodb_connection import get_database
    db = get_database()
    # Conectado silenciosamente
except Exception as e:
    print(f"! Erro MongoDB: {e}")
    db = None
    print(f"⚠ MongoDB não disponível: {e}")

STATUS_SUCCESS = "SUCCESS"
STATUS_ERROR = "ERROR"

ERROR_INSUFFICIENT_FUNDS = "Insufficient funds to place orders"
ERROR_API_RESPONSE = "API response error"
ERROR_DB_SAVE = "Error saving to the database"
ERROR_BALANCE_FETCH = "Error fetching available balance"

# db = None  # Mock do banco de dados (desabilitado por enquanto)

class MexcClient:
    def __init__(self, api_key, api_secret, config: dict = None):
        """
        Inicializa o cliente MEXC usando ccxt
        Carrega estratégias de compra e venda
        
        Args:
            api_key: Chave da API MEXC
            api_secret: Secret da API MEXC
            config: Configuração do MongoDB (opcional) contendo trading_strategy e sell_strategy
        """
        self.client = ccxt.mexc({
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'spot',  # Trading spot
            }
        })
        
        # Inicializa estratégias com config do MongoDB (se fornecido)
        if config:
            # Valida se strategy_4h_config existe quando config é fornecido
            strategy_4h_config = config.get('strategy_4h')
            if not strategy_4h_config:
                raise ValueError(
                    ' strategy_4h não encontrada na configuração! '
                    'Verifique se o documento no MongoDB possui a chave "strategy_4h".'
                )
            
            # Inicializa estratégias unificadas com estrutura simplificada
            # trading_mode pode ser "safe" ou "aggressive"
            trading_mode = config.get('trading_mode', 'safe')
            
            # BuyStrategy recebe a configuração simplificada
            self.buy_strategy = BuyStrategy({
                'trading_mode': trading_mode,
                'buy_strategy': config.get('buy_strategy', {}),
                # Suporte para estrutura antiga (retrocompatibilidade)
                'trading_strategy': config.get('trading_strategy'),
                'strategy_4h': strategy_4h_config
            })
            
            # SellStrategy recebe a configuração simplificada
            self.sell_strategy = SellStrategy({
                'trading_mode': trading_mode,
                'sell_strategy': config.get('sell_strategy', {}),
                'risk_management': config.get('risk_management', {}),
                # Suporte para estrutura antiga (retrocompatibilidade)
                'strategy_4h': strategy_4h_config
            })
            
            # SmartInvestmentStrategy usa o trading_mode
            self.smart_strategy = SmartInvestmentStrategy(trading_mode)
        else:
            # Sem config: inicializa com None (operações básicas como get_balance)
            self.buy_strategy = None
            self.sell_strategy = None
            self.smart_strategy = SmartInvestmentStrategy()  # Usa modo safe por padrão
        
        # Threshold de volume para decidir entre market/limit
        # Mercados com volume > $1M/24h usam limit (boa liquidez)
        # Mercados com volume < $1M/24h usam market (pouca liquidez)
        self.VOLUME_THRESHOLD_USD = 1_000_000  # $1 milhão
        
        # Blacklist de moedas que NUNCA devem ser consideradas pelo bot
        self.BLACKLIST = ['ICG']  # Adicione mais moedas aqui se necessário
        
        # URL base da API interna (endpoint /prices)
        self.API_BASE_URL = os.getenv('API_BASE_URL', 'http://localhost:5000')
        
    def get_price_data(self, symbol: str) -> Optional[Dict]:
        """
        Busca dados de preço do endpoint /prices/{symbol}
        
        Retorna estrutura completa com:
        - current: Preço atual (last)
        - ask: Preço de compra (o que você paga)
        - bid: Preço de venda (o que você recebe)
        - change_1h_percent: Variação 1h
        - change_4h_percent: Variação 4h
        - change_24h_percent: Variação 24h
        - high_24h, low_24h, volume_24h
        
        Args:
            symbol: Par de trading (ex: BTC/USDT)
        
        Returns:
            Dict com dados do preço ou None se falhar
        """
        try:
            # Remove / do símbolo para URL
            url_symbol = symbol.replace('/', '')
            url = f"{self.API_BASE_URL}/prices/{url_symbol}"
            
            # Faz request com timeout curto
            response = requests.get(url, timeout=3)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('success') and data.get('data'):
                    price_data = data['data']
                    
                    # Retorna dados estruturados
                    return {
                        'symbol': symbol,
                        'current': price_data.get('current', 0),
                        'ask': price_data.get('ask', 0),
                        'bid': price_data.get('bid', 0),
                        'change_1h_percent': price_data.get('change_1h_percent', 0),
                        'change_4h_percent': price_data.get('change_4h_percent', 0),
                        'change_24h_percent': price_data.get('change_24h_percent', 0),
                        'high_24h': price_data.get('high_24h', 0),
                        'low_24h': price_data.get('low_24h', 0),
                        'volume_24h': price_data.get('volume_24h', 0),
                        'source': 'api_endpoint'
                    }
            
            # Se falhar, retorna None para usar fallback
            return None
            
        except Exception as e:
            # Erro silencioso - usa fallback
            return None
        
    def should_use_limit_order(self, symbol: str) -> tuple[bool, str]:
        """
        Decide se deve usar ordem limitada baseado na liquidez do mercado
        
        Args:
            symbol: Par de negociação (ex: "REKT/USDT")
        
        Returns:
            (use_limit, reason) - True se deve usar limit, False para market
        """
        try:
            ticker = self.client.fetch_ticker(symbol)
            volume_24h_usd = float(ticker.get('quoteVolume', 0))  # Volume em USDT
            
            # Se volume > $1M: mercado líquido, usa limit
            if volume_24h_usd >= self.VOLUME_THRESHOLD_USD:
                return True, f"Alto volume (${volume_24h_usd:,.0f}/24h) - usando LIMIT"
            else:
                return False, f"Baixo volume (${volume_24h_usd:,.0f}/24h) - usando MARKET"
                
        except Exception as e:
            # Em caso de erro, usa market por segurança
            print(f"⚠️  Erro ao verificar volume: {e}")
            return False, "Erro ao verificar volume - usando MARKET por segurança"
    
    def get_usdt_available(self):
        """
        Retorna o saldo disponível em USDT
        """
        try:
            balance = self.client.fetch_balance()
            usdt_balance = balance['USDT']['free'] if 'USDT' in balance else 0
            return round(float(usdt_balance), 2)
        except Exception as e:
            print(f"{ERROR_BALANCE_FETCH}: {e}")
            return 0

    def get_USDT_available(self):
        """
        Retorna o saldo disponível em USDT (se disponível na MEXC)
        Caso contrário, retorna USDT
        """
        try:
            balance = self.client.fetch_balance()
            USDT_balance = balance.get('USDT', {}).get('free', 0)
            if USDT_balance > 0:
                return round(float(USDT_balance), 2)
            else:
                # Se não houver USDT, retorna USDT como fallback
                return self.get_usdt_available()
        except Exception as e:
            print(f"{ERROR_BALANCE_FETCH}: {e}")
            return 0

    def get_non_zero_sorted_assets(self):
        """
        Retorna ativos com saldo maior que 1, ordenados por valor
        IGNORA moedas da blacklist
        """
        try:
            balance = self.client.fetch_balance()
            non_zero_assets = []
            
            for currency, data in balance['total'].items():
                # Ignora moedas da blacklist
                if currency in self.BLACKLIST:
                    continue
                    
                if float(data) > 1:
                    non_zero_assets.append({
                        'currency': currency,
                        'balance': str(data),
                        'available': str(balance[currency].get('free', 0))
                    })
            
            return sorted(non_zero_assets, key=lambda x: float(x['balance']), reverse=True)
        except Exception as e:
            print(f"Error fetching assets: {e}")
            return []

    def get_total_assets_in_usdt(self):
        """
        Calcula o valor total dos ativos em USDT
        IGNORA moedas da blacklist
        """
        try:
            balance = self.client.fetch_balance()
            total_in_usdt = 0.0
            
            for currency, data in balance['total'].items():
                balance_amount = float(data)
                if balance_amount <= 0:
                    continue
                
                # Ignora moedas da blacklist
                if currency in self.BLACKLIST:
                    continue
                
                if currency == 'USDT':
                    total_in_usdt += balance_amount
                else:
                    total_in_usdt += self.convert_to_usdt(currency, balance_amount)
            
            available = self.get_usdt_available()
            assets_coin = self.get_non_zero_sorted_assets()
            
            return {
                "total_assets_usdt": round(total_in_usdt - available, 2),
                "available_usdt": available,
                "total_usdt": round(total_in_usdt, 2),
                "date": datetime.now().astimezone(),
                "tokens": assets_coin
            }
        except Exception as e:
            print(f"Error calculating total assets: {e}")
            return {"error": str(e)}

    def get_total_assets_in_USDT(self):
        """
        Alias para manter compatibilidade com o código anterior
        """
        return self.get_total_assets_in_usdt()

    def convert_to_usdt(self, currency, balance):
        """
        Converte o saldo de uma moeda para USDT
        Retorna 0 se a moeda não tiver par USDT na exchange
        """
        if currency == 'USDT':
            return balance
            
        symbol = f"{currency}/USDT"
        try:
            ticker = self.client.fetch_ticker(symbol)
            last_price = float(ticker['last'])
            usdt_value = balance * last_price
            return usdt_value
        except Exception as e:
            error_msg = str(e)
            # Ignora erros de símbolos que não existem na exchange
            if "does not have market symbol" in error_msg:
                # Não imprime erro para moedas sem par USDT (é normal ter)
                pass
            else:
                print(f"⚠️  Error converting {currency} to USDT: {e}")
            return 0

    def get_symbol_variations(self):
        """
        Retorna as variações de 24h dos símbolos configurados no MongoDB
        """
        variations = []
        
        # Busca símbolos configurados no MongoDB
        if db is not None:
            symbols_config = list(db['BotConfigs'].find({'enabled': True}))
            print(f" Símbolos configurados no MongoDB: {len(symbols_config)}")
            
            for config in symbols_config:
                symbol = config.get('pair')
                if symbol:
                    print(f"   > Analisando {symbol}...")
                    variation = self.get_symbol_variation(symbol)
                    if variation:
                        variations.append(variation)
        else:
            print("⚠️  MongoDB não disponível - usando lista vazia")
        
        print(f" Total de variações coletadas: {len(variations)}")
        return sorted(variations, key=lambda x: x['variation_24h'])

    def get_symbol_variation(self, symbol):
        """
        Retorna a variação de 24h de um símbolo específico
        Retorna None se o símbolo não existir na exchange
        """
        try:
            ticker = self.client.fetch_ticker(symbol)
            if ticker and 'last' in ticker and 'open' in ticker:
                last_price = float(ticker['last'])
                opening_price24h = float(ticker['open'])
                
                if opening_price24h > 0:
                    variation_24h = ((last_price - opening_price24h) / opening_price24h) * 100
                    return {
                        "symbol": symbol,
                        "variation_24h": round(variation_24h, 2),
                        "last_price": last_price
                    }
        except Exception as e:
            error_msg = str(e)
            # Ignora silenciosamente símbolos que não existem
            if "does not have market symbol" not in error_msg:
                print(f"⚠️  Error fetching data for {symbol}: {e}")
        return None

    def get_variation_1h(self, symbol):
        """
        Retorna a variação de preço na última hora
        
        OTIMIZADO: Usa endpoint /prices primeiro (mais rápido)
        Fallback: Calcula usando candles se endpoint falhar
        
        Args:
            symbol: Par de trading (ex: REKTCOIN/USDT)
        
        Returns:
            Variação percentual da última hora ou None em caso de erro
        """
        # 🚀 PRIORIDADE: Tenta buscar do endpoint /prices
        price_data = self.get_price_data(symbol)
        if price_data and price_data.get('change_1h_percent') is not None:
            return round(price_data['change_1h_percent'], 2)
        
        # 🔄 FALLBACK: Calcula usando candles (método antigo)
        try:
            # Busca o preço atual
            ticker = self.client.fetch_ticker(symbol)
            current_price = float(ticker.get('last', 0))
            
            if current_price <= 0:
                return None
            
            # Busca candles de 1 hora (pega 3 para garantir que temos dados completos)
            ohlcv = self.client.fetch_ohlcv(symbol, '1h', limit=3)
            
            if len(ohlcv) >= 2:
                # O último candle [-1] pode estar em formação (não completo)
                # O penúltimo candle [-2] é o último candle COMPLETO de 1h atrás
                # Usamos o CLOSE do penúltimo candle como referência de 1h atrás
                price_1h_ago = float(ohlcv[-2][4])  # [4] = preço de fechamento (close)
                
                if price_1h_ago > 0:
                    variation_1h = ((current_price - price_1h_ago) / price_1h_ago) * 100
                    return round(variation_1h, 2)
            
            return None
            
        except Exception as e:
            print(f"⚠️  Erro ao buscar variação 1h para {symbol}: {e}")
            return None

    def get_variation_4h(self, symbol):
        """
        Retorna a variação de preço nas últimas 4 horas
        
        OTIMIZADO: Usa endpoint /prices primeiro (mais rápido e consistente)
        Fallback: Calcula usando candles se endpoint falhar
        
        🔧 Usa candles de 1h para consistência com exchange
        - 4 horas = 5 candles de 1h (4h atrás + atual)
        - Alinhado com o que a exchange mostra na interface
        - Mais confiável para decisões de compra/venda
        
        Args:
            symbol: Par de trading (ex: REKTCOIN/USDT)
        
        Returns:
            Variação percentual das últimas 4 horas ou None em caso de erro
        """
        # 🚀 PRIORIDADE: Tenta buscar do endpoint /prices
        price_data = self.get_price_data(symbol)
        if price_data and price_data.get('change_4h_percent') is not None:
            return round(price_data['change_4h_percent'], 2)
        
        # 🔄 FALLBACK: Calcula usando candles (método antigo)
        try:
            # Busca o preço atual
            ticker = self.client.fetch_ticker(symbol)
            current_price = float(ticker.get('last', 0))
            
            if current_price <= 0:
                return None
            
            # 🔧 Usa candles de 1h para consistência com exchange
            # 4 horas = 5 candles de 1h (índice 0 = 4h atrás)
            ohlcv = self.client.fetch_ohlcv(symbol, '1h', limit=5)
            
            if len(ohlcv) >= 5:
                # ohlcv[0] = 4 horas atrás (candle completo)
                # ohlcv[-1] = agora (último candle, pode estar em formação)
                # Usamos o CLOSE do candle de 4h atrás
                price_4h_ago = float(ohlcv[0][4])  # [4] = preço de fechamento (close)
                
                if price_4h_ago > 0:
                    variation_4h = ((current_price - price_4h_ago) / price_4h_ago) * 100
                    return round(variation_4h, 2)
            
            return None
            
        except Exception as e:
            print(f"⚠️  Erro ao buscar variação 4h para {symbol}: {e}")
            return None

    def get_variation_24h(self, symbol):
        """
        Retorna a variação de preço nas últimas 24 horas
        Usa o ticker['open'] que representa o início do período de 24h da exchange
        
        Args:
            symbol: Par de trading (ex: REKTCOIN/USDT)
        
        Returns:
            Variação percentual das últimas 24 horas ou None em caso de erro
        """
        try:
            # Busca o ticker que contém open/last para 24h
            ticker = self.client.fetch_ticker(symbol)
            current_price = float(ticker.get('last', 0))
            open_24h = float(ticker.get('open', 0))
            
            if current_price <= 0 or open_24h <= 0:
                return None
            
            # Calcula variação baseada no open do ticker (padrão da exchange)
            variation_24h = ((current_price - open_24h) / open_24h) * 100
            return round(variation_24h, 2)
            
        except Exception as e:
            print(f"⚠️  Erro ao buscar variação 24h para {symbol}: {e}")
            return None

    def get_multi_timeframe_variations(self, symbol):
        """
        Retorna variações de preço em múltiplos timeframes
        
        Args:
            symbol: Par de trading (ex: REKTCOIN/USDT)
        
        Returns:
            Dict com variações em diferentes períodos ou None em caso de erro
        """
        try:
            # Busca o preço atual
            ticker = self.client.fetch_ticker(symbol)
            current_price = float(ticker.get('last', 0))
            
            if current_price <= 0:
                return None
            
            variations = {}
            
            # Timeframes a verificar
            timeframes = {
                '5m': 'var_5m',
                '15m': 'var_15m',
                '30m': 'var_30m',
                '1h': 'var_1h',
                '4h': 'var_4h'
            }
            
            for tf, key in timeframes.items():
                try:
                    ohlcv = self.client.fetch_ohlcv(symbol, tf, limit=2)
                    if len(ohlcv) >= 2:
                        # Usa o close do penúltimo candle (último completo)
                        price_ago = float(ohlcv[-2][4])
                        if price_ago > 0:
                            variation = ((current_price - price_ago) / price_ago) * 100
                            variations[key] = round(variation, 2)
                except:
                    variations[key] = None
            
            return variations
            
        except Exception as e:
            print(f"⚠️  Erro ao buscar variações multi-timeframe para {symbol}: {e}")
            return None

    def create_order(self, execution_type="scheduled", dry_run=False):
        """
        Cria ordens de compra nos símbolos configurados com estratégia avançada
        
        Args:
            execution_type (str): Tipo de execução - "manual" ou "scheduled"
            dry_run (bool): Se True, apenas simula sem executar ordens reais
        
        Estratégia de Maximização de Lucro:
            1. Compra APENAS em extremos (alta forte ou queda significativa)
        2. Usa DCA (Dollar Cost Average) - divide compras em partes
        3. Calcula lucro potencial baseado em histórico
        4. Implementa stop loss e take profit automaticamente
        """
        if dry_run:
            print("🧪 MODO SIMULAÇÃO - NENHUMA ORDEM SERÁ EXECUTADA")
        
        print(f"CREATE_ORDER - Tipo: {execution_type}")
        
        usdt_balance = self.get_usdt_available()
        
        if usdt_balance < MIN_VALUE_PER_CREATE_ORDER:
            error_message = f"{ERROR_INSUFFICIENT_FUNDS}: Available balance: $ {usdt_balance:.2f}"
            print(error_message)
            return {
                "error": ERROR_INSUFFICIENT_FUNDS,
                "available_balance": round(usdt_balance, 2)
            }

        # Busca variações e filtra apenas símbolos que atendem critérios
        symbol_variations = self.get_symbol_variations()
        filtered_symbols = self.filter_symbols_by_strategy(symbol_variations)
        
        if not filtered_symbols:
            print(f"   > Nenhum símbolo atende os critérios de compra no momento")
            return {
                "status": "skipped",
                "reason": "No symbols meet trading criteria",
                "symbols_analyzed": len(symbol_variations),
                "available_balance": round(usdt_balance, 2)
            }
        
        # Inicializa ordens com análise de risco
        symbol_orders = self.initialize_symbol_orders_with_strategy(filtered_symbols)
        
        # Aloca fundos usando estratégia DCA (Dollar Cost Average)
        self.allocate_funds_with_dca_strategy(usdt_balance, symbol_orders)
        
        # Executa ordens com cálculo de lucro esperado
        results = self.execute_orders_with_profit_tracking(symbol_orders, execution_type, dry_run)
        
        # Calcula métricas de performance
        performance_metrics = self.calculate_performance_metrics(results)
        
        print(f" Orders executed with strategy: {len(results)} orders")
        return {
            "status": "success",
            "orders": results,
            "total_invested": sum(order['value'] for order in results),
            "performance_metrics": performance_metrics,
            "strategy_used": "DCA + Risk Management"
        }
    
    def filter_symbols_by_strategy(self, symbol_variations):
        """
        Filtra símbolos usando BuyStrategy (24h) e BuyStrategy1h (1h)
        Delega lógica de compra para as classes especializadas
        Prioriza estratégia de 1h se habilitada e atende critérios
        """
        print(f" Analisando {len(symbol_variations)} símbolos")
        
        # Busca configs DIRETAMENTE do MongoDB (não usa BotConfig legado)
        symbols_config = []
        if db is not None:
            symbols_config = list(db['BotConfigs'].find({'enabled': True}))
        else:
            print(f"⚠️  MongoDB não disponível")
        
        filtered = []
        
        # Processa cada símbolo
        for variation_data in symbol_variations:
            symbol = variation_data['symbol']
            variation_24h = variation_data['variation_24h']
            
            # Busca config específica do símbolo
            symbol_config = next(
                (cfg for cfg in symbols_config if cfg.get('pair') == symbol),
                None
            )
            
            if not symbol_config:
                continue
            
            # Verifica estratégia de 4h PRIMEIRO (se habilitada)
            strategy_4h_config = symbol_config.get('strategy_4h', {})            
            if not strategy_4h_config:
                print(f"⚠️  {symbol}: strategy_4h não encontrada, pulando...")
                continue
            
            if strategy_4h_config.get('enabled', False):
                print(f" {symbol}: Strategy 4h está HABILITADA")
                # Busca variação de 4h (mais estável que 1h)
                variation_4h = self.get_variation_4h(symbol)
                print(f" {symbol}: Variação 4h = {variation_4h}%")
                
                if variation_4h is not None:
                    # Usa estratégia unificada BuyStrategy com método should_buy_4h
                    should_buy_4h, buy_info_4h = self.buy_strategy.should_buy_4h(variation_4h, symbol)
                    
                    if should_buy_4h:
                        # Adiciona à lista com info da estratégia 4h
                        filtered.append({
                            **variation_data,
                            'config': symbol_config,
                            'signal_strength': buy_info_4h.get('signal_strength', 'medium'),
                            'reason': buy_info_4h.get('reason', 'Queda significativa 4h'),
                            'buy_percentage': buy_info_4h.get('buy_percentage', buy_info_4h.get('invest_percent', 15)),
                            'variation_4h': variation_4h,
                            'strategy': '4h'
                        })
                        print(f" {symbol}: ADICIONADO à lista de compra (estratégia 4h)")
                        continue  # Não verifica estratégia 24h se 4h já ativou
                    else:
                        print(f" {symbol}: NÃO passou no filtro da estratégia 4h")
            else:
                print(f" {symbol}: Strategy 4h está DESABILITADA")
            
            # Se não ativou estratégia 4h, verifica estratégia 24h
            strategy_24h_config = symbol_config.get('strategy_24h', {})
            if strategy_24h_config.get('enabled', False):
                print(f" {symbol}: Strategy 24h está HABILITADA")
                variation_24h = variation_data.get('variation')
                
                if variation_24h is not None:
                    # Usa estratégia unificada BuyStrategy com método should_buy_24h
                    should_buy_24h, buy_info_24h = self.buy_strategy.should_buy_24h(variation_24h, symbol)
                    
                    if should_buy_24h:
                        # Adiciona à lista com info da estratégia 24h
                        filtered.append({
                            **variation_data,
                            'config': symbol_config,
                            'signal_strength': buy_info_24h.get('signal_strength', 'medium'),
                            'reason': buy_info_24h.get('reason', 'Queda significativa 24h'),
                            'buy_percentage': buy_info_24h.get('buy_percentage', 20),
                            'variation_4h': None,
                            'strategy': '24h'
                        })
                        print(f" {symbol}: ADICIONADO à lista de compra (estratégia 24h)")
                    else:
                        print(f" {symbol}: NÃO passou no filtro da estratégia 24h")
            else:
                print(f" {symbol}: Strategy 24h está DESABILITADA")
        
        # Adiciona cálculo de lucro esperado
        for item in filtered:
            item['expected_profit_pct'] = self.calculate_expected_profit(
                item['variation_24h'], 
                item['config']
            )
        
        return filtered
    
    def calculate_expected_profit(self, variation, symbol_config):
        """
        Calcula o lucro esperado baseado na variação e configuração
        
        Lógica:
            - Se comprou na alta: espera-se mais 5-10% de alta
        - Se comprou na queda: espera-se recuperação de 10-20%
        """
        if variation > 0:
            # Compra em alta - lucro esperado menor (3-8%)
            return round(3 + (variation * 0.15), 2)
        else:
            # Compra em queda - lucro esperado maior (5-15%)
            recovery_potential = abs(variation) * 0.5
            return round(min(recovery_potential, 15), 2)
    
    def initialize_symbol_orders_with_strategy(self, filtered_symbols):
        """
        Inicializa ordens com análise de risco e lucro esperado
        Inclui porcentagem de compra gradativa baseada na queda
        """
        return {
            item['symbol']: {
                'value': 0,
                'date': None,
                'variation': item['variation_24h'],
                'signal_strength': item['signal_strength'],
                'reason': item['reason'],
                'expected_profit_pct': item['expected_profit_pct'],
                'buy_price': item['last_price'],
                'buy_percentage': item.get('buy_percentage', 100),  # % do saldo a investir
                'take_profit_price': item['last_price'] * (1 + item['expected_profit_pct'] / 100),
                'stop_loss_price': item['last_price'] * 0.95,  # Stop loss em -5%
                'allocation_pct': item['config'].get('allocation_percentage', 100),
                'strategy': item.get('strategy', '24h'),  # Salva qual estratégia foi usada (4h ou 24h)
                'variation_4h': item.get('variation_4h')  # Salva variação 4h se disponível
            }
            for item in filtered_symbols
        }

    
    def allocate_funds_with_dca_strategy(self, usdt_balance, symbol_orders):
        """
        Aloca fundos usando estratégia INTELIGENTE
        
        Lógica Inteligente:
        - Saldo < $10: Usa 100% para maximizar lucro (ignora percentuais)
        - Saldo >= $10: Usa percentuais da estratégia (gestão de risco)
        
        Delega cálculo de investimento para a classe especializada
        """
        if not symbol_orders:
            return
        
        for symbol, order in symbol_orders.items():
            # Identifica qual estratégia foi usada
            strategy_used = order.get('strategy', '24h')
            buy_percentage = order.get('buy_percentage', 100)
            
            # 🎯 APLICA ESTRATÉGIA INTELIGENTE
            # Usa SmartInvestmentStrategy para calcular investimento seguro
            investment_amount, smart_info = self.smart_strategy.calculate_smart_investment(
                usdt_balance,
                buy_percentage,
                strategy_name=strategy_used
            )
            
            # Pega a porcentagem ajustada para logging
            adjusted_percentage = smart_info.get('adjusted_percentage', buy_percentage)
            
            # Verifica se aplicou lógica inteligente
            used_smart_logic = adjusted_percentage != buy_percentage
            smart_emoji = "🎯" if used_smart_logic else "💰"
            
            # Garante valor mínimo
            if investment_amount >= MIN_VALUE_PER_SYMBOL:
                order['value'] = investment_amount
                order['date'] = datetime.utcnow()
                
                # Calcula lucro esperado em USDT
                order['expected_profit_usdt'] = round(
                order['value'] * (order['expected_profit_pct'] / 100), 
                2
                )
                
                # Logging detalhado
                strategy_label = order.get('strategy', '24h')
                if strategy_label == '4h' and order.get('variation_4h') is not None:
                    if used_smart_logic:
                        print(f"{smart_emoji} {symbol}: [4H] Queda {order.get('variation_4h', 0):.1f}% → SALDO BAIXO: Investe 100% (${order['value']:.2f}) ao invés de {buy_percentage}%")
                    else:
                        print(f"{smart_emoji} {symbol}: [4H] Queda {order.get('variation_4h', 0):.1f}% → Investe {adjusted_percentage}% (${order['value']:.2f})")
                else:
                    if used_smart_logic:
                        print(f"{smart_emoji} {symbol}: [24H] Queda {order['variation']:.1f}% → SALDO BAIXO: Investe 100% (${order['value']:.2f}) ao invés de {buy_percentage}%")
                    else:
                        print(f"{smart_emoji} {symbol}: [24H] Queda {order['variation']:.1f}% → Investe {adjusted_percentage}% (${order['value']:.2f})")
            else:
                order['value'] = 0
                print(f"⏸️  {symbol}: Valor muito baixo (${investment_amount:.2f} < ${MIN_VALUE_PER_SYMBOL})")
    
    def execute_orders_with_profit_tracking(self, symbol_orders, execution_type="scheduled", dry_run=False):
        """
        Executa ordens e registra tracking de lucro/perda
        
        Args:
            symbol_orders: Dicionário com ordens por símbolo
            execution_type: Tipo de execução - "manual" ou "scheduled"
            dry_run: Se True, apenas simula sem executar ordens reais
        """
        results = []
        for symbol, order in symbol_orders.items():
            if order['value'] > 0:
                success, order_result = self.create_and_send_order(symbol, order['value'], dry_run)
                status = STATUS_SUCCESS if success else STATUS_ERROR
                
                # Calcula quantidade comprada
                amount_bought = order['value'] / order['buy_price'] if success else 0
                
                result = {
                'symbol': symbol,
                'value': order['value'],
                'amount_bought': round(amount_bought, 8),
                'buy_price': order['buy_price'],
                'status': status,
                'variation_24h': order['variation'],
                'signal_strength': order['signal_strength'],
                'reason': order['reason'],
                'date': order['date'],
                'order_id': order_result.get('id') if order_result else None,
                
                # Profit Tracking
                'expected_profit_pct': order['expected_profit_pct'],
                'expected_profit_usdt': order['expected_profit_usdt'],
                'take_profit_price': round(order['take_profit_price'], 8),
                'stop_loss_price': round(order['stop_loss_price'], 8),
                
                # Cálculo de ROI esperado
                'expected_roi': f"+{order['expected_profit_pct']}%",
                'risk_reward_ratio': round(order['expected_profit_pct'] / 5, 2),  # 5% é o stop loss
                
                #  NOVO: Tracking de execução
                'execution_type': execution_type,
                'executed_by': 'user' if execution_type == 'manual' else 'scheduler'
                }
                results.append(result)
                
                # Salvar no banco com informações de lucro
                self.save_to_db_with_profit_tracking(symbol, result)
                
                print(f"{'' if success else ''} Order {status}: {symbol}")
                print(f"   💰 Investido: ${order['value']:.2f} USDT")
                print(f"    Quantidade: {amount_bought:,.2f} tokens")
                print(f"    Take Profit: ${order['take_profit_price']:.8f} (+{order['expected_profit_pct']}%)")
                print(f"   🛡️  Stop Loss: ${order['stop_loss_price']:.8f} (-5%)")
                print(f"   💵 Lucro Esperado: ${order['expected_profit_usdt']:.2f} USDT")
        
        return results
    
    def calculate_performance_metrics(self, results):
        """
        Calcula métricas de performance da estratégia
        """
        if not results:
            return {}
        
        total_invested = sum(r['value'] for r in results)
        total_expected_profit = sum(r['expected_profit_usdt'] for r in results)
        avg_expected_roi = sum(r['expected_profit_pct'] for r in results) / len(results)
        
        return {
            'total_orders': len(results),
            'total_invested_usdt': round(total_invested, 2),
            'total_expected_profit_usdt': round(total_expected_profit, 2),
            'average_expected_roi_pct': round(avg_expected_roi, 2),
            'potential_return_usdt': round(total_invested + total_expected_profit, 2),
            'risk_exposure_pct': 5.0,  # Stop loss fixo em -5%
            'best_signal': max(results, key=lambda x: x['signal_strength'])['symbol'] if results else None
        }
    
    def save_to_db_with_profit_tracking(self, symbol, result):
        """
        Salva ordem no banco com informações de lucro/tracking
        Inclui tipo de execução (manual ou scheduled) para auditoria
        """
        order_data = {
            "symbol": symbol,
            "value": result['value'],
            "amount_bought": result['amount_bought'],
            "buy_price": result['buy_price'],
            "date": result['date'],
            "variation_24h": result['variation_24h'],
            "status": result['status'],
            "signal_strength": result['signal_strength'],
            "reason": result['reason'],
            
            # Profit tracking
            "expected_profit_pct": result['expected_profit_pct'],
            "expected_profit_usdt": result['expected_profit_usdt'],
            "take_profit_price": result['take_profit_price'],
            "stop_loss_price": result['stop_loss_price'],
            "risk_reward_ratio": result['risk_reward_ratio'],
            
            #  NOVO: Tracking de execução
            "execution_type": result.get('execution_type', 'unknown'),
            "executed_by": result.get('executed_by', 'unknown'),
            
            # Status de acompanhamento
            "is_active": True,
            "sell_price": None,
            "actual_profit_pct": None,
            "actual_profit_usdt": None,
            "closed_at": None
        }
        
        try:
            if db is not None:
                db.insert_one(order_data)
                execution_label = "🤖 AUTOMÁTICA" if result.get('execution_type') == 'scheduled' else "👤 MANUAL"
                print(f"   ✓ Order saved to database [{execution_label}]")
                return True
            else:
                print(f"   ⚠ MongoDB disabled - Order logged: {symbol}")
                return False
        except Exception as e:
            print(f"    {ERROR_DB_SAVE}: {e}")
            return False

    def initialize_symbol_orders(self, symbol_variations):
        """
        Inicializa a estrutura de ordens para cada símbolo
        """
        return {
            item['symbol']: {
                'value': 0,
                'date': None,
                'variation': item['variation_24h']
            }
            for item in symbol_variations
        }

    def allocate_funds_to_orders(self, usdt_balance, symbol_orders):
        """
        Distribui o saldo disponível entre os símbolos
        """
        while usdt_balance >= MIN_VALUE_PER_SYMBOL:
            for symbol in symbol_orders:
                if usdt_balance < MIN_VALUE_PER_SYMBOL:
                    break
                symbol_orders[symbol]['value'] += MIN_VALUE_PER_SYMBOL
                usdt_balance -= MIN_VALUE_PER_SYMBOL
                symbol_orders[symbol]['date'] = datetime.utcnow()

    def execute_orders(self, symbol_orders):
        """
        Executa as ordens para cada símbolo
        """
        results = []
        for symbol, order in symbol_orders.items():
            if order['value'] > 0:
                success, order_result = self.create_and_send_order(symbol, order['value'])
                status = STATUS_SUCCESS if success else STATUS_ERROR
                
                result = {
                'symbol': symbol,
                'value': order['value'],
                'status': status,
                'variation': order['variation'],
                'date': order['date'],
                'order_id': order_result.get('id') if order_result else None
                }
                results.append(result)
                
                # Salvar no banco se estiver configurado
                self.save_to_db(symbol, order['value'], order['date'], order['variation'], status)
                print(f"Order {status}: {symbol} - ${order['value']:.2f}")
        
        return results

    def create_and_send_order(self, symbol, value, dry_run=False):
        """
        Cria e envia ordem usando estratégia HÍBRIDA:
            - Mercados líquidos (volume > $1M/24h): ordem LIMITADA
        - Mercados ilíquidos (volume < $1M/24h): ordem MERCADO
        
        OTIMIZADO: Usa endpoint /prices para obter ask/bid corretos
        
        Args:
            symbol: Par de negociação
            value: Valor em USDT a investir
            dry_run: Se True, apenas simula sem executar ordem real
        """
        try:
            # 🚀 PRIORIDADE: Tenta buscar dados do endpoint /prices
            price_data = self.get_price_data(symbol)
            
            if price_data:
                # Usa dados do endpoint (mais rápido e completo)
                last_price = price_data['current']
                ask_price = price_data['ask']
                bid_price = price_data['bid']
            else:
                # 🔄 FALLBACK: Busca via CCXT
                ticker = self.client.fetch_ticker(symbol)
                last_price = float(ticker['last'])
                ask_price = float(ticker.get('ask', last_price))
                bid_price = float(ticker.get('bid', last_price))
            
            # Calcula a quantidade baseada no valor em USDT
            amount = value / last_price
            
            # Arredonda a quantidade para o número de casas decimais aceito
            markets = self.client.load_markets()
            market = markets[symbol]
            amount = self.client.amount_to_precision(symbol, amount)
            
            # Estratégia HÍBRIDA: decide entre limit/market baseado no volume
            use_limit, reason = self.should_use_limit_order(symbol)
            
            print(f"\n   💡 Estratégia de Compra: {reason}")
            
            if dry_run:
                # 🧪 MODO SIMULAÇÃO - NÃO EXECUTA ORDEM REAL
                print(f"   🧪 [SIMULAÇÃO] Ordem NÃO foi executada na exchange")
                print(f"    [SIMULAÇÃO] Tipo: {'LIMIT' if use_limit else 'MARKET'}")
                print(f"    [SIMULAÇÃO] Amount: {amount} | Price: ${last_price:.10f} | Value: ${value:.2f}")
                
                # Retorna ordem simulada
                simulated_order = {
                    'id': f"SIM-{int(datetime.now().timestamp())}",
                    'symbol': symbol,
                    'type': 'limit' if use_limit else 'market',
                    'side': 'buy',
                    'price': last_price,
                    'amount': float(amount),
                    'cost': value,
                    'status': 'simulated',
                    'timestamp': datetime.now().timestamp()
                }
                return True, simulated_order
            
            if use_limit:
                # MERCADO LÍQUIDO: Ordem LIMITADA usando ASK (preço real de compra)
                buy_price = ask_price if ask_price > 0 else last_price
                buy_price = self.client.price_to_precision(symbol, buy_price)
                
                order = self.client.create_limit_buy_order(symbol, float(amount), float(buy_price))
                print(f"    Order created (LIMIT): {symbol}")
                print(f"      Amount: {amount} | Price: ${buy_price:.10f} | Value: ${value:.2f}")
            else:
                # MERCADO ILÍQUIDO: Ordem MERCADO para garantir execução
                order = self.client.create_market_buy_order(symbol, float(amount))
                print(f"    Order created (MARKET): {symbol}")
                print(f"      Amount: {amount} | Price: ~${last_price:.10f} | Value: ${value:.2f}")
            
            return True, order
            
        except Exception as e:
            print(f"Error creating order for {symbol}: {e}")
            return False, None

    def check_and_execute_sells(self, symbol=None):
        """
        Verifica holdings atuais e executa vendas se condições forem atendidas
        
        Args:
            symbol: Par específico para verificar (opcional). Se None, verifica todos os holdings.
        
        Returns:
            Dict com resultados das vendas executadas
        """
        try:
            # Busca holdings silenciosamente
            holdings = self.get_non_zero_sorted_assets()
            
            if not holdings:
                print("   > Nenhum ativo disponível")
                return {
                "status": "no_holdings",
                "message": "Nenhum ativo disponível para venda",
                "sells_executed": []
                }
            
            sells_executed = []
            total_profit = 0.0
            
            for holding in holdings:
                currency = holding['currency']
                balance = float(holding['available'])
                total_balance = float(holding['balance'])
                
                # Ignora USDT (é a moeda base)
                if currency == 'USDT':
                    continue
                
                # Se um símbolo específico foi fornecido, verifica apenas ele
                if symbol:
                    # Remove /USDT do symbol se presente
                    symbol_currency = symbol.replace('/USDT', '').replace('/', '').upper()
                    if currency.upper() != symbol_currency:
                        continue
                
                # Monta o símbolo de trading
                trading_symbol = f"{currency}/USDT"
                
                # 🚀 PRIORIDADE: Busca dados do endpoint /prices
                price_data = self.get_price_data(trading_symbol)
                
                if price_data:
                    # Usa dados do endpoint (mais rápido e completo)
                    current_price = price_data['current']
                    bid_price = price_data['bid']
                else:
                    # 🔄 FALLBACK: Verifica se símbolo existe na exchange via CCXT
                    try:
                        ticker = self.client.fetch_ticker(trading_symbol)
                        current_price = float(ticker['last'])
                        bid_price = float(ticker.get('bid', current_price))
                    except Exception as e:
                        error_msg = str(e)
                        if "does not have market symbol" in error_msg:
                            print(f"   ! {trading_symbol} sem par USDT")
                        else:
                            print(f"   ! Erro ao buscar preço: {e}")
                        continue
                
                # Calcula valor em USDT do holding
                holding_value_usdt = balance * current_price
                
                # Verifica valor mínimo
                if holding_value_usdt < 1:
                    continue
                
                # Verifica lucro antes de vender usando SellStrategy
                
                # Busca preço de compra do banco de dados
                buy_price = None
                if db is not None:
                    try:
                        # Busca na collection de ordens (ajuste o nome da collection conforme necessário)
                        orders_collection = db['Orders']  # ou db['ExecutionLogs'] dependendo de onde salva
                        buy_record = orders_collection.find_one(
                            {"symbol": trading_symbol}, 
                            sort=[("date", -1)]  # Usa 'date' em vez de 'timestamp'
                        )
                        if buy_record and 'buy_price' in buy_record:
                            buy_price = float(buy_record['buy_price'])
                    except Exception as e:
                        print(f"   ! Erro DB: {e}")
                
                # Se não tiver preço de compra no DB, calcula lucro com base na variação de 24h
                if not buy_price:
                    try:
                        ticker = self.client.fetch_ticker(trading_symbol)
                        change_percent_24h = float(ticker.get('percentage', 0))
                        
                        # Estima preço de compra baseado na variação
                        if change_percent_24h != 0:
                            buy_price = current_price / (1 + (change_percent_24h / 100))
                    except Exception as e:
                        pass  # Erro ao estimar
                
                # Verifica se deve vender usando a estratégia
                if buy_price:
                    profit_percent = ((current_price - buy_price) / buy_price) * 100
                    print(f"   > {trading_symbol}: Lucro {profit_percent:+.2f}%")
                    
                    # REGRA ESPECIAL: Se lucro > 100%, NÃO VENDE (deixa continuar subindo)
                    if profit_percent > 100:
                        continue
                    
                    # Define lucro mínimo baseado na estratégia (24h por padrão para verificação automática)
                    min_profit = self.sell_strategy.min_profit_24h
                    
                    # Decide se usa venda gradativa ou venda completa
                    if profit_percent >= 40:
                        # Lucro >= 40%: VENDA COMPLETA (100%)
                        # Lucro alto - venda completa
                        
                        try:
                            markets = self.client.load_markets()
                            market = markets[trading_symbol]
                            sell_amount = self.client.amount_to_precision(trading_symbol, balance)
                            
                            # Estratégia HÍBRIDA: lucro alto = URGÊNCIA (sempre MARKET)
                            use_limit = False
                            reason = "Lucro alto - usando MARKET para realização imediata"
                            
                            
                            if use_limit:
                                # MERCADO LÍQUIDO: Ordem LIMITADA usando BID (preço real de venda)
                                sell_price = bid_price if bid_price > 0 else current_price
                                sell_price = self.client.price_to_precision(trading_symbol, sell_price)
                                
                                
                                order = self.client.create_limit_sell_order(trading_symbol, float(sell_amount), float(sell_price))
                            else:
                                # LUCRO ALTO: Ordem MERCADO para realização rápida
                                
                                order = self.client.create_market_sell_order(trading_symbol, float(sell_amount))
                            
                            print(f"   > Vendido: {sell_amount} {currency} | Lucro: {profit_percent:+.2f}% | ${holding_value_usdt:.2f}")
                            
                            sell_result = {
                                "success": True,
                                "symbol": trading_symbol,
                                "amount_sold": float(sell_amount),
                                "sell_percentage": 100,
                                "buy_price": buy_price,
                                "sell_price": current_price,
                                "profit_percent": round(profit_percent, 2),
                                "usdt_received": round(holding_value_usdt, 2),
                                "order_id": order.get("id"),
                                "sell_type": "complete",
                                "message": f" Venda COMPLETA de {currency} - Lucro {profit_percent:+.2f}%!"
                            }
                            
                            sells_executed.append(sell_result)
                            total_profit += holding_value_usdt
                            
                        except Exception as e:
                            print(f"    ERRO ao executar venda completa: {e}\n")
                            sells_executed.append({
                                "success": False,
                                "symbol": trading_symbol,
                                "error": str(e),
                                "message": f" Erro ao vender {currency}: {e}"
                            })
                    
                    elif profit_percent >= min_profit:
                        # Lucro entre min_profit e 40%: VENDA GRADATIVA
                        print(f"    VENDA GRADATIVA ({profit_percent:+.2f}% < 40%)")
                        print(f"    Calculando níveis de venda progressiva...")
                        
                        # Calcula alvos de venda usando SellStrategy
                        investment_value = balance * buy_price  # Valor investido estimado
                        sell_targets = self.sell_strategy.calculate_sell_targets(
                            buy_price=buy_price,
                            amount_bought=balance,
                            investment_value=investment_value
                        )
                        
                        # Verifica quais níveis devem ser executados
                        levels_to_sell = self.sell_strategy.check_sell_opportunities(
                            current_price=current_price,
                            sell_targets=sell_targets
                        )
                        
                        if levels_to_sell:
                            print(f"    {len(levels_to_sell)} NÍVEL(IS) ATINGIDO(S)!")
                            
                            for level in levels_to_sell:
                                print(f"\n    {level['name']} - Alvo: +{level['profit_target_pct']}%")
                                print(f"      Vender: {level['sell_percentage']}% do saldo")
                                print(f"      Preço alvo: ${level['target_price']:.10f}")
                                print(f"      Lucro esperado: ${level['profit_usdt']:.2f} USDT")
                                
                                try:
                                    markets = self.client.load_markets()
                                    market = markets[trading_symbol]
                                    sell_amount = self.client.amount_to_precision(trading_symbol, level['sell_amount'])
                                    
                                    # Estratégia HÍBRIDA: decide entre limit/market baseado no volume
                                    use_limit, reason = self.should_use_limit_order(trading_symbol)
                                    
                                    print(f"\n      💡 Estratégia: {reason}")
                                    
                                    if use_limit:
                                        # MERCADO LÍQUIDO: Ordem LIMITADA para melhor preço
                                        ticker_fresh = self.client.fetch_ticker(trading_symbol)
                                        sell_price = float(ticker_fresh['bid']) if ticker_fresh.get('bid') else current_price
                                        sell_price = self.client.price_to_precision(trading_symbol, sell_price)
                                        
                                        order = self.client.create_limit_sell_order(trading_symbol, float(sell_amount), float(sell_price))
                                        # Venda executada
                                    else:
                                        # MERCADO ILÍQUIDO: Ordem MERCADO para garantir execução
                                        order = self.client.create_market_sell_order(trading_symbol, float(sell_amount))
                                        print(f"      > {level['name']}: {level['sell_percentage']}% vendido")
                                    
                                    usdt_received = level['sell_amount'] * current_price
                                    
                                    sell_result = {
                                        "success": True,
                                        "symbol": trading_symbol,
                                        "level": level['level'],
                                        "level_name": level['name'],
                                        "amount_sold": float(sell_amount),
                                        "sell_percentage": level['sell_percentage'],
                                        "buy_price": buy_price,
                                        "sell_price": current_price,
                                        "profit_percent": round(profit_percent, 2),
                                        "profit_target": level['profit_target_pct'],
                                        "usdt_received": round(usdt_received, 2),
                                        "order_id": order.get("id"),
                                        "sell_type": "gradual",
                                        "message": f" {level['name']} executado - {level['sell_percentage']}% vendido!"
                                    }
                                    
                                    sells_executed.append(sell_result)
                                    total_profit += usdt_received
                                    
                                except Exception as e:
                                    print(f"       ERRO ao executar {level['name']}: {e}")
                                    sells_executed.append({
                                        "success": False,
                                        "symbol": trading_symbol,
                                        "level": level['level'],
                                        "level_name": level['name'],
                                        "error": str(e),
                                        "message": f" Erro ao executar {level['name']}: {e}"
                                    })
                            
                            print(f"\n    Resumo da venda gradativa:")
                            print(f"      Níveis executados: {len([l for l in levels_to_sell if l.get('success', True)])}")
                            print(f"      Total vendido: {sum(l['sell_percentage'] for l in levels_to_sell)}%")
                            print(f"      USDT recebido nesta operação: ${sum(s.get('usdt_received', 0) for s in sells_executed[-len(levels_to_sell):]):.2f}")
                            
                        else:
                            print(f"   ⏸️  Nenhum nível de venda atingido ainda")
                            print(f"   💡 Próximo nível: {sell_targets[0]['profit_target_pct']}% (Preço: ${sell_targets[0]['target_price']:.10f})")
                    
                    else:
                        print(f"   ⏸️  Lucro insuficiente: {profit_percent:+.2f}% < {min_profit}%")
                        print(f"   💡 Aguardando lucro mínimo de {min_profit}% para vender\n")
                else:
                    print(f"   ! Preço de compra não encontrado")
            
            if sells_executed:
                print(f"   > Vendas: {len(sells_executed)} | Total: ${total_profit:.2f} USDT")
            else:
                print(f"   > Nenhum ativo atende os critérios de venda no momento")
            
            if not sells_executed:
                return {
                "status": "no_sells",
                "message": "Nenhuma venda executada - aguardando alvos de lucro",
                "holdings_checked": len([h for h in holdings if h['currency'] != 'USDT']),
                "sells_executed": [],
                "holdings_found": holdings
                }
            
            return {
                "status": "success",
                "sells_executed": sells_executed,
                "total_profit": round(total_profit, 2),
                "total_sells": len(sells_executed)
            }
            
        except Exception as e:
            print(f" ERRO FATAL ao verificar vendas: {e}")
            import traceback
            traceback.print_exc()
            return {
                "status": "error",
                "message": f"Erro ao verificar vendas: {str(e)}",
                "sells_executed": []
            }

    def save_to_db(self, symbol, value, date, variation, status):
        """
        Salva a ordem no banco de dados (se configurado)
        """
        order_data = {
            "symbol": symbol,
            "value": value,
            "date": date,
            "variation": variation,
            "status": status
        }
        
        try:
            if db is not None:  # Só salva se o banco estiver disponível
                db.insert_one(order_data)
                print(f"✓ Order saved to database: {order_data}")
                return f"Order saved to database: {order_data}"
            else:
                print(f"⚠ MongoDB disabled - Order would be saved: {order_data}")
                return f"Order logged (DB disabled): {order_data}"
        except Exception as e:
            print(f"{ERROR_DB_SAVE}: {e}")
            return f"Error saving to DB: {e}"
