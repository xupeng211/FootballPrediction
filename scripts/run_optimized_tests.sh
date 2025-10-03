#!/bin/bash
# 优化的测试运行脚本

set -e

# 激活虚拟环境
source .venv/bin/activate

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "${YELLOW}🚀 开始运行测试套件...${NC}"

# 1. 先运行单元测试
echo "${YELLOW}📋 运行单元测试...${NC}"
if pytest tests/unit/ -v --maxfail=5 --timeout=60 --disable-warnings --cov=src --cov-report=term-missing --cov-report=json; then
    echo "${GREEN}✅ 单元测试通过${NC}"
else
    echo "${RED}❌ 单元测试失败${NC}"
    exit 1
fi

# 2. 检查服务状态
echo "${YELLOW}🔍 检查服务状态...${NC}"
if docker compose ps >/dev/null 2>&1; then
    echo "${GREEN}✅ Docker服务可用${NC}"

    # 3. 运行集成测试
    echo "${YELLOW}🔗 运行集成测试...${NC}"
    if pytest tests/integration/ -v --maxfail=3 --timeout=120 --disable-warnings; then
        echo "${GREEN}✅ 集成测试通过${NC}"
    else
        echo "${YELLOW}⚠️  集成测试失败（可能需要启动服务）${NC}"
    fi
else
    echo "${YELLOW}⚠️  Docker服务未运行，跳过集成测试${NC}"
fi

# 4. 生成覆盖率报告
echo "${YELLOW}📊 生成覆盖率报告...${NC}"
if [ -f "coverage.json" ]; then
    python scripts/run_tests_with_report.py
    echo "${GREEN}✅ 覆盖率报告已生成${NC}"
else
    echo "${YELLOW}⚠️  覆盖率数据不存在${NC}"
fi

echo "${GREEN}🎉 测试完成！${NC}"
