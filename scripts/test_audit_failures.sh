#!/bin/bash

# ============================================================================
# Kanban Audit 故意破坏场景测试脚本
# ============================================================================
#
# 该脚本用于批量模拟 "故意破坏场景"，验证 kanban-audit.yml 工作流
# 能否正确检测并报告错误。
#
# 依赖要求:
# - gh CLI 已安装并登录 (gh auth status)
# - 具备仓库写权限
# - git 配置正确
#
# 使用方法:
# chmod +x scripts/test_audit_failures.sh
# ./scripts/test_audit_failures.sh
# ============================================================================

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 脚本配置
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
REPO_OWNER="xupeng211"
REPO_NAME="FootballPrediction"
TEMP_BRANCH_PREFIX="test-break-"

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

# 检查依赖
check_dependencies() {
    log_info "检查依赖..."

    # 检查 gh CLI
    if ! command -v gh &> /dev/null; then
        log_error "gh CLI 未安装。请访问 https://cli.github.com/ 安装。"
        exit 1
    fi

    # 检查 gh 登录状态
    if ! gh auth status &> /dev/null; then
        log_error "gh CLI 未登录。请运行 'gh auth login'。"
        exit 1
    fi

    # 检查 git 状态
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        log_error "不在 git 仓库中。"
        exit 1
    fi

    # 检查是否有未提交的更改
    if ! git diff-index --quiet HEAD; then
        log_warning "工作目录有未提交的更改，可能会影响测试。"
        read -p "是否继续？(y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi

    log_success "依赖检查通过。"
}

# 获取当前分支
get_current_branch() {
    git rev-parse --abbrev-ref HEAD
}

# 切换到主分支
ensure_main_branch() {
    local current_branch=$(get_current_branch)
    if [[ "$current_branch" != "main" ]]; then
        log_info "切换到 main 分支..."
        git checkout main
    fi

    # 确保本地 main 分支是最新的
    log_info "更新 main 分支..."
    git pull origin main
}

# 清理测试分支
cleanup_test_branches() {
    log_info "清理旧的测试分支..."

    # 删除本地测试分支
    git branch | grep "$TEMP_BRANCH_PREFIX" | while read branch; do
        branch=$(echo "$branch" | sed 's/^[ *]*//')
        log_info "删除本地分支: $branch"
        git branch -D "$branch" 2>/dev/null || true
    done

    # 删除远程测试分支
    git branch -r | grep "origin/$TEMP_BRANCH_PREFIX" | while read branch; do
        branch=$(echo "$branch" | sed 's/^[ *]*origin\///')
        log_info "删除远程分支: $branch"
        git push origin --delete "$branch" 2>/dev/null || true
    done

    log_success "清理完成。"
}

# 创建测试分支
create_test_branch() {
    local scenario_num=$1
    local branch_name="${TEMP_BRANCH_PREFIX}${scenario_num}"

    log_info "创建测试分支: $branch_name"
    git checkout -b "$branch_name"
}

# 提交并推送更改
commit_and_push() {
    local scenario_num=$1
    local description=$2

    log_info "提交更改..."
    git add .
    git commit -m "test: break scenario $scenario_num - $description

    This is a test commit to validate kanban-audit workflow.
    Expected behavior: audit should detect failures and generate report."

    log_info "推送分支..."
    git push origin "HEAD"
}

