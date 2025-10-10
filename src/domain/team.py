"""
球队领域模型

封装球队相关的业务逻辑和统计。
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass, field

from .match import Match, MatchStatus


@dataclass
class TeamStatistics:
    """球队统计数据"""

    played: int = 0
    won: int = 0
    drawn: int = 0
    lost: int = 0
    goals_for: int = 0
    goals_against: int = 0
    clean_sheets: int = 0
    failed_to_score: int = 0
    yellow_cards: int = 0
    red_cards: int = 0

    @property
    def points(self) -> int:
        """积分"""
        return self.won * 3 + self.drawn

    @property
    def win_rate(self) -> float:
        """胜率"""
        if self.played == 0:
            return 0.0
        return self.won / self.played

    @property
    def goal_difference(self) -> int:
        """净胜球"""
        return self.goals_for - self.goals_against

    @property
    def average_goals_for(self) -> float:
        """场均进球"""
        if self.played == 0:
            return 0.0
        return self.goals_for / self.played

    @property
    def average_goals_against(self) -> float:
        """场均失球"""
        if self.played == 0:
            return 0.0
        return self.goals_against / self.played

    @property
    def clean_sheet_rate(self) -> float:
        """零封率"""
        if self.played == 0:
            return 0.0
        return self.clean_sheets / self.played

    def update_from_match(self, match: Match, is_home: bool):
        """从比赛更新统计"""
        goals_scored = (
            match.current_score.home_score
            if is_home
            else match.current_score.away_score
        )
        goals_conceded = (
            match.current_score.away_score
            if is_home
            else match.current_score.home_score
        )

        self.played += 1
        self.goals_for += goals_scored
        self.goals_against += goals_conceded

        if goals_scored == 0:
            self.failed_to_score += 1
        if goals_conceded == 0:
            self.clean_sheets += 1

        # 判断胜负
        if goals_scored > goals_conceded:
            self.won += 1
        elif goals_scored < goals_conceded:
            self.lost += 1
        else:
            self.drawn += 1


@dataclass
class FormRecord:
    """近期战绩记录"""

    match_id: int
    date: datetime
    opponent_id: int
    opponent_name: str
    is_home: bool
    result: str  # W, D, L
    goals_scored: int
    goals_conceded: int


class Team:
    """球队领域模型

    封装球队的核心业务逻辑和统计计算。
    """

    def __init__(
        self,
        name: str,
        id: Optional[int] = None,
        short_name: Optional[str] = None,
        country: Optional[str] = None,
        founded: Optional[int] = None,
        stadium: Optional[str] = None,
        capacity: Optional[int] = None,
        logo_url: Optional[str] = None,
        website: Optional[str] = None,
    ):
        self.id = id
        self.name = name
        self.short_name = short_name or name[:3].upper()
        self.country = country
        self.founded = founded
        self.stadium = stadium
        self.capacity = capacity
        self.logo_url = logo_url
        self.website = website

        # 统计数据
        self.overall_stats = TeamStatistics()
        self.home_stats = TeamStatistics()
        self.away_stats = TeamStatistics()
        self.recent_form: List[FormRecord] = []

        # 元数据
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

        # 业务规则验证
        self._validate_initialization()

    def _validate_initialization(self):
        """验证初始化数据"""
        if not self.name or len(self.name.strip()) == 0:
            raise ValueError("球队名称不能为空")

        if self.capacity and self.capacity <= 0:
            raise ValueError("球场容量必须大于0")

    # ==================== 基础信息 ====================

    def get_full_name(self) -> str:
        """获取完整名称"""
        if self.country:
            return f"{self.name} ({self.country})"
        return self.name

    def get_display_name(self) -> str:
        """获取显示名称"""
        return f"{self.short_name} - {self.name}" if self.short_name else self.name

    def get_age(self) -> int:
        """获取球队年龄"""
        if not self.founded:
            return 0
        current_year = datetime.now().year
        return current_year - self.founded

    # ==================== 统计计算 ====================

    def update_statistics(self, match: Match):
        """从比赛更新统计数据"""
        if match.home_team_id == self.id:
            self.overall_stats.update_from_match(match, is_home=True)
            self.home_stats.update_from_match(match, is_home=True)
        elif match.away_team_id == self.id:
            self.overall_stats.update_from_match(match, is_home=False)
            self.away_stats.update_from_match(match, is_home=False)

        # 更新近期战绩
        self._update_recent_form(match)
        self.updated_at = datetime.now()

    def _update_recent_form(self, match: Match):
        """更新近期战绩记录"""
        if match.home_team_id == self.id:
            is_home = True
            opponent_id = match.away_team_id
            opponent_name = match.away_team.name if match.away_team else "Unknown"
            goals_scored = match.current_score.home_score
            goals_conceded = match.current_score.away_score
        elif match.away_team_id == self.id:
            is_home = False
            opponent_id = match.home_team_id
            opponent_name = match.home_team.name if match.home_team else "Unknown"
            goals_scored = match.current_score.away_score
            goals_conceded = match.current_score.home_score
        else:
            return

        # 确定结果
        if goals_scored > goals_conceded:
            result = "W"
        elif goals_scored < goals_conceded:
            result = "L"
        else:
            result = "D"

        # 添加到近期战绩
        form_record = FormRecord(
            match_id=match.id,
            date=match.match_time,
            opponent_id=opponent_id,
            opponent_name=opponent_name,
            is_home=is_home,
            result=result,
            goals_scored=goals_scored,
            goals_conceded=goals_conceded,
        )

        # 保持最近10场记录
        self.recent_form.insert(0, form_record)
        self.recent_form = self.recent_form[:10]

    def get_recent_form_string(self, matches: int = 5) -> str:
        """获取近期战绩字符串"""
        recent_matches = self.recent_form[:matches]
        return "".join([record.result for record in recent_matches])

    def get_points_from_recent_games(self, matches: int = 5) -> int:
        """获取最近几场比赛的积分"""
        recent_matches = self.recent_form[:matches]
        points = 0
        for record in recent_matches:
            if record.result == "W":
                points += 3
            elif record.result == "D":
                points += 1
        return points

    def get_scoring_streak(self) -> int:
        """获取连续进球场次"""
        streak = 0
        for record in self.recent_form:
            if record.goals_scored > 0:
                streak += 1
            else:
                break
        return streak

    def get_clean_sheet_streak(self) -> int:
        """获取连续零封场次"""
        streak = 0
        for record in self.recent_form:
            if record.goals_conceded == 0:
                streak += 1
            else:
                break
        return streak

    # ==================== 战力评估 ====================

    def get_strength_score(self) -> float:
        """获取球队实力评分"""
        score = 0.0

        # 基础分数
        score += 50.0

        # 胜率加成
        if self.overall_stats.played > 0:
            win_rate = self.overall_stats.win_rate
            score += win_rate * 30.0

        # 进球能力加成
        if self.overall_stats.played > 0:
            avg_goals = self.overall_stats.average_goals_for
            score += min(avg_goals * 5.0, 15.0)

        # 防守能力加成
        if self.overall_stats.played > 0:
            avg_conceded = self.overall_stats.average_goals_against
            defense_bonus = max(0, (2.0 - avg_conceded) * 5.0)
            score += defense_bonus

        # 主客场能力
        if self.home_stats.played > 5:
            home_win_rate = self.home_stats.win_rate
            score += home_win_rate * 5.0

        if self.away_stats.played > 5:
            away_win_rate = self.away_stats.win_rate
            score += away_win_rate * 5.0

        # 近期状态
        recent_points = self.get_points_from_recent_games(5)
        score += recent_points * 2.0

        return min(score, 100.0)

    def get_home_advantage_score(self) -> float:
        """获取主场优势评分"""
        if self.home_stats.played < 5:
            return 0.0

        home_win_rate = self.home_stats.win_rate
        overall_win_rate = self.overall_stats.win_rate

        # 主场胜率与总体胜率的差异
        advantage = home_win_rate - overall_win_rate
        return max(0, advantage * 100)

    def get_consistency_score(self) -> float:
        """获取稳定性评分"""
        if len(self.recent_form) < 5:
            return 0.0

        # 计算近期表现的波动性
        recent_points = [
            self._get_points_from_result(r.result) for r in self.recent_form[:5]
        ]
        avg_points = sum(recent_points) / len(recent_points)

        # 计算标准差（简化版）
        variance = sum((p - avg_points) ** 2 for p in recent_points) / len(
            recent_points
        )
        std_dev = variance**0.5

        # 标准差越小，稳定性越高
        consistency = max(0, 100 - std_dev * 50)
        return consistency

    def _get_points_from_result(self, result: str) -> int:
        """从结果获取积分"""
        if result == "W":
            return 3
        elif result == "D":
            return 1
        else:
            return 0

    # ==================== 对阵分析 ====================

    def get_head_to_head_stats(
        self, opponent_id: int, matches: List[Match]
    ) -> Dict[str, Any]:
        """获取与特定对手的历史交锋统计"""
        h2h_matches = []
        for match in matches:
            if match.status == MatchStatus.FINISHED and match.current_score.is_valid():
                if (
                    match.home_team_id == self.id and match.away_team_id == opponent_id
                ) or (
                    match.away_team_id == self.id and match.home_team_id == opponent_id
                ):
                    h2h_matches.append(match)

        if not h2h_matches:
            return {
                "total_matches": 0,
                "wins": 0,
                "draws": 0,
                "losses": 0,
                "goals_for": 0,
                "goals_against": 0,
                "win_rate": 0.0,
            }

        stats = {
            "total_matches": len(h2h_matches),
            "wins": 0,
            "draws": 0,
            "losses": 0,
            "goals_for": 0,
            "goals_against": 0,
        }

        for match in h2h_matches:
            is_home = match.home_team_id == self.id
            goals_scored = (
                match.current_score.home_score
                if is_home
                else match.current_score.away_score
            )
            goals_conceded = (
                match.current_score.away_score
                if is_home
                else match.current_score.home_score
            )

            stats["goals_for"] += goals_scored
            stats["goals_against"] += goals_conceded

            if goals_scored > goals_conceded:
                stats["wins"] += 1
            elif goals_scored < goals_conceded:
                stats["losses"] += 1
            else:
                stats["draws"] += 1

        stats["win_rate"] = stats["wins"] / stats["total_matches"]
        return stats

    # ==================== 业务规则 ====================

    def is_formidable_opponent(self, opponent: "Team") -> bool:
        """判断是否为强劲对手"""
        opponent_strength = opponent.get_strength_score()
        return opponent_strength > 70.0

    def should_be_favored(self, opponent: "Team", is_home: bool = True) -> bool:
        """判断是否应该是 favored"""
        my_strength = self.get_strength_score()
        opponent_strength = opponent.get_strength_score()

        strength_diff = my_strength - opponent_strength

        if is_home:
            # 主场有额外优势
            home_advantage = self.get_home_advantage_score()
            return strength_diff + home_advantage > 10.0
        else:
            return strength_diff > 15.0

    def calculate_expected_goals(
        self, opponent: "Team", is_home: bool = True
    ) -> Tuple[float, float]:
        """计算预期进球数"""
        my_attack = (
            self.overall_stats.average_goals_for
            if self.overall_stats.played > 0
            else 1.0
        )
        opponent_defense = (
            opponent.overall_stats.average_goals_against
            if opponent.overall_stats.played > 0
            else 1.5
        )

        opponent_attack = (
            opponent.overall_stats.average_goals_for
            if opponent.overall_stats.played > 0
            else 1.0
        )
        my_defense = (
            self.overall_stats.average_goals_against
            if self.overall_stats.played > 0
            else 1.5
        )

        if is_home:
            # 主场有进攻加成
            my_expected_goals = (my_attack + opponent_defense) * 1.1
            opponent_expected_goals = (opponent_attack + my_defense) * 0.9
        else:
            my_expected_goals = (my_attack + opponent_defense) * 0.9
            opponent_expected_goals = (opponent_attack + my_defense) * 1.1

        return (my_expected_goals, opponent_expected_goals)

    # ==================== 比较和哈希 ====================

    def __eq__(self, other) -> bool:
        """比较两个球队是否相同"""
        if not isinstance(other, Team):
            return False
        return self.id == other.id if self.id and other.id else self.name == other.name

    def __hash__(self) -> int:
        """生成哈希值"""
        if self.id:
            return hash(self.id)
        return hash(self.name)

    def __str__(self) -> str:
        """字符串表示"""
        return self.name

    def __repr__(self) -> str:
        """详细字符串表示"""
        return (
            f"Team(id={self.id}, name='{self.name}', "
            f"short_name='{self.short_name}', country='{self.country}')"
        )

    # ==================== 序列化 ====================

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "short_name": self.short_name,
            "country": self.country,
            "founded": self.founded,
            "stadium": self.stadium,
            "capacity": self.capacity,
            "logo_url": self.logo_url,
            "website": self.website,
            "strength_score": self.get_strength_score(),
            "home_advantage_score": self.get_home_advantage_score(),
            "consistency_score": self.get_consistency_score(),
            "recent_form": self.get_recent_form_string(5),
            "overall_stats": {
                "played": self.overall_stats.played,
                "won": self.overall_stats.won,
                "drawn": self.overall_stats.drawn,
                "lost": self.overall_stats.lost,
                "points": self.overall_stats.points,
                "win_rate": self.overall_stats.win_rate,
                "goal_difference": self.overall_stats.goal_difference,
                "average_goals_for": self.overall_stats.average_goals_for,
                "average_goals_against": self.overall_stats.average_goals_against,
            },
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Team":
        """从字典创建实例"""
        return cls(
            id=data.get("id"),
            name=data["name"],
            short_name=data.get("short_name"),
            country=data.get("country"),
            founded=data.get("founded"),
            stadium=data.get("stadium"),
            capacity=data.get("capacity"),
            logo_url=data.get("logo_url"),
            website=data.get("website"),
        )
