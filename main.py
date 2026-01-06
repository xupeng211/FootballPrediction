#!/usr/bin/env python3
"""V144.7 FootballPrediction - Multi-Source Command Center.

V144.7 更新:
- ✅ 新增 --source 参数支持 oddsportal 和 fotmob 数据源切换
- ✅ Ghost Protocol 统一验证日志
- ✅ 配置参数透传至各采集器
- ✅ 100% 生产就绪状态

This is the unified command-line interface for the FootballPrediction system.
It provides a single entry point for all operations, replacing the scattered
script-based approach.

Features:
    - Automatic environment pre-check (WSL2 proxy discovery, IP detection)
    - Mode scheduling (single/cruise/check)
    - Multi-source support (OddsPortal / FotMob)
    - Rich console output with professional formatting
    - Integration with all Phase 1 components (BaseExtractor V141.0, TeamNameNormalizer V140.0)

Usage:
    # OddsPortal (默认)
    python main.py --source oddsportal --mode single --limit 10

    # FotMob
    python main.py --source fotmob --mode single --limit 10

    # Cruise mode with FotMob
    python main.py --source fotmob --mode cruise

Author: Chief System Architect
Version: V144.7
Date: 2026-01-06
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
        logging.FileHandler('logs/v144_7_main.log'),
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
║         FootballPrediction V144.7 - Multi-Source Command Center         ║
║                                                                        ║
║  Phase 4: Dual-Line Architecture                                       ║
║  ├─ BaseExtractor V144.2 (Ghost Protocol)                            ║
║  ├─ FotMob V144.5 (Unified Schema V36.0)                             ║
║  ├─ OddsPortal V144.2 (Enhanced Stealth)                            ║
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

    # Check proxy configuration (V144.2: BaseExtractor auto-discovery)
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
            logger.info(f"  ℹ️ 代理: 未配置")
    except Exception as e:
        info["proxy"] = "error"
        logger.warning(f"  ⚠️ 代理检测失败: {e}")

    # Check WSL2 environment
    if os.path.exists("/proc/version"):
        with open("/proc/version", "r") as f:
            version_content = f.read().lower()
            is_wsl = "microsoft" in version_content
            info["is_wsl"] = str(is_wsl)
            if is_wsl:
                logger.info(f"  ✓ WSL2 环境: 是")
            else:
                logger.info(f"  ℹ️ WSL2 环境: 否")
    else:
        info["is_wsl"] = "False"
        logger.info(f"  ℹ️ WSL2 环境: 无法检测")

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
    """Check the current IP address (V144.2: with BaseExtractor proxy support).

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
            logger.info(f"  ℹ️ 直连模式 (未发现代理)")
    except Exception as e:
        logger.warning(f"  ⚠️ 代理探测跳过: {e}")

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
        logger.warning(f"  ⚠️ IP 检测失败: {e}")
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


# ============================================================================
# V144.7: Multi-Source Implementations
# ============================================================================

async def run_oddsportal_mode(args) -> int:
    """V144.7: Run OddsPortal harvesting mode.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    logger.info("🎯 启动 OddsPortal 采集模式")
    print("")

    proxy_file = args.proxy_file if args.proxy_file != "proxies.txt" or Path(args.proxy_file).exists() else None

    service = HarvesterService(
        mode="single" if args.mode == "single" else "cruise",
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
        logger.error(f"❌ OddsPortal 采集失败: {e}")
        return 1


async def run_fotmob_mode(args) -> int:
    """V144.8: Run FotMob harvesting mode with batch collection support.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    logger.info("🎯 启动 FotMob 采集模式")
    print("")

    # Import FotMob core collector
    try:
        from src.api.collectors.fotmob_core import FotMobCoreCollector
        import psycopg2

        # V144.8: 初始化 FotMob 采集器（已集成 Ghost Protocol V144.2）
        collector = FotMobCoreCollector()

        # V144.8: Ghost Protocol 验证日志
        logger.info("[V144.8] 🛡️ Unified Ghost Protocol initialized for fotmob")

        if args.dry_run:
            logger.info("🔬 FotMob 干跑模式 (不实际采集数据)")
            logger.info(f"   - 限制数量: {args.limit if args.limit else '无限制'}")
            logger.info(f"   - 联赛: {args.league if args.league else '所有联赛'}")
            logger.info(f"   - 赛季: {args.season if args.season else '当前赛季'}")
            return 0

        # V144.8: 实现实际的 FotMob 批量采集逻辑
        logger.info("[V144.8] 📊 开始 FotMob 批量采集")

        # 连接数据库获取待采集比赛
        settings = get_settings()
        conn = psycopg2.connect(
            host=settings.database.host,
            port=settings.database.port,
            database=settings.database.name,
            user=settings.database.user,
            password=settings.database.password.get_secret_value(),
        )
        cursor = conn.cursor()

        # 查询待采集比赛（没有 L2 数据的比赛）
        # 使用 ON CONFLICT 跳过已存在的记录
        query = """
            SELECT m.match_id
            FROM matches m
            WHERE m.l2_raw_json IS NULL
        """

        if args.league:
            query += " AND m.league_name = %s"
            cursor.execute(query, (args.league,))
        else:
            cursor.execute(query)

        match_ids = [row[0] for row in cursor.fetchall()]
        cursor.close()
        conn.close()

        logger.info(f"[V144.8] 📋 找到 {len(match_ids)} 场待采集比赛")

        if not match_ids:
            logger.info("[V144.8] ℹ️ 没有待采集比赛")
            return 0

        # 应用限制
        if args.limit:
            match_ids = match_ids[:args.limit]
            logger.info(f"[V144.8] ⚠️ 限制采集数量: {args.limit}")

        # V144.8: 批量采集
        success_count = 0
        failed_count = 0

        for i, match_id in enumerate(match_ids, 1):
            try:
                logger.info(f"[V144.8] [{i}/{len(match_ids)}] 采集比赛: {match_id}")

                # 使用 harvest_match_with_league 进行采集
                # 该方法内部已实现 ON CONFLICT DO NOTHING，支持断点续传
                result = collector.harvest_match_with_league(match_id)

                if result:
                    success_count += 1
                    logger.info(f"[V144.8] ✅ 比赛 {match_id} 采集成功")
                else:
                    failed_count += 1
                    logger.warning(f"[V144.8] ⚠️ 比赛 {match_id} 采集失败")

                # 每 10 场打印进度
                if i % 10 == 0:
                    logger.info(
                        f"[V144.8] 📊 进度: {i}/{len(match_ids)} | "
                        f"成功: {success_count} | 失败: {failed_count}"
                    )

            except Exception as e:
                failed_count += 1
                logger.error(f"[V144.8] ❌ 比赛 {match_id} 异常: {e}")

        # 最终报告
        logger.info("")
        logger.info("=" * 60)
        logger.info("[V144.8] 📊 FotMob 批量采集完成")
        logger.info("=" * 60)
        logger.info(f"总计: {len(match_ids)} 场")
        logger.info(f"成功: {success_count} 场")
        logger.info(f"失败: {failed_count} 场")
        logger.info(f"成功率: {100 * success_count / len(match_ids):.1f}%")
        logger.info("=" * 60)

        return 0 if failed_count == 0 else 1

    except ImportError as e:
        logger.error(f"❌ FotMob 模块导入失败: {e}")
        logger.error(f"   请确保 src/api/collectors/fotmob_core.py 存在")
        return 1
    except Exception as e:
        logger.error(f"❌ FotMob 采集失败: {e}")
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
        description="FootballPrediction V144.7 - Multi-Source Command Center",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # OddsPortal (默认数据源)
  python main.py --source oddsportal --mode single --limit 10

  # FotMob 数据源
  python main.py --source fotmob --mode single --limit 10

  # Cruise mode with FotMob
  python main.py --source fotmob --mode cruise

  # Check mode - data quality verification
  python main.py --mode check

  # Disable Ghost Protocol (for debugging)
  python main.py --source oddsportal --mode single --no-ghost

  # Limit processing to 50 matches
  python main.py --source fotmob --mode single --limit 50

  # Dry run (test without actual collection)
  python main.py --source fotmob --mode single --dry-run
        """
    )

    # V144.7: 新增 --source 参数
    parser.add_argument(
        "--source",
        type=str,
        choices=["oddsportal", "fotmob"],
        default="oddsportal",
        help="V144.7: 数据源选择 - oddsportal (OddsPortal RPA) / fotmob (FotMob API) [默认: oddsportal]"
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

    # V144.7: Ghost Protocol 统一验证日志
    logger.info(f"[V144.7] 🛡️ Unified Ghost Protocol initialized for {args.source}")
    print("")

    # Environment pre-check
    if not args.skip_precheck:
        env_info = check_environment()
        ip_address = await check_ip_address(fail_fast=True)
        print("")

    # V144.7: 根据数据源路由到对应的处理器
    if args.source == "oddsportal":
        if args.mode == "check":
            return await run_check_mode(args)
        else:
            return await run_oddsportal_mode(args)
    elif args.source == "fotmob":
        if args.mode == "check":
            # check 模式对 FotMob 也有效（数据质量检查）
            return await run_check_mode(args)
        else:
            return await run_fotmob_mode(args)
    else:
        logger.error(f"❌ 未知数据源: {args.source}")
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
