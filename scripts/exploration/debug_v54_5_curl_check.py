#!/usr/bin/env python3
"""
V54.5 网络诊断 - 检查 OddsPortal 响应
====================================

使用 curl 检查服务器是否正常响应
"""

import subprocess
import json

# 测试 URL
test_urls = [
    ("主页", "https://www.oddsportal.com"),
    ("详情页", "https://www.oddsportal.com/football/england/premier-league/manchester-city-brentford/"),
]

print("=" * 60)
print("V54.5 网络诊断报告")
print("=" * 60)
print()

for name, url in test_urls:
    print(f"检查: {name} - {url}")
    print("-" * 60)

    # 使用 curl 获取响应头
    cmd = [
        "curl", "-s", "-I", "-L",
        "-H", "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        url
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        print(result.stdout)

        # 检查状态码
        lines = result.stdout.split('\n')
        for line in lines:
            if line.startswith('HTTP/'):
                status_code = line.split()[1]
                print(f"  状态码: {status_code}")

    except Exception as e:
        print(f"  错误: {e}")

    print()

print("=" * 60)
print("结论:")
print("如果所有请求都返回 200 或 3xx 状态码，")
print("但 Playwright 仍然获得空页面，")
print("说明 OddsPortal 使用了 JavaScript 渲染层面的检测。")
print("=" * 60)
