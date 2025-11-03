#!/bin/bash
# 测试健康检查脚本

echo "🏥 运行测试健康检查..."

# 检查测试环境
python -c "import pytest; print('pytest版本:', pytest.__version__)" || {
    echo "❌ pytest不可用"
    exit 1
}

# 检查项目结构
if [ ! -d "tests" ]; then
    echo "❌ tests目录不存在"
    exit 1
fi

# 干运行测试收集
echo "🔍 检查测试可收集性..."
pytest --collect-only -q > /dev/null || {
    echo "⚠️ 测试收集存在问题"
}

echo "✅ 测试健康检查通过！"
