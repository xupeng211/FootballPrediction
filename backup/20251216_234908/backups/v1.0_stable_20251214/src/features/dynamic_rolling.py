"""
动态滚动特征计算模块
为即将进行的比赛实时计算滚动特征

功能:
1. 动态获取球队的过去比赛记录
2. 计算滚动统计指标 (最近5场的平均xG、进球等)
3. 生成与Phase 2一致的特征格式
4. 支持实时特征计算

作者: Full Stack Automation Engineer
创建时间: 2025-01-10
版本: 1.0.0 - Phase 4 Daily Automation
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.async_manager import get_db_session
from src.core.config import get_settings

logger = logging.getLogger(__name__)


class DynamicRollingFeatureExtractor:
    """动态滚动特征提取器"""

    def __init__(self):
        self.settings = get_settings()
        self.default_window = 5  # 默认滚动窗口大小

    async def get_features_for_upcoming_match(
        self, match_id: str, db_session: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        为即将进行的比赛计算动态特征

        Args:
            match_id: 比赛ID
            db_session: 数据库会话 (可选)

        Returns:
            特征字典，格式与Phase 2一致
        """
        try:
            if db_session:
                return await self._calculate_features_with_session(match_id, db_session)
            else:
                async with get_db_session() as session:
                    return await self._calculate_features_with_session(
                        match_id, session
                    )

        except Exception as e:
            logger.error(f"❌ 计算动态特征失败 (match_id: {match_id}): {e}")
            return self._get_default_features()

    async def _calculate_features_with_session(
        self, match_id: str, session: AsyncSession
    ) -> Dict[str, Any]:
        """使用现有会话计算特征"""

        # 1. 获取比赛信息
        match_info = await self._get_match_info(match_id, session)
        if not match_info:
            return self._get_default_features()

        # 2. 获取主客队的过去比赛
        home_team_stats = await self._get_team_rolling_stats(
            match_info["home_team_id"], session, match_info["match_date"]
        )
        away_team_stats = await self._get_team_rolling_stats(
            match_info["away_team_id"], session, match_info["match_date"]
        )

        # 3. 构建特征字典
        features = self._build_feature_dict(
            match_info=match_info,
            home_stats=home_team_stats,
            away_stats=away_team_stats,
        )

        logger.debug(f"✅ 成功计算比赛 {match_id} 的动态特征")
        return features

    async def _get_match_info(
        self, match_id: str, session: AsyncSession
    ) -> Optional[Dict[str, Any]]:
        """获取比赛基本信息"""
        sql = """
        SELECT
            m.id,
            m.home_team_id,
            m.away_team_id,
            m.home_team_name,
            m.away_team_name,
            m.match_date,
            m.league_id,
            ht.name as home_team_name_db,
            at.name as away_team_name_db
        FROM matches m
        LEFT JOIN teams ht ON m.home_team_id = ht.id
        LEFT JOIN teams at ON m.away_team_id = at.id
        WHERE m.id = :match_id;
        """

        result = await session.execute(text(sql), {"match_id": match_id})
        row = result.first()

        if not row:
            logger.warning(f"⚠️ 未找到比赛信息: {match_id}")
            return None

        return {
            "match_id": row.id,
            "home_team_id": row.home_team_id,
            "away_team_id": row.away_team_id,
            "home_team_name": row.home_team_name or row.home_team_name_db,
            "away_team_name": row.away_team_name or row.away_team_name_db,
            "match_date": row.match_date,
            "league_id": row.league_id,
            "league_name": None,  # 数据库中没有这个字段
        }

    async def _get_team_rolling_stats(
        self,
        team_id: str,
        session: AsyncSession,
        match_date: datetime,
        window_size: int = None,
    ) -> Dict[str, float]:
        """获取球队的滚动统计数据"""
        if window_size is None:
            window_size = self.default_window

        sql = """
        SELECT
            COUNT(*) as total_matches,
            AVG(home_score) as avg_home_goals,
            AVG(away_score) as avg_away_goals,
            AVG(home_xg) as avg_home_xg,
            AVG(away_xg) as avg_away_xg,
            AVG(home_shots) as avg_home_shots,
            AVG(away_shots) as avg_away_shots,
            AVG(home_shots_on_target) as avg_home_sot,
            AVG(away_shots_on_target) as avg_away_sot,
            SUM(CASE WHEN home_score > away_score THEN 1 ELSE 0 END) as home_wins,
            SUM(CASE WHEN home_score = away_score THEN 1 ELSE 0 END) as home_draws,
            SUM(CASE WHEN home_score < away_score THEN 1 ELSE 0 END) as home_losses
        FROM (
            SELECT
                m.home_score,
                m.away_score,
                m.home_xg,
                m.away_xg,
                m.home_shots,
                m.away_shots,
                m.home_shots_on_target,
                m.away_shots_on_target,
                m.match_date
            FROM matches m
            WHERE (m.home_team_id = :team_id OR m.away_team_id = :team_id)
                AND m.match_date < :match_date
                AND m.status = 'completed'
                AND m.home_score IS NOT NULL
                AND m.away_score IS NOT NULL
            ORDER BY m.match_date DESC
            LIMIT :window_size
        ) recent_matches;
        """

        result = await session.execute(
            text(sql),
            {"team_id": team_id, "match_date": match_date, "window_size": window_size},
        )

        row = result.first()

        if not row or row.total_matches == 0:
            # 如果没有历史数据，返回默认值
            return self._get_default_team_stats()

        # 计算统计数据
        stats = {
            "total_matches": row.total_matches,
            "avg_goals_scored": float(row.avg_home_goals or 0)
            + float(row.avg_away_goals or 0),
            "avg_goals_conceded": float(row.avg_away_goals or 0)
            + float(row.avg_home_goals or 0),
            "avg_xg_for": float(row.avg_home_xg or 0) + float(row.avg_away_xg or 0),
            "avg_xg_against": float(row.avg_away_xg or 0) + float(row.avg_home_xg or 0),
            "avg_shots_for": float(row.avg_home_shots or 0)
            + float(row.avg_away_shots or 0),
            "avg_shots_against": float(row.avg_away_shots or 0)
            + float(row.avg_home_shots or 0),
            "avg_sot_for": float(row.avg_home_sot or 0) + float(row.avg_away_sot or 0),
            "avg_sot_against": float(row.avg_away_sot or 0)
            + float(row.avg_home_shots or 0),
            "win_rate": (row.home_wins or 0) / row.total_matches,
            "draw_rate": (row.home_draws or 0) / row.total_matches,
            "loss_rate": (row.home_losses or 0) / row.total_matches,
        }

        return stats

    def _get_default_team_stats(self) -> Dict[str, float]:
        """获取默认球队统计数据"""
        return {
            "total_matches": 0,
            "avg_goals_scored": 1.0,
            "avg_goals_conceded": 1.0,
            "avg_xg_for": 1.2,
            "avg_xg_against": 1.2,
            "avg_shots_for": 12.0,
            "avg_shots_against": 12.0,
            "avg_sot_for": 4.0,
            "avg_sot_against": 4.0,
            "win_rate": 0.33,
            "draw_rate": 0.34,
            "loss_rate": 0.33,
        }

    def _build_feature_dict(
        self,
        match_info: Dict[str, Any],
        home_stats: Dict[str, float],
        away_stats: Dict[str, float],
    ) -> Dict[str, Any]:
        """构建与Phase 2一致的特征字典"""

        # 计算衍生特征 (与Phase 2保持一致)
        home_xg_diff = home_stats["avg_xg_for"] - home_stats["avg_xg_against"]
        away_xg_diff = away_stats["avg_xg_for"] - away_stats["avg_xg_against"]

        home_goals_diff = (
            home_stats["avg_goals_scored"] - home_stats["avg_goals_conceded"]
        )
        away_goals_diff = (
            away_stats["avg_goals_scored"] - away_stats["avg_goals_conceded"]
        )

        home_shot_ratio = self._safe_division(
            home_stats["avg_shots_for"], home_stats["avg_shots_against"]
        )
        away_shot_ratio = self._safe_division(
            away_stats["avg_shots_for"], away_stats["avg_shots_against"]
        )

        # 构建完整的特征字典 (14个核心特征)
        features = {
            # 基础信息
            "id": match_info["match_id"],
            "home_team_name": match_info["home_team_name"],
            "away_team_name": match_info["away_team_name"],
            "match_date": match_info["match_date"].isoformat()
            if match_info["match_date"]
            else None,
            "league_id": match_info["league_id"],
            "league_name": match_info["league_name"],
            # 滚动特征 (主队)
            "home_last_5_avg_goals_scored": round(home_stats["avg_goals_scored"], 3),
            "home_last_5_avg_goals_conceded": round(
                home_stats["avg_goals_conceded"], 3
            ),
            "home_last_5_avg_xg_for": round(home_stats["avg_xg_for"], 3),
            "home_last_5_avg_xg_against": round(home_stats["avg_xg_against"], 3),
            "home_last_5_xg_difference": round(home_xg_diff, 3),
            "home_last_5_shot_ratio": round(home_shot_ratio, 3),
            # 滚动特征 (客队)
            "away_last_5_avg_goals_scored": round(away_stats["avg_goals_scored"], 3),
            "away_last_5_avg_goals_conceded": round(
                away_stats["avg_goals_conceded"], 3
            ),
            "away_last_5_avg_xg_for": round(away_stats["avg_xg_for"], 3),
            "away_last_5_avg_xg_against": round(away_stats["avg_xg_against"], 3),
            "away_last_5_xg_difference": round(away_xg_diff, 3),
            "away_last_5_shot_ratio": round(away_shot_ratio, 3),
            # 差值特征
            "xg_difference_gap": round(home_xg_diff - away_xg_diff, 3),
            "goals_difference_gap": round(home_goals_diff - away_goals_diff, 3),
            # 额外元数据
            "feature_source": "dynamic_rolling",
            "calculation_time": datetime.now().isoformat(),
            "home_team_matches_used": home_stats["total_matches"],
            "away_team_matches_used": away_stats["total_matches"],
        }

        return features

    def _safe_division(
        self, numerator: float, denominator: float, default: float = 1.0
    ) -> float:
        """安全除法，避免除零错误"""
        if denominator == 0:
            return default
        return numerator / denominator

    def _get_default_features(self) -> Dict[str, Any]:
        """获取默认特征字典"""
        default_stats = self._get_default_team_stats()

        return {
            "id": None,
            "home_team_name": "Unknown",
            "away_team_name": "Unknown",
            "match_date": None,
            "league_id": None,
            "league_name": None,
            # 默认滚动特征
            "home_last_5_avg_goals_scored": round(default_stats["avg_goals_scored"], 3),
            "home_last_5_avg_goals_conceded": round(
                default_stats["avg_goals_conceded"], 3
            ),
            "home_last_5_avg_xg_for": round(default_stats["avg_xg_for"], 3),
            "home_last_5_avg_xg_against": round(default_stats["avg_xg_against"], 3),
            "home_last_5_xg_difference": 0.0,
            "home_last_5_shot_ratio": 1.0,
            "away_last_5_avg_goals_scored": round(default_stats["avg_goals_scored"], 3),
            "away_last_5_avg_goals_conceded": round(
                default_stats["avg_goals_conceded"], 3
            ),
            "away_last_5_avg_xg_for": round(default_stats["avg_xg_for"], 3),
            "away_last_5_avg_xg_against": round(default_stats["avg_xg_against"], 3),
            "away_last_5_xg_difference": 0.0,
            "away_last_5_shot_ratio": 1.0,
            "xg_difference_gap": 0.0,
            "goals_difference_gap": 0.0,
            "feature_source": "default_fallback",
            "calculation_time": datetime.now().isoformat(),
            "home_team_matches_used": 0,
            "away_team_matches_used": 0,
        }

    async def batch_get_features(self, match_ids: List[str]) -> List[Dict[str, Any]]:
        """批量计算多场比赛的特征"""
        logger.info(f"🔄 批量计算 {len(match_ids)} 场比赛的动态特征")

        features_list = []

        async with get_db_session() as session:
            for match_id in match_ids:
                try:
                    features = await self._calculate_features_with_session(
                        match_id, session
                    )
                    features_list.append(features)
                except Exception as e:
                    logger.error(f"❌ 计算比赛 {match_id} 特征失败: {e}")
                    features_list.append(self._get_default_features())

        logger.info(f"✅ 完成 {len(features_list)} 场比赛的特征计算")
        return features_list


# 全局实例
dynamic_feature_extractor = DynamicRollingFeatureExtractor()


async def get_features_for_upcoming_match(match_id: str) -> Dict[str, Any]:
    """
    便捷函数: 获取即将进行比赛的特征

    Args:
        match_id: 比赛ID

    Returns:
        特征字典
    """
    return await dynamic_feature_extractor.get_features_for_upcoming_match(match_id)


async def batch_get_features_for_upcoming_matches(
    match_ids: List[str],
) -> List[Dict[str, Any]]:
    """
    便捷函数: 批量获取即将进行比赛的特征

    Args:
        match_ids: 比赛ID列表

    Returns:
        特征字典列表
    """
    return await dynamic_feature_extractor.batch_get_features(match_ids)
