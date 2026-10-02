# NeuroSeek AI - Self-Improving Multi-Model Intelligence

A fully local, privacy-first AI assistant that routes queries to the best model, learns from interactions, and continuously improves via LoRA fine-tuning.

## 🏗 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        NeuroSeek AI                              │
├─────────────────────────────────────────────────────────────────┤
│  Frontend (Next.js + TypeScript)                                │
│  ├─ Chat Interface (ChatGPT-like)                               │
│  ├─ Model Management Dashboard                                  │
│  ├─ Training Monitor                                            │
│  └─ Analytics / Evaluation                                      │
├─────────────────────────────────────────────────────────────────┤
│  Backend (FastAPI + Python)                                     │
│  ├─ API Gateway                                                 │
│  ├─ Model Router (Smart routing + Ensemble)                     │
│  ├─ Inference Engine (Ollama + llama.cpp)                       │
│  ├─ Training Pipeline (LoRA/QLoRA via Unsloth)                  │
│  ├─ Data Curator (RLHF-style preference learning)               │
│  └─ Evaluation Framework                                        │
├─────────────────────────────────────────────────────────────────┤
│  Infrastructure                                                 │
│  ├─ Ollama (Model serving)                                      │
│  ├─ PostgreSQL + pgvector (Conversations, embeddings)           │
│  ├─ Redis (Caching, job queues)                                 │
│  ├─ MinIO / Local FS (Model checkpoints, datasets)              │
│  └─ Docker Compose / Kubernetes                                 │
└─────────────────────────────────────────────────────────────────┘
```

## ✨ Features

- **Multi-Model Inference**: Route to best model per query type (coding, reasoning, creative, etc.)
- **Ensemble Voting**: Send to multiple models, synthesize best answer
- **Continuous LoRA Training**: Automatic fine-tuning from user feedback
- **RLHF Pipeline**: Collect preferences → Reward model → PPO/LoRA
- **Local-First**: Zero external API calls, full privacy
- **Model Zoo Management**: Auto-download, quantize, benchmark models
- **ChatGPT-like UI**: Streaming, branching, artifacts, code execution

## 🚀 Quick Start

```bash
# Clone and enter
git clone https://github.com/yourusername/neuroseek-ai
cd neuroseek-ai

# Start infrastructure
docker compose up -d postgres redis minio ollama

# Install backend
cd backend
pip install -e ".[dev,training]"

# Install frontend
cd ../frontend
npm install

# Run development
# Terminal 1: Backend
cd backend && uvicorn app.main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend && npm run dev

# Terminal 3: Ollama (pull models)
ollama pull llama3.1:8b
ollama pull qwen2.5-coder:7b
ollama pull nemotron3-ultra:latest
```

## 📁 Project Structure

```
neuroseek-ai/
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── api/            # REST endpoints
│   │   ├── core/           # Config, security, database
│   │   ├── models/         # SQLAlchemy models
│   │   ├── schemas/        # Pydantic schemas
│   │   ├── services/       # Business logic
│   │   │   ├── inference/  # Model inference
│   │   │   ├── routing/    # Smart model routing
│   │   │   ├── training/   # LoRA/QLoRA training
│   │   │   ├── evaluation/ # Model evaluation
│   │   │   └── data/       # Data curation
│   │   ├── workers/        # Background jobs (Celery)
│   │   └── main.py
│   ├── tests/
│   ├── pyproject.toml
│   └── Dockerfile
├── frontend/                # Next.js frontend
│   ├── src/
│   │   ├── app/            # App router pages
│   │   ├── components/     # React components
│   │   ├── hooks/          # Custom hooks
│   │   ├── lib/            # Utilities, API client
│   │   ├── stores/         # Zustand stores
│   │   └── types/          # TypeScript types
│   ├── package.json
│   └── Dockerfile
├── infrastructure/          # Docker, K8s, scripts
│   ├── docker-compose.yml
│   ├── kubernetes/
│   └── scripts/
├── models/                  # Model configs, LoRA adapters
│   ├── registry.yaml       # Model registry
│   └── adapters/           # Trained LoRA weights
└── docs/
```

## 🧠 Self-Improvement Loop

```
User Query
    │
    ▼
