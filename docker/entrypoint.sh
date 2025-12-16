#!/bin/bash
# Docker容器入口点脚本
# 负责应用初始化、数据库连接池初始化和启动服务

set -e  # 遇到错误立即退出

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

# 检查必需的环境变量
check_environment_variables() {
    log_info "检查环境变量..."

    local required_vars=("DB_HOST" "DB_USER" "DB_PASSWORD" "DB_NAME")
    local missing_vars=()

    for var in "${required_vars[@]}"; do
        if [[ -z "${!var}" ]]; then
            missing_vars+=("$var")
        fi
    done

    if [[ ${#missing_vars[@]} -gt 0 ]]; then
        log_error "缺少必需的环境变量: ${missing_vars[*]}"
        exit 1
    fi

    log_success "环境变量检查通过"
}

# 等待数据库可用
wait_for_database() {
    log_info "等待数据库连接..."

    local max_attempts=30
    local attempt=1

    while [[ $attempt -le $max_attempts ]]; do
        if python -c "
import asyncio
import asyncpg
import os

async def check_db():
    try:
        conn = await asyncpg.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=int(os.getenv('DB_PORT', '5432')),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD', 'postgres'),
            database=os.getenv('DB_NAME', 'football_prediction'),
            timeout=5
        )
        await conn.execute('SELECT 1')
        await conn.close()
        print('OK')
    except Exception as e:
        print(f'ERROR: {e}')
        exit(1)

asyncio.run(check_db())
" 2>/dev/null; then
            log_success "数据库连接成功"
            return 0
        fi

        log_warning "数据库连接失败，等待5秒后重试 ($attempt/$max_attempts)"
        sleep 5
        ((attempt++))
    done

    log_error "数据库连接失败，已达到最大重试次数"
    exit 1
}

# 运行数据库迁移
run_database_migrations() {
    log_info "检查数据库迁移..."

    if [[ -f "/app/alembic.ini" ]]; then
        log_info "运行数据库迁移..."
        cd /app
        python -m alembic upgrade head || {
            log_warning "数据库迁移失败，但继续启动应用"
        }
    else
        log_info "未找到迁移文件，跳过数据库迁移"
    fi
}

# 初始化应用
initialize_application() {
    log_info "初始化应用..."

    # 运行应用初始化脚本
    python -c "
import asyncio
import sys
import os
sys.path.insert(0, '/app/src')

async def init():
    try:
        # 初始化配置
        from config import get_settings, setup_logging
        setup_logging()

        settings = get_settings()
        print(f'应用配置: {settings.app.name} v{settings.app.version}')
        print(f'运行环境: {settings.app.environment}')

        # 初始化数据库连接池
        from database.db_pool import init_global_db_pool
        await init_global_db_pool()
        print('✅ 数据库连接池初始化成功')

        # 验证关键模块
        from collectors.enhanced_fotmob_collector import EnhancedFotMobCollector
        print('✅ 数据采集模块加载成功')

        print('应用初始化完成')

    except Exception as e:
        print(f'❌ 应用初始化失败: {e}')
        import traceback
        traceback.print_exc()
        sys.exit(1)

asyncio.run(init())
" || {
        log_error "应用初始化失败"
        exit 1
    }

    log_success "应用初始化完成"
}

# 启动应用
start_application() {
    log_info "启动足球预测系统..."

    # 设置默认命令
    if [[ $# -eq 0 ]]; then
        set -- python -m src.main
    fi

    log_success "启动命令: $*"

    # 启动应用
    exec "$@"
}

# 信号处理
cleanup() {
    log_info "收到停止信号，正在清理..."

    # 运行清理脚本
    python -c "
import asyncio
import sys
sys.path.insert(0, '/app/src')

async def cleanup():
    try:
        from database.db_pool import get_db_pool
        pool = await get_db_pool()
        await pool.close()
        print('✅ 数据库连接池已关闭')
    except Exception as e:
        print(f'清理警告: {e}')

asyncio.run(cleanup())
" || log_warning "清理过程中出现警告"

    log_info "清理完成，退出"
    exit 0
}

# 设置信号处理
trap cleanup SIGTERM SIGINT

# 主函数
main() {
    log_info "足球预测系统 Docker 容器启动"
    log_info "Python 版本: $(python --version)"
    log_info "工作目录: $(pwd)"

    # 检查Python模块
    if ! python -c "import src.config" 2>/dev/null; then
        log_error "无法导入应用模块"
        exit 1
    fi

    # 执行初始化步骤
    check_environment_variables
    wait_for_database
    run_database_migrations
    initialize_application

    # 启动应用
    start_application "$@"
}

# 显示帮助信息
show_help() {
    cat << EOF
足球预测系统 Docker 入口点

用法: $0 [选项] [命令...]

选项:
  -h, --help     显示此帮助信息

环境变量:
  DB_HOST          数据库主机地址 (必需)
  DB_PORT          数据库端口 (默认: 5432)
  DB_USER          数据库用户名 (必需)
  DB_PASSWORD      数据库密码 (必需)
  DB_NAME          数据库名称 (必需)
  DB_POOL_MIN_SIZE 连接池最小大小 (默认: 5)
  DB_POOL_MAX_SIZE 连接池最大大小 (默认: 20)

  FOTMOB_X_MAS_HEADER     FotMob x-mas鉴权头
  FOTMOB_X_FOO_HEADER     FotMob x-foo鉴权头

  APP_NAME        应用名称 (默认: FootballPrediction)
  APP_VERSION     应用版本 (默认: 1.0.0)
  APP_ENV         运行环境 (development|testing|staging|production)

  LOG_LEVEL       日志级别 (DEBUG|INFO|WARNING|ERROR|CRITICAL)

示例:
  $0                                    # 启动默认应用
  $0 python -m src.main                 # 启动主应用
  $0 python scripts/healthcheck.py     # 运行健康检查
  $0 python -m pytest tests/           # 运行测试

EOF
}

# 解析命令行参数
case "$1" in
    -h|--help)
        show_help
        exit 0
        ;;
    *)
        main "$@"
        ;;
esac