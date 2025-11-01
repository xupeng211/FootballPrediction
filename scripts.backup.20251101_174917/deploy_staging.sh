#!/bin/bash

# =================================================================
# 本地试运营环境部署脚本
# Local Staging Environment Deployment Script
# =================================================================

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

# 配置变量
PROJECT_NAME="football-prediction-staging"
COMPOSE_FILE="docker/docker-compose.staging.yml"
ENV_FILE="environments/.env.local"

# 函数：打印带颜色的消息
print_message() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# 函数：检查命令是否存在
check_command() {
    if ! command -v $1 &> /dev/null; then
        print_message $RED "❌ 错误: $1 命令未找到，请先安装"
        exit 1
    fi
}

# 函数：检查端口是否可用
check_port() {
    local port=$1
    local service=$2

    if netstat -tlnp | grep -q ":${port} "; then
        print_message $YELLOW "⚠️  端口 ${port} 已被占用 (${service})"
        read -p "是否继续? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_message $RED "部署已取消"
            exit 1
        fi
    fi
}

# 函数：环境检查
environment_check() {
    print_message $BLUE "🔍 环境检查..."

    # 检查必要命令
    check_command "docker"
    check_command "docker-compose"

    # 检查必要文件
    if [ ! -f "$ENV_FILE" ]; then
        print_message $RED "❌ 错误: $ENV_FILE 文件不存在"
        exit 1
    fi

    if [ ! -f "$COMPOSE_FILE" ]; then
        print_message $RED "❌ 错误: $COMPOSE_FILE 文件不存在"
        exit 1
    fi

    print_message $GREEN "✅ 环境检查通过"
}

# 函数：端口检查
port_check() {
    print_message $BLUE "🔍 端口检查..."
    check_port 80 "HTTP服务"
    check_port 8000 "应用服务"
    check_port 5432 "PostgreSQL数据库"
    check_port 6379 "Redis缓存"
    check_port 3000 "Grafana监控"
    check_port 9090 "Prometheus监控"
    print_message $GREEN "✅ 端口检查完成"
}

