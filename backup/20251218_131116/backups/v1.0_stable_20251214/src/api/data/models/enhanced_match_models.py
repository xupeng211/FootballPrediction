"""增强版比赛相关模型 - 集成业务验证逻辑
Enhanced Match Related Models with Business Validation Logic.

使用 Pydantic v2 的 field_validator 和 model_validator 实现强业务逻辑验证.
"""

    """增强版比赛查询参数."""

    league_id: Optional[int] = Field(None, description="联赛ID")
    team_id: Optional[int] = Field(None, description="球队ID")
    status: Optional[str] = Field(None, description="比赛状态")
    start_date: Optional[datetime] = Field(None, description="开始日期")
    end_date: Optional[datetime] = Field(None, description="结束日期")
    limit: int = Field(50, ge=1, le=1000, description="返回数量限制")
    offset: int = Field(0, ge=0, description="偏移量")

    @field_validator('status')
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        """验证比赛状态."""
        """验证日期范围."""
        start_date = values.get('start_date')
        end_date = values.get('end_date')

        if start_date and end_date:
            if start_date > end_date:
                raise ValueError("开始日期不能晚于结束日期")

        # 验证日期在合理范围内
        if start_date:
            validate_date_range(start_date)
        if end_date:
            validate_date_range(end_date)

        return values


class EnhancedMatchCreateRequest(BaseModel):
    """增强版创建比赛请求."""
        """验证比赛状态."""
        if v.upper() not in MatchStatusConstants.VALID_STATUSES:
            raise ValueError(f"无效的比赛状态: {v}。有效状态为: {sorted(MatchStatusConstants.VALID_STATUSES)}")
        return v.upper()

    @field_validator('venue')
    @classmethod
    def clean_venue(cls, v: Optional[str]) -> Optional[str]:
        """清理比赛场地名称."""
        """验证比赛一致性."""
        # 验证时间顺序
        match_time = self.match_time
        end_time = self.end_time
        if match_time and end_time:
            time_order_validator(match_time, end_time)

        # 验证日期范围
        if match_time:
            validate_date_range(match_time)
        if end_time:
            validate_date_range(end_time)

        # 验证比分一致性
        status = self.status
        home_score = self.home_score
        away_score = self.away_score
        home_half_score = self.home_half_score
        away_half_score = self.away_half_score

        if status in MatchStatusConstants.FINISHED_STATUSES:
            if home_score is None or away_score is None:
                raise ValueError("已完成的比赛必须有完整的比分")

        # 验证比分合理性
        if home_score is not None and away_score is not None:
            validate_score_consistency(home_score, away_score, status)

        # 验证半场比分
        if home_half_score is not None and away_half_score is not None:
            validate_score_consistency(home_half_score, away_half_score, status)

        # 验证半场比分不能超过全场比分
        if (home_score is not None and home_half_score is not None and
            away_score is not None and away_half_score is not None):

            if home_half_score > home_score:
                raise ValueError("半场主队得分不能超过全场主队得分")

            if away_half_score > away_score:
                raise ValueError("半场客队得分不能超过全场客队得分")

        # 验证球队不能相同
        home_team_id = self.home_team_id
        away_team_id = self.away_team_id
        if home_team_id == away_team_id:
            raise ValueError("主队和客队不能相同")

        return self


class EnhancedMatchUpdateRequest(BaseModel):
    """增强版更新比赛请求."""
        """验证比赛状态."""
        if v is None:
            return v

        if v.upper() not in MatchStatusConstants.VALID_STATUSES:
            raise ValueError(f"无效的比赛状态: {v}。有效状态为: {sorted(MatchStatusConstants.VALID_STATUSES)}")

        return v.upper()

    @field_validator('venue')
    @classmethod
    def clean_venue(cls, v: Optional[str]) -> Optional[str]:
        """清理比赛场地名称."""
        """验证更新一致性."""
        # 只有提供的字段才进行验证
        status = values.get('status')
        home_score = values.get('home_score')
        away_score = values.get('away_score')
        home_half_score = values.get('home_half_score')
        away_half_score = values.get('away_half_score')

        # 如果状态更新为已完成，必须有比分
        if status in MatchStatusConstants.FINISHED_STATUSES:
            if home_score is None or away_score is None:
                raise ValueError("更新状态为已完成时，必须提供完整的比分")

        # 验证比分一致性
        if home_score is not None and away_score is not None:
            if status:
                validate_score_consistency(home_score, away_score, status)

        # 验证半场比分
        if home_half_score is not None and away_half_score is not None:
            if status:
                validate_score_consistency(home_half_score, away_half_score, status)

        return values


class EnhancedMatchResponse(BaseModel):
    """增强版比赛响应模型."""
        """验证响应数据的一致性."""
        # 确保从数据库返回的数据也符合业务规则
        status = values.get('status', '')
        home_score = values.get('home_score')
        away_score = values.get('away_score')

        if status in MatchStatusConstants.FINISHED_STATUSES:
            if home_score is None or away_score is None:
                warnings.warn(
                    f"比赛ID {values.get('id')} 状态为已完成但缺少比分数据",
                    UserWarning,
                    stacklevel=2
                )

        return values


