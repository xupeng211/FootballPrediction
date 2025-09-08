#!/bin/bash

# CI 验证脚本 - 本地一键执行 CI 验证
# 确保本地环境与远程 CI 环境完全对齐

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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
    fi
}

# 错误处理函数
handle_error() {
    local step=$1
    print_status "error" "步骤失败: $step"
    echo -e "${RED}❌ CI 验证失败！请检查并修复问题后重试。${NC}"
    exit 1
}

echo -e "${BLUE}🚀 开始本地 CI 验证...${NC}"
echo "=========================================="

# Step 1: 清理并重建虚拟环境
print_status "info" "步骤 1/3: 清理并重建虚拟环境"
echo "清理旧的虚拟环境..."

if [ -d "venv" ]; then
    rm -rf venv
    print_status "success" "旧虚拟环境已清理"
else
    print_status "info" "未找到旧虚拟环境，跳过清理"
fi

echo "创建新的虚拟环境..."
python3 -m venv venv || handle_error "创建虚拟环境"
print_status "success" "虚拟环境创建成功"

echo "激活虚拟环境并安装依赖..."
source venv/bin/activate || handle_error "激活虚拟环境"

pip install --upgrade pip || handle_error "升级 pip"
pip install -r requirements.txt || handle_error "安装基础依赖"
pip install -r requirements-dev.txt || handle_error "安装开发依赖"
pip install -e . || handle_error "安装当前项目"

print_status "success" "依赖安装完成"

# Step 2: 启动 Docker Compose
print_status "info" "步骤 2/3: 启动 Docker Compose 环境"
echo "停止现有容器..."

docker-compose down || print_status "warning" "没有运行中的容器需要停止"

echo "构建并启动服务..."
docker-compose up --build -d || handle_error "启动 Docker Compose"

echo "等待服务就绪..."
sleep 10

echo "检查服务状态..."
docker-compose ps || handle_error "检查服务状态"

# 验证关键服务是否正常运行
if ! docker-compose ps | grep -q "Up"; then
    handle_error "部分服务启动失败"
fi

print_status "success" "Docker 环境启动成功"

# Step 3: 运行测试并验证覆盖率
print_status "info" "步骤 3/3: 运行测试并验证覆盖率"

echo "设置测试环境变量..."
export TEST_DB_HOST=localhost
export TEST_DB_PORT=5432
export TEST_DB_NAME=football_prediction_test
export TEST_DB_USER=postgres
export TEST_DB_PASSWORD=postgres
export ENVIRONMENT=test

echo "等待数据库就绪..."
max_attempts=30
attempt=0
while [ $attempt -lt $max_attempts ]; do
    if docker-compose exec db pg_isready -U postgres > /dev/null 2>&1; then
        break
    fi
    attempt=$((attempt + 1))
    sleep 2
done

if [ $attempt -eq $max_attempts ]; then
    handle_error "数据库启动超时"
fi

print_status "success" "数据库已就绪"

echo "激活虚拟环境并执行测试套件..."
source venv/bin/activate
export PYTHONPATH="$(pwd):${PYTHONPATH}"
pytest \
    --cov=core --cov=models --cov=services --cov=utils --cov=database --cov=api \
    --cov-fail-under=80 \
    --cov-report=xml \
    --cov-report=html \
    -v || handle_error "测试执行或覆盖率不足"

print_status "success" "测试执行完成，覆盖率达标"

# 最终成功信息
echo ""
echo "=========================================="
echo -e "${GREEN}🎉 CI 绿灯验证成功！本地环境与远程 CI 一致${NC}"
echo ""
echo -e "${BLUE}📊 验证报告:${NC}"
echo -e "  ✅ 虚拟环境: 重建成功"
echo -e "  ✅ Docker 环境: 启动正常"
echo -e "  ✅ 测试覆盖率: >= 78%"
echo -e "  ✅ 所有测试: 通过"
echo ""
echo -e "${GREEN}🚀 可以安全推送到远程仓库！${NC}"
echo "=========================================="
