#!/usr/bin/env bash
# 足球预测项目 - 运行全部测试 + 覆盖率
# 该脚本运行所有测试并生成覆盖率报告

set -e  # 遇到错误时立即退出

echo "🚀 开始运行足球预测项目完整测试套件..."
echo "================================================"

# 运行所有测试
echo "📊 运行所有测试（包括单元测试和集成测试）..."
pytest tests/ \
    --cov=src \
    --cov-report=term-missing:skip-covered \
    --cov-report=html:htmlcov \
    --cov-report=term \
    -v

echo "================================================"
echo "✅ 所有测试完成！"
echo "📈 覆盖率报告已生成在 htmlcov/ 目录中"
echo "📄 打开 htmlcov/index.html 查看详细报告"