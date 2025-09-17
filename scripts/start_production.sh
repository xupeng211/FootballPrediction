#!/bin/bash

# 足球预测平台生产环境一键启动脚本
# 启动所有依赖服务并进行健康检查

set -e  # 遇到错误立即退出

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

# 检查Docker和Docker Compose
check_prerequisites() {
    log_info "检查前置条件..."

    if ! command -v docker &> /dev/null; then
        log_error "Docker 未安装或不在 PATH 中"
        exit 1
    fi

    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "Docker Compose 未安装或不在 PATH 中"
        exit 1
    fi

    log_success "前置条件检查通过"
}

# 创建必要的数据目录
create_directories() {
    log_info "创建数据目录..."

    directories=(
        "data/postgres"
        "data/redis"
        "data/minio"
        "data/pgadmin"
        "logs/mlflow"
        "logs/grafana"
        "logs/prometheus"
        ".feast"
    )

    for dir in "${directories[@]}"; do
        if [ ! -d "$dir" ]; then
            mkdir -p "$dir"
            log_info "创建目录: $dir"
        fi
    done

    log_success "数据目录创建完成"
}

# 设置环境变量
setup_environment() {
    log_info "设置环境变量..."

    if [ ! -f ".env" ]; then
        if [ -f "env.template" ]; then
            cp env.template .env
            log_info "从模板创建 .env 文件"
        else
            log_warning ".env 文件不存在，将使用默认配置"
        fi
    fi

    # 导出必要的环境变量
    export POSTGRES_ROOT_PASSWORD=${POSTGRES_ROOT_PASSWORD:-change_me}
    export DB_PASSWORD=${DB_PASSWORD:-change_me}
    export REDIS_PASSWORD=${REDIS_PASSWORD:-change_me}
    export MINIO_ROOT_USER=${MINIO_ROOT_USER:-minioadmin}
    export MINIO_ROOT_PASSWORD=${MINIO_ROOT_PASSWORD:-change_me}
    export MLFLOW_PORT=${MLFLOW_PORT:-5000}
    export MINIO_PORT=${MINIO_PORT:-9000}

    log_success "环境变量设置完成"
}

# 启动核心基础服务
start_core_services() {
    log_info "启动核心基础服务..."

    # 启动数据库和缓存服务
    docker-compose up -d db redis

    # 等待数据库和Redis就绪
    log_info "等待 PostgreSQL 就绪..."
    timeout 120 bash -c 'until docker-compose exec -T db pg_isready -U postgres; do sleep 2; done'

    log_info "等待 Redis 就绪..."
    timeout 60 bash -c 'until docker-compose exec -T redis redis-cli ping | grep PONG; do sleep 2; done'

    log_success "核心基础服务启动完成"
}

# 启动存储和消息队列服务
start_storage_services() {
    log_info "启动存储和消息队列服务..."

    # 启动MinIO、Kafka、Zookeeper
    docker-compose up -d minio zookeeper kafka

    # 等待MinIO就绪
    log_info "等待 MinIO 就绪..."
    timeout 90 bash -c 'until curl -f http://localhost:${MINIO_PORT:-9000}/minio/health/live &>/dev/null; do sleep 3; done'

    # 等待Kafka就绪
    log_info "等待 Kafka 就绪..."
    timeout 120 bash -c 'until docker-compose exec -T kafka kafka-topics --bootstrap-server localhost:9092 --list &>/dev/null; do sleep 3; done'

    log_success "存储和消息队列服务启动完成"
}

# 启动ML和特征服务
start_ml_services() {
    log_info "启动机器学习和特征服务..."

    # 启动MLflow
    docker-compose -f docker-compose.override.yml up -d mlflow

    # 等待MLflow就绪
    log_info "等待 MLflow 就绪..."
    timeout 180 bash -c 'until curl -f http://localhost:${MLFLOW_PORT:-5000}/health &>/dev/null; do sleep 5; done'

    log_success "机器学习和特征服务启动完成"
}

# 启动监控服务
start_monitoring_services() {
    log_info "启动监控服务..."

    # 启动Prometheus和Grafana
    docker-compose up -d prometheus grafana postgres-exporter

    # 等待Prometheus就绪
    log_info "等待 Prometheus 就绪..."
    timeout 90 bash -c 'until curl -f http://localhost:9090/-/ready &>/dev/null; do sleep 3; done'

    # 等待Grafana就绪
    log_info "等待 Grafana 就绪..."
    timeout 120 bash -c 'until curl -f http://localhost:3000/api/health &>/dev/null; do sleep 3; done'

    log_success "监控服务启动完成"
}

