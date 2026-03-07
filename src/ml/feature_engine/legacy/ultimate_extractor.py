"""
V79.200 Ultimate Feature Extractor - 协调器模式
================================================

V79.200: 极致原子化，仅作为"协调者"
- 所有业务逻辑已委托给专用模块
- 配置外部化至 hyper_parameters.yaml
- 代码目标: <200 行
- 新增: @validate_call 运行时类型验证

Core Delegates:
- FatigueCalculator: 疲劳度计算
- StartingQualityAssessor: 首发质量评估 (使用 InjuryDataExtractor)
- OddsTrendAnalyzer: 赔率动向分析
- PreMatchFeaturePlugin: 特征验证

Author: V79.200 Engineering Team
Version: V79.200 "Atomic Coordinator + Type Safety"
Date: 2026-01-25
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import logging
from typing import Any
import uuid

from pydantic import validate_call

from src.ml.feature_engine.legacy.base_processor import BaseFeatureProcessor, ProcessorConfig
from src.ml.feature_engine.legacy.fatigue_calculator import FatigueCalculator
from src.ml.feature_engine.legacy.odds_trend_analyzer import OddsTrendAnalyzer
from src.ml.feature_engine.legacy.pure_feature_filter import PureFeatureFilter
from src.ml.feature_engine.legacy.starting_quality_assessor import StartingQualityAssessor
from src.ml.feature_engine.legacy.technical_parser import PreMatchFeaturePlugin

logger = logging.getLogger(__name__)


# =============================================================================
# V79.200 Configuration (测试兼容性)
# =============================================================================

@dataclass
class UltimateExtractorConfig(ProcessorConfig):
    """V79.200 终极特征提取器配置 (测试兼容性)"""
    busy_week_threshold: int = 4
    default_rest_days: int = 14
    star_market_value: float = 30_000_000
    TOP_5_LEAGUES: frozenset = frozenset({
        "Premier League", "La Liga", "Bundesliga", "Serie A", "Ligue 1"
    })


DEFAULT_CONFIG = UltimateExtractorConfig()

# 从配置获取五大联赛（V79.200）
TOP_5_LEAGUES = DEFAULT_CONFIG.TOP_5_LEAGUES


# =============================================================================
# Ultimate Feature Extractor (Coordinator Pattern)
# =============================================================================

class UltimateFeatureExtractor(BaseFeatureProcessor):
    """
    V79.200 终极特征提取器 - 协调器模式

    仅作为"协调者"，所有业务逻辑委托给专用模块：
    - FatigueCalculator: 疲劳度特征
    - StartingQualityAssessor: 首发质量/缺阵特征
    - OddsTrendAnalyzer: 赔率动向特征
    - PreMatchFeaturePlugin: 特征验证
    """

    def __init__(self, config: ProcessorConfig | None = None):
        super().__init__(config)
        self.pure_filter = PureFeatureFilter(strict_mode=True)
        self.pre_match_plugin = PreMatchFeaturePlugin(strict_mode=True)
        self.odds_analyzer = OddsTrendAnalyzer()
        self.fatigue_calculator = FatigueCalculator()
        self.quality_assessor = StartingQualityAssessor()
        self._match_cache: dict[str, dict[str, Any]] = {}

    def extract_features(
        self,
        match_data: dict[str, Any],
        verbose: bool = False
    ) -> dict[str, Any]:
        """实现 BaseFeatureProcessor 抽象方法"""
        return self.extract_ultimate_features(match_data, verbose)

    # ========================================================================
    # Feature Extraction Methods (委托给专用模块)
    # ========================================================================

    def _calculate_fatigue_features(self, match_data: dict[str, Any]) -> dict[str, float]:
        """委托给 FatigueCalculator"""
        return self.fatigue_calculator.calculate_fatigue_features(match_data)

    def _extract_unavailable_features(self, l2_raw_json: dict[str, Any] | str | None) -> dict[str, float]:
        """委托给 StartingQualityAssessor (使用 InjuryDataExtractor)"""
        return self.quality_assessor.extract_unavailable_features(l2_raw_json)

    def _calculate_odds_movement(self, initial_price: list[float] | None, closing_price: list[float] | None) -> dict[str, float]:
        """委托给 OddsTrendAnalyzer"""
        return self.odds_analyzer.calculate_odds_movement(initial_price, closing_price)

    def _get_odds_features(self, match_id: str) -> dict[str, float]:
        """委托给 OddsTrendAnalyzer"""
        return self.odds_analyzer.get_odds_features(match_id)

    def _is_top_5_league(self, league_name: str | None) -> int:
        """判断是否为五大联赛"""
        return 1 if league_name in TOP_5_LEAGUES else 0

    # ========================================================================
    # Test Compatibility Wrappers (保留以通过测试)
    # ========================================================================

    def _calculate_rest_days(self, current_date: datetime, prev_date: datetime | None) -> int:
        """测试兼容性包装器"""
        return self.fatigue_calculator.calculate_rest_days(current_date, prev_date)

    def _is_busy_week(self, rest_days: int) -> int:
        """测试兼容性包装器"""
        return self.fatigue_calculator.is_busy_week(rest_days)

    @validate_call
    def extract_ultimate_features(
        self,
        match_data: dict[str, Any],
        verbose: bool = False
    ) -> dict[str, float]:
        """
        V79.200: 提取终极特征（协调所有专用模块）

        使用 @validate_call 进行运行时类型验证，确保：
        - match_data 必须是 dict[str, Any] 类型
        - verbose 必须是 bool 类型
        - 任何类型不匹配将抛出 pydantic.ValidationError
        """
        # V79.200: 生成 TraceID 用于结构化日志
        trace_id = str(uuid.uuid4())[:8]

        logger.info({
            "event": "feature_extraction_start",
            "trace_id": trace_id,
            "match_id": match_data.get("match_id"),
            "league_name": match_data.get("league_name"),
            "verbose": verbose
        })

        try:
            all_features = {}
            match_id = match_data.get("match_id")

            # 1. Pure features (from PureFeatureFilter)
            tech_features = match_data.get("technical_features") or {}
            if isinstance(tech_features, str):
                import json
                tech_features = json.loads(tech_features)
            golden_features = match_data.get("golden_features") or {}
            if isinstance(golden_features, str):
                import json
                golden_features = json.loads(golden_features)
            combined = dict(tech_features)
            if golden_features:
                combined.update(golden_features)
            pure_features = self.pure_filter.filter_features(combined, verbose=False)
            all_features.update(pure_features)

            # 2. League tier
            league_name = match_data.get("league_name")
            all_features["is_top_5_league"] = float(self._is_top_5_league(league_name))

            # 3. Fatigue features
            all_features.update(self._calculate_fatigue_features(match_data))

            # 4. Unavailable features
            l2_raw_json = match_data.get("l2_raw_json")
            all_features.update(self._extract_unavailable_features(l2_raw_json))

            # 5. Odds features
            if match_id:
                all_features.update(self._get_odds_features(match_id))

            # 6. Final validation
            validated_features = self.pre_match_plugin.validate_and_filter_features(
                all_features, match_id=match_id, verbose=verbose
            )

            # V79.200: 结构化日志记录完成状态
            rejected_count = len(all_features) - len(validated_features)
            logger.info({
                "event": "feature_extraction_complete",
                "trace_id": trace_id,
                "match_id": match_id,
                "feature_count": len(validated_features),
                "rejected_count": rejected_count,
                "status": "success"
            })

            return validated_features

        except Exception as e:
            # V79.200: 结构化错误日志
            logger.error({
                "event": "feature_extraction_error",
                "trace_id": trace_id,
                "match_id": match_data.get("match_id"),
                "error_type": type(e).__name__,
                "error_message": str(e),
                "status": "failed"
            })
            raise

    def cleanup(self):
        """清理所有子模块资源"""
        self.odds_analyzer.cleanup()
        self.fatigue_calculator.cleanup()
        self.quality_assessor.cleanup()
        super().cleanup()


# =============================================================================
# Singleton Instance
# =============================================================================

_ultimate_extractor_instance = None


def get_ultimate_extractor() -> UltimateFeatureExtractor:
    """获取终极特征提取器单例"""
    global _ultimate_extractor_instance
    if _ultimate_extractor_instance is None:
        _ultimate_extractor_instance = UltimateFeatureExtractor()
    return _ultimate_extractor_instance
