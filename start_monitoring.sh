#!/bin/bash

# P0-4 ML Pipeline 监控服务启动脚本

echo "🚀 启动P0-4 ML Pipeline监控服务..."

# 检查Docker是否运行
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker未运行，请先启动Docker"
    exit 1
fi

# 启动监控服务
echo "📊 启动Prometheus..."
docker-compose -f docker-compose.monitoring.yml up -d prometheus

echo "📈 启动Grafana..."
docker-compose -f docker-compose.monitoring.yml up -d grafana

echo "🚨 启动AlertManager..."
docker-compose -f docker-compose.monitoring.yml up -d alertmanager

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 10

# 检查服务状态
echo "🔍 检查服务状态..."
docker-compose -f docker-compose.monitoring.yml ps

# 显示访问地址
echo ""
echo "✅ 监控服务启动完成!"
echo "📊 Prometheus: http://localhost:9090"
echo "📈 Grafana: http://localhost:3000 (admin/admin123)"
echo "🚨 AlertManager: http://localhost:9093"
echo ""
echo "💡 使用 './stop_monitoring.sh' 停止监控服务"
