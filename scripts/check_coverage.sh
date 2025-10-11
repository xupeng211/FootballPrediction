#!/bin/bash
# 快速检查测试覆盖率

cd "$(dirname "$0")/.." || exit 1

echo "正在运行测试覆盖率分析..."
echo ""

# 运行pytest覆盖率测试（简洁模式）
python -m pytest tests/ \
  --cov=src \
  --cov-report=term-missing \
  --cov-report=html:htmlcov \
  -q \
  --tb=no \
  --no-header \
  2>&1 | tail -50

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 详细HTML报告已生成: htmlcov/index.html"
echo "📄 完整分析报告: COVERAGE_ANALYSIS_REPORT.md"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
