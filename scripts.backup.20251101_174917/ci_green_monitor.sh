#!/bin/bash
# CI/CD 绿灯监控脚本
# 确保所有工作流持续保持绿灯状态

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 计数器
SUCCESS_COUNT=0
FAILURE_COUNT=0
TOTAL_COUNT=0

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
    SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
    FAILURE_COUNT=$((FAILURE_COUNT + 1))
}

# 检查最新工作流运行状态
check_workflow_status() {
    local workflow_name="$1"
    local limit="${2:-5}"

    log_info "检查工作流: $workflow_name"
    TOTAL_COUNT=$((TOTAL_COUNT + 1))

    # 获取最新运行状态
    local latest_status=$(gh run list --workflow="$workflow_name" --limit="$limit" --json status,conclusion --jq '.[0].status + ":" + .[0].conclusion' 2>/dev/null || echo "unknown:unknown")

    case "$latest_status" in
        "completed:success")
            log_success "$workflow_name - ✅ 绿灯"
            return 0
            ;;
        "completed:failure")
            log_error "$workflow_name - ❌ 红灯"
            return 1
            ;;
        "completed:cancelled")
            log_warning "$workflow_name - ⚠️ 已取消"
            return 2
            ;;
        "in_progress:"*)
            log_warning "$workflow_name - 🔄 运行中"
            return 2
            ;;
        "queued:"*)
            log_warning "$workflow_name - ⏳ 排队中"
            return 2
            ;;
        *)
            log_error "$workflow_name - ❓ 状态未知: $latest_status"
            return 1
            ;;
    esac
}

# 检查所有工作流
check_all_workflows() {
    log_info "🔍 开始检查所有工作流状态..."
    echo "========================================"

    # 主要工作流列表
    local workflows=(
        "Main CI/CD Pipeline"
        "🤖 Automated Testing Pipeline (Simplified)"
        "测试工作流"
        "质量守护系统集成"
        "项目健康监控"
        "🧠 智能质量监控"
    )

    local exit_code=0

    for workflow in "${workflows[@]}"; do
        if ! check_workflow_status "$workflow"; then
            exit_code=1
        fi
        sleep 1  # 避免API限制
    done

    echo "========================================"
    log_info "📊 统计结果:"
    echo "  总计: $TOTAL_COUNT"
    echo -e "  成功: ${GREEN}$SUCCESS_COUNT${NC}"
    echo -e "  失败: ${RED}$FAILURE_COUNT${NC}"

    local success_rate=0
    if [ $TOTAL_COUNT -gt 0 ]; then
        success_rate=$((SUCCESS_COUNT * 100 / TOTAL_COUNT))
    fi

    echo "  成功率: $success_rate%"

    if [ $success_rate -eq 100 ]; then
        log_success "🎉 所有工作流都是绿灯！"
    elif [ $success_rate -ge 80 ]; then
        log_warning "⚠️ 大部分工作流正常，但需要关注失败的流程"
    else
        log_error "🚨 多个工作流失败，需要立即处理！"
    fi

    return $exit_code
}

# 检查最新提交的状态
check_latest_commit() {
    log_info "🔍 检查最新提交的工作流状态..."

    local latest_run=$(gh run list --limit 1 --json status,conclusion,headBranch,headSha --jq '.[0]' 2>/dev/null)

    if [ -z "$latest_run" ]; then
        log_error "无法获取最新运行状态"
        return 1
    fi

    local status=$(echo "$latest_run" | jq -r '.status')
    local conclusion=$(echo "$latest_run" | jq -r '.conclusion')
    local branch=$(echo "$latest_run" | jq -r '.headBranch')
    local sha=$(echo "$latest_run" | jq -r '.headSha')

    echo "最新提交: $sha (分支: $branch)"
    echo "状态: $status"
    echo "结论: $conclusion"

    if [ "$status" = "completed" ] && [ "$conclusion" = "success" ]; then
        log_success "最新提交通过所有检查 ✅"
        return 0
    else
        log_error "最新提交存在问题 ❌"
        return 1
    fi
}

# 主函数
main() {
    echo "🚦 CI/CD 绿灯监控器"
    echo "===================="
    echo "时间: $(date)"
    echo ""

    # 检查gh CLI是否可用
    if ! command -v gh &> /dev/null; then
        log_error "GitHub CLI (gh) 未安装或不在PATH中"
        exit 1
    fi

    # 检查是否已认证
    if ! gh auth status &> /dev/null; then
        log_error "GitHub CLI 未认证，请运行: gh auth login"
        exit 1
    fi

    local overall_exit_code=0

    # 检查所有工作流
    if ! check_all_workflows; then
        overall_exit_code=1
    fi

    echo ""

    # 检查最新提交
    if ! check_latest_commit; then
        overall_exit_code=1
    fi

    echo ""

    if [ $overall_exit_code -eq 0 ]; then
        log_success "🎯 所有检查通过！CI/CD系统运行正常。"
    else
        log_error "⚠️ 发现问题，请查看上述详情并及时处理。"
    fi

    return $overall_exit_code
}

# 帮助信息
show_help() {
    echo "CI/CD 绿灯监控器"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  -h, --help     显示此帮助信息"
    echo "  -w, --workflow 检查特定工作流"
    echo "  -c, --commit   仅检查最新提交"
    echo ""
    echo "示例:"
    echo "  $0                    # 检查所有工作流"
    echo "  $0 -w 'Main CI/CD'    # 检查特定工作流"
    echo "  $0 -c                 # 仅检查最新提交"
}

# 参数处理
case "${1:-}" in
    -h|--help)
        show_help
        exit 0
        ;;
    -w|--workflow)
        if [ -z "${2:-}" ]; then
            log_error "请指定工作流名称"
            exit 1
        fi
        check_workflow_status "$2"
        exit $?
        ;;
    -c|--commit)
        check_latest_commit
        exit $?
        ;;
    "")
        main
        exit $?
        ;;
    *)
        log_error "未知参数: $1"
        show_help
        exit 1
        ;;
esac