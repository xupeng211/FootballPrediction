"""
球队领域模型
"""

from datetime import datetime
from typing import Any, Dict, List, Optional


class TeamStatistics:
    """类文档字符串"""

    pass  # 添加pass语句
    """球队统计数据"""

    def __init__(self):
        """函数文档字符串"""
        pass
        # 添加pass语句
        self.matches_played = 0
        self.wins = 0
        self.draws = 0
        self.losses = 0
        self.goals_for = 0
        self.goals_against = 0
        self.goal_difference = 0
        self.points = 0

    def update(self, goals_for: int, goals_against: int) -> None:
        """更新统计"""
        self.matches_played += 1
        self.goals_for += goals_for
        self.goals_against += goals_against
        self.goal_difference = self.goals_for - self.goals_against

        if goals_for > goals_against:
            self.wins += 1
            self.points += 3
        elif goals_for < goals_against:
            self.losses += 1
        else:
            self.draws += 1
            self.points += 1

    def get_win_rate(self) -> float:
        """获取胜率"""
        if self.matches_played == 0:
            return 0.0
        return self.wins / self.matches_played

    def get_avg_goals(self) -> float:
        """获取场均进球"""
        if self.matches_played == 0:
            return 0.0
        return self.goals_for / self.matches_played

    def get_avg_conceded(self) -> float:
        """获取场均失球"""
        if self.matches_played == 0:
            return 0.0
        return self.goals_against / self.matches_played


class Team:
    """类文档字符串"""

    pass  # 添加pass语句
    """球队领域模型"""

    def __init__(
        self,
        id: Optional[int] = None,
        name: str = "",
        short_name: str = "",
        founded_year: Optional[int] = None,
        stadium: str = "",
        league_id: int = 0,
    ):
        self.id = id
        self.name = name
        self.short_name = short_name
        self.founded_year = founded_year
        self.stadium = stadium
        self.league_id = league_id

        # 统计数据
        self.overall_stats = TeamStatistics()
        self.home_stats = TeamStatistics()
        self.away_stats = TeamStatistics()

        # 近期状态
        self.recent_form: List[str] = []  # W/D/L序列
        self.current_streak = {"type": "", "count": 0}

        # 实力评分
        self.strength_score = 50.0  # 0-100
        self.attack_rating = 50.0
        self.defense_rating = 50.0

        # 元数据
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

    def update_stats(self, goals_for: int, goals_against: int, is_home: bool) -> None:
        """更新统计数据"""
        self.overall_stats.update(goals_for, goals_against)

        if is_home:
            self.home_stats.update(goals_for, goals_against)
        else:
            self.away_stats.update(goals_for, goals_against)

        # 更新近期状态
        if goals_for > goals_against:
            self.recent_form.append("W")
        elif goals_for < goals_against:
            self.recent_form.append("L")
        else:
            self.recent_form.append("D")

        # 只保留最近5场
        if len(self.recent_form) > 5:
            self.recent_form = self.recent_form[-5:]

        # 更新连胜/连败
        self._update_streak()

        # 更新实力评分
        self._update_strength_rating()

        self.updated_at = datetime.now()

    def _update_streak(self) -> None:
        """更新连胜/连败记录"""
        if not self.recent_form:
            return None
        last_result = self.recent_form[-1]
        streak_type = (
            "win" if last_result == "W" else "lose" if last_result == "L" else "draw"
        )
        streak_count = 0

        # 从最新结果往前数
        for result in reversed(self.recent_form):
            if (
                (streak_type == "win" and result == "W")
                or (streak_type == "lose" and result == "L")
                or (streak_type == "draw" and result == "D")
            ):
                streak_count += 1
            else:
                break

        self.current_streak = {"type": streak_type, "count": streak_count}

    def _update_strength_rating(self) -> None:
        """更新实力评分"""
        # 基于近期表现调整实力评分
        recent_points = 0
        for result in self.recent_form[-5:]:
            if result == "W":
                recent_points += 3
            elif result == "D":
                recent_points += 1

        # 简单的实力评分计算
        performance_factor = recent_points / 15.0  # 15分是满分
        self.strength_score = min(100, max(0, 50 + (performance_factor - 0.5) * 100))

        # 调整攻防评分
        avg_goals = self.overall_stats.get_avg_goals()
        avg_conceded = self.overall_stats.get_avg_conceded()

        self.attack_rating = min(100, max(0, avg_goals * 10))
        self.defense_rating = min(100, max(0, 100 - avg_conceded * 10))

    def get_form_points(self, last_n: int = 5) -> int:
        """获取最近N场的积分"""
        if not self.recent_form or last_n <= 0:
            return 0

        points = 0
        count = min(last_n, len(self.recent_form))

        for result in self.recent_form[-count:]:
            if result == "W":
                points += 3
            elif result == "D":
                points += 1

        return points

    def get_strength_score(self) -> float:
        """获取综合实力评分"""
        return self.strength_score

    def is_in_form(self) -> bool:
        """判断状态是否良好"""
        if len(self.recent_form) < 3:
            return False

        # 最近3场至少2胜1平
        recent_three = self.recent_form[-3:]
        wins = recent_three.count("W")
        draws = recent_three.count("D")

        return wins >= 2 or (wins >= 1 and draws >= 2)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "short_name": self.short_name,
            "founded_year": self.founded_year,
            "stadium": self.stadium,
            "league_id": self.league_id,
            "strength_score": self.strength_score,
            "attack_rating": self.attack_rating,
            "defense_rating": self.defense_rating,
            "recent_form": self.recent_form,
            "current_streak": self.current_streak,
            "overall_stats": {
                "matches_played": self.overall_stats.matches_played,
                "wins": self.overall_stats.wins,
                "draws": self.overall_stats.draws,
                "losses": self.overall_stats.losses,
                "goals_for": self.overall_stats.goals_for,
                "goals_against": self.overall_stats.goals_against,
                "goal_difference": self.overall_stats.goal_difference,
                "points": self.overall_stats.points,
                "win_rate": self.overall_stats.get_win_rate(),
            },
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Team":
        """从字典创建实例"""
        team = cls(
            id=data.get("id"),
            name=data.get("name", ""),
            short_name=data.get("short_name", ""),
            founded_year=data.get("founded_year"),
            stadium=data.get("stadium", ""),
            league_id=data.get("league_id", 0),
        )

        # 设置实力评分
        team.strength_score = data.get("strength_score", 50.0)
        team.attack_rating = data.get("attack_rating", 50.0)
        team.defense_rating = data.get("defense_rating", 50.0)

        # 设置近期状态
        team.recent_form = data.get("recent_form", [])
        team.current_streak = data.get("current_streak", {"type": "", "count": 0})

        # 设置时间
        if data.get("created_at"):
            team.created_at = datetime.fromisoformat(data["created_at"])
        if data.get("updated_at"):
            team.updated_at = datetime.fromisoformat(data["updated_at"])

        return team

    def __str__(self) -> str:
        return f"Team({self.name})"

    def __repr__(self) -> str:
        return f"<Team(id={self.id}, name={self.name}, strength={self.strength_score})>"
