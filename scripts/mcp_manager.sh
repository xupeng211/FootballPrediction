#!/bin/bash
# MCP服务器管理脚本
# 用于启动、停止和管理MCP服务器

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log() {
    echo -e "${2}$(date '+%Y-%m-%d %H:%M:%S') $1${NC}"
}

# 项目根目录
PROJECT_ROOT="/home/user/projects/FootballPrediction"
cd "$PROJECT_ROOT"

# MCP服务器列表
MCP_SERVERS=("postgres" "redis" "filesystem")

# 检查MCP服务器状态
check_status() {
    log "🔍 检查MCP服务器状态..."

    for server in "${MCP_SERVERS[@]}"; do
        if pgrep -f "mcp_servers/${server}_server.py" > /dev/null; then
            echo -e "  ${GREEN}✓${NC} $server server: ${GREEN}running${NC}"
        else
            echo -e "  ${RED}✗${NC} $server server: ${RED}stopped${NC}"
        fi
    done

    echo
}

# 启动所有MCP服务器
start_all() {
    log "🚀 启动所有MCP服务器..."

    for server in "${MCP_SERVERS[@]}"; do
        echo -n "  Starting $server server... "
        nohup python "mcp_servers/${server}_server.py" > "logs/${server}_server.log" 2>&1 &
        echo -e "${GREEN}✓${NC} PID: $!"
    done

    echo
    log "📝 所有MCP服务器已启动"
    log "📊 查看状态: ./scripts/mcp_manager.sh status"
    log "📋 查看日志: ./scripts/mcp_manager.sh logs"
}

# 停止所有MCP服务器
stop_all() {
    log "🛑 停止所有MCP服务器..."

    for server in "${MCP_SERVERS[@]}"; do
        echo -n "  Stopping $server server... "
        if pkill -f "mcp_servers/${server}_server.py"; then
            echo -e "${GREEN}✓${NC} Stopped"
        else
            echo -e "${YELLOW}⚠ $server server was not running${NC}"
        fi
    done

    echo
    log "📝 所有MCP服务器已停止"
}

# 启动单个MCP服务器
start_single() {
    local server=$1
    if [[ ! " ${MCP_SERVERS[@]} " =~ $server ]]; then
        echo -e "${RED}错误: 未知的服务器 '$server'${NC}"
        echo "可用的服务器: ${MCP_SERVERS[*]}"
        return 1
    fi

    log "🚀 启动 $server MCP服务器..."

    # 创建日志目录
    mkdir -p logs

    # 检查是否已经运行
    if pgrep -f "mcp_servers/${server}_server.py" > /dev/null; then
        echo -e "${YELLOW}⚠ $server server is already running${NC}"
        return 0
    fi

    # 启动服务器
    nohup python "mcp_servers/${server}_server.py" > "logs/${server}_server.log" 2>&1 &
    local pid=$!

    echo -e "${GREEN}✓${NC} $server server started (PID: $pid)"

    # 等待启动完成
    sleep 2

    # 检查是否成功启动
    if pgrep -f "mcp_servers/${server}_server.py" > /dev/null; then
        echo -e "${GREEN}✅${NC} $server server is running successfully"
    else
        echo -e "${RED}❌${NC} Failed to start $server server"
        echo "Check logs for details: tail logs/${server}_server.log"
        return 1
    fi
}

# 停止单个MCP服务器
stop_single() {
    local server=$1
    if [[ ! " ${MCP_SERVERS[@]} " =~ $server ]]; then
        echo -e "${RED}错误: 未知的服务器 '$server'${NC}"
        echo "可用的服务器: ${MCP_SERVERS[*]}"
        return 1
    fi

    log "🛑 停止 $server MCP服务器..."

    if pkill -f "mcp_servers/${server}_server.py"; then
        echo -e "${GREEN}✓${NC} $server server stopped"
    else
        echo -e "${YELLOW}⚠ $server server was not running${NC}"
    fi
}

# 查看服务器状态
status() {
    log "📊 MCP服务器状态"
    check_status
}

# 查看日志
logs() {
    local server=$1

    if [ -n "$server" ] && [[ " ${MCP_SERVERS[@]} " =~ $server ]]; then
        log "📋 查看 $server 服务器日志 (最后50行):"
        tail -50 "logs/${server}_server.log"
    else
        log "📋 查看所有服务器日志 (最后20行):"
        for server in "${MCP_SERVERS[@]}"; do
            echo
            echo -e "${BLUE}=== $server 服务器日志 ===${NC}"
            tail -20 "logs/${server}_server.log" || echo "No logs found"
        done
    fi
}

