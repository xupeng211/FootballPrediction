#!/usr/bin/env python3
"""
L2 特征提取器 - Pydantic 数据模型
=================================

定义特征输出的标准 Schema，确保类型安全和数据完整性。

设计原则:
    - 使用 Pydantic 进行类型验证
    - 支持 881 维特征的完整定义
    - 提供灵活的扩展机制

Author: Architecture Team
Version: V25.0
Date: 2025-12-26
"""

from datetime import datetime
from enum import Enum
from typing import Any, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class MatchOutcome(str, Enum):
    """比赛结果枚举"""

    HOME_WIN = "H"
    DRAW = "D"
    AWAY_WIN = "A"
    UNKNOWN = "U"


class FeatureCategory(str, Enum):
    """特征类别枚举"""

    ROLLING = "rolling"  # 滚动统计特征
    PRE_MATCH = "pre_match"  # 赛前特征
    ADVANCED = "advanced"  # 高级动态特征
    TACTICAL = "tactical"  # 战术特征
    MARKET = "market"  # 市场赔率特征
    HISTORICAL = "historical"  # 历史交锋特征


# ============================================================================
# 基础统计特征
# ============================================================================


class TeamStats(BaseModel):
    """
    球队基础统计

    Attributes:
        possession: 控球率 (0-100)
        shots_total: 总射门数
        shots_on_target: 射正数
        corners: 角球数
        fouls: 犯规数
        offsides: 越位数
        saves: 扑救数
        tackles: 抢断数
        interceptions: 拦截数
        clearances: 解围数
    """

    possession: float | None = Field(default=None, ge=0, le=100)
    shots_total: int | None = Field(default=None, ge=0)
    shots_on_target: int | None = Field(default=None, ge=0)
    corners: int | None = Field(default=None, ge=0)
    fouls: int | None = Field(default=None, ge=0)
    offsides: int | None = Field(default=None, ge=0)
    saves: int | None = Field(default=None, ge=0)
    tackles: int | None = Field(default=None, ge=0)
    interceptions: int | None = Field(default=None, ge=0)
    clearances: int | None = Field(default=None, ge=0)

    @field_validator("*", mode="before")
    @classmethod
    def handle_nan(cls, v: Any) -> float | None:
        """处理 NaN 值"""
        if isinstance(v, float) and v != v:  # NaN check
            return None
        return v


class AdvancedStats(BaseModel):
    """
    高级统计特征

    Attributes:
        expected_goals: xG 期望进球数
        expected_assists: xA 期望助攻数
        big_chances_created: 创造重大机会数
        big_chances_missed: 错失重大机会数
        accurate_passes: 成功传球数
        pass_accuracy: 传球成功率 (0-100)
        duels_won: 赢下对抗次数
        aerial_duels_won: 赢下空中对抗次数
    """

    expected_goals: float | None = Field(default=None, ge=0)
    expected_assists: float | None = Field(default=None, ge=0)
    big_chances_created: int | None = Field(default=None, ge=0)
    big_chances_missed: int | None = Field(default=None, ge=0)
    accurate_passes: int | None = Field(default=None, ge=0)
    pass_accuracy: float | None = Field(default=None, ge=0, le=100)
    duels_won: int | None = Field(default=None, ge=0)
    aerial_duels_won: int | None = Field(default=None, ge=0)


# ============================================================================
# 滚动特征
# ============================================================================


class RollingFeatures(BaseModel):
    """
    滚动统计特征（过去 N 场比赛）

    Attributes:
        rolling_xg: 滚动 xG
        rolling_xg_std: 滚动 xG 标准差
        rolling_shots_on_target: 滚动射正
        rolling_shots_on_target_std: 滚动射正标准差
        rolling_possession: 滚动控球率
        rolling_possession_std: 滚动控球率标准差
        rolling_team_rating: 滚动球队评分
        rolling_team_rating_std: 滚动评分标准差
    """

    rolling_xg: float | None = None
    rolling_xg_std: float | None = None
    rolling_shots_on_target: float | None = None
    rolling_shots_on_target_std: float | None = None
    rolling_possession: float | None = None
    rolling_possession_std: float | None = None
    rolling_team_rating: float | None = None
    rolling_team_rating_std: float | None = None


