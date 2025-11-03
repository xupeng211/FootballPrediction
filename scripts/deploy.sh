#!/bin/bash

# 部署脚本
echo "🚀 开始部署足球预测系统..."

# 检查Docker是否运行
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker未运行，请先启动Docker"
    exit 1
fi

# 构建并启动服务
echo "📦 构建Docker镜像..."
docker-compose build

echo "🔄 启动服务..."
docker-compose up -d

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 10

# 健康检查
echo "🔍 执行健康检查..."
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ 服务启动成功！"
    echo "🌐 API地址: http://localhost:8000"
    echo "📊 监控地址: http://localhost:9090/metrics"
else
    echo "❌ 服务启动失败，请检查日志"
    docker-compose logs
    exit 1
fi

echo "🎉 部署完成！"
