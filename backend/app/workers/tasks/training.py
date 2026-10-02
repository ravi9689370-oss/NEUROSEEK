"""Training background tasks."""
import asyncio
import structlog
from uuid import UUID

from celery import shared_task
from sqlalchemy import select

from app.core.database import get_db_session
from app.models.training import TrainingRun, TrainingStatus
from app.services.training.scheduler import TrainingScheduler, get_training_scheduler

logger = structlog.get_logger()


@shared_task(bind=True, max_retries=3)
def check_training_trigger(self):
    """Periodic task to check if training should be triggered."""
    logger.info("celery_check_training_trigger")
    
    async def _check():
        scheduler = await get_training_scheduler()
        run = await scheduler.check_and_trigger_training()
        if run:
            logger.info("celery_training_triggered", run_id=str(run.id))
            return str(run.id)
        return None
    
    try:
        return asyncio.run(_check())
    except Exception as e:
        logger.error("celery_check_training_failed", error=str(e))
        raise self.retry(exc=e, countdown=60)


@shared_task(bind=True, max_retries=2)
def run_training_task(self, run_id: str):
    """Execute a training run in background."""
    logger.info("celery_run_training_started", run_id=run_id)
    
    async def _run():
        scheduler = await get_training_scheduler()
        await scheduler._run_training(UUID(run_id))
    
    try:
        asyncio.run(_run())
        logger.info("celery_run_training_completed", run_id=run_id)
        return {"status": "completed", "run_id": run_id}
    except Exception as e:
        logger.error("celery_run_training_failed", run_id=run_id, error=str(e))
        raise self.retry(exc=e, countdown=300)


@shared_task(bind=True)
def cleanup_old_runs(self):
    """Clean up old training runs and artifacts."""
    logger.info("celery_cleanup_old_runs")
    
    async def _cleanup():
        async with get_db_session() as db:
            # Delete failed runs older than 30 days
            from datetime import datetime, timedelta, timezone
            cutoff = datetime.now(timezone.utc) - timedelta(days=30)
            
            result = await db.execute(
                select(TrainingRun).where(
                    TrainingRun.status == TrainingStatus.FAILED,
                    TrainingRun.created_at < cutoff,
                )
            )
            old_runs = result.scalars().all()
            
            for run in old_runs:
                # Clean up output directory
                import shutil
                from pathlib import Path
                if run.output_dir:
                    output_path = Path(run.output_dir)
                    if output_path.exists():
                        shutil.rmtree(output_path, ignore_errors=True)
                
                await db.delete(run)
            
            await db.commit()
            logger.info("celery_cleanup_completed", deleted=len(old_runs))
            return len(old_runs)
    
    try:
        return asyncio.run(_cleanup())
    except Exception as e:
        logger.error("celery_cleanup_failed", error=str(e))
        raise self.retry(exc=e, countdown=3600)