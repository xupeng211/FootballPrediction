#!/bin/bash
# ============================================
# MCP 工具链验证脚本
# ============================================
# 用途: 验证所有 MCP 服务是否正常工作
# 执行: bash scripts/ops/verify_mcp.sh
# ============================================

set -e

# 加载 nvm 环境
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && source "$NVM_DIR/nvm.sh"

PROJECT_ROOT="/home/xupeng/projects/FootballPrediction"
cd "$PROJECT_ROOT"

echo "============================================"
echo "MCP 工具链验证"
echo "============================================"

PASS=0
FAIL=0

# 验证函数
check_pass() {
    echo "  ✓ $1"
    PASS=$((PASS + 1))
}

check_fail() {
    echo "  ✗ $1"
    echo "    原因: $2"
    FAIL=$((FAIL + 1))
}

# 1. Filesystem MCP
echo ""
echo "[1/4] Filesystem MCP"

# 检查 npx 是否可用
if command -v npx &>/dev/null; then
    check_pass "npx 命令可用"
else
    check_fail "npx 命令不可用" "安装 Node.js"
fi

# 检查 npm 是否能解析包名
if npm view @modelcontextprotocol/server-filesystem version &>/dev/null; then
    check_pass "filesystem MCP 包存在 (v$(npm view @modelcontextprotocol/server-filesystem version))"
else
    check_fail "无法获取 filesystem MCP 包信息" "检查网络连接"
fi

if [ -d "$PROJECT_ROOT" ]; then
    check_pass "项目目录存在: $PROJECT_ROOT"
else
    check_fail "项目目录不存在" "$PROJECT_ROOT"
fi

# 2. PostgreSQL MCP
echo ""
echo "[2/4] PostgreSQL MCP"

# 检查 npm 是否能解析包名
if npm view @modelcontextprotocol/server-postgres version &>/dev/null; then
    check_pass "postgres MCP 包存在 (v$(npm view @modelcontextprotocol/server-postgres version))"
else
    check_fail "无法获取 postgres MCP 包信息" "检查网络连接"
fi

# 检查数据库是否运行
if docker-compose -f docker-compose.yml ps db 2>/dev/null | grep -q "Up"; then
    check_pass "PostgreSQL 容器运行中"
else
    check_fail "PostgreSQL 容器未运行" "运行: docker-compose up -d db"
fi

# 检查只读用户
if docker-compose -f docker-compose.yml exec -T db psql -U football_user -d football_db -c "\du claude_reader" 2>/dev/null | grep -q "claude_reader"; then
    check_pass "只读用户 claude_reader 存在"
else
    check_fail "只读用户不存在" "执行: deploy/docker/init_claude_reader.sql"
fi

# 测试只读用户连接
if docker-compose -f docker-compose.yml exec -T db psql -U claude_reader -d football_db -c "SELECT 1" &>/dev/null; then
    check_pass "只读用户连接成功"
else
    check_fail "只读用户连接失败" "检查密码或权限配置"
fi

# 3. pytest MCP
echo ""
echo "[3/4] pytest MCP"

# 检查 Python MCP SDK (在 dev 容器中)
if docker-compose -f docker-compose.yml exec -T dev python -c "import mcp" 2>/dev/null; then
    check_pass "Python MCP SDK 已安装 (dev 容器)"
else
    check_fail "Python MCP SDK 未安装" "运行: docker-compose exec dev pip install mcp"
fi

if [ -f "mcp_servers/pytest_server.py" ]; then
    check_pass "pytest_server.py 存在"
else
    check_fail "pytest_server.py 不存在" "检查 mcp_servers 目录"
fi

if [ -f "mcp_servers/docker_server.py" ]; then
    check_pass "docker_server.py 存在"
else
    check_fail "docker_server.py 不存在" "检查 mcp_servers 目录"
fi

# 检查 MCP 服务器脚本语法
if python3 -m py_compile mcp_servers/pytest_server.py 2>/dev/null; then
    check_pass "pytest_server.py 语法正确"
else
    check_fail "pytest_server.py 语法错误" "检查 Python 语法"
fi

if python3 -m py_compile mcp_servers/docker_server.py 2>/dev/null; then
    check_pass "docker_server.py 语法正确"
else
    check_fail "docker_server.py 语法错误" "检查 Python 语法"
fi

# 4. Docker MCP
echo ""
echo "[4/4] Docker MCP"

if docker --version &>/dev/null; then
    check_pass "Docker 已安装: $(docker --version | head -1)"
else
    check_fail "Docker 未安装" "安装 Docker"
fi

if docker-compose --version &>/dev/null; then
    check_pass "Docker Compose 已安装"
else
    check_fail "Docker Compose 未安装" "安装 Docker Compose"
fi

# 检查 docker-compose.yml
if [ -f "docker-compose.yml" ]; then
    check_pass "docker-compose.yml 存在"
else
    check_fail "docker-compose.yml 不存在"
fi

# 5. MCP 配置文件
echo ""
echo "[5/5] MCP 配置文件"

if [ -f ".claude/mcp-config.json" ]; then
    check_pass "mcp-config.json 存在"
    # 验证 JSON 格式
    if python3 -c "import json; json.load(open('.claude/mcp-config.json'))" 2>/dev/null; then
        check_pass "mcp-config.json JSON 格式正确"
    else
        check_fail "mcp-config.json JSON 格式错误" "检查 JSON 语法"
    fi
else
    check_fail "mcp-config.json 不存在" "运行 setup_mcp.sh"
fi

# 汇总
echo ""
echo "============================================"
echo "验证结果: $PASS 通过, $FAIL 失败"
echo "============================================"

if [ $FAIL -eq 0 ]; then
    echo "✓ 所有 MCP 服务验证通过!"
    echo ""
    echo "下一步: 重启 Claude Code 以加载 MCP 配置"
    exit 0
else
    echo "✗ 部分验证失败，请检查上述错误"
    exit 1
fi
