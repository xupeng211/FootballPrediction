#!/bin/bash

# Docker 优化部署脚本
# 解决构建时间过长问题，从 7GB 减少到 <2GB

set -e

echo "🚀 Docker 镜像优化开始..."

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 备份原始 Dockerfile
if [ -f "Dockerfile" ]; then
    echo -e "${YELLOW}📦 备份原始 Dockerfile...${NC}"
    cp Dockerfile Dockerfile.backup.$(date +%Y%m%d_%H%M%S)
fi

# 选择优化策略
echo -e "${BLUE}🎯 请选择优化策略:${NC}"
echo "1) 标准 Slim 优化 (推荐) - 预计减少到 1.5-2GB"
echo "2) Ultra-Slim 优化 - 预计减少到 <1GB (可能兼容性风险)"
echo "3) 查看优化差异对比"

read -p "请输入选择 (1-3): " choice

case $choice in
    1)
        echo -e "${GREEN}✅ 应用标准 Slim 优化...${NC}"
        cp Dockerfile.optimized Dockerfile
        echo -e "${GREEN}📝 优化要点:${NC}"
        echo "   - 基础镜像: python:3.11-slim (从 Playwright 7GB 改为 800MB)"
        echo "   - 只安装 Chromium 浏览器 (移除 Firefox, WebKit)"
        echo "   - 精准系统依赖安装"
        echo "   - 多阶段构建保持缓存优化"
        ;;
    2)
        echo -e "${YELLOW}⚡ 应用 Ultra-Slim 优化...${NC}"
        cp Dockerfile.ultra-slim Dockerfile
        echo -e "${YELLOW}📝 优化要点:${NC}"
        echo "   - 多阶段构建分离编译和运行时"
        echo "   - Python 包预安装到 /opt/python-packages"
        echo "   - 最小化运行时依赖"
        echo "   - 极致缓存清理"
        echo -e "${RED}   ⚠️  可能的兼容性风险，建议先测试${NC}"
        ;;
    3)
        echo -e "${BLUE}📊 优化差异对比:${NC}"
        echo ""
        echo "🔍 镜像大小对比:"
        echo "   原始 (Playwright): ~7GB"
        echo "   标准 Slim 优化: ~1.5-2GB (减少 70-75%)"
        echo "   Ultra-Slim 优化: ~800MB-1GB (减少 85%)"
        echo ""
        echo "🏗️ 构建时间对比:"
        echo "   原始: 45+ 分钟 (tarball 传输慢)"
        echo "   优化后: 5-10 分钟 (缓存命中更快)"
        echo ""
        echo "🎯 关键优化策略:"
        echo "   1. 基础镜像: mcr.microsoft.com/playwright/python:latest → python:3.11-slim"
        echo "   2. 浏览器: 全套 Playwright → 仅 Chromium"
        echo "   3. 依赖管理: 全量安装 → 精准安装 + 清理缓存"
        echo "   4. 多阶段: 分离构建和运行时环境"
        exit 0
        ;;
    *)
        echo -e "${RED}❌ 无效选择${NC}"
        exit 1
        ;;
esac

# 清理旧镜像
echo -e "${YELLOW}🧹 清理旧 Docker 镜像...${NC}"
docker system prune -f

# 构建优化后的镜像
echo -e "${BLUE}🏗️ 构建优化后的镜像...${NC}"
echo "这可能需要 5-10 分钟，比原来的 45+ 分钟快很多！"

start_time=$(date +%s)

# 构建开发环境镜像
docker build -t footballprediction-app:optimized --target development .

# 构建生产环境镜像
docker build -t footballprediction-app:optimized-prod --target production .

end_time=$(date +%s)
duration=$((end_time - start_time))

echo -e "${GREEN}✅ 构建完成！耗时: ${duration} 秒${NC}"

# 显示镜像大小对比
echo -e "${BLUE}📊 镜像大小信息:${NC}"
docker images | grep footballprediction

# 更新 docker-compose.yml 使用优化镜像
echo -e "${YELLOW}📝 更新 docker-compose.yml 使用优化镜像...${NC}"

# 备份原始 docker-compose.yml
if [ -f "docker-compose.yml" ]; then
    cp docker-compose.yml docker-compose.yml.backup.$(date +%Y%m%d_%H%M%S)
fi

# 生成优化版本的 docker-compose.yml
cat > docker-compose.optimized.yml << 'EOF'
services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
      target: development  # 使用优化后的开发阶段
    image: footballprediction-app:optimized
    ports:
      - "8000:8000"
    env_file:
      - .env
    environment:
      - ENV=development
      - DATABASE_URL=${DATABASE_URL:-postgresql://postgres:postgres-dev-password@db:5432/football_prediction}
      - REDIS_URL=${REDIS_URL:-redis://redis:6379/0}
      - SECRET_KEY=${SECRET_KEY:-dev-secret-key-for-development-only}
      - FOOTBALL_DATA_API_KEY=${FOOTBALL_DATA_API_KEY}
      - PYTHONPATH=/app:/opt/python-packages:/opt/python-packages-dev
      # 代理配置
      - HTTP_PROXY=${HTTP_PROXY:-}
      - HTTPS_PROXY=${HTTPS_PROXY:-}
      - NO_PROXY=localhost,127.0.0.1,0.0.0.0,db,redis,beat,worker,app,data-collector,data-collector-l2,frontend,nginx
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_started
    volumes:
      - ./src:/app/src
      - ./tests:/app/tests
      - ./scripts:/app/scripts
      - ./models:/app/models
    restart: unless-stopped
    command: ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

  # 其他服务保持不变...
EOF

echo -e "${GREEN}✅ 优化完成！${NC}"
echo ""
echo -e "${BLUE}🎯 下一步操作:${NC}"
echo "1. 测试优化镜像: docker-compose -f docker-compose.optimized.yml up -d"
echo "2. 验证功能正常: curl http://localhost:8000/health"
echo "3. 如果测试通过，替换原始 docker-compose.yml"
echo "4. 清理旧镜像: docker rmi \$(docker images 'footballprediction*' -q)"
echo ""
echo -e "${GREEN}⚡ 预期效果:${NC}"
echo "- 构建时间: 从 45+ 分钟 → 5-10 分钟"
echo "- 镜像大小: 从 7GB → 1.5-2GB (减少 70%+)"
echo "- 传输速度: 显著提升"
echo "- 缓存效率: 大幅改善"