#!/bin/bash
# 清理重复的脚本
# 用途：删除或整合功能重复的脚本
# 作者：AI Assistant
# 日期：2025-10-05

set -e

SCRIPTS_DIR="/home/user/projects/FootballPrediction/scripts"
cd "$SCRIPTS_DIR"

echo "🧹 开始清理重复脚本..."
echo "================================================"

# 创建整合目录
mkdir -p archive/syntax_fixers archive/import_fixers archive/linting_fixers

echo "📦 1/3 归档重复的语法修复脚本..."
# 保留 smart_syntax_fixer.py，归档其他
mv batch_fix_syntax.py archive/syntax_fixers/ 2>/dev/null || true
mv batch_syntax_fixer.py archive/syntax_fixers/ 2>/dev/null || true
mv fix_all_syntax.py archive/syntax_fixers/ 2>/dev/null || true
mv global_syntax_fixer.py archive/syntax_fixers/ 2>/dev/null || true
mv fix_batch_syntax_errors.py archive/syntax_fixers/ 2>/dev/null || true
mv fix_remaining_syntax.py archive/syntax_fixers/ 2>/dev/null || true
mv fix_syntax_ast.py archive/syntax_fixers/ 2>/dev/null || true
mv fix_test_syntax.py archive/syntax_fixers/ 2>/dev/null || true
mv formatting_fixer.py archive/syntax_fixers/ 2>/dev/null || true

# 保留 smart_syntax_fixer.py 到 fix_tools/
mv smart_syntax_fixer.py fix_tools/fix_syntax.py 2>/dev/null || true

echo "📦 2/3 归档重复的导入修复脚本..."
# 保留最新的 fix_imports.py
mv fix_tools/fix_imports_v2.py archive/import_fixers/ 2>/dev/null || true
mv fix_tools/fix_final_imports.py archive/import_fixers/ 2>/dev/null || true
mv fix_tools/fix_remaining_imports.py archive/import_fixers/ 2>/dev/null || true
mv cleanup_imports.py archive/import_fixers/ 2>/dev/null || true
mv variable_import_fixer.py archive/import_fixers/ 2>/dev/null || true

echo "📦 3/3 归档重复的 linting 修复脚本..."
# 保留 fix_linting.py
mv fix_tools/fix_lint_issues.py archive/linting_fixers/ 2>/dev/null || true
mv fix_tools/fix_linting_errors.py archive/linting_fixers/ 2>/dev/null || true
mv fix_tools/fix_remaining_lint.py archive/linting_fixers/ 2>/dev/null || true

echo ""
echo "🗑️  清理 scripts/tests/ 目录..."
# scripts/tests/ 中的测试应该在 tests/ 目录
if [ -d "tests" ]; then
    echo "  发现 scripts/tests/ 目录，这些测试应该移到 tests/ 目录"
    mv tests archive/misplaced_tests 2>/dev/null || true
fi

echo ""
echo "✅ 清理完成！"
echo "================================================"
echo ""
echo "📊 清理统计："
echo "  - 语法修复: $(find archive/syntax_fixers/ -name '*.py' 2>/dev/null | wc -l) 个归档"
echo "  - 导入修复: $(find archive/import_fixers/ -name '*.py' 2>/dev/null | wc -l) 个归档"
echo "  - Linting: $(find archive/linting_fixers/ -name '*.py' 2>/dev/null | wc -l) 个归档"
echo ""
echo "⚠️  保留的核心脚本："
echo "  - fix_tools/fix_syntax.py (整合所有语法修复)"
echo "  - fix_tools/fix_imports.py (整合所有导入修复)"
echo "  - fix_tools/fix_linting.py (整合所有 linting 修复)"
echo ""
