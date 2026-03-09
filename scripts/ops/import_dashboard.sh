#!/bin/bash
# =============================================================================
# TITAN-V4.46.6 Grafana Dashboard 自动导入脚本
# =============================================================================
# 用途: 通过 Grafana API 自动导入监控仪表盘
# 使用: ./scripts/ops/import_dashboard.sh
# =============================================================================

set -e

# 配置
GRAFANA_HOST="${GRAFANA_HOST:-localhost}"
GRAFANA_PORT="${GRAFANA_PORT:-3001}"
GRAFANA_USER="${GRAFANA_ADMIN_USER:-admin}"
GRAFANA_PASSWORD="${GRAFANA_ADMIN_PASSWORD:-titan2024}"
DASHBOARD_FILE="config/monitoring/grafana_dashboard.json"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo ""
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║  📊 TITAN-V4.46.6 Grafana Dashboard 导入器                   ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

# 检查 Grafana 是否可用
echo -e "${YELLOW}🔍 检查 Grafana 连接...${NC}"
GRAFANA_URL="http://${GRAFANA_HOST}:${GRAFANA_PORT}"

if ! curl -s -o /dev/null -w "%{http_code}" "${GRAFANA_URL}/api/health" | grep -q "200"; then
    echo -e "${RED}❌ Grafana 不可用: ${GRAFANA_URL}${NC}"
    echo "   请确保 Grafana 容器正在运行:"
    echo "   docker-compose -f docker-compose.dev.yml up -d grafana"
    exit 1
fi

echo -e "${GREEN}✅ Grafana 连接成功${NC}"

# 检查 dashboard 文件
if [ ! -f "$DASHBOARD_FILE" ]; then
    echo -e "${RED}❌ Dashboard 文件不存在: $DASHBOARD_FILE${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Dashboard 文件找到: $DASHBOARD_FILE${NC}"

# 创建导入 payload
# Grafana API 需要特定格式的 JSON
DASHBOARD_UID="titan-v4464-dashboard"

# 读取 dashboard JSON 并包装成导入格式
DASHBOARD_JSON=$(cat "$DASHBOARD_FILE")

# 构建导入请求
IMPORT_PAYLOAD=$(cat <<EOF
{
  "dashboard": ${DASHBOARD_JSON},
  "overwrite": true,
  "message": "Auto-imported by TITAN-V4.46.6"
}
EOF
)

# 导入 dashboard
echo ""
echo -e "${YELLOW}📦 导入 Dashboard...${NC}"

RESPONSE=$(curl -s -X POST \
    -u "${GRAFANA_USER}:${GRAFANA_PASSWORD}" \
    -H "Content-Type: application/json" \
    -d "$IMPORT_PAYLOAD" \
    "${GRAFANA_URL}/api/dashboards/db")

# 检查响应
if echo "$RESPONSE" | grep -q '"status":"success"'; then
    echo -e "${GREEN}✅ Dashboard 导入成功！${NC}"
    
    # 提取 dashboard URL
    DASHBOARD_URL="${GRAFANA_URL}/d/${DASHBOARD_UID}/titan-v4464-dashboard"
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    echo -e "${GREEN}  🎉 监控仪表盘已就绪！${NC}"
    echo "═══════════════════════════════════════════════════════════════"
    echo ""
    echo "  📊 Dashboard URL: ${DASHBOARD_URL}"
    echo "  👤 用户名: ${GRAFANA_USER}"
    echo "  🔑 密码: ${GRAFANA_PASSWORD}"
    echo ""
    echo "  📱 手机访问: http://<YOUR_IP>:${GRAFANA_PORT}"
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
else
    echo -e "${RED}❌ Dashboard 导入失败${NC}"
    echo "响应: $RESPONSE"
    exit 1
fi

# 验证数据源连接
echo ""
echo -e "${YELLOW}🔍 验证 Prometheus 数据源...${NC}"

DS_RESPONSE=$(curl -s -u "${GRAFANA_USER}:${GRAFANA_PASSWORD}" \
    "${GRAFANA_URL}/api/datasources/proxy/1/api/v1/query?query=up")

if echo "$DS_RESPONSE" | grep -q '"status":"success"'; then
    echo -e "${GREEN}✅ Prometheus 数据源连接正常${NC}"
else
    echo -e "${YELLOW}⚠️  Prometheus 数据源可能需要配置${NC}"
fi

echo ""
echo -e "${GREEN}🚀 监控全家桶部署完成！${NC}"
echo ""