# 创建 PR
create_pr() {
    local scenario_num=$1
    local description=$2
    local expected_result=$3
    local branch_name="${TEMP_BRANCH_PREFIX}${scenario_num}"

    log_info "创建 Pull Request..."

    # 使用 gh CLI 创建 PR
    local pr_url=$(gh pr create \
        --title "test: break scenario $scenario_num - $description" \
        --body "## 🧪 Audit Break Test - Scenario $scenario_num

### Description
$description

### Expected Result
$expected_result

### Purpose
This PR tests the kanban-audit.yml workflow's ability to detect and report configuration errors.

### Instructions
1. Merge this PR to trigger the audit workflow
2. Check the GitHub Actions logs
3. Verify the audit report contains ❌ markers
4. Confirm the workflow completes successfully even with failures

**Note**: This is an automated test for audit validation." \
        --head "$branch_name" \
        --base "main")

    if [[ $? -eq 0 ]]; then
        log_success "PR 创建成功: $pr_url"
        echo "$pr_url" >> "$SCRIPT_DIR/audit_test_prs.txt"
    else
        log_error "PR 创建失败"
        return 1
    fi
}

# 场景 1: 删除 Kanban 文件
run_scenario_1() {
    log_info "=== Running Break Scenario 1: Remove Kanban File ==="

    create_test_branch 1

    # 删除 Kanban 文件
    if [[ -f "$PROJECT_ROOT/docs/_reports/TEST_OPTIMIZATION_KANBAN.md" ]]; then
        rm "$PROJECT_ROOT/docs/_reports/TEST_OPTIMIZATION_KANBAN.md"
        log_info "已删除 Kanban 文件"
    else
        log_warning "Kanban 文件不存在，跳过删除步骤"
    fi

    commit_and_push 1 "remove Kanban file" \
        "Audit should detect missing Kanban file and report ❌"

    create_pr 1 "Remove Kanban File" \
        "Audit report should show: ❌ Kanban file missing"

    log_success "场景 1 完成"
}

# 场景 2: 注释掉 pre-commit hook
run_scenario_2() {
    log_info "=== Running Break Scenario 2: Disable Pre-commit Hook ==="

    create_test_branch 2

    # 注释 pre-commit hook 内容
    if [[ -f "$PROJECT_ROOT/.git/hooks/pre-commit" ]]; then
        echo "# Disabled for audit testing" > "$PROJECT_ROOT/.git/hooks/pre-commit"
        log_info "已禁用 pre-commit hook"
    else
        log_warning "pre-commit hook 不存在，创建空文件"
        echo "# Disabled for audit testing" > "$PROJECT_ROOT/.git/hooks/pre-commit"
    fi

    commit_and_push 2 "disable pre-commit hook" \
        "Audit should detect invalid pre-commit hook and report ❌"

    create_pr 2 "Disable Pre-commit Hook" \
        "Audit report should show: ❌ pre-commit hook invalid"

    log_success "场景 2 完成"
}

# 场景 3: 删除 Makefile 目标
run_scenario_3() {
    log_info "=== Running Break Scenario 3: Remove Makefile Target ==="

    create_test_branch 3

    # 注释 setup-hooks 目标
    if [[ -f "$PROJECT_ROOT/Makefile" ]]; then
        # 备份原文件
        cp "$PROJECT_ROOT/Makefile" "$PROJECT_ROOT/Makefile.backup"

        # 注释 setup-hooks 目标
        sed -i '/^setup-hooks:/,/^$/ s/^setup-hooks:/# setup-hooks:/' "$PROJECT_ROOT/Makefile"
        log_info "已注释 setup-hooks 目标"
    else
        log_error "Makefile 不存在"
        return 1
    fi

    commit_and_push 3 "remove setup-hooks target" \
        "Audit should detect missing setup-hooks target and report ❌"

    create_pr 3 "Remove Makefile Target" \
        "Audit report should show: ❌ setup-hooks target missing"

    log_success "场景 3 完成"
}

# 场景 4: 删除 CI 缓存配置
run_scenario_4() {
    log_info "=== Running Break Scenario 4: Remove CI Cache ==="

    create_test_branch 4

    # 注释缓存步骤
    if [[ -f "$PROJECT_ROOT/.github/workflows/kanban-check.yml" ]]; then
        # 备份原文件
        cp "$PROJECT_ROOT/.github/workflows/kanban-check.yml" "$PROJECT_ROOT/.github/workflows/kanban-check.yml.backup"

        # 注释缓存步骤
        sed -i '/- name: Cache hooks and Kanban file/,/^$/ s/^/#/' "$PROJECT_ROOT/.github/workflows/kanban-check.yml"
        log_info "已注释 CI 缓存步骤"
    else
        log_error "kanban-check.yml 不存在"
        return 1
    fi

    commit_and_push 4 "remove CI cache configuration" \
        "Audit should detect missing cache configuration and report ❌"

    create_pr 4 "Remove CI Cache" \
        "Audit report should show: ❌ cache configuration missing"

    log_success "场景 4 完成"
}

# 场景 5: 删除 README 徽章
run_scenario_5() {
    log_info "=== Running Break Scenario 5: Remove README Badge ==="

    create_test_branch 5

    # 删除 Test Improvement Guide 徽章
    if [[ -f "$PROJECT_ROOT/README.md" ]]; then
        # 备份原文件
        cp "$PROJECT_ROOT/README.md" "$PROJECT_ROOT/README.md.backup"

        # 删除 Test Improvement Guide 徽章行
        sed -i '/Test Improvement Guide.*blue/d' "$PROJECT_ROOT/README.md"
        log_info "已删除 README 徽章"
    else
        log_error "README.md 不存在"
        return 1
    fi

    commit_and_push 5 "remove README badge" \
        "Audit should detect missing README badge and report ❌"

    create_pr 5 "Remove README Badge" \
        "Audit report should show: ❌ README badge missing"

    log_success "场景 5 完成"
}

# 恢复环境
restore_environment() {
    log_info "恢复环境..."

    ensure_main_branch

    # 恢复备份文件
    if [[ -f "$PROJECT_ROOT/Makefile.backup" ]]; then
        mv "$PROJECT_ROOT/Makefile.backup" "$PROJECT_ROOT/Makefile"
        log_info "已恢复 Makefile"
    fi

    if [[ -f "$PROJECT_ROOT/.github/workflows/kanban-check.yml.backup" ]]; then
        mv "$PROJECT_ROOT/.github/workflows/kanban-check.yml.backup" "$PROJECT_ROOT/.github/workflows/kanban-check.yml"
        log_info "已恢复 kanban-check.yml"
    fi

    if [[ -f "$PROJECT_ROOT/README.md.backup" ]]; then
        mv "$PROJECT_ROOT/README.md.backup" "$PROJECT_ROOT/README.md"
        log_info "已恢复 README.md"
    fi

    # 提交恢复
    if ! git diff-index --quiet HEAD; then
        log_info "提交恢复的文件..."
        git add .
        git commit -m "chore: restore files after audit break tests"
        git push origin main
    fi

    log_success "环境恢复完成"
}

# 显示使用说明
show_usage() {
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  -h, --help      显示此帮助信息"
    echo "  -c, --cleanup   仅清理测试分支"
    echo "  -s, --scenario  运行指定场景 (1-5)"
    echo "  -a, --all       运行所有场景 (默认)"
    echo ""
    echo "示例:"
    echo "  $0              # 运行所有场景"
    echo "  $0 -s 1         # 仅运行场景 1"
    echo "  $0 -c           # 仅清理测试分支"
    echo ""
    echo "注意事项:"
    echo "- 需要 gh CLI 已安装并登录"
    echo "- 需要仓库写权限"
    echo "- 每个场景会创建 PR，需要手动合并以触发审计"
}

# 主函数
main() {
    local scenario=""
    local cleanup_only=false

    # 解析命令行参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_usage
                exit 0
                ;;
            -c|--cleanup)
                cleanup_only=true
                shift
                ;;
            -s|--scenario)
                scenario="$2"
                shift 2
                ;;
            -a|--all)
                scenario="all"
                shift
                ;;
            *)
                log_error "未知选项: $1"
                show_usage
                exit 1
                ;;
        esac
    done

    # 设置默认场景
    if [[ -z "$scenario" && "$cleanup_only" == false ]]; then
        scenario="all"
    fi

    # 清理 PR 记录文件
    echo "" > "$SCRIPT_DIR/audit_test_prs.txt"

    # 检查依赖
    if [[ "$cleanup_only" == false ]]; then
        check_dependencies
    fi

    # 切换到项目根目录
    cd "$PROJECT_ROOT"

    # 清理旧分支
    cleanup_test_branches

    if [[ "$cleanup_only" == true ]]; then
        log_success "清理完成"
        exit 0
    fi

    # 确保在 main 分支
    ensure_main_branch

    # 运行测试场景
    case $scenario in
        1)
            run_scenario_1
            ;;
        2)
            run_scenario_2
            ;;
        3)
            run_scenario_3
            ;;
        4)
            run_scenario_4
            ;;
        5)
            run_scenario_5
            ;;
        all)
            log_info "开始运行所有破坏场景测试..."
            run_scenario_1
            ensure_main_branch
            run_scenario_2
            ensure_main_branch
            run_scenario_3
            ensure_main_branch
            run_scenario_4
            ensure_main_branch
            run_scenario_5
            ;;
        *)
            log_error "无效的场景编号: $scenario (支持 1-5)"
            exit 1
            ;;
    esac

    # 恢复环境
    restore_environment

    # 显示结果
    log_success "=== 测试完成 ==="
    echo ""
    echo "📋 接下来的操作:"
    echo "1. 访问 GitHub 并依次合并创建的 PR"
    echo "2. 观察 kanban-audit 工作流的执行"
    echo "3. 检查生成的审计报告"
    echo ""
    echo "📄 PR 列表已保存到: $SCRIPT_DIR/audit_test_prs.txt"
    echo ""

    # 显示 PR 列表
    if [[ -f "$SCRIPT_DIR/audit_test_prs.txt" ]]; then
        echo "🔗 创建的 PR:"
        cat "$SCRIPT_DIR/audit_test_prs.txt"
    fi

    echo ""
    echo "🎯 预期结果:"
    echo "- 每个 PR 合并后应触发 kanban-audit 工作流"
    echo "- 审计报告应包含对应的 ❌ 标记"
    echo "- 工作流应成功完成，不被错误阻塞"
}

# 运行主函数
main "$@"