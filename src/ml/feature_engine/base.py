"""
BaseProcessor - 特征处理器抽象基类
====================================

定义所有特征处理器必须遵循的接口规范。
采用插件化架构，新增特征类型无需修改核心代码。

设计模式:
    - Strategy Pattern: 处理器可替换算法
    - Template Method: 定义处理流程骨架
    - Dependency Injection: 通过上下文注入依赖

作者: FootballPrediction Architecture Team
版本: V21.0-alpha
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Generic, Optional, TypeVar

logger = logging.getLogger(__name__)

# 泛型类型定义
T = TypeVar("T")


@dataclass
class ProcessorResult:
    """
    处理器执行结果封装

    Attributes:
        success: 处理是否成功
        data: 提取的特征数据（字典形式）
        metadata: 处理过程元数据（耗时、版本等）
        errors: 错误信息列表（非阻塞错误）
        warnings: 警告信息列表

    Example:
        >>> result = ProcessorResult.success({"xg": 1.25})
        >>> result.with_warning("数据可能不完整")
    """

    success: bool
    data: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @classmethod
    def success_result(cls, data: dict[str, Any], metadata: dict[str, Any] | None = None) -> "ProcessorResult":
        """创建成功结果"""
        return cls(success=True, data=data, metadata=metadata or {})

    @classmethod
    def failure_result(cls, errors: list[str] | str, data: dict[str, Any] | None = None) -> "ProcessorResult":
        """创建失败结果"""
        if isinstance(errors, str):
            errors = [errors]
        return cls(success=False, data=data or {}, errors=errors)

    def with_warning(self, warning: str) -> "ProcessorResult":
        """添加警告信息"""
        self.warnings.append(warning)
        return self

    def with_error(self, error: str) -> "ProcessorResult":
        """添加错误信息（不改变success状态）"""
        self.errors.append(error)
        return self

    def merge(self, other: "ProcessorResult") -> "ProcessorResult":
        """合并两个结果"""
        return ProcessorResult(
            success=self.success and other.success,
            data={**self.data, **other.data},
            metadata={**self.metadata, **other.metadata},
            errors=self.errors + other.errors,
            warnings=self.warnings + other.warnings,
        )


@dataclass
class ProcessorConfig:
    """
    处理器配置基类

    Attributes:
        enabled: 是否启用该处理器
        timeout_ms: 超时时间（毫秒）
        retry_times: 失败重试次数
        strict_mode: 严格模式（任何错误视为失败）
    """

    enabled: bool = True
    timeout_ms: int = 5000
    retry_times: int = 1
    strict_mode: bool = False

    def validate(self) -> bool:
        """验证配置合法性"""
        if self.timeout_ms < 0:
            raise ValueError("timeout_ms must be non-negative")
        if self.retry_times < 0:
            raise ValueError("retry_times must be non-negative")
        return True


class BaseProcessor(ABC, Generic[T]):
    """
    特征处理器抽象基类

    所有特征处理器必须继承此类并实现 process() 方法。

    设计原则:
        - 单一职责: 每个处理器只负责一类特征
        - 开闭原则: 新增处理器不修改现有代码
        - 依赖倒置: 依赖抽象（MatchData）而非具体实现

    类型参数:
        T: 输入数据类型（通常是 MatchData）

    Example:
        >>> class MyProcessor(BaseProcessor[MatchData]):
        ...     def process(self, data: MatchData, context: ProcessingContext) -> ProcessorResult:
        ...         # 实现特征提取逻辑
        ...         return ProcessorResult.success_result({"my_feature": 1.0})
    """

    # 处理器名称（用于日志和配置）
    processor_name: str = "BaseProcessor"
    # 处理器版本（用于特征溯源）
    processor_version: str = "1.0.0"
    # 处理器优先级（数字越小越先执行）
    priority: int = 100

    def __init__(self, config: ProcessorConfig | None = None) -> None:
        """
        初始化处理器

        Args:
            config: 处理器配置，默认使用默认配置
        """
        self.config = config or ProcessorConfig()
        self.config.validate()
        self._setup()

    def _setup(self) -> None:
        """
        处理器初始化钩子（可选重写）

        用于资源初始化，如加载模型、建立连接等。
        """
        pass

    @abstractmethod
    def process(self, data: T, context: "ProcessingContext") -> ProcessorResult:
        """
        核心处理方法（必须实现）

        Args:
            data: 输入数据
            context: 处理上下文（包含共享状态）

        Returns:
            ProcessorResult: 处理结果，包含提取的特征

        Raises:
            NotImplementedError: 子类必须实现此方法
        """
        raise NotImplementedError(f"{self.processor_name} must implement process()")

    def pre_process(self, data: T, context: "ProcessingContext") -> tuple:
        """
        预处理钩子（可选重写）

        用于数据验证、转换等前置处理。

        Args:
            data: 原始输入数据
            context: 处理上下文

        Returns:
            处理后的数据和上下文
        """
        return data, context

    def post_process(self, result: ProcessorResult, context: "ProcessingContext") -> ProcessorResult:
        """
        后处理钩子（可选重写）

        用于结果校验、格式转换等后置处理。

        Args:
            result: 原始处理结果
            context: 处理上下文

        Returns:
            最终处理结果
        """
        return result

    def execute(self, data: T, context: Optional["ProcessingContext"] = None) -> ProcessorResult:
        """
        执行完整处理流程（模板方法）

        流程: pre_process -> process -> post_process

        Args:
            data: 输入数据
            context: 处理上下文（可选，默认创建新上下文）

        Returns:
            最终处理结果
        """
        if context is None:
            from .models import ProcessingContext

            context = ProcessingContext()

        if not self.config.enabled:
            logger.debug(f"{self.processor_name} is disabled, skipping")
            return ProcessorResult.success_result({}, metadata={"skipped": True})

        try:
            # 预处理
            processed_data, processed_context = self.pre_process(data, context)

            # 核心处理
            result = self.process(processed_data, processed_context)

            # 后处理
            final_result = self.post_process(result, processed_context)

            # 记录元数据
            final_result.metadata.update(
                {
                    "processor": self.processor_name,
                    "version": self.processor_version,
                    "priority": self.priority,
                }
            )

            return final_result

        except Exception as e:
            logger.error(f"{self.processor_name} failed: {e}", exc_info=True)
            if self.config.strict_mode:
                raise
            return ProcessorResult.failure_result(str(e))

    def validate_input(self, data: T) -> bool:
        """
        验证输入数据（可选重写）

        Args:
            data: 待验证的输入数据

        Returns:
            验证是否通过
        """
        return data is not None

    def get_feature_schema(self) -> dict[str, type]:
        """
        获取输出特征的 Schema（可选重写）

        Returns:
            特征名到类型的映射
        """
        return {}

    def __repr__(self) -> str:
        return f"{self.processor_name}(v{self.processor_version}, priority={self.priority})"
