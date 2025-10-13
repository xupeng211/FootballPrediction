#!/bin/bash

# Staging 环境管理脚本
# 用于 E2E 测试和生产前验证

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置
COMPOSE_FILE="docker-compose.staging.yml"
ENV_FILE="docker/environments/.env.staging"
PROJECT_NAME="football-staging"

# 函数定义
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

# 显示帮助信息
show_help() {
    cat << EOF
Staging 环境管理脚本

用法: $0 [命令] [选项]

命令:
    start               启动 Staging 环境
    stop                停止 Staging 环境
    restart             重启 Staging 环境
    status              查看环境状态
    logs                查看服务日志
    shell               进入应用容器 shell
    db                  连接 Staging 数据库
    redis               连接 Redis
    migrate             运行数据库迁移
    seed                加载种子数据
    backup              备份数据库
    restore             恢复数据库
    health              检查环境健康状态
    monitor             打开监控面板
    test                运行 E2E 测试
    reset               重置环境（危险！）
    cleanup             清理资源

选项:
    -f, --file          指定 compose 文件 (默认: $COMPOSE_FILE)
    -e, --env           指定环境文件 (默认: $ENV_FILE)
    -v, --verbose       详细输出
    -h, --help          显示此帮助信息

示例:
    $0 start                    # 启动 Staging 环境
    $0 test                     # 运行 E2E 测试
    $0 logs app                 # 查看应用日志
    $0 monitor                  # 打开监控面板

EOF
}

# 检查依赖
check_dependencies() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker 未安装或不在 PATH 中"
        exit 1
    fi

    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "Docker Compose 未安装"
        exit 1
    fi
}

# 获取 Docker Compose 命令
get_compose_cmd() {
    if command -v docker-compose &> /dev/null; then
        echo "docker-compose"
    else
        echo "docker compose"
    fi
}

# 启动 Staging 环境
start_env() {
    log_info "启动 Staging 环境..."

    COMPOSE_CMD=$(get_compose_cmd)

    # 创建必要的目录
    mkdir -p logs/staging logs/nginx backups storage ssl

    # 检查环境变量
    if [ ! -f "$ENV_FILE" ]; then
        log_warning "环境文件不存在，使用默认配置"
    fi

    # 启动基础服务
    log_info "启动基础服务 (数据库、Redis、Kafka)..."
    $COMPOSE_CMD -f $COMPOSE_FILE -p $PROJECT_NAME up -d db redis kafka zookeeper

    log_info "等待基础服务启动..."
    sleep 20

    # 运行数据库迁移
    log_info "运行数据库迁移..."
    $COMPOSE_CMD -f $COMPOSE_FILE -p $PROJECT_NAME run --rm migration

    # 启动所有服务
    log_info "启动所有服务..."
    $COMPOSE_CMD -f $COMPOSE_FILE -p $PROJECT_NAME up -d

    # 等待服务就绪
    log_info "等待服务就绪..."
    sleep 30

    # 检查健康状态
    check_health

    # 显示服务地址
    show_service_urls

    log_success "Staging 环境启动完成！"
}

# 停止环境
stop_env() {
    log_info "停止 Staging 环境..."

    COMPOSE_CMD=$(get_compose_cmd)
    $COMPOSE_CMD -f $COMPOSE_FILE -p $PROJECT_NAME down

    log_success "Staging 环境已停止"
}

# 重启环境
restart_env() {
    log_info "重启 Staging 环境..."
    stop_env
    sleep 2
    start_env
}

# 查看状态
show_status() {
    log_info "Staging 环境状态："

    COMPOSE_CMD=$(get_compose_cmd)
    $COMPOSE_CMD -f $COMPOSE_FILE -p $PROJECT_NAME ps
}

# 查看日志
show_logs() {
    local service=$1
    COMPOSE_CMD=$(get_compose_cmd)

    if [ -z "$service" ]; then
        $COMPOSE_CMD -f $COMPOSE_FILE -p $PROJECT_NAME logs -f
    else
        $COMPOSE_CMD -f $COMPOSE_FILE -p $PROJECT_NAME logs -f "$service"
    fi
}

# 进入容器
enter_shell() {
    log_info "进入应用容器..."

    COMPOSE_CMD=$(get_compose_cmd)
    $COMPOSE_CMD -f $COMPOSE_FILE -p $PROJECT_NAME exec app bash
}

# 连接数据库
connect_db() {
    log_info "连接 Staging 数据库..."

    COMPOSE_CMD=$(get_compose_cmd)
    $COMPOSE_CMD -f $COMPOSE_FILE -p $PROJECT_NAME exec db psql -U staging_user -d football_staging
}

