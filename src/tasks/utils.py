"""
任务工具函数

提供任务调度相关的工具函数，包括：
- 比赛时间检查
- 数据采集条件判断
- 任务状态管理
"""

from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import text

from src.database.connection import DatabaseManager


async def should_collect_live_scores() -> bool:
    """
    判断是否应该采集实时比分

    检查当前是否有进行中的比赛或即将开始的比赛

    Returns:
        是否需要采集实时比分
    """
    try:
        db_manager = DatabaseManager()

        async with db_manager.get_async_session() as session:
            # 查询当前时间前后2小时内的比赛
            now = datetime.now()
            start_time = now - timedelta(hours=2)
            end_time = now + timedelta(hours=2)

            query = text(
                """
                SELECT COUNT(*) as match_count
                FROM matches
                WHERE match_time BETWEEN :start_time AND :end_time
                AND match_status IN ('scheduled', 'live', 'first_half', 'second_half', 'halftime')
            """
            )

            _result = await session.execute(
                query, {"start_time": start_time, "end_time": end_time}
            )

            match_count = result.scalar()  # type: ignore or 0
            return match_count > 0

    except (ValueError, KeyError, RuntimeError):
        # 如果查询失败，返回 False（避免在测试中无谓的数据采集）
        return False


async def get_upcoming_matches(hours: int = 24) -> List[dict]:
    """
    获取未来N小时内的比赛

    Args:
        hours: 时间范围（小时）

    Returns:
        比赛列表
    """
    try:
        db_manager = DatabaseManager()

        async with db_manager.get_async_session() as session:
            now = datetime.now()
            end_time = now + timedelta(hours=hours)

            query = text(
                """
                SELECT
                    id,
                    home_team_id,
                    away_team_id,
                    league_id,
                    match_time,
                    match_status
                FROM matches
                WHERE match_time BETWEEN :now AND :end_time
                AND match_status IN ('scheduled', 'live')
                ORDER BY match_time ASC
            """
            )

            _result = await session.execute(query, {"now": now, "end_time": end_time})

            _matches = []
            for row in result:
                matches.append(
                    {
                        "id": row.id,
                        "home_team_id": row.home_team_id,
                        "away_team_id": row.away_team_id,
                        "league_id": row.league_id,
                        "match_time": row.match_time.isoformat(),
                        "match_status": row.match_status,
                    }
                )

            return matches

    except (ValueError, KeyError, RuntimeError):
        return []


def is_match_day(date: Optional[datetime] = None) -> bool:
    """
    检查指定日期是否有比赛

    Args:
        date: 要检查的日期，默认为今天

    Returns:
        是否有比赛
    """
    if date is None:
        date = datetime.now()

    # 简化实现：假设周末更可能有比赛
    weekday = date.weekday()
    return weekday in [5, 6]  # 周六、周日


async def get_active_leagues() -> List[str]:
    """
    获取当前活跃的联赛列表

    Returns:
        活跃联赛ID列表
    """
    try:
        db_manager = DatabaseManager()

        async with db_manager.get_async_session() as session:
            # 查询最近30天内有比赛的联赛
            query = text(
                """
                SELECT DISTINCT l.name
                FROM leagues l
                INNER JOIN matches m ON l.id = m.league_id
                WHERE m.match_time >= NOW() - INTERVAL '30 days'
                ORDER BY l.name
            """
            )

            _result = await session.execute(query)
            leagues = [row.name for row in result]

            return leagues

    except (ValueError, KeyError, RuntimeError):
        # 返回一些常见的联赛作为默认值
        return ["Premier League", "La Liga", "Serie A", "Bundesliga"]


def calculate_next_collection_time(
    task_name: str, interval_minutes: int = None
) -> datetime:
    """
    计算下次采集时间

    Args:
        task_name: 任务名称

    Returns:
        下次执行时间
    """
    now = datetime.now()

    if task_name == "collect_fixtures_task":
        # 赛程采集：每日凌晨2点
        next_run = now.replace(hour=2, minute=0, second=0, microsecond=0)
        if next_run <= now:
            next_run += timedelta(days=1)
        return next_run

    elif task_name == "collect_odds_task":
        # 赔率采集：每5分钟
        minutes = (now.minute // 5 + 1) * 5
        next_run = now.replace(minute=minutes % 60, second=0, microsecond=0)
        if minutes >= 60:
            next_run += timedelta(hours=1)
        return next_run

    elif task_name == "collect_scores_task":
        # 比分采集：每2分钟
        minutes = (now.minute // 2 + 1) * 2
        next_run = now.replace(minute=minutes % 60, second=0, microsecond=0)
        if minutes >= 60:
            next_run += timedelta(hours=1)
        return next_run

    else:
        # 默认1小时后
        return now + timedelta(hours=1)


async def cleanup_stale_tasks() -> int:
    """
    清理过期的任务记录

    Returns:
        清理的记录数
    """
    try:
        db_manager = DatabaseManager()

        async with db_manager.get_async_session() as session:
            # 清理7天前的错误日志
            cleanup_query = text(
                """
                DELETE FROM error_logs
                WHERE created_at < NOW() - INTERVAL '7 days'
            """
            )

            _result = await session.execute(cleanup_query)
            await session.commit()

            # For DELETE queries, we need to check if the result has rowcount
            if hasattr(result, "rowcount") and result.rowcount is not None:  # type: ignore
                return result.rowcount  # type: ignore
            return 0

    except (ValueError, KeyError, RuntimeError):
        return 0


def get_task_priority(task_name: str) -> int:
    """
    获取任务优先级

    Args:
        task_name: 任务名称

    Returns:
        优先级数值（数字越小优先级越高）
    """
    priorities = {
        "collect_scores_task": 1,  # 实时比分优先级最高
        "collect_odds_task": 2,  # 赔率采集优先级中等
        "collect_fixtures_task": 3,  # 赛程采集优先级较低
    }

    return priorities.get(str(task_name), 5)  # 默认优先级为5
