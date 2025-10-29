#!/bin/bash

# 足球预测系统生产环境一键部署脚本
set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 项目信息
PROJECT_NAME="football-prediction"
DOCKER_IMAGE_TAG="football-prediction:prod"
COMPOSE_FILE="docker-compose.prod.yml"

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

# 函数：备份现有数据
backup_data() {
    print_message $BLUE "📦 备份现有数据..."

    BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
    mkdir -p $BACKUP_DIR

    # 备份数据库
    if docker-compose -f $COMPOSE_FILE ps db | grep -q "Up"; then
        print_message $CYAN "  - 备份数据库..."
        docker-compose -f $COMPOSE_FILE exec -T db pg_dump -U postgres football_prediction_prod | gzip > $BACKUP_DIR/database.sql.gz
        print_message $GREEN "  ✅ 数据库备份完成"
    fi

    # 备份配置文件
    print_message $CYAN "  - 备份配置文件..."
    cp .env.production $BACKUP_DIR/env.production.backup 2>/dev/null || true
    cp nginx/nginx.prod.conf $BACKUP_DIR/nginx.prod.conf.backup 2>/dev/null || true
    print_message $GREEN "  ✅ 配置文件备份完成"

    print_message $GREEN "📦 数据备份完成: $BACKUP_DIR"
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
        sleep 10
        ((attempt++))
    done

    print_message $RED "  ❌ $service_name 健康检查失败"
    return 1
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
    local domain=${DOMAIN:-localhost}

    print_message $BLUE "🌐 访问信息:"
    echo "----------------------------------------"
    echo "🎯 主应用: http://${domain}"
    echo "🔒 HTTPS: https://${domain}"
    echo "📊 API文档: http://${domain}/docs"
    echo "💾 健康检查: http://${domain}/health"
    echo "📈 监控面板: http://${domain}/grafana"
    echo "📊 Prometheus: http://${domain}/prometheus"
    echo "----------------------------------------"

    if [ -n "$GRAFANA_ADMIN_PASSWORD" ]; then
        print_message $CYAN "🔑 Grafana 登录信息:"
        echo "  用户名: admin"
        echo "  密码: $GRAFANA_ADMIN_PASSWORD"
    fi
}

# 主部署函数
deploy() {
    print_message $PURPLE "🚀 开始部署足球预测系统生产环境..."
    print_message $BLUE "📅 部署时间: $(date '+%Y-%m-%d %H:%M:%S')"
    echo ""

    # 1. 环境检查
    print_message $BLUE "🔍 环境检查..."
    check_command "docker"
    check_command "docker-compose"
    check_command "curl"

    # 检查必要文件
    if [ ! -f ".env.production" ]; then
        print_message $RED "❌ 错误: .env.production 文件不存在"
        print_message $YELLOW "💡 请复制 .env.production.example 并配置相关参数"
        exit 1
    fi

    if [ ! -f "$COMPOSE_FILE" ]; then
        print_message $RED "❌ 错误: $COMPOSE_FILE 文件不存在"
        exit 1
    fi

    print_message $GREEN "✅ 环境检查通过"
    echo ""

    # 2. 端口检查
    print_message $BLUE "🔍 端口检查..."
    check_port 80 "HTTP服务"
    check_port 443 "HTTPS服务"
    check_port 5432 "PostgreSQL数据库"
    check_port 6379 "Redis缓存"
    print_message $GREEN "✅ 端口检查完成"
    echo ""

    # 3. 备份现有数据
    backup_data
    echo ""

    # 4. 检查Docker镜像
    print_message $BLUE "🔍 检查 Docker 镜像..."
    if ! docker images | grep -q "$DOCKER_IMAGE_TAG"; then
        print_message $YELLOW "⚠️  生产镜像不存在，开始构建..."
        docker build -t $DOCKER_IMAGE_TAG -f Dockerfile.prod .
        print_message $GREEN "✅ Docker 镜像构建完成"
    else
        print_message $GREEN "✅ Docker 镜像已存在"
    fi
    echo ""

    # 5. 停止现有服务
    print_message $BLUE "🛑 停止现有服务..."
    docker-compose -f $COMPOSE_FILE down 2>/dev/null || true
    print_message $GREEN "✅ 现有服务已停止"
    echo ""

    # 6. 启动服务
    print_message $BLUE "🚀 启动生产服务..."
    docker-compose -f $COMPOSE_FILE up -d
    print_message $GREEN "✅ 服务启动完成"
    echo ""

    # 7. 等待服务启动
    print_message $BLUE "⏳ 等待服务启动..."
    sleep 30
    echo ""

    # 8. 健康检查
    print_message $BLUE "🏥 执行健康检查..."

    # 检查数据库
    health_check "PostgreSQL" "http://localhost/api/v1/health" 6

    # 检查Redis
    health_check "Redis" "http://localhost/api/v1/health" 3

    # 检查主应用
    health_check "主应用" "http://localhost/health" 5

    print_message $GREEN "✅ 所有服务健康检查通过"
    echo ""

    # 9. 显示部署状态
    show_status
    echo ""

    # 10. 显示访问信息
    show_access_info
    echo ""

    # 11. 部署成功
    print_message $GREEN "🎉 部署完成！"
    print_message $CYAN "📊 系统状态: 生产就绪"
    print_message $CYAN "🌐 访问地址: https://${DOMAIN:-localhost}"
    print_message $CYAN "📈 监控面板: https://${DOMAIN:-localhost}/grafana"
    echo ""

    print_message $YELLOW "📋 后续建议:"
    echo "1. 配置监控告警规则"
    echo "2. 设置定期备份任务"
    echo "3. 配置SSL证书自动续期"
    echo "4. 启用日志轮转"
    echo "5. 设置性能监控"
}

