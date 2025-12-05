#!/bin/bash
# 本机运行L1赛季回填脚本
# Local L1 Season Backfill Script

echo "🚀 启动本机L1赛季回填任务..."

# 设置环境变量
export DATABASE_URL="postgresql://postgres:postgres-dev-password@localhost:5432/football_prediction"
export PYTHONPATH="/home/user/projects/FootballPrediction/src:$PYTHONPATH"

# 运行L1脚本
python3 src/jobs/run_season_backfill.py

echo "✅ L1任务完成"