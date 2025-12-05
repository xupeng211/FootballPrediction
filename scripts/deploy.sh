#!/bin/bash
# FootballPrediction 部署脚本
# 简化的部署和验证流程

set -e

echo "🏈 FootballPrediction 部署脚本"
echo "================================"

# 检查必需文件
if [ ! -f "docker-compose.deploy.yml" ]; then
    echo "❌ 错误: docker-compose.deploy.yml 不存在"
    exit 1
fi

if [ ! -f ".env" ]; then
    echo "⚠️ 警告: .env 文件不存在，使用默认配置"
    # 创建基本的.env文件
    cat > .env << EOF
# FootballPrediction 环境配置
POSTGRES_DB=football_prediction
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres-dev-password
DATABASE_URL=postgresql://postgres:postgres-dev-password@db:5432/football_prediction
REDIS_URL=redis://redis:6379/0
SECRET_KEY=dev-secret-key-change-in-production
ENV=production

# ML配置
FOOTBALL_PREDICTION_ML_MODE=real
SKIP_ML_MODEL_LOADING=false
INFERENCE_SERVICE_MOCK=false
XGBOOST_MOCK=false
EOF
    echo "✅ 已创建基本的 .env 文件"
fi

# 检查Docker是否运行
if ! docker info > /dev/null 2>&1; then
    echo "❌ 错误: Docker 未运行，请先启动Docker"
    exit 1
fi

echo "📦 构建和启动服务..."

# 构建镜像并启动服务
docker-compose -f docker-compose.deploy.yml down  # 清理现有容器
docker-compose -f docker-compose.deploy.yml build --parallel
docker-compose -f docker-compose.deploy.yml up -d

echo "⏳ 等待服务启动..."
sleep 30

echo "🔍 执行部署验证..."

# 执行验证脚本
if python scripts/deploy_verify.py; then
    echo ""
    echo "🎉 部署成功完成!"
    echo ""
    echo "📍 服务访问地址:"
    echo "  - FastAPI应用: http://localhost:8000"
    echo "  - API文档: http://localhost:8000/docs"
    echo "  - 健康检查: http://localhost:8000/health"
    echo ""
    echo "📋 有用的命令:"
    echo "  - 查看日志: docker-compose -f docker-compose.deploy.yml logs -f"
    echo "  - 查看状态: docker-compose -f docker-compose.deploy.yml ps"
    echo "  - 停止服务: docker-compose -f docker-compose.deploy.yml down"
    echo ""
    echo "🔧 可选服务 (使用 --profile 启动):"
    echo "  - 生产环境代理: docker-compose -f docker-compose.deploy.yml --profile production up -d nginx"
    echo "  - 监控服务: docker-compose -f docker-compose.deploy.yml --profile monitoring up -d prometheus grafana"
    echo ""
else
    echo ""
    echo "❌ 部署验证失败!"
    echo ""
    echo "🔍 调试命令:"
    echo "  - 查看应用日志: docker-compose -f docker-compose.deploy.yml logs app"
    echo "  - 查看数据库日志: docker-compose -f docker-compose.deploy.yml logs db"
    echo "  - 查看Redis日志: docker-compose -f docker-compose.deploy.yml logs redis"
    echo "  - 检查容器状态: docker-compose -f docker-compose.deploy.yml ps"
    echo ""
    echo "🔄 重试部署:"
    echo "  ./scripts/deploy.sh"
    echo ""
    exit 1
fi
