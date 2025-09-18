#!/bin/bash

# ==================================================
# 🔍 Cursor SSL 连接问题自动化诊断脚本
# 目标：确定 api.cursor.sh 连接失败的根本原因
# ==================================================

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

# 配置
TARGET_DOMAIN="api.cursor.sh"
PROXY_URL="http://172.25.16.1:7890"
CLOUDFLARE_DNS="1.1.1.1"
GOOGLE_DNS="8.8.8.8"

echo -e "${BLUE}${BOLD}================================${NC}"
echo -e "${BLUE}${BOLD}🔍 Cursor SSL 诊断工具${NC}"
echo -e "${BLUE}${BOLD}================================${NC}"
echo -e "目标域名: ${YELLOW}${TARGET_DOMAIN}${NC}"
echo -e "代理服务器: ${YELLOW}${PROXY_URL}${NC}"
echo ""

# 1. DNS 解析诊断
echo -e "${YELLOW}📍 步骤 1: DNS 解析诊断${NC}"
echo -e "${BLUE}——————————————————————————————————${NC}"

echo "🔍 使用系统 DNS 解析:"
SYSTEM_DNS=$(nslookup $TARGET_DOMAIN 2>/dev/null | grep "Address:" | tail -1 | awk '{print $2}')
echo -e "   系统 DNS 结果: ${YELLOW}${SYSTEM_DNS}${NC}"

echo -e "\n🔍 使用 Cloudflare DNS (1.1.1.1) 解析:"
CF_DNS=$(nslookup $TARGET_DOMAIN $CLOUDFLARE_DNS 2>/dev/null | grep "Address:" | tail -1 | awk '{print $2}')
echo -e "   Cloudflare DNS 结果: ${YELLOW}${CF_DNS}${NC}"

echo -e "\n🔍 使用 Google DNS (8.8.8.8) 解析:"
GOOGLE_DNS_RESULT=$(nslookup $TARGET_DOMAIN $GOOGLE_DNS 2>/dev/null | grep "Address:" | tail -1 | awk '{print $2}')
echo -e "   Google DNS 结果: ${YELLOW}${GOOGLE_DNS_RESULT}${NC}"

# DNS 污染判断
echo -e "\n📊 DNS 污染分析:"
if [[ "$SYSTEM_DNS" == "198.18.0."* ]] || [[ "$SYSTEM_DNS" == "127.0.0."* ]]; then
    echo -e "   ${RED}⚠️ 检测到 DNS 污染！系统 DNS 返回了被劫持的 IP${NC}"
    DNS_POISONED=true
else
    echo -e "   ${GREEN}✅ 系统 DNS 解析正常${NC}"
    DNS_POISONED=false
fi

# 2. 网络连通性测试
echo -e "\n${YELLOW}📍 步骤 2: 网络连通性测试${NC}"
echo -e "${BLUE}——————————————————————————————————${NC}"

echo "🔍 测试直连 (不通过代理):"
DIRECT_TEST=$(curl -I -s --max-time 10 --connect-timeout 5 https://$TARGET_DOMAIN 2>&1)
DIRECT_EXIT_CODE=$?

case $DIRECT_EXIT_CODE in
    0)
        echo -e "   ${GREEN}✅ 直连成功${NC}"
        ;;
    35)
        echo -e "   ${RED}❌ SSL 握手失败 (错误代码: 35)${NC}"
        echo -e "   ${YELLOW}   原因：可能是证书问题或连接被重置${NC}"
        ;;
    7)
        echo -e "   ${RED}❌ 无法连接到服务器 (错误代码: 7)${NC}"
        ;;
    28)
        echo -e "   ${RED}❌ 连接超时 (错误代码: 28)${NC}"
        ;;
    *)
        echo -e "   ${RED}❌ 其他连接错误 (错误代码: $DIRECT_EXIT_CODE)${NC}"
        ;;
esac

echo -e "\n🔍 测试通过代理连接:"
PROXY_TEST=$(curl -I -s --max-time 10 --connect-timeout 5 --proxy $PROXY_URL https://$TARGET_DOMAIN 2>&1)
PROXY_EXIT_CODE=$?

case $PROXY_EXIT_CODE in
    0)
        echo -e "   ${GREEN}✅ 代理连接成功${NC}"
        ;;
    35)
        echo -e "   ${RED}❌ SSL 握手失败 (错误代码: 35)${NC}"
        echo -e "   ${YELLOW}   原因：可能是代理服务器 SSL 处理问题${NC}"
        ;;
    7)
        echo -e "   ${RED}❌ 无法连接到代理服务器 (错误代码: 7)${NC}"
        ;;
    *)
        echo -e "   ${RED}❌ 其他代理错误 (错误代码: $PROXY_EXIT_CODE)${NC}"
        ;;
esac

# 3. SSL 证书检查
echo -e "\n${YELLOW}📍 步骤 3: SSL 证书检查${NC}"
echo -e "${BLUE}——————————————————————————————————${NC}"

