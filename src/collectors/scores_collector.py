"""
比分收集器
实时收集比赛比分和事件
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.cache.redis_manager import RedisManager
from src.database.base import DatabaseSession
from src.models.common_models import Match, MatchEvent, Score
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ScoresCollector:
    """比分收集器"""

    def __init__(self, db_session: AsyncSession, redis_client: RedisManager):
        self.db_session = db_session
        self.redis_client = redis_client
        self.cache_timeout = 60  # 1分钟缓存，比分变化很快
        self.api_endpoints = {
            "live_scores": "https://api.football-data.org/v4/matches",
            "events": "https://api.football-data.org/v4/matches/{match_id}/events",
        }
        self.headers = {"X-Auth-Token": "YOUR_API_TOKEN"}  # 应该从配置中读取

    async def collect_live_scores(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        收集所有正在进行的比赛比分

        Args:
            force_refresh: 是否强制刷新

        Returns:
            实时比分数据
        """
        cache_key = "scores:live"

        if not force_refresh:
            cached_data = await self.redis_client.get_cache_value(cache_key)
            if cached_data:
                logger.debug("从缓存获取实时比分")
                return cached_data

        try:
            # 获取数据库中的实时比赛
            live_matches = await self._get_live_matches_from_db()

            live_scores = {}
            for match in live_matches:
                # 获取最新比分
                score_data = await self._get_match_score(match.id)

                # 获取比赛事件
                events = await self._get_match_events(match.id)

                live_scores[match.id] = {
                    "match_info": {
                        "id": match.id,
                        "home_team_id": match.home_team_id,
                        "away_team_id": match.away_team_id,
                        "minute": match.minute,
                        "status": match.match_status,
                    },
                    "score": score_data,
                    "events": events,
                    "last_updated": datetime.now().isoformat(),
                }

            # 缓存结果
            await self.redis_client.set_cache_value(
                cache_key, live_scores, expire=self.cache_timeout
            )

            logger.info(f"收集到 {len(live_scores)} 场实时比分")
            return {"live_matches_count": len(live_scores), "scores": live_scores}

        except Exception as e:
            logger.error(f"收集实时比分失败: {e}")
            return {"error": str(e)}

    async def predict_final_score(
        self, match_id: int, current_score: Optional[Dict[str, int]] = None
    ) -> Dict[str, Any]:
        """
        预测最终比分

        Args:
            match_id: 比赛ID
            current_score: 当前比分（可选）

        Returns:
            预测结果
        """
        try:
            # 获取比赛信息
            match = await self._get_match_by_id(match_id)
            if not match:
                return {"error": "比赛不存在"}

            # 获取当前比分
            if not current_score:
                current_score = await self._get_match_score(match_id)

            # 获取比赛历史数据
            teams_history = await self._get_teams_history(
                match.home_team_id, match.away_team_id
            )

            # 基于历史数据和当前比分进行预测
            prediction = await self._generate_final_score_prediction(
                match, current_score, teams_history
            )

            # 缓存预测结果
            cache_key = f"prediction:final_score:{match_id}"
            await self.redis_client.set_cache_value(
                cache_key, prediction, expire=300
            )  # 5分钟缓存

            return prediction

        except Exception as e:
            logger.error(f"预测最终比分失败: {e}")
            return {"error": str(e)}

    async def collect_match_events(
        self, match_id: int, force_refresh: bool = False
    ) -> List[Dict[str, Any]]:
        """
        收集比赛事件

        Args:
            match_id: 比赛ID
            force_refresh: 是否强制刷新

        Returns:
            事件列表
        """
        cache_key = f"events:match:{match_id}"

        if not force_refresh:
            cached_data = await self.redis_client.get_cache_value(cache_key)
            if cached_data:
                return cached_data

        try:
            events = await self._get_match_events(match_id)

            # 缓存结果
            if events:
                await self.redis_client.set_cache_value(
                    cache_key, events, expire=self.cache_timeout
                )

            return events

        except Exception as e:
            logger.error(f"收集比赛 {match_id} 事件失败: {e}")
            return []

    async def update_match_score(
        self,
        match_id: int,
        home_score: int,
        away_score: int,
        minute: Optional[int] = None,
    ) -> bool:
        """
        更新比赛比分

        Args:
            match_id: 比赛ID
            home_score: 主队得分
            away_score: 客队得分
            minute: 比赛分钟

        Returns:
            是否更新成功
        """
        try:
            # 获取比赛
            match = await self._get_match_by_id(match_id)
            if not match:
                logger.error(f"比赛 {match_id} 不存在")
                return False

            # 更新比分
            match.home_score = home_score
            match.away_score = away_score
            if minute:
                match.minute = minute

            # 更新状态
            if match.match_status == "scheduled":
                match.match_status = "live"

            # 创建或更新比分记录
            score = await self._get_or_create_score(match_id)
            score.home_score = home_score
            score.away_score = away_score
            score.timestamp = datetime.now()

            await self.db_session.commit()

            # 清除相关缓存
            await self._clear_match_cache(match_id)

            logger.info(f"更新比赛 {match_id} 比分: {home_score}-{away_score}")
            return True

        except Exception as e:
            logger.error(f"更新比分失败: {e}")
            await self.db_session.rollback()
            return False

    async def add_match_event(
        self,
        match_id: int,
        event_type: str,
        minute: int,
        team_id: int,
        player_id: Optional[int] = None,
        description: Optional[str] = None,
    ) -> bool:
        """
        添加比赛事件

        Args:
            match_id: 比赛ID
            event_type: 事件类型 (goal, yellow_card, red_card, substitution等)
            minute: 比赛分钟
            team_id: 球队ID
            player_id: 球员ID
            description: 事件描述

        Returns:
            是否添加成功
        """
        try:
            event = MatchEvent(
                match_id=match_id,
                event_type=event_type,
                minute=minute,
                team_id=team_id,
                player_id=player_id,
                description=description or f"{event_type} at {minute}'",
            )

            self.db_session.add(event)
            await self.db_session.commit()

            # 清除相关缓存
            await self._clear_match_cache(match_id)

            logger.info(f"添加比赛 {match_id} 事件: {event_type}")
            return True

        except Exception as e:
            logger.error(f"添加比赛事件失败: {e}")
            await self.db_session.rollback()
            return False

    async def _get_live_matches_from_db(self) -> List[Match]:
        """从数据库获取正在进行的比赛"""
        result = await self.db_session.execute(
            select(Match).where(
                or_(Match.match_status == "live", Match.match_status == "half_time")
            )
        )
        return result.scalars().all()

    async def _get_match_by_id(self, match_id: int) -> Optional[Match]:
        """根据ID获取比赛"""
        result = await self.db_session.execute(
            select(Match).where(Match.id == match_id)
        )
        return result.scalar_one_or_none()

    async def _get_match_score(self, match_id: int) -> Dict[str, int]:
        """获取比赛比分"""
        # 先从match表获取
        match = await self._get_match_by_id(match_id)
        if match and match.home_score is not None:
            return {"home": match.home_score, "away": match.away_score}

        # 从score表获取
        result = await self.db_session.execute(
            select(Score)
            .where(Score.match_id == match_id)
            .order_by(Score.timestamp.desc())
        ).first()

        if result:
            return {"home": result.home_score, "away": result.away_score}

        return {"home": 0, "away": 0}

    async def _get_or_create_score(self, match_id: int) -> Score:
        """获取或创建比分记录"""
        result = await self.db_session.execute(
            select(Score).where(Score.match_id == match_id)
        ).scalar_one_or_none()

        if not result:
            result = Score(match_id=match_id, home_score=0, away_score=0)
            self.db_session.add(result)

        return result

    async def _get_match_events(self, match_id: int) -> List[Dict[str, Any]]:
        """获取比赛事件"""
        result = await self.db_session.execute(
            select(MatchEvent)
            .where(MatchEvent.match_id == match_id)
            .order_by(MatchEvent.minute.asc())
        )
        events = result.scalars().all()

        event_list = []
        for event in events:
            event_list.append(
                {
                    "id": event.id,
                    "type": event.event_type,
                    "minute": event.minute,
                    "team_id": event.team_id,
                    "player_id": event.player_id,
                    "description": event.description,
                }
            )

        return event_list

    async def _get_teams_history(
        self, home_team_id: int, away_team_id: int
    ) -> Dict[str, Any]:
        """获取两队历史交锋数据"""
        # 获取过去5次交锋
        result = await self.db_session.execute(
            select(Match)
            .where(
                or_(
                    and_(
                        Match.home_team_id == home_team_id,
                        Match.away_team_id == away_team_id,
                    ),
                    and_(
                        Match.home_team_id == away_team_id,
                        Match.away_team_id == home_team_id,
                    ),
                )
            )
            .order_by(Match.start_time.desc())
            .limit(5)
        )

        matches = result.scalars().all()

        history = {
            "matches_played": len(matches),
            "home_wins": 0,
            "away_wins": 0,
            "draws": 0,
            "average_goals": 0,
        }

        total_goals = 0
        for match in matches:
            if match.home_score is not None and match.away_score is not None:
                total_goals += match.home_score + match.away_score

                if match.home_team_id == home_team_id:
                    if match.home_score > match.away_score:
                        history["home_wins"] += 1
                    elif match.home_score < match.away_score:
                        history["away_wins"] += 1
                    else:
                        history["draws"] += 1
                else:
                    if match.home_score > match.away_score:
                        history["away_wins"] += 1
                    elif match.home_score < match.away_score:
                        history["home_wins"] += 1
                    else:
                        history["draws"] += 1

        if len(matches) > 0:
            history["average_goals"] = total_goals / len(matches)

        return history

    async def _generate_final_score_prediction(
        self, match: Match, current_score: Dict[str, int], history: Dict[str, Any]
    ) -> Dict[str, Any]:
        """生成最终比分预测"""
        # 基于历史数据和当前比分的简单预测算法
        current_home = current_score.get("home", 0)
        current_away = current_score.get("away", 0)

        # 计算预期进球数
        avg_goals = history.get("average_goals", 2.5)
        minute = match.minute or 0

        # 根据比赛进度调整
        remaining_minutes = max(90 - minute, 1)
        expected_remaining_goals = (avg_goals * remaining_minutes) / 90

        # 根据历史优势调整
        home_advantage = (
            history.get("home_wins", 0) - history.get("away_wins", 0)
        ) / max(history.get("matches_played", 1), 1)

        # 预测最终比分
        predicted_home_goals = current_home + (
            expected_remaining_goals * (0.5 + home_advantage * 0.2)
        )
        predicted_away_goals = current_away + (
            expected_remaining_goals * (0.5 - home_advantage * 0.2)
        )

        # 生成最可能的比分
        final_score = {
            "home": round(predicted_home_goals),
            "away": round(predicted_away_goals),
        }

        # 计算置信度
        confidence = min(0.5 + (history.get("matches_played", 0) / 10), 0.95)

        return {
            "match_id": match.id,
            "current_score": current_score,
            "predicted_final_score": final_score,
            "confidence": confidence,
            "reasoning": {
                "average_goals": avg_goals,
                "minute": minute,
                "remaining_minutes": remaining_minutes,
                "history": history,
            },
        }

    async def _clear_match_cache(self, match_id: int) -> None:
        """清除比赛相关的缓存"""
        keys_to_clear = [
            "scores:live",
            f"events:match:{match_id}",
            f"prediction:final_score:{match_id}",
        ]

        for key in keys_to_clear:
            await self.redis_client.delete_cache(key)


class ScoresCollectorFactory:
    """比分收集器工厂类"""

    @staticmethod
    def create() -> ScoresCollector:
        """创建比分收集器实例"""
        db_session = DatabaseSession()
        redis_client = RedisManager()
        return ScoresCollector(db_session, redis_client)
