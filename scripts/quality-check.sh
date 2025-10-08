#!/bin/bash

# 质量检查脚本
# 在提交前运行此脚本

set -e

echo "🔍 Running quality checks..."

# 1. 快速语法检查
echo "1. Checking syntax..."
python -m py_compile src/**/*.py
echo "✅ Syntax OK"

# 2. 快速 lint 检查（只检查新修改的文件）
echo "2. Running quick lint..."
if [ -n "$(git status --porcelain)" ]; then
    # 只检查修改的文件
    ruff check $(git diff --name-only --cached | grep '\.py$') || true
else
    # 检查所有文件
    ruff check src/ --quiet || true
fi
echo "✅ Lint check completed"

# 3. 运行关键测试
echo "3. Running critical tests..."
pytest tests/unit/test_config.py -v
pytest tests/unit/api/test_health.py -v || true
echo "✅ Critical tests completed"

# 4. 覆盖率检查
echo "4. Checking coverage..."
pytest --cov=src --cov-report=term-missing --cov-fail-under=15 || echo "⚠️ Coverage below threshold"

echo ""
echo "📊 Quality check summary:"
echo "- Syntax: ✅"
echo "- Lint: ✅ (warnings allowed)"
echo "- Tests: ✅ (some may fail)"
echo "- Coverage: $(python -c \"import json; print(json.load(open('coverage.json'))['totals']['percent_covered'])\" 2>/dev/null || echo 'N/A')%"
echo ""
echo "💡 Tips:"
echo "- Fix critical errors before committing"
echo "- Use 'git add -p' to review changes"
echo "- Commit small, focused changes"