#!/bin/bash
# FootballPrediction 远程分支清理脚本
# 生成时间: 2026-02-22
# 警告: 此脚本会删除远程分支，请谨慎操作！

set -e

echo "=========================================="
echo "FootballPrediction 远程分支清理工具"
echo "=========================================="
echo ""

# 配置 - 设置为 true 启用实际删除
DRY_RUN=${DRY_RUN:-true}

# 统计信息
TOTAL_BRANCHES=$(git branch -r | wc -l)
BUGFIX_REPORTS=$(git branch -r | grep "chore/bugfix-report" | wc -l)
DEPENDABOT=$(git branch -r | grep "dependabot" | wc -l)
BACKUP=$(git branch -r | grep "backup" | wc -l)

echo "📊 当前状态:"
echo "  - 远程分支总数: $TOTAL_BRANCHES"
echo "  - chore/bugfix-report 自动生成分支: $BUGFIX_REPORTS"
echo "  - dependabot 分支: $DEPENDABOT"
echo "  - backup 分支: $BACKUP"
echo ""

if [ "$DRY_RUN" = true ]; then
    echo "⚠️  干运行模式 (DRY_RUN=true)"
    echo "   设置 DRY_RUN=false 以执行实际删除"
    echo ""
fi

# 1. 删除 chore/bugfix-report 自动生成分支 (289个)
echo "🗑️  清理 chore/bugfix-report 分支..."
deleted_count=0
for branch in $(git branch -r | grep "chore/bugfix-report" | sed 's/origin\///'); do
    if [ "$DRY_RUN" = true ]; then
        echo "  [DRY-RUN] 将删除: origin/$branch"
    else
        git push origin --delete "$branch" 2>/dev/null && echo "  ✅ 已删除: $branch" || echo "  ❌ 删除失败: $branch"
    fi
    ((deleted_count++))
done
echo "  共 $deleted_count 个 bugfix-report 分支"
echo ""

# 2. 删除 backup 分支 (2个)
echo "🗑️  清理 backup 分支..."
for branch in $(git branch -r | grep "backup" | sed 's/origin\///'); do
    if [ "$DRY_RUN" = true ]; then
        echo "  [DRY-RUN] 将删除: origin/$branch"
    else
        git push origin --delete "$branch" 2>/dev/null && echo "  ✅ 已删除: $branch" || echo "  ❌ 删除失败: $branch"
    fi
done
echo ""

# 3. 可选: 删除 dependabot 分支 (10个)
echo "⚠️  dependabot 分支 (可选清理)..."
echo "  这些分支可能还有依赖更新价值，建议手动审查"
for branch in $(git branch -r | grep "dependabot" | sed 's/origin\///'); do
    echo "  - $branch"
done
echo ""

# 4. 可选: 删除 develop 分支
echo "⚠️  develop 分支状态:"
echo "  - 最新提交: fa322a071 (Phase 4 - Real World Integration Complete)"
echo "  - 落后 main: 251 个提交"
echo "  - 建议: 重命名或删除 (开发工作流已迁移到 main)"
echo ""

echo "=========================================="
echo "📋 清理摘要"
echo "=========================================="
if [ "$DRY_RUN" = true ]; then
    echo "干运行完成，未执行实际删除"
    echo ""
    echo "要执行实际清理，运行:"
    echo "  DRY_RUN=false ./scripts/ops/cleanup_remote_branches.sh"
else
    echo "清理完成"
fi
echo ""

# 预期结果
echo "📈 清理后预期:"
echo "  - 分支数: 381 → ~80 (减少 301 个)"
echo "  - 保留: main + feature/* + fix/* 等开发分支"
