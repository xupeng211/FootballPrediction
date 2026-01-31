"""V145.1 L2 数据版本化迁移 - 添加 l2_raw_json 和 l2_data_version 字段

Revision ID: 003_v145
Revises: 002_v105
Create Date: 2026-01-06 10:00:00.000000

此迁移为 matches 表添加 L2 数据版本化支持：
1. 添加 l2_raw_json JSONB 字段 - 存储 FotMob L2 原始数据
2. 添加 l2_data_version VARCHAR(20) 字段 - 标记数据收割时的代码版本
3. 创建 JSONB GIN 索引 - 优化 L2 JSON 查询性能
4. 符合大厂数据湖标准 - 每条数据可追溯到收割版本
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "003_v145"
down_revision: str | None = "002_v105"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """升级：添加 L2 数据版本化字段"""

    # 1. 添加 l2_raw_json JSONB 字段
    op.execute("""
        ALTER TABLE matches
        ADD COLUMN IF NOT EXISTS l2_raw_json JSONB;
    """)

    # 2. 添加 l2_data_version VARCHAR 字段，默认值 V145.0
    op.execute("""
        ALTER TABLE matches
        ADD COLUMN IF NOT EXISTS l2_data_version VARCHAR(20) DEFAULT 'V145.0';
    """)

    # 3. 创建 JSONB GIN 索引用于高性能查询
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_matches_l2_raw_json_gin
        ON matches USING GIN(l2_raw_json);
    """)

    # 4. 创建部分索引 - 只索引已采集的 L2 数据
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_matches_l2_collected
        ON matches(id) WHERE l2_raw_json IS NOT NULL;
    """)

    # 5. 添加注释
    op.execute("""
        COMMENT ON COLUMN matches.l2_raw_json IS 'FotMob L2 原始数据 (JSONB格式)';
    """)

    op.execute("""
        COMMENT ON COLUMN matches.l2_data_version IS 'L2 数据收割代码版本 (如: V145.0, V145.1)';
    """)


def downgrade() -> None:
    """回滚：删除 L2 数据版本化字段"""

    # 删除索引
    op.execute("""
        DROP INDEX IF EXISTS idx_matches_l2_collected;
    """)

    op.execute("""
        DROP INDEX IF EXISTS idx_matches_l2_raw_json_gin;
    """)

    # 删除字段
    op.execute("""
        ALTER TABLE matches
        DROP COLUMN IF EXISTS l2_data_version;
    """)

    op.execute("""
        ALTER TABLE matches
        DROP COLUMN IF EXISTS l2_raw_json;
    """)
