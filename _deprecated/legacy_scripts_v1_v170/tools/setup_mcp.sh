#!/bin/bash
# ============================================
# MCP 工具链安装脚本
# ============================================
# 用途: 一键安装所有 MCP 依赖和配置
# 执行: bash scripts/ops/setup_mcp.sh
# ============================================

set -e

# 加载 nvm 环境
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && source "$NVM_DIR/nvm.sh"

PROJECT_ROOT="/home/xupeng/projects/FootballPrediction"
cd "$PROJECT_ROOT"

echo "============================================"
echo "MCP 工具链安装"
echo "============================================"

# 1. 安装 Node.js 依赖
echo ""
echo "[1/4] 安装 Node.js MCP 依赖..."
npm install -g @modelcontextprotocol/server-filesystem @modelcontextprotocol/server-postgres 2>/dev/null || true

# 2. 安装 Python MCP SDK
echo ""
echo "[2/4] 安装 Python MCP SDK..."
pip install mcp --quiet

# 3. 创建 PostgreSQL 只读用户
echo ""
echo "[3/4] 配置 PostgreSQL 只读用户..."
echo "请在数据库中执行以下 SQL (如果尚未执行):"
echo ""
cat deploy/docker/init_claude_reader.sql
echo ""

# 4. 设置 MCP 服务器脚本权限
echo ""
echo "[4/4] 设置脚本权限..."
chmod +x mcp_servers/*.py 2>/dev/null || true

echo ""
echo "============================================"
echo "安装完成!"
echo "============================================"
echo ""
echo "MCP 配置文件: .claude/mcp-config.json"
echo ""
echo "可用服务:"
echo "  - filesystem  : 项目文件读写"
echo "  - postgres    : 只读数据库查询"
echo "  - pytest      : 测试执行"
echo "  - docker      : 容器管理"
echo "  - playwright  : 浏览器自动化"
echo ""
echo "下一步:"
echo "  1. 重启 Claude Code 以加载 MCP 配置"
echo "  2. 运行验证: bash scripts/ops/verify_mcp.sh"
echo ""
