#!/bin/bash

# Loki日志栈启动脚本
# Football Prediction Project

set -euo pipefail

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# 检查Docker和Docker Compose
check_requirements() {
    log_step "检查系统要求..."

    # 检查Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker未安装，请先安装Docker"
        exit 1
    fi

    # 检查Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "Docker Compose未安装，请先安装Docker Compose"
        exit 1
    fi

    # 检查Docker服务状态
    if ! docker info &> /dev/null; then
        log_error "Docker服务未运行，请启动Docker服务"
        exit 1
    fi

    log_info "系统要求检查通过"
}

# 创建必要的目录
create_directories() {
    log_step "创建必要的目录..."

    local dirs=(
        "monitoring/data/loki"
        "monitoring/data/grafana"
        "monitoring/data/promtail"
        "monitoring/data/minio"
        "logs/loki"
        "logs/grafana"
    )

    for dir in "${dirs[@]}"; do
        mkdir -p "$dir"
        log_info "创建目录: $dir"
    done
}

# 生成配置文件
generate_configs() {
    log_step "生成配置文件..."

    # 生成Grafana数据源配置
    cat > monitoring/grafana/provisioning/datasources/loki.yaml <<EOF
apiVersion: 1

datasources:
  - name: Loki
    type: loki
    access: proxy
    url: http://loki:3100
    editable: true
    jsonData:
      maxLines: 1000
      derivedFields:
        - datasourceUid: jaeger
          matcherRegex: "trace_id=(\\w+)"
          name: TraceID
          url: "http://jaeger:16686/trace/\\\$1"
EOF

    # 生成环境变量文件
    cat > .env.loki <<EOF
# Loki Stack Environment Variables

# Grafana配置
GRAFANA_PASSWORD=admin123456
SMTP_HOST=smtp.gmail.com:587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM=alerts@footballprediction.com

# Loki配置
LOKI_RETENTION=7d
LOKI_MEMORY_LIMIT=1G

# MinIO配置
MINIO_ROOT_USER=loki
MINIO_ROOT_PASSWORD=loki123456789

# 服务名称
SERVICE_NAME=football-prediction
ENVIRONMENT=production
EOF

    log_info "配置文件生成完成"
}

# 启动服务
start_services() {
    log_step "启动Loki日志栈..."

    # 加载环境变量
    if [[ -f .env.loki ]]; then
        export $(cat .env.loki | grep -v '^#' | xargs)
    fi

    # 使用docker-compose启动服务
    if command -v docker-compose &> /dev/null; then
        COMPOSE_CMD="docker-compose"
    else
        COMPOSE_CMD="docker compose"
    fi

    # 启动服务
    $COMPOSE_CMD -f docker-compose.loki.yml up -d

    log_info "等待服务启动..."
    sleep 30
}

# 检查服务状态
check_services() {
    log_step "检查服务状态..."

    local services=(
        "loki:3100"
        "grafana:3000"
        "minio:9000"
    )

    for service in "${services[@]}"; do
        local name=$(echo "$service" | cut -d: -f1)
        local port=$(echo "$service" | cut -d: -f2)

        if curl -s "http://localhost:$port" > /dev/null; then
            log_info "✓ $name 服务运行正常 (端口: $port)"
        else
            log_error "✗ $name 服务启动失败 (端口: $port)"
        fi
    done
}

# 显示访问信息
show_access_info() {
    log_step "显示访问信息..."

    echo ""
    echo "==========================================="
    echo "Loki日志栈已成功启动！"
    echo "==========================================="
    echo ""
    echo "访问地址："
    echo "  • Grafana:     http://localhost:3000"
    echo "    - 用户名: admin"
    echo "    - 密码: ${GRAFANA_PASSWORD:-admin123456}"
    echo ""
    echo "  • Loki:        http://localhost:3100"
    echo "  • MinIO:       http://localhost:9001"
    echo "    - 用户名: loki"
    echo "    - 密码: loki123456789"
    echo ""
    echo "管理命令："
    echo "  • 查看日志: docker-compose -f docker-compose.loki.yml logs -f [service]"
    echo "  • 停止服务: docker-compose -f docker-compose.loki.yml down"
    echo "  • 重启服务: docker-compose -f docker-compose.loki.yml restart [service]"
    echo ""
    echo "日志查询："
    echo "  1. 登录Grafana"
    echo "  2. 进入 Explore 页面"
    echo "  3. 选择Loki数据源"
    echo "  4. 使用LogQL查询日志"
    echo ""
    echo "示例查询："
    echo '  • 查看所有日志: {}'
    echo '  • 查看错误日志: {level="ERROR"}'
    echo '  • 查看API日志: {job="football-prediction"}'
    echo '  • 查看特定服务: {service="api"}'
    echo ""
}

# 创建测试日志
create_test_logs() {
    log_step "创建测试日志..."

    # 确保日志目录存在
    sudo mkdir -p /var/log/football-prediction

    # 创建测试日志
    echo '{"timestamp": "'$(date -Iseconds)'", "level": "INFO", "logger": "test", "message": "Loki日志系统测试成功！"}' | sudo tee -a /var/log/football-prediction/app.log

    echo '{"timestamp": "'$(date -Iseconds)'", "level": "ERROR", "logger": "test", "message": "这是一个测试错误日志"}' | sudo tee -a /var/log/football-prediction/error.log

    log_info "测试日志已创建"
}

# 主函数
main() {
    echo ""
    echo "==========================================="
    echo "Football Prediction - Loki日志栈启动脚本"
    echo "==========================================="
    echo ""

    # 检查是否为root用户
    if [[ $EUID -eq 0 ]]; then
        log_error "请不要以root用户运行此脚本"
        exit 1
    fi

    # 执行步骤
    check_requirements
    create_directories
    generate_configs
    start_services
    check_services
    create_test_logs
    show_access_info

    log_info "Loki日志栈启动完成！"
}

# 处理命令行参数
case "${1:-start}" in
    start)
        main
        ;;
    stop)
        log_step "停止Loki日志栈..."
        docker-compose -f docker-compose.loki.yml down
        log_info "服务已停止"
        ;;
    restart)
        log_step "重启Loki日志栈..."
        docker-compose -f docker-compose.loki.yml restart
        log_info "服务已重启"
        ;;
    logs)
        docker-compose -f docker-compose.loki.yml logs -f "${2:-}"
        ;;
    status)
        check_services
        ;;
    *)
        echo "用法: $0 {start|stop|restart|logs|status}"
        echo ""
        echo "命令说明："
        echo "  start   - 启动Loki日志栈"
        echo "  stop    - 停止Loki日志栈"
        echo "  restart - 重启Loki日志栈"
        echo "  logs    - 查看服务日志"
        echo "  status  - 检查服务状态"
        exit 1
        ;;
esac
