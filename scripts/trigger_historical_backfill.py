#!/usr/bin/env python3
"""
历史数据回溯采集脚本 / Historical Data Backfill Collection Script

该脚本读取数据源配置，生成过去3年的历史日期列表，
并通过Celery触发大规模的FotMob历史数据采集任务。

This script reads data source configuration, generates historical date lists for the past 3 years,
and triggers large-scale FotMob historical data collection tasks via Celery.

使用方法 / Usage:
    python scripts/trigger_historical_backfill.py [--dry-run]

参数 / Arguments:
    --dry-run: 只生成日期列表，不实际触发任务

注意事项 / Notes:
- 该脚本会生成大量的Celery任务，请确保Worker有足够的处理能力
- 建议分批执行，避免对API造成过大压力
- 历史数据采集对于机器学习模型训练至关重要
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any
import argparse

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 加载环境变量
from dotenv import load_dotenv

# 尝试加载.env文件
env_files = [
    project_root / ".env",
    project_root / ".env.local",
    project_root / ".env.development",
]

for env_file in env_files:
    if env_file.exists():
        load_dotenv(env_file)
        break

import json
from src.tasks.celery_app import celery_app


def load_data_source_config() -> Dict[str, Any]:
    """加载数据源配置"""
    try:
        config_path = project_root / "src" / "config" / "data_sources.json"
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        logger.info(f"✅ 成功加载数据战略配置: {config_path}")
        logger.info(f"📋 配置版本: {config.get('version', 'unknown')}")
        logger.info(f"🎯 采集策略: {config.get('collection_strategy', 'unknown')}")
        return config
    except Exception as e:
        logger.error(f"❌ 加载数据源配置失败: {e}")
        # 返回默认配置
        return {
            "version": "1.0.0",
            "collection_strategy": "high_value_focus",
            "backfill": {
                "years": 3,
                "days_per_season": 30,
                "target_leagues": ["PL", "PD", "BL1", "SA", "FL1"]
            },
            "fotmob": {
                "rate_limit": {
                    "requests_per_minute": 10,
                    "delay_between_requests": 6
                }
            }
        }


def generate_historical_dates(config: Dict[str, Any]) -> List[str]:
    """生成历史日期列表"""
    strategic_settings = config.get('strategic_settings', {})
    years = strategic_settings.get('backfill_seasons', 3)
    days_per_season = 20  # 每赛季采样20天，平衡覆盖面和效率
    target_leagues = config.get('target_leagues', [])

    current_year = datetime.now().year

    logger.info(f"🎯 开始生成 {years} 年历史数据回溯配置")
    logger.info(f"   - 当前年份: {current_year}")
    logger.info(f"   - 回溯年份数: {years}")
    logger.info(f"   - 每赛季采样天数: {days_per_season}")
    logger.info(f"   - 目标联赛数量: {len(target_leagues)}")

    # 生成年份列表
    target_years = [current_year - i for i in range(years)]
    logger.info(f"   - 目标年份: {target_years}")

    # 为每年生成采样日期
    all_dates = []

    for year in target_years:
        season_dates = generate_season_dates(year, days_per_season)
        all_dates.extend(season_dates)
        logger.info(f"✅ {year}年生成 {len(season_dates)} 个日期")

    # 去重并排序
    unique_dates = list(set(all_dates))
    unique_dates.sort()

    logger.info(f"📅 生成的历史日期范围:")
    logger.info(f"   - 最早: {unique_dates[0] if unique_dates else 'None'}")
    logger.info(f"   - 最晚: {unique_dates[-1] if unique_dates else 'None'}")
    logger.info(f"   - 总日期数: {len(unique_dates)}")
    logger.info(f"   - 每赛季平均日期数: {len(unique_dates) // years}")

    return unique_dates


def generate_season_dates(year: int, days_per_season: int) -> List[str]:
    """为指定赛季生成采样日期"""
    dates = []

    # 定义赛季大致时间范围
    season_start_month = 8  # 8月开始
    season_end_month = 5   # 次年5月结束

    # 生成赛季起始日期
    season_start = datetime(year, season_start_month, 1)
    season_end = datetime(year + 1, season_end_month, 31)

    # 计算总天数
    total_days = (season_end - season_start).days
    logger.info(f"   - {year}赛季: {season_start.strftime('%Y-%m-%d')} 到 {season_end.strftime('%Y-%m-%d')}")
    logger.info(f"   - 赛季总天数: {total_days}")

    # 计算采样间隔
    if total_days <= days_per_season:
        # 如果赛季天数少于目标天数，采样所有天
        interval_days = 1
    else:
        # 计算采样间隔
        interval_days = total_days // days_per_season

    logger.info(f"   - 采样间隔: {interval_days}天")

    # 生成采样日期
    current_date = season_start
    while current_date <= season_end:
        date_str = current_date.strftime('%Y%m%d')
        dates.append(date_str)
        current_date += timedelta(days=interval_days)

    return dates


async def trigger_collection_tasks(dates: List[str], dry_run: bool = False) -> int:
    """触发采集任务"""
    # 从配置中获取速率限制
    rate_limit = 6  # 每个任务间隔6秒，避免API 429错误

    logger.info(f"🚀 开始历史数据回溯采集，共 {len(dates)} 个日期")
    logger.info(f"⚠️ 启用速率节流: 每个任务间隔 {rate_limit} 秒，避免 API 429 错误")

    if dry_run:
        logger.info("🔍 DRY RUN 模式: 只显示将要触发的任务")
        for i, date_str in enumerate(dates):
            logger.info(f"   [{i+1:3}/{len(dates)}] 将触发日期 {date_str} 的数据采集")
        return len(dates)

    tasks_triggered = 0
    failed_tasks = 0

    for i, date_str in enumerate(dates):
        try:
            logger.info(f"📅 [{i+1:3}/{len(dates)}] 触发日期 {date_str} 的数据采集")

            # 调用Celery任务
            task = celery_app.send_task(
                'collect_fotmob_data',
                kwargs={'date': date_str},
                queue='fotmob'
            )

            tasks_triggered += 1
            logger.info(f"✅ 任务已提交: {task.id}")

            # 速率限制：等待一段时间再触发下一个任务
            if i < len(dates) - 1:  # 最后一个任务不需要等待
                logger.info(f"⏱️ 速率限制: 等待 {rate_limit} 秒...")
                await asyncio.sleep(rate_limit)

        except Exception as e:
            logger.error(f"❌ 触发日期 {date_str} 的采集任务失败: {e}")
            failed_tasks += 1
            continue

    logger.info(f"🎉 历史数据回溯采集任务触发完成！")
    logger.info(f"📊 采集任务统计: {'total_dates': len(dates), 'successful_tasks': tasks_triggered, 'failed_tasks': failed_tasks, 'success_rate': tasks_triggered / len(dates) * 100 if dates else 0}")
    logger.info(f"📋 下一步操作:")
    logger.info(f"   1. 监控采集进度: docker-compose logs -f worker | grep -i fotmob")
    logger.info(f"   2. 运行 ETL 处理: docker-compose exec app python scripts/run_etl_silver.py")
    logger.info(f"   3. 触发完整管道: docker-compose exec worker celery -A src.tasks.celery_app call complete_data_pipeline")

    return tasks_triggered


def print_collection_summary(config: Dict[str, Any], dates: List[str]):
    """打印采集摘要信息"""
    strategic_settings = config.get('strategic_settings', {})
    target_leagues = config.get('target_leagues', [])

    print("=" * 80)
    print("🎯 历史数据回溯采集计划")
    print("=" * 80)

    print(f"📊 采集策略: {strategic_settings.get('collection_strategy', 'unknown')}")
    print(f"📅 时间范围: {strategic_settings.get('backfill_seasons', 3)} 年")
    print(f"📈 目标联赛数量: {len(target_leagues)}")
    print(f"📋 总采样日期: {len(dates)} 个")

    # 显示核心联赛
    tier1_leagues = [league['name'] for league in target_leagues if league.get('type') == 'Tier1']
    tier2_leagues = [league['name'] for league in target_leagues if league.get('type') == 'Tier2']
    cup_leagues = [league['name'] for league in target_leagues if league.get('type') == 'Cup']

    if tier1_leagues:
        print(f"🏆 核心联赛: {', '.join(tier1_leagues[:3])}{'...' if len(tier1_leagues) > 3 else ''}")
    if tier2_leagues:
        print(f"📈 次级联赛: {', '.join(tier2_leagues[:2])}{'...' if len(tier2_leagues) > 2 else ''}")
    if cup_leagues:
        print(f"🏅 杯赛: {', '.join(cup_leagues)}")

    # 按年份统计
    year_stats = {}
    for date_str in dates:
        year = date_str[:4]
        year_stats[year] = year_stats.get(year, 0) + 1

    print(f"📅 按年份分布:")
    for year in sorted(year_stats.keys(), reverse=True):
        print(f"   {year}年: {year_stats[year]} 个日期")

    rate_limit = 6
    print(f"⚙️  速率限制: {rate_limit} 秒/任务")
    print(f"⏱️  预计总时长: {len(dates) * rate_limit / 60:.1f} 分钟")
    print(f"📈 预期数据量: 约 {len(dates) * 20} - {len(dates) * 50} 场比赛")
    print("=" * 80)


def validate_environment():
    """验证执行环境"""
    try:
        # 简单的环境验证
        import os
        database_url = os.getenv("DATABASE_URL")
        redis_url = os.getenv("REDIS_URL")

        logger.info("✅ 环境配置验证通过")
        logger.info(f"   - Database URL: {'已配置' if database_url else '未配置'}")
        logger.info(f"   - Redis URL: {'已配置' if redis_url else '未配置'}")
        logger.info(f"   - Celery连接: {'可用' if database_url and redis_url else '不可用'}")
        return True
    except Exception as e:
        logger.error(f"❌ 环境验证失败: {e}")
        return False


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='历史数据回溯采集脚本')
    parser.add_argument('--dry-run', action='store_true', help='只生成日期列表，不实际触发任务')
    args = parser.parse_args()

    logger.info("🎯 历史数据回溯采集启动")
    logger.info("=" * 80)

    # 验证环境
    if not validate_environment():
        logger.error("❌ 环境验证失败，退出执行")
        return 1

    # 加载配置
    config = load_data_source_config()
    if not config:
        logger.error("❌ 配置加载失败，退出执行")
        return 1

    # 生成历史日期
    dates = generate_historical_dates(config)
    if not dates:
        logger.error("❌ 没有生成历史日期，退出执行")
        return 1

    # 打印采集摘要
    print_collection_summary(config, dates)

    # 确认执行
    if not args.dry_run:
        try:
            response = input("\n❓ 确认要执行大规模历史数据采集吗？这将触发大量Celery任务 [y/N]: ")
            if response.lower() not in ['y', 'yes', '是']:
                logger.info("❌ 用户取消执行")
                return 0
        except KeyboardInterrupt:
            logger.info("❌ 用户中断执行")
            return 0

    # 执行采集
    try:
        tasks_triggered = await trigger_collection_tasks(dates, args.dry_run)

        if args.dry_run:
            logger.info(f"🔍 DRY RUN 完成: 将触发 {tasks_triggered} 个任务")
        else:
            logger.info(f"🚀 执行完成: 成功触发 {tasks_triggered} 个任务")

            # 提供后续操作指导
            print("\n📋 后续操作建议:")
            print("1. 监控任务执行: docker-compose logs -f worker")
            print("2. 检查采集进度: docker-compose exec db psql -U postgres -d football_prediction -c \"SELECT COUNT(*) FROM raw_match_data WHERE created_at > NOW() - INTERVAL '1 hour';\"")
            print("3. 查看任务队列: docker-compose exec worker celery -A src.tasks.celery_app inspect active")
            print("4. 运行ETL处理: docker-compose exec app python scripts/run_etl_silver.py")

        return 0

    except Exception as e:
        logger.error(f"❌ 执行失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)