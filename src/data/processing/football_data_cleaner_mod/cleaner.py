"""
足球数据清洗器主模块

协调各个子模块，提供统一的数据清洗接口。
"""




class FootballDataCleaner:
    """
    足球数据清洗器

    负责清洗和标准化从外部API采集的原始足球数据，
    确保数据质量和一致性。
    """

    def __init__(self):
        """初始化数据清洗器"""
        from ....database.connection import DatabaseManager

        self.db_manager = DatabaseManager()
        self.logger = logging.getLogger(f"cleaner.{self.__class__.__name__}")

        # 初始化子处理器
        self.time_processor = TimeProcessor()
        self.id_mapper = IDMapper(self.db_manager)
        self.data_validator = DataValidator()
        self.odds_processor = OddsProcessor(self.time_processor)

    async def clean_match_data(
        self, raw_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        清洗比赛数据

        Args:
            raw_data: 原始比赛数据

        Returns:
            Optional[Dict]: 清洗后的数据，无效则返回None
        """
        try:
            if not self.data_validator.validate_match_data(raw_data):
                return None

            league_id = await self.id_mapper.map_league_id(
                raw_data.get("competition", {})
            )

            home_team_id = await self.id_mapper.map_team_id(
                raw_data.get("homeTeam", {}), league_id=league_id
            )
            away_team_id = await self.id_mapper.map_team_id(
                raw_data.get("awayTeam", {}), league_id=league_id
            )

            cleaned_data = {
                # 基础信息
                "external_match_id": str(raw_data.get("id", "")),
                "external_league_id": str(
                    raw_data.get("competition", {}).get("id", "")
                ),
                # 时间统一 - 转换为UTC
                "match_time": self.time_processor.to_utc_time(raw_data.get("utcDate")),
                # 球队ID统一 - 映射到标准ID
                "home_team_id": home_team_id,
                "away_team_id": away_team_id,
                # 联赛ID映射
                "league_id": league_id,
                # 比赛状态标准化
                "match_status": self.data_validator.standardize_match_status(
                    raw_data.get("status")
                ),
                # 比分验证 - 范围检查
                "home_score": self.data_validator.validate_score(
                    raw_data.get("score", {}).get("fullTime", {}).get("home")
                ),
                "away_score": self.data_validator.validate_score(
                    raw_data.get("score", {}).get("fullTime", {}).get("away")
                ),
                "home_ht_score": self.data_validator.validate_score(
                    raw_data.get("score", {}).get("halfTime", {}).get("home")
                ),
                "away_ht_score": self.data_validator.validate_score(
                    raw_data.get("score", {}).get("halfTime", {}).get("away")
                ),
                # 其他信息
                "season": self.time_processor.extract_season(
                    raw_data.get("season", {})
                ),
                "matchday": raw_data.get("matchday"),
                "venue": self.data_validator.clean_venue_name(raw_data.get("venue")),
                "referee": self.data_validator.clean_referee_name(
                    raw_data.get("referees")
                ),
                # 元数据
                "cleaned_at": datetime.now(timezone.utc).isoformat(),
                "data_source": "cleaned",
            }

            return cleaned_data

        except Exception as e:
            self.logger.error(f"Failed to clean match data: {str(e)}")
            return None

    async def clean_odds_data(
        self, raw_odds: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        清洗赔率数据

        Args:
            raw_odds: 原始赔率数据列表

        Returns:
            List[Dict]: 清洗后的赔率数据列表
        """
        return await self.odds_processor.clean_odds_data(raw_odds)

    # 向后兼容的方法
    def _validate_match_data(self, raw_data: Dict[str, Any]) -> bool:
        """验证比赛数据的基础字段（向后兼容）"""
        return self.data_validator.validate_match_data(raw_data)

    def _validate_odds_data(self, raw_odds: Dict[str, Any]) -> bool:
        """验证赔率数据的基础字段（向后兼容）"""
        return self.data_validator.validate_odds_data(raw_odds)

    def _to_utc_time(self, time_str: Optional[str]) -> Optional[str]:
        """时间统一转换为UTC（向后兼容）"""
        return self.time_processor.to_utc_time(time_str)

    async def _map_team_id(
        self, team_data: Dict[str, Any], *, league_id: Optional[int] = None
    ) -> Optional[int]:
        """球队ID映射到标准ID（向后兼容）"""
        return await self.id_mapper.map_team_id(team_data, league_id=league_id)

    async def _map_league_id(self, league_data: Dict[str, Any]) -> Optional[int]:
        """联赛ID映射到标准ID（向后兼容）"""
        return await self.id_mapper.map_league_id(league_data)

    def _deterministic_id(self, value: str, *, modulus: int) -> int:
        """基于稳定哈希生成确定性ID（向后兼容）"""
        return self.id_mapper._deterministic_id(value, modulus=modulus)

    def _standardize_match_status(self, status: Optional[str]) -> str:
        """标准化比赛状态（向后兼容）"""
        return self.data_validator.standardize_match_status(status)

    def _validate_score(self, score: Any) -> Optional[int]:
        """验证比分数据（向后兼容）"""
        return self.data_validator.validate_score(score)

    def _extract_season(self, season_data: Dict[str, Any]) -> Optional[str]:
        """提取赛季信息（向后兼容）"""
        return self.time_processor.extract_season(season_data)

    def _clean_venue_name(self, venue: Optional[str]) -> Optional[str]:
        """清洗场地名称（向后兼容）"""
        return self.data_validator.clean_venue_name(venue)

    def _clean_referee_name(
        self, referees: Optional[List[Dict[str, Any]]]
    ) -> Optional[str]:
        """清洗裁判姓名（向后兼容）"""
        return self.data_validator.clean_referee_name(referees)

    def _validate_odds_value(self, price: Any) -> bool:
        """验证赔率值（向后兼容）"""
        return self.odds_processor.validate_odds_value(price)

    def _standardize_outcome_name(self, name: Optional[str]) -> str:
        """标准化结果名称（向后兼容）"""
        return self.odds_processor.standardize_outcome_name(name)

    def _standardize_bookmaker_name(self, bookmaker: Optional[str]) -> str:
        """标准化博彩公司名称（向后兼容）"""
        return self.odds_processor.standardize_bookmaker_name(bookmaker)

    def _standardize_market_type(self, market_type: Optional[str]) -> str:
        """标准化市场类型（向后兼容）"""
        return self.odds_processor.standardize_market_type(market_type)

    def _validate_odds_consistency(self, outcomes: List[Dict[str, Any]]) -> bool:
        """验证赔率合理性（向后兼容）"""
        return self.odds_processor.validate_odds_consistency(outcomes)

    def _calculate_implied_probabilities(
        self, outcomes: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """计算隐含概率（向后兼容）"""
        return self.odds_processor.calculate_implied_probabilities(outcomes)
from datetime import datetime, timezone
import logging

from .data_validator import DataValidator
from .id_mapper import IDMapper
from .odds_processor import OddsProcessor
from .time_processor import TimeProcessor

