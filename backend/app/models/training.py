"""Training and LoRA adapter models."""
import enum
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, List

from sqlalchemy import (
    DateTime, String, Text, Integer, Float, ForeignKey, Enum, Index, JSON
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base


class TrainingStatus(str, enum.Enum):
    PENDING = "pending"
    PREPARING = "preparing"
    RUNNING = "running"
    EVALUATING = "evaluating"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    DEPLOYED = "deployed"


class TrainingMethod(str, enum.Enum):
    LORA = "lora"
    QLORA = "qlora"
    FULL = "full"
    DPO = "dpo"
    KTO = "kto"


class TrainingRun(Base):
    __tablename__ = "training_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Configuration
    method: Mapped[TrainingMethod] = mapped_column(Enum(TrainingMethod), nullable=False)
    base_model_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("model_registry.id", ondelete="RESTRICT"), nullable=False
    )
    
    # Hyperparameters (stored as JSON for flexibility)
    hyperparameters: Mapped[Dict] = mapped_column(JSONB, default=dict, nullable=False)
    
    # Dataset info
    train_samples: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    val_samples: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    dataset_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    
    # Status & Progress
    status: Mapped[TrainingStatus] = mapped_column(
        Enum(TrainingStatus), default=TrainingStatus.PENDING, nullable=False, index=True
    )
    progress: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    current_step: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_steps: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    current_epoch: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    
    # Metrics
    train_loss: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    val_loss: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    metrics: Mapped[Dict] = mapped_column(JSONB, default=dict, nullable=False)
    
    # Evaluation
    eval_results: Mapped[Dict] = mapped_column(JSONB, default=dict, nullable=False)
    passed_evaluation: Mapped[Optional[bool]] = mapped_column(nullable=True)
    improvement_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Output
    output_dir: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    adapter_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    checkpoint_paths: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    
    # Logs
    log_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Timing
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Deployment
    deployed_model_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("model_registry.id", ondelete="SET NULL"), nullable=True
    )
    deployed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    metadata: Mapped[Dict] = mapped_column(JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    base_model: Mapped["ModelRegistry"] = relationship("ModelRegistry", foreign_keys=[base_model_id])
    deployed_model: Mapped[Optional["ModelRegistry"]] = relationship(
        "ModelRegistry", foreign_keys=[deployed_model_id]
    )

    __table_args__ = (
        Index("ix_training_runs_status_created", "status", "created_at"),
        Index("ix_training_runs_base_model", "base_model_id"),
    )

    def __repr__(self) -> str:
        return f"<TrainingRun(id={self.id}, name={self.name}, status={self.status})>"


class LoRAAdapter(Base):
    __tablename__ = "lora_adapters"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False, index=True)
    training_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("training_runs.id", ondelete="RESTRICT"), nullable=False
    )
    base_model_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("model_registry.id", ondelete="RESTRICT"), nullable=False
    )
    
    # Adapter config
    r: Mapped[int] = mapped_column(Integer, nullable=False)
    alpha: Mapped[int] = mapped_column(Integer, nullable=False)
    dropout: Mapped[float] = mapped_column(Float, nullable=False)
    target_modules: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    
    # Files
    adapter_path: Mapped[str] = mapped_column(String(500), nullable=False)
    config_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Performance
    eval_metrics: Mapped[Dict] = mapped_column(JSONB, default=dict, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=False, nullable=False)
    deployed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    metadata: Mapped[Dict] = mapped_column(JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    training_run: Mapped["TrainingRun"] = relationship("TrainingRun")
    base_model: Mapped["ModelRegistry"] = relationship("ModelRegistry")

    def __repr__(self) -> str:
        return f"<LoRAAdapter(name={self.name}, r={self.r}, alpha={self.alpha})>"