# 连接 Redis
connect_redis() {
    log_info "连接 Redis..."

    COMPOSE_CMD=$(get_compose_cmd)
    $COMPOSE_CMD -f $COMPOSE_FILE -p $PROJECT_NAME exec redis redis-cli -n 0
}

# 运行迁移
run_migrations() {
    log_info "运行数据库迁移..."

    COMPOSE_CMD=$(get_compose_cmd)
    $COMPOSE_CMD -f $COMPOSE_FILE -p $PROJECT_NAME run --rm migration
}

# 加载种子数据
load_seed_data() {
    log_info "加载种子数据..."

    COMPOSE_CMD=$(get_compose_cmd)
    $COMPOSE_CMD -f $COMPOSE_FILE -p $PROJECT_NAME exec -T app python scripts/load_staging_data.py
}

# 备份数据库
backup_database() {
    log_info "备份数据库..."

    COMPOSE_CMD=$(get_compose_cmd)
    backup_file="backups/staging_backup_$(date +%Y%m%d_%H%M%S).sql"

    $COMPOSE_CMD -f $COMPOSE_FILE -p $PROJECT_NAME exec db pg_dump \
        -U staging_user \
        -h localhost \
        -d football_staging \
        --clean \
        --if-exists \
        --create \
        > "$backup_file"

    log_success "备份完成: $backup_file"
}

# 恢复数据库
restore_database() {
    local backup_file=$1

    if [ -z "$backup_file" ]; then
        log_error "请指定备份文件"
        echo "用法: $0 restore <backup_file>"
        exit 1
    fi

    if [ ! -f "$backup_file" ]; then
        log_error "备份文件不存在: $backup_file"
        exit 1
    fi

    log_warning "这将覆盖当前数据库！继续吗？(y/N)"
    read -r response

    if [[ $response =~ ^[Yy]$ ]]; then
        log_info "恢复数据库从: $backup_file"

        COMPOSE_CMD=$(get_compose_cmd)
        $COMPOSE_CMD -f $COMPOSE_FILE -p $PROJECT_NAME exec -T db psql \
            -U staging_user \
            -h localhost \
            -d football_staging \
            < "$backup_file"

        log_success "数据库恢复完成"
    else
        log_info "操作已取消"
    fi
}

# 检查健康状态
check_health() {
    log_info "检查服务健康状态..."

    COMPOSE_CMD=$(get_compose_cmd)

    # 检查应用健康
    if curl -f http://localhost:8000/health &> /dev/null; then
        log_success "✅ 应用服务健康"
    else
        log_warning "⚠️ 应用服务未就绪"
    fi

    # 检查数据库
    if $COMPOSE_CMD -f $COMPOSE_FILE -p $PROJECT_NAME exec -T db pg_isready -U staging_user -d football_staging &> /dev/null; then
        log_success "✅ 数据库连接正常"
    else
        log_warning "⚠️ 数据库未就绪"
    fi

    # 检查 Redis
    if $COMPOSE_CMD -f $COMPOSE_FILE -p $PROJECT_NAME exec -T redis redis-cli ping &> /dev/null; then
        log_success "✅ Redis 连接正常"
    else
        log_warning "⚠️ Redis 未就绪"
    fi

    # 检查 Kafka
    if $COMPOSE_CMD -f $COMPOSE_FILE -p $PROJECT_NAME exec -T kafka kafka-broker-api-versions --bootstrap-server localhost:9092 &> /dev/null; then
        log_success "✅ Kafka 连接正常"
    else
        log_warning "⚠️ Kafka 未就绪"
    fi

    # 检查监控服务
    if curl -f http://localhost:9091/targets &> /dev/null; then
        log_success "✅ Prometheus 监控正常"
    else
        log_warning "⚠️ Prometheus 未就绪"
    fi

    if curl -f http://localhost:3001/api/health &> /dev/null; then
        log_success "✅ Grafana 监控正常"
    else
        log_warning "⚠️ Grafana 未就绪"
    fi
}

