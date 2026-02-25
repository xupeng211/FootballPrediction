#!/bin/bash
# V71.000 - Stress Test Monitor
# Monitors system resources during the 100-match stress test

LOG_DIR="/home/user/projects/FootballPrediction/logs/stress_test_v71_000"
METRICS_FILE="$LOG_DIR/metrics.json"

mkdir -p "$LOG_DIR"

echo "[V71.000] Stress Test Monitor Starting..."
echo "[V71.000] Monitoring system resources during test..."

# Start monitoring in background
(
    while true; do
        # Record timestamp
        TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
        
        # Get browser process count
        BROWSER_COUNT=$(ps aux | grep -E "(playwright|chromium|node.*orchestrator)" | grep -v grep | wc -l)
        
        # Get memory usage (MB)
        MEM_USAGE=$(free -m | awk 'NR==2{print $3,$2,$3/$2*100}')
        
        # Get orchestrator process if running
        ORCH_PID=$(cat /home/user/projects/FootballPrediction/var/run/orchestrator.pid 2>/dev/null || echo "none")
        ORCH_MEM="0"
        if [ "$ORCH_PID" != "none" ] && ps -p "$ORCH_PID" > /dev/null 2>&1; then
            ORCH_MEM=$(ps -p "$ORCH_PID" -o rss= | awk '{print $1/1024}')  # Convert KB to MB
        fi
        
        # Record to metrics file
        echo "{\"timestamp\":\"$TS\",\"browser_count\":$BROWSER_COUNT,\"orchestrator_pid\":\"$ORCH_PID\",\"orchestrator_mem_mb\":$ORCH_MEM}" >> "$METRICS_FILE"
        
        sleep 5
    done
) &
MONITOR_PID=$!

echo "[V71.000] Monitor PID: $MONITOR_PID"
echo "[V71.000] Logging to: $METRICS_FILE"

# Store monitor PID for cleanup
echo "$MONITOR_PID" > "$LOG_DIR/monitor.pid"

echo "[V71.000] Monitor active. Press Ctrl+C to stop."
wait $MONITOR_PID
