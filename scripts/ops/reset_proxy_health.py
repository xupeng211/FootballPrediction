#!/usr/bin/env python3
"""
V32.0 Proxy Health Reset - 代理池一键恢复工具

核心功能:
1. 强制清除所有代理的黑名单状态
2. 清除所有代理的冷却期和失败计数
3. 生成复位前后的状态对比报告
4. 支持 --dry-run 模式预览

使用场景:
- 代理池大面积被封禁需要快速恢复
- 手动重置代理状态进行故障排查
- 定期维护清理代理状态

Author: 高级 SRE (Staff SRE)
Date: 2026-01-11
Version: V32.0 (Proxy Health Reset)
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# V29.0: 加载 .env 文件
from dotenv import load_dotenv
load_dotenv(override=True)

from core.scrapers.oddsportal import (
    CircuitBreakerManager,
    CircuitBreakerConfig,
)

# ============================================================================
# 日志配置
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('logs/proxy_reset.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ============================================================================
# Proxy Reset 功能
# ============================================================================

def get_proxy_status_before(manager: CircuitBreakerManager) -> dict:
    """获取复位前的状态"""
    status = manager.get_status()
    status["timestamp"] = datetime.now().isoformat()
    status["blacklisted_proxies_detail"] = list(manager.blacklist_until.keys())
    status["cooldown_proxies_detail"] = list(manager.cooldown_until.keys())
    return status


def get_proxy_status_after(manager: CircuitBreakerManager) -> dict:
    """获取复位后的状态"""
    status = manager.get_status()
    status["timestamp"] = datetime.now().isoformat()
    return status


def print_status_report(before: dict, after: dict, dry_run: bool = False):
    """打印状态对比报告"""
    logger.info("")
    logger.info("=" * 70)
    logger.info("📊 V32.0 Proxy Health Reset 状态报告")
    logger.info("=" * 70)

    # 复位前状态
    logger.info(f"\n📋 复位前状态 ({before['timestamp']})")
    logger.info(f"  总代理数: {before['total_proxies']}")
    logger.info(f"  可用代理: {before['active_proxies']}")
    logger.info(f"  黑名单代理: {before['blacklisted_proxies']}")
    logger.info(f"  可用率: {before['availability_rate']}")

    if before.get('blacklisted_proxies_detail'):
        logger.info(f"  黑名单详情:")
        for proxy in before['blacklisted_proxies_detail']:
            logger.info(f"    - {proxy}")

    if before.get('cooldown_proxies_detail'):
        logger.info(f"  冷却期详情:")
        for proxy in before['cooldown_proxies_detail']:
            logger.info(f"    - {proxy}")

    # 复位后状态
    logger.info(f"\n✅ 复位后状态 ({after['timestamp']})")
    logger.info(f"  总代理数: {after['total_proxies']}")
    logger.info(f"  可用代理: {after['active_proxies']}")
    logger.info(f"  黑名单代理: {after['blacklisted_proxies']}")
    logger.info(f"  可用率: {after['availability_rate']}")

    # 改进摘要
    active_change = after['active_proxies'] - before['active_proxies']
    logger.info(f"\n📈 改进摘要")
    logger.info(f"  可用代理变化: +{active_change}")
    logger.info(f"  可用率提升: {before['availability_rate']} → {after['availability_rate']}")

    if dry_run:
        logger.info("\n⚠️  干跑模式 - 未实际执行复位")


# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="V32.0 Proxy Health Reset - 代理池一键恢复"
    )
    parser.add_argument(
        '--proxy-ports',
        type=int,
        nargs='+',
        default=list(range(7890, 7898)),
        help='代理端口列表 (默认: 7890-7897)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='干跑模式，只预览不执行'
    )
    parser.add_argument(
        '--failure-threshold',
        type=int,
        default=3,
        help='失败阈值 (默认: 3)'
    )
    parser.add_argument(
        '--cooldown-timeout',
        type=int,
        default=300,
        help='冷却超时时间（秒） (默认: 300)'
    )

    args = parser.parse_args()

    logger.info("=" * 70)
    logger.info("🚀 V32.0 Proxy Health Reset 启动")
    logger.info("=" * 70)
    logger.info(f"代理端口: {args.proxy_ports}")
    logger.info(f"干跑模式: {args.dry_run}")
    logger.info("")

    # 构建代理列表
    proxy_pool = [f"http://172.25.16.1:{port}" for port in args.proxy_ports]
    logger.info(f"📋 代理池 ({len(proxy_pool)} 个):")
    for proxy in proxy_pool:
        logger.info(f"  - {proxy}")

    # 创建熔断器管理器
    config = CircuitBreakerConfig(
        failure_threshold=args.failure_threshold,
        cooldown_timeout=args.cooldown_timeout,
        emergency_stop_threshold=0.3
    )
    manager = CircuitBreakerManager(config, proxy_pool)

    # 获取复位前状态
    before_status = get_proxy_status_before(manager)

    if args.dry_run:
        # 干跑模式 - 模拟复位
        logger.info("\n🔍 干跑模式 - 模拟复位操作...")
        after_status = before_status.copy()
        after_status["active_proxies"] = len(proxy_pool)
        after_status["blacklisted_proxies"] = 0
        after_status["availability_rate"] = "100.0%"
        after_status["timestamp"] = datetime.now().isoformat()
    else:
        # 实际执行复位
        logger.info("\n🔄 执行代理池复位...")
        reset_result = manager.reset_all_proxies()
        after_status = get_proxy_status_after(manager)

        logger.info(f"\n✅ 复位完成")
        logger.info(f"  清除黑名单: {reset_result['blacklisted_cleared']} 个")
        logger.info(f"  清除冷却期: {reset_result['cooldown_cleared']} 个")
        logger.info(f"  总清除: {reset_result['total_cleared']} 个")

    # 打印状态报告
    print_status_report(before_status, after_status, args.dry_run)

    logger.info("\n" + "=" * 70)
    logger.info("✅ V32.0 Proxy Health Reset 完成")
    logger.info("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
