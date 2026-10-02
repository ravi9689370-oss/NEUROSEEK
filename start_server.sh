#!/bin/bash
# NeuroSeek AI Server Startup Script
# Termux band hone ke baad bhi app chalta rahe

echo "🧠 NeuroSeek AI Server Starting..."

# Server start karo
cd /home/quantarion/neuroseek-ai/backend/api

# Agar server pehle se chal raha hai toh band karo
pkill -f "python -c" 2>/dev/null
sleep 1

# Server start karo
setsid nohup python -c "
import sys
sys.path.insert(0, '.')
from server import app
app.run(host='0.0.0.0', port=5000, debug=False)
" > /tmp/neuroseek.log 2>&1 &

sleep 3

# Health check
if curl -s http://localhost:5000/api/health > /dev/null 2>&1; then
    echo "✅ Server started successfully!"
    echo "🌐 URL: http://localhost:5000"
else
    echo "❌ Server failed to start"
    echo "📋 Log: /tmp/neuroseek.log"
fi
