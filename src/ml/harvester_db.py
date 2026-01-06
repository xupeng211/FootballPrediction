#!/usr/bin/env python3
"""
V20.8 Harvester 数据库连接管理器 - 自愈连接
=============================================

特性:
- 3 次重试机制
- 自动探测容器内外环境
- 连接池管理
- 健康检查

作者: SRE Lead
日期: 2025-12-25
版本: V20.8
"""

import logging
import time

import psycopg2
from psycopg2.extras import RealDictCursor

from src.ml.harvester_config import get_harvester_settings

logger = logging.getLogger(__name__)


class DatabaseConnectionError(Exception):
    """数据库连接错误"""



class HarvesterConnectionManager:
    """
    V20.8 Harvester 数据库连接管理器

    特性:
    - 自愈连接（3次重试）
    - 健康检查
    - 环境感知
    """

    def __init__(self):
        self.settings = get_harvester_settings()
        self._conn: psycopg2.extensions.connection | None = None

    def connect(self) -> psycopg2.extensions.connection:
        """
        建立数据库连接（带重试机制）

        Returns:
            psycopg2 连接对象

        Raises:
            DatabaseConnectionError: 连接失败
        """
        if self._is_connected():
            return self._conn

        db_params = self.settings.get_db_params()
        retry_attempts = self.settings.db_retry_attempts
        retry_delay = self.settings.db_retry_delay

        for attempt in range(1, retry_attempts + 1):
            try:
                logger.debug(f"数据库连接尝试 {attempt}/{retry_attempts}...")

                self._conn = psycopg2.connect(**db_params, cursor_factory=RealDictCursor)

                # 设置自动提交为 False（手动控制事务）
                self._conn.autocommit = False

                logger.info(f"✓ 数据库连接已建立: {db_params['host']}/{db_params['database']}")
                return self._conn

            except psycopg2.OperationalError as e:
                logger.warning(f"✗ 连接失败 (尝试 {attempt}/{retry_attempts}): {e}")

                if attempt < retry_attempts:
                    logger.info(f"等待 {retry_delay} 秒后重试...")
                    time.sleep(retry_delay)
                else:
                    error_msg = (
                        f"数据库连接失败，已重试 {retry_attempts} 次\n"
                        f"主机: {db_params['host']}\n"
                        f"数据库: {db_params['database']}\n"
                        f"用户: {db_params['user']}"
                    )
                    logger.error(error_msg)
                    raise DatabaseConnectionError(error_msg) from e

            except Exception as e:
                error_msg = f"数据库连接异常: {e}"
                logger.error(error_msg)
                raise DatabaseConnectionError(error_msg) from e

    def _is_connected(self) -> bool:
        """
        检查连接是否有效

        Returns:
            True 如果连接有效，否则 False
        """
        if self._conn is None or self._conn.closed:
            return False

        try:
            # 执行简单查询验证连接
            with self._conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
            return True
        except Exception:
            return False

    def get_connection(self) -> psycopg2.extensions.connection:
        """
        获取数据库连接（自动重连）

        Returns:
            psycopg2 连接对象
        """
        if not self._is_connected():
            return self.connect()
        return self._conn

    def health_check(self) -> bool:
        """
        数据库健康检查

        Returns:
            True 如果数据库健康，否则 False
        """
        try:
            conn = self.get_connection()
            with conn.cursor() as cur:
                cur.execute("SELECT version()")
                version = cur.fetchone()
                logger.debug(f"数据库健康检查通过: {version['version'][:50]}...")
            return True
        except Exception as e:
            logger.error(f"数据库健康检查失败: {e}")
            return False

    def close(self):
        """关闭数据库连接"""
        if self._conn and not self._conn.closed:
            self._conn.close()
            logger.info("数据库连接已关闭")

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()


# ==================== 单例模式 ====================
_connection_manager: HarvesterConnectionManager | None = None


def get_connection_manager() -> HarvesterConnectionManager:
    """
    获取数据库连接管理器单例

    Returns:
        HarvesterConnectionManager 实例
    """
    global _connection_manager
    if _connection_manager is None:
        _connection_manager = HarvesterConnectionManager()
    return _connection_manager


def close_connection_manager():
    """关闭连接管理器（用于清理）"""
    global _connection_manager
    if _connection_manager:
        _connection_manager.close()
        _connection_manager = None
