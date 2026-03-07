#!/bin/bash
# ============================================================================
# V172 项目清场脚本
# ============================================================================
#
# 用途: 清理历史残留文件，保持项目纯净
#
# 使用方法:
#   ./scripts/maintenance/cleanup_project.sh --dry-run   # 预览模式
#   ./scripts/maintenance/cleanup_project.sh --execute   # 执行清理
#
# ============================================================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 参数检查
DRY_RUN=true
if [[ "$1" == "--execute" ]]; then
    DRY_RUN=false
elif [[ "$1" != "--dry-run" ]]; then
    echo "用法: $0 [--dry-run | --execute]"
    echo ""
    echo "  --dry-run   预览模式，不实际执行 (默认)"
    echo "  --execute   执行实际清理"
    exit 1
fi

echo ""
echo "═══════════════════════════════════════════════════════════════════════════════"
echo "  V172 项目清场脚本"
echo "═══════════════════════════════════════════════════════════════════════════════"
echo ""
echo "  模式: $(if $DRY_RUN; then echo "${YELLOW}预览模式${NC}"; else echo "${RED}执行模式${NC}"; fi)"
echo ""

# ============================================================================
# 创建归档目录
# ============================================================================

create_archive_dirs() {
    mkdir -p archives/v170_legacy_junk
    mkdir -p archives/v171_scripts
    mkdir -p archives/v172_dev
    echo -e "${GREEN}✅ 归档目录已创建${NC}"
}

# ============================================================================
# 1. 归档 V87/V91 历史文件
# ============================================================================

archive_v87_v91() {
    echo ""
    echo -e "${BLUE}📦 归档 V87/V91 历史文件...${NC}"

    local files=(
        "scripts/ops/v87_master_pipeline.js"
        "scripts/ops/v91_000_main.js"
        "scripts/ops/v91_000_config.js"
        "scripts/ops/v91_000_monitor_service.js"
        "scripts/ops/v91_000_parser_engine.js"
    )

    for file in "${files[@]}"; do
        if [[ -f "$file" ]]; then
            if $DRY_RUN; then
                echo -e "  ${YELLOW}[预览]${NC} 将归档: $file"
            else
                mv "$file" archives/v170_legacy_junk/
                echo -e "  ${GREEN}✅${NC} 已归档: $file"
            fi
        fi
    done
}

# ============================================================================
# 2. 归档 V171 脚本
# ============================================================================

archive_v171() {
    echo ""
    echo -e "${BLUE}📦 归档 V171 脚本...${NC}"

    local count=0
    for file in scripts/ops/v171_*.js; do
        if [[ -f "$file" ]]; then
            if $DRY_RUN; then
                echo -e "  ${YELLOW}[预览]${NC} 将归档: $file"
            else
                mv "$file" archives/v171_scripts/
                echo -e "  ${GREEN}✅${NC} 已归档: $file"
            fi
            ((count++))
        fi
    done

    echo -e "  找到 ${count} 个 V171 文件"
}

# ============================================================================
# 3. 归档 legacy_research
# ============================================================================

archive_legacy_research() {
    echo ""
    echo -e "${BLUE}📦 归档 legacy_research 目录...${NC}"

    if [[ -d "scripts/legacy_research" ]]; then
        if $DRY_RUN; then
            local count=$(find scripts/legacy_research -type f | wc -l)
            echo -e "  ${YELLOW}[预览]${NC} 将归档整个目录 ($count 文件)"
        else
            mv scripts/legacy_research archives/v170_legacy_junk/
            echo -e "  ${GREEN}✅${NC} legacy_research 已归档"
        fi
    fi
}

# ============================================================================
# 4. 归档 temporal_sync_engine
# ============================================================================

archive_temporal() {
    echo ""
    echo -e "${BLUE}📦 归档 temporal_sync_engine...${NC}"

    for file in scripts/ops/temporal_sync_engine*.js; do
        if [[ -f "$file" ]]; then
            if $DRY_RUN; then
                echo -e "  ${YELLOW}[预览]${NC} 将归档: $file"
            else
                mv "$file" archives/v170_legacy_junk/
                echo -e "  ${GREEN}✅${NC} 已归档: $file"
            fi
        fi
    done
}

# ============================================================================
# 5. 清理 node_modules 中的临时文件
# ============================================================================

cleanup_temp_files() {
    echo ""
    echo -e "${BLUE}🧹 清理临时文件...${NC}"

    # 清理 .log 文件
    local log_count=$(find . -name "*.log" -not -path "*/node_modules/*" 2>/dev/null | wc -l)
    if [[ $log_count -gt 0 ]]; then
        if $DRY_RUN; then
            echo -e "  ${YELLOW}[预览]${NC} 将删除 $log_count 个 .log 文件"
        else
            find . -name "*.log" -not -path "*/node_modules/*" -delete
            echo -e "  ${GREEN}✅${NC} 已删除 $log_count 个 .log 文件"
        fi
    else
        echo -e "  无 .log 文件需要清理"
    fi
}

# ============================================================================
# 6. 生成归档 README
# ============================================================================

generate_readme() {
    echo ""
    echo -e "${BLUE}📝 生成归档 README...${NC}"

    if ! $DRY_RUN; then
        cat > archives/v170_legacy_junk/README.md << 'EOF'
# V170 及更早版本的遗留代码归档

⚠️ **警告**: 本目录包含历史版本的代码，仅供参考。

## 归档内容

| 目录/文件 | 版本 | 说明 |
|----------|------|------|
| `v87_master_pipeline.js` | V87 | 早期流水线 |
| `v91_000_*.js` | V91 | 主程序架构 |
| `legacy_research/` | V117-V140 | 研究性代码 |
| `temporal_sync_engine*.js` | V49 | 时间同步引擎 |

## 归档日期

2026-02-27 (V172-GOLD 发布)

## 如需恢复

1. 确认文件用途
2. 复制到目标目录
3. 更新引用路径
EOF
        echo -e "  ${GREEN}✅${NC} README 已生成"
    fi
}

# ============================================================================
# 执行清理
# ============================================================================

main() {
    create_archive_dirs
    archive_v87_v91
    archive_v171
    archive_legacy_research
    archive_temporal
    cleanup_temp_files
    generate_readme

    echo ""
    echo "═══════════════════════════════════════════════════════════════════════════════"

    if $DRY_RUN; then
        echo -e "  ${YELLOW}预览完成。使用 --execute 执行实际清理。${NC}"
    else
        echo -e "  ${GREEN}✅ 清理完成！${NC}"
        echo ""
        echo "  归档位置:"
        echo "    - archives/v170_legacy_junk/"
        echo "    - archives/v171_scripts/"
    fi

    echo "═══════════════════════════════════════════════════════════════════════════════"
}

main
