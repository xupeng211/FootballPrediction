"""
比赛领域模型

封装比赛相关的业务逻辑和规则。
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass, field

from .team import Team
from .odds import Odds


class MatchStatus(Enum):
    """比赛状态枚举"""

    SCHEDULED = "scheduled"  # 已安排
    LIVE = "live"  # 进行中
    HALF_TIME = "half_time"  # 中场休息
    FINISHED = "finished"  # 已结束
    POSTPONED = "postponed"  # 延期
    CANCELLED = "cancelled"  # 取消


class MatchResult(Enum):
    """比赛结果枚举"""

    HOME_WIN = "home_win"
    AWAY_WIN = "away_win"
    DRAW = "draw"
    UNKNOWN = "unknown"


@dataclass
class MatchScore:
    """比分数据类"""

    home_score: int = 0
    away_score: int = 0

    def __str__(self):
        return f"{self.home_score}:{self.away_score}"

    def is_valid(self) -> bool:
        """检查比分是否有效"""
        return self.home_score >= 0 and self.away_score >= 0

    def get_winner(self) -> Optional[str]:
        """获取胜者"""
        if self.home_score > self.away_score:
            return "home"
        elif self.away_score > self.home_score:
            return "away"
        else:
            return None

    def get_result(self) -> MatchResult:
        """获取比赛结果"""
        if not self.is_valid():
            return MatchResult.UNKNOWN

        winner = self.get_winner()
        if winner == "home":
            return MatchResult.HOME_WIN
        elif winner == "away":
            return MatchResult.AWAY_WIN
        else:
            return MatchResult.DRAW


@dataclass
class MatchStatistics:
    """比赛统计数据"""

    possession_home: float = 0.0  # 主队控球率
    possession_away: float = 0.0  # 客队控球率
    shots_home: int = 0  # 主队射门数
    shots_away: int = 0  # 客队射门数
    shots_on_target_home: int = 0  # 主队射正数
    shots_on_target_away: int = 0  # 客队射正数
    corners_home: int = 0  # 主队角球数
    corners_away: int = 0  # 客队角球数
    fouls_home: int = 0  # 主队犯规数
    fouls_away: int = 0  # 客队犯规数
    yellow_cards_home: int = 0  # 主队黄牌数
    yellow_cards_away: int = 0  # 客队黄牌数
    red_cards_home: int = 0  # 主队红牌数
    red_cards_away: int = 0  # 客队红牌数


@dataclass
class MatchEvent:
    """比赛事件"""

    minute: int
    event_type: str  # goal, yellow_card, red_card, substitution, etc.
    team: str  # home or away
    player_id: Optional[int] = None
    player_name: Optional[str] = None
    description: Optional[str] = None


class Match:
    """比赛领域模型

    封装比赛的核心业务逻辑和规则。
    """

    def __init__(
        self,
        id: Optional[int] = None,
        home_team: Optional[Team] = None,
        away_team: Optional[Team] = None,
        match_time: Optional[datetime] = None,
        league_id: Optional[int] = None,
        season: Optional[str] = None,
        venue: Optional[str] = None,
        status: MatchStatus = MatchStatus.SCHEDULED,
    ):
        self.id = id
        self.home_team = home_team
        self.away_team = away_team
        self.match_time = match_time or datetime.now()
        self.league_id = league_id
        self.season = season
        self.venue = venue
        self.status = status

        # 比分和统计
        self.current_score = MatchScore()
        self.halftime_score = MatchScore()
        self.final_score = MatchScore()
        self.statistics = MatchStatistics()
        self.events: List[MatchEvent] = []

        # 赔率信息
        self.odds: List[Odds] = []

        # 元数据
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

        # 业务规则验证
        self._validate_initialization()

    def _validate_initialization(self):
        """验证初始化数据"""
        if self.match_time and self.match_time < datetime.now():
            if self.status == MatchStatus.SCHEDULED:
                raise ValueError("过去的比赛不能是SCHEDULED状态")

    # ==================== 状态管理 ====================

    def can_predict(self) -> bool:
        """检查是否可以进行预测"""
        return (
            self.status == MatchStatus.SCHEDULED
            and self.is_not_started()
            and self.home_team is not None
            and self.away_team is not None
        )

    def is_not_started(self) -> bool:
        """检查比赛是否尚未开始"""
        if not self.match_time:
            return True
        return datetime.now() < self.match_time

    def is_live(self) -> bool:
        """检查比赛是否正在进行"""
        return self.status in [MatchStatus.LIVE, MatchStatus.HALF_TIME]

    def is_finished(self) -> bool:
        """检查比赛是否已结束"""
        return self.status == MatchStatus.FINISHED

    def is_postponed(self) -> bool:
        """检查比赛是否延期"""
        return self.status == MatchStatus.POSTPONED

    def is_cancelled(self) -> bool:
        """检查比赛是否取消"""
        return self.status == MatchStatus.CANCELLED

    def start_match(self) -> bool:
        """开始比赛"""
        if self.status != MatchStatus.SCHEDULED:
            return False

        self.status = MatchStatus.LIVE
        self.updated_at = datetime.now()
        return True

    def finish_match(self) -> bool:
        """结束比赛"""
        if not self.is_live():
            return False

        self.status = MatchStatus.FINISHED
        self.final_score = MatchScore(
            self.current_score.home_score, self.current_score.away_score
        )
        self.updated_at = datetime.now()
        return True

    def postpone_match(self, reason: Optional[str] = None) -> bool:
        """延期比赛"""
        if self.status == MatchStatus.FINISHED:
            return False

        self.status = MatchStatus.POSTPONED
        self.updated_at = datetime.now()
        return True

    def cancel_match(self, reason: Optional[str] = None) -> bool:
        """取消比赛"""
        if self.status == MatchStatus.FINISHED:
            return False

        self.status = MatchStatus.CANCELLED
        self.updated_at = datetime.now()
        return True

    # ==================== 比分管理 ====================

    def update_score(self, home_score: int, away_score: int) -> bool:
        """更新比分"""
        if not self.is_live():
            return False

        if home_score < 0 or away_score < 0:
            return False

        self.current_score.home_score = home_score
        self.current_score.away_score = away_score
        self.updated_at = datetime.now()
        return True

    def add_goal(self, team: str, minute: int, player_name: str) -> bool:
        """添加进球"""
        if not self.is_live():
            return False

        if team == "home":
            self.current_score.home_score += 1
        elif team == "away":
            self.current_score.away_score += 1
        else:
            return False

        # 添加事件
        event = MatchEvent(
            minute=minute,
            event_type="goal",
            team=team,
            player_name=player_name,
            description=f"Goal by {player_name}",
        )
        self.events.append(event)

        self.updated_at = datetime.now()
        return True

    # ==================== 业务规则 ====================

    def get_time_until_kickoff(self) -> timedelta:
        """获取距离开赛的时间"""
        if not self.match_time:
            return timedelta(0)
        return self.match_time - datetime.now()

    def get_duration(self) -> timedelta:
        """获取比赛持续时间"""
        if not self.is_live() and not self.is_finished():
            return timedelta(0)

        start_time = self.match_time or datetime.now()
        end_time = datetime.now() if self.is_live() else self.updated_at
        return end_time - start_time

    def get_confidence_level(self) -> float:
        """计算预测置信度

        基于多个因素计算预测的置信度：
        - 时间临近度
        - 数据完整性
        - 球队实力差距
        """
        confidence = 0.0

        # 时间因素 - 越临近比赛，置信度越高
        if self.match_time:
            hours_until = self.get_time_until_kickoff().total_seconds() / 3600
            if hours_until < 24:
                confidence += 0.3
            elif hours_until < 72:
                confidence += 0.2
            else:
                confidence += 0.1

        # 数据完整性
        if self.home_team and self.away_team:
            confidence += 0.2

        if self.odds:
            confidence += 0.2

        # 历史数据可用性
        if self.home_team and self.away_team:
            # 这里可以检查是否有足够的历史交锋数据
            confidence += 0.3

        return min(confidence, 1.0)

    def is_value_bet(self, threshold: float = 0.1) -> bool:
        """检查是否为价值投注

        通过比较预测概率和市场赔率判断是否存在价值。
        """
        if not self.odds:
            return False

        # 简化的价值投注计算
        # 实际应用中会更复杂，考虑更多因素
        best_odds = max(self.odds, key=lambda x: x.home_win if x else 0)
        if best_odds and best_odds.home_win > 2.0:
            return True

        return False

    def calculate_risk_level(self) -> str:
        """计算风险等级"""
        risk_score = 0.0

        # 时间风险
        hours_until = self.get_time_until_kickoff().total_seconds() / 3600
        if hours_until > 72:
            risk_score += 0.3

        # 数据风险
        if not self.home_team or not self.away_team:
            risk_score += 0.4

        if not self.odds:
            risk_score += 0.2

        # 确定风险等级
        if risk_score < 0.3:
            return "low"
        elif risk_score < 0.6:
            return "medium"
        else:
            return "high"

    # ==================== 比较和哈希 ====================

    def __eq__(self, other) -> bool:
        """比较两个比赛是否相同"""
        if not isinstance(other, Match):
            return False
        return (
            self.id == other.id
            if self.id and other.id
            else (
                self.home_team == other.home_team
                and self.away_team == other.away_team
                and self.match_time == other.match_time
            )
        )

    def __hash__(self) -> int:
        """生成哈希值"""
        if self.id:
            return hash(self.id)
        return hash(
            (
                self.home_team.id if self.home_team else None,
                self.away_team.id if self.away_team else None,
                self.match_time,
            )
        )

    def __str__(self) -> str:
        """字符串表示"""
        home_name = self.home_team.name if self.home_team else "TBD"
        away_name = self.away_team.name if self.away_team else "TBD"
        score = (
            str(self.current_score) if self.is_live() or self.is_finished() else "vs"
        )
        return f"{home_name} {score} {away_name}"

    def __repr__(self) -> str:
        """详细字符串表示"""
        return (
            f"Match(id={self.id}, "
            f"home={self.home_team.name if self.home_team else None}, "
            f"away={self.away_team.name if self.away_team else None}, "
            f"time={self.match_time}, "
            f"status={self.status.value})"
        )

    # ==================== 序列化 ====================

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "home_team_id": self.home_team.id if self.home_team else None,
            "away_team_id": self.away_team.id if self.away_team else None,
            "home_team_name": self.home_team.name if self.home_team else None,
            "away_team_name": self.away_team.name if self.away_team else None,
            "match_time": self.match_time.isoformat() if self.match_time else None,
            "league_id": self.league_id,
            "season": self.season,
            "venue": self.venue,
            "status": self.status.value,
            "current_score": {
                "home": self.current_score.home_score,
                "away": self.current_score.away_score,
            },
            "halftime_score": {
                "home": self.halftime_score.home_score,
                "away": self.halftime_score.away_score,
            },
            "final_score": {
                "home": self.final_score.home_score,
                "away": self.final_score.away_score,
            },
            "can_predict": self.can_predict(),
            "confidence_level": self.get_confidence_level(),
            "risk_level": self.calculate_risk_level(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Match":
        """从字典创建实例"""
        match = cls(
            id=data.get("id"),
            league_id=data.get("league_id"),
            season=data.get("season"),
            venue=data.get("venue"),
            status=MatchStatus(data.get("status", "scheduled")),
        )

        # 设置时间
        if data.get("match_time"):
            match.match_time = datetime.fromisoformat(data["match_time"])

        # 设置比分
        if data.get("current_score"):
            score = data["current_score"]
            match.current_score = MatchScore(
                home_score=score.get("home", 0), away_score=score.get("away", 0)
            )

        # 更新时间戳
        if data.get("created_at"):
            match.created_at = datetime.fromisoformat(data["created_at"])
        if data.get("updated_at"):
            match.updated_at = datetime.fromisoformat(data["updated_at"])

        return match
