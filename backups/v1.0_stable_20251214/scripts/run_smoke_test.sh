#!/bin/bash

# FotMob 冒烟测试启动脚本
# FotMob Smoke Test Startup Script

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
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

log_step() {
    echo -e "${PURPLE}[STEP]${NC} $1"
}

# 检查Docker服务
check_docker_services() {
    log_step "检查Docker服务状态..."

    # 检查docker是否运行
    if ! docker info > /dev/null 2>&1; then
        log_error "Docker服务未运行"
        log_info "请启动Docker服务"
        exit 1
    fi

    # 检查PostgreSQL容器
    db_container=$(docker ps -q --filter "name=postgres" --filter "status=running")
    if [[ -z "$db_container" ]]; then
        log_error "PostgreSQL容器未运行"
        log_info "启动命令: docker-compose up -d db"
        exit 1
    fi

    log_success "Docker服务检查通过"
    log_info "PostgreSQL容器: ${db_container:0:12}..."
}

# 检查项目目录
check_project_directory() {
    if [[ ! -f "CLAUDE.md" ]]; then
        log_error "请在项目根目录运行此脚本"
        exit 1
    fi
    log_success "项目目录检查通过"
}

# 检查Python环境
check_python_environment() {
    log_step "检查Python环境..."

    # 检查Python
    if ! command -v python &> /dev/null; then
        log_error "Python未安装或不在PATH中"
        exit 1
    fi

    python_version=$(python --version 2>&1)
    log_info "Python版本: $python_version"

    # 检查关键模块
    modules=(
        "src.collectors.enhanced_fotmob_collector"
        "src.data.collectors.fotmob_details_collector"
        "src.database.async_manager"
        "sqlalchemy"
    )

    for module in "${modules[@]}"; do
        if python -c "import $module" 2>/dev/null; then
            log_success "✓ $module"
        else
            log_error "✗ $module 导入失败"
            log_info "请检查虚拟环境和依赖安装"
            exit 1
        fi
    done
}

