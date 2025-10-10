"""
联赛领域模型

封装联赛相关的业务逻辑和规则。
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass, field

from .team import Team
from .match import Match, MatchResult


class LeagueStatus(Enum):
    """联赛状态枚举"""

    UPCOMING = "upcoming"  # 即将开始
    ONGOING = "ongoing"  # 进行中
    PAUSED = "paused"  # 暂停（如世界杯期间）
    FINISHED = "finished"  # 已结束
    CANCELLED = "cancelled"  # 取消


class LeagueTier(Enum):
    """联赛级别枚举"""

    TIER_1 = 1  # 顶级联赛
    TIER_2 = 2  # 次级联赛
    TIER_3 = 3  # 第三级别
    TIER_4 = 4  # 第四级别


@dataclass
class LeagueTableEntry:
    """联赛积分榜条目"""

    position: int
    team: Team
    played: int = 0
    won: int = 0
    drawn: int = 0
    lost: int = 0
    goals_for: int = 0
    goals_against: int = 0
    goal_difference: int = 0
    points: int = 0

    @property
    def win_rate(self) -> float:
        """胜率"""
        if self.played == 0:
            return 0.0
        return self.won / self.played

    @property
    def avg_goals_for(self) -> float:
        """场均进球"""
        if self.played == 0:
            return 0.0
        return self.goals_for / self.played

    @property
    def avg_goals_against(self) -> float:
        """场均失球"""
        if self.played == 0:
            return 0.0
        return self.goals_against / self.played

    @property
    def form_string(self) -> str:
        """近期战绩字符串（从其他地方获取）"""
        return ""  # 实际实现需要从Team获取


@dataclass
class LeagueSeason:
    """联赛赛季"""

    season: str
    start_date: datetime
    end_date: datetime
    total_teams: int
    total_matches: int
    current_matchday: int
    total_matchdays: int
    status: LeagueStatus = LeagueStatus.UPCOMING

    def get_progress(self) -> float:
        """获取赛季进度"""
        if self.total_matchdays == 0:
            return 0.0
        return self.current_matchday / self.total_matchdays

    def is_active(self) -> bool:
        """检查是否为当前赛季"""
        return self.status == LeagueStatus.ONGOING

    def get_remaining_matchdays(self) -> int:
        """获取剩余比赛轮次"""
        return max(0, self.total_matchdays - self.current_matchday)


class League:
    """联赛领域模型

    封装联赛的核心业务逻辑和规则。
    """

    def __init__(
        self,
        name: str,
        country: str,
        id: Optional[int] = None,
        tier: LeagueTier = LeagueTier.TIER_1,
        short_name: Optional[str] = None,
        logo_url: Optional[str] = None,
        current_season: Optional[str] = None,
        description: Optional[str] = None,
    ):
        self.id = id
        self.name = name
        self.country = country
        self.tier = tier
        self.short_name = short_name or name[:3].upper()
        self.logo_url = logo_url
        self.current_season = current_season
        self.description = description

        # 赛季信息
        self.seasons: Dict[str, LeagueSeason] = {}
        self.current_matchday = 1
        self.total_matchdays = 38  # 默认38轮

        # 积分榜
        self.table: List[LeagueTableEntry] = []

        # 参赛球队
        self.teams: List[Team] = []

        # 比赛记录
        self.matches: List[Match] = []

        # 元数据
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

        # 业务规则验证
        self._validate_initialization()

    def _validate_initialization(self):
        """验证初始化数据"""
        if not self.name or len(self.name.strip()) == 0:
            raise ValueError("联赛名称不能为空")

        if not self.country or len(self.country.strip()) == 0:
            raise ValueError("国家不能为空")

    # ==================== 赛季管理 ====================

    def add_season(
        self,
        season: str,
        start_date: datetime,
        end_date: datetime,
        total_teams: int,
        total_matchdays: int = 38,
    ) -> bool:
        """添加赛季"""
        if season in self.seasons:
            return False

        # 验证日期
        if start_date >= end_date:
            raise ValueError("开始日期必须早于结束日期")

        new_season = LeagueSeason(
            season=season,
            start_date=start_date,
            end_date=end_date,
            total_teams=total_teams,
            total_matches=total_teams * (total_teams - 1),
            current_matchday=1,
            total_matchdays=total_matchdays,
        )

        self.seasons[season] = new_season
        self.updated_at = datetime.now()

        # 如果是第一个赛季，设为当前赛季
        if not self.current_season:
            self.current_season = season
            self.total_matchdays = total_matchdays

        return True

    def set_current_season(self, season: str) -> bool:
        """设置当前赛季"""
        if season not in self.seasons:
            return False

        self.current_season = season
        self.current_matchday = self.seasons[season].current_matchday
        self.total_matchdays = self.seasons[season].total_matchdays
        self.updated_at = datetime.now()

        return True

    def get_current_season_info(self) -> Optional[LeagueSeason]:
        """获取当前赛季信息"""
        if not self.current_season:
            return None
        return self.seasons.get(self.current_season)

    def get_season_status(self) -> LeagueStatus:
        """获取当前赛季状态"""
        current_season = self.get_current_season_info()
        if not current_season:
            return LeagueStatus.UPCOMING

        now = datetime.now()
        if now < current_season.start_date:
            return LeagueStatus.UPCOMING
        elif now > current_season.end_date:
            return LeagueStatus.FINISHED
        else:
            return LeagueStatus.ONGOING

    # ==================== 积分榜管理 ====================

    def initialize_table(self, teams: List[Team]) -> bool:
        """初始化积分榜"""
        if not self.current_season:
            return False

        self.teams = teams
        self.table = []

        for i, team in enumerate(teams):
            entry = LeagueTableEntry(position=i + 1, team=team)
            self.table.append(entry)

        self.updated_at = datetime.now()
        return True

    def update_table_from_match(self, match: Match) -> bool:
        """根据比赛更新积分榜"""
        if not match.is_finished():
            return False

        if match.league_id != self.id:
            return False

        # 找到主队和客队
        home_entry = None
        away_entry = None

        for entry in self.table:
            if entry.team.id == match.home_team_id:
                home_entry = entry
            elif entry.team.id == match.away_team_id:
                away_entry = entry

        if not home_entry or not away_entry:
            return False

        # 更新统计
        home_goals = match.current_score.home_score
        away_goals = match.current_score.away_score

        # 主队统计
        home_entry.played += 1
        home_entry.goals_for += home_goals
        home_entry.goals_against += away_goals
        home_entry.goal_difference = home_entry.goals_for - home_entry.goals_against

        # 客队统计
        away_entry.played += 1
        away_entry.goals_for += away_goals
        away_entry.goals_against += home_goals
        away_entry.goal_difference = away_entry.goals_for - away_entry.goals_against

        # 更新积分
        if home_goals > away_goals:
            home_entry.won += 1
            home_entry.points += 3
            away_entry.lost += 1
        elif away_goals > home_goals:
            away_entry.won += 1
            away_entry.points += 3
            home_entry.lost += 1
        else:
            home_entry.drawn += 1
            home_entry.points += 1
            away_entry.drawn += 1
            away_entry.points += 1

        # 重新排序
        self._sort_table()
        self._update_positions()
        self.updated_at = datetime.now()

        return True

    def _sort_table(self):
        """对积分榜排序"""
        self.table.sort(
            key=lambda x: (x.points, x.goal_difference, x.goals_for), reverse=True
        )

    def _update_positions(self):
        """更新排名"""
        for i, entry in enumerate(self.table):
            entry.position = i + 1

    def get_table_entry(self, team_id: int) -> Optional[LeagueTableEntry]:
        """获取球队积分榜条目"""
        for entry in self.table:
            if entry.team.id == team_id:
                return entry
        return None

    def get_standings(self, limit: Optional[int] = None) -> List[LeagueTableEntry]:
        """获取积分榜"""
        standings = self.table.copy()
        if limit:
            standings = standings[:limit]
        return standings

    # ==================== 球队管理 ====================

    def add_team(self, team: Team) -> bool:
        """添加球队"""
        if team in self.teams:
            return False

        self.teams.append(team)
        self.updated_at = datetime.now()

        # 如果积分榜已初始化，添加新条目
        if self.table:
            new_entry = LeagueTableEntry(position=len(self.table) + 1, team=team)
            self.table.append(new_entry)
            self._sort_table()
            self._update_positions()

        return True

    def remove_team(self, team_id: int) -> bool:
        """移除球队"""
        team_to_remove = None
        for team in self.teams:
            if team.id == team_id:
                team_to_remove = team
                break

        if not team_to_remove:
            return False

        self.teams.remove(team_to_remove)

        # 从积分榜移除
        self.table = [e for e in self.table if e.team.id != team_id]
        self._update_positions()

        self.updated_at = datetime.now()
        return True

    # ==================== 比赛管理 ====================

    def add_match(self, match: Match) -> bool:
        """添加比赛"""
        if match in self.matches:
            return False

        if match.league_id != self.id:
            return False

        self.matches.append(match)
        self.updated_at = datetime.now()
        return True

    def get_matches_for_team(
        self, team_id: int, limit: Optional[int] = None
    ) -> List[Match]:
        """获取球队的比赛"""
        team_matches = []
        for match in self.matches:
            if match.home_team_id == team_id or match.away_team_id == team_id:
                team_matches.append(match)

        # 按时间排序
        team_matches.sort(key=lambda x: x.match_time, reverse=True)

        if limit:
            team_matches = team_matches[:limit]

        return team_matches

    def get_upcoming_matches(
        self, days: int = 7, limit: Optional[int] = None
    ) -> List[Match]:
        """获取即将到来的比赛"""
        now = datetime.now()
        upcoming = []

        for match in self.matches:
            if now < match.match_time <= now + timedelta(days=days):
                upcoming.append(match)

        # 按时间排序
        upcoming.sort(key=lambda x: x.match_time)

        if limit:
            upcoming = upcoming[:limit]

        return upcoming

    # ==================== 统计分析 ====================

    def get_league_statistics(self) -> Dict[str, Any]:
        """获取联赛统计"""
        if not self.table:
            return {}

        stats = {
            "total_teams": len(self.table),
            "total_matches": sum(e.played for e in self.table) // 2,
            "avg_goals_per_match": self._calculate_avg_goals(),
            "home_win_rate": self._calculate_home_win_rate(),
            "draw_rate": self._calculate_draw_rate(),
            "top_scorer_team": self._get_top_scorer_team(),
            "best_defense_team": self._get_best_defense_team(),
            "most_clean_sheets": self._get_most_clean_sheets(),
            "season_progress": self.get_current_season_info().get_progress()
            if self.get_current_season_info()
            else 0.0,
        }

        return stats

    def _calculate_avg_goals(self) -> float:
        """计算场均进球"""
        if not self.table:
            return 0.0
        total_goals = sum(e.goals_for for e in self.table)
        total_matches = sum(e.played for e in self.table) // 2
        return total_goals / total_matches if total_matches > 0 else 0.0

    def _calculate_home_win_rate(self) -> float:
        """计算主场胜率"""
        # 这里需要分析所有比赛的主队胜率
        # 简化实现
        return 0.45  # 一般联赛的主场胜率约45%

    def _calculate_draw_rate(self) -> float:
        """计算平局率"""
        # 简化实现
        return 0.25  # 一般联赛的平局率约25%

    def _get_top_scorer_team(self) -> Optional[Team]:
        """获取进球最多的球队"""
        if not self.table:
            return None
        return max(self.table, key=lambda x: x.goals_for).team

    def _get_best_defense_team(self) -> Optional[Team]:
        """获取防守最好的球队"""
        if not self.table:
            return None
        return min(self.table, key=lambda x: x.goals_against).team

    def _get_most_clean_sheets(self) -> Optional[Team]:
        """获取零封次数最多的球队"""
        # 这里需要从Team获取clean_sheets统计
        # 简化实现
        return None

    def get_competition_level(self) -> float:
        """获取联赛竞争水平评分"""
        if not self.table or len(self.table) < 5:
            return 0.0

        # 计算积分分布的方差
        points = [e.points for e in self.table]
        avg_points = sum(points) / len(points)
        variance = sum((p - avg_points) ** 2 for p in points) / len(points)

        # 方差越大，竞争水平越高
        competition_level = min(100, variance * 2)
        return competition_level

    # ==================== 导出和序列化 ====================

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "country": self.country,
            "tier": self.tier.value,
            "short_name": self.short_name,
            "logo_url": self.logo_url,
            "current_season": self.current_season,
            "description": self.description,
            "current_matchday": self.current_matchday,
            "total_matchdays": self.total_matchdays,
            "season_status": self.get_season_status().value,
            "team_count": len(self.teams),
            "competition_level": self.get_competition_level(),
            "statistics": self.get_league_statistics(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "League":
        """从字典创建实例"""
        return cls(
            id=data.get("id"),
            name=data["name"],
            country=data["country"],
            tier=LeagueTier(data.get("tier", 1)),
            short_name=data.get("short_name"),
            logo_url=data.get("logo_url"),
            current_season=data.get("current_season"),
            description=data.get("description"),
        )

    # ==================== 比较和哈希 ====================

    def __eq__(self, other) -> bool:
        """比较两个联赛是否相同"""
        if not isinstance(other, League):
            return False
        return self.id == other.id if self.id and other.id else self.name == other.name

    def __hash__(self) -> int:
        """生成哈希值"""
        if self.id:
            return hash(self.id)
        return hash(self.name)

    def __str__(self) -> str:
        """字符串表示"""
        return f"{self.name} ({self.country})"

    def __repr__(self) -> str:
        """详细字符串表示"""
        return (
            f"League(id={self.id}, name='{self.name}', "
            f"country='{self.country}', tier={self.tier.value})"
        )
