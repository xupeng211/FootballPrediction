#!/bin/bash

# Phase 1 测试运行脚本
# 用于运行API模块的所有测试

set -e  # 遇到错误立即退出

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 开始运行 Phase 1 API 测试...${NC}"
echo "========================================="

# 激活虚拟环境
if [ -d ".venv" ]; then
    source .venv/bin/activate
    echo -e "${GREEN}✓ 虚拟环境已激活${NC}"
else
    echo -e "${RED}❌ 未找到虚拟环境 .venv${NC}"
    exit 1
fi

# 设置测试环境变量
export ENABLE_FEAST=false
export MINIMAL_HEALTH_MODE=false  # 加载所有API路由
export FAST_FAIL=false
export ENABLE_METRICS=false
export ENVIRONMENT=test
export TESTING=true
export REDIS_URL="redis://localhost:6379/0"  # 测试数据库
export DATABASE_URL="sqlite:///./test.db"   # SQLite测试数据库

echo -e "${BLUE}ℹ️  环境变量已设置${NC}"

# 检查Docker服务（可选）
if command -v docker-compose &> /dev/null; then
    if docker-compose ps | grep -q "Up"; then
        echo -e "${GREEN}✓ Docker服务正在运行${NC}"
    else
        echo -e "${YELLOW}⚠️  Docker服务未运行，某些测试可能失败${NC}"
    fi
fi

echo -e "${BLUE}📝 运行测试命令...${NC}"

# 运行测试
pytest \
    tests/unit/api/test_data.py \
    tests/unit/api/test_health.py \
    tests/unit/api/test_features.py \
    tests/unit/api/test_predictions_simple.py \
    -v \
    --cov=src/api \
    --cov-report=term-missing \
    --cov-report=html:htmlcov_phase1 \
    --tb=short \
    --maxfail=10 \
    -x

# 检查结果
if [ $? -eq 0 ]; then
    echo -e "${GREEN}🎉 所有测试通过！${NC}"
    echo -e "${BLUE}📊 覆盖率报告已生成: htmlcov_phase1/index.html${NC}"

    # 显示覆盖率摘要
    echo -e "${BLUE}📈 覆盖率摘要:${NC}"
    coverage report --include='src/api/*' --show-missing
else
    echo -e "${RED}❌ 测试失败，请检查错误信息${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Phase 1 测试完成！${NC}"
