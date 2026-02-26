#!/usr/bin/env python3
"""
V32.2 Worker Efficiency Audit Plugin

功能：扫描 harvest_worker_*.log 日志，分析 Worker 效率指标

输出（过去 1 小时）：
1. 哪个 Worker 遇到的 403 错误最多
2. 哪个 Worker 的原地重试成功率最高
3. 每个 Worker 的总请求数和成功率统计

Author: Staff Site Reliability Engineer
Date: 2026-01-11
Version: V32.2 (Efficiency Audit)
"""

import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple
from collections import defaultdict

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


# ============================================================================
# 日志解析
# ============================================================================

def parse_log_line(line: str) -> Dict[str, any]:
    """解析单行日志，提取关键信息

    Returns:
        包含 timestamp, worker_id, status_code, retry_info 的字典
    """
    # 匹配时间戳: [2026-01-11 18:22:35,782]
    timestamp_match = re.search(r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
    if not timestamp_match:
        return None

    timestamp_str = timestamp_match.group(1)
    try:
        timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None

    # 匹配 Worker ID: Worker-1, Worker-2, etc.
    worker_match = re.search(r'Worker-(\d+)', line)
    worker_id = worker_match.group(1) if worker_match else "unknown"

    # 匹配 HTTP 状态码: 403, 200, 429, etc.
    status_match = re.search(r'HTTP (\d{3})', line)
    status_code = status_match.group(1) if status_match else None

    # 匹配重试信息: retry 1/3, retry 2/3, etc.
    retry_match = re.search(r'retry (\d+)/(\d+)', line)
    retry_info = {
        'current': int(retry_match.group(1)) if retry_match else None,
        'total': int(retry_match.group(2)) if retry_match else None,
    }

    # 匹配成功/失败关键词
    is_success = any(keyword in line.lower() for keyword in ['success', '成功', '✅'])
    is_error = any(keyword in line.lower() for keyword in ['error', 'failed', '错误', '❌', '403', '429'])

    return {
        'timestamp': timestamp,
        'worker_id': worker_id,
        'status_code': status_code,
        'retry_info': retry_info,
        'is_success': is_success,
        'is_error': is_error,
        'line': line.strip(),
    }


def scan_worker_logs(log_dir: str = "logs", hours: int = 1) -> List[Dict]:
    """扫描 Worker 日志文件

    Args:
        log_dir: 日志目录
        hours: 扫描最近 N 小时的日志

    Returns:
        解析后的日志条目列表
    """
    log_entries = []
    cutoff_time = datetime.now() - timedelta(hours=hours)

    # 查找所有 harvest_worker_*.log 文件
    log_files = list(Path(log_dir).glob("harvest_worker_*.log"))

    if not log_files:
        print(f"⚠️ 未找到 {log_dir}/harvest_worker_*.log 文件")
        return []

    for log_file in log_files:
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    parsed = parse_log_line(line)
                    if parsed and parsed['timestamp'] >= cutoff_time:
                        log_entries.append(parsed)
        except Exception as e:
            print(f"⚠️ 读取文件 {log_file} 失败: {e}")

    # 按时间排序
    log_entries.sort(key=lambda x: x['timestamp'])
    return log_entries


# ============================================================================
# 统计分析
# ============================================================================

def analyze_worker_efficiency(log_entries: List[Dict]) -> Dict[str, Dict]:
    """分析 Worker 效率指标

    Args:
        log_entries: 解析后的日志条目

    Returns:
        每个 Worker 的统计指标
    """
    worker_stats = defaultdict(lambda: {
        'total_requests': 0,
        'success_count': 0,
        'error_count': 0,
        '403_count': 0,
        '429_count': 0,
        'retry_attempts': 0,
        'retry_success': 0,
    })

    for entry in log_entries:
        worker_id = entry['worker_id']
        stats = worker_stats[worker_id]

        stats['total_requests'] += 1

        if entry['is_success']:
            stats['success_count'] += 1
        elif entry['is_error']:
            stats['error_count'] += 1

        # 统计特定错误码
        if entry['status_code'] == '403':
            stats['403_count'] += 1
        elif entry['status_code'] == '429':
            stats['429_count'] += 1

        # 统计重试
        if entry['retry_info']['current'] is not None:
            stats['retry_attempts'] += 1
            if entry['is_success']:
                stats['retry_success'] += 1

    return dict(worker_stats)


def print_efficiency_report(worker_stats: Dict[str, Dict], hours: int):
    """打印效率审计报告

    Args:
        worker_stats: Worker 统计指标
        hours: 扫描时间范围
    """
    print("=" * 70)
    print(f"📊 V32.2 Worker Efficiency Audit (过去 {hours} 小时)")
    print("=" * 70)

    if not worker_stats:
        print("⚠️ 没有找到 Worker 活动")
        return

    # 1. 找出 403 错误最多的 Worker
    worst_worker_403 = max(
        worker_stats.items(),
        key=lambda x: x[1]['403_count'],
        default=(None, {'403_count': 0})
    )
    print(f"\n🔴 403 错误最多的 Worker:")
    if worst_worker_403[0]:
        print(f"   Worker-{worst_worker_403[0]}: {worst_worker_403[1]['403_count']} 次")
    else:
        print("   无 403 错误")

    # 2. 找出重试成功率最高的 Worker
    best_retry_worker = None
    best_retry_rate = -1

    for worker_id, stats in worker_stats.items():
        if stats['retry_attempts'] > 0:
            retry_rate = stats['retry_success'] / stats['retry_attempts']
            if retry_rate > best_retry_rate:
                best_retry_rate = retry_rate
                best_retry_worker = worker_id

    print(f"\n🟢 重试成功率最高的 Worker:")
    if best_retry_worker:
        print(f"   Worker-{best_retry_worker}: {best_retry_rate:.1%} "
              f"({worker_stats[best_retry_worker]['retry_success']}/"
              f"{worker_stats[best_retry_worker]['retry_attempts']})")
    else:
        print("   无重试记录")

    # 3. 详细统计表
    print(f"\n📋 详细统计表:")
    print("-" * 70)
    print(f"{'Worker':<10} {'总请求':<10} {'成功':<10} {'失败':<10} {'403':<10} {'429':<10}")
    print("-" * 70)

    # 按 Worker ID 排序（跳过 unknown）
    valid_workers = [w for w in worker_stats.keys() if w != "unknown"]
    for worker_id in sorted(valid_workers, key=int):
        stats = worker_stats[worker_id]
        success_rate = stats['success_count'] / stats['total_requests'] * 100 if stats['total_requests'] > 0 else 0

        print(f"Worker-{worker_id:<4} {stats['total_requests']:<10} "
              f"{stats['success_count']:<10} {stats['error_count']:<10} "
              f"{stats['403_count']:<10} {stats['429_count']:<10} "
              f"({success_rate:.1f}%)")

    print("-" * 70)

    # 4. 汇总统计
    total_requests = sum(s['total_requests'] for s in worker_stats.values())
    total_success = sum(s['success_count'] for s in worker_stats.values())
    total_403 = sum(s['403_count'] for s in worker_stats.values())
    total_429 = sum(s['429_count'] for s in worker_stats.values())

    print(f"\n📈 汇总统计:")
    print(f"   总请求数: {total_requests}")
    print(f"   成功请求: {total_success} ({total_success/total_requests*100:.1f}%)")
    print(f"   403 错误: {total_403} ({total_403/total_requests*100:.1f}%)")
    print(f"   429 错误: {total_429} ({total_429/total_requests*100:.1f}%)")
    print("=" * 70)


# ============================================================================
# 主流程
# ============================================================================

def main():
    """主流程"""
    import argparse

    parser = argparse.ArgumentParser(description="V32.2 Worker Efficiency Audit")
    parser.add_argument('--hours', type=int, default=1,
                        help='扫描最近 N 小时的日志（默认: 1）')
    parser.add_argument('--log-dir', type=str, default='logs',
                        help='日志目录（默认: logs）')

    args = parser.parse_args()

    # 扫描日志
    log_entries = scan_worker_logs(log_dir=args.log_dir, hours=args.hours)

    if not log_entries:
        print(f"⚠️ 过去 {args.hours} 小时内没有 Worker 活动")
        return

    # 分析效率
    worker_stats = analyze_worker_efficiency(log_entries)

    # 打印报告
    print_efficiency_report(worker_stats, args.hours)


if __name__ == "__main__":
    main()
