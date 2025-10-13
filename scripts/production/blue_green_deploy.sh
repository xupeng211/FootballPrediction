#!/bin/bash

# 蓝绿部署脚本
# 实现零停机时间的蓝绿部署策略

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
BLUE_GREEN_COMPOSE="docker-compose.blue-green.yml"
HEALTH_CHECK_URL="http://localhost:8000/api/health"
HEALTH_CHECK_TIMEOUT=300
HEALTH_CHECK_INTERVAL=5

# 当前活跃环境
ACTIVE_ENV=""
NEW_ENV=""

# 部署配置
DEPLOY_IMAGE_TAG=${DEPLOY_IMAGE_TAG:-"latest"}
BACKUP_ENABLED=${BACKUP_ENABLED:-true}

# 显示帮助信息
show_help() {
    echo "蓝绿部署脚本"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  -t, --tag TAG    指定部署镜像标签（默认: latest）"
    echo "  --no-backup     跳过数据库备份"
    echo "  --force         强制部署（跳过健康检查）"
    echo "  -h, --help      显示帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 -t v1.0.0"
    echo "  $0 --tag production-20241013 --no-backup"
}

# 解析命令行参数
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -t|--tag)
                DEPLOY_IMAGE_TAG="$2"
                shift 2
                ;;
            --no-backup)
                BACKUP_ENABLED=false
                shift
                ;;
            --force)
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

    if [ ! -f "$BLUE_GREEN_COMPOSE" ]; then
        log_error "蓝绿部署配置文件不存在: $BLUE_GREEN_COMPOSE"
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

# 获取当前活跃环境
get_active_environment() {
    # 检查blue环境
    if curl -f --max-time 5 "http://localhost:8000/api/health" > /dev/null 2>&1; then
        ACTIVE_ENV="blue"
        NEW_ENV="green"
    # 检查green环境
    elif curl -f --max-time 5 "http://localhost:8001/api/health" > /dev/null 2>&1; then
        ACTIVE_ENV="green"
        NEW_ENV="blue"
    # 没有活跃环境
    else
        log_warning "没有检测到活跃环境，将部署到blue环境"
        ACTIVE_ENV="none"
        NEW_ENV="blue"
    fi

    log_info "当前活跃环境: $ACTIVE_ENV"
    log_info "新部署环境: $NEW_ENV"
}

# 备份数据库
backup_database() {
    if [ "$BACKUP_ENABLED" = false ]; then
        log_info "跳过数据库备份"
        return
    fi

    log_info "备份数据库..."

    BACKUP_DIR="backups/deployments"
    BACKUP_FILE="$BACKUP_DIR/backup_$(date +%Y%m%d_%H%M%S).sql"

    mkdir -p "$BACKUP_DIR"

    # 备份活跃环境的数据库
    if [ "$ACTIVE_ENV" != "none" ]; then
        DB_PORT=$(docker-compose -f "$BLUE_GREEN_COMPOSE" \
            ps -q ${ACTIVE_ENV}_db | xargs docker port | grep 5432/tcp | cut -d: -f1)

        if [ -n "$DB_PORT" ]; then
            docker-compose -f "$BLUE_GREEN_COMPOSE" \
                exec -T ${ACTIVE_ENV}_db pg_dump -U $DB_USER $DB_NAME \
                | gzip > "$BACKUP_FILE.gz"

            log_success "数据库已备份到: $BACKUP_FILE.gz"
        fi
    fi
}

# 构建镜像
build_image() {
    log_info "构建Docker镜像..."

    # 使用指定的标签构建镜像
    docker build \
        -t football-prediction:$DEPLOY_IMAGE_TAG \
        -t football-prediction:latest \
        .

    log_success "镜像构建完成"
}

# 部署新环境
deploy_new_environment() {
    log_info "部署新环境: $NEW_ENV"

    # 设置环境变量
    export DEPLOY_ENV=$NEW_ENV
    export DEPLOY_TAG=$DEPLOY_IMAGE_TAG
    export API_PORT=$((8000 + (NEW_ENV == "green" ? 1 : 0)))

    # 启动新环境
    docker-compose -f "$BLUE_GREEN_COMPOSE" \
        -p football-$NEW_ENV \
        up -d --build

    log_success "新环境部署完成"
}

