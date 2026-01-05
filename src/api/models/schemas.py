#!/usr/bin/env python3
"""V105.0 强类型数据模型 - Pydantic 驱动开发.

定义所有业务数据的严格类型模型，包含：
1. 自动数据验证
2. 类型安全保证
3. 序列化/反序列化支持
4. JSON Schema 生成

Usage:
    >>> from src.api.models.schemas import MarketMetric, VendorOddsData
    >>> metric = MarketMetric(id=18, value=1.85, timestamp=datetime.now())
    >>> metric.validate()
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator, model_validator

# ============================================================================
# 枚举类型定义
# ============================================================================

class DataSource(str, Enum):
    """数据源枚举 - 标准化供应商标识"""

    PINNACLE = "Entity_P"
    WILLIAM_HILL = "Entity_B"
    BET365 = "Entity_W"
    LADBROKES = "Entity_L"
    AVERAGE = "Entity_AVG"


class VendorID(str, Enum):
    """供应商 ID 枚举"""

    PINNACLE = "18"
    WILLIAM_HILL = "16"
    BET365 = "7"
    LADBROKES = "2"
    AVERAGE = "avg"


# ============================================================================
# 核心数据模型
# ============================================================================

class MarketMetric(BaseModel):
    """市场指标数据模型 - 强类型验证.

    Attributes:
        id: 指标标识符（供应商 ID）
        value: 指标值（赔率数据）
        timestamp: 数据时间戳
        source: 数据来源（可选）

    Validators:
        - id: 必须为正整数或特定字符串
        - value: 必须在 1.01 到 50.00 之间
        - timestamp: 自动设置默认值
    """

    id: int = Field(..., description="指标标识符", ge=1, le=100)
    value: float = Field(..., description="指标值（赔率）", ge=1.01, le=50.00)
    timestamp: datetime = Field(default_factory=datetime.now, description="数据时间戳")
    source: DataSource | None = Field(default=None, description="数据来源")

    @field_validator("value")
    @classmethod
    def validate_value_range(cls, v: float) -> float:
        """验证赔率值在合理范围内"""
        if not (1.01 <= v <= 50.00):
            raise ValueError(f"赔率值 {v} 超出有效范围 [1.01, 50.00]")
        return v

    def to_dict(self) -> dict:
        """转换为字典（数据库入库使用）"""
        return {
            "id": self.id,
            "value": self.value,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source.value if self.source else None
        }


class VendorOddsData(BaseModel):
    """供应商赔率数据模型 - Pydantic 驱动.

    替代原有的 dataclass 实现，提供：
    1. 自动类型验证
    2. JSON 序列化支持
    3. 数据完整性检查
    4. 详细的错误信息

    Attributes:
        vendor_id: 供应商 ID (18, 16, 7, 2, avg)
        source_name: 内部实体代码 (e.g., "Entity_P")
        name: 供应商显示名称
        priority: 提取优先级 (1=最高)
        init_h/d/a: 初始赔率（开盘）
        final_h/d/a: 最终赔率
        integrity_score: 完整性评分
        is_valid: 是否通过验证
        validation_error: 验证错误信息
        extracted_at: 提取时间戳
    """

    vendor_id: int | str = Field(..., description="供应商 ID")
    source_name: str = Field(..., min_length=1, description="内部实体代码")
    name: str = Field(..., min_length=1, description="供应商显示名称")
    priority: int = Field(..., ge=1, le=10, description="提取优先级")

    # 初始赔率（开盘）
    init_h: float | None = Field(default=None, ge=1.01, le=50.00, description="初始主胜赔率")
    init_d: float | None = Field(default=None, ge=1.01, le=50.00, description="初始平局赔率")
    init_a: float | None = Field(default=None, ge=1.01, le=50.00, description="初始客胜赔率")

    # 最终赔率
    final_h: float | None = Field(default=None, ge=1.01, le=50.00, description="最终主胜赔率")
    final_d: float | None = Field(default=None, ge=1.01, le=50.00, description="最终平局赔率")
    final_a: float | None = Field(default=None, ge=1.01, le=50.00, description="最终客胜赔率")

    # 验证元数据
    integrity_score: float | None = Field(default=None, ge=0.5, le=1.5, description="完整性评分")
    is_valid: bool = Field(default=False, description="是否通过验证")
    validation_error: str | None = Field(default=None, description="验证错误信息")

    # 元数据
    extracted_at: datetime = Field(default_factory=datetime.now, description="提取时间戳")

    @model_validator(mode="after")
    def validate_odds_completeness(self) -> "VendorOddsData":
        """验证赔率数据完整性"""
        # 检查是否至少有一种赔率类型（init 或 final）
        has_init = all([self.init_h, self.init_d, self.init_a])
        has_final = all([self.final_h, self.final_d, self.final_a])

        if not (has_init or has_final):
            self.is_valid = False
            self.validation_error = "缺少完整的赔率数据（需要 init 或 final 中的完整 1X2 数据）"

        return self

    def calculate_integrity(self) -> float | None:
        """计算并验证完整性评分.

        使用最终赔率（如果可用），否则回退到初始赔率。
        有效的 1X2 市场: 1.02 < Score < 1.08

        Returns:
            完整性评分（如果可计算），否则返回 None
        """
        h = self.final_h or self.init_h
        d = self.final_d or self.init_d
        a = self.final_a or self.init_a

        if not all([h, d, a]):
            self.is_valid = False
            self.validation_error = "计算完整性评分时缺少赔率数据"
            return None

        try:
            self.integrity_score = 1.0 / h + 1.0 / d + 1.0 / a
            self.is_valid = 1.02 < self.integrity_score < 1.08

            if not self.is_valid:
                self.validation_error = (
                    f"完整性评分 {self.integrity_score:.4f} 超出有效范围 [1.02, 1.08]"
                )
            else:
                self.validation_error = None

            return self.integrity_score

        except ZeroDivisionError:
            self.is_valid = False
            self.validation_error = "完整性计算中出现除零错误"
            return None

    def to_dict(self) -> dict:
        """转换为字典（数据库入库使用）"""
        return {
            "vendor_id": self.vendor_id,
            "source_name": self.source_name,
            "name": self.name,
            "priority": self.priority,
            "init_h": self.init_h,
            "init_d": self.init_d,
            "init_a": self.init_a,
            "final_h": self.final_h,
            "final_d": self.final_d,
            "final_a": self.final_a,
            "integrity_score": self.integrity_score,
            "is_valid": self.is_valid,
            "validation_error": self.validation_error,
            "extracted_at": self.extracted_at.isoformat()
        }


class MatchOddsPayload(BaseModel):
    """比赛赔率数据负载 - 批量入库模型.

    用于批量提交多供应商的赔率数据。

    Attributes:
        match_id: 比赛 ID
        odds_data: 供应商赔率数据列表
        data_timestamp: 数据时间戳
    """

    match_id: str = Field(..., min_length=1, description="比赛 ID")
    odds_data: list[VendorOddsData] = Field(default_factory=list, description="供应商赔率数据列表")
    data_timestamp: datetime = Field(default_factory=datetime.now, description="数据时间戳")

    @field_validator("odds_data")
    @classmethod
    def validate_odds_data_not_empty(cls, v: list) -> list:
        """验证赔率数据列表非空"""
        if not v:
            raise ValueError("赔率数据列表不能为空")
        return v

    @model_validator(mode="after")
    def validate_data_integrity(self) -> "MatchOddsPayload":
        """验证整个负载数据完整性"""
        # 检查是否有完整的赔率数据（有 final 或 init 的完整 1X2 数据）
        has_complete_data = False
        for data in self.odds_data:
            final_complete = all([data.final_h, data.final_d, data.final_a])
            init_complete = all([data.init_h, data.init_d, data.init_a])
            if final_complete or init_complete:
                has_complete_data = True
                break

        if not has_complete_data:
            raise ValueError("负载中必须包含至少一个有完整赔率数据的供应商")

        return self

    def get_valid_vendors(self) -> list[VendorOddsData]:
        """获取所有有效的供应商数据"""
        return [data for data in self.odds_data if data.is_valid]

    def get_vendor_sources(self) -> list[str]:
        """获取所有供应商源名称"""
        return [data.source_name for data in self.odds_data]


# ============================================================================
# 辅助模型
# ============================================================================

class ValidationResult(BaseModel):
    """验证结果模型.

    Attributes:
        is_valid: 是否通过验证
        errors: 错误列表
        warnings: 警告列表
        score: 健康评分 (0-100)
    """

    is_valid: bool = Field(..., description="是否通过验证")
    errors: list[str] = Field(default_factory=list, description="错误列表")
    warnings: list[str] = Field(default_factory=list, description="警告列表")
    score: float = Field(default=100.0, ge=0.0, le=100.0, description="健康评分")

    def add_error(self, error: str) -> None:
        """添加错误"""
        self.errors.append(error)
        self.score = max(0, self.score - 25)

    def add_warning(self, warning: str) -> None:
        """添加警告"""
        self.warnings.append(warning)
        self.score = max(0, self.score - 5)

    def is_healthy(self) -> bool:
        """检查是否健康（无严重错误）"""
        return self.is_valid and len(self.errors) == 0
