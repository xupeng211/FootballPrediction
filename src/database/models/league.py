from sqlalchemy import Boolean, Column, Index, Integer, String
from sqlalchemy.orm import relationship

"""
联赛模型

存储足球联赛的基础信息，如英超、西甲等。
"""

from sqlalchemy import Column, Integer, String
from ..base import BaseModel
from sqlalchemy import Boolean
from sqlalchemy import Index
from sqlalchemy import Integer
from sqlalchemy import String


class League(BaseModel):
    """
    联赛表模型

    对应 architecture.md 中的 leagues 表设计
    """

    __tablename__ = "leagues"

    # 基础信息字段
    league_name = Column(String(100), nullable=False, comment="联赛名称")

    league_code = Column(String(20), unique=True, nullable=True, comment="联赛代码")

    country = Column(String(50), nullable=True, comment="所属国家")

    level = Column(
        Integer, nullable=True, comment="联赛级别（1=顶级联赛，2=二级联赛等）"
    )

    # API相关字段
    api_league_id = Column(Integer, unique=True, nullable=True, comment="API联赛ID")

    # 赛季信息
    season_start_month = Column(Integer, nullable=True, comment="赛季开始月份（1-12）")

    season_end_month = Column(Integer, nullable=True, comment="赛季结束月份（1-12）")

    # 状态字段
    is_active = Column(Boolean, default=True, nullable=False, comment="是否活跃")

    # 关系定义
    teams = relationship(
        "Team", back_populates="league", lazy="dynamic", cascade="all, delete-orphan"
    )

    matches = relationship("Match", back_populates="league", lazy="dynamic")

    # 索引定义
    __table_args__ = (
        Index("idx_leagues_country", "country"),
        Index("idx_leagues_active", "is_active"),
        Index("idx_leagues_level", "level"),
    )

    def __repr__(self) -> str:
        return f"<League(id={self.id}, name='{self.league_name}', country='{self.country}')>"

    @property
    def display_name(self) -> str:
        """返回用于显示的联赛名称"""
        if self.country:
            return f"{str(self.league_name)} ({self.country})"
        return str(self.league_name)

    @property
    def is_top_league(self) -> bool:
        """判断是否为顶级联赛"""
        return bool(self.level == 1 if self.level is not None else False)

    def get_active_teams_count(self) -> int:
        """获取当前活跃球队数量"""
        return self.teams.filter_by(is_active=True).count()  # type: ignore

    @classmethod
    def get_by_code(cls, session, league_code: str):
        """根据联赛代码获取联赛"""
        return session.query(cls).filter(cls.league_code == league_code).first()

    @classmethod
    def get_by_country(cls, session, country: str):
        """获取指定国家的所有联赛"""
        return session.query(cls).filter(cls.country == country).all()

    @classmethod
    def get_active_leagues(cls, session):
        """获取所有活跃的联赛"""
        return session.query(cls).filter(cls.is_active is True).all()
