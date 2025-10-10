"""
import asyncio
    from sqlalchemy.ext.asyncio import create_async_engine

from src.database.base import Base  # noqa: E402
from src.database.config import get_database_config  # noqa: E402
from src.database.models import Odds  # noqa: F401, E402

Alembic环境配置

配置数据库迁移环境，使用我们的数据库配置和模型。
"""

# 导入我们的数据库配置和模型
sys.path.append(os.path.join(os.path.dirname(__file__), "../../.."))  # type: ignore


# 导入所有模型以确保它们被注册到Base.metadata

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config  # type: ignore

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)  # type: ignore

# 获取数据库配置 - 优先使用测试环境配置
environment = os.getenv("ENVIRONMENT", "test")  # type: ignore

# 检查是否使用本地数据库（用于本地开发环境）
use_local_db = os.getenv("USE_LOCAL_DB", "false").lower() == "true"  # type: ignore

# 检查是否在CI环境中
in_ci = os.getenv("GITHUB_ACTIONS", "false").lower() == "true"  # type: ignore

# 获取数据库配置
db_config = get_database_config(environment)  # type: ignore

# 如果使用本地数据库或在CI环境中，覆盖数据库主机配置
if use_local_db or in_ci:
    # 为本地开发修改数据库配置
    db_config.host = "localhost"
    db_config.port = "5432"
    # 重新构建URL

    parsed_url = urlparse(db_config.alembic_url)  # type: ignore
    local_url = urlunparse(  # type: ignore
        (
            parsed_url.scheme,
            f"{parsed_url.username}:{parsed_url.password}@localhost:5432",
            parsed_url.path,
            parsed_url.params,
            parsed_url.query,
            parsed_url.fragment,
        )
    )
    config.set_main_option("sqlalchemy.url", local_url)
else:
    # 设置数据库连接URL
    config.set_main_option("sqlalchemy.url", db_config.alembic_url)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata  # type: ignore

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
    context.configure(  # type: ignore
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,  # 支持SQLite等数据库的批量操作
        compare_type=True,  # 比较列类型变化
        compare_server_default=True,  # 比较默认值变化
    )

    with context.begin_transaction():  # type: ignore
        context.run_migrations()  # type: ignore


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
        asyncio.get_running_loop()  # type: ignore
        asyncio.create_task(run_async_migrations())  # type: ignore
        return
    except RuntimeError:
        # 没有运行中的事件循环，使用同步方式
        pass

    # 同步方式运行迁移
    connectable = engine_from_config(  # type: ignore
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,  # type: ignore
        url=db_config.sync_url,
    )

    with connectable.connect() as connection:
        do_run_migrations(connection)


if context.is_offline_mode():  # type: ignore
    run_migrations_offline()
else:
    run_migrations_online()
