#!/bin/bash
# pip-audit环境修复脚本
# pip-audit Environment Fix Script

echo "🔧 修复pip-audit环境检测问题..."

# 检查是否在虚拟环境中
if [[ "$VIRTUAL_ENV" != "" ]]; then
    echo "✅ 检测到虚拟环境: $VIRTUAL_ENV"

    # 设置pip-audit环境变量
    export PIPAPI_PYTHON_LOCATION="$VIRTUAL_ENV/bin/python"
    echo "✅ 设置 PIPAPI_PYTHON_LOCATION=$PIPAPI_PYTHON_LOCATION"

    # 运行pip-audit
    echo "
🔍 运行pip-audit..."
    pip-audit
else
    echo "❌ 未检测到虚拟环境"
    echo "💡 请先激活虚拟环境:"
    echo "   source .venv/bin/activate"
    echo "   然后重新运行此脚本"
fi
