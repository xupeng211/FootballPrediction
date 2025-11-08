#!/bin/bash

# 部署管理脚本
# Deployment Manager Script

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_command() {
    echo -e "${CYAN}[COMMAND]${NC} $1"
}

# 显示帮助信息
show_help() {
    cat << EOF
Football Prediction 部署管理工具

用法: $0 [命令] [选项]

命令:
  setup           设置环境
  deploy          部署应用
  update          更新应用
  rollback        回滚部署
  backup          备份数据
  monitor         设置监控
  status          查看状态
  logs            查看日志
  stop            停止服务
  restart         重启服务
  cleanup         清理资源
  help            显示帮助信息

选项:
  --env ENV       指定环境 (development|production) [默认: production]
  --skip-tests    跳过测试
  --skip-backup   跳过备份
  --force         强制执行
  --verbose       详细输出

示例:
  $0 setup                           # 设置生产环境
  $0 setup --env development         # 设置开发环境
  $0 deploy                          # 部署到生产环境
  $0 deploy --env development        # 部署到开发环境
  $0 update --skip-backup            # 更新应用，跳过备份
  $0 rollback                        # 回滚到上一版本
  $0 backup                          # 手动备份
  $0 monitor                         # 设置监控系统
  $0 status                          # 查看服务状态
  $0 logs --env production           # 查看生产环境日志

EOF
}

# 解析命令行参数
parse_args() {
    ENVIRONMENT="production"
    SKIP_TESTS=false
    SKIP_BACKUP=false
    FORCE=false
    VERBOSE=false
    COMMAND=""

    while [[ $# -gt 0 ]]; do
        case $1 in
            setup|deploy|update|rollback|backup|monitor|status|logs|stop|restart|cleanup|help)
                COMMAND="$1"
                shift
                ;;
            --env)
                ENVIRONMENT="$2"
                shift 2
                ;;
            --skip-tests)
                SKIP_TESTS=true
                shift
                ;;
            --skip-backup)
                SKIP_BACKUP=true
                shift
                ;;
            --force)
                FORCE=true
                shift
                ;;
            --verbose)
                VERBOSE=true
                shift
                ;;
            *)
                log_error "未知参数: $1"
                show_help
                exit 1
                ;;
        esac
    done

    if [[ -z "$COMMAND" ]]; then
        log_error "请指定命令"
        show_help
        exit 1
    fi
}

# 验证环境
validate_environment() {
    if [[ "$ENVIRONMENT" != "development" ]] && [[ "$ENVIRONMENT" != "production" ]]; then
        log_error "无效的环境: $ENVIRONMENT (支持: development, production)"
        exit 1
    fi
}

# 检查脚本文件是否存在
check_scripts() {
    local scripts=(
        "setup_environment.sh"
        "production_deploy.sh"
        "backup_database.sh"
        "setup_monitoring.sh"
    )

    for script in "${scripts[@]}"; do
        if [[ ! -f "scripts/deployment/$script" ]]; then
            log_error "脚本文件不存在: scripts/deployment/$script"
            exit 1
        fi
    done
}

# 执行设置
execute_setup() {
    log_info "设置 $ENVIRONMENT 环境..."

    local setup_args=""
    if [[ "$ENVIRONMENT" == "development" ]]; then
        setup_args="--dev --skip-firewall"
    else
        setup_args=""
    fi

    if [[ "$VERBOSE" == true ]]; then
        setup_args="$setup_args --verbose"
    fi

    log_command "./scripts/deployment/setup_environment.sh $setup_args"
    ./scripts/deployment/setup_environment.sh $setup_args

    log_success "环境设置完成"
}

# 执行部署
execute_deploy() {
    log_info "部署到 $ENVIRONMENT 环境..."

    local deploy_args=""
    if [[ "$SKIP_BACKUP" == true ]]; then
        deploy_args="$deploy_args --skip-backup"
    fi
    if [[ "$SKIP_TESTS" == true ]]; then
        deploy_args="$deploy_args --skip-tests"
    fi

    if [[ "$ENVIRONMENT" == "development" ]]; then
        log_command "docker-compose -f docker-compose.yml up -d --build"
        docker-compose -f docker-compose.yml up -d --build
    else
        log_command "./scripts/deployment/production_deploy.sh $deploy_args"
        ./scripts/deployment/production_deploy.sh $deploy_args
    fi

    log_success "部署完成"
}

