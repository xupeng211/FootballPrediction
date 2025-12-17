"""
Alembic环境配置

配置数据库迁移环境，使用我们的数据库配置和模型。
"""

import asyncio
import os
import sys
from logging.config import fileConfig

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

print(f"Alembic Debug: sys.path = {sys.path}")
print(f"Alembic Debug: project_root = {project_root}")

try:
    from src.database.base import Base  # noqa: E402
    from src.database.config import get_database_config  # noqa: E402
    from src.database.models import Odds  # noqa: F401, E402
    print("✅ Alembic: 所有模块导入成功")
except ImportError as e:
    print(f"❌ Alembic: 模块导入失败: {e}")
    sys.exit(1)

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
# 注意：config只在alembic运行时可用，不要在import时直接使用
config = None

def setup_logging():
    """设置日志配置"""
    try:
        from alembic import context
        if hasattr(context, 'config') and context.config.config_file_name is not None:
            fileConfig(context.config.config_file_name)
    except Exception as e:
        print(f"⚠️ Alembic: 日志配置失败，使用默认日志: {e}")
        # 忽略日志配置错误，继续执行

def get_database_url():
    """获取数据库URL，优先使用环境变量"""
    env_url = os.getenv("DATABASE_URL")
    if env_url:
        print(f"✅ Alembic: 使用环境变量DATABASE_URL = {env_url}")
        return env_url
    else:
        # 回退到配置文件
        db_config = get_database_config()
        print(f"✅ Alembic: 使用配置文件URL = {db_config.alembic_url}")
        return db_config.alembic_url

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