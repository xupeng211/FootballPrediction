#!/bin/bash

# FootballPrediction v2.3.1 - 磁盘空间监控与告警
# 触发条件: 磁盘使用率 > 90%

set -euo pipefail

# 获取磁盘使用率
DISK_USAGE=$(df . | tail -1 | awk '{print $5}' | sed 's/%//')
AVAILABLE_SPACE=$(df -h . | tail -1 | awk '{print $4}')
CURRENT_DATE=$(date '+%Y-%m-%d %H:%M:%S')

# 告警阈值
ALERT_THRESHOLD=90
WARNING_THRESHOLD=80

# 日志文件
ALERT_LOG="./logs/disk_space_alerts.log"

# 确保日志目录存在
mkdir -p "$(dirname "$ALERT_LOG")"

# 检查磁盘空间状态
if [ "$DISK_USAGE" -gt "$ALERT_THRESHOLD" ]; then
    # 严重告警
    echo "🚨 CRITICAL DISK SPACE ALERT - ${CURRENT_DATE}" | tee -a "$ALERT_LOG"
    echo "   磁盘使用率: ${DISK_USAGE}% (超过${ALERT_THRESHOLD}%阈值)" | tee -a "$ALERT_LOG"
    echo "   剩余空间: ${AVAILABLE_SPACE}" | tee -a "$ALERT_LOG"
    echo "   建议: 立即清理日志文件或扩展磁盘空间" | tee -a "$ALERT_LOG"
    echo "" | tee -a "$ALERT_LOG"

    # 可以在这里添加自动清理逻辑
    # docker system prune -f

    exit 1

elif [ "$DISK_USAGE" -gt "$WARNING_THRESHOLD" ]; then
    # 警告
    echo "⚠️  DISK SPACE WARNING - ${CURRENT_DATE}" | tee -a "$ALERT_LOG"
    echo "   磁盘使用率: ${DISK_USAGE}% (超过${WARNING_THRESHOLD}%阈值)" | tee -a "$ALERT_LOG"
    echo "   剩余空间: ${AVAILABLE_SPACE}" | tee -a "$ALERT_LOG"
    echo "" | tee -a "$ALERT_LOG"

else
    # 正常状态
    echo "✅ Disk space OK - ${CURRENT_DATE}" >> "$ALERT_LOG"
    echo "   磁盘使用率: ${DISK_USAGE}%" >> "$ALERT_LOG"
    echo "   剩余空间: ${AVAILABLE_SPACE}" >> "$ALERT_LOG"
    echo "" >> "$ALERT_LOG"
fi

echo "🔍 Disk space check completed: ${DISK_USAGE}% used, ${AVAILABLE_SPACE} available"
exit 0