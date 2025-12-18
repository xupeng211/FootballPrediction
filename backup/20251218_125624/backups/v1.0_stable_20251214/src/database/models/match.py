"""Match - 数据库模块.

提供 match 相关的数据库功能.

主要功能：
- [待补充 - Match的主要功能]

使用示例:
    from database.models import Match
    # 使用示例代码

注意事项:
- [待补充 - 使用注意事项]
"""

from enum import Enum

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, JSON, Float
from sqlalchemy.orm import relationship
from datetime import datetime

from src.database.base import BaseModel

"""
比赛模型

存储足球比赛的详细信息,包括比赛时间,比分,状态等.
"""


class MatchStatus(Enum):
    """比赛状态枚举."""

    SCHEDULED = "scheduled"  # 已安排
    LIVE = "live"  # 进行中
    FINISHED = "finished"  # 已结束
    CANCELLED = "cancelled"  # 已取消


class MatchResult(Enum):
    """比赛结果枚举."""

    HOME_WIN = "home_win"  # 主队获胜
    AWAY_WIN = "away_win"  # 客队获胜
    DRAW = "draw"  # 平局


class Match(BaseModel):
    __table_args__ = {"extend_existing": True}
    __tablename__ = "matches"

    # 基本字段
    id = Column(Integer, primary_key=True)
    fotmob_id = Column(String(50), nullable=True, index=True)  # FotMob外部ID
    home_team_id = Column(
        Integer, ForeignKey("teams.id"), nullable=True
    )  # 修复: 允许NULL，Team记录可异步补齐
    away_team_id = Column(
        Integer, ForeignKey("teams.id"), nullable=True
    )  # 修复: 允许NULL，Team记录可异步补齐
    home_score = Column(Integer, default=0)
    away_score = Column(Integer, default=0)

    # DAO层需要的字段
    home_team_name = Column(String(100), nullable=True)  # 主队名称 (用于DAO层)
    away_team_name = Column(String(100), nullable=True)  # 客队名称 (用于DAO层)
    match_time = Column(
        DateTime, nullable=True, comment="比赛时间 (允许NULL，支持TBD/Postponed比赛)"
    )  # 比赛时间

    # 保持向后兼容的字段
    status = Column(String(20), default="scheduled")
    match_date = Column(
        DateTime, nullable=True, comment="比赛日期 (允许NULL，支持TBD/Postponed比赛)"
    )
    venue = Column(String(255))
    league_id = Column(Integer, ForeignKey("leagues.id"))
    season = Column(String(20))

    # 时间戳字段
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True)

    # 🚀 V2深度数据字段 - 全栈架构师升级
    # 使用JSON类型存储复杂数据结构
    lineups = Column(JSON, nullable=True)  # 阵容数据 (首发+替补)
    stats = Column(JSON, nullable=True)  # 技术统计 (控球率、射门等)
    events = Column(JSON, nullable=True)  # 比赛事件 (进球、红黄牌、换人)
    odds = Column(JSON, nullable=True)  # 赔率信息
    match_metadata = Column(JSON, nullable=True)  # 其他元数据 (xG、rating等)

    # 🔥 Greedy Mode 新增字段 - 全量数据采集
    # 专门的JSON字段存储结构化数据，避免混合存储
    stats_json = Column(
        JSON, nullable=True, comment="全量技术统计 (matchStats原始数据)"
    )
    lineups_json = Column(JSON, nullable=True, comment="完整阵容数据 (包含评分、伤停)")
    odds_snapshot_json = Column(JSON, nullable=True, comment="赔率快照数据")
    match_info = Column(JSON, nullable=True, comment="战意上下文 (排名、轮次等)")

    # 🌟 Super Greedy Mode 新增字段 - 环境暗物质采集
    # 捕获裁判、场地、天气、主帅等环境因素
    environment_json = Column(
        JSON, nullable=True, comment="环境暗物质 (裁判、场地、天气、主帅、阵型)"
    )

    # 🎯 高级统计字段 - P2-3.1 数据库结构修复
    # 期望进球数 (Expected Goals)
    home_xg = Column(Float, nullable=True, comment="主场期望进球数")
    away_xg = Column(Float, nullable=True, comment="客场期望进球数")

    # 控球率 (Possession %)
    home_possession = Column(Float, nullable=True, comment="主场控球率 (%)")
    away_possession = Column(Float, nullable=True, comment="客场控球率 (%)")

    # 射门数据
    home_shots = Column(Integer, nullable=True, comment="主场射门数")
    away_shots = Column(Integer, nullable=True, comment="客场射门数")
    home_shots_on_target = Column(Integer, nullable=True, comment="主场射正数")
    away_shots_on_target = Column(Integer, nullable=True, comment="客场射正数")

    # 角球和犯规
    home_corners = Column(Integer, nullable=True, comment="主场角球数")
    away_corners = Column(Integer, nullable=True, comment="客场角球数")
    home_fouls = Column(Integer, nullable=True, comment="主场犯规数")
    away_fouls = Column(Integer, nullable=True, comment="客场犯规数")

    # 黄牌和红牌
    home_yellow_cards = Column(Integer, nullable=True, comment="主场黄牌数")
    away_yellow_cards = Column(Integer, nullable=True, comment="客场黄牌数")
    home_red_cards = Column(Integer, nullable=True, comment="主场红牌数")
    away_red_cards = Column(Integer, nullable=True, comment="客场红牌数")

    # 传球统计
    home_passes = Column(Integer, nullable=True, comment="主场传球数")
    away_passes = Column(Integer, nullable=True, comment="客场传球数")
    home_pass_accuracy = Column(Float, nullable=True, comment="主场传球成功率 (%)")
    away_pass_accuracy = Column(Float, nullable=True, comment="客场传球成功率 (%)")

    # 数据来源和质量追踪
    data_source = Column(String(50), default="fotmob_v2")  # 数据来源标识
    data_completeness = Column(
        String(20), default="partial"
    )  # 数据完整度 (partial/detailed/complete)
    collection_time = Column(DateTime, nullable=True)  # 数据采集时间

    # 关系
    home_team = relationship("Team", foreign_keys=[home_team_id])
    away_team = relationship("Team", foreign_keys=[away_team_id])
    league = relationship("League", foreign_keys=[league_id])
    features = relationship("Features", back_populates="match")

    def __repr__(self):
        return f"<Match(id={self.id}, home_team_id={self.home_team_id}, away_team_id={self.away_team_id})>"
