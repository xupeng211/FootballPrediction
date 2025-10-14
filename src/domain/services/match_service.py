"""
比赛领域服务
Match Domain Service

处理比赛相关的复杂业务逻辑。
Handles complex business logic related to matches.
"""

from typing import Any, List[Any], Optional
from datetime import datetime

from ..models.match import MatchScore, MatchResult
from ..models.match import Match, MatchStatus
from ..models.team import Team
from ..events.match_events import (
    MatchStartedEvent,
    MatchFinishedEvent,
    MatchCancelledEvent,
    MatchPostponedEvent,
)


class MatchDomainService:
    """比赛领域服务"""

    def __init__(self) -> None:
        self._events: List[Any] = {}]

    def schedule_match(
        self,
        home_team: Team,
        away_team: Team,
        match_time: datetime,
        venue: Optional[str] ] = None,
        round_number: Optional[int] ] = None,
    ) -> Match:
        """安排新比赛"""
        if home_team.id == away_team.id:
            raise ValueError("主队和客队不能是同一支球队")

        # 检查球队是否已经在同一时间有比赛
        # 这里简化处理，实际应该查询数据库

        if home_team.id is None or away_team.id is None:
            raise ValueError("球队ID不能为空")

        match = Match(
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            match_date=match_time,
            venue=venue,
        )

        return match

    def start_match(self, match: Match) -> None:
        """开始比赛"""
        if match.status != MatchStatus.SCHEDULED:
            raise ValueError(f"比赛状态为 {match.status.value}，无法开始")

        if datetime.utcnow() < match.match_date:
            raise ValueError("比赛时间还未到")

        match.start_match()

        # 记录领域事件
        event = MatchStartedEvent(
            match_id=match.id or 0,
            home_team_id=match.home_team_id,
            away_team_id=match.away_team_id,
        )
        self._events.append(event)

    def update_match_score(
        self,
        match: Match,
        home_score: int,
        away_score: int,
        minute: Optional[int] ] = None,
    ) -> None:
        """更新比赛比分"""
        if match.status != MatchStatus.LIVE:
            raise ValueError("只有进行中的比赛才能更新比分")

        if home_score < 0 or away_score < 0:
            raise ValueError("比分不能为负数")

        match.update_score(home_score, away_score)

        # 可以记录进球事件
        # event = GoalScoredEvent(...)
        # self._events.append(event)

    def finish_match(self, match: Match) -> None:
        """结束比赛"""
        if match.status != MatchStatus.LIVE:
            raise ValueError("只有进行中的比赛才能结束")

        match.finish_match()

        # 记录领域事件
        if match.score:
            event = MatchFinishedEvent(
                match_id=match.id or 0,
                home_team_id=match.home_team_id,
                away_team_id=match.away_team_id,
                final_score=match.score or MatchScore(0, 0),
                result =match.score.result if match.score else MatchResult.DRAW,
            )
            self._events.append(event)

    def cancel_match(self, match: Match, reason: str) -> None:
        """取消比赛"""
        if match.status in [MatchStatus.FINISHED, MatchStatus.CANCELLED]:
            raise ValueError(f"比赛状态为 {match.status.value}，无法取消")

        match.status = MatchStatus.CANCELLED

        # 记录领域事件
        event = MatchCancelledEvent(match_id=match.id or 0, reason=reason)
        self._events.append(event)

    def postpone_match(self, match: Match, new_date: datetime, reason: str) -> None:
        """延期比赛"""
        if match.status in [MatchStatus.FINISHED, MatchStatus.CANCELLED]:
            raise ValueError(f"比赛状态为 {match.status.value}，无法延期")

        match.status = MatchStatus.POSTPONED
        match.match_date = new_date

        # 记录领域事件
        event = MatchPostponedEvent(
            match_id=match.id or 0,
            new_date=new_date.isoformat(),
            reason=reason,
        )
        self._events.append(event)

    def validate_match_schedule(self, match: Match) -> List[str]:
        """验证比赛安排"""
        errors = []

        # 检查比赛时间
        if match.match_date <= datetime.utcnow():
            errors.append("比赛时间必须是未来时间")

        # Note: expected_end_time 属性在当前模型中不存在
        # # 检查比赛时长（通常90分钟）
        # if match.match_date and match.expected_end_time:
        #     duration = match.expected_end_time - match.match_date
        #     if duration.total_seconds() < 5400:  # 90分钟
        #         errors.append("比赛时长不能少于90分钟")

        # 检查场地
        if not match.venue:
            errors.append("必须指定比赛场地")

        # Note: round_number 属性在当前模型中不存在
        # # 检查轮次
        # if match.round_number and match.round_number < 1:
        #     errors.append("比赛轮次必须大于0")

        return errors

    def calculate_match_importance(
        self,
        match: Match,
        home_team_position: Optional[int] ] = None,
        away_team_position: Optional[int] ] = None,
        total_teams: Optional[int] ] = None,
    ) -> float:
        """计算比赛重要性"""
        importance = 0.5  # 基础重要性

        # Note: is_knockout 和 is_final 属性在当前模型中不存在
        # # 根据比赛类型调整
        # if match.is_knockout:
        #     importance += 0.3
        # if match.is_final:
        #     importance += 0.2

        # 根据球队排名调整
        if home_team_position and away_team_position and total_teams:
            # 强强对话（前5名）
            if home_team_position <= 5 and away_team_position <= 5:
                importance += 0.2

            # 升级/降级关键战（最后3名）
            if (
                home_team_position >= total_teams - 2
                or away_team_position >= total_teams - 2
            ):
                importance += 0.1

        return min(importance, 1.0)

    def get_domain_events(self) -> List[Any]:
        """获取领域事件"""
        return self._events.copy()

    def clear_domain_events(self) -> None:
        """清除领域事件"""
        self._events.clear()
