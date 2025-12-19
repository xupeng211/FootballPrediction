#!/bin/bash

# ====================================================================
# 🚀 FootballPrediction 运维监控仪表盘 v2.3.1
#
# 功能：一键查看容器内实时运行状态
# 作者：DevOps Team
# 日期：2025-12-19
# ====================================================================

set -euo pipefail

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 图标定义
ICON_ROCKET="🚀"
ICON_HEART="❤️"
ICON_CHART="📊"
ICON_CLOCK="⏰"
ICON_DATABASE="🗄️"
ICON_MEMORY="💾"
ICON_ROBOT="🤖"
ICON_TROPHY="🏆"

echo -e "${CYAN}================================================================${NC}"
echo -e "${CYAN}🏆 FootballPrediction v2.3.1 - 运维监控仪表盘${NC}"
echo -e "${CYAN}================================================================${NC}"
echo

# 检查Docker容器状态
echo -e "${BLUE}📱 容器状态检查${NC}"
echo "----------------------------------------"

app_status=$(docker-compose ps --format table | grep "app" | awk '{print $3, $4}' 2>/dev/null || echo "unknown")
db_status=$(docker-compose ps --format table | grep "db" | awk '{print $3, $4}' 2>/dev/null || echo "unknown")
redis_status=$(docker-compose ps --format table | grep "redis" | awk '{print $3, $4}' 2>/dev/null || echo "unknown")

if [[ "$app_status" == *"Up"* ]]; then
    echo -e "🟢 应用容器: ${GREEN}运行中${NC}"
else
    echo -e "🔴 应用容器: ${RED}${app_status}${NC}"
fi

echo -e "🗄️  数据库: ${GREEN}${db_status}${NC}"
echo -e "🔴 缓存服务: ${GREEN}${redis_status}${NC}"
echo

# 守护进程心跳检查
echo -e "${BLUE}🤖 自动化守护进程状态${NC}"
echo "----------------------------------------"

last_heartbeat=$(docker logs footballprediction-app 2>/dev/null | grep "执行预测" | tail -1 | grep -o '[0-9]\{4\}-[0-9]\{2\}-[0-9]\{2\} [0-9]\{2\}:[0-9]\{2\}:[0-9]\{2\}' || echo "未找到")
prediction_count=$(docker logs footballprediction-app 2>/dev/null | grep -c "✅ 预测成功" || echo "0")

if [[ -n "$last_heartbeat" && "$last_heartbeat" != "未找到" ]]; then
    echo -e "❤️  最后心跳: ${GREEN}${last_heartbeat}${NC}"
else
    echo -e "❤️  最后心跳: ${YELLOW}守护进程可能未启动${NC}"
fi

echo -e "🏆 成功预测次数: ${GREEN}${prediction_count}${NC}"

# 下次预测时间计算
if [[ -n "$last_heartbeat" && "$last_heartbeat" != "未找到" ]]; then
    # 解析最后心跳时间
    heartbeat_ts=$(date -d "$last_heartbeat" +%s 2>/dev/null || echo "0")
    current_ts=$(date +%s)

    if [[ $heartbeat_ts -gt 0 ]]; then
        next_prediction_ts=$((heartbeat_ts + 900)) # 15分钟后
        next_prediction_time=$(date -d "@$next_prediction_ts" '+%H:%M:%S' 2>/dev/null || echo "计算中...")
        echo -e "⏰  下次预测: ${YELLOW}${next_prediction_time}${NC}"
    fi
fi
echo

# 数据库预测记录统计
echo -e "${BLUE}📊 数据库统计${NC}"
echo "----------------------------------------"

total_records=$(docker exec footballprediction-db psql -U football_user -d football_prediction_shadow -t -c "SELECT COUNT(*) FROM realtime_predictions;" 2>/dev/null | xargs || echo "查询失败")
recent_predictions=$(docker exec footballprediction-db psql -U football_user -d football_prediction_shadow -t -c "SELECT COUNT(*) FROM realtime_predictions WHERE created_at > NOW() - INTERVAL '24 hours';" 2>/dev/null | xargs || echo "查询失败")

if [[ "$total_records" != "查询失败" ]]; then
    echo -e "🗄️  预测记录总数: ${GREEN}${total_records}${NC}"
    echo -e "📈 24小时预测数: ${GREEN}${recent_predictions}${NC}"
else
    echo -e "🔴 数据库查询: ${RED}失败${NC}"
    echo -e "💡 提示: 检查数据库连接和表结构"
