from typing import Any, Dict, List, Optional, Union
"""
命令和查询总线
Command and Query Bus

实现命令和查询的分发机制。
Implements dispatching mechanism for commands and queries.
"""

import logging
from .base import Command, Query, CommandHandler, QueryHandler

logger = logging.getLogger(__name__)


class CommandBus:
    """命令总线

    负责将命令分发给对应的处理器。
    Responsible for dispatching commands to their handlers.
    """

    def __init__(self):
        self._handlers: Dict[str, Any][Type[Any, Command], CommandHandler] = {}
        self._middleware: list = []

    def register_handler(
        self, command_type: Type[Any, Command], handler: CommandHandler
    ) -> None:
        """注册命令处理器"""
        self._handlers[command_type] = handler
        logger.info(
            f"注册命令处理器: {command_type.__name__} -> {handler.__class__.__name__}"
        )

    def register_middleware(self, middleware) -> None:
        """注册中间件"""
        self._middleware.append(middleware)

    async def dispatch(self, command: Command) -> Any:
        """分发命令"""
        command_type = type(command)

        if command_type not in self._handlers:
            raise ValueError(f"没有找到命令 {command_type.__name__} 的处理器")

        handler = self._handlers[command_type]

        # 执行中间件
        for middleware in self._middleware:
            command = await middleware.process(command)

        logger.info(f"分发命令: {command_type.__name__}")

        # 验证命令
        if hasattr(command, "validate"):
            validation_result = await command.validate()
            if not validation_result.is_valid:
                raise ValueError(f"命令验证失败: {', '.join(validation_result.errors)}")

        # 处理命令
        _result = await handler.handle(command)

        logger.info(f"命令处理完成: {command_type.__name__}")

        return result

    def get_registered_commands(self) -> Dict[str, str]:
        """获取已注册的命令"""
        return {
            cmd_type.__name__: handler.__class__.__name__
            for cmd_type, handler in self._handlers.items()
        }


class QueryBus:
    """查询总线

    负责将查询分发给对应的处理器。
    Responsible for dispatching queries to their handlers.
    """

    def __init__(self):
        self._handlers: Dict[str, Any][Type[Any, Query], QueryHandler] = {}
        self._middleware: list = []

    def register_handler(self, query_type: Type[Any, Query], handler: QueryHandler) -> None:
        """注册查询处理器"""
        self._handlers[query_type] = handler
        logger.info(
            f"注册查询处理器: {query_type.__name__} -> {handler.__class__.__name__}"
        )

    def register_middleware(self, middleware) -> None:
        """注册中间件"""
        self._middleware.append(middleware)

    async def dispatch(self, query: Query) -> Any:
        """分发查询"""
        query_type = type(query)

        if query_type not in self._handlers:
            raise ValueError(f"没有找到查询 {query_type.__name__} 的处理器")

        handler = self._handlers[query_type]

        # 执行中间件
        for middleware in self._middleware:
            query = await middleware.process(query)

        logger.info(f"分发查询: {query_type.__name__}")

        # 验证查询
        if hasattr(query, "validate"):
            validation_result = await query.validate()
            if not validation_result.is_valid:
                raise ValueError(f"查询验证失败: {', '.join(validation_result.errors)}")

        # 处理查询
        _result = await handler.handle(query)

        logger.info(f"查询处理完成: {query_type.__name__}")

        return result

    def get_registered_queries(self) -> Dict[str, str]:
        """获取已注册的查询"""
        return {
            query_type.__name__: handler.__class__.__name__
            for query_type, handler in self._handlers.items()
        }


# 全局实例
_command_bus: Optional[CommandBus] = None
_query_bus: Optional[QueryBus] = None
def get_command_bus() -> CommandBus:
    """获取命令总线实例"""
    global _command_bus
    if _command_bus is None:
        _command_bus = CommandBus()
    return _command_bus


def get_query_bus() -> QueryBus:
    """获取查询总线实例"""
    global _query_bus
    if _query_bus is None:
        _query_bus = QueryBus()
    return _query_bus


# 中间件示例
class LoggingMiddleware:
    """日志中间件"""

    async def process(self, message):
        """处理消息"""
        message_type = type(message).__name__
        logger.info(f"处理消息: {message_type} (ID: {message.message_id})")
        return message


class ValidationMiddleware:
    """验证中间件"""

    async def process(self, message):
        """处理消息"""
        if hasattr(message, "validate"):
            validation_result = await message.validate()
            if not validation_result.is_valid:
                logger.error(f"消息验证失败: {', '.join(validation_result.errors)}")
                raise ValueError(f"消息验证失败: {', '.join(validation_result.errors)}")
        return message


class MetricsMiddleware:
    """指标中间件"""

    def __init__(self):
        self._metrics = {
            "commands_processed": 0,
            "queries_processed": 0,
            "processing_times": [],
        }

    async def process(self, message):
        """处理消息"""
        import time

        time.time()

        type(message).__name__
        if isinstance(message, Command):
            self._metrics["commands_processed"] += 1
        elif isinstance(message, Query):
            self._metrics["queries_processed"] += 1

        return message

    def get_metrics(self) -> Dict[str, Any]:
        """获取指标"""
        return self._metrics.copy()  # type: ignore
