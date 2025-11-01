#!/bin/bash

# 快速诊断脚本
# Quick Diagnosis Script

set -euo pipefail

# 配置变量
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🔍 足球预测系统快速诊断${NC}"
echo "=================================="

# 1. 系统状态
echo -e "\n${GREEN}📊 系统状态${NC}"
echo "------------"

if command -v docker-compose &> /dev/null; then
    cd "$PROJECT_ROOT"
    echo "Docker服务状态:"
    docker-compose ps
else
    echo -e "${RED}❌ Docker Compose 未安装${NC}"
fi

# 2. 资源使用
echo -e "\n${GREEN}💻 资源使用情况${NC}"
echo "------------------"

if command -v docker &> /dev/null; then
    echo "容器资源使用:"
    docker stats --no-stream 2>/dev/null || echo "无法获取容器统计信息"
fi

echo "系统资源:"
if command -v top &> /dev/null; then
    echo "CPU和内存使用率:"
    top -bn1 | head -5 | tail -2
fi

if command -v df &> /dev/null; then
    echo "磁盘使用情况:"
    df -h | grep -E "(/$|/var|/tmp)" | head -3
fi

# 3. 网络连通性
echo -e "\n${GREEN}🌐 网络连通性${NC}"
echo "------------------"

# 检查关键端口
declare -A ports=(
    ["80"]="HTTP服务"
    ["8000"]="API服务"
    ["5432"]="PostgreSQL数据库"
    ["6379"]="Redis缓存"
    ["9090"]="Prometheus监控"
    ["3000"]="Grafana仪表板"
)

for port in "${!ports[@]}"; do
    service_name="${ports[$port]}"
    if netstat -tuln 2>/dev/null | grep -q ":$port "; then
        echo -e "✅ 端口 $port ($service_name): 正常"
    else
        echo -e "❌ 端口 $port ($service_name): 未监听"
    fi
done

# 4. 健康检查
echo -e "\n${GREEN}🏥 健康检查${NC}"
echo "------------"

# 基础健康检查
if curl -s -f http://localhost/health/ > /dev/null 2>&1; then
    echo -e "✅ 基础健康检查: 通过"

    # 详细健康状态
    health_response=$(curl -s http://localhost/health/ 2>/dev/null || echo '{"status":"unknown"}')
    if echo "$health_response" | grep -q '"status":"healthy"'; then
        echo -e "✅ 详细健康状态: 健康"
    else
        echo -e "⚠️ 详细健康状态: 异常"
    fi
else
    echo -e "❌ 基础健康检查: 失败"
fi

# API端点检查
if curl -s -f http://localhost/api/v1/predictions/1 > /dev/null 2>&1; then
    echo -e "✅ API端点: 正常"
else
    echo -e "❌ API端点: 异常"
fi

# 5. 数据库连接
echo -e "\n${GREEN}🗄️ 数据库连接${NC}"
echo "------------------"

cd "$PROJECT_ROOT"
if docker-compose ps | grep -q "db.*Up"; then
    if docker-compose exec -T db pg_isready -U prod_user > /dev/null 2>&1; then
        echo -e "✅ PostgreSQL连接: 正常"

        # 检查连接数
        connection_count=$(docker-compose exec -T db psql -U prod_user -t -c "SELECT count(*) FROM pg_stat_activity;" 2>/dev/null | xargs || echo "unknown")
        echo "📊 当前数据库连接数: $connection_count"
    else
        echo -e "❌ PostgreSQL连接: 失败"
    fi
else
    echo -e "❌ PostgreSQL服务: 未运行"
fi

if docker-compose ps | grep -q "redis.*Up"; then
    if docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; then
        echo -e "✅ Redis连接: 正常"
    else
        echo -e "❌ Redis连接: 失败"
    fi
else
    echo -e "❌ Redis服务: 未运行"
fi

# 6. 最近错误
echo -e "\n${GREEN}🚨 最近错误日志${NC}"
echo "------------------"

cd "$PROJECT_ROOT"
echo "应用错误 (最近10条):"
docker-compose logs --tail=100 app 2>/dev/null | grep -i error | tail -5 || echo "无错误日志"

echo ""
echo "Nginx错误 (最近10条):"
docker-compose logs --tail=100 nginx 2>/dev/null | grep -i error | tail -5 || echo "无错误日志"

# 7. 监控状态
echo -e "\n${GREEN}📈 监控状态${NC}"
echo "------------"

# Prometheus
if curl -s -f http://localhost:9090/-/healthy > /dev/null 2>&1; then
    echo -e "✅ Prometheus: 正常"
else
    echo -e "❌ Prometheus: 异常"
fi

# Grafana
if curl -s -f http://localhost:3000/api/health > /dev/null 2>&1; then
    echo -e "✅ Grafana: 正常"
else
    echo -e "❌ Grafana: 异常"
fi

# 8. 建议操作
echo -e "\n${GREEN}💡 建议操作${NC}"
echo "------------"

issues_found=0

# 检查是否有服务宕机
cd "$PROJECT_ROOT"
if ! docker-compose ps | grep -q "app.*Up"; then
    echo -e "${YELLOW}• 应用服务未运行，建议: ./scripts/emergency-response.sh restart app${NC}"
    ((issues_found++))
fi

if ! docker-compose ps | grep -q "db.*Up"; then
    echo -e "${YELLOW}• 数据库服务未运行，建议: ./scripts/emergency-response.sh restart db${NC}"
    ((issues_found++))
fi

# 检查健康状态
if ! curl -s -f http://localhost/health/ > /dev/null 2>&1; then
    echo -e "${YELLOW}• 健康检查失败，建议: ./scripts/emergency-response.sh check${NC}"
    ((issues_found++))
fi

# 检查资源使用
if command -v docker &> /dev/null; then
    cpu_usage=$(docker stats --no-stream --format "table {{.CPUPerc}}" | tail -n +2 | head -1 | sed 's/%//')
    if [[ -n "$cpu_usage" ]] && (( $(echo "$cpu_usage > 80" | bc -l 2>/dev/null || echo "0") )); then
        echo -e "${YELLOW}• CPU使用率过高 ($cpu_usage%)，建议: ./scripts/emergency-response.sh cleanup${NC}"
        ((issues_found++))
    fi
fi

if [[ $issues_found -eq 0 ]]; then
    echo -e "${GREEN}• 系统运行正常，无需立即操作${NC}"
else
    echo -e "${YELLOW}• 发现 $issues_found 个问题，建议及时处理${NC}"
fi

# 9. 快速命令
echo -e "\n${GREEN}⚡ 快速命令${NC}"
echo "------------"
echo "• 完整健康检查:     ./scripts/emergency-response.sh check"
echo "• 重启所有服务:     ./scripts/emergency-response.sh restart all"
echo "• 紧急数据库修复:   ./scripts/emergency-response.sh database"
echo "• 清理系统资源:     ./scripts/emergency-response.sh cleanup"
echo "• 运行压力测试:     python scripts/stress_test.py"
echo "• 性能检查:         ./scripts/performance-check.sh"
echo "• 查看实时日志:     docker-compose logs -f"

echo -e "\n${BLUE}诊断完成！${NC}"
echo "如需详细帮助，请查看 EMERGENCY_RESPONSE_PLAN.md"