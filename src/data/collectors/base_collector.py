# 数据收集器基础模块
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class CollectionResult:
    """数据收集结果."""

    success: bool
    data: Any = None
    error: str | None = None
    metadata: dict[str, Any] | None = None
    timestamp: datetime | None = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class BaseCollector:
    """数据收集器基类."""

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}

    async def collect(self, *args, **kwargs) -> CollectionResult:
        """收集数据的抽象方法."""
        raise NotImplementedError("Subclasses must implement collect method")

    def create_success_result(
        self, data: Any, metadata: dict[str, Any] | None = None
    ) -> CollectionResult:
        """创建成功的结果."""
        return CollectionResult(success=True, data=data, metadata=metadata)

    def create_error_result(
        self, error: str, metadata: dict[str, Any] | None = None
    ) -> CollectionResult:
        """创建错误的结果."""
        return CollectionResult(success=False, error=error, metadata=metadata)


def example():
    return None


EXAMPLE = "value"
