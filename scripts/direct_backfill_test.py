#!/usr/bin/env python3
"""
简化的历史数据采集脚本（直接调用，不使用Celery）
解决速率限制问题
"""

import time
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
import random

from src.tasks.data_collection_tasks import collect_fotmob_data

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def generate_sample_dates(count: int = 10) -> List[str]:
    """生成少量示例日期用于测试"""
    dates = []
    base_date = datetime(2024, 1, 1)

    for i in range(count):
        # 每隔一天生成一个日期
        target_date = base_date + timedelta(days=i*7)  # 每周一个日期
        dates.append(target_date.strftime("%Y%m%d"))

    return dates


def trigger_direct_collection(dates: List[str], api_throttle_delay: float = 5.0) -> Dict[str, Any]:
    """直接调用数据采集函数（不通过Celery）"""
    logger.info(f"🚀 开始直接数据采集，共 {len(dates)} 个日期")
    logger.info(f"⚠️ 启用速率节流: 每个任务间隔 {api_throttle_delay} 秒，避免 API 429 错误")

    success_count = 0
    error_count = 0
    total_matches = 0
    total_saved = 0

    for i, date in enumerate(dates, 1):
        try:
            logger.info(f"📅 [{i}/{len(dates)}] 开始采集日期 {date} 的数据")

            # 直接调用数据采集函数
            result = collect_fotmob_data(date=date)

            if result.get('status') == 'success':
                success_count += 1
                matches_collected = result.get('matches_collected', 0)
                records_saved = result.get('records_saved', 0)
                total_matches += matches_collected
                total_saved += records_saved

                logger.info(f"✅ 采集成功: {matches_collected} 场比赛, {records_saved} 条记录保存")
            else:
                error_count += 1
                logger.error(f"❌ 采集失败: {result.get('error', 'Unknown error')}")

            # 🚨 关键修复：每个任务后都强制等待，避免 API 速率限制
            if i < len(dates):  # 最后一个任务不需要等待
                logger.info(f"⏳ 正在等待 {api_throttle_delay} 秒，避免 API 速率限制...")
                time.sleep(api_throttle_delay)

        except Exception as e:
            logger.error(f"❌ 采集日期 {date} 失败: {e}")
            error_count += 1

    # 统计结果
    result_summary = {
        "total_dates": len(dates),
        "successful_tasks": success_count,
        "failed_tasks": error_count,
        "success_rate": (success_count / len(dates)) * 100 if dates else 0,
        "total_matches_collected": total_matches,
        "total_records_saved": total_saved,
        "average_matches_per_date": total_matches / success_count if success_count > 0 else 0
    }

    logger.info(f"📊 采集统计: {result_summary}")
    return result_summary


def main():
    """主函数"""
    logger.info("🎯 开始简化的历史数据采集（直接调用模式）")

    # 生成少量测试日期
    test_dates = [
        "20241201",  # 2024年12月1日
        "20241208",  # 2024年12月8日
        "20241215",  # 2024年12月15日
        "20241222",  # 2024年12月22日
        "20241229",  # 2024年12月29日
    ]

    logger.info(f"📅 测试日期: {test_dates}")

    # 触发采集任务
    if test_dates:
        result_summary = trigger_direct_collection(
            test_dates,
            api_throttle_delay=5.0  # 每个 API 调用间隔 5 秒，避免 429 错误
        )

        logger.info(f"🎉 数据采集完成！")
        logger.info(f"📊 采集统计: {result_summary}")
    else:
        logger.warning("⚠️ 没有指定测试日期")


if __name__ == "__main__":
    main()