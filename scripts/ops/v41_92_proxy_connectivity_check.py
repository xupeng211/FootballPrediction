#!/usr/bin/env python3
"""
V41.92 "金丝雀收割" - 代理连通性自检脚本
==========================================

任务：在代码执行前，执行 172.25.16.1:7891-7909 的物理连通性自检
要求：如果连通性自检失败，输出具体的 Error 码
"""

import asyncio
import sys
from datetime import datetime
from typing import Dict, List, Tuple

import aiohttp


async def check_proxy_port(session: aiohttp.ClientSession, proxy_host: str, proxy_port: int, timeout: int = 5) -> Tuple[int, bool, str]:
    """
    检查单个代理端口的连通性

    Args:
        session: aiohttp 会话
        proxy_host: 代理主机地址
        proxy_port: 代理端口
        timeout: 超时时间（秒）

    Returns:
        Tuple[端口, 是否成功, 错误信息/状态码]
    """
    proxy_url = f"http://{proxy_host}:{proxy_port}"
    target_url = "https://api.ipify.org?format=json"

    try:
        async with session.get(
            target_url,
            proxy=proxy_url,
            timeout=timeout,
            ssl=False  # 跳过 SSL 验证以加快速度
        ) as response:
            if response.status == 200:
                data = await response.json()
                ip = data.get("ip", "unknown")
                return (proxy_port, True, f"✅ 200 OK - IP: {ip}")
            else:
                return (proxy_port, False, f"❌ HTTP {response.status}")

    except asyncio.TimeoutError:
        return (proxy_port, False, "❌ Timeout Error")
    except aiohttp.ClientConnectorError as e:
        error_msg = str(e)
        if "Connection refused" in error_msg:
            return (proxy_port, False, "❌ Connection Refused (端口未监听)")
        elif "Connection reset" in error_msg:
            return (proxy_port, False, "❌ Connection Reset")
        else:
            return (proxy_port, False, f"❌ ClientConnectorError: {error_msg[:50]}")
    except Exception as e:
        return (proxy_port, False, f"❌ {type(e).__name__}: {str(e)[:50]}")


async def check_all_ports(proxy_host: str, port_range: Tuple[int, int]) -> Dict[str, List]:
    """
    检查所有端口的连通性

    Args:
        proxy_host: 代理主机地址
        port_range: 端口范围 (起始, 结束)

    Returns:
        结果字典: {"success": [], "failed": []}
    """
    start_port, end_port = port_range
    results = {"success": [], "failed": []}

    print(f"\n{'='*70}")
    print(f"V41.92 代理连通性自检")
    print(f"{'='*70}")
    print(f"🔍 目标: {proxy_host}:{start_port}-{end_port}")
    print(f"⏰ 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    async with aiohttp.ClientSession() as session:
        tasks = []
        for port in range(start_port, end_port + 1):
            tasks.append(check_proxy_port(session, proxy_host, port))

        # 并发执行所有检查
        port_results = await asyncio.gather(*tasks)

        # 分类结果
        for port, success, message in port_results:
            print(f"  端口 {port}: {message}")
            if success:
                results["success"].append(port)
            else:
                results["failed"].append((port, message))

    return results


def main():
    """主函数"""
    proxy_host = "172.25.16.1"
    port_range = (7891, 7909)

    # 运行检查
    results = asyncio.run(check_all_ports(proxy_host, port_range))

    # 汇总结果
    print()
    print(f"{'='*70}")
    print("📊 检查结果汇总")
    print(f"{'='*70}")

    success_count = len(results["success"])
    failed_count = len(results["failed"])
    total_count = success_count + failed_count

    print(f"✅ 成功: {success_count}/{total_count} 端口")
    if results["success"]:
        print(f"   可用端口: {', '.join(map(str, results['success']))}")

    print(f"❌ 失败: {failed_count}/{total_count} 端口")
    if results["failed"]:
        print(f"   失败详情:")
        for port, message in results["failed"]:
            print(f"     - 端口 {port}: {message}")

    print()

    # 判定是否可以启动收割
    MIN_REQUIRED_PORTS = 3  # 最少需要 3 个可用端口

    if success_count >= MIN_REQUIRED_PORTS:
        print(f"{'='*70}")
        print(f"✅ 代理连通性检查通过！")
        print(f"   可用端口数量: {success_count} (要求: ≥{MIN_REQUIRED_PORTS})")
        print(f"   🚀 准许启动数据收割！")
        print(f"{'='*70}")
        return 0
    else:
        print(f"{'='*70}")
        print(f"❌ 代理连通性检查失败！")
        print(f"   可用端口数量: {success_count} (要求: ≥{MIN_REQUIRED_PORTS})")
        print(f"   🚫 禁止启动数据收割！")
        print(f"   💡 建议:")
        print(f"      1. 检查宿主机代理服务是否启动")
        print(f"      2. 检查 Clash/代理客户端是否允许局域网连接")
        print(f"      3. 检查 Windows 防火墙是否阻止 WSL2 访问")
        print(f"{'='*70}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
