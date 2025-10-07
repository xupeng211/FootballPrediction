#!/bin/bash
# 启动测试服务脚本
# 启动PostgreSQL和Redis服务用于测试

set -e

# 颜色定义
GREEN='\033[32m'
YELLOW='\033[33m'
RED='\033[31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}🚀 启动测试服务...${NC}"

# 检查Docker是否运行
if ! docker info >/dev/null 2>&1; then
    echo -e "${RED}❌ Docker未运行，请先启动Docker${NC}"
    exit 1
fi

# 检查docker-compose是否存在
if ! command -v docker-compose >/dev/null 2>&1; then
    echo -e "${RED}❌ docker-compose未安装${NC}"
    exit 1
fi

# 进入项目根目录
cd "$(dirname "$0")/../.."

# 启动PostgreSQL和Redis服务
echo -e "${YELLOW}📦 启动PostgreSQL和Redis服务...${NC}"
docker-compose up -d db redis

# 等待服务启动
echo -e "${YELLOW}⏳ 等待服务启动...${NC}"
sleep 10

# 检查服务状态
echo -e "${YELLOW}🔍 检查服务状态...${NC}"
docker-compose ps db redis

# 测试PostgreSQL连接
echo -e "${YELLOW}🧪 测试PostgreSQL连接...${NC}"
max_attempts=30
attempt=0

while [ $attempt -lt $max_attempts ]; do
    if docker-compose exec -T db pg_isready -U postgres >/dev/null 2>&1; then
        echo -e "${GREEN}✅ PostgreSQL连接成功${NC}"
        break
    fi

    attempt=$((attempt + 1))
    echo -e "${YELLOW}等待PostgreSQL启动... (${attempt}/${max_attempts})${NC}"
    sleep 2
done

if [ $attempt -eq $max_attempts ]; then
    echo -e "${RED}❌ PostgreSQL启动失败${NC}"
    exit 1
fi

# 测试Redis连接
echo -e "${YELLOW}🧪 测试Redis连接...${NC}"
# 获取Redis密码
REDIS_PASSWORD=$(grep REDIS_PASSWORD .env 2>/dev/null | cut -d'=' -f2 || echo "redis_password")
if docker-compose exec -T redis redis-cli -a "${REDIS_PASSWORD}" ping >/dev/null 2>&1; then
    echo -e "${GREEN}✅ Redis连接成功${NC}"
else
    echo -e "${RED}❌ Redis连接失败${NC}"
    exit 1
fi

# 设置环境变量
echo -e "${YELLOW}🔧 设置环境变量...${NC}"
export DOCKER_COMPOSE_ACTIVE=1
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/football_prediction_dev"
export TEST_DATABASE_URL="postgresql://postgres:postgres@localhost:5432/football_prediction_dev"

# 从.env文件获取Redis密码
REDIS_PASSWORD=$(grep REDIS_PASSWORD .env 2>/dev/null | cut -d'=' -f2 || echo "redis_password")
export REDIS_URL="redis://:${REDIS_PASSWORD}@localhost:6379/1"
export TEST_REDIS_URL="redis://:${REDIS_PASSWORD}@localhost:6379/1"
export TESTING=true
export ENVIRONMENT=test

# 创建.env.test文件
cat > .env.test << EOF
# 测试环境配置
DOCKER_COMPOSE_ACTIVE=1
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/football_prediction_dev
TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/football_prediction_dev
REDIS_URL=redis://:${REDIS_PASSWORD}@localhost:6379/1
TEST_REDIS_URL=redis://:${REDIS_PASSWORD}@localhost:6379/1
TESTING=true
ENVIRONMENT=test
LOG_LEVEL=DEBUG
EOF

echo -e "${GREEN}✅ 测试服务已成功启动${NC}"
echo -e "${GREEN}✅ 环境变量已设置${NC}"
echo -e "${GREEN}✅ .env.test文件已创建${NC}"
echo ""
echo -e "${YELLOW}现在可以运行:${NC}"
echo -e "  make test.unit                    # 运行单元测试"
echo -e "  make test.integration              # 运行集成测试"
echo -e "  python -m pytest tests/unit/test_database_integration.py -v  # 运行数据库集成测试"
echo ""
echo -e "${YELLOW}停止服务:${NC}"
echo -e "  docker-compose down db redis"