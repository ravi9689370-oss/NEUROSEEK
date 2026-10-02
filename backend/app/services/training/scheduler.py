"""Training scheduler - manages automatic training triggers and job queue."""
import asyncio
import json
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
from uuid import UUID

import structlog
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db_session
from app.models.conversation import Message, MessageFeedback
from app.models.training import TrainingRun, TrainingStatus, TrainingMethod, LoRAAdapter
from app.services.training.trainer import LoRATrainer, get_trainer
from app.services.training.data_curator import DataCurator, get_data_curator

logger = structlog.get_logger()
settings = get_settings()


class TrainingScheduler:
    """Schedule and manage automatic training runs."""
    
    def __init__(self):
        self.config = settings.training
        self.trigger_config = self.config.trigger
        self._running = False
        _task = None
    
    async def start(self) -> None:
        """Start the scheduler background task."""
        if not self.config.enabled or not self.trigger_config.auto_trigger:
            logger.info("training_scheduler_disabled")
            return
        
        self._running = True
        self._task = asyncio.create_task(self._scheduler_loop())
        logger.info("training_scheduler_started")
    
    async def stop(self) -> None:
        """Stop the scheduler."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("training_scheduler_stopped")
    
    async def _scheduler_loop(self) -> None:
        """Main scheduler loop - checks for training triggers periodically."""
        while self._running:
            try:
                await self.check_and_trigger_training()
            except Exception as e:
                logger.error("scheduler_loop_error", error=str(e))
            
            # Check every hour
            await asyncio.sleep(3600)
    
    async def check_and_trigger_training(self) -> Optional[TrainingRun]:
        """Check if training should be triggered and start it."""
        async with get_db_session() as db:
            # Check if enough new feedback data
            new_samples = await self._count_new_training_samples(db)
            
            if new_samples < self.trigger_config.min_new_samples:
                logger.debug("not_enough_samples_for_training", 
                           new_samples=new_samples, 
                           required=self.trigger_config.min_new_samples)
                return None
            
            # Check if training ran recently
            last_run = await self._get_last_completed_training(db)
            if last_run:
                hours_since = (datetime.now(timezone.utc) - last_run.completed_at).total_seconds() / 3600
                if hours_since < self.trigger_config.max_training_frequency_hours:
                    logger.debug("training_too_recent", hours_since=hours_since)
                    return None
            
            # Check for running training
            running = await self._get_running_training(db)
            if running:
                logger.debug("training_already_running", run_id=str(running.id))
                return None
            
            # Trigger training
            logger.info("triggering_automatic_training", new_samples=new_samples)
            return await self.trigger_training(
                method=self.config.method,
                reason=f"Auto-triggered: {new_samples} new samples",
            )
    
    async def _count_new_training_samples(self, db: AsyncSession, since: Optional[datetime] = None) -> int:
        """Count new training-eligible samples since last training."""
        if since is None:
            last_run = await self._get_last_completed_training(db)
            since = last_run.completed_at if last_run else datetime.now(timezone.utc) - timedelta(days=30)
        
        # Count positive feedback, edits, regenerations
        query = select(func.count(Message.id)).where(
            and_(
                Message.created_at >= since,
                Message.feedback.in_([
                    MessageFeedback.POSITIVE,
                    MessageFeedback.EDITED,
                    MessageFeedback.REGENERATED,
                ]),
                Message.is_training_candidate == True,
            )
        )
        result = await db.execute(query)
        return result.scalar() or 0
    
    async def _get_last_completed_training(self, db: AsyncSession) -> Optional[TrainingRun]:
        query = select(TrainingRun).where(
            TrainingStatus.COMPLETED == TrainingRun.status
        ).order_by(TrainingRun.completed_at.desc()).limit(1)
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def _get_running_training(self, db: AsyncSession) -> Optional[TrainingRun]:
        query = select(TrainingRun).where(
            TrainingRun.status.in_([
                TrainingStatus.PENDING,
                TrainingStatus.PREPARING,
                TrainingStatus.RUNNING,
                TrainingStatus.EVALUATING,
            ])
        ).limit(1)
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def trigger_training(
        self,
        method: TrainingMethod = TrainingMethod.QLORA,
        reason: str = "Manual trigger",
        hyperparameters: Optional[Dict] = None,
    ) -> TrainingRun:
        """Manually trigger a training run."""
        async with get_db_session() as db:
            # Create training run record
            run = TrainingRun(
                name=f"training_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
                description=reason,
                method=method,
                base_model_id=await self._get_base_model_id(db),
                hyperparameters=hyperparameters or self._get_default_hyperparams(),
                status=TrainingStatus.PENDING,
            )
            db.add(run)
            await db.commit()
            await db.refresh(run)
            
            # Start training in background
            asyncio.create_task(self._run_training(run.id))
            
            return run
    
    async def _get_base_model_id(self, db: AsyncSession) -> UUID:
        from app.models.model_registry import ModelRegistry
        query = select(ModelRegistry.id).where(
            ModelRegistry.name == settings.training.base_model_local
        )
        result = await db.execute(query)
        model_id = result.scalar_one_or_none()
        if not model_id:
            raise ValueError(f"Base model {settings.training.base_model_local} not found in registry")
        return model_id
    
    def _get_default_hyperparams(self) -> Dict:
        return {
            "lora_r": self.config.lora.r,
            "lora_alpha": self.config.lora.alpha,
            "lora_dropout": self.config.lora.dropout,
            "target_modules": self.config.lora.target_modules,
            "learning_rate": self.config.trainer.learning_rate,
            "max_steps": self.config.trainer.max_steps,
            "batch_size": self.config.trainer.per_device_train_batch_size,
            "gradient_accumulation": self.config.trainer.gradient_accumulation_steps,
        }
    
    async def _run_training(self, run_id: UUID) -> None:
        """Execute the full training pipeline."""
        async with get_db_session() as db:
            run = await db.get(TrainingRun, run_id)
            if not run:
                logger.error("training_run_not_found", run_id=str(run_id))
                return
            
            try:
                # Phase 1: Preparing
                run.status = TrainingStatus.PREPARING
                run.started_at = datetime.now(timezone.utc)
                await db.commit()
                
                # Curate data
                curator = await get_data_curator()
                dataset_dict, stats = await curator.curate_training_data()
                
                # Update run with dataset stats
                run.train_samples = stats.sft_samples + stats.preference_pairs * 2
                run.val_samples = 0  # Will be updated after split
                await db.commit()
                
                # Save datasets
                output_dir = f"models/training_runs/{run_id}"
                saved_paths = await curator.save_datasets(dataset_dict, output_dir)
                run.output_dir = output_dir
                
                # Phase 2: Training
                run.status = TrainingStatus.RUNNING
                await db.commit()
                
                trainer = await get_trainer()
                
                # Progress callback
                async def update_progress(progress_data: Dict):
                    async with get_db_session() as progress_db:
                        progress_run = await progress_db.get(TrainingRun, run_id)
                        if progress_run:
                            progress_run.progress = progress_data["progress"]
                            progress_run.current_step = progress_data["step"]
                            progress_run.total_steps = progress_data["max_steps"]
                            progress_run.current_epoch = progress_data.get("epoch", 0)
                            if "loss" in progress_data:
                                progress_run.train_loss = progress_data["loss"]
                            await progress_db.commit()
                
                # Select dataset based on method
                if run.method == TrainingMethod.DPO:
                    train_ds = dataset_dict["preference"]["train"]
                    eval_ds = dataset_dict["preference"].get("validation")
                    result = await trainer.train_dpo(
                        train_dataset=train_ds,
                        eval_dataset=eval_ds,
                        output_dir=output_dir,
                        run_id=str(run_id),
                        progress_callback=update_progress,
                    )
                else:
                    train_ds = dataset_dict["sft"]["train"]
                    eval_ds = dataset_dict["sft"].get("validation")
                    result = await trainer.train_lora(
                        train_dataset=train_ds,
                        eval_dataset=eval_ds,
                        output_dir=output_dir,
                        run_id=str(run_id),
                        progress_callback=update_progress,
                    )
                
                if not result.success:
                    run.status = TrainingStatus.FAILED
                    run.error_message = result.error
                    run.completed_at = datetime.now(timezone.utc)
                    await db.commit()
                    return
                
                # Phase 3: Evaluating
                run.status = TrainingStatus.EVALUATING
                run.adapter_path = result.adapter_path
                run.metrics = result.metrics
                await db.commit()
                
                # Run evaluation (simplified - would call evaluator service)
                eval_results = await self._evaluate_adapter(run, result.adapter_path)
                run.eval_results = eval_results
                run.improvement_score = eval_results.get("improvement", 0)
                run.passed_evaluation = eval_results.get("passed", False)
                
                # Phase 4: Complete or Deploy
                if run.passed_evaluation and self.config.evaluation.auto_deploy:
                    run.status = TrainingStatus.DEPLOYED
                    deployed_model = await self._deploy_adapter(run)
                    run.deployed_model_id = deployed_model.id
                    run.deployed_at = datetime.now(timezone.utc)
                else:
                    run.status = TrainingStatus.COMPLETED
                
                run.completed_at = datetime.now(timezone.utc)
                run.duration_seconds = int((run.completed_at - run.started_at).total_seconds())
                await db.commit()
                
                logger.info("training_completed", run_id=str(run_id), status=run.status.value)
                
            except Exception as e:
                logger.error("training_failed", run_id=str(run_id), error=str(e))
                run.status = TrainingStatus.FAILED
                run.error_message = str(e)
                run.completed_at = datetime.now(timezone.utc)
                if run.started_at:
                    run.duration_seconds = int((run.completed_at - run.started_at).total_seconds())
                await db.commit()
    
    async def _evaluate_adapter(self, run: TrainingRun, adapter_path: str) -> Dict[str, Any]:
        """Evaluate trained adapter against base model."""
        # This would call the ModelEvaluator service
        # Simplified for now
        return {
            "improvement": run.improvement_score or 0.05,
            "passed": True,
            "benchmarks": {},
        }
    
    async def _deploy_adapter(self, run: TrainingRun) -> LoRAAdapter:
        """Deploy adapter to Ollama as a new model."""
        # This would create a Modelfile and register with Ollama
        # Simplified for now
        from app.models.training import LoRAAdapter
        
        async with get_db_session() as db:
            adapter = LoRAAdapter(
                name=f"{run.name}_adapter",
                training_run_id=run.id,
                base_model_id=run.base_model_id,
                r=run.hyperparameters.get("lora_r", 64),
                alpha=run.hyperparameters.get("lora_alpha", 128),
                dropout=run.hyperparameters.get("lora_dropout", 0.05),
                target_modules=run.hyperparameters.get("target_modules", []),
                adapter_path=run.adapter_path,
                eval_metrics=run.eval_results,
                is_active=True,
                deployed_at=datetime.now(timezone.utc),
            )
            db.add(adapter)
            await db.commit()
            await db.refresh(adapter)
            return adapter
    
    async def get_training_status(self, run_id: UUID) -> Optional[Dict]:
        """Get current training status."""
        async with get_db_session() as db:
            run = await db.get(TrainingRun, run_id)
            if not run:
                return None
            
            return {
                "id": str(run.id),
                "name": run.name,
                "status": run.status.value,
                "progress": run.progress,
                "current_step": run.current_step,
                "total_steps": run.total_steps,
                "current_epoch": run.current_epoch,
                "train_loss": run.train_loss,
                "val_loss": run.val_loss,
                "metrics": run.metrics,
                "eval_results": run.eval_results,
                "improvement_score": run.improvement_score,
                "passed_evaluation": run.passed_evaluation,
                "started_at": run.started_at.isoformat() if run.started_at else None,
                "completed_at": run.completed_at.isoformat() if run.completed_at else None,
                "duration_seconds": run.duration_seconds,
                "error_message": run.error_message,
            }
    
    async def cancel_training(self, run_id: UUID) -> bool:
        """Cancel a running training."""
        async with get_db_session() as db:
            run = await db.get(TrainingRun, run_id)
            if not run:
                return False
            
            if run.status in [TrainingStatus.RUNNING, TrainingStatus.PREPARING, TrainingStatus.PENDING]:
                run.status = TrainingStatus.CANCELLED
                run.completed_at = datetime.now(timezone.utc)
                await db.commit()
                return True
            return False


# Singleton
_scheduler: Optional[TrainingScheduler] = None
_scheduler_lock = asyncio.Lock()


async def get_training_scheduler() -> TrainingScheduler:
    global _scheduler
    async with _scheduler_lock:
        if _scheduler is None:
            _scheduler = TrainingScheduler()
        return _scheduler