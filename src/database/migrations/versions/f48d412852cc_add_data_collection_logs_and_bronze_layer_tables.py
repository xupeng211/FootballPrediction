import sqlalchemy as sa
from sqlalchemy.exc import SQLAlchemyError, DatabaseError
from typing import Union, Sequence
from alembic import op

# mypy: ignore-errors
import logging

logger = logging.getLogger(__name__)
"""add_data_collection_logs_and_bronze_layer_tables


Revision ID: f48d412852cc
Revises: d56c8d0d5aa0
Create Date: 2025-09-10 20:42:25.754318

"""

# revision identifiers, used by Alembic.
revision: str = "f48d412852cc"
down_revision: Union[str, None] = "d56c8d0d5aa0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    创建数据采集日志表和Bronze层原始数据表

    基于 DATA_DESIGN.md 第1.3节和第2.1节设计：
    - data_collection_logs: 采集任务日志记录
    - raw_match_data: Bronze层原始比赛数据
    - raw_odds_data: Bronze层原始赔率数据（分区表）
    """

    # 创建数据采集日志表
    op.create_table(
        "data_collection_logs",
        sa.Column("id", sa.Integer(), nullable=False, comment="主键ID"),
        sa.Column(
            "data_source",
            sa.String(length=100),
            nullable=False,
            comment="数据源标识",
        ),
        sa.Column(
            "collection_type",
            sa.String(length=50),
            nullable=False,
            comment="采集类型(fixtures/odds/scores)",
        ),
        sa.Column("start_time", sa.DateTime(), nullable=False, comment="开始时间"),
        sa.Column("end_time", sa.DateTime(), nullable=True, comment="结束时间"),
        sa.Column(
            "records_collected",
            sa.Integer(),
            nullable=False,
            default=0,
            comment="采集记录数",
        ),
        sa.Column(
            "success_count",
            sa.Integer(),
            nullable=False,
            default=0,
            comment="成功数量",
        ),
        sa.Column(
            "error_count",
            sa.Integer(),
            nullable=False,
            default=0,
            comment="错误数量",
        ),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            comment="状态(success/failed/partial)",
        ),
        sa.Column("error_message", sa.Text(), nullable=True, comment="错误信息"),
        sa.Column("created_at", sa.DateTime(), nullable=False, comment="创建时间"),
        sa.PrimaryKeyConstraint("id"),
        comment="数据采集日志表",
    )

    # 为采集日志表创建索引
    op.create_index(
        "idx_collection_logs_source_type",
        "data_collection_logs",
        ["data_source", "collection_type"],
    )
    op.create_index(
        "idx_collection_logs_start_time", "data_collection_logs", ["start_time"]
    )
    op.create_index("idx_collection_logs_status", "data_collection_logs", ["status"])

    # 创建Bronze层原始比赛数据表
    op.create_table(
        "raw_match_data",
        sa.Column("id", sa.Integer(), nullable=False, comment="主键ID"),
        sa.Column(
            "data_source",
            sa.String(length=100),
            nullable=False,
            comment="数据源标识",
        ),
        sa.Column("raw_data", sa.JSON(), nullable=False, comment="原始JSON数据"),
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
            "external_league_id",
            sa.String(length=100),
            nullable=True,
            comment="外部联赛ID",
        ),
        sa.Column("match_time", sa.DateTime(), nullable=True, comment="比赛时间"),
        sa.Column("created_at", sa.DateTime(), nullable=False, comment="创建时间"),
        sa.PrimaryKeyConstraint("id"),
        comment="Bronze层原始比赛数据表",
    )

    # 为Bronze层比赛数据表创建索引
    op.create_index("idx_raw_match_data_source", "raw_match_data", ["data_source"])
    op.create_index(
        "idx_raw_match_data_collected_at", "raw_match_data", ["collected_at"]
    )
    op.create_index("idx_raw_match_data_processed", "raw_match_data", ["processed"])
    op.create_index(
        "idx_raw_match_data_external_id", "raw_match_data", ["external_match_id"]
    )
    op.create_index("idx_raw_match_data_match_time", "raw_match_data", ["match_time"])

    # 创建Bronze层原始赔率数据表（分区表准备）
    # 注意：PostgreSQL分区表需要特殊语法，这里先创建基础结构
    op.create_table(
        "raw_odds_data",
        sa.Column("id", sa.Integer(), nullable=False, comment="主键ID"),
        sa.Column(
            "data_source",
            sa.String(length=100),
            nullable=False,
            comment="数据源标识",
        ),
        sa.Column(
            "external_match_id",
            sa.String(length=100),
            nullable=True,
            comment="外部比赛ID",
        ),
        sa.Column(
            "bookmaker", sa.String(length=100), nullable=True, comment="博彩公司"
        ),
        sa.Column(
            "market_type", sa.String(length=50), nullable=True, comment="市场类型"
        ),
        sa.Column("raw_data", sa.JSON(), nullable=False, comment="原始JSON数据"),
        sa.Column("collected_at", sa.DateTime(), nullable=False, comment="采集时间"),
        sa.Column(
            "processed",
            sa.Boolean(),
            nullable=False,
            default=False,
            comment="是否已处理",
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False, comment="创建时间"),
        sa.PrimaryKeyConstraint("id"),
        comment="Bronze层原始赔率数据表",
    )

    # 为Bronze层赔率数据表创建索引
    op.create_index("idx_raw_odds_data_source", "raw_odds_data", ["data_source"])
    op.create_index("idx_raw_odds_data_collected_at", "raw_odds_data", ["collected_at"])
    op.create_index("idx_raw_odds_data_processed", "raw_odds_data", ["processed"])
    op.create_index(
        "idx_raw_odds_data_match_bookmaker",
        "raw_odds_data",
        ["external_match_id", "bookmaker"],
    )
    op.create_index("idx_raw_odds_data_market_type", "raw_odds_data", ["market_type"])

    # 这需要使用原生SQL来创建分区表结构

    # 创建Gold层特征表的扩展字段（对现有features表的增强）
    # 只添加在初始schema中不存在的字段
    try:
        # 添加新的特征字段以支持更复杂的ML特征
        # 跳过已在初始schema中存在的字段：recent_5_draws, recent_5_losses,
        # recent_5_goals_against, h2h_draws, h2h_losses
        new_columns = [
            ("home_advantage_score", sa.Numeric(5, 2), "主场优势评分"),
            (
                "form_trend",
                sa.String(length=20),
                "状态趋势(improving/declining/stable)",
            ),
            ("odds_movement", sa.String(length=20), "赔率变动趋势"),
            ("market_sentiment", sa.Numeric(5, 4), "市场情绪指数"),
            ("feature_version", sa.String(length=20), "特征版本"),
            ("last_updated", sa.DateTime(), "最后更新时间"),
        ]

        for column_name, column_type, column_comment in new_columns:
            try:
                op.add_column(
                    "features",
                    sa.Column(
                        column_name, column_type, nullable=True, comment=column_comment
                    ),
                )
            except (SQLAlchemyError, DatabaseError, ConnectionError, TimeoutError) as e:
                # 如果字段已存在，忽略错误
                logger.info(f"Warning: Column {column_name} already exists: {e}")

    except (SQLAlchemyError, DatabaseError, ConnectionError, TimeoutError) as e:
        # 如果features表不存在或字段已存在，忽略错误但记录日志
        logger.info(f"Warning: Could not add columns to features table: {e}")


def downgrade() -> None:
    """
    回滚数据采集日志表和Bronze层表的创建
    """

    # 删除Gold层特征表的扩展字段
    try:
        # 只删除在此迁移中添加的字段

        columns_to_drop = [
            "last_updated",
            "feature_version",
            "market_sentiment",
            "odds_movement",
            "form_trend",
            "home_advantage_score",
        ]

        for column_name in columns_to_drop:
            try:
                op.drop_column("features", column_name)
            except (SQLAlchemyError, DatabaseError, ConnectionError, TimeoutError) as e:
                # 忽略字段不存在的错误但记录日志
                logger.info(f"Warning: Could not drop column {column_name}: {e}")
    except (SQLAlchemyError, DatabaseError, ConnectionError, TimeoutError) as e:
        # 忽略字段不存在的错误但记录日志
        logger.info(f"Warning: Could not drop columns from features table: {e}")

    # 删除Bronze层赔率数据表
    op.drop_index("idx_raw_odds_data_market_type", table_name="raw_odds_data")
    op.drop_index("idx_raw_odds_data_match_bookmaker", table_name="raw_odds_data")
    op.drop_index("idx_raw_odds_data_processed", table_name="raw_odds_data")
    op.drop_index("idx_raw_odds_data_collected_at", table_name="raw_odds_data")
    op.drop_index("idx_raw_odds_data_source", table_name="raw_odds_data")
    op.drop_table("raw_odds_data")

    # 删除Bronze层比赛数据表
    op.drop_index("idx_raw_match_data_match_time", table_name="raw_match_data")
    op.drop_index("idx_raw_match_data_external_id", table_name="raw_match_data")
    op.drop_index("idx_raw_match_data_processed", table_name="raw_match_data")
    op.drop_index("idx_raw_match_data_collected_at", table_name="raw_match_data")
    op.drop_index("idx_raw_match_data_source", table_name="raw_match_data")
    op.drop_table("raw_match_data")

    # 删除数据采集日志表
    op.drop_index("idx_collection_logs_status", table_name="data_collection_logs")
    op.drop_index("idx_collection_logs_start_time", table_name="data_collection_logs")
    op.drop_index("idx_collection_logs_source_type", table_name="data_collection_logs")
    op.drop_table("data_collection_logs")
