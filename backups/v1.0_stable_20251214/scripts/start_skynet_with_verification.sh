#!/bin/bash
# 天网计划启动脚本 - 包含验证和监控
# CEO强制版

set -e

cd /home/user/projects/FootballPrediction

echo "🚀 天网计划全域采集启动"
echo "📂 工作目录: $(pwd)"
echo "⏰ 启动时间: $(date)"
echo ""

# 1. 清理旧的进度文件
echo "🧹 清理旧进度文件..."
rm -f logs/coverage_progress.json
rm -f logs/failed_leagues.log
rm -f logs/skynet.pid
echo "  ✅ 清理完成"

# 2. 运行预启动验证
echo ""
echo "🔍 预启动验证..."
python scripts/verify_skynet_realtime.py
if [ $? -ne 0 ]; then
    echo ""
    echo "⚠️  验证发现问题，但将继续启动..."
else
    echo "  ✅ 验证通过"
fi

# 3. 确保日志目录存在
echo ""
echo "📁 准备日志目录..."
mkdir -p logs

# 4. 启动脚本
echo ""
echo "🚀 启动天网计划..."
nohup python scripts/launch_robust_coverage.py > logs/robust_coverage.log 2>&1 &

# 获取进程ID
PID=$!
echo $PID > logs/skynet.pid

# 5. 等待启动
echo ""
echo "⏳ 等待脚本启动..."
sleep 3

# 6. 验证启动状态
if ps -p $PID > /dev/null; then
    echo "✅ 天网计划已启动"
    echo ""
    echo "🆔 进程ID: $PID"
    echo "📄 主日志: logs/robust_coverage.log"
    echo ""
    echo "📊 监控命令:"
    echo "  • 实时日志: tail -f logs/robust_coverage.log"
    echo "  • 检查进度: python scripts/verify_skynet_realtime.py"
    echo "  • 监控进程: ps aux | grep launch_robust"
    echo "  • 终止进程: kill $PID"
    echo ""

    # 7. 等待并显示启动日志
    echo "📝 启动日志 (最近10行):"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    tail -n 10 logs/robust_coverage.log
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    # 8. 启动实时监控（可选）
    read -p "是否启动实时监控? (y/N): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "📊 启动实时监控..."
        watch -n 5 'echo "$(date)" && tail -n 5 logs/robust_coverage.log'
    fi
else
    echo "❌ 启动失败，请检查日志: logs/robust_coverage.log"
    exit 1
fi
