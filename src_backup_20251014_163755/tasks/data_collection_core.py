"""
数据收集核心
Data Collection Core

数据收集的核心逻辑和任务定义。
"""

import asyncio
from datetime import datetime, timedelta
from typing import List, Optional

from celery import Celery

from src.core.logging import get_logger
from src.database.connection import DatabaseManager

from .data_collectors import DataCollectionOrchestrator  # type: ignore

logger = get_logger(__name__)

# Celery实例
celery_app = Celery("data_collection")


class DataCollectionTask:
    """数据收集任务基类"""

    def __init__(self):
        """初始化任务"""
        self.db_manager: Optional[DatabaseManager] = None
        self.orchestrator = DataCollectionOrchestrator()

    def set_database_manager(self, db_manager: DatabaseManager) -> None:
        """设置数据库管理器"""
        self.db_manager = db_manager
        # 将数据库管理器传递给收集器
        for collector in self.orchestrator.collectors.values():
            if hasattr(collector, "set_database_manager"):
                collector.set_database_manager(db_manager)

    def on_failure(self, exc, task_id, args, kwargs, einfo) -> None:
        """任务失败回调"""
        logger.error(f"Task {task_id} failed: {str(exc)}")
        logger.error(f"Exception info: {einfo}")

    def on_success(self, retval, task_id, args, kwargs) -> None:
        """任务成功回调"""
        logger.info(f"Task {task_id} completed successfully")


@celery_app.task(bind=True)
def collect_fixtures_task(self) -> Dict[str, Any]:
    """收集赛程数据任务"""
    task = DataCollectionTask()

    try:
        # 获取数据库连接
        from src.database.connection import get_db_manager  # type: ignore

        db_manager = get_db_manager()
        task.set_database_manager(db_manager)

        # 收集数据
        collector = task.orchestrator.get_collector("fixtures")
        if collector:
            # 使用asyncio.run在同步上下文中运行异步代码
            _result = asyncio.run(collector.collect_async(days_ahead=30))
            return result  # type: ignore
        else:
            return {"error": "Fixtures collector not found"}

    except (RuntimeError, ValueError, ConnectionError) as e:
        logger.error(f"Failed to collect fixtures: {str(e)}")
        raise


@celery_app.task(bind=True)
def collect_odds_task(self) -> Dict[str, Any]:
    """收集赔率数据任务"""
    task = DataCollectionTask()

    try:
        # 获取数据库连接
        from src.database.connection import get_db_manager  # type: ignore

        db_manager = get_db_manager()
        task.set_database_manager(db_manager)

        # 收集数据
        collector = task.orchestrator.get_collector("odds")
        if collector:
            # 使用asyncio.run在同步上下文中运行异步代码
            _result = asyncio.run(collector.collect_async())
            return result  # type: ignore
        else:
            return {"error": "Odds collector not found"}

    except (RuntimeError, ValueError, ConnectionError) as e:
        logger.error(f"Failed to collect odds: {str(e)}")
        raise


@celery_app.task(bind=True)
def collect_scores_task(self) -> Dict[str, Any]:
    """收集比分数据任务"""
    task = DataCollectionTask()

    try:
        # 获取数据库连接
        from src.database.connection import get_db_manager  # type: ignore

        db_manager = get_db_manager()
        task.set_database_manager(db_manager)

        # 收集数据
        collector = task.orchestrator.get_collector("scores")
        if collector:
            # 使用asyncio.run在同步上下文中运行异步代码
            _result = asyncio.run(collector.collect_async())
            return result  # type: ignore
        else:
            return {"error": "Scores collector not found"}

    except (RuntimeError, ValueError, ConnectionError) as e:
        logger.error(f"Failed to collect scores: {str(e)}")
        raise


@celery_app.task
def manual_collect_all_data() -> Dict[str, Any]:
    """手动收集所有数据任务

    手动触发所有数据收集

    这是一个同步任务，用于立即收集所有类型的数据。
    """
    task = DataCollectionTask()

    try:
        # 获取数据库连接
        from src.database.connection import get_db_manager  # type: ignore

        db_manager = get_db_manager()
        task.set_database_manager(db_manager)

        # 使用asyncio.run在同步上下文中运行异步代码
        results = asyncio.run(task.orchestrator.collect_all_data())
        return results  # type: ignore

    except (RuntimeError, ValueError, ConnectionError) as e:
        logger.error(f"Failed to collect all data: {str(e)}")
        return {"error": str(e), "collected_at": datetime.utcnow().isoformat()}


@celery_app.task
def emergency_data_collection_task(
    data_types: Optional[List[str]] = None, priority: int = 1
) -> Dict[str, Any]:
    """
    紧急数据收集任务

    用于在数据缺失时紧急收集关键数据。
    """
    task = DataCollectionTask()

    try:
        # 获取数据库连接
        from src.database.connection import get_db_manager  # type: ignore

        db_manager = get_db_manager()
        task.set_database_manager(db_manager)

        # 只收集关键数据类型
        critical_types = data_types or ["fixtures", "scores"]

        logger.warning(f"Emergency data collection triggered for: {critical_types}")

        # 使用asyncio.run在同步上下文中运行异步代码
        results = asyncio.run(
            task.orchestrator.collect_all_data(data_types=critical_types)
        )

        # 标记为紧急收集
        results["emergency"] = True
        results["priority"] = priority

        return results  # type: ignore

    except (RuntimeError, ValueError, ConnectionError) as e:
        logger.error(f"Emergency data collection failed: {str(e)}")
        return {
            "error": str(e),
            "emergency": True,
            "collected_at": datetime.utcnow().isoformat(),
        }


# 定时任务定义
@celery_app.task
def collect_historical_data_task():
    """定期收集历史数据任务"""
    task = DataCollectionTask()

    try:
        # 获取数据库连接
        from src.database.connection import get_db_manager

        db_manager = get_db_manager()
        task.set_database_manager(db_manager)

        # 收集过去30天的比赛数据
        historical_collector = task.orchestrator.get_collector("historical")
        if historical_collector:
            # 使用asyncio.run在同步上下文中运行异步代码
            results = asyncio.run(
                historical_collector.collect_historical_data(
                    data_type="matches",
                    start_date=datetime.utcnow() - timedelta(days=30),
                    end_date=datetime.utcnow(),
                )
            )

            # 保存到数据库
            asyncio.run(_save_historical_data(results, "matches"))
            return results

        return {"error": "Historical collector not found"}

    except (RuntimeError, ValueError, ConnectionError) as e:
        logger.error(f"Failed to collect historical data: {str(e)}")
        raise


async def _save_historical_data(data: Dict[str, Any], data_type: str) -> None:
    """保存历史数据到数据库"""
    # 这里应该实现实际的数据库保存逻辑
    logger.info(f"Saving {len(data.get('data', []))} {data_type} records to database")

    # 模拟保存操作
    await asyncio.sleep(0.1)


def validate_collected_data(data: Dict[str, Any], data_type: str) -> Dict[str, Any]:
    """验证收集的数据"""
    validation_result = {
        "data_type": data_type,
        "is_valid": True,
        "validation_errors": [],
        "recommendations": [],
    }

    try:
        # 基本验证
        if not data:
            validation_result["is_valid"] = False
            validation_result["validation_errors"].append("Data is empty")  # type: ignore
            return validation_result

        # 检查必要字段
        if data_type == "fixtures":
            validation_result.update(_validate_fixtures_data(data))
        elif data_type == "odds":
            validation_result.update(_validate_odds_data(data))
        elif data_type == "scores":
            validation_result.update(_validate_scores_data(data))
        elif data_type == "matches":
            validation_result.update(_validate_matches_data(data))

    except (RuntimeError, ValueError, ConnectionError) as e:
        validation_result["is_valid"] = False
        validation_result["validation_errors"].append(f"Validation error: {str(e)}")  # type: ignore

    return validation_result


def _validate_fixtures_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """验证赛程数据"""
    errors = []
    recommendations = []  # type: ignore

    fixtures = data.get("fixtures", [])
    for i, fixture in enumerate(fixtures):
        if not isinstance(fixture, Dict[str, Any]):
            errors.append(f"Fixture {i} is not a dictionary")
            continue

        # 检查必要字段
        required_fields = ["id", "date", "home_team", "away_team"]
        for field in required_fields:
            if field not in fixture:
                errors.append(f"Fixture {i} missing field: {field}")

        # 检查日期格式
        if "date" in fixture:
            try:
                datetime.fromisoformat(fixture["date"])
            except ValueError:
                errors.append(f"Fixture {i} has invalid date format")

    return {"validation_errors": errors, "recommendations": recommendations}


def _validate_odds_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """验证赔率数据"""
    errors = []  # type: ignore
    recommendations = []  # type: ignore

    # 实现赔率数据验证逻辑
    return {"validation_errors": errors, "recommendations": recommendations}


def _validate_scores_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """验证比分数据"""
    errors = []  # type: ignore
    recommendations = []  # type: ignore

    # 实现比分数据验证逻辑
    return {"validation_errors": errors, "recommendations": recommendations}


def _validate_matches_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """验证比赛数据"""
    errors = []  # type: ignore
    recommendations = []  # type: ignore

    # 实现比赛数据验证逻辑
    return {"validation_errors": errors, "recommendations": recommendations}
