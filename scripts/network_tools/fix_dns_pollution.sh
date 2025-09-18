#!/bin/bash

# ==================================================
# 🔧 DNS 污染修复验证脚本
# 用于验证 DNS 配置修复后的效果
# ==================================================

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${BLUE}${BOLD}================================${NC}"
echo -e "${BLUE}${BOLD}🔧 DNS 污染修复验证${NC}"
echo -e "${BLUE}${BOLD}================================${NC}"

# 1. 清除本地DNS缓存
echo -e "${YELLOW}📍 步骤 1: 清除本地 DNS 缓存${NC}"
echo "清除 systemd-resolved 缓存..."
sudo systemctl restart systemd-resolved 2>/dev/null
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ DNS 缓存清理完成${NC}"
else
    echo -e "${YELLOW}⚠️ 系统 DNS 缓存清理需要 sudo 权限${NC}"
fi

echo ""

# 2. 等待 Clash 重新启动
echo -e "${YELLOW}📍 步骤 2: 检查 Clash Verge 状态${NC}"
echo "请确认您已经:"
echo -e "  ${BLUE}1.${NC} 更新了 Clash Verge 的 DNS 配置"
echo -e "  ${BLUE}2.${NC} 重启了 Clash Verge 应用"
echo -e "  ${BLUE}3.${NC} 确认代理状态为 '运行中'"
echo ""
read -p "配置已更新并重启 Clash Verge？(y/n): " confirm
if [[ $confirm != [yY] ]]; then
    echo -e "${YELLOW}请先完成 Clash Verge 配置更新后再运行此脚本${NC}"
    exit 1
fi

# 3. 重新测试 DNS 解析
echo -e "${YELLOW}📍 步骤 3: 验证 DNS 修复效果${NC}"
echo -e "${BLUE}——————————————————————————————————${NC}"

test_dns_resolution() {
    local domain=$1
    local description=$2

    echo "🔍 测试 $description DNS 解析:"

    # 通过代理测试连接
    local result=$(curl -I -s --max-time 10 --proxy http://172.25.16.1:7890 "https://$domain" 2>&1)
    local exit_code=$?

    if [ $exit_code -eq 0 ]; then
        local http_code=$(echo "$result" | head -1 | cut -d' ' -f2)
        echo -e "   ${GREEN}✅ 连接成功${NC} (HTTP: $http_code)"
        return 0
    else
        case $exit_code in
            35)
                echo -e "   ${RED}❌ 仍然存在 SSL 握手问题${NC}"
                echo -e "   ${YELLOW}   可能需要进一步配置或等待 DNS 生效${NC}"
                ;;
            7)
                echo -e "   ${RED}❌ 无法连接到服务器${NC}"
                ;;
            28)
                echo -e "   ${RED}❌ 连接超时${NC}"
                ;;
            *)
                echo -e "   ${RED}❌ 其他错误 (代码: $exit_code)${NC}"
                ;;
        esac
        return 1
    fi
}

# 测试关键域名
test_dns_resolution "api.cursor.sh" "Cursor API"
echo ""
test_dns_resolution "cursor.com" "Cursor 主站"
echo ""
test_dns_resolution "api.openai.com" "OpenAI API"
echo ""

# 4. 最终验证
echo -e "${YELLOW}📍 步骤 4: 完整连通性验证${NC}"
echo -e "${BLUE}——————————————————————————————————${NC}"

echo "运行完整的代理验证脚本..."
echo ""
./verify_proxy.sh

# 5. 给出最终建议
echo -e "\n${BLUE}${BOLD}================================${NC}"
echo -e "${BLUE}${BOLD}📋 修复验证完成${NC}"
echo -e "${BLUE}${BOLD}================================${NC}"

echo -e "\n${BOLD}🎯 下一步操作：${NC}"
echo -e "${GREEN}1.${NC} 如果所有测试都显示 ✅，则问题已解决"
echo -e "${GREEN}2.${NC} 在 Cursor 中测试 AI 对话功能"
echo -e "${GREEN}3.${NC} 如果仍有问题，可能需要："
echo -e "   • 等待 DNS 配置完全生效（5-10分钟）"
echo -e "   • 检查 Clash Verge 的日志是否有错误"
echo -e "   • 尝试切换不同的代理节点"

echo -e "\n${BLUE}修复验证完成时间: $(date '+%Y-%m-%d %H:%M:%S')${NC}"

exit 0
