#!/usr/bin/env python3
"""
L2 特征提取器 - 统一抽象基类
=====================================

定义了所有特征提取器必须遵循的接口规范，支持策略模式。

设计原则:
    - 开闭原则: 新增特征提取器无需修改基类
    - 依赖倒置: 高层模块依赖抽象而非具体实现
    - 单一职责: 每个提取器只负责一种特征提取策略

Author: Architecture Team
Version: V26.0 (Stable)
Date: 2025-12-27
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import structlog

from src.ml.feature_engine.legacy.exceptions import ExtractionError, InsufficientFeaturesError, ValidationError

logger = structlog.get_logger(__name__)


class ExtractionStatus(str, Enum):
    """提取状态枚举"""

    SUCCESS = "success"
    PARTIAL = "partial"  # 部分特征缺失但仍可用
    FAILED = "failed"
    SKIPPED = "skipped"  # 已存在最新版本，跳过


@dataclass
class ExtractionResult:
    """
    特征提取结果

    Attributes:
        status: 提取状态
        features: 提取的特征字典
        metadata: 元数据信息
        errors: 收集的错误列表
        warnings: 收集的警告列表
    """

    status: ExtractionStatus
    features: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def feature_count(self) -> int:
        """返回特征数量"""
        return len(self.features)

    @property
    def is_success(self) -> bool:
        """是否提取成功"""
        return self.status in (ExtractionStatus.SUCCESS, ExtractionStatus.PARTIAL)

    @property
    def has_errors(self) -> bool:
        """是否有错误"""
        return len(self.errors) > 0


@dataclass
class ValidationConfig:
    """
    验证配置

    Attributes:
        min_features: 最小特征维度要求
        max_features: 最大特征维度限制（可选）
        required_keys: 必需的特征键列表
        allow_partial: 是否允许部分特征缺失
    """

    min_features: int = 800  # 881 维的 90% 作为底线
    max_features: int | None = None
    required_keys: list[str] = field(default_factory=list)
    allow_partial: bool = True


class BaseExtractor(ABC):
    """
    特征提取器抽象基类

    所有 L2 特征提取器必须继承此类并实现抽象方法。

    子类必须实现:
        - extract(): 从原始数据中提取特征
        - validate(): 验证提取的特征

    可选重写:
        - pre_process(): 预处理原始数据
        - post_process(): 后处理提取的特征
        - get_version(): 返回版本号
    """

    # 类级别的默认验证配置
    DEFAULT_VALIDATION_CONFIG = ValidationConfig()

    def __init__(self, validation_config: ValidationConfig | None = None):
        """
        初始化提取器

        Args:
            validation_config: 验证配置，None 时使用默认配置
        """
        self._validation_config = validation_config or self.DEFAULT_VALIDATION_CONFIG
        self._logger = logger.bind(extractor=self.__class__.__name__)

    @abstractmethod
    def extract(self, raw_data: dict[str, Any]) -> ExtractionResult:
        """
        从原始数据中提取特征

        Args:
            raw_data: 原始 JSON 数据（来自 FotMob API）

        Returns:
            ExtractionResult: 提取结果对象

        Raises:
            ExtractionError: 提取过程中的严重错误
        """

    @abstractmethod
    def validate(self, features: dict[str, Any]) -> bool:
        """
        验证提取的特征

        Args:
            features: 提取的特征字典

        Returns:
            bool: 验证是否通过

        Raises:
            ValidationError: 验证失败时抛出
            InsufficientFeaturesError: 特征维度不足时抛出
        """

    def pre_process(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        """
        预处理原始数据（可选重写）

        默认实现返回原始数据。子类可重写以添加自定义预处理逻辑。

        Args:
            raw_data: 原始数据

        Returns:
            预处理后的数据
        """
        return raw_data

    def post_process(self, features: dict[str, Any]) -> dict[str, Any]:
        """
        后处理提取的特征（可选重写）

        默认实现返回原始特征。子类可重写以添加自定义后处理逻辑。

        Args:
            features: 提取的特征

        Returns:
            后处理的特征
        """
        return features

    @property
    @abstractmethod
    def version(self) -> str:
        """
        返回提取器版本号

        Returns:
            版本字符串，格式如 "V25.0"
        """

    @property
    def validation_config(self) -> ValidationConfig:
        """获取验证配置"""
        return self._validation_config

    def extract_with_validation(
        self, raw_data: dict[str, Any], skip_validation: bool = False
    ) -> ExtractionResult:
        """
        提取特征并验证（完整流程）

        这是一个模板方法，定义了提取的完整流程:
        1. 预处理
        2. 提取
        3. 后处理
        4. 验证
        5. 注入元数据

        Args:
            raw_data: 原始数据
            skip_validation: 是否跳过验证

        Returns:
            ExtractionResult: 完整的提取结果

        Raises:
            ExtractionError: 提取失败
            ValidationError: 验证失败且不允许部分结果
        """
        self._logger.info("开始特征提取", version=self.version)

        try:
            # Step 1: 预处理
            processed_data = self.pre_process(raw_data)

            # Step 2: 提取
            result = self.extract(processed_data)

            # Step 3: 后处理
            result.features = self.post_process(result.features)

            # Step 4: 验证
            if not skip_validation:
                try:
                    is_valid = self.validate(result.features)
                    if not is_valid:
                        raise ValidationError(f"特征验证失败: {self.version}")
                except (ValidationError, InsufficientFeaturesError) as e:
                    # 根据配置决定是否允许部分结果
                    # 允许 PARTIAL 或 FAILED 状态在 allow_partial=True 时继续
                    is_recoverable = result.status in (
                        ExtractionStatus.PARTIAL,
                        ExtractionStatus.FAILED,
                    )

                    if self._validation_config.allow_partial and is_recoverable:
                        self._logger.warning(
                            "特征验证部分失败，但允许继续",
                            errors=str(e),
                            feature_count=result.feature_count,
                            status=result.status.value,
                        )
                        result.warnings.append(str(e))
                        # 将 FAILED 状态降级为 PARTIAL
                        if result.status == ExtractionStatus.FAILED:
                            result.status = ExtractionStatus.PARTIAL
                    else:
                        self._logger.exception("特征验证失败", error=str(e))
                        raise

            # Step 5: 注入元数据
            result.metadata.update(
                {
                    "extractor_version": self.version,
                    "extractor_class": self.__class__.__name__,
                    "feature_count": result.feature_count,
                    "validation_passed": not result.has_errors,
                }
            )

            self._logger.info(
                "特征提取完成",
                status=result.status.value,
                feature_count=result.feature_count,
                has_errors=result.has_errors,
            )

            return result

        except Exception as e:
            self._logger.exception("特征提取异常", error=str(e), error_type=type(e).__name__)
            raise ExtractionError(f"{self.version} 特征提取失败: {e}") from e


class ExtractorRegistry:
    """
    提取器注册表（工厂模式的实现）

    用于管理所有可用的特征提取器，支持按版本号查找。
    """

    _extractors: dict[str, type[BaseExtractor]] = {}

    @classmethod
    def register(cls, extractor_class: type[BaseExtractor]) -> None:
        """
        注册提取器

        Args:
            extractor_class: 提取器类
        """
        # 创建临时实例获取版本号
        temp_instance = extractor_class()
        version = temp_instance.version
        cls._extractors[version] = extractor_class
        logger.info("提取器已注册", version=version, class_name=extractor_class.__name__)

    @classmethod
    def get(cls, version: str) -> type[BaseExtractor]:
        """
        获取指定版本的提取器类

        Args:
            version: 版本号

        Returns:
            提取器类

        Raises:
            KeyError: 版本不存在
        """
        if version not in cls._extractors:
            available = ", ".join(cls._extractors.keys())
            raise KeyError(f"未找到版本 {version} 的提取器。可用版本: {available}")
        return cls._extractors[version]

    @classmethod
    def create(cls, version: str, **kwargs: Any) -> BaseExtractor:
        """
        创建提取器实例

        Args:
            version: 版本号
            **kwargs: 传递给提取器构造函数的参数

        Returns:
            提取器实例
        """
        extractor_class = cls.get(version)
        return extractor_class(**kwargs)

    @classmethod
    def list_versions(cls) -> list[str]:
        """返回所有已注册的版本号"""
        return list(cls._extractors.keys())


def register_extractor(cls: type[BaseExtractor]) -> type[BaseExtractor]:
    """
    提取器注册装饰器

    使用方式:
        @register_extractor
        class V25ProductionExtractor(BaseExtractor):
            ...
    """
    ExtractorRegistry.register(cls)
    return cls
