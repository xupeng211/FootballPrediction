#!/bin/bash

# 停止测试环境脚本
set -e

echo "🛑 停止足球预测测试环境..."

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 检查docker-compose文件是否存在
if [ ! -f "docker-compose.test.yml" ]; then
    echo -e "${RED}❌ 找不到 docker-compose.test.yml 文件${NC}"
    exit 1
fi

# 停止并移除容器
echo -e "${YELLOW}📦 停止测试容器...${NC}"
docker-compose -f docker-compose.test.yml down

# 询问是否删除数据卷
read -p "是否删除测试数据？(y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}🗑️ 删除测试数据卷...${NC}"
    docker-compose -f docker-compose.test.yml down -v
    echo -e "${GREEN}✅ 测试数据已删除${NC}"
fi

# 清理测试配置文件
if [ -f ".env.test" ]; then
    read -p "是否删除 .env.test 配置文件？(y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm .env.test
        echo -e "${GREEN}✅ .env.test 已删除${NC}"
    fi
fi

# 清理临时文件
rm -rf logs/test/* 2>/dev/null || true
rm -rf data/test/* 2>/dev/null || true

echo -e "\n${GREEN}✅ 测试环境已停止${NC}"