# 重启所有服务器
restart() {
    log "🔄 重启所有MCP服务器..."
    stop_all
    sleep 2
    start_all
}

# 重启单个服务器
restart_single() {
    local server=$1
    log "🔄 重启 $server MCP服务器..."
    stop_single "$server"
    sleep 2
    start_single "$server"
}

# 测试服务器连接
test() {
    log "🧪 测试MCP服务器连接..."

    # 测试PostgreSQL连接
    echo -n "  Testing PostgreSQL connection... "
    if python -c "
import sys
sys.path.append('mcp_servers')
from postgres_server import PostgresMCPServer
import asyncio

async def test():
    server = PostgresMCPServer()
    if await server.connect():
        print('SUCCESS')
        return True
    else:
        print('FAILED')
        return False

result = asyncio.run(test())
sys.exit(0 if result else 1)
" 2>/dev/null; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗${NC}"
    fi

    # 测试Redis连接
    echo -n "  Testing Redis connection... "
    if python -c "
import sys
sys.path.append('mcp_servers')
from redis_server import RedisMCPServer

server = RedisMCPServer()
if server.connect():
    print('SUCCESS')
else:
    print('FAILED')
" 2>/dev/null; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗${NC}"
    fi

    # 测试文件系统访问
    echo -n "  Testing file system access... "
    if [ -f "mcp_servers/postgres_server.py" ]; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗${NC}"
    fi

    echo
    log "📊 测试完成"
}

# 清理日志
clean_logs() {
    log "🧹 清理MCP服务器日志..."

    for server in "${MCP_SERVERS[@]}"; do
        if [ -f "logs/${server}_server.log" ]; then
            echo -n "  Cleaning $server logs... "
            > "logs/${server}_server.log"
            echo -e "${GREEN}✓${NC}"
        fi
    done

    echo
    log "📝 日志清理完成"
}

# 创建启动配置文件
create_config() {
    log "📝 创建MCP启动配置..."

    cat > .env.mcp << 'EOF'
# MCP服务器配置
# 数据库配置
DB_HOST=localhost
DB_PORT=5432
DB_NAME=football_prediction_dev
DB_USER=football_user
DB_PASSWORD=football_pass

# Redis配置
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# 日志配置
MCP_LOG_LEVEL=INFO
LOG_DIR=logs
EOF

    echo -e "${GREEN}✓${NC} .env.mcp 已创建"
    echo -e "${YELLOW}⚠${NC} 请根据实际环境修改配置"
}

# 显示帮助信息
show_help() {
    cat << 'EOF'
MCP服务器管理脚本

用法: ./scripts/mcp_manager.sh [命令] [选项]

命令:
    start       启动所有MCP服务器
    stop        停止所有MCP服务器
    restart     重启所有MCP服务器
    status      查看服务器状态
    logs        查看日志
    test        测试服务器连接
    clean-logs  清理日志文件
    config      创建配置文件

单个服务器管理:
    start [server]     启动指定服务器
    stop [server]      停动指定服务器
    restart [server]   重启指定服务器
    logs [server]      查看指定服务器日志

可用服务器:
    postgres    PostgreSQL数据库服务器
    redis        Redis缓存服务器
    filesystem   文件系统服务器

示例:
    ./scripts/mcp_manager.sh start              # 启动所有服务器
    ./scripts/mcp_manager.sh start postgres      # 只启动PostgreSQL服务器
    ./scripts/mcp_manager.sh logs redis           # 查看Redis服务器日志
    ./scripts/mcp_manager.sh test                 # 测试所有服务器连接

EOF
}

# 主程序
case "${1:-help}" in
    start)
        start_all
        ;;
    stop)
        stop_all
        ;;
    restart)
        restart
        ;;
    status)
        status
        ;;
    logs)
        logs "$2"
        ;;
    test)
        test
        ;;
    clean-logs)
        clean_logs
        ;;
    config)
        create_config
        ;;
    start_single)
        if [ -n "$2" ]; then
            start_single "$2"
        else
            echo -e "${RED}错误: 请指定服务器名称${NC}"
            show_help
            exit 1
        fi
        ;;
    stop_single)
        if [ -n "$2" ]; then
            stop_single "$2"
        else
            echo -e "${RED}错误: 请指定服务器名称${NC}"
            show_help
            exit 1
        fi
        ;;
    restart_single)
        if [ -n "$2" ]; then
            restart_single "$2"
        else
            echo -e "${RED}错误: 请指定服务器名称${NC}"
            show_help
            exit 1
        fi
        ;;
    *)
        show_help
        exit 0
        ;;
esac