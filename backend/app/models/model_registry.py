"""Model registry and management models."""
import enum
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, List

from sqlalchemy import (
    DateTime, String, Text, Integer, Float, Boolean, Enum, Index, JSON
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base


class ModelType(str, enum.Enum):
    CHAT = "chat"
    CODING = "coding"
    REASONING = "reasoning"
    EMBEDDING = "embedding"
    ROUTER = "router"
    JUDGE = "judge"


class ModelStatus(str, enum.Enum):
    AVAILABLE = "available"
    DOWNLOADING = "downloading"
    LOADING = "loading"
    ACTIVE = "active"
    ERROR = "error"
    DEPRECATED = "deprecated"


class ModelRegistry(Base):
    __tablename__ = "model_registry"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    model_type: Mapped[ModelType] = mapped_column(Enum(ModelType), nullable=False, index=True)
    status: Mapped[ModelStatus] = mapped_column(Enum(ModelStatus), default=ModelStatus.AVAILABLE, nullable=False)
    
    # Model details
    parameter_count: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # "8B", "70B"
    quantization: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # "Q4_K_M", "bf16"
    context_length: Mapped[int] = mapped_column(Integer, default=4096, nullable=False)
    
    # Source
    source: Mapped[str] = mapped_column(String(50), default="ollama", nullable=False)  # ollama, huggingface, local
    source_id: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # HF repo, ollama tag
    local_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Capabilities
    capabilities: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    supported_tasks: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    
    # Performance metadata
    avg_latency_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    avg_throughput_tps: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    memory_usage_gb: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Routing
    routing_priority: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    routing_tags: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    
    # Training
    is_trainable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    base_model_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("model_registry.id", ondelete="SET NULL"), nullable=True
    )
    lora_adapter_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Config
    default_params: Mapped[Dict] = mapped_column(JSONB, default=dict, nullable=False)
    ollama_options: Mapped[Dict] = mapped_column(JSONB, default=dict, nullable=False)
    
    # Metadata
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    license: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
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
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Self-referential relationship for base model
    base_model: Mapped[Optional["ModelRegistry"]] = relationship(
        "ModelRegistry", remote_side=[id], backref="fine_tunes"
    )

    __table_args__ = (
        Index("ix_model_registry_type_status", "model_type", "status"),
        Index("ix_model_registry_routing", "routing_priority", "model_type"),
    )

    def __repr__(self) -> str:
        return f"<ModelRegistry(name={self.name}, type={self.model_type}, status={self.status})>"