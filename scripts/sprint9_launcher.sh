#!/bin/bash
# Sprint 9 生产环境一键启动脚本
# 用途: 快速部署完整的生产环境和监控栈

set -e  # 遇到错误立即退出

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}ℹ️  INFO: $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ SUCCESS: $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  WARNING: $1${NC}"
}

log_error() {
    echo -e "${RED}❌ ERROR: $1${NC}"
}

# 检查当前目录
PROJECT_DIR="/home/user/projects/FootballPrediction"
if [[ ! -d "$PROJECT_DIR" ]]; then
    log_error "项目目录不存在: $PROJECT_DIR"
    exit 1
fi

cd "$PROJECT_DIR"
log_info "当前工作目录: $(pwd)"

# 显示启动横幅
echo -e "${BLUE}"
echo "=========================================="
echo "🚀 Sprint 9 生产环境一键启动器"
echo "=========================================="
echo "📋 部署内容:"
echo "   • FastAPI应用 + PostgreSQL + Redis"
echo "   • Prometheus + Grafana + Alertmanager"
echo "   • 首周观察模式 (0.1x Kelly)"
echo "   • 完整监控和告警系统"
echo "=========================================="
echo -e "${NC}"

# 检查必要文件
log_info "检查必要文件..."
required_files=(
    "scripts/setup_api_keys.py"
    "scripts/deploy_production.py"
    "scripts/start_first_week.py"
    "docker-compose.yml"
    "docker-compose.monitoring.yml"
)

for file in "${required_files[@]}"; do
    if [[ ! -f "$file" ]]; then
        log_error "缺少必要文件: $file"
        exit 1
    fi
done
log_success "所有必要文件检查通过"

# 检查Docker环境
log_info "检查Docker环境..."
if ! command -v docker &> /dev/null; then
    log_error "Docker未安装或不在PATH中"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    log_error "Docker Compose未安装或不在PATH中"
    exit 1
fi

# 检查Docker服务状态
if ! docker info &> /dev/null; then
    log_error "Docker服务未运行，请启动Docker服务"
    exit 1
fi

log_success "Docker环境检查通过"

# 创建必要目录
log_info "创建必要目录..."
mkdir -p logs/{kelly,performance,audit,monitoring}
mkdir -p data/{models,cache,backups}
mkdir -p monitoring/{prometheus,grafana,alertmanager}
log_success "目录创建完成"

