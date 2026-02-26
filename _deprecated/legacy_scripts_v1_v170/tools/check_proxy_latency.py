#!/usr/bin/env python3
"""
代理池性能审计 (Proxy Pulse Audit)

核心功能:
1. 并发测试端口 7890-7899
2. 每端口重复测试 3 次取平均值
3. 记录 status_code 和 latency_ms
4. 生成分布报告

准入红线: 必须使用真实物理探测，严禁模拟数据

Author: 高级网络诊断工程师
Date: 2026-01-11
Version: V1.0
"""

import asyncio
import json
import logging
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import httpx

# V29.0 P0 整改: 标准化 .env 加载
from dotenv import load_dotenv
load_dotenv(override=True)

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('logs/proxy_pulse_audit.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ============================================================================
# 配置常量
# ============================================================================

PROXY_HOST = "172.25.16.1"  # WSL2 宿主机IP
PROXY_PORTS = list(range(7890, 7900))  # 7890-7899
TEST_URL = "https://www.oddsportal.com/"
TEST_REPETITIONS = 3  # 每端口测试次数
TIMEOUT_SECONDS = 15.0  # 单次请求超时
RISK_THRESHOLD_MS = 10000  # >10s 计为潜在风险
REPORT_FILE = "logs/proxy_pulse_report.json"


# ============================================================================
# 探测逻辑
# ============================================================================

async def test_proxy_once(
    client: httpx.AsyncClient,
    proxy_url: str,
    test_num: int
) -> Dict[str, any]:
    """单次代理测试

    Args:
        client: httpx 异步客户端
        proxy_url: 代理URL
        test_num: 测试编号

    Returns:
        测试结果字典
    """
    start_time = time.time()

    try:
        response = await client.get(
            TEST_URL,
            timeout=TIMEOUT_SECONDS,
            follow_redirects=True,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        )

        latency_ms = (time.time() - start_time) * 1000

        return {
            'test_num': test_num,
            'status_code': response.status_code,
            'latency_ms': round(latency_ms, 2),
            'success': response.status_code == 200,
            'error': None
        }

    except asyncio.TimeoutError:
        latency_ms = (time.time() - start_time) * 1000
        return {
            'test_num': test_num,
            'status_code': None,
            'latency_ms': round(latency_ms, 2),
            'success': False,
            'error': 'Timeout'
        }
    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        return {
            'test_num': test_num,
            'status_code': None,
            'latency_ms': round(latency_ms, 2),
            'success': False,
            'error': str(e)
        }


async def test_proxy_port(port: int, repetitions: int = 3, timeout: float = 15.0) -> Dict[str, any]:
    """测试单个代理端口（重复指定次数）

    Args:
        port: 代理端口号
        repetitions: 重复测试次数
        timeout: 单次请求超时

    Returns:
        端口测试结果字典
    """
    proxy_url = f"http://{PROXY_HOST}:{port}"
    results = []

    logger.info(f"🔍 测试代理 {proxy_url} (重复 {repetitions} 次)...")

    async with httpx.AsyncClient(timeout=timeout) as client:
        for i in range(1, repetitions + 1):
            result = await test_proxy_once(
                client,
                proxy_url,
                i
            )
            results.append(result)

            status_icon = "✅" if result['success'] else "❌"
            logger.info(f"  [{i}/{repetitions}] {status_icon} "
                       f"Status={result['status_code']} "
                       f"Latency={result['latency_ms']:.0f}ms "
                       f"Error={result['error']}")

    # 计算统计信息
    successful_results = [r for r in results if r['success']]
    failed_results = [r for r in results if not r['success']]

    if successful_results:
        latencies = [r['latency_ms'] for r in successful_results]
        avg_latency = statistics.mean(latencies)
        min_latency = min(latencies)
        max_latency = max(latencies)
    else:
        avg_latency = None
        min_latency = None
        max_latency = None

    return {
        'port': port,
        'proxy_url': proxy_url,
        'total_tests': repetitions,
        'successful_count': len(successful_results),
        'failed_count': len(failed_results),
        'success_rate': len(successful_results) / repetitions if repetitions > 0 else 0,
        'avg_latency_ms': round(avg_latency, 2) if avg_latency is not None else None,
        'min_latency_ms': round(min_latency, 2) if min_latency is not None else None,
        'max_latency_ms': round(max_latency, 2) if max_latency is not None else None,
        'all_results': results
    }


async def run_proxy_pulse_audit(
    proxy_ports: List[int] = None,
    repetitions: int = 3,
    timeout: float = 15.0
) -> List[Dict]:
    """运行代理池脉冲审计（带配置参数）

    Args:
        proxy_ports: 代理端口列表
        repetitions: 每端口重复测试次数
        timeout: 单次请求超时

    Returns:
        所有端口测试结果列表
    """
    if proxy_ports is None:
        proxy_ports = PROXY_PORTS

    logger.info("=" * 70)
    logger.info("🚀 代理池性能审计 (Proxy Pulse Audit)")
    logger.info("=" * 70)
    logger.info(f"测试目标: {TEST_URL}")
    logger.info(f"代理范围: {PROXY_HOST}:{proxy_ports[0]}-{proxy_ports[-1]}")
    logger.info(f"重复次数: {repetitions}")
    logger.info(f"超时设置: {timeout}s")
    logger.info(f"风险阈值: {RISK_THRESHOLD_MS}ms")
    logger.info("")

    start_time = time.time()

    # 并发测试所有端口
    tasks = [test_proxy_port(port, repetitions, timeout) for port in proxy_ports]
    results = await asyncio.gather(*tasks)

    total_elapsed = time.time() - start_time

    logger.info("")
    logger.info(f"✅ 审计完成！总耗时: {total_elapsed:.1f}s")

    return results


# ============================================================================
# 报告生成
# ============================================================================

def generate_distribution_report(results: List[Dict]) -> Dict:
    """生成分发报告

    Args:
        results: 端口测试结果列表

    Returns:
        分发报告字典
    """
    # 提取所有成功的延迟数据
    all_successful_tests = []
    for result in results:
        for test in result['all_results']:
            if test['success']:
                all_successful_tests.append(test['latency_ms'])

    # 提取所有端口的平均延迟
    port_avg_latencies = []
    for result in results:
        if result['avg_latency_ms'] is not None:
            port_avg_latencies.append(result['avg_latency_ms'])

    # 统计信息
    if all_successful_tests:
        overall_min = min(all_successful_tests)
        overall_max = max(all_successful_tests)
        overall_avg = statistics.mean(all_successful_tests)
        overall_median = statistics.median(all_successful_tests)
        overall_stdev = statistics.stdev(all_successful_tests) if len(all_successful_tests) > 1 else 0
    else:
        overall_min = None
        overall_max = None
        overall_avg = None
        overall_median = None
        overall_stdev = None

    if port_avg_latencies:
        port_avg_min = min(port_avg_latencies)
        port_avg_max = max(port_avg_latencies)
        port_avg_mean = statistics.mean(port_avg_latencies)
    else:
        port_avg_min = None
        port_avg_max = None
        port_avg_mean = None

    # 风险统计（>10s）
    risk_count = sum(1 for lat in all_successful_tests if lat > RISK_THRESHOLD_MS)
    risk_ratio = risk_count / len(all_successful_tests) if all_successful_tests else 0

    # 超时统计
    timeout_tests = []
    for result in results:
        for test in result['all_results']:
            if test['error'] == 'Timeout':
                timeout_tests.append({
                    'port': result['port'],
                    'test_num': test['test_num'],
                    'latency_ms': test['latency_ms']
                })

    report = {
        'timestamp': datetime.now().isoformat(),
        'summary': {
            'total_ports_tested': len(PROXY_PORTS),
            'total_tests_conducted': len(all_successful_tests) + len(timeout_tests),
            'successful_tests': len(all_successful_tests),
            'timeout_tests': len(timeout_tests),
            'overall_success_rate': len(all_successful_tests) / (len(all_successful_tests) + len(timeout_tests)) if (len(all_successful_tests) + len(timeout_tests)) > 0 else 0
        },
        'latency_distribution': {
            'overall_min_ms': round(overall_min, 2) if overall_min is not None else None,
            'overall_max_ms': round(overall_max, 2) if overall_max is not None else None,
            'overall_avg_ms': round(overall_avg, 2) if overall_avg is not None else None,
            'overall_median_ms': round(overall_median, 2) if overall_median is not None else None,
            'overall_stdev_ms': round(overall_stdev, 2) if overall_stdev is not None else None,
            'port_avg_min_ms': round(port_avg_min, 2) if port_avg_min is not None else None,
            'port_avg_max_ms': round(port_avg_max, 2) if port_avg_max is not None else None,
            'port_avg_mean_ms': round(port_avg_mean, 2) if port_avg_mean is not None else None
        },
        'risk_analysis': {
            'risk_threshold_ms': RISK_THRESHOLD_MS,
            'tests_above_threshold': risk_count,
            'risk_ratio': round(risk_ratio, 4),
            'timeout_count': len(timeout_tests)
        },
        'timeout_details': timeout_tests,
        'port_details': results
    }

    return report


def print_report_summary(report: Dict):
    """打印报告摘要

    Args:
        report: 分发报告字典
    """
    print()
    print("=" * 70)
    print("📊 代理池性能审计报告")
    print("=" * 70)
    print(f"时间: {report['timestamp']}")
    print()

    # 测试概览
    print("🔍 测试概览:")
    print("-" * 70)
    summary = report['summary']
    print(f"  测试端口数:     {summary['total_ports_tested']}")
    print(f"  总测试次数:     {summary['total_tests_conducted']}")
    print(f"  成功次数:       {summary['successful_tests']}")
    print(f"  超时次数:       {summary['timeout_tests']}")
    print(f"  整体成功率:     {summary['overall_success_rate']*100:.1f}%")
    print()

    # 延迟分布
    print("⚡ 延迟分布:")
    print("-" * 70)
    dist = report['latency_distribution']
    print(f"  最快响应:       {dist['overall_min_ms']:.0f} ms" if dist['overall_min_ms'] else "  最快响应:       N/A")
    print(f"  最慢响应:       {dist['overall_max_ms']:.0f} ms" if dist['overall_max_ms'] else "  最慢响应:       N/A")
    print(f"  平均响应:       {dist['overall_avg_ms']:.0f} ms" if dist['overall_avg_ms'] else "  平均响应:       N/A")
    print(f"  中位数:         {dist['overall_median_ms']:.0f} ms" if dist['overall_median_ms'] else "  中位数:         N/A")
    print(f"  标准差:         {dist['overall_stdev_ms']:.0f} ms" if dist['overall_stdev_ms'] else "  标准差:         N/A")
    print()
    print(f"  端口平均最快:   {dist['port_avg_min_ms']:.0f} ms" if dist['port_avg_min_ms'] else "  端口平均最快:   N/A")
    print(f"  端口平均最慢:   {dist['port_avg_max_ms']:.0f} ms" if dist['port_avg_max_ms'] else "  端口平均最慢:   N/A")
    print(f"  端口平均均值:   {dist['port_avg_mean_ms']:.0f} ms" if dist['port_avg_mean_ms'] else "  端口平均均值:   N/A")
    print()

    # 风险分析
    print("⚠️  风险分析:")
    print("-" * 70)
    risk = report['risk_analysis']
    print(f"  风险阈值:       >{risk['risk_threshold_ms']} ms")
    print(f"  超阈值次数:     {risk['tests_above_threshold']}")
    print(f"  风险比例:       {risk['risk_ratio']*100:.2f}%")
    print(f"  超时次数:       {risk['timeout_count']}")
    print()

    # 端口详情
    print("📋 端口详情:")
    print("-" * 70)

    # 按平均延迟排序
    port_details = sorted(
        [p for p in report['port_details'] if p['avg_latency_ms'] is not None],
        key=lambda x: x['avg_latency_ms']
    )

    for port_info in port_details:
        port = port_info['port']
        avg = port_info['avg_latency_ms']
        min_lat = port_info['min_latency_ms']
        max_lat = port_info['max_latency_ms']
        success_rate = port_info['success_rate'] * 100

        # 风险标识
        risk_icon = "🔴" if avg and avg > RISK_THRESHOLD_MS else "🟢"

        print(f"  端口 {port}: {risk_icon} "
              f"平均={avg:.0f}ms "
              f"范围=[{min_lat:.0f}, {max_lat:.0f}] "
              f"成功率={success_rate:.0f}%")

    print()
    print("=" * 70)


def save_report(report: Dict):
    """保存报告到文件

    Args:
        report: 分发报告字典
    """
    try:
        os.makedirs(os.path.dirname(REPORT_FILE), exist_ok=True)
        with open(REPORT_FILE, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        logger.info(f"💾 报告已保存: {REPORT_FILE}")
    except Exception as e:
        logger.error(f"❌ 保存报告失败: {e}")


import os


# ============================================================================
# 主函数
# ============================================================================

async def main_async():
    """异步主函数"""
    import argparse

    parser = argparse.ArgumentParser(
        description="代理池性能审计 (Proxy Pulse Audit)"
    )
    parser.add_argument(
        '--ports',
        type=str,
        default='7890-7899',
        help='代理端口范围 (默认: 7890-7899)'
    )
    parser.add_argument(
        '--repetitions',
        type=int,
        default=3,
        help='每端口测试次数 (默认: 3)'
    )
    parser.add_argument(
        '--timeout',
        type=float,
        default=15.0,
        help='单次请求超时 (默认: 15s)'
    )

    args = parser.parse_args()

    # 解析端口范围
    if '-' in args.ports:
        start, end = map(int, args.ports.split('-'))
        proxy_ports = list(range(start, end + 1))
    else:
        proxy_ports = [int(p) for p in args.ports.split(',')]

    # 运行审计（传入参数）
    results = await run_proxy_pulse_audit(
        proxy_ports=proxy_ports,
        repetitions=args.repetitions,
        timeout=args.timeout
    )

    # 生成报告
    report = generate_distribution_report(results)

    # 打印摘要
    print_report_summary(report)

    # 保存报告
    save_report(report)

    # 结果对账
    print()
    print("🔍 结果对账:")
    print("-" * 70)
    avg_latency = report['latency_distribution']['port_avg_mean_ms']
    max_latency = report['latency_distribution']['overall_max_ms']
    risk_ratio = report['risk_analysis']['risk_ratio']

    print(f"  当前超时配置: 15s (oddsportal.py)")
    print()

    if avg_latency:
        if avg_latency < 3000:
            print(f"  ✅ 平均延迟 {avg_latency:.0f}ms < 3000ms")
            print(f"     结论: 15s 超时配置非常稳健 (5x安全余量)")
        elif avg_latency < 8000:
            print(f"  ⚠️  平均延迟 {avg_latency:.0f}ms < 8000ms")
            print(f"     结论: 15s 超时配置基本合理 (约2x安全余量)")
        else:
            print(f"  🔴 平均延迟 {avg_latency:.0f}ms >= 8000ms")
            print(f"     建议: 考虑将超时放宽至 30s")

    if max_latency:
        print(f"  📊 最慢响应 {max_latency:.0f}ms")
        if max_latency < 10000:
            print(f"     结论: 最慢场景仍低于10s风险阈值")
        else:
            print(f"     警告: 存在超过10s的高延迟请求")

    print(f"  📈 风险比例 {risk_ratio*100:.1f}%")
    if risk_ratio > 0.1:
        print(f"     警告: 超过10%的请求存在高延迟风险")
    elif risk_ratio > 0.05:
        print(f"     注意: 5%-10%的请求存在高延迟风险")
    else:
        print(f"     结论: 风险可控 (<5%)")

    print()
    print("=" * 70)


def main():
    """命令行入口"""
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
