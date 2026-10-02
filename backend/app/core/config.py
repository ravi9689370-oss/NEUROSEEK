"""Application configuration using Pydantic Settings."""
import os
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

import yaml
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    name: str = "NeuroSeek AI"
    version: str = "0.1.0"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: List[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    api_prefix: str = "/api/v1"


class DatabaseSettings(BaseSettings):
    url: str = "postgresql+asyncpg://neuroseek:changeme@localhost:5432/neuroseek"
    pool_size: int = 20
    max_overflow: int = 10
    pool_timeout: int = 30
    echo: bool = False


class RedisSettings(BaseSettings):
    url: str = "redis://localhost:6379/0"
    max_connections: int = 50
    decode_responses: bool = True


class MinIOSettings(BaseSettings):
    endpoint: str = "localhost:9000"
    access_key: str = "minioadmin"
    secret_key: str = "minioadmin"
    secure: bool = False
    bucket: str = "neuroseek-models"


class OllamaSettings(BaseSettings):
    host: str = "http://localhost:11434"
    timeout: int = 120
    max_parallel: int = 3
    default_model: str = "llama3.1:8b"
    keep_alive: str = "5m"


class AuthSettings(BaseSettings):
    secret_key: str = "CHANGE_ME_IN_PRODUCTION_USE_STRONG_RANDOM_KEY"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440
    refresh_token_expire_days: int = 30


class RoutingRule(BaseSettings):
    models: List[str]


class InferenceSettings(BaseSettings):
    class RoutingSettings(BaseSettings):
        enabled: bool = True
        intent_classifier_model: str = "phi3.5:3.8b"
        classification_timeout: int = 5
        fallback_model: str = "llama3.1:8b"
        rules: dict = Field(default_factory=dict)

    class EnsembleSettings(BaseSettings):
        enabled: bool = True
        max_models: int = 3
        synthesis_model: str = "nemotron3-ultra"
        synthesis_prompt: str = ""
        voting_strategy: str = "weighted"
        weights: dict = Field(default_factory=dict)

    class GenerationSettings(BaseSettings):
        temperature: float = 0.7
        top_p: float = 0.9
        top_k: int = 40
        max_tokens: int = 4096
        repeat_penalty: float = 1.1
        stop_sequences: List[str] = Field(default_factory=list)

    routing: RoutingSettings = Field(default_factory=RoutingSettings)
    ensemble: EnsembleSettings = Field(default_factory=EnsembleSettings)
    generation: GenerationSettings = Field(default_factory=GenerationSettings)


class LoRASettings(BaseSettings):
    r: int = 64
    alpha: int = 128
    dropout: float = 0.05
    bias: str = "none"
    target_modules: List[str] = Field(default_factory=lambda: [
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj"
    ])
    task_type: str = "CAUSAL_LM"


class UnslothSettings(BaseSettings):
    max_seq_length: int = 4096
    dtype: str = "bfloat16"
    load_in_4bit: bool = True
    use_gradient_checkpointing: str = "unsloth"
    random_state: int = 42


class TrainerSettings(BaseSettings):
    per_device_train_batch_size: int = 2
    gradient_accumulation_steps: int = 4
    warmup_steps: int = 10
    max_steps: int = 100
    learning_rate: float = 2e-4
    weight_decay: float = 0.01
    lr_scheduler_type: str = "cosine"
    optim: str = "adamw_8bit"
    logging_steps: int = 5
    save_steps: int = 50
    eval_steps: int = 50
    fp16: bool = False
    bf16: bool = True
    gradient_checkpointing: bool = True
    dataloader_num_workers: int = 4
    remove_unused_columns: bool = False


class DPOSettings(BaseSettings):
    beta: float = 0.1
    loss_type: str = "sigmoid"
    max_prompt_length: int = 2048
    max_length: int = 4096
    reference_free: bool = False


class TrainingSettings(BaseSettings):
    enabled: bool = True
    method: str = "qlora"
    base_model: str = "unsloth/llama-3.1-8b-instruct-bnb-4bit"
    base_model_local: str = "llama3.1:8b-instruct"

    class TriggerSettings(BaseSettings):
        min_new_samples: int = 100
        min_improvement_threshold: float = 0.02
        max_training_frequency_hours: int = 24
        auto_trigger: bool = True

    trigger: TriggerSettings = Field(default_factory=TriggerSettings)
    lora: LoRASettings = Field(default_factory=LoRASettings)
    unsloth: UnslothSettings = Field(default_factory=UnslothSettings)
    trainer: TrainerSettings = Field(default_factory=TrainerSettings)
    dpo: DPOSettings = Field(default_factory=DPOSettings)


class EvaluationSettings(BaseSettings):
    enabled: bool = True
    judge_model: str = "nemotron3-ultra"
    benchmarks: List[str] = Field(default_factory=lambda: [
        "mt_bench", "humaneval", "gsm8k", "custom_eval"
    ])
    custom_eval_dataset: str = "data/eval/custom_eval.jsonl"
    auto_deploy: bool = True
    min_score_improvement: float = 0.02
    evaluation_timeout: int = 600


class DataCurationSettings(BaseSettings):
    min_conversation_length: int = 2
    max_conversation_age_days: int = 30
    preference_threshold: float = 0.7
    deduplication_threshold: float = 0.95


class DataSettings(BaseSettings):
    curation: DataCurationSettings = Field(default_factory=DataCurationSettings)
    splits: dict = Field(default_factory=lambda: {
        "train": 0.85, "validation": 0.10, "test": 0.05
    })


class PrometheusSettings(BaseSettings):
    enabled: bool = True
    port: int = 9090
    path: str = "/metrics"


class LoggingSettings(BaseSettings):
    level: str = "INFO"
    format: str = "json"
    file: str = "logs/neuroseek.log"


class LangfuseSettings(BaseSettings):
    enabled: bool = False
    public_key: str = ""
    secret_key: str = ""
    host: str = "https://cloud.langfuse.com"


class MonitoringSettings(BaseSettings):
    prometheus: PrometheusSettings = Field(default_factory=PrometheusSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    langfuse: LangfuseSettings = Field(default_factory=LangfuseSettings)


class CelerySettings(BaseSettings):
    broker_url: str = "redis://localhost:6379/1"
    result_backend: str = "redis://localhost:6379/2"
    task_serializer: str = "json"
    result_serializer: str = "json"
    accept_content: List[str] = Field(default_factory=lambda: ["json"])
    timezone: str = "UTC"
    enable_utc: bool = True
    task_routes: dict = Field(default_factory=dict)
    worker_prefetch_multiplier: int = 1
    task_acks_late: bool = True


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
    )

    app: AppSettings = Field(default_factory=AppSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    minio: MinIOSettings = Field(default_factory=MinIOSettings)
    ollama: OllamaSettings = Field(default_factory=OllamaSettings)
    auth: AuthSettings = Field(default_factory=AuthSettings)
    inference: InferenceSettings = Field(default_factory=InferenceSettings)
    training: TrainingSettings = Field(default_factory=TrainingSettings)
    evaluation: EvaluationSettings = Field(default_factory=EvaluationSettings)
    data: DataSettings = Field(default_factory=DataSettings)
    monitoring: MonitoringSettings = Field(default_factory=MonitoringSettings)
    celery: CelerySettings = Field(default_factory=CelerySettings)

    @classmethod
    def from_yaml(cls, path: str = "config.yaml") -> "Settings":
        """Load settings from YAML file, with env var overrides."""
        config_path = Path(path)
        if not config_path.is_absolute():
            config_path = Path(__file__).parent.parent.parent / path
        
        if config_path.exists():
            with open(config_path) as f:
                yaml_data = yaml.safe_load(f)
            return cls(**yaml_data)
        return cls()


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings.from_yaml()