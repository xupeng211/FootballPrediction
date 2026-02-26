#!/bin/bash
# =============================================================================
# FootballPrediction - 开发环境快速启动脚本
# =============================================================================
# 版本: V170.000
# 用途: 一键启动容器化开发环境
# =============================================================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT"

# 打印函数
print_header() {
    echo -e "${BLUE}"
    echo "=============================================="
    echo "  FootballPrediction 开发环境启动器"
    echo "  版本: V170.000"
    echo "=============================================="
    echo -e "${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

# 检查 Docker
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker 未安装，请先安装 Docker"
        exit 1
    fi

    if ! docker info &> /dev/null; then
        print_error "Docker 未运行，请先启动 Docker"
        exit 1
    fi

    print_success "Docker 已就绪 ($(docker --version))"
}

# 检查 Docker Compose
check_docker_compose() {
    if docker compose version &> /dev/null; then
        COMPOSE_CMD="docker compose"
    elif command -v docker-compose &> /dev/null; then
        COMPOSE_CMD="docker-compose"
    else
        print_error "Docker Compose 未安装"
        exit 1
    fi
    print_success "Docker Compose 已就绪 ($($COMPOSE_CMD version --short))"
}

# 构建开发镜像
build_image() {
    print_info "构建开发镜像 (首次可能需要几分钟)..."

    # 设置代理（如果有）
    if [ -n "$HTTP_PROXY" ]; then
        export BUILD_HTTP_PROXY="$HTTP_PROXY"
        export BUILD_HTTPS_PROXY="$HTTPS_PROXY"
    fi

    $COMPOSE_CMD -f docker-compose.dev.yml build --no-cache dev 2>&1 | while read -r line; do
        # 只显示关键信息
        if [[ "$line" == *"Step"* ]] || [[ "$line" == *"Successfully"* ]]; then
            echo "  $line"
        fi
    done

    print_success "开发镜像构建完成"
}

# 启动服务
start_services() {
    print_info "启动开发服务..."

    # 启动核心服务
    $COMPOSE_CMD -f docker-compose.dev.yml up -d db redis
    sleep 5

    # 等待数据库就绪
    print_info "等待数据库就绪..."
    for i in {1..30}; do
        if $COMPOSE_CMD -f docker-compose.dev.yml exec -T db pg_isready -U football_user -d football_db &> /dev/null; then
            print_success "数据库已就绪"
            break
        fi
        sleep 1
    done

    # 启动开发容器
    $COMPOSE_CMD -f docker-compose.dev.yml up -d dev

    print_success "所有服务已启动"
}

# 安装依赖
install_dependencies() {
    print_info "安装项目依赖..."

    # Python 依赖
    $COMPOSE_CMD -f docker-compose.dev.yml exec -T dev pip install -r requirements.txt -q 2>/dev/null || true

    # Node.js 依赖
    $COMPOSE_CMD -f docker-compose.dev.yml exec -T dev npm install --silent 2>/dev/null || true

    print_success "依赖安装完成"
}

# 显示状态
show_status() {
    echo ""
    print_info "服务状态:"
    $COMPOSE_CMD -f docker-compose.dev.yml ps
    echo ""
}

# 显示使用说明
show_usage() {
    echo ""
    echo -e "${GREEN}=============================================="
    echo "  🚀 开发环境已就绪！"
    echo "==============================================${NC}"
    echo ""
    echo "📋 常用命令:"
    echo ""
    echo "  进入开发容器:"
    echo "    docker-compose -f docker-compose.dev.yml exec dev bash"
    echo ""
    echo "  运行 Python 代码:"
    echo "    docker-compose -f docker-compose.dev.yml exec dev python main.py --help"
    echo ""
    echo "  运行 JavaScript 收割机:"
    echo "    docker-compose -f docker-compose.dev.yml exec dev node src/infrastructure/engines/QuantHarvester.js"
    echo ""
    echo "  查看日志:"
    echo "    docker-compose -f docker-compose.dev.yml logs -f dev"
    echo ""
    echo "  停止服务:"
    echo "    docker-compose -f docker-compose.dev.yml down"
    echo ""
    echo "📁 代码目录: $PROJECT_ROOT"
    echo "   (Windows 侧修改会自动同步到容器)"
    echo ""
    echo "🌐 服务端口:"
    echo "   API:     http://localhost:8000"
    echo "   DB:      localhost:5432"
    echo "   Redis:   localhost:6379"
    echo ""
}

# 主函数
main() {
    print_header

    check_docker
    check_docker_compose

    # 检查是否需要构建
    if ! docker images | grep -q "footballprediction.*v170.000-dev"; then
        build_image
    else
        print_success "开发镜像已存在，跳过构建"
    fi

    start_services
    install_dependencies
    show_status
    show_usage
}

# 解析参数
case "${1:-}" in
    --build|-b)
        check_docker
        check_docker_compose
        build_image
        ;;
    --stop|-s)
        check_docker
        check_docker_compose
        print_info "停止开发环境..."
        docker-compose -f docker-compose.dev.yml down
        print_success "开发环境已停止"
        ;;
    --shell|-sh)
        check_docker
        check_docker_compose
        docker-compose -f docker-compose.dev.yml exec dev bash
        ;;
    --logs|-l)
        check_docker
        check_docker_compose
        docker-compose -f docker-compose.dev.yml logs -f dev
        ;;
    --help|-h)
        echo "用法: $0 [选项]"
        echo ""
        echo "选项:"
        echo "  --build, -b    强制重新构建镜像"
        echo "  --stop, -s     停止开发环境"
        echo "  --shell, -sh   进入开发容器 Shell"
        echo "  --logs, -l     查看开发容器日志"
        echo "  --help, -h     显示帮助信息"
        echo ""
        echo "无参数运行将启动完整的开发环境"
        ;;
    *)
        main
        ;;
esac
