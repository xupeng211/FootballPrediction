"""
数据库会话管理器

提供同步和异步数据库会话的上下文管理
"""

import logging
from contextlib import asynccontextmanager, contextmanager
from typing import AsyncGenerator, Generator

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from src.database.connection.pools.engine_manager import DatabaseEngineManager
from src.utils.retry import RetryConfig, retry

logger = logging.getLogger(__name__)


class DatabaseSessionManager:
    """
    数据库会话管理器

    提供同步和异步数据库会话的上下文管理器，自动处理事务
    """

    def __init__(self, engine_manager: DatabaseEngineManager):
        """
        初始化会话管理器

        Args:
            engine_manager: 数据库引擎管理器
        """
        self.engine_manager = engine_manager

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """
        获取同步数据库会话上下文管理器

        提供一个同步数据库会话的上下文管理器，自动处理事务提交和回滚。

        Yields:
            Session: 同步数据库会话

        Raises:
            Exception: 当数据库操作发生错误时抛出

        Example:
            ```python
            session_manager = DatabaseSessionManager(engine_manager)

            # 使用同步会话进行数据库操作
            with session_manager.get_session() as session:
                # 执行数据库查询
                result = session.query(SomeModel).all()
                # 执行数据库更新
                session.add(new_record)
                # 自动提交或回滚
            ```

        Note:
            会话在使用完毕后会自动关闭。
        """
        if not self.engine_manager.is_initialized:
            raise RuntimeError("数据库引擎未初始化")

        session = self.engine_manager.create_session()
        try:
            yield session
            session.commit()
            logger.debug("同步数据库事务已提交")
        except Exception as e:
            session.rollback()
            logger.error(f"数据库操作失败: {e}")
            raise
        finally:
            session.close()

    @asynccontextmanager
    async def get_async_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        获取异步数据库会话上下文管理器

        提供一个异步数据库会话的上下文管理器，自动处理事务提交和回滚。

        Yields:
            AsyncSession: 异步数据库会话

        Raises:
            Exception: 当异步数据库操作发生错误时抛出

        Example:
            ```python
            session_manager = DatabaseSessionManager(engine_manager)

            # 使用异步会话进行数据库操作
            async with session_manager.get_async_session() as session:
                # 执行异步数据库查询
                result = await session.execute(select(SomeModel))
                # 执行异步数据库更新
                session.add(new_record)
                # 自动提交或回滚
            ```

        Note:
            会话在使用完毕后会自动关闭。
        """
        if not self.engine_manager.is_initialized:
            raise RuntimeError("数据库引擎未初始化")

        session = self.engine_manager.create_async_session()
        try:
            yield session
            await session.commit()
            logger.debug("异步数据库事务已提交")
        except Exception as e:
            await session.rollback()
            logger.error(f"异步数据库操作失败: {e}")
            raise
        finally:
            await session.close()

    def get_sync_session(self) -> Session:
        """
        获取同步数据库会话（非上下文管理器）

        用于需要手动管理会话生命周期的场景

        Returns:
            Session: 同步数据库会话

        Warning:
            使用此方法需要手动管理事务和会话关闭
        """
        if not self.engine_manager.is_initialized:
            raise RuntimeError("数据库引擎未初始化")

        return self.engine_manager.create_session()

    def get_async_session_obj(self):
        """
        获取异步数据库会话（非上下文管理器）

        用于需要手动管理会话生命周期的场景

        Returns:
            AsyncSession: 异步数据库会话

        Warning:
            使用此方法需要手动管理事务和会话关闭
        """
        if not self.engine_manager.is_initialized:
            raise RuntimeError("数据库引擎未初始化")

        return self.engine_manager.create_async_session()

    @retry(config=RetryConfig(max_attempts=3, base_delay=0.5))
    def execute_with_retry(self, session: Session, operation):
        """
        带重试机制执行同步数据库操作

        Args:
            session: 数据库会话
            operation: 要执行的操作

        Returns:
            操作结果
        """
        try:
            return operation(session)
        except Exception as e:
            logger.warning(f"数据库操作失败，准备重试: {e}")
            raise

    @retry(config=RetryConfig(max_attempts=3, base_delay=0.5))
    async def execute_async_with_retry(self, session: AsyncSession, operation):
        """
        带重试机制执行异步数据库操作

        Args:
            session: 异步数据库会话
            operation: 要执行的操作

        Returns:
            操作结果
        """
        try:
            return await operation(session)
        except Exception as e:
            logger.warning(f"异步数据库操作失败，准备重试: {e}")
            raise