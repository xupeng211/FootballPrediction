#!/bin/bash
# 智能依赖管理：检测变更并提供交互式指导

echo "🔍 智能依赖管理系统"
echo "======================"

# 检测最近变更中的新导入
echo "正在分析最近提交中的新导入..."
NEW_IMPORTS=$(git diff HEAD~1 --name-only --diff-filter=ACMRTUXB -- '*.py' | xargs grep -h "^import\|^from" 2>/dev/null | \
              grep -v "^from \." | grep -v "^from src" | \
              awk '{print $2}' | cut -d'.' -f1 | sort -u | \
              grep -v -E "^(os|sys|json|datetime|pathlib|typing|unittest|pytest|fastapi|sqlalchemy|pydantic|logging|collections|itertools|functools|re|math|random|time|uuid|hashlib|base64|csv|io|threading|multiprocessing|asyncio|queue|socket|urllib|http|email|xml|sqlite3|tempfile|shutil|glob|fnmatch|pickle|json|decimal|fractions|statistics)$")

if [ -n "$NEW_IMPORTS" ]; then
    echo ""
    echo "📦 检测到可能的新依赖包："
    for pkg in $NEW_IMPORTS; do
        echo "  - $pkg"
    done

    echo ""
    echo "⚠️  重要提醒！"
    echo "这些包可能需要在requirements/中声明。"
    echo ""
    echo "请阅读："
    echo "  1. CLAUDE.md - 了解依赖管理文化"
    echo "  2. .ai-reminder.md - 查看操作指南"
    echo ""
    echo "推荐的添加方式："
    echo "  python scripts/dependency/add_dependency.py <package> --category <core|api|ml|dev>"
    echo ""
else
    echo "✅ 没有检测到新的外部依赖。"
fi

# 检查requirements/目录变更
echo ""
echo "正在检查requirements/目录变更..."
if git diff HEAD~1 --name-only | grep -q "requirements/"; then
    echo "📝 检测到requirements/文件变更："
    git diff HEAD~1 --name-only | grep "requirements/" | while read file; do
        echo "  - $file"
    done

    # 检查是否有.in变更但没有.lock变更
    IN_CHANGED=$(git diff HEAD~1 --name-only | grep "requirements.*\.in$" | wc -l)
    LOCK_CHANGED=$(git diff HEAD~1 --name-only | grep "requirements.*\.lock$" | wc -l)

    if [ $IN_CHANGED -gt 0 ] && [ $LOCK_CHANGED -eq 0 ]; then
        echo ""
        echo "⚠️  警告：检测到.in文件变更但没有对应的.lock文件变更！"
        echo "   请运行："
        echo "   make lock-deps"
        echo "   make verify-deps"
    fi
else
    echo "✅ requirements/目录没有变更。"
fi

echo ""
echo "💡 如需帮助，请查看："
echo "   - CLAUDE.md (项目AI编程指南)"
echo "   - .ai-reminder.md (依赖管理提醒)"
echo "   - requirements/README.md (依赖管理方案)"