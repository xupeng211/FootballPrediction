"""外部联赛数据模型
External League Data Model.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class ExternalLeague(Base):
    """外部联赛数据模型."""

    __tablename__ = "external_leagues"

    id = Column(Integer, primary_key=True, autoincrement=True)
    external_id = Column(
        String(50), unique=True, nullable=False, index=True, comment="外部API的联赛ID"
    )

    # 联赛基本信息
    name = Column(String(100), nullable=False, comment="联赛名称")
    code = Column(String(10), nullable=True, comment="联赛代码")
    typing.Type = Column(String(20), nullable=True, comment="联赛类型(LEAGUE/CUP)")
    emblem = Column(Text, nullable=True, comment="联赛标志URL")

    # 地理信息
    area_id = Column(Integer, nullable=True, comment="地区ID")
    area_name = Column(String(100), nullable=True, comment="地区名称")
    area_code = Column(String(3), nullable=True, comment="地区代码")
    area_flag = Column(Text, nullable=True, comment="地区旗帜URL")

    # 当前赛季信息
    current_season_id = Column(Integer, nullable=True, comment="当前赛季ID")
    current_season_start = Column(DateTime, nullable=True, comment="当前赛季开始时间")
    current_season_end = Column(DateTime, nullable=True, comment="当前赛季结束时间")
    current_matchday = Column(Integer, nullable=True, comment="当前轮次")
    season_winner = Column(JSON, nullable=True, comment="赛季冠军信息")

    # 元数据
    last_updated = Column(DateTime, nullable=True, comment="API最后更新时间")
    raw_data = Column(JSON, nullable=True, comment="原始API数据")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间"
    )

    # 状态标志
    is_processed = Column(Boolean, default=False, comment="是否已处理")
    is_active = Column(Boolean, default=True, comment="是否激活")
    is_supported = Column(Boolean, default=False, comment="是否为支持的联赛")
    data_quality_score = Column(Integer, default=0, comment="数据质量评分(0-100)")

    # 统计信息
    total_teams = Column(Integer, default=0, comment="总球队数")
    total_matches = Column(Integer, default=0, comment="总比赛数")
    last_sync_at = Column(DateTime, nullable=True, comment="最后同步时间")

    def __repr__(self):
        return f"<ExternalLeague(id={self.id}, external_id={self.external_id}, name={self.name})>"

    @property
    def display_name(self) -> str:
        """显示名称."""
        return self.name

    @property
    def is_current_season_active(self) -> bool:
        """当前赛季是否活跃."""
        if not self.current_season_start or not self.current_season_end:
            return False
        now = datetime.utcnow()
        return self.current_season_start <= now <= self.current_season_end

    @property
    def season_progress(self) -> float | None:
        """赛季进度百分比."""
        if (
            not self.current_season_start
            or not self.current_season_end
            or not self.current_matchday
        ):
            return None

        # 假设标准赛季有38轮（英超等）
        total_matchdays = 38
        progress = (self.current_matchday / total_matchdays) * 100
        return min(progress, 100.0)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "id": self.id,
            "external_id": self.external_id,
            "name": self.name,
            "code": self.code,
            "typing.Type": self.typing.Type,
            "emblem": self.emblem,
            "area_id": self.area_id,
            "area_name": self.area_name,
            "area_code": self.area_code,
            "area_flag": self.area_flag,
            "current_season_id": self.current_season_id,
            "current_season_start": (
                self.current_season_start.isoformat()
                if self.current_season_start
                else None
            ),
            "current_season_end": (
                self.current_season_end.isoformat() if self.current_season_end else None
            ),
            "current_matchday": self.current_matchday,
            "season_winner": self.season_winner,
            "last_updated": (
                self.last_updated.isoformat() if self.last_updated else None
            ),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "is_processed": self.is_processed,
            "is_active": self.is_active,
            "is_supported": self.is_supported,
            "data_quality_score": self.data_quality_score,
            "total_teams": self.total_teams,
            "total_matches": self.total_matches,
            "last_sync_at": (
                self.last_sync_at.isoformat() if self.last_sync_at else None
            ),
            "display_name": self.display_name,
            "is_current_season_active": self.is_current_season_active,
            "season_progress": self.season_progress,
        }

    @classmethod
    def from_api_data(
        cls, data: dict[str, Any], is_supported: bool = False
    ) -> "ExternalLeague":
        """从API数据创建实例."""
        try:
            # 解析地区信息
            area = data.get("area", {})

            # 解析赛季信息
            season = data.get("season", {})
            current_season_id = season.get("id")
            current_season_start = None
            current_season_end = None
            current_matchday = season.get("currentMatchday")
            season_winner = season.get("winner")

            # 解析赛季时间
            if season:
                start_date_str = season.get("startDate")
                end_date_str = season.get("endDate")
                if start_date_str:
                    try:
                        current_season_start = datetime.fromisoformat(
                            start_date_str.replace("Z", "+00:00")
                        )
                    except ValueError:
                        pass
                if end_date_str:
                    try:
                        current_season_end = datetime.fromisoformat(
                            end_date_str.replace("Z", "+00:00")
                        )
                    except ValueError:
                        pass

            # 解析最后更新时间
            last_updated = None
            last_updated_str = data.get("lastUpdated")
            if last_updated_str:
                try:
                    last_updated = datetime.fromisoformat(
                        last_updated_str.replace("Z", "+00:00")
                    )
                except ValueError:
                    pass

            # 计算数据质量评分
            quality_score = cls._calculate_data_quality_score(data)

            return cls(
                external_id=str(data.get("id")),
                name=data.get("name"),
                code=data.get("code"),
                typing.Type=data.get("typing.Type"),
                emblem=data.get("emblem"),
                area_id=area.get("id"),
                area_name=area.get("name"),
                area_code=area.get("code"),
                area_flag=area.get("flag"),
                current_season_id=current_season_id,
                current_season_start=current_season_start,
                current_season_end=current_season_end,
                current_matchday=current_matchday,
                season_winner=season_winner,
                last_updated=last_updated,
                raw_data=data,
                is_supported=is_supported,
                data_quality_score=quality_score,
            )

        except Exception as e:
            # 创建错误记录
            return cls(
                external_id=str(data.get("id", "")),
                name=data.get("name", "Unknown League"),
                raw_data={"error": str(e), "original_data": data},
                data_quality_score=0,
            )

    @staticmethod
    def _calculate_data_quality_score(data: dict[str, Any]) -> int:
        """计算数据质量评分."""
        score = 0

        # 基础信息 (40分)
        basic_fields = ["name", "code", "typing.Type", "emblem"]
        score += sum(10 for field in basic_fields if data.get(field))

        # 地理信息 (20分)
        if data.get("area") and isinstance(data["area"], dict):
            area_data = data["area"]
            area_keys = ["id", "name", "code", "flag"]
            score += sum(5 for key in area_keys if area_data.get(key))

        # 赛季信息 (30分)
        if data.get("season") and isinstance(data["season"], dict):
            season_data = data["season"]
            season_keys = ["id", "startDate", "endDate", "currentMatchday"]
            score += sum(7.5 for key in season_keys if season_data.get(key))

        # 更新时间 (10分)
        if data.get("lastUpdated"):
            score += 10

        return min(int(score), 100)  # 最高100分

    def update_from_api_data(self, data: dict[str, Any]) -> bool:
        """从API数据更新实例."""
        try:
            # 检查外部ID是否匹配
            if str(data.get("id")) != self.external_id:
                return False

            # 更新基础信息
            self.name = data.get("name", self.name)
            self.code = data.get("code", self.code)
            self.typing.Type = data.get("typing.Type", self.typing.Type)
            self.emblem = data.get("emblem", self.emblem)

            # 更新地理信息
            area = data.get("area", {})
            if area:
                self.area_id = area.get("id", self.area_id)
                self.area_name = area.get("name", self.area_name)
                self.area_code = area.get("code", self.area_code)
                self.area_flag = area.get("flag", self.area_flag)

            # 更新赛季信息
            season = data.get("season", {})
            if season:
                self.current_season_id = season.get("id", self.current_season_id)
                self.current_matchday = season.get(
                    "currentMatchday", self.current_matchday
                )
                self.season_winner = season.get("winner", self.season_winner)

                # 更新赛季时间
                start_date_str = season.get("startDate")
                end_date_str = season.get("endDate")
                if start_date_str:
                    try:
                        self.current_season_start = datetime.fromisoformat(
                            start_date_str.replace("Z", "+00:00")
                        )
                    except ValueError:
                        pass
                if end_date_str:
                    try:
                        self.current_season_end = datetime.fromisoformat(
                            end_date_str.replace("Z", "+00:00")
                        )
                    except ValueError:
                        pass

            # 更新元数据
            self.raw_data = data
            self.data_quality_score = self._calculate_data_quality_score(data)

            # 更新最后更新时间
            last_updated_str = data.get("lastUpdated")
            if last_updated_str:
                try:
                    self.last_updated = datetime.fromisoformat(
                        last_updated_str.replace("Z", "+00:00")
                    )
                except ValueError:
                    pass

            self.updated_at = datetime.utcnow()
            return True

        except Exception as e:
            # 记录错误但不抛出异常
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Error updating league {self.external_id}: {e}")
            return False

    def update_statistics(
        self, total_teams: int = None, total_matches: int = None
    ) -> None:
        """更新统计信息."""
        if total_teams is not None:
            self.total_teams = total_teams
        if total_matches is not None:
            self.total_matches = total_matches
        self.last_sync_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def mark_as_processed(self) -> None:
        """标记为已处理."""
        self.is_processed = True
        self.updated_at = datetime.utcnow()

    def activate_support(self) -> None:
        """激活支持."""
        self.is_supported = True
        self.updated_at = datetime.utcnow()

    def deactivate_support(self) -> None:
        """取消支持."""
        self.is_supported = False
        self.updated_at = datetime.utcnow()


# 联赛积分榜模型
class ExternalLeagueStandings(Base):
    """外部联赛积分榜模型."""

    __tablename__ = "external_league_standings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    league_id = Column(
        Integer, ForeignKey("external_leagues.id"), nullable=False, comment="联赛ID"
    )
    external_league_id = Column(String(50), nullable=False, comment="外部联赛ID")

    # 积分榜信息
    position = Column(Integer, nullable=False, comment="排名")
    team_id = Column(Integer, nullable=False, comment="球队ID")
    team_external_id = Column(String(50), nullable=False, comment="球队外部ID")
    team_name = Column(String(100), nullable=False, comment="球队名称")
    team_short_name = Column(String(50), nullable=True, comment="球队简称")
    team_crest = Column(Text, nullable=True, comment="球队队徽")
    team_tla = Column(String(3), nullable=True, comment="球队三字母代码")

    # 比赛统计
    played_games = Column(Integer, default=0, comment="已比赛数")
    won = Column(Integer, default=0, comment="胜场数")
    draw = Column(Integer, default=0, comment="平局数")
    lost = Column(Integer, default=0, comment="负场数")

    # 进球统计
    goals_for = Column(Integer, default=0, comment="进球数")
    goals_against = Column(Integer, default=0, comment="失球数")
    goal_difference = Column(Integer, default=0, comment="净胜球")
    points = Column(Integer, default=0, comment="积分")

    # 分组信息
    group = Column(String(10), nullable=True, comment="分组")
    stage = Column(String(50), nullable=True, comment="阶段")
    table_type = Column(String(20), default="TOTAL", comment="积分榜类型")

    # 状态信息
    form = Column(String(20), nullable=True, comment="近期战绩")
    status = Column(String(20), default="active", comment="状态")

    # 元数据
    last_updated = Column(DateTime, nullable=True, comment="最后更新时间")
    raw_data = Column(JSON, nullable=True, comment="原始API数据")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间"
    )

    # 关联关系
    league = relationship("ExternalLeague", backref="standings")

    def __repr__(self):
        return f"<ExternalLeagueStandings(league_id={self.league_id}, position={self.position}, team={self.team_name})>"

    @property
    def display_record(self) -> str:
        """显示战绩."""
        return f"{self.won}胜{self.draw}平{self.lost}负"

    @property
    def goal_record(self) -> str:
        """显示进球记录."""
        return f"{self.goals_for}:{self.goals_against}"

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "id": self.id,
            "league_id": self.league_id,
            "external_league_id": self.external_league_id,
            "position": self.position,
            "team_id": self.team_id,
            "team_external_id": self.team_external_id,
            "team_name": self.team_name,
            "team_short_name": self.team_short_name,
            "team_crest": self.team_crest,
            "team_tla": self.team_tla,
            "played_games": self.played_games,
            "won": self.won,
            "draw": self.draw,
            "lost": self.lost,
            "goals_for": self.goals_for,
            "goals_against": self.goals_against,
            "goal_difference": self.goal_difference,
            "points": self.points,
            "group": self.group,
            "stage": self.stage,
            "table_type": self.table_type,
            "form": self.form,
            "status": self.status,
            "last_updated": (
                self.last_updated.isoformat() if self.last_updated else None
            ),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "display_record": self.display_record,
            "goal_record": self.goal_record,
        }

    @classmethod
    def from_api_data(
        cls, data: dict[str, Any], league_id: int, external_league_id: str
    ) -> "ExternalLeagueStandings":
        """从API数据创建实例."""
        try:
            team = data.get("team", {})

            return cls(
                league_id=league_id,
                external_league_id=external_league_id,
                team_id=team.get("id"),
                team_external_id=str(team.get("id")),
                team_name=team.get("name"),
                team_short_name=team.get("shortName"),
                team_crest=team.get("crest"),
                team_tla=team.get("tla"),
                played_games=data.get("playedGames", 0),
                won=data.get("won", 0),
                draw=data.get("draw", 0),
                lost=data.get("lost", 0),
                goals_for=data.get("goalsFor", 0),
                goals_against=data.get("goalsAgainst", 0),
                goal_difference=data.get("goalDifference", 0),
                points=data.get("points", 0),
                form=data.get("form"),
                group=data.get("group"),
                stage=data.get("stage"),
                table_type=data.get("typing.Type", "TOTAL"),
                raw_data=data,
            )

        except Exception as e:
            # 创建错误记录
            team = data.get("team", {})
            return cls(
                league_id=league_id,
                external_league_id=external_league_id,
                team_external_id=str(team.get("id", "")),
                team_name=team.get("name", "Unknown Team"),
                raw_data={"error": str(e), "original_data": data},
            )
