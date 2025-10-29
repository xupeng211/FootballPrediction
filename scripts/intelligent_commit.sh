#!/bin/bash

# 智能暂存区管理和提交脚本
set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

print_message() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# 获取暂存区统计
get_stash_stats() {
    local modified=$(git status --porcelain | grep "^M" | wc -l)
    local added=$(git status --porcelain | grep "^??" | wc -l)
    local deleted=$(git status --porcelain | grep "^D" | wc -l)
    local renamed=$(git status --porcelain | grep "^R" | wc -l)
    local untracked=$(git status --porcelain | "^??" | wc -l)

    echo "$modified:$added:$deleted:$renamed:$untracked"
}

# 智能提交决策
intelligent_commit() {
    local stats=$(get_stash_stats)
    IFS=':' read -r modified added deleted renamed untracked <<< "$stats"

    print_message $BLUE "📊 暂存区分析结果:"
    print_message $CYAN "  - 修改文件: $modified 个"
    print_message $CYAN "  - 新增文件: $added 个"
    print_message $CYAN "  - 删除文件: $deleted 个"
    print_message $CYAN "  - 重命名文件: $renamed 个"
    print_message $CYAN "  - 未跟踪文件: $untracked 个"
    echo ""

    total=$((modified + added + deleted + renamed + untracked))

    if [ $total -eq 0 ]; then
        print_message $GREEN "✅ 暂存区是干净的，无需提交"
        return 0
    fi

    # 提交决策
    if [ $total -le 10 ]; then
        print_message $YELLOW "📝 文件数量较少 ($total)，建议单次提交"
        single_commit "生产部署完成 - 完整功能验证和配置"
    elif [ $total -le 30 ]; then
        print_message $YELLOW "📝 文件数量适中 ($total)，建议分类提交"
        phased_commit
    else
        print_message $YELLOW "📝 文件数量较多 ($total)，建议分批次提交"
        batch_commit
    fi
}

# 单次提交
single_commit() {
    local message="$1"

    print_message $BLUE "🚀 执行单次提交..."

    git add .
    git commit -m "$message"

    print_message $GREEN "✅ 单次提交完成: $message"

    # 推送到远程
    if [ -n "$(git remote get-url origin)" ]; then
        print_message $CYAN "📤 推送到远程仓库..."
        git push origin main
        print_message $GREEN "✅ 远程推送完成"
    fi
}

# 分类提交
phased_commit() {
    print_message $BLUE "🔄 执行分类提交..."

    # 第一阶段：核心配置文件
    print_message $CYAN "=== 第一阶段：核心生产配置 ==="
    git add docker-compose.prod.yml .env.production nginx/ monitoring/
    git commit -m "🚀 Phase 1: 生产环境核心配置"
    print_message $GREEN "✅ 第一阶段提交完成"
    echo ""

    # 第二阶段：应用代码
    print_message $CYAN "=== 第二阶段：应用源码和配置 ==="
    git add src/
    git commit -m "💻 Phase 2: 应用源码和配置更新"
    print_message $GREEN "✅ 第二阶段提交完成"
    echo ""

    # 第三阶段：文档和脚本
    print_message $CYAN "=== 第三阶段：文档和自动化脚本 ==="
    git add docs/ scripts/ *.md
    git commit -m "📚 Phase 3: 文档和自动化脚本"
    print_message $GREEN "✅ 第三阶段提交完成"
    echo ""

    # 第四阶段：测试文件
    print_message $CYAN "=== 第四阶段：测试用例和验证 ==="
    git add tests/
    git commit -m "🧪 Phase 4: 测试用例和验证"
    print_message $GREEN "✅ 第四阶段提交完成"
    echo ""

    # 第五阶段：剩余文件
    print_message $CYAN "=== 第五阶段：剩余所有文件 ==="
    git add .
    git commit -m "🔧 Phase 5: 剩余文件整合"
    print_message $GREEN "✅ 第五阶段提交完成"
    echo ""

    # 推送到远程
    if [ -n "$(git remote get-url origin)" ]; then
        print_message $CYAN "📤 推送所有提交到远程仓库..."
        git push origin main --force
        print_message $GREEN "✅ 所有提交已推送到远程"
    fi
}

# 批量提交（适用于大量文件）
batch_commit() {
    print_message $BLUE "🔄 执行批量提交..."

    # 分批提交，每批最多20个文件
    batch_size=20
    batch_count=1

    while [ $(git status --porcelain | wc -l) -gt 0 ]; do
        print_message $CYAN "=== 第 $batch_count 批 ($batch_size 个文件/批次) ==="

        # 添加最多batch_size个文件
        files_to_add=$(git status --porcelain | head -n $batch_size | cut -c4-)

        if [ -n "$files_to_add" ]; then
            git add $files_to_add
            git commit -m "📦 批量提交 - 第 $batch_count 批"
            print_message $GREEN "✅ 第 $batch_count 批提交完成"
            ((batch_count++))
        else
            break
        fi
        sleep 1
    done

    print_message $GREEN "✅ 批量提交完成，共 $((batch_count-1)) 批"

    # 推送到远程
    if [ -n "$(git remote get-url origin)" ]; then
        print_message $CYAN "📤 推送批量提交到远程仓库..."
        git push origin main --force
        print_message $GREEN "✅ 批量提交已推送到远程"
    fi
}

# 创建提交前摘要
create_commit_summary() {
    local message="$1"
    local stats=$(get_stash_stats)
    IFS=':' read -r modified added deleted renamed untracked <<< "$stats"
    total=$((modified + added + deleted + renamed + untracked))

    print_message $BLUE "📝 提交摘要:"
    print_message $CYAN "  消息: $message"
    print_message $CYAN "  文件数: $total (M:$modified, A:$added, D:$deleted, R:$renamed, U:$untracked)"

    if [ -n "$(git remote get-url origin)" ]; then
        print_message $CYAN "  远程: 将推送到 origin/main"
    fi
    echo ""
}

# 显示帮助信息
show_help() {
    echo "智能暂存区管理和提交脚本"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  auto        智能分析并选择最佳提交策略"
    echo "  single     单次提交所有暂存区文件"
    "  phased     分类提交（分5个阶段）"
    "  batch      批量提交（适用于大量文件）"
    "  summary   显示提交前摘要"
    "  help       显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 auto        # 智能分析和提交"
    echo "  $0 single     # 单次提交所有文件"
    echo "  $0 phased     # 分类分阶段提交"
    echo "  $0 batch      # 批量提交"
    echo "  $0 summary   # 显示提交前摘要"
    echo ""
    echo "推荐用法:"
    echo "  1. 使用 $0 auto 进行智能分析"
    echo "  2. 根据暂存区大小自动选择最佳策略"
    echo "  3. 自动推送到远程仓库"
}

# 主函数
main() {
    case "$1" in
        auto)
            create_commit_summary "智能自动提交 - 生产部署完成"
            intelligent_commit
            ;;
        single)
            create_commit_summary "单次提交 - 生产部署完成"
            single_commit "生产部署完成 - 完整功能验证和配置"
            ;;
        phased)
            create_commit_summary "分类提交 - 生产部署完成"
            phased_commit
            ;;
        batch)
            create_commit_summary "批量提交 - 大规模更新"
            batch_commit
            ;;
        summary)
            create_commit_summary "提交前摘要"
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            print_message $PURPLE "🤖 智能暂存区管理脚本"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

# 如果直接执行脚本，运行主函数
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi