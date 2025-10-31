#!/bin/bash

# Week 1 基础设施监控部署脚本
# 用于快速部署Prometheus + Grafana + Node Exporter + cAdvisor + AlertManager

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

# 检查Docker和Docker Compose
check_dependencies() {
    log_info "检查依赖项..."

    if ! command -v docker &> /dev/null; then
        log_error "Docker未安装，请先安装Docker"
        exit 1
    fi

    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose未安装，请先安装Docker Compose"
        exit 1
    fi

    log_success "依赖项检查完成"
}

# 创建网络
create_network() {
    log_info "创建Docker网络..."

    if ! docker network ls | grep -q "monitoring"; then
        docker network create monitoring --driver bridge --subnet=172.20.0.0/16
        log_success "监控网络创建完成"
    else
        log_warning "监控网络已存在"
    fi
}

# 部署Prometheus
deploy_prometheus() {
    log_info "部署Prometheus..."

    cd prometheus

    # 检查配置文件
    if [ ! -f "prometheus-complete.yml" ]; then
        log_error "Prometheus配置文件不存在"
        exit 1
    fi

    # 启动Prometheus
    docker-compose -f prometheus-complete.yml up -d

    # 等待Prometheus启动
    log_info "等待Prometheus启动..."
    sleep 10

    # 检查Prometheus健康状态
    if curl -f http://localhost:9090/-/healthy > /dev/null 2>&1; then
        log_success "Prometheus部署成功 - http://localhost:9090"
    else
        log_error "Prometheus部署失败"
        exit 1
    fi

    cd ..
}

# 部署Grafana
deploy_grafana() {
    log_info "部署Grafana..."

    cd grafana

    # 检查配置文件
    if [ ! -f "grafana-complete.yml" ]; then
        log_error "Grafana配置文件不存在"
        exit 1
    fi

    # 设置环境变量
    export GRAFANA_ADMIN_PASSWORD=${GRAFANA_ADMIN_PASSWORD:-admin123}

    # 启动Grafana
    docker-compose -f grafana-complete.yml up -d

    # 等待Grafana启动
    log_info "等待Grafana启动..."
    sleep 20

    # 检查Grafana健康状态
    if curl -f http://localhost:3000/api/health > /dev/null 2>&1; then
        log_success "Grafana部署成功 - http://localhost:3000 (admin/admin123)"
    else
        log_error "Grafana部署失败"
        exit 1
    fi

    cd ..
}

# 部署Node Exporter
deploy_node_exporter() {
    log_info "部署Node Exporter..."

    cd node-exporter

    # 检查配置文件
    if [ ! -f "node-exporter.yml" ]; then
        log_error "Node Exporter配置文件不存在"
        exit 1
    fi

    # 启动Node Exporter
    docker-compose -f node-exporter.yml up -d

    # 等待Node Exporter启动
    log_info "等待Node Exporter启动..."
    sleep 5

    # 检查Node Exporter健康状态
    if curl -f http://localhost:9100/metrics > /dev/null 2>&1; then
        log_success "Node Exporter部署成功 - http://localhost:9100/metrics"
    else
        log_error "Node Exporter部署失败"
        exit 1
    fi

    cd ..
}

# 部署cAdvisor
deploy_cadvisor() {
    log_info "部署cAdvisor..."

    cd cadvisor

    # 检查配置文件
    if [ ! -f "cadvisor.yml" ]; then
        log_error "cAdvisor配置文件不存在"
        exit 1
    fi

    # 启动cAdvisor
    docker-compose -f cadvisor.yml up -d

    # 等待cAdvisor启动
    log_info "等待cAdvisor启动..."
    sleep 10

    # 检查cAdvisor健康状态
    if curl -f http://localhost:8080/healthz > /dev/null 2>&1; then
        log_success "cAdvisor部署成功 - http://localhost:8080"
    else
        log_error "cAdvisor部署失败"
        exit 1
    fi

    cd ..
}

