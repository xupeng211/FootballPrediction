#!/bin/bash
# Docker 容器管理脚本 v2.0
# 用于管理 Football Prediction System 的 Docker 容器

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 脚本信息
SCRIPT_NAME="Docker Manager v2.0"
DESCRIPTION="Football Prediction System 容器管理工具"

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
    echo -e "${CYAN}[COMMAND]${NC} $1"
}

# 显示帮助信息
show_help() {
    cat << EOF
$SCRIPT_NAME - $DESCRIPTION

用法: $0 <命令> [选项]

命令:
    build           构建所有服务镜像
    up              启动开发环境服务
    down            停止并删除所有服务
    restart         重启所有服务
    logs            查看服务日志
    status          查看服务状态
    shell           进入应用容器 shell
    test            运行测试套件
    quality         运行代码质量检查
    clean           清理未使用的 Docker 资源
    dev             启动完整开发环境
    prod            启动生产环境模拟
    health          检查所有服务健康状态

开发环境选项:
    --debug         启用调试模式
    --reload        启用热重载
    --collectors    同时启动数据收集器
    --testing       启动测试环境

生产环境选项:
    --monitoring    启动监控服务
    --nginx         启动 Nginx 反向代理

其他选项:
    -h, --help      显示此帮助信息
    -v, --verbose   详细输出模式

示例:
    $0 dev                    # 启动开发环境
    $0 build && $0 up        # 构建并启动
    $0 logs -f app           # 查看应用日志
    $0 test                  # 运行测试
    $0 clean --all           # 清理所有资源

EOF
}

# 检查 Docker 和 Docker Compose
check_dependencies() {
    log_step "检查依赖..."

    if ! command -v docker &> /dev/null; then
        log_error "Docker 未安装或不在 PATH 中"
        exit 1
    fi

    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose 未安装或不在 PATH 中"
        exit 1
    fi

    log_success "依赖检查通过"
}

# 构建镜像
build_images() {
    log_step "构建 Docker 镜像..."

    if [[ "$VERBOSE" == "true" ]]; then
        log_command "docker-compose build --parallel"
        docker-compose build --parallel
    else
        docker-compose build --parallel --quiet
    fi

    log_success "镜像构建完成"
}

# 启动服务
start_services() {
    local compose_file="${1:-docker-compose.yml}"
    local extra_args="${2:-}"

    log_step "启动服务 (使用 $compose_file)..."

    if [[ "$VERBOSE" == "true" ]]; then
        log_command "docker-compose -f $compose_file up -d $extra_args"
        docker-compose -f $compose_file up -d $extra_args
    else
        docker-compose -f $compose_file up -d $extra_args
    fi

    log_success "服务启动完成"
}

# 停止服务
stop_services() {
    local compose_file="${1:-docker-compose.yml}"

    log_step "停止服务..."

    log_command "docker-compose -f $compose_file down"
    docker-compose -f $compose_file down

    log_success "服务已停止"
}

# 查看服务状态
show_status() {
    log_step "查看服务状态..."

    echo
    docker-compose ps
    echo

    # 显示资源使用情况
    log_info "资源使用情况:"
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}" || true
}

# 查看日志
show_logs() {
    local service="${1:-}"
    local follow=""

    if [[ "$1" == "-f" ]]; then
        follow="-f"
        service="${2:-}"
    fi

    if [[ -n "$service" ]]; then
        log_step "查看服务日志: $service"
        docker-compose logs $follow "$service"
    else
        log_step "查看所有服务日志"
        docker-compose logs $follow
    fi
}

# 进入容器 shell
enter_shell() {
    log_step "进入应用容器 shell..."

    local container_id=$(docker-compose ps -q app)
    if [[ -z "$container_id" ]]; then
        log_error "应用容器未运行"
        exit 1
    fi

    log_command "docker exec -it $container_id /bin/bash"
    docker exec -it $container_id /bin/bash
}

# 运行测试
run_tests() {
    log_step "运行测试套件..."

    log_command "docker-compose --profile testing up --build --abort-on-container-exit pytest"
    docker-compose --profile testing up --build --abort-on-container-exit pytest

    log_success "测试完成"
}

# 运行代码质量检查
run_quality_check() {
    log_step "运行代码质量检查..."

    log_command "docker-compose --profile quality up --build --abort-on-container-exit quality-check"
    docker-compose --profile quality up --build --abort-on-container-exit quality-check

    log_success "代码质量检查完成"
}

