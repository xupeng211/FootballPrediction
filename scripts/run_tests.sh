#!/bin/bash
# 运行测试脚本

set -e

echo "🧪 开始运行测试套件..."

# 清理缓存
echo "🧹 清理测试缓存..."
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name ".pytest_cache" -type d -exec rm -rf {} + 2>/dev/null || true

# 运行单元测试
echo "🔍 运行单元测试..."
pytest tests/unit/ -v --cov=src --cov-report=html --cov-report=term-missing --cov-fail-under=30

# 运行集成测试
echo "🔗 运行集成测试..."
pytest tests/integration/ -v --maxfail=5

# 生成测试报告
echo "📊 生成测试报告..."
pytest --html=reports/test_report.html --self-contained-html

echo "✅ 测试完成！"
echo "📈 覆盖率报告: htmlcov/index.html"
echo "📄 HTML测试报告: reports/test_report.html"
