#!/bin/bash

# 滚动更新部署脚本
# 适用于单实例的滚动更新策略

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

# 配置
ENV_FILE=".env.production"
COMPOSE_FILE="docker-compose.prod.yml"
HEALTH_CHECK_URL="http://localhost:8000/api/health"
HEALTH_CHECK_TIMEOUT=300
HEALTH_CHECK_INTERVAL=5
MAX_RETRIES=3

# 部署配置
DEPLOY_IMAGE_TAG=${DEPLOY_IMAGE_TAG:-"latest}
UPDATE_STRATEGY=${UPDATE_STRATEGY:-"rolling"}
REPLICAS=${REPLICAS:-2}

# 显示帮助信息
show_help() {
    echo "滚动更新部署脚本"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  -t, --tag TAG          指定部署镜像标签（默认: latest）"
    echo "  -r, --replicas NUM     指定副本数（默认: 2）"
    echo "  -s, --strategy STRAT   更新策略（rolling/ recreate）"
    echo "  --max-retries NUM     最大重试次数（默认: 3）"
    echo "  --no-backup           跳过数据库备份"
    echo "  -f, --force           强制部署"
    echo "  -h, --help            显示帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 -t v1.0.0 -r 3"
    echo "  $0 --tag production-20241013 --strategy recreate"
}

# 解析命令行参数
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -t|--tag)
                DEPLOY_IMAGE_TAG="$2"
                shift 2
                ;;
            -r|--replicas)
                REPLICAS="$2"
                shift 2
                ;;
            -s|--strategy)
                UPDATE_STRATEGY="$2"
                shift 2
                ;;
            --max-retries)
                MAX_RETRIES="$2"
                shift 2
                ;;
            --no-backup)
                BACKUP_ENABLED=false
                shift
                ;;
            -f|--force)
                FORCE_DEPLOY=true
                shift
                ;;
            -h|--help)
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
}

# 检查环境
check_environment() {
    log_info "检查部署环境..."

    # 检查必要文件
    if [ ! -f "$ENV_FILE" ]; then
        log_error "环境文件不存在: $ENV_FILE"
        exit 1
    fi

    # 检查Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker 未安装"
        exit 1
    fi

    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose 未安装"
        exit 1
    fi

    log_success "环境检查通过"
}

# 获取当前服务状态
get_service_status() {
    log_info "获取当前服务状态..."

    # 获取运行中的容器
    RUNNING_CONTAINERS=$(docker-compose -f "$COMPOSE_FILE" ps -q | wc -l)
    log_info "当前运行的容器数: $RUNNING_CONTAINERS"

    # 检查服务健康状态
    if curl -f "$HEALTH_CHECK_URL" > /dev/null 2>&1; then
        log_info "服务健康状态: 正常"
        SERVICE_HEALTHY=true
    else
        log_warning "服务健康状态: 异常"
        SERVICE_HEALTHY=false
    fi
}

# 备份当前部署
backup_current_deployment() {
    if [ "$BACKUP_ENABLED" = false ]; then
        log_info "跳过备份"
        return
    fi

    log_info "备份当前部署..."

    BACKUP_DIR="backups/rolling/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$BACKUP_DIR"

    # 备份配置文件
    cp "$COMPOSE_FILE" "$BACKUP_DIR/docker-compose.yml"
    cp "$ENV_FILE" "$BACKUP_DIR/.env.production"

    # 导出镜像列表
    docker-compose -f "$COMPOSE_FILE" images > "$BACKUP_DIR/images.txt"

    # 备份数据库
    docker-compose -f "$COMPOSE_FILE" exec -T db pg_dump -U $DB_USER $DB_NAME \
        | gzip > "$BACKUP_DIR/database.sql.gz"

    log_success "部署已备份到: $BACKUP_DIR"
}

# 构建新镜像
build_new_image() {
    log_info "构建新镜像: $DEPLOY_IMAGE_TAG"

    # 构建镜像
    docker build \
        -t football-prediction:$DEPLOY_IMAGE_TAG \
        .

    # 打标签为latest
    docker tag football-prediction:$DEPLOY_IMAGE_TAG football-prediction:latest

    log_success "镜像构建完成"
}

