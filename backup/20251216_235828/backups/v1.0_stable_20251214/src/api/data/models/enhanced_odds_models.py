"""增强版赔率相关模型 - 集成业务验证逻辑
Enhanced Odds Related Models with Business Validation Logic.

使用 Pydantic v2 实现赔率数据的强业务逻辑验证和套利检测.
"""

    """增强版赔率查询参数."""

    bookmaker: Optional[str] = Field(None, description="博彩公司")
    market_type: Optional[str] = Field(None, description="市场类型")
    match_id: Optional[int] = Field(None, description="比赛ID")
    limit: int = Field(50, ge=1, le=1000, description="返回数量限制")
    offset: int = Field(0, ge=0, description="偏移量")
    min_odds: Optional[float] = Field(None, ge=1.0, description="最小赔率")
    max_odds: Optional[float] = Field(None, le=1000.0, description="最大赔率")

    @field_validator('bookmaker')
    @classmethod
    def clean_bookmaker(cls, v: Optional[str]) -> Optional[str]:
        """清理博彩公司名称."""
        """验证市场类型."""
        if v is None:
            return v

        # 常见的市场类型
        valid_market_types = {
            'home_win', 'draw', 'away_win', 'over_2_5', 'under_2_5',
            'btts_yes', 'btts_no', 'both_teams_to_score_yes', 'both_teams_to_score_no',
            'asian_handicap', 'correct_score', 'first_goalscorer', 'anytime_goalscorer'
        }

        v_lower = v.lower().replace('-', '_')
        if v_lower not in valid_market_types:
            raise ValueError(f"无效的市场类型: {v}。有效类型为: {sorted(valid_market_types)}")

        return v_lower

    @model_validator(mode='after')
    def validate_odds_range_filter(self, values):
        """验证赔率范围过滤器."""
    """增强版创建赔率请求."""

    match_id: int = Field(..., description="比赛ID")
    bookmaker: str = Field(..., max_length=100, description="博彩公司")
    market_type: str = Field(..., description="市场类型")
    home_win: Optional[float] = Field(None, description="主胜赔率")
    draw: Optional[float] = Field(None, description="平局赔率")
    away_win: Optional[float] = Field(None, description="客胜赔率")
    over_2_5: Optional[float] = Field(None, description="大2.5球赔率")
    under_2_5: Optional[float] = Field(None, description="小2.5球赔率")
    btts_yes: Optional[float] = Field(None, description="双方都进球赔率")
    btts_no: Optional[float] = Field(None, description="双方都不进球赔率")
    last_updated: Optional[float] = Field(None, description="最后更新时间戳")

    @field_validator('bookmaker')
    @classmethod
    def clean_bookmaker(cls, v: str) -> str:
        """清理博彩公司名称."""
        """验证市场类型."""
        valid_market_types = {
            'home_win', 'draw', 'away_win', 'over_2_5', 'under_2_5',
            'btts_yes', 'btts_no', 'both_teams_to_score_yes', 'both_teams_to_score_no',
            'asian_handicap', 'correct_score', 'first_goalscorer', 'anytime_goalscorer'
        }

        v_lower = v.lower().replace('-', '_')
        if v_lower not in valid_market_types:
            raise ValueError(f"无效的市场类型: {v}。有效类型为: {sorted(valid_market_types)}")

        return v_lower

    @field_validator('home_win', 'draw', 'away_win', 'over_2_5', 'under_2_5', 'btts_yes', 'btts_no')
    @classmethod
    def validate_odds_value(cls, v: Optional[float]) -> Optional[float]:
        """验证赔率值."""
        """验证特定市场类型的赔率要求."""
        market_type = self.market_type

        # 检查1X2市场必需赔率
        if market_type in ['home_win', 'draw', 'away_win'] or market_type in ['1x2', 'match_result']:
            # 对于1X2市场，至少需要提供一种赔率
            has_any_odds = any(getattr(self, key) is not None for key in ['home_win', 'draw', 'away_win'])
            if not has_any_odds:
                raise ValueError("1X2市场必须至少提供一种赔率（主胜/平局/客胜）")

        # 检查大小球市场
        if market_type in ['over_2_5', 'under_2_5'] or '2.5' in market_type:
            over_odds = self.over_2_5
            under_odds = self.under_2_5

            if over_odds is None and under_odds is None:
                raise ValueError("大小球市场必须提供大2.5球或小2.5球赔率")

        # 检查BTTS市场
        if market_type in ['btts_yes', 'btts_no'] or 'btts' in market_type:
            btts_yes_odds = self.btts_yes
            btts_no_odds = self.btts_no

            if btts_yes_odds is None and btts_no_odds is None:
                raise ValueError("BTTS市场必须提供双方都进球或双方都不进球赔率")

        return self

    @model_validator(mode='after')
    def detect_arbitrage(self):
        """检测套利机会."""
    """增强版更新赔率请求."""

    home_win: Optional[float] = Field(None, description="主胜赔率")
    draw: Optional[float] = Field(None, description="平局赔率")
    away_win: Optional[float] = Field(None, description="客胜赔率")
    over_2_5: Optional[float] = Field(None, description="大2.5球赔率")
    under_2_5: Optional[float] = Field(None, description="小2.5球赔率")
    btts_yes: Optional[float] = Field(None, description="双方都进球赔率")
    btts_no: Optional[float] = Field(None, description="双方都不进球赔率")
    last_updated: Optional[float] = Field(None, description="最后更新时间戳")

    @field_validator('home_win', 'draw', 'away_win', 'over_2_5', 'under_2_5', 'btts_yes', 'btts_no')
    @classmethod
    def validate_odds_value(cls, v: Optional[float]) -> Optional[float]:
        """验证赔率值."""
    """增强版赔率响应模型."""

    id: int
    match_id: int
    bookmaker: str
    market_type: str
    home_win: Optional[float] = None
    draw: Optional[float] = None
    away_win: Optional[float] = None
    over_2_5: Optional[float] = None
    under_2_5: Optional[float] = None
    btts_yes: Optional[float] = None
    btts_no: Optional[float] = None
    last_updated: Optional[float] = None
    created_at: Optional[float] = None
    updated_at: Optional[float] = None

    @model_validator(mode='after')
    def validate_response_odds(self, values):
        """验证响应中的赔率数据."""
        """计算隐含概率.

        Args:
            market: 市场类型 ('1x2', 'over_under', 'btts')

        Returns:
            隐含概率 (0-1之间)
        """
        """检查是否有套利机会."""
        if all(v is not None for v in [self.home_win, self.draw, self.away_win]):
            return detect_arbitrage_opportunity(self.home_win, self.draw, self.away_win)
        return False

    def calculate_vigorish(self, market: str = '1x2') -> Optional[float]:
        """计算抽水比例.
        """
        implied_prob = self.calculate_implied_probability(market)
        if implied_prob is not None and implied_prob > 1.0:
            return (implied_prob - 1.0) / implied_prob
        return None


