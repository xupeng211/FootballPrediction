#!/bin/bash

# 启动测试环境脚本
set -e

echo "🚀 启动足球预测测试环境..."

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 检查Docker是否运行
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker未运行，请先启动Docker${NC}"
    exit 1
fi

# 检查docker-compose是否存在
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ docker-compose未安装${NC}"
    exit 1
fi

# 停止可能存在的旧容器
echo -e "${YELLOW}📦 停止现有测试容器...${NC}"
docker-compose -f docker-compose.test.yml down -v 2>/dev/null || true

# 创建必要的目录
mkdir -p logs/test
mkdir -p data/test

# 启动基础服务（PostgreSQL和Redis）
echo -e "${YELLOW}🐘 启动PostgreSQL测试数据库...${NC}"
docker-compose -f docker-compose.test.yml up -d db

echo -e "${YELLOW}🔴 启动Redis测试缓存...${NC}"
docker-compose -f docker-compose.test.yml up -d redis

# 等待服务就绪
echo -e "${YELLOW}⏳ 等待服务启动...${NC}"
sleep 5

# 检查PostgreSQL
echo -e "${YELLOW}🔍 检查PostgreSQL连接...${NC}"
max_attempts=30
attempt=0

while [ $attempt -lt $max_attempts ]; do
    if docker-compose -f docker-compose.test.yml exec -T db pg_isready -U test_user -d football_test > /dev/null 2>&1; then
        echo -e "${GREEN}✅ PostgreSQL已就绪${NC}"
        break
    fi

    attempt=$((attempt + 1))
    if [ $attempt -eq $max_attempts ]; then
        echo -e "${RED}❌ PostgreSQL启动失败${NC}"
        docker-compose -f docker-compose.test.yml logs db
        exit 1
    fi

    sleep 1
done

# 检查Redis
echo -e "${YELLOW}🔍 检查Redis连接...${NC}"
if docker-compose -f docker-compose.test.yml exec -T redis redis-cli -a test_pass ping > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Redis已就绪${NC}"
else
    echo -e "${RED}❌ Redis启动失败${NC}"
    docker-compose -f docker-compose.test.yml logs redis
    exit 1
fi

# 启动可选服务（如果环境变量设置）
if [ "$INCLUDE_FULL_STACK" = "true" ]; then
    echo -e "${YELLOW}📊 启动MinIO存储服务...${NC}"
    docker-compose -f docker-compose.test.yml up -d minio-test

    echo -e "${YELLOW}🤖 启动MLflow服务...${NC}"
    docker-compose -f docker-compose.test.yml up -d mlflow-test

    echo -e "${YELLOW}📨 启动Kafka服务...${NC}"
    docker-compose -f docker-compose.test.yml up -d kafka-test zookeeper-test
fi

# 创建测试环境配置文件
echo -e "${YELLOW}📝 创建测试配置文件...${NC}"
cat > .env.test << EOF
# 测试环境配置
ENVIRONMENT=test
DEBUG=true
LOG_LEVEL=DEBUG

# 数据库配置（测试环境）
DATABASE_URL=postgresql+asyncpg://test_user:test_password@localhost:5433/football_test
DATABASE_HOST=localhost
DATABASE_PORT=5433
DATABASE_NAME=football_prediction_test
DATABASE_USER=test_user
DATABASE_PASSWORD=test_password

# 测试环境专用数据库配置（用于get_database_config函数）
TEST_DB_HOST=localhost
TEST_DB_PORT=5433
TEST_DB_NAME=football_test
TEST_DB_USER=test_user
TEST_DB_PASSWORD=test_pass

# Redis配置（测试环境）
REDIS_URL=redis://localhost:6380/0
REDIS_HOST=localhost
REDIS_PORT=6380
REDIS_DB=0

# MinIO配置（如果使用）
MINIO_ENDPOINT=localhost:9001
MINIO_ACCESS_KEY=test_access_key
MINIO_SECRET_KEY=test_secret_key
MINIO_BUCKET=test-data

# MLflow配置
MLFLOW_TRACKING_URI=http://localhost:5001

# Kafka配置（如果使用）
KAFKA_BOOTSTRAP_SERVERS=localhost:9093
KAFKA_TOPIC_PREFIX=test

# 测试配置
TEST_DATABASE_URL=postgresql+asyncpg://test_user:test_password@localhost:5433/football_test
TEST_REDIS_URL=redis://localhost:6380/0

# 其他配置
SECRET_KEY=test-secret-key-for-testing-only
JWT_SECRET_KEY=test-jwt-secret-key-for-testing-only
API_PREFIX=/api/v1
CORS_ORIGINS=http://localhost:3000,http://localhost:8080

# 性能配置（测试环境优化）
DATABASE_POOL_SIZE=5
DATABASE_MAX_OVERFLOW=10
REDIS_POOL_SIZE=10
EOF

echo -e "${GREEN}✅ 测试环境配置已保存到 .env.test${NC}"

# 显示服务状态
echo -e "\n${GREEN}🎉 测试环境启动成功！${NC}"
echo -e "${YELLOW}📋 服务状态：${NC}"
docker-compose -f docker-compose.test.yml ps

echo -e "\n${YELLOW}📝 使用说明：${NC}"
echo "1. 加载测试环境: source .env.test"
echo "2. 运行测试: pytest tests/"
echo "3. 停止环境: docker-compose -f docker-compose.test.yml down"
echo "4. 查看日志: docker-compose -f docker-compose.test.yml logs [service-name]"

echo -e "\n${YELLOW}🔗 服务端点：${NC}"
echo "- PostgreSQL: localhost:5433"
echo "- Redis: localhost:6380"
if [ "$INCLUDE_FULL_STACK" = "true" ]; then
    echo "- MinIO: http://localhost:9001"
    echo "- MLflow: http://localhost:5001"
    echo "- Kafka: localhost:9093"
fi

echo -e "\n${GREEN}✨ 环境已准备就绪，可以开始测试！${NC}"
