from typing import Any, Dict, List, Optional, Union

"""
查询定义
Query Definitions

定义所有读操作查询。
Defines all read operation queries.
"""

from datetime import date
from .base import ValidatableQuery, ValidationResult


class GetPredictionByIdQuery(ValidatableQuery):
    """根据ID获取预测查询"""

    def __init__(
        self,
        prediction_id: int,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(metadata)
        self.prediction_id = prediction_id

    async def validate(self) -> ValidationResult:
        """验证查询"""
        errors = []

        if self.prediction_id <= 0:
            errors.append("预测ID必须为正数")

        return (
            ValidationResult.success()
            if not errors
            else ValidationResult.failure(errors)
        )


class GetPredictionsByUserQuery(ValidatableQuery):
    """获取用户的所有预测查询"""

    def __init__(
        self,
        user_id: int,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(metadata)
        self.user_id = user_id
        self.limit = limit
        self.offset = offset
        self.start_date = start_date
        self.end_date = end_date

    async def validate(self) -> ValidationResult:
        """验证查询"""
        errors = []

        if self.user_id <= 0:
            errors.append("用户ID必须为正数")

        if self.limit is not None and self.limit <= 0:
            errors.append("限制数量必须为正数")

        if self.offset is not None and self.offset < 0:
            errors.append("偏移量不能为负数")

        if self.start_date and self.end_date and self.start_date > self.end_date:
            errors.append("开始日期不能晚于结束日期")

        return (
            ValidationResult.success()
            if not errors
            else ValidationResult.failure(errors)
        )


class GetMatchPredictionsQuery(ValidatableQuery):
    """获取比赛的所有预测查询"""

    def __init__(
        self,
        match_id: int,
        include_user_details: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(metadata)
        self.match_id = match_id
        self.include_user_details = include_user_details

    async def validate(self) -> ValidationResult:
        """验证查询"""
        errors = []

        if self.match_id <= 0:
            errors.append("比赛ID必须为正数")

        return (
            ValidationResult.success()
            if not errors
            else ValidationResult.failure(errors)
        )


class GetUserStatsQuery(ValidatableQuery):
    """获取用户统计查询"""

    def __init__(
        self,
        user_id: int,
        include_predictions: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(metadata)
        self.user_id = user_id
        self.include_predictions = include_predictions

    async def validate(self) -> ValidationResult:
        """验证查询"""
        errors = []

        if self.user_id <= 0:
            errors.append("用户ID必须为正数")

        return (
            ValidationResult.success()
            if not errors
            else ValidationResult.failure(errors)
        )


class GetMatchByIdQuery(ValidatableQuery):
    """根据ID获取比赛查询"""

    def __init__(
        self,
        match_id: int,
        include_predictions: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(metadata)
        self.match_id = match_id
        self.include_predictions = include_predictions

    async def validate(self) -> ValidationResult:
        """验证查询"""
        errors = []

        if self.match_id <= 0:
            errors.append("比赛ID必须为正数")

        return (
            ValidationResult.success()
            if not errors
            else ValidationResult.failure(errors)
        )


class GetUpcomingMatchesQuery(ValidatableQuery):
    """获取即将到来的比赛查询"""

    def __init__(
        self,
        days_ahead: int = 7,
        competition: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(metadata)
        self.days_ahead = days_ahead
        self.competition = competition
        self.limit = limit
        self.offset = offset

    async def validate(self) -> ValidationResult:
        """验证查询"""
        errors = []

        if self.days_ahead <= 0:
            errors.append("提前天数必须为正数")

        if self.limit is not None and self.limit <= 0:
            errors.append("限制数量必须为正数")

        if self.offset is not None and self.offset < 0:
            errors.append("偏移量不能为负数")

        return (
            ValidationResult.success()
            if not errors
            else ValidationResult.failure(errors)
        )


class GetPredictionAnalyticsQuery(ValidatableQuery):
    """获取预测分析查询"""

    def __init__(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        strategy_filter: Optional[str] = None,
        user_id: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(metadata)
        self.start_date = start_date
        self.end_date = end_date
        self.strategy_filter = strategy_filter
        self.user_id = user_id

    async def validate(self) -> ValidationResult:
        """验证查询"""
        errors = []

        if self.start_date and self.end_date and self.start_date > self.end_date:
            errors.append("开始日期不能晚于结束日期")

        if self.user_id is not None and self.user_id <= 0:
            errors.append("用户ID必须为正数")

        return (
            ValidationResult.success()
            if not errors
            else ValidationResult.failure(errors)
        )


class GetLeaderboardQuery(ValidatableQuery):
    """获取排行榜查询"""

    def __init__(
        self,
        period: str = "all_time",  # all_time, monthly, weekly
        limit: Optional[int] = 10,
        offset: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(metadata)
        self.period = period
        self.limit = limit
        self.offset = offset

    async def validate(self) -> ValidationResult:
        """验证查询"""
        errors = []

        valid_periods = ["all_time", "monthly", "weekly"]
        if self.period not in valid_periods:
            errors.append(f"无效的时间段，必须是: {', '.join(valid_periods)}")

        if self.limit is not None and self.limit <= 0:
            errors.append("限制数量必须为正数")

        if self.offset is not None and self.offset < 0:
            errors.append("偏移量不能为负数")

        return (
            ValidationResult.success()
            if not errors
            else ValidationResult.failure(errors)
        )