┌─────────────────────┐
│  Smart Router       │──→ Selects best model(s) for query type
│  (Intent + History) │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  Inference Engine   │──→ Parallel inference (single or ensemble)
│  (Ollama/llama.cpp) │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  Response Synthesis │──→ Best answer + confidence + citations
│  (Judgment LLM)     │
└─────────┬───────────┘
          │
          ▼
    User Feedback 👍/👎 / Edit / Regenerate
          │
          ▼
┌─────────────────────┐
│  Data Curator       │──→ Builds preference pairs (chosen vs rejected)
│  (RLHF Dataset)     │
└─────────┬───────────┘
          │
          ▼ (async, batched)
┌─────────────────────┐
│  Training Pipeline  │──→ LoRA/QLoRA on chosen model
│  (Unsloth + PEFT)   │     Uses preference pairs + SFT data
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  Evaluation Gate    │──→ Benchmark vs base model
│  (Auto-eval)        │     Deploy if improved
└─────────┬───────────┘
          │
          ▼
    Updated Model → Ollama Registry
```

## 🎯 Model Registry (Default)

| Model | Size | Role | Quantization |
|-------|------|------|--------------|
| `llama3.1:8b` | 8B | General chat, reasoning | Q4_K_M |
| `qwen2.5-coder:7b` | 7B | Code generation, debugging | Q4_K_M |
| `nemotron3-ultra` | 70B | Complex reasoning, synthesis | Q4_K_M |
| `phi3.5:3.8b` | 3.8B | Fast routing, classification | Q4_K_M |
| `deepseek-r1:7b` | 7B | Step-by-step reasoning | Q4_K_M |
| `llama3.1:8b-instruct` | 8B | **Training target** (LoRA) | Q4_K_M |

## ⚙️ Configuration

```yaml
# backend/config.yaml
inference:
  ollama_host: "http://ollama:11434"
  default_model: "llama3.1:8b"
  ensemble_models: ["llama3.1:8b", "qwen2.5-coder:7b", "nemotron3-ultra"]
  timeout: 120
  max_parallel: 3

routing:
  enabled: true
  intent_classifier: "phi3.5:3.8b"
  rules:
    coding: ["qwen2.5-coder:7b", "deepseek-coder:6.7b"]
    reasoning: ["deepseek-r1:7b", "nemotron3-ultra"]
    creative: ["llama3.1:8b", "nemotron3-ultra"]
    fast: ["phi3.5:3.8b"]

training:
  enabled: true
  method: "qlora"  # qlora, lora, full
  base_model: "llama3.1:8b-instruct"
  trigger:
    min_samples: 100
    min_improvement: 0.02
  lora:
    r: 64
    alpha: 128
    dropout: 0.05
    target_modules: ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]
  unsloth:
    max_seq_length: 4096
    dtype: "bfloat16"
    load_in_4bit: true

evaluation:
  benchmarks: ["mt-bench", "humaneval", "gsm8k", "custom"]
  judge_model: "nemotron3-ultra"
  auto_deploy: true
```

## 🔬 Training Pipeline Details

### LoRA/QLoRA with Unsloth (2-5x faster)

```python
# backend/app/services/training/unsloth_trainer.py
from unsloth import FastLanguageModel
from trl import SFTTrainer, DPOTrainer

# Load 4-bit quantized model
model, tokenizer = FastLanguageModel.from_pretrained(
    "unsloth/llama-3.1-8b-instruct-bnb-4bit",
    max_seq_length=4096,
    dtype=None,  # Auto detect
    load_in_4bit=True,
)

# Add LoRA adapters
model = FastLanguageModel.get_peft_model(
    model,
    r=64,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    lora_alpha=128,
    lora_dropout=0.05,
    bias="none",
    use_gradient_checkpointing="unsloth",
    random_state=42,
)

# Train with SFT (supervised fine-tuning)
trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,
    train_dataset=dataset,
    dataset_text_field="text",
    max_seq_length=4096,
    args=TrainingArguments(...),
)