echo "🔍 尝试获取 SSL 证书信息:"
SSL_CHECK=$(timeout 10 openssl s_client -connect $TARGET_DOMAIN:443 -servername $TARGET_DOMAIN </dev/null 2>/dev/null | openssl x509 -noout -subject -issuer 2>/dev/null)

if [ -n "$SSL_CHECK" ]; then
    echo -e "   ${GREEN}✅ 成功获取 SSL 证书${NC}"
    echo "$SSL_CHECK" | sed 's/^/   /'
else
    echo -e "   ${RED}❌ 无法获取有效的 SSL 证书${NC}"
    echo -e "   ${YELLOW}   可能原因：域名被劫持或证书链不完整${NC}"
fi

# 4. 代理规则检查
echo -e "\n${YELLOW}📍 步骤 4: 代理规则验证${NC}"
echo -e "${BLUE}——————————————————————————————————${NC}"

echo "🔍 测试相关域名的代理连通性:"
test_proxy_domain() {
    local domain=$1
    local description=$2

    local result=$(curl -I -s --max-time 8 --proxy $PROXY_URL https://$domain 2>/dev/null)
    local exit_code=$?

    if [ $exit_code -eq 0 ]; then
        local http_code=$(echo "$result" | head -1 | cut -d' ' -f2)
        echo -e "   ${GREEN}✅${NC} $description (HTTP: $http_code)"
    else
        echo -e "   ${RED}❌${NC} $description (错误: $exit_code)"
    fi
}

test_proxy_domain "cursor.com" "Cursor 主站"
test_proxy_domain "api.openai.com" "OpenAI API"
test_proxy_domain "openai.com" "OpenAI 主站"

# 5. 问题诊断结论
echo -e "\n${YELLOW}📍 步骤 5: 问题诊断结论${NC}"
echo -e "${BLUE}——————————————————————————————————${NC}"

echo -e "\n${BOLD}🎯 诊断结果分析：${NC}"

if $DNS_POISONED; then
    echo -e "${RED}🚨 主要问题：DNS 污染${NC}"
    echo -e "   • ${TARGET_DOMAIN} 被解析到错误的 IP 地址"
    echo -e "   • 这是网络环境问题，不是您的配置问题"
    echo -e "   • 建议解决方案："
    echo -e "     ${YELLOW}1. 在 Clash Verge 中启用 DoH/DoT 防 DNS 污染${NC}"
    echo -e "     ${YELLOW}2. 手动添加 fake-ip 规则绕过 DNS 污染${NC}"
    echo -e "     ${YELLOW}3. 使用国外 DNS 服务器 (1.1.1.1, 8.8.8.8)${NC}"
elif [ $DIRECT_EXIT_CODE -eq 35 ] && [ $PROXY_EXIT_CODE -eq 35 ]; then
    echo -e "${RED}🚨 主要问题：SSL/TLS 协议问题${NC}"
    echo -e "   • 直连和代理都出现 SSL 握手失败"
    echo -e "   • 可能是目标服务器的 TLS 配置问题"
    echo -e "   • 或者是网络中间设备的干扰"
elif [ $PROXY_EXIT_CODE -eq 0 ] && [ $DIRECT_EXIT_CODE -ne 0 ]; then
    echo -e "${GREEN}🎯 代理配置正常${NC}"
    echo -e "   • 通过代理可以正常连接"
    echo -e "   • 直连存在问题（网络限制）"
else
    echo -e "${YELLOW}🤔 复合问题${NC}"
    echo -e "   • 需要进一步排查网络环境和代理配置"
fi

# 6. 推荐解决方案
echo -e "\n${BOLD}🛠️  推荐解决方案：${NC}"

if $DNS_POISONED; then
    echo -e "${YELLOW}针对 DNS 污染问题：${NC}"
    echo -e "1. 在 Clash Verge 配置中添加:"
    echo -e "   ${BLUE}dns:${NC}"
    echo -e "   ${BLUE}  enable: true${NC}"
    echo -e "   ${BLUE}  enhanced-mode: fake-ip${NC}"
    echo -e "   ${BLUE}  nameserver:${NC}"
    echo -e "   ${BLUE}    - 1.1.1.1${NC}"
    echo -e "   ${BLUE}    - 8.8.8.8${NC}"
    echo -e ""
    echo -e "2. 添加 fake-ip 规则:"
    echo -e "   ${BLUE}rules:${NC}"
    echo -e "   ${BLUE}  - DOMAIN-SUFFIX,cursor.sh,🚀 代理${NC}"
    echo -e "   ${BLUE}  - DOMAIN,api.cursor.sh,🚀 代理${NC}"
fi

echo -e "\n${YELLOW}通用解决步骤：${NC}"
echo -e "1. 重启 Clash Verge 以应用新的 DNS 配置"
echo -e "2. 清除系统 DNS 缓存: ${BLUE}sudo systemctl restart systemd-resolved${NC}"
echo -e "3. 重新运行验证脚本: ${BLUE}./verify_proxy.sh${NC}"

echo -e "\n${BLUE}当前时间: $(date '+%Y-%m-%d %H:%M:%S')${NC}"
echo -e "${BLUE}诊断完成！${NC}"

exit 0