# 启动应用服务
start_application_services() {
    log_info "启动应用服务..."

    # 启动主应用、Celery worker和调度器
    docker-compose up -d app celery-worker celery-beat celery-flower

    # 等待应用就绪
    log_info "等待主应用就绪..."
    timeout 120 bash -c 'until curl -f http://localhost:8000/health &>/dev/null; do sleep 3; done'

    # 等待Flower就绪
    log_info "等待 Flower 监控就绪..."
    timeout 60 bash -c 'until curl -f http://localhost:5555/api/workers &>/dev/null; do sleep 3; done'

    log_success "应用服务启动完成"
}

# 初始化Feast特征存储
initialize_feast() {
    log_info "初始化 Feast 特征存储..."

    # 检查虚拟环境
    if [ -d "venv" ]; then
        source venv/bin/activate
    fi

    # 设置环境变量
    export DB_HOST=localhost
    export REDIS_URL=redis://localhost:6379/0

    # 运行初始化脚本
    python scripts/feast_init.py

    if [ $? -eq 0 ]; then
        log_success "Feast 特征存储初始化完成"
    else
        log_warning "Feast 特征存储初始化失败，但不影响其他服务"
    fi
}

# 服务健康检查
perform_health_checks() {
    log_info "执行服务健康检查..."

    # 检查各服务状态
    services=(
        "db:5432"
        "redis:6379"
        "minio:9000"
        "prometheus:9090"
        "grafana:3000"
        "app:8000"
        "mlflow:5000"
        "flower:5555"
    )

    failed_services=()

    for service in "${services[@]}"; do
        service_name=$(echo $service | cut -d':' -f1)
        port=$(echo $service | cut -d':' -f2)

        if curl -f "http://localhost:$port/health" &>/dev/null || \
           curl -f "http://localhost:$port/" &>/dev/null || \
           nc -z localhost $port &>/dev/null; then
            log_success "✅ $service_name (端口 $port) - 健康"
        else
            log_error "❌ $service_name (端口 $port) - 不健康"
            failed_services+=("$service_name")
        fi
    done

    if [ ${#failed_services[@]} -eq 0 ]; then
        log_success "🎉 所有服务健康检查通过！"
        return 0
    else
        log_error "以下服务健康检查失败: ${failed_services[*]}"
        return 1
    fi
}

# 显示访问信息
show_access_info() {
    log_info "服务访问信息:"
    echo "=========================================="
    echo "🌐 主要服务访问地址:"
    echo ""
    echo "  📊 足球预测API:      http://localhost:8000"
    echo "  📚 API文档:          http://localhost:8000/docs"
    echo "  🔬 MLflow UI:        http://localhost:5000"
    echo "  📈 Grafana监控:      http://localhost:3000 (admin/${GRAFANA_ADMIN_PASSWORD:-change_me})"
    echo "  📊 Prometheus:       http://localhost:9090"
    echo "  🌸 Celery Flower:    http://localhost:5555"
    echo "  💾 MinIO Console:    http://localhost:9001 (${MINIO_ROOT_USER:-minioadmin}/${MINIO_ROOT_PASSWORD:-change_me})"
    echo "  🗄️ pgAdmin:         http://localhost:8080"
    echo ""
    echo "🔧 管理工具:"
    echo "  - 查看日志: docker-compose logs -f [服务名]"
    echo "  - 停止服务: docker-compose down"
    echo "  - 重启服务: docker-compose restart [服务名]"
    echo ""
    echo "🎯 健康检查: curl http://localhost:8000/health"
    echo "=========================================="
}

# 主函数
main() {
    echo "🚀 足球预测平台生产环境启动脚本"
    echo "=========================================="

    # 执行启动步骤
    check_prerequisites
    create_directories
    setup_environment

    log_info "开始启动所有服务..."
    start_core_services
    start_storage_services
    start_ml_services
    start_monitoring_services
    start_application_services

    # 初始化特征存储（可选）
    if [ "$1" = "--init-feast" ] || [ "$1" = "-f" ]; then
        initialize_feast
    fi

    # 健康检查
    log_info "等待所有服务完全启动..."
    sleep 10

    if perform_health_checks; then
        show_access_info
        log_success "🎉 生产环境启动成功！系统已就绪！"
        exit 0
    else
        log_error "❌ 部分服务启动失败，请检查日志：docker-compose logs"
        exit 1
    fi
}

# 脚本入口
main "$@"
