#!/usr/bin/env bash
# 足球预测项目 - 仅运行单元测试
# 该脚本只运行标记为 unit 的测试

set -e  # 遇到错误时立即退出

echo "🔬 开始运行足球预测项目单元测试..."
echo "========================================"

# 仅运行单元测试
echo "📊 运行单元测试（无外部依赖）..."
pytest tests/ \
    -m unit \
    --cov=src \
    --cov-report=term-missing:skip-covered \
    --cov-report=html:htmlcov_unit \
    -v

echo "========================================"
echo "✅ 单元测试完成！"
echo "📈 覆盖率报告已生成在 htmlcov_unit/ 目录中"
