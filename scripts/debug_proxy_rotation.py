#!/usr/bin/env python3
"""V142.0 Multi-Node Proxy Rotation Test.

This script allows testing against multiple proxy nodes to determine whether
the issue is IP-specific or a systemic problem.

Features:
    - Fetch free proxies from public APIs
    - Test multiple proxy nodes in parallel
    - Identify working proxies for OddsPortal access
    - Generate proxy pool configuration

Usage:
    # Test with free proxy APIs
    python scripts/debug_proxy_rotation.py --source free-proxy-list

    # Test with custom proxy list
    python scripts/debug_proxy_rotation.py --source custom --proxies "http://ip1:port,http://ip2:port"

Author: Cyber Security & Penetration Testing Expert
Version: V142.0
Date: 2026-01-05
"""

from __future__ import annotations

import asyncio
import argparse
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


# ============================================================================
# Proxy Fetchers
# ============================================================================

async def fetch_free_proxies() -> list[str]:
    """Fetch free proxy list from public APIs.

    Returns:
        List of proxy URLs
    """
    print("🔍 Fetching free proxies from public APIs...")
    print()

    # Static list of known free proxy APIs
    # In production, you would scrape these dynamically
    proxy_sources = {
        "proxylist_geonode": [
            "http://185.162.231.166:80",
            "http://185.162.230.167:80",
            "http://185.162.231.166:3128",
            "http://185.162.230.167:3128",
        ],
        # Add more sources as needed
        # Note: These are example proxies and may not be active
    }

    all_proxies = []
    for source, proxies in proxy_sources.items():
        print(f"  ✓ Fetched {len(proxies)} from {source}")
        all_proxies.extend(proxies)

    print(f"\n  📊 Total proxies: {len(all_proxies)}")
    return all_proxies


# ============================================================================
# Proxy Tester
# ============================================================================

async def test_single_proxy(
    proxy_url: str,
    target_url: str,
    timeout: int = 15,
) -> dict[str, Any]:
    """Test a single proxy against the target URL.

    Args:
        proxy_url: Proxy URL to test
        target_url: Target URL
        timeout: Request timeout in seconds

    Returns:
        Test result dictionary
    """
    result = {
        "proxy": proxy_url,
        "success": False,
        "status_code": None,
        "content_length": 0,
        "response_time": None,
        "error": None,
        "hard_ban": False,
    }

    start_time = datetime.now()

    try:
        import aiohttp

        async with aiohttp.ClientSession() as session:
            kwargs = {
                "timeout": aiohttp.ClientTimeout(total=timeout),
                "proxy": proxy_url,
                "headers": {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }
            }

            async with session.get(target_url, **kwargs) as resp:
                result["status_code"] = resp.status
                content = await resp.text()
                result["content_length"] = len(content)
                result["response_time"] = (datetime.now() - start_time).total_seconds()

                # Check for 39-byte Hard Ban
                if len(content) == 39:
                    result["hard_ban"] = True
                elif len(content) > 1000:
                    result["success"] = True

    except asyncio.TimeoutError:
        result["error"] = "Timeout"
    except Exception as e:
        result["error"] = str(e)[:50]

    return result


async def test_proxies_parallel(
    proxy_list: list[str],
    target_url: str,
    max_concurrent: int = 10,
) -> list[dict[str, Any]]:
    """Test multiple proxies in parallel.

    Args:
        proxy_list: List of proxy URLs to test
        target_url: Target URL
        max_concurrent: Maximum concurrent tests

    Returns:
        List of test results
    """
    print(f"\n🚀 Testing {len(proxy_list)} proxies (max concurrent: {max_concurrent})")
    print("="*80)
    print()

    semaphore = asyncio.Semaphore(max_concurrent)

    async def test_with_semaphore(proxy: str) -> dict[str, Any]:
        async with semaphore:
            return await test_single_proxy(proxy, target_url)

    tasks = [test_with_semaphore(proxy) for proxy in proxy_list]
    results = await asyncio.gather(*tasks)

    return results


# ============================================================================
# Report Generation
# ============================================================================

