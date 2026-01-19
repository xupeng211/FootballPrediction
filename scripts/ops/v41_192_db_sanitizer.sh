#!/bin/bash
#
# V41.192 "肃清与深挖" - 数据库环境彻底治理脚本
# ===================================================
#
# 功能：
#   1. 停止并禁用 WSL2 本地 PostgreSQL 服务
#   2. 清理 5432 端口占用
#   3. 验证 Docker 容器数据库连接
#
# Usage:
#   bash scripts/ops/v41_192_db_sanitizer.sh
#
# Author: V41.192 Infrastructure Team
# Date: 2026-01-19
# Version: V41.192 "肃清"
#

set -e

echo "========================================================================"
echo "V41.192 数据库环境彻底治理"
echo "========================================================================"
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# ============================================================================
# 步骤 1: 停止并禁用 PostgreSQL 服务
# ============================================================================

echo -e "${YELLOW}[步骤 1/4] 停止并禁用 PostgreSQL 服务${NC}"
echo "----------------------------------------"

# 尝试 systemctl
if command -v systemctl &> /dev/null; then
    echo "使用 systemctl 停止服务..."
    sudo systemctl stop postgresql 2>/dev/null || echo "  postgresql 已停止或不存在"
    sudo systemctl disable postgresql 2>/dev/null || echo "  postgresql 已禁用或不存在"
fi

# 尝试 service 命令
if command -v service &> /dev/null; then
    echo "使用 service 停止服务..."
    sudo service postgresql stop 2>/dev/null || echo "  postgresql 已停止或不存在"
fi

# 检查所有 PostgreSQL 相关进程
echo "检查 PostgreSQL 进程..."
PIDS=$(pgrep -f postgres || true)
if [ -n "$PIDS" ]; then
    echo "  发现 PostgreSQL 进程: $PIDS"
    echo "  正在终止..."
    sudo kill -9 $PIDS 2>/dev/null || true
    sleep 1
else
    echo "  ✓ 没有运行中的 PostgreSQL 进程"
fi

echo ""

# ============================================================================
# 步骤 2: 清理 5432 端口占用
# ============================================================================

echo -e "${YELLOW}[步骤 2/4] 清理 5432 端口占用${NC}"
echo "----------------------------------------"

# 检查端口占用
if command -v ss &> /dev/null; then
    PORT_INFO=$(ss -tlnp 2>/dev/null | grep :5432 || echo "")
elif command -v netstat &> /dev/null; then
    PORT_INFO=$(sudo netstat -tlnp 2>/dev/null | grep :5432 || echo "")
fi

if [ -n "$PORT_INFO" ]; then
    echo "  ⚠️  5432 端口被占用:"
    echo "$PORT_INFO"

    # 尝试提取 PID
    PID=$(echo "$PORT_INFO" | grep -oP 'pid=\K[0-9]+' || echo "")
    if [ -n "$PID" ]; then
        echo "  正在终止进程 $PID..."
        sudo kill -9 $PID 2>/dev/null || true
        sleep 1
    fi
else
    echo "  ✓ 5432 端口未被占用"
fi

# 再次检查
sleep 1
if command -v ss &> /dev/null; then
    REMAINING=$(ss -tlnp 2>/dev/null | grep :5432 || echo "")
else
    REMAINING=$(sudo netstat -tlnp 2>/dev/null | grep :5432 || echo "")
fi

if [ -n "$REMAINING" ]; then
    echo -e "${RED}  ❌ 5432 端口仍被占用，请手动检查${NC}"
    echo "$REMAINING"
else
    echo -e "${GREEN}  ✅ 5432 端口已释放${NC}"
fi

echo ""

# ============================================================================
# 步骤 3: 启动 Docker 数据库服务
# ============================================================================

echo -e "${YELLOW}[步骤 3/4] 启动 Docker 数据库服务${NC}"
echo "----------------------------------------"

if ! docker ps &> /dev/null; then
    echo "  ⚠️  Docker 未运行，请先启动 Docker"
    exit 1
fi

cd /home/user/projects/FootballPrediction

# 启动数据库服务
echo "启动 db 服务..."
docker-compose up -d db 2>/dev/null || docker compose up -d db

# 等待数据库启动
echo "等待数据库启动..."
for i in {1..30}; do
    if docker exec football_db pg_isready -U football_user &> /dev/null; then
        echo -e "${GREEN}  ✅ 数据库已就绪${NC}"
        break
    fi
    sleep 1
done

echo ""

# ============================================================================
# 步骤 4: 验证连接
# ============================================================================

echo -e "${YELLOW}[步骤 4/4] 验证数据库连接${NC}"
echo "----------------------------------------"

# 测试连接
RESULT=$(docker exec football_db psql -U football_user -d football_db -tAc "SELECT 1" 2>/dev/null || echo "")

if [ "$RESULT" = "1" ]; then
    echo -e "${GREEN}  ✅ 数据库连接成功${NC}"

    # 显示数据库信息
    MATCH_COUNT=$(docker exec football_db psql -U football_user -d football_db -tAc "SELECT COUNT(*) FROM matches" 2>/dev/null || echo "N/A")
    ODDS_COUNT=$(docker exec football_db psql -U football_user -d football_db -tAc "SELECT COUNT(*) FROM odds" 2>/dev/null || echo "N/A")

    echo "  数据库统计:"
    echo "    - matches 表: $MATCH_COUNT 行"
    echo "    - odds 表: $ODDS_COUNT 行"
else
    echo -e "${RED}  ❌ 数据库连接失败${NC}"
    exit 1
fi

echo ""
echo "========================================================================"
echo -e "${GREEN}V41.192 治理完成！${NC}"
echo "========================================================================"
echo ""
echo "下一步: 运行数据采集验证"
echo "  python scripts/ops/v41_192_opening_ripper.py"
echo ""