# 函数：回滚部署
rollback() {
    print_message $PURPLE "🔄 开始回滚部署..."

    if [ ! -d "backups" ]; then
        print_message $RED "❌ 错误: 没有找到备份目录"
        exit 1
    fi

    # 找到最新的备份
    LATEST_BACKUP=$(ls -t backups/ | head -n 1)

    if [ -z "$LATEST_BACKUP" ]; then
        print_message $RED "❌ 错误: 没有找到可用的备份"
        exit 1
    fi

    print_message $BLUE "📦 使用备份: $LATEST_BACKUP"

    # 停止当前服务
    docker-compose -f $COMPOSE_FILE down

    # 恢复配置文件
    if [ -f "backups/$LATEST_BACKUP/env.production.backup" ]; then
        cp "backups/$LATEST_BACKUP/env.production.backup" .env.production
    fi

    if [ -f "backups/$LATEST_BACKUP/nginx.prod.conf.backup" ]; then
        cp "backups/$LATEST_BACKUP/nginx.prod.conf.backup" nginx/nginx.prod.conf
    fi

    # 重新启动服务
    docker-compose -f $COMPOSE_FILE up -d

    print_message $GREEN "✅ 回滚完成"
}

# 显示帮助信息
show_help() {
    echo "足球预测系统生产环境部署脚本"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  deploy     部署生产环境"
    echo "  rollback   回滚到上一个版本"
    echo "  status     显示当前状态"
    echo "  logs       显示服务日志"
    echo "  stop       停止所有服务"
    echo "  restart    重启所有服务"
    echo "  help       显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 deploy     # 部署生产环境"
    echo "  $0 status     # 查看服务状态"
    echo "  $0 logs       # 查看日志"
}

# 主程序
case "$1" in
    deploy)
        deploy
        ;;
    rollback)
        rollback
        ;;
    status)
        show_status
        ;;
    logs)
        docker-compose -f $COMPOSE_FILE logs -f
        ;;
    stop)
        print_message $BLUE "🛑 停止所有服务..."
        docker-compose -f $COMPOSE_FILE down
        print_message $GREEN "✅ 服务已停止"
        ;;
    restart)
        print_message $BLUE "🔄 重启所有服务..."
        docker-compose -f $COMPOSE_FILE restart
        print_message $GREEN "✅ 服务已重启"
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