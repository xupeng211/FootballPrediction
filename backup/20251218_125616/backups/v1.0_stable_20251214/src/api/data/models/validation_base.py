"""数据验证基础工具和常量
Data Validation Base Utilities and Constants.

提供通用的验证工具函数和常量定义.
"""

    """清理球队名称.

    Args:
        name: 原始球队名称

    Returns:
        清理后的球队名称
    """
    """验证日期范围.

    Args:
        date: 待验证的日期
        min_year: 最小年份
        max_year: 最大年份

    Returns:
        验证后的日期

    Raises:
        ValueError: 日期超出范围
    """
    """验证比分一致性.

    Args:
        home_score: 主队得分
        away_score: 客队得分
        status: 比赛状态

    Returns:
        验证后的比分元组

    Raises:
        ValueError: 比分不一致
    """
    """验证赔率范围.

    Args:
        odds_value: 赔率值
        min_value: 最小值
        max_value: 最大值

    Returns:
        验证后的赔率值

    Raises:
        ValueError: 赔率超出范围
    """
    """检测套利机会.

    Args:
        home_win: 主胜赔率
        draw: 平局赔率
        away_win: 客胜赔率

    Returns:
        是否存在套利机会
    """
    """验证时间顺序.

    Args:
        start_time: 开始时间
        end_time: 结束时间

    Returns:
        验证后的时间元组

    Raises:
        ValueError: 时间顺序错误
    """
    """创建名称清理验证器."""

    @field_validator(field_name, mode="before")
    @classmethod
    def clean_name(cls, v: Any) -> Any:
        if isinstance(v, str):
            return clean_team_name(v)
        return v

    return clean_name


def validate_positive_numbers(*field_names: str):
    """创建正数验证器."""
    """比赛状态常量."""

    VALID_STATUSES = {
        'SCHEDULED', 'LIVE', 'FINISHED', 'CANCELLED', 'POSTPONED', 'ABANDONED',
        'scheduled', 'live', 'finished', 'cancelled', 'postponed', 'abandoned'
    }

    FINISHED_STATUSES = {'FINISHED', 'finished'}

    LIVE_STATUSES = {'LIVE', 'live'}

    UPCOMING_STATUSES = {'SCHEDULED', 'scheduled'}


class ValidationResult:
    """验证结果."""
        """添加错误."""
        self.errors.append(error)
        self.is_valid = False

    def add_warning(self, warning: str):
        """添加警告."""
        """转换为字典."""
        return {
            'is_valid': self.is_valid,
            'errors': self.errors,
            'warnings': self.warnings
        }


# 第三方库导入
from datetime import datetime
from pydantic import ValidationInfo, field_validator
import re
import unicodedata


def clean_team_name(name: str) -> str:
    if not name:
        return name
    # 去除首尾空格
    cleaned = name.strip()
    # 移除不可见字符（除了常规空格）
    cleaned = ''.join(
        char for char in cleaned
        if char.isprintable() or char == ' '
    )
    # 标准化Unicode字符
    cleaned = unicodedata.normalize('NFKC', cleaned)
    # 去除多余空格
    cleaned = re.sub(r'\s+', ' ', cleaned)
    return cleaned
def validate_date_range(date: datetime, min_year: int = 1990, max_year: int = 2030) -> datetime:
    if date.year < min_year or date.year > max_year:
        raise ValueError(f"日期必须在 {min_year} 年到 {max_year} 年之间，当前为 {date.year} 年")
    return date
def validate_score_consistency(home_score: int, away_score: int, status: str) -> tuple[int, int]:
    if home_score < 0 or away_score < 0:
        raise ValueError("比分不能为负数")
    if status.lower() == 'finished' and (home_score is None or away_score is None):
        raise ValueError("已完成的比赛必须有有效的比分")
    return home_score, away_score
def validate_odds_range(odds_value: float, min_value: float = 1.0, max_value: float = 1000.0) -> float:
    if odds_value <= 0:
        raise ValueError("赔率必须为正数")
    if odds_value < min_value:
        raise ValueError(f"赔率不能小于 {min_value}")
    if odds_value > max_value:
        raise ValueError(f"赔率不能大于 {max_value}")
    return odds_value
def detect_arbitrage_opportunity(home_win: float, draw: float, away_win: float) -> bool:
    try:
        # 计算三项赔率的倒数之和
        implied_probability = (1/home_win) + (1/draw) + (1/away_win)
        return implied_probability < 1.0
    except (ZeroDivisionError, ValueError):
        return False
def time_order_validator(start_time: datetime, end_time: datetime) -> tuple[datetime, datetime]:
    if end_time and start_time and end_time <= start_time:
        raise ValueError("结束时间必须晚于开始时间")
    return start_time, end_time
# 常用的Pydantic验证器装饰器
def validate_name_cleaning(field_name: str = "name"):
    validators = []
    for field_name in field_names:
        @field_validator(field_name)
        @classmethod
        def validate_positive(cls, v: Any) -> Any:
            if v is not None and (not isinstance(v, (int, float)) or v < 0):
                raise ValueError(f"{field_name} 必须为非负数")
            return v
        validators.append(validate_positive)
    return validators
# 常用的业务状态常量
class MatchStatusConstants:
    def __init__(self, is_valid: bool, errors: list[str] = None, warnings: list[str] = None):
        self.is_valid = is_valid
        self.errors = errors or []
        self.warnings = warnings or []
    def add_error(self, error: str):
        self.warnings.append(warning)
    def to_dict(self) -> dict: