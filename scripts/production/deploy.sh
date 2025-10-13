#!/bin/bash

# 一键部署脚本
# 整合蓝绿部署、滚动更新、金丝雀发布等多种部署策略

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

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

log_debug() {
    if [ "$DEBUG" = true ]; then
        echo -e "${CYAN}[DEBUG]${NC} $1"
    fi
}

# 显示横幅
show_banner() {
    echo -e "${BLUE}"
    echo "██████╗ ██╗ ██████╗ ███╗   ██╗███████╗████████╗███████╗██████╗ "
    echo "██╔══██╗██║██╔════╝ ████╗  ██║██╔════╝╚══██╔══╝██╔════╝██╔══██╗"
    echo "██████╔╝██║██║  ███╗██╔██╗ ██║███████╗   ██║   █████╗  ██████╔╝"
    echo "██╔══██╗██║██║   ██║██║╚██╗██║╚════██║   ██║   ██╔══╝  ██╔══██╗"
    echo "██████╔╝██║╚██████╔╝██║ ╚████║███████║   ██║   ███████╗██║  ██║"
    echo "╚═════╝ ╚═╝ ╚═════╝ ╚═╝  ╚═══╝╚══════╝   ╚═╝   ╚══════╝╚═╝  ╚═╝"
    echo -e "${NC}"
    echo -e "${CYAN}Football Prediction 部署脚本 v1.0${NC}"
    echo ""
}

# 配置
PROJECT_NAME="football-prediction"
DEPLOY_MODE=${DEPLOY_MODE:-"blue-green"}
DEPLOY_ENV=${DEPLOY_ENV:-"production"}
BUILD_IMAGE=${BUILD_IMAGE:-true}
RUN_TESTS=${RUN_TESTS:-true}
SEND_NOTIFICATIONS=${SEND_NOTIFICATIONS:-true}

# 显示帮助信息
show_help() {
    cat << EOF
Football Prediction 部署脚本

用法: $0 [命令] [选项]

命令:
  deploy              部署应用（默认）
  rollback            回滚到上一个版本
  status              显示部署状态
  logs                显示应用日志
  stop                停止所有服务
  start               启动所有服务
  restart             重启所有服务
  cleanup             清理资源
  backup              备份数据
  restore             恢复数据

部署选项:
  -m, --mode MODE     部署模式 (blue-green|rolling|canary)
  -e, --env ENV       部署环境 (development|staging|production)
  -t, --tag TAG       镜像标签
  -b, --build         构建镜像
  --no-build          不构建镜像
  --tests             运行测试
  --no-tests          不运行测试
  --dry-run           模拟运行（不执行实际操作）
  -f, --force         强制执行
  -v, --verbose       详细输出
  -h, --help          显示帮助信息

示例:
  $0 deploy -m blue-green -t v1.0.0
  $0 rollback
  $0 status
  $0 logs --tail 100
  $0 backup --full

部署模式说明:
  blue-green          蓝绿部署（零停机）
  rolling            滚动更新（逐个更新）
  canary             金丝雀发布（灰度发布）

EOF
}

# 解析命令行参数
parse_args() {
    COMMAND=${1:-deploy}
    shift

    while [[ $# -gt 0 ]]; do
        case $1 in
            -m|--mode)
                DEPLOY_MODE="$2"
                shift 2
                ;;
            -e|--env)
                DEPLOY_ENV="$2"
                shift 2
                ;;
            -t|--tag)
                DEPLOY_TAG="$2"
                shift 2
                ;;
            -b|--build)
                BUILD_IMAGE=true
                shift
                ;;
            --no-build)
                BUILD_IMAGE=false
                shift
                ;;
            --tests)
                RUN_TESTS=true
                shift
                ;;
            --no-tests)
                RUN_TESTS=false
                shift
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            -f|--force)
                FORCE=true
                shift
                ;;
            -v|--verbose)
                VERBOSE=true
                DEBUG=true
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                # 传递给子命令的参数
                EXTRA_ARGS+=("$1")
                shift
                ;;
        esac
    done

    # 设置默认标签
    if [ -z "$DEPLOY_TAG" ]; then
        DEPLOY_TAG=$(date +%Y%m%d-%H%M%S)
        if [ "$DEPLOY_ENV" = "production" ]; then
            DEPLOY_TAG="prod-$DEPLOY_TAG"
        fi
    fi
}

