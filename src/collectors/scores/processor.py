"""
数据处理器
Data Processor

处理和验证比分数据。
"""




logger = __import__("logging").getLogger(__name__)


class ScoreDataProcessor:
    """比分数据处理器"""

    def __init__(self, db_session: AsyncSession):
        """
        初始化处理器

        Args:
            db_session: 数据库会话
        """
        self.db_session = db_session

    async def process_score_data(
        self, match_id: int, score_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        处理和验证比分数据

        Args:
            match_id: 比赛ID
            score_data: 原始比分数据

        Returns:
            Optional[Dict[str, Any]]: 处理后的数据
        """
        try:
            # 获取数据库中的比赛信息
            match = await self.db_session.get(Match, match_id)
            if not match:
                logger.warning(f"比赛 {match_id} 不存在于数据库中")
                return None

            # 验证数据完整性
            if not all(
                k in score_data for k in ["home_score", "away_score", "match_status"]
            ):
                logger.warning(f"比赛 {match_id} 比分数据不完整")
                return None

            # 更新比赛状态
            old_status = match.match_status
            new_status = self._map_status(score_data["match_status"])

            processed_data = {
                "match_id": match_id,
                "home_score": int(score_data["home_score"]),
                "away_score": int(score_data["away_score"]),
                "home_half_score": int(score_data.get("home_half_score", 0)),
                "away_half_score": int(score_data.get("away_half_score", 0)),
                "match_status": new_status.value,
                "match_time": parse_datetime(score_data.get("match_time")),
                "last_updated": parse_datetime(score_data.get("last_updated")),
                "events": score_data.get("events", []),
                "previous_status": old_status.value,
            }

            # 检查是否有实质性更新
            if self._has_significant_change(match, processed_data):
                return processed_data

            logger.debug(f"比赛 {match_id} 比分无实质性变化")
            return None

        except Exception as e:
            logger.error(f"处理比赛 {match_id} 比分数据失败: {e}")
            return None

    def _map_status(self, api_status: str) -> MatchStatus:
        """
        映射API状态到内部状态

        Args:
            api_status: API状态

        Returns:
            MatchStatus: 内部状态
        """
        status_mapping = {
            "SCHEDULED": MatchStatus.SCHEDULED,
            "TIMED": MatchStatus.SCHEDULED,
            "POSTPONED": MatchStatus.POSTPONED,
            "CANCELED": MatchStatus.CANCELLED,
            "IN_PLAY": MatchStatus.IN_PROGRESS,
            "LIVE": MatchStatus.IN_PROGRESS,
            "PAUSED": MatchStatus.PAUSED,
            "FINISHED": MatchStatus.FINISHED,
            "AWARDED": MatchStatus.FINISHED,
        }

        return status_mapping.get(api_status.upper(), MatchStatus.SCHEDULED)

    def _has_significant_change(self, match: Match, new_data: Dict[str, Any]) -> bool:
        """
        检查是否有实质性变化

        Args:
            match: 比赛记录
            new_data: 新数据

        Returns:
            bool: 是否有实质性变化
        """
        # 比分变化
        if (
            match.home_score != new_data["home_score"]
            or match.away_score != new_data["away_score"]
        ):
            return True

        # 状态变化
        if match.match_status != new_data["match_status"]:
            return True

        # 半场比分变化
        if (
            match.home_half_score != new_data["home_half_score"]
            or match.away_half_score != new_data["away_half_score"]
        ):
            return True

        return False

    def validate_score_data(self, score_data: Dict[str, Any]) -> bool:
        """
        验证比分数据格式

        Args:
            score_data: 比分数据

        Returns:
            bool: 是否有效
        """
        required_fields = ["match_id", "home_score", "away_score"]
        for field in required_fields:
            if field not in score_data:
                return False




        # 验证比分是否为数字
        try:
            int(score_data["home_score"])
            int(score_data["away_score"])
        except (ValueError, TypeError):
            return False

        return True