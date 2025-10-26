#!/bin/bash
# GitHub Issue 管理最佳实践工具
# 用途：Issue创建前的重复检查和标准化管理

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

# 检查Issue重复性
check_duplicate_issues() {
    local search_term="$1"
    local max_results=${2:-5}

    print_info "检查重复Issue: '$search_term'"

    # 使用gh cli搜索重复Issues
    local duplicate_count
    duplicate_count=$(gh issue list --search "$search_term" --limit $max_results --state all | wc -l)

    if [ "$duplicate_count" -gt 1 ]; then
        print_error "发现 $duplicate_count 个重复Issue:"
        echo
        gh issue list --search "$search_term" --limit $max_results --state all
        echo
        print_warning "是否继续创建新Issue? (y/N)"
        read -r confirm

        if [[ ! $confirm =~ ^[Yy]$ ]]; then
            print_error "❌ 已取消Issue创建"
            exit 1
        fi
    else
        print_success "✅ 无重复Issue，可以继续创建"
    fi
}

# 验证Issue标题格式
validate_title() {
    local title="$1"

    print_info "验证Issue标题格式: '$title'"

    # 检查是否符合标准格式
    if [[ ! "$title" =~ ^Phase\ [0-9]+\.[0-9]+:\ .*$ ]]; then
        print_warning "⚠️ Issue标题不符合标准格式"
        print_info "建议格式: 'Phase X.Y: [功能模块] - [具体目标]'"

        print_warning "是否继续使用此标题? (y/N)"
        read -r confirm

        if [[ ! $confirm =~ ^[Yy]$ ]]; then
            print_error "❌ 请修正Issue标题"
            exit 1
        fi
    else
        print_success "✅ Issue标题格式正确"
    fi
}

# 创建标准化Issue
create_standard_issue() {
    local phase="$1"
    local week="$2"
    local module="$3"
    local target="$4"
    local description="$5"

    local title="Phase $phase.$week: $module - $target"

    print_info "创建Issue: '$title'"

    # 构建Issue描述
    local issue_body="## Phase $phase.$week: $module\n\n### 🎯 核心目标\n$description\n\n### 📊 成功指标\n- [ ] 目标1\n- [ ] 目标2\n- [ ] 目标3\n\n### 🔗 相关链接\n- 前置Issue: #81 (测试覆盖率提升路线图)\n- 当前状态: $target"

    # 创建Issue
    gh issue create \
        --title "$title" \
        --body "$issue_body" \
        --label "phase-$phase$week,in-progress,coverage-improvement" \
        --assignee "$GITHUB_USERNAME"

    print_success "✅ Issue创建成功"
}

# 关闭重复Issue
close_duplicate_issue() {
    local issue_number="$1"
    local reason="$2"

    print_info "关闭重复Issue #$issue_number"

    gh issue close "$issue_number" \
        --comment "📋 $reason\n\n此Issue与现有主Issue重复，已合并到主Issue进行统一管理。"

    print_success "✅ Issue #$issue_number 已关闭"
}

# 更新Issue内容
update_issue() {
    local issue_number="$1"
    local title="$2"
    local body="$3"

    print_info "更新Issue #$issue_number"

    gh issue edit "$issue_number" \
        --title "$title" \
        --body "$body"

    print_success "✅ Issue #$issue_number 已更新"
}

# 主函数
main() {
    case "$1" in
        "check")
            if [ -z "$2" ]; then
                print_error "❌ 请提供搜索词: ./github_issue_manager.sh check \"search term\""
                exit 1
            fi
            check_duplicate_issues "$2" "${3:-5}"
            ;;
        "validate")
            if [ -z "$2" ]; then
                print_error "❌ 请提供Issue标题: ./github_issue_manager.sh validate \"Issue Title\""
                exit 1
            fi
            validate_title "$2"
            ;;
        "create")
            if [ $# -lt 6 ]; then
                print_error "❌ 参数不足"
                print_info "用法: ./github_issue_manager.sh create phase week module target description"
                print_info "示例: ./github_issue_manager.sh create 4A 1 \"核心业务逻辑\" \"测试覆盖率提升\" \"详细描述\""
                exit 1
            fi
            create_standard_issue "$2" "$3" "$4" "$5" "$6"
            ;;
        "close")
            if [ $# -lt 3 ]; then
                print_error "❌ 参数不足"
                print_info "用法: ./github_issue_manager.sh close issue_number reason"
                exit 1
            fi
            close_duplicate_issue "$2" "$3"
            ;;
        "update")
            if [ $# -lt 4 ]; then
                print_error "❌ 参数不足"
                print_info "用法: ./github_issue_manager.sh update issue_number new_title new_body"
                exit 1
            fi
            update_issue "$2" "$3" "$4"
            ;;
        "help"|"-h"|"--help")
            echo "GitHub Issue 管理最佳实践工具"
            echo
            echo "用法:"
            echo "  $0 check \"搜索词\" [最大结果数]"
            echo "  $0 validate \"Issue标题\""
            echo "  $0 create phase week module target \"描述\""
            echo "  $0 close issue_number \"关闭原因\""
            echo "  $0 update issue_number \"新标题\" \"新内容\""
            echo "  $0 help"
            echo
            echo "示例:"
            echo "  $0 check \"Phase 4A\""
            echo "  $0 validate \"Phase 4A: 核心业务逻辑测试\""
            echo "  $0 create 4A 1 \"核心业务逻辑\" \"测试覆盖率提升\" \"详细描述内容\""
            echo "  $0 close 82 \"重复Issue\""
            echo "  $0 update 83 \"Phase 4A: 测试覆盖率提升至50%\" \"更新后的内容\""
            ;;
        *)
            print_error "❌ 未知命令: $1"
            print_info "使用 '$0 help' 查看帮助信息"
            exit 1
            ;;
    esac
}

# 检查依赖
if ! command -v gh &> /dev/null; then
    print_error "❌ 需要安装GitHub CLI: https://cli.github.com/"
    exit 1
fi

# 检查登录状态
if ! gh auth status &> /dev/null; then
    print_error "❌ 请先登录GitHub CLI: gh auth login"
    exit 1
fi

# 运行主函数
main "$@"