# 执行更新
execute_update() {
    log_info "更新 $ENVIRONMENT 环境..."

    # 拉取最新代码
    log_command "git pull origin main"
    git pull origin main

    # 重新部署
    execute_deploy

    log_success "更新完成"
}

# 执行回滚
execute_rollback() {
    log_info "回滚 $ENVIRONMENT 环境..."

    if [[ "$ENVIRONMENT" == "development" ]]; then
        log_command "docker-compose -f docker-compose.yml down"
        docker-compose -f docker-compose.yml down

        # 这里可以实现更复杂的回滚逻辑
        log_warning "开发环境回滚完成，请手动恢复代码版本"
    else
        log_command "./scripts/deployment/production_deploy.sh --rollback"
        ./scripts/deployment/production_deploy.sh --rollback
    fi

    log_success "回滚完成"
}

# 执行备份
execute_backup() {
    log_info "备份 $ENVIRONMENT 环境数据..."

    local backup_args=""
    if [[ "$SKIP_CLEANUP" == true ]]; then
        backup_args="$backup_args --skip-cleanup"
    fi

    log_command "./scripts/deployment/backup_database.sh $backup_args"
    ./scripts/deployment/backup_database.sh $backup_args

    log_success "备份完成"
}

# 设置监控
execute_monitor() {
    log_info "设置 $ENVIRONMENT 环境监控..."

    log_command "./scripts/deployment/setup_monitoring.sh"
    ./scripts/deployment/setup_monitoring.sh

    if [[ "$ENVIRONMENT" == "production" ]]; then
        log_command "docker-compose -f docker-compose.monitoring.yml up -d"
        docker-compose -f docker-compose.monitoring.yml up -d
    fi

    log_success "监控设置完成"
}

# 查看状态
execute_status() {
    log_info "查看 $ENVIRONMENT 环境状态..."

    echo "=== Docker 容器状态 ==="
    if [[ "$ENVIRONMENT" == "development" ]]; then
        docker-compose -f docker-compose.yml ps
    else
        docker-compose -f docker-compose.prod.yml ps
    fi

    echo -e "\n=== 服务健康检查 ==="

    # 检查应用健康状态
    local health_url="http://localhost:8000/api/v1/health"
    if curl -f -s "$health_url" > /dev/null 2>&1; then
        log_success "应用服务: 健康"
    else
        log_error "应用服务: 不可用"
    fi

    # 检查数据库连接
    if docker exec football-prediction-db pg_isready -U postgres > /dev/null 2>&1; then
        log_success "数据库: 健康"
    else
        log_error "数据库: 不可用"
    fi

    # 检查Redis连接
    if docker exec football-prediction-redis redis-cli ping > /dev/null 2>&1; then
        log_success "Redis: 健康"
    else
        log_error "Redis: 不可用"
    fi

    # 显示资源使用情况
    echo -e "\n=== 资源使用情况 ==="
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"

    # 显示磁盘使用情况
    echo -e "\n=== 磁盘使用情况 ==="
    df -h | grep -E "(Filesystem|/dev/)"

    if [[ "$ENVIRONMENT" == "production" ]]; then
        echo -e "\n=== 监控服务状态 ==="
        if docker-compose -f docker-compose.monitoring.yml ps > /dev/null 2>&1; then
            docker-compose -f docker-compose.monitoring.yml ps
        else
            log_warning "监控服务未运行"
        fi
    fi
}

# 查看日志
execute_logs() {
    log_info "查看 $ENVIRONMENT 环境日志..."

    local service=""
    if [[ -n "$1" ]]; then
        service="$1"
    fi

    if [[ "$ENVIRONMENT" == "development" ]]; then
        if [[ -n "$service" ]]; then
            log_command "docker-compose -f docker-compose.yml logs -f $service"
            docker-compose -f docker-compose.yml logs -f "$service"
        else
            log_command "docker-compose -f docker-compose.yml logs -f"
            docker-compose -f docker-compose.yml logs -f
        fi
    else
        if [[ -n "$service" ]]; then
            log_command "docker-compose -f docker-compose.prod.yml logs -f $service"
            docker-compose -f docker-compose.prod.yml logs -f "$service"
        else
            log_command "docker-compose -f docker-compose.prod.yml logs -f"
            docker-compose -f docker-compose.prod.yml logs -f
        fi
    fi
}