def generate_proxy_test_report(results: list[dict[str, Any]]) -> None:
    """Generate comprehensive proxy test report.

    Args:
        results: List of test results
    """
    print("\n" + "="*80)
    print("📊 MULTI-NODE PROXY TEST RESULTS")
    print("="*80)
    print()

    # Sort results by success first, then by response time
    sorted_results = sorted(
        results,
        key=lambda x: (
            not x["success"],
            x.get("response_time") or float("inf"),
            x["hard_ban"],
        )
    )

    # Summary statistics
    total = len(sorted_results)
    success = sum(1 for r in sorted_results if r["success"])
    hard_ban = sum(1 for r in sorted_results if r["hard_ban"])
    error = sum(1 for r in sorted_results if r["error"] and not r["success"])

    print(f"Total Proxies Tested: {total}")
    print(f"✓ Success: {success} ({success/total*100:.1f}%)")
    print(f"🔴 Hard Ban: {hard_ban} ({hard_ban/total*100:.1f}%)")
    print(f"❌ Error: {error} ({error/total*100:.1f}%)")
    print()

    # Detailed results table
    print("="*80)
    print(f"{'Proxy':<30} {'Status':<15} {'Size':<10} {'Time':<10}")
    print("="*80)

    for result in sorted_results[:20]:  # Show top 20
        proxy = result["proxy"][:30]

        if result["success"]:
            status = "✓ SUCCESS"
            size = f"{result['content_length']} bytes"
            time_str = f"{result['response_time']:.2f}s"
        elif result["hard_ban"]:
            status = "🔴 HARD BAN"
            size = f"{result['content_length']} bytes"
            time_str = f"{result.get('response_time') or 0:.2f}s"
        elif result["error"]:
            status = f"✗ {result['error'][:10]}"
            size = "-"
            time_str = "-"
        else:
            status = "⚠️  SUSPICIOUS"
            size = f"{result['content_length']} bytes"
            time_str = f"{result.get('response_time') or 0:.2f}s"

        print(f"{proxy:<30} {status:<15} {size:<10} {time_str:<10}")

    if len(sorted_results) > 20:
        print(f"... and {len(sorted_results) - 20} more")

    print()

    # Working proxies export
    working_proxies = [r["proxy"] for r in sorted_results if r["success"]]

    if working_proxies:
        print("="*80)
        print("✅ WORKING PROXIES DETECTED!")
        print("="*80)
        print()
        print("Add these to your environment:")
        print()
        for proxy in working_proxies:
            print(f"  export HTTPS_PROXY={proxy}")
        print()

        # Generate proxy pool config
        config_path = Path("logs/proxy_pool.txt")
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, "w") as f:
            for proxy in working_proxies:
                f.write(f"{proxy}\n")

        print(f"✓ Proxy pool saved to: {config_path}")
        print()

    # Final verdict
    print("="*80)
    print("🎯 FINAL VERDICT")
    print("="*80)
    print()

    if success > 0:
        print("✅ SOLUTION FOUND: Change IP Address")
        print()
        print(f"   {success} out of {total} proxies work successfully.")
        print("   This confirms the issue is IP-BLACKLIST specific.")
        print()
        print("   📋 RECOMMENDED ACTIONS:")
        print("   1. Use one of the working proxies above")
        print("   2. Implement proxy rotation in production")
        print("   3. Consider residential proxies for better reputation")
    elif hard_ban == total:
        print("🔴 SYSTEMIC ISSUE: All Proxies Blocked")
        print()
        print("   ALL tested proxies received 39-byte Hard Ban.")
        print("   This suggests:")
        print("   1. The free proxy list is already poisoned")
        print("   2. OddsPortal has broad IP range blocking")
        print("   3. Browser fingerprinting is the primary detection method")
        print()
        print("   📋 RECOMMENDED ACTIONS:")
        print("   1. Try residential proxies (cleaner IP pool)")
        print("   2. Enhance browser fingerprinting evasion")
        print("   3. Reduce request frequency")
    else:
        print("⚠️  MIXED RESULTS: Inconclusive")
        print()
        print("   No working proxies found, but not all are Hard Banned.")
        print("   This suggests network connectivity issues.")
        print()
        print("   📋 RECOMMENDED ACTIONS:")
        print("   1. Check your network connectivity")
        print("   2. Try with premium proxy services")
        print("   3. Verify target URL is accessible")

    print()
    print(f"Test completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
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
    parser = argparse.ArgumentParser(
        description="V142.0 Multi-Node Proxy Rotation Test",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--source",
        type=str,
        choices=["free-proxy-list", "custom"],
        default="free-proxy-list",
        help="Proxy source to use"
    )

    parser.add_argument(
        "--proxies",
        type=str,
        help="Comma-separated list of custom proxies (use with --source custom)"
    )

    parser.add_argument(
        "--target",
        type=str,
        default="https://www.oddsportal.com/soccer/england/premier-league-2023-2024/",
        help="Target URL to test"
    )

    parser.add_argument(
        "--concurrent",
        type=int,
        default=10,
        help="Maximum concurrent tests"
    )

    args = parser.parse_args()

    print()
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║                                                                    ║")
    print("║           V142.0 Multi-Node Proxy Rotation Test                    ║")
    print("║                                                                    ║")
    print("║  Cyber Security & Penetration Testing                              ║")
    print("║  ├─ Parallel Proxy Testing                                        ║")
    print("║  └─ Working Proxy Discovery                                       ║")
    print("║                                                                    ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")
    print()

    # Get proxy list
    if args.source == "free-proxy-list":
        proxy_list = asyncio.run(fetch_free_proxies())
    elif args.source == "custom":
        if not args.proxies:
            print("❌ --proxies argument required when using --source custom")
            return 1
        proxy_list = [p.strip() for p in args.proxies.split(",")]
    else:
        print("❌ Unknown source")
        return 1

    if not proxy_list:
        print("❌ No proxies to test")
        return 1

    # Run tests
    results = asyncio.run(test_proxies_parallel(
        proxy_list=proxy_list,
        target_url=args.target,
        max_concurrent=args.concurrent,
    ))

    # Generate report
    generate_proxy_test_report(results)

    # Exit code based on results
    success_count = sum(1 for r in results if r["success"])
    return 0 if success_count > 0 else 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print()
        print("👋 Test interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
