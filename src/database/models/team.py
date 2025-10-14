from typing import Any,  Dict[str, Any],  Any, List[Any], Optional
from sqlalchemy import Boolean, Column, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Session, relationship
from ..base import BaseModel
from enum import Enum


"""
球队模型

存储足球队伍的基础信息，如曼联、巴塞罗那等。
"""

# Match model imported locally to avoid circular imports


class TeamForm(Enum):
    """球队状态枚举"""

    GOOD = "good"  # 状态良好
    AVERAGE = "average"  # 状态一般
    POOR = "poor"  # 状态不佳


class Team(BaseModel):
    """
    球队表模型

    对应 architecture.md 中的 teams 表设计
    """

    __tablename__ = "teams"

    # 基础信息字段
    team_name = Column(String(100), nullable=False, comment="球队名称")

    team_code = Column(String(10), unique=True, nullable=True, comment="球队代码")

    country = Column(String(50), nullable=True, comment="所属国家")

    # API相关字段
    api_team_id = Column(Integer, unique=True, nullable=True, comment="API球队ID")

    # 联赛关系
    league_id = Column(
        Integer, ForeignKey("leagues.id"), nullable=True, comment="所属联赛ID"
    )

    # 球队详细信息
    founded_year = Column(Integer, nullable=True, comment="成立年份")

    stadium = Column(String(100), nullable=True, comment="主场体育场名称")

    # 状态字段
    is_active = Column(Boolean, default=True, nullable=False, comment="是否活跃")

    # 关系定义
    league = relationship("League", back_populates="teams")

    # 主场比赛
    home_matches = relationship(
        "Match",
        foreign_keys="Match.home_team_id",
        back_populates="home_team",
        lazy="dynamic",
    )

    # 客场比赛
    away_matches = relationship(
        "Match",
        foreign_keys="Match.away_team_id",
        back_populates="away_team",
        lazy="dynamic",
    )

    # 特征数据
    features = relationship(
        "Features", back_populates="team", lazy="dynamic", cascade="all, delete-orphan"
    )

    # 索引定义
    __table_args__ = (
        Index("idx_teams_league", "league_id"),
        Index("idx_teams_country", "country"),
        Index("idx_teams_active", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<Team(id={self.id}, name='{self.team_name}', league='{self.league.league_name if self.league else None}')>"

    @property
    def name(self) -> str:
        """球队名称的别名属性，为了兼容性"""
        return self.team_name  # type: ignore

    @property
    def display_name(self) -> str:
        """返回用于显示的球队名称。

        Returns:
            str: 格式化的球队显示名称，包含联赛信息（如果有）。
        """
        if self.country and hasattr(self, "league") and self.league:
            return f"{self.team_name} ({self.league.league_name})"
        return str(self.team_name)

    def get_all_matches(self) -> None:
        """获取所有比赛（主场+客场）。

        Note:
            这需要在调用时传入session参数，当前实现返回None。

        Returns:
            None: 实际使用时需要session参数。
        """
        # 这需要在调用时传入session
        return None  # 实际使用时需要session参数

    def get_recent_matches(self, session: Session, limit: int = 5) -> List[Any]:
        """获取最近的比赛。

        Args:
            session: 数据库会话对象。
            limit: 返回的比赛数量限制，默认为5。

        Returns:
            List[Match]: 按时间倒序排列的最近比赛列表。
        """
        from .match import Match
        from sqlalchemy import desc, or_

        return (
            session.query(Match)
            .filter(or_(Match.home_team_id == self.id, Match.away_team_id == self.id))
            .order_by(desc(Match.match_time))
            .limit(limit)
            .all()  # type: ignore
        )

    def get_home_record(self, session: Session) -> Dict[str, int]:
        """获取主场战绩。

        Args:
            session: 数据库会话对象。

        Returns:
            Dict[str, int]: 包含胜/平/负/总场次的字典。
                - wins: 胜场数
                - draws: 平局数
                - losses: 负场数
                - total: 总场次
        """
        from .match import Match

        home_matches = session.query(Match).filter(
            Match.home_team_id == self.id, Match.match_status == "finished"
        )

        wins = home_matches.filter(Match.home_score > Match.away_score).count()
        draws = home_matches.filter(Match.home_score == Match.away_score).count()
        losses = home_matches.filter(Match.home_score < Match.away_score).count()

        return {
            "wins": wins,
            "draws": draws,
            "losses": losses,
            "total": wins + draws + losses,
        }

    def get_away_record(self, session: Session) -> Dict[str, int]:
        """获取客场战绩。

        Args:
            session: 数据库会话对象。

        Returns:
            Dict[str, int]: 包含胜/平/负/总场次的字典。
                - wins: 胜场数
                - draws: 平局数
                - losses: 负场数
                - total: 总场次
        """
        from .match import Match

        away_matches = session.query(Match).filter(
            Match.away_team_id == self.id, Match.match_status == "finished"
        )

        wins = away_matches.filter(Match.away_score > Match.home_score).count()
        draws = away_matches.filter(Match.away_score == Match.home_score).count()
        losses = away_matches.filter(Match.away_score < Match.home_score).count()

        return {
            "wins": wins,
            "draws": draws,
            "losses": losses,
            "total": wins + draws + losses,
        }

    def get_season_stats(self, session: Session, season: str) -> Dict[str, int]:
        """获取指定赛季的统计数据。

        Args:
            session: 数据库会话对象。
            season: 赛季字符串标识。

        Returns:
            Dict[str, int]: 包含完整赛季统计的字典。
                - matches_played: 已踢场次
                - wins: 胜场数
                - draws: 平局数
                - losses: 负场数
                - goals_for: 进球数
                - goals_against: 失球数
                - points: 积分
                - goal_difference: 净胜球
        """
        from .match import Match
        from sqlalchemy import or_

        _matches = (
            session.query(Match)
            .filter(
                or_(Match.home_team_id == self.id, Match.away_team_id == self.id),
                Match.season == season,
                Match.match_status == "finished",
            )
            .all()  # type: ignore
        )

        _stats = {
            "matches_played": len(matches),
            "wins": 0,
            "draws": 0,
            "losses": 0,
            "goals_for": 0,
            "goals_against": 0,
        }

        for match in matches:
            if match.home_team_id == self.id:
                self._process_home_match(match, stats)
            else:
                self._process_away_match(match, stats)

        stats["points"] = stats["wins"] * 3 + stats["draws"]
        stats["goal_difference"] = stats["goals_for"] - stats["goals_against"]

        return stats

    def _process_home_match(self, match, stats: Dict[str, int]) -> None:
        """处理主场比赛统计。

        Args:
            match: 比赛对象。
            stats: 统计数据字典，将在原地修改。
        """
        stats["goals_for"] += match.home_score or 0
        stats["goals_against"] += match.away_score or 0

        if match.home_score > match.away_score:
            stats["wins"] += 1
        elif match.home_score == match.away_score:
            stats["draws"] += 1
        else:
            stats["losses"] += 1

    def _process_away_match(self, match, stats: Dict[str, int]) -> None:
        """处理客场比赛统计。

        Args:
            match: 比赛对象。
            stats: 统计数据字典，将在原地修改。
        """
        stats["goals_for"] += match.away_score or 0
        stats["goals_against"] += match.home_score or 0

        if match.away_score > match.home_score:
            stats["wins"] += 1
        elif match.away_score == match.home_score:
            stats["draws"] += 1
        else:
            stats["losses"] += 1

    @classmethod
    def get_by_code(cls, session: Session, team_code: str) -> Optional["Team"]:
        """根据球队代码获取球队。

        Args:
            session: 数据库会话对象。
            team_code: 球队代码。

        Returns:
            Optional[Team]: 匹配的球队对象，未找到则返回None。
        """
        return session.query(cls).filter(cls.team_code == team_code).first()  # type: ignore

    @classmethod
    def get_by_league(cls, session: Session, league_id: int) -> List["Team"]:
        """获取指定联赛的所有球队。

        Args:
            session: 数据库会话对象。
            league_id: 联赛ID。

        Returns:
            List[Team]: 该联赛下的所有球队列表。
        """
        return session.query(cls).filter(cls.league_id == league_id).all()  # type: ignore

    @classmethod
    def get_active_teams(cls, session: Session) -> List["Team"]:
        """获取所有活跃的球队。

        Args:
            session: 数据库会话对象。

        Returns:
            List[Team]: 所有活跃状态的球队列表。
        """
        return session.query(cls).filter(cls.is_active is True).all()  # type: ignore  # type: ignore
