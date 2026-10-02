"""Inference background tasks."""
import asyncio
import structlog
from typing import List, Dict, Any

from celery import shared_task

from app.services.inference.engine import get_inference_engine
from app.services.routing.router import get_model_router

logger = structlog.get_logger()


@shared_task(bind=True, max_retries=3)
def batch_inference_task(self, requests: List[Dict[str, Any]]):
    """Process multiple inference requests in batch."""
    logger.info("celery_batch_inference", count=len(requests))
    
    async def _batch():
        engine = await get_inference_engine()
        router = await get_model_router()
        
        results = []
        for req in requests:
            try:
                # Route if needed
                model = req.get("model")
                if not model:
                    routing = await router.route(req["query"], req.get("context"))
                    model = routing.model
                
                # Generate
                result = await engine.generate(
                    model=model,
                    messages=req["messages"],
                    temperature=req.get("temperature"),
                    stream=False,
                )
                
                results.append({
                    "success": True,
                    "response": result.text,
                    "model": result.model,
                    "tokens": result.total_tokens,
                    "time_ms": result.generation_time_ms,
                })
            except Exception as e:
                results.append({
                    "success": False,
                    "error": str(e),
                })
        
        return results
    
    try:
        return asyncio.run(_batch())
    except Exception as e:
        logger.error("celery_batch_inference_failed", error=str(e))
        raise self.retry(exc=e, countdown=60)


@shared_task(bind=True, max_retries=2)
def pull_model_task(self, model_name: str):
    """Pull/download a model in background."""
    logger.info("celery_pull_model", model=model_name)
    
    async def _pull():
        engine = await get_inference_engine()
        async for progress in engine.pull_model(model_name):
            # Could update progress via Celery
            pass
        return {"success": True, "model": model_name}
    
    try:
        return asyncio.run(_pull())
    except Exception as e:
        logger.error("celery_pull_model_failed", model=model_name, error=str(e))
        raise self.retry(exc=e, countdown=120)


@shared_task
def warmup_models_task(model_names: List[str]):
    """Warm up models by running a dummy inference."""
    logger.info("celery_warmup_models", models=model_names)
    
    async def _warmup():
        engine = await get_inference_engine()
        results = {}
        
        for model in model_names:
            try:
                result = await engine.generate(
                    model=model,
                    messages=[{"role": "user", "content": "Hello"}],
                    max_tokens=10,
                )
                results[model] = {"status": "warmed", "time_ms": result.generation_time_ms}
            except Exception as e:
                results[model] = {"status": "failed", "error": str(e)}
        
        return results
    
    return asyncio.run(_warmup())