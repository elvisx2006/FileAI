#!/bin/bash
# FileAI — 双击此文件启动应用
cd "$(dirname "$0")"

# 如果 8000 端口已占用，先关闭（避免第二个 uvicorn 因 Errno 48 退出）
lsof -ti :8000 | xargs kill -9 2>/dev/null
sleep 0.3

# 激活虚拟环境并启动后端
source backend/venv/bin/activate
python run_server.py &
BACKEND_PID=$!

# 等待后端就绪
echo "正在启动 FileAI..."
for i in {1..20}; do
    if curl -s http://127.0.0.1:8000/api/health > /dev/null 2>&1; then
        break
    fi
    sleep 0.5
done

# 打开浏览器
open http://127.0.0.1:8000
echo "FileAI 已启动: http://127.0.0.1:8000"
echo "按 Ctrl+C 停止"

# 等待后端进程
wait $BACKEND_PID