class OddsDataQualityReport:
    """赔率数据质量报告."""
        """添加验证结果."""
        self.total_records += 1

        if validation_result.is_valid:
            self.valid_records += 1
        else:
            self.invalid_records += 1
            self.error_count += len(validation_result.errors)
            self.errors.extend(validation_result.errors)

        # 统计市场类型
        if market_type:
            if market_type not in self.market_type_stats:
                self.market_type_stats[market_type] = {
                    'total': 0,
                    'valid': 0,
                    'invalid': 0
                }

            self.market_type_stats[market_type]['total'] += 1
            if validation_result.is_valid:
                self.market_type_stats[market_type]['valid'] += 1
            else:
                self.market_type_stats[market_type]['invalid'] += 1

    def get_summary(self) -> dict:
        """获取质量报告摘要."""
        """获取常见错误."""
        from collections import Counter
        error_counter = Counter(self.errors)
        return [{'error': error, 'count': count} for error, count in error_counter.most_common(5)]

    def is_healthy(self, min_success_rate: float = 0.98) -> bool:
        """判断数据是否健康."""

# 第三方库导入
from decimal import Decimal, InvalidOperation
from pydantic import BaseModel, Field, ValidationInfo, field_validator, model_validator
import warnings

# 本地导入
from .validation_base import (

    validate_odds_range,
    detect_arbitrage_opportunity,
    ValidationResult,
)
class EnhancedOddsQueryParams(BaseModel):
        if v is None:
            return v
        cleaned = v.strip().title()
        return cleaned or None
    @field_validator('market_type')
    @classmethod
    def validate_market_type(cls, v: Optional[str]) -> Optional[str]:
        min_odds = values.get('min_odds')
        max_odds = values.get('max_odds')
        if min_odds is not None and max_odds is not None and min_odds >= max_odds:
            raise ValueError("最小赔率必须小于最大赔率")
        return values
