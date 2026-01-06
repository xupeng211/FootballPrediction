"""
FeatureEngine - 特征引擎主编排器
==================================

负责协调所有处理器，按优先级执行特征提取流程。
支持断点续传、并行处理、结果聚合。

设计模式:
    - Facade Pattern: 统一入口，隐藏内部复杂性
    - Chain of Responsibility: 处理器按优先级链式执行
    - Observer: 进度回调机制

作者: FootballPrediction Architecture Team
版本: V24.0-alpha
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
import logging
from typing import Any

from .base import BaseProcessor, ProcessorResult
from .models import FeatureVector, MatchData, ProcessingContext
from .processors import (
    AdvancedPassingProcessor,
    AtomicProcessor,
    ContextProcessor,
    # V24.0 新增
    HistoricalRollingProcessor,
    InjuryImpactProcessor,
    LineupProcessor,
    # V22.0 新增
    LineupValueProcessor,
    # V23.0 新增
    MarketOddsProcessor,
    RefereeProcessor,
    TacticalCrossProcessor,
    TacticalProcessor,
)

logger = logging.getLogger(__name__)


@dataclass
class EngineConfig:
    """
    引擎配置

    Attributes:
        enable_parallel: 是否启用并行处理
        fail_fast: 是否快速失败（遇到错误立即停止）
        enable_checkpoint: 是否启用断点续传
        progress_callback: 进度回调函数
    """

    enable_parallel: bool = False
    fail_fast: bool = False
    enable_checkpoint: bool = True
    progress_callback: Callable[[str, float], None] | None = None


@dataclass
class EngineResult:
    """
    引擎执行结果

    Attributes:
        success: 是否成功
        feature_vector: 特征向量
        processor_results: 各处理器结果
        metadata: 执行元数据
        errors: 错误列表
        warnings: 警告列表
    """

    success: bool
    feature_vector: FeatureVector | None = None
    processor_results: dict[str, ProcessorResult] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @classmethod
    def success_result(
        cls,
        feature_vector: FeatureVector,
        processor_results: dict[str, ProcessorResult],
        metadata: dict[str, Any] | None = None,
    ) -> "EngineResult":
        """创建成功结果"""
        return cls(
            success=True,
            feature_vector=feature_vector,
            processor_results=processor_results,
            metadata=metadata or {},
        )

    @classmethod
    def failure_result(
        cls,
        errors: list[str] | str,
        processor_results: dict[str, ProcessorResult] | None = None,
    ) -> "EngineResult":
        """创建失败结果"""
        if isinstance(errors, str):
            errors = [errors]
        return cls(
            success=False,
            processor_results=processor_results or {},
            errors=errors,
        )


class FeatureEngine:
    """
    特征引擎主编排器

    职责:
        1. 管理所有处理器实例
        2. 按优先级调度处理器执行
        3. 聚合处理器结果为特征向量
        4. 支持断点续传和进度回调
        5. 提供统一的外部接口

    使用示例:
        >>> engine = FeatureEngine()
        >>> result = engine.extract_features(match_data)
        >>> if result.success:
        ...     features = result.feature_vector.to_dict()
        ...     print(f"Extracted {len(features)} features")
    """

    # 引擎版本
    engine_version = "24.0.0-alpha"
    # 引擎名称
    engine_name = "FootballPredictionFeatureEngine"

    def __init__(
        self,
        config: EngineConfig | None = None,
        processors: list[BaseProcessor] | None = None,
    ) -> None:
        """
        初始化特征引擎

        Args:
            config: 引擎配置
            processors: 自定义处理器列表（可选，默认使用内置处理器）
        """
        self.config = config or EngineConfig()

        # 初始化处理器
        if processors is not None:
            self.processors = processors
        else:
            self.processors = self._create_default_processors()

        # 按优先级排序
        self.processors.sort(key=lambda p: p.priority)

        # 记录处理器信息
        logger.info(f"{self.engine_name} v{self.engine_version} initialized with {len(self.processors)} processors")
        for proc in self.processors:
            logger.debug(f"  - {proc.processor_name} (priority={proc.priority})")

    def _create_default_processors(self) -> list[BaseProcessor[MatchData]]:
        """
        创建默认处理器集合

        V24.0 架构:
            - 优先级 10-19: 基础统计（AtomicProcessor）
            - 优先级 15: 历史追溯（HistoricalRollingProcessor, V24.0 新增）
            - 优先级 20-29: 战术分析（TacticalProcessor）
            - 优先级 30-39: 阵容与传球（LineupProcessor, AdvancedPassingProcessor）
            - 优先级 40-49: 裁判与上下文（RefereeProcessor, ContextProcessor）
            - 优先级 45: 战术交叉（TacticalCrossProcessor, V24.0 新增）
            - 优先级 50-59: 高级特征（LineupValueProcessor）
            - 优先级 55-59: 市场与伤停（MarketOddsProcessor, InjuryImpactProcessor）

        Returns:
            默认处理器列表
        """
        return [
            # P10: 原子级基础统计
            AtomicProcessor(),
            # P15: 历史追溯处理器（V24.0 新增）
            HistoricalRollingProcessor(),
            # P20: 战术特征
            TacticalProcessor(),
            # P30: 阵容稳定性
            LineupProcessor(),
            # P32: 深度传球 DNA（V22.0 新增）
            AdvancedPassingProcessor(),
            # P35: 阵容价值（V22.0 新增）
            LineupValueProcessor(),
            # P40: 裁判特征
            RefereeProcessor(),
            # P45: 战术交叉处理器（V24.0 新增）
            TacticalCrossProcessor(),
            # P50: 上下文特征
            ContextProcessor(),
            # P55: 市场赔率与偏见（V23.0 新增）
            MarketOddsProcessor(),
            # P58: 战损与伤停深度分析（V23.0 新增）
            InjuryImpactProcessor(),
        ]

    def register_processor(self, processor: BaseProcessor[MatchData]) -> None:
        """
        注册新处理器

        Args:
            processor: 待注册的处理器

        Example:
            >>> engine = FeatureEngine()
            >>> engine.register_processor(MyCustomProcessor())
        """
        self.processors.append(processor)
        self.processors.sort(key=lambda p: p.priority)
        logger.info(f"Registered processor: {processor.processor_name}")

    def extract_features(
        self,
        data: MatchData,
        context: ProcessingContext | None = None,
    ) -> EngineResult:
        """
        提取特征（主入口方法）

        Args:
            data: 比赛数据
            context: 处理上下文（可选）

        Returns:
            EngineResult: 引擎执行结果
        """
        # 初始化上下文
        if context is None:
            context = ProcessingContext(match_id=data.match_id)
        else:
            context.match_id = data.match_id

        # 记录开始时间
        start_time = datetime.now()

        # 存储各处理器结果
        processor_results: dict[str, ProcessorResult] = {}
        all_features: dict[str, Any] = {}
        all_errors: list[str] = []
        all_warnings: list[str] = []

        logger.info(f"Starting feature extraction for match {data.match_id}")

        try:
            # 执行所有处理器
            for i, processor in enumerate(self.processors):
                processor_name = processor.processor_name

                # 检查是否已完成（断点续传）
                if self.config.enable_checkpoint and context.is_completed(processor_name):
                    logger.debug(f"Skipping completed processor: {processor_name}")
                    continue

                # 进度回调
                if self.config.progress_callback:
                    progress = (i + 1) / len(self.processors)
                    self.config.progress_callback(processor_name, progress)

                logger.debug(f"Executing processor: {processor_name}")

                # 执行处理器
                result = processor.execute(data, context)
                processor_results[processor_name] = result

                # 收集错误和警告
                if result.errors:
                    all_errors.extend([f"{processor_name}: {e}" for e in result.errors])
                if result.warnings:
                    all_warnings.extend([f"{processor_name}: {w}" for w in result.warnings])

                # 检查是否快速失败
                if not result.success and self.config.fail_fast:
                    error_msg = f"Processor {processor_name} failed, aborting"
                    logger.error(error_msg)
                    all_errors.append(error_msg)
                    return EngineResult.failure_result(
                        errors=all_errors,
                        processor_results=processor_results,
                    )

                # 合并特征
                all_features.update(result.data)

                # 标记已完成（断点续传）
                if self.config.enable_checkpoint:
                    context.mark_completed(processor_name)

            # 创建特征向量
            feature_vector = FeatureVector(
                match_id=data.match_id,
                feature_version=self.engine_version,
                extracted_at=datetime.now(),
                **all_features,
            )

            # 计算执行时间
            execution_time = (datetime.now() - start_time).total_seconds()

            # 构建成功结果
            result = EngineResult.success_result(
                feature_vector=feature_vector,
                processor_results=processor_results,
                metadata={
                    "match_id": data.match_id,
                    "feature_count": len(all_features),
                    "processor_count": len(processor_results),
                    "execution_time_seconds": execution_time,
                    "engine_version": self.engine_version,
                    "processors": [p.processor_name for p in self.processors],
                },
            )

            # 添加警告
            result.warnings.extend(all_warnings)

            logger.info(
                f"Feature extraction completed for match {data.match_id}: "
                f"{len(all_features)} features in {execution_time:.2f}s"
            )

            return result

        except Exception as e:
            logger.error(f"Feature extraction failed for match {data.match_id}: {e}")
            all_errors.append(str(e))
            return EngineResult.failure_result(
                errors=all_errors,
                processor_results=processor_results,
            )

    def extract_features_batch(
        self,
        data_list: list[MatchData],
    ) -> list[EngineResult]:
        """
        批量提取特征

        Args:
            data_list: 比赛数据列表

        Returns:
            引擎执行结果列表
        """
        results = []

        logger.info(f"Starting batch feature extraction for {len(data_list)} matches")

        for i, data in enumerate(data_list):
            logger.debug(f"Processing match {i + 1}/{len(data_list)}: {data.match_id}")

            result = self.extract_features(data)
            results.append(result)

        # 统计
        success_count = sum(1 for r in results if r.success)
        logger.info(f"Batch extraction completed: {success_count}/{len(data_list)} successful")

        return results

    def get_processor_info(self) -> list[dict[str, Any]]:
        """
        获取处理器信息

        Returns:
            处理器信息列表
        """
        return [
            {
                "name": p.processor_name,
                "version": p.processor_version,
                "priority": p.priority,
                "enabled": p.config.enabled,
                "schema": p.get_feature_schema(),
            }
            for p in self.processors
        ]

    def get_total_feature_count(self) -> int:
        """
        获取特征总数（基于 Schema）

        Returns:
            特征总数
        """
        total = 0
        for p in self.processors:
            total += len(p.get_feature_schema())
        return total

    def __repr__(self) -> str:
        return (
            f"{self.engine_name}(v{self.engine_version}, "
            f"processors={len(self.processors)}, features={self.get_total_feature_count()})"
        )


# ============================================================================
# 便捷函数
# ============================================================================


def create_default_engine() -> FeatureEngine:
    """
    创建默认配置的特征引擎

    Returns:
        配置好的 FeatureEngine 实例
    """
    return FeatureEngine()


def extract_features_simple(data: MatchData) -> dict[str, Any]:
    """
    简单特征提取接口（一行代码提取特征）

    Args:
        data: 比赛数据

    Returns:
        特征字典

    Example:
        >>> features = extract_features_simple(match_data)
        >>> print(features["home_xg"])
        1.25
    """
    engine = create_default_engine()
    result = engine.extract_features(data)

    if result.success and result.feature_vector:
        return result.feature_vector.to_dict()
    logger.error(f"Feature extraction failed: {result.errors}")
    return {}
