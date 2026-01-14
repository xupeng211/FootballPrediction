#!/bin/bash
# V41.52: 端口冲突诊断与修复脚本
# ====================================
# 用途: 诊断并修复 localhost:5432 端口冲突
# 问题: 本地 PostgreSQL 占用了端口，导致连接到空数据库

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  V41.52: 端口冲突诊断与修复脚本${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""

# ========================================
# 1. 诊断阶段
# ========================================

echo -e "${YELLOW}[诊断 1/4] Docker 容器状态${NC}"
if docker-compose ps db | grep -q "Up"; then
    echo -e "${GREEN}✅${NC} Docker 数据库容器运行正常"
    docker-compose ps db
else
    echo -e "${RED}❌${NC} Docker 数据库容器未运行"
    echo "请执行: make up"
    exit 1
fi
echo ""

echo -e "${YELLOW}[诊断 2/4] Docker 数据库验证${NC}"
DOCKER_TABLE_COUNT=$(docker-compose exec -T db psql -U football_user -d football_db -t -c "
    SELECT COUNT(*) FROM information_schema.tables
    WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
" | tr -d ' ')
echo -e "${GREEN}✅${NC} Docker 内数据库: $DOCKER_TABLE_COUNT 张表"

if [ "$DOCKER_TABLE_COUNT" -ge 10 ]; then
    echo -e "${GREEN}✅${NC} Docker 数据库健康（真实数据库）"
else
    echo -e "${RED}❌${NC} Docker 数据库异常（表数量过少）"
fi
echo ""

echo -e "${YELLOW}[诊断 3/4] localhost 连接测试${NC}"
python3 -c "
import psycopg2
try:
    conn = psycopg2.connect(
        host='localhost',
        port=5432,
        database='football_db',
        user='football_user',
        password='football_pass',
        connect_timeout=3
    )
    cursor = conn.cursor()
    cursor.execute(\"\"\"
        SELECT COUNT(*) FROM information_schema.tables
        WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
    \"\"\")
    table_count = cursor.fetchone()[0]
    conn.close()
    print(f'localhost:5432: {table_count} 张表')
    if table_count == 0:
        print('⚠️  检测到空数据库（可能被其他 PostgreSQL 实例占用）')
except Exception as e:
    print(f'连接失败: {e}')
" 2>/dev/null || echo -e "${YELLOW}⚠️${NC} Python 测试不可用"
echo ""

echo -e "${YELLOW}[诊断 4/4] 端口占用检查${NC}"
if command -v ss >/dev/null 2>&1; then
    echo "5432 端口占用情况:"
    ss -tulpn | grep 5432 || echo "未检测到端口占用"
elif command -v netstat >/dev/null 2>&1; then
    echo "5432 端口占用情况:"
    netstat -tulpn | grep 5432 || echo "未检测到端口占用"
else
    echo -e "${YELLOW}⚠️${NC} ss/netstat 命令不可用"
fi
echo ""

# ========================================
# 2. 问题分析
# ========================================

echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  问题分析${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${RED}问题:${NC} localhost:5432 连接到空数据库（0 张表）"
echo -e "${RED}原因:${NC} 主机上可能运行着另一个 PostgreSQL 实例"
echo ""
echo -e "${GREEN}期望:${NC} localhost:5432 应连接到 Docker 容器内的真实数据库"
echo -e "${GREEN}状态:${NC} Docker 数据库有 $DOCKER_TABLE_COUNT 张表（健康）"
echo ""

# ========================================
# 3. 解决方案
# ========================================

echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  解决方案${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""

echo -e "${GREEN}[方案 1] 使用 Docker 内部连接（推荐）${NC}"
echo "    直接在 Docker 容器内运行收割，绕过 localhost 端口问题："
echo ""
echo -e "${YELLOW}    ./scripts/ops/v41_52_docker_harvest.sh \"Ligue 1\" \"23/24\"${NC}"
echo ""

echo -e "${GREEN}[方案 2] 查找并停止本地 PostgreSQL${NC}"
echo "    如果主机上运行着 PostgreSQL 服务，需要停止它："
echo ""
echo -e "    ${YELLOW}sudo systemctl stop postgresql${NC}    # Ubuntu/Debian"
echo -e "    ${YELLOW}sudo brew services stop postgresql${NC} # macOS (Homebrew)"
echo -e "    ${YELLOW}sudo service postgresql stop${NC}       # 通用方法"
echo ""

echo -e "${GREEN}[方案 3] 修改 Docker 端口映射${NC}"
echo "    将 Docker 端口映射改为其他端口（如 5433）："
echo ""
echo -e "    ${YELLOW}# 修改 docker-compose.yml:${NC}"
echo -e "    ${YELLOW}ports:${NC}"
echo -e "    ${YELLOW}  - \"5433:5432\"${NC}"
echo -e "    ${YELLOW}# 然后更新 .env: DB_PORT=5433${NC}"
echo ""

echo -e "${GREEN}[方案 4] 使用 Docker 网络直接连接${NC}"
echo "    通过 Docker 网络直接连接容器 IP："
echo ""
echo -e "    ${YELLOW}docker inspect football_prediction_db | grep IPAddress${NC}"
echo -e "    ${YELLOW}# 然后更新 .env: DB_HOST=172.20.0.x${NC}"
echo ""

# ========================================
# 4. 快速修复
# ========================================

echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  快速修复命令${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""

# 检测操作系统并提供相应的修复命令
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
else
    OS=$(uname -s)
fi

case "$OS" in
    ubuntu|debian)
        echo -e "${YELLOW}检测到 Ubuntu/Debian 系统${NC}"
        echo ""
        echo "停止本地 PostgreSQL 服务："
        echo "  ${GREEN}sudo systemctl stop postgresql${NC}"
        echo "  ${GREEN}sudo systemctl disable postgresql${NC}  # 禁止开机启动"
        echo ""
        ;;
    centos|rhel|fedora)
        echo -e "${YELLOW}检测到 CentOS/RHEL/Fedora 系统${NC}"
        echo ""
        echo "停止本地 PostgreSQL 服务："
        echo "  ${GREEN}sudo systemctl stop postgresql${NC}"
        echo "  ${GREEN}sudo systemctl disable postgresql${NC}"
        echo ""
        ;;
    darwin)
        echo -e "${YELLOW}检测到 macOS 系统${NC}"
        echo ""
        echo "停止本地 PostgreSQL 服务："
        echo "  ${GREEN}brew services stop postgresql${NC}"
        echo "  ${GREEN}brew services stop postgresql@14${NC}  # 指定版本"
        echo ""
        ;;
    *)
        echo -e "${YELLOW}未知操作系统类型${NC}"
        echo ""
        echo "通用方法停止 PostgreSQL："
        echo "  ${GREEN}sudo pkill -9 postgres${NC}"
        echo "  ${GREEN}sudo service postgresql stop${NC}"
        echo ""
        ;;
esac

echo "验证修复："
echo "  ${GREEN}python scripts/ops/v41_51_db_identity_check.py${NC}"
echo ""

echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""
