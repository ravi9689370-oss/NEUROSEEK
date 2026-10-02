# NeuroSeek AI - Deployment Guide

## Quick Start (Docker)

### Prerequisites
- Docker & Docker Compose
- NVIDIA GPU with drivers (for GPU acceleration)
- 16GB+ RAM recommended
- 50GB+ free disk space

### One-Command Deploy
```bash
# Clone and enter
git clone https://github.com/yourusername/neuroseek-ai
cd neuroseek-ai

# Set password
export POSTGRES_PASSWORD="your_secure_password_here"

# Start all services
docker compose -f docker-compose.simple.yml up -d

# Pull default models (run once)
docker exec neuroseek-ollama ollama pull llama3.1:8b
docker exec neuroseek-ollama ollama pull qwen2.5-coder:7b
docker exec neuroseek-ollama ollama pull nemotron3-ultra
docker exec neuroseek-ollama ollama pull deepseek-r1:7b
docker exec neuroseek-ollama ollama pull phi3.5:3.8b

# Access
# Frontend: http://localhost:3000
# API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

## Android APK Build

### Prerequisites
- Node.js 20+
- Android Studio (for SDK)
- Java 17+
- Gradle (wrapper included)

### Build APK
```bash
# Make script executable
chmod +x build-apk.sh

# Run build
./build-apk.sh

# Install on device
adb install neuroseek-ai-debug.apk

# Or transfer APK to phone and install manually
```

### Build Release APK
```bash
cd frontend/android
./gradlew assembleRelease
# APK at: app/build/outputs/apk/release/app-release.apk
```

## Manual Development Setup

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -e ".[dev,training]"
cp config.yaml.example config.yaml
# Edit config.yaml with your settings
uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
# Runs on http://localhost:3000
```

### Ollama Models
```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Pull models
ollama pull llama3.1:8b
ollama pull qwen2.5-coder:7b
ollama pull nemotron3-ultra
ollama pull deepseek-r1:7b
ollama pull phi3.5:3.8b
```

## Model Configuration

### Recommended Models by Use Case

| Task | Model | Size | VRAM (4-bit) |
|------|-------|------|--------------|
| General Chat | llama3.1:8b | 8B | ~8 GB |
| Coding | qwen2.5-coder:7b | 7B | ~6 GB |
| Reasoning | deepseek-r1:7b | 7B | ~6 GB |
| Complex Analysis | nemotron3-ultra | 70B | ~40 GB* |
| Fast/Routing | phi3.5:3.8b | 3.8B | ~4 GB |

*Requires 24GB+ VRAM or CPU offload

### Custom Models
Add to `backend/config.yaml`:
```yaml
inference:
  routing:
    rules:
      your_task:
        - "your-custom-model:tag"
```

## GPU Requirements

| Configuration | Min VRAM | Recommended |
|--------------|----------|-------------|
| 8B models only | 8 GB | 12 GB |
| 70B models (offload) | 16 GB | 24 GB |
| Training (QLoRA 8B) | 12 GB | 16 GB |
| Training (QLoRA 70B) | 24 GB | 48 GB |

## Environment Variables

### Backend (.env)
```bash
POSTGRES_PASSWORD=secure_password
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin
OLLAMA_HOST=http://ollama:11434
SECRET_KEY=your_very_long_random_secret_key_here
```

### Frontend (.env.local)
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_WS_URL=ws://localhost:8000/api/v1
```

## Production Deployment

### With Reverse Proxy (Nginx)
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### SSL with Let's Encrypt
```bash
certbot --nginx -d your-domain.com
```

## Monitoring

### Health Checks
```bash
# Backend
curl http://localhost:8000/api/v1/health

# Frontend
curl http://localhost:3000

# Ollama
curl http://localhost:11434/api/tags
```

### Logs
```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f backend
docker compose logs -f ollama
```

## Backup & Restore

### Database Backup
```bash
docker exec neuroseek-postgres pg_dump -U neuroseek neuroseek > backup.sql
```

### Restore
```bash
docker exec -i neuroseek-postgres psql -U neuroseek neuroseek < backup.sql
```

### Model Data
```bash
# Backup Ollama models
docker run --rm -v neuroseek_ollama_data:/data -v $(pwd):/backup alpine tar czf /backup/ollama-backup.tar.gz -C /data .

# Restore
docker run --rm -v neuroseek_ollama_data:/data -v $(pwd):/backup alpine tar xzf /backup/ollama-backup.tar.gz -C /data
```

## Troubleshooting

### Common Issues

**Ollama not downloading models**
```bash
# Check logs
docker logs neuroseek-ollama

# Increase timeout
docker exec neuroseek-ollama ollama pull llama3.1:8b --timeout 30m
```

**Out of memory**
```bash
# Reduce parallel models in docker-compose.yml
OLLAMA_NUM_PARALLEL: "1"
OLLAMA_MAX_LOADED_MODELS: "1"
```

**Database connection failed**
```bash
# Check postgres is healthy
docker compose ps
docker logs neuroseek-postgres
```

**GPU not detected**
```bash
# Verify nvidia-docker
docker run --rm --gpus all nvidia/cuda:12.0-base nvidia-smi
```

## Scaling

### Horizontal Scaling
```yaml
# In docker-compose.yml
deploy:
  replicas: 3
  resources:
    limits:
      cpus: '2'
      memory: 4G
```

### Model Serving Separation
Run Ollama on dedicated GPU server:
```bash
# On GPU server
docker run -d --gpus all -p 11434:11434 -v ollama_data:/root/.ollama ollama/ollama

# In config.yaml
ollama:
  host: "http://gpu-server:11434"
```

## Security Checklist

- [ ] Change default POSTGRES_PASSWORD
- [ ] Change MINIO credentials
- [ ] Generate strong SECRET_KEY
- [ ] Enable HTTPS in production
- [ ] Configure firewall rules
- [ ] Disable debug mode
- [ ] Set up automated backups
- [ ] Configure log rotation
- [ ] Set up monitoring alerts

## Support

- GitHub Issues: https://github.com/yourusername/neuroseek-ai/issues
- Documentation: https://neuroseek.ai/docs
- Discord: https://discord.gg/neuroseek