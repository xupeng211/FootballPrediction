#!/bin/bash

# 开发环境设置脚本
# Phase 3: 开发环境自动化

echo "🚀 设置开发环境..."

# 检查Python版本
python_version=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
echo "Python版本: $python_version"

if [[ "$python_version" < "3.11" ]]; then
    echo "⚠️ 建议使用Python 3.11+"
fi

# 安装pre-commit
echo "📦 安装pre-commit..."
pip install pre-commit

# 安装开发依赖
echo "📦 安装开发依赖..."
pip install pytest pytest-cov pytest-asyncio ruff black

# 安装pre-commit钩子
echo "🔧 安装pre-commit钩子..."
pre-commit install

# 运行快速质量检查验证设置
echo "🧪 验证质量检查设置..."
python scripts/quality_gate.py --quick-mode

echo ""
echo "✅ 开发环境设置完成！"
echo ""
echo "📋 可用的命令："
echo "  pre-commit run --all-files              # 运行所有pre-commit检查"
echo "  python scripts/quality_gate.py          # 运行完整质量门禁"
echo "  python scripts/quality_gate.py --quick-mode  # 运行快速检查"
echo "  pytest tests/unit/api/test_adapters.py  # 运行API适配器测试"
echo "  pytest tests/unit/utils/test_dict_utils_enhanced.py  # 运行核心工具测试"
echo ""
echo "🎯 质量目标："
echo "  - API适配器测试: 100% 通过率 ✅"
echo "  - 核心工具测试: 100% 通过率 ✅"
echo "  - 整体覆盖率: 40%+ 🎯"
echo "  - 代码质量: 8.0+/10 ✅"