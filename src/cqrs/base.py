from typing import Any, Dict, List, Optional, Union

"""
CQRS基础类
CQRS Base Classes

定义命令、查询和处理器的基础接口。
Defines base interfaces for commands, queries, and handlers.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from dataclasses import dataclass
import uuid

# 定义泛型类型
CommandResultType = TypeVar("CommandResultType")
QueryResultType = TypeVar("QueryResultType")


@dataclass
class BaseMessage:
    """消息基类"""

    message_id: str
    timestamp: datetime
    metadata: Dict[str, Any]

    def __init__(self, metadata: Optional[Dict[str, Any]] = None):
        self.message_id = str(uuid.uuid4())
        self.timestamp = datetime.utcnow()
        self._metadata = metadata or {}


class Command(BaseMessage, ABC):
    """命令基类

    命令表示改变系统状态的意图。
    Commands represent intentions to change system state.
    """

    def __init__(self, metadata: Optional[Dict[str, Any]] = None):
        super().__init__(metadata)
        self.correlation_id: Optional[str] = None
        self.causation_id: Optional[str] = None


class Query(BaseMessage, ABC):
    """查询基类

    查询表示获取系统数据的请求。
    Queries represent requests to retrieve system data.
    """

    def __init__(self, metadata: Optional[Dict[str, Any]] = None):
        super().__init__(metadata)


class CommandHandler(ABC, Generic[CommandResultType]):
    """命令处理器基类

    处理特定类型的命令。
    Handles specific types of commands.
    """

    @abstractmethod
    async def handle(self, command: Command) -> CommandResultType:
        """处理命令"""
        pass

    @property
    @abstractmethod
    def command_type(self) -> type:
        """支持的命令类型"""
        pass


class QueryHandler(ABC, Generic[QueryResultType]):
    """查询处理器基类

    处理特定类型的查询。
    Handles specific types of queries.
    """

    @abstractmethod
    async def handle(self, query: Query) -> QueryResultType:
        """处理查询"""
        pass

    @property
    @abstractmethod
    def query_type(self) -> type:
        """支持的查询类型"""
        pass


class ValidationResult:
    """验证结果"""

    def __init__(self, is_valid: bool, errors: Optional[list] = None):
        self.is_valid = is_valid
        self.errors = errors or []

    @classmethod
    def success(cls) -> "ValidationResult":
        """创建成功的验证结果"""
        return cls(True)

    @classmethod
    def failure(cls, errors: list) -> "ValidationResult":
        """创建失败的验证结果"""
        return cls(False, errors)


class ValidatableCommand(Command, ABC):
    """可验证的命令基类"""

    @abstractmethod
    async def validate(self) -> ValidationResult:
        """验证命令"""
        pass


class ValidatableQuery(Query, ABC):
    """可验证的查询基类"""

    @abstractmethod
    async def validate(self) -> ValidationResult:
        """验证查询"""
        pass