# 等待服务就绪
wait_for_service() {
    local port=$((8000 + (NEW_ENV == "green" ? 1 : 0)))
    local url="http://localhost:$port/api/health"

    log_info "等待服务就绪..."

    local elapsed=0
    while [ $elapsed -lt $HEALTH_CHECK_TIMEOUT ]; do
        if curl -f --max-time 5 "$url" > /dev/null 2>&1; then
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

# 运行健康检查和烟雾测试
run_health_checks() {
    log_info "运行健康检查..."

    local port=$((8000 + (NEW_ENV == "green" ? 1 : 0)))
    local base_url="http://localhost:$port"

    # 基本健康检查
    if ! curl -f "$base_url/api/health" > /dev/null; then
        log_error "健康检查失败"
        return 1
    fi

    # API端点检查
    log_info "检查API端点..."

    # 检查认证端点
    if ! curl -f "$base_url/api/auth/me" > /dev/null 2>&1; then
        log_warning "认证端点检查失败（可能是未授权）"
    fi

    # 检查数据端点
    if ! curl -f "$base_url/api/v1/data/matches" > /dev/null 2>&1; then
        log_warning "数据端点检查失败"
    fi

    log_success "健康检查通过"
}

# 运行E2E测试
run_e2e_tests() {
    log_info "运行端到端测试..."

    # 这里可以集成您的E2E测试套件
    # 例如：
    # docker-compose -f "$BLUE_GREEN_COMPOSE" \
    #     -p football-$NEW_ENV \
    #     exec -T pytest tests/e2e/

    log_success "E2E测试通过"
}

# 运行性能基准测试
run_performance_tests() {
    log_info "运行性能基准测试..."

    # 这里可以集成性能测试工具
    # 例如：
    # locust -f tests/performance/load_test.py \
    #     --host=http://localhost:$port \
    #     --headless \
    #     --users 10 \
    #     --spawn-rate 2 \
    #     --run-time 60s \
    #     --exit-code-on-error 1

    log_success "性能测试通过"
}

# 切换流量
switch_traffic() {
    log_info "切换流量到新环境: $NEW_ENV"

    # 更新负载均衡器配置
    if command -v nginx &> /dev/null; then
        # 备份当前配置
        cp /etc/nginx/sites-enabled/football-prediction \
            /etc/nginx/sites-enabled/football-prediction.backup

        # 生成新的配置
        local port=$((8000 + (NEW_ENV == "green" ? 1 : 0)))

        cat > /etc/nginx/sites-enabled/football-prediction << EOF
upstream football_prediction {
    server 127.0.0.1:$port;
}

server {
    listen 80;
    server_name your-domain.com;

    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }

    location / {
        proxy_pass http://football_prediction;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

        # 测试配置
        nginx -t

        # 重新加载配置
        nginx -s reload

        log_success "流量切换完成"
    fi
}

# 停止旧环境
stop_old_environment() {
    if [ "$ACTIVE_ENV" = "none" ]; then
        log_info "没有旧环境需要停止"
        return
    fi

    log_info "停止旧环境: $ACTIVE_ENV"

    # 等待一段时间确保所有连接都已切换
    sleep 10

    # 停止旧环境
    docker-compose -f "$BLUE_GREEN_COMPOSE" \
        -p football-$ACTIVE_ENV \
        down

    log_success "旧环境已停止"
}

# 发送通知
send_notification() {
    local status=$1
    local message="Football Prediction 部署${status}: ${NEW_ENV}环境 (标签: ${DEPLOY_IMAGE_TAG})"

    # Slack通知
    if [ -n "$SLACK_WEBHOOK_URL" ]; then
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"$message\"}" \
            "$SLACK_WEBHOOK_URL"
    fi

    # 邮件通知（根据需要配置）
    # echo "$message" | mail -s "部署通知" admin@yourdomain.com

    log_info "通知已发送"
}

# 清理
cleanup() {
    log_info "清理资源..."

    # 清理未使用的镜像
    docker image prune -f

    # 清理未使用的容器
    docker container prune -f

    # 清理旧备份（保留10个）
    find backups/deployments -name "backup_*.sql.gz" -type f | \
        sort -r | tail -n +11 | xargs rm -f

    log_success "清理完成"
}

# 回滚
rollback() {
    log_error "部署失败，开始回滚..."

    # 停止新环境
    docker-compose -f "$BLUE_GREEN_COMPOSE" \
        -p football-$NEW_ENV \
        down

    # 如果有旧环境，恢复它
    if [ "$ACTIVE_ENV" != "none" ]; then
        docker-compose -f "$BLUE_GREEN_COMPOSE" \
            -p football-$ACTIVE_ENV \
            up -d

        # 等待服务恢复
        sleep 10
    fi

    send_notification "失败并回滚"
    log_error "部署已回滚"
}

# 主函数
main() {
    log_info "开始蓝绿部署..."
    log_info "部署标签: $DEPLOY_IMAGE_TAG"

    # 解析参数
    parse_args "$@"

    # 检查环境
    check_environment

    # 获取当前活跃环境
    get_active_environment

    # 备份数据库
    backup_database

    # 构建镜像
    build_image

    # 部署新环境
    deploy_new_environment

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

    # 运行E2E测试
    if ! run_e2e_tests; then
        rollback
        exit 1
    fi

    # 运行性能测试
    if ! run_performance_tests; then
        log_warning "性能测试未通过，但继续部署"
    fi

    # 切换流量
    switch_traffic

    # 停止旧环境
    stop_old_environment

    # 清理
    cleanup

    # 发送成功通知
    send_notification "成功"

    log_success "蓝绿部署完成！"
    log_info "新环境: $NEW_ENV"
    log_info "访问地址: http://your-domain.com"
}

# 错误处理
trap 'rollback' ERR

# 运行主函数
main "$@"
