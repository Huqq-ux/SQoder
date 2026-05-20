#!/bin/bash
# ============================================================
# Coder Agent - Docker 服务器端一键部署脚本
# 用法:
#   全新部署:   ./deploy/docker-deploy.sh
#   清数据重来: ./deploy/docker-deploy.sh --reset
#   仅重启:     ./deploy/docker-deploy.sh --restart
# ============================================================
set -e

# --- 配置 ------------------------------------------------
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEPLOY_DIR="$PROJECT_DIR/deploy"
COMPOSE_FILE="$DEPLOY_DIR/docker-compose.yml"
ENV_FILE="$PROJECT_DIR/.env"

cd "$PROJECT_DIR"

# --- 解析参数 --------------------------------------------
 RESET_DATA=false
 RESTART_ONLY=false
 NO_CACHE=false
 for arg in "$@"; do
     case $arg in
         --reset)   RESET_DATA=true ;;
         --restart) RESTART_ONLY=true ;;
         --rebuild) NO_CACHE=true ;;
         --help)
             echo "用法: $0 [--reset|--restart|--rebuild]"
             echo "  无参数     增量构建（利用缓存，中断后可续传）"
             echo "  --rebuild  强制从头构建（相当于旧版的 --no-cache）"
             echo "  --reset    清空所有数据卷，从头开始"
             echo "  --restart  仅重启容器，不重新构建"
             exit 0
             ;;
     esac
 done

# --- 0. 环境检查 ----------------------------------------
echo "=============================================="
echo "  Coder Agent Docker 部署"
echo "=============================================="

if ! command -v docker &>/dev/null; then
    echo "[错误] 未安装 Docker，请先安装"
    exit 1
fi

if ! docker compose version &>/dev/null 2>&1; then
    echo "[错误] 需要 docker compose 插件，请升级 Docker"
    exit 1
fi

# --- 1. 检查前端构建产物 ---------------------------------
if [ ! -d "$PROJECT_DIR/web/dist" ]; then
    echo "=============================================="
    echo "[警告] 未找到 web/dist/ 前端构建产物"
    echo "Nginx 容器将无法提供前端页面"
    echo "请先在本地执行: cd web && npm run build"
    echo "=============================================="
fi

# --- 2. 创建 .env ---------------------------------------
if [ ! -f "$ENV_FILE" ]; then
    if [ -f "$DEPLOY_DIR/.env.example" ]; then
        cp "$DEPLOY_DIR/.env.example" "$ENV_FILE"
        echo "[提示] 已从 .env.example 创建 .env 文件"
        echo "请编辑 $ENV_FILE 填入你的 DEEPSEEK_API_KEY 等配置"
        echo ""
    else
        cat > "$ENV_FILE" << 'EOF'
DEEPSEEK_API_KEY=your_api_key_here
HF_ENDPOINT=https://hf-mirror.com
HF_HOME=/opt/Coder/.cache/huggingface
DATABASE_URL=postgresql://coder:coder123@localhost:5432/coder_db
REDIS_URL=redis://localhost:6379/0
EOF
        echo "[提示] 已生成默认 .env 文件，请编辑填入 API Key"
        echo ""
    fi
fi

# 检查 API Key 是否已配置
if grep -q "your_api_key_here" "$ENV_FILE" 2>/dev/null; then
    echo "=============================================="
    echo "[警告] .env 中的 DEEPSEEK_API_KEY 尚未配置"
    echo "请编辑 $ENV_FILE 填入真实 API Key"
    echo "=============================================="
fi

# --- 3. 停止旧容器 ---------------------------------------
echo "[1/4] 停止旧容器..."

# 也尝试停掉旧版 systemd 服务（如果有的话），避免端口冲突
sudo systemctl stop coder 2>/dev/null || true
sudo systemctl stop nginx 2>/dev/null || true

DOWN_FLAGS=""
if [ "$RESET_DATA" = true ]; then
    echo "  → 同时清空数据卷 (--reset)"
    DOWN_FLAGS="-v"
fi

if [ "$RESTART_ONLY" = true ]; then
    echo "  → 仅重启模式，跳过构建"
    docker compose -f "$COMPOSE_FILE" down 2>/dev/null || true
else
    docker compose -f "$COMPOSE_FILE" down $DOWN_FLAGS 2>/dev/null || true
fi

# --- 4. 构建镜像 -----------------------------------------
if [ "$RESTART_ONLY" = false ]; then
    if [ "$NO_CACHE" = true ]; then
        echo "[2/4] 强制从头构建镜像..."
        docker compose -f "$COMPOSE_FILE" build --no-cache
    else
        echo "[2/4] 增量构建镜像（利用缓存，中断后可续传）..."
        docker compose -f "$COMPOSE_FILE" build
    fi
else
    echo "[2/4] 跳过构建"
fi

# --- 5. 启动服务 -----------------------------------------
echo "[3/4] 启动服务..."
docker compose -f "$COMPOSE_FILE" up -d

# --- 6. 等待健康检查 --------------------------------------
echo "[4/4] 等待服务就绪..."
ATTEMPTS=0
MAX_ATTEMPTS=30
while [ $ATTEMPTS -lt $MAX_ATTEMPTS ]; do
    if docker compose -f "$COMPOSE_FILE" ps | grep -q "unhealthy\|starting"; then
        sleep 2
        ATTEMPTS=$((ATTEMPTS + 1))
    else
        break
    fi
done

echo ""
echo "=============================================="
echo "  部署完成！"
echo "=============================================="
echo ""
echo "  服务状态:"
docker compose -f "$COMPOSE_FILE" ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"
echo ""
echo "  访问地址: http://$(hostname -I 2>/dev/null | awk '{print $1}' || echo '服务器IP')"
echo ""
echo "  查看日志: docker compose -f $COMPOSE_FILE logs -f"
echo "  查看状态: docker compose -f $COMPOSE_FILE ps"
echo "  停止服务: docker compose -f $COMPOSE_FILE down"
echo "  彻底清理: docker compose -f $COMPOSE_FILE down -v"
echo ""