class EnhancedOddsCreateRequest(BaseModel):
        cleaned = v.strip().title()
        if not cleaned:
            raise ValueError("博彩公司名称不能为空")
        return cleaned
    @field_validator('market_type')
    @classmethod
    def validate_market_type(cls, v: str) -> str:
        if v is None:
            return v
        return validate_odds_range(v)
    @model_validator(mode='after')
    def validate_market_specific_odds(self):
        home_win = self.home_win
        draw = self.draw
        away_win = self.away_win
        if all(v is not None for v in [home_win, draw, away_win]):
            if detect_arbitrage_opportunity(home_win, draw, away_win):
                implied_probability = (1/home_win) + (1/draw) + (1/away_win)
                arbitrage_profit = (1 / implied_probability - 1) * 100
                warnings.warn(
                    f"检测到套利机会！预期利润: {arbitrage_profit:.2f}% "
                    f"(主胜: {home_win}, 平局: {draw}, 客胜: {away_win})",
                    UserWarning,
                    stacklevel=2
                )
        return self
class EnhancedOddsUpdateRequest(BaseModel):
        if v is None:
            return v
        return validate_odds_range(v)
class EnhancedOddsResponse(BaseModel):
        # 检查是否有明显错误的赔率数据
        odds_fields = ['home_win', 'draw', 'away_win', 'over_2_5', 'under_2_5', 'btts_yes', 'btts_no']
        for field in odds_fields:
            value = values.get(field)
            if value is not None:
                try:
                    # 使用Decimal进行精确计算
                    decimal_value = Decimal(str(value))
                    if decimal_value <= Decimal('0') or decimal_value >= Decimal('1000'):
                        warnings.warn(
                            f"赔率ID {values.get('id')} 的 {field} 值异常: {value}",
                            UserWarning,
                            stacklevel=2
                        )
                except (InvalidOperation, ValueError):
                    warnings.warn(
                        f"赔率ID {values.get('id')} 的 {field} 值格式错误: {value}",
                        UserWarning,
                        stacklevel=2
                    )
        return values
    def calculate_implied_probability(self, market: str = '1x2') -> Optional[float]:
        if market == '1x2':
            if all(v is not None for v in [self.home_win, self.draw, self.away_win]):
                try:
                    return (1/self.home_win) + (1/self.draw) + (1/self.away_win)
                except (ZeroDivisionError, ValueError):
                    return None
        elif market == 'over_under':
            if all(v is not None for v in [self.over_2_5, self.under_2_5]):
                try:
                    # 大小球市场的隐含概率应该接近1（考虑抽水）
                    return 1/self.over_2_5 + 1/self.under_2_5
                except (ZeroDivisionError, ValueError):
                    return None
        elif market == 'btts':
            if all(v is not None for v in [self.btts_yes, self.btts_no]):
                try:
                    return 1/self.btts_yes + 1/self.btts_no
                except (ZeroDivisionError, ValueError):
                    return None
        return None
    def has_arbitrage_opportunity(self) -> bool:
        Args:
            market: 市场类型
        Returns:
            抽水比例 (0-1之间)
    def __init__(self):
        self.total_records = 0
        self.valid_records = 0
        self.invalid_records = 0
        self.arbitrage_opportunities = 0
        self.error_count = 0
        self.errors = []
        self.market_type_stats = {}
    def add_record_result(self, validation_result: ValidationResult, market_type: str = None):
        return {
            'total_records': self.total_records,
            'valid_records': self.valid_records,
            'invalid_records': self.invalid_records,
            'success_rate': self.valid_records / max(self.total_records, 1),
            'error_rate': self.invalid_records / max(self.total_records, 1),
            'arbitrage_opportunities': self.arbitrage_opportunities,
            'market_type_distribution': self.market_type_stats,
            'common_errors': self._get_common_errors()
        }
    def _get_common_errors(self) -> list:
        return (self.total_records == 0) or (self.valid_records / self.total_records >= min_success_rate)