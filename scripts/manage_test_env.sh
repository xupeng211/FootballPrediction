#!/bin/bash

# 测试环境管理脚本
# 用于启动、停止和管理集成测试、E2E 测试环境

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置
COMPOSE_FILE="docker-compose.test.yml"
ENV_FILE="docker/environments/.env.test"
PROJECT_NAME="football-test"

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
测试环境管理脚本

用法: $0 [命令] [选项]

命令:
    start           启动测试环境
    stop            停止测试环境
    restart         重启测试环境
    status          查看环境状态
    logs            查看服务日志
    shell           进入应用容器 shell
    test-db         连接测试数据库
    test-redis      连接 Redis
    reset           重置测试环境（删除所有数据）
    init            初始化测试数据
    check           检查环境健康状态
    clean           清理未使用的 Docker 资源

测试命令:
    unit            运行单元测试
    integration     运行集成测试
    e2e             运行端到端测试
    all             运行所有测试
    coverage        生成测试覆盖率报告

选项:
    -f, --file      指定 compose 文件 (默认: $COMPOSE_FILE)
    -e, --env       指定环境文件 (默认: $ENV_FILE)
    -v, --verbose   详细输出
    -h, --help      显示此帮助信息

示例:
    $0 start                    # 启动测试环境
    $0 test integration         # 运行集成测试
    $0 logs app                 # 查看应用日志
    $0 shell                    # 进入容器 shell
    $0 reset                    # 重置环境

EOF
}

# 检查 Docker 和 Docker Compose
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

# 启动测试环境
start_env() {
    log_info "启动测试环境..."

    COMPOSE_CMD=$(get_compose_cmd)

    # 创建必要的目录
    mkdir -p logs reports coverage tests/fixtures

    # 启动基础设施服务
    $COMPOSE_CMD -f $COMPOSE_FILE -p $PROJECT_NAME up -d db redis kafka zookeeper

    log_info "等待基础设施服务启动..."
    sleep 10

    # 启动所有服务
    $COMPOSE_CMD -f $COMPOSE_FILE -p $PROJECT_NAME up -d

    # 等待服务就绪
    log_info "等待服务就绪..."
    sleep 20

    # 检查健康状态
    check_health

    log_success "测试环境启动完成！"
    show_service_urls
}

# 停止测试环境
stop_env() {
    log_info "停止测试环境..."

    COMPOSE_CMD=$(get_compose_cmd)
    $COMPOSE_CMD -f $COMPOSE_FILE -p $PROJECT_NAME down

    log_success "测试环境已停止"
}

# 重启测试环境
restart_env() {
    log_info "重启测试环境..."
    stop_env
    sleep 2
    start_env
}

