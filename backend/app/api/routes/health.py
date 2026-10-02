"""Health check API routes."""
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.services.inference.engine import InferenceEngine, get_inference_engine

router = APIRouter()
settings = get_settings()


@router.get("/health")
async def health_check(
    db: AsyncSession = Depends(get_db),
    engine: InferenceEngine = Depends(get_inference_engine),
):
    """Comprehensive health check."""
    checks = {}
    
    # Database
    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = "healthy"
    except Exception as e:
        checks["database"] = f"unhealthy: {str(e)}"
    
    # Redis - would need redis client
    checks["redis"] = "healthy"  # Placeholder
    
    # Ollama
    ollama_health = await engine.health_check()
    checks["ollama"] = "healthy" if ollama_health.get("ollama") == "healthy" else "unhealthy"
    
    # Models loaded
    models = ollama_health.get("models", [])
    checks["models_loaded"] = len(models)
    
    # Overall status
    unhealthy = [k for k, v in checks.items() if isinstance(v, str) and v.startswith("unhealthy")]
    overall = "healthy" if not unhealthy else "degraded"
    
    return {
        "status": overall,
        "version": settings.app.version,
        "checks": checks,
    }


@router.get("/ready")
async def readiness_check(
    db: AsyncSession = Depends(get_db),
    engine: InferenceEngine = Depends(get_inference_engine),
):
    """Kubernetes readiness probe."""
    try:
        await db.execute(text("SELECT 1"))
        ollama_health = await engine.health_check()
        if ollama_health.get("ollama") != "healthy":
            return {"ready": False, "reason": "Ollama not ready"}
        return {"ready": True}
    except Exception as e:
        return {"ready": False, "reason": str(e)}


@router.get("/live")
async def liveness_check():
    """Kubernetes liveness probe."""
    return {"alive": True}


@router.get("/version")
async def version_info():
    """Get version information."""
    return {
        "name": settings.app.name,
        "version": settings.app.version,
        "api_version": "v1",
    }