# 部署AlertManager
deploy_alertmanager() {
    log_info "部署AlertManager..."

    cd alertmanager

    # 检查配置文件
    if [ ! -f "alertmanager-config.yml" ]; then
        log_error "AlertManager配置文件不存在"
        exit 1
    fi

    # 创建AlertManager容器
    docker run -d \
        --name alertmanager \
        --restart unless-stopped \
        -p 9093:9093 \
        -v "$(pwd)/alertmanager-config.yml:/etc/alertmanager/alertmanager.yml" \
        -v "$(pwd)/rules:/etc/alertmanager/rules" \
        --network monitoring \
        prom/alertmanager:v0.25.0 \
        --config.file=/etc/alertmanager/alertmanager.yml \
        --storage.path=/alertmanager

    # 等待AlertManager启动
    log_info "等待AlertManager启动..."
    sleep 10

    # 检查AlertManager健康状态
    if curl -f http://localhost:9093/-/healthy > /dev/null 2>&1; then
        log_success "AlertManager部署成功 - http://localhost:9093"
    else
        log_error "AlertManager部署失败"
        exit 1
    fi

    cd ..
}

# 验证部署
verify_deployment() {
    log_info "验证部署状态..."

    # 检查所有容器状态
    containers=("prometheus" "grafana" "node-exporter" "cadvisor" "alertmanager")

    for container in "${containers[@]}"; do
        if docker ps --format "table {{.Names}}" | grep -q "$container"; then
            status=$(docker inspect --format='{{.State.Health.Status}}' $container 2>/dev/null || echo "unknown")
            if [ "$status" = "healthy" ] || [ "$status" = "unknown" ]; then
                log_success "$container 运行正常"
            else
                log_warning "$container 健康状态: $status"
            fi
        else
            log_error "$container 未运行"
        fi
    done

    # 检查服务可访问性
    services=(
        "Prometheus:http://localhost:9090/-/healthy"
        "Grafana:http://localhost:3000/api/health"
        "Node Exporter:http://localhost:9100/metrics"
        "cAdvisor:http://localhost:8080/healthz"
        "AlertManager:http://localhost:9093/-/healthy"
    )

    for service in "${services[@]}"; do
        name=$(echo $service | cut -d':' -f1)
        url=$(echo $service | cut -d':' -f2-)

        if curl -f "$url" > /dev/null 2>&1; then
            log_success "$name 服务可访问"
        else
            log_error "$name 服务不可访问"
        fi
    done
}

# 显示访问信息
show_access_info() {
    log_success "Week 1 基础设施监控部署完成！"
    echo ""
    echo "访问地址："
    echo "  Prometheus:  http://localhost:9090"
    echo "  Grafana:     http://localhost:3000 (admin/admin123)"
    echo "  Node Exporter: http://localhost:9100/metrics"
    echo "  cAdvisor:    http://localhost:8080"
    echo "  AlertManager: http://localhost:9093"
    echo ""
    echo "Grafana仪表板："
    echo "  系统概览: http://localhost:3000/d/football-prediction-overview"
    echo ""
    echo "后续步骤："
    echo "1. 访问Grafana并配置数据源"
    echo "2. 导入预配置的仪表板"
    echo "3. 配置告警规则"
    echo "4. 设置通知渠道"
    echo ""
    echo "管理命令："
    echo "  查看容器状态: docker ps"
    echo "  查看日志: docker logs [container_name]"
    echo "  停止服务: docker-compose down"
    echo "  重启服务: docker-compose restart"
}

# 主函数
main() {
    log_info "开始部署Week 1基础设施监控..."
    echo ""

    # 检查是否在正确的目录
    if [ ! -d "monitoring" ]; then
        log_error "请在monitoring目录下运行此脚本"
        exit 1
    fi

    # 执行部署步骤
    check_dependencies
    create_network
    deploy_prometheus
    deploy_grafana
    deploy_node_exporter
    deploy_cadvisor
    deploy_alertmanager
    verify_deployment
    show_access_info

    log_success "部署完成！"
}

# 错误处理
trap 'log_error "部署过程中发生错误，请检查日志"; exit 1' ERR

# 执行主函数
main "$@"