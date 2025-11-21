#!/bin/bash

# 足球预测系统启动脚本
# Football Prediction System Startup Script

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

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

log_info "🏈 足球预测系统启动脚本"
log_info "项目根目录: $PROJECT_ROOT"

# 检查环境变量
log_info "🔍 检查环境变量..."
if [ ! -f ".env" ]; then
    log_warning ".env 文件不存在，使用默认环境变量"
else
    log_success "✅ 找到 .env 文件"
fi

# 函数：停止现有进程
stop_services() {
    log_info "🛑 停止现有服务..."

    # 停止后端服务
    if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
        log_info "停止后端服务 (端口 8000)..."
        pkill -f "uvicorn.*src.main:app" || true
    fi

    # 停止前端服务
    if lsof -Pi :3000 -sTCP:LISTEN -t >/dev/null 2>&1; then
        log_info "停止前端服务 (端口 3000)..."
        pkill -f "react-scripts.*start" || true
        pkill -f "npm.*start" || true
    fi

    # 等待进程完全停止
    sleep 2
}

# 函数：启动后端服务
start_backend() {
    log_info "🚀 启动后端服务..."

    # 检查Python环境
    if ! command -v python3 &> /dev/null; then
        log_error "Python3 未安装"
        exit 1
    fi

    # 激活虚拟环境（如果存在）
    if [ -d ".venv" ]; then
        log_info "📦 激活虚拟环境..."
        source .venv/bin/activate
    fi

    # 检查依赖
    if ! python3 -c "import fastapi" 2>/dev/null; then
        log_error "FastAPI 未安装，请先运行: pip install fastapi uvicorn"
        exit 1
    fi

    # 启动后端服务（后台运行）
    log_info "🔧 启动 FastAPI 服务 (端口 8000)..."
    nohup python3 -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000 \
        > logs/backend.log 2>&1 &

    BACKEND_PID=$!
    echo $BACKEND_PID > logs/backend.pid

    # 等待后端启动
    log_info "⏳ 等待后端服务启动..."
    for i in {1..30}; do
        if curl -s http://localhost:8000/ >/dev/null 2>&1; then
            log_success "✅ 后端服务启动成功 (PID: $BACKEND_PID)"
            break
        fi
        if [ $i -eq 30 ]; then
            log_error "❌ 后端服务启动超时"
            tail -20 logs/backend.log
            exit 1
        fi
        sleep 1
    done
}

# 函数：启动前端服务
start_frontend() {
    log_info "🎨 启动前端服务..."

    # 检查Node.js环境
    if ! command -v node &> /dev/null; then
        log_error "Node.js 未安装"
        exit 1
    fi

    # 检查前端目录
    if [ ! -d "frontend" ]; then
        log_error "前端目录不存在"
        exit 1
    fi

    cd frontend

    # 检查依赖是否安装
    if [ ! -d "node_modules" ]; then
        log_info "📦 安装前端依赖..."
        npm install
    fi

    # 检查环境变量
    if [ ! -f ".env.local" ]; then
        log_info "📝 创建前端环境配置..."
        cat > .env.local << EOF
REACT_APP_API_BASE_URL=http://localhost:8000/api/v1
GENERATE_SOURCEMAP=false
EOF
    fi

    # 启动前端服务（后台运行）
    log_info "🔧 启动 React 开发服务器 (端口 3000)..."
    nohup npm start > ../logs/frontend.log 2>&1 &

    FRONTEND_PID=$!
    echo $FRONTEND_PID > ../logs/frontend.pid

    cd ..

    # 等待前端启动
    log_info "⏳ 等待前端服务启动..."
    for i in {1..60}; do
        if curl -s http://localhost:3000 >/dev/null 2>&1; then
            log_success "✅ 前端服务启动成功 (PID: $FRONTEND_PID)"
            break
        fi
        if [ $i -eq 60 ]; then
            log_error "❌ 前端服务启动超时"
            tail -20 logs/frontend.log
            exit 1
        fi
        sleep 2
    done
}

# 函数：显示服务状态
show_status() {
    log_info "📊 服务状态:"
    echo ""

    # 后端状态
    if curl -s http://localhost:8000/ >/dev/null 2>&1; then
        log_success "✅ 后端服务: http://localhost:8000"
        log_info "   API文档: http://localhost:8000/docs"
    else
        log_error "❌ 后端服务未响应"
    fi

    # 前端状态
    if curl -s http://localhost:3000 >/dev/null 2>&1; then
        log_success "✅ 前端服务: http://localhost:3000"
    else
        log_error "❌ 前端服务未响应"
    fi

    echo ""
    log_info "📝 日志文件:"
    log_info "   后端日志: logs/backend.log"
    log_info "   前端日志: logs/frontend.log"
    log_info ""
    log_info "🔧 停止服务:"
    log_info "   ./scripts/start_app.sh stop"
}

# 函数：测试API
test_api() {
    log_info "🧪 测试API连接..."

    # 测试根路径
    if curl -s http://localhost:8000/ | grep -q "足球预测系统API"; then
        log_success "✅ 根路径测试通过"
    else
        log_warning "⚠️ 根路径测试失败"
    fi

    # 测试比赛API
    if curl -s http://localhost:8000/api/v1/matches | grep -q "matches"; then
        log_success "✅ 比赛API测试通过"
    else
        log_warning "⚠️ 比赛API测试失败"
    fi
}

# 主函数
main() {
    # 创建日志目录
    mkdir -p logs

    # 处理命令行参数
    if [ "$1" = "stop" ]; then
        stop_services
        log_success "🛑 所有服务已停止"
        exit 0
    fi

    if [ "$1" = "status" ]; then
        show_status
        exit 0
    fi

    log_info "🚀 启动足球预测系统..."

    # 停止现有服务
    stop_services

    # 启动后端
    start_backend

    # 启动前端
    start_frontend

    # 测试API
    test_api

    # 显示状态
    show_status

    log_success "🎉 足球预测系统启动完成！"
    log_info ""
    log_info "🌐 访问地址:"
    log_info "   前端界面: http://localhost:3000"
    log_info "   API文档:  http://localhost:8000/docs"
    log_info ""
    log_info "📋 常用命令:"
    log_info "   查看状态: ./scripts/start_app.sh status"
    log_info "   停止服务: ./scripts/start_app.sh stop"
    log_info ""
}

# 信号处理
trap 'log_warning "接收到中断信号，正在停止服务..."; stop_services; exit 1' INT TERM

# 运行主函数
main "$@"