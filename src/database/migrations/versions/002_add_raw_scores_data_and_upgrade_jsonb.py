# mypy: ignore-errors
import logging
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import DatabaseError, SQLAlchemyError

# revision identifiers, used by Alembic.


# 检查是否在SQLite环境中（测试环境）

# 1. 创建Bronze层原始比分数据表
# 快速检索字段（从JSONB中提取）
# 时间戳字段

# 为raw_scores_data表创建索引

# 为JSONB字段创建GIN索引，支持高效的JSON查询（仅PostgreSQL）

# 2. 升级现有表的JSON字段为JSONB（仅PostgreSQL环境）
# 注意：这需要在实际应用时谨慎操作，可能需要数据迁移
# 升级raw_match_data表
# 为JSONB创建GIN索引

# 升级raw_odds_data表
# 为JSONB创建GIN索引

# 如果升级失败，记录警告但不中断迁移

# 3. 为Bronze层表添加分区准备（按月分区）
# 注意：实际的分区实现需要在数据库层面进行，这里只是准备工作

# PostgreSQL环境：创建分区管理函数（可选，用于自动创建分区）


# 4. 添加数据质量约束
# 为raw_scores_data添加检查约束（PostgreSQL环境）

# SQLite环境：跳过约束添加

# 5. 添加触发器自动更新updated_at字段

# 为raw_scores_data表创建更新时间触发器


# 检查数据库方言

# 删除触发器和函数（仅PostgreSQL环境）


# 删除raw_scores_data表的索引


# 删除约束（仅PostgreSQL环境）

# 删除raw_scores_data表

# 删除其他表的JSONB索引（如果存在）
# 忽略索引不存在的错误，但记录日志

