#!/bin/bash

# 依赖包安装脚本
# Dependency Installation Script

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# 检查Python环境
check_python() {
    log_info "检查Python环境..."

    if ! command -v python3 &> /dev/null; then
        log_error "Python3 未安装"
        exit 1
    fi

    python_version=$(python3 --version | cut -d' ' -f2)
    log_success "Python版本: $python_version"

    # 检查虚拟环境
    if [[ "$VIRTUAL_ENV" != "" ]]; then
        log_info "当前在虚拟环境中: $VIRTUAL_ENV"
        PYTHON_CMD="python"
        PIP_CMD="pip"
    else
        log_warning "未检测到虚拟环境，使用系统Python"
        PYTHON_CMD="python3"
        PIP_CMD="pip3"
    fi
}

# 升级pip
upgrade_pip() {
    log_info "升级pip..."
    $PYTHON_CMD -m pip install --upgrade pip
    log_success "pip升级完成"
}

# 安装关键依赖
install_critical_dependencies() {
    log_info "安装关键依赖包..."

    critical_deps=(
        "requests>=2.31.0"
        "aiohttp>=3.9.0"
        "pyyaml>=6.0.1"
        "psutil>=5.9.0"
        "pandas>=2.1.0"
        "numpy>=1.26.0"
        "redis>=5.0.0"
        "prometheus-client>=0.19.0"
        "fastapi>=0.115.0"
        "sqlalchemy>=2.0.0"
        "asyncpg>=0.30.0"
        "uvicorn[standard]>=0.32.0"
    )

    for dep in "${critical_deps[@]}"; do
        log_info "安装 $dep..."
        $PIP_CMD install "$dep"
    done

    log_success "关键依赖包安装完成"
}

# 安装开发依赖（可选）
install_development_dependencies() {
    if [[ "$1" == "--include-dev" ]]; then
        log_info "安装开发依赖包..."

        dev_deps=(
            "pytest>=7.0.0"
            "pytest-asyncio>=0.21.0"
            "pytest-cov>=4.0.0"
            "black>=23.0.0"
            "mypy>=1.0.0"
            "bandit>=1.7.0"
            "pip-audit>=2.0.0"
            "matplotlib>=3.7.0"
            "scikit-learn>=1.3.0"
            "jupyter>=1.0.0"
        )

        for dep in "${dev_deps[@]}"; do
            log_info "安装 $dep..."
            $PIP_CMD install "$dep"
        done

        log_success "开发依赖包安装完成"
    else
        log_info "跳过开发依赖包安装（使用 --include-dev 参数安装）"
    fi
}

# 验证安装
verify_installation() {
    log_info "验证依赖安装..."

    $PYTHON_CMD scripts/verify_dependencies.py

    if [[ $? -eq 0 ]]; then
        log_success "依赖验证通过"
    else
        log_warning "依赖验证发现问题，请查看上述建议"
    fi
}

# 创建虚拟环境（如果需要）
create_virtual_environment() {
    if [[ "$1" == "--create-venv" ]]; then
        log_info "创建虚拟环境..."

        if [[ -d ".venv" ]]; then
            log_warning "虚拟环境已存在，跳过创建"
        else
            $PYTHON_CMD -m venv .venv
            log_success "虚拟环境创建完成"

            log_info "激活虚拟环境..."
            source .venv/bin/activate
            log_success "虚拟环境已激活"
        fi
    fi
}

# 显示使用帮助
show_help() {
    echo "FootballPrediction 依赖包安装脚本"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  --create-venv     创建虚拟环境"
    echo "  --include-dev     包含开发依赖"
    echo "  --help           显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0                       # 仅安装关键依赖"
    echo "  $0 --create-venv         # 创建虚拟环境并安装关键依赖"
    echo "  $0 --include-dev         # 安装关键依赖和开发依赖"
    echo "  $0 --create-venv --include-dev  # 完整安装"
}

# 主函数
main() {
    echo "🔧 FootballPrediction 依赖包安装脚本"
    echo "=================================="
    echo ""

    # 解析命令行参数
    CREATE_VENV=false
    INCLUDE_DEV=false

    while [[ $# -gt 0 ]]; do
        case $1 in
            --create-venv)
                CREATE_VENV=true
                shift
                ;;
            --include-dev)
                INCLUDE_DEV=true
                shift
                ;;
            --help)
                show_help
                exit 0
                ;;
            *)
                log_error "未知参数: $1"
                show_help
                exit 1
                ;;
        esac
    done

    # 执行安装步骤
    create_virtual_environment $([[ $CREATE_VENV == true ]] && echo "--create-venv")
    check_python
    upgrade_pip
    install_critical_dependencies
    install_development_dependencies $([[ $INCLUDE_DEV == true ]] && echo "--include-dev")
    verify_installation

    echo ""
    log_success "依赖安装完成！"

    if [[ "$VIRTUAL_ENV" != "" ]]; then
        log_info "虚拟环境路径: $VIRTUAL_ENV"
        log_info "使用 'source $VIRTUAL_ENV/bin/activate' 激活虚拟环境"
    fi

    log_info "使用 'python scripts/verify_dependencies.py' 验证安装状态"
}

# 错误处理
trap 'log_error "安装过程中出现错误，请检查上述输出"; exit 1' ERR

# 执行主函数
main "$@"