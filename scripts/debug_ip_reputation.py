#!/usr/bin/env python3
"""V142.0 IP Reputation Diagnostic Tool.

This script performs cross-platform testing to determine whether the 39-byte
Hard Ban is caused by IP blacklisting or browser fingerprinting.

Test Matrix:
    1. curl (native CLI) - Baseline comparison
    2. requests (Python) - Without Playwright fingerprint
    3. Playwright (Stealth) - With anti-fingerprinting

Verdict Logic:
    - If curl/requests succeed but Playwright fails → Fingerprinting issue
    - If all three return 39 bytes → IP blacklisting issue

Usage:
    python scripts/debug_ip_reputation.py

Author: Cyber Security & Penetration Testing Expert
Version: V142.0
Date: 2026-01-05
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


# ============================================================================
# Test Functions
# ============================================================================

def get_proxy_url() -> str | None:
    """Get proxy URL from BaseExtractor auto-discovery.

    Returns:
        Proxy URL string or None
    """
    try:
        from src.api.collectors.base_extractor import BaseExtractor
        extractor = BaseExtractor(auto_proxy=True)
        proxy_config = extractor.get_proxy_config()
        if proxy_config:
            return proxy_config["server"]
    except Exception as e:
        print(f"⚠️  BaseExtractor proxy discovery failed: {e}")
    return None


def test_with_curl(proxy_url: str, target_url: str) -> dict[str, Any]:
    """Test 1: curl (native CLI) - Baseline comparison.

    Args:
        proxy_url: Proxy URL
        target_url: Target URL to test

    Returns:
        Test result dictionary
    """
    print("\n" + "="*80)
    print("TEST 1: curl (Native CLI - Baseline)")
    print("="*80)
    print()

    result = {
        "method": "curl",
        "success": False,
        "status_code": None,
        "content_length": 0,
        "response_preview": "",
        "error": None,
    }

    try:
        # Construct curl command
        cmd = [
            "curl",
            "-x", proxy_url,
            "-s", "-o", "/dev/null",
            "-w", "%{http_code}",
            "-H", "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            target_url
        ]

        print(f"  Command: curl -x {proxy_url} -s -o /dev/null -w '%{{http_code}}' {target_url}")
        print(f"  Testing...")

        # Execute curl
        process = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )

        status_code = process.stdout.strip()
        result["status_code"] = status_code

        # Get actual content for verification
        cmd_content = [
            "curl",
            "-x", proxy_url,
            "-s",
            "-H", "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            target_url
        ]

        process_content = subprocess.run(
            cmd_content,
            capture_output=True,
            text=True,
            timeout=30
        )

        content = process_content.stdout
        result["content_length"] = len(content)

        # Check for 39-byte Hard Ban signature
        if len(content) == 39:
            result["response_preview"] = content
            print(f"  ✗ HTTP {status_code} | {len(content)} bytes")
            print(f"  🔴 HARD BAN DETECTED (39 bytes)")
            print(f"  Content: {content[:100]}")
        elif len(content) < 100:
            result["response_preview"] = content
            print(f"  ⚠️  HTTP {status_code} | {len(content)} bytes (suspicious)")
            print(f"  Content: {content[:100]}")
        else:
            result["success"] = True
            result["response_preview"] = content[:200]
            print(f"  ✓ HTTP {status_code} | {len(content)} bytes")
            print(f"  📄 Content preview: {content[:100]}...")

    except subprocess.TimeoutExpired:
        result["error"] = "Timeout (30s)"
        print(f"  ✗ Timeout after 30 seconds")
    except FileNotFoundError:
        result["error"] = "curl not found"
        print(f"  ✗ curl command not found")
    except Exception as e:
        result["error"] = str(e)
        print(f"  ✗ Error: {e}")

    print()
    return result


def test_with_requests(proxy_url: str, target_url: str) -> dict[str, Any]:
    """Test 2: requests (Python) - Without Playwright fingerprint.

    Args:
        proxy_url: Proxy URL
        target_url: Target URL to test

    Returns:
        Test result dictionary
    """
    print("\n" + "="*80)
    print("TEST 2: requests (Python - No Playwright Fingerprint)")
    print("="*80)
    print()

    result = {
        "method": "requests",
        "success": False,
        "status_code": None,
        "content_length": 0,
        "response_preview": "",
        "error": None,
    }

    try:
        import requests

        # Setup proxy
        proxies = {
            "http": proxy_url,
            "https": proxy_url,
        }

        # Setup headers
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                         "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

        print(f"  URL: {target_url}")
        print(f"  Proxy: {proxy_url}")
        print(f"  Testing...")

        # Make request
        response = requests.get(
            target_url,
            proxies=proxies,
            headers=headers,
            timeout=30
        )

        result["status_code"] = response.status_code
        content = response.text
        result["content_length"] = len(content)

        # Check for 39-byte Hard Ban signature
        if len(content) == 39:
            result["response_preview"] = content
            print(f"  ✗ HTTP {response.status_code} | {len(content)} bytes")
            print(f"  🔴 HARD BAN DETECTED (39 bytes)")
            print(f"  Content: {content[:100]}")
        elif len(content) < 100:
            result["response_preview"] = content
            print(f"  ⚠️  HTTP {response.status_code} | {len(content)} bytes (suspicious)")
            print(f"  Content: {content[:100]}")
        else:
            result["success"] = True
            result["response_preview"] = content[:200]
            print(f"  ✓ HTTP {response.status_code} | {len(content)} bytes")
            print(f"  📄 Content preview: {content[:100]}...")

    except requests.exceptions.Timeout:
        result["error"] = "Timeout (30s)"
        print(f"  ✗ Timeout after 30 seconds")
    except requests.exceptions.RequestException as e:
        result["error"] = str(e)
        print(f"  ✗ Request error: {e}")
    except Exception as e:
        result["error"] = str(e)
        print(f"  ✗ Error: {e}")

    print()
    return result


async def test_with_playwright_stealth(
    proxy_url: str,
    target_url: str,
    use_stealth: bool = True,
) -> dict[str, Any]:
    """Test 3: Playwright (with/without stealth) - Full browser fingerprint.

    Args:
        proxy_url: Proxy URL
        target_url: Target URL to test
        use_stealth: Whether to use playwright-stealth

    Returns:
        Test result dictionary
    """
    stealth_mode = "Stealth" if use_stealth else "Standard"
    print("\n" + "="*80)
    print(f"TEST 3: Playwright ({stealth_mode} Mode - Full Browser Fingerprint)")
    print("="*80)
    print()

    result = {
        "method": f"playwright_{stealth_mode.lower()}",
        "success": False,
        "status_code": None,
        "content_length": 0,
        "response_preview": "",
        "error": None,
    }

    try:
        from playwright.async_api import async_playwright

        # Setup proxy config
        from urllib.parse import urlparse
        parsed = urlparse(proxy_url)

        proxy_config = {
            "server": f"{parsed.scheme}://{parsed.hostname}:{parsed.port}",
        }

        print(f"  URL: {target_url}")
        print(f"  Proxy: {proxy_url}")
        print(f"  Stealth: {use_stealth}")
        print(f"  Testing...")

        async with async_playwright() as pw:
            # Launch browser
            browser = await pw.chromium.launch(
                headless=True,
                proxy=proxy_config
            )

            # Create context with random UA
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080},
            )

            # Apply stealth if requested
            if use_stealth:
                try:
                    from playwright_stealth import stealth_async
                    page = await context.new_page()
                    await stealth_async(page)
                except ImportError:
                    print(f"  ⚠️  playwright-stealth not installed, using standard mode")
                    page = await context.new_page()
            else:
                page = await context.new_page()

            # Navigate to target
            await page.goto(target_url, timeout=30000, wait_until="domcontentloaded")

            # Get content
            content = await page.inner_text("body")
            result["content_length"] = len(content)

            # Check for 39-byte Hard Ban signature
            if len(content) == 39:
                result["response_preview"] = content
                print(f"  ✗ Response | {len(content)} bytes")
                print(f"  🔴 HARD BAN DETECTED (39 bytes)")
                print(f"  Content: {content[:100]}")
            elif len(content) < 100:
                result["response_preview"] = content
                print(f"  ⚠️  Response | {len(content)} bytes (suspicious)")
                print(f"  Content: {content[:100]}")
            else:
                result["success"] = True
                result["response_preview"] = content[:200]
                print(f"  ✓ Response | {len(content)} bytes")
                print(f"  📄 Content preview: {content[:100]}...")

            await context.close()
            await browser.close()

    except Exception as e:
        result["error"] = str(e)
        print(f"  ✗ Error: {e}")

    print()
    return result


def generate_verdict_report(
    curl_result: dict[str, Any],
    requests_result: dict[str, Any],
    playwright_stealth_result: dict[str, Any],
    proxy_url: str | None,
) -> None:
    """Generate final verdict report.

    Args:
        curl_result: Test 1 result
        requests_result: Test 2 result
        playwright_stealth_result: Test 3 result
        proxy_url: Proxy URL used
    """
    print("\n" + "="*80)
    print("🔬 PENETRATION TEST VERDICT")
    print("="*80)
    print()

    # Summary table
    print("📊 Test Results Summary")
    print("-" * 80)
    print(f"{'Method':<25} {'Status':<15} {'Size':<10} {'Verdict'}")
    print("-" * 80)

    all_results = [
        ("curl (CLI)", curl_result),
        ("requests (Python)", requests_result),
        ("Playwright (Stealth)", playwright_stealth_result),
    ]

    for method_name, result in all_results:
        if result["success"]:
            status = "✓ SUCCESS"
            verdict = "CLEAN"
        elif result["content_length"] == 39:
            status = "✗ HARD BAN"
            verdict = "🔴 BANNED"
        elif result["error"]:
            status = f"✗ ERROR"
            verdict = f"⚠️  {result['error'][:20]}"
        else:
            status = "⚠️  SUSPICIOUS"
            verdict = "⚠️  CHECK"

        size = f"{result['content_length']} bytes"
        print(f"{method_name:<25} {status:<15} {size:<10} {verdict}")

    print()

    # Final verdict logic
    print("="*80)
    print("🎯 ROOT CAUSE ANALYSIS")
    print("="*80)
    print()

    # Count 39-byte responses
    hard_ban_count = sum(
        1 for _, result in all_results
        if result["content_length"] == 39
    )

    # Count successes
    success_count = sum(1 for _, result in all_results if result["success"])

    print(f"Proxy URL: {proxy_url or 'None'}")
    print(f"Hard Ban Count: {hard_ban_count}/3")
    print(f"Success Count: {success_count}/3")
    print()

    # Verdict logic
    if hard_ban_count == 0 and success_count > 0:
        print("✅ VERDICT: CLEAN IP")
        print()
        print("   The proxy IP is NOT blacklisted by OddsPortal.")
        print("   The 39-byte Hard Ban in main.py is likely caused by:")
        print("   1. Playwright browser fingerprint leakage")
        print("   2. Insufficient stealth measures")
        print("   3. Request pattern detection")
        print()
        print("   📋 RECOMMENDATION: Fix code (enhance stealth measures)")
    elif hard_ban_count == 3:
        print("🔴 VERDICT: IP BLACKLIST")
        print()
        print("   The proxy IP is BLACKLISTED by OddsPortal.")
        print("   ALL test methods (curl, requests, Playwright) received 39-byte response.")
        print()
        print("   📋 RECOMMENDATION: Change IP address")
        print("   - Switch to a different proxy node")
        print("   - Use residential proxies")
        print("   - Implement proxy rotation")
    elif hard_ban_count > 0 and success_count > 0:
        print("⚠️  VERDICT: MIXED (PARTIAL BAN)")
        print()
        print("   Some methods work, others don't. This suggests:")
        print("   1. Partial IP reputation scoring")
        print("   2. Browser fingerprint filtering")
        print("   3. User-Agent specific blocking")
        print()
        # Detail which methods worked
        for method_name, result in all_results:
            if result["success"]:
                print(f"   ✓ {method_name} succeeded")
            elif result["content_length"] == 39:
                print(f"   ✗ {method_name} blocked")
        print()
        print("   📋 RECOMMENDATION: Both IP change AND code fixes needed")
    else:
        print("❌ VERDICT: INCONCLUSIVE")
        print()
        print("   Unable to determine root cause.")
        print("   All tests failed with different errors.")
        print()
        print("   📋 RECOMMENDATION:")
        print("   1. Check proxy connectivity")
        print("   2. Verify proxy server is running")
        print("   3. Test with a different target URL")

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
    print()
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║                                                                    ║")
    print("║           V142.0 IP Reputation Diagnostic Tool                      ║")
    print("║                                                                    ║")
    print("║  Cyber Security & Penetration Testing                              ║")
    print("║  ├─ Test Matrix: curl / requests / Playwright                      ║")
    print("║  └─ Verdict: IP Blacklist vs Fingerprint Detection                ║")
    print("║                                                                    ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")
    print()

    # Get proxy URL
    proxy_url = get_proxy_url()
    if not proxy_url:
        print("❌ Failed to discover proxy URL")
        print()
        print("Please ensure:")
        print("  1. BaseExtractor can auto-discover WSL2 proxy")
        print("  2. Or set HTTPS_PROXY environment variable")
        return 1

    # Target URL for testing (use a specific OddsPortal match page)
    target_url = "https://www.oddsportal.com/soccer/england/premier-league-2023-2024/"

    # Run all tests
    curl_result = test_with_curl(proxy_url, target_url)
    requests_result = test_with_requests(proxy_url, target_url)
    playwright_stealth_result = asyncio.run(
        test_with_playwright_stealth(proxy_url, target_url, use_stealth=True)
    )

    # Generate final verdict
    generate_verdict_report(
        curl_result=curl_result,
        requests_result=requests_result,
        playwright_stealth_result=playwright_stealth_result,
        proxy_url=proxy_url,
    )

    # Exit code based on results
    if playwright_stealth_result["success"]:
        return 0
    elif curl_result["success"] or requests_result["success"]:
        return 2  # Mixed results
    else:
        return 1  # All failed


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print()
        print("👋 Test interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Diagnostic script failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
