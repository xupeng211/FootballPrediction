#!/usr/bin/env python3
"""
V79.100 Feature Extraction Schema - 特征提取数据模型
====================================================

功能:
- 定义 UltimateFeatureExtractor 的输入/输出数据模型
- 提供类型安全的特征提取接口
- 数据验证和转换

Author: V79.100 Engineering Team
Date: 2026-01-25
Version: V79.100
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator

# =============================================================================
# Enums
# =============================================================================


class FeatureExtractionStatus(str, Enum):
    """特征提取状态枚举"""

    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class FeatureQuality(str, Enum):
    """特征质量评级"""

    EXCELLENT = "EXCELLENT"  # >=100 features
    GOOD = "GOOD"  # >=80 features
    FAIR = "FAIR"  # >=50 features
    POOR = "POOR"  # <50 features


# =============================================================================
# Input Schemas
# =============================================================================


class MatchDataInput(BaseModel):
    """
    V79.100 UltimateFeatureExtractor 输入数据模型

    定义特征提取器的输入数据结构，确保类型安全。

    Fields:
        match_id: 比赛唯一标识符
        league_name: 联赛名称
        home_team: 主队名称
        away_team: 客队名称
        match_date: 比赛日期
        technical_features: 技术特征 (JSON string or dict)
        golden_features: 黄金特征 (JSON string or dict)
        l2_raw_json: L2 原始数据 (JSON string or dict)
    """

    # 核心标识
    match_id: str | None = Field(None, description="比赛唯一标识符")

    # 基础信息
    league_name: str | None = Field(None, description="联赛名称")
    home_team: str | None = Field(None, description="主队名称")
    away_team: str | None = Field(None, description="客队名称")
    match_date: datetime | None = Field(None, description="比赛日期")

    # 特征数据
    technical_features: dict[str, Any] | str | None = Field(
        None, description="技术特征 (152维)"
    )
    golden_features: dict[str, Any] | str | None = Field(
        None, description="黄金特征 (市场价值/缺阵/评分)"
    )
    l2_raw_json: dict[str, Any] | str | None = Field(
        None, description="L2 原始 JSON 数据"
    )

    @field_validator("technical_features", "golden_features", "l2_raw_json", mode="before")
    @classmethod
    def parse_json_fields(cls, v: Any) -> dict[str, Any] | str | None:
        """解析 JSON 字符串字段"""
        if isinstance(v, str):
            import json

            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return None
        return v


# =============================================================================
# Output Schemas
# =============================================================================


class FeatureExtractionResult(BaseModel):
    """
    V79.100 特征提取结果模型

    定义特征提取器的输出数据结构。

    Fields:
        match_id: 比赛唯一标识符
        status: 提取状态
        features: 提取的特征字典
        quality: 特征质量评级
        feature_count: 特征数量
        rejected_count: 被拒绝的特征数量（赛中/赛后特征）
        extracted_at: 提取时间
        error_message: 错误信息（如果失败）
    """

    match_id: str | None = Field(None, description="比赛唯一标识符")
    status: FeatureExtractionStatus = Field(
        default=FeatureExtractionStatus.PENDING, description="提取状态"
    )
    features: dict[str, float] = Field(default_factory=dict, description="提取的特征字典")
    quality: FeatureQuality = Field(default=FeatureQuality.POOR, description="特征质量评级")
    feature_count: int = Field(default=0, description="特征数量")
    rejected_count: int = Field(default=0, description="被拒绝的特征数量")
    extracted_at: datetime = Field(
        default_factory=datetime.now, description="提取时间"
    )
    error_message: str | None = Field(None, description="错误信息")

    def calculate_quality(self) -> FeatureQuality:
        """根据特征数量计算质量评级"""
        if self.feature_count >= 100:
            return FeatureQuality.EXCELLENT
        if self.feature_count >= 80:
            return FeatureQuality.GOOD
        if self.feature_count >= 50:
            return FeatureQuality.FAIR
        return FeatureQuality.POOR


class UnavailablePlayerStats(BaseModel):
    """
    缺阵球员统计模型

    Fields:
        total_count: 缺阵总数
        injury_count: 伤病数
        suspension_count: 禁赛数
        other_count: 其他原因数
        total_market_value: 总身价（欧元）
        avg_market_value: 平均身价（欧元）
        star_count: 球星数（身价>30M）
    """

    total_count: int = Field(default=0, ge=0, description="缺阵总数")
    injury_count: int = Field(default=0, ge=0, description="伤病数")
    suspension_count: int = Field(default=0, ge=0, description="禁赛数")
    other_count: int = Field(default=0, ge=0, description="其他原因数")
    total_market_value: float = Field(default=0.0, ge=0, description="总身价（欧元）")
    avg_market_value: float = Field(default=0.0, ge=0, description="平均身价（欧元）")
    star_count: int = Field(default=0, ge=0, description="球星数（身价>30M）")


class FatigueFeatures(BaseModel):
    """
    疲劳度特征模型

    Fields:
        home_rest_days: 主队休息天数
        away_rest_days: 客队休息天数
        home_is_busy_week: 主队是否为忙碌周
        away_is_busy_week: 客队是否为忙碌周
        diff_rest_days: 休息天数差值
        home_less_rest: 主队休息是否少于客队
    """

    home_rest_days: float = Field(default=14.0, ge=0.0, description="主队休息天数")
    away_rest_days: float = Field(default=14.0, ge=0.0, description="客队休息天数")
    home_is_busy_week: float = Field(
        default=0.0, ge=0.0, le=1.0, description="主队是否为忙碌周"
    )
    away_is_busy_week: float = Field(
        default=0.0, ge=0.0, le=1.0, description="客队是否为忙碌周"
    )
    diff_rest_days: float = Field(default=0.0, description="休息天数差值")
    home_less_rest: float = Field(
        default=0.0, ge=0.0, le=1.0, description="主队休息是否少于客队"
    )


class OddsMovementFeatures(BaseModel):
    """
    赔率动向特征模型

    Fields:
        home_drop_ratio: 主胜赔率下降比率
        draw_drop_ratio: 平局赔率下降比率
        away_drop_ratio: 客胜赔率下降比率
        total_movement: 总变化幅度
        max_drop_ratio: 最大下降比率
    """

    home_drop_ratio: float | None = Field(None, ge=-1.0, le=1.0, description="主胜赔率下降比率")
    draw_drop_ratio: float | None = Field(None, ge=-1.0, le=1.0, description="平局赔率下降比率")
    away_drop_ratio: float | None = Field(None, ge=-1.0, le=1.0, description="客胜赔率下降比率")
    total_movement: float | None = Field(None, ge=0.0, description="总变化幅度")
    max_drop_ratio: float | None = Field(None, ge=-1.0, le=1.0, description="最大下降比率")


# =============================================================================
# Export
# =============================================================================

__all__ = [
    "FatigueFeatures",
    "FeatureExtractionResult",
    "FeatureExtractionStatus",
    "FeatureQuality",
    "MatchDataInput",
    "OddsMovementFeatures",
    "UnavailablePlayerStats",
]
