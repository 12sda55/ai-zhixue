#!/usr/bin/env bash
set -e

echo "============================================"
echo "   AI 多智能体个性化学习系统 - 一键启动"
echo "============================================"
echo ""

# 检查 Python
if ! command -v python3 &>/dev/null; then
    echo "[错误] 未检测到 Python3，请先安装 Python 3.10+"
    exit 1
fi

# 检查 Node.js
if ! command -v node &>/dev/null; then
    echo "[错误] 未检测到 Node.js，请先安装 Node.js 18+"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# 检查后端 .env
if [ ! -f "$SCRIPT_DIR/backend/.env" ]; then
    echo "[提示] 后端 .env 不存在，从 .env.example 复制..."
    cp "$SCRIPT_DIR/backend/.env.example" "$SCRIPT_DIR/backend/.env"
    echo "      请编辑 backend/.env 填入 API Key 后重新启动"
    echo ""
fi

# 检查前端依赖
if [ ! -d "$SCRIPT_DIR/frontend/node_modules" ]; then
    echo "[提示] 前端依赖未安装，正在安装..."
    cd "$SCRIPT_DIR/frontend"
    npm install
fi

# 启动后端
echo "[1/3] 启动后端服务 (端口 8000)..."
cd "$SCRIPT_DIR/backend"
python3 run.py &
BACKEND_PID=$!
echo "      后端服务已启动 (PID: $BACKEND_PID)"

sleep 3

# 启动 AI Tutor（可选）
echo "[2/3] 启动 AI Tutor 服务 (端口 8001，可选)..."
if [ -f "$SCRIPT_DIR/ai-tutor/app/main.py" ] && [ -f "$SCRIPT_DIR/ai-tutor/.env" ]; then
    cd "$SCRIPT_DIR/ai-tutor"
    python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8001 &
    TUTOR_PID=$!
    echo "      AI Tutor 服务已启动 (PID: $TUTOR_PID)"
else
    echo "[跳过] ai-tutor 未配置，视频生成功能不可用"
fi

# 启动前端
echo "[3/3] 启动前端开发服务 (端口 5173)..."
cd "$SCRIPT_DIR/frontend"
npm run dev &
FRONTEND_PID=$!
echo "      前端开发服务已启动 (PID: $FRONTEND_PID)"

echo ""
echo "============================================"
echo " 启动完成！请稍等几秒后访问:"
echo ""
echo "   http://localhost:5173"
echo ""
echo " 默认账号（首次启动自动创建）:"
echo "   管理员: admin / admin123"
echo "   学生:   student1 / 123456"
echo ""
echo " 按 Ctrl+C 停止所有服务"
echo "============================================"

# 等待任意子进程退出
wait