# 注意:将JSONB降级回JSON需要谨慎处理,这里不自动执行
# 如果需要,可以手动执行:
# ALTER TABLE raw_match_data ALTER COLUMN raw_data TYPE JSON;
# ALTER TABLE raw_odds_data ALTER COLUMN raw_data TYPE JSON;
logger = logging.getLogger(__name__)
"""add_raw_scores_data_and_upgrade_jsonb"
Revision ID: 002_add_raw_scores_data_and_upgrade_jsonb
Revises: f48d412852cc
Create Date: 2025-09-10 18:20:30.000000
"""
revision: str = "002_add_raw_scores_data_and_upgrade_jsonb"
down_revision: str | None = "f48d412852cc"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """
    添加raw_scores_data表并升级现有Bronze层表为JSONB
    变更内容:
    1. 创建raw_scores_data表（Bronze层比分数据）
    2. 升级raw_match_data和raw_odds_data表的JSON字段为JSONB
    3. 添加分区策略（按月分区）
    4. 创建相关索引优化查询性能
    """
    conn = op.get_bind()
    db_dialect = conn.dialect.name.lower()
    op.create_table(
        "raw_scores_data",
        sa.Column("id", sa.Integer(), nullable=False, comment="主键ID"),
        sa.Column(
            "data_source",
            sa.String(length=100),
            nullable=False,
            comment="数据源标识",
        ),
        sa.Column(
            "raw_data",
            (
                sa.JSON()
                if db_dialect == "sqlite"
                else postgresql.JSONB(astext_type=sa.Text())
            ),
            nullable=False,
            comment="原始JSON数据",
        ),
        sa.Column("collected_at", sa.DateTime(), nullable=False, comment="采集时间"),
        sa.Column(
            "processed",
            sa.Boolean(),
            nullable=False,
            default=False,
            comment="是否已处理",
        ),
        sa.Column(
            "external_match_id",
            sa.String(length=100),
            nullable=True,
            comment="外部比赛ID",
        ),
        sa.Column(
            "match_status",
            sa.String(length=50),
            nullable=True,
            comment="比赛状态",
        ),
        sa.Column("home_score", sa.Integer(), nullable=True, comment="主队比分"),
        sa.Column("away_score", sa.Integer(), nullable=True, comment="客队比分"),
        sa.Column("match_minute", sa.Integer(), nullable=True, comment="比赛分钟"),
        sa.Column("created_at", sa.DateTime(), nullable=False, comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, comment="更新时间"),
        sa.PrimaryKeyConstraint("id"),
        comment="Bronze层原始比分数据表",
    )
    op.create_index("idx_raw_scores_data_source", "raw_scores_data", ["data_source"])
    op.create_index(
        "idx_raw_scores_data_collected_at", "raw_scores_data", ["collected_at"]
    )
    op.create_index("idx_raw_scores_data_processed", "raw_scores_data", ["processed"])
    op.create_index(
        "idx_raw_scores_data_external_match", "raw_scores_data", ["external_match_id"]
    )
    op.create_index("idx_raw_scores_data_status", "raw_scores_data", ["match_status"])
    op.create_index(
        "idx_raw_scores_data_score", "raw_scores_data", ["home_score", "away_score"]
    )
    if db_dialect != "sqlite":
        op.create_index(
            "idx_raw_scores_data_jsonb_gin",
            "raw_scores_data",
            ["raw_data"],
            postgresql_using="gin",
        )
    else:
        logger.info("⚠️  SQLite环境:跳过JSONB GIN索引创建")
    if db_dialect != "sqlite":
        try:
            op.execute(
                "ALTER TABLE raw_match_data ALTER COLUMN raw_data TYPE JSONB USING raw_data::jsonb"
            )
            op.create_index(
                "idx_raw_match_data_jsonb_gin",
                "raw_match_data",
                ["raw_data"],
                postgresql_using="gin",
            )
            op.execute(
                "ALTER TABLE raw_odds_data ALTER COLUMN raw_data TYPE JSONB USING raw_data::jsonb"
            )
            op.create_index(
                "idx_raw_odds_data_jsonb_gin",
                "raw_odds_data",
                ["raw_data"],
                postgresql_using="gin",
            )
        except (SQLAlchemyError, DatabaseError, ConnectionError, TimeoutError) as e:
            logger.info(f"Warning: Failed to upgrade JSON to JSONB: {e}")
    else:
        logger.info("⚠️  SQLite环境:跳过JSON到JSONB的升级")
    if db_dialect != "sqlite":
        op.execute(
            """
        CREATE OR REPLACE FUNCTION create_monthly_partition(table_name TEXT, year_month TEXT)
        RETURNS void AS $$
        DECLARE
            partition_name TEXT;
            start_date DATE;
            end_date DATE;
        BEGIN
            partition_name := table_name || '_' || year_month;
            start_date := (year_month || '-01')::DATE;
            end_date := start_date + INTERVAL '1 month';
            -- 创建分区表（仅作为示例,实际实现需要根据具体需求调整）
            EXECUTE format('CREATE TABLE IF NOT EXISTS %I PARTITION OF %I'
                            FOR VALUES FROM (%L) TO (%L)','
                           partition_name, table_name, start_date, end_date);
        END;
        $$ LANGUAGE plpgsql;
        """
        )
    if db_dialect != "sqlite":
        op.create_check_constraint(
            "ck_raw_scores_data_scores_range",
            "raw_scores_data",
            "home_score >= 0 AND home_score <= 99 AND away_score >= 0 AND away_score <= 99",
        )
        op.create_check_constraint(
            "ck_raw_scores_data_minute_range",
            "raw_scores_data",
            "match_minute IS NULL OR (match_minute >= 0 AND match_minute <= 150)",
        )
    else:
        logger.info("⚠️  SQLite环境:跳过检查约束添加")
    if db_dialect != "sqlite":
        op.execute(
            """
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
        )
        op.execute(
            """
        CREATE TRIGGER trigger_raw_scores_data_updated_at
            BEFORE UPDATE ON raw_scores_data
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
        """
        )


def downgrade() -> None:
    """
    回滚raw_scores_data表和JSONB升级的更改
    """
    conn = op.get_bind()
    db_dialect = conn.dialect.name.lower()
    if db_dialect != "sqlite":
        op.execute(
            "DROP TRIGGER IF EXISTS trigger_raw_scores_data_updated_at ON raw_scores_data"
        )
        op.execute("DROP FUNCTION IF EXISTS update_updated_at_column()")
        op.execute("DROP FUNCTION IF EXISTS create_monthly_partition(TEXT, TEXT)")
    else:
        logger.info("⚠️  SQLite环境:跳过触发器和函数删除")
    try:
        op.drop_index("idx_raw_scores_data_jsonb_gin", table_name="raw_scores_data")
    except (SQLAlchemyError, DatabaseError):
        logger.info("⚠️  索引idx_raw_scores_data_jsonb_gin不存在,跳过删除")
    op.drop_index("idx_raw_scores_data_score", table_name="raw_scores_data")
    op.drop_index("idx_raw_scores_data_status", table_name="raw_scores_data")
    op.drop_index("idx_raw_scores_data_external_match", table_name="raw_scores_data")
    op.drop_index("idx_raw_scores_data_processed", table_name="raw_scores_data")
    op.drop_index("idx_raw_scores_data_collected_at", table_name="raw_scores_data")
    op.drop_index("idx_raw_scores_data_source", table_name="raw_scores_data")
    if db_dialect != "sqlite":
        try:
            op.drop_constraint("ck_raw_scores_data_minute_range", "raw_scores_data")
            op.drop_constraint("ck_raw_scores_data_scores_range", "raw_scores_data")
        except (SQLAlchemyError, DatabaseError):
            logger.info("⚠️  约束不存在,跳过删除")
    op.drop_table("raw_scores_data")
    if db_dialect != "sqlite":
        try:
            op.drop_index("idx_raw_match_data_jsonb_gin", table_name="raw_match_data")
            op.drop_index("idx_raw_odds_data_jsonb_gin", table_name="raw_odds_data")
        except (SQLAlchemyError, DatabaseError, ConnectionError, TimeoutError) as e:
            logger.info(f"Warning: Could not drop indexes during downgrade: {e}")
    else:
        logger.info("⚠️  SQLite环境:跳过JSONB索引删除")
