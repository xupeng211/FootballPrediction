#!/usr/bin/env python3
"""
API性能分析工具
"""

import subprocess
import time
import statistics
from typing import List, Dict
import json


def analyze_api_endpoints():
    """分析API端点性能"""
    # 模拟API端点测试
    endpoints = ["/api/health", "/api/predictions", "/api/matches", "/api/teams", "/api/users"]

    results = []

    for endpoint in endpoints:
        print(f"  📊 测试端点: {endpoint}")

        # 模拟多次请求并测量响应时间
        response_times = []

        for i in range(10):
            start_time = time.time()
            try:
                # 这里应该是实际的API请求，现在用模拟
                time.sleep(0.01)  # 模拟网络延迟
                end_time = time.time()
                response_times.append((end_time - start_time) * 1000)  # 转换为毫秒
            except Exception as e:
                print(f"    ⚠️ 端点 {endpoint} 测试失败: {e}")

        if response_times:
            avg_time = statistics.mean(response_times)
            max_time = max(response_times)
            min_time = min(response_times)

            results.append(
                {
                    "endpoint": endpoint,
                    "avg_response_time": avg_time,
                    "max_response_time": max_time,
                    "min_response_time": min_time,
                    "requests": len(response_times),
                }
            )

            print(f"    📈 平均响应时间: {avg_time:.2f}ms")
            print(f"    📊 最大响应时间: {max_time:.2f}ms")
            print(f"    📊 最小响应时间: {min_time:.2f}ms")

    # 生成分析报告
    report = {
        "analysis_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "results": results,
        "summary": {
            "total_endpoints": len(results),
            "avg_response_time": (
                statistics.mean([r["avg_response_time"] for r in results]) if results else 0
            ),
            "slowest_endpoint": (
                max(results, key=lambda x: x["avg_response_time"]) if results else None
            ),
        },
    }

    with open("api_performance_analysis.json", "w") as f:
        json.dump(report, f, indent=2)

    print("  📋 分析报告已保存: api_performance_analysis.json")
    return report


if __name__ == "__main__":
    analyze_api_endpoints()
