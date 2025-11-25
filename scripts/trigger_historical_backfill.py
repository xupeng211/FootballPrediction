#!/usr/bin/env python3
"""
FotMob 历史数据回溯采集脚本
根据配置文件回溯采集过去 3 个赛季的核心联赛数据
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
import random
import time

import requests
from src.tasks.data_collection_tasks import collect_fotmob_data

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_data_config() -> dict[str, Any]:
    """加载数据源配置"""
    import json
    with open('/app/src/config/data_sources.json') as f:
        return json.load(f)


def generate_historical_dates(backfill_seasons: int, dates_per_season: int = 50) -> list[str]:
    """生成需要回溯的历史日期列表

    Args:
        backfill_seasons: 回溯的年份数
        dates_per_season: 每个赛季生成的日期数

    Returns:
        需要采集的日期列表 (YYYYMMDD 格式)
    """
    dates = []
    current_date = datetime.now()

    # 为每个赛季生成关键日期
    for years_back in range(1, backfill_seasons + 1):
        season_year = current_date.year - years_back
        season_start = datetime(season_year, 8, 1)  # 赛季通常8月开始
        season_end = datetime(season_year + 1, 5, 31)  # 赛季通常次年5月结束

        # 计算赛季总天数
        total_days = (season_end - season_start).days

        # 生成均匀分布的关键日期
        for i in range(dates_per_season):
            # 在赛季期间均匀分布日期
            day_offset = int((i / dates_per_season) * total_days)
            target_date = season_start + timedelta(days=day_offset)
            dates.append(target_date.strftime("%Y%m%d"))

    return dates


def trigger_fotmob_collection_tasks(dates: list[str], api_throttle_delay: float = 5.0) -> dict[str, Any]:
    """触发 FotMob 数据采集任务

    Args:
        dates: 需要采集的日期列表
        api_throttle_delay: 每个任务间的API节流延迟时间（秒）

    Returns:
        采集结果统计
    """
    logger.info(f"🚀 开始 FotMob 历史数据回溯采集，共 {len(dates)} 个日期")
    logger.info(f"⚠️ 启用速率节流: 每个任务间隔 {api_throttle_delay} 秒，避免 API 429 错误")

    success_count = 0
    error_count = 0
    total_matches = 0
    total_saved = 0

    for i, date in enumerate(dates, 1):
        try:
            logger.info(f"📅 [{i}/{len(dates)}] 触发日期 {date} 的数据采集")

            # 调用 Celery 任务
            result = collect_fotmob_data.delay(date=date)

            # 获取任务结果（带超时）
            try:
                # 等待任务完成，最多等待60秒
                task_result = result.get(timeout=60)

                if task_result.get('status') == 'success':
                    success_count += 1
                    matches_collected = task_result.get('matches_collected', 0)
                    records_saved = task_result.get('records_saved', 0)
                    total_matches += matches_collected
                    total_saved += records_saved

                    logger.info(f"✅ 任务成功: {matches_collected} 场比赛, {records_saved} 条记录保存")
                else:
                    error_count += 1
                    logger.error(f"❌ 任务失败: {task_result.get('error', 'Unknown error')}")

            except Exception as task_error:
                error_count += 1
                logger.error(f"❌ 获取任务结果失败: {task_error}")

            # 🚨 关键修复：每个任务后都强制等待，避免 API 速率限制
            if i < len(dates):  # 最后一个任务不需要等待
                logger.info(f"⏳ 正在等待 {api_throttle_delay} 秒，避免 API 速率限制...")
                time.sleep(api_throttle_delay)

        except Exception as e:
            logger.error(f"❌ 触发日期 {date} 的采集任务失败: {e}")
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

    logger.info(f"📊 采集任务统计: {result_summary}")
    return result_summary


def main():
    """主函数"""
    logger.info("🎯 开始 FotMob 3 赛季历史数据回溯采集")

    # 1. 加载配置
    config = load_data_config()
    backfill_seasons = config['strategic_settings']['backfill_seasons']
    current_season = config['strategic_settings']['current_season']

    logger.info("📋 配置信息:")
    logger.info(f"  - 回溯赛季数: {backfill_seasons}")
    logger.info(f"  - 当前赛季: {current_season}")
    logger.info(f"  - 目标联赛数量: {len(config['target_leagues'])}")

    # 2. 生成历史日期
    dates_per_season = 30  # 每个赛季30个关键日期，总计90个日期
    historical_dates = generate_historical_dates(backfill_seasons, dates_per_season)

    # 打乱日期顺序，确保数据的时间分布更自然
    random.shuffle(historical_dates)

    logger.info("📅 生成的历史日期范围:")
    logger.info(f"  - 最早: {min(historical_dates)}")
    logger.info(f"  - 最晚: {max(historical_dates)}")
    logger.info(f"  - 总日期数: {len(historical_dates)}")
    logger.info(f"  - 每赛季日期数: {dates_per_season}")

    # 3. 触发采集任务
    if historical_dates:
        result_summary = trigger_fotmob_collection_tasks(
            historical_dates,
            api_throttle_delay=5.0  # 每个 API 调用间隔 5 秒，避免 429 错误
        )

        logger.info("🎉 历史数据回溯采集任务触发完成！")
        logger.info(f"📊 采集统计: {result_summary}")
    else:
        logger.warning("⚠️ 没有生成历史日期，请检查配置")

    logger.info("📋 下一步操作:")
    logger.info("1. 监控采集进度: docker-compose logs -f worker | grep -i fotmob")
    logger.info("2. 运行 ETL 处理: docker-compose exec app python scripts/run_etl_silver.py")
    logger.info("3. 触发完整管道: docker-compose exec worker celery -A src.tasks.celery_app call complete_data_pipeline")


if __name__ == "__main__":
    main()
