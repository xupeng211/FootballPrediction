#!/bin/bash

# 暂存区分阶段提交脚本
set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_message() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# 函数：提交特定类型的文件
commit_by_pattern() {
    local pattern=$1
    local message=$2
    local files=$(git status --porcelain | grep -E "$pattern" | cut -c4-)

    if [ -n "$files" ]; then
        print_message $BLUE "📝 提交文件类型: $message"
        print_message $CYAN "文件列表:"
        echo "$files" | while read file; do
            echo "  - $file"
        done

        git add $files
        git commit -m "$message

        print_message $GREEN "✅ 提交完成: $message"
        echo ""
    else
        print_message $YELLOW "⚠️  没有找到 $message 类型的文件"
        echo ""
    fi
}

# 主函数
main() {
    print_message $PURPLE "🚀 开始分阶段提交暂存区文件..."
    print_message $BLUE "📅 提交时间: $(date '+%Y-%m-%d %H:%M:%S')"
    echo ""

    # 第一阶段：生产配置文件
    print_message $YELLOW "=== 第一阶段：生产配置文件 ==="
    commit_by_pattern "docker-compose\.prod\.yml|nginx.*\.conf|\.env\.production|monitoring/.*\.yml|scripts/ssl/.*" "🚀 配置：生产环境配置文件"

    # 第二阶段：文档文件
    print_message $YELLOW "=== 第二阶段：文档文件 ==="
    commit_by_pattern "\.md$" "📚 文档：技术文档和报告"

    # 第三阶段：核心源码
    print_message $YELLOW "=== 第三阶段：核心源码 ==="
    commit_by_pattern "src/[^/]+/[^/]+\.py$" "💻 源码：核心应用代码"

    # 第四阶段：配置和工具
    print_message $YELLOW "=== 第四阶段：配置和工具 ==="
    commit_by_pattern "src/.*\.py$" "🔧 工具：配置和脚本"

    # 第五阶段：测试文件
    print_message $YELLOW "=== 第五阶段：测试文件 ==="
    commit_by_pattern "tests/.*\.py$" "🧪 测试：测试用例"

    # 第六阶段：其他文件
    print_message $YELLOW "=== 第六阶段：其他文件 ==="
    commit_by_pattern "." "📦 其他：剩余所有文件"

    print_message $GREEN "🎉 所有暂存区文件提交完成！"
    print_message $CYAN "📊 总计: $(git log --oneline -n 6 | wc -l) 个提交"

    # 显示最近的提交
    echo ""
    print_message $BLUE "📋 最近提交历史:"
    git log --oneline -n 6
}

# 如果直接执行脚本，运行主函数
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi