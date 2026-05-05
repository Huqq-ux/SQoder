#!/bin/bash
set -e

echo "=== Coder Agent 部署脚本 ==="

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
DEPLOY_DIR="/opt/coder-agent"

echo "=== 1. 停止旧服务 ==="
sudo systemctl stop coder 2>/dev/null || true

echo "=== 2. 同步代码 ==="
sudo mkdir -p "$DEPLOY_DIR/Coder"
sudo cp -r "$PROJECT_DIR/Coder" "$DEPLOY_DIR/"
sudo cp -r "$PROJECT_DIR/model" "$DEPLOY_DIR/"
sudo cp "$PROJECT_DIR/pyproject.toml" "$DEPLOY_DIR/"

echo "=== 3. 搭建 Python 虚拟环境 ==="
cd "$DEPLOY_DIR"
uv venv
uv pip install -r <(uv pip compile pyproject.toml 2>/dev/null || echo "langchain langchain-openai langchain-core langgraph pydantic fastapi uvicorn[standard] python-multipart streamlit psutil mcp sentence-transformers faiss-cpu huggingface-hub langchain-community langchain-huggingface")

echo "=== 4. 配置环境变量 ==="
if [ ! -f "$DEPLOY_DIR/.env" ]; then
    echo "创建 .env 文件，请编辑填入 DASHSCOPE_API_KEY"
    sudo cp "$PROJECT_DIR/deploy/.env.example" "$DEPLOY_DIR/.env"
    echo "⚠️ 请编辑 $DEPLOY_DIR/.env 填入你的 DASHSCOPE_API_KEY"
fi

echo "=== 5. 构建前端 ==="
cd "$PROJECT_DIR/web"
npm install
npm run build
sudo mkdir -p "$DEPLOY_DIR/static"
sudo cp -r "$PROJECT_DIR/web/dist/"* "$DEPLOY_DIR/static/"

echo "=== 6. 设置权限 ==="
sudo mkdir -p "$DEPLOY_DIR/.cache"
sudo chown -R www-data:www-data "$DEPLOY_DIR"

echo "=== 7. 安装 systemd 服务 ==="
sudo cp "$PROJECT_DIR/deploy/coder.service" /etc/systemd/system/coder.service
sudo systemctl daemon-reload
sudo systemctl enable coder

echo "=== 8. 安装 Nginx 配置 ==="
sudo cp "$PROJECT_DIR/deploy/nginx-coder.conf" /etc/nginx/sites-available/coder
sudo ln -sf /etc/nginx/sites-available/coder /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx

echo "=== 9. 启动服务 ==="
sudo systemctl start coder

echo ""
echo "=== 部署完成 ==="
echo "后端服务状态: sudo systemctl status coder"
echo "后端日志: sudo journalctl -u coder -f"
echo "Nginx 日志: sudo tail -f /var/log/nginx/access.log"
echo "请确保已设置 DASHSCOPE_API_KEY 在 $DEPLOY_DIR/.env 中"