# ============================================================================
# 赛前特征
# ============================================================================


class PreMatchFeatures(BaseModel):
    """
    赛前特征（比赛开始前已知）

    Attributes:
        home_table_position: 主队积分榜排名
        away_table_position: 客队积分榜排名
        table_position_diff: 排名差
        home_points: 主队积分
        away_points: 客队积分
        points_diff: 积分差
        home_recent_form_points: 主队近期状态积分
        away_recent_form_points: 客队近期状态积分
    """

    home_table_position: int | None = Field(default=None, ge=1)
    away_table_position: int | None = Field(default=None, ge=1)
    table_position_diff: int | None = None
    home_points: int | None = Field(default=None, ge=0)
    away_points: int | None = Field(default=None, ge=0)
    points_diff: int | None = None
    home_recent_form_points: int | None = None
    away_recent_form_points: int | None = None


# ============================================================================
# 高级动态特征
# ============================================================================


class AdvancedDynamicFeatures(BaseModel):
    """
    高级动态特征（ELO、疲劳、战意等）

    Attributes:
        raw_elo_gap: 原始 ELO 差距
        adjusted_elo_gap: 调整后 ELO 差距
        fatigue_impact: 疲劳影响因子
        schedule_impact: 赛程强度影响
        home_fatigue_index: 主队疲劳指数
        away_fatigue_index: 客队疲劳指数
        fatigue_diff: 疲劳差
        home_rest_days: 主队休息天数
        away_rest_days: 客队休息天数
        home_relegation_incentive: 主队保级战意
        away_relegation_incentive: 客队保级战意
        incentive_diff: 战意差
        home_desperation: 主队绝望指数
    """

    raw_elo_gap: float | None = None
    adjusted_elo_gap: float | None = None
    fatigue_impact: float | None = None
    schedule_impact: float | None = None
    home_fatigue_index: float | None = Field(default=None, ge=0, le=1)
    away_fatigue_index: float | None = Field(default=None, ge=0, le=1)
    fatigue_diff: float | None = None
    home_rest_days: int | None = Field(default=None, ge=0)
    away_rest_days: int | None = Field(default=None, ge=0)
    home_relegation_incentive: float | None = Field(default=None, ge=0, le=1)
    away_relegation_incentive: float | None = Field(default=None, ge=0, le=1)
    incentive_diff: float | None = None
    home_desperation: float | None = Field(default=None, ge=0, le=1)


# ============================================================================
# 平局敏感度特征
# ============================================================================


class DrawSensitivityFeatures(BaseModel):
    """
    平局敏感度特征（V19.4 新增）

    Attributes:
        table_proximity: 积分榜接近度
        low_scoring_tendency: 低得分倾向
        elo_diff_cluster: ELO 差距聚类
    """

    table_proximity: float | None = Field(default=None, ge=0)
    low_scoring_tendency: float | None = Field(default=None, ge=0, le=1)
    elo_diff_cluster: str | None = None


# ============================================================================
# 完整特征输出
# ============================================================================


class FeatureMetadata(BaseModel):
    """特征元数据"""

    extractor_version: str
    extractor_class: str
    feature_count: int
    extraction_timestamp: datetime = Field(default_factory=datetime.now)
    validation_passed: bool = True
    warnings: list[str] = Field(default_factory=list)
    data_source: str | None = None
    match_id: int | None = None
    league_id: int | None = None
    season: str | None = None


