#!/bin/bash
# NeuroSeek AI — One-Click Start Script
# Termux mein double-tap karo aur server start!

echo "🧠 NeuroSeek AI Server"
echo "====================="

# Check if server already running
if curl -s http://localhost:5000/api/health > /dev/null 2>&1; then
    echo "✅ Server already running!"
    echo "🌐 URL: http://localhost:5000"
    exit 0
fi

# Kill any existing server
pkill -f "python.*server" 2>/dev/null
sleep 1

# Start server
echo "⏳ Starting server..."
cd /home/quantarion/neuroseek-ai/backend/api

setsid nohup python -c "
import sys
sys.path.insert(0, '.')
from server import app
app.run(host='0.0.0.0', port=5000, debug=False)
" > /tmp/neuroseek.log 2>&1 &

# Wait for server to start
for i in {1..10}; do
    if curl -s http://localhost:5000/api/health > /dev/null 2>&1; then
        echo "✅ Server started successfully!"
        echo "🌐 URL: http://localhost:5000"
        echo "📋 Log: /tmp/neuroseek.log"
        exit 0
    fi
    sleep 1
done

echo "❌ Server failed to start"
echo "📋 Check log: cat /tmp/neuroseek.log"
exit 1
