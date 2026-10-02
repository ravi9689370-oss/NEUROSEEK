"""Conversation and message models."""
import enum
import uuid
from datetime import datetime, timezone
from typing import Optional, List

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    DateTime, String, Text, Integer, Float, ForeignKey, Enum, Index, JSON
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base


class MessageRole(str, enum.Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class MessageFeedback(str, enum.Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    EDITED = "edited"
    REGENERATED = "regenerated"


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    system_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    model_used: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    routing_intent: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    is_archived: Mapped[bool] = mapped_column(default=False, nullable=False)
    is_pinned: Mapped[bool] = mapped_column(default=False, nullable=False)
    metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
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
    user: Mapped[Optional["User"]] = relationship("User", back_populates="conversations")
    messages: Mapped[List["Message"]] = relationship(
        "Message", back_populates="conversation", lazy="selectin", order_by="Message.created_at"
    )
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True
    )
    branch_from_message_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("messages.id", ondelete="SET NULL"), nullable=True
    )

    __table_args__ = (
        Index("ix_conversations_user_updated", "user_id", "updated_at"),
        Index("ix_conversations_parent", "parent_id"),
    )

    def __repr__(self) -> str:
        return f"<Conversation(id={self.id}, title={self.title})>"


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[MessageRole] = mapped_column(Enum(MessageRole), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    provider: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # ollama, llama.cpp
    
    # Token usage
    prompt_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Generation params
    temperature: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    top_p: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    max_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Timing
    generation_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    time_to_first_token_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Feedback & Training
    feedback: Mapped[Optional[MessageFeedback]] = mapped_column(
        Enum(MessageFeedback), nullable=True, index=True
    )
    feedback_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_training_candidate: Mapped[bool] = mapped_column(default=False, nullable=False)
    training_weight: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    
    # Embedding for semantic search
    embedding: Mapped[Optional[List[float]]] = mapped_column(Vector(384), nullable=True)
    
    # Metadata
    metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="messages")

    __table_args__ = (
        Index("ix_messages_conv_created", "conversation_id", "created_at"),
        Index("ix_messages_feedback", "feedback"),
        Index("ix_messages_training", "is_training_candidate", "feedback"),
    )

    def __repr__(self) -> str:
        return f"<Message(id={self.id}, role={self.role}, conv={self.conversation_id})>"