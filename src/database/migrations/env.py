"""
import asyncio
Alembic环境配置

配置数据库迁移环境，使用我们的数据库配置和模型。
"""

import asyncio
import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# 导入我们的数据库配置和模型
sys.path.append(os.path.join(os.path.dirname(__file__), "../../.."))

from src.database.base import Base  # noqa: E402
from src.database.config import get_database_config  # noqa: E402

# 导入所有模型以确保它们被注册到Base.metadata
from src.database.models import Odds  # noqa: F401, E402

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 获取数据库配置 - 优先使用测试环境配置
environment = os.getenv("ENVIRONMENT", "test")
db_config = get_database_config(environment)

# 设置数据库连接URL
config.set_main_option("sqlalchemy.url", db_config.alembic_url)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,  # 支持SQLite等数据库的批量操作
        compare_type=True,  # 比较列类型变化
        compare_server_default=True,  # 比较默认值变化
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    """运行迁移的辅助函数"""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=True,  # 支持SQLite等数据库的批量操作
        compare_type=True,  # 比较列类型变化
        compare_server_default=True,  # 比较默认值变化
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations():
    """在异步模式下运行迁移"""
    from sqlalchemy.ext.asyncio import create_async_engine

    connectable = create_async_engine(
        db_config.async_url,
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    # 检查是否在异步环境中
    try:
        # 如果当前已经有事件循环，使用异步方式
        asyncio.get_running_loop()
        asyncio.create_task(run_async_migrations())
        return
    except RuntimeError:
        # 没有运行中的事件循环，使用同步方式
        pass

    # 同步方式运行迁移
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        url=db_config.sync_url,
    )

    with connectable.connect() as connection:
        do_run_migrations(connection)


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
