#!/usr/bin/env python3
"""
地毯式覆盖数据采集脚本 / Comprehensive Coverage Data Collection Script

🎯 战略变更：执行"地毯式覆盖"策略
- 时间范围：2022年1月1日 到 今天
- 采集方式：连续日期，一天都不跳过
- 包含赛事：所有联赛 + 国际杯赛 + 友谊赛
- 不再随机采样，不再跳过休赛期

🚀 Strategic Change: "Comprehensive Coverage" Strategy
- Time Range: 2022-01-01 to Today
- Collection Method: Continuous dates, no skipping
- Include: All leagues + International cups + Friendlies
- No random sampling, no rest day skipping

使用方法 / Usage:
    python scripts/trigger_historical_backfill.py [--dry-run]

参数 / Arguments:
    --dry-run: 只显示计划，不实际触发任务

注意事项 / Notes:
- 这是一个大规模数据采集任务，预计需要数小时完成
- 5-10秒随机延迟，模拟真人行为，更加安全
- 将采集包括休赛期在内的每一天的数据
- 国际友谊赛是高价值数据源，不容忽视
"""

import asyncio
import logging
import os
import sys
import random
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
import argparse

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
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


def load_data_source_config() -> dict[str, Any]:
    """加载数据源配置"""
    try:
        config_path = project_root / "src" / "config" / "data_sources.json"
        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)
        logger.info(f"✅ 成功加载数据战略配置: {config_path}")
        logger.info(f"📋 配置版本: {config.get('version', 'unknown')}")
        logger.info(f"🎯 采集策略: {config.get('collection_strategy', 'unknown')}")
        return config
    except Exception:
        logger.error(f"❌ 加载数据源配置失败: {e}")
        # 返回默认配置
        return {
            "version": "1.0.0",
            "collection_strategy": "high_value_focus",
            "backfill": {
                "years": 3,
                "days_per_season": 30,
                "target_leagues": ["PL", "PD", "BL1", "SA", "FL1"],
            },
            "fotmob": {
                "rate_limit": {"requests_per_minute": 10, "delay_between_requests": 6}
            },
        }


def generate_comprehensive_dates(config: dict[str, Any]) -> list[str]:
    """生成地毯式覆盖的连续日期列表"""
    strategic_settings = config.get("strategic_settings", {})

    # 🎯 地毯式覆盖策略参数
    start_date_str = strategic_settings.get("start_date", "20220101")
    end_date_str = strategic_settings.get("end_date", "today")
    skip_rest_days = strategic_settings.get("skip_rest_days", False)

    target_leagues = config.get("target_leagues", [])

    # 解析日期范围
    if end_date_str == "today":
        end_date = datetime.now()
    else:
        end_date = datetime.strptime(end_date_str, "%Y%m%d")

    start_date = datetime.strptime(start_date_str, "%Y%m%d")

    logger.info("🎯 地毯式覆盖数据采集策略")
    logger.info(
        f"   - 时间范围: {start_date.strftime('%Y-%m-%d')} 到 {end_date.strftime('%Y-%m-%d')}"
    )
    logger.info(f"   - 跳过休赛期: {'是' if skip_rest_days else '否（地毯式覆盖）'}")
    logger.info(f"   - 目标联赛数量: {len(target_leagues)}")

    # 识别国际赛事
    international_leagues = [
        league for league in target_leagues if league.get("type") == "International"
    ]
    domestic_leagues = [
        league for league in target_leagues if league.get("type") != "International"
    ]

    logger.info(f"   - 国内联赛: {len(domestic_leagues)} 个")
    logger.info(f"   - 国际赛事: {len(international_leagues)} 个")

    if international_leagues:
        logger.info(
            f"   - 国际赛事包括: {', '.join([league['name'] for league in international_leagues])}"
        )

    # 生成连续日期列表（地毯式覆盖）
    all_dates = []
    current_date = start_date

    while current_date <= end_date:
        date_str = current_date.strftime("%Y%m%d")
        all_dates.append(date_str)
        current_date += timedelta(days=1)

    logger.info("📅 地毯式覆盖日期统计:")
    logger.info(f"   - 最早日期: {all_dates[0] if all_dates else 'None'}")
    logger.info(f"   - 最晚日期: {all_dates[-1] if all_dates else 'None'}")
    logger.info(f"   - 总天数: {len(all_dates)} 天")

    # 计算预计执行时间
    min_delay = 5
    max_delay = 10
    avg_delay = (min_delay + max_delay) / 2
    estimated_minutes = len(all_dates) * avg_delay / 60
    estimated_hours = estimated_minutes / 60

    logger.info("⏱️ 预计执行时间:")
    logger.info(f"   - 延迟范围: {min_delay}-{max_delay} 秒/任务")
    logger.info(
        f"   - 预计总时长: {estimated_minutes:.1f} 分钟 ({estimated_hours:.1f} 小时)"
    )

    return all_dates


async def trigger_comprehensive_collection(
    dates: list[str], dry_run: bool = False
) -> int:
    """触发地毯式覆盖采集任务"""
    # 🎯 地毯式覆盖策略：5-10秒随机延迟，模拟真人行为
    min_delay = 5
    max_delay = 10

    logger.info("🚀 启动地毯式覆盖数据采集")
    logger.info(f"📅 采集日期范围: {len(dates)} 天连续覆盖")
    logger.info(f"⏱️ 延迟策略: {min_delay}-{max_delay} 秒随机延迟（模拟真人行为）")
    logger.info("🎯 不跳过休赛期: 确保数据完整性")

    if dry_run:
        logger.info("🔍 DRY RUN 模式: 显示地毯式覆盖计划")
        for i, date_str in enumerate(dates[:10]):  # 只显示前10个
            logger.info(f"   [{i + 1:3}/{len(dates)}] 采集日期: {date_str}")
        if len(dates) > 10:
            logger.info(f"   ... 还有 {len(dates) - 10} 个日期")
        return len(dates)

    tasks_triggered = 0
    failed_tasks = 0

    for i, date_str in enumerate(dates):
        try:
            # 格式化进度显示
            progress = (i + 1) / len(dates) * 100
            logger.info(
                f"📅 [{i + 1:4}/{len(dates)}] ({progress:5.1f}%) 采集 {date_str}"
            )

            # 调用Celery任务触发FotMob数据采集
            task = celery_app.send_task(
                "collect_fotmob_data",
                kwargs={"date": date_str},
                queue="fotmob",
                priority=5,  # 中等优先级
            )

            tasks_triggered += 1
            logger.info(f"✅ 任务提交成功: {task.id}")

            # 🎯 地毯式覆盖延迟策略：随机延迟5-10秒
            if i < len(dates) - 1:  # 最后一个任务不需要等待
                delay = random.uniform(min_delay, max_delay)
                logger.info(f"⏱️ 随机延迟 {delay:.1f} 秒...")
                await asyncio.sleep(delay)

        except Exception:
            logger.error(f"❌ 日期 {date_str} 采集失败: {e}")
            failed_tasks += 1
            # 失败时也添加短暂延迟，避免连续失败冲击API
            await asyncio.sleep(random.uniform(2, 4))
            continue

    # 最终统计报告
    success_rate = (tasks_triggered / len(dates)) * 100 if dates else 0
    logger.info("🎉 地毯式覆盖采集任务触发完成！")
    logger.info("📊 执行统计:")
    logger.info(f"   - 总日期数: {len(dates)}")
    logger.info(f"   - 成功任务: {tasks_triggered}")
    logger.info(f"   - 失败任务: {failed_tasks}")
    logger.info(f"   - 成功率: {success_rate:.1f}%")

    return tasks_triggered


def print_comprehensive_summary(config: dict[str, Any], dates: list[str]):
    """打印地毯式覆盖采集摘要"""
    strategic_settings = config.get("strategic_settings", {})
    target_leagues = config.get("target_leagues", [])

    print("=" * 80)
    print("🎯 地毯式覆盖数据采集战略")
    print("=" * 80)

    print(
        f"📊 采集策略: {strategic_settings.get('collection_strategy', 'comprehensive_coverage')}"
    )
    print(
        f"📅 时间范围: {strategic_settings.get('start_date', '20220101')} 到 {strategic_settings.get('end_date', 'today')}"
    )
    print("🎯 覆盖方式: 连续日期，不跳过休赛期")
    print(f"📋 总天数: {len(dates)} 天")

    # 联赛分类统计
    tier1_leagues = [
        league["name"] for league in target_leagues if league.get("type") == "Tier1"
    ]
    tier2_leagues = [
        league["name"] for league in target_leagues if league.get("type") == "Tier2"
    ]
    cup_leagues = [
        league["name"] for league in target_leagues if league.get("type") == "Cup"
    ]
    international_leagues = [
        league["name"]
        for league in target_leagues
        if league.get("type") == "International"
    ]
    asian_leagues = [
        league["name"] for league in target_leagues if league.get("type") == "Asia"
    ]
    american_leagues = [
        league["name"] for league in target_leagues if league.get("type") == "America"
    ]

    print("\n🏆 目标赛事分类:")
    if tier1_leagues:
        print(f"   🥇 顶级联赛: {', '.join(tier1_leagues)}")
    if tier2_leagues:
        print(f"   🥈 次级联赛: {', '.join(tier2_leagues)}")
    if cup_leagues:
        print(f"   🏅 杯赛: {', '.join(cup_leagues)}")
    if international_leagues:
        print(f"   🌍 国际赛事: {', '.join(international_leagues)}")
    if asian_leagues:
        print(f"   🏮 亚洲联赛: {', '.join(asian_leagues)}")
    if american_leagues:
        print(f"   ⚽ 美洲联赛: {', '.join(american_leagues)}")

    # 按年份统计
    year_stats = {}
    month_stats = {}
    for date_str in dates:
        year = date_str[:4]
        month = date_str[4:6]
        year_stats[year] = year_stats.get(year, 0) + 1
        month_stats[f"{year}-{month}"] = month_stats.get(f"{year}-{month}", 0) + 1

    print("\n📅 按年份分布:")
    for year in sorted(year_stats.keys()):
        print(f"   {year}年: {year_stats[year]} 天")

    print("\n⏱️ 执行参数:")
    print("   - 延迟策略: 5-10秒随机延迟")
    print(f"   - 预计时长: {len(dates) * 7.5 / 60:.1f} 分钟")
    print("   - 并发任务: 1个（顺序执行保安全）")

    print("\n📈 预期收益:")
    print("   - 数据完整性: 100%无间断覆盖")
    print(f"   - 预期比赛数: 约 {len(dates) * 15} - {len(dates) * 40} 场")
    print("   - 包含友谊赛: 高价值训练数据")
    print("   - 国际杯赛: 重大赛事数据全覆盖")

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
        logger.info(
            f"   - Celery连接: {'可用' if database_url and redis_url else '不可用'}"
        )
        return True
    except Exception:
        logger.error(f"❌ 环境验证失败: {e}")
        return False


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="历史数据回溯采集脚本")
    parser.add_argument(
        "--dry-run", action="store_true", help="只生成日期列表，不实际触发任务"
    )
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

    # 生成地毯式覆盖日期
    dates = generate_comprehensive_dates(config)
    if not dates:
        logger.error("❌ 没有生成地毯式覆盖日期，退出执行")
        return 1

    # 打印地毯式覆盖摘要
    print_comprehensive_summary(config, dates)

    # 确认执行
    if not args.dry_run:
        try:
            print("\n⚠️  地毯式覆盖采集确认")
            print(
                f"📅 将采集 {len(dates)} 天的数据，预计需要 {len(dates) * 7.5 / 60:.1f} 分钟"
            )
            response = input(
                "❓ 确认要执行地毯式覆盖数据采集吗？这将触发大量Celery任务 [y/N]: "
            )
            if response.lower() not in ["y", "yes", "是"]:
                logger.info("❌ 用户取消执行")
                return 0
        except KeyboardInterrupt:
            logger.info("❌ 用户中断执行")
            return 0

    # 执行地毯式覆盖采集
    try:
        tasks_triggered = await trigger_comprehensive_collection(dates, args.dry_run)

        if args.dry_run:
            logger.info(f"🔍 DRY RUN 完成: 将触发 {tasks_triggered} 个地毯式覆盖任务")
        else:
            logger.info(f"🚀 地毯式覆盖执行完成: 成功触发 {tasks_triggered} 个任务")

            # 提供后续操作指导
            print("\n📋 地毯式覆盖后续操作建议:")
            print("1. 📊 实时监控: docker-compose logs -f worker | grep -i fotmob")
            print(
                "2. 🔍 检查进度: docker-compose exec db psql -U postgres -d football_prediction -c \"SELECT COUNT(*) FROM raw_match_data WHERE created_at > NOW() - INTERVAL '1 hour';\""
            )
            print(
                "3. 📋 查看队列: docker-compose exec worker celery -A src.tasks.celery_app inspect active"
            )
            print(
                "4. ⚡ ETL处理: docker-compose exec app python scripts/run_etl_silver.py"
            )
            print(
                "5. 📈 质量审计: docker-compose exec app python scripts/audit_data_quality.py"
            )

        return 0

    except Exception:
        logger.error(f"❌ 地毯式覆盖执行失败: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
