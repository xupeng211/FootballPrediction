#!/bin/bash
# GitHub Issue 创建前验证脚本
# 自动检查重复Issue和验证格式规范

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_error() { echo -e "${RED}❌ $1${NC}" >&2; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}" >&2; }
print_success() { echo -e "${GREEN}✅ $1${NC}" >&2; }
print_info() { echo -e "${BLUE}ℹ️  $1${NC}" >&2; }

# 检查GitHub CLI安装
check_gh_cli() {
    if ! command -v gh &> /dev/null; then
        print_error "GitHub CLI未安装，请先安装: https://cli.github.com/"
        print_info "安装命令: curl -fsSL https://cli.github.com/packages/github-cli | sudo tar -xzvf -C /usr/local/bin"
        exit 1
    fi

    # 检查登录状态
    if ! gh auth status &> /dev/null; then
        print_error "GitHub CLI未登录，请先登录: gh auth login"
        exit 1
    fi
}

# 检查Issue重复性
check_duplicates() {
    local search_term="$1"

    print_info "🔍 检查重复Issue: '$search_term'"

    # 搜索重复Issues
    local issues
    issues=$(gh issue list --search "$search_term" --limit 10 --state all 2>/dev/null || true)

    if [ -z "$issues" ]; then
        print_success "✅ 无重复Issue"
        return 0
    fi

    local duplicate_count
    duplicate_count=$(echo "$issues" | grep -c "")

    if [ "$duplicate_count" -gt 0 ]; then
        print_warning "⚠️ 发现 $duplicate_count 个重复Issue:"
        echo "$issues"

        # 检查是否包含当前Phase
        if echo "$issues" | grep -q "Phase"; then
            print_error "❌ 检测到重复的Phase Issue，建议检查Phase编号"

            # 提取现有Phase编号
            local existing_phases=$(echo "$issues" | grep -o "Phase [0-9]\+\.[0-9]\+" | sed 's/Phase //' | sort -u)
            if [ -n "$existing_phases" ]; then
                echo "现有Phase:"
                echo "$existing_phases"

                # 建议下一个Phase编号
                local next_phase=$(echo "$existing_phases" | tail -1 | awk -F. '{print $1+0.1}' 2>/dev/null || echo "4.1")
                print_info "建议使用Phase $next_phase"
            fi
        fi

        return 1
    else
        print_success "✅ 无重复Issue"
        return 0
    fi
}

# 验证Issue标题格式
validate_title() {
    local title="$1"

    print_info "📝 验证Issue标题: '$title'"

    # 检查标准Phase格式
    if [[ ! "$title" =~ ^Phase\ [0-9]+\.[0-9]+:\ .*$ ]]; then
        print_error "❌ Issue标题不符合Phase X.Y格式"
        print_info "标准格式: 'Phase X.Y: [功能模块] - [具体目标]'"
        print_info "示例: 'Phase 4A.1: 核心业务逻辑测试'"
        return 1
    fi

    # 检查标题长度
    if [ ${#title} -gt 100 ]; then
        print_warning "⚠️ Issue标题过长 (>${#title}字符)，建议精简"
    fi

    # 检查特殊字符
    if [[ "$title" =~ [<>|{}|\[\]|\\|&] ]]; then
        print_warning "⚠️ Issue标题包含特殊字符，建议移除"
    fi

    # 检查包含引用 (不应该有#82等)
    if [[ "$title" =~ #[0-9]+\ +$ ]]; then
        print_error "❌ Issue标题包含Issue引用，标题应该独立"
        print_info "错误格式: 'Phase 4A: 测试覆盖率提升至50% #82'"
        print_info "正确格式: 'Phase 4A: 测试覆盖率提升至50%'"
        return 1
    fi

    print_success "✅ Issue标题格式正确"
    return 0
}

# 生成Issue编号建议
suggest_phase_number() {
    local search_term="$1"

    print_info "🔢 分析现有Phase编号..."

    # 搜索现有Phase Issues
    local existing_issues
    existing_issues=$(gh issue list --search "$search_term" --limit 20 --state all 2>/dev/null || true)

    if [ -z "$existing_issues" ]; then
        print_info "🆕 未找到现有Phase Issue"
        echo "建议使用: Phase 4A.1"
        return "4A.1"
    fi

    # 提取Phase编号
    local phase_numbers
    phase_numbers=$(echo "$existing_issues" | grep -o "Phase [0-9]\+\.[0-9]\+" | sed 's/Phase //' | sort -uV)

    if [ -z "$phase_numbers" ]; then
        print_warning "⚠️ 未找到标准格式的Phase编号"
        return "4A.1"
    fi

    # 找到最大编号
    local max_phase
    max_phase=$(echo "$phase_numbers" | sort -V | tail -1)

    if [[ "$max_phase" =~ ^([0-9]+)\.([0-9]+)$ ]]; then
        local major="${BASH_REMATCH[1]}"
        local minor="${BASH_REMATCH[2]}"

        if [ "$minor" -eq "9" ]; then
            # 如果minor是9，则major进位
            major=$((major + 1))
            minor=0
        else
            minor=$((minor + 1))
        fi

        local next_phase="$major.$minor"
        print_info "💡 建议使用下一个Phase: $next_phase"
        echo "$next_phase"
    else
        print_warning "⚠️ 无法解析Phase编号格式"
        return "4A.1"
    fi
}

# 主验证函数
main() {
    case "$1" in
        "check-duplicates")
            if [ -z "$2" ]; then
                print_error "用法: $0 check-duplicates \"搜索词\""
                exit 1
            fi
            check_duplicates "$2"
            ;;
        "validate-title")
            if [ -z "$2" ]; then
                print_error "用法: $0 validate-title \"Issue标题\""
                exit 1
            fi
            validate_title "$2"
            ;;
        "suggest-phase")
            if [ -z "$2" ]; then
                print_error "用法: $0 suggest-phase \"搜索词\""
                exit 1
            fi
            suggest_phase_number "$2"
            ;;
        "full")
            if [ -z "$2" ]; then
                print_error "用法: $0 full \"Issue标题\""
                exit 1
            fi

            # 执行完整检查
            print_info "🔍 开始完整Issue验证..."

            # 检查GitHub CLI
            check_gh_cli

            # 检查重复
            if ! check_duplicates "$2"; then
                exit 1
            fi

            # 验证标题
            if ! validate_title "$2"; then
                exit 1
            fi

            # 建议Phase编号
            suggest_phase_number "$2"

            print_success "✅ Issue验证通过"
            ;;
        "help"|"-h"|"--help")
            echo "GitHub Issue 预验证脚本"
            echo ""
            echo "用法:"
            echo "  $0 <command> <argument>"
            echo ""
            echo "命令:"
            echo "  check-duplicates <search_term>    检查重复Issue"
            echo "  validate-title <title>         验证Issue标题格式"
            echo "  suggest-phase <search_term>      建议Phase编号"
            echo "  full <title>                 执行完整检查"
            echo "  help                          显示帮助信息"
            echo ""
            echo "示例:"
            echo "  $0 check-duplicates \"Phase 4A\""
            echo "  $0 validate-title \"Phase 4A: 测试覆盖率提升\""
            echo "  $0 suggest-phase \"Phase 4A\""
            echo "  $0 full \"Phase 4A: 测试覆盖率提升\""
            exit 0
            ;;
        *)
            print_error "未知命令: $1"
            echo "使用 '$0 help' 查看帮助信息"
            exit 1
            ;;
    esac
}

# 检查依赖并执行
if [ "$BASH_SOURCE" = "${0}" ]; then
    check_gh_cli
    main "$@"
fi