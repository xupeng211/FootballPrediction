#!/usr/bin/env python3
"""
📊 简化数据增长监控脚本
"""

import subprocess
import time
from datetime import datetime

def get_match_count():
    """获取当前比赛总数"""
    try:
        cmd = 'psql -U postgres -d football_prediction -c "SELECT COUNT(*) FROM matches;"'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            # 提取数字 (从 "95" 或 " 95 |" 等格式中)
            import re
            count_match = re.search(r'(\d+)', result.stdout)
            if count_match:
                return int(count_match.group(1))
    except Exception as e:
        print(f"❌ 数据库查询异常: {e}")
    return None

def get_latest_log():
    """获取日志文件的最后一行"""
    try:
        cmd = 'tail -n 1 logs/backfill_clean.log'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception as e:
        return f"❌ 日志读取异常: {e}"

def main():
    print("📊 数据增长监控启动")
    print("=" * 60)

    initial_count = get_match_count()
    if initial_count is None:
        print("❌ 无法获取初始数据")
        return

    print(f"🕐 开始时间: {datetime.now().strftime('%H:%M:%S')}")
    print(f"📈 初始比赛数: {initial_count}")
    print("=" * 60)

    previous_count = initial_count

    for i in range(4):  # 4次采样
        current_count = get_match_count()
        latest_log = get_latest_log()
        current_time = datetime.now().strftime('%H:%M:%S')

        if current_count is not None:
            growth = current_count - initial_count
            incremental = current_count - previous_count
            growth_rate = f"+{growth}" if growth >= 0 else str(growth)
            incremental_rate = f"+{incremental}" if incremental >= 0 else str(incremental)
        else:
            current_count = "未知"
            growth_rate = "未知"
            incremental_rate = "未知"

        print(f"\n🔍 采样 #{i+1} [{current_time}]")
        print(f"📊 当前比赛数: {current_count}")
        print(f"📈 相对初始: {growth_rate}")
        print(f"📊 本次增量: {incremental_rate}")
        print(f"📝 最新日志: {latest_log[:100]}...")
        print("-" * 60)

        if i < 3:  # 最后一次不等待
            print(f"⏱️ 等待30秒...")
            time.sleep(30)
            previous_count = current_count if isinstance(current_count, int) else previous_count

    print(f"\n🎯 监控完成时间: {datetime.now().strftime('%H:%M:%S')}")
    print("=" * 60)

    if isinstance(current_count, int):
        total_growth = current_count - initial_count

        if total_growth > 0:
            print(f"✅ **数据增长确认**: 从 {initial_count} 涨到 {current_count} (+{total_growth})")
            print(f"📊 **增长速率**: 平均每30秒增长 {total_growth/4:.1f} 场比赛")
            verdict = "🟢 **数据收集正在正常进行**"
        elif total_growth == 0:
            print(f"⚠️ **数据停滞**: 维持在 {current_count} 场比赛")
            verdict = "🟡 **系统可能卡死或去重导致无增长**"
        else:
            print(f"❌ **数据减少**: 从 {initial_count} 减到 {current_count} ({total_growth})")
            verdict = "🔴 **数据清理异常或系统错误**"
    else:
        print(f"❌ **监控失败**: 无法获取最终数据")
        verdict = "🔴 **系统异常，需要立即检查**"

    print(f"\n🎭 **最终评估**: {verdict}")
    print("=" * 60)

if __name__ == "__main__":
    main()