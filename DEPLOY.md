# NeuroSeek AI — Deployment Guide

## 🚀 Termux Mein Start (Abhi ke liye)

```bash
bash /home/quantarion/neuroseek-ai/start.sh
```

## 🌐 Permanent Link (Render Par Deploy)

### Step 1: GitHub Upload
```bash
cd /home/quantarion/neuroseek-ai
git init
git add .
git commit -m "NeuroSeek AI"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/neuroseek-ai.git
git push -u origin main
```

### Step 2: Render Deploy
1. https://render.com par jao
2. Sign Up (GitHub se login)
3. New + → Web Service
4. Repo connect karo
5. Settings:
   - Name: neuroseek-ai
   - Runtime: Python
   - Build: `pip install -r requirements.txt`
   - Start: `gunicorn server:app --bind 0.0.0.0:$PORT`
6. Create Web Service

### Step 3: Link Lo
```
https://neuroseek-ai.onrender.com
```

## 📁 Files Ready For Deployment
- ✅ `Procfile` — Render/Railway ke liye
- ✅ `render.yaml` — Render blueprint
- ✅ `requirements.txt` — gunicorn added
- ✅ `start.sh` — Termux one-click start
