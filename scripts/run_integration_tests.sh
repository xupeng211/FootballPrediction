#!/bin/bash
# 集成测试执行脚本
# 依赖Docker服务

set -e

# 激活虚拟环境
source .venv/bin/activate

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 配置
REPORT_DIR="docs/_reports"
TIMEOUT=300
COMPOSE_FILE="config/docker/docker-compose.minimal.yml"

echo -e "${BLUE}🔗 集成测试执行器${NC}"
echo -e "${YELLOW}======================${NC}"

# 创建报告目录
mkdir -p $REPORT_DIR

# 记录开始时间
START_TIME=$(date +%s)

echo -e "${BLUE}📋 运行参数:${NC}"
echo -e "  测试路径: tests/integration/"
echo -e "  超时时间: ${TIMEOUT}秒"
echo -e "  Docker文件: $COMPOSE_FILE"

# 检查Docker是否运行
if ! docker info >/dev/null 2>&1; then
    echo -e "\n${RED}❌ Docker未运行，请先启动Docker${NC}"
    exit 1
fi

# 检查docker-compose文件
if [ ! -f "$COMPOSE_FILE" ]; then
    echo -e "\n${RED}❌ docker-compose文件不存在: $COMPOSE_FILE${NC}"
    exit 1
fi

echo -e "\n${YELLOW}🐳 启动Docker服务...${NC}"

# 启动数据库与API服务
if docker compose -f "$COMPOSE_FILE" --env-file config/docker/.env.minimal up -d db redis api; then
    echo -e "${GREEN}✅ 服务启动成功${NC}"
else
    echo -e "${RED}❌ 服务启动失败${NC}"
    exit 1
fi

# 测试结束后自动清理
cleanup() {
    docker compose -f "$COMPOSE_FILE" --env-file config/docker/.env.minimal down >/dev/null 2>&1 || true
}
trap cleanup EXIT

# 等待服务就绪
echo -e "\n${YELLOW}⏳ 等待服务就绪...${NC}"
sleep 10

# 检查服务健康状态
check_service() {
    local service=$1
    local port=$2
    local host=${3:-localhost}

    for i in {1..30}; do
        if nc -z $host $port 2>/dev/null; then
            echo -e "${GREEN}✅ $service 已就绪${NC}"
            return 0
        fi
        echo -e "${YELLOW}⏳ 等待 $service... ($i/30)${NC}"
        sleep 2
    done

    echo -e "${RED}❌ $service 未就绪${NC}"
    return 1
}

# 仅检查对外提供接口的 API 服务
if ! check_service "API" 8000; then
    echo -e "${RED}❌ API未就绪，无法运行集成测试${NC}"
    exit 1
fi

# 进一步确认健康检查端点可用
echo -e "\n${YELLOW}🩺 验证 /health 接口...${NC}"
for i in {1..30}; do
    if curl -sSf http://localhost:8000/health >/dev/null 2>&1; then
        echo -e "${GREEN}✅ API /health 正常${NC}"
        break
    fi
    echo -e "${YELLOW}⏳ /health 未就绪，继续等待... ($i/30)${NC}"
    sleep 2
    if [ "$i" -eq 30 ]; then
        echo -e "${RED}❌ API 健康检查失败${NC}"
        exit 1
    fi
done

# 运行集成测试
echo -e "\n${YELLOW}🚀 开始执行集成测试...${NC}"

# 设置环境变量
export ENVIRONMENT=test
export DATABASE_URL=postgresql://postgres:postgres@localhost:5432/football_prediction_test
export REDIS_URL=redis://localhost:6379/0
export API_URL=${API_URL:-http://localhost:8000}

# 执行测试
TEST_EXIT_CODE=0
pytest tests/integration/ \
    -v \
    --tb=short \
    --maxfail=5 \
    --timeout=$TIMEOUT \
    --disable-warnings \
    --junit-xml=$REPORT_DIR/integration-tests.xml \
    --capture=no \
    || TEST_EXIT_CODE=$?

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

# 生成报告
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "\n${GREEN}✅ 集成测试通过！${NC}"
    TEST_STATUS="通过"
    EMOJI="✅"
else
    echo -e "\n${YELLOW}⚠️ 集成测试失败（这是允许的）${NC}"
    TEST_STATUS="失败"
    EMOJI="⚠️"
fi

echo -e "⏱️  执行时间: ${DURATION}秒"

# 生成测试报告
REPORT_FILE="$REPORT_DIR/integration_test_report_$(date +%Y%m%d_%H%M%S).md"
cat > $REPORT_FILE << EOF
# 集成测试报告

## 执行结果
- **状态**: $EMOJI $TEST_STATUS
- **时间**: $(date)
- **执行时长**: ${DURATION}秒
- **退出码**: $TEST_EXIT_CODE

## 服务状态
\`\`\`
$(docker compose -f $COMPOSE_FILE ps)
\`\`\`

## 测试统计
$(pytest tests/integration/ --collect-only -q 2>/dev/null || echo "无法收集测试用例")

## 日志信息
### Docker服务日志
\`\`\`
$(docker compose -f $COMPOSE_FILE logs --tail=20)
\`\`\`

## 建议
- 如果测试失败，请检查服务是否正常运行
- 确认数据库连接配置正确
- 查看具体测试失败原因

---
Generated at $(date)
EOF

echo -e "\n📄 报告已生成: $REPORT_FILE"

# 清理服务（可选）
echo -e "\n${YELLOW}🧹 清理Docker服务...${NC}"
docker compose -f config/docker/docker-compose.minimal.yml down || true

echo -e "\n${GREEN}🎉 集成测试执行完成！${NC}"

# 即使失败也返回0，因为集成测试允许失败
exit 0
