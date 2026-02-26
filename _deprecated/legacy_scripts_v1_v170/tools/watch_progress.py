#!/usr/bin/env python3
"""
V41.23 进程心跳监测器

目标：
1. 每 10 分钟统计一次 logs/v41_23_harvest.log 中的更新总数
2. 如果连续 20 分钟没有新增"更新哈希"记录，触发警报并截图
Author: 首席自动化运维专家
Version: V41.23
Date: 2026-01-13
"""

import logging
import re
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path

LOG_FILE = "logs/v41_23_harvest.log"
ALERT_THRESHOLD_MINUTES = 20  # 20分钟无更新触发警报
CHECK_INTERVAL_MINUTES = 10   # 每10分钟检查一次

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def get_last_update_time(log_file: str) -> datetime:
    """
    获取最后一次"更新哈希"的时间

    Args:
        log_file: 日志文件路径

    Returns:
        最后更新时间的 datetime 对象，如果未找到则返回 None
    """
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            # 从文件末尾向前搜索
            for line in reversed(f.readlines()):
                if "更新哈希:" in line:
                    # 提取时间戳: [2026-01-13 16:48:23]
                    match = re.search(r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]', line)
                    if match:
                        return datetime.strptime(match.group(1), '%Y-%m-%d %H:%M:%S')
    except FileNotFoundError:
        logger.error(f"日志文件不存在: {log_file}")
    except Exception as e:
        logger.error(f"读取日志文件失败: {e}")

    return None


def get_total_updates(log_file: str) -> int:
    """
    统计日志中"更新哈希"的总数

    Args:
        log_file: 日志文件路径

    Returns:
        更新总数
    """
    try:
        result = subprocess.run(
            ['grep', '-c', '更新哈希:', log_file],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            return int(result.stdout.strip())
    except Exception as e:
        logger.error(f"统计更新数失败: {e}")

    return 0


def get_progress_stats(log_file: str) -> dict:
    """
    获取采集进度统计

    Args:
        log_file: 日志文件路径

    Returns:
        包含进度信息的字典
    """
    try:
        # 获取已处理日期数
        result = subprocess.run(
            ['grep', '-c', '处理日期:', log_file],
            capture_output=True,
            text=True
        )
        dates_processed = int(result.stdout.strip()) if result.returncode == 0 else 0

        # 获取最后处理的日期
        result = subprocess.run(
            ['tail', '-100', log_file],
            capture_output=True,
            text=True
        )
        last_date = None
        if result.returncode == 0:
            match = re.search(r'\[(\d+)/(\d+)\] 处理日期: ([\d-]+)', result.stdout)
            if match:
                last_date = f"{match.group(1)}/{match.group(2)} ({match.group(3)})"

        return {
            'dates_processed': dates_processed,
            'total_updates': get_total_updates(log_file),
            'last_date': last_date,
        }
    except Exception as e:
        logger.error(f"获取进度统计失败: {e}")
        return {}


def take_screenshot(output_file: str):
    """
    截取终端截图（记录当前状态）

    Args:
        output_file: 输出文件路径
    """
    try:
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ['scrot', output_file],
            check=True,
            capture_output=True
        )
        logger.info(f"截图已保存: {output_file}")
    except FileNotFoundError:
        # scrot 未安装，尝试替代方案
        logger.warning("scrot 未安装，跳过截图")
    except Exception as e:
        logger.error(f"截图失败: {e}")


def trigger_alert(reason: str):
    """
    触发警报

    Args:
        reason: 警报原因
    """
    logger.error("=" * 73)
    logger.error("🚨 警报触发！")
    logger.error(f"原因: {reason}")
    logger.error("=" * 73)

    # 截图记录
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    screenshot_file = f"logs/alert_screenshot_{timestamp}.png"
    take_screenshot(screenshot_file)


def monitor_progress():
    """
    主监控循环
    """
    logger.info("=" * 73)
    logger.info("💓 V41.23 进程心跳监测器启动")
    logger.info("=" * 73)
    logger.info(f"监控日志: {LOG_FILE}")
    logger.info(f"检查间隔: {CHECK_INTERVAL_MINUTES} 分钟")
    logger.info(f"警报阈值: {ALERT_THRESHOLD_MINUTES} 分钟无更新")
    logger.info("")

    consecutive_failures = 0

    while True:
        try:
            # 获取进度统计
            stats = get_progress_stats(LOG_FILE)
            last_update = get_last_update_time(LOG_FILE)

            # 计算距离上次更新的时间
            time_since_update = None
            if last_update:
                time_since_update = datetime.now() - last_update
                minutes_since = time_since_update.total_seconds() / 60
            else:
                minutes_since = float('inf')

            # 显示当前状态
            logger.info("-" * 73)
            logger.info(f"💓 检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"📊 进度: {stats.get('last_date', 'N/A')}")
            logger.info(f"📈 已处理日期: {stats.get('dates_processed', 0)}")
            logger.info(f"✅ 已更新哈希: {stats.get('total_updates', 0)} 场")

            if last_update:
                logger.info(f"🕐 最后更新: {last_update.strftime('%Y-%m-%d %H:%M:%S')}")
                logger.info(f"⏱️  距上次更新: {int(minutes_since)} 分钟")
            else:
                logger.warning("⚠️  未找到任何更新记录")

            # 检查是否需要触发警报
            if minutes_since >= ALERT_THRESHOLD_MINUTES:
                consecutive_failures += 1
                trigger_alert(
                    f"连续 {int(minutes_since)} 分钟无新增更新（阈值: {ALERT_THRESHOLD_MINUTES} 分钟）"
                )
            else:
                consecutive_failures = 0
                logger.info("✅ 系统运行正常")

        except Exception as e:
            logger.error(f"监控检查失败: {e}")

        # 等待下一次检查
        logger.info(f"💤 下次检查: {CHECK_INTERVAL_MINUTES} 分钟后")
        logger.info("")
        time.sleep(CHECK_INTERVAL_MINUTES * 60)


if __name__ == "__main__":
    try:
        monitor_progress()
    except KeyboardInterrupt:
        logger.info("\n监控已停止")
