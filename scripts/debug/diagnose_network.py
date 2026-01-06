#!/usr/bin/env python3
"""V142.0 Network Diagnostic Script.

This script provides comprehensive network diagnostics for the FootballPrediction
system, focusing on proxy configuration and connectivity issues.

Features:
    - Environment variable audit
    - WSL2 host auto-detection
    - Proxy connectivity testing (aiohttp, playwright, requests)
    - DNS resolution testing
    - Network routing analysis

Usage:
    python scripts/diagnose_network.py

Author: Network Engineer & DevOps Specialist
Version: V142.0
Date: 2026-01-05
"""

from __future__ import annotations

import asyncio
import os
import socket
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


# ============================================================================
# Diagnostic Functions
# ============================================================================

def print_banner() -> None:
    """Print the diagnostic banner."""
    banner = """
╔══════════════════════════════════════════════════════════════════════╗
║                                                                    ║
║           V142.0 网络诊断工具                                        ║
║                                                                    ║
║  Network & Proxy Diagnostic Suite                                  ║
║  ├─ Environment Variable Audit                                     ║
║  ├─ WSL2 Auto-Discovery                                            ║
║  ├─ Proxy Connectivity Testing                                     ║
║  └─ DNS Resolution Analysis                                        ║
║                                                                    ║
╚══════════════════════════════════════════════════════════════════════╝
"""
    print(banner)


def check_env_variables() -> dict[str, Any]:
    """Check all relevant environment variables.

    Returns:
        Dictionary with environment variable status
    """
    print("\n" + "="*80)
    print("1️⃣  环境变量审计")
    print("="*80)
    print()

    proxy_vars = {
        "PROXY_SERVER": None,
        "HTTP_PROXY": None,
        "HTTPS_PROXY": None,
        "http_proxy": None,
        "https_proxy": None,
        "ALL_PROXY": None,
        "NO_PROXY": None,
        "no_proxy": None,
    }

    found_vars = False
    for var in proxy_vars:
        value = os.getenv(var)
        proxy_vars[var] = value
        if value:
            found_vars = True
            print(f"  ✓ {var} = {value}")
        else:
            print(f"  - {var} = (未设置)")

    print()

    if not found_vars:
        print("  ⚠️  警告: 未发现任何代理环境变量")
        print("  💡 建议: 设置 HTTPS_PROXY 环境变量 (推荐)")
    else:
        print(f"  ✅ 发现 {sum(1 for v in proxy_vars.values() if v)} 个代理相关变量")

    print()
    return proxy_vars


def check_wsl2_environment() -> dict[str, Any]:
    """Check WSL2 environment and host IP.

    Returns:
        Dictionary with WSL2 status and host IP
    """
    print("\n" + "="*80)
    print("2️⃣  WSL2 环境检测")
    print("="*80)
    print()

    result = {
        "is_wsl2": False,
        "host_ip": None,
        "resolv_conf_nameserver": None,
    }

    # Check /proc/version for WSL2 signature
    try:
        with open("/proc/version", "r") as f:
            version_content = f.read().lower()
            is_wsl2 = "microsoft" in version_content
            result["is_wsl2"] = is_wsl2

            if is_wsl2:
                print(f"  ✓ WSL2 环境: 是")
                print(f"  ℹ️  内核版本: {version_content.split()[0]}")
            else:
                print(f"  - WSL2 环境: 否")
    except Exception as e:
        print(f"  ✗ WSL2 检测失败: {e}")

    # Check /etc/resolv.conf for host IP
    try:
        with open("/etc/resolv.conf", "r") as f:
            for line in f:
                if line.startswith("nameserver"):
                    nameserver = line.split()[1].strip()
                    result["resolv_conf_nameserver"] = nameserver
                    print(f"  ✓ DNS 服务器: {nameserver}")
                    break
    except Exception as e:
        print(f"  ✗ resolv.conf 读取失败: {e}")

    # Get WSL2 host IP
    if result["is_wsl2"]:
        host_ip_found = False
        # Method 1: Try to get default gateway via 'ip route' command
        try:
            import subprocess
            output = subprocess.check_output(
                ["ip", "route", "show", "default"],
                stderr=subprocess.DEVNULL,
                text=True
            )
            if output and "via" in output:
                # Output format: "default via 172.x.x.1 dev eth0 ..."
                host_ip = output.split()[2]
                result["host_ip"] = host_ip
                print(f"  ✓ 宿主机 IP: {host_ip} (默认网关)")
                host_ip_found = True
        except Exception as e:
            print(f"  ⚠️  默认网关获取失败: {e}")

        # Method 2: Fallback to /etc/resolv.conf nameserver
        if not host_ip_found:
            try:
                with open("/etc/resolv.conf", "r") as f:
                    for line in f:
                        if line.startswith("nameserver"):
                            host_ip = line.split()[1].strip()
                            result["host_ip"] = host_ip
                            print(f"  ✓ 宿主机 IP: {host_ip} (DNS 服务器)")
                            break
            except Exception as e:
                print(f"  ✗ 宿主机 IP 获取失败: {e}")

    print()
    return result


