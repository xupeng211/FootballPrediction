"""
联赛领域模型
League Domain Model

封装联赛相关的业务逻辑和不变性约束.
Encapsulates league-related business logic and invariants.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

from ...core.exceptions import DomainError


class LeagueType(Enum):
    """联赛类型"""

    DOMESTIC_LEAGUE = "domestic_league"  # 国内联赛
    CUP = "cup"  # 杯赛
    INTERNATIONAL = "international"  # 国际赛事
    FRIENDLY = "friendly"  # 友谊赛


class LeagueStatus(Enum):
    """联赛状态"""

    UPCOMING = "upcoming"  # 即将开始
    ACTIVE = "active"  # 进行中
    COMPLETED = "completed"  # 已结束
    SUSPENDED = "suspended"  # 暂停


@dataclass
class LeagueSeason:
    """类文档字符串"""
    pass  # 添加pass语句
    """联赛赛季值对象"""

    season: str
    start_date: datetime
    end_date: datetime
    status: LeagueStatus = LeagueStatus.UPCOMING
    total_rounds: int = 38  # 标准联赛轮次
    current_round: int = 0

    def __post_init__(self):
        """函数文档字符串"""
        pass
  # 添加pass语句
        """验证赛季信息"""
        if not self.season:
            raise DomainError("赛季名称不能为空")

        if self.start_date >= self.end_date:
            raise DomainError("开始日期必须早于结束日期")

        if self.total_rounds < 1:
            raise DomainError("总轮次必须大于0")

        if self.current_round < 0 or self.current_round > self.total_rounds:
            raise DomainError("当前轮次无效")

    @property
    def progress(self) -> float:
        """赛季进度"""
        if self.total_rounds == 0:
            return 0.0
        return min(self.current_round / self.total_rounds, 1.0)

    @property
    def is_active(self) -> bool:
        """是否进行中"""
        return self.status == LeagueStatus.ACTIVE

    def start_season(self) -> None:
        """开始赛季"""
        if self.status != LeagueStatus.UPCOMING:
            raise DomainError(f"赛季状态为 {self.status.value},无法开始")

        self.status = LeagueStatus.ACTIVE
        self.current_round = 1

    def advance_round(self) -> None:
        """推进轮次"""
        if self.status != LeagueStatus.ACTIVE:
            raise DomainError("只有进行中的赛季才能推进轮次")

        if self.current_round >= self.total_rounds:
            self.status = LeagueStatus.COMPLETED
        else:
            self.current_round += 1

    def complete_season(self) -> None:
        """结束赛季"""
        self.status = LeagueStatus.COMPLETED
        if self.current_round < self.total_rounds:
            self.current_round = self.total_rounds

    def __str__(self) -> str:
        return f"{self.season} - 第 {self.current_round}/{self.total_rounds} 轮"


@dataclass
class LeagueSettings:
    """类文档字符串"""
    pass  # 添加pass语句
    """联赛设置值对象"""

    points_for_win: int = 3
    points_for_draw: int = 1
    points_for_loss: int = 0
    promotion_places: int = 3  # 升级名额
    relegation_places: int = 3  # 降级名额
    max_foreign_players: int = 5  # 外援名额
    match_duration: int = 90  # 比赛时长（分钟）
    halftime_duration: int = 15  # 中场休息时长
    extra_time: bool = False  # 是否加时
    penalty_shootout: bool = False  # 是否点球

    def __post_init__(self):
        """函数文档字符串"""
        pass
  # 添加pass语句
        """验证设置"""
        if any(
            x < 0
            for x in [self.points_for_win, self.points_for_draw, self.points_for_loss]
        ):
            raise DomainError("积分不能为负数")

        if self.points_for_win < self.points_for_draw:
            raise DomainError("胜场积分不能少于平场积分")

        if self.points_for_draw < self.points_for_loss:
            raise DomainError("平场积分不能少于负场积分")

        if self.promotion_places < 0 or self.relegation_places < 0:
            raise DomainError("升级降级名额不能为负数")

        if self.max_foreign_players < 0:
            raise DomainError("外援名额不能为负数")

        if self.match_duration <= 0:
            raise DomainError("比赛时长必须大于0")

        if self.halftime_duration < 0:
            raise DomainError("中场休息时长不能为负数")

    def calculate_points(self, wins: int, draws: int, losses: int) -> int:
        """计算积分"""
        return (
            wins * self.points_for_win
            + draws * self.points_for_draw
            + losses * self.points_for_loss
        )

    def __str__(self) -> str:
        return (
            f"胜{self.points_for_win} 平{self.points_for_draw} 负{self.points_for_loss}"
        )


@dataclass
class League:
    """类文档字符串"""
    pass  # 添加pass语句
    """
    联赛领域模型

    封装联赛的核心业务逻辑和不变性约束.
    """

    id: Optional[int] = None
    name: str = ""
    short_name: Optional[str] = None
    code: Optional[str] = None
    type: LeagueType = LeagueType.DOMESTIC_LEAGUE
    country: str = ""
    level: int = 1  # 联赛级别
    is_active: bool = True
    founded_year: Optional[int] = None
    website: Optional[str] = None
    logo_url: Optional[str] = None
    current_season: Optional[LeagueSeason] = None
    settings: Optional[LeagueSettings] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    # 领域事件
    _domain_events: List[Any] = field(default_factory=list, init=False)

    def __post_init__(self):
        """函数文档字符串"""
        pass
  # 添加pass语句
        """初始化后的验证"""
        if not self.name or len(self.name.strip()) == 0:
            raise DomainError("联赛名称不能为空")

        if self.short_name and len(self.short_name) > 20:
            raise DomainError("简称不能超过20个字符")

        if self.code and (len(self.code) < 2 or len(self.code) > 5):
            raise DomainError("联赛代码长度必须在2-5个字符之间")

        if self.level < 1:
            raise DomainError("联赛级别必须大于0")

        if self.founded_year and (
            self.founded_year < 1800 or self.founded_year > datetime.utcnow().year
        ):
            raise DomainError("成立年份无效")

        # 初始化默认值
        if not self.settings:
            self.settings = LeagueSettings()

    # ========================================
    # 业务方法
    # ========================================

    def start_new_season(
        self,
        season: str,
        start_date: datetime,
        end_date: datetime,
        total_rounds: Optional[int] = None,
    ) -> LeagueSeason:
        """开始新赛季"""
        if self.current_season and self.current_season.is_active:
            raise DomainError("当前赛季仍在进行中")

        new_season = LeagueSeason(
            season=season,
            start_date=start_date,
            end_date=end_date,
            total_rounds=total_rounds or self.settings.match_duration,
            status=LeagueStatus.UPCOMING,
        )

        self.current_season = new_season
        self.updated_at = datetime.utcnow()

        return new_season

    def update_info(
        self,
        name: Optional[str] = None,
        short_name: Optional[str] = None,
        website: Optional[str] = None,
        logo_url: Optional[str] = None,
    ) -> None:
        """更新联赛信息"""
        if name:
            self.name = name
        if short_name:
            self.short_name = short_name
        if website:
            self.website = website
        if logo_url:
            self.logo_url = logo_url

        self.updated_at = datetime.utcnow()

    def update_settings(
        self,
        points_for_win: Optional[int] = None,
        points_for_draw: Optional[int] = None,
        points_for_loss: Optional[int] = None,
        max_foreign_players: Optional[int] = None,
    ) -> None:
        """更新联赛设置"""
        if points_for_win is not None:
            self.settings.points_for_win = points_for_win
        if points_for_draw is not None:
            self.settings.points_for_draw = points_for_draw
        if points_for_loss is not None:
            self.settings.points_for_loss = points_for_loss
        if max_foreign_players is not None:
            self.settings.max_foreign_players = max_foreign_players

        self.updated_at = datetime.utcnow()

    def activate(self) -> None:
        """激活联赛"""
        self.is_active = True
        self.updated_at = datetime.utcnow()

    def deactivate(self) -> None:
        """停用联赛"""
        self.is_active = False
        self.updated_at = datetime.utcnow()

    def promote_to_next_level(self) -> None:
        """升级到下一级别"""
        if self.level <= 1:
            raise DomainError("已经是最高级别联赛")

        self.level -= 1  # 数字越小级别越高
        self.updated_at = datetime.utcnow()

    def relegate_to_lower_level(self) -> None:
        """降级到下一级别"""
        self.level += 1
        self.updated_at = datetime.utcnow()

    def calculate_revenue_sharing(self, position: int, total_teams: int) -> Decimal:
        """计算收入分成（基于排名）"""
        if position < 1 or position > total_teams:
            raise DomainError("排名无效")

        # 简化的分成计算
        base_share = Decimal("1000000")  # 基础分成100万
        position_bonus = max(0, (total_teams - position) * Decimal("100000"))
        return base_share + position_bonus

    # ========================================
    # 查询方法
    # ========================================

    @property
    def display_name(self) -> str:
        """显示名称"""
        return self.short_name or self.name

    @property
    def age(self) -> Optional[int]:
        """联赛年龄"""
        if self.founded_year:
            return datetime.utcnow().year - self.founded_year
        return None

    @property
    def prestige(self) -> str:
        """声望等级"""
        if self.level == 1:
            return "顶级联赛"
        elif self.level <= 3:
            return "高级联赛"
        elif self.level <= 5:
            return "中级联赛"
        else:
            return "低级联赛"

    @property
    def current_progress(self) -> float:
        """当前赛季进度"""
        if self.current_season:
            return self.current_season.progress
        return 0.0

    @property
    def is_cup_competition(self) -> bool:
        """是否是杯赛"""
        return self.type == LeagueType.CUP

    @property
    def is_international(self) -> bool:
        """是否是国际赛事"""
        return self.type == LeagueType.INTERNATIONAL

    def get_seasons_count(self) -> int:
        """获取赛季数量（简化处理）"""
        if self.founded_year:
            return datetime.utcnow().year - self.founded_year + 1
        return 0

    def can_team_register(self, team_level: int) -> bool:
        """检查球队是否可以注册"""
        # 简化规则:球队级别不能超过联赛级别太多
        return abs(team_level - self.level) <= 2

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
            "level": self.level,
            "is_active": self.is_active,
            "founded_year": self.founded_year,
            "website": self.website,
            "logo_url": self.logo_url,
            "prestige": self.prestige,
            "current_season": (
                {
                    "season": self.current_season.season,
                    "start_date": self.current_season.start_date.isoformat(),
                    "end_date": self.current_season.end_date.isoformat(),
                    "status": self.current_season.status.value,
                    "total_rounds": self.current_season.total_rounds,
                    "current_round": self.current_season.current_round,
                    "progress": self.current_season.progress,
                }
                if self.current_season
                else None
            ),
            "settings": (
                {
                    "points_for_win": self.settings.points_for_win,
                    "points_for_draw": self.settings.points_for_draw,
                    "points_for_loss": self.settings.points_for_loss,
                    "promotion_places": self.settings.promotion_places,
                    "relegation_places": self.settings.relegation_places,
                    "max_foreign_players": self.settings.max_foreign_players,
                }
                if self.settings
                else None
            ),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "League":
        """从字典创建实例"""
        season_data = data.pop("current_season", None)
        current_season = None
        if season_data:
            season_data.pop("progress", None)
            if season_data.get("start_date"):
                season_data["start_date"] = datetime.fromisoformat(
                    season_data["start_date"]
                )
            if season_data.get("end_date"):
                season_data["end_date"] = datetime.fromisoformat(
                    season_data["end_date"]
                )
            if season_data.get("status"):
                season_data["status"] = LeagueStatus(season_data["status"])
            current_season = LeagueSeason(**season_data)

        settings_data = data.pop("settings", None)
        settings = LeagueSettings(**settings_data) if settings_data else None

        # 处理类型枚举
        data.pop("prestige", None)
        if data.get("type"):
            data["type"] = LeagueType(data["type"])

        # 处理日期
        if data.get("created_at"):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if data.get("updated_at"):
            data["updated_at"] = datetime.fromisoformat(data["updated_at"])

        return cls(current_season=current_season, settings=settings, **data)

    def __str__(self) -> str:
        return f"{self.name} ({self.prestige}) - {self.country}"
