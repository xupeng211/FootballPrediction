#!/bin/bash

# FootballPrediction v2.0 系统集成验收执行脚本
#
# 使用方法:
#   ./run_audit.sh [选项]
#
# 选项:
#   --install     安装依赖项
#   --verbose     详细输出模式
#   --json        输出JSON格式报告
#   --output FILE 输出报告到文件
#   --help        显示帮助信息

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 显示帮助信息
show_help() {
    cat << EOF
FootballPrediction v2.0 系统集成验收脚本

使用方法:
    $0 [选项]

选项:
    --install     安装Python依赖项
    --verbose     启用详细输出模式
    --json        输出JSON格式报告
    --output FILE 指定报告输出文件路径
    --help        显示此帮助信息

示例:
    $0 --install --verbose --output audit_report.json
    $0 --json --output /tmp/audit_$(date +%Y%m%d_%H%M%S).json

依赖要求:
    - Python 3.8+
    - pip
    - 系统服务运行中 (API:8000, Redis:6379, Prometheus:9090)

EOF
}

# 检查系统依赖
check_dependencies() {
    print_info "检查系统依赖..."

    # 检查Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 未安装或不在PATH中"
        exit 1
    fi

    python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    print_info "Python版本: $python_version"

    # 检查pip
    if ! command -v pip &> /dev/null && ! command -v pip3 &> /dev/null; then
        print_error "pip 未安装"
        exit 1
    fi

    # 检查关键服务是否运行
    print_info "检查系统服务状态..."

    services=(
        "API服务:8000:curl -s http://localhost:8000/health"
        "Redis:6379:redis-cli ping"
        "Prometheus:9090:curl -s http://localhost:9090/-/healthy"
    )

    for service_info in "${services[@]}"; do
        IFS=':' read -r name port check_cmd <<< "$service_info"
        if eval "$check_cmd" &> /dev/null; then
            print_success "$name 服务运行正常"
        else
            print_warning "$name 服务可能未运行或不可访问"
        fi
    done
}

# 安装Python依赖
install_dependencies() {
    print_info "安装Python依赖项..."

    # 进入项目目录
    cd "$PROJECT_ROOT"

    # 创建虚拟环境（如果不存在）
    if [ ! -d "venv" ]; then
        print_info "创建Python虚拟环境..."
        python3 -m venv venv
    fi

    # 激活虚拟环境
    source venv/bin/activate

    # 升级pip
    pip install --upgrade pip

    # 安装审计脚本依赖
    if [ -f "$SCRIPT_DIR/requirements.txt" ]; then
        pip install -r "$SCRIPT_DIR/requirements.txt"
        print_success "依赖项安装完成"
    else
        print_error "requirements.txt 文件不存在: $SCRIPT_DIR/requirements.txt"
        exit 1
    fi
}

# 运行验收测试
run_audit() {
    local verbose_flag=""
    local json_flag=""
    local output_flag=""

    # 解析参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            --verbose)
                verbose_flag="--verbose"
                shift
                ;;
            --json)
                json_flag="--output-json"
                shift
                ;;
            --output)
                output_flag="--output-file $2"
                shift 2
                ;;
            *)
                print_error "未知参数: $1"
                show_help
                exit 1
                ;;
        esac
    done

    print_info "开始运行系统集成验收..."
    print_info "脚本路径: $SCRIPT_DIR/system_health_check.py"

    # 激活虚拟环境（如果存在）
    if [ -d "$PROJECT_ROOT/venv" ]; then
        source "$PROJECT_ROOT/venv/bin/activate"
        print_info "已激活Python虚拟环境"
    fi

    # 执行验收脚本
    cmd="python3 $SCRIPT_DIR/system_health_check.py $verbose_flag $json_flag $output_flag"
    print_info "执行命令: $cmd"

    eval $cmd
    local exit_code=$?

    if [ $exit_code -eq 0 ]; then
        print_success "系统集成验收通过！"
    else
        print_error "系统集成验收失败！"
        exit $exit_code
    fi
}

# 主函数
main() {
    print_info "FootballPrediction v2.0 系统集成验收工具"
    print_info "项目根目录: $PROJECT_ROOT"

    # 解析命令行参数
    install_deps=false
    show_help_only=false

    while [[ $# -gt 0 ]]; do
        case $1 in
            --install)
                install_deps=true
                shift
                ;;
            --help)
                show_help_only=true
                shift
                ;;
            *)
                # 其他参数传递给验收脚本
                break
                ;;
        esac
    done

    if [ "$show_help_only" = true ]; then
        show_help
        exit 0
    fi

    # 安装依赖（如果指定）
    if [ "$install_deps" = true ]; then
        check_dependencies
        install_dependencies
        print_success "依赖项安装完成，可以开始验收测试"
        exit 0
    fi

    # 运行验收测试
    check_dependencies
    run_audit "$@"
}

# 执行主函数
main "$@"