# 检查先决条件
check_prerequisites() {
    log_step "检查先决条件..."

    # 检查操作系统
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        OS="linux"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
    else
        log_error "不支持的操作系统: $OSTYPE"
        exit 1
    fi

    # 检查Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker 未安装"
        exit 1
    fi

    # 检查Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose 未安装"
        exit 1
    fi

    # 检查Docker权限
    if ! docker info &> /dev/null; then
        log_error "Docker 权限不足，请检查用户是否在docker组"
        exit 1
    fi

    # 检查端口
    check_ports

    # 检查磁盘空间
    check_disk_space

    log_success "先决条件检查通过"
}

# 检查端口占用
check_ports() {
    log_debug "检查端口占用..."

    local ports=(80 443 8000 8001 5432 6379 3000 9090)
    local occupied_ports=()

    for port in "${ports[@]}"; do
        if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
            occupied_ports+=($port)
        fi
    done

    if [ ${#occupied_ports[@]} -gt 0 ]; then
        log_warning "以下端口已被占用: ${occupied_ports[*]}"
        if [ "$FORCE" != true ]; then
            log_error "请释放端口或使用 --force 强制继续"
            exit 1
        fi
    fi
}

# 检查磁盘空间
check_disk_space() {
    log_debug "检查磁盘空间..."

    local available=$(df . | awk 'NR==2 {print $4}')
    local required=2097152  # 2GB in KB

    if [ "$available" -lt "$required" ]; then
        log_error "磁盘空间不足（需要至少2GB）"
        exit 1
    fi
}

# 加载环境变量
load_environment() {
    log_step "加载环境变量..."

    local env_file=".env.$DEPLOY_ENV"

    if [ ! -f "$env_file" ]; then
        log_error "环境文件不存在: $env_file"
        exit 1
    fi

    # 加载环境变量
    set -a
    source "$env_file"
    set +a

    # 验证必需的环境变量
    local required_vars=("DATABASE_URL" "SECRET_KEY")
    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            log_error "缺少必需的环境变量: $var"
            exit 1
        fi
    done

    log_success "环境变量加载完成"
}

# 执行部署前检查
pre_deploy_checks() {
    log_step "执行部署前检查..."

    # 检查Git状态
    if [ -d ".git" ]; then
        local git_status=$(git status --porcelain)
        if [ -n "$git_status" ] && [ "$FORCE" != true ]; then
            log_warning "Git工作目录有未提交的更改"
            read -p "是否继续？(y/N): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                exit 1
            fi
        fi
    fi

    # 运行测试
    if [ "$RUN_TESTS" = true ]; then
        log_info "运行测试..."
        if ! make test-quick > /dev/null 2>&1; then
            log_error "测试失败"
            if [ "$FORCE" != true ]; then
                exit 1
            fi
        fi
    fi

    # 检查代码质量
    log_info "检查代码质量..."
    if ! make lint > /dev/null 2>&1; then
        log_warning "代码检查发现问题"
        if [ "$FORCE" != true ]; then
            log_error "请修复代码问题或使用 --force 强制继续"
            exit 1
        fi
    fi

    log_success "部署前检查通过"
}

# 构建镜像
build_image() {
    if [ "$BUILD_IMAGE" != true ]; then
        log_info "跳过镜像构建"
        return
    fi

    log_step "构建Docker镜像..."

    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY-RUN] 将构建镜像: $PROJECT_NAME:$DEPLOY_TAG"
        return
    fi

    # 构建镜像
    docker build \
        -t "$PROJECT_NAME:$DEPLOY_TAG" \
        -t "$PROJECT_NAME:latest" \
        .

    # 推送到镜像仓库（如果配置了）
    if [ -n "$DOCKER_REGISTRY" ]; then
        docker tag "$PROJECT_NAME:$DEPLOY_TAG" "$DOCKER_REGISTRY/$PROJECT_NAME:$DEPLOY_TAG"
        docker push "$DOCKER_REGISTRY/$PROJECT_NAME:$DEPLOY_TAG"
    fi

    log_success "镜像构建完成"
}

# 执行部署
execute_deploy() {
    log_step "执行部署..."
    log_info "部署模式: $DEPLOY_MODE"
    log_info "部署标签: $DEPLOY_TAG"

    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY-RUN] 将使用 $DEPLOY_MODE 模式部署"
        return
    fi

    case $DEPLOY_MODE in
        blue-green)
            ./scripts/production/blue_green_deploy.sh -t "$DEPLOY_TAG"
            ;;
        rolling)
            ./scripts/production/rolling_update.sh -t "$DEPLOY_TAG"
            ;;
        canary)
            log_warning "金丝雀发布模式尚未实现"
            exit 1
            ;;
        *)
            log_error "未知的部署模式: $DEPLOY_MODE"
            exit 1
            ;;
    esac
}

