#!/usr/bin/env python3
"""
实时监控影子守护进程输出
"""
import subprocess
import time
import sys
import os
from pathlib import Path

def monitor_shadow_daemon():
    """监控影子守护进程输出"""
    print("🔍 开始监控影子守护进程...")

    # 查找影子守护进程
    try:
        result = subprocess.run(['pgrep', '-f', 'shadow_daemon_production.py'],
                              capture_output=True, text=True)
        if result.returncode != 0:
            print("❌ 未找到影子守护进程")
            return

        pid = result.stdout.strip()
        print(f"✅ 找到影子守护进程 PID: {pid}")

        # 监控stdout和stderr (如果可能的话)
        # 由于进程已经启动，我们检查日志文件或数据目录

    except Exception as e:
        print(f"❌ 监控失败: {e}")

    # 检查是否有输出文件生成
    data_dir = Path("data")
    logs_dir = Path("logs")

    print("\n📁 检查数据目录...")
    if data_dir.exists():
        for file in data_dir.rglob("*"):
            if file.is_file():
                print(f"  📄 {file.relative_to(data_dir)} ({file.stat().st_size} bytes)")

    print("\n📋 检查日志目录...")
    if logs_dir.exists():
        for file in logs_dir.rglob("*"):
            if file.is_file():
                print(f"  📄 {file.relative_to(logs_dir)} (修改时间: {time.ctime(file.stat().st_mtime)})")

    # 尝试读取最新的日志内容
    automation_log = logs_dir / "automation_24h.log"
    if automation_log.exists():
        print(f"\n📊 自动化日志最后10行:")
        try:
            with open(automation_log, 'r') as f:
                lines = f.readlines()
                for line in lines[-10:]:
                    print(f"  {line.strip()}")
        except Exception as e:
            print(f"  ❌ 读取失败: {e}")

if __name__ == "__main__":
    monitor_shadow_daemon()