class MatchDataQualityReport:
    """比赛数据质量报告."""
        """添加验证结果."""
        self.total_records += 1

        if validation_result.is_valid:
            self.valid_records += 1
        else:
            self.invalid_records += 1

        self.warnings_count += len(validation_result.warnings)
        self.errors.extend(validation_result.errors)
        self.warnings.extend(validation_result.warnings)

    def get_summary(self) -> dict:
        """获取质量报告摘要."""
        """获取常见错误."""
        from collections import Counter
        error_counter = Counter(self.errors)
        return [{'error': error, 'count': count} for error, count in error_counter.most_common(5)]

    def _get_common_warnings(self) -> list:
        """获取常见警告."""
        """判断数据是否健康."""
        return (self.total_records == 0) or (self.valid_records / self.total_records >= min_success_rate)


# 第三方库导入
        from collections import Counter
from datetime import datetime
from pydantic import BaseModel, Field, ValidationInfo, field_validator, model_validator
import warnings

# 本地导入
from .validation_base import (

    MatchStatusConstants,
    ValidationResult,
    validate_date_range,
    validate_score_consistency,
    time_order_validator,
)
class EnhancedMatchQueryParams(BaseModel):
        if v is None:
            return v
        if v.upper() not in MatchStatusConstants.VALID_STATUSES:
            raise ValueError(f"无效的比赛状态: {v}。有效状态为: {sorted(MatchStatusConstants.VALID_STATUSES)}")
        return v.upper()
    @model_validator(mode='after')
    def validate_date_range(self, values):
    home_team_id: int = Field(..., description="主队ID")
    away_team_id: int = Field(..., description="客队ID")
    league_id: int = Field(..., description="联赛ID")
    match_time: datetime = Field(..., description="比赛时间")
    end_time: Optional[datetime] = Field(None, description="结束时间")
    venue: Optional[str] = Field(None, max_length=200, description="比赛场地")
    status: str = Field("SCHEDULED", description="比赛状态")
    home_score: Optional[int] = Field(None, ge=0, description="主队得分")
    away_score: Optional[int] = Field(None, ge=0, description="客队得分")
    home_half_score: Optional[int] = Field(None, ge=0, description="主队半场得分")
    away_half_score: Optional[int] = Field(None, ge=0, description="客队半场得分")
    @field_validator('status')
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v is None:
            return v
        # 去除首尾空格和不可见字符
        cleaned = v.strip()
        cleaned = ''.join(char for char in cleaned if char.isprintable() or char == ' ')
        return cleaned or None
    @model_validator(mode='after')
    def validate_match_consistency(self):
    match_time: Optional[datetime] = Field(None, description="比赛时间")
    end_time: Optional[datetime] = Field(None, description="结束时间")
    venue: Optional[str] = Field(None, max_length=200, description="比赛场地")
    home_score: Optional[int] = Field(None, ge=0, description="主队得分")
    away_score: Optional[int] = Field(None, ge=0, description="客队得分")
    home_half_score: Optional[int] = Field(None, ge=0, description="主队半场得分")
    away_half_score: Optional[int] = Field(None, ge=0, description="客队半场得分")
    status: Optional[str] = Field(None, description="比赛状态")
    @field_validator('status')
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        cleaned = v.strip()
        cleaned = ''.join(char for char in cleaned if char.isprintable() or char == ' ')
        return cleaned or None
    @model_validator(mode='after')
    def validate_update_consistency(self, values):
    id: int
    home_team_id: int
    away_team_id: int
    league_id: int
    match_time: datetime
    end_time: Optional[datetime] = None
    venue: Optional[str] = None
    status: str
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    home_half_score: Optional[int] = None
    away_half_score: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    @model_validator(mode='after')
    def validate_response_data(self, values):
    def __init__(self):
        self.total_records = 0
        self.valid_records = 0
        self.invalid_records = 0
        self.warnings_count = 0
        self.errors = []
        self.warnings = []
    def add_record_result(self, validation_result: ValidationResult):
        return {
            'total_records': self.total_records,
            'valid_records': self.valid_records,
            'invalid_records': self.invalid_records,
            'warnings_count': self.warnings_count,
            'success_rate': self.valid_records / max(self.total_records, 1),
            'error_rate': self.invalid_records / max(self.total_records, 1),
            'common_errors': self._get_common_errors(),
            'common_warnings': self._get_common_warnings()
        }
    def _get_common_errors(self) -> list:
        warning_counter = Counter(self.warnings)
        return [{'warning': warning, 'count': count} for warning, count in warning_counter.most_common(5)]
    def is_healthy(self, min_success_rate: float = 0.95) -> bool: