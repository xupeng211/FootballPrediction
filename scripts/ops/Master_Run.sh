#!/bin/bash

# ============================================================================
# V102.500 PRODUCTION HARVESTER MASTER CONTROL
# 9900X Optimized - 20 Concurrent Matrix
# ============================================================================

# 1. 环境准备
export PROJECT_ROOT="/home/user/projects/FootballPrediction"
export PROXY_URL="http://172.25.16.1:7890"
export MAX_CONCURRENT=20  # 释放 9900X 的多核性能
export LOG_FILE="$PROJECT_ROOT/logs/harvest_$(date +%Y%m%d_%H%M%S).log"

# 开启代理 (WSL2 环境)
export http_proxy=$PROXY_URL
export https_proxy=$PROXY_URL

# 激活虚拟环境
source $PROJECT_ROOT/venv/bin/activate

# 2. 清理旧日志与缓存
mkdir -p $PROJECT_ROOT/logs
echo "[$(date)] Cleaning up environment..."
rm -rf /tmp/playwright_reporting_* # 3. 核心收割指令
echo "------------------------------------------------------------"
echo "  🚀 STARTING FULL SCALE HARVEST (V102.000 Engine)"
echo "  🖥️ CPU: i9-9900X | Workers: $MAX_CONCURRENT"
echo "  📁 Log: $LOG_FILE"
echo "------------------------------------------------------------"

# 运行主程序并实时监控
# 我们通过环境变量直接注入 top 联赛，覆盖 config 里的默认值（可选）
node $PROJECT_ROOT/scripts/ops/v91_000_main.js 2>&1 | tee $LOG_FILE

# 4. 数据一致性终检 (物理核对)
echo ""
echo "------------------------------------------------------------"
echo "  🏁 HARVEST FINISHED. RUNNING DB INTEGRITY CHECK..."
echo "------------------------------------------------------------"

# 直接在容器内运行统计 SQL
docker exec football_prediction_db psql -U football_user -d football_db -c \
"SELECT provider_name, count(*),
        round(avg(value)::numeric, 2) as avg_odds,
        count(CASE WHEN (raw_data->>'is_moved')::boolean = true THEN 1 END) as moved_count
 FROM temporal_metric_records
 WHERE created_at > now() - interval '1 hour'
 GROUP BY provider_name
 ORDER BY count DESC;"

echo "------------------------------------------------------------"
echo "  ✅ MISSION ACCOMPLISHED."