# 查看环境状态
show_status() {
    log_info "环境状态："

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

# 进入容器 shell
enter_shell() {
    log_info "进入应用容器..."

    COMPOSE_CMD=$(get_compose_cmd)
    $COMPOSE_CMD -f $COMPOSE_FILE -p $PROJECT_NAME exec app bash
}

# 连接测试数据库
connect_db() {
    log_info "连接测试数据库..."

    COMPOSE_CMD=$(get_compose_cmd)
    $COMPOSE_CMD -f $COMPOSE_FILE -p $PROJECT_NAME exec db psql -U test_user -d football_test
}

# 连接 Redis
connect_redis() {
    log_info "连接 Redis..."

    COMPOSE_CMD=$(get_compose_cmd)
    $COMPOSE_CMD -f $COMPOSE_FILE -p $PROJECT_NAME exec redis redis-cli -a test_pass -n 1
}

# 重置测试环境
reset_env() {
    log_warning "这将删除所有测试数据！"
    read -p "确定要继续吗？(y/N): " -n 1 -r
    echo

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "重置测试环境..."

        COMPOSE_CMD=$(get_compose_cmd)
        $COMPOSE_CMD -f $COMPOSE_FILE -p $PROJECT_NAME down -v
        $COMPOSE_CMD -f $COMPOSE_FILE -p $PROJECT_NAME up -d

        log_info "等待服务启动..."
        sleep 20

        # 初始化数据
        init_data

        log_success "测试环境重置完成"
    else
        log_info "操作已取消"
    fi
}

# 初始化测试数据
init_data() {
    log_info "初始化测试数据..."

    COMPOSE_CMD=$(get_compose_cmd)

    # 初始化数据库
    $COMPOSE_CMD -f $COMPOSE_FILE -p $PROJECT_NAME exec -T app python scripts/load_test_data.py --env=test --all

    log_success "测试数据初始化完成"
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
    if $COMPOSE_CMD -f $COMPOSE_FILE -p $PROJECT_NAME exec -T db pg_isready -U test_user -d football_test &> /dev/null; then
        log_success "✅ 数据库连接正常"
    else
        log_warning "⚠️ 数据库未就绪"
    fi

    # 检查 Redis
    if $COMPOSE_CMD -f $COMPOSE_FILE -p $PROJECT_NAME exec -T redis redis-cli -a test_pass ping &> /dev/null; then
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
}

# 显示服务 URL
show_service_urls() {
    echo
    log_info "服务访问地址："
    echo -e "  📱 应用 API:    ${GREEN}http://localhost:8000${NC}"
    echo -e "  📊 API 文档:    ${GREEN}http://localhost:8000/docs${NC}"
    echo -e "  🌐 Nginx 代理:  ${GREEN}http://localhost:81${NC}"
    echo -e "  🗄️  数据库:      ${GREEN}localhost:5433${NC} (test_user/football_test)"
    echo -e "  🗃️  Redis:       ${GREEN}localhost:6380${NC} (密码: test_pass)"
    echo -e "  📨 Kafka:       ${GREEN}localhost:9093${NC}"
    echo -e "  📈 MLflow:      ${GREEN}http://localhost:5001${NC}"
    echo
}

# 运行测试
run_tests() {
    local test_type=$1
    COMPOSE_CMD=$(get_compose_cmd)

    case $test_type in
        unit)
            log_info "运行单元测试..."
            $COMPOSE_CMD -f $COMPOSE_FILE -p $PROJECT_NAME exec app pytest tests/unit/ -v
            ;;
        integration)
            log_info "运行集成测试..."
            $COMPOSE_CMD -f $COMPOSE_FILE -p $PROJECT_NAME exec app pytest tests/integration/ -v
            ;;
        e2e)
            log_info "运行端到端测试..."
            $COMPOSE_CMD -f $COMPOSE_FILE -p $PROJECT_NAME exec app pytest tests/e2e/ -v
            ;;
        all)
            log_info "运行所有测试..."
            $COMPOSE_CMD -f $COMPOSE_FILE -p $PROJECT_NAME exec app pytest tests/ -v
            ;;
        coverage)
            log_info "生成测试覆盖率报告..."
            $COMPOSE_CMD -f $COMPOSE_FILE -p $PROJECT_NAME exec app pytest --cov=src --cov-report=html
            ;;
        *)
            log_error "未知的测试类型: $test_type"
            log_info "可用的测试类型: unit, integration, e2e, all, coverage"
            exit 1
            ;;
    esac
}

# 清理 Docker 资源
clean_docker() {
    log_info "清理未使用的 Docker 资源..."

    # 清理停止的容器
    docker container prune -f

    # 清理未使用的镜像
    docker image prune -f

    # 清理未使用的网络
    docker network prune -f

    # 清理未使用的卷（小心使用）
    # docker volume prune -f

    log_success "Docker 资源清理完成"
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
            test)
                if [ -z "$2" ]; then
                    log_error "请指定测试类型"
                    show_help
                    exit 1
                fi
                run_tests "$2"
                exit 0
                ;;
            start|stop|restart|status|logs|shell|db|redis|reset|init|check|clean)
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
        reset)
            reset_env
            ;;
        init)
            init_data
            ;;
        check)
            check_health
            ;;
        clean)
            clean_docker
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
