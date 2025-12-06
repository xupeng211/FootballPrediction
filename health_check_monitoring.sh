#!/bin/bash

# P0-4 ML Pipeline 监控健康检查脚本

echo "🏥 执行监控健康检查..."

# 检查Prometheus
echo "📊 检查Prometheus..."
if curl -s http://localhost:9090/-/healthy > /dev/null; then
    echo "  ✅ Prometheus健康"
else
    echo "  ❌ Prometheus异常"
fi

# 检查Grafana
echo "📈 检查Grafana..."
if curl -s http://localhost:3000/api/health > /dev/null; then
    echo "  ✅ Grafana健康"
else
    echo "  ❌ Grafana异常"
fi

# 检查AlertManager
echo "🚨 检查AlertManager..."
if curl -s http://localhost:9093/-/healthy > /dev/null; then
    echo "  ✅ AlertManager健康"
else
    echo "  ❌ AlertManager异常"
fi

# 检查磁盘空间
echo "💾 检查磁盘空间..."
DISK_USAGE=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
if [ $DISK_USAGE -lt 80 ]; then
    echo "  ✅ 磁盘空间充足 (${DISK_USAGE}%)"
else
    echo "  ⚠️ 磁盘空间不足 (${DISK_USAGE}%)"
fi

# 检查内存使用
echo "🧠 检查内存使用..."
MEMORY_USAGE=$(free | grep Mem | awk '{printf("%.1f", $3/$2 * 100.0)}')
if (( $(echo "$MEMORY_USAGE < 80" | bc -l) )); then
    echo "  ✅ 内存使用正常 (${MEMORY_USAGE}%)"
else
    echo "  ⚠️ 内存使用过高 (${MEMORY_USAGE}%)"
fi

echo "🏥 健康检查完成"
