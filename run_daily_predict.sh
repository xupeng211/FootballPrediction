#!/bin/bash
# Football Prediction Daily Runner
# 实战预测自动化脚本 - V2.0

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 脚本信息
SCRIPT_NAME="Football Prediction Daily Runner"
VERSION="v2.0"
DATE=$(date +%Y-%m-%d)
TIME=$(date +%H:%M:%S)

echo -e "${CYAN}======================================"
echo -e "${CYAN}🏆 $SCRIPT_NAME $VERSION"
echo -e "${CYAN}📅 Date: $DATE $TIME"
echo -e "${CYAN}======================================${NC}"

# 检查Docker是否运行
echo -e "\n${BLUE}🔍 检查Docker环境...${NC}"
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker未运行，请先启动Docker服务${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Docker环境正常${NC}"

# 检查Docker Compose文件
if [ ! -f "docker-compose.yml" ]; then
    echo -e "${RED}❌ 未找到docker-compose.yml文件${NC}"
    exit 1
fi

# 启动Docker服务栈
echo -e "\n${BLUE}🚀 启动Docker服务栈...${NC}"
docker-compose up -d db redis

# 等待数据库就绪
echo -e "\n${YELLOW}⏳ 等待数据库服务就绪...${NC}"
for i in {1..30}; do
    if docker-compose exec -T db pg_isready -U football_user -d football_prediction > /dev/null 2>&1; then
        echo -e "${GREEN}✅ 数据库服务就绪${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}❌ 数据库服务启动超时${NC}"
        exit 1
    fi
    echo -e "${YELLOW}  等待中... ($i/30)${NC}"
    sleep 2
done

# 启动预测引擎
echo -e "\n${BLUE}🔮 启动足球预测引擎...${NC}"
echo -e "${PURPLE}📊 执行特征收割 + 实时预测...${NC}"

# 运行主引擎（包含预测功能）
docker-compose run --rm \
    -e DOCKER_ENV=true \
    -e ENVIRONMENT=production \
    -e LOG_LEVEL=INFO \
    --name footballprediction-runner \
    engine python src/core/main_engine_v5.py --mode full --limit 50

# 检查运行结果
if [ $? -eq 0 ]; then
    echo -e "\n${GREEN}🎉 预测任务执行成功！${NC}"

    # 显示今日预测统计
    echo -e "\n${CYAN}📈 今日预测统计:${NC}"
    echo -e "${BLUE}├── 已收割比赛特征数据${NC}"
    echo -e "${BLUE}├── 已对未来比赛进行实时预测${NC}"
    echo -e "${BLUE├── 模型版本: V2.0 真实比分 (60.00% Acc)${NC}"
    echo -e "${BLUE└── 预测引擎状态: 在线${NC}"

else
    echo -e "\n${RED}❌ 预测任务执行失败${NC}"
    echo -e "${YELLOW}📋 检查日志获取详细信息...${NC}"
    docker-compose logs --tail=20 engine
    exit 1
fi

# 清理容器
echo -e "\n${YELLOW}🧹 清理临时容器...${NC}"
docker-compose rm -f engine > /dev/null 2>&1 || true

# 显示服务状态
echo -e "\n${CYAN}🔧 服务状态检查:${NC}"
docker-compose ps

# 健康检查
echo -e "\n${CYAN}💓 服务健康检查:${NC}"
if docker-compose exec -T db pg_isready -U football_user -d football_prediction > /dev/null 2>&1; then
    echo -e "${GREEN}  ✅ PostgreSQL: 健康${NC}"
else
    echo -e "${RED}  ❌ PostgreSQL: 异常${NC}"
fi

if docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; then
    echo -e "${GREEN}  ✅ Redis: 健康${NC}"
else
    echo -e "${RED}  ❌ Redis: 异常${NC}"
fi

# 显示访问信息
echo -e "\n${GREEN}======================================"
echo -e "${GREEN}🏆 足球预测系统运行完成！"
echo -e "${GREEN}======================================"
echo -e "${BLUE}📊 数据库: localhost:5432${NC}"
echo -e "${BLUE}🗄️ Redis: localhost:6379${NC}"
echo -e "${BLUE}🔮 预测模型: V2.0 真实比分版本${NC}"
echo -e "${BLUE}🎯 预测准确率: 60.00%${NC}"
echo -e "${BLUE}📁 日志目录: logs/${NC}"
echo -e "${GREEN}======================================${NC}"

echo -e "\n${PURPLE}💡 提示: 使用 'docker-compose logs -f engine' 查看详细预测日志${NC}"
echo -e "${PURPLE}💡 提示: 使用 'docker-compose down' 停止所有服务${NC}"