# 拉取新镜像
pull_new_image() {
    log_info "拉取新镜像: $DEPLOY_IMAGE_TAG"

    # 如果是私有仓库，先登录
    if [ -n "$DOCKER_REGISTRY_URL" ]; then
        docker login -u "$DOCKER_REGISTRY_USER" -p "$DOCKER_REGISTRY_PASSWORD" "$DOCKER_REGISTRY_URL"
    fi

    # 拉取镜像
    docker pull football-prediction:$DEPLOY_IMAGE_TAG
    docker tag football-prediction:$DEPLOY_IMAGE_TAG football-prediction:latest

    log_success "镜像拉取完成"
}

# 执行滚动更新
perform_rolling_update() {
    log_info "执行滚动更新..."

    local retry_count=0
    local success=false

    while [ $retry_count -lt $MAX_RETRIES ] && [ "$success" = false ]; do
        log_info "尝试更新 ($((retry_count + 1))/$MAX_RETRIES)..."

        # 更新服务
        if [ "$UPDATE_STRATEGY" = "recreate" ]; then
            # 重建策略：先停止再启动
            docker-compose -f "$COMPOSE_FILE" down
            docker-compose -f "$COMPOSE_FILE" up -d --force-recreate
        else
            # 滚动更新策略：逐个更新容器
            docker-compose -f "$COMPOSE_FILE" up -d --no-deps app
        fi

        # 等待服务就绪
        if wait_for_service; then
            success=true
        else
            retry_count=$((retry_count + 1))
            if [ $retry_count -lt $MAX_RETRIES ]; then
                log_warning "更新失败，准备重试..."
                sleep 10
            fi
        fi
    done

    if [ "$success" = false ]; then
        log_error "滚动更新失败，已达到最大重试次数"
        return 1
    fi

    log_success "滚动更新完成"
}

# 等待服务就绪
wait_for_service() {
    log_info "等待服务就绪..."

    local elapsed=0
    while [ $elapsed -lt $HEALTH_CHECK_TIMEOUT ]; do
        if curl -f "$HEALTH_CHECK_URL" > /dev/null 2>&1; then
            log_success "服务就绪"
            return 0
        fi

        echo -n "."
        sleep $HEALTH_CHECK_INTERVAL
        elapsed=$((elapsed + HEALTH_CHECK_INTERVAL))
    done

    log_error "服务启动超时"
    return 1
}

# 运行健康检查
run_health_checks() {
    log_info "运行健康检查..."

    # API健康检查
    if ! curl -f "$HEALTH_CHECK_URL" > /dev/null; then
        log_error "API健康检查失败"
        return 1
    fi

    # 数据库连接检查
    if ! docker-compose -f "$COMPOSE_FILE" exec db pg_isready -U $DB_USER > /dev/null 2>&1; then
        log_error "数据库连接失败"
        return 1
    fi

    # Redis连接检查
    if ! docker-compose -f "$COMPOSE_FILE" exec redis redis-cli ping > /dev/null 2>&1; then
        log_error "Redis连接失败"
        return 1
    fi

    log_success "所有健康检查通过"
}

# 运行冒烟测试
run_smoke_tests() {
    log_info "运行冒烟测试..."

    # 测试基本端点
    local endpoints=(
        "/api/health"
        "/api/v1/data/matches"
        "/api/v1/features/predictions"
    )

    for endpoint in "${endpoints[@]}"; do
        if curl -f "http://localhost:8000$endpoint" > /dev/null 2>&1; then
            log_info "✓ $endpoint"
        else
            log_error "✗ $endpoint"
            return 1
        fi
    done

    log_success "冒烟测试通过"
}

