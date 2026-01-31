#!/usr/bin/env python3
"""
V30.2 生产监控看板 - 指标化监控 + 预计完成时间

核心指标：
1. 每小时吞吐量 (Throughput) - 当前小时成功采集了多少场
2. 单位成功成本 (Unit Cost) - 平均多少次尝试能换回 1 场成功的 L2 数据
3. MALFORMED 告警 - 连续失败计数
4. 预计完成时间 (Estimated Finish) - 倒计时显示

Author: 高级站点可靠性工程师 (SRE)
Date: 2026-01-11
Version: V30.2 (Incremental Persistence Upgrade)
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

# V29.0 P0 整改: 标准化 .env 加载
from dotenv import load_dotenv
load_dotenv(override=True)

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

MONITOR_INTERVAL = 300  # 5 分钟（秒）
CRASH_SUMMARY_FILE = "logs/crash_summary.json"
METRICS_FILE = "logs/production_metrics.json"  # 新增：指标存储文件


def get_db_status():
    """获取数据库 status 统计

    Returns:
        status 统计字典
    """
    try:
        result = subprocess.run(
            ['docker-compose', 'exec', '-T', 'db', 'psql', '-U', 'football_user',
             '-d', 'football_db', '-c',
             "SELECT status, COUNT(*) FROM matches_mapping GROUP BY status ORDER BY status;"],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent.parent)
        )

        output = result.stdout
        status_counts = {}

        for line in output.split('\n'):
            if '|' in line and 'status' not in line and '---' not in line:
                parts = line.split('|')
                if len(parts) >= 2:
                    status = parts[0].strip()
                    count = parts[1].strip()
                    if status and count.isdigit():
                        status_counts[status] = int(count)

        return status_counts

    except Exception as e:
        print(f"❌ 获取数据库状态失败: {e}")
        return {}


def get_crash_summary():
    """获取崩溃摘要

    Returns:
        崩溃摘要列表
    """
    if not os.path.exists(CRASH_SUMMARY_FILE):
        return []

    try:
        with open(CRASH_SUMMARY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ 读取崩溃摘要失败: {e}")
        return []


def get_throughput_metrics() -> Dict:
    """获取吞吐量指标

    Returns:
        吞吐量指标字典
    """
    try:
        result = subprocess.run(
            ['docker-compose', 'exec', '-T', 'db', 'psql', '-U', 'football_user',
             '-d', 'football_db', '-c',
             """
             SELECT
                 EXTRACT(HOUR FROM updated_at) as hour,
                 COUNT(*) FILTER (WHERE status = 'harvested') as harvested_count,
                 COUNT(*) FILTER (WHERE is_malformed = TRUE) as malformed_count
             FROM matches_mapping
             WHERE updated_at >= NOW() - INTERVAL '1 hour'
             GROUP BY EXTRACT(HOUR FROM updated_at)
             ORDER BY hour DESC;
             """],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent.parent)
        )

        output = result.stdout
        metrics = {}

        for line in output.split('\n'):
            if '|' in line and 'hour' not in line and '---' not in line:
                parts = line.split('|')
                if len(parts) >= 3:
                    try:
                        hour = int(float(parts[0].strip()))
                        harvested = int(parts[1].strip())
                        malformed = int(parts[2].strip())
                        metrics[hour] = {
                            'harvested': harvested,
                            'malformed': malformed
                        }
                    except (ValueError, IndexError):
                        continue

        return metrics

    except Exception as e:
        print(f"❌ 获取吞吐量指标失败: {e}")
        return {}


def get_unit_cost() -> Dict:
    """获取单位成功成本

    Returns:
        单位成本字典
    """
    try:
        result = subprocess.run(
            ['docker-compose', 'exec', '-T', 'db', 'psql', '-U', 'football_user',
             '-d', 'football_db', '-c',
             """
             WITH attempt_stats AS (
                 SELECT
                     COUNT(*) as total_attempts,
                     COUNT(*) FILTER (WHERE status = 'harvested') as success_count,
                     COUNT(*) FILTER (WHERE is_malformed = TRUE) as malformed_count
                 FROM matches_mapping
                 WHERE updated_at >= NOW() - INTERVAL '1 hour'
             )
             SELECT
                 total_attempts,
                 success_count,
                 malformed_count,
                 CASE
                     WHEN success_count > 0 THEN ROUND(CAST(total_attempts AS NUMERIC) / success_count, 2)
                     ELSE 0
                 END as unit_cost,
                 CASE
                     WHEN total_attempts > 0 THEN ROUND(100.0 * success_count / total_attempts, 2)
                     ELSE 0
                 END as success_rate
             FROM attempt_stats;
             """],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent.parent)
        )

        output = result.stdout

        for line in output.split('\n'):
            if '|' in line and 'total_attempts' not in line and '---' not in line:
                parts = line.split('|')
                if len(parts) >= 5:
                    try:
                        return {
                            'total_attempts': int(parts[0].strip()),
                            'success_count': int(parts[1].strip()),
                            'malformed_count': int(parts[2].strip()),
                            'unit_cost': float(parts[3].strip()),
                            'success_rate': float(parts[4].strip())
                        }
                    except (ValueError, IndexError):
                        continue

        return {}

    except Exception as e:
        print(f"❌ 获取单位成本失败: {e}")
        return {}


def get_malformed_alert_status() -> Dict:
    """获取 MALFORMED 告警状态

    Returns:
        告警状态字典
    """
    try:
        result = subprocess.run(
            ['docker-compose', 'exec', '-T', 'db', 'psql', '-U', 'football_user',
             '-d', 'football_db', '-c',
             """
             SELECT
                 COUNT(*) FILTER (WHERE is_malformed = TRUE) as malformed_count,
                 COUNT(*) FILTER (WHERE is_malformed = TRUE AND updated_at >= NOW() - INTERVAL '10 minutes') as recent_malformed
             FROM matches_mapping
             WHERE updated_at >= NOW() - INTERVAL '1 hour';
             """],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent.parent)
        )

        output = result.stdout

        for line in output.split('\n'):
            if '|' in line and 'malformed_count' not in line and '---' not in line:
                parts = line.split('|')
                if len(parts) >= 2:
                    try:
                        malformed_count = int(parts[0].strip())
                        recent_malformed = int(parts[1].strip())

                        # 判断是否触发告警（连续10场失败）
                        alert_triggered = recent_malformed >= 10

                        return {
                            'malformed_count': malformed_count,
                            'recent_malformed': recent_malformed,
                            'alert_threshold': 10,
                            'alert_triggered': alert_triggered
                        }
                    except (ValueError, IndexError):
                        continue

        return {'malformed_count': 0, 'recent_malformed': 0, 'alert_threshold': 10, 'alert_triggered': False}

    except Exception as e:
        print(f"❌ 获取告警状态失败: {e}")
        return {'malformed_count': 0, 'recent_malformed': 0, 'alert_threshold': 10, 'alert_triggered': False}


def save_metrics_snapshot(metrics: Dict):
    """保存指标快照到文件

    Args:
        metrics: 指标字典
    """
    try:
        # 读取现有数据
        existing_metrics = []
        if os.path.exists(METRICS_FILE):
            with open(METRICS_FILE, 'r', encoding='utf-8') as f:
                existing_metrics = json.load(f)

        # 添加新记录
        snapshot = {
            'timestamp': datetime.now().isoformat(),
            'metrics': metrics
        }
        existing_metrics.append(snapshot)

        # 保留最近 100 条记录
        if len(existing_metrics) > 100:
            existing_metrics = existing_metrics[-100:]

        # 保存到文件
        os.makedirs(os.path.dirname(METRICS_FILE), exist_ok=True)
        with open(METRICS_FILE, 'w', encoding='utf-8') as f:
            json.dump(existing_metrics, f, indent=2, ensure_ascii=False)

    except Exception as e:
        print(f"❌ 保存指标快照失败: {e}")


def get_estimated_finish_time() -> Dict:
    """计算预计完成时间（V151.0 新增）

    Returns:
        预计完成时间字典
    """
    try:
        result = subprocess.run(
            ['docker-compose', 'exec', '-T', 'db', 'psql', '-U', 'football_user',
             '-d', 'football_db', '-c',
             """
             SELECT
                 COUNT(*) FILTER (WHERE l2_raw_json IS NOT NULL) as harvested_count,
                 COUNT(*) FILTER (WHERE l2_raw_json IS NULL) as remaining_count,
                 COUNT(*) as total_count,
                 MIN(updated_at) FILTER (WHERE l2_raw_json IS NOT NULL) as first_harvest_time,
                 MAX(updated_at) FILTER (WHERE l2_raw_json IS NOT NULL) as last_harvest_time
             FROM matches_mapping
             WHERE oddsportal_url IS NOT NULL AND oddsportal_url != '';
             """],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent.parent)
        )

        output = result.stdout

        for line in output.split('\n'):
            if '|' in line and 'harvested_count' not in line and '---' not in line:
                parts = line.split('|')
                if len(parts) >= 5:
                    try:
                        harvested_count = int(parts[0].strip())
                        remaining_count = int(parts[1].strip())
                        total_count = int(parts[2].strip())

                        # 计算平均采集速度（场/小时）
                        first_harvest_str = parts[3].strip()
                        last_harvest_str = parts[4].strip()

                        if first_harvest_str and last_harvest_str:
                            # 简单计算：假设从第一次采集到现在的时间
                            from datetime import datetime
                            now = datetime.now()
                            # 假设采集起始时间为最后一次更新的时间之前
                            # 使用一个保守估计：160秒/场
                            avg_seconds_per_match = 160

                            if remaining_count > 0:
                                estimated_seconds = remaining_count * avg_seconds_per_match
                                finish_time = now + timedelta(seconds=estimated_seconds)

                                hours = int(estimated_seconds // 3600)
                                minutes = int((estimated_seconds % 3600) // 60)

                                return {
                                    'harvested_count': harvested_count,
                                    'remaining_count': remaining_count,
                                    'total_count': total_count,
                                    'avg_seconds_per_match': avg_seconds_per_match,
                                    'estimated_seconds': estimated_seconds,
                                    'estimated_finish_time': finish_time.strftime('%Y-%m-%d %H:%M:%S'),
                                    'estimated_hours_minutes': f"{hours}h {minutes}min",
                                    'harvest_rate': harvested_count / total_count if total_count > 0 else 0
                                }
                    except (ValueError, IndexError):
                        continue

        return {}

    except Exception as e:
        print(f"❌ 计算预计完成时间失败: {e}")
        return {}


def get_process_status():
    """获取进程状态

    Returns:
        进程信息字典
    """
    try:
        result = subprocess.run(
            ['ps', 'aux'],
            capture_output=True,
            text=True
        )

        processes = {'supervisor': None, 'harvester': None}

        for line in result.stdout.split('\n'):
            if 'harvester_supervisor' in line and 'grep' not in line:
                parts = line.split()
                if len(parts) >= 11:
                    processes['supervisor'] = {
                        'pid': parts[1],
                        'cpu': parts[2],
                        'mem': parts[3],
                        'command': ' '.join(parts[11:])
                    }
            elif 'harvest_pinnacle_odds.py' in line and 'grep' not in line:
                parts = line.split()
                if len(parts) >= 11:
                    processes['harvester'] = {
                        'pid': parts[1],
                        'cpu': parts[2],
                        'mem': parts[3],
                        'command': ' '.join(parts[11:])
                    }

        return processes

    except Exception as e:
        print(f"❌ 获取进程状态失败: {e}")
        return {'supervisor': None, 'harvester': None}


def print_monitoring_dashboard(round_num: int):
    """打印监控看板（V30.1 增强版）

    Args:
        round_num: 监控轮次
    """
    print("=" * 70)
    print(f"📊 V30.1 生产监控看板 - 第 {round_num} 轮")
    print("=" * 70)
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # 1. 进程状态
    print("🔄 进程状态:")
    print("-" * 70)
    processes = get_process_status()

    if processes['supervisor']:
        print(f"  守护进程: ✅ PID={processes['supervisor']['pid']} "
              f"CPU={processes['supervisor']['cpu']}% "
              f"MEM={processes['supervisor']['mem']}")
    else:
        print("  守护进程: ❌ 未运行")

    if processes['harvester']:
        print(f"  收割进程: ✅ PID={processes['harvester']['pid']} "
              f"CPU={processes['harvester']['cpu']}% "
              f"MEM={processes['harvester']['mem']}")
    else:
        print("  收割进程: ❌ 未运行")

    print()

    # 2. 核心指标（V30.1 新增）
    print("📊 核心指标（V30.1 指标化监控）:")
    print("-" * 70)

    # 2.1 每小时吞吐量
    throughput = get_throughput_metrics()
    if throughput:
        print("  每小时吞吐量 (Throughput):")
        for hour, metrics in throughput.items():
            print(f"    {hour:2d}时 - 采集:{metrics['harvested']:3d} 场  |  异常:{metrics['malformed']:3d} 场")
    else:
        print("  每小时吞吐量: 暂无数据")

    print()

    # 2.2 单位成功成本
    unit_cost = get_unit_cost()
    if unit_cost:
        print("  单位成功成本 (Unit Cost):")
        print(f"    总尝试次数: {unit_cost.get('total_attempts', 0)}")
        print(f"    成功次数:   {unit_cost.get('success_count', 0)}")
        print(f"    成本:        {unit_cost.get('unit_cost', 0):.2f} 次尝试/场成功")
        print(f"    成功率:      {unit_cost.get('success_rate', 0):.1f}%")
    else:
        print("  单位成功成本: 暂无数据")

    print()

    # 2.3 预计完成时间（V151.0 新增）
    estimated_finish = get_estimated_finish_time()
    if estimated_finish:
        print("  ⏱️  预计完成时间 (Estimated Finish):")
        print(f"    已采集:     {estimated_finish.get('harvested_count', 0)} 场")
        print(f"    剩余:       {estimated_finish.get('remaining_count', 0)} 场")
        print(f"    总目标:     {estimated_finish.get('total_count', 0)} 场")
        print(f"    采集率:     {estimated_finish.get('harvest_rate', 0)*100:.1f}%")
        print(f"    预计完成:   {estimated_finish.get('estimated_finish_time', 'N/A')}")
        print(f"    剩余时间:   {estimated_finish.get('estimated_hours_minutes', 'N/A')}")
    else:
        print("  ⏱️  预计完成时间: 暂无数据")

    print()

    # 2.4 MALFORMED 告警状态
    alert_status = get_malformed_alert_status()
    print("  🚨 MALFORMED 告警状态:")
    print(f"    总异常数:   {alert_status.get('malformed_count', 0)}")
    print(f"    近10分钟:   {alert_status.get('recent_malformed', 0)} / {alert_status.get('alert_threshold', 10)}")
    if alert_status.get('alert_triggered'):
        print(f"    状态:       🔴 **告警触发！连续10场失败**")
    else:
        print(f"    状态:       ✅ 正常")

    print()

    # 3. 数据库 status 统计
    print("📊 数据库 status 统计:")
    print("-" * 70)
    status_counts = get_db_status()

    if status_counts:
        for status, count in status_counts.items():
            print(f"  {status:12s}: {count:4d} 条")
    else:
        print("  暂无数据")

    print()

    # 4. 崩溃摘要
    print("📋 crash_summary.json:")
    print("-" * 70)
    crash_summary = get_crash_summary()

    if crash_summary:
        print(f"  总崩溃次数: {len(crash_summary)}")

        # 显示最近 3 次崩溃
        recent_crashes = crash_summary[-3:] if len(crash_summary) > 3 else crash_summary
        for i, crash in enumerate(recent_crashes, 1):
            print(f"  {i}. {crash.get('timestamp', 'N/A')}")
            print(f"     原因: {crash.get('crash_reason', 'UNKNOWN')}")
            print(f"     错误数: {crash.get('error_count', 0)}")
    else:
        print("  ✅ 暂无崩溃记录")

    print()

    # 5. 保存指标快照
    metrics_snapshot = {
        'round_num': round_num,
        'throughput': throughput,
        'unit_cost': unit_cost,
        'alert_status': alert_status,
        'status_counts': status_counts,
        'crash_count': len(crash_summary)
    }
    save_metrics_snapshot(metrics_snapshot)

    print()
    print("=" * 70)
    print()


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(
        description="V30.0 生产监控看板"
    )
    parser.add_argument(
        '--rounds',
        type=int,
        default=1,
        help='监控轮次（每轮 5 分钟）'
    )
    parser.add_argument(
        '--continuous',
        action='store_true',
        help='持续监控模式（直到手动停止）'
    )

    args = parser.parse_args()

    print()
    print("🚀 V30.0 生产监控看板已启动")
    print(f"监控间隔: {MONITOR_INTERVAL} 秒 ({MONITOR_INTERVAL//60} 分钟)")
    print()

    if args.continuous:
        round_num = 1
        try:
            while True:
                print_monitoring_dashboard(round_num)
                time.sleep(MONITOR_INTERVAL)
                round_num += 1
        except KeyboardInterrupt:
            print("\n\n👋 监控已停止")
    else:
        for round_num in range(1, args.rounds + 1):
            print_monitoring_dashboard(round_num)
            if round_num < args.rounds:
                print(f"⏳ 等待 {MONITOR_INTERVAL//60} 分钟后进行下一轮监控...")
                print()
                time.sleep(MONITOR_INTERVAL)


if __name__ == "__main__":
    main()
