#!/bin/bash

# =============================================================================
# Football Prediction 自动化部署脚本
# =============================================================================
# 使用方法:
#   ./deploy.sh [环境] [选项]
#
# 环境:
#   dev     - 开发环境
#   staging - 测试环境
#   prod    - 生产环境
#
# 选项:
#   --skip-tests    - 跳过测试
#   --skip-backup   - 跳过备份
#   --force         - 强制部署
#   --dry-run       - 模拟运行
#
# 示例:
#   ./deploy.sh dev
#   ./deploy.sh prod --skip-tests
# =============================================================================

set -euo pipefail

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# 检查依赖
check_dependencies() {
    log_info "检查系统依赖..."

    # 检查 Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker 未安装"
        exit 1
    fi

    # 检查 Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose 未安装"
        exit 1
    fi

    # 检查 kubectl (如果是 K8s 环境)
    if [ "$ENVIRONMENT" = "prod" ] && [ "$USE_K8S" = "true" ]; then
        if ! command -v kubectl &> /dev/null; then
            log_error "kubectl 未安装"
            exit 1
        fi
    fi

    log_success "依赖检查通过"
}

# 加载环境配置
load_env() {
    local env_file=".env.${ENVIRONMENT}"

    if [ ! -f "$env_file" ]; then
        log_error "环境文件 $env_file 不存在"
        exit 1
    fi

    log_info "加载环境配置: $env_file"
    set -a
    source "$env_file"
    set +a

    # 验证必要的环境变量
    required_vars=("DATABASE_URL" "REDIS_URL" "SECRET_KEY")
    for var in "${required_vars[@]}"; do
        if [ -z "${!var:-}" ]; then
            log_error "环境变量 $var 未设置"
            exit 1
        fi
    done

    log_success "环境配置加载完成"
}

# 备份数据库
backup_database() {
    if [ "$SKIP_BACKUP" = "true" ]; then
        log_warning "跳过数据库备份"
        return
    fi

    log_info "开始备份数据库..."

    local backup_file="backup_${ENVIRONMENT}_$(date +%Y%m%d_%H%M%S).sql"

    # 创建备份目录
    mkdir -p backups

    # 执行备份
    docker-compose exec -T postgres pg_dump -U $POSTGRES_USER $POSTGRES_DB > "backups/$backup_file"

    # 压缩备份文件
    gzip "backups/$backup_file"

    log_success "数据库备份完成: backups/${backup_file}.gz"

    # 清理旧备份（保留最近7天）
    find backups -name "backup_${ENVIRONMENT}_*.sql.gz" -mtime +7 -delete
}

# 运行测试
run_tests() {
    if [ "$SKIP_TESTS" = "true" ]; then
        log_warning "跳过测试"
        return
    fi

    log_info "运行测试套件..."

    # 单元测试
    log_info "运行单元测试..."
    docker-compose exec app pytest tests/unit/ -v --cov=src

    # 集成测试
    log_info "运行集成测试..."
    docker-compose exec app pytest tests/integration/ -v

    log_success "所有测试通过"
}

# 构建镜像
build_images() {
    log_info "构建 Docker 镜像..."

    # 构建应用镜像
    docker build -t football-prediction:${VERSION} .

    # 如果是生产环境，打上 latest 标签
    if [ "$ENVIRONMENT" = "prod" ]; then
        docker tag football-prediction:${VERSION} football-prediction:latest
    fi

    log_success "镜像构建完成"
}

# 部署到 Docker Compose
deploy_docker_compose() {
    log_info "部署到 Docker Compose..."

    # 停止现有服务
    log_info "停止现有服务..."
    docker-compose down

    # 启动新服务
    log_info "启动新服务..."
    docker-compose -f docker-compose.yml -f docker-compose.${ENVIRONMENT}.yml up -d

    # 等待服务就绪
    log_info "等待服务就绪..."
    sleep 30

    # 运行数据库迁移
    log_info "运行数据库迁移..."
    docker-compose exec app alembic upgrade head

    log_success "Docker Compose 部署完成"
}

# 部署到 Kubernetes
deploy_kubernetes() {
    log_info "部署到 Kubernetes..."

    # 设置上下文
    kubectl config use-context $KUBE_CONTEXT

    # 应用配置
    kubectl apply -f k8s/namespaces/
    kubectl apply -f k8s/configmaps/
    kubectl apply -f k8s/secrets/

    # 部署应用
    kubectl apply -f k8s/deployments/
    kubectl apply -f k8s/services/
    kubectl apply -f k8s/ingress/

    # 等待部署完成
    kubectl rollout status deployment/football-prediction -n $NAMESPACE --timeout=300s

    log_success "Kubernetes 部署完成"
}

