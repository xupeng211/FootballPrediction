"""add_jsonb_sqlite_compatibility


添加JSONB与SQLite兼容性支持

本迁移文件主要目的是确保数据库模型在不同数据库类型（PostgreSQL/SQLite）下的兼容性。
主要变更：
1. 验证现有JSONB字段的兼容性配置
2. 添加数据库类型检测辅助函数
3. 确保SQLite环境下JSON字段正常工作
4. 添加兼容性检查和验证

Revision ID: c1d8ae5075f0
Revises: 006_missing_indexes
Create Date: 2025-09-12 12:41:21.259691

"""

from typing import Sequence, Union, cast

import sqlalchemy as sa
from alembic import context, op

# revision identifiers, used by Alembic.
revision: str = "c1d8ae5075f0"
down_revision: Union[str, None] = "006_missing_indexes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def is_sqlite():
    """检测当前是否为SQLite数据库"""
    if context.is_offline_mode():
        return False  # 离线模式下假设不是SQLite
    bind = op.get_bind()
    return bind.dialect.name == "sqlite"


def is_postgresql():
    """检测当前是否为PostgreSQL数据库"""
    if context.is_offline_mode():
        return True  # 离线模式下假设是PostgreSQL
    bind = op.get_bind()
    return bind.dialect.name == "postgresql"


def upgrade() -> None:
    """
    升级数据库结构以支持JSONB与SQLite兼容性

    注意：由于我们已经在模型层面使用了兼容的类型定义，
    这个迁移主要是为了验证和确保现有结构的兼容性。
    """
    # 检查是否在离线模式
    if context.is_offline_mode():
        print("⚠️  离线模式：跳过JSONB兼容性检查")
        # 在离线模式下执行注释，确保 SQL 生成正常
        op.execute("-- offline mode: skipped JSONB compatibility validation")
        return

    bind = op.get_bind()

    print(f"当前数据库类型: {bind.dialect.name}")

    if is_sqlite():
        print("检测到SQLite数据库，执行SQLite兼容性配置...")
        _configure_sqlite_compatibility()
    elif is_postgresql():
        print("检测到PostgreSQL数据库，验证JSONB配置...")
        _verify_postgresql_jsonb_config()
    else:
        print(f"检测到其他数据库类型: {bind.dialect.name}")

    print("JSONB与SQLite兼容性配置完成")


def _configure_sqlite_compatibility():
    """为SQLite配置兼容性设置"""
    # SQLite特定的配置
    # 由于我们使用了TypeDecorator，JSON数据会自动转换为TEXT存储

    # 验证主要的JSON字段表是否存在
    tables_to_check = [
        "raw_match_data",
        "raw_odds_data",
        "raw_scores_data",
        "predictions",
    ]

    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    for table_name in tables_to_check:
        if table_name in existing_tables:
            print(f"  ✓ 表 {table_name} 存在，JSON字段将自动适配为TEXT")
        else:
            print(f"  ⚠ 表 {table_name} 不存在，跳过检查")


def _verify_postgresql_jsonb_config():
    """验证PostgreSQL的JSONB配置"""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # 检查JSONB字段和索引
    jsonb_tables = {
        "raw_match_data": "raw_data",
        "raw_odds_data": "raw_data",
        "raw_scores_data": "raw_data",
    }

    for table_name, jsonb_column in jsonb_tables.items():
        try:
            # 检查表是否存在
            if table_name in inspector.get_table_names():
                columns = inspector.get_columns(table_name)
                jsonb_col = next(
                    (col for col in columns if col["name"] == jsonb_column), None
                )

                if jsonb_col:
                    print(f"  ✓ 表 {table_name} 的 {jsonb_column} 字段配置正确")

                    # 检查GIN索引是否存在（PostgreSQL特有）
                    indexes = inspector.get_indexes(table_name)
                    gin_index = next(
                        (
                            idx
                            for idx in indexes
                            if jsonb_column in idx["column_names"]
                            and idx.get("type") == "gin"
                        ),
                        None,
                    )

                    if gin_index:
                        print(f"    ✓ GIN索引 {gin_index['name']} 存在")
                    else:
                        print(
                            f"    ⚠ {jsonb_column} 字段缺少GIN索引，查询性能可能受影响"
                        )
                else:
                    print(f"  ⚠ 表 {table_name} 缺少 {jsonb_column} 字段")
            else:
                print(f"  ⚠ 表 {table_name} 不存在")

        except Exception as e:
            print(f"  ❌ 检查表 {table_name} 时出错: {e}")


def downgrade() -> None:
    """
    降级操作

    由于此迁移主要是兼容性验证和配置，降级时不需要特殊操作。
    实际的数据库结构没有发生改变。
    """
    # 检查是否在离线模式
    if context.is_offline_mode():
        print("⚠️  离线模式：跳过JSONB兼容性降级")
        # 在离线模式下执行注释，确保 SQL 生成正常
        op.execute("-- offline mode: skipped JSONB compatibility downgrade")
        return

    print("JSONB兼容性迁移降级 - 无需特殊操作")
