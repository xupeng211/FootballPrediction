#!/bin/bash
# 端到端（E2E）测试执行脚本

set -euo pipefail

source .venv/bin/activate

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

REPORT_DIR="docs/_reports"
TIMEOUT=600
COMPOSE_FILE="config/docker/docker-compose.minimal.yml"

mkdir -p "$REPORT_DIR"

START_TIME=$(date +%s)

echo -e "${BLUE}🚀 启动 E2E 测试流程${NC}"

echo -e "${BLUE}📋 运行参数:${NC}"
echo -e "  测试路径: tests/e2e/"
echo -e "  超时时间: ${TIMEOUT} 秒"
echo -e "  Docker 文件: $COMPOSE_FILE"

if ! docker info >/dev/null 2>&1; then
    echo -e "\n${RED}❌ Docker 未运行，请先启动 Docker${NC}"
    exit 1
fi

if [ ! -f "$COMPOSE_FILE" ]; then
    echo -e "\n${RED}❌ docker-compose 文件不存在: $COMPOSE_FILE${NC}"
    exit 1
fi

echo -e "\n${YELLOW}🐳 启动依赖服务...${NC}"
if docker compose -f "$COMPOSE_FILE" --env-file config/docker/.env.minimal up -d db redis api; then
    echo -e "${GREEN}✅ 服务启动成功${NC}"
else
    echo -e "${RED}❌ 服务启动失败${NC}"
    exit 1
fi

cleanup() {
    docker compose -f "$COMPOSE_FILE" --env-file config/docker/.env.minimal down >/dev/null 2>&1 || true
}
trap cleanup EXIT

check_service() {
    local service=$1
    local port=$2
    local host=${3:-localhost}

    for i in {1..60}; do
        if nc -z "$host" "$port" 2>/dev/null; then
            echo -e "${GREEN}✅ $service 已就绪${NC}"
            return 0
        fi
        echo -e "${YELLOW}⏳ 等待 $service... ($i/60)${NC}"
        sleep 2
    done

    echo -e "${RED}❌ $service 未就绪${NC}"
    return 1
}

echo -e "\n${YELLOW}⏳ 检查服务健康...${NC}"
check_service "PostgreSQL" 5432 || echo -e "${YELLOW}⚠️ PostgreSQL 未就绪，继续尝试...${NC}"
check_service "Redis" 6379 || echo -e "${YELLOW}⚠️ Redis 未就绪，继续尝试...${NC}"
if ! check_service "API" 8000; then
    echo -e "${RED}❌ API 服务未就绪，终止 E2E 测试${NC}"
    exit 1
fi

echo -e "\n${YELLOW}🩺 检查 API /health 接口...${NC}"
for i in {1..30}; do
    if curl -sSf http://localhost:8000/health >/dev/null 2>&1; then
        echo -e "${GREEN}✅ API /health 正常${NC}"
        break
    fi
    echo -e "${YELLOW}⏳ API /health 未就绪，继续等待... ($i/30)${NC}"
    sleep 2
    if [ "$i" -eq 30 ]; then
        echo -e "${RED}❌ API /health 检查失败${NC}"
        exit 1
    fi
done

echo -e "\n${YELLOW}🚀 执行 E2E 测试...${NC}"
export ENVIRONMENT=test
export DATABASE_URL=postgresql://postgres:postgres@localhost:5432/football_prediction_test
export REDIS_URL=redis://localhost:6379/0
export API_URL=${API_URL:-http://localhost:8000}

TEST_EXIT_CODE=0
pytest tests/e2e/ \
    -v \
    --tb=short \
    --maxfail=3 \
    --timeout=$TIMEOUT \
    --disable-warnings \
    --junit-xml=$REPORT_DIR/e2e-tests.xml \
    --capture=no \
    || TEST_EXIT_CODE=$?

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "\n${GREEN}✅ E2E 测试全部通过${NC}"
    STATUS_LABEL="通过"
    STATUS_EMOJI="✅"
else
    echo -e "\n${YELLOW}⚠️ E2E 测试出现失败${NC}"
    STATUS_LABEL="失败"
    STATUS_EMOJI="⚠️"
fi

echo -e "${YELLOW}⏱️ 测试耗时:${NC} ${DURATION} 秒"

REPORT_FILE="$REPORT_DIR/e2e_test_report_$(date +%Y%m%d_%H%M%S).md"
cat > "$REPORT_FILE" <<REPORT
# E2E 测试报告

- **状态**: $STATUS_EMOJI $STATUS_LABEL
- **时间**: $(date)
- **耗时**: ${DURATION} 秒
- **退出码**: $TEST_EXIT_CODE

## 服务状态
\`\`\`
docker compose -f $COMPOSE_FILE ps
\`\`\`

## 收集的测试
\`\`\`
pytest tests/e2e/ --collect-only -q 2>/dev/null
\`\`\`
REPORT

exit $TEST_EXIT_CODE
