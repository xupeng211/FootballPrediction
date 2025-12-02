#!/usr/bin/env python3
"""
FBref数据管道健康检查脚本
运营总监监控系统
"""

import subprocess
import time
from datetime import datetime
from pathlib import Path


def check_system_health():
    """检查系统健康状态"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] 🏥 FBref数据管道健康检查")

    # 检查磁盘空间
    disk_usage = subprocess.run(["df", "-h", "/"], capture_output=True, text=True)
    disk_line = (
        disk_usage.stdout.split("\n")[1]
        if len(disk_usage.stdout.split("\n")) > 1
        else "N/A"
    )
    print(f"磁盘状态: {disk_line}")

    # 检查内存使用
    memory = subprocess.run(["free", "-h"], capture_output=True, text=True)
    mem_line = (
        memory.stdout.split("\n")[1] if len(memory.stdout.split("\n")) > 1 else "N/A"
    )
    print(f"内存状态: {mem_line}")

    # 检查最近的日志
    log_dir = Path(__file__).parent.parent / "logs"
    if log_dir.exists():
        recent_logs = list(log_dir.glob("*.log"))[-3:]  # 最近3个日志文件
        print(f"最近日志文件: {[f.name for f in recent_logs]}")

    print("✅ 系统健康检查完成\n")


if __name__ == "__main__":
    check_system_health()
