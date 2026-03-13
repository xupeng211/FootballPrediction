#!/bin/bash
# =============================================================================
# TITAN Archive Legacy Script
# =============================================================================
# Description: 清理和归档废弃/半成品的采集组件，保持 scripts/ 目录纯净
# Version: 1.0.0
# Usage: ./scripts/ops/archive_legacy.sh [--dry-run]
# =============================================================================

set -euo pipefail

# 颜色定义
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly NC='\033[0m' # No Color

# 项目根目录
readonly PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
readonly ARCHIVE_DIR="${PROJECT_ROOT}/archive/scripts"
readonly SOURCE_DIR="${PROJECT_ROOT}/scripts"

# 需要归档的文件列表（相对于 scripts/ 目录）
readonly LEGACY_FILES=(
    # 旧版采集脚本（已被 V3 版本替代）
    "capture_auth_v2.js"
    "capture_auth_v3.js"
    
    # 临时测试脚本
    "test_gui.js"
    "import_manual_cookies.js"
    "inject_total_war_cookies.js"
)

# =============================================================================
# 函数定义
# =============================================================================

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

show_banner() {
    echo ""
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║          TITAN Archive Legacy Script v1.0                    ║"
    echo "║          废弃组件归档工具                                    ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo ""
}

show_help() {
    cat << EOF
用法: $0 [选项]

选项:
    --dry-run    模拟运行，仅显示将要归档的文件，不实际移动
    --help       显示此帮助信息

说明:
    此脚本将废弃/半成品的采集组件从 scripts/ 移动到 archive/scripts/ 目录，
    保持项目根目录的整洁。归档的文件仍可追溯，但不再出现在主目录。

EOF
}

# =============================================================================
# 主逻辑
# =============================================================================

main() {
    local dry_run=false
    
    # 解析参数
    for arg in "$@"; do
        case $arg in
            --dry-run)
                dry_run=true
                shift
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            *)
                log_error "未知参数: $arg"
                show_help
                exit 1
                ;;
        esac
    done
    
    show_banner
    
    # 检查归档目录是否存在
    if [[ ! -d "$ARCHIVE_DIR" ]]; then
        log_info "创建归档目录: $ARCHIVE_DIR"
        if [[ "$dry_run" == false ]]; then
            mkdir -p "$ARCHIVE_DIR"
        fi
    fi
    
    local archived_count=0
    local skipped_count=0
    
    echo "扫描废弃文件..."
    echo "----------------------------------------"
    
    for file in "${LEGACY_FILES[@]}"; do
        local source_path="${SOURCE_DIR}/${file}"
        local target_path="${ARCHIVE_DIR}/${file}"
        
        if [[ -f "$source_path" ]]; then
            if [[ "$dry_run" == true ]]; then
                echo "[DRY-RUN] 将归档: $file"
                ((archived_count++))
            else
                # 检查目标是否已存在
                if [[ -f "$target_path" ]]; then
                    log_warn "目标已存在，跳过: $file"
                    ((skipped_count++))
                else
                    mv "$source_path" "$target_path"
                    log_info "已归档: $file"
                    ((archived_count++))
                fi
            fi
        else
            log_warn "文件不存在: $file"
        fi
    done
    
    echo "----------------------------------------"
    
    if [[ "$dry_run" == true ]]; then
        echo ""
        log_info "模拟运行完成"
        echo "将要归档的文件数: $archived_count"
        echo ""
        echo "提示: 去掉 --dry-run 参数以实际执行归档"
    else
        echo ""
        log_info "归档完成"
        echo "已归档: $archived_count 个文件"
        echo "已跳过: $skipped_count 个文件"
        echo ""
        echo "归档位置: $ARCHIVE_DIR"
    fi
}

# 执行主函数
main "$@"
