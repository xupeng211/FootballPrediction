#!/bin/bash
# 🏆 全量数据回填后台执行脚本
# Enterprise-grade Backfill Background Execution Script
#
# Usage:
#   ./scripts/run_backfill_background.sh [--start-date=2022-01-01] [--end-date=today] [--source=all] [--resume]

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

# 默认参数
START_DATE="2022-01-01"
END_DATE=$(date +%Y-%m-%d)
SOURCE="all"
RESUME=false
DRY_RUN=false

# 解析参数
for arg in "$@"; do
    case $arg in
        --start-date=*)
            START_DATE="${arg#*=}"
            ;;
        --end-date=*)
            END_DATE="${arg#*=}"
            ;;
        --source=*)
            SOURCE="${arg#*=}"
            ;;
        --resume)
            RESUME=true
            ;;
        --dry-run)
            DRY_RUN=true
            ;;
        --help|-h)
            echo "🏆 全量数据回填后台执行脚本"
            echo ""
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --start-date=DATE    开始日期 (YYYY-MM-DD, 默认: 2022-01-01)"
            echo "  --end-date=DATE      结束日期 (YYYY-MM-DD, 默认: 今天)"
            echo "  --source=SOURCE      数据源 (all, football-data, fotmob, 默认: all)"
            echo "  --resume             从上次中断处继续"
            echo "  --dry-run            干运行模式"
            echo "  --help, -h           显示帮助信息"
            echo ""
            echo "Examples:"
            echo "  $0                                    # 默认全量回填"
            echo "  $0 --start-date=2023-01-01             # 从2023年开始"
            echo "  $0 --source=football-data              # 只使用Football-Data.org"
            echo "  $0 --resume                           # 断点续传"
            echo "  $0 --dry-run                          # 预览执行计划"
            exit 0
            ;;
        *)
            log_error "未知参数: $arg"
            echo "使用 --help 查看帮助信息"
            exit 1
            ;;
    esac
done

# 项目路径
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

log_info "🏆 启动全量数据回填系统"
log_info "📁 项目目录: $PROJECT_DIR"

# 环境检查
check_environment() {
    log_info "🔍 检查执行环境..."

    # 检查Python
    if ! command -v python3 &> /dev/null; then
        log_error "Python3 未安装"
        exit 1
    fi

    # 检查Docker
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose 未安装"
        exit 1
    fi

    # 检查脚本文件
    if [ ! -f "scripts/backfill_global.py" ]; then
        log_error "回填脚本不存在: scripts/backfill_global.py"
        exit 1
    fi

    # 检查环境文件
    if [ ! -f ".env" ]; then
        log_warn "环境文件 .env 不存在，请确保配置正确"
    fi

    log_info "✅ 环境检查通过"
}

# Docker服务检查
check_docker_services() {
    log_info "🐳 检查Docker服务状态..."

    # 检查服务是否运行
    if ! docker-compose ps | grep -q "Up"; then
        log_warn "Docker服务未运行，尝试启动..."
        docker-compose up -d

        # 等待服务启动
        log_info "⏳ 等待服务启动完成..."
        sleep 30
    fi

    # 检查数据库连接
    if docker-compose exec -T db pg_isready -U postgres > /dev/null 2>&1; then
        log_info "✅ 数据库连接正常"
    else
        log_error "数据库连接失败"
        exit 1
    fi

    log_info "✅ Docker服务检查通过"
}

# 创建日志目录
setup_logging() {
    local log_dir="logs/backfill"
    mkdir -p "$log_dir"

    # 生成日志文件名
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local log_file="$log_dir/backfill_$timestamp.log"

    echo "$log_file"
}

# 执行预检查
run_precheck() {
    log_info "🔍 执行预检查..."

    # 检查API密钥
    local api_key=$(python3 -c "
import os
from dotenv import load_dotenv
load_dotenv()
api_key = os.getenv('FOOTBALL_DATA_API_KEY', '')
print('CONFIGURED' if api_key else 'MISSING')
" 2>/dev/null)

    if [ "$api_key" = "MISSING" ]; then
        log_warn "FOOTBALL_DATA_API_KEY 未配置或为空"
        log_warn "数据采集可能失败，请检查 .env 文件"
    else
        log_info "✅ API密钥配置正常"
    fi

    # 测试数据库连接
    if docker-compose exec -T app python3 -c "
from sqlalchemy import create_engine
import os
database_url = os.getenv('DATABASE_URL')
if database_url:
    engine = create_engine(database_url)
    with engine.connect() as conn:
        conn.execute('SELECT 1')
    print('OK')
" 2>/dev/null; then
        log_info "✅ 应用数据库连接正常"
    else
        log_error "应用数据库连接失败"
        exit 1
    fi

    log_info "✅ 预检查完成"
}

# 主执行函数
main() {
    # 环境检查
    check_environment

    # Docker服务检查
    check_docker_services

    # 预检查
    run_precheck

    # 设置日志
    local log_file
    log_file=$(setup_logging)

    log_info "📝 日志文件: $log_file"

    # 构建Python命令
    local python_cmd="python3 scripts/backfill_global.py"
    python_cmd+=" --start-date=$START_DATE"
    python_cmd+=" --end-date=$END_DATE"
    python_cmd+=" --source=$SOURCE"

    if [ "$RESUME" = true ]; then
        python_cmd+=" --resume"
    fi

    if [ "$DRY_RUN" = true ]; then
        python_cmd+=" --dry-run"
    fi

    # 显示执行信息
    log_info "📋 执行配置:"
    log_info "   📅 时间范围: $START_DATE 到 $END_DATE"
    log_info "   🔗 数据源: $SOURCE"
    log_info "   🔄 断点续传: $([ "$RESUME" = true ] && echo "是" || echo "否")"
    log_info "   🔍 干运行: $([ "$DRY_RUN" = true ] && echo "是" || echo "否")"
    log_info ""
    log_info "🚀 开始执行数据回填..."

    # 执行命令
    if [ "$DRY_RUN" = true ]; then
        # 干运行直接输出到控制台
        $python_cmd
    else
        # 后台执行，输出到日志文件
        nohup $python_cmd > "$log_file" 2>&1 &
        local pid=$!

        log_info "✅ 后台任务已启动"
        log_info "🆔 进程ID: $pid"
        log_info "📝 实时日志: tail -f $log_file"
        log_info ""
        log_info "📊 监控命令:"
        log_info "   📋 查看日志: tail -f $log_file"
        log_info "   🔄 检查进度: grep -E '(处理|成功|失败)' $log_file | tail -20"
        log_info "   🗄️ 数据库查询: docker-compose exec db psql -U postgres -d football_prediction -c \"SELECT COUNT(*) FROM matches;\""
        log_info "   📈 统计信息: grep -E '(总比赛数|成功率)' $log_file | tail -5"
        log_info ""
        log_info "⚠️  如需停止: kill $pid"
        log_info "⚠️  如需继续: $0 --resume"

        # 保存PID到文件
        echo "$pid" > "data/backfill.pid"
        log_info "💾 进程ID已保存到: data/backfill.pid"
    fi
}

# 执行主函数
main "$@"