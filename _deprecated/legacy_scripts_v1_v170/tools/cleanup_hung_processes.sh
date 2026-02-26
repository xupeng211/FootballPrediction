#!/bin/bash
# V84.600 - 一键清理残留进程脚本
# =====================================
# 用于清理可能导致系统卡死的残留 node/chromium 进程

echo "[V84.600] ========================================"
echo "[V84.600] 残留进程清理工具"
echo "[V84.600] ========================================"
echo ""

# 查找残留进程
echo "[1/4] 扫描残留进程..."
NODE_PROCS=$(ps aux | grep -E "node|chromium|playwright|headless" | grep -v grep | grep -v "vscode-server" | grep -v "gemini" | grep -v "mcp-server")

if [ -z "$NODE_PROCS" ]; then
    echo "  ✓ 未发现残留进程"
else
    echo "  ! 发现以下进程:"
    echo "$NODE_PROCS"
    echo ""
    echo "[2/4] 提取进程 PID..."
    PIDS=$(echo "$NODE_PROCS" | awk '{print $2}')
    echo "  目标 PID: $PIDS"
    echo ""

    echo "[3/4] 终止进程..."
    for PID in $PIDS; do
        if [ "$PID" != "" ]; then
            kill -9 "$PID" 2>/dev/null && echo "  ✓ 已终止 PID $PID" || echo "  ✗ 无法终止 PID $PID"
        fi
    done
    echo ""
fi

echo "[4/4] 验证清理结果..."
REMAINING=$(ps aux | grep -E "node|chromium|playwright|headless" | grep -v grep | grep -v "vscode-server" | grep -v "gemini" | grep -v "mcp-server" | wc -l)

if [ "$REMAINING" -eq 0 ]; then
    echo "  ✓ 清理完成 - 无残留进程"
else
    echo "  ! 仍有 $REMAINING 个进程残留（可能是系统进程）"
fi

echo ""
echo "[V84.600] ========================================"
echo "[V84.600] 清理完成"
echo "[V84.600] ========================================"