fi
echo

# 内存和资源使用情况
echo -e "${BLUE}💾 系统资源${NC}"
echo "----------------------------------------"

# 容器内存使用
memory_stats=$(docker stats footballprediction-app --no-stream --format "table {{.MemUsage}}\t{{.MemPerc}}" 2>/dev/null | tail -n +2 || echo "N/A")
cpu_stats=$(docker stats footballprediction-app --no-stream --format "table {{.CPUPerc}}" 2>/dev/null | tail -n +2 || echo "N/A")

if [[ "$memory_stats" != "N/A" ]]; then
    echo -e "💾 应用内存使用: ${GREEN}${memory_stats}${NC}"
    echo -e "⚙️  CPU使用率: ${GREEN}${cpu_stats}${NC}"
else
    echo -e "🔴 资源统计: ${RED}获取失败${NC}"
fi

# 磁盘使用情况
disk_usage=$(df -h . | tail -1 | awk '{print $5}' | sed 's/%//')
if [[ "$disk_usage" -lt 80 ]]; then
    echo -e "💿 磁盘使用: ${GREEN}${disk_usage}%${NC}"
elif [[ "$disk_usage" -lt 90 ]]; then
    echo -e "💿 磁盘使用: ${YELLOW}${disk_usage}%${NC}"
else
    echo -e "💿 磁盘使用: ${RED}${disk_usage}% (警告)${NC}"
fi
echo

# 服务健康检查
echo -e "${BLUE}🔍 服务健康检查${NC}"
echo "----------------------------------------"

# 应用健康检查
app_health=$(docker exec footballprediction-app curl -s http://localhost:8000/health 2>/dev/null || echo "failed")
if [[ "$app_health" == *"healthy"* ]]; then
    echo -e "🟢 应用健康检查: ${GREEN}通过${NC}"
else
    echo -e "🔴 应用健康检查: ${RED}失败${NC}"
fi

# 数据库连接检查
db_health=$(docker exec footballprediction-app python -c "
import asyncio
import sys
try:
    from src.config_unified import get_settings
    settings = get_settings()
    print('数据库配置正常')
except Exception as e:
    print(f'数据库配置错误: {e}')
    sys.exit(1)
" 2>/dev/null || echo "配置检查失败")

echo -e "🗄️  数据库配置: ${GREEN}${db_health}${NC}"
echo

# 实时日志片段
echo -e "${BLUE}📋 最新日志片段${NC}"
echo "----------------------------------------"
docker logs footballprediction-app --tail 3 2>/dev/null | while IFS= read -r line; do
    echo -e "${CYAN}  ${line}${NC}"
done
echo

# 系统时间
echo -e "${BLUE}⏰ 系统信息${NC}"
echo "----------------------------------------"
echo -e "🕐 当前时间: ${GREEN}$(date '+%Y-%m-%d %H:%M:%S')${NC}"
echo -e "⏱️  系统运行: ${GREEN}$(uptime -p 2>/dev/null || echo "N/A")${NC}"
echo -e "🚀 版本: ${GREEN}v2.3.1${NC}"
echo

# 建议和警告
echo -e "${BLUE}💡 运维建议${NC}"
echo "----------------------------------------"

# 检查预测间隔
if [[ -n "$last_heartbeat" && "$last_heartbeat" != "未找到" ]]; then
    heartbeat_ts=$(date -d "$last_heartbeat" +%s 2>/dev/null || echo "0")
    current_ts=$(date +%s)
    if [[ $heartbeat_ts -gt 0 ]]; then
        time_diff=$((current_ts - heartbeat_ts))
        if [[ $time_diff -gt 1800 ]]; then  # 30分钟
            echo -e "⚠️  ${YELLOW}警告: 守护进程可能已停止，超过30分钟无预测${NC}"
        else
            echo -e "✅ ${GREEN}守护进程运行正常，最近预测时间: ${time_diff}秒前${NC}"
        fi
    fi
else
    echo -e "⚠️  ${YELLOW}建议: 检查自动化守护进程是否正常启动${NC}"
fi

# 磁盘空间建议
if [[ "$disk_usage" -gt 85 ]]; then
    echo -e "⚠️  ${YELLOW}建议: 磁盘使用率较高，建议清理日志文件${NC}"
fi

echo
echo -e "${GREEN}================================================================${NC}"
echo -e "${GREEN}🏆 FootballPrediction v2.3.1 - 监控完成${NC}"
echo -e "${GREEN}================================================================${NC}"