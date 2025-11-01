#!/bin/bash
#
# GitHub标签分析工具
# 用于分析仓库中所有标签的使用情况
#

REPO="xupeng211/FootballPrediction"

echo "=== GitHub标签使用情况分析 ==="
echo "仓库: $REPO"
echo "时间: $(date)"
echo ""

# 获取所有标签
echo "📊 获取标签列表..."
labels=$(gh label list --repo "$REPO" --limit 100 --json name | jq -r '.[].name')

echo ""
echo "=== 详细分析结果 ==="
echo ""

used_labels=()
unused_labels=()

# 检查每个标签
for label in $labels; do
    count=$(gh issue list --repo "$REPO" --label "$label" 2>/dev/null | wc -l)

    if [ "$count" -eq 0 ]; then
        unused_labels+=("$label")
        echo "❌ 未使用: $label"
    else
        used_labels+=("$label")
        echo "✅ 使用中: $label ($count个Issues)"
    fi
done

echo ""
echo "=== 统计汇总 ==="
echo ""
echo "📈 使用中的标签 (${#used_labels[@]}个):"
for label in "${used_labels[@]}"; do
    echo "  - $label"
done

echo ""
echo "⚠️ 未使用的标签 (${#unused_labels[@]}个):"
for label in "${unused_labels[@]}"; do
    echo "  - $label"
done

echo ""
echo "💡 清理建议:"
if [ ${#unused_labels[@]} -gt 0 ]; then
    echo "  建议删除 ${#unused_labels[@]} 个未使用的标签以保持标签体系精简"
    echo ""
    echo "删除命令示例:"
    for label in "${unused_labels[@]}"; do
        echo "  gh label delete \"$label\" --repo \"$REPO\" --yes"
    done
else
    echo "  ✅ 所有标签都在使用中，无需清理"
fi