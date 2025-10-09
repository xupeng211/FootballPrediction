"""
赔率数据存储
Odds Data Storage

管理赔率数据的存储和检索
"""




# Market type mapping
class MarketType:
    MATCH_WINNER = "match_winner"
    OVER_UNDER = "over_under"
    HANDICAP = "handicap"
    BOTH_TEAMS_SCORE = "both_teams_score"
    CORRECT_SCORE = "correct_score"

logger = logging.getLogger(__name__)


class OddsStorage:
    """赔率数据存储管理器"""

    def __init__(self, db_session: AsyncSession, redis_manager=None):
        """
        初始化存储管理器

        Args:
            db_session: 数据库会话
            redis_manager: Redis管理器
        """
        self.db_session = db_session
        self.redis_manager = redis_manager

        # 缓存管理
        self.odds_cache: Dict[str, Dict[str, Any]] = {}
        self.last_update_cache: Dict[str, datetime] = {}

        # 市场类型映射
        self.market_types = {
            "match_winner": MarketType.MATCH_WINNER,
            "over_under": MarketType.OVER_UNDER,
            "handicap": MarketType.HANDICAP,
            "both_teams_score": MarketType.BOTH_TEAMS_SCORE,
            "correct_score": MarketType.CORRECT_SCORE,
        }

    async def save_odds_data(self, odds_data: Dict[str, Any]) -> bool:
        """
        保存赔率数据到数据库

        Args:
            odds_data: 赔率数据

        Returns:
            是否成功
        """
        try:
            start_time = utc_now()

            # 保存每个博彩公司的赔率
            for bookmaker_data in odds_data.get("bookmakers", []):
                odds = Odds(
                    match_id=odds_data["match_id"],
                    bookmaker=bookmaker_data["name"],
                    market_type="match_winner",  # 使用字符串而不是枚举
                    home_win_odds=bookmaker_data["home_win"],
                    draw_odds=bookmaker_data["draw"],
                    away_win_odds=bookmaker_data["away_win"],
                    created_at=parse_datetime(odds_data["timestamp"]),
                )
                self.db_session.add(odds)

            # 保存原始数据
            raw_data = RawOddsData(
                match_id=odds_data["match_id"],
                source="odds_collector",
                data=odds_data,
                collected_at=parse_datetime(odds_data["timestamp"]),
            )
            self.db_session.add(raw_data)

            await self.db_session.commit()

            logger.debug(f"保存比赛 {odds_data['match_id']} 赔率数据成功")
            return True

        except Exception as e:
            await self.db_session.rollback()
            logger.error(f"保存赔率数据失败: {e}")
            return False

    async def get_odds_history(
        self,
        match_id: int,
        bookmaker: str,
        market: str,
        hours: int = 24,
    ) -> List[Dict[str, Any]]:
        """
        获取赔率历史数据

        Args:
            match_id: 比赛ID
            bookmaker: 博彩公司
            market: 市场类型
            hours: 历史时长（小时）

        Returns:
            历史赔率数据
        """
        cutoff_time = utc_now() - timedelta(hours=hours)

        query = (
            select(Odds)
            .where(
                and_(
                    Odds.match_id == match_id,
                    Odds.bookmaker == bookmaker,
                    Odds.market_type
                    == market,  # 直接比较字符串
                    Odds.created_at >= cutoff_time,
                )
            )
            .order_by(Odds.created_at)
        )

        result = await self.db_session.execute(query)
        odds_records = result.scalars().all()

        return [
            {
                "timestamp": odds.created_at.isoformat(),
                "home_win": odds.home_win_odds,
                "draw": odds.draw_odds,
                "away_win": odds.away_win_odds,
                "over_line": odds.over_line,
                "over_odds": odds.over_odds,
                "under_odds": odds.under_odds,
            }
            for odds in odds_records
        ]

    async def get_match_info(self, match_id: int) -> Optional[Dict[str, Any]]:
        """
        获取比赛基本信息

        Args:
            match_id: 比赛ID

        Returns:
            比赛信息
        """
        query = select(Match).where(Match.id == match_id)
        result = await self.db_session.execute(query)
        match = result.scalar_one_or_none()

        if match:
            return {
                "id": match.id,
                "home_team_id": match.home_team_id,
                "away_team_id": match.away_team_id,
                "match_time": match.match_time,
                "status": match.match_status,
            }
        return None

    async def get_upcoming_matches(
        self,
        hours_ahead: int,
        max_matches: int,
    ) -> List[Dict[str, Any]]:
        """
        获取即将开始的比赛

        Args:
            hours_ahead: 未来多少小时
            max_matches: 最大比赛数

        Returns:
            比赛列表
        """
        start_time = utc_now()
        end_time = start_time + timedelta(hours=hours_ahead)

        query = (
            select(Match)
            .where(
                and_(
                    Match.match_time >= start_time,
                    Match.match_time <= end_time,
                    Match.match_status == MatchStatus.SCHEDULED,
                )
            )
            .order_by(Match.match_time)
            .limit(max_matches)
        )

        result = await self.db_session.execute(query)
        matches = result.scalars().all()

        return [
            {
                "id": match.id,
                "home_team_id": match.home_team_id,
                "away_team_id": match.away_team_id,
                "match_time": match.match_time.isoformat(),
                "status": match.match_status.value,
            }
            for match in matches
        ]

    def check_cache(
        self,
        match_id: int,
        bookmakers: List[str],
        markets: List[str],
        cache_duration_minutes: int = 5,
    ) -> Optional[Dict[str, Any]]:
        """
        检查缓存

        Args:
            match_id: 比赛ID
            bookmakers: 博彩公司列表
            markets: 市场类型列表
            cache_duration_minutes: 缓存有效期（分钟）

        Returns:
            缓存的数据或None
        """
        cache_key = f"odds:{match_id}:{':'.join(bookmakers)}:{':'.join(markets)}"

        if cache_key in self.odds_cache:
            last_update = self.last_update_cache.get(cache_key, utc_now())
            if utc_now() - last_update < timedelta(minutes=cache_duration_minutes):
                return self.odds_cache[cache_key]

        return None

    def update_cache(
        self,
        match_id: int,
        bookmakers: List[str],
        markets: List[str],
        data: Dict[str, Any],
    ):
        """
        更新缓存

        Args:
            match_id: 比赛ID
            bookmakers: 博彩公司列表
            markets: 市场类型列表
            data: 要缓存的数据
        """
        cache_key = f"odds:{match_id}:{':'.join(bookmakers)}:{':'.join(markets)}"
        self.odds_cache[cache_key] = data
        self.last_update_cache[cache_key] = utc_now()

    async def publish_odds_update(self, odds_data: Dict[str, Any]):
        """发布赔率更新到Redis"""
        if not self.redis_manager:
            return

        try:
            channel = f"odds:match:{odds_data['match_id']}"
            message = {
                "type": "odds_update",
                "match_id": odds_data["match_id"],
                "average_odds": odds_data.get("average_odds"),
                "best_odds": odds_data.get("best_odds"),
                "bookmaker_count": len(odds_data.get("bookmakers", [])),
                "timestamp": odds_data["timestamp"],
            }

            await self.redis_manager.client.publish(
                channel, json.dumps(message)
            )

            # 如果有价值投注，发送通知
            if odds_data.get("value_bets"):
                await self.redis_manager.client.publish(
                    "value_bets:alerts",
                    json.dumps(
                        {
                            "match_id": odds_data["match_id"],
                            "value_bets": odds_data["value_bets"],
                            "timestamp": odds_data["timestamp"],
                        }
                    ),
                )

        except Exception as e:
            logger.error(f"发布赔率更新失败: {e}")

    def clear_cache(self):
        """清空缓存"""
        self.odds_cache.clear()
        self.last_update_cache.clear()
        logger.info("赔率缓存已清空")
from datetime import datetime, timedelta
from typing import Any, Dict
import json

from sqlalchemy import select, and_

from .time_utils_compat import utc_now, parse_datetime
from src.database.models import Match, Odds, RawOddsData
from src.database.models.match import MatchStatus

