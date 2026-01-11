#!/usr/bin/env python3
"""
V32.1 Log Lifecycle Management - 日志清理工具

核心功能:
1. 自动扫描 logs/ 目录
2. 物理删除超过指定天数的 .log 和 .json 文件
3. 支持 --dry-run 模式预览
4. 保留其他扩展名文件（.py, .txt 等）
5. TDD 驱动开发

使用场景:
- 定期清理过期日志释放磁盘空间
- 自动化运维脚本
- 日志生命周期管理

Author: 高级基础设施工程师 (Principal Infrastructure Engineer)
Date: 2026-01-11
Version: V32.1 (Log Lifecycle Management)
"""

import argparse
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# V29.0: 加载 .env 文件
from dotenv import load_dotenv
load_dotenv(override=True)


# ============================================================================
# 日志配置
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('logs/clean_old_logs.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ============================================================================
# Log Cleanup Functions
# ============================================================================

def cleanup_logs(log_dir: Path, days: int = 7, dry_run: bool = False) -> int:
    """清理超过指定天数的日志文件

    Args:
        log_dir: 日志目录路径
        days: 保留天数（默认 7 天）
        dry_run: 干跑模式，不实际删除

    Returns:
        删除的文件数量
    """
    if not log_dir.exists():
        logger.warning(f"日志目录不存在: {log_dir}")
        return 0

    # 目标扩展名
    target_extensions = {'.log', '.json'}

    # 计算截止时间
    cutoff_time = datetime.now() - timedelta(days=days)

    # 扫描文件
    deleted_count = 0
    scanned_count = 0

    for file_path in log_dir.rglob('*'):
        if not file_path.is_file():
            continue

        # 检查扩展名
        if file_path.suffix.lower() not in target_extensions:
            continue

        scanned_count += 1

        # 检查文件修改时间
        file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)

        if file_mtime < cutoff_time:
            # 文件超过指定天数，需要删除
            file_age_days = (datetime.now() - file_mtime).days

            if dry_run:
                logger.info(f"[DRY-RUN] 将删除: {file_path.name} ({file_age_days} 天前)")
            else:
                try:
                    file_path.unlink()
                    logger.info(f"已删除: {file_path.name} ({file_age_days} 天前)")
                    deleted_count += 1
                except Exception as e:
                    logger.error(f"删除失败 {file_path.name}: {e}")

    logger.info(f"扫描文件: {scanned_count} 个")
    logger.info(f"删除文件: {deleted_count} 个")

    return deleted_count


# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="V32.1 Log Lifecycle Management - 日志清理工具"
    )
    parser.add_argument(
        '--log-dir',
        type=str,
        default='logs',
        help='日志目录路径 (默认: logs)'
    )
    parser.add_argument(
        '--days',
        type=int,
        default=7,
        help='保留天数 (默认: 7)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='干跑模式，只预览不删除'
    )
    parser.add_argument(
        '--extensions',
        type=str,
        nargs='+',
        default=['.log', '.json'],
        help='要清理的文件扩展名 (默认: .log .json)'
    )

    args = parser.parse_args()

    logger.info("=" * 70)
    logger.info("🧹 V32.1 Log Lifecycle Management 启动")
    logger.info("=" * 70)
    logger.info(f"日志目录: {args.log_dir}")
    logger.info(f"保留天数: {args.days}")
    logger.info(f"目标扩展名: {', '.join(args.extensions)}")
    logger.info(f"干跑模式: {args.dry_run}")
    logger.info("")

    # 验证日志目录
    log_dir = Path(args.log_dir)
    if not log_dir.exists():
        logger.error(f"❌ 日志目录不存在: {log_dir}")
        return 1

    # 执行清理
    if args.dry_run:
        logger.info("🔍 干跑模式 - 预览将删除的文件...")

    deleted = cleanup_logs(
        log_dir=log_dir,
        days=args.days,
        dry_run=args.dry_run
    )

    logger.info("")
    logger.info("=" * 70)
    if args.dry_run:
        logger.info(f"📊 干跑完成 - 将删除 {deleted} 个文件")
        logger.info("💡 移除 --dry-run 参数以执行实际删除")
    else:
        logger.info(f"✅ 清理完成 - 已删除 {deleted} 个文件")
    logger.info("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
