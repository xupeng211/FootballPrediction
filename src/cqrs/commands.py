from datetime import datetime
from typing import Any

from src.database.models import Match, Prediction, User

from .base import ValidatableCommand, ValidationResult

"""
命令定义
Command Definitions

定义所有写操作命令.
Defines all write operation commands.
"""


class CreatePredictionCommand(ValidatableCommand):
    """创建预测命令"""

    def __init__(
        self,
        match_id: int,
        user_id: int,
        predicted_home: int,
        predicted_away: int,
        confidence: float,
        strategy_used: str | None = None,
        notes: str | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        super().__init__(metadata)
        self.match_id = match_id
        self.user_id = user_id
        self.predicted_home = predicted_home
        self.predicted_away = predicted_away
        self.confidence = confidence
        self.strategy_used = strategy_used
        self.notes = notes

    async def validate(self) -> ValidationResult:
        """验证命令"""
        errors = []

        # 验证预测值
        if self.predicted_home < 0:
            errors.append("主队预测得分不能为负数")
        if self.predicted_away < 0:
            errors.append("客队预测得分不能为负数")

        # 验证置信度
        if not (0 <= self.confidence <= 1):
            errors.append("置信度必须在0到1之间")

        # 验证比赛和用户是否存在
        # 在实际应用中,这些验证应该在服务层处理
        # 这里仅做基本验证

        return (
            ValidationResult.success()
            if not errors
            else ValidationResult.failure(errors)
        )


class UpdatePredictionCommand(ValidatableCommand):
    """更新预测命令"""

    def __init__(
        self,
        prediction_id: int,
        predicted_home: int | None = None,
        predicted_away: int | None = None,
        confidence: float | None = None,
        strategy_used: str | None = None,
        notes: str | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        super().__init__(metadata)
        self.prediction_id = prediction_id
        self.predicted_home = predicted_home
        self.predicted_away = predicted_away
        self.confidence = confidence
        self.strategy_used = strategy_used
        self.notes = notes

    async def validate(self) -> ValidationResult:
        """验证命令"""
        errors = []

        # 验证预测是否存在
        from ..database.connection_mod import get_session

        async with get_session() as session:
            prediction = await session.get(Prediction, self.prediction_id)
            if not prediction:
                errors.append("指定的预测不存在")
            elif prediction.match.match_date < datetime.utcnow():
                errors.append("无法更新已结束比赛的预测")

        # 验证预测值
        if self.predicted_home is not None and self.predicted_home < 0:
            errors.append("主队预测得分不能为负数")
        if self.predicted_away is not None and self.predicted_away < 0:
            errors.append("客队预测得分不能为负数")

        # 验证置信度
        if self.confidence is not None and not (0 <= self.confidence <= 1):
            errors.append("置信度必须在0到1之间")

        return (
            ValidationResult.success()
            if not errors
            else ValidationResult.failure(errors)
        )


class DeletePredictionCommand(ValidatableCommand):
    """删除预测命令"""

    def __init__(
        self,
        prediction_id: int,
        metadata: dict[str, Any] | None = None,
    ):
        super().__init__(metadata)
        self.prediction_id = prediction_id

    async def validate(self) -> ValidationResult:
        """验证命令"""
        errors = []

        # 验证预测是否存在
        from ..database.connection_mod import get_session

        async with get_session() as session:
            prediction = await session.get(Prediction, self.prediction_id)
            if not prediction:
                errors.append("指定的预测不存在")
            elif prediction.match.match_date < datetime.utcnow():
                errors.append("无法删除已结束比赛的预测")

        return (
            ValidationResult.success()
            if not errors
            else ValidationResult.failure(errors)
        )


class CreateUserCommand(ValidatableCommand):
    """创建用户命令"""

    def __init__(
        self,
        username: str,
        email: str,
        password_hash: str,
        metadata: dict[str, Any] | None = None,
    ):
        super().__init__(metadata)
        self.username = username
        self.email = email
        self.password_hash = password_hash

    async def validate(self) -> ValidationResult:
        """验证命令"""
        errors = []

        # 验证用户名
        if not self.username or len(self.username) < 3:
            errors.append("用户名至少需要3个字符")

        # 验证邮箱
        if not self.email or "@" not in self.email:
            errors.append("邮箱格式不正确")

        # 验证密码哈希
        if not self.password_hash:
            errors.append("密码哈希不能为空")

        # 验证用户名唯一性
        from ..database.connection_mod import get_session

        async with get_session() as session:
            existing_user = await session.execute(
                "SELECT id FROM users WHERE username = :username",
                {"username": self.username},
            )
            if existing_user.scalar():
                errors.append("用户名已存在")

        return (
            ValidationResult.success()
            if not errors
            else ValidationResult.failure(errors)
        )


class UpdateUserCommand(ValidatableCommand):
    """更新用户命令"""

    def __init__(
        self,
        user_id: int,
        username: str | None = None,
        email: str | None = None,
        is_active: bool | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        super().__init__(metadata)
        self.user_id = user_id
        self.username = username
        self.email = email
        self.is_active = is_active

    async def validate(self) -> ValidationResult:
        """验证命令"""
        errors = []

        # 验证用户是否存在
        from ..database.connection_mod import get_session

        async with get_session() as session:
            user = await session.get(User, self.user_id)
            if not user:
                errors.append("指定的用户不存在")

        return (
            ValidationResult.success()
            if not errors
            else ValidationResult.failure(errors)
        )


class CreateMatchCommand(ValidatableCommand):
    """创建比赛命令"""

    def __init__(
        self,
        home_team: str,
        away_team: str,
        match_date: datetime,
        competition: str | None = None,
        venue: str | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        super().__init__(metadata)
        self.home_team = home_team
        self.away_team = away_team
        self.match_date = match_date
        self.competition = competition
        self.venue = venue

    async def validate(self) -> ValidationResult:
        """验证命令"""
        errors = []

        # 验证队伍名称
        if not self.home_team:
            errors.append("主队名称不能为空")
        if not self.away_team:
            errors.append("客队名称不能为空")
        if self.home_team == self.away_team:
            errors.append("主队和客队不能相同")

        # 验证比赛日期
        if self.match_date < datetime.utcnow():
            errors.append("比赛日期不能是过去的时间")

        return (
            ValidationResult.success()
            if not errors
            else ValidationResult.failure(errors)
        )


class UpdateMatchCommand(ValidatableCommand):
    """更新比赛命令"""

    def __init__(
        self,
        match_id: int,
        home_score: int | None = None,
        away_score: int | None = None,
        status: str | None = None,
        competition: str | None = None,
        venue: str | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        super().__init__(metadata)
        self.match_id = match_id
        self.home_score = home_score
        self.away_score = away_score
        self.status = status
        self.competition = competition
        self.venue = venue

    async def validate(self) -> ValidationResult:
        """验证命令"""
        errors = []

        # 验证比赛是否存在
        from ..database.connection_mod import get_session

        async with get_session() as session:
            match = await session.get(Match, self.match_id)
            if not match:
                errors.append("指定的比赛不存在")

        # 验证比分
        if self.home_score is not None and self.home_score < 0:
            errors.append("主队得分不能为负数")
        if self.away_score is not None and self.away_score < 0:
            errors.append("客队得分不能为负数")

        return (
            ValidationResult.success()
            if not errors
            else ValidationResult.failure(errors)
        )
