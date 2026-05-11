#!/bin/bash
set -e
echo "=== Coder Agent Docker 部署 ==="

# 停止旧服务
systemctl stop coder 2>/dev/null || true
systemctl stop nginx 2>/dev/null || true

# 创建部署目录
mkdir -p /opt/coder-docker
cd /opt/coder-docker

# 确保前端已构建（如果没有，从 scp 上传的 dist 中复制）
if [ ! -d "web/dist" ]; then
    echo "前端构建产物未找到，请确保 web/dist/ 已上传"
fi

# 创建 .env（如果不存在）
if [ ! -f ".env" ]; then
    echo "DASHSCOPE_API_KEY=your_api_key_here" > .env
    echo "请编辑 .env 填入 DASHSCOPE_API_KEY"
fi

# 构建并启动
docker compose -f deploy/docker-compose.yml down 2>/dev/null || true
docker compose -f deploy/docker-compose.yml build --no-cache
docker compose -f deploy/docker-compose.yml up -d

echo ""
echo "=== 部署完成 ==="
echo "查看日志: docker compose -f /opt/coder-docker/deploy/docker-compose.yml logs -f"
echo "访问: http://服务器IP"