def check_proxy_connectivity() -> dict[str, Any]:
    """Check proxy connectivity using multiple methods.

    Returns:
        Dictionary with connectivity test results
    """
    print("\n" + "="*80)
    print("3️⃣  代理连接测试")
    print("="*80)
    print()

    # Import BaseExtractor for proxy discovery
    from src.api.collectors.base_extractor import BaseExtractor

    result = {
        "proxy_discovered": None,
        "socket_test": None,
        "aiohttp_test": None,
        "playwright_test": None,
    }

    # Discover proxy
    extractor = BaseExtractor()
    proxy_config = extractor.get_proxy_config()
    result["proxy_discovered"] = proxy_config

    if proxy_config:
        proxy_url = proxy_config["server"]
        print(f"  ✓ 代理已发现: {proxy_url}")
        print()

        # Test 1: Socket connectivity
        print("  3.1 Socket 连接测试...")
        try:
            from urllib.parse import urlparse

            parsed = urlparse(proxy_url)
            host = parsed.hostname
            port = parsed.port

            if host and port:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5.0)
                conn_result = sock.connect_ex((host, port))
                sock.close()

                if conn_result == 0:
                    result["socket_test"] = "SUCCESS"
                    print(f"      ✓ Socket 连接成功 ({host}:{port})")
                else:
                    result["socket_test"] = f"FAILED ({conn_result})"
                    print(f"      ✗ Socket 连接失败: 错误码 {conn_result}")
            else:
                result["socket_test"] = "INVALID_URL"
                print(f"      ✗ 无效的代理 URL: {proxy_url}")
        except Exception as e:
            result["socket_test"] = f"EXCEPTION: {e}"
            print(f"      ✗ Socket 测试异常: {e}")

        # Test 2: aiohttp connectivity
        print("  3.2 aiohttp 连接测试...")

        async def test_aiohttp():
            try:
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        "https://api.ipify.org",
                        timeout=10,
                        proxy=proxy_url
                    ) as resp:
                        ip = await resp.text()
                        return {"status": "SUCCESS", "ip": ip}
            except Exception as e:
                return {"status": f"FAILED: {e}", "ip": None}

        try:
            aiohttp_result = asyncio.run(test_aiohttp())
            if aiohttp_result["status"] == "SUCCESS":
                result["aiohttp_test"] = f"SUCCESS (IP: {aiohttp_result['ip']})"
                print(f"      ✓ aiohttp 连接成功 (出口 IP: {aiohttp_result['ip']})")
            else:
                result["aiohttp_test"] = aiohttp_result["status"]
                print(f"      ✗ aiohttp 连接失败: {aiohttp_result['status']}")
        except Exception as e:
            result["aiohttp_test"] = f"EXCEPTION: {e}"
            print(f"      ✗ aiohttp 测试异常: {e}")

        # Test 3: Playwright connectivity
        print("  3.3 Playwright 连接测试...")

        async def test_playwright():
            try:
                from playwright.async_api import async_playwright

                async with async_playwright() as pw:
                    browser = await pw.chromium.launch(
                        headless=True,
                        proxy=proxy_config
                    )
                    context = await browser.new_context()
                    page = await context.new_page()

                    await page.goto("https://api.ipify.org", timeout=15000)
                    ip = await page.inner_text("body")

                    await context.close()
                    await browser.close()

                    return {"status": "SUCCESS", "ip": ip.strip()}
            except Exception as e:
                return {"status": f"FAILED: {e}", "ip": None}

        try:
            playwright_result = asyncio.run(test_playwright())
            if playwright_result["status"] == "SUCCESS":
                result["playwright_test"] = f"SUCCESS (IP: {playwright_result['ip']})"
                print(f"      ✓ Playwright 连接成功 (出口 IP: {playwright_result['ip']})")
            else:
                result["playwright_test"] = playwright_result["status"]
                print(f"      ✗ Playwright 连接失败: {playwright_result['status']}")
        except Exception as e:
            result["playwright_test"] = f"EXCEPTION: {e}"
            print(f"      ✗ Playwright 测试异常: {e}")

    else:
        print(f"  ✗ 未发现可用代理")
        print(f"  ℹ️  跳过连接测试")

    print()
    return result


def check_dns_resolution() -> dict[str, Any]:
    """Check DNS resolution for critical domains.

    Returns:
        Dictionary with DNS resolution results
    """
    print("\n" + "="*80)
    print("4️⃣  DNS 解析测试")
    print("="*80)
    print()

    test_domains = [
        ("api.ipify.org", "IP 检测服务"),
        ("www.google.com", "Google"),
        ("www.oddsportal.com", "OddsPortal"),
        ("www.fotmob.com", "FotMob"),
    ]

    result = {}

    for domain, description in test_domains:
        try:
            ip = socket.gethostbyname(domain)
            result[domain] = {"status": "SUCCESS", "ip": ip}
            print(f"  ✓ {description:20s} ({domain}) → {ip}")
        except socket.gaierror as e:
            result[domain] = {"status": f"FAILED: {e}", "ip": None}
            print(f"  ✗ {description:20s} ({domain}) → 解析失败: {e}")
        except Exception as e:
            result[domain] = {"status": f"EXCEPTION: {e}", "ip": None}
            print(f"  ✗ {description:20s} ({domain}) → 异常: {e}")

    print()
    return result


def check_network_routing() -> dict[str, Any]:
    """Check network routing and gateway.

    Returns:
        Dictionary with routing information
    """
    print("\n" + "="*80)
    print("5️⃣  网络路由分析")
    print("="*80)
    print()

    result = {
        "hostname": None,
        "default_gateway": None,
    }

    # Get hostname
    try:
        hostname = socket.gethostname()
        result["hostname"] = hostname
        print(f"  ✓ 主机名: {hostname}")
    except Exception as e:
        print(f"  ✗ 主机名获取失败: {e}")

    # Try to get default gateway (Linux)
    try:
        import subprocess
        output = subprocess.check_output(
            ["ip", "route", "show", "default"],
            stderr=subprocess.DEVNULL,
            text=True
        )
        if output:
            result["default_gateway"] = output.strip()
            print(f"  ✓ 默认网关: {output.strip()}")
    except Exception as e:
        print(f"  ℹ️  默认网关: 无法获取 ({e})")

    print()
    return result


def generate_diagnostic_report(
    env_vars: dict[str, Any],
    wsl2_info: dict[str, Any],
    proxy_conn: dict[str, Any],
    dns_res: dict[str, Any],
    routing: dict[str, Any],
) -> None:
    """Generate final diagnostic report.

    Args:
        env_vars: Environment variable audit results
        wsl2_info: WSL2 environment information
        proxy_conn: Proxy connectivity test results
        dns_res: DNS resolution results
        routing: Network routing information
    """
    print("\n" + "="*80)
    print("📊 诊断总结报告")
    print("="*80)
    print()

    # Environment variables summary
    proxy_count = sum(1 for v in env_vars.values() if v)
    print(f"环境变量: {proxy_count} 个代理变量已设置")
    if proxy_count == 0:
        print(f"  ⚠️  未设置任何代理环境变量")
        print(f"  💡 建议: export HTTPS_PROXY=http://host:port")

    # WSL2 summary
    if wsl2_info["is_wsl2"]:
        print(f"WSL2 环境: 是")
        if wsl2_info["host_ip"]:
            print(f"  ✓ 宿主机 IP: {wsl2_info['host_ip']}")
    else:
        print(f"WSL2 环境: 否")

    # Proxy discovery summary
    if proxy_conn["proxy_discovered"]:
        print(f"代理发现: ✅ 成功 ({proxy_conn['proxy_discovered']['server']})")
    else:
        print(f"代理发现: ❌ 失败")

    # Connectivity summary
    if proxy_conn["proxy_discovered"]:
        socket_ok = proxy_conn["socket_test"] and "SUCCESS" in proxy_conn["socket_test"]
        aiohttp_ok = proxy_conn["aiohttp_test"] and "SUCCESS" in proxy_conn["aiohttp_test"]
        playwright_ok = proxy_conn["playwright_test"] and "SUCCESS" in proxy_conn["playwright_test"]

        print(f"连接测试:")
        print(f"  - Socket:    {'✅' if socket_ok else '❌'}")
        print(f"  - aiohttp:   {'✅' if aiohttp_ok else '❌'}")
        print(f"  - Playwright: {'✅' if playwright_ok else '❌'}")

    # DNS summary
    dns_success = sum(1 for v in dns_res.values() if "SUCCESS" in v.get("status", ""))
    print(f"DNS 解析: {dns_success}/{len(dns_res)} 成功")

    # Final verdict
    print()
    print("="*80)
    print("🎯 最终诊断结论")
    print("="*80)
    print()

    if proxy_conn["proxy_discovered"]:
        if (proxy_conn["socket_test"] and "SUCCESS" in proxy_conn["socket_test"] and
            proxy_conn["aiohttp_test"] and "SUCCESS" in proxy_conn["aiohttp_test"]):
            print("✅ 代理配置正常！系统已就绪。")
            print()
            print("启动命令:")
            print("  python main.py --mode single --dry-run")
        else:
            print("⚠️  代理已发现但连接测试失败")
            print()
            print("可能原因:")
            print("  1. 代理服务未启动")
            print("  2. 代理端口错误")
            print("  3. 防火墙阻止连接")
            print("  4. WSL2 宿主机代理未允许局域网连接")
            print()
            print("建议操作:")
            if wsl2_info["is_wsl2"]:
                print("  - 检查 Windows 代理软件是否允许局域网连接")
                print("  - 在 Windows 防火墙中允许 WSL2 访问")
            print("  - 运行 'python main.py --test-proxy' 进行快速测试")
    else:
        print("❌ 未发现可用代理配置")
        print()
        print("建议操作:")
        print("  1. 设置环境变量:")
        print("     export HTTPS_PROXY=http://172.x.x.x:7890")
        print("  2. 或在 .env 文件中添加:")
        print("     PROXY_SERVER=http://172.x.x.x:7890")
        print("  3. 确保代理服务已启动并监听对应端口")

    print()
    print(f"诊断时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    print()


# ============================================================================
# Main Entry Point
# ============================================================================

def main() -> int:
    """Main entry point.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    print_banner()

    # Run all diagnostic tests
    env_vars = check_env_variables()
    wsl2_info = check_wsl2_environment()
    proxy_conn = check_proxy_connectivity()
    dns_res = check_dns_resolution()
    routing = check_network_routing()

    # Generate final report
    generate_diagnostic_report(
        env_vars=env_vars,
        wsl2_info=wsl2_info,
        proxy_conn=proxy_conn,
        dns_res=dns_res,
        routing=routing,
    )

    # Return exit code based on proxy discovery
    return 0 if proxy_conn["proxy_discovered"] else 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print()
        print("👋 收到中断信号，正在退出...")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ 诊断脚本异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
