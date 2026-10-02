"""Evaluation background tasks."""
import asyncio
import structlog
from uuid import UUID
from typing import List, Dict, Any

from celery import shared_task

from app.core.database import get_db_session
from app.models.training import TrainingRun, TrainingStatus
from app.services.training.evaluator import ModelEvaluator, get_evaluator
from app.services.inference.engine import get_inference_engine

logger = structlog.get_logger()


@shared_task(bind=True, max_retries=2)
def evaluate_model_task(self, run_id: str):
    """Evaluate a trained model."""
    logger.info("celery_evaluate_model", run_id=run_id)
    
    async def _evaluate():
        async with get_db_session() as db:
            from app.models.training import LoRAAdapter
            from sqlalchemy import select
            
            # Get the run and adapter
            run = await db.get(TrainingRun, UUID(run_id))
            if not run:
                raise ValueError(f"Run {run_id} not found")
            
            # Get deployed adapter
            adapter_result = await db.execute(
                select(LoRAAdapter).where(LoRAAdapter.training_run_id == UUID(run_id))
            )
            adapter = adapter_result.scalar_one_or_none()
            
            if not adapter or not adapter.is_active:
                raise ValueError("No active adapter found for this run")
            
            # Get model names
            from app.models.model_registry import ModelRegistry
            base_model_result = await db.execute(
                select(ModelRegistry.name).where(ModelRegistry.id == run.base_model_id)
            )
            base_model_name = base_model_result.scalar_one_or_none()
            
            adapter_model_name = f"{base_model_name}-{adapter.name}"
            
            # Run evaluation
            evaluator = await get_evaluator()
            results = await evaluator.evaluate_model(
                model_name=adapter_model_name,
                base_model=base_model_name,
            )
            
            # Update run with results
            run.eval_results = {r.benchmark: r.details for r in results}
            run.improvement_score = max((r.improvement or 0) for r in results)
            run.passed_evaluation = all(r.passed for r in results)
            
            if run.passed_evaluation and run.status == TrainingStatus.EVALUATING:
                run.status = TrainingStatus.DEPLOYED
            
            await db.commit()
            
            return {
                "run_id": run_id,
                "results": [
                    {
                        "benchmark": r.benchmark,
                        "score": r.score,
                        "improvement": r.improvement,
                        "passed": r.passed,
                    }
                    for r in results
                ],
            }
    
    try:
        return asyncio.run(_evaluate())
    except Exception as e:
        logger.error("celery_evaluate_failed", run_id=run_id, error=str(e))
        raise self.retry(exc=e, countdown=300)


@shared_task(bind=True, max_retries=1)
def compare_models_task(self, model_a: str, model_b: str, prompts: List[str]):
    """Compare two models side by side."""
    logger.info("celery_compare_models", model_a=model_a, model_b=model_b)
    
    async def _compare():
        evaluator = await get_evaluator()
        return await evaluator.compare_models(model_a, model_b, prompts)
    
    try:
        return asyncio.run(_compare())
    except Exception as e:
        logger.error("celery_compare_failed", error=str(e))
        raise self.retry(exc=e, countdown=60)


@shared_task
def benchmark_all_models_task(benchmarks: List[str] = None):
    """Run benchmarks on all available models."""
    logger.info("celery_benchmark_all", benchmarks=benchmarks)
    
    async def _benchmark():
        engine = await get_inference_engine()
        models = await engine.list_models()
        model_names = [m["name"] for m in models]
        
        evaluator = await get_evaluator()
        results = {}
        
        for model in model_names:
            try:
                model_results = await evaluator.evaluate_model(
                    model_name=model,
                    benchmarks=benchmarks,
                )
                results[model] = [
                    {"benchmark": r.benchmark, "score": r.score, "passed": r.passed}
                    for r in model_results
                ]
            except Exception as e:
                logger.error("model_benchmark_failed", model=model, error=str(e))
                results[model] = {"error": str(e)}
        
        return results
    
    return asyncio.run(_benchmark())