#!/bin/bash
# 设置pre-commit hooks

echo "🔧 设置pre-commit hooks..."

# 检查是否安装了pre-commit
if ! command -v pre-commit &> /dev/null; then
    echo "安装pre-commit..."
    pip install pre-commit
fi

# 安装hooks
echo "安装hooks..."
pre-commit install

# 测试hooks
echo "测试hooks..."
pre-commit run --all-files

echo "✅ Pre-commit hooks设置完成！"
echo ""
echo "现在每次提交代码时都会自动运行以下检查："
echo "  - Python语法检查"
echo "  - 代码格式检查"
echo "  - 类型检查"
echo "  - YAML/JSON格式检查"
