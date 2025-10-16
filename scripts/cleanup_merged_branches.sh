#!/bin/bash
# 安全删除已合并分支的脚本

set -e

echo "=== Git 分支清理工具 ==="
echo "⚠️  此脚本将删除已经合并到 main 的所有分支（除了 main 和 develop）"
echo ""

# 确保在 main 分支
current_branch=$(git branch --show-current)
if [ "$current_branch" != "main" ]; then
    echo "❌ 请先切换到 main 分支"
    echo "   git checkout main"
    exit 1
fi

# 拉取最新代码
echo "📥 更新 main 分支..."
git pull origin main

# 找出已合并的分支
echo ""
echo "=== 查找已合并的分支 ==="
merged_branches=$(git branch --merged main | grep -v "^\*" | grep -v "main" | grep -v "master" | grep -v "develop" || true)

if [ -z "$merged_branches" ]; then
    echo "✅ 没有找到已合并的分支需要删除"
    exit 0
fi

# 显示将要删除的分支
echo "📋 以下分支将被删除："
echo "$merged_branches"
echo ""

# 确认
read -p "确定要删除这些分支吗？(y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ 取消操作"
    exit 1
fi

# 删除本地分支
echo ""
echo "🗑️  删除本地分支..."
for branch in $merged_branches; do
    echo "  删除分支: $branch"
    git branch -d "$branch"
done

echo ""
echo "✅ 清理完成！"
echo ""
echo "💡 提示："
echo "   - 如果还想删除未合并的分支，请使用: git branch -D <branch-name>"
echo "   - 清理远程分支: git remote prune origin"
