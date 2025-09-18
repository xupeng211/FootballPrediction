#!/bin/bash

# ==================================================
# 🔍 Clash Verge 代理配置验证脚本
# 用途：验证 Cursor/OpenAI/Anthropic 域名代理连通性
# 环境：WSL2 + Clash Verge (代理端口: 7890)
# ==================================================

# 配置变量
PROXY_HOST="172.25.16.1"
PROXY_PORT="7890"
PROXY_URL="http://${PROXY_HOST}:${PROXY_PORT}"
TIMEOUT=15
TOTAL_TESTS=0
PASSED_TESTS=0

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# 输出标题
echo -e "${BLUE}${BOLD}================================${NC}"
echo -e "${BLUE}${BOLD}🔍 代理连通性验证工具${NC}"
echo -e "${BLUE}${BOLD}================================${NC}"
echo -e "代理服务器: ${YELLOW}${PROXY_URL}${NC}"
echo -e "连接超时: ${YELLOW}${TIMEOUT}s${NC}"
echo ""

# 测试函数
test_url() {
    local url="$1"
    local description="$2"
    local expected_pattern="$3"

    TOTAL_TESTS=$((TOTAL_TESTS + 1))

    printf "%-50s" "🌐 测试 ${description}..."

    # 执行 curl 请求
    local response
    local http_code
    local curl_exit_code

    response=$(curl -s -I \
        --max-time ${TIMEOUT} \
        --proxy "${PROXY_URL}" \
        --write-out "HTTPSTATUS:%{http_code}" \
        "${url}" 2>/dev/null)

    curl_exit_code=$?
    http_code=$(echo "$response" | tail -n1 | sed 's/.*HTTPSTATUS://')

    # 判断连接结果
    if [ $curl_exit_code -eq 0 ]; then
        if [[ "$http_code" =~ ^[2-4][0-9][0-9]$ ]]; then
            echo -e "${GREEN}✅ 成功${NC} (HTTP: $http_code)"
            PASSED_TESTS=$((PASSED_TESTS + 1))
            return 0
        else
            echo -e "${RED}❌ 失败${NC} (HTTP: $http_code)"
            return 1
        fi
    else
        # 根据 curl 退出代码提供具体错误信息
        case $curl_exit_code in
            7)  echo -e "${RED}❌ 失败${NC} (无法连接到代理服务器)";;
            28) echo -e "${RED}❌ 失败${NC} (连接超时)";;
            56) echo -e "${RED}❌ 失败${NC} (网络接收数据失败)";;
            *)  echo -e "${RED}❌ 失败${NC} (错误代码: $curl_exit_code)";;
        esac
        return 1
    fi
}

# 检查代理服务器是否可达
echo -e "${YELLOW}📡 检查代理服务器连通性...${NC}"
if timeout 5 bash -c "cat < /dev/null > /dev/tcp/${PROXY_HOST}/${PROXY_PORT}" 2>/dev/null; then
    echo -e "${GREEN}✅ 代理服务器可达 (${PROXY_HOST}:${PROXY_PORT})${NC}"
else
    echo -e "${RED}❌ 代理服务器不可达！请检查 Clash Verge 是否正常运行${NC}"
    echo ""
    echo -e "${YELLOW}💡 故障排除建议：${NC}"
    echo -e "   1. 确认 Clash Verge 正在运行"
    echo -e "   2. 检查代理端口是否为 7890"
    echo -e "   3. 确认 WSL2 能访问 Windows 主机"
    exit 1
fi

echo ""
echo -e "${YELLOW}🚀 开始测试目标服务连通性...${NC}"
echo ""

# 执行连通性测试
test_url "https://api.cursor.sh" "Cursor API 服务"
test_url "https://cursor.com" "Cursor 官网"
test_url "https://api.openai.com/v1/models" "OpenAI API 服务"
test_url "https://api.anthropic.com/v1/complete" "Anthropic API 服务"

# 额外测试一些可能相关的域名
echo ""
echo -e "${YELLOW}🔍 附加连通性测试...${NC}"
test_url "https://cursor.blob.core.windows.net" "Cursor 资源服务"
test_url "https://openai.com" "OpenAI 官网"
test_url "https://anthropic.com" "Anthropic 官网"

# 显示测试结果汇总
echo ""
echo -e "${BLUE}${BOLD}================================${NC}"
echo -e "${BLUE}${BOLD}📊 测试结果汇总${NC}"
echo -e "${BLUE}${BOLD}================================${NC}"

if [ $PASSED_TESTS -eq $TOTAL_TESTS ]; then
    echo -e "${GREEN}${BOLD}🎉 全部测试通过！(${PASSED_TESTS}/${TOTAL_TESTS})${NC}"
    echo -e "${GREEN}代理配置正确，Cursor 应该能正常工作${NC}"
else
    echo -e "${YELLOW}⚠️  部分测试失败 (${PASSED_TESTS}/${TOTAL_TESTS})${NC}"
    echo -e "${YELLOW}建议检查 Clash Verge 的代理规则配置${NC}"
fi

echo ""
echo -e "${BLUE}${BOLD}🛠️  下一步建议：${NC}"
if [ $PASSED_TESTS -eq $TOTAL_TESTS ]; then
    echo -e "   ${GREEN}✓${NC} 在 Cursor 中测试 AI 对话功能"
    echo -e "   ${GREEN}✓${NC} 如果仍有问题，检查 Cursor 内部代理设置"
else
    echo -e "   ${RED}1.${NC} 检查 Clash Verge 规则是否包含失败的域名"
    echo -e "   ${RED}2.${NC} 确认代理规则放在配置文件最顶部"
    echo -e "   ${RED}3.${NC} 重启 Clash Verge 服务"
    echo -e "   ${RED}4.${NC} 重新运行此脚本验证"
fi

echo ""
echo -e "${BLUE}当前时间: $(date '+%Y-%m-%d %H:%M:%S')${NC}"

exit 0
