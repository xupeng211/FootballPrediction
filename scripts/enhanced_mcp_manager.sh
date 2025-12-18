#!/bin/bash
# ==============================================
# Enhanced MCP Manager with System Monitoring
# 增强版MCP管理器 - 包含系统监控功能
# ==============================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

# 脚本信息
SCRIPT_NAME="Enhanced MCP Manager v2.0"
DESCRIPTION="MCP服务器管理与系统监控工具"

# MCP服务器配置
MCP_SERVERS=(
    "postgres:PostgreSQL数据库服务器"
    "redis:Redis缓存服务器"
    "filesystem:文件系统服务器"
    "system-monitor:系统监控服务器"
)

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${PURPLE}[STEP]${NC} $1"
}

log_command() {
    echo -e "${CYAN}[CMD]${NC} $1"
}

# 显示帮助信息
show_help() {
    cat << EOF
$SCRIPT_NAME - $DESCRIPTION

用法: $0 <命令> [选项]

命令:
    start              启动所有MCP服务器
    stop               停止所有MCP服务器
    restart            重启所有MCP服务器
    status             查看MCP服务器状态
    logs               查看MCP服务器日志
    test               测试MCP服务器功能
    monitor            系统监控面板
    benchmark          性能基准测试
    health             健康检查
    config             配置验证

服务器管理:
    start_single <name>    启动单个MCP服务器
    stop_single <name>     停止单个MCP服务器
    restart_single <name>  重启单个MCP服务器

监控功能:
    system_metrics      显示系统性能指标
    docker_metrics      显示Docker容器指标
    bottlenecks         分析资源瓶颈
    connectivity       网络连通性测试

其他选项:
    -h, --help          显示此帮助信息
    -v, --verbose       详细输出模式
    -q, --quiet         静默模式

MCP服务器列表:
EOF
    for server in "${MCP_SERVERS[@]}"; do
        name=$(echo $server | cut -d: -f1)
        desc=$(echo $server | cut -d: -f2)
        echo "    $name        $desc"
    done
}

# 检查Python环境
check_python_environment() {
    log_step "检查Python环境..."

    if ! command -v python3 &> /dev/null; then
        log_error "Python3未安装"
        exit 1
    fi

    # 检查必要的依赖
    python3 -c "
import sys
required_packages = ['asyncpg', 'psutil', 'mcp']
missing = []
for pkg in required_packages:
    try:
        __import__(pkg)
    except ImportError:
        missing.append(pkg)
if missing:
    print(f'缺少依赖: {missing}')
    sys.exit(1)
print('Python环境检查通过')
" || {
        log_error "缺少必要的Python依赖"
        log_info "请安装: pip install asyncpg psutil mcp"
        exit 1
    }

    log_success "Python环境检查通过"
}

# 检查MCP配置
check_mcp_config() {
    log_step "检查MCP配置..."

    if [ ! -f ".claude/settings.json" ]; then
        log_error "MCP配置文件不存在: .claude/settings.json"
        exit 1
    fi

    # 验证配置文件格式
    if ! python3 -m json.tool .claude/settings.json > /dev/null 2>&1; then
        log_error "MCP配置文件格式错误"
        exit 1
    fi

    # 检查MCP服务器配置
    mcp_count=$(python3 -c "
import json
with open('.claude/settings.json', 'r') as f:
    config = json.load(f)
mcp_servers = config.get('mcpServers', {})
print(len(mcp_servers))
")

    if [ "$mcp_count" -eq 0 ]; then
        log_warning "未配置MCP服务器"
    else
        log_success "发现 $mcp_count 个MCP服务器配置"
    fi
}

# 获取MCP服务器状态
get_mcp_server_status() {
    local server_name=$1
    local pids=$(pgrep -f "mcp_servers/${server_name}_server.py" 2>/dev/null || true)

    if [ -n "$pids" ]; then
        echo "running"
        return 0
    else
        echo "stopped"
        return 1
    fi
}

# 启动单个MCP服务器
start_mcp_server() {
    local server_name=$1
    local server_file="mcp_servers/${server_name}_server.py"

    if [ ! -f "$server_file" ]; then
        log_error "MCP服务器文件不存在: $server_file"
        return 1
    fi

    log_info "启动MCP服务器: $server_name"

    # 设置环境变量
    export PYTHONPATH="${PWD}:${PYTHONPATH:-}"

    # 启动服务器
    nohup python3 "$server_file" > "logs/mcp_${server_name}.log" 2>&1 &
    local pid=$!

    # 等待启动
    sleep 2

    if kill -0 $pid 2>/dev/null; then
        log_success "MCP服务器 $server_name 启动成功 (PID: $pid)"
        echo $pid > "logs/mcp_${server_name}.pid"
        return 0
    else
        log_error "MCP服务器 $server_name 启动失败"
        return 1
    fi
}

# 停止单个MCP服务器
stop_mcp_server() {
    local server_name=$1
    local pid_file="logs/mcp_${server_name}.pid"

    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if kill -0 $pid 2>/dev/null; then
            log_info "停止MCP服务器: $server_name (PID: $pid)"
            kill $pid
            sleep 1

            # 强制停止如果还在运行
            if kill -0 $pid 2>/dev/null; then
                kill -9 $pid
            fi

            log_success "MCP服务器 $server_name 已停止"
        else
            log_warning "MCP服务器 $server_name 未运行"
        fi
        rm -f "$pid_file"
    else
        log_warning "未找到MCP服务器 $server_name 的PID文件"

        # 尝试通过进程名停止
        local pids=$(pgrep -f "mcp_servers/${server_name}_server.py" 2>/dev/null || true)
        if [ -n "$pids" ]; then
            log_info "发现运行中的MCP服务器 $server_name，正在停止..."
            echo "$pids" | xargs kill
            log_success "MCP服务器 $server_name 已停止"
        fi
    fi
}

# 启动所有MCP服务器
start_all_servers() {
    log_step "启动所有MCP服务器..."

    # 创建日志目录
    mkdir -p logs

    local success_count=0
    local total_count=${#MCP_SERVERS[@]}

    for server in "${MCP_SERVERS[@]}"; do
        server_name=$(echo $server | cut -d: -f1)
        if start_mcp_server "$server_name"; then
            ((success_count++))
        fi
    done

    if [ $success_count -eq $total_count ]; then
        log_success "所有MCP服务器启动成功 ($success_count/$total_count)"
    else
        log_warning "部分MCP服务器启动失败 ($success_count/$total_count)"
    fi
}

# 停止所有MCP服务器
stop_all_servers() {
    log_step "停止所有MCP服务器..."

    for server in "${MCP_SERVERS[@]}"; do
        server_name=$(echo $server | cut -d: -f1)
        stop_mcp_server "$server_name"
    done

    log_success "所有MCP服务器已停止"
}

# 查看MCP服务器状态
show_server_status() {
    log_step "查看MCP服务器状态..."

    echo ""
    printf "%-20s %-10s %-10s %s\n" "服务器名称" "状态" "PID" "描述"
    printf "%-20s %-10s %-10s %s\n" "--------------------" "----------" "----------" "--------------------"

    for server in "${MCP_SERVERS[@]}"; do
        server_name=$(echo $server | cut -d: -f1)
        server_desc=$(echo $server | cut -d: -f2)

        status=$(get_mcp_server_status "$server_name")
        status_color=""

        if [ "$status" = "running" ]; then
            status_color="${GREEN}运行中${NC}"
            if [ -f "logs/mcp_${server_name}.pid" ]; then
                pid=$(cat "logs/mcp_${server_name}.pid")
            else
                pid="-"
            fi
        else
            status_color="${RED}已停止${NC}"
            pid="-"
        fi

        printf "%-20s %-20s %-10s %s\n" "$server_name" "$status_color" "$pid" "$server_desc"
    done

    echo ""
}

# 查看MCP服务器日志
show_server_logs() {
    local server_name=${1:-""}

    if [ -n "$server_name" ]; then
        log_step "查看MCP服务器日志: $server_name"
        local log_file="logs/mcp_${server_name}.log"
        if [ -f "$log_file" ]; then
            tail -f "$log_file"
        else
            log_error "日志文件不存在: $log_file"
        fi
    else
        log_step "查看所有MCP服务器日志..."

        for server in "${MCP_SERVERS[@]}"; do
            server_name=$(echo $server | cut -d: -f1)
            local log_file="logs/mcp_${server_name}.log"

            if [ -f "$log_file" ]; then
                echo ""
                log_info "=== $server_name 日志 (最后10行) ==="
                tail -10 "$log_file"
            else
                log_warning "未找到 $server_name 的日志文件"
            fi
        done
    fi
}

# 测试MCP服务器功能
test_mcp_servers() {
    log_step "测试MCP服务器功能..."

    echo ""
    log_info "测试PostgreSQL MCP服务器..."
    python3 -c "
import sys
sys.path.append('mcp_servers')
try:
    from postgres_server import PostgresMCPServer
    server = PostgresMCPServer()
    print('✅ PostgreSQL MCP服务器导入成功')
    print(f'   数据库配置: {server.db_config}')
except Exception as e:
    print(f'❌ PostgreSQL MCP服务器测试失败: {e}')
"

    echo ""
    log_info "测试Redis MCP服务器..."
    python3 -c "
import sys
sys.path.append('mcp_servers')
try:
    from redis_server import RedisMCPServer
    server = RedisMCPServer()
    print('✅ Redis MCP服务器导入成功')
except Exception as e:
    print(f'❌ Redis MCP服务器测试失败: {e}')
"

    echo ""
    log_info "测试FileSystem MCP服务器..."
    python3 -c "
import sys
sys.path.append('mcp_servers')
try:
    from filesystem_server import FileSystemMCPServer
    server = FileSystemMCPServer()
    print('✅ FileSystem MCP服务器导入成功')
except Exception as e:
    print(f'❌ FileSystem MCP服务器测试失败: {e}')
"

    echo ""
    log_info "测试System Monitor MCP服务器..."
    python3 -c "
import sys
sys.path.append('mcp_servers')
try:
    from system_monitor_server import SystemMonitorMCPServer
    server = SystemMonitorMCPServer()
    print('✅ System Monitor MCP服务器导入成功')
except Exception as e:
    print(f'❌ System Monitor MCP服务器测试失败: {e}')
"

    echo ""
}

# 系统监控面板
show_monitoring_panel() {
    log_step "启动系统监控面板..."

    # 检查系统监控MCP服务器是否运行
    if [ "$(get_mcp_server_status system-monitor)" != "running" ]; then
        log_warning "System Monitor MCP服务器未运行，正在启动..."
        start_mcp_server "system-monitor"
    fi

    echo ""
    log_info "=== 系统监控面板 ==="

    # 系统指标
    echo ""
    log_info "📊 系统性能指标:"
    python3 -c "
import sys
sys.path.append('mcp_servers')
try:
    from system_monitor_server import SystemMonitorMCPServer
    import asyncio

    async def get_metrics():
        server = SystemMonitorMCPServer()
        metrics = await server.get_system_metrics()

        print(f'CPU使用率: {metrics.get(\"cpu\", {}).get(\"usage_percent\", 0):.1f}%')
        print(f'内存使用率: {metrics.get(\"memory\", {}).get(\"percent\", 0):.1f}%')
        print(f'磁盘使用率: {metrics.get(\"disk\", {}).get(\"percent\", 0):.1f}%')
        print(f'网络发送: {metrics.get(\"network\", {}).get(\"bytes_sent\", 0) / 1024 / 1024:.1f} MB')
        print(f'网络接收: {metrics.get(\"network\", {}).get(\"bytes_recv\", 0) / 1024 / 1024:.1f} MB')

    asyncio.run(get_metrics())
except Exception as e:
    print(f'获取系统指标失败: {e}')
"

    # Docker容器指标
    echo ""
    log_info "🐳 Docker容器指标:"
    if command -v docker &> /dev/null; then
        docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}"
    else
        echo "Docker未安装或未运行"
    fi

    # 资源瓶颈分析
    echo ""
    log_info "⚠️ 资源瓶颈分析:"
    python3 -c "
import sys
sys.path.append('mcp_servers')
try:
    from system_monitor_server import SystemMonitorMCPServer
    import asyncio

    async def analyze():
        server = SystemMonitorMCPServer()
        analysis = await server.analyze_resource_bottlenecks()

        bottlenecks = analysis.get('bottlenecks', [])
        if bottlenecks:
            for bottleneck in bottlenecks:
                severity = bottleneck.get('severity', 'unknown')
                message = bottleneck.get('message', 'No message')
                print(f'  {severity.upper()}: {message}')
        else:
            print('  ✅ 未发现明显瓶颈')

    asyncio.run(analyze())
except Exception as e:
    print(f'瓶颈分析失败: {e}')
"

    echo ""
    log_info "提示: 使用 '$0 test connectivity' 测试网络连通性"
}

# 性能基准测试
run_benchmark() {
    log_step "执行性能基准测试..."

    echo ""
    log_info "🚀 系统性能基准测试:"

    # CPU基准测试
    log_info "CPU基准测试 (10秒)..."
    cpu_result=$(python3 -c "
import time
import multiprocessing
start = time.time()
end = start + 10
count = 0
while time.time() < end:
    count += 1
    sum(i*i for i in range(1000))
print(f'CPU计算次数: {count}')
")
    echo "结果: $cpu_result"

    # 内存基准测试
    log_info "内存基准测试..."
    mem_result=$(python3 -c "
import time
import psutil
import gc

start = time.time()
mem = psutil.virtual_memory()
start_mem = mem.available

# 分配和释放内存
data = []
for i in range(1000):
    data.append([0] * 10000)

gc.collect()

end = time.time()
mem_after = psutil.virtual_memory().available
mem_used = (start_mem - mem_after) / 1024 / 1024

print(f'内存分配: {mem_used:.1f} MB')
print(f'耗时: {(end - start):.3f} 秒')
")
    echo "结果: $mem_result"

    # 磁盘I/O基准测试
    log_info "磁盘I/O基准测试..."
    disk_result=$(python3 -c "
import time
import tempfile
import os

start = time.time()
with tempfile.NamedTemporaryFile(mode='w+b', delete=True) as f:
    # 写入测试
    data = b'x' * (1024 * 1024)  # 1MB
    for _ in range(100):  # 100MB
        f.write(data)

    # 读取测试
    f.seek(0)
    content = f.read()

end = time.time()

print(f'磁盘I/O: 100MB')
print(f'耗时: {(end - start):.3f} 秒')
")
    echo "结果: $disk_result"

    echo ""
    log_success "性能基准测试完成"
}

# 健康检查
run_health_check() {
    log_step "执行健康检查..."

    local issues=0

    echo ""
    log_info "🔍 系统健康检查:"

    # 检查Python环境
    if check_python_environment >/dev/null 2>&1; then
        log_success "✅ Python环境正常"
    else
        log_error "❌ Python环境异常"
        ((issues++))
    fi

    # 检查MCP配置
    if check_mcp_config >/dev/null 2>&1; then
        log_success "✅ MCP配置正常"
    else
        log_error "❌ MCP配置异常"
        ((issues++))
    fi

    # 检查MCP服务器状态
    local running_servers=0
    for server in "${MCP_SERVERS[@]}"; do
        server_name=$(echo $server | cut -d: -f1)
        if [ "$(get_mcp_server_status "$server_name")" = "running" ]; then
            ((running_servers++))
        fi
    done

    if [ $running_servers -gt 0 ]; then
        log_success "✅ $running_servers/${#MCP_SERVERS[@]} MCP服务器运行中"
    else
        log_warning "⚠️ 没有MCP服务器运行"
        ((issues++))
    fi

    # 检查系统资源
    local mem_usage=$(free | grep Mem | awk '{printf "%.1f", $3/$2 * 100.0}')
    local disk_usage=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')

    if (( $(echo "$mem_usage > 80" | bc -l) )); then
        log_warning "⚠️ 内存使用率过高: ${mem_usage}%"
        ((issues++))
    else
        log_success "✅ 内存使用正常: ${mem_usage}%"
    fi

    if [ "$disk_usage" -gt 90 ]; then
        log_warning "⚠️ 磁盘使用率过高: ${disk_usage}%"
        ((issues++))
    else
        log_success "✅ 磁盘使用正常: ${disk_usage}%"
    fi

    echo ""
    if [ $issues -eq 0 ]; then
        log_success "🎉 系统健康状况良好"
        return 0
    else
        log_warning "⚠️ 发现 $issues 个问题需要关注"
        return 1
    fi
}

# 网络连通性测试
test_connectivity() {
    log_step "测试网络连通性..."

    echo ""
    log_info "🌐 网络连通性测试:"

    # DNS解析测试
    echo ""
    log_info "DNS解析测试:"
    test_hosts=("google.com" "github.com" "www.fotmob.com")

    for host in "${test_hosts[@]}"; do
        if nslookup "$host" >/dev/null 2>&1; then
            log_success "✅ $host - DNS解析成功"
        else
            log_error "❌ $host - DNS解析失败"
        fi
    done

    # 端口连通性测试
    echo ""
    log_info "端口连通性测试:"

    # 测试HTTP/HTTPS端口
    test_ports=(
        "google.com:443"
        "github.com:443"
        "www.fotmob.com:443"
    )

    for test in "${test_ports[@]}"; do
        host=$(echo "$test" | cut -d: -f1)
        port=$(echo "$test" | cut -d: -f2)

        if timeout 5 bash -c "</dev/tcp/$host/$port" 2>/dev/null; then
            log_success "✅ $host:$port - 连接成功"
        else
            log_error "❌ $host:$port - 连接失败"
        fi
    done

    # 代理连通性测试
    echo ""
    log_info "代理连通性测试:"

    proxy_host="172.25.16.1"
    proxy_port="7890"

    if timeout 5 bash -c "</dev/tcp/$proxy_host/$proxy_port" 2>/dev/null; then
        log_success "✅ 代理服务器 $proxy_host:$proxy_port - 连接成功"
    else
        log_warning "⚠️ 代理服务器 $proxy_host:$proxy_port - 连接失败"
    fi

    echo ""
}

# 主函数
main() {
    # 创建日志目录
    mkdir -p logs

    case "${1:-}" in
        start)
            check_python_environment
            check_mcp_config
            start_all_servers
            ;;
        stop)
            stop_all_servers
            ;;
        restart)
            stop_all_servers
            sleep 2
            start_all_servers
            ;;
        status)
            show_server_status
            ;;
        logs)
            show_server_logs "${2:-}"
            ;;
        test)
            test_mcp_servers
            ;;
        monitor)
            show_monitoring_panel
            ;;
        benchmark)
            run_benchmark
            ;;
        health)
            run_health_check
            ;;
        config)
            check_python_environment
            check_mcp_config
            show_server_status
            ;;
        start_single)
            if [ -z "${2:-}" ]; then
                log_error "请指定服务器名称"
                show_help
                exit 1
            fi
            check_python_environment
            start_mcp_server "$2"
            ;;
        stop_single)
            if [ -z "${2:-}" ]; then
                log_error "请指定服务器名称"
                show_help
                exit 1
            fi
            stop_mcp_server "$2"
            ;;
        restart_single)
            if [ -z "${2:-}" ]; then
                log_error "请指定服务器名称"
                show_help
                exit 1
            fi
            stop_mcp_server "$2"
            sleep 2
            start_mcp_server "$2"
            ;;
        connectivity)
            test_connectivity
            ;;
        -h|--help)
            show_help
            ;;
        *)
            log_error "未知命令: ${1:-}"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

# 错误处理
trap 'log_error "脚本执行失败"; exit 1' ERR

# 检查bc命令（用于数值比较）
if ! command -v bc &> /dev/null; then
    log_error "需要安装bc命令进行数值比较"
    exit 1
fi

# 执行主函数
main "$@"