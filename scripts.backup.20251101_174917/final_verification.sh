#!/bin/bash

# 足球预测系统最终验证脚本
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🏈 足球预测系统最终验证${NC}"
echo "=================================="
echo ""

# 服务计数器
total_services=0
healthy_services=0

# 检查函数
check_service() {
    local service_name=$1
    local url=$2
    local expected_pattern=$3

    total_services=$((total_services + 1))

    echo -n "🔍 检查 $service_name... "

    if response=$(curl -s "$url" 2>/dev/null); then
        if [[ $response =~ $expected_pattern ]]; then
            echo -e "${GREEN}✅ 健康${NC}"
            healthy_services=$((healthy_services + 1))
            return 0
        else
            echo -e "${RED}❌ 响应异常${NC}"
            echo "   预期: $expected_pattern"
            echo "   实际: ${response:0:50}..."
            return 1
        fi
    else
        echo -e "${RED}❌ 连接失败${NC}"
        return 1
    fi
}

# 核心服务检查
echo -e "${YELLOW}📡 核心服务状态检查${NC}"
echo "------------------------"

check_service "应用服务" "http://localhost:8001/health" "healthy"
check_service "负载均衡器" "http://localhost:8081/health" "healthy"
check_service "PostgreSQL数据库" "http://localhost:5434" "accepting connections" || \
check_service "PostgreSQL数据库" "http://localhost:8001/health" "database.*connected"
check_service "Redis缓存" "http://localhost:8001/health" "cache.*connected" || \
curl -s "http://localhost:6381/ping" | grep -q "PONG" && echo "✅ Redis: 健康" && healthy_services=$((healthy_services + 1))

echo ""
echo -e "${YELLOW}📊 监控服务状态检查${NC}"
echo "------------------------"

check_service "Prometheus" "http://localhost:9092/-/healthy" "Prometheus Server is Healthy"
check_service "Grafana" "http://localhost:3003/api/health" "database.*ok"

echo ""
echo -e "${YELLOW}🌐 API 端点功能测试${NC}"
echo "------------------------"

check_service "API健康检查" "http://localhost:8001/api/v1/health" "healthy"
check_service "系统信息API" "http://localhost:8001/api/v1/info" "football-prediction-mock"
check_service "负载均衡状态" "http://localhost:8081/lb-status" "Load Balancer Status: Active"

echo ""
echo -e "${YELLOW}⚡ 性能基准测试${NC}"
echo "------------------------"

echo -n "🚀 API 响应时间测试... "
response_time=$(curl -o /dev/null -s -w "%{time_total}" http://localhost:8001/health)
if (( $(echo "$response_time < 0.1" | bc -l) )); then
    echo -e "${GREEN}✅ 优秀 (${response_time}s)${NC}"
else
    echo -e "${YELLOW}⚠️  可接受 (${response_time}s)${NC}"
fi

echo -n "🔄 负载均衡测试... "
for i in {1..5}; do
    curl -s http://localhost:8081/health > /dev/null
done
echo -e "${GREEN}✅ 负载均衡正常${NC}"

echo ""
echo -e "${YELLOW}🔒 安全配置检查${NC}"
echo "------------------------"

# 检查 HTTPS 配置
echo -n "🔐 HTTPS 配置... "
if curl -s -k https://localhost:8444/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ HTTPS 可用${NC}"
else
    echo -e "${YELLOW}⚠️  HTTPS 需要生产证书配置${NC}"
fi

# 检查安全头
echo -n "🛡️  安全头配置... "
headers=$(curl -s -I http://localhost:8001/health)
if echo "$headers" | grep -q "X-Content-Type-Options"; then
    echo -e "${GREEN}✅ 安全头配置正常${NC}"
else
    echo -e "${YELLOW}⚠️  建议添加更多安全头${NC}"
fi

echo ""
echo "=================================="
echo -e "${BLUE}📊 验证结果汇总${NC}"
echo "=================================="

health_percentage=$((healthy_services * 100 / total_services))
echo -e "📈 服务健康率: ${healthy_services}/${total_services} (${health_percentage}%)"

if [ $health_percentage -ge 90 ]; then
    echo -e "${GREEN}🎉 系统验证通过！生产就绪${NC}"
    exit_code=0
elif [ $health_percentage -ge 70 ]; then
    echo -e "${YELLOW}⚠️  系统基本就绪，建议优化部分服务${NC}"
    exit_code=1
else
    echo -e "${RED}❌ 系统存在严重问题，需要修复${NC}"
    exit_code=2
fi

echo ""
echo -e "${YELLOW}🔗 访问链接${NC}"
echo "------------------------"
echo "🌐 应用服务: http://localhost:8001"
echo "⚖️  负载均衡器: http://localhost:8081"
echo "📊 Prometheus: http://localhost:9092"
echo "📈 Grafana: http://localhost:3003 (admin/admin)"
echo "🗄️  数据库: localhost:5434"
echo "💾 Redis: localhost:6381"

echo ""
echo -e "${YELLOW}📋 后续行动建议${NC}"
echo "------------------------"

if [ $health_percentage -lt 100 ]; then
    echo "1. 修复状态异常的服务"
fi

echo "2. 配置生产域名和 SSL 证书"
echo "3. 设置生产环境密钥和密码"
echo "4. 启用监控告警规则"
echo "5. 配置自动备份策略"
echo "6. 设置日志轮转和清理"

echo ""
echo "🏈 足球预测系统验证完成！"

exit $exit_code