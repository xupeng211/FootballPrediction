#!/bin/bash

# Docker CI 完整测试脚本 - 在 Docker 容器中完全模拟 GitHub Actions CI 环境
# 目标：在本地 Docker 环境中暴露和修复所有 CI 问题

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# 打印状态函数
print_status() {
    local status=$1
    local message=$2
    if [ "$status" = "success" ]; then
        echo -e "${GREEN}✅ $message${NC}"
    elif [ "$status" = "error" ]; then
        echo -e "${RED}❌ $message${NC}"
    elif [ "$status" = "info" ]; then
        echo -e "${BLUE}ℹ️  $message${NC}"
    elif [ "$status" = "warning" ]; then
        echo -e "${YELLOW}⚠️  $message${NC}"
    elif [ "$status" = "debug" ]; then
        echo -e "${PURPLE}🔍 $message${NC}"
    fi
}

# 错误处理函数
handle_error() {
    local step=$1
    print_status "error" "Docker CI 测试失败: $step"
    print_status "error" "请在 Docker 环境中修复此问题后再推送代码"
    exit 1
}

echo -e "${BLUE}🐳 Docker CI 完整测试开始${NC}"
echo "=================================="

# Step 0: 检查 Docker 环境
print_status "info" "步骤 0/5: 检查 Docker 环境"
if ! command -v docker &> /dev/null; then
    handle_error "Docker 未安装"
fi

if ! command -v docker-compose &> /dev/null; then
    handle_error "Docker Compose 未安装"
fi

print_status "success" "Docker 环境检查通过"

# Step 1: 启动 Docker 服务
print_status "info" "步骤 1/5: 启动 Docker 服务环境"

# 清理旧容器
echo "清理旧的 Docker 容器..."
docker-compose -f docker-compose.test.yml down --remove-orphans 2>/dev/null || true

# 启动服务
echo "启动 PostgreSQL、Redis、Kafka 服务..."
docker-compose -f docker-compose.test.yml up -d

# 等待服务启动
echo "等待服务启动..."
sleep 10

# 检查服务状态
echo "检查服务健康状态..."
if ! docker-compose -f docker-compose.test.yml ps | grep -q "Up"; then
    handle_error "Docker 服务启动失败"
fi

print_status "success" "Docker 服务启动完成"

# Step 2: 在 Docker 中运行单元测试
print_status "info" "步骤 2/5: 在 Docker 中运行单元测试 (模拟 unit-fast)"

# 创建临时容器进行测试
echo "运行单元测试..."
docker run --rm \
    --network football_test_network \
    -v "$(pwd):/app" \
    -w /app \
    -e ENVIRONMENT=test \
    python:3.11-slim \
    bash -c "
        apt-get update && apt-get install -y gcc g++ libpq-dev && \
        python -m venv .venv && \
        source .venv/bin/activate && \
        pip install --upgrade pip && \
        pip install -r requirements.txt && \
        pip install -r requirements-dev.txt && \
        make test-quick
    " || handle_error "单元测试在 Docker 中失败"

print_status "success" "单元测试在 Docker 中通过"

# Step 3: 在 Docker 中准备数据库
print_status "info" "步骤 3/5: 在 Docker 中准备数据库 (模拟 integration-tests)"

# 运行数据库准备脚本
echo "准备数据库 schema 和种子数据..."
docker run --rm \
    --network football_test_network \
    -v "$(pwd):/app" \
    -w /app \
    -e ENVIRONMENT=test \
    -e TEST_DB_HOST=db \
    -e TEST_DB_PORT=5432 \
    -e TEST_DB_NAME=football_prediction_test \
    -e TEST_DB_USER=postgres \
    -e TEST_DB_PASSWORD=postgres \
    python:3.11-slim \
    bash -c "
        apt-get update && apt-get install -y gcc g++ libpq-dev && \
        python -m venv .venv && \
        source .venv/bin/activate && \
        pip install --upgrade pip && \
        pip install -r requirements.txt && \
        pip install -r requirements-dev.txt && \
        python scripts/prepare_test_db.py
    " || handle_error "数据库准备在 Docker 中失败"

print_status "success" "数据库准备在 Docker 中完成"

# Step 4: 在 Docker 中运行集成测试
print_status "info" "步骤 4/5: 在 Docker 中运行集成测试"

echo "运行集成测试..."
docker run --rm \
    --network football_test_network \
    -v "$(pwd):/app" \
    -w /app \
    -e ENVIRONMENT=test \
    -e TEST_DB_HOST=db \
    -e TEST_DB_PORT=5432 \
    -e TEST_DB_NAME=football_prediction_test \
    -e TEST_DB_USER=postgres \
    -e TEST_DB_PASSWORD=postgres \
    -e REDIS_URL=redis://redis:6379/0 \
    -e KAFKA_BOOTSTRAP_SERVERS=kafka:9092 \
    python:3.11-slim \
    bash -c "
        apt-get update && apt-get install -y gcc g++ libpq-dev && \
        python -m venv .venv && \
        source .venv/bin/activate && \
        pip install --upgrade pip && \
        pip install -r requirements.txt && \
        pip install -r requirements-dev.txt && \
        pytest tests/integration/ -v --tb=short
    " || handle_error "集成测试在 Docker 中失败"

print_status "success" "集成测试在 Docker 中通过"

# Step 5: 在 Docker 中运行慢速测试
print_status "info" "步骤 5/5: 在 Docker 中运行慢速测试 (模拟 slow-suite)"

echo "运行慢速测试..."
docker run --rm \
    --network football_test_network \
    -v "$(pwd):/app" \
    -w /app \
    -e ENVIRONMENT=test \
    -e TEST_DB_HOST=db \
    -e TEST_DB_PORT=5432 \
    -e TEST_DB_NAME=football_prediction_test \
    -e TEST_DB_USER=postgres \
    -e TEST_DB_PASSWORD=postgres \
    -e REDIS_URL=redis://redis:6379/0 \
    -e KAFKA_BOOTSTRAP_SERVERS=kafka:9092 \
    python:3.11-slim \
    bash -c "
        apt-get update && apt-get install -y gcc g++ libpq-dev && \
        python -m venv .venv && \
        source .venv/bin/activate && \
        pip install --upgrade pip && \
        pip install -r requirements.txt && \
        pip install -r requirements-dev.txt && \
        pytest tests/unit/ -m 'slow' -v --tb=short --timeout=30
    " || handle_error "慢速测试在 Docker 中失败"

print_status "success" "慢速测试在 Docker 中通过"

# 清理
echo "清理 Docker 容器..."
docker-compose -f docker-compose.test.yml down

echo ""
echo -e "${GREEN}🎉 Docker CI 完整测试成功！${NC}"
echo -e "${GREEN}✅ 所有测试在 Docker 环境中通过${NC}"
echo -e "${BLUE}📋 测试结果:${NC}"
echo "  - 单元测试: ✅ 通过"
echo "  - 数据库准备: ✅ 通过"
echo "  - 集成测试: ✅ 通过"
echo "  - 慢速测试: ✅ 通过"
echo ""
echo -e "${GREEN}🚀 现在可以安全地推送代码到 GitHub！${NC}"
