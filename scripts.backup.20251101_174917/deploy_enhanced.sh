#!/bin/bash

# =================================================================
# 增强版部署脚本 - 渐进式增强阶段1
# Enhanced Deployment Script - Progressive Enhancement Phase 1
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
COMPOSE_FILE="docker/docker-compose.enhanced.yml"

# 函数：打印带颜色的消息
print_message() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# 函数：检查端口冲突
check_port_conflicts() {
    print_message $BLUE "🔍 检查端口冲突..."

    local ports=(8001 5433 6380)
    local conflicts=()

    for port in "${ports[@]}"; do
        if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
            conflicts+=($port)
        fi
    done

    if [ ${#conflicts[@]} -gt 0 ]; then
        print_message $YELLOW "⚠️  端口冲突检测到: ${conflicts[*]}"
        print_message $YELLOW "   增强版将使用不同端口以避免冲突"
        print_message $CYAN "   - 应用: 8001 (vs 8000)"
        print_message $CYAN "   - 数据库: 5433 (vs 5432)"
        print_message $CYAN "   - Redis: 6380 (vs 6379)"
    else
        print_message $GREEN "✅ 无端口冲突"
    fi
}

# 函数：环境检查
environment_check() {
    print_message $BLUE "🔍 环境检查..."

    if ! command -v docker &> /dev/null; then
        print_message $RED "❌ Docker 未安装"
        exit 1
    fi

    if ! command -v docker-compose &> /dev/null; then
        print_message $RED "❌ Docker Compose 未安装"
        exit 1
    fi

    print_message $GREEN "✅ 环境检查通过"
}

# 函数：创建增强版网络
create_enhanced_network() {
    print_message $BLUE "🌐 创建增强版网络..."

    # 检查网络是否存在
    if ! docker network ls | grep -q "enhanced_backend"; then
        docker network create enhanced_backend
        print_message $GREEN "✅ 增强版网络已创建"
    else
        print_message $CYAN "  - 增强版网络已存在"
    fi
}

# 函数：构建增强版镜像
build_enhanced_image() {
    print_message $BLUE "🏗️ 构建增强版应用镜像..."

    if docker-compose -f $COMPOSE_FILE build app; then
        print_message $GREEN "✅ 增强版镜像构建成功"
    else
        print_message $RED "❌ 增强版镜像构建失败"
        exit 1
    fi
}

# 函数：启动增强版服务
start_enhanced_services() {
    print_message $BLUE "🚀 启动增强版服务..."

    # 启动数据库和Redis
    print_message $CYAN "  - 启动数据存储服务..."
    docker-compose -f $COMPOSE_FILE up -d db redis

    # 等待数据库健康检查
    print_message $CYAN "  - 等待数据库健康检查..."
    local max_attempts=30
    local attempt=0

    while [ $attempt -lt $max_attempts ]; do
        if docker-compose -f $COMPOSE_FILE exec -T db pg_isready -U postgres -d football_prediction_staging >/dev/null 2>&1; then
            print_message $GREEN "    ✅ 数据库健康"
            break
        fi
        if [ $attempt -eq $((max_attempts-1)) ]; then
            print_message $YELLOW "    ⚠️  数据库健康检查超时，继续启动应用"
            break
        fi
        echo -n "."
        sleep 2
        attempt=$((attempt+1))
    done

    # 启动应用
    print_message $CYAN "  - 启动增强版应用..."
    docker-compose -f $COMPOSE_FILE up -d app

    print_message $GREEN "✅ 增强版服务启动完成"
}

# 函数：增强版健康检查
enhanced_health_check() {
    print_message $BLUE "🏥 执行增强版健康检查..."

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
    print_message $CYAN "  - 检查增强版应用启动..."
    for i in {1..60}; do
        if curl -sf http://localhost:8001/health > /dev/null 2>&1; then
            print_message $GREEN "  ✅ 增强版应用健康"
            break
        fi
        if [ $i -eq 60 ]; then
            print_message $YELLOW "  ⚠️  增强版应用启动超时"
            break
        fi
        echo -n "."
        sleep 3
    done
}

# 函数：测试数据访问功能
test_data_access() {
    print_message $BLUE "🧪 测试数据访问功能..."

    # 等待应用完全启动
    sleep 5

    # 测试基础健康检查
    print_message $CYAN "  - 测试基础健康检查..."
    if curl -sf http://localhost:8001/health > /dev/null 2>&1; then
        local health_response=$(curl -s http://localhost:8001/health)
        print_message $GREEN "    ✅ 健康检查响应: $health_response"
    else
        print_message $YELLOW "    ⚠️  健康检查失败"
    fi

    # 测试预测API
    print_message $CYAN "  - 测试预测API..."
    if curl -sf http://localhost:8001/predictions > /dev/null 2>&1; then
        print_message $GREEN "    ✅ 预测API可访问"
    else
        print_message $YELLOW "    ⚠️  预测API访问失败"
    fi

    # 创建测试预测
    print_message $CYAN "  - 创建测试预测..."
    local test_response=$(curl -s -X POST "http://localhost:8001/predictions?match_id=1&predicted_winner=TeamA&confidence=0.75" 2>/dev/null || echo "")
    if [[ $test_response == *"id"* ]]; then
        print_message $GREEN "    ✅ 测试预测创建成功"
    else
        print_message $YELLOW "    ⚠️  测试预测创建失败"
    fi
}

# 函数：显示增强版状态
show_enhanced_status() {
    print_message $BLUE "📊 增强版部署状态:"
    echo "----------------------------------------"
    docker-compose -f $COMPOSE_FILE ps
    echo "----------------------------------------"
}

# 函数：显示增强版访问信息
show_enhanced_access_info() {
    print_message $BLUE "🌐 增强版访问信息:"
    echo "----------------------------------------"
    echo "🎯 增强版应用: http://localhost:8001"
    echo "📊 增强版API文档: http://localhost:8001/docs"
    echo "💾 增强版健康检查: http://localhost:8001/health"
    echo "🔍 预测管理API: http://localhost:8001/predictions"
    echo ""
    echo "🔑 数据库连接 (增强版):"
    echo "  主机: localhost:5433"
    echo "  数据库: football_prediction_staging"
    echo "  用户名: postgres"
    echo "  密码: enhanced_db_password_2024"
    echo ""
    echo "🔑 Redis连接 (增强版):"
    echo "  主机: localhost:6380"
    echo "  密码: enhanced_redis_password_2024"
    echo ""
    echo "🔗 API功能对比:"
    echo "  原版: http://localhost:8000 (基础功能)"
    echo "  增强版: http://localhost:8001 (数据库集成)"
    echo ""
    echo "📝 查看日志:"
    echo "  docker-compose -f $COMPOSE_FILE logs -f"
    echo "  docker-compose -f $COMPOSE_FILE logs -f app"
    echo "----------------------------------------"
}

# 主部署函数
deploy_enhanced() {
    print_message $PURPLE "🚀 开始增强版部署 - 渐进式增强阶段1..."
    print_message $BLUE "📅 部署时间: $(date '+%Y-%m-%d %H:%M:%S')"
    echo ""

    # 1. 环境检查
    environment_check
    echo ""

    # 2. 端口冲突检查
    check_port_conflicts
    echo ""

    # 3. 创建网络
    create_enhanced_network
    echo ""

    # 4. 停止现有的增强版服务
    print_message $BLUE "🛑 停止现有增强版服务..."
    docker-compose -f $COMPOSE_FILE down 2>/dev/null || true
    echo ""

    # 5. 构建镜像
    build_enhanced_image
    echo ""

    # 6. 启动服务
    start_enhanced_services
    echo ""

    # 7. 等待服务启动
    print_message $BLUE "⏳ 等待服务完全启动..."
    sleep 20
    echo ""

    # 8. 健康检查
    enhanced_health_check
    echo ""

    # 9. 测试数据访问功能
    test_data_access
    echo ""

    # 10. 显示状态
    show_enhanced_status
    echo ""

    # 11. 显示访问信息
    show_enhanced_access_info
    echo ""

    # 12. 部署成功
    print_message $GREEN "🎉 增强版部署完成！"
    print_message $CYAN "📊 系统状态: 渐进式增强阶段1完成"
    print_message $CYAN "🌐 增强版地址: http://localhost:8001"
    print_message $CYAN "🔗 原版地址: http://localhost:8000"
    echo ""

    print_message $YELLOW "📋 增强版功能:"
    echo "✅ PostgreSQL 数据库集成"
    echo "✅ 预测数据 CRUD 操作"
    echo "✅ 增强健康检查"
    echo "✅ 数据库连接池管理"
    echo "✅ Pydantic 数据验证"
    echo ""

    print_message $CYAN "🔄 下一步建议:"
    echo "1. 测试 http://localhost:8001/docs API文档"
    echo "2. 创建和查询预测数据"
    echo "3. 验证数据库持久化"
    echo "4. 准备阶段3: 业务逻辑层集成"
}

# 主程序
case "$1" in
    deploy)
        deploy_enhanced
        ;;
    status)
        show_enhanced_status
        ;;
    logs)
        docker-compose -f $COMPOSE_FILE logs -f
        ;;
    stop)
        print_message $BLUE "🛑 停止增强版服务..."
        docker-compose -f $COMPOSE_FILE down
        print_message $GREEN "✅ 增强版服务已停止"
        ;;
    restart)
        print_message $BLUE "🔄 重启增强版服务..."
        docker-compose -f $COMPOSE_FILE restart
        print_message $GREEN "✅ 增强版服务已重启"
        ;;
    test)
        test_data_access
        ;;
    help|--help|-h)
        echo "足球预测系统增强版部署脚本"
        echo ""
        echo "用法: $0 [选项]"
        echo ""
        echo "选项:"
        echo "  deploy     部署增强版环境"
        echo "  status     显示增强版状态"
        echo "  logs       显示增强版服务日志"
        echo "  stop       停止增强版所有服务"
        echo "  restart    重启增强版所有服务"
        echo "  test       测试数据访问功能"
        echo "  help       显示此帮助信息"
        echo ""
        echo "示例:"
        echo "  $0 deploy     # 部署增强版环境"
        echo "  $0 status     # 查看增强版服务状态"
        echo "  $0 logs       # 查看增强版日志"
        ;;
    *)
        echo "错误: 未知选项 '$1'"
        echo "使用 '$0 help' 查看帮助信息"
        exit 1
        ;;
esac