# Or DPO (Direct Preference Optimization) for RLHF
trainer = DPOTrainer(
    model=model,
    ref_model=ref_model,
    tokenizer=tokenizer,
    train_dataset=preference_dataset,
    args=DPOConfig(...),
)
```

### Automatic Training Trigger

```python
# backend/app/services/training/scheduler.py
async def check_training_trigger():
    """Check if enough new preference data for retraining"""
    new_samples = await db.count_new_preferences(since=last_training)
    if new_samples >= config.training.trigger.min_samples:
        # Prepare dataset
        dataset = await prepare_training_dataset()
        # Launch training job
        job_id = await training_queue.enqueue(train_lora, dataset)
        # Monitor and evaluate
        await monitor_training(job_id)
```

## 📊 API Endpoints

### Chat & Inference
```
POST   /api/v1/chat/completions        # Main chat endpoint (streaming)
POST   /api/v1/chat/ensemble           # Multi-model ensemble
GET    /api/v1/models                  # List available models
POST   /api/v1/models/pull             # Download new model
GET    /api/v1/models/{name}/info      # Model details
```

### Training & Improvement
```
POST   /api/v1/training/trigger        # Manual training trigger
GET    /api/v1/training/status         # Current training status
GET    /api/v1/training/history        # Past training runs
POST   /api/v1/training/evaluate       # Run evaluation
POST   /api/v1/training/deploy/{run_id} # Deploy adapter to Ollama
```

### Feedback & Data
```
POST   /api/v1/feedback                # Submit 👍/👎/edit
GET    /api/v1/conversations           # List conversations
GET    /api/v1/conversations/{id}      # Get conversation
POST   /api/v1/conversations/{id}/branch # Branch conversation
```

### Analytics
```
GET    /api/v1/analytics/model-performance
GET    /api/v1/analytics/routing-stats
GET    /api/v1/analytics/training-progress
```

## 🐳 Docker Compose (Production)

```yaml
# infrastructure/docker-compose.yml
version: '3.8'

services:
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: neuroseek
      POSTGRES_USER: neuroseek
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U neuroseek"]
      interval: 10s

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: ${MINIO_ROOT_USER}
      MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD}
    volumes:
      - minio_data:/data
    ports:
      - "9000:9000"
      - "9001:9001"

  ollama:
    image: ollama/ollama:latest
    volumes:
      - ollama_data:/root/.ollama
      - ./models:/models
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]

  backend:
    build: ../backend
    environment:
      - DATABASE_URL=postgresql://neuroseek:${POSTGRES_PASSWORD}@postgres:5432/neuroseek
      - REDIS_URL=redis://redis:6379/0
      - MINIO_ENDPOINT=minio:9000
      - OLLAMA_HOST=http://ollama:11434
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_started
      ollama:
        condition: service_started
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

  frontend:
    build: ../frontend
    ports:
      - "3000:3000"
    depends_on:
      - backend

  worker:
    build: ../backend
    command: celery -A app.workers.celery_app worker -l info -Q training,inference,evaluation
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

volumes:
  postgres_data:
  redis_data:
  minio_data:
  ollama_data:
```

## 🔧 Hardware Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| GPU VRAM | 12 GB (QLoRA 8B) | 24 GB+ (QLoRA 70B, full fine-tune) |
| System RAM | 16 GB | 32-64 GB |
| Storage | 100 GB NVMe | 500 GB+ NVMe |
| CPU | 8 cores | 16+ cores |

### Model VRAM Requirements (4-bit QLoRA)
- 3.8B model: ~4 GB
- 7B model: ~6 GB
- 8B model: ~8 GB
- 14B model: ~12 GB
- 32B model: ~20 GB
- 70B model: ~40 GB (needs multi-GPU or CPU offload)

## 📈 Monitoring & Observability

- **Prometheus + Grafana**: Metrics dashboards
- **Langfuse / LangSmith**: LLM observability (optional)
- **Custom Dashboard**: Training curves, model comparison, routing accuracy

## 🛡 Security & Privacy

- **Zero Telemetry**: No data leaves your infrastructure
- **Local Models**: All inference on your hardware
- **Encrypted Storage**: pgvector + MinIO encryption at rest
- **Auth**: JWT + API keys for multi-user deployments

## 🤝 Contributing

1. Fork the repo
2. Create feature branch
3. Run tests: `pytest` (backend) / `npm test` (frontend)
4. Submit PR

## 📄 License

MIT License - See LICENSE file

---

**Built with**: FastAPI, Next.js, Ollama, Unsloth, PEFT, pgvector, Redis, Docker