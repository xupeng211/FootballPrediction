#!/bin/bash
# Docker辅助脚本
# 提供统一的Docker操作接口

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 获取环境
get_env() {
    echo "${ENV:-development}"
}

# Docker compose命令
dco() {
    docker-compose -f docker/docker-compose.yml "$@"
}

# 带环境的docker compose命令
dco_env() {
    local env="${1:-$(get_env)}"
    shift
    ENV=$env docker-compose -f docker/docker-compose.yml "$@"
}

# 帮助信息
show_help() {
    cat << EOF
Docker辅助脚本

用法: $0 [命令] [参数]

命令:
    up [env]          启动服务 (env: development|staging|production|test)
    down [env]        停止服务
    logs [service]    查看日志
    build [env]       构建镜像
    shell [service]   进入容器shell
    db [env]          进入数据库
    migrate [env]     运行数据库迁移
    test [env]        运行测试
    clean             清理Docker资源
    status            查看服务状态

示例:
    $0 up             # 启动开发环境
    $0 up production  # 启动生产环境
    $0 logs app       # 查看应用日志
    $0 shell app      # 进入应用容器
    $0 db             # 进入数据库
    $0 test           # 运行测试

环境变量:
    ENV               环境名称 (development|staging|production|test)
    COMPOSE_PROFILES   Docker Compose profiles
EOF
}

# 启动服务
cmd_up() {
    local env="${1:-$(get_env)}"
    local profiles="${2:-}"

    log_info "启动 $env 环境..."

    # 设置环境特定的profiles
    case $env in
        "production")
            profiles="$profiles production monitoring logging celery"
            ;;
        "staging")
            profiles="$profiles staging monitoring"
            ;;
        "test")
            profiles="$profiles test"
            ;;
        "development")
            profiles="$profiles tools"
            ;;
    esac

    if [[ -n "$profiles" ]]; then
        export COMPOSE_PROFILES="$profiles"
        log_info "使用 profiles: $profiles"
    fi

    ENV=$env dco up -d

    log_info "等待服务启动..."
    sleep 5

    # 显示服务状态
    dco ps

    # 显示访问地址
    show_urls "$env"
}

# 停止服务
cmd_down() {
    local env="${1:-$(get_env)}"

    log_info "停止 $env 环境..."
    ENV=$env dco down

    # 清理未使用的资源（可选）
    read -p "是否清理未使用的Docker资源? (y/N): " confirm
    if [[ "$confirm" =~ ^[Yy]$ ]]; then
        docker system prune -f
        log_info "清理完成"
    fi
}

# 查看日志
cmd_logs() {
    local service="${1:-}"
    local follow="${2:-true}"

    if [[ -n "$service" ]]; then
        if [[ "$follow" == "true" ]]; then
            dco logs -f "$service"
        else
            dco logs --tail=100 "$service"
        fi
    else
        dco logs -f
    fi
}

# 构建镜像
cmd_build() {
    local env="${1:-$(get_env)}"
    local target="${2:-}"

    log_info "构建 $env 环境镜像..."

    # 设置构建目标
    case $env in
        "production")
            target="--target production"
            ;;
        "test")
            target="--target test"
            ;;
        "development"|"staging")
            target="--target development"
            ;;
    esac

    # 构建参数
    local build_args=""
    build_args="$build_args --build-arg APP_VERSION=$(git describe --tags --always --dirty 2>/dev/null || echo 'dev')"
    build_args="$build_args --build-arg BUILD_DATE=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    build_args="$build_args --build-arg GIT_COMMIT=$(git rev-parse HEAD 2>/dev/null || echo 'unknown')"
    build_args="$build_args --build-arg GIT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo 'unknown')"

    ENV=$env dco build $target $build_args app

    log_info "构建完成"
}

# 进入容器shell
cmd_shell() {
    local service="${1:-app}"
    local shell="${2:-bash}"

    log_info "进入 $service 容器..."
    dco exec "$service" "$shell"
}

# 进入数据库
cmd_db() {
    local env="${1:-$(get_env)}"

    log_info "连接 $env 环境数据库..."

    # 获取数据库连接信息
    case $env in
        "test")
            dco exec -T test-db psql -U test_user -d football_prediction_test
            ;;
        *)
            dco exec db psql -U ${DB_USER:-postgres} -d ${DB_NAME:-football_prediction}
            ;;
    esac
}

# 运行迁移
cmd_migrate() {
    local env="${1:-$(get_env)}"

    log_info "运行 $env 环境数据库迁移..."

    case $env in
        "test")
            log_info "测试环境，跳过迁移"
            ;;
        *)
            dco exec app alembic upgrade head
            ;;
    esac

    log_info "迁移完成"
}

# 运行测试
cmd_test() {
    log_info "运行测试..."

    # 启动测试环境
    cmd_up test

    # 运行测试
    dco run --rm app pytest -v --cov=src --cov-report=html --cov-report=term

    # 清理测试环境
    cmd_down test

    log_info "测试完成"
}

# 清理Docker资源
cmd_clean() {
    log_info "清理Docker资源..."

    # 停止所有容器
    dco down --remove-orphans

    # 删除所有相关镜像
    docker images | grep football_prediction | awk '{print $3}' | xargs -r docker rmi -f

    # 删除所有相关卷
    docker volume ls | grep football_prediction | awk '{print $2}' | xargs -r docker volume rm

    # 清理系统
    docker system prune -f

    log_info "清理完成"
}

# 查看服务状态
cmd_status() {
    log_info "Docker服务状态:"
    echo
    dco ps
    echo

    # 显示资源使用
    log_info "资源使用情况:"
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}"
}

# 显示访问URL
show_urls() {
    local env="$1"

    echo
    log_info "服务访问地址:"

    case $env in
        "production"|"staging")
            echo "  🌐 应用: https://your-domain.com"
            echo "  📊 监控: http://localhost:3000 (Grafana)"
            echo "  📈 指标: http://localhost:9090 (Prometheus)"
            ;;
        "development")
            echo "  🌐 应用: http://localhost:8000"
            echo "  🗄️  数据库管理: http://localhost:8080 (Adminer)"
            echo "  📦 Redis管理: http://localhost:8081 (Redis Commander)"
            echo "  📧 邮件模拟: http://localhost:8025 (MailHog)"
            ;;
        "test")
            echo "  🧪 测试环境已启动"
            ;;
    esac

    echo
}

# 主函数
main() {
    local command="${1:-}"
    shift || true

    case $command in
        "up")
            cmd_up "$@"
            ;;
        "down")
            cmd_down "$@"
            ;;
        "logs")
            cmd_logs "$@"
            ;;
        "build")
            cmd_build "$@"
            ;;
        "shell")
            cmd_shell "$@"
            ;;
        "db")
            cmd_db "$@"
            ;;
        "migrate")
            cmd_migrate "$@"
            ;;
        "test")
            cmd_test
            ;;
        "clean")
            cmd_clean
            ;;
        "status")
            cmd_status
            ;;
        "help"|"-h"|"--help"|"")
            show_help
            ;;
        *)
            log_error "未知命令: $command"
            show_help
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@"
