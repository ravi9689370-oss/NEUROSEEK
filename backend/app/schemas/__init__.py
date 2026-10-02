"""Pydantic schemas for API requests/responses."""
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


# Base schemas
class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# User schemas
class UserBase(BaseSchema):
    email: str
    full_name: Optional[str] = None


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)


class UserUpdate(BaseSchema):
    full_name: Optional[str] = None
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    id: UUID
    is_active: bool
    is_superuser: bool
    created_at: datetime
    last_login: Optional[datetime] = None


class UserWithAPIKeys(UserResponse):
    api_keys: List["APIKeyResponse"] = []


# API Key schemas
class APIKeyBase(BaseSchema):
    name: str


class APIKeyCreate(APIKeyBase):
    expires_days: Optional[int] = None


class APIKeyResponse(APIKeyBase):
    id: UUID
    key_prefix: str
    is_active: bool
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    created_at: datetime


class APIKeyWithSecret(APIKeyResponse):
    secret: str  # Only returned on creation


# Auth schemas
class Token(BaseSchema):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseSchema):
    sub: str
    exp: int
    type: str


class LoginRequest(BaseSchema):
    email: str
    password: str


class RefreshRequest(BaseSchema):
    refresh_token: str


# Conversation schemas
class ConversationBase(BaseSchema):
    title: Optional[str] = None
    system_prompt: Optional[str] = None
    model_used: Optional[str] = None
    metadata: Dict[str, Any] = {}


class ConversationCreate(ConversationBase):
    pass


class ConversationUpdate(BaseSchema):
    title: Optional[str] = None
    system_prompt: Optional[str] = None
    is_archived: Optional[bool] = None
    is_pinned: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None


class ConversationResponse(ConversationBase):
    id: UUID
    user_id: Optional[UUID] = None
    routing_intent: Optional[str] = None
    is_archived: bool
    is_pinned: bool
    created_at: datetime
    updated_at: datetime
    message_count: int = 0


class ConversationDetail(ConversationResponse):
    messages: List["MessageResponse"] = []


# Message schemas
class MessageBase(BaseSchema):
    role: str
    content: str
    model: Optional[str] = None
    provider: Optional[str] = None


class MessageCreate(MessageBase):
    conversation_id: UUID
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    max_tokens: Optional[int] = None


class MessageUpdate(BaseSchema):
    content: Optional[str] = None
    feedback: Optional[str] = None
    feedback_note: Optional[str] = None


class MessageResponse(MessageBase):
    id: UUID
    conversation_id: UUID
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    generation_time_ms: Optional[int] = None
    time_to_first_token_ms: Optional[int] = None
    feedback: Optional[str] = None
    is_training_candidate: bool
    created_at: datetime
    metadata: Dict[str, Any] = {}


# Feedback schemas
class FeedbackRequest(BaseSchema):
    message_id: UUID
    feedback: str  # positive, negative, edited, regenerated
    feedback_note: Optional[str] = None
    edited_content: Optional[str] = None


# Model Registry schemas
class ModelRegistryBase(BaseSchema):
    name: str
    display_name: str
    model_type: str
    parameter_count: Optional[str] = None
    quantization: Optional[str] = None
    context_length: int = 4096
    source: str = "ollama"
    source_id: Optional[str] = None
    capabilities: List[str] = []
    supported_tasks: List[str] = []
    routing_priority: int = 100
    routing_tags: List[str] = []
    is_trainable: bool = True
    default_params: Dict[str, Any] = {}
    ollama_options: Dict[str, Any] = {}
    description: Optional[str] = None
    license: Optional[str] = None


class ModelRegistryCreate(ModelRegistryBase):
    pass


class ModelRegistryUpdate(BaseSchema):
    display_name: Optional[str] = None
    status: Optional[str] = None
    routing_priority: Optional[int] = None
    routing_tags: Optional[List[str]] = None
    is_trainable: Optional[bool] = None
    default_params: Optional[Dict[str, Any]] = None
    ollama_options: Optional[Dict[str, Any]] = None


class ModelRegistryResponse(ModelRegistryBase):
    id: UUID
    status: str
    avg_latency_ms: Optional[float] = None
    avg_throughput_tps: Optional[float] = None
    memory_usage_gb: Optional[float] = None
    base_model_id: Optional[UUID] = None
    lora_adapter_path: Optional[str] = None
    last_used_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


# Inference schemas
class ChatMessage(BaseSchema):
    role: str
    content: str


class ChatCompletionRequest(BaseSchema):
    messages: List[ChatMessage]
    model: Optional[str] = None
    temperature: Optional[float] = Field(default=0.7, ge=0, le=2)
    top_p: Optional[float] = Field(default=0.9, ge=0, le=1)
    top_k: Optional[int] = Field(default=40, ge=1)
    max_tokens: Optional[int] = Field(default=4096, ge=1)
    stream: bool = False
    use_ensemble: bool = False
    ensemble_models: Optional[List[str]] = None
    metadata: Dict[str, Any] = {}


class ChatCompletionChoice(BaseSchema):
    index: int
    message: ChatMessage
    finish_reason: str


class ChatCompletionUsage(BaseSchema):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatCompletionResponse(BaseSchema):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[ChatCompletionChoice]
    usage: ChatCompletionUsage
    routing_info: Optional[Dict[str, Any]] = None


class StreamingChatResponse(BaseSchema):
    id: str
    object: str = "chat.completion.chunk"
    created: int
    model: str
    choices: List[ChatCompletionChoice]


# Training schemas
class TrainingRunBase(BaseSchema):
    name: str
    description: Optional[str] = None
    method: str
    base_model_id: UUID
    hyperparameters: Dict[str, Any] = {}


class TrainingRunCreate(TrainingRunBase):
    pass


class TrainingRunUpdate(BaseSchema):
    name: Optional[str] = None
    description: Optional[str] = None


class TrainingRunResponse(TrainingRunBase):
    id: UUID
    status: str
    progress: float
    current_step: int
    total_steps: int
    current_epoch: float
    train_loss: Optional[float] = None
    val_loss: Optional[float] = None
    metrics: Dict[str, Any] = {}
    eval_results: Dict[str, Any] = {}
    passed_evaluation: Optional[bool] = None
    improvement_score: Optional[float] = None
    adapter_path: Optional[str] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    deployed_model_id: Optional[UUID] = None
    deployed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


# Evaluation schemas
class EvaluationRequest(BaseSchema):
    model_id: UUID
    benchmarks: Optional[List[str]] = None
    judge_model: Optional[str] = None


class EvaluationResponse(BaseSchema):
    model_id: UUID
    benchmark: str
    score: float
    details: Dict[str, Any]
    compared_to_base: Optional[float] = None
    improvement: Optional[float] = None


# Analytics schemas
class ModelPerformanceMetrics(BaseSchema):
    model: str
    total_requests: int
    avg_latency_ms: float
    avg_tokens_per_sec: float
    success_rate: float
    avg_feedback_score: float
    training_candidates: int


class RoutingStats(BaseSchema):
    intent: str
    count: int
    models_used: Dict[str, int]
    avg_latency_ms: float


class TrainingProgress(BaseSchema):
    run_id: UUID
    name: str
    status: str
    progress: float
    current_step: int
    total_steps: int
    train_loss: Optional[float] = None
    val_loss: Optional[float] = None
    estimated_time_remaining: Optional[int] = None


# Health check
class HealthResponse(BaseSchema):
    status: str
    version: str
    database: str
    redis: str
    ollama: str
    models_loaded: int