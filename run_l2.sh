#!/bin/bash
# L2采集器启动脚本 - 确保正确的Python路径和导入

# 确保脚本在项目根目录运行
cd "$(dirname "$0")"
export PYTHONPATH=$(pwd)
echo "🚀 PYTHONPATH set to: $PYTHONPATH"

# 验证Python路径设置
if python -c "import sys; print('✅ Python path:', sys.path[0])"; then
    echo "✅ Python导入路径设置成功"
else
    echo "❌ Python导入路径设置失败"
    exit 1
fi

# 验证核心模块导入
if python -c "from src.collectors.l2_parser import EnhancedL2Parser; print('✅ L2解析器导入成功')"; then
    echo "✅ 核心模块导入验证通过"
else
    echo "❌ 核心模块导入失败"
    exit 1
fi

# 运行真实冒烟测试 (限制 1 场，开启详细日志)
echo "🔥 启动L2采集器进行真实冒烟测试..."
echo "📊 测试目标: API -> 解析器 -> 数据库完整链路"
echo "🎯 测试数量: 1场比赛"
echo ""

python scripts/real_l2_smoke_test.py --limit 1 --log-level DEBUG