#!/bin/bash
# 快速测试脚本

echo "⚡ 运行快速测试..."

# 只运行关键测试
pytest tests/unit/ -v -m "smoke or critical" --maxfail=3

echo "✅ 快速测试完成！"
