#!/bin/bash

# 生产环境部署脚本
# Production Deployment Script

set -e

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

# 检查环境变量
check_env_vars() {
    log_info "检查环境变量..."

    required_vars=(
        "PROD_DB_PASSWORD"
        "PROD_REDIS_PASSWORD"
        "PROD_SECRET_KEY"
        "PROD_GRAFANA_PASSWORD"
        "PROD_API_KEY"
    )

    missing_vars=()
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var}" ]]; then
            missing_vars+=("$var")
        fi
    done

    if [[ ${#missing_vars[@]} -gt 0 ]]; then
        log_error "缺少必需的环境变量: ${missing_vars[*]}"
        exit 1
    fi

    log_success "环境变量检查通过"
}

# 备份当前部署
backup_current() {
    log_info "备份当前部署..."

    backup_dir="backups/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$backup_dir"

    # 备份数据库
    if docker-compose exec db pg_dump -U prod_user football_prediction > "$backup_dir/database.sql"; then
        log_success "数据库备份完成"
    else
        log_warning "数据库备份失败"
    fi

    # 备份配置文件
    cp -r docker/environments "$backup_dir/"
    cp docker-compose*.yml "$backup_dir/" 2>/dev/null || true

    log_success "备份完成: $backup_dir"
}

# 健康检查
health_check() {
    log_info "执行健康检查..."

    # 检查服务状态
    services=("app" "db" "redis" "nginx" "prometheus" "grafana")

    for service in "${services[@]}"; do
        if docker-compose ps "$service" | grep -q "Up"; then
            log_success "$service 服务运行正常"
        else
            log_error "$service 服务异常"
            return 1
        fi
    done

    # 检查API健康端点
    for i in {1..30}; do
        if curl -f http://localhost/health >/dev/null 2>&1; then
            log_success "API健康检查通过"
            break
        else
            if [[ $i -eq 30 ]]; then
                log_error "API健康检查失败"
                return 1
            fi
            log_info "等待API启动... ($i/30)"
            sleep 2
        fi
    done

    log_success "健康检查完成"
}

# 部署函数
deploy() {
    log_info "开始生产环境部署..."

    # 检查环境变量
    check_env_vars

    # 备份当前部署
    backup_current

    # 拉取最新代码
    log_info "拉取最新代码..."
    git pull origin main

    # 构建镜像
    log_info "构建Docker镜像..."
    docker-compose -f docker-compose.yml -f docker-compose.prod.yml build --no-cache

    # 停止旧服务
    log_info "停止旧服务..."
    docker-compose -f docker-compose.yml -f docker-compose.prod.yml down

    # 启动新服务
    log_info "启动新服务..."
    docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

    # 等待服务启动
    log_info "等待服务启动..."
    sleep 30

    # 健康检查
    health_check

    # 清理旧镜像
    log_info "清理旧镜像..."
    docker image prune -f

    log_success "部署完成！"
}

# 回滚函数
rollback() {
    log_info "执行回滚操作..."

    if [[ -z "$1" ]]; then
        log_error "请指定回滚版本: ./scripts/deploy-production.sh rollback <backup_dir>"
        exit 1
    fi

    backup_dir="$1"

    if [[ ! -d "$backup_dir" ]]; then
        log_error "备份目录不存在: $backup_dir"
        exit 1
    fi

    # 停止当前服务
    docker-compose -f docker-compose.yml -f docker-compose.prod.yml down

    # 恢复配置文件
    cp "$backup_dir/docker-compose.prod.yml" . 2>/dev/null || true
    cp -r "$backup_dir/environments/" docker/

    # 恢复数据库
    if [[ -f "$backup_dir/database.sql" ]]; then
        log_info "恢复数据库..."
        docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d db redis
        sleep 20
        docker-compose exec db psql -U prod_user -d football_prediction < "$backup_dir/database.sql"
    fi

    # 启动服务
    docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

    # 健康检查
    health_check

    log_success "回滚完成！"
}

# 主函数
main() {
    case "${1:-deploy}" in
        "deploy")
            deploy
            ;;
        "rollback")
            rollback "$2"
            ;;
        "health")
            health_check
            ;;
        "backup")
            backup_current
            ;;
        *)
            echo "用法: $0 {deploy|rollback <backup_dir>|health|backup}"
            echo "  deploy  - 部署到生产环境"
            echo "  rollback - 回滚到指定备份"
            echo "  health  - 执行健康检查"
            echo "  backup  - 创建备份"
            exit 1
            ;;
    esac
}

# 脚本入口
main "$@"