# 检查健康状态
check_health() {
    log_step "检查服务健康状态..."

    # 检查 Docker 容器状态
    local unhealthy_containers=$(docker-compose ps | grep -E "(unhealthy|exited)" | wc -l)

    if [[ $unhealthy_containers -gt 0 ]]; then
        log_warning "发现 $unhealthy_containers 个不健康的容器"
        docker-compose ps
    else
        log_success "所有容器运行正常"
    fi

    # 检查应用健康检查
    log_info "执行应用健康检查..."
    docker-compose exec app python /app/healthcheck.py || log_warning "应用健康检查失败"
}

# 清理 Docker 资源
clean_docker() {
    local all_resources="${1:-false}"

    log_step "清理 Docker 资源..."

    # 停止所有服务
    docker-compose down --remove-orphans 2>/dev/null || true

    if [[ "$all_resources" == "true" ]]; then
        log_info "清理所有资源..."

        # 删除所有未使用的镜像
        docker image prune -af

        # 删除所有未使用的卷
        docker volume prune -f

        # 删除所有未使用的网络
        docker network prune -f
    else
        log_info "清理悬空资源..."

        # 只删除悬空的镜像
        docker image prune -f

        # 只删除未使用的卷
        docker volume prune -f
    fi

    log_success "资源清理完成"
}

# 启动开发环境
start_dev_environment() {
    local extra_services=""

    if [[ "$ENABLE_COLLECTORS" == "true" ]]; then
        extra_services="--profile collectors"
    fi

    log_step "启动开发环境 v2.0..."

    # 构建镜像
    build_images

    # 启动开发环境
    start_services "docker-compose.dev.yml" "$extra_services"

    # 等待服务就绪
    log_info "等待服务就绪..."
    sleep 10

    # 检查健康状态
    check_health

    log_success "开发环境启动完成"
    log_info "📱 应用地址: http://localhost:8000"
    log_info "🗄️  数据库管理: http://localhost:8080"
    log_info "📦 Redis 管理: http://localhost:8081"
    log_info "📚 API 文档: http://localhost:8000/docs"
}

# 启动生产环境
start_prod_environment() {
    local extra_services=""

    if [[ "$ENABLE_MONITORING" == "true" ]]; then
        extra_services="--profile monitoring"
    fi

    if [[ "$ENABLE_NGINX" == "true" ]]; then
        extra_services="$extra_services --profile nginx"
    fi

    log_step "启动生产环境模拟..."

    # 构建生产镜像
    log_command "docker-compose -f docker-compose.yml -f docker-compose.prod.yml build"
    docker-compose -f docker-compose.yml -f docker-compose.prod.yml build

    # 启动生产环境
    log_command "docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d $extra_services"
    docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d $extra_services

    # 等待服务就绪
    log_info "等待服务就绪..."
    sleep 15

    # 检查健康状态
    check_health

    log_success "生产环境启动完成"
}

# 解析命令行参数
VERBOSE=false
DEBUG=false
RELOAD=false
ENABLE_COLLECTORS=false
ENABLE_MONITORING=false
ENABLE_NGINX=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        --debug)
            DEBUG=true
            shift
            ;;
        --reload)
            RELOAD=true
            shift
            ;;
        --collectors)
            ENABLE_COLLECTORS=true
            shift
            ;;
        --monitoring)
            ENABLE_MONITORING=true
            shift
            ;;
        --nginx)
            ENABLE_NGINX=true
            shift
            ;;
        *)
            COMMAND="$1"
            shift
            break
            ;;
    esac
done

# 设置默认命令
COMMAND="${COMMAND:-help}"

# 主逻辑
main() {
    echo "🐳 $SCRIPT_NAME"
    echo "=" * 50

    # 检查依赖
    check_dependencies

    # 执行命令
    case $COMMAND in
        build)
            build_images
            ;;
        up)
            start_services
            ;;
        down)
            stop_services
            ;;
        restart)
            stop_services
            sleep 5
            start_services
            ;;
        logs)
            show_logs "$@"
            ;;
        status)
            show_status
            ;;
        shell)
            enter_shell
            ;;
        test)
            run_tests
            ;;
        quality)
            run_quality_check
            ;;
        clean)
            clean_docker "$1"
            ;;
        health)
            check_health
            ;;
        dev)
            start_dev_environment
            ;;
        prod)
            start_prod_environment
            ;;
        help|*)
            show_help
            ;;
    esac

    echo "=" * 50
}

# 执行主函数
main "$@"