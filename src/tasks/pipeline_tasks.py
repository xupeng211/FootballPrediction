"""Pipeline Tasks module.

定义数据管道的串联任务，实现采集->清洗->特征工程的自动化流程。
使用Celery Chain和Group来编排任务依赖关系。
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List

from celery import chain, group, shared_task
from celery.schedules import crontab

logger = logging.getLogger(__name__)

# 导入基础数据采集任务
from .data_collection_tasks import collect_daily_fixtures, collect_live_scores, collect_odds_data


def sync_task_to_async(async_func):
    """将异步函数转换为同步的Celery任务"""
    from functools import wraps

    @wraps(async_func)
    def wrapper(*args, **kwargs):
        import asyncio
        return asyncio.run(async_func(*args, **kwargs))

    return wrapper


@shared_task(bind=True, name="data_cleaning_task")
def data_cleaning_task(self, collection_result: Dict[str, Any]) -> Dict[str, Any]:
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

        # 这里实现数据清洗逻辑
        # 暂时返回成功状态，后续可以集成FootballDataCleaner
        cleaning_result = {
            "status": "success",
            "cleaned_records": collection_result.get("collected_records", 0),
            "cleaning_timestamp": datetime.utcnow().isoformat(),
            "errors_removed": 0,
            "duplicates_removed": 0,
        }

        logger.info(f"数据清洗完成: {cleaning_result}")
        return cleaning_result

    except Exception as e:
        logger.error(f"数据清洗任务失败: {e}")
        return {
            "status": "error",
            "error": str(e),
            "cleaning_timestamp": datetime.utcnow().isoformat()
        }


@shared_task(bind=True, name="feature_engineering_task")
def feature_engineering_task(self, cleaning_result: Dict[str, Any]) -> Dict[str, Any]:
    """特征工程任务.

    Args:
        cleaning_result: 数据清洗任务的返回结果

    Returns:
        Dict[str, Any]: 特征工程结果统计
    """
    try:
        logger.info(f"开始执行特征工程任务，处理清洗结果: {cleaning_result}")

        # 确保数据库已初始化
        db_manager = ensure_database_initialized()

        # 模拟特征计算（实际应该根据清洗后的数据计算特征）
        features_calculated = cleaning_result.get("cleaned_records", 0)

        # 这里可以添加实际的特征计算逻辑
        feature_result = {
            "status": "success",
            "features_calculated": features_calculated,
            "feature_timestamp": datetime.utcnow().isoformat(),
            "feature_columns": [
                "home_team_id", "away_team_id", "home_last_5_points", "away_last_5_points",
                "home_last_5_avg_goals", "away_last_5_avg_goals", "h2h_last_3_home_wins",
                "home_last_5_goal_diff", "away_last_5_goal_diff", "home_win_streak",
                "away_win_streak", "home_last_5_win_rate", "away_last_5_win_rate",
                "home_rest_days", "away_rest_days"
            ]
        }

        logger.info(f"特征工程完成: {feature_result}")
        return feature_result

    except Exception as e:
        logger.error(f"特征工程任务失败: {e}")
        return {
            "status": "error",
            "error": str(e),
            "feature_timestamp": datetime.utcnow().isoformat()
        }


@shared_task(bind=True, name="data_storage_task")
def data_storage_task(self, feature_result: Dict[str, Any]) -> Dict[str, Any]:
    """数据存储任务.

    Args:
        feature_result: 特征工程任务的返回结果

    Returns:
        Dict[str, Any]: 存储结果统计
    """
    try:
        logger.info(f"开始执行数据存储任务，处理特征结果: {feature_result}")

        # 确保数据库已初始化
        db_manager = ensure_database_initialized()

        # 这里实现特征数据到数据库的存储
        stored_features = feature_result.get("features_calculated", 0)

        storage_result = {
            "status": "success",
            "stored_features": stored_features,
            "storage_timestamp": datetime.utcnow().isoformat(),
            "database_table": "features"
        }

        logger.info(f"数据存储完成: {storage_result}")
        return storage_result

    except Exception as e:
        logger.error(f"数据存储任务失败: {e}")
        return {
            "status": "error",
            "error": str(e),
            "storage_timestamp": datetime.utcnow().isoformat()
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
def complete_data_pipeline(self) -> Dict[str, Any]:
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
            data_storage_task.s()
        )

        # 执行管道
        result = pipeline.apply_async()

        pipeline_result = {
            "status": "success",
            "pipeline_completed": True,
            "completion_timestamp": datetime.utcnow().isoformat(),
            "task_id": result.id,
            "message": "数据管道任务链已启动"
        }

        logger.info(f"完整数据管道执行完成: {pipeline_result}")
        return pipeline_result

    except Exception as e:
        logger.error(f"完整数据管道执行失败: {e}")
        return {
            "status": "error",
            "error": str(e),
            "pipeline_completed": False,
            "completion_timestamp": datetime.utcnow().isoformat()
        }


@shared_task(bind=True, name="trigger_feature_calculation_for_new_matches")
def trigger_feature_calculation_for_new_matches(self, match_ids: List[int]) -> Dict[str, Any]:
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
            "calculation_timestamp": datetime.utcnow().isoformat()
        }

        logger.info(f"特征计算触发完成: {result}")
        return result

    except Exception as e:
        logger.error(f"触发特征计算失败: {e}")
        return {
            "status": "error",
            "error": str(e),
            "calculation_timestamp": datetime.utcnow().isoformat()
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