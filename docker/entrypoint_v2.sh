#!/bin/bash
# Docker容器入口点脚本 v2.0
# 负责应用初始化、数据库连接池初始化和启动服务
# 适配新的 v2.0 架构：services + inference modules

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

# 等待数据库就绪
wait_for_database() {
    log_info "等待数据库就绪..."

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
            host=os.getenv('DB_HOST'),
            port=int(os.getenv('DB_PORT', 5432)),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            database=os.getenv('DB_NAME'),
            timeout=5
        )
        await conn.close()
        return True
    except Exception as e:
        print(f'数据库连接失败: {e}')
        return False

result = asyncio.run(check_db())
exit(0 if result else 1)
" 2>/dev/null; then
            log_success "数据库连接成功"
            return 0
        fi

        log_warning "数据库连接尝试 $attempt/$max_attempts 失败，重试中..."
        sleep 2
        ((attempt++))
    done

    log_error "数据库连接失败，超过最大尝试次数"
    exit 1
}

# 运行数据库迁移
run_database_migrations() {
    log_info "运行数据库迁移..."

    # 检查是否有 alembic 配置
    if [[ ! -f "alembic.ini" ]]; then
        log_warning "未找到 alembic.ini，跳过数据库迁移"
        return 0
    fi

    # 检查是否有迁移目录
    if [[ ! -d "src/database/migrations" ]]; then
        log_warning "未找到迁移目录，跳过数据库迁移"
        return 0
    fi

    if python -c "
import os
import sys
sys.path.insert(0, '/app/src')

try:
    from alembic.config import Config
    from alembic import command

    # 配置 alembic
    alembic_cfg = Config('alembic.ini')

    # 运行迁移
    command.upgrade(alembic_cfg, 'head')
    print('✅ 数据库迁移成功')

except ImportError:
    print('⚠️ alembic 未安装，跳过数据库迁移')
except Exception as e:
    print(f'❌ 数据库迁移失败: {e}')
    exit(1)
"; then
        log_success "数据库迁移完成"
    else
        log_warning "数据库迁移失败，但继续启动应用"
    fi
}

# 初始化应用 (v2.0 架构)
initialize_application() {
    log_info "初始化足球预测系统 v2.0..."

    python -c "
import asyncio
import os
import sys
sys.path.insert(0, '/app/src')

async def init_v2():
    try:
        print('🚀 启动 Football Prediction System v2.0')
        print('=' * 50)

        # 1. 初始化配置 (v2.0)
        from src.config import get_settings, setup_logging
        setup_logging()

        settings = get_settings()
        print(f'📋 应用: {settings.app.name} v{settings.app.version}')
        print(f'🌍 运行环境: {settings.app.environment}')

        # 2. 初始化数据库连接池
        from src.database.db_pool import init_global_db_pool
        await init_global_db_pool()
        print('✅ 数据库连接池初始化成功')

        # 3. 验证核心模块 (v2.0)
        print('\\n🔍 验证核心模块:')

        # 验证 inference 模块
        try:
            from src.ml.inference.model_loader import ModelLoader
            from src.ml.inference.predictor import MatchPredictor
            print('  ✅ ML Inference 模块加载成功')
        except Exception as e:
            print(f'  ⚠️ ML Inference 模块加载警告: {e}')

        # 验证 services 模块
        try:
            from src.services.inference_service_v2 import InferenceServiceV2
            from src.services.collection_service import CollectionService
            print('  ✅ Services 模块加载成功')
        except Exception as e:
            print(f'  ⚠️ Services 模块加载警告: {e}')

        # 验证数据收集器
        try:
            from src.collectors.enhanced_fotmob_collector import EnhancedFotMobCollector
            print('  ✅ 数据收集器加载成功')
        except Exception as e:
            print(f'  ⚠️ 数据收集器加载警告: {e}')

        # 4. 验证 FastAPI 应用
        try:
            from src.main import app
            print('  ✅ FastAPI 应用加载成功')
        except Exception as e:
            print(f'  ❌ FastAPI 应用加载失败: {e}')
            return False

        print('\\n🎉 应用初始化完成')
        print('=' * 50)
        return True

    except Exception as e:
        print(f'❌ 应用初始化失败: {e}')
        import traceback
        traceback.print_exc()
        return False

# 运行初始化
success = asyncio.run(init_v2())
exit(0 if success else 1)
" || {
        log_error "应用初始化失败"
        exit 1
    }

    log_success "应用初始化完成"
}

# 启动应用
start_application() {
    log_info "启动足球预测系统 v2.0..."

    # 设置默认命令
    if [[ $# -eq 0 ]]; then
        set -- python -m uvicorn src.main:app --host 0.0.0.0 --port 8000
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

async def cleanup_resources():
    try:
        # 清理数据库连接池
        from src.database.db_pool import cleanup_global_db_pool
        await cleanup_global_db_pool()
        print('✅ 数据库连接池已清理')

        # 清理推理服务
        try:
            from src.services.inference_service_v2 import inference_service_v2
            if hasattr(inference_service_v2, 'shutdown'):
                inference_service_v2.shutdown()
                print('✅ 推理服务已关闭')
        except:
            pass

        print('🧹 应用资源清理完成')

    except Exception as e:
        print(f'⚠️ 清理过程中出现警告: {e}')

asyncio.run(cleanup_resources())
"

    log_success "清理完成，退出应用"
    exit 0
}

# 健康检查
health_check() {
    log_info "执行健康检查..."

    python -c "
import asyncio
import sys
sys.path.insert(0, '/app/src')

async def check_health():
    try:
        # 检查数据库连接
        from src.database.db_pool import get_db_pool
        pool = get_db_pool()
        if pool:
            async with pool.acquire() as conn:
                await conn.fetchval('SELECT 1')
            print('✅ 数据库连接正常')
        else:
            print('❌ 数据库连接池未初始化')
            return False

        # 检查核心模块
        from src.main import app
        print('✅ FastAPI 应用正常')

        return True

    except Exception as e:
        print(f'❌ 健康检查失败: {e}')
        return False

result = asyncio.run(check_health())
exit(0 if result else 1)
" || {
        log_error "健康检查失败"
        exit 1
    }

    log_success "健康检查通过"
}

# 主函数
main() {
    log_info "🐳 Football Prediction System v2.0 容器启动"
    log_info "=============================================="

    # 设置信号处理
    trap cleanup SIGTERM SIGINT

    # 检查环境变量
    check_environment_variables

    # 等待数据库就绪
    wait_for_database

    # 运行数据库迁移
    run_database_migrations

    # 初始化应用
    initialize_application

    # 根据参数执行不同操作
    case "${1:-}" in
        "health")
            health_check
            ;;
        "migrate")
            run_database_migrations
            ;;
        *)
            start_application "$@"
            ;;
    esac
}

# 执行主函数
main "$@"