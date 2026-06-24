"""
Alembic环境配置

配置数据库迁移环境，使用我们的数据库配置和模型。
"""

import asyncio
from logging.config import fileConfig
import os
import sys

from alembic import context
from sqlalchemy import engine_from_config, pool

# 修复sys.path问题 - 确保能找到src模块
project_root = os.getcwd()
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 备用路径计算方式
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root_alt = os.path.abspath(os.path.join(current_dir, "../../../"))
if project_root_alt not in sys.path:
    sys.path.insert(0, project_root_alt)


try:
    from src.config import get_settings
    from src.database.base import Base

    # Odds model import removed - not needed for migrations
    # 提供兼容的 get_database_config 函数
    def get_database_config():
        """获取数据库配置（从 src.config）"""
        return get_settings().database

except ImportError:
    sys.exit(1)

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
# 注意：config只在alembic运行时可用，不要在import时直接使用
config = None


def setup_logging():
    """设置日志配置"""
    try:
        from alembic import context

        if hasattr(context, "config") and context.config.config_file_name is not None:
            fileConfig(context.config.config_file_name)
    except Exception:
        # 忽略日志配置错误，继续执行
        pass


def get_database_url():
    """获取数据库URL，优先使用环境变量"""
    env_url = os.getenv("DATABASE_URL")
    if env_url:
        return env_url
    # 回退到配置文件（通过 src.config.get_settings()）
    db_config = get_database_config()
    return db_config.get_connection_string()


# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


# SC-002 Mitigation: Alembic migration runtime guard.
# Guard rules: (1) production-like host -> hard block; (2) ALEMBIC_CTX
# auto-allow; (3) standard SC-002 gates; (4) offline mode NOT guarded.
# Design doc: docs/SC002_ALEMBIC_MIGRATION_GUARD_DESIGN.md


def _check_alembic_migration_guard() -> None:
    """Check SC-002 migration guard before executing Alembic migrations online.

    Must be called BEFORE any DB engine creation, connection, or
    ``context.run_migrations()``.

    Raises :exc:`DbWriteBlockedError` if the migration is blocked.
    """
    import os

    # Import guard helper inline to avoid import errors when env.py is loaded
    # for offline mode (--sql) where the full application config is unavailable.
    from scripts.ops.helpers.python_db_write_guard import assert_db_write_allowed

    alembic_ctx = os.getenv("ALEMBIC_CTX", "").strip().lower()

    # ── CI / dev / Docker init auto-allow ──────────────────────────────────
    # ALLOW_SCHEMA_WRITE=yes is sufficient for controlled CI/dev environments.
    allow_schema = os.getenv("ALLOW_SCHEMA_WRITE", "").strip().lower() == "yes"
    if alembic_ctx in ("ci", "docker_init", "dev") and allow_schema:
        return
    # If ALEMBIC_CTX is set but ALLOW_SCHEMA_WRITE is missing, fall through
    # to the full guard check below.

    # ── Standard SC-002 gate for all other contexts ────────────────────────
    # The guard helper enforces:
    #   - Production env detection → hard block
    #   - Production DB host → hard block
    #   - DRY_RUN default (true → returns early, no write)
    #   - ALLOW_DB_WRITE=yes, FINAL_DB_WRITE_CONFIRMATION=yes
    #   - ALLOW_SCHEMA_WRITE=yes (because operation is CREATE → high-risk)
    assert_db_write_allowed(
        script_name="env.py (Alembic migration)",
        operation="CREATE",  # triggers schema-level gate in guard helper
        target="alembic_migration (schema-level)",
        tables=["alembic_version"],
    )


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
    setup_logging()  # 设置日志
    url = get_database_url()
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
    setup_logging()  # 设置日志
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

    db_config = get_database_config()  # 重新获取配置
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
    # ── SC-002: Migration runtime guard ────────────────────────────────────
    # Must be the FIRST thing — before any DB engine, connection, or migration.
    _check_alembic_migration_guard()

    # 获取配置
    database_url = get_database_url()

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
        {"sqlalchemy.url": database_url},  # 直接使用URL，不依赖config
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        do_run_migrations(connection)


# 运行迁移的入口点 - Alembic会自动调用适当的函数
