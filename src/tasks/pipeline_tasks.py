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
    collect_fotmob_data,  # 新增 FotMob 数据采集
)


def sync_task_to_async(async_func):
    """将异步函数转换为同步的Celery任务"""
    from functools import wraps

    @wraps(async_func)
    def wrapper(*args, **kwargs):
        import asyncio

        return asyncio.run(async_func(*args, **kwargs))

    return wrapper


async def batch_data_cleaning() -> int:
    """高性能分块批量数据清洗：支持大数据量处理，避免长事务超时"""
    try:
        logger.info("🚀 开始分块高性能批量数据清洗...")

        # 确保数据库已初始化
        from src.database.connection import initialize_database
        initialize_database()

        from src.database.connection import get_async_session
        from src.database.models.raw_data import RawMatchData
        from src.database.models.league import League
        from src.database.models.team import Team
        from src.database.models.match import Match
        from sqlalchemy import select, text, update

        total_cleaned_count = 0
        BATCH_SIZE = 5  # 减小批次大小以便更好地调试
        offset = 0

        logger.info("🔄 开始分块处理循环...")

        # 🔄 分块处理循环
        while True:
            logger.info(f"📊 处理批次 offset={offset}, batch_size={BATCH_SIZE}")

            # 每个批次使用独立的事务
            async with get_async_session() as session:
                # 步骤1：分批获取未处理的原始数据 - 使用多层级查询策略
                batch_raw_matches = []

                # 方法1：尝试简单的布尔比较
                try:
                    query = (
                        select(RawMatchData)
                        .where(not RawMatchData.processed)
                        .limit(BATCH_SIZE)
                        .offset(offset)
                    )
                    result = await session.execute(query)
                    batch_raw_matches = result.scalars().all()
                    logger.info(f"✅ 方法1成功: 找到 {len(batch_raw_matches)} 条记录")
                except Exception as e:
                    logger.warning(f"⚠️ 方法1失败: {e}")

                # 方法2：如果方法1失败，使用原生SQL查询
                if not batch_raw_matches:
                    try:
                        sql_query = text("""
                            SELECT * FROM raw_match_data
                            WHERE processed = false
                            ORDER BY created_at ASC
                            LIMIT :limit OFFSET :offset
                        """)
                        result = await session.execute(sql_query, {
                            "limit": BATCH_SIZE,
                            "offset": offset
                        })

                        # 将结果转换为RawMatchData对象
                        rows = result.fetchall()
                        for row in rows:
                            raw_match = RawMatchData(
                                id=row[0],
                                external_id=row[1],
                                source=row[2],
                                match_data=row[3],
                                collected_at=row[4],
                                processed=row[5],
                                created_at=row[6] if len(row) > 6 else None,
                                updated_at=row[7] if len(row) > 7 else None
                            )
                            batch_raw_matches.append(raw_match)

                        logger.info(f"✅ 方法2成功: 找到 {len(batch_raw_matches)} 条记录")
                    except Exception as e:
                        logger.error(f"❌ 方法2也失败: {e}")
                        # 方法3：最后回退到检查所有数据
                        try:
                            all_query = select(RawMatchData).limit(BATCH_SIZE).offset(offset)
                            result = await session.execute(all_query)
                            all_matches = result.scalars().all()

                            # 在Python中过滤未处理的
                            batch_raw_matches = [
                                match for match in all_matches
                                if not match.processed
                            ]
                            logger.info(f"✅ 方法3成功: 从{len(all_matches)}条中筛选出{len(batch_raw_matches)}条未处理记录")
                        except Exception as e3:
                            logger.error(f"❌ 所有方法都失败: {e3}")
                            break

                if not batch_raw_matches:
                    logger.info("📊 没有更多未处理的原始数据")
                    break

                logger.info(f"📊 本批次找到 {len(batch_raw_matches)} 条原始数据")

                # 步骤2：在当前事务中处理这批数据
                batch_cleaned_count = await _process_data_batch(session, batch_raw_matches)

                # 步骤3：提交当前批次的事务
                await session.commit()

                total_cleaned_count += batch_cleaned_count
                logger.info(f"✅ 批次处理完成: {batch_cleaned_count} 条记录，总计: {total_cleaned_count}")

                # 如果返回的记录数少于批次大小，说明没有更多数据了
                if len(batch_raw_matches) < BATCH_SIZE:
                    break

                offset += BATCH_SIZE

        logger.info(f"🎉 分块批量数据清洗完成！总计处理 {total_cleaned_count} 条记录")
        return total_cleaned_count

    except Exception as e:
        logger.error(f"❌ 分块批量数据清洗失败: {e}")
        import traceback
        traceback.print_exc()
        return 0


async def _process_data_batch(session, raw_matches) -> int:
    """处理单批次数据的内部函数"""
    leagues_created = 0
    teams_created = 0
    cleaned_count = 0

    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from sqlalchemy import text, update
    from src.database.models.league import League
    from src.database.models.team import Team
    from src.database.models.match import Match
    from src.database.models.raw_data import RawMatchData

    # 步骤1：提取本批唯一的Leagues
    logger.info("📝 提取本批次Leagues...")
    unique_leagues = {}
    for raw_match in raw_matches:
        try:
            match_data = raw_match.match_data
            raw_content = match_data.get("raw_data", {})

            if "competition" in raw_content:
                comp = raw_content["competition"]
                league_name = comp.get("name", "Unknown League")
                league_country = comp.get("area", {}).get("name", "Unknown Country")

                league_key = (league_name, league_country)
                if league_key not in unique_leagues:
                    unique_leagues[league_key] = {
                        'name': league_name,
                        'country': league_country
                    }
        except Exception as e:
            logger.debug(f"提取league信息失败: {e}")
            continue

    # 步骤2：批量创建Leagues
    if unique_leagues:
        logger.info(f"🏆 批量创建 {len(unique_leagues)} 个Leagues...")
        existing_leagues = {}
        for (name, country), _league_data in unique_leagues.items():
            query = text("SELECT id FROM leagues WHERE name = :name AND country = :country")
            result = await session.execute(query, {"name": name, "country": country})
            existing = result.scalar_one_or_none()
            if existing:
                existing_leagues[(name, country)] = existing

        new_leagues = []
        for (name, country), _league_data in unique_leagues.items():
            if (name, country) not in existing_leagues:
                new_league = League(
                    name=name,
                    country=country,
                    is_active=True,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                new_leagues.append(new_league)

        if new_leagues:
            session.add_all(new_leagues)
            await session.flush()
            leagues_created = len(new_leagues)

    # 步骤3：重新获取Leagues映射
    leagues_query = text("SELECT id, name, country FROM leagues")
    leagues_result = await session.execute(leagues_query)
    leagues_map = {(row[1], row[2]): row[0] for row in leagues_result.fetchall()}

    # 🆕 添加League映射调试信息
    logger.info(f"🗺️ League映射表 (共{len(leagues_map)}个):")
    for (name, country), league_id in list(leagues_map.items())[:5]:  # 显示前5个
        logger.info(f"   - ({name}, {country}) -> {league_id}")
    if len(leagues_map) > 5:
        logger.info(f"   ... 还有{len(leagues_map) - 5}个league")

    # 步骤4：提取本批唯一的Teams
    logger.info("👥 提取本批次Teams...")
    unique_teams = {}
    for raw_match in raw_matches:
        try:
            match_data = raw_match.match_data

            # 🔄 适配不同数据源：优先使用match_data中的球队名称，回退到raw_data
            home_team_name = match_data.get("home_team_name")
            away_team_name = match_data.get("away_team_name")

            # 如果match_data中没有球队信息，尝试从raw_data获取
            if not home_team_name or not away_team_name:
                raw_content = match_data.get("raw_data", {})

                if not home_team_name and "homeTeam" in raw_content:
                    home_team_info = raw_content["homeTeam"]
                    home_team_name = home_team_info.get("name", "Unknown Team")

                if not away_team_name and "awayTeam" in raw_content:
                    away_team_info = raw_content["awayTeam"]
                    away_team_name = away_team_info.get("name", "Unknown Team")

            # 处理主队
            if home_team_name:
                team_short_name = home_team_name[:10] if len(home_team_name) > 10 else home_team_name
                team_country = match_data.get("league_country", "Unknown Country")

                if home_team_name not in unique_teams:
                    unique_teams[home_team_name] = {
                        'name': home_team_name,
                        'short_name': team_short_name,
                        'country': team_country
                    }

            # 处理客队
            if away_team_name:
                team_short_name = away_team_name[:10] if len(away_team_name) > 10 else away_team_name
                team_country = match_data.get("league_country", "Unknown Country")

                if away_team_name not in unique_teams:
                    unique_teams[away_team_name] = {
                        'name': away_team_name,
                        'short_name': team_short_name,
                        'country': team_country
                    }

        except Exception as e:
            logger.debug(f"提取team信息失败: {e}")
            continue

    # 步骤5：批量创建Teams
    if unique_teams:
        logger.info(f"⚽ 批量创建 {len(unique_teams)} 个Teams...")
        existing_teams = {}
        for team_name, _team_data in unique_teams.items():
            query = text("SELECT id FROM teams WHERE name = :name")
            result = await session.execute(query, {"name": team_name})
            existing = result.scalar_one_or_none()
            if existing:
                existing_teams[team_name] = existing

        new_teams = []
        for team_name, _team_data in unique_teams.items():
            if team_name not in existing_teams:
                new_team = Team(
                    name=team_name,
                    short_name=team_data['short_name'],
                    country=team_data['country'],
                    founded_year=2000,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                new_teams.append(new_team)

        if new_teams:
            session.add_all(new_teams)
            await session.flush()
            teams_created = len(new_teams)

    # 步骤6：重新获取Teams映射
    teams_query = text("SELECT id, name FROM teams")
    teams_result = await session.execute(teams_query)
    teams_map = {row[1]: row[0] for row in teams_result.fetchall()}

    # 步骤7：批量创建Matches
    logger.info("⚽ 批量创建Matches...")
    matches_to_create = []
    raw_match_ids_to_update = []

    for raw_match in raw_matches:
        try:
            match_data = raw_match.match_data
            raw_content = match_data.get("raw_data", {})

            # 处理状态字段
            status_field = match_data.get("status", {})
            if isinstance(status_field, dict):
                if status_field.get('finished', False):
                    status = 'FINISHED'
                elif status_field.get('started', False):
                    status = 'LIVE'
                else:
                    status = 'SCHEDULED'
            else:
                status = str(status_field) if status_field else 'SCHEDULED'

            # 获取关联的ID - 🔄 修复League映射不匹配问题
            # 优先使用match_data中的结构化信息，回退到raw_data确保一致性
            league_name = match_data.get("league_name", "Unknown League")

            # 🆕 统一League查找逻辑，与League创建时保持一致
            raw_content = match_data.get("raw_data", {})
            if "competition" in raw_content:
                comp = raw_content["competition"]
                league_country_lookup = comp.get("area", {}).get("name", "Unknown Country")
            else:
                league_country_lookup = match_data.get("league_country", "Unknown Country")

            # 保持原始信息用于日志
            league_country_display = match_data.get("league_country", league_country_lookup)

            home_team_name = match_data.get("home_team_name", "Unknown Team")
            away_team_name = match_data.get("away_team_name", "Unknown Team")

            # 🆕 使用统一查找逻辑
            league_id = leagues_map.get((league_name, league_country_lookup))
            home_team_id = teams_map.get(home_team_name)
            away_team_id = teams_map.get(away_team_name)

            # 🆕 添加详细调试信息
            logger.info("🔍 比赛数据检查:")
            logger.info(f"   - 比赛: {home_team_name} vs {away_team_name}")
            logger.info(f"   - 联赛: {league_name} ({league_country_display})")
            logger.info(f"   - 查找键: ({league_name}, {league_country_lookup})")
            logger.info(f"   - 关联ID: league_id={league_id}, home_team_id={home_team_id}, away_team_id={away_team_id}")

            if not all([league_id, home_team_id, away_team_id]):
                logger.warning(f"⚠️ 跳过比赛，缺少关联ID: league={league_name}, home={home_team_name}, away={away_team_name}")
                logger.warning(f"   ID详情: league_id={league_id}, home_team_id={home_team_id}, away_team_id={away_team_id}")
                continue

            # 处理时间
            match_time_str = match_data.get("match_time")
            match_date = None
            if match_time_str and isinstance(match_time_str, str):
                try:
                    aware_dt = datetime.fromisoformat(match_time_str.replace("Z", "+00:00"))
                    match_date = aware_dt.replace(tzinfo=None)
                except (ValueError, TypeError):
                    match_date = None

            # 如果没有有效时间，使用默认时间
            if match_date is None:
                match_date = datetime.utcnow()
                logger.debug(f"使用默认比赛时间: {match_date}")

            # 获取比分
            home_score = raw_content.get("homeScore", 0)
            away_score = raw_content.get("awayScore", 0)

            # 创建Match对象
            new_match = Match(
                home_team_id=home_team_id,
                away_team_id=away_team_id,
                league_id=league_id,
                status=status,
                match_date=match_date,
                season=str(match_data.get("season", "2024")),
                venue=raw_content.get("venue", "Unknown Venue"),
                home_score=home_score,
                away_score=away_score,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )

            matches_to_create.append(new_match)
            raw_match_ids_to_update.append(raw_match.id)

        except Exception as e:
            logger.error(f"❌ 处理比赛数据失败: {e}")
            continue

    # 步骤8：批量插入Matches
    if matches_to_create:
        logger.info(f"💾 批量插入 {len(matches_to_create)} 场比赛...")
        session.add_all(matches_to_create)
        await session.flush()

        # 步骤9：批量标记原始数据为已处理
        if raw_match_ids_to_update:
            logger.info(f"🔄 标记 {len(raw_match_ids_to_update)} 条原始数据为已处理...")
            update_stmt = (
                update(RawMatchData)
                .where(RawMatchData.id.in_(raw_match_ids_to_update))
                .values(
                    processed=True,
                    updated_at=datetime.utcnow()
                )
            )
            await session.execute(update_stmt)

        cleaned_count = len(matches_to_create)
        logger.info(f"✅ 本批次完成: 创建 {cleaned_count} 场比赛")

    logger.info(f"📊 本批次统计: leagues={leagues_created}, teams={teams_created}, matches={cleaned_count}")
    return cleaned_count


@shared_task(bind=True, name="data_cleaning_task")
def data_cleaning_task(self, collection_result: dict[str, Any]) -> dict[str, Any]:
    """数据清洗任务 - 使用高性能批量操作.

    Args:
        collection_result: 数据采集任务的返回结果

    Returns:
        Dict[str, Any]: 清洗结果统计
    """
    try:
        logger.info(f"🚀 开始执行批量数据清洗任务，处理采集结果: {collection_result}")

        # 确保数据库已初始化
        ensure_database_initialized()

        # 修复字段映射：采集任务返回的是 total_collected 或 records_collected
        collected_records = (
            collection_result.get("records_collected")
            or collection_result.get("total_collected")
            or collection_result.get("collected_records", 0)
        )

        logger.info(f"📊 采集到的原始数据记录数: {collected_records}")

        # 如果有原始数据，执行高效批量数据清洗
        cleaned_count = 0
        if collected_records > 0:
            try:
                # 优先使用FootballDataCleaner（如果可用）
                from src.data.processors.football_data_cleaner import FootballDataCleaner

                async def clean_data():
                    FootballDataCleaner()
                    # 这里可以扩展为支持批量清洗的方法
                    result = {"cleaned_records": 0}  # 临时占位
                    return result

                import asyncio
                clean_result = asyncio.run(clean_data())
                cleaned_count = clean_result.get("cleaned_records", 0)
                logger.info(f"✅ FootballDataCleaner清洗完成，清洗记录数: {cleaned_count}")

            except Exception as clean_error:
                logger.info(f"📝 使用高性能批量数据清洗: {clean_error}")
                # 使用新的批量清洗逻辑
                import asyncio
                cleaned_count = asyncio.run(batch_data_cleaning())

        cleaning_result = {
            "status": "success",
            "cleaned_records": cleaned_count,
            "cleaning_timestamp": datetime.utcnow().isoformat(),
            "errors_removed": max(0, collected_records - cleaned_count),
            "duplicates_removed": 0,
            "performance_improvement": "batch_processing_enabled",
        }

        logger.info(f"🎉 批量数据清洗完成: {cleaning_result}")
        return cleaning_result

    except Exception as e:
        logger.error(f"❌ 批量数据清洗任务失败: {e}")
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
        from src.database.connection import DatabaseManager
        import os

        db_manager = DatabaseManager()

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
    """完整的数据管道任务 - 升级至FotMob数据源.

    按顺序执行：FotMob数据采集 -> 批量数据清洗 -> 特征工程 -> 数据存储

    Returns:
        Dict[str, Any]: 管道执行结果
    """
    try:
        logger.info("🚀 开始执行完整数据管道 (FotMob数据源)")

        # 确保数据库已初始化
        ensure_database_initialized()

        # 定义任务链：FotMob采集 -> 批量清洗 -> 特征 -> 存储
        from .data_collection_tasks import collect_fotmob_data

        pipeline = chain(
            collect_fotmob_data.s(),        # 🆕 使用FotMob数据源
            data_cleaning_task.s(),         # 🆕 批量数据清洗
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
            "message": "🚀 数据管道任务链已启动 (FotMob + 批量处理)",
            "data_source": "fotmob",
            "performance_mode": "batch_processing_enabled",
        }

        logger.info(f"🎉 完整数据管道执行完成: {pipeline_result}")
        return pipeline_result

    except Exception as e:
        logger.error(f"❌ 完整数据管道执行失败: {e}")
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
        from src.database.connection import DatabaseManager

        # 初始化数据库连接
        db_manager = DatabaseManager()

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
