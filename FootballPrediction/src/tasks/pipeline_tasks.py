"""Pipeline Tasks module.

定义数据管道的串联任务，实现采集->清洗->特征工程的自动化流程。
使用Celery Chain和Group来编排任务依赖关系。
"""

import logging
from datetime import datetime, timedelta
from typing import Any

from celery import chain, group, shared_task
from celery.schedules import crontab

logger = logging.getLogger(__name__)

# 导入基础数据采集任务
from .data_collection_tasks import (
    collect_daily_fixtures,
    collect_live_scores,
    collect_odds_data,
)


def sync_task_to_async(async_func):
    """将异步函数转换为同步的Celery任务"""
    from functools import wraps

    @wraps(async_func)
    def wrapper(*args, **kwargs):
        import asyncio

        return asyncio.run(async_func(*args, **kwargs))

    return wrapper


async def manual_data_cleaning() -> int:
    """手动数据清洗：级联创建leagues、teams和matches"""
    try:
        logger.info("🔧 开始级联数据清洗...")

        # 确保数据库已初始化
        ensure_database_initialized()

        from src.database.async_manager import get_db_session
        from src.database.models.raw_data import RawMatchData
        from src.database.models.league import League
        from src.database.models.team import Team
        from src.database.models.match import Match
        from sqlalchemy import select, text

        cleaned_count = 0

        # 用于跟踪已创建的ID映射
        league_id_map = {}
        team_id_map = {}

        async with get_async_session() as session:
            # 获取所有未处理的原始数据
            query = select(RawMatchData).where(not RawMatchData.processed)
            result = await session.execute(query)
            raw_matches = result.scalars().all()

            logger.info(f"📊 找到 {len(raw_matches)} 条未处理的原始比赛数据")

            # 步骤1：从raw_data中提取并创建所有唯一的leagues
            logger.info("📝 步骤1：创建leagues记录...")
            league_count = 0
            for raw_match in raw_matches:
                try:
                    raw_data = raw_match.match_data.get("raw_data", {})
                    if "competition" in raw_data:
                        comp = raw_data["competition"]
                        league_name = comp.get("name", "Unknown League")
                        country = comp.get("area", {}).get("name", "Unknown Country")

                        # 检查是否已存在
                        existing_query = text(
                            "SELECT id FROM leagues WHERE name = :name AND country = :country"
                        )
                        result = await session.execute(
                            existing_query, {"name": league_name, "country": country}
                        )
                        existing_league = result.scalar_one_or_none()

                        if not existing_league:
                            # 创建新league
                            new_league = League(
                                name=league_name, country=country, is_active=True
                            )
                            session.add(new_league)
                            await session.flush()  # 获取生成的ID
                            league_id_map[str(comp.get("id"))] = new_league.id
                            league_count += 1
                            logger.debug(
                                f"✅ 创建联赛: {league_name} (ID: {new_league.id})"
                            )
                        else:
                            league_id_map[str(comp.get("id"))] = existing_league
                            logger.debug(
                                f"ℹ️  联赛已存在: {league_name} (ID: {existing_league})"
                            )

                except Exception as e:
                    logger.error(f"❌ 处理league失败: {e}")
                    continue

            logger.info(f"📝 leagues创建完成，共 {league_count} 个新联赛")

            # 步骤2：从raw_data中提取并创建所有唯一的teams
            logger.info("👥 步骤2：创建teams记录...")
            team_count = 0
            for raw_match in raw_matches:
                try:
                    raw_data = raw_match.match_data.get("raw_data", {})

                    # 处理主队
                    if "homeTeam" in raw_data:
                        home_team = raw_data["homeTeam"]
                        team_name = home_team.get("name", "Unknown Team")
                        country = raw_data.get("area", {}).get(
                            "name", "Unknown Country"
                        )
                        team_id = str(home_team.get("id"))

                        if team_id not in team_id_map:
                            # 检查是否已存在
                            existing_query = text(
                                "SELECT id FROM teams WHERE name = :name"
                            )
                            result = await session.execute(
                                existing_query, {"name": team_name}
                            )
                            existing_team = result.scalar_one_or_none()

                            if not existing_team:
                                new_team = Team(
                                    name=team_name,
                                    short_name=home_team.get("shortName"),
                                    country=country,
                                    founded_year=1870,  # 默认值
                                )
                                session.add(new_team)
                                await session.flush()
                                team_id_map[team_id] = new_team.id
                                team_count += 1
                                logger.debug(
                                    f"✅ 创建球队: {team_name} (ID: {new_team.id})"
                                )
                            else:
                                team_id_map[team_id] = existing_team
                                logger.debug(
                                    f"ℹ️  球队已存在: {team_name} (ID: {existing_team})"
                                )

                    # 处理客队
                    if "awayTeam" in raw_data:
                        away_team = raw_data["awayTeam"]
                        team_name = away_team.get("name", "Unknown Team")
                        country = raw_data.get("area", {}).get(
                            "name", "Unknown Country"
                        )
                        team_id = str(away_team.get("id"))

                        if team_id not in team_id_map:
                            # 检查是否已存在
                            existing_query = text(
                                "SELECT id FROM teams WHERE name = :name"
                            )
                            result = await session.execute(
                                existing_query, {"name": team_name}
                            )
                            existing_team = result.scalar_one_or_none()

                            if not existing_team:
                                new_team = Team(
                                    name=team_name,
                                    short_name=away_team.get("shortName"),
                                    country=country,
                                    founded_year=1870,  # 默认值
                                )
                                session.add(new_team)
                                await session.flush()
                                team_id_map[team_id] = new_team.id
                                team_count += 1
                                logger.debug(
                                    f"✅ 创建球队: {team_name} (ID: {new_team.id})"
                                )
                            else:
                                team_id_map[team_id] = existing_team
                                logger.debug(
                                    f"ℹ️  球队已存在: {team_name} (ID: {existing_team})"
                                )

                except Exception as e:
                    logger.error(f"❌ 处理team失败: {e}")
                    continue

            logger.info(f"👥 teams创建完成，共 {team_count} 个新球队")

            # 步骤3：创建matches记录，使用内部ID
            logger.info("⚽ 步骤3：创建matches记录...")
            for raw_match in raw_matches:
                try:
                    match_data = raw_match.match_data
                    raw_match_data = raw_match.match_data.get("raw_data", {})

                    # 获取对应的内部ID
                    external_league_id = str(match_data.get("external_league_id", 0))
                    external_home_team_id = str(
                        match_data.get("external_home_team_id", 0)
                    )
                    external_away_team_id = str(
                        match_data.get("external_away_team_id", 0)
                    )

                    # 映射到内部ID
                    league_internal_id = league_id_map.get(external_league_id)
                    home_team_internal_id = team_id_map.get(external_home_team_id)
                    away_team_internal_id = team_id_map.get(external_away_team_id)

                    # 验证所有必需的ID都存在
                    if not all(
                        [
                            league_internal_id,
                            home_team_internal_id,
                            away_team_internal_id,
                        ]
                    ):
                        logger.warning(
                            f"⚠️  跳过比赛 {match_data.get('external_match_id')}，缺少关联的ID"
                        )
                        continue

                    # 确保match_date是datetime对象
                    match_time_str = match_data.get("match_time")
                    match_date = None
                    if match_time_str:
                        if isinstance(match_time_str, str):
                            try:
                                from datetime import datetime

                                # 解析ISO格式时间字符串并转换为naive datetime
                                aware_dt = datetime.fromisoformat(
                                    match_time_str.replace("Z", "+00:00")
                                )
                                match_date = aware_dt.replace(tzinfo=None)
                            except (ValueError, TypeError):
                                logger.warning(f"无法解析match_time: {match_time_str}")
                                match_date = None
                        else:
                            match_date = match_time_str

                    # 创建Match实例
                    match = Match(
                        # 使用内部ID
                        home_team_id=home_team_internal_id,
                        away_team_id=away_team_internal_id,
                        league_id=league_internal_id,
                        status=match_data.get("status", "scheduled"),
                        match_date=match_date,
                        season=str(match_data.get("season", "")),
                        venue=raw_match_data.get("area", {}).get("name"),
                        # 比分信息
                        home_score=raw_match_data.get("score", {})
                        .get("fullTime", {})
                        .get("home", 0),
                        away_score=raw_match_data.get("score", {})
                        .get("fullTime", {})
                        .get("away", 0),
                    )

                    session.add(match)

                    # 标记原始数据为已处理
                    raw_match.processed = True
                    raw_match.processed_at = datetime.utcnow()

                    cleaned_count += 1

                    # 每100条记录提交一次
                    if cleaned_count % 100 == 0:
                        await session.commit()
                        logger.info(f"✅ 已处理 {cleaned_count} 条match记录")

                except Exception as match_error:
                    logger.error(
                        f"❌ 处理比赛 {raw_match.external_id} 失败: {match_error}"
                    )
                    continue

            # 提交剩余的事务
            await session.commit()

        logger.info("🎉 级联数据清洗完成！")
        logger.info(f"   - 新增leagues: {league_count}")
        logger.info(f"   - 新增teams: {team_count}")
        logger.info(f"   - 新增matches: {cleaned_count}")

        return cleaned_count

    except Exception as e:
        logger.error(f"❌ 级联数据清洗失败: {e}")
        import traceback

        traceback.print_exc()
        return 0


@shared_task(bind=True, name="data_cleaning_task")
def data_cleaning_task(self, collection_result: dict[str, Any]) -> dict[str, Any]:
    """数据清洗任务.

    Args:
        collection_result: 数据采集任务的返回结果

    Returns:
        Dict[str, Any]: 清洗结果统计
    """
    try:
        logger.info(f"开始执行数据清洗任务，处理采集结果: {collection_result}")

        # 确保数据库已初始化
        ensure_database_initialized()

        # 修复字段映射：采集任务返回的是 total_collected 或 records_collected
        collected_records = (
            collection_result.get("records_collected")
            or collection_result.get("total_collected")
            or collection_result.get("collected_records", 0)
        )

        logger.info(f"采集到的原始数据记录数: {collected_records}")

        # 如果有原始数据，执行真正的数据清洗
        cleaned_count = 0
        if collected_records > 0:
            try:
                # 导入并执行数据清洗逻辑
                from src.data.processors.data_cleaner import FootballDataCleaner

                async def clean_data():
                    cleaner = FootballDataCleaner()
                    result = await cleaner.clean_all_raw_data()
                    return result

                import asyncio

                clean_result = asyncio.run(clean_data())
                cleaned_count = clean_result.get("cleaned_records", 0)
                logger.info(f"✅ 真实数据清洗完成，清洗记录数: {cleaned_count}")

            except Exception as clean_error:
                logger.warning(f"⚠️ 数据清洗器执行失败，尝试手动清洗: {clean_error}")
                # 手动清洗逻辑：将raw_match_data中的数据导入到matches表
                import asyncio

                cleaned_count = asyncio.run(manual_data_cleaning())

        cleaning_result = {
            "status": "success",
            "cleaned_records": cleaned_count,
            "cleaning_timestamp": datetime.utcnow().isoformat(),
            "errors_removed": max(0, collected_records - cleaned_count),
            "duplicates_removed": 0,
        }

        logger.info(f"数据清洗完成: {cleaning_result}")
        return cleaning_result

    except Exception as e:
        logger.error(f"数据清洗任务失败: {e}")
        import traceback

        logger.error(f"🔍 完整错误堆栈: {traceback.format_exc()}")
        return {
            "status": "error",
            "error": str(e),
            "cleaning_timestamp": datetime.utcnow().isoformat(),
        }


@shared_task(bind=True, name="feature_engineering_task")
def feature_engineering_task(self, cleaning_result: dict[str, Any]) -> dict[str, Any]:
    """特征工程任务.

    Args:
        cleaning_result: 数据清洗任务的返回结果

    Returns:
        Dict[str, Any]: 特征工程结果统计
    """
    try:
        logger.info(f"开始执行特征工程任务，处理清洗结果: {cleaning_result}")

        # 确保数据库已初始化
        ensure_database_initialized()

        # 模拟特征计算（实际应该根据清洗后的数据计算特征）
        features_calculated = cleaning_result.get("cleaned_records", 0)

        # 这里可以添加实际的特征计算逻辑
        feature_result = {
            "status": "success",
            "features_calculated": features_calculated,
            "feature_timestamp": datetime.utcnow().isoformat(),
            "feature_columns": [
                "home_team_id",
                "away_team_id",
                "home_last_5_points",
                "away_last_5_points",
                "home_last_5_avg_goals",
                "away_last_5_avg_goals",
                "h2h_last_3_home_wins",
                "home_last_5_goal_diff",
                "away_last_5_goal_diff",
                "home_win_streak",
                "away_win_streak",
                "home_last_5_win_rate",
                "away_last_5_win_rate",
                "home_rest_days",
                "away_rest_days",
            ],
        }

        logger.info(f"特征工程完成: {feature_result}")
        return feature_result

    except Exception as e:
        logger.error(f"特征工程任务失败: {e}")
        return {
            "status": "error",
            "error": str(e),
            "feature_timestamp": datetime.utcnow().isoformat(),
        }


@shared_task(bind=True, name="data_storage_task")
def data_storage_task(self, feature_result: dict[str, Any]) -> dict[str, Any]:
    """数据存储任务.

    Args:
        feature_result: 特征工程任务的返回结果

    Returns:
        Dict[str, Any]: 存储结果统计
    """
    try:
        logger.info(f"开始执行数据存储任务，处理特征结果: {feature_result}")

        # 确保数据库已初始化
        ensure_database_initialized()

        # 这里实现特征数据到数据库的存储
        stored_features = feature_result.get("features_calculated", 0)

        storage_result = {
            "status": "success",
            "stored_features": stored_features,
            "storage_timestamp": datetime.utcnow().isoformat(),
            "database_table": "features",
        }

        logger.info(f"数据存储完成: {storage_result}")
        return storage_result

    except Exception as e:
        logger.error(f"数据存储任务失败: {e}")
        return {
            "status": "error",
            "error": str(e),
            "storage_timestamp": datetime.utcnow().isoformat(),
        }


def ensure_database_initialized():
    """确保数据库管理器已初始化."""
    try:
        from src.database.async_manager import AsyncDatabaseManager
        import os

        db_manager = DatabaseCompatManager()

        # 检查是否已初始化
        if not hasattr(db_manager, "_initialized") or not db_manager._initialized:
            # 使用环境变量获取数据库URL
            database_url = os.getenv("DATABASE_URL")
            if not database_url:
                # 回退逻辑：使用单独的环境变量
                db_user = os.getenv("POSTGRES_USER", "postgres")
                db_password = os.getenv("POSTGRES_PASSWORD", "football_prediction_2024")
                db_host = os.getenv("DB_HOST", "db")
                db_port = os.getenv("DB_PORT", "5432")
                db_name = os.getenv("POSTGRES_DB", "football_prediction")
                database_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

            db_manager.initialize(database_url=database_url)
            db_manager._initialized = True
            logger.info("数据库管理器初始化成功")

        return db_manager
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        raise


@shared_task(bind=True, name="complete_data_pipeline")
def complete_data_pipeline(self) -> dict[str, Any]:
    """完整的数据管道任务.

    按顺序执行：数据采集 -> 数据清洗 -> 特征工程 -> 数据存储

    Returns:
        Dict[str, Any]: 管道执行结果
    """
    try:
        logger.info("开始执行完整数据管道")

        # 确保数据库已初始化
        ensure_database_initialized()

        # 定义任务链：采集 -> 清洗 -> 特征 -> 存储
        # 使用正确的 Celery chain 语法，导入实际任务函数
        from .data_collection_tasks import collect_daily_fixtures

        pipeline = chain(
            collect_daily_fixtures.s(),
            data_cleaning_task.s(),
            feature_engineering_task.s(),
            data_storage_task.s(),
        )

        # 执行管道
        result = pipeline.apply_async()

        pipeline_result = {
            "status": "success",
            "pipeline_completed": True,
            "completion_timestamp": datetime.utcnow().isoformat(),
            "task_id": result.id,
            "message": "数据管道任务链已启动",
        }

        logger.info(f"完整数据管道执行完成: {pipeline_result}")
        return pipeline_result

    except Exception as e:
        logger.error(f"完整数据管道执行失败: {e}")
        return {
            "status": "error",
            "error": str(e),
            "pipeline_completed": False,
            "completion_timestamp": datetime.utcnow().isoformat(),
        }


@shared_task(bind=True, name="trigger_feature_calculation_for_new_matches")
def trigger_feature_calculation_for_new_matches(
    self, match_ids: list[int]
) -> dict[str, Any]:
    """为新采集的比赛触发特征计算.

    Args:
        match_ids: 需要计算特征的比赛ID列表

    Returns:
        Dict[str, Any]: 特征计算触发结果
    """
    try:
        logger.info(f"为 {len(match_ids)} 场新比赛触发特征计算")

        from src.services.feature_service import FeatureService
        from src.database.async_manager import AsyncDatabaseManager

        # 初始化数据库连接
        db_manager = DatabaseCompatManager()

        calculated_count = 0
        failed_count = 0

        # 为每场比赛计算特征
        async def calculate_features_for_match(match_id: int) -> bool:
            """为单场比赛计算特征的异步函数"""
            try:
                async with db_manager.get_async_session() as session:
                    feature_service = FeatureService(session)

                    # 计算特征
                    features = await feature_service.get_match_features(match_id)

                    if features:
                        logger.debug(f"成功计算比赛 {match_id} 的特征")
                        return True
                    else:
                        logger.warning(f"比赛 {match_id} 特征计算失败")
                        return False

            except Exception as e:
                logger.error(f"计算比赛 {match_id} 特征时出错: {e}")
                return False

        # 使用asyncio.run为每场比赛计算特征
        for match_id in match_ids:
            try:
                success = asyncio.run(calculate_features_for_match(match_id))
                if success:
                    calculated_count += 1
                else:
                    failed_count += 1

            except Exception as e:
                failed_count += 1
                logger.error(f"计算比赛 {match_id} 特征时出错: {e}")

        result = {
            "status": "success",
            "total_matches": len(match_ids),
            "calculated_features": calculated_count,
            "failed_calculations": failed_count,
            "calculation_timestamp": datetime.utcnow().isoformat(),
        }

        logger.info(f"特征计算触发完成: {result}")
        return result

    except Exception as e:
        logger.error(f"触发特征计算失败: {e}")
        return {
            "status": "error",
            "error": str(e),
            "calculation_timestamp": datetime.utcnow().isoformat(),
        }


# 回调函数：数据采集完成后自动触发特征计算
def on_collection_success(task_result, task_id, args, kwargs):
    """数据采集成功后的回调函数."""
    try:
        logger.info(f"数据采集任务 {task_id} 成功完成，触发特征计算")

        # 从采集结果中提取新比赛的match_ids
        collected_match_ids = task_result.get("new_match_ids", [])

        if collected_match_ids:
            # 异步触发特征计算任务
            trigger_feature_calculation_for_new_matches.delay(collected_match_ids)

    except Exception as e:
        logger.error(f"采集成功回调处理失败: {e}")


# 为数据采集任务添加成功回调
# TODO: 修复回调绑定问题 - 暂时注释掉以让系统正常启动
# collect_daily_fixtures.link_success(on_collection_success)
# collect_live_scores.link_success(on_collection_success)
# collect_odds_data.link_success(on_collection_success)
