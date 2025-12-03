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
from apscheduler.jobstores.base import ConflictingIdError, JobLookupError

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.services.config_service import config_service
from src.clients.exchange import MexcClient

TZ = pytz.timezone("America/Sao_Paulo")


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
            """Job específico para executar ordem de um símbolo"""
            # Busca configuração atualizada do MongoDB
            config = config_service.get_symbol_config(pair)
            
            if not config or not config.get('enabled'):
                # Desabilitado - pula silenciosamente
                return
            
            # Executa ordem 24/7 (sem restrição de horário)
            try:
                print(f"\n[JOB] {pair} | {datetime.now(TZ).strftime('%H:%M:%S')}")
                
                # Cria cliente com configuração do MongoDB
                mexc_client = MexcClient(self.api_key, self.api_secret, config)
                
                # TODO: Modificar create_order para aceitar símbolo específico
                # Por enquanto, executa ordem normal
                result = mexc_client.create_order(execution_type="scheduled")
                
                # Atualiza metadata
                metadata_updates = {
                    "last_execution": datetime.now(),
                    "status": "active"
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
                
                # Job executado silenciosamente
                
            except Exception as e:
                print(f"! Erro job {pair}: {e}")
                
                # Atualiza status para erro
                config_service.update_metadata(pair, {
                    "last_execution": datetime.now(),
                    "status": "error"
                })
        
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
                'name': f"Trading Job: {pair}",
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
                    print(f"   > Job: {pair} ({message.split('(')[1].split(')')[0]})")
        
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
