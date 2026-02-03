#!/bin/bash
# [Genesis.CleanSweep] src 目录清理脚本
# ================================================
#
# 功能：执行遗留代码归档和目录清理
# 使用：./scripts/ops/genesis_cleanup.sh --dry-run (先预览)
#       ./scripts/ops/genesis_cleanup.sh --execute (执行清理)
#
# 作者：[Genesis.FinalCleanSweep]
# 日期：2026-02-03
# 版本：V1.0.0

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_header() {
    echo -e "${BLUE}============================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}============================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# ============================================================================
# 命令行参数
# ============================================================================

DRY_RUN=false
EXECUTE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --execute)
            EXECUTE=true
            shift
            ;;
        *)
            print_error "Unknown option: $1"
            echo "Usage: $0 [--dry-run] [--execute]"
            exit 1
            ;;
    esac
done

if [ "$DRY_RUN" = false ] && [ "$EXECUTE" = false ]; then
    print_error "Please specify either --dry-run or --execute"
    exit 1
fi

# ============================================================================
# 创建归档目录
# ============================================================================

ARCHIVE_DIR="archive/legacy"
mkdir -p "$ARCHIVE_DIR"

# ============================================================================
# 高优先级迁移文件（6 个）
# ============================================================================

print_header "Phase 1: High Priority Migration"

HIGH_PRIORITY_FILES=(
    "src/core/proxy/__init___DEPRECATED.py"
    "src/core/proxy/proxy_manager.py"
    "src/core/proxy/proxy_guardian.py"
    "src/core/proxy/proxy_health_checker.py"
    "src/collectors/proxy_health_manager.py"
    "src/scrapers/proxy_manager.py"
)

for file in "${HIGH_PRIORITY_FILES[@]}"; do
    if [ -f "$file" ]; then
        if [ "$EXECUTE" = true ]; then
            mkdir -p "$ARCHIVE_DIR/$(dirname $file)"
            mv "$file" "$ARCHIVE_DIR/$file"
            print_success "Archived: $file"
        else
            print_warning "[DRY RUN] Would archive: $file"
        fi
    else
        print_warning "[SKIP] File not found: $file"
    fi
done

# ============================================================================
# 中优先级整合文件（15 个）
# ============================================================================

print_header "Phase 2: Medium Priority Reorganization"

MEDIUM_PRIORITY_FILES=(
    "src/collectors/circuit_breaker.py"
    "src/collectors/resilience.py"
    "src/collectors/rollback_manager.py"
    "src/collectors/odds_api_client.py"
    "src/collectors/odds_api_interceptor.py"
    "src/collectors/odds_models.py"
    "src/collectors/prometheus_metrics.py"
    "src/collectors/js_templates.py"
    "src/collectors/metadata_manager.py"
    "src/collectors/season_manifest_generator.py"
    "src/collectors/fotmob_league_registry.py"
    "src/collectors/fotmob_historical_id_scanner.py"
    "src/collectors/semantic_matcher.py"
    "src/collectors/semantic_refiner.py"
    "src/collectors/levenshtein_matcher.py"
)

# 创建目标目录
TARGET_DIRS=(
    "src/api/models"
    "src/api/monitoring"
    "src/infrastructure/engines/selectors"
    "src/config"
    "src/utils"
)

for dir in "${TARGET_DIRS[@]}"; do
    mkdir -p "$dir"
done

for file in "${MEDIUM_PRIORITY_FILES[@]}"; do
    if [ -f "$file" ]; then
        if [ "$EXECUTE" = true ]; then
            # 根据文件类型移动到相应目录
            case "$file" in
                *odds_models.py)
                    mkdir -p "src/api/models"
                    mv "$file" "src/api/models/"
                    print_success "Moved: $file → src/api/models/"
                    ;;
                *prometheus_metrics.py)
                    mkdir -p "src/api/monitoring"
                    mv "$file" "src/api/monitoring/"
                    print_success "Moved: $file → src/api/monitoring/"
                    ;;
                *js_templates.py)
                    mkdir -p "src/infrastructure/engines/selectors"
                    mv "$file" "src/infrastructure/engines/selectors/"
                    print_success "Moved: $file → src/infrastructure/engines/selectors/"
                    ;;
                *metadata_manager.py|*league_registry.py|*manifest_generator.py)
                    mkdir -p "src/config/league"
                    mv "$file" "src/config/league/"
                    print_success "Moved: $file → src/config/league/"
                    ;;
                *semantic_matcher.py|*semantic_refiner.py|*levenshtein_matcher.py)
                    mv "$file" "src/utils/"
                    print_success "Moved: $file → src/utils/"
                    ;;
                *)
                    mkdir -p "$ARCHIVE_DIR/$(dirname $file)"
                    mv "$file" "$ARCHIVE_DIR/$file"
                    print_success "Archived: $file"
                    ;;
            esac
        else
            print_warning "[DRY RUN] Would reorganize: $file"
        fi
    fi
done

# ============================================================================
# 低优先级归档目录
# ============================================================================

print_header "Phase 3: Low Priority Archival"

LOW_PRIORITY_DIRS=(
    "src/bridge"
    "src/analysis"
    "src/modules"
)

for dir in "${LOW_PRIORITY_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        if [ "$EXECUTE" = true ]; then
            mkdir -p "$ARCHIVE_DIR/$dir"
            mv "$dir" "$ARCHIVE_DIR/$dir"
            print_success "Archived directory: $dir"
        else
            print_warning "[DRY RUN] Would archive: $dir"
        fi
    fi
done

# ============================================================================
# 创建 README 说明
# ============================================================================

if [ "$EXECUTE" = true ]; then
    cat > "$ARCHIVE_DIR/README.md" << 'EOF'
# Legacy Archive - [Genesis.CleanSweep]

本目录包含已归档的遗留代码，不再使用于生产环境。

## 归档日期
2026-02-03

## 归档原因

### 代理系统 (src/core/proxy/)
- 被 NetworkShield V1.1.0 替代
- 缺乏跨语言状态同步
- 熔断器实现碎片化

### 重复采集器 (src/scrapers/proxy_manager.py)
- 功能与 NetworkShield 重复
- 维护成本高

### 旧架构目录
- src/bridge/: 旧桥接层
- src/analysis/: 空目录
- src/modules/: JavaScript 模块已迁移

## 迁移路径

详见 CLAUDE.md 中的 [Genesis.CleanSweep] 审计报告。
EOF
    print_success "Created archive README"
fi

# ============================================================================
# 总结报告
# ============================================================================

print_header "Cleanup Summary"

if [ "$EXECUTE" = true ]; then
    echo -e "${GREEN}Cleanup complete!${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Update imports in affected files"
    echo "  2. Run tests: make verify"
    echo "  3. Update CLAUDE.md with new structure"
else
    echo -e "${YELLOW}Dry run complete!${NC}"
    echo ""
    echo "To execute the cleanup, run:"
    echo "  ./scripts/ops/genesis_cleanup.sh --execute"
fi

echo ""
echo -e "${BLUE}[Genesis.CleanSweep] AUDIT COMPLETE. 23 files marked for legacy. Merger logic READY. Ready for the final click?${NC}"
