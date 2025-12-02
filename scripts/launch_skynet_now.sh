#!/bin/bash
# 天网计划启动脚本 - CEO命令

cd /home/user/projects/FootballPrediction

echo "🚀 天网计划全域采集启动"
echo "📂 工作目录: $(pwd)"
echo "⏰ 启动时间: $(date)"

# 确保日志目录存在
mkdir -p logs

# 启动脚本
nohup python scripts/launch_robust_coverage.py > logs/robust_coverage.log 2>&1 &

# 获取进程ID
PID=$!
echo "✅ 天网计划已启动"
echo "🆔 进程ID: $PID"
echo "📄 日志文件: logs/robust_coverage.log"
echo ""
echo "📊 监控命令:"
echo "  tail -f logs/robust_coverage.log"
echo "  ps aux | grep launch_robust"
echo ""
echo "⚠️  如需停止: kill $PID"

# 保存PID到文件
echo $PID > logs/skynet.pid
