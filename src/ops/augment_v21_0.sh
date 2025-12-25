#!/bin/bash
# ============================================================================
# V21.0 增量特征补完启动脚本
# ============================================================================
#
# 功能: 在不中断 Docker 收割进程的前提下，增量升级数据库记录
#
# 使用方法:
#   ./augment_v21_0.sh [选项]
#
# 环境变量:
#   DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
#   或者使用 .env 文件
#
# 选项:
#   --dry-run     演练模式（不实际更新数据库）
#   --batch-size  批量处理大小（默认: 50）
#   --no-referee  禁用裁判因子
#   --no-context  禁用上下文因子
#
# 作者: FootballPrediction Architecture Team
# 版本: V21.0-deep-blowout
# ============================================================================

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

# 打印横幅
print_banner() {
    echo ""
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║     V21.0 增量特征补完脚本 (Surgical Feature Augmentor)     ║"
    echo "║                                                              ║"
    echo "║  在不中断 Docker 收割进程的前提下，将数据库记录从 V20.8    ║"
    echo "║  无损升级至 V21.0 (881维 → 900+维)                          ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo ""
}

# 检查环境变量
check_env() {
    log_info "检查环境变量..."

    if [ -f .env ]; then
        log_info "加载 .env 文件..."
        export $(cat .env | grep -v '^#' | xargs)
    fi

    # 检查必需的环境变量
    if [ -z "$DB_PASSWORD" ]; then
        log_error "DB_PASSWORD 环境变量未设置"
        log_info "请设置环境变量或创建 .env 文件"
        exit 1
    fi

    log_success "环境变量检查通过"
}

# 检查依赖
check_dependencies() {
    log_info "检查依赖..."

    # 检查 Python
    if ! command -v python3 &> /dev/null; then
        log_error "Python3 未安装"
        exit 1
    fi

    # 检查必要的 Python 包
    python3 -c "import psycopg2, pydantic" 2>/dev/null || {
        log_error "缺少必要的 Python 包"
        log_info "运行: pip install psycopg2-binary pydantic"
        exit 1
    }

    log_success "依赖检查通过"
}

# 检查数据库连接
check_database() {
    log_info "检查数据库连接..."

    python3 -c "
import psycopg2
import os
from psycopg2.extras import RealDictCursor

try:
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=int(os.getenv('DB_PORT', 5432)),
        database=os.getenv('DB_NAME', 'football_db'),
        user=os.getenv('DB_USER', 'football_user'),
        password=os.getenv('DB_PASSWORD'),
        cursor_factory=RealDictCursor
    )

    with conn.cursor() as cur:
        cur.execute('SELECT COUNT(*) as cnt FROM match_features_training')
        count = cur.fetchone()['cnt']
        print(f'数据库连接成功，当前记录数: {count}')

    conn.close()
except Exception as e:
    print(f'数据库连接失败: {e}')
    exit(1)
" || exit 1

    log_success "数据库连接正常"
}

# 解析命令行参数
parse_args() {
    ARGS=""

    while [[ $# -gt 0 ]]; do
        case $1 in
            --dry-run)
                ARGS="$ARGS --dry-run"
                log_warning "启用演练模式（不会实际更新数据库）"
                shift
                ;;
            --batch-size=*)
                BATCH_SIZE="${1#*=}"
                ARGS="$ARGS --batch-size $BATCH_SIZE"
                log_info "批量大小设置为: $BATCH_SIZE"
                shift
                ;;
            --no-referee)
                ARGS="$ARGS --no-referee"
                log_warning "禁用裁判因子"
                shift
                ;;
            --no-context)
                ARGS="$ARGS --no-context"
                log_warning "禁用上下文因子"
                shift
                ;;
            *)
                log_error "未知选项: $1"
                echo "使用方法: $0 [--dry-run] [--batch-size=N] [--no-referee] [--no-context]"
                exit 1
                ;;
        esac
    done
}

# 运行补完脚本
run_augmentation() {
    log_info "启动 V21.0 增量特征补完..."

    # 创建日志目录
    mkdir -p logs

    # 运行脚本
    python3 src/ops/augment_v21_0_surgical.py $ARGS

    # 捕获退出码
    EXIT_CODE=$?

    if [ $EXIT_CODE -eq 0 ]; then
        log_success "V21.0 增量特征补完完成！"
    else
        log_error "V21.0 增量特征补完失败（退出码: $EXIT_CODE）"
        exit $EXIT_CODE
    fi
}

# ============================================================================
# 主程序
# ============================================================================

main() {
    print_banner
    check_env
    check_dependencies
    check_database
    parse_args "$@"
    run_augmentation
}

# 捕获中断信号
trap 'log_warning "用户中断"; exit 130' INT

# 运行主程序
main "$@"