# 停止服务
execute_stop() {
    log_info "停止 $ENVIRONMENT 环境服务..."

    if [[ "$ENVIRONMENT" == "development" ]]; then
        log_command "docker-compose -f docker-compose.yml down"
        docker-compose -f docker-compose.yml down
    else
        log_command "docker-compose -f docker-compose.prod.yml down"
        docker-compose -f docker-compose.prod.yml down
    fi

    if [[ "$ENVIRONMENT" == "production" ]]; then
        log_command "docker-compose -f docker-compose.monitoring.yml down"
        docker-compose -f docker-compose.monitoring.yml down
    fi

    log_success "服务已停止"
}

# 重启服务
execute_restart() {
    log_info "重启 $ENVIRONMENT 环境服务..."

    execute_stop
    sleep 5
    execute_deploy

    log_success "服务已重启"
}

# 清理资源
execute_cleanup() {
    log_info "清理 $ENVIRONMENT 环境资源..."

    # 停止所有服务
    execute_stop

    # 清理Docker资源
    log_command "docker system prune -f"
    docker system prune -f

    # 清理日志文件
    if [[ -d "logs" ]]; then
        log_command "find logs -name '*.log' -mtime +7 -delete"
        find logs -name '*.log' -mtime +7 -delete
    fi

    # 清理备份文件
    if [[ -d "backups" ]]; then
        log_command "find backups -name '*.sql.gz' -mtime +30 -delete"
        find backups -name '*.sql.gz' -mtime +30 -delete
    fi

    log_success "资源清理完成"
}

# 显示欢迎信息
show_welcome() {
    echo -e "${CYAN}"
    cat << "EOF"
███╗   ██╗███████╗████████╗███████╗██████╗ ███╗   ███╗
████╗  ██║██╔════╝╚══██╔══╝██╔════╝██╔══██╗████╗ ████║
██╔██╗ ██║█████╗     ██║   █████╗  ██████╔╝██╔████╔██║
██║╚██╗██║██╔══╝     ██║   ██╔══╝  ██╔══██╗██║╚██╔╝██║
██║ ╚████║███████╗   ██║   ███████╗██║  ██║██║ ╚═╝ ██║
╚═╝  ╚═══╝╚══════╝   ╚═╝   ╚══════╝╚═╝  ╚═╝╚═╝     ╚═╝

                    部署管理工具 v1.0.0
EOF
    echo -e "${NC}"
}

# 主函数
main() {
    show_welcome

    # 解析参数
    parse_args "$@"

    # 验证环境
    validate_environment

    # 检查脚本文件
    if [[ "$COMMAND" != "help" ]]; then
        check_scripts
    fi

    # 显示详细信息
    if [[ "$VERBOSE" == true ]]; then
        log_info "环境: $ENVIRONMENT"
        log_info "命令: $COMMAND"
        log_info "跳过测试: $SKIP_TESTS"
        log_info "跳过备份: $SKIP_BACKUP"
        log_info "强制执行: $FORCE"
    fi

    # 执行命令
    case "$COMMAND" in
        help)
            show_help
            ;;
        setup)
            execute_setup
            ;;
        deploy)
            execute_deploy
            ;;
        update)
            execute_update
            ;;
        rollback)
            execute_rollback
            ;;
        backup)
            execute_backup
            ;;
        monitor)
            execute_monitor
            ;;
        status)
            execute_status
            ;;
        logs)
            execute_logs "$2"
            ;;
        stop)
            execute_stop
            ;;
        restart)
            execute_restart
            ;;
        cleanup)
            execute_cleanup
            ;;
        *)
            log_error "未知命令: $COMMAND"
            show_help
            exit 1
            ;;
    esac

    log_success "命令执行完成！"
}

# 脚本入口
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi