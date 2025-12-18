#!/bin/bash
# Titan007 生产环境部署脚本

set -e  # 遇到错误立即退出

echo "🚀 开始 Titan007 生产环境部署..."

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查前置条件
check_prerequisites() {
    log_info "检查部署前置条件..."

    # 检查 Python 环境
    if ! command -v python3 &> /dev/null; then
        log_error "Python3 未安装"
        exit 1
    fi

    # 检查虚拟环境
    if [ -z "$VIRTUAL_ENV" ]; then
        log_error "请先激活虚拟环境: source venv/bin/activate"
        exit 1
    fi

    # 检查环境变量文件
    if [ ! -f ".env" ]; then
        log_warn ".env 文件不存在，使用模板创建..."
        cp .env.template .env
        log_warn "请编辑 .env 文件配置生产环境参数"
        exit 1
    fi

    log_info "✅ 前置条件检查通过"
}

# 运行数据库迁移
run_migrations() {
    log_info "运行数据库迁移..."

    # 备份当前数据库状态
    log_info "备份当前数据库状态..."
    alembic current --verbose > /tmp/alembic_current_backup.txt

    # 运行迁移
    log_info "执行数据库迁移..."
    alembic upgrade head

    # 验证迁移结果
    log_info "验证迁移结果..."
    alembic current --verbose

    log_info "✅ 数据库迁移完成"
}

# 验证配置
validate_config() {
    log_info "验证配置文件..."

    # 验证数据库连接
    python3 -c "
from src.database.async_manager import get_database_manager
import asyncio

async def test_db():
    try:
        manager = get_database_manager()
        status = await manager.check_connection()
        if status['status'] != 'healthy':
            print(f'数据库连接失败: {status}')
            exit(1)
        print('✅ 数据库连接正常')
    except Exception as e:
        print(f'数据库连接异常: {e}')
        exit(1)

asyncio.run(test_db())
"

    # 验证 Titan 配置
    python3 -c "
from src.config.titan_settings import get_titan_settings

try:
    settings = get_titan_settings()
    print(f'✅ Titan 配置验证通过')
    print(f'   - Base URL: {settings.titan.base_url}')
    print(f'   - Max Retries: {settings.titan.max_retries}')
    print(f'   - Timeout: {settings.titan.timeout}s')
    print(f'   - DB Pool Size: {settings.db_pool.pool_size}')
except Exception as e:
    print(f'配置验证失败: {e}')
    exit(1)
"

    log_info "✅ 配置验证完成"
}

# 运行集成测试
run_integration_tests() {
    log_info "运行集成测试..."

    # 运行 Titan007 双表架构测试
    python3 test_titan_odds_db.py --use-real-db

    log_info "✅ 集成测试通过"
}

# 部署健康检查
health_check() {
    log_info "执行部署后健康检查..."

    # 检查进程
    if pgrep -f "titan" > /dev/null; then
        log_info "✅ Titan 进程运行正常"
    else
        log_warn "未检测到 Titan 进程"
    fi

    # 检查端口
    if netstat -tuln | grep -q ":8000 "; then
        log_info "✅ API 服务端口 8000 正常监听"
    else
        log_warn "API 服务端口 8000 未监听"
    fi

    log_info "✅ 健康检查完成"
}

# 主部署流程
main() {
    echo "=============================================="
    echo "🎯 Titan007 生产环境部署脚本"
    echo "=============================================="

    check_prerequisites
    validate_config
    run_migrations
    run_integration_tests
    health_check

    echo "=============================================="
    log_info "🎉 Titan007 生产环境部署完成！"
    echo "=============================================="
    echo ""
    echo "📋 部署后检查清单:"
    echo "1. ✅ 数据库迁移已执行"
    echo "2. ✅ 配置文件已验证"
    echo "3. ✅ 集成测试已通过"
    echo "4. ✅ 健康检查已执行"
    echo ""
    echo "🚀 下一步操作:"
    echo "1. 启动数据采集调度器"
    echo "2. 配置监控告警"
    echo "3. 验证数据采集功能"
    echo ""
}

# 错误处理
trap 'log_error "部署过程中发生错误，请检查日志"; exit 1' ERR

# 执行主流程
main "$@"