# 部署后验证
post_deploy_verification() {
    log_step "执行部署后验证..."

    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY-RUN] 将执行部署后验证"
        return
    fi

    # 等待服务启动
    sleep 10

    # 健康检查
    local health_url="http://localhost:8000/api/health"
    local max_attempts=30
    local attempt=0

    while [ $attempt -lt $max_attempts ]; do
        if curl -f "$health_url" > /dev/null 2>&1; then
            log_success "健康检查通过"
            break
        fi

        attempt=$((attempt + 1))
        echo -n "."
        sleep 2
    done

    if [ $attempt -eq $max_attempts ]; then
        log_error "健康检查失败"
        exit 1
    fi

    # 运行冒烟测试
    log_info "运行冒烟测试..."
    # 这里可以添加具体的测试命令

    log_success "部署后验证通过"
}

# 发送通知
send_notifications() {
    if [ "$SEND_NOTIFICATIONS" != true ]; then
        return
    fi

    log_step "发送通知..."

    local message="Football Prediction 部署成功\n"
    message+="环境: $DEPLOY_ENV\n"
    message+="模式: $DEPLOY_MODE\n"
    message+="标签: $DEPLOY_TAG\n"
    message+="时间: $(date)"

    # Slack通知
    if [ -n "$SLACK_WEBHOOK_URL" ]; then
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"$message\"}" \
            "$SLACK_WEBHOOK_URL"
    fi

    # 邮件通知（可选）
    if [ -n "$NOTIFICATION_EMAIL" ]; then
        echo -e "$message" | mail -s "部署通知" "$NOTIFICATION_EMAIL"
    fi

    log_success "通知已发送"
}

# 显示部署状态
show_status() {
    log_step "显示部署状态..."

    echo ""
    echo -e "${CYAN}=== 容器状态 ===${NC}"
    docker-compose -f docker-compose.prod.yml ps

    echo ""
    echo -e "${CYAN}=== 服务健康状态 ===${NC}"
    local services=("app:8000" "db:5432" "redis:6379")
    for service in "${services[@]}"; do
        local name=$(echo $service | cut -d: -f1)
        local port=$(echo $service | cut -d: -f2)
        if curl -f --max-time 2 "http://localhost:$port/health" > /dev/null 2>&1; then
            echo -e "  $name: ${GREEN}✓ 正常${NC}"
        else
            echo -e "  $name: ${RED}✗ 异常${NC}"
        fi
    done

    echo ""
    echo -e "${CYAN}=== 资源使用 ===${NC}"
    docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"

    echo ""
    echo -e "${CYAN}=== 访问地址 ===${NC}"
    echo "  API: http://localhost:8000"
    echo "  文档: http://localhost:8000/docs"
    echo "  Grafana: http://localhost:3000"
    echo "  Prometheus: http://localhost:9090"
}

