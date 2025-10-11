#!/bin/bash
# 快速 MyPy 错误修复脚本
# Quick MyPy Error Fix Script
#
# 这是一个便捷的包装脚本，提供常用修复选项

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# 显示帮助信息
show_help() {
    cat << EOF
快速 MyPy 错误修复脚本

用法:
    $0 [选项] [模块]

选项:
    -h, --help      显示此帮助信息
    -d, --dry-run   试运行模式，不修改文件
    -q, --quick     快速模式，只修复最常见的错误
    -a, --all       修复所有模块（默认只修复 src）

模块:
    要修复的模块路径（默认: src）

示例:
    $0                    # 修复 src 目录
    $0 -d                # 试运行模式
    $0 src/api          # 修复特定模块
    $0 -q src/core      # 快速修复核心模块
    $0 -d --all         # 试运行所有模块

EOF
}

# 解析命令行参数
DRY_RUN=""
MODULE="src"
QUICK_MODE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -d|--dry-run)
            DRY_RUN="--dry-run"
            shift
            ;;
        -q|--quick)
            QUICK_MODE="--quick"
            shift
            ;;
        -a|--all)
            MODULE="src"
            shift
            ;;
        -*)
            print_error "未知选项: $1"
            show_help
            exit 1
            ;;
        *)
            MODULE="$1"
            shift
            ;;
    esac
done

# 检查脚本是否存在
SCRIPT_PATH="scripts/fix_mypy_errors.py"
if [[ ! -f "$SCRIPT_PATH" ]]; then
    print_error "找不到修复脚本: $SCRIPT_PATH"
    exit 1
fi

# 显示执行信息
print_info "开始 MyPy 错误修复..."
if [[ -n "$DRY_RUN" ]]; then
    print_warning "试运行模式 - 不会修改任何文件"
fi
print_info "目标模块: $MODULE"

# 执行修复
if python "$SCRIPT_PATH" $DRY_RUN --module "$MODULE"; then
    print_success "修复完成！"

    # 显示报告位置
    LATEST_REPORT=$(ls -t scripts/cleanup/mypy_fix_report_*.md 2>/dev/null | head -1)
    if [[ -n "$LATEST_REPORT" ]]; then
        print_info "详细报告: $LATEST_REPORT"
    fi

    # 建议下一步操作
    print_info "建议运行 'make lint' 检查其他代码质量问题"
else
    print_error "修复失败，请检查错误信息"
    exit 1
fi
