#!/usr/bin/env bash
# 足球预测项目 - 仅运行集成测试
# 该脚本只运行标记为 integration 的测试

set -e  # 遇到错误时立即退出

echo "🔗 开始运行足球预测项目集成测试..."
echo "========================================"

# 仅运行集成测试
echo "📊 运行集成测试（有外部依赖）..."
pytest tests/ \
    -m integration \
    --cov=src \
    --cov-report=term-missing:skip-covered \
    --cov-report=html:htmlcov_integration \
    -v

echo "========================================"
echo "✅ 集成测试完成！"
echo "📈 覆盖率报告已生成在 htmlcov_integration/ 目录中"