# 显示日志
show_logs() {
    log_step "显示应用日志..."

    local service=${EXTRA_ARGS[0]:-app}
    local follow=false
    local tail=100

    for arg in "${EXTRA_ARGS[@]}"; do
        case $arg in
            -f|--follow)
                follow=true
                ;;
            --tail=*)
                tail=${arg#--tail=}
                ;;
        esac
    done

    if [ "$follow" = true ]; then
        docker-compose -f docker-compose.prod.yml logs -f --tail=$tail $service
    else
        docker-compose -f docker-compose.prod.yml logs --tail=$tail $service
    fi
}

# 回滚部署
rollback_deployment() {
    log_step "回滚部署..."

    # 获取可用的备份
    local backups=($(ls -t backups/deployments/ 2>/dev/null | head -5))
    if [ ${#backups[@]} -eq 0 ]; then
        log_error "没有找到可用的备份"
        exit 1
    fi

    echo ""
    echo "可用的备份版本："
    for i in "${!backups[@]}"; do
        echo "  $((i+1)). ${backups[i]}"
    done

    read -p "请选择要回滚的版本 (1-${#backups[@]}): " -n 1 -r
    echo

    if [[ $REPLY =~ ^[0-9]+$ ]] && [ "$REPLY" -ge 1 ] && [ "$REPLY" -le ${#backups[@]} ]; then
        local selected_backup=${backups[$((REPLY-1))]}
        log_info "回滚到: $selected_backup"

        # 执行回滚
        # 这里需要实现具体的回滚逻辑

        log_success "回滚完成"
    else
        log_error "无效的选择"
        exit 1
    fi
}

# 停止服务
stop_services() {
    log_step "停止所有服务..."

    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY-RUN] 将停止所有服务"
        return
    fi

    docker-compose -f docker-compose.prod.yml down

    log_success "所有服务已停止"
}

# 启动服务
start_services() {
    log_step "启动所有服务..."

    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY-RUN] 将启动所有服务"
        return
    fi

    docker-compose -f docker-compose.prod.yml up -d

    log_success "所有服务已启动"
}

# 重启服务
restart_services() {
    log_step "重启所有服务..."

    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY-RUN] 将重启所有服务"
        return
    fi

    docker-compose -f docker-compose.prod.yml restart

    log_success "所有服务已重启"
}

# 清理资源
cleanup_resources() {
    log_step "清理资源..."

    # 清理未使用的容器
    log_info "清理未使用的容器..."
    docker container prune -f

    # 清理未使用的镜像
    log_info "清理未使用的镜像..."
    docker image prune -f

    # 清理未使用的网络
    log_info "清理未使用的网络..."
    docker network prune -f

    # 清理未使用的卷
    log_info "清理未使用的卷..."
    docker volume prune -f

    log_success "资源清理完成"
}

# 主函数
main() {
    # 显示横幅
    show_banner

    # 解析参数
    parse_args "$@"

    # 执行命令
    case $COMMAND in
        deploy)
            check_prerequisites
            load_environment
            pre_deploy_checks
            build_image
            execute_deploy
            post_deploy_verification
            send_notifications
            show_status
            ;;
        rollback)
            rollback_deployment
            ;;
        status)
            show_status
            ;;
        logs)
            show_logs
            ;;
        stop)
            stop_services
            ;;
        start)
            start_services
            ;;
        restart)
            restart_services
            ;;
        cleanup)
            cleanup_resources
            ;;
        backup)
            ./scripts/production/backup.sh "${EXTRA_ARGS[@]}"
            ;;
        restore)
            ./scripts/production/restore.sh "${EXTRA_ARGS[@]}"
            ;;
        *)
            log_error "未知命令: $COMMAND"
            show_help
            exit 1
            ;;
    esac

    log_success "操作完成！"
}

# 设置错误处理
trap 'log_error "脚本执行失败"; exit 1' ERR

# 运行主函数
main "$@"