# 设置权限
log_info "设置脚本执行权限..."
chmod +x scripts/*.py
chmod +x scripts/*.sh 2>/dev/null || true
log_success "权限设置完成"

# 检查环境配置
log_info "检查环境配置..."
if [[ ! -f ".env.production" ]]; then
    log_warning ".env.production文件不存在，将运行API配置向导"

    # 运行API配置
    log_info "启动API配置向导..."
    if python3 scripts/setup_api_keys.py; then
        log_success "API配置完成"
    else
        log_error "API配置失败"
        exit 1
    fi
else
    log_success "环境配置文件已存在"
fi

# 检查Python依赖
log_info "检查Python依赖..."
if ! python3 -c "import requests, asyncio" &> /dev/null; then
    log_error "Python依赖缺失，请运行: pip install -r requirements.txt"
    exit 1
fi
log_success "Python依赖检查通过"

# Step 1: API连接验证
log_info "Step 1: 验证API连接..."
echo "----------------------------------------"
if python3 scripts/verify_live_connection.py; then
    log_success "API连接验证通过"
else
    log_warning "API连接验证失败，但继续部署..."
fi

# Step 2: 部署生产环境
log_info "Step 2: 部署生产环境..."
echo "----------------------------------------"
if python3 scripts/deploy_production.py; then
    log_success "生产环境部署完成"
else
    log_error "生产环境部署失败"
    exit 1
fi

# 等待服务启动
log_info "等待服务启动完成..."
sleep 30

# 验证核心服务
log_info "验证核心服务状态..."
if curl -f http://localhost:8000/health &> /dev/null; then
    log_success "主应用服务正常"
else
    log_error "主应用服务异常"
    docker-compose logs app
    exit 1
fi

# Step 3: 启动监控栈
log_info "Step 3: 启动监控栈..."
echo "----------------------------------------"
if docker-compose -f docker-compose.monitoring.yml up -d; then
    log_success "监控栈启动完成"
else
    log_error "监控栈启动失败"
    exit 1
fi

# 等待监控服务启动
log_info "等待监控服务启动..."
sleep 20

# Step 4: 启动首周观察模式
log_info "Step 4: 启动首周观察模式..."
echo "----------------------------------------"
if python3 scripts/start_first_week.py; then
    log_success "首周观察模式启动完成"
else
    log_warning "首周观察模式启动失败，请手动检查"
fi

# 最终验证
log_info "最终验证部署状态..."
echo "========================================"

# 服务状态检查
services_status=true

# 检查主应用
if curl -f http://localhost:8000/health &> /dev/null; then
    log_success "✅ 主应用服务 (http://localhost:8000)"
else
    log_error "❌ 主应用服务异常"
    services_status=false
fi

# 检查Prometheus
if curl -f http://localhost:9090/-/healthy &> /dev/null; then
    log_success "✅ Prometheus监控 (http://localhost:9090)"
else
    log_warning "⚠️ Prometheus监控启动中或异常"
fi

# 检查Grafana
if curl -f http://localhost:3000/api/health &> /dev/null; then
    log_success "✅ Grafana面板 (http://localhost:3000)"
else
    log_warning "⚠️ Grafana面板启动中或异常"
fi

# 检查数据库
if docker-compose exec -T db pg_isready -U football_user &> /dev/null; then
    log_success "✅ PostgreSQL数据库"
else
    log_error "❌ PostgreSQL数据库异常"
    services_status=false
fi

# 检查Redis
if docker-compose exec -T redis redis-cli ping &> /dev/null; then
    log_success "✅ Redis缓存"
else
    log_error "❌ Redis缓存异常"
    services_status=false
fi

echo "========================================"

# 显示访问信息
echo -e "${GREEN}"
echo "🎉 Sprint 9 生产环境部署完成！"
echo "========================================"
echo -e "${YELLOW}📊 监控面板访问信息:"
echo "   Grafana:     http://localhost:3000 (admin/admin123)"
echo "   Prometheus:  http://localhost:9090"
echo "   API文档:     http://localhost:8000/docs"
echo "   健康检查:    http://localhost:8000/health"
echo ""
echo -e "${BLUE}🔧 首周观察模式配置:"
echo "   • Kelly倍数: 0.1x (极保守)"
echo "   • 单日限额: ¥10"
echo "   • 自动观察: Brier Score偏离>15%触发"
echo ""
echo -e "${GREEN}📋 常用命令:"
echo "   查看日志:    docker-compose logs -f app"
echo "   服务状态:    docker-compose ps"
echo "   重启服务:    docker-compose restart"
echo "   性能报告:    python3 scripts/daily_performance.py"
echo "   完整文档:    docs/SPRINT9_OPERATIONS_MANUAL.md"
echo -e "${NC}"

# 设置定时任务提醒
echo -e "${YELLOW}"
echo "⏰ 建议设置以下定时任务 (crontab -e):"
echo "   # 每日00:30重置Kelly计数器"
echo "   30 0 * * * cd $PROJECT_DIR && python3 scripts/reset_kelly_counters.py reset"
echo ""
echo "   # 每日08:00生成性能报告"
echo "   0 8 * * * cd $PROJECT_DIR && python3 scripts/daily_performance.py"
echo -e "${NC}"

# 安全提示
echo -e "${GREEN}"
echo "========================================"
echo "🔒 首周安全提醒:"
echo "   1. 系统运行在极低风险模式 (0.1x Kelly)"
echo "   2. 所有异常都会自动切换到观察模式"
echo "   3. 实时监控面板24/7跟踪系统状态"
echo "   4. 建议每日检查性能报告和告警信息"
echo "========================================"
echo -e "${NC}"

if [ "$services_status" = true ]; then
    log_success "🎯 所有核心服务运行正常，系统已就绪！"
    exit 0
else
    log_warning "⚠️ 部分服务异常，请检查日志进行排查"
    exit 1
fi