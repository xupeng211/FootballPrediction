#!/bin/bash

# P0-4 ML Pipeline 监控服务停止脚本

echo "🛑 停止P0-4 ML Pipeline监控服务..."

# 停止监控服务
docker-compose -f docker-compose.monitoring.yml down

echo "✅ 监控服务已停止"

# 可选: 清理数据卷
read -p "是否清理监控数据? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    docker-compose -f docker-compose.monitoring.yml down -v
    echo "🗑️ 监控数据已清理"
fi
