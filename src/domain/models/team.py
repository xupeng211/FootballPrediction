"""
球队领域模型
Team Domain Model

封装球队相关的业务逻辑和不变性约束.
Encapsulates team-related business logic and invariants.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from src.core.exceptions import DomainError


class TeamType(Enum):
    """球队类型"""

    CLUB = "club"  # 俱乐部
    NATIONAL = "national"  # 国家队


@dataclass
class TeamStats:
    """类文档字符串"""
    pass  # 添加pass语句
    """球队统计值对象"""

    matches_played: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0
    goals_for: int = 0
    goals_against: int = 0

    def __post_init__(self):
        """验证统计数据"""
        if any(
            x < 0
            for x in [
                self.matches_played,
                self.wins,
                self.draws,
                self.losses,
                self.goals_for,
                self.goals_against,
            ]
        ):
            raise DomainError("统计数据不能为负数")

        # 验证比赛场次
        total = self.wins + self.draws + self.losses
        if total > self.matches_played:
            raise DomainError("胜负平场次之和不能大于总比赛场次")

    @property
    def points(self) -> int:
        """积分（标准足球积分:胜3平1负0）"""
        return self.wins * 3 + self.draws

    @property
    def goal_difference(self) -> int:
        """净胜球"""
        return self.goals_for - self.goals_against

    @property
    def win_rate(self) -> float:
        """胜率"""
        if self.matches_played == 0:
            return 0.0
        return self.wins / self.matches_played

    @property
    def form(self) -> List[str]:
        """最近状态（简化表示）"""
        # 这里应该从历史记录计算,简化处理
        return []

    def update(self, result: str, goals_for: int, goals_against: int) -> None:
        """更新统计数据"""
        self.matches_played += 1
        self.goals_for += goals_for
        self.goals_against += goals_against

        if result == "win":
            self.wins += 1
        elif result == "draw":
            self.draws += 1
        elif result == "loss":
            self.losses += 1

    def __str__(self) -> str:
        return f"{self.matches_played}场 {self.wins}胜 {self.draws}平 {self.losses}负"


@dataclass
class TeamForm:
    """类文档字符串"""
    pass  # 添加pass语句
    """球队状态值对象"""

    last_matches: List[str] = field(default_factory=list)  # 最近比赛结果:W/D/L
    current_streak: int = 0  # 当前连续纪录（胜/负为正数,平为0）
    streak_type: str = ""  # 连续类型:win/draw/loss/none

    def __post_init__(self):
        """函数文档字符串"""
        pass
  # 添加pass语句
        """验证状态数据"""
        if len(self.last_matches) > 10:
            raise DomainError("最近比赛记录最多保留10场")

        for result in self.last_matches:
            if result not in ["W", "D", "L"]:
                raise DomainError("比赛结果只能是 W/D/L")

    def add_result(self, result: str) -> None:
        """添加比赛结果"""
        if result not in ["W", "D", "L"]:
            raise DomainError("比赛结果只能是 W/D/L")

        # 添加到记录开头,保留最近10场
        self.last_matches.insert(0, result)
        self.last_matches = self.last_matches[:10]

        # 更新连续纪录
        self._update_streak()

    def _update_streak(self) -> None:
        """更新连续纪录"""
        if not self.last_matches:
            self.current_streak = 0
            self.streak_type = "none"
            return None
        first_result = self.last_matches[0]
        if first_result == "D":
            self.current_streak = 0
            self.streak_type = "draw"
            return None
        streak_type = "win" if first_result == "W" else "loss"
        streak = 1

        for result in self.last_matches[1:]:
            if result == "D":
                break
            if (streak_type == "win" and result == "W") or (
                streak_type == "loss" and result == "L"
            ):
                streak += 1
            else:
                break

        self.current_streak = streak
        self.streak_type = streak_type

    @property
    def recent_form_string(self) -> str:
        """最近状态字符串"""
        return "".join(self.last_matches[:5])

    @property
    def is_in_good_form(self) -> bool:
        """是否状态良好"""
        # 简单判断:最近5场不败且至少赢3场
        if len(self.last_matches) < 5:
            return False

        recent = self.last_matches[:5]
        wins = recent.count("W")
        draws = recent.count("D")
        return wins >= 3 and (wins + draws) == 5

    def __str__(self) -> str:
        streak_str = (
            f"{self.current_streak}{self.streak_type[0].upper()}"
            if self.streak_type != "none"
            else "无"
        )
        return f"状态: {self.recent_form_string} ({streak_str})"


@dataclass
class Team:
    """类文档字符串"""
    pass  # 添加pass语句
    """
    球队领域模型

    封装球队的核心业务逻辑和不变性约束.
    """

    id: Optional[int] = None
    name: str = ""
    short_name: Optional[str] = None
    code: Optional[str] = None
    type: TeamType = TeamType.CLUB
    country: str = ""
    founded_year: Optional[int] = None
    stadium: Optional[str] = None
    capacity: Optional[int] = None
    website: Optional[str] = None
    logo_url: Optional[str] = None
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    # 值对象
    stats: Optional[TeamStats] = None
    form: Optional[TeamForm] = None

    # 领域事件
    _domain_events: List[Any] = field(default_factory=list, init=False)

    def __post_init__(self):
        """函数文档字符串"""
        pass
  # 添加pass语句
        """初始化后的验证"""
        if not self.name or len(self.name.strip()) == 0:
            raise DomainError("球队名称不能为空")

        if self.short_name and len(self.short_name) > 10:
            raise DomainError("简称不能超过10个字符")

        if self.code and (len(self.code) != 3 or not self.code.isalpha()):
            raise DomainError("球队代码必须是3个字母")

        if self.founded_year and (
            self.founded_year < 1800 or self.founded_year > datetime.utcnow().year
        ):
            raise DomainError("成立年份无效")

        if self.capacity and self.capacity < 0:
            raise DomainError("体育场容量不能为负数")

        # 初始化值对象
        if not self.stats:
            self.stats = TeamStats()
        if not self.form:
            self.form = TeamForm()

    # ========================================
    # 业务方法
    # ========================================

    def update_info(
        self,
        name: Optional[str] = None,
        short_name: Optional[str] = None,
        stadium: Optional[str] = None,
        capacity: Optional[int] = None,
    ) -> None:
        """更新球队信息"""
        if name:
            self.name = name
        if short_name:
            self.short_name = short_name
        if stadium:
            self.stadium = stadium
        if capacity is not None:
            if capacity < 0:
                raise DomainError("体育场容量不能为负数")
            self.capacity = capacity

        self.updated_at = datetime.utcnow()

    def add_match_result(
        self,
        result: str,
        goals_for: int,
        goals_against: int,
        is_home: Optional[bool] = None,
    ) -> None:
        """添加比赛结果"""
        if result not in ["win", "draw", "loss"]:
            raise DomainError("比赛结果必须是 win/draw/loss")

        if goals_for < 0 or goals_against < 0:
            raise DomainError("进球数不能为负数")

        # 更新统计
        self.stats.update(result, goals_for, goals_against)

        # 更新状态
        self.form.add_result(
            "W" if result == "win" else "D" if result == "draw" else "L"
        )

        self.updated_at = datetime.utcnow()

    def promote(self) -> None:
        """升级（用于联赛系统）"""
        # 这里可以添加升级相关的业务逻辑
        self.updated_at = datetime.utcnow()

    def relegate(self) -> None:
        """降级（用于联赛系统）"""
        # 这里可以添加降级相关的业务逻辑
        self.updated_at = datetime.utcnow()

    def activate(self) -> None:
        """激活球队"""
        self.is_active = True
        self.updated_at = datetime.utcnow()

    def deactivate(self) -> None:
        """停用球队"""
        self.is_active = False
        self.updated_at = datetime.utcnow()

    def calculate_strength(self) -> float:
        """计算球队实力（0-100）"""
        if not self.stats or self.stats.matches_played == 0:
            return 50.0  # 默认中等实力

        # 基于胜率和净胜球计算
        strength = 50.0
        strength += self.stats.win_rate * 40  # 胜率权重40%

        # 净胜球影响
        avg_goal_diff = self.stats.goal_difference / max(1, self.stats.matches_played)
        strength += min(max(avg_goal_diff * 2, -10), 10)  # 净胜球权重最高±10

        # 最近状态加成
        if self.form.is_in_good_form:
            strength += 10

        return min(max(strength, 0), 100)  # 限制在0-100

    # ========================================
    # 查询方法
    # ========================================

    @property
    def full_name(self) -> str:
        """全名"""
        return self.name

    @property
    def display_name(self) -> str:
        """显示名称"""
        return self.short_name or self.name

    @property
    def age(self) -> Optional[int]:
        """球队年龄"""
        if self.founded_year:
            return datetime.utcnow().year - self.founded_year
        return None

    @property
    def rank(self) -> str:
        """排名级别"""
        if not self.stats or self.stats.matches_played < 10:
            return "N/A"

        points_per_game = self.stats.points / self.stats.matches_played
        if points_per_game >= 2.5:
            return "顶级"
        elif points_per_game >= 2.0:
            return "强队"
        elif points_per_game >= 1.5:
            return "中游"
        elif points_per_game >= 1.0:
            return "弱旅"
        else:
            return "保级"

    def get_rival_team_ids(self) -> List[int]:
        """获取死敌球队ID（需要从外部配置）"""
        # 这里应该从配置或数据库获取
        return []

    def is_rival(self, team_id: int) -> bool:
        """是否是死敌"""
        return team_id in self.get_rival_team_ids()

    # ========================================
    # 领域事件管理
    # ========================================

    def _add_domain_event(self, event: Any) -> None:
        """添加领域事件"""
        self._domain_events.append(event)

    def get_domain_events(self) -> List[Any]:
        """获取领域事件"""
        return self._domain_events.copy()

    def clear_domain_events(self) -> None:
        """清除领域事件"""
        self._domain_events.clear()

    # ========================================
    # 序列化方法
    # ========================================

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "short_name": self.short_name,
            "code": self.code,
            "type": self.type.value,
            "country": self.country,
            "founded_year": self.founded_year,
            "stadium": self.stadium,
            "capacity": self.capacity,
            "website": self.website,
            "logo_url": self.logo_url,
            "is_active": self.is_active,
            "stats": (
                {
                    "matches_played": self.stats.matches_played,
                    "wins": self.stats.wins,
                    "draws": self.stats.draws,
                    "losses": self.stats.losses,
                    "goals_for": self.stats.goals_for,
                    "goals_against": self.stats.goals_against,
                    "points": self.stats.points,
                    "goal_difference": self.stats.goal_difference,
                    "win_rate": self.stats.win_rate,
                }
                if self.stats
                else None
            ),
            "form": (
                {
                    "last_matches": self.form.last_matches,
                    "current_streak": self.form.current_streak,
                    "streak_type": self.form.streak_type,
                    "recent_form_string": self.form.recent_form_string,
                }
                if self.form
                else None
            ),
            "strength": self.calculate_strength(),
            "rank": self.rank,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Team":
        """从字典创建实例"""
        stats_data = data.pop("stats", None)
        stats = None
        if stats_data:
            for transient_key in ["points", "goal_difference", "win_rate"]:
                stats_data.pop(transient_key, None)
            stats = TeamStats(**stats_data)

        form_data = data.pop("form", None)
        form = None
        if form_data:
            form_data.pop("recent_form_string", None)
            form = TeamForm(**form_data)

        # 处理类型枚举
        if data.get("type"):
            data["type"] = TeamType(data["type"])

        data.pop("strength", None)
        data.pop("rank", None)

        # 处理日期
        if data.get("created_at"):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if data.get("updated_at"):
            data["updated_at"] = datetime.fromisoformat(data["updated_at"])

        return cls(stats=stats, form=form, **data)

    def __str__(self) -> str:
        return f"{self.name} ({self.code or self.short_name}) - {self.rank}"
