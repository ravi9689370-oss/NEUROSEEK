"""NeuroSeek AI - Main FastAPI Application."""
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
import structlog

from app.core.config import get_settings
from app.core.database import init_db, close_db
from app.api.routes import (
    chat, conversations, models, training, feedback, analytics, health
)
from app.services.inference.engine import get_inference_engine, close_inference_engine
from app.services.routing.router import get_model_router
from app.services.routing.ensemble import get_ensemble_manager
from app.services.training.scheduler import get_training_scheduler, TrainingScheduler

# Configure structlog
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(20),  # INFO
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()
settings = get_settings()

# Global references for cleanup
_scheduler: TrainingScheduler | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global _scheduler
    
    logger.info("starting_neuroseek_ai", version=settings.app.version)
    
    # Initialize database
    await init_db()
    logger.info("database_initialized")
    
    # Initialize inference engine
    inference_engine = await get_inference_engine()
    logger.info("inference_engine_initialized")
    
    # Initialize router and ensemble
    await get_model_router()
    await get_ensemble_manager()
    logger.info("routing_initialized")
    
    # Initialize training scheduler
    _scheduler = await get_training_scheduler()
    await _scheduler.start()
    logger.info("training_scheduler_started")
    
    yield
    
    # Cleanup
    logger.info("shutting_down")
    
    if _scheduler:
        await _scheduler.stop()
    
    await close_inference_engine()
    await close_db()
    
    logger.info("shutdown_complete")


app = FastAPI(
    title=settings.app.name,
    version=settings.app.version,
    description="Self-improving multi-model AI with continuous LoRA fine-tuning",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.app.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)


# Exception handlers
@app.exception_handler(500)
async def internal_error_handler(request, exc):
    logger.error("internal_server_error", path=request.url.path, error=str(exc))
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc)},
    )


# Include routers
app.include_router(health.router, prefix=settings.app.api_prefix, tags=["Health"])
app.include_router(chat.router, prefix=settings.app.api_prefix, tags=["Chat"])
app.include_router(conversations.router, prefix=settings.app.api_prefix, tags=["Conversations"])
app.include_router(models.router, prefix=settings.app.api_prefix, tags=["Models"])
app.include_router(training.router, prefix=settings.app.api_prefix, tags=["Training"])
app.include_router(feedback.router, prefix=settings.app.api_prefix, tags=["Feedback"])
app.include_router(analytics.router, prefix=settings.app.api_prefix, tags=["Analytics"])


# Root endpoint
@app.get("/")
async def root():
    return {
        "name": settings.app.name,
        "version": settings.app.version,
        "description": "Self-improving multi-model AI with continuous LoRA fine-tuning",
        "docs": "/docs",
        "health": f"{settings.app.api_prefix}/health",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.app.host,
        port=settings.app.port,
        reload=settings.app.debug,
        log_config=None,  # Use structlog
    )