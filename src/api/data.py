import os
"""
import asyncio
数据API接口

提供足球预测系统的数据访问接口。
包含比赛特征、球队统计、仪表板数据等接口。

基于 DATA_DESIGN.md 第6.2节设计。
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.data.quality.data_quality_monitor import DataQualityMonitor
from src.database.connection import get_async_session
from src.database.models.data_collection_log import DataCollectionLog
from src.database.models.features import Features
from src.database.models.league import League
from src.database.models.match import Match, MatchStatus
from src.database.models.odds import Odds
from src.database.models.predictions import Predictions
from src.database.models.team import Team

router = APIRouter(tags=["data"])
logger = logging.getLogger(__name__)


def _get_attr(source: Any, name: str, default: Any = None) -> Any:
    """容错地从对象或字典中获取属性。"""
    if isinstance(source, dict):
        return source.get(name, default)
    return getattr(source, name, default)


def _normalize_datetime(value: Any) -> Optional[str]:
    """将日期/时间值转换为 ISO 字符串。"""
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _enum_value(value: Any) -> Any:
    """获取枚举或普通值的原始表示。"""
    if hasattr(value, "value"):
        return value.value
    return value


def format_match_response(match: Any) -> Dict[str, Any]:
    """标准化比赛数据结构，兼容 ORM、字典与 Mock 对象。"""
    return {
        "id": _get_attr(match, "id"),
        "home_team_id": _get_attr(match, "home_team_id"),
        "away_team_id": _get_attr(match, "away_team_id"),
        "league_id": _get_attr(match, "league_id"),
        "season": _get_attr(match, "season"),
        "match_time": _normalize_datetime(_get_attr(match, "match_time")),
        "match_status": _enum_value(_get_attr(match, "match_status")),
        "home_score": _get_attr(match, "home_score"),
        "away_score": _get_attr(match, "away_score"),
    }


def format_team_response(team: Any) -> Dict[str, Any]:
    """标准化球队数据结构。"""
    primary_name = _get_attr(team, "team_name")
    secondary_name = _get_attr(team, "name")
    display_name = secondary_name or primary_name
    team_name = primary_name or secondary_name
    return {
        "id": _get_attr(team, "id"),
        "name": display_name,
        "team_name": team_name,
        "short_name": _get_attr(team, "short_name", _get_attr(team, "team_code")),
        "founded_year": _get_attr(team, "founded_year", _get_attr(team, "founded")),
        "country": _get_attr(team, "country"),
        "league_id": _get_attr(team, "league_id"),
        "stadium": _get_attr(team, "stadium"),
        "website": _get_attr(team, "website"),
    }


def format_league_response(league: Any) -> Dict[str, Any]:
    """标准化联赛信息。"""
    primary_name = _get_attr(league, "league_name")
    fallback_name = _get_attr(league, "name")
    return {
        "id": _get_attr(league, "id"),
        "name": primary_name or fallback_name,
        "country": _get_attr(league, "country"),
        "code": _get_attr(league, "league_code"),
        "level": _get_attr(league, "level"),
        "is_active": _get_attr(league, "is_active"),
    }


def format_pagination(limit: int, offset: int, total: int) -> Dict[str, Any]:
    """构建统一的分页结构。"""
    return {
        "limit": limit,
        "offset": offset,
        "total": total,
        "has_next": offset + limit < total,
        "has_prev": offset > 0,
    }


def validate_pagination(limit: int, offset: int) -> None:
    """校验分页参数，非法时抛出 HTTP 400。"""
    if limit <= 0:
        raise HTTPException(status_code=400, detail = os.getenv("DATA_DETAIL_118"))
    if offset < 0:
        raise HTTPException(status_code=400, detail = os.getenv("DATA_DETAIL_120"))


def validate_date_format(date_str: str) -> datetime:
    """校验日期格式，返回解析后的 datetime。"""
    try:
        return datetime.fromisoformat(date_str)
    except ValueError as exc:  # pragma: no cover - 保持清晰的错误信息
        raise HTTPException(status_code=400, detail=f"invalid date format: {date_str}") from exc


def validate_match_data(match: Any) -> bool:
    """验证比赛数据是否符合基本约束。"""
    home_team_id = _get_attr(match, "home_team_id")
    away_team_id = _get_attr(match, "away_team_id")
    if home_team_id is None or away_team_id is None:
        return False
    return home_team_id != away_team_id


def _parse_match_status(status: Optional[str]) -> Optional[MatchStatus]:
    """将字符串转换为 MatchStatus，非法值返回 HTTP 400。"""
    if status is None:
        return None
    try:
        normalized = status.strip().lower()
        return MatchStatus(normalized)
    except (ValueError, AttributeError) as exc:
        raise HTTPException(status_code=400, detail=f"invalid match status: {status}") from exc


def _calculate_team_statistics(matches: Iterable[Any], team_id: int) -> Dict[str, Any]:
    """根据比赛列表计算球队统计信息。"""
    stats = {
        "total_matches": 0,
        "wins": 0,
        "draws": 0,
        "losses": 0,
        "goals_for": 0,
        "goals_against": 0,
        "clean_sheets": 0,
    }

    for match in matches:
        home_id = _get_attr(match, "home_team_id")
        away_id = _get_attr(match, "away_team_id")
        home_score = _get_attr(match, "home_score") or 0
        away_score = _get_attr(match, "away_score") or 0

        if home_id != team_id and away_id != team_id:
            continue

        stats["total_matches"] += 1
        is_home = home_id == team_id
        team_score = home_score if is_home else away_score
        opponent_score = away_score if is_home else home_score

        if team_score > opponent_score:
            stats["wins"] += 1
        elif team_score == opponent_score:
            stats["draws"] += 1
        else:
            stats["losses"] += 1

        stats["goals_for"] += team_score
        stats["goals_against"] += opponent_score
        if opponent_score == 0:
            stats["clean_sheets"] += 1

    total = stats["total_matches"] or 1  # 避免除零
    stats.update(
        {
            "win_rate": stats["wins"] / total if stats["total_matches"] else 0.0,
            "avg_goals_for": stats["goals_for"] / total if stats["total_matches"] else 0.0,
            "avg_goals_against": stats["goals_against"] / total if stats["total_matches"] else 0.0,
            "goal_difference": stats["goals_for"] - stats["goals_against"],
            "points": stats["wins"] * 3 + stats["draws"],
        }
    )
    return stats


@router.get("/matches/{match_id}/features")
async def get_match_features(
    match_id: int, session: AsyncSession = Depends(get_async_session)
):
    """
    获取比赛特征数据

    Args:
        match_id: 比赛ID

    Returns:
        Dict: 比赛特征数据
    """
    try:
        # 查询比赛基本信息
        match_query = select(Match).where(Match.id == match_id)
        match_result = await session.execute(match_query)
        match = match_result.scalar_one_or_none()

        if not match:
            raise HTTPException(status_code=404, detail="比赛不存在")

        # 查询比赛特征
        features_query = select(Features).where(Features.match_id == match_id)
        features_result = await session.execute(features_query)
        features_list = features_result.scalars().all()

        # 查询最新预测
        predictions_query = (
            select(Predictions)
            .where(Predictions.match_id == match_id)
            .order_by(Predictions.predicted_at.desc())
            .limit(1)
        )
        predictions_result = await session.execute(predictions_query)
        latest_prediction = predictions_result.scalar_one_or_none()

        # 查询最新赔率
        odds_query = (
            select(Odds)
            .where(Odds.match_id == match_id)
            .order_by(Odds.collected_at.desc())
            .limit(5)
        )
        odds_result = await session.execute(odds_query)
        latest_odds = odds_result.scalars().all()

        # 构建响应数据
        response_data = {
            "match_id": match_id,
            "match_info": {
                "home_team_id": match.home_team_id,
                "away_team_id": match.away_team_id,
                "league_id": match.league_id,
                "match_time": match.match_time.isoformat(),
                "match_status": match.match_status.value,
                "season": match.season,
            },
            "features": {"home_team": None, "away_team": None},
            "prediction": None,
            "odds": [],
        }

        # 处理特征数据
        for feature in features_list:
            team_type = (
                "home_team" if feature.team_type.value == "home" else "away_team"
            )
            response_data["features"][team_type] = {
                "team_id": feature.team_id,
                "recent_form": {
                    "wins": feature.recent_5_wins,
                    "draws": feature.recent_5_draws,
                    "losses": feature.recent_5_losses,
                    "goals_for": feature.recent_5_goals_for,
                    "goals_against": feature.recent_5_goals_against,
                    "win_rate": feature.recent_5_win_rate(),
                },
                "home_away_record": {
                    "home_wins": feature.home_wins,
                    "home_draws": feature.home_draws,
                    "home_losses": feature.home_losses,
                    "away_wins": feature.away_wins,
                    "away_draws": feature.away_draws,
                    "away_losses": feature.away_losses,
                    "home_win_rate": feature.home_win_rate(),
                    "away_win_rate": feature.away_win_rate(),
                },
                "head_to_head": {
                    "wins": feature.h2h_wins,
                    "draws": feature.h2h_draws,
                    "losses": feature.h2h_losses,
                    "goals_for": feature.h2h_goals_for,
                    "goals_against": feature.h2h_goals_against,
                    "win_rate": feature.h2h_win_rate(),
                },
                "league_standing": {
                    "position": feature.league_position,
                    "points": feature.points,
                    "goal_difference": feature.goal_difference,
                },
                "team_strength": feature.calculate_team_strength(),
            }

        # 处理预测数据
        if latest_prediction:
            response_data["prediction"] = {
                "model_name": latest_prediction.model_name,
                "model_version": latest_prediction.model_version,
                "predicted_result": latest_prediction.predicted_result.value,
                "probabilities": {
                    "home_win": float(latest_prediction.home_win_probability),
                    "draw": float(latest_prediction.draw_probability),
                    "away_win": float(latest_prediction.away_win_probability),
                },
                "confidence_score": (
                    float(latest_prediction.confidence_score)
                    if latest_prediction.confidence_score
                    else None
                ),
                "predicted_score": latest_prediction.get_predicted_score(),
                "predicted_at": (
                    latest_prediction.predicted_at.isoformat()
                    if hasattr(latest_prediction.predicted_at, "isoformat")
                    else str(latest_prediction.predicted_at)
                ),
            }

        # 处理赔率数据
        for odds in latest_odds:
            response_data["odds"].append(
                {
                    "bookmaker": odds.bookmaker,
                    "market_type": odds.market_type.value,
                    "home_odds": float(odds.home_odds) if odds.home_odds else None,
                    "draw_odds": float(odds.draw_odds) if odds.draw_odds else None,
                    "away_odds": float(odds.away_odds) if odds.away_odds else None,
                    "collected_at": odds.collected_at.isoformat(),
                }
            )

        return response_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取比赛特征失败: {str(e)}")
        raise HTTPException(status_code=500, detail = os.getenv("DATA_DETAIL_349"))


@router.get("/teams/{team_id}/stats")
async def get_team_stats(
    team_id: int,
    session: AsyncSession = Depends(get_async_session),
):
    """
    获取球队统计数据

    Args:
        team_id: 球队ID

    Returns:
        Dict: 球队统计数据
    """
    try:
        # 查询球队基本信息
        team_query = select(Team).where(Team.id == team_id)
        team_result = await session.execute(team_query)
        team = team_result.scalar_one_or_none()

        if not team:
            raise HTTPException(status_code=404, detail="球队不存在")

        # 查询所有比赛
        matches_query = (
            select(Match)
            .where(
                and_(
                    or_(Match.home_team_id == team_id, Match.away_team_id == team_id),
                    Match.match_status == "finished",
                )
            )
            .limit(50)  # 限制最近50场比赛
        )

        matches_result = await session.execute(matches_query)
        matches = matches_result.scalars().all()

        # 初始化统计数据
        stats = {
            "team_id": team_id,
            "team_name": team.name,
            "total_matches": 0,
            "wins": 0,
            "draws": 0,
            "losses": 0,
            "goals_for": 0,
            "goals_against": 0,
            "clean_sheets": 0,
        }

        # 计算统计
        for match in matches:
            is_home = match.home_team_id == team_id
            team_score = match.home_score if is_home else match.away_score
            opponent_score = match.away_score if is_home else match.home_score

            if team_score is not None and opponent_score is not None:
                stats["total_matches"] += 1
                stats["goals_for"] += team_score
                stats["goals_against"] += opponent_score

                if team_score > opponent_score:
                    stats["wins"] += 1
                elif team_score == opponent_score:
                    stats["draws"] += 1
                else:
                    stats["losses"] += 1

                if opponent_score == 0:
                    stats["clean_sheets"] += 1

        # 计算衍生统计
        if stats["total_matches"] > 0:
            stats["win_rate"] = stats["wins"] / stats["total_matches"]
            stats["avg_goals_for"] = stats["goals_for"] / stats["total_matches"]
            stats["avg_goals_against"] = stats["goals_against"] / stats["total_matches"]
        else:
            stats["win_rate"] = 0.0
            stats["avg_goals_for"] = 0.0
            stats["avg_goals_against"] = 0.0

        stats["goal_difference"] = stats["goals_for"] - stats["goals_against"]
        stats["points"] = stats["wins"] * 3 + stats["draws"]

        return stats

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取球队统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail = os.getenv("DATA_DETAIL_443"))


@router.get("/teams/{team_id}/recent_stats")
async def get_team_recent_stats(
    team_id: int,
    days: int = Query(default=30, ge=1, le=365, description="统计天数"),
    session: AsyncSession = Depends(get_async_session),
):
    """
    获取球队近期统计数据

    Args:
        team_id: 球队ID
        days: 统计天数（默认30天）

    Returns:
        Dict: 球队近期统计数据
    """
    try:
        # 查询球队基本信息
        team_query = select(Team).where(Team.id == team_id)
        team_result = await session.execute(team_query)
        team = team_result.scalar_one_or_none()

        if not team:
            raise HTTPException(status_code=404, detail="球队不存在")

        # 计算时间范围
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        # 查询近期比赛
        matches_query = (
            select(Match)
            .where(
                and_(
                    or_(Match.home_team_id == team_id, Match.away_team_id == team_id),
                    Match.match_time >= start_date,
                    Match.match_time <= end_date,
                    Match.match_status == "finished",
                )
            )
            .order_by(Match.match_time.desc())
        )
        matches_result = await session.execute(matches_query)
        recent_matches = matches_result.scalars().all()

        # 统计数据
        stats = {
            "team_id": team_id,
            "team_name": team.team_name,
            "period_days": days,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "total_matches": len(recent_matches),
            "home_matches": 0,
            "away_matches": 0,
            "wins": 0,
            "draws": 0,
            "losses": 0,
            "goals_for": 0,
            "goals_against": 0,
            "clean_sheets": 0,
            "matches": [],
        }

        # 处理每场比赛
        for match in recent_matches:
            is_home = match.home_team_id == team_id
            team_score = match.home_score if is_home else match.away_score
            opponent_score = match.away_score if is_home else match.home_score

            if is_home:
                stats["home_matches"] += 1
            else:
                stats["away_matches"] += 1

            # 统计结果
            if team_score > opponent_score:
                stats["wins"] += 1
                result = "win"
            elif team_score == opponent_score:
                stats["draws"] += 1
                result = "draw"
            else:
                stats["losses"] += 1
                result = "loss"

            # 统计进球和失球
            stats["goals_for"] += team_score
            stats["goals_against"] += opponent_score

            # 统计零封
            if opponent_score == 0:
                stats["clean_sheets"] += 1

            # 添加比赛详情
            stats["matches"].append(
                {
                    "match_id": match.id,
                    "opponent_team_id": (
                        match.away_team_id if is_home else match.home_team_id
                    ),
                    "is_home": is_home,
                    "match_time": match.match_time.isoformat(),
                    "score": f"{team_score}-{opponent_score}",
                    "result": result,
                }
            )

        # 计算衍生统计
        if stats["total_matches"] > 0:
            stats["win_rate"] = stats["wins"] / stats["total_matches"]
            stats["avg_goals_for"] = stats["goals_for"] / stats["total_matches"]
            stats["avg_goals_against"] = stats["goals_against"] / stats["total_matches"]
            stats["clean_sheet_rate"] = stats["clean_sheets"] / stats["total_matches"]
        else:
            stats["win_rate"] = 0.0
            stats["avg_goals_for"] = 0.0
            stats["avg_goals_against"] = 0.0
            stats["clean_sheet_rate"] = 0.0

        stats["goal_difference"] = stats["goals_for"] - stats["goals_against"]
        stats["points"] = stats["wins"] * 3 + stats["draws"]

        return stats

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取球队统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail = os.getenv("DATA_DETAIL_443"))


@router.get("/dashboard/data")
async def get_dashboard_data(session: AsyncSession = Depends(get_async_session)):
    """
    获取仪表板数据

    Returns:
        Dict: 仪表板数据（比赛、预测、质量监控）
    """
    try:
        # 获取今日比赛
        today = datetime.now().date()
        tomorrow = today + timedelta(days=1)

        today_matches_query = (
            select(Match)
            .where(and_(Match.match_time >= today, Match.match_time < tomorrow))
            .order_by(Match.match_time)
        )
        today_matches_result = await session.execute(today_matches_query)
        today_matches = today_matches_result.scalars().all()

        # 获取最新预测
        latest_predictions_query = (
            select(Predictions).order_by(Predictions.predicted_at.desc()).limit(10)
        )
        predictions_result = await session.execute(latest_predictions_query)
        latest_predictions = predictions_result.scalars().all()

        # 获取数据质量状态
        quality_monitor = DataQualityMonitor()
        quality_report = await quality_monitor.generate_quality_report()

        # 获取系统健康状态
        system_health = await get_system_health(session)

        dashboard_data = {
            "generated_at": datetime.now().isoformat(),
            "today_matches": {
                "count": len(today_matches),
                "matches": [
                    {
                        "match_id": match.id,
                        "home_team_id": match.home_team_id,
                        "away_team_id": match.away_team_id,
                        "league_id": match.league_id,
                        "match_time": match.match_time.isoformat(),
                        "match_status": match.match_status.value,
                    }
                    for match in today_matches
                ],
            },
            "predictions": {
                "count": len(latest_predictions),
                "latest": [
                    {
                        "match_id": pred.match_id,
                        "model_name": pred.model_name,
                        "predicted_result": pred.predicted_result.value,
                        "confidence": (
                            float(pred.confidence_score)
                            if pred.confidence_score
                            else None
                        ),
                        "predicted_at": (
                            pred.predicted_at.isoformat()
                            if hasattr(pred.predicted_at, "isoformat")
                            else str(pred.predicted_at)
                        ),
                    }
                    for pred in latest_predictions
                ],
            },
            "data_quality": {
                "overall_status": quality_report.get("overall_status", "unknown"),
                "quality_score": quality_report.get("quality_score", 0),
                "anomalies_count": quality_report.get("anomalies", {}).get("count", 0),
                "last_check": quality_report.get("report_time"),
            },
            "system_health": system_health,
        }

        return dashboard_data

    except Exception as e:
        logger.error(f"获取仪表板数据失败: {str(e)}")
        raise HTTPException(status_code=500, detail = os.getenv("DATA_DETAIL_662"))


@router.get("/matches")
async def get_matches(
    limit: int = Query(default=50, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    league_id: int = Query(default=None),
    team_id: int = Query(default=None),
    status: str = Query(default=None),
    session: AsyncSession = Depends(get_async_session)
):
    """
    获取比赛列表

    Args:
        limit: 返回数量限制
        offset: 偏移量
        league_id: 联赛ID过滤
        team_id: 球队ID过滤
        status: 比赛状态过滤

    Returns:
        Dict: 比赛列表
    """
    try:
        validate_pagination(limit, offset)
        match_status = _parse_match_status(status)

        query = select(Match).order_by(Match.match_time.desc())
        conditions = []
        if league_id is not None:
            conditions.append(Match.league_id == league_id)
        if team_id is not None:
            conditions.append(or_(Match.home_team_id == team_id, Match.away_team_id == team_id))
        if match_status is not None:
            conditions.append(Match.match_status == match_status)

        if conditions:
            query = query.where(and_(*conditions))

        query = query.offset(offset).limit(limit)
        result = await session.execute(query)
        matches = result.scalars().all()

        count_query = select(func.count(Match.id))
        if conditions:
            count_query = count_query.where(and_(*conditions))
        total = (await session.execute(count_query)).scalar() or 0

        response = {
            "success": True,
            "data": {
                "matches": [format_match_response(match) for match in matches],
                "pagination": format_pagination(limit, offset, total),
            },
        }
        return response

    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - 日志保留上下文
        logger.error("获取比赛列表失败: %s", exc)
        raise HTTPException(status_code=500, detail = os.getenv("DATA_DETAIL_725")) from exc


@router.get("/teams")
async def get_teams(
    limit: int = Query(default=50, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    search: str = Query(default=None),
    session: AsyncSession = Depends(get_async_session)
):
    """
    获取球队列表

    Args:
        limit: 返回数量限制
        offset: 偏移量
        search: 搜索关键词

    Returns:
        Dict: 球队列表
    """
    try:
        validate_pagination(limit, offset)

        query = select(Team).order_by(Team.team_name)
        if search:
            like_pattern = f"%{search}%"
            query = query.where(
                or_(
                    Team.team_name.ilike(like_pattern),
                    Team.team_code.ilike(like_pattern),
                )
            )

        query = query.offset(offset).limit(limit)
        result = await session.execute(query)
        teams = result.scalars().all()

        count_query = select(func.count(Team.id))
        if search:
            like_pattern = f"%{search}%"
            count_query = count_query.where(
                or_(
                    Team.team_name.ilike(like_pattern),
                    Team.team_code.ilike(like_pattern),
                )
            )

        total = (await session.execute(count_query)).scalar() or 0

        return {
            "success": True,
            "data": {
                "teams": [format_team_response(team) for team in teams],
                "pagination": format_pagination(limit, offset, total),
            },
        }

    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover
        logger.error("获取球队列表失败: %s", exc)
        raise HTTPException(status_code=500, detail = os.getenv("DATA_DETAIL_786")) from exc


@router.get("/teams/{team_id}")
async def get_team_by_id(
    team_id: int,
    session: AsyncSession = Depends(get_async_session)
):
    """
    根据ID获取球队信息

    Args:
        team_id: 球队ID

    Returns:
        Dict: 球队信息
    """
    try:
        query = select(Team).where(Team.id == team_id)
        result = await session.execute(query)
        team = result.scalar_one_or_none()

        if not team:
            raise HTTPException(status_code=404, detail="球队不存在")

        return {"success": True, "data": {"team": format_team_response(team)}}

    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover
        logger.error("获取球队信息失败: %s", exc)
        raise HTTPException(status_code=500, detail = os.getenv("DATA_DETAIL_817")) from exc


@router.get("/leagues")
async def get_leagues(
    limit: int = Query(default=50, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    season: Optional[str] = Query(default=None),
    session: AsyncSession = Depends(get_async_session)
):
    """
    获取联赛列表

    Args:
        limit: 返回数量限制
        offset: 偏移量

    Returns:
        Dict: 联赛列表
    """
    try:
        validate_pagination(limit, offset)

        base_query = select(
            Match.league_id,
            func.count(Match.id).label("match_count"),
            func.max(Match.match_time).label("last_match_time"),
        ).group_by(Match.league_id).order_by(Match.league_id)

        if season:
            base_query = base_query.where(Match.season == season)

        paginated_query = base_query.offset(offset).limit(limit)
        result = await session.execute(paginated_query)
        league_stats = result.all()

        total_query = select(func.count(func.distinct(Match.league_id)))
        if season:
            total_query = total_query.where(Match.season == season)
        total = (await session.execute(total_query)).scalar() or 0

        leagues_data: List[Dict[str, Any]] = []
        league_ids: List[int] = []
        for row in league_stats:
            mapping = getattr(row, "_mapping", row)
            league_id = mapping["league_id"]
            league_ids.append(league_id)
            leagues_data.append(
                {
                    "league_id": league_id,
                    "match_count": mapping["match_count"],
                    "last_match_time": _normalize_datetime(mapping["last_match_time"]),
                }
            )

        if league_ids:
            leagues_result = await session.execute(
                select(League).where(League.id.in_(league_ids))
            )
            league_map = {
                league.id: format_league_response(league)
                for league in leagues_result.scalars().all()
            }
        else:
            league_map = {}

        for league_summary in leagues_data:
            league_info = league_map.get(league_summary["league_id"])
            if league_info:
                league_summary["info"] = league_info

        return {
            "success": True,
            "data": {
                "leagues": leagues_data,
                "pagination": format_pagination(limit, offset, total),
            },
        }

    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover
        logger.error("获取联赛列表失败: %s", exc)
        raise HTTPException(status_code=500, detail = os.getenv("DATA_DETAIL_899")) from exc


@router.get("/leagues/{league_id}")
async def get_league_by_id(
    league_id: int,
    session: AsyncSession = Depends(get_async_session)
):
    """
    根据ID获取联赛信息

    Args:
        league_id: 联赛ID

    Returns:
        Dict: 联赛信息
    """
    try:
        league_result = await session.execute(select(League).where(League.id == league_id))
        league = league_result.scalar_one_or_none()
        if not league:
            raise HTTPException(status_code=404, detail="联赛不存在")

        stats_query = select(
            func.count(Match.id).label("total_matches"),
            func.min(Match.match_time).label("first_match_time"),
            func.max(Match.match_time).label("last_match_time"),
            func.count(func.distinct(Match.home_team_id)).label("team_count"),
        ).where(Match.league_id == league_id)

        stats_result = await session.execute(stats_query)
        stats = stats_result.first()
        if not stats or (getattr(stats, "total_matches", 0) or 0) == 0:
            raise HTTPException(status_code=404, detail = os.getenv("DATA_DETAIL_932"))

        recent_matches_query = (
            select(Match)
            .where(Match.league_id == league_id)
            .order_by(Match.match_time.desc())
            .limit(5)
        )
        recent_matches_result = await session.execute(recent_matches_query)
        recent_matches = recent_matches_result.scalars().all()

        return {
            "success": True,
            "data": {
                "league": format_league_response(league),
                "statistics": {
                    "total_matches": stats.total_matches,
                    "team_count": stats.team_count,
                    "first_match_time": _normalize_datetime(stats.first_match_time),
                    "last_match_time": _normalize_datetime(stats.last_match_time),
                },
                "recent_matches": [format_match_response(match) for match in recent_matches],
            },
        }

    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover
        logger.error("获取联赛信息失败: %s", exc)
        raise HTTPException(status_code=500, detail = os.getenv("DATA_DETAIL_959")) from exc


@router.get("/matches/{match_id}")
async def get_match_by_id(
    match_id: int,
    session: AsyncSession = Depends(get_async_session),
):
    """根据ID获取比赛详情。"""
    try:
        match_result = await session.execute(select(Match).where(Match.id == match_id))
        match = match_result.scalar_one_or_none()
        if not match:
            raise HTTPException(status_code=404, detail="比赛不存在")

        return {"success": True, "data": {"match": format_match_response(match)}}

    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover
        logger.error("获取比赛详情失败: %s", exc)
        raise HTTPException(status_code=500, detail = os.getenv("DATA_DETAIL_979")) from exc


@router.get("/matches/date-range")
async def get_matches_by_date_range(
    start_date: str,
    end_date: str,
    session: AsyncSession = Depends(get_async_session),
):
    """按日期范围查询比赛列表。"""
    try:
        start_dt = validate_date_format(start_date)
        end_dt = validate_date_format(end_date)
        if start_dt > end_dt:
            raise HTTPException(status_code=400, detail = os.getenv("DATA_DETAIL_992"))

        query = (
            select(Match)
            .where(and_(Match.match_time >= start_dt, Match.match_time <= end_dt))
            .order_by(Match.match_time)
        )
        result = await session.execute(query)
        matches = result.scalars().all()

        return {
            "success": True,
            "data": {
                "matches": [format_match_response(match) for match in matches],
                "date_range": {"start": start_date, "end": end_date},
                "count": len(matches),
            },
        }

    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover
        logger.error("按日期范围获取比赛失败: %s", exc)
        raise HTTPException(status_code=500, detail = os.getenv("DATA_DETAIL_725")) from exc


@router.get("/matches/live")
async def get_live_matches(session: AsyncSession = Depends(get_async_session)):
    """获取正在进行的比赛。"""
    try:
        query = (
            select(Match)
            .where(Match.match_status == MatchStatus.LIVE)
            .order_by(Match.match_time.desc())
        )
        result = await session.execute(query)
        matches = result.scalars().all()

        return {
            "success": True,
            "data": {
                "count": len(matches),
                "matches": [format_match_response(match) for match in matches],
            },
        }

    except Exception as exc:  # pragma: no cover
        logger.error("获取进行中比赛失败: %s", exc)
        raise HTTPException(status_code=500, detail = os.getenv("DATA_DETAIL_725")) from exc


@router.get("/teams/{team_id}/matches")
async def get_team_matches(
    team_id: int,
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    season: Optional[str] = Query(default=None),
    session: AsyncSession = Depends(get_async_session),
):
    """获取指定球队的比赛历史及统计。"""
    try:
        validate_pagination(limit, offset)

        team_result = await session.execute(select(Team).where(Team.id == team_id))
        team = team_result.scalar_one_or_none()
        if not team:
            raise HTTPException(status_code=404, detail="球队不存在")

        conditions = [or_(Match.home_team_id == team_id, Match.away_team_id == team_id)]
        if season:
            conditions.append(Match.season == season)

        query = (
            select(Match)
            .where(and_(*conditions))
            .order_by(Match.match_time.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await session.execute(query)
        matches = result.scalars().all()

        total_query = select(func.count(Match.id)).where(and_(*conditions))
        total = (await session.execute(total_query)).scalar() or 0

        statistics = _calculate_team_statistics(matches, team_id)

        return {
            "success": True,
            "data": {
                "team": format_team_response(team),
                "matches": [format_match_response(match) for match in matches],
                "pagination": format_pagination(limit, offset, total),
                "statistics": statistics,
            },
        }

    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover
        logger.error("获取球队比赛历史失败: %s", exc)
        raise HTTPException(status_code=500, detail = os.getenv("DATA_DETAIL_1091")) from exc


@router.get("/leagues/{league_id}/standings")
async def get_league_standings(
    league_id: int,
    season: Optional[str] = Query(default=None),
    session: AsyncSession = Depends(get_async_session),
):
    """获取联赛积分榜数据。"""
    try:
        league_result = await session.execute(select(League).where(League.id == league_id))
        league = league_result.scalar_one_or_none()
        if not league:
            raise HTTPException(status_code=404, detail="联赛不存在")

        matches_query = select(Match).where(Match.league_id == league_id)
        if season:
            matches_query = matches_query.where(Match.season == season)

        matches_result = await session.execute(matches_query)
        matches = matches_result.scalars().all()

        standings_map: Dict[int, Dict[str, Any]] = {}
        for match in matches:
            home_id = _get_attr(match, "home_team_id")
            away_id = _get_attr(match, "away_team_id")
            home_score = _get_attr(match, "home_score") or 0
            away_score = _get_attr(match, "away_score") or 0

            for team_id, goals_for, goals_against, is_home in (
                (home_id, home_score, away_score, True),
                (away_id, away_score, home_score, False),
            ):
                if team_id is None:
                    continue
                team_stats = standings_map.setdefault(
                    team_id,
                    {
                        "team_id": team_id,
                        "played": 0,
                        "won": 0,
                        "drawn": 0,
                        "lost": 0,
                        "goals_for": 0,
                        "goals_against": 0,
                    },
                )

                team_stats["played"] += 1
                team_stats["goals_for"] += goals_for
                team_stats["goals_against"] += goals_against

                if goals_for > goals_against:
                    team_stats["won"] += 1
                elif goals_for == goals_against:
                    team_stats["drawn"] += 1
                else:
                    team_stats["lost"] += 1

        team_ids = list(standings_map.keys())
        if team_ids:
            teams_result = await session.execute(select(Team).where(Team.id.in_(team_ids)))
            teams = {team.id: format_team_response(team) for team in teams_result.scalars().all()}
        else:
            teams = {}

        standings = []
        for team_id, stats in standings_map.items():
            points = stats["won"] * 3 + stats["drawn"]
            goal_diff = stats["goals_for"] - stats["goals_against"]
            standings.append(
                {
                    **stats,
                    "points": points,
                    "goal_difference": goal_diff,
                    "team": teams.get(team_id),
                }
            )

        standings.sort(key=lambda item: (item["points"], item["goal_difference"], item["goals_for"]), reverse=True)
        for idx, row in enumerate(standings, start=1):
            row["position"] = idx

        return {
            "success": True,
            "data": {
                "league": format_league_response(league),
                "standings": standings,
                "season": season,
            },
        }

    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover
        logger.error("获取联赛积分榜失败: %s", exc)
        raise HTTPException(status_code=500, detail = os.getenv("DATA_DETAIL_1188")) from exc


async def get_matches_batch(match_ids: List[int], session: AsyncSession) -> List[Dict[str, Any]]:
    """批量获取比赛信息，使用 IN 查询避免 N+1。"""
    if not match_ids:
        return []

    query = select(Match).where(Match.id.in_(match_ids))
    result = await session.execute(query)
    matches = result.scalars().all()
    return [format_match_response(match) for match in matches]


async def get_system_health(session: AsyncSession) -> Dict[str, Any]:
    """
    获取系统健康状态

    Args:
        session: 数据库会话

    Returns:
        Dict: 系统健康状态
    """
    try:
        # 检查数据库连接
        db_health = os.getenv("DATA_DB_HEALTH_1207")
        try:
            await session.execute(select(1))
        except Exception:
            db_health = os.getenv("DATA_DB_HEALTH_1211")

        # 检查最近的数据采集状态
        recent_logs_query = (
            select(DataCollectionLog)
            .where(DataCollectionLog.created_at >= datetime.now() - timedelta(hours=24))
            .order_by(DataCollectionLog.created_at.desc())
            .limit(10)
        )
        logs_result = await session.execute(recent_logs_query)
        recent_logs = logs_result.scalars().all()

        collection_health = os.getenv("DATA_COLLECTION_HEALTH_1231")
        if not recent_logs:
            collection_health = os.getenv("DATA_COLLECTION_HEALTH_1232")
        else:
            failed_logs = [log for log in recent_logs if log.status == "failed"]
            if len(failed_logs) > len(recent_logs) * 0.5:
                collection_health = os.getenv("DATA_COLLECTION_HEALTH_1236")
            elif failed_logs:
                collection_health = os.getenv("DATA_COLLECTION_HEALTH_1239")

        return {
            "database": db_health,
            "data_collection": collection_health,
            "last_collection": (
                recent_logs[0].created_at.isoformat() if recent_logs else None
            ),
            "recent_failures": len(
                [log for log in recent_logs if log.status == "failed"]
            ),
        }

    except Exception as e:
        logger.error(f"获取系统健康状态失败: {str(e)}")
        return {"database": "unknown", "data_collection": "unknown", "error": str(e)}
