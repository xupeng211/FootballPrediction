#!/bin/bash
# Phase 7 覆盖率改进循环
# AI-Driven Coverage Improvement Loop

echo "🔄 启动 AI 驱动的覆盖率改进循环..."

# 创建日志目录
mkdir -p logs/phase7

# 运行改进周期
python scripts/phase7_ai_coverage_loop.py > logs/phase7/$(date +%Y%m%d_%H%M%S).log 2>&1

# 检查结果
if [ $? -eq 0 ]; then
    echo "✅ 覆盖率改进周期完成"

    # 运行快速测试验证
    make test-quick

    # 生成覆盖率摘要
    make coverage-local
else
    echo "❌ 覆盖率改进失败，检查日志"
fi
