#!/usr/bin/env python3
"""
UCL 特征适配器 - 欧冠专用特征列表
====================================

功能:
1. 针对欧冠赛制的精简版特征列表
2. 排除"League Position（联赛排名）"等干扰特征
3. 保留滚动特征、ELO 评分、疲劳度等通用特征

设计原则:
- 欧冠没有联赛排名，排除相关特征
- 保留通用技术统计特征
- 保留球队实力评估特征（ELO）
- 保留近期状态特征

作者: Statistical Validation Team
日期: 2025-12-30
版本: V1.0
"""

from dataclasses import dataclass
from typing import Any

import structlog

from src.processors.base_extractor import (
    BaseExtractor,
    ExtractionResult,
    ExtractionStatus,
    ValidationConfig,
    register_extractor,
)

logger = structlog.get_logger(__name__)


# ============================================================================
# UCL 专用特征列表（精简版，排除联赛排名相关）
# ============================================================================

# UCL 可用特征（不依赖联赛排名）
UCL_AVAILABLE_FEATURES = [
    # ========== 滚动特征 (8个) ==========
    "rolling_xg_home",              # 主队近期 xG
    "rolling_xg_away",              # 客队近期 xG
    "rolling_shots_on_target_home", # 主队近期射正数
    "rolling_shots_on_target_away", # 客队近期射正数
    "rolling_possession_home",      # 主队近期控球率
    "rolling_possession_away",      # 客队近期控球率
    "rolling_team_rating_home",     # 主队近期评分
    "rolling_team_rating_away",     # 客队近期评分

    # ========== 高级特征 (4个) ==========
    "raw_elo_gap",                  # 原始 ELO 分差
    "adjusted_elo_gap",             # 调整后 ELO 分差（主场优势）
    "home_fatigue_index",           # 主队疲劳度
    "away_fatigue_index",           # 客队疲劳度

    # ========== 比赛上下文特征 (可选) ==========
    "is_home_advantage",            # 主场优势标识
    "days_since_last_match_home",   # 主队休息天数
    "days_since_last_match_away",   # 客队休息天数
]

# UCL 排除特征（依赖联赛排名）
UCL_EXCLUDED_FEATURES = [
    # ========== 积分榜特征 (7个) - 欧冠不适用 ==========
    "home_table_position",          # 主队联赛排名
    "away_table_position",          # 客队联赛排名
    "table_position_diff",          # 排名差
    "home_points",                  # 主队积分
    "away_points",                  # 客队积分
    "points_diff",                  # 积分差
    "home_recent_form_points",      # 主队近期联赛积分
]


@dataclass
class UCLFeatureConfig:
    """UCL 特征适配器配置"""

    min_features: int = 10        # 最小特征数（降低阈值，因为特征少）
    max_features: int = 20        # 最大特征数
    require_elo: bool = True      # 要求 ELO 评分
    require_fatigue: bool = True  # 要求疲劳度


class UCLFeatureAdapter(BaseExtractor):
    """
    UCL 专用特征适配器

    针对欧冠赛制的特点，排除联赛排名相关特征，保留通用技术统计。
    """

    VERSION = "UCL_V1.0"

    DEFAULT_CONFIG = ValidationConfig(
        min_features=10,
        max_features=20,
        allow_partial=True,
    )

    def __init__(self, config: UCLFeatureConfig | None = None):
        """初始化 UCL 特征适配器"""
        super().__init__(self.DEFAULT_CONFIG)
        self.ucl_config = config or UCLFeatureConfig()
        self._logger = logger

    @property
    def version(self) -> str:
        """返回版本号"""
        return self.VERSION

    def pre_process(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        """预处理原始数据"""
        self._logger.debug("UCL 特征适配器预处理", version=self.version)

        if not raw_data:
            from src.processors.exceptions import DataParsingError

            raise DataParsingError(
                "原始数据为空",
                raw_data_type=type(raw_data).__name__,
            )

        return raw_data

    def extract(self, raw_data: dict[str, Any]) -> ExtractionResult:
        """
        提取 UCL 专用特征

        策略：
        1. 从原始数据中提取可用特征
        2. 排除联赛排名相关特征
        3. 验证特征完整性
        """
        self._logger.info("开始 UCL 特征提取", version=self.version)

        features: dict[str, Any] = {}
        warnings: list[str] = []
        errors: list[str] = []

        try:
            # 提取可用特征
            for feature_key in UCL_AVAILABLE_FEATURES:
                if feature_key in raw_data:
                    features[feature_key] = raw_data[feature_key]
                else:
                    # 某些特征可能有不同的键名
                    alt_keys = self._get_alternative_keys(feature_key)
                    value = None
                    for alt_key in alt_keys:
                        if alt_key in raw_data:
                            value = raw_data[alt_key]
                            break

                    if value is not None:
                        features[feature_key] = value
                    else:
                        # 使用默认值
                        features[feature_key] = self._get_default_value(feature_key)

            # 排除干扰特征（如果存在）
            for excluded_key in UCL_EXCLUDED_FEATURES:
                if excluded_key in raw_data:
                    warnings.append(f"排除联赛排名特征: {excluded_key}")

            # 添加元数据
            features["_meta"] = {
                "extraction_version": self.version,
                "feature_count": len(features),
                "available_features": UCL_AVAILABLE_FEATURES,
                "excluded_features": UCL_EXCLUDED_FEATURES,
            }

            # 验证特征数量
            if len(features) >= self._validation_config.min_features:
                status = ExtractionStatus.SUCCESS
            else:
                status = ExtractionStatus.PARTIAL
                errors.append(f"特征数量不足: {len(features)} < {self._validation_config.min_features}")

            self._logger.info(
                "UCL 特征提取完成",
                feature_count=len(features),
                status=status.value,
            )

            return ExtractionResult(
                status=status,
                features=features,
                warnings=warnings,
                errors=errors,
            )

        except Exception as e:
            self._logger.error("UCL 特征提取异常", error=str(e), error_type=type(e).__name__)
            from src.processors.exceptions import DataParsingError

            raise DataParsingError(
                f"{self.version} 特征提取失败: {e}",
                parse_error=str(e),
            ) from e

    def _get_alternative_keys(self, feature_key: str) -> list[str]:
        """获取特征键的替代名称"""
        alternatives = {
            # 滚动特征替代键
            "rolling_xg_home": ["home_xg_recent", "xg_home_avg"],
            "rolling_xg_away": ["away_xg_recent", "xg_away_avg"],
            "rolling_shots_on_target_home": ["home_sot_recent", "shots_on_target_home_avg"],
            "rolling_shots_on_target_away": ["away_sot_recent", "shots_on_target_away_avg"],
            "rolling_possession_home": ["home_possession_recent", "possession_home_avg"],
            "rolling_possession_away": ["away_possession_recent", "possession_away_avg"],
            "rolling_team_rating_home": ["home_rating_recent", "rating_home_avg"],
            "rolling_team_rating_away": ["away_rating_recent", "rating_away_avg"],
            # ELO 替代键
            "raw_elo_gap": ["elo_difference", "elo_diff"],
            "adjusted_elo_gap": ["elo_gap_adjusted", "adjusted_elo"],
            # 疲劳度替代键
            "home_fatigue_index": ["fatigue_home", "home_fatigue"],
            "away_fatigue_index": ["fatigue_away", "away_fatigue"],
        }
        return alternatives.get(feature_key, [])

    def _get_default_value(self, feature_key: str) -> Any:
        """获取特征的默认值"""
        defaults = {
            # 滚动特征默认值
            "rolling_xg_home": 1.2,
            "rolling_xg_away": 1.2,
            "rolling_shots_on_target_home": 4.0,
            "rolling_shots_on_target_away": 4.0,
            "rolling_possession_home": 50.0,
            "rolling_possession_away": 50.0,
            "rolling_team_rating_home": 6.8,
            "rolling_team_rating_away": 6.8,
            # ELO 默认值
            "raw_elo_gap": 0.0,
            "adjusted_elo_gap": 0.0,
            # 疲劳度默认值
            "home_fatigue_index": 0.5,
            "away_fatigue_index": 0.5,
            # 比赛上下文默认值
            "is_home_advantage": 1,
            "days_since_last_match_home": 7.0,
            "days_since_last_match_away": 7.0,
        }
        return defaults.get(feature_key, 0.0)

    def validate(self, features: dict[str, Any]) -> bool:
        """
        验证 UCL 特征

        检查：
        1. ELO 评分是否存在
        2. 疲劳度是否存在
        3. 滚动特征是否完整
        """
        feature_count = len(features)

        self._logger.debug(
            "开始验证 UCL 特征",
            feature_count=feature_count,
            min_required=self._validation_config.min_features,
        )

        # 检查特征数量
        if feature_count < self._validation_config.min_features:
            from src.processors.exceptions import InsufficientFeaturesError

            raise InsufficientFeaturesError(
                f"UCL 特征维度不足: {feature_count} < {self._validation_config.min_features}",
                actual_count=feature_count,
                min_required=self._validation_config.min_features,
            )

        # 检查必需特征
        if self.ucl_config.require_elo:
            if "raw_elo_gap" not in features and "adjusted_elo_gap" not in features:
                self._logger.warning("UCL 特征缺少 ELO 评分")

        if self.ucl_config.require_fatigue:
            if "home_fatigue_index" not in features or "away_fatigue_index" not in features:
                self._logger.warning("UCL 特征缺少疲劳度指数")

        # 检查最大限制
        if self._validation_config.max_features is not None and feature_count > self._validation_config.max_features:
            self._logger.warning(
                "UCL 特征维度超过上限",
                feature_count=feature_count,
                max_allowed=self._validation_config.max_features,
            )

        self._logger.debug("UCL 特征验证通过", feature_count=feature_count)
        return True


# 注册提取器
register_extractor(UCLFeatureAdapter)


# ============================================================================
# 辅助函数
# ============================================================================


def create_ucl_features_from_v267(v267_features: dict[str, Any]) -> dict[str, Any]:
    """
    从 V26.7 特征转换为 UCL 特征

    Args:
        v267_features: V26.7 完整特征字典

    Returns:
        UCL 专用特征字典
    """
    ucl_features = {}

    # 复制可用特征
    for key in UCL_AVAILABLE_FEATURES:
        if key in v267_features:
            ucl_features[key] = v267_features[key]

    # 添加转换标识
    ucl_features["_meta"] = {
        "source": "V26.7",
        "adapter": "UCL_V1.0",
        "excluded_features": UCL_EXCLUDED_FEATURES,
        "original_feature_count": len(v267_features),
        "adapted_feature_count": len(ucl_features),
    }

    return ucl_features


def get_ucl_feature_list() -> dict[str, list[str]]:
    """
    获取 UCL 特征列表信息

    Returns:
        Dict: {
            "available": 可用特征列表,
            "excluded": 排除特征列表,
            "count": 可用特征数量
        }
    """
    return {
        "available": UCL_AVAILABLE_FEATURES,
        "excluded": UCL_EXCLUDED_FEATURES,
        "count": len(UCL_AVAILABLE_FEATURES),
    }


# 导出
__all__ = [
    "UCLFeatureAdapter",
    "UCLFeatureConfig",
    "create_ucl_features_from_v267",
    "get_ucl_feature_list",
]
