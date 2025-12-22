"""
Jobs Router - FastAPI
Endpoints para monitoramento de jobs/workers
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional
from datetime import datetime
import logging
from motor.motor_asyncio import AsyncIOMotorDatabase

from src.api_fastapi.database import get_database

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================
# JOBS ENDPOINTS
# ============================================

@router.get("/jobs/status")
async def get_jobs_status(
    job_type: Optional[str] = Query(None, description="Filtrar por tipo de job"),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Busca status de jobs em execução
    
    Args:
        job_type: Tipo de job (strategy_worker, balance_sync, price_feed)
        
    Returns:
        Status de jobs ativos
    """
    try:
        query = {}
        
        if job_type:
            query["type"] = job_type
        
        # Buscar jobs
        cursor = db.jobs.find(query).sort("last_run", -1)
        jobs = await cursor.to_list(length=100)
        
        # Formatar IDs
        for job in jobs:
            job["_id"] = str(job["_id"])
        
        # Estatísticas
        total_jobs = len(jobs)
        active_jobs = len([j for j in jobs if j.get("is_running", False)])
        failed_jobs = len([j for j in jobs if j.get("status") == "failed"])
        
        return {
            "success": True,
            "jobs": jobs,
            "stats": {
                "total": total_jobs,
                "active": active_jobs,
                "failed": failed_jobs
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting jobs status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs/{job_id}")
async def get_job_details(
    job_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Busca detalhes de um job específico
    
    Args:
        job_id: ID do job
        
    Returns:
        Detalhes do job
    """
    try:
        from bson import ObjectId
        
        if not ObjectId.is_valid(job_id):
            raise HTTPException(status_code=400, detail="Invalid job_id format")
        
        job = await db.jobs.find_one({"_id": ObjectId(job_id)})
        
        if not job:
            raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
        
        job["_id"] = str(job["_id"])
        
        # Buscar logs do job
        logs_cursor = db.job_logs.find({"job_id": ObjectId(job_id)}).sort("timestamp", -1).limit(50)
        logs = await logs_cursor.to_list(length=50)
        
        for log in logs:
            log["_id"] = str(log["_id"])
            log["job_id"] = str(log["job_id"])
        
        return {
            "success": True,
            "job": job,
            "recent_logs": logs
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job details: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs/scheduler/status")
async def get_scheduler_status():
    """
    Busca status do scheduler APScheduler
    
    Returns:
        Status do scheduler e jobs agendados
    """
    try:
        # TODO: Implementar quando scheduler global estiver configurado
        # Por enquanto, retornar status mockado
        
        return {
            "success": True,
            "scheduler": {
                "running": False,
                "jobs_count": 0,
                "jobs": [],
                "message": "Scheduler not initialized. Need to configure global scheduler instance."
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting scheduler status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/jobs/{job_id}/restart")
async def restart_job(
    job_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Reinicia um job que falhou
    
    Args:
        job_id: ID do job
        
    Returns:
        Confirmação
    """
    try:
        from bson import ObjectId
        
        if not ObjectId.is_valid(job_id):
            raise HTTPException(status_code=400, detail="Invalid job_id format")
        
        job = await db.jobs.find_one({"_id": ObjectId(job_id)})
        
        if not job:
            raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
        
        # Atualizar status do job
        await db.jobs.update_one(
            {"_id": ObjectId(job_id)},
            {
                "$set": {
                    "status": "pending",
                    "is_running": False,
                    "error_count": 0,
                    "last_error": None,
                    "restarted_at": datetime.utcnow()
                }
            }
        )
        
        logger.info(f"✅ Job {job_id} restarted")
        
        return {
            "success": True,
            "message": "Job restarted successfully",
            "job_id": job_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error restarting job: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