# 验证部署
verify_deployment() {
    log_info "验证部署..."

    # 检查容器状态
    local unhealthy_containers=$(docker-compose -f "$COMPOSE_FILE" ps | grep -c "unhealthy\|exited")
    if [ "$unhealthy_containers" -gt 0 ]; then
        log_error "发现不健康的容器: $unhealthy_containers"
        return 1
    fi

    # 检查资源使用
    local memory_usage=$(docker stats --no-stream --format "table {{.MemUsage}}" | tail -n +2 | awk '{sum+=$1} END {print sum}')
    log_info "内存使用: $memory_usage"

    # 检查错误日志
    local error_count=$(docker-compose -f "$COMPOSE_FILE" logs --tail=100 | grep -i error | wc -l)
    if [ "$error_count" -gt 10 ]; then
        log_warning "发现较多错误日志: $error_count"
    fi

    log_success "部署验证通过"
}

# 发送通知
send_notification() {
    local status=$1
    local message="Football Prediction 滚动更新${status}: 标签=${DEPLOY_IMAGE_TAG}, 策略=${UPDATE_STRATEGY}"

    # Slack通知
    if [ -n "$SLACK_WEBHOOK_URL" ]; then
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"$message\"}" \
            "$SLACK_WEBHOOK_URL"
    fi

    log_info "通知已发送: $message"
}

# 回滚到上一个版本
rollback() {
    log_error "部署失败，开始回滚..."

    # 获取最新的备份
    local latest_backup=$(ls -t backups/rolling/ | head -n 1)
    if [ -z "$latest_backup" ]; then
        log_error "没有找到备份，无法回滚"
        exit 1
    fi

    log_info "使用备份: $latest_backup"

    # 恢复配置
    cp "backups/rolling/$latest_backup/docker-compose.yml" "$COMPOSE_FILE"
    cp "backups/rolling/$latest_backup/.env.production" "$ENV_FILE"

    # 使用备份的镜像
    while read -r image; do
        docker pull "$image" 2>/dev/null || true
    done < "backups/rolling/$latest_backup/images.txt"

    # 重新部署
    docker-compose -f "$COMPOSE_FILE" down
    docker-compose -f "$COMPOSE_FILE" up -d

    # 等待服务恢复
    sleep 30

    # 恢复数据库（如果需要）
    if [ "$RESTORE_DB" = true ]; then
        log_info "恢复数据库..."
        docker-compose -f "$COMPOSE_FILE" exec -T db dropdb -U $DB_USER $DB_NAME
        docker-compose -f "$COMPOSE_FILE" exec -T db createdb -U $DB_USER $DB_NAME
        gunzip -c "backups/rolling/$latest_backup/database.sql.gz" | \
            docker-compose -f "$COMPOSE_FILE" exec -T db psql -U $DB_USER -d $DB_NAME
    fi

    send_notification "失败并回滚"
    log_error "已回滚到备份版本"
}

# 主函数
main() {
    log_info "开始滚动更新部署..."
    log_info "镜像标签: $DEPLOY_IMAGE_TAG"
    log_info "更新策略: $UPDATE_STRATEGY"
    log_info "副本数: $REPLICAS"

    # 解析参数
    parse_args "$@"

    # 检查环境
    check_environment

    # 获取当前状态
    get_service_status

    # 备份当前部署
    backup_current_deployment

    # 构建或拉取新镜像
    if [ "$BUILD_IMAGE" = true ]; then
        build_new_image
    else
        pull_new_image
    fi

    # 执行滚动更新
    if ! perform_rolling_update; then
        rollback
        exit 1
    fi

    # 等待服务就绪
    if ! wait_for_service; then
        rollback
        exit 1
    fi

    # 运行健康检查
    if ! run_health_checks; then
        rollback
        exit 1
    fi

    # 运行冒烟测试
    if ! run_smoke_tests; then
        log_warning "冒烟测试失败，但继续部署"
    fi

    # 验证部署
    verify_deployment

    # 发送成功通知
    send_notification "成功"

    log_success "滚动更新部署完成！"
}

# 错误处理
trap 'rollback' ERR

# 运行主函数
main "$@"
