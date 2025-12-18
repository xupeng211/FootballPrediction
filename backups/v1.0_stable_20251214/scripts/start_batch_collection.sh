#!/bin/bash

# FotMob 批量采集启动脚本
# FotMob Batch Collection Startup Script

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
    log_info "检查Python环境..."

    # 检查虚拟环境
    if [[ -z "$VIRTUAL_ENV" ]]; then
        log_warning "未激活虚拟环境，建议先激活"
        log_info "运行: source venv/bin/activate"
    else
        log_success "虚拟环境已激活: $VIRTUAL_ENV"
    fi

    # 检查Python版本
    python_version=$(python --version 2>&1)
    log_info "Python版本: $python_version"

    # 检查关键依赖
    log_info "检查关键依赖..."

    dependencies=("src.collectors.enhanced_fotmob_collector" "src.data.collectors.fotmob_details_collector" "src.database.async_manager")

    for dep in "${dependencies[@]}"; do
        if python -c "import $dep" 2>/dev/null; then
            log_success "✓ $dep"
        else
            log_error "✗ $dep 导入失败"
            log_info "请运行: pip install -r requirements.txt"
            exit 1
        fi
    done
}

# 检查目录结构
check_directories() {
    log_info "检查目录结构..."

    directories=("scripts" "data" "logs")

    for dir in "${directories[@]}"; do
        if [[ ! -d "$dir" ]]; then
            log_info "创建目录: $dir"
            mkdir -p "$dir"
        fi
    done

    # 创建批量采集专用目录
    batch_dirs=("data/batch_cache" "logs/batch_collection")
    for dir in "${batch_dirs[@]}"; do
        if [[ ! -d "$dir" ]]; then
            log_info "创建批量采集目录: $dir"
            mkdir -p "$dir"
        fi
    done

    log_success "目录结构检查完成"
}

# 检查环境变量
check_environment() {
    log_info "检查环境变量..."

    # 数据库URL
    if [[ -z "$DATABASE_URL" ]]; then
        log_warning "DATABASE_URL 未设置，将使用默认配置"
    else
        log_success "DATABASE_URL: ${DATABASE_URL:0:20}..."
    fi

    # 代理配置
    if [[ -n "$PROXY_LIST" ]]; then
        log_success "代理配置已设置: ${PROXY_LIST:0:30}..."
    else
        log_info "未配置代理，将使用直连"
    fi
}

# 检查脚本文件
check_script_file() {
    script_path="scripts/run_batch_collection.py"

    if [[ ! -f "$script_path" ]]; then
        log_error "采集脚本不存在: $script_path"
        exit 1
    fi

    log_success "采集脚本检查通过: $script_path"
}

# 检查数据库连接
check_database_connection() {
    log_info "测试数据库连接..."

    if python -c "
import asyncio
import sys
try:
    from src.database.async_manager import initialize_database
    asyncio.run(initialize_database())
    print('✅ 数据库连接成功')
except Exception as e:
    print(f'❌ 数据库连接失败: {e}')
    sys.exit(1)
" 2>/dev/null; then
        log_success "数据库连接测试通过"
    else
        log_warning "数据库连接测试失败，将使用文件缓存"
    fi
}

# 显示配置信息
show_configuration() {
    echo ""
    log_info "=== 批量采集配置信息 ==="
    echo "📅 采集范围: 过去30天"
    echo "🏆 目标联赛: 五大联赛 (英超、西甲、德甲、意甲、法甲)"
    echo "📁 输出目录: data/batch_cache/"
    echo "📄 日志目录: logs/batch_collection/"
    echo "⚙️ 断点续传: 启用"
    echo "🔄 错误重试: 3次"
    echo "⏱️ 延迟控制: 自适应"
    echo ""
}