class FeatureOutput(BaseModel):
    """
    完整特征输出模型

    包含所有类别的特征，确保 881 维完整性。

    设计说明:
        - 使用 Optional 允许部分特征缺失
        - Pydantic 自动验证类型
        - 支持 JSON 序列化
    """

    # 模型配置
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="allow",  # 允许额外字段以支持未来扩展
    )

    # 元数据
    metadata: FeatureMetadata | None = None

    # 主队特征
    home_team_stats: TeamStats | None = None
    home_rolling: RollingFeatures | None = None

    # 客队特征
    away_team_stats: TeamStats | None = None
    away_rolling: RollingFeatures | None = None

    # 赛前特征
    pre_match: PreMatchFeatures | None = None

    # 高级特征
    home_advanced: AdvancedStats | None = None
    away_advanced: AdvancedStats | None = None
    advanced_dynamic: AdvancedDynamicFeatures | None = None
    draw_sensitivity: DrawSensitivityFeatures | None = None

    # 差异特征（主队 - 客队）
    diff_possession: float | None = None
    diff_shots_total: int | None = None
    diff_shots_on_target: int | None = None
    diff_expected_goals: float | None = None
    diff_team_rating: float | None = None

    # 比率特征
    ratio_home_possession: float | None = Field(default=None, ge=0, le=1)
    ratio_away_possession: float | None = Field(default=None, ge=0, le=1)

    # 扩展字段（用于 881 维的其余部分）
    extended_features: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_feature_count(self) -> "FeatureOutput":
        """
        验证特征数量是否足够

        这个方法在模型验证后自动调用。
        """
        # 计算总特征数（包括嵌套字段）
        count = self.calculate_feature_count()
        # 注意：这里不做强制验证，因为允许部分特征缺失
        # 验证逻辑应该由 extractor.validate() 完成
        return self

    def calculate_feature_count(self) -> int:
        """
        计算总特征数量

        Returns:
            特征总数（包括嵌套字段和扩展字段）
        """
        count = 0

        # 计算各个模型字段
        for field_name in self.model_fields:
            if field_name == "extended_features":
                continue
            value = getattr(self, field_name, None)
            if value is not None:
                if isinstance(value, BaseModel):
                    count += len(value.model_fields)
                elif isinstance(value, (list, dict)):
                    count += len(value)
                else:
                    count += 1

        # 添加扩展特征
        count += len(self.extended_features)

        return count

    def to_flat_dict(self) -> dict[str, Any]:
        """
        转换为扁平字典

        将嵌套结构展开为单层字典，便于模型训练使用。

        Returns:
            扁平化的特征字典
        """
        flat_dict: dict[str, Any] = {}

        # 展开嵌套字段
        for field_name in self.model_fields:
            if field_name in ("metadata", "extended_features"):
                continue
            value = getattr(self, field_name, None)
            if value is not None:
                if isinstance(value, BaseModel):
                    # 展开嵌套模型
                    for sub_field, sub_value in value.model_dump().items():
                        flat_dict[f"{field_name}_{sub_field}"] = sub_value
                else:
                    flat_dict[field_name] = value

        # 添加扩展特征
        flat_dict.update(self.extended_features)

        # 添加元数据标签（非训练特征）
        if self.metadata:
            flat_dict["_meta"] = self.metadata.model_dump()

        return flat_dict

    @classmethod
    def from_raw_dict(cls, raw_dict: dict[str, Any]) -> "FeatureOutput":
        """
        从原始字典创建实例

        这是一个工厂方法，支持从任意字典创建模型实例。
        会尝试将字段映射到正确的子模型。

        Args:
            raw_dict: 原始特征字典

        Returns:
            FeatureOutput 实例
        """
        # 分离元数据
        metadata = None
        if "_meta" in raw_dict:
            metadata_data = raw_dict.pop("_meta")
            metadata = FeatureMetadata(**metadata_data)

        # 分离已知字段和扩展字段
        known_fields = set(cls.model_fields) - {"metadata", "extended_features"}
        known_dict: dict[str, Any] = {}
        extended_dict: dict[str, Any] = {}

        for key, value in raw_dict.items():
            if key in known_fields:
                known_dict[key] = value
            else:
                extended_dict[key] = value

        # 构建实例
        return cls(
            metadata=metadata,
            extended_features=extended_dict,
            **known_dict,
        )


# ============================================================================
# 便捷类型别名
# ============================================================================

# 原始特征字典（用于训练）
FeatureDict = dict[str, Any]

# 特征集合（支持多种格式）
FeatureData = Union[FeatureOutput, FeatureDict, str]  # str 支持 JSON
