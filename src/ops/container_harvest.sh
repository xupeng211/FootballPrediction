#!/bin/bash
# V20.8 容器原生收割脚本
# Environment: Docker Container Native
# Purpose: Execute harvest without permission issues

set -e

# 强制环境变量（显式指定，不依赖 .env）
export DB_HOST=db
export DB_NAME=football_db
export DB_USER=football_user
export DB_PASSWORD=football_pass
export FOOTBALL_DB_HOST=db
export PYTHONPATH=/app:$PYTHONPATH

# 切换到工作目录
cd /app

# 执行收割（日志输出到挂载卷）
echo "[$(date)] V20.8 容器原生收割启动..." >> /app/data/backfill_stats/V20.8_CONTAINER_HARVEST.log
python3 /app/src/ops/backfill_v20.8_scorched_earth.py >> /app/data/backfill_stats/V20.8_CONTAINER_HARVEST.log 2>&1

echo "[$(date)] V20.8 收割完成" >> /app/data/backfill_stats/V20.8_CONTAINER_HARVEST.log
