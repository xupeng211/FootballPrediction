#!/bin/bash

# 生产环境部署脚本
# Production Deployment Script

set -e  # 遇到错误立即退出

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
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

# 检查前置条件
check_prerequisites() {
    log_info "检查部署前置条件..."

    # 检查Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker未安装"
        exit 1
    fi

    # 检查Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose未安装"
        exit 1
    fi

    # 检查Python
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3未安装"
        exit 1
    fi

    # 检查Git
    if ! command -v git &> /dev/null; then
        log_error "Git未安装"
        exit 1
    fi

    # 检查环境变量文件
    if [[ ! -f ".env.production" ]]; then
        log_error "生产环境配置文件 .env.production 不存在"
        exit 1
    fi

    log_success "前置条件检查通过"
}

# 备份当前版本
backup_current_version() {
    log_info "备份当前版本..."

    BACKUP_DIR="/tmp/football_prediction_backup_$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$BACKUP_DIR"

    # 备份数据库（如果存在）
    if docker ps | grep -q football_prediction_db; then
        log_info "备份数据库..."
        docker exec football_prediction_db pg_dump -U postgres football_prediction > "$BACKUP_DIR/database.sql"
        log_success "数据库备份完成"
    fi

    # 备份当前代码
    cp -r . "$BACKUP_DIR/code" 2>/dev/null || true

    log_success "备份完成: $BACKUP_DIR"
}

# 更新代码
update_code() {
    log_info "更新代码..."

    # 拉取最新代码
    git fetch origin
    git pull origin main

    # 检查代码更新
    if [[ $? -ne 0 ]]; then
        log_error "代码更新失败"
        exit 1
    fi

    log_success "代码更新完成"
}

# 构建Docker镜像
build_images() {
    log_info "构建Docker镜像..."

    # 构建应用镜像
    docker build -t football-prediction:latest .

    if [[ $? -ne 0 ]]; then
        log_error "Docker镜像构建失败"
        exit 1
    fi

    log_success "Docker镜像构建完成"
}

# 运行健康检查
run_health_checks() {
    log_info "运行健康检查..."

    # 等待服务启动
    sleep 30

    # 检查应用健康状态
    HEALTH_URL="http://localhost:8000/api/v1/health"
    MAX_RETRIES=30
    RETRY_COUNT=0

    while [[ $RETRY_COUNT -lt $MAX_RETRIES ]]; do
        if curl -f -s "$HEALTH_URL" > /dev/null; then
            log_success "应用健康检查通过"
            return 0
        fi

        log_warning "健康检查失败，重试中... ($((RETRY_COUNT + 1))/$MAX_RETRIES)"
        sleep 10
        ((RETRY_COUNT++))
    done

    log_error "健康检查失败，部署可能存在问题"
    return 1
}

# 滚动更新
rolling_update() {
    log_info "执行滚动更新..."

    # 更新主服务
    docker-compose -f docker-compose.prod.yml up -d --no-deps app

    # 等待主服务健康
    if ! run_health_checks; then
        log_error "主服务健康检查失败，回滚部署"
        rollback
        exit 1
    fi

    log_success "滚动更新完成"
}

# 回滚部署
rollback() {
    log_warning "开始回滚部署..."

    # 停止新服务
    docker-compose -f docker-compose.prod.yml down

    # 恢复备份（如果需要）
    # 这里可以添加数据库恢复逻辑

    log_warning "回滚完成，请检查系统状态"
}

# 清理资源
cleanup() {
    log_info "清理未使用的Docker资源..."

    # 清理未使用的镜像
    docker image prune -f

    # 清理未使用的容器
    docker container prune -f

    log_success "资源清理完成"
}

# 部署监控
setup_monitoring() {
    log_info "部署监控系统..."

    # 启动监控服务
    docker-compose -f docker-compose.monitoring.yml up -d

    log_success "监控系统部署完成"
}

# 发送通知
send_notification() {
    local status=$1
    local message=$2

    # 这里可以添加Slack、邮件等通知逻辑
    log_info "部署通知: $status - $message"

    # 示例Slack通知（需要配置Webhook）
    # if [[ -n "$SLACK_WEBHOOK_URL" ]]; then
    #     curl -X POST -H 'Content-type: application/json' \
    #         --data "{\"text\":\"Football Prediction 部署 $status: $message\"}" \
    #         "$SLACK_WEBHOOK_URL"
    # fi
}

# 主部署流程
main() {
    log_info "开始生产环境部署..."

    # 解析命令行参数
    SKIP_BACKUP=false
    SKIP_TESTS=false
    ROLLBACK=false

    while [[ $# -gt 0 ]]; do
        case $1 in
            --skip-backup)
                SKIP_BACKUP=true
                shift
                ;;
            --skip-tests)
                SKIP_TESTS=true
                shift
                ;;
            --rollback)
                ROLLBACK=true
                shift
                ;;
            *)
                log_error "未知参数: $1"
                exit 1
                ;;
        esac
    done

    # 回滚模式
    if [[ "$ROLLBACK" == true ]]; then
        rollback
        exit 0
    fi

    # 部署流程
    trap 'log_error "部署过程中发生错误，正在清理..."; cleanup; send_notification "FAILED" "部署失败"; exit 1' ERR

    check_prerequisites

    if [[ "$SKIP_BACKUP" != true ]]; then
        backup_current_version
    fi

    update_code

    # 运行测试（如果未跳过）
    if [[ "$SKIP_TESTS" != true ]]; then
        log_info "运行测试..."
        make test.unit
        log_success "测试通过"
    fi

    build_images
    rolling_update
    setup_monitoring
    cleanup

    log_success "生产环境部署完成！"
    send_notification "SUCCESS" "部署成功"
}

# 脚本入口
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi