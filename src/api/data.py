"""
import asyncio
数据API接口

提供足球预测系统的数据访问接口。
包含比赛特征、球队统计、仪表板数据等接口。

基于 DATA_DESIGN.md 第6.2节设计。
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.data.quality.data_quality_monitor import DataQualityMonitor
from src.database.connection import get_async_session
from src.database.models.data_collection_log import DataCollectionLog
from src.database.models.features import Features
from src.database.models.match import Match
from src.database.models.odds import Odds
from src.database.models.predictions import Predictions
from src.database.models.team import Team

router = APIRouter(prefix="/data", tags=["data"])
logger = logging.getLogger(__name__)


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
        raise HTTPException(status_code=500, detail="获取比赛特征失败")


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
        raise HTTPException(status_code=500, detail="获取球队统计失败")


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
        raise HTTPException(status_code=500, detail="获取球队统计失败")


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
                "overall_status": quality_report.get(str("overall_status"), "unknown"),
                "quality_score": quality_report.get(str("quality_score"), 0),
                "anomalies_count": quality_report.get(str("anomalies"), {}).get(
                    str("count"), 0
                ),
                "last_check": quality_report.get("report_time"),
            },
            "system_health": system_health,
        }

        return dashboard_data

    except Exception as e:
        logger.error(f"获取仪表板数据失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取仪表板数据失败")


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
        db_health = "healthy"
        try:
            await session.execute(select(1))
        except Exception:
            db_health = "unhealthy"

        # 检查最近的数据采集状态
        recent_logs_query = (
            select(DataCollectionLog)
            .where(DataCollectionLog.created_at >= datetime.now() - timedelta(hours=24))
            .order_by(DataCollectionLog.created_at.desc())
            .limit(10)
        )
        logs_result = await session.execute(recent_logs_query)
        recent_logs = logs_result.scalars().all()

        collection_health = "healthy"
        if not recent_logs:
            collection_health = "no_data"
        else:
            failed_logs = [log for log in recent_logs if log.status == "failed"]
            if len(failed_logs) > len(recent_logs) * 0.5:
                collection_health = "unhealthy"
            elif failed_logs:
                collection_health = "warning"

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
