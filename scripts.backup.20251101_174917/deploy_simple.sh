#!/bin/bash

# =================================================================
# 简化快速部署脚本
# Simple Quick Deployment Script
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
COMPOSE_FILE="docker/docker-compose.simple.yml"
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

# 函数：环境检查
environment_check() {
    print_message $BLUE "🔍 环境检查..."

    check_command "docker"
    check_command "docker-compose"

    print_message $GREEN "✅ 环境检查通过"
}

# 函数：创建必要目录
create_directories() {
    print_message $BLUE "📁 创建必要目录..."

    mkdir -p data/{postgres,redis}
    mkdir -p logs

    print_message $GREEN "✅ 目录创建完成"
}

# 函数：停止现有服务
stop_existing() {
    print_message $BLUE "🛑 停止现有服务..."

    docker-compose -f $COMPOSE_FILE down 2>/dev/null || true
    docker-compose -f docker/docker-compose.quick.yml down 2>/dev/null || true
    docker-compose -f docker/docker-compose.staging.yml down 2>/dev/null || true

    print_message $GREEN "✅ 现有服务已停止"
}

# 函数：启动服务
start_services() {
    print_message $BLUE "🚀 启动简化快速服务..."

    # 启动数据库和Redis
    print_message $CYAN "  - 启动数据存储服务..."
    docker-compose -f $COMPOSE_FILE up -d db redis

    # 等待数据库启动
    print_message $CYAN "  - 等待数据库启动..."
    sleep 15

    # 检查数据库健康状态
    print_message $CYAN "  - 检查数据库健康状态..."
    for i in {1..30}; do
        if docker-compose -f $COMPOSE_FILE exec -T db pg_isready -U postgres -d football_prediction_staging >/dev/null 2>&1; then
            print_message $GREEN "    ✅ 数据库健康"
            break
        fi
        if [ $i -eq 30 ]; then
            print_message $YELLOW "    ⚠️  数据库启动超时，继续启动应用"
            break
        fi
        echo -n "."
        sleep 2
    done

    # 启动应用
    print_message $CYAN "  - 启动应用服务..."
    docker-compose -f $COMPOSE_FILE up -d app

    print_message $GREEN "✅ 简化快速服务启动完成"
}

# 函数：健康检查
health_check() {
    print_message $BLUE "🏥 执行健康检查..."

    # 检查数据库
    if docker-compose -f $COMPOSE_FILE exec -T db pg_isready -U postgres -d football_prediction_staging >/dev/null 2>&1; then
        print_message $GREEN "  ✅ PostgreSQL 健康"
    else
        print_message $YELLOW "  ⚠️  PostgreSQL 连接检查失败"
    fi

    # 检查Redis
    if docker-compose -f $COMPOSE_FILE exec -T redis redis-cli ping >/dev/null 2>&1; then
        print_message $GREEN "  ✅ Redis 健康"
    else
        print_message $YELLOW "  ⚠️  Redis 连接检查失败"
    fi

    # 检查应用（等待启动）
    print_message $CYAN "  - 等待应用启动..."
    for i in {1..60}; do
        if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
            print_message $GREEN "  ✅ 应用健康"
            break
        fi
        if [ $i -eq 60 ]; then
            print_message $YELLOW "  ⚠️  应用启动超时"
            break
        fi
        echo -n "."
        sleep 5
    done
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
    print_message $BLUE "🌐 简化快速部署访问信息:"
    echo "----------------------------------------"
    echo "🎯 主应用: http://localhost:8000"
    echo "📊 API文档: http://localhost:8000/docs"
    echo "💾 健康检查: http://localhost:8000/health"
    echo "🔍 API端点: http://localhost:8000/api/v1"
    echo ""
    echo "🔑 数据库连接:"
    echo "  主机: localhost:5432"
    echo "  数据库: football_prediction_staging"
    echo "  用户名: postgres"
    echo "  密码: simple_db_password_2024"
    echo ""
    echo "🔑 Redis连接:"
    echo "  主机: localhost:6379"
    echo "  密码: simple_redis_password_2024"
    echo ""
    echo "📝 查看日志:"
    echo "  docker-compose -f $COMPOSE_FILE logs -f"
    echo "  docker-compose -f $COMPOSE_FILE logs -f app"
    echo "  docker-compose -f $COMPOSE_FILE logs -f db"
    echo "----------------------------------------"
}

# 主部署函数
deploy() {
    print_message $PURPLE "🚀 开始部署足球预测系统简化快速环境..."
    print_message $BLUE "📅 部署时间: $(date '+%Y-%m-%d %H:%M:%S')"
    echo ""

    # 1. 环境检查
    environment_check
    echo ""

    # 2. 创建目录
    create_directories
    echo ""

    # 3. 停止现有服务
    stop_existing
    echo ""

    # 4. 启动服务
    start_services
    echo ""

    # 5. 等待服务启动
    print_message $BLUE "⏳ 等待服务完全启动..."
    sleep 30
    echo ""

    # 6. 健康检查
    health_check
    echo ""

    # 7. 显示部署状态
    show_status
    echo ""

    # 8. 显示访问信息
    show_access_info
    echo ""

    # 9. 部署成功
    print_message $GREEN "🎉 简化快速环境部署完成！"
    print_message $CYAN "📊 系统状态: 简化快速就绪"
    print_message $CYAN "🌐 访问地址: http://localhost:8000"
    echo ""

    print_message $YELLOW "📋 简化快速建议:"
    echo "1. 访问 http://localhost:8000/docs 查看API文档"
    echo "2. 测试API端点功能"
    echo "3. 检查数据库连接和数据"
    echo "4. 测试JWT认证功能"
    echo "5. 使用 docker-compose logs 查看日志"
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
        docker-compose -f $COMPOSE_FILE logs -f
        ;;
    stop)
        print_message $BLUE "🛑 停止简化快速服务..."
        docker-compose -f $COMPOSE_FILE down
        print_message $GREEN "✅ 服务已停止"
        ;;
    restart)
        print_message $BLUE "🔄 重启简化快速服务..."
        docker-compose -f $COMPOSE_FILE restart
        print_message $GREEN "✅ 服务已重启"
        ;;
    health)
        health_check
        ;;
    help|--help|-h)
        echo "足球预测系统简化快速部署脚本"
        echo ""
        echo "用法: $0 [选项]"
        echo ""
        echo "选项:"
        echo "  deploy     部署简化快速环境"
        echo "  status     显示当前状态"
        echo "  logs       显示服务日志"
        echo "  stop       停止所有服务"
        echo "  restart    重启所有服务"
        echo "  health     健康检查"
        echo "  help       显示此帮助信息"
        echo ""
        echo "示例:"
        echo "  $0 deploy     # 部署简化快速环境"
        echo "  $0 status     # 查看服务状态"
        echo "  $0 logs       # 查看日志"
        ;;
    *)
        echo "错误: 未知选项 '$1'"
        echo "使用 '$0 help' 查看帮助信息"
        exit 1
        ;;
esac
