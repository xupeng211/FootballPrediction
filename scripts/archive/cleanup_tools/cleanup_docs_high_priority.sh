#!/bin/bash
#
# 文档清理脚本 - 高优先级任务
# 基于 docs/DOCS_CLEANUP_ANALYSIS.md 分析报告
#
# 使用方法:
#   ./scripts/cleanup_docs_high_priority.sh --dry-run  # 预览将要执行的操作
#   ./scripts/cleanup_docs_high_priority.sh            # 实际执行清理
#

set -e

DOCS_DIR="/home/user/projects/FootballPrediction/docs"
DRY_RUN=false

# 解析命令行参数
if [[ "$1" == "--dry-run" ]]; then
    DRY_RUN=true
    echo "🔍 DRY RUN 模式 - 仅预览，不实际执行"
    echo ""
fi

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 辅助函数
log_info() {
    echo -e "${BLUE}ℹ ${NC}$1"
}

log_success() {
    echo -e "${GREEN}✓${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
}

# 统计函数
count_files() {
    find "$1" -type f 2>/dev/null | wc -l
}

# 执行或模拟命令
run_cmd() {
    if [ "$DRY_RUN" = true ]; then
        echo "  [DRY-RUN] $*"
    else
        eval "$*"
    fi
}

# 创建目录（如果需要）
mkdir_safe() {
    if [ ! -d "$1" ]; then
        run_cmd "mkdir -p '$1'"
    fi
}

echo "========================================"
echo "📚 文档清理脚本 - 高优先级任务"
echo "========================================"
echo ""

# 前置检查
log_info "检查docs目录..."
if [ ! -d "$DOCS_DIR" ]; then
    log_error "docs目录不存在: $DOCS_DIR"
    exit 1
fi

cd "$DOCS_DIR"
INITIAL_COUNT=$(count_files "$DOCS_DIR")
log_info "当前文档总数: $INITIAL_COUNT"
echo ""

# ============================================
# 任务1: 清理 _reports 目录中的时间戳文件
# ============================================
echo "----------------------------------------"
echo "任务1: 清理_reports中的时间戳文件"
echo "----------------------------------------"