# 健康检查
health_check() {
    log_info "执行健康检查..."

    local max_attempts=30
    local attempt=1
    local health_url="http://localhost:${PORT:-8000}/health"

    while [ $attempt -le $max_attempts ]; do
        if curl -f -s "$health_url" > /dev/null; then
            log_success "健康检查通过"
            return
        fi

        log_info "等待服务就绪... ($attempt/$max_attempts)"
        sleep 5
        ((attempt++))
    done

    log_error "健康检查失败"
    exit 1
}

# 发送通知
send_notification() {
    if [ -z "${SLACK_WEBHOOK_URL:-}" ]; then
        return
    fi

    local color="good"
    local message="✅ 部署成功: $ENVIRONMENT 环境 (版本: $VERSION)"

    if [ "$1" = "failure" ]; then
        color="danger"
        message="❌ 部署失败: $ENVIRONMENT 环境"
    fi

    curl -X POST -H 'Content-type: application/json' \
        --data "{\"text\":\"$message\"}" \
        "$SLACK_WEBHOOK_URL"
}

# 清理
cleanup() {
    log_info "清理资源..."

    # 清理未使用的 Docker 镜像
    docker image prune -f

    # 清理未使用的容器
    docker container prune -f

    log_success "清理完成"
}

# 显示帮助信息
show_help() {
    cat << EOF
Football Prediction 自动化部署脚本

使用方法:
  $0 [环境] [选项]

环境:
  dev     - 开发环境
  staging - 测试环境
  prod    - 生产环境

选项:
  --skip-tests    - 跳过测试
  --skip-backup   - 跳过备份
  --force         - 强制部署
  --dry-run       - 模拟运行
  --help          - 显示此帮助信息

示例:
  $0 dev
  $0 staging --skip-tests
  $0 prod --skip-backup
  $0 dev --dry-run

EOF
}

# 主函数
main() {
    # 解析参数
    ENVIRONMENT=""
    SKIP_TESTS="false"
    SKIP_BACKUP="false"
    FORCE="false"
    DRY_RUN="false"
    VERSION=${VERSION:-$(date +%Y%m%d_%H%M%S)}

    while [[ $# -gt 0 ]]; do
        case $1 in
            dev|staging|prod)
                ENVIRONMENT="$1"
                shift
                ;;
            --skip-tests)
                SKIP_TESTS="true"
                shift
                ;;
            --skip-backup)
                SKIP_BACKUP="true"
                shift
                ;;
            --force)
                FORCE="true"
                shift
                ;;
            --dry-run)
                DRY_RUN="true"
                shift
                ;;
            --help)
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

    # 验证环境参数
    if [ -z "$ENVIRONMENT" ]; then
        log_error "请指定部署环境 (dev/staging/prod)"
        show_help
        exit 1
    fi

    # 显示部署信息
    log_info "========================================"
    log_info "Football Prediction 部署脚本"
    log_info "========================================"
    log_info "环境: $ENVIRONMENT"
    log_info "版本: $VERSION"
    log_info "跳过测试: $SKIP_TESTS"
    log_info "跳过备份: $SKIP_BACKUP"
    log_info "强制部署: $FORCE"
    log_info "模拟运行: $DRY_RUN"
    log_info "========================================"

    # 模拟运行模式
    if [ "$DRY_RUN" = "true" ]; then
        log_info "模拟运行模式 - 不会执行实际部署"
        exit 0
    fi

    # 执行部署流程
    trap 'send_notification failure' ERR

    check_dependencies
    load_env
    backup_database
    run_tests
    build_images

    # 根据环境选择部署方式
    if [ "$ENVIRONMENT" = "prod" ] && [ "$USE_K8S" = "true" ]; then
        deploy_kubernetes
    else
        deploy_docker_compose
    fi

    health_check
    cleanup

    # 发送成功通知
    send_notification success

    log_success "🎉 部署完成！"
    log_info "访问地址: http://localhost:${PORT:-8000}"
    log_info "API 文档: http://localhost:${PORT:-8000}/docs"
}

# 执行主函数
main "$@"
