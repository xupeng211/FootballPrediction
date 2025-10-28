#!/bin/bash

# CI质量门禁脚本
# CI Quality Gate Script

set -e

echo "🚀 CI质量门禁检查开始..."

# 1. 环境检查
echo "📋 步骤 1/4: 环境检查"
python --version
echo "✅ Python环境正常"

# 2. 语法检查
echo "📝 步骤 2/4: 代码语法检查"
if ! python -m py_compile src/**/*.py; then
    echo "❌ 语法检查失败"
    exit 1
fi
echo "✅ 语法检查通过"

# 3. 质量检查
echo "🛡️ 步骤 3/4: 质量守护检查"
if ! python scripts/quality_guardian_check.py; then
    echo "❌ 质量守护检查失败"
    exit 1
fi
echo "✅ 质量守护检查通过"

# 4. 类型检查
echo "🔍 步骤 4/4: 类型检查"
if ! make type-check; then
    echo "❌ 类型检查失败"
    exit 1
fi
echo "✅ 类型检查通过"

echo ""
echo "🎉 CI质量门禁全部通过！"
echo "✅ 代码质量达标，可以安全部署"