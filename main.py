#!/usr/bin/env python3
"""V142.0 FootballPrediction - Main Entry Point.

This is the unified command-line interface for the FootballPrediction system.
It provides a single entry point for all operations, replacing the scattered
script-based approach.

Features:
    - Automatic environment pre-check (WSL2 proxy discovery, IP detection)
    - Mode scheduling (single/cruise/check)
    - Rich console output with professional formatting
    - Integration with all Phase 1 components (BaseExtractor V141.0, TeamNameNormalizer V140.0)

Usage:
    # Single mode - harvest specific league/season
    python main.py --mode single --league "Premier League" --season "23/24"

    # Cruise mode - 24h automatic harvesting
    python main.py --mode cruise

    # Check mode - data quality verification
    python main.py --mode check

    # Dry run (test without actual collection)
    python main.py --mode single --dry-run

Author: Chief System Architect
Version: V142.0
Date: 2026-01-05
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# V144.2: 加载.env文件并覆盖环境变量（必须在import config_unified之前）
from dotenv import load_dotenv
load_dotenv(override=True)

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.config_unified import get_settings
from src.api.services.harvester_service import HarvesterService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('logs/v142_0_main.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ============================================================================
# Environment Pre-Check
# ============================================================================

def print_banner() -> None:
    """Print the application banner."""
    banner = """
╔══════════════════════════════════════════════════════════════════════╗
║                                                                        ║
║           FootballPrediction V142.0 - Unified Command Center           ║
║                                                                        ║
║  Phase 3: Single Entry Point                                          ║
║  ├─ BaseExtractor V141.0 (Ghost Protocol)                             ║
║  ├─ TeamNameNormalizer V140.0 (Full-path Trial Matching)             ║
║  └─ HarvesterService V142.0 (Queue-driven Architecture)               ║
║                                                                        ║
╚══════════════════════════════════════════════════════════════════════╝
"""
    print(banner)


def check_environment() -> dict[str, str]:
    """Check the environment and return diagnostic information.

    Returns:
        Dictionary with environment information
    """
    logger.info("🔍 环境预检...")
    print("")

    info = {}

    # Check Python version
    python_version = sys.version.split()[0]
    info["python_version"] = python_version
    logger.info(f"  ✓ Python 版本: {python_version}")

    # Check database connection
    try:
        settings = get_settings()
        info["db_host"] = settings.database.host
        info["db_name"] = settings.database.name
        logger.info(f"  ✓ 数据库配置: {settings.database.host}/{settings.database.name}")
    except Exception as e:
        logger.warning(f"  ⚠️  数据库配置检查失败: {e}")
        info["db_host"] = "unknown"

    # Check proxy configuration (V142.0: BaseExtractor auto-discovery)
    try:
        from src.api.collectors.base_extractor import BaseExtractor
        extractor = BaseExtractor(auto_proxy=True)
        proxy_config = extractor.get_proxy_config()

        if proxy_config:
            proxy_url = proxy_config["server"]
            info["proxy"] = proxy_url

            # Check if proxy is from environment variable or WSL2 auto-discovery
            if any(os.getenv(var) for var in ["PROXY_SERVER", "HTTP_PROXY", "HTTPS_PROXY"]):
                logger.info(f"  ✓ 代理 (环境变量): {proxy_url}")
            else:
                logger.info(f"  ✓ 代理 (WSL2 自动探测): {proxy_url}")
        else:
            info["proxy"] = "None"
            logger.info(f"  ℹ️  代理: 未配置")
    except Exception as e:
        info["proxy"] = "error"
        logger.warning(f"  ⚠️  代理检测失败: {e}")

    # Check WSL2 environment
    if os.path.exists("/proc/version"):
        with open("/proc/version", "r") as f:
            version_content = f.read().lower()
            is_wsl = "microsoft" in version_content
            info["is_wsl"] = str(is_wsl)
            if is_wsl:
                logger.info(f"  ✓ WSL2 环境: 是")
            else:
                logger.info(f"  ℹ️  WSL2 环境: 否")
    else:
        info["is_wsl"] = "False"
        logger.info(f"  ℹ️  WSL2 环境: 无法检测")

    # Check log directory
    log_dir = Path("logs")
    if not log_dir.exists():
        log_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"  ✓ 创建日志目录: {log_dir}")
    else:
        logger.info(f"  ✓ 日志目录: {log_dir}")

    print("")
    logger.info("✅ 环境预检完成")
    print("")

    return info


async def check_ip_address(fail_fast: bool = False) -> str:
    """Check the current IP address (V142.0: with BaseExtractor proxy support).

    This function now uses the auto-discovered proxy from BaseExtractor to ensure
    the IP detection reflects the actual network path used during data collection.

    Args:
        fail_fast: If True, raise exception on failure instead of returning "unknown"

    Returns:
        IP address string

    Raises:
        RuntimeError: If fail_fast=True and IP detection fails
    """
    logger.info("🌐 检测出口 IP...")

    # Get proxy configuration from BaseExtractor
    proxy_url = None
    try:
        from src.api.collectors.base_extractor import BaseExtractor
        extractor = BaseExtractor(auto_proxy=True)
        proxy_config = extractor.get_proxy_config()

        if proxy_config:
            proxy_url = proxy_config["server"]
            logger.info(f"  📡 使用代理: {proxy_url}")
        else:
            logger.info(f"  ℹ️  直连模式 (未发现代理)")
    except Exception as e:
        logger.warning(f"  ⚠️  代理探测跳过: {e}")

    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            kwargs = {"timeout": 10}
            if proxy_url:
                kwargs["proxy"] = proxy_url

            async with session.get("https://api.ipify.org", **kwargs) as resp:
                ip = await resp.text()
                logger.info(f"  ✓ 出口 IP: {ip}")
                return ip
    except Exception as e:
        logger.warning(f"  ⚠️  IP 检测失败: {e}")
        if fail_fast:
            error_msg = "❌ 网络连接失败！无法检测到出口 IP。\n\n   可能原因：\n"
            if proxy_url:
                error_msg += f"   1. 代理服务器 {proxy_url} 不可用\n"
                error_msg += "   2. 代理端口错误或防火墙阻止\n"
                error_msg += "   3. 代理服务未启动\n\n"
                error_msg += "   建议操作：\n"
                error_msg += "   - 运行 'python main.py --test-proxy' 进行代理测试\n"
                error_msg += "   - 检查 Windows 代理软件是否允许局域网连接\n"
                error_msg += "   - 运行 'python scripts/diagnose_network.py' 查看详细诊断"
            else:
                error_msg += "   1. 网络未连接\n"
                error_msg += "   2. WSL2 代理自动探测失败\n"
                error_msg += "   3. 防火墙阻止\n\n"
                error_msg += "   建议操作：\n"
                error_msg += "   - 设置环境变量: export HTTPS_PROXY=http://host:port\n"
                error_msg += "   - 运行 'python main.py --test-proxy' 进行网络诊断\n"
                error_msg += "   - 运行 'python scripts/diagnose_network.py' 查看详细诊断"

            raise RuntimeError(error_msg) from e
        return "unknown"


async def test_proxy_connection() -> int:
    """Test proxy connection (V142.0 network diagnostic).

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    print("\n" + "="*80)
    print("V142.0 网络代理诊断测试")
    print("="*80)
    print()

    # Import BaseExtractor for proxy testing
    from src.api.collectors.base_extractor import BaseExtractor

    results = {
        "env_vars": [],
        "wsl2_detected": False,
        "proxy_discovered": None,
        "ip_direct": None,
        "ip_via_proxy": None,
    }

    # Test 1: Check environment variables
    print("1️⃣  环境变量检测")
    print("-" * 80)
    for var in ["PROXY_SERVER", "HTTP_PROXY", "HTTPS_PROXY"]:
        value = os.getenv(var)
        if value:
            results["env_vars"].append((var, value))
            print(f"  ✓ {var} = {value}")
        else:
            print(f"  - {var} = (未设置)")
    print()

    # Test 2: WSL2 detection
    print("2️⃣  WSL2 环境检测")
    print("-" * 80)
    extractor = BaseExtractor()
    if extractor._is_wsl2():
        results["wsl2_detected"] = True
        wsl_host = extractor._get_wsl2_host_ip()
        print(f"  ✓ WSL2 环境: 是")
        print(f"  ✓ 宿主机 IP: {wsl_host}")
    else:
        print(f"  - WSL2 环境: 否")
    print()

    # Test 3: Proxy discovery
    print("3️⃣  代理自动发现")
    print("-" * 80)
    proxy_config = extractor._discover_proxy()
    results["proxy_discovered"] = proxy_config
    if proxy_config:
        print(f"  ✓ 代理已发现: {proxy_config['server']}")
    else:
        print(f"  ✗ 未发现可用代理")
    print()

    # Test 4: Direct IP detection (without proxy)
    print("4️⃣  直连 IP 检测")
    print("-" * 80)
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get("https://api.ipify.org", timeout=10) as resp:
                ip_direct = await resp.text()
                results["ip_direct"] = ip_direct
                print(f"  ✓ 直连 IP: {ip_direct}")
    except Exception as e:
        print(f"  ✗ 直连失败: {e}")
    print()

    # Test 5: Proxy IP detection (with proxy)
    if proxy_config:
        print("5️⃣  代理 IP 检测")
        print("-" * 80)
        try:
            import aiohttp
            proxy_url = proxy_config["server"]
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://api.ipify.org",
                    timeout=10,
                    proxy=proxy_url
                ) as resp:
                    ip_via_proxy = await resp.text()
                    results["ip_via_proxy"] = ip_via_proxy
                    print(f"  ✓ 代理 IP: {ip_via_proxy}")
                    if results["ip_direct"]:
                        if results["ip_direct"] != ip_via_proxy:
                            print(f"  ✓ 代理生效: IP 已变更 ({results['ip_direct']} → {ip_via_proxy})")
                        else:
                            print(f"  ⚠️  警告: 代理 IP 与直连 IP 相同，代理可能未生效")
                    else:
                        print(f"  ✓ 代理连接成功 (直连不可用，无法比较)")
        except Exception as e:
            print(f"  ✗ 代理连接失败: {e}")
        print()
    else:
        print("5️⃣  代理 IP 检测")
        print("-" * 80)
        print(f"  ⊘ 跳过 (未发现代理)")
        print()

    # Final verdict
    print("="*80)
    print("📊 诊断总结")
    print("="*80)

    if results["proxy_discovered"]:
        print(f"✅ 代理配置成功")
        print(f"   环境变量: {len(results['env_vars'])} 个")
        if results["wsl2_detected"]:
            print(f"   WSL2 检测: 启用")
        if results["ip_via_proxy"]:
            print(f"   代理连接: 成功 (IP: {results['ip_via_proxy']})")
        return 0
    else:
        print(f"❌ 代理配置失败")
        print(f"   建议：")
        if not results["env_vars"]:
            print(f"   1. 设置环境变量 (推荐 HTTPS_PROXY)")
        if results["wsl2_detected"]:
            print(f"   2. 确保 Windows 代理软件允许局域网连接")
            print(f"   3. 检查防火墙是否阻止 WSL2 访问")
        print(f"   4. 运行 'python scripts/diagnose_network.py' 获取详细信息")
        return 1


# ============================================================================
# Mode Implementations
# ============================================================================

async def run_single_mode(args) -> int:
    """Run in single mode.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    logger.info("🎯 启动单次收割模式")
    print("")

    # V142.8: Pass proxy_file parameter to HarvesterService
    proxy_file = args.proxy_file if args.proxy_file != "proxies.txt" or Path(args.proxy_file).exists() else None

    service = HarvesterService(
        mode="single",
        enable_ghost_protocol=not args.no_ghost,
        enable_queue=not args.no_queue,
        limit=args.limit,
        dry_run=args.dry_run,
        proxy_file=proxy_file,
    )

    try:
        await service.run()
        return 0
    except Exception as e:
        logger.error(f"❌ 单次收割失败: {e}")
        return 1


async def run_cruise_mode(args) -> int:
    """Run in cruise mode (24h automatic harvesting).

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    logger.info("🚀 启动 24h 全自动巡航模式")
    print("")

    # V142.8: Pass proxy_file parameter to HarvesterService
    proxy_file = args.proxy_file if args.proxy_file != "proxies.txt" or Path(args.proxy_file).exists() else None

    service = HarvesterService(
        mode="cruise",
        enable_ghost_protocol=not args.no_ghost,
        enable_queue=not args.no_queue,
        dry_run=args.dry_run,
        proxy_file=proxy_file,
    )

    try:
        await service.run()
        return 0
    except Exception as e:
        logger.error(f"❌ 巡航模式失败: {e}")
        return 1


async def run_check_mode(args) -> int:
    """Run in check mode (data quality verification).

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    logger.info("🔍 启动数据质量检查模式")
    print("")

    # Import check_data_quality module
    try:
        sys.path.insert(0, "scripts")
        import check_data_quality

        # Run the check
        result = await check_data_quality.main() if hasattr(check_data_quality, 'main') else 0
        return result if isinstance(result, int) else 0
    except ImportError:
        logger.warning("⚠️  check_data_quality.py 未找到，跳过数据质量检查")
        return 0
    except Exception as e:
        logger.error(f"❌ 数据质量检查失败: {e}")
        return 1


# ============================================================================
# CLI Interface
# ============================================================================

def parse_args() -> argparse.Namespace:
    """Parse command-line arguments.

    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        description="FootballPrediction V142.0 - Unified Command Center",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single mode - harvest Premier League 23/24 (dry run)
  python main.py --mode single --league "Premier League" --season "23/24" --dry-run

  # Cruise mode - 24h automatic harvesting
  python main.py --mode cruise

  # Check mode - data quality verification
  python main.py --mode check

  # Disable Ghost Protocol (for debugging)
  python main.py --mode single --no-ghost

  # Limit processing to 50 matches
  python main.py --mode single --limit 50
        """
    )

    parser.add_argument(
        "--mode",
        type=str,
        choices=["single", "cruise", "check"],
        default="single",
        help="运行模式: single (单次收割) / cruise (24h 巡航) / check (数据质量检查)"
    )

    parser.add_argument(
        "--league",
        type=str,
        help="联赛名称 (例如: \"Premier League\")"
    )

    parser.add_argument(
        "--season",
        type=str,
        help="赛季格式 (例如: \"23/24\")"
    )

    parser.add_argument(
        "--limit",
        type=int,
        help="最大处理数量"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="干跑模式 (不实际采集数据)"
    )

    parser.add_argument(
        "--no-ghost",
        action="store_true",
        help="禁用幽灵协议"
    )

    parser.add_argument(
        "--no-queue",
        action="store_true",
        help="禁用队列系统"
    )

    parser.add_argument(
        "--skip-precheck",
        action="store_true",
        help="跳过环境预检"
    )

    parser.add_argument(
        "--test-proxy",
        action="store_true",
        help="测试代理连接性 (V142.0 网络诊断)"
    )

    parser.add_argument(
        "--proxy-file",
        type=str,
        default="proxies.txt",
        help="V142.7: 代理配置文件路径 (默认: proxies.txt，留空启用 WSL2 自动探测)"
    )

    return parser.parse_args()


# ============================================================================
# Main Entry Point
# ============================================================================

async def main() -> int:
    """Main entry point.

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    args = parse_args()

    # Print banner
    print_banner()

    # Handle --test-proxy flag
    if args.test_proxy:
        return await test_proxy_connection()

    # Environment pre-check
    if not args.skip_precheck:
        env_info = check_environment()
        ip_address = await check_ip_address(fail_fast=True)
        print("")

    # Route to appropriate mode
    if args.mode == "single":
        return await run_single_mode(args)
    elif args.mode == "cruise":
        return await run_cruise_mode(args)
    elif args.mode == "check":
        return await run_check_mode(args)
    else:
        logger.error(f"❌ 未知模式: {args.mode}")
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("")
        logger.info("👋 收到中断信号，正在退出...")
        sys.exit(130)
    except Exception as e:
        logger.error(f"❌ 未处理的异常: {e}")
        sys.exit(1)
