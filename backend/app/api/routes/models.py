"""Model registry API routes."""
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.model_registry import ModelRegistry, ModelType, ModelStatus
from app.schemas import (
    ModelRegistryCreate,
    ModelRegistryUpdate,
    ModelRegistryResponse,
)
from app.services.inference.engine import InferenceEngine, get_inference_engine

router = APIRouter()


@router.post("", response_model=ModelRegistryResponse)
async def register_model(
    model: ModelRegistryCreate,
    db: AsyncSession = Depends(get_db),
):
    """Register a new model in the registry."""
    # Check if exists
    result = await db.execute(select(ModelRegistry).where(ModelRegistry.name == model.name))
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(400, f"Model {model.name} already registered")
    
    db_model = ModelRegistry(**model.model_dump())
    db.add(db_model)
    await db.commit()
    await db.refresh(db_model)
    
    return ModelRegistryResponse.model_validate(db_model)


@router.get("", response_model=List[ModelRegistryResponse])
async def list_models(
    db: AsyncSession = Depends(get_db),
    model_type: Optional[ModelType] = None,
    status: Optional[ModelStatus] = None,
    trainable_only: bool = False,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
):
    """List registered models with filters."""
    query = select(ModelRegistry)
    
    if model_type:
        query = query.where(ModelRegistry.model_type == model_type)
    if status:
        query = query.where(ModelRegistry.status == status)
    if trainable_only:
        query = query.where(ModelRegistry.is_trainable == True)
    
    query = query.order_by(ModelRegistry.routing_priority, ModelRegistry.name).offset(skip).limit(limit)
    
    result = await db.execute(query)
    models = result.scalars().all()
    
    return [ModelRegistryResponse.model_validate(m) for m in models]


@router.get("/available", response_model=List[ModelRegistryResponse])
async def list_available_models(
    engine: InferenceEngine = Depends(get_inference_engine),
    db: AsyncSession = Depends(get_db),
):
    """List models that are currently available in Ollama."""
    ollama_models = await engine.list_models()
    ollama_names = {m["name"] for m in ollama_models}
    
    result = await db.execute(
        select(ModelRegistry).where(ModelRegistry.name.in_(ollama_names))
    )
    models = result.scalars().all()
    
    return [ModelRegistryResponse.model_validate(m) for m in models]


@router.get("/{model_id}", response_model=ModelRegistryResponse)
async def get_model(
    model_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get model details."""
    result = await db.execute(select(ModelRegistry).where(ModelRegistry.id == model_id))
    model = result.scalar_one_or_none()
    
    if not model:
        raise HTTPException(404, "Model not found")
    
    return ModelRegistryResponse.model_validate(model)


@router.patch("/{model_id}", response_model=ModelRegistryResponse)
async def update_model(
    model_id: uuid.UUID,
    update: ModelRegistryUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update model registry entry."""
    result = await db.execute(select(ModelRegistry).where(ModelRegistry.id == model_id))
    model = result.scalar_one_or_none()
    
    if not model:
        raise HTTPException(404, "Model not found")
    
    update_data = update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(model, field, value)
    
    await db.commit()
    await db.refresh(model)
    
    return ModelRegistryResponse.model_validate(model)


@router.delete("/{model_id}")
async def delete_model(
    model_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    engine: InferenceEngine = Depends(get_inference_engine),
):
    """Delete model from registry and optionally from Ollama."""
    result = await db.execute(select(ModelRegistry).where(ModelRegistry.id == model_id))
    model = result.scalar_one_or_none()
    
    if not model:
        raise HTTPException(404, "Model not found")
    
    # Delete from Ollama if requested
    await engine.delete_model(model.name)
    
    await db.delete(model)
    await db.commit()
    
    return {"success": True, "message": f"Model {model.name} deleted"}


@router.post("/{model_id}/set-default")
async def set_default_model(
    model_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Set model as default for its type."""
    result = await db.execute(select(ModelRegistry).where(ModelRegistry.id == model_id))
    model = result.scalar_one_or_none()
    
    if not model:
        raise HTTPException(404, "Model not found")
    
    # Reset all models of same type to lower priority
    await db.execute(
        select(ModelRegistry)
        .where(ModelRegistry.model_type == model.model_type)
        .where(ModelRegistry.id != model_id)
    )
    # Actually update them
    from sqlalchemy import update
    await db.execute(
        update(ModelRegistry)
        .where(ModelRegistry.model_type == model.model_type)
        .where(ModelRegistry.id != model_id)
        .values(routing_priority=ModelRegistry.routing_priority + 100)
    )
    
    # Set this model to highest priority
    model.routing_priority = 10
    await db.commit()
    
    return {"success": True, "message": f"{model.name} set as default for {model.model_type.value}"}


@router.get("/stats/overview")
async def model_stats(db: AsyncSession = Depends(get_db)):
    """Get model registry statistics."""
    total = await db.execute(select(func.count(ModelRegistry.id)))
    by_type = await db.execute(
        select(ModelRegistry.model_type, func.count(ModelRegistry.id))
        .group_by(ModelRegistry.model_type)
    )
    by_status = await db.execute(
        select(ModelRegistry.model_type, func.count(ModelRegistry.id))
        .group_by(ModelRegistry.status)
    )
    trainable = await db.execute(
        select(func.count(ModelRegistry.id)).where(ModelRegistry.is_trainable == True)
    )
    
    return {
        "total_models": total.scalar(),
        "by_type": dict(by_type.all()),
        "by_status": dict(by_status.all()),
        "trainable_models": trainable.scalar(),
    }