REPORTS_DIR="_reports"
if [ -d "$REPORTS_DIR" ]; then
    log_info "查找带时间戳的COVERAGE_BASELINE文件..."

    # 查找所有COVERAGE_BASELINE_P1文件，保留最新的，删除其他
    BASELINE_FILES=($(ls -t "${REPORTS_DIR}/COVERAGE_BASELINE_P1_"*.md 2>/dev/null || true))

    if [ ${#BASELINE_FILES[@]} -gt 1 ]; then
        log_warning "找到 ${#BASELINE_FILES[@]} 个COVERAGE_BASELINE_P1文件"
        log_info "保留最新: ${BASELINE_FILES[0]}"

        for file in "${BASELINE_FILES[@]:1}"; do
            log_info "删除: $file"
            run_cmd "rm '$file'"
        done

        log_success "清理了 $((${#BASELINE_FILES[@]} - 1)) 个旧的基线文件"
    else
        log_info "未找到需要清理的COVERAGE_BASELINE_P1文件"
    fi
else
    log_warning "_reports目录不存在"
fi

echo ""

# ============================================
# 任务2: 归档过时的看板文件
# ============================================
echo "----------------------------------------"
echo "任务2: 归档过时的看板文件"
echo "----------------------------------------"

KANBAN_ARCHIVE_DIR="${REPORTS_DIR}/archive/2025-09/kanbans"
mkdir_safe "$KANBAN_ARCHIVE_DIR"

# 要归档的看板文件列表（排除QA_TEST_KANBAN.md）
KANBAN_FILES_TO_ARCHIVE=(
    "${REPORTS_DIR}/TASK_KANBAN.md"
    "${REPORTS_DIR}/TASK_KANBAN_REVIEW.md"
    "${REPORTS_DIR}/TASK_KANBAN_REVIEW_FINAL.md"
    "${REPORTS_DIR}/TEST_COVERAGE_KANBAN.md"
    "${REPORTS_DIR}/TEST_OPTIMIZATION_KANBAN.md"
    "${REPORTS_DIR}/TEST_REFACTOR_KANBAN.md"
    "${REPORTS_DIR}/KANBAN_AUDIT_BREAK_TESTS.md"
    "${REPORTS_DIR}/KANBAN_AUDIT_TEST_INSTRUCTIONS.md"
)

KANBAN_ARCHIVED=0
for file in "${KANBAN_FILES_TO_ARCHIVE[@]}"; do
    if [ -f "$file" ]; then
        log_info "归档: $file"
        run_cmd "mv '$file' '$KANBAN_ARCHIVE_DIR/'"
        ((KANBAN_ARCHIVED++))
    fi
done

if [ $KANBAN_ARCHIVED -gt 0 ]; then
    log_success "归档了 $KANBAN_ARCHIVED 个看板文件"
else
    log_info "未找到需要归档的看板文件"
fi

echo ""

# ============================================
# 任务3: 删除 _meta 目录
# ============================================
echo "----------------------------------------"
echo "任务3: 删除_meta目录"
echo "----------------------------------------"

META_DIR="_meta"
if [ -d "$META_DIR" ]; then
    META_COUNT=$(count_files "$META_DIR")
    log_warning "准备删除_meta目录 (包含 $META_COUNT 个文件)"

    if [ "$DRY_RUN" = false ]; then
        read -p "确认删除_meta目录? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            run_cmd "rm -rf '$META_DIR'"
            log_success "已删除_meta目录"
        else
            log_info "跳过删除_meta目录"
        fi
    else
        run_cmd "rm -rf '$META_DIR'"
    fi
else
    log_info "_meta目录不存在，跳过"
fi

echo ""

# ============================================
# 任务4: 删除 _backup 目录
# ============================================
echo "----------------------------------------"
echo "任务4: 删除_backup目录"
echo "----------------------------------------"

BACKUP_DIR="_backup"
if [ -d "$BACKUP_DIR" ]; then
    BACKUP_COUNT=$(count_files "$BACKUP_DIR")
    log_warning "准备删除_backup目录 (包含 $BACKUP_COUNT 个文件)"

    if [ "$DRY_RUN" = false ]; then
        read -p "确认删除_backup目录? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            run_cmd "rm -rf '$BACKUP_DIR'"
            log_success "已删除_backup目录"
        else
            log_info "跳过删除_backup目录"
        fi
    else
        run_cmd "rm -rf '$BACKUP_DIR'"
    fi
else
    log_info "_backup目录不存在，跳过"
fi

echo ""

# ============================================
# 任务5: 整合部署文档
# ============================================
echo "----------------------------------------"
echo "任务5: 整合部署文档"
echo "----------------------------------------"

log_info "建议保留的部署文档:"
log_info "  - how-to/PRODUCTION_DEPLOYMENT_GUIDE.md"
log_info "  - how-to/DEPLOYMENT_ISSUES_LOG.md"
echo ""

log_warning "以下文档建议手动审查后删除/合并:"

DEPLOY_FILES_TO_REVIEW=(
    "how-to/DEPLOYMENT.md"
    "how-to/DEPLOYMENT_GUIDE.md"
    "legacy/DEPLOYMENT.md"
    "legacy/STAGING_DEPLOYMENT_REHEARSAL.md"
    "legacy/PRODUCTION_DEPLOYMENT_MONITORING_COMPLETION_REPORT.md"
    "project/STAGING_DEPLOYMENT_RESULTS.md"
)

for file in "${DEPLOY_FILES_TO_REVIEW[@]}"; do
    if [ -f "$file" ]; then
        log_info "  - $file"
    fi
done

echo ""
log_info "请手动审查这些文件后决定是否删除"
log_info "建议: 将有用内容合并到PRODUCTION_DEPLOYMENT_GUIDE.md"

echo ""

# ============================================
# 任务6: 整合API文档
# ============================================
echo "----------------------------------------"
echo "任务6: 整合API文档"
echo "----------------------------------------"

log_info "建议保留的API文档:"
log_info "  - reference/API_REFERENCE.md"
log_info "  - reference/COMPREHENSIVE_API_DOCUMENTATION_STYLE_GUIDE.md"
echo ""

log_warning "以下文档建议手动审查后删除/合并:"

API_FILES_TO_REVIEW=(
    "API_DOCUMENTATION.md"
    "reference/API_DOCUMENTATION_STYLE_GUIDE.md"
    "reference/API_500_ERROR_ANALYSIS.md"
)

for file in "${API_FILES_TO_REVIEW[@]}"; do
    if [ -f "$file" ]; then
        log_info "  - $file"
    fi
done

echo ""
log_info "请手动审查这些文件后决定是否删除"
log_info "建议: 将有用内容合并到API_REFERENCE.md"

echo ""

# ============================================
# 统计结果
# ============================================
echo "========================================"
echo "📊 清理统计"
echo "========================================"

FINAL_COUNT=$(count_files "$DOCS_DIR")
REMOVED_COUNT=$((INITIAL_COUNT - FINAL_COUNT))

log_info "清理前文档总数: $INITIAL_COUNT"
log_info "清理后文档总数: $FINAL_COUNT"

if [ $REMOVED_COUNT -gt 0 ]; then
    log_success "已清理文档数: $REMOVED_COUNT"
else
    log_info "已清理文档数: $REMOVED_COUNT"
fi

echo ""

# ============================================
# 后续建议
# ============================================
echo "========================================"
echo "📋 后续建议"
echo "========================================"

log_info "1. 手动审查并整合部署文档（任务5）"
log_info "2. 手动审查并整合API文档（任务6）"
log_info "3. 更新 INDEX.md 中的文档链接"
log_info "4. 运行: make context 更新元数据"
log_info "5. 查看 DOCS_CLEANUP_ANALYSIS.md 了解中优先级清理任务"
log_info "6. 提交更改: git add docs/ && git commit -m 'docs: 清理冗余文档（高优先级任务）'"

echo ""
log_success "清理脚本执行完成！"

if [ "$DRY_RUN" = true ]; then
    echo ""
    log_warning "这是DRY RUN模式，没有实际执行任何操作"
    log_info "要实际执行清理，请运行: $0"
fi