# 显示服务 URL
show_service_urls() {
    echo
    log_info "Staging 环境服务地址："
    echo -e "  📱 应用 API:    ${GREEN}http://localhost:8000${NC}"
    echo -e "  📊 API 文档:    ${GREEN}http://localhost:8000/docs${NC}"
    echo -e "  🌐 Nginx 代理:  ${GREEN}http://localhost:80${NC}"
    echo -e "  📈 Prometheus:  ${GREEN}http://localhost:9091${NC}"
    echo -e "  📊 Grafana:     ${GREEN}http://localhost:3001${NC} (admin/admin123)"
    echo -e "  🗄️  数据库:      ${GREEN}localhost:5434${NC} (staging_user/football_staging)"
    echo -e "  🗃️  Redis:       ${GREEN}localhost:6381${NC}"
    echo -e "  📨 Kafka:       ${GREEN}localhost:9094${NC}"
    echo -e "  📈 MLflow:      ${GREEN}http://localhost:5002${NC}"
    echo
}

# 打开监控面板
open_monitoring() {
    log_info "打开监控面板..."

    # 尝试打开默认浏览器
    if command -v xdg-open &> /dev/null; then
        xdg-open http://localhost:3001
    elif command -v open &> /dev/null; then
        open http://localhost:3001
    else
        log_info "请手动访问: http://localhost:3001"
    fi
}

# 运行 E2E 测试
run_e2e_tests() {
    log_info "运行 E2E 测试..."

    COMPOSE_CMD=$(get_compose_cmd)

    # 确保 Staging 环境运行
    if ! $COMPOSE_CMD -f $COMPOSE_FILE -p $PROJECT_NAME ps -q app | grep -q "Up"; then
        log_warning "Staging 环境未运行，先启动环境..."
        start_env
    fi

    # 运行 E2E 测试
    $COMPOSE_CMD -f $COMPOSE_FILE -p $PROJECT_NAME exec app pytest tests/e2e/ -v --html=reports/e2e.html --self-contained-html

    log_success "E2E 测试完成，查看报告: reports/e2e.html"
}

# 重置环境（危险）
reset_env() {
    log_warning "⚠️ 这将删除所有 Staging 数据！"
    echo "此操作不可逆！"
    read -p "确定要继续吗？(yes/no): " -r
    echo

    if [[ $REPLY =~ ^yes$ ]]; then
        log_info "重置 Staging 环境..."

        COMPOSE_CMD=$(get_compose_cmd)
        $COMPOSE_CMD -f $COMPOSE_FILE -p $PROJECT_NAME down -v
        $COMPOSE_CMD -f $COMPOSE_FILE -p $PROJECT_NAME up -d

        log_info "等待服务启动..."
        sleep 30

        # 迁移和种子数据
        run_migrations
        load_seed_data

        log_success "Staging 环境重置完成"
    else
        log_info "操作已取消"
    fi
}

# 清理资源
cleanup_resources() {
    log_info "清理 Staging 资源..."

    # 清理未使用的 Docker 资源
    docker container prune -f
    docker image prune -f
    docker network prune -f

    # 清理旧备份（保留最近7个）
    ls -t backups/staging_backup_*.sql | tail -n +8 | xargs -r rm -f

    log_success "资源清理完成"
}

# 主函数
main() {
    # 解析参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            -f|--file)
                COMPOSE_FILE="$2"
                shift 2
                ;;
            -e|--env)
                ENV_FILE="$2"
                shift 2
                ;;
            -v|--verbose)
                set -x
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            start|stop|restart|status|logs|shell|db|redis|migrate|seed|backup|restore|health|monitor|test|reset|cleanup)
                COMMAND="$1"
                shift
                ;;
            *)
                log_error "未知命令: $1"
                show_help
                exit 1
                ;;
        esac
    done

    # 检查依赖
    check_dependencies

    # 执行命令
    case $COMMAND in
        start)
            start_env
            ;;
        stop)
            stop_env
            ;;
        restart)
            restart_env
            ;;
        status)
            show_status
            ;;
        logs)
            show_logs "$1"
            ;;
        shell)
            enter_shell
            ;;
        db)
            connect_db
            ;;
        redis)
            connect_redis
            ;;
        migrate)
            run_migrations
            ;;
        seed)
            load_seed_data
            ;;
        backup)
            backup_database
            ;;
        restore)
            restore_database "$1"
            ;;
        health)
            check_health
            ;;
        monitor)
            open_monitoring
            ;;
        test)
            run_e2e_tests
            ;;
        reset)
            reset_env
            ;;
        cleanup)
            cleanup_resources
            ;;
        *)
            log_error "请指定命令"
            show_help
            exit 1
            ;;
    esac
}

# 如果没有参数，显示帮助
if [ $# -eq 0 ]; then
    show_help
    exit 0
fi

# 设置默认命令
COMMAND="${1:-help}"

# 运行主函数
main "$@"