# 检查数据库连接
check_database_connection() {
    log_step "检查数据库连接..."

    if python -c "
import asyncio
import sys
try:
    from src.database.async_manager import get_db_session
    from sqlalchemy import text
    async def test():
        async with get_db_session() as session:
            result = await session.execute(text('SELECT 1'))
            print('✅ 数据库连接成功')
    asyncio.run(test())
except Exception as e:
    print(f'❌ 数据库连接失败: {e}')
    sys.exit(1)
" 2>/dev/null; then
        log_success "数据库连接正常"
    else
        log_error "数据库连接失败"
        log_info "请检查PostgreSQL容器是否正常运行"
        exit 1
    fi
# 检查表结构
check_database_schema() {
    log_step "检查数据库表结构..."

    tables_check=$(python -c "
import asyncio
import sys
try:
    from src.database.async_manager import get_db_session
    from sqlalchemy import text
    async def check():
        async with get_db_session() as session:
            result = await session.execute(text('''
                SELECT COUNT(*) FROM information_schema.tables
                WHERE table_schema = \"public\"
                AND table_type = \"BASE TABLE\"
            '''))
            count = result.fetchone()[0]
            print(f'{count}')
    asyncio.run(check())
except Exception as e:
    print('0')
" 2>/dev/null)

    if [[ "$tables_check" -gt "0" ]]; then
        log_success "数据库表结构正常 (发现 $tables_check 张表)"
    else
        log_warning "数据库表为空"
        log_info "提示: 冒烟测试会自动创建临时测试表"
    fi
}

# 运行冒烟测试
run_smoke_test() {
    log_step "运行FotMob冒烟测试..."

    log_info "测试配置:"
    log_info "  📅 采集范围: 过去1天"
    log_info "  🏆 目标联赛: 仅英超 (Premier League)"
    log_info "  ⏱️ 超时时间: 2分钟"
    log_info "  🎯 测试目标: 验证端到端采集流程"

    echo ""

    # 运行冒烟测试
    if python scripts/smoke_test_collection.py; then
        log_success "冒烟测试执行成功"
        return 0
    else
        log_error "冒烟测试执行失败"
        log_error "请查看上方错误信息"
        return 1
    fi
}

# 验证测试结果
verify_results() {
    log_step "验证冒烟测试结果..."

    if python scripts/verify_smoke_test.py; then
        log_success "结果验证成功"
        return 0
    else
        log_warning "结果验证失败或数据不完整"
        log_info "请检查采集日志和数据库状态"
        return 1
    fi
}

# 显示状态摘要
show_status_summary() {
    echo ""
    echo "🚀 FotMob 冒烟测试状态摘要"
    echo "=================================="

    # 检查容器状态
    echo "📦 Docker服务状态:"
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "(postgres|NAMES|health)" || echo "未发现PostgreSQL容器"

    echo ""
    echo "📊 数据库状态:"
    # 检查测试数据
    test_count=$(python -c "
import asyncio
try:
    from src.database.async_manager import get_db_session
    from sqlalchemy import text
    async def check():
        try:
            async with get_db_session() as session:
                result = await session.execute(text('SELECT COUNT(*) FROM smoke_test_results WHERE collection_type = \"smoke_test\"'))
                count = result.fetchone()[0]
                print(count)
        except:
            print(0)
    asyncio.run(check())
except:
    print(0)
" 2>/dev/null || echo "0")

    echo "  冒烟测试数据: $test_count 条记录"

    if [[ "$test_count" -gt "0" ]]; then
        echo "  状态: ✅ 测试数据存在"
    else
        echo "  状态: ❌ 无测试数据"
    fi

    echo ""
    echo "📁 相关文件:"
    echo "  冒烟测试脚本: scripts/smoke_test_collection.py"
    echo "  验证脚本: scripts/verify_smoke_test.py"
    echo "  日志文件: logs/smoke_test.log"
    echo "  测试缓存: data/smoke_test_cache/"

    echo ""
    echo "🔧 下一步操作:"
    if [[ "$test_count" -gt "0" ]]; then
        echo "  ✅ 冒烟测试成功，可以开始全量采集"
        echo "     命令: ./scripts/start_batch_collection.sh"
    else
        echo "  ❌ 冒烟测试失败，请排查问题"
        echo "     重新测试: ./scripts/run_smoke_test.sh"
        echo "     查看日志: tail -f logs/smoke_test.log"
    fi

    echo "=================================="
}

# 清理测试数据
cleanup_test_data() {
    log_step "清理测试数据..."

    read -p "是否要清理冒烟测试数据? (y/N): " -n 1 -r
    echo

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        python -c "
import asyncio
try:
    from src.database.async_manager import get_db_session
    from sqlalchemy import text
    async def cleanup():
        async with get_db_session() as session:
            await session.execute(text('DELETE FROM smoke_test_results WHERE collection_type = \"smoke_test\"'))
            await session.commit()
            print('✅ 测试数据已清理')
    asyncio.run(cleanup())
except Exception as e:
    print(f'❌ 清理失败: {e}')
" 2>/dev/null

        # 清理缓存文件
        if [[ -d "data/smoke_test_cache" ]]; then
            rm -rf data/smoke_test_cache
            echo "✅ 缓存文件已清理"
        fi

        log_success "测试数据清理完成"
    else
        log_info "跳过数据清理"
    fi
}

# 显示使用帮助
show_usage() {
    echo "使用方法:"
    echo "  $0 [选项]"
    echo ""
    echo "选项:"
    echo "  test      运行冒烟测试 (默认)"
    echo "  verify    仅验证已有测试结果"
    echo "  status    显示当前状态"
    echo "  cleanup   清理测试数据"
    echo "  help      显示帮助信息"
    echo ""
    echo "示例:"
    echo "  $0                # 运行完整冒烟测试"
    echo "  $0 test          # 运行冒烟测试"
    echo "  $0 verify        # 验证测试结果"
    echo "  $0 status        # 显示状态摘要"
    echo "  $0 cleanup       # 清理测试数据"
}

# 主函数
main() {
    local action="${1:-test}"

    echo "🔍 FotMob 冒烟测试系统"
    echo "========================"

    case "$action" in
        "test")
            # 系统检查
            check_project_directory
            check_docker_services
            check_python_environment
            check_database_connection
            check_database_schema

            # 运行测试
            echo ""
            log_info "开始执行冒烟测试..."
            if run_smoke_test && verify_results; then
                echo ""
                log_success "🎉 冒烟测试完全成功!"
                show_status_summary
            else
                echo ""
                log_error "❌ 冒烟测试失败"
                show_status_summary
                exit 1
            fi
            ;;
        "verify")
            check_project_directory
            check_python_environment
            check_database_connection
            verify_results
            show_status_summary
            ;;
        "status")
            check_project_directory
            show_status_summary
            ;;
        "cleanup")
            check_project_directory
            check_python_environment
            check_database_connection
            cleanup_test_data
            ;;
        "help"|"-h"|"--help")
            show_usage
            ;;
        *)
            log_error "未知选项: $action"
            echo ""
            show_usage
            exit 1
            ;;
    esac
}

# 运行主函数
main "$@"