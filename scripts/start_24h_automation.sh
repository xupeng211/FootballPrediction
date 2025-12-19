#!/bin/bash
# FootballPrediction v2.3.0-production - 24小时自动化启动脚本
# 支持Docker环境和本地环境

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_message() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================${NC}"
}

# 显示帮助信息
show_help() {
    cat << EOF
FootballPrediction 24小时自动化启动脚本

用法: $0 [选项]

选项:
    -m, --mode MODE       运行模式:
                         internal_loop - 内部循环模式 (默认)
                         crontab       - Crontab任务模式
                         shadow_test   - 影子测试模式
    -d, --duration HOURS  运行时长 (默认: 24小时)
    -i, --interval MINUTES 预测间隔 (默认: 15分钟)
    --docker             在Docker容器中运行
    --env-file FILE      环境配置文件
    -h, --help           显示帮助信息

示例:
    $0                           # 默认内部循环模式，24小时
    $0 -m crontab -d 48         # Crontab模式，48小时
    $0 -m shadow_test -i 30     # 影子测试模式，30分钟间隔
    $0 --docker -m internal_loop # Docker环境运行

EOF
}

# 检查依赖
check_dependencies() {
    print_message "检查系统依赖..."

    # 检查Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python3 未安装"
        exit 1
    fi

    # 检查项目目录
    if [[ ! -f "scripts/automation_daemon_24h.py" ]]; then
        print_error "automation_daemon_24h.py 文件不存在"
        exit 1
    fi

    # 检查日志目录
    mkdir -p logs
    mkdir -p data/shadow

    print_message "依赖检查完成"
}

# 检查Docker环境
check_docker() {
    if ! command -v docker-compose &> /dev/null && ! command -v docker &> /dev/null; then
        print_error "Docker未安装"
        exit 1
    fi

    if [[ ! -f "docker-compose.yml" ]]; then
        print_error "docker-compose.yml 文件不存在"
        exit 1
    fi

    print_message "Docker环境检查完成"
}

# 在Docker中运行
run_in_docker() {
    local mode=$1
    local duration=$2
    local interval=$3
    local env_file=$4

    print_header "在Docker环境中启动24小时自动化"

    # 设置环境变量
    local compose_args=""
    if [[ -n "$env_file" ]]; then
        compose_args="--env-file $env_file"
    fi

    # 根据模式选择compose文件
    if [[ "$mode" == "shadow_test" ]]; then
        export ENVIRONMENT=shadow
        export SHADOW_MODE=true
    fi

    print_message "启动Docker服务..."
    docker-compose $compose_args up -d

    print_message "等待服务启动..."
    sleep 30

    print_message "在容器中启动自动化守护进程..."
    docker-compose exec app python3 scripts/automation_daemon_24h.py \
        --mode "$mode" \
        --duration "$duration" \
        --interval "$interval"
}

# 在本地环境运行
run_locally() {
    local mode=$1
    local duration=$2
    local interval=$3
    local env_file=$4

    print_header "在本地环境中启动24小时自动化"

    # 加载环境变量
    if [[ -n "$env_file" && -f "$env_file" ]]; then
        print_message "加载环境文件: $env_file"
        export $(grep -v '^#' "$env_file" | xargs)
    fi

    # 设置Python路径
    export PYTHONPATH="$(pwd):$(pwd)/src:$(pwd)/scripts"

    print_message "启动自动化守护进程..."
    python3 scripts/automation_daemon_24h.py \
        --mode "$mode" \
        --duration "$duration" \
        --interval "$interval"
}

# 监控运行状态
monitor_automation() {
    local mode=$1

    print_header "监控自动化运行状态"

    if [[ "$mode" == "crontab" ]]; then
        print_message "Crontab任务状态:"
        crontab -l | grep football || print_warning "未找到相关crontab任务"
    fi

    print_message "实时日志 (按Ctrl+C退出):"
    tail -f logs/automation_24h.log
}

# 默认参数
MODE="internal_loop"
DURATION=24
INTERVAL=15
DOCKER_MODE=false
ENV_FILE=""

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        -m|--mode)
            MODE="$2"
            shift 2
            ;;
        -d|--duration)
            DURATION="$2"
            shift 2
            ;;
        -i|--interval)
            INTERVAL="$2"
            shift 2
            ;;
        --docker)
            DOCKER_MODE=true
            shift
            ;;
        --env-file)
            ENV_FILE="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            print_error "未知参数: $1"
            show_help
            exit 1
            ;;
    esac
done

# 主逻辑
main() {
    print_header "FootballPrediction 24小时自动化系统"
    print_message "模式: $MODE"
    print_message "时长: ${DURATION}小时"
    print_message "间隔: ${INTERVAL}分钟"
    print_message "环境: $([[ "$DOCKER_MODE" == true ]] && echo "Docker" || echo "本地")"

    # 检查依赖
    check_dependencies

    if [[ "$DOCKER_MODE" == true ]]; then
        check_docker
        run_in_docker "$MODE" "$DURATION" "$INTERVAL" "$ENV_FILE"
    else
        run_locally "$MODE" "$DURATION" "$INTERVAL" "$ENV_FILE"
    fi

    # 询问是否监控
    echo
    read -p "是否监控运行状态? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        monitor_automation "$MODE"
    fi
}

# 错误处理
trap 'print_error "脚本执行失败"; exit 1' ERR

# 运行主程序
main