# 函数：创建必要目录
create_directories() {
    print_message $BLUE "📁 创建必要目录..."

    mkdir -p data/{postgres,redis,prometheus,grafana}
    mkdir -p logs/{nginx,app,db,redis}

    # 设置权限
    chmod 755 data logs
    chmod 755 data/* logs/*

    print_message $GREEN "✅ 目录创建完成"
}

# 函数：构建Docker镜像
build_images() {
    print_message $BLUE "🔨 构建Docker镜像..."

    docker-compose -f $COMPOSE_FILE build

    print_message $GREEN "✅ Docker镜像构建完成"
}

# 函数：启动服务
start_services() {
    print_message $BLUE "🚀 启动试运营服务..."

    # 首先启动数据库和Redis
    print_message $CYAN "  - 启动数据存储服务..."
    docker-compose -f $COMPOSE_FILE up -d db redis

    # 等待数据库启动
    print_message $CYAN "  - 等待数据库启动..."
    sleep 10

    # 启动应用
    print_message $CYAN "  - 启动应用服务..."
    docker-compose -f $COMPOSE_FILE up -d app

    # 等待应用启动
    print_message $CYAN "  - 等待应用启动..."
    sleep 15

    # 启动其他服务
    print_message $CYAN "  - 启动监控和代理服务..."
    docker-compose -f $COMPOSE_FILE up -d nginx prometheus grafana loki promtail node-exporter redis-exporter

    print_message $GREEN "✅ 所有服务启动完成"
}

# 函数：健康检查
health_check() {
    local service_name=$1
    local url=$2
    local max_attempts=$3
    local attempt=1

    print_message $CYAN "🔍 检查 $service_name 健康状态..."

    while [ $attempt -le $max_attempts ]; do
        if curl -sf $url > /dev/null 2>&1; then
            print_message $GREEN "  ✅ $service_name 健康"
            return 0
        fi

        print_message $YELLOW "  ⏳ 等待 $service_name 启动... ($attempt/$max_attempts)"
        sleep 5
        ((attempt++))
    done

    print_message $RED "  ❌ $service_name 健康检查失败"
    return 1
}

# 函数：全面健康检查
comprehensive_health_check() {
    print_message $BLUE "🏥 执行全面健康检查..."

    # 检查数据库
    docker-compose -f $COMPOSE_FILE exec -T db pg_isready -U postgres -d football_prediction_staging
    print_message $GREEN "  ✅ PostgreSQL 健康"

    # 检查Redis
    docker-compose -f $COMPOSE_FILE exec -T redis redis-cli ping
    print_message $GREEN "  ✅ Redis 健康"

    # 检查主应用
    health_check "主应用" "http://localhost/health" 10

    # 检查API端点
    health_check "API端点" "http://localhost/api/v1/health" 5

    print_message $GREEN "✅ 所有服务健康检查通过"
}

# 函数：显示部署状态
show_status() {
    print_message $BLUE "📊 当前部署状态:"
    echo "----------------------------------------"
    docker-compose -f $COMPOSE_FILE ps
    echo "----------------------------------------"
}

# 函数：显示访问信息
show_access_info() {
    print_message $BLUE "🌐 试运营环境访问信息:"
    echo "----------------------------------------"
    echo "🎯 主应用: http://localhost"
    echo "📊 API文档: http://localhost/docs"
    echo "💾 健康检查: http://localhost/health"
    echo "🔍 API端点: http://localhost/api/v1"
    echo ""
    echo "📈 监控面板:"
    echo "  📊 Grafana: http://localhost:3000"
    echo "  🔍 Prometheus: http://localhost:9090"
    echo "  📝 Loki: http://localhost:3100"
    echo ""
    echo "🔐 默认管理员账户:"
    echo "  👤 邮箱: admin@localhost.local"
    echo "  🔑 密码: StagingAdmin123!"
    echo ""
    echo "📊 Grafana登录:"
    echo "  👤 用户名: admin"
    echo "  🔑 密码: staging_grafana_admin_2024"
    echo "----------------------------------------"
}

# 函数：显示日志
show_logs() {
    print_message $BLUE "📝 显示服务日志..."
    docker-compose -f $COMPOSE_FILE logs -f
}

# 函数：停止服务
stop_services() {
    print_message $BLUE "🛑 停止试运营服务..."
    docker-compose -f $COMPOSE_FILE down
    print_message $GREEN "✅ 服务已停止"
}

# 函数：清理数据
clean_data() {
    print_message $BLUE "🧹 清理试运营数据..."
    docker-compose -f $COMPOSE_FILE down -v
    docker system prune -f
    print_message $GREEN "✅ 数据清理完成"
}

# 函数：重启服务
restart_services() {
    print_message $BLUE "🔄 重启试运营服务..."
    docker-compose -f $COMPOSE_FILE restart
    print_message $GREEN "✅ 服务已重启"
}

# 函数：更新服务
update_services() {
    print_message $BLUE "🔄 更新试运营服务..."

    # 备份当前数据
    docker-compose -f $COMPOSE_FILE exec -T db pg_dump -U postgres football_prediction_staging > backup_$(date +%Y%m%d_%H%M%S).sql

    # 重新构建和部署
    docker-compose -f $COMPOSE_FILE down
    build_images
    start_services
    comprehensive_health_check

    print_message $GREEN "✅ 服务更新完成"
}

# 函数：显示帮助信息
show_help() {
    echo "足球预测系统本地试运营环境部署脚本"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  deploy     部署试运营环境"
    echo "  status     显示当前状态"
    echo "  logs       显示服务日志"
    echo "  stop       停止所有服务"
    echo "  restart    重启所有服务"
    echo "  update     更新服务"
    echo "  clean      清理所有数据"
    echo "  health     健康检查"
    echo "  help       显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 deploy     # 部署试运营环境"
    echo "  $0 status     # 查看服务状态"
    echo "  $0 logs       # 查看日志"
}

# 主部署函数
deploy() {
    print_message $PURPLE "🚀 开始部署足球预测系统本地试运营环境..."
    print_message $BLUE "📅 部署时间: $(date '+%Y-%m-%d %H:%M:%S')"
    echo ""

    # 1. 环境检查
    environment_check
    echo ""

    # 2. 端口检查
    port_check
    echo ""

    # 3. 创建目录
    create_directories
    echo ""

    # 4. 构建镜像
    build_images
    echo ""

    # 5. 启动服务
    start_services
    echo ""

    # 6. 等待服务启动
    print_message $BLUE "⏳ 等待服务完全启动..."
    sleep 30
    echo ""

    # 7. 健康检查
    comprehensive_health_check
    echo ""

    # 8. 显示部署状态
    show_status
    echo ""

    # 9. 显示访问信息
    show_access_info
    echo ""

    # 10. 部署成功
    print_message $GREEN "🎉 试运营环境部署完成！"
    print_message $CYAN "📊 系统状态: 试运营就绪"
    print_message $CYAN "🌐 访问地址: http://localhost"
    print_message $CYAN "📈 监控面板: http://localhost:3000"
    echo ""

    print_message $YELLOW "📋 试运营建议:"
    echo "1. 访问主应用验证功能"
    echo "2. 查看监控面板了解系统状态"
    echo "3. 测试API端点和认证功能"
    echo "4. 检查日志输出和错误处理"
    echo "5. 验证数据持久化功能"
}

# 主程序
case "$1" in
    deploy)
        deploy
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
    restart)
        restart_services
        ;;
    update)
        update_services
        ;;
    clean)
        clean_data
        ;;
    health)
        comprehensive_health_check
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo "错误: 未知选项 '$1'"
        echo "使用 '$0 help' 查看帮助信息"
        exit 1
        ;;
esac