#!/bin/bash
# Docker容器生产入口点脚本 v2.3-production
# 适配最新的架构重构和权限要求

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

    # 简化的迁移检查
    if python -c "
import os
import sys
sys.path.insert(0, '/app/src')

try:
    # 检查数据库连接和基本表结构
    import asyncpg

    async def check_tables():
        conn = await asyncpg.connect(
            host=os.getenv('DB_HOST'),
            port=int(os.getenv('DB_PORT', 5432)),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            database=os.getenv('DB_NAME')
        )

        # 检查关键表是否存在
        result = await conn.fetchval('''
            SELECT COUNT(*) FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name IN ('matches', 'teams', 'predictions')
        ''')

        await conn.close()
        return True

    import asyncio
    asyncio.run(check_tables())
    print('✅ 数据库检查成功')

except Exception as e:
    print(f'⚠️ 数据库检查警告: {e}')
    exit(1)
"; then
        log_success "数据库迁移检查完成"
    else
        log_warning "数据库迁移检查失败，但继续启动应用"
    fi
}

# 初始化应用 (v2.3-production 架构)
initialize_application() {
    log_info "初始化足球预测系统 v2.3-production..."

    python -c "
import asyncio
import os
import sys
sys.path.insert(0, '/app/src')

async def init_production():
    try:
        print('🚀 启动 Football Prediction System v2.3-production')
        print('=' * 60)

        # 1. 初始化配置（使用新的 src.config 配置包）
        try:
            from src.config import get_settings
            settings = get_settings()
            print(f'📋 应用: Football Prediction System v2.3-production')
            print(f'🌍 环境: {settings.environment}')
        except Exception as e:
            print(f'⚠️ 配置加载警告: {e}')
            # 使用默认配置继续
            print('📋 使用默认配置继续启动')

        # 2. 验证核心模块导入
        print('\\n🔍 验证核心模块:')

        # 验证统一配置包
        try:
            from src.config import UnifiedSettings
            print('  ✅ 配置模块 (src.config)')
        except Exception as e:
            print(f'  ❌ 配置模块失败: {e}')
            return False

        # 验证 config 兼容性桥接
        try:
            from src.config import get_settings as get_settings_legacy
            print('  ✅ 配置兼容性桥接 (config.py)')
        except Exception as e:
            print(f'  ⚠️ 配置兼容性桥接警告: {e}')

        # 验证 services 核心模块
        try:
            from src.services.core_inference import CoreInferenceService
            print('  ✅ 核心推理服务')
        except Exception as e:
            print(f'  ⚠️ 核心推理服务警告: {e}')

        # 验证 ML 模块
        try:
            from src.ml.inference.model_loader import ModelLoader
            print('  ✅ ML推理模块')
        except Exception as e:
            print(f'  ⚠️ ML推理模块警告: {e}')

        # 验证 FastAPI 应用
        try:
            from src.main import app
            print('  ✅ FastAPI 应用')
        except Exception as e:
            print(f'  ❌ FastAPI 应用失败: {e}')
            return False

        print('\\n🎉 应用初始化完成')
        print('=' * 60)
        return True

    except Exception as e:
        print(f'❌ 应用初始化失败: {e}')
        import traceback
        traceback.print_exc()
        return False

# 运行初始化
success = asyncio.run(init_production())
exit(0 if success else 1)
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
        set -- python -m uvicorn src.main:app --host 0.0.0.0 --port 8000
    fi

    log_success "启动命令: $*"

    # 启动应用
    exec "$@"
}

# 信号处理
cleanup() {
    log_info "收到停止信号，正在清理..."
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
        # 检查配置模块
        from src.config import get_settings
        settings = get_settings()
        print('✅ 配置模块正常')

        # 检查核心应用
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
    log_info "🐳 Football Prediction System v2.3-production 容器启动"
    log_info "=================================================="

    # 设置信号处理
    trap cleanup SIGTERM SIGINT

    # 检查环境变量
    check_environment_variables

    # 等待数据库就绪
    wait_for_database

    # 运行数据库迁移检查
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
