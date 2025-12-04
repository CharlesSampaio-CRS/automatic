"""
Gerenciador de Jobs Dinâmicos por Símbolo

Cada criptomoeda habilitada terá seu próprio job no APScheduler
com intervalo e horário configuráveis individualmente
"""

import os
import sys
from datetime import datetime
import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.base import JobLookupError

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.services.config_service import config_service
from src.clients.exchange import MexcClient
from src.database.mongodb_connection import connection_mongo
from src.utils.number_formatter import format_usdt

TZ = pytz.timezone("America/Sao_Paulo")

# Conecta ao MongoDB para logs de execução
try:
    execution_logs_db = connection_mongo("ExecutionLogs")
except Exception:
    execution_logs_db = None


class DynamicJobManager:
    """Gerencia jobs individuais para cada símbolo"""
    
    def __init__(self, scheduler: BackgroundScheduler, api_key: str, api_secret: str):
        """
        Inicializa gerenciador de jobs
        
        Args:
            scheduler: Instância do APScheduler
            api_key: Chave da API MEXC
            api_secret: Secret da API MEXC
        """
        self.scheduler = scheduler
        self.api_key = api_key
        self.api_secret = api_secret
        self.active_jobs = {}  # pair -> job_id
        
        # Inicializado silenciosamente
    
    def create_symbol_job_function(self, pair: str):
        """
        Cria função de job para um símbolo específico
        
        Args:
            pair: Par da criptomoeda (ex: "REKT/USDT")
        
        Returns:
            Função executável pelo scheduler
        """
        def symbol_job():
            """Job específico para executar ordem de um símbolo - GARANTIA DE EXECUÇÃO"""
            job_start_time = datetime.now(TZ)
            job_id_display = f"JOB_{pair.replace('/', '_')}"
            
            try:
                # 1. VALIDAÇÃO: Busca configuração atualizada do MongoDB
                config = config_service.get_symbol_config(pair)
                
                if not config:
                    print(f"WARNING [{job_id_display}] Config não encontrada - pulando execução", flush=True)
                    return
                
                if not config.get('enabled'):
                    print(f"WARNING [{job_id_display}] Config desabilitada - pulando execução", flush=True)
                    return
                
                # 2. INICIALIZAÇÃO: Log de início
                print(f"\n{'='*60}", flush=True)
                print(f"START [{job_id_display}] INICIANDO EXECUÇÃO", flush=True)
                print(f"{'='*60}", flush=True)
                print(f"TIME  [{job_id_display}] Início: {job_start_time.strftime('%d/%m/%Y %H:%M:%S')}", flush=True)
                
            except Exception as e:
                print(f"ERROR [{job_id_display}] ERRO CRÍTICO na validação: {e}", flush=True)
                import traceback
                traceback.print_exc()
                return
            
            # 3. EXECUÇÃO PRINCIPAL (com garantia de robustez)
            try:
                # Busca intervalo do job para calcular próxima execução
                schedule_config = config.get('schedule', {})
                interval_minutes = schedule_config.get('interval_minutes')
                interval_hours = schedule_config.get('interval_hours')
                
                if interval_minutes:
                    interval_display = f"{interval_minutes} min"
                    from datetime import timedelta
                    next_run = job_start_time + timedelta(minutes=interval_minutes)
                elif interval_hours:
                    interval_display = f"{interval_hours}h"
                    from datetime import timedelta
                    next_run = job_start_time + timedelta(hours=interval_hours)
                else:
                    interval_display = "?"
                    next_run = None
                
                print(f"PAIR  [{job_id_display}] Par: {pair}", flush=True)
                if next_run:
                    print(f"NEXT  [{job_id_display}] Próxima execução: {next_run.strftime('%d/%m/%Y %H:%M:%S')} (em {interval_display})", flush=True)
                print(f"{'='*60}\n", flush=True)
                
                # 4. EXECUÇÃO: Cria cliente com configuração do MongoDB
                print(f"SETUP [{job_id_display}] Criando cliente MEXC...", flush=True)
                mexc_client = MexcClient(self.api_key, self.api_secret, config)
                print(f"OK    [{job_id_display}] Cliente MEXC criado", flush=True)
                
                # 5. EXECUÇÃO: Executa ordem
                print(f"EXEC  [{job_id_display}] Executando ordem (tipo: scheduled)...", flush=True)
                result = mexc_client.create_order(execution_type="scheduled")
                print(f"DONE  [{job_id_display}] Ordem executada - Status: {result.get('status')}", flush=True)
                
                # Atualiza metadata
                metadata_updates = {
                    "last_execution": datetime.now(),
                    "status": "active" if result.get('status') == 'success' else "skipped"
                }
                
                if result.get('status') == 'success':
                    orders = result.get('orders', [])
                    total_invested = result.get('total_invested', 0)
                    
                    # Incrementa contadores
                    current_total_orders = config.get('metadata', {}).get('total_orders', 0)
                    current_total_invested = config.get('metadata', {}).get('total_invested', 0.0)
                    
                    metadata_updates['total_orders'] = current_total_orders + len(orders)
                    metadata_updates['total_invested'] = current_total_invested + total_invested
                
                config_service.update_metadata(pair, metadata_updates)
                print(f"OK    [{job_id_display}] Metadata atualizada no MongoDB", flush=True)
                
                # ✅ SEMPRE SALVA LOG (sucesso, skipped ou erro)
                print(f"LOG   [{job_id_display}] Preparando log para MongoDB...", flush=True)
                
                if execution_logs_db is not None:
                    try:
                        print(f"INFO  [{job_id_display}] Coletando informações de mercado...", flush=True)
                        # Busca informações de mercado do par
                        market_info = None
                        try:
                            ticker = mexc_client.client.fetch_ticker(pair)
                            if ticker:
                                last_price = float(ticker.get('last', 0))
                                bid_price = float(ticker.get('bid', 0))
                                ask_price = float(ticker.get('ask', 0))
                                high_24h = float(ticker.get('high', 0))
                                low_24h = float(ticker.get('low', 0))
                                open_24h = float(ticker.get('open', 0))
                                volume_24h = float(ticker.get('quoteVolume', 0))
                                
                                # Calcula variações
                                change_24h = last_price - open_24h if open_24h > 0 else 0
                                change_percent_24h = (change_24h / open_24h * 100) if open_24h > 0 else 0
                                
                                # Busca variação 1h
                                variation_1h = mexc_client.get_variation_1h(pair)
                                
                                # Calcula spread
                                spread_value = ask_price - bid_price if (ask_price and bid_price) else 0
                                spread_percent = (spread_value / bid_price * 100) if bid_price > 0 else 0
                                
                                # Calcula volatilidade
                                volatility = ((high_24h - low_24h) / low_24h * 100) if low_24h > 0 else 0
                                
                                # Status do spread
                                if spread_percent < 0.3:
                                    spread_status = "LOW"
                                elif spread_percent < 1.0:
                                    spread_status = "MEDIUM"
                                else:
                                    spread_status = "HIGH"
                                
                                # Análise de tendência
                                if change_percent_24h > 2:
                                    trend = "UP"
                                elif change_percent_24h < -2:
                                    trend = "DOWN"
                                else:
                                    trend = "FLAT"
                                
                                # Análise de momentum
                                if abs(change_percent_24h) > 10:
                                    momentum = "STRONG"
                                elif abs(change_percent_24h) > 5:
                                    momentum = "MODERATE"
                                else:
                                    momentum = "WEAK"
                                
                                # Análise de liquidez
                                if volume_24h > 1000000:
                                    liquidity = "HIGH"
                                elif volume_24h > 100000:
                                    liquidity = "MEDIUM"
                                else:
                                    liquidity = "LOW"
                                
                                market_info = {
                                    "pair": pair,
                                    "current_price": last_price,
                                    "bid_price": bid_price,
                                    "ask_price": ask_price,
                                    "spread": {
                                        "value": spread_value,
                                        "percent": round(spread_percent, 4),
                                        "status": spread_status
                                    },
                                    "24h_stats": {
                                        "high": high_24h,
                                        "low": low_24h,
                                        "open": open_24h,
                                        "change": change_24h,
                                        "change_percent": round(change_percent_24h, 2),
                                        "volume_usdt": round(volume_24h, 2),
                                        "volatility": round(volatility, 2)
                                    },
                                    "1h_stats": {
                                        "change_percent": variation_1h if variation_1h else None
                                    },
                                    "trading_fees": {
                                        "maker_fee": 0,
                                        "taker_fee": 0,
                                        "estimated_buy_cost": last_price,
                                        "estimated_sell_return": last_price
                                    },
                                    "market_analysis": {
                                        "trend": trend,
                                        "momentum": momentum,
                                        "liquidity": liquidity,
                                        "recommendation": f"Spread {spread_status} | {trend} | {liquidity}"
                                    }
                                }
                        except Exception:
                            market_info = None
                        
                        # Monta resumo
                        summary = {
                            "buy_executed": result.get('status') == 'success',
                            "sell_executed": False,  # Scheduled não executa venda
                            "total_invested": format_usdt(result.get('total_invested', 0)),
                            "total_profit": format_usdt(0),
                            "net_result": format_usdt(0)
                        }
                        
                        execution_log = {
                            "execution_type": "scheduled",
                            "executed_by": "scheduler",
                            "timestamp": datetime.now().isoformat(),
                            "pair": pair,
                            
                            # Resumo da execução (valores formatados)
                            "summary": summary,
                            
                            # Resultado da compra
                            "buy_details": {
                                "status": result.get('status'),
                                "message": result.get('message'),
                                "symbols_analyzed": result.get('symbols_analyzed', 0),
                                "orders_executed": len(result.get('orders', [])),
                                "total_invested": format_usdt(result.get('total_invested', 0))
                            },
                            
                            # Resultado da venda (scheduled não vende)
                            "sell_details": {
                                "status": "no_sells",
                                "message": "Execução scheduled não realiza vendas",
                                "holdings_checked": 0,
                                "sells_executed": 0,
                                "total_profit": format_usdt(0)
                            },
                            
                            # Informações de mercado
                            "market_info": market_info
                        }
                        
                        print(f"SAVE  [{job_id_display}] Log montado, inserindo no MongoDB...", flush=True)
                        result_insert = execution_logs_db.insert_one(execution_log)
                        print(f"OK    [{job_id_display}] Log salvo! ID: {result_insert.inserted_id}", flush=True)
                        
                    except Exception as e:
                        print(f"ERROR [{job_id_display}] ERRO ao salvar log no MongoDB: {e}", flush=True)
                        import traceback
                        traceback.print_exc()
                else:
                    print(f"ERROR [{job_id_display}] execution_logs_db is None - MongoDB não conectado!", flush=True)
                
                # Job executado silenciosamente
                
                # 6. FINALIZAÇÃO: Calcula tempo de execução
                job_end_time = datetime.now(TZ)
                execution_duration = (job_end_time - job_start_time).total_seconds()
                
                print(f"\n{'='*60}", flush=True)
                print(f"END   [{job_id_display}] EXECUÇÃO CONCLUÍDA", flush=True)
                print(f"TIME  [{job_id_display}] Duração: {execution_duration:.2f}s", flush=True)
                print(f"STAT  [{job_id_display}] Status: {result.get('status')}", flush=True)
                print(f"{'='*60}\n", flush=True)
                
            except Exception as e:
                job_end_time = datetime.now(TZ)
                execution_duration = (job_end_time - job_start_time).total_seconds()
                
                print(f"\n{'='*60}", flush=True)
                print(f"ERROR [{job_id_display}] ERRO NA EXECUÇÃO", flush=True)
                print(f"TIME  [{job_id_display}] Duração: {execution_duration:.2f}s", flush=True)
                print(f"ERR   [{job_id_display}] Erro: {e}", flush=True)
                print(f"{'='*60}\n", flush=True)
                
                import traceback
                traceback.print_exc()
                
                # Atualiza status para erro
                config_service.update_metadata(pair, {
                    "last_execution": datetime.now(),
                    "status": "error"
                })
                
                # ✅ SALVA LOG DE ERRO TAMBÉM
                if execution_logs_db is not None:
                    try:
                        error_log = {
                            "execution_type": "scheduled",
                            "executed_by": "scheduler",
                            "timestamp": datetime.now().isoformat(),
                            "pair": pair,
                            
                            # Resumo da execução
                            "summary": {
                                "buy_executed": False,
                                "sell_executed": False,
                                "total_invested": "0.00",
                                "total_profit": "0.00",
                                "net_result": "0.00"
                            },
                            
                            # Detalhes do erro
                            "buy_details": {
                                "status": "error",
                                "message": str(e),
                                "error_type": type(e).__name__,
                                "symbols_analyzed": 0,
                                "orders_executed": 0,
                                "total_invested": "0.00"
                            },
                            
                            # Venda não executada
                            "sell_details": {
                                "status": "no_sells",
                                "message": "Execução não chegou até a venda devido ao erro",
                                "holdings_checked": 0,
                                "sells_executed": 0,
                                "total_profit": "0.00"
                            },
                            
                            # Sem informações de mercado em caso de erro
                            "market_info": None
                        }
                        execution_logs_db.insert_one(error_log)
                        print(f"   > Log de erro salvo no banco")
                    except Exception as log_error:
                        print(f"   ! Erro ao salvar log de erro: {log_error}")
        
        return symbol_job
    
    def add_job_for_symbol(self, pair: str) -> tuple[bool, str]:
        """
        Adiciona job para um símbolo
        
        Args:
            pair: Par da criptomoeda
        
        Returns:
            (success, message)
        """
        # Busca configuração
        config = config_service.get_symbol_config(pair)
        
        if not config:
            return False, f"Configuração de {pair} não encontrada"
        
        if not config.get('enabled'):
            return False, f"{pair} está desabilitado"
        
        schedule = config.get('schedule', {})
        if not schedule.get('enabled'):
            return False, f"Schedule de {pair} está desabilitado"
        
        # Suporta interval_minutes ou interval_hours
        interval_minutes = schedule.get('interval_minutes')
        interval_hours = schedule.get('interval_hours')
        
        # Prioriza minutos, mas aceita horas
        if interval_minutes:
            interval_value = interval_minutes
            interval_unit = 'minutes'
            interval_display = f"{interval_minutes} minuto{'s' if interval_minutes != 1 else ''}"
        elif interval_hours:
            interval_value = interval_hours
            interval_unit = 'hours'
            interval_display = f"{interval_hours}h"
        else:
            # Default: 2 horas
            interval_value = 2
            interval_unit = 'hours'
            interval_display = "2h"
        
        # ID único do job
        job_id = f"job_{pair.replace('/', '_')}"
        
        # Remove job existente se houver
        self.remove_job_for_symbol(pair)
        
        # Cria função do job
        job_function = self.create_symbol_job_function(pair)
        
        try:
            # Cria job com intervalo em minutos ou horas
            job_kwargs = {
                'id': job_id,
                'name': f"Tranding Job: {pair}",
                'replace_existing': True
            }
            job_kwargs[interval_unit] = interval_value
            
            self.scheduler.add_job(
                job_function,
                'interval',
                **job_kwargs
            )
            
            self.active_jobs[pair] = job_id
            
            return True, f"Job criado para {pair} (intervalo: {interval_display})"
            
        except Exception as e:
            return False, f"Erro ao criar job: {e}"
    
    def remove_job_for_symbol(self, pair: str) -> tuple[bool, str]:
        """
        Remove job de um símbolo
        
        Args:
            pair: Par da criptomoeda
        
        Returns:
            (success, message)
        """
        job_id = self.active_jobs.get(pair)
        
        if not job_id:
            return False, f"Job de {pair} não está ativo"
        
        try:
            self.scheduler.remove_job(job_id)
            del self.active_jobs[pair]
            return True, f"Job de {pair} removido"
        except JobLookupError:
            # Job já não existe
            if pair in self.active_jobs:
                del self.active_jobs[pair]
            return True, f"Job de {pair} já estava inativo"
        except Exception as e:
            return False, f"Erro ao remover job: {e}"
    
    def reload_all_jobs(self) -> tuple[int, int]:
        """
        Recarrega todos os jobs baseado nas configurações do MongoDB
        
        Returns:
            (jobs_added, jobs_removed)
        """
        # Remove todos os jobs atuais (silenciosamente)
        removed_count = 0
        for pair in list(self.active_jobs.keys()):
            success, _ = self.remove_job_for_symbol(pair)
            if success:
                removed_count += 1
        
        # Adiciona jobs para símbolos habilitados
        enabled_configs = config_service.get_all_configs(enabled_only=True)
        added_count = 0
        
        for config in enabled_configs:
            pair = config['pair']
            schedule = config.get('schedule', {})
            
            if schedule.get('enabled', True):
                success, message = self.add_job_for_symbol(pair)
                if success:
                    added_count += 1
                    print(f"> Job: {pair} ({message.split('(')[1].split(')')[0]})")
        
        return added_count, removed_count
    
    def get_active_jobs_status(self) -> dict:
        """
        Retorna status de todos os jobs ativos
        
        Returns:
            Dicionário com status dos jobs
        """
        jobs_status = []
        
        for pair, job_id in self.active_jobs.items():
            try:
                job = self.scheduler.get_job(job_id)
                config = config_service.get_symbol_config(pair)
                
                if job and config:
                    next_run = job.next_run_time.strftime('%Y-%m-%d %H:%M:%S') if job.next_run_time else None
                    
                    # Suporta interval_minutes ou interval_hours
                    schedule_config = config.get('schedule', {})
                    interval_minutes = schedule_config.get('interval_minutes')
                    interval_hours = schedule_config.get('interval_hours')
                    
                    jobs_status.append({
                        "pair": pair,
                        "job_id": job_id,
                        "next_run": next_run,
                        "interval_minutes": interval_minutes,
                        "interval_hours": interval_hours,
                        "last_execution": config.get('metadata', {}).get('last_execution'),
                        "status": config.get('metadata', {}).get('status', 'unknown')
                    })
            except Exception as e:
                print(f"Erro ao obter status de {pair}: {e}")
        
        return {
            "total_jobs": len(jobs_status),
            "jobs": jobs_status
        }


# Instância global (será inicializada no main.py)
job_manager = None


def initialize_job_manager(scheduler: BackgroundScheduler, api_key: str, api_secret: str):
    """
    Inicializa o gerenciador de jobs global
    
    Args:
        scheduler: Instância do APScheduler
        api_key: Chave da API
        api_secret: Secret da API
    """
    global job_manager
    job_manager = DynamicJobManager(scheduler, api_key, api_secret)
    return job_manager