# 启动采集
start_collection() {
    local mode="$1"

    log_info "启动FotMob批量采集..."

    case "$mode" in
        "foreground")
            log_info "前台运行模式"
            python scripts/run_batch_collection.py
            ;;
        "background")
            log_info "后台运行模式"
            log_info "日志文件: logs/batch_collection.log"

            # 检查是否已有进程在运行
            if pgrep -f "run_batch_collection.py" > /dev/null; then
                log_warning "检测到已有采集进程在运行"
                log_info "进程列表:"
                ps aux | grep run_batch_collection.py | grep -v grep
                read -p "是否要强制停止现有进程? (y/N): " -n 1 -r
                echo
                if [[ $REPLY =~ ^[Yy]$ ]]; then
                    pkill -f "run_batch_collection.py"
                    log_success "已停止现有进程"
                    sleep 2
                else
                    log_info "退出启动"
                    exit 0
                fi
            fi

            # 启动后台进程
            nohup python scripts/run_batch_collection.py > logs/batch_collection.log 2>&1 &
            local pid=$!

            log_success "后台采集已启动"
            log_info "进程ID: $pid"
            log_info "查看日志: tail -f logs/batch_collection.log"
            log_info "停止进程: pkill -f 'run_batch_collection.py'"
            ;;
        "tmux")
            log_info "Tmux会话模式"

            session_name="fotmob_batch"

            # 检查会话是否存在
            if tmux has-session -t "$session_name" 2>/dev/null; then
                log_warning "Tmux会话 '$session_name' 已存在"
                read -p "是否要附加到现有会话? (y/N): " -n 1 -r
                echo
                if [[ $REPLY =~ ^[Yy]$ ]]; then
                    tmux attach-session -t "$session_name"
                    exit 0
                else
                    read -p "是否要删除现有会话并重新创建? (y/N): " -n 1 -r
                    echo
                    if [[ $REPLY =~ ^[Yy]$ ]]; then
                        tmux kill-session -t "$session_name"
                    else
                        log_info "退出启动"
                        exit 0
                    fi
                fi
            fi

            # 创建新会话
            tmux new-session -d -s "$session_name" "python scripts/run_batch_collection.py"

            log_success "Tmux会话已创建: $session_name"
            log_info "附加会话: tmux attach-session -t $session_name"
            log_info "查看会话: tmux list-sessions"
            log_info "分离会话: Ctrl+B 然后按 D"
            ;;
        *)
            log_error "未知的运行模式: $mode"
            show_usage
            exit 1
            ;;
    esac
}

# 显示使用帮助
show_usage() {
    echo "使用方法:"
    echo "  $0 [运行模式]"
    echo ""
    echo "运行模式:"
    echo "  foreground  前台运行 (默认)"
    echo "  background  后台运行"
    echo "  tmux        使用tmux会话运行"
    echo ""
    echo "示例:"
    echo "  $0              # 前台运行"
    echo "  $0 background   # 后台运行"
    echo "  $0 tmux         # tmux会话运行"
    echo ""
    echo "监控命令:"
    echo "  查看日志:     tail -f logs/batch_collection.log"
    echo "  查看进度:     cat data/batch_cache/progress.json | python -m json.tool"
    echo "  停止采集:     pkill -f 'run_batch_collection.py'"
}

# 主函数
main() {
    echo "🚀 FotMob 批量采集启动脚本"
    echo "================================"

    # 解析参数
    local mode="${1:-foreground}"

    # 检查模式参数
    if [[ "$mode" == "--help" ]] || [[ "$mode" == "-h" ]]; then
        show_usage
        exit 0
    fi

    # 系统检查
    check_project_directory
    check_python_environment
    check_directories
    check_environment
    check_script_file
    check_database_connection

    # 显示配置
    show_configuration

    # 确认启动
    read -p "确认开始批量采集? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "用户取消启动"
        exit 0
    fi

    # 启动采集
    start_collection "$mode"
}

# 信号处理
trap 'log_warning "脚本被中断"; exit 1' INT TERM

# 运行主函数
main "$@"