"""
球队模型

存储足球队伍的基础信息，如曼联、巴塞罗那等。
"""

from sqlalchemy import Boolean, Column, ForeignKey, Index, Integer, String
from sqlalchemy.orm import relationship

from ..base import BaseModel


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
    def display_name(self) -> str:
        """返回用于显示的球队名称"""
        if self.country and hasattr(self, "league") and self.league:
            return f"{self.team_name} ({self.league.league_name})"
        return str(self.team_name)

    def get_all_matches(self):
        """获取所有比赛（主场+客场）"""
        # 这需要在调用时传入session
        return None  # 实际使用时需要session参数

    def get_recent_matches(self, session, limit: int = 5):
        """获取最近的比赛"""
        from sqlalchemy import desc, or_

        from .match import Match

        return (
            session.query(Match)
            .filter(
                or_(  # type: ignore
                    Match.home_team_id == self.id, Match.away_team_id == self.id
                )
            )
            .order_by(desc(Match.match_time))
            .limit(limit)
            .all()
        )  # type: ignore

    def get_home_record(self, session):
        """获取主场战绩"""
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

    def get_away_record(self, session):
        """获取客场战绩"""
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

    def get_season_stats(self, session, season: str):
        """获取指定赛季的统计数据"""
        from sqlalchemy import or_

        from .match import Match

        matches = (
            session.query(Match)
            .filter(
                or_(  # type: ignore
                    Match.home_team_id == self.id, Match.away_team_id == self.id
                ),
                Match.season == season,
                Match.match_status == "finished",
            )
            .all()
        )

        stats = {
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

    def _process_home_match(self, match, stats: dict):
        """处理主场比赛统计"""
        stats["goals_for"] += match.home_score or 0
        stats["goals_against"] += match.away_score or 0

        if match.home_score > match.away_score:
            stats["wins"] += 1
        elif match.home_score == match.away_score:
            stats["draws"] += 1
        else:
            stats["losses"] += 1

    def _process_away_match(self, match, stats: dict):
        """处理客场比赛统计"""
        stats["goals_for"] += match.away_score or 0
        stats["goals_against"] += match.home_score or 0

        if match.away_score > match.home_score:
            stats["wins"] += 1
        elif match.away_score == match.home_score:
            stats["draws"] += 1
        else:
            stats["losses"] += 1

    @classmethod
    def get_by_code(cls, session, team_code: str):
        """根据球队代码获取球队"""
        return session.query(cls).filter(cls.team_code == team_code).first()

    @classmethod
    def get_by_league(cls, session, league_id: int):
        """获取指定联赛的所有球队"""
        return session.query(cls).filter(cls.league_id == league_id).all()

    @classmethod
    def get_active_teams(cls, session):
        """获取所有活跃的球队"""
        return session.query(cls).filter(cls.is_active is True).all()
