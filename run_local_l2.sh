#!/bin/bash
# 本机运行L2详情采集脚本
# Local L2 Details Collection Script

echo "🚀 启动本机L2详情采集任务..."

# 设置环境变量
export DATABASE_URL="postgresql://postgres:postgres-dev-password@localhost:5432/football_prediction"
export PYTHONPATH="/home/user/projects/FootballPrediction/src:$PYTHONPATH"

# 运行L2脚本
python3 src/jobs/run_l2_details.py

echo "✅ L2任务完成"