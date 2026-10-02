"""Training API routes."""
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.training import TrainingRun, TrainingStatus, TrainingMethod, LoRAAdapter
from app.schemas import (
    TrainingRunCreate,
    TrainingRunUpdate,
    TrainingRunResponse,
    EvaluationRequest,
    EvaluationResponse,
)
from app.services.training.scheduler import TrainingScheduler, get_training_scheduler
from app.services.training.evaluator import ModelEvaluator, get_evaluator
from app.services.inference.engine import InferenceEngine, get_inference_engine

router = APIRouter()


@router.post("", response_model=TrainingRunResponse)
async def create_training_run(
    training_run: TrainingRunCreate,
    db: AsyncSession = Depends(get_db),
    scheduler: TrainingScheduler = Depends(get_training_scheduler),
):
    """Create and start a new training run."""
    run = await scheduler.trigger_training(
        method=TrainingMethod(training_run.method),
        reason=training_run.description or "Manual trigger",
        hyperparameters=training_run.hyperparameters,
    )
    
    return TrainingRunResponse.model_validate(run)


@router.get("", response_model=List[TrainingRunResponse])
async def list_training_runs(
    db: AsyncSession = Depends(get_db),
    status: Optional[TrainingStatus] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    """List training runs."""
    query = select(TrainingRun).order_by(desc(TrainingRun.created_at))
    
    if status:
        query = query.where(TrainingRun.status == status)
    
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    runs = result.scalars().all()
    
    return [TrainingRunResponse.model_validate(r) for r in runs]


@router.get("/{run_id}", response_model=TrainingRunResponse)
async def get_training_run(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get training run details."""
    result = await db.execute(select(TrainingRun).where(TrainingRun.id == run_id))
    run = result.scalar_one_or_none()
    
    if not run:
        raise HTTPException(404, "Training run not found")
    
    return TrainingRunResponse.model_validate(run)


@router.get("/{run_id}/status")
async def get_training_status(
    run_id: uuid.UUID,
    scheduler: TrainingScheduler = Depends(get_training_scheduler),
):
    """Get real-time training status."""
    status = await scheduler.get_training_status(run_id)
    if not status:
        raise HTTPException(404, "Training run not found")
    return status


@router.post("/{run_id}/cancel")
async def cancel_training(
    run_id: uuid.UUID,
    scheduler: TrainingScheduler = Depends(get_training_scheduler),
):
    """Cancel a running training."""
    success = await scheduler.cancel_training(run_id)
    if not success:
        raise HTTPException(400, "Cannot cancel - training not in cancellable state")
    return {"success": True, "message": "Training cancelled"}


@router.post("/trigger", response_model=TrainingRunResponse)
async def trigger_training(
    method: str = "qlora",
    reason: str = "Manual trigger",
    scheduler: TrainingScheduler = Depends(get_training_scheduler),
):
    """Manually trigger training."""
    run = await scheduler.trigger_training(
        method=TrainingMethod(method),
        reason=reason,
    )
    return TrainingRunResponse.model_validate(run)


@router.post("/evaluate", response_model=List[EvaluationResponse])
async def evaluate_model(
    request: EvaluationRequest,
    evaluator: ModelEvaluator = Depends(get_evaluator),
):
    """Evaluate a model on benchmarks."""
    results = await evaluator.evaluate_model(
        model_name=request.model_id,  # This would need model name lookup
        benchmarks=request.benchmarks,
    )
    
    return [
        EvaluationResponse(
            model_id=r.model_id,
            benchmark=r.benchmark,
            score=r.score,
            details=r.details,
            compared_to_base=r.compared_to_base,
            improvement=r.improvement,
        )
        for r in results
    ]


@router.post("/compare")
async def compare_models(
    model_a: str,
    model_b: str,
    prompts: List[str],
    evaluator: ModelEvaluator = Depends(get_evaluator),
):
    """Compare two models side by side."""
    return await evaluator.compare_models(model_a, model_b, prompts)


@router.get("/adapters/", response_model=List[dict])
async def list_adapters(db: AsyncSession = Depends(get_db)):
    """List trained LoRA adapters."""
    result = await db.execute(select(LoRAAdapter).order_by(desc(LoRAAdapter.created_at)))
    adapters = result.scalars().all()
    
    return [
        {
            "id": str(a.id),
            "name": a.name,
            "training_run_id": str(a.training_run_id),
            "base_model_id": str(a.base_model_id),
            "r": a.r,
            "alpha": a.alpha,
            "dropout": a.dropout,
            "adapter_path": a.adapter_path,
            "eval_metrics": a.eval_metrics,
            "is_active": a.is_active,
            "deployed_at": a.deployed_at.isoformat() if a.deployed_at else None,
            "created_at": a.created_at.isoformat(),
        }
        for a in adapters
    ]


@router.post("/adapters/{adapter_id}/activate")
async def activate_adapter(
    adapter_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Activate a LoRA adapter (set as default for base model)."""
    result = await db.execute(select(LoRAAdapter).where(LoRAAdapter.id == adapter_id))
    adapter = result.scalar_one_or_none()
    
    if not adapter:
        raise HTTPException(404, "Adapter not found")
    
    # Deactivate other adapters for same base model
    await db.execute(
        select(LoRAAdapter)
        .where(LoRAAdapter.base_model_id == adapter.base_model_id)
        .where(LoRAAdapter.id != adapter_id)
    )
    # Actually update
    from sqlalchemy import update
    await db.execute(
        update(LoRAAdapter)
        .where(LoRAAdapter.base_model_id == adapter.base_model_id)
        .where(LoRAAdapter.id != adapter_id)
        .values(is_active=False)
    )
    
    adapter.is_active = True
    await db.commit()
    
    return {"success": True, "message": f"Adapter {adapter.name} activated"}


@router.get("/history")
async def training_history(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(20, ge=1, le=100),
):
    """Get training history with metrics."""
    result = await db.execute(
        select(TrainingRun)
        .where(TrainingRun.status.in_([TrainingStatus.COMPLETED, TrainingStatus.DEPLOYED, TrainingStatus.FAILED]))
        .order_by(desc(TrainingRun.completed_at))
        .limit(limit)
    )
    runs = result.scalars().all()
    
    return [
        {
            "id": str(r.id),
            "name": r.name,
            "method": r.method.value,
            "status": r.status.value,
            "train_samples": r.train_samples,
            "train_loss": r.train_loss,
            "val_loss": r.val_loss,
            "improvement_score": r.improvement_score,
            "passed_evaluation": r.passed_evaluation,
            "duration_seconds": r.duration_seconds,
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
            "deployed": r.status == TrainingStatus.DEPLOYED,
        }
        for r in runs
    ]