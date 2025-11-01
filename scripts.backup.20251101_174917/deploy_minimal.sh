#!/bin/bash

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

print_message() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

COMPOSE_FILE="docker/docker-compose.minimal.yml"

deploy() {
    print_message $PURPLE "🚀 开始最小化部署..."
    
    print_message $BLUE "🛑 停止现有服务..."
    docker-compose -f $COMPOSE_FILE down 2>/dev/null || true
    
    print_message $BLUE "🚀 启动数据库服务..."
    docker-compose -f $COMPOSE_FILE up -d db redis
    
    print_message $CYAN "⏳ 等待数据库启动..."
    sleep 15
    
    print_message $BLUE "🚀 启动应用服务..."
    docker-compose -f $COMPOSE_FILE up -d app
    
    print_message $BLUE "⏳ 等待应用启动..."
    sleep 30
    
    print_message $BLUE "🏥 健康检查..."
    
    if docker-compose -f $COMPOSE_FILE exec -T db pg_isready -U postgres -d football_prediction_staging >/dev/null 2>&1; then
        print_message $GREEN "  ✅ PostgreSQL 健康"
    else
        print_message $YELLOW "  ⚠️  PostgreSQL 连接检查失败"
    fi
    
    if docker-compose -f $COMPOSE_FILE exec -T redis redis-cli ping >/dev/null 2>&1; then
        print_message $GREEN "  ✅ Redis 健康"
    else
        print_message $YELLOW "  ⚠️  Redis 连接检查失败"
    fi
    
    print_message $CYAN "  - 检查应用启动..."
    for i in {1..30}; do
        if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
            print_message $GREEN "  ✅ 应用健康"
            break
        fi
        if [ $i -eq 30 ]; then
            print_message $YELLOW "  ⚠️  应用启动超时"
            break
        fi
        echo -n "."
        sleep 5
    done
    
    echo ""
    print_message $BLUE "📊 部署状态:"
    docker-compose -f $COMPOSE_FILE ps
    echo ""
    
    print_message $BLUE "🌐 访问信息:"
    echo "----------------------------------------"
    echo "🎯 主应用: http://localhost:8000"
    echo "📊 API文档: http://localhost:8000/docs"
    echo "💾 健康检查: http://localhost:8000/health"
    echo ""
    echo "🔑 数据库连接:"
    echo "  主机: localhost:5432"
    echo "  数据库: football_prediction_staging"
    echo "  用户名: postgres"
    echo "  密码: minimal_db_password_2024"
    echo ""
    echo "🔑 Redis连接:"
    echo "  主机: localhost:6379"
    echo "  密码: minimal_redis_password_2024"
    echo "----------------------------------------"
    echo ""
    
    print_message $GREEN "🎉 最小化部署完成！"
}

case "$1" in
    deploy)
        deploy
        ;;
    status)
        docker-compose -f $COMPOSE_FILE ps
        ;;
    logs)
        docker-compose -f $COMPOSE_FILE logs -f
        ;;
    stop)
        docker-compose -f $COMPOSE_FILE down
        print_message $GREEN "✅ 服务已停止"
        ;;
    restart)
        docker-compose -f $COMPOSE_FILE restart
        print_message $GREEN "✅ 服务已重启"
        ;;
    *)
        echo "用法: $0 {deploy|status|logs|stop|restart}"
        exit 1
        ;;
esac
