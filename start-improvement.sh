#!/bin/bash
# 持续改进引擎快速启动脚本

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

echo "🚀 启动持续改进引擎..."
echo "项目目录: $PROJECT_ROOT"

# 运行持续改进引擎
python3 scripts/continuous_improvement_engine.py

echo ""
echo "📊 查看改进报告:"
ls -la improvement-report-*.md 2>/dev/null | tail -1

echo ""
echo "📈 监控改进状态:"
python3 scripts/improvement_monitor.py