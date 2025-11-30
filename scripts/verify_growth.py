#!/usr/bin/env python3
"""
📊 数据增长速率验证脚本
监控 backfill 进程的数据增长情况
"""

import asyncio
import sys
import time
from datetime import datetime
from pathlib import Path
import subprocess
import re

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


async def get_match_count():
    """获取当前比赛总数"""
    try:
        cmd = [
            "docker-compose",
            "exec",
            "-T",
            "db",
            "psql",
            "-U",
            "postgres",
            "-d",
            "football_prediction",
            "-c",
            "SELECT COUNT(*) FROM matches;",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

        if result.returncode == 0:
            count_str = result.stdout.strip()
            count = int(re.findall(r"\d+", count_str)[0])
            return count
        else:
            print(f"❌ 数据库查询失败: {result.stderr}")
            return None
    except Exception:
        print(f"❌ 获取比赛数量异常: {e}")
        return None


def get_latest_log():
    """获取日志文件的最后一行"""
    try:
        cmd = [
            "docker-compose",
            "exec",
            "-T",
            "app",
            "tail",
            "-n",
            "1",
            "logs/backfill_clean.log",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

        if result.returncode == 0:
            return result.stdout.strip()
        else:
            return f"❌ 日志读取失败: {result.stderr.strip()}"
    except Exception:
        return f"❌ 日志读取异常: {e}"


def extract_date_from_log(log_line):
    """从日志中提取处理日期"""
    patterns = [
        r"处理 (\d{4}-\d{2}-\d{2})",  # 处理 2022-01-01
        r"(\d{4}-\d{2}-\d{2})",  # 任何YYYY-MM-DD格式
    ]

    for pattern in patterns:
        match = re.search(pattern, log_line)
        if match:
            return match.group(1)

    return "未知日期"


def extract_progress_from_log(log_line):
    """从日志中提取进度信息"""
    patterns = [
        r"\[(\d+)/1429\]\s*\(([^)]+)\)",  # [19/1429] (1.3%)
        r"(\d{4}-\d{2}-\d{2})\s*采集完成",  # 2022-01-01 采集完成
    ]

    for pattern in patterns:
        match = re.search(pattern, log_line)
        if match:
            return match.group(0)

    return "未知进度"


async def main():
    """主监控循环"""
    print("📊 数据增长速率监控启动")
    print("=" * 60)

    initial_count = await get_match_count()
    if initial_count is None:
        print("❌ 无法获取初始数据，监控终止")
        return

    print(f"🕐 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📈 初始比赛数: {initial_count}")
    print("=" * 60)

    previous_count = initial_count

    for i in range(4):  # 4次采样，每次间隔30秒，共2分钟
        # 获取当前数据
        current_count = await get_match_count()
        latest_log = get_latest_log()
        current_time = datetime.now().strftime("%H:%M:%S")

        # 计算增量
        if current_count is not None:
            growth = current_count - initial_count
            incremental = current_count - previous_count
            growth_rate = f"+{growth}" if growth >= 0 else str(growth)
            incremental_rate = (
                f"+{incremental}" if incremental >= 0 else str(incremental)
            )
        else:
            current_count = "未知"
            growth_rate = "未知"
            incremental_rate = "未知"

        # 提取关键信息
        current_date = extract_date_from_log(latest_log)
        current_progress = extract_progress_from_log(latest_log)

        # 输出采样结果
        print(f"\n🔍 采样 #{i + 1} [{current_time}]")
        print(f"📊 当前比赛总数: {current_count}")
        print(f"📈 相对初始: {growth_rate}")
        print(f"📊 本次增量: {incremental_rate}")
        print(f"📅 处理日期: {current_date}")
        print(f"⏳ 进度信息: {current_progress}")
        print(f"📝 最新日志: {latest_log[:100]}...")
        print("-" * 60)

        if i < 3:  # 最后一次不等待
            print("⏱️ 等待30秒后进行下次采样...")
            time.sleep(30)
            previous_count = (
                current_count if isinstance(current_count, int) else previous_count
            )

    # 最终评估
    print(f"\n🎯 监控完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    if isinstance(current_count, int):
        total_growth = current_count - initial_count

        if total_growth > 0:
            print(
                f"✅ **数据增长确认**: 从 {initial_count} 涨到 {current_count} (+{total_growth})"
            )
            print(f"📊 **增长速率**: 平均每30秒增长 {total_growth / 4:.1f} 场比赛")
            verdict = "🟢 **数据收集正在正常进行**"
        elif total_growth == 0:
            print(f"⚠️ **数据停滞**: 维持在 {current_count} 场比赛")
            verdict = "🟡 **系统可能卡死或去重导致无增长**"
        else:
            print(
                f"❌ **数据减少**: 从 {initial_count} 减到 {current_count} ({total_growth})"
            )
            verdict = "🔴 **数据清理异常或系统错误**"
    else:
        print("❌ **监控失败**: 无法获取最终数据")
        verdict = "🔴 **系统异常，需要立即检查**"

    print(f"\n🎭 **最终评估**: {verdict}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
