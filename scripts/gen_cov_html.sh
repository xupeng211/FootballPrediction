#!/usr/bin/env bash
# 足球预测项目 - 生成 HTML 覆盖率报告
# 该脚本生成详细的 HTML 覆盖率报告

set -e  # 遇到错误时立即退出

echo "📊 开始生成足球预测项目 HTML 覆盖率报告..."
echo "=============================================="

# 运行测试并生成 HTML 覆盖率报告
echo "📈 运行测试并生成 HTML 报告..."
pytest tests/ \
    --cov=src \
    --cov-report=html:htmlcov \
    --cov-report=term-missing \
    -v

echo "=============================================="
echo "✅ HTML 覆盖率报告生成完成！"
echo "📄 报告位置: htmlcov/index.html"
echo "🌐 使用浏览器打开 htmlcov/index.html 查看详细覆盖率信息"