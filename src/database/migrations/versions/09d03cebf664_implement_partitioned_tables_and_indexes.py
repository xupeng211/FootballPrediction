import logging
from collections.abc import Sequence

# mypy: ignore-errors
from alembic import context, op
from sqlalchemy import text
from sqlalchemy.exc import DatabaseError, SQLAlchemyError

# revision identifiers, used by Alembic.


# 检查是否在离线模式
# 在离线模式下执行注释，确保 SQL 生成正常


# 1. 创建分区管理函数


# 2. 创建预测表月度分区管理函数


# 3. 为现有表添加分区（需要先备份数据）
# 注意:在生产环境中，这需要谨慎操作
# 检查表是否已分区

# 在实际部署中，需要先创建分区表,再迁移数据


# 4. 创建年度分区（示例）

# 5. 创建月度分区（最近12个月）

# 6. 实现PostgreSQL高级索引


# JSONB字段的GIN索引（如果尚未存在）
# 复合索引优化查询
# 部分索引（仅索引活跃数据）


# 基础查询优化索引
# 特征工程查询优化
# Bronze层数据查询优化


# 检查索引是否存在


# 构建索引创建语句


# 检查是否在离线模式
# 在离线模式下执行注释,确保 SQL 生成正常


# 删除分区管理函数

# 删除创建的索引


logger = logging.getLogger(__name__)
"""implement_partitioned_tables_and_indexes"
实现分区表和索引优化策略
基于 architecture.md 第3.4节和第3.3节的设计要求,实现:
1. 比赛表按年份分区
2. 预测表按月分区
3. 补充缺失的查询优化索引
4. 添加特征工程优化索引
Revision ID: 09d03cebf664
Revises: c1d8ae5075f0
Create Date: 2025-09-12 12:48:23.849021
"""
revision: str = "09d03cebf664"
down_revision: str | None = "c1d8ae5075f0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def is_sqlite():
    """函数文档字符串"""
    pass  # 添加pass语句
    """检测当前是否为SQLite数据库"""
    if context.is_offline_mode():
        return False  # 离线模式下假设不是SQLite
    bind = op.get_bind()
    return bind.dialect.name == "sqlite"


def is_postgresql():
    """函数文档字符串"""
    pass  # 添加pass语句
    """检测当前是否为PostgreSQL数据库"""
    if context.is_offline_mode():
        return True  # 离线模式下假设是PostgreSQL
    bind = op.get_bind()
    return bind.dialect.name == "postgresql"


def upgrade() -> None:
    """
    升级数据库:实现分区表和索引优化
    SQLite不支持分区表,但会创建相应的索引来优化查询性能。
    PostgreSQL将实现完整的分区表策略和高级索引.
    """
    if context.is_offline_mode():
        logger.info("⚠️  离线模式:跳过分区表实现")
        op.execute("-- offline mode: skipped partitioned tables implementation")
        op.execute("-- offline mode: skipped advanced indexes creation")
        return None
    bind = op.get_bind()
    logger.info(f"当前数据库类型: {bind.dialect.name}")
    if is_postgresql():
        logger.info("PostgreSQL环境:实现分区表和高级索引...")
        _implement_postgresql_partitioning_and_indexes()
    elif is_sqlite():
        logger.info("SQLite环境:实现优化索引（不支持分区表）...")
        _implement_sqlite_optimized_indexes()
    else:
        logger.info(f"其他数据库类型 {bind.dialect.name}:实现基础索引...")
        _implement_basic_indexes()
    logger.info("分区表和索引优化实施完成")


def _implement_postgresql_partitioning_and_indexes():
    """函数文档字符串"""
    pass  # 添加pass语句
    """PostgreSQL环境下实现分区表和高级索引"""
    op.execute(
        text(
            """
        CREATE OR REPLACE FUNCTION create_match_partition(year_val INTEGER)
        RETURNS void AS $$
        DECLARE
            partition_name TEXT;
            start_date DATE;
            end_date DATE;
        BEGIN
            partition_name := 'matches_y' || year_val::TEXT;
            start_date := (year_val::TEXT || '-01-01')::DATE;
            end_date := ((year_val + 1)::TEXT || '-01-01')::DATE;
            -- 检查分区是否已存在
            IF NOT EXISTS (
                SELECT 1 FROM pg_class WHERE relname = partition_name
            ) THEN
                EXECUTE format(
                    'CREATE TABLE %I PARTITION OF matches FOR VALUES FROM (%L) TO (%L)',
                    partition_name, start_date, end_date
                );
                RAISE NOTICE '已创建比赛分区: %', partition_name;
            END IF;
        END;
        $$ LANGUAGE plpgsql;
    """
        )
    )
    op.execute(
        text(
            """
        CREATE OR REPLACE FUNCTION create_prediction_partition(year_val INTEGER,
    month_val INTEGER)
        RETURNS void AS $$
        DECLARE
            partition_name TEXT;
            range_start INTEGER;
            range_end INTEGER;
        BEGIN
            partition_name : =
    'predictions_y' || year_val::TEXT || 'm' || lpad(month_val::TEXT, 2, '0');
            range_start := year_val * 100 + month_val;
            range_end := CASE
                WHEN month_val = 12 THEN (year_val + 1) * 100 + 1
                ELSE year_val * 100 + month_val + 1
            END;
            IF NOT EXISTS (
                SELECT 1 FROM pg_class WHERE relname = partition_name
            ) THEN
                EXECUTE format(
                    'CREATE TABLE %I PARTITION OF predictions FOR VALUES FROM (%L) TO (%L)',
    
                    partition_name, range_start, range_end
                );
                RAISE NOTICE '已创建预测分区: %', partition_name;
            END IF;
        END;
        $$ LANGUAGE plpgsql;
    """
        )
    )
    try:
        result = (
            op.get_bind()
            .execute(
                text(
                    """
            SELECT COUNT(*) FROM pg_partitioned_table
            WHERE partrelid = 'matches'::regclass
        """
                )
            )
            .scalar()
        )
        if result == 0:
            logger.info("  提醒:matches表尚未分区,建议在维护窗口期间手动执行分区操作")
    except (SQLAlchemyError, DatabaseError, ConnectionError, TimeoutError) as e:
        logger.info(f"  分区检查失败: {e}")
    current_year = 2025
    for year in range(2020, current_year + 2):
        try:
            op.execute(text(f"SELECT create_match_partition({year})"))
        except (SQLAlchemyError, DatabaseError, ConnectionError, TimeoutError) as e:
            logger.info(f"  创建分区 {year} 失败: {e}")
    for year in [2024, 2025]:
        for month in range(1, 13):
            if year == 2024 and month < 9:  # 跳过太早的月份
                continue
            try:
                op.execute(text(f"SELECT create_prediction_partition({year}, {month})"))
            except (SQLAlchemyError, DatabaseError, ConnectionError, TimeoutError) as e:
                logger.info(f"  创建预测分区 {year}-{month:02d} 失败: {e}")
    _create_postgresql_advanced_indexes()


def _create_postgresql_advanced_indexes():
    """函数文档字符串"""
    pass  # 添加pass语句
    """创建PostgreSQL高级索引"""
    advanced_indexes = [
        {
            "name": "idx_raw_match_data_jsonb_gin",
            "table": "raw_match_data",
            "columns": ["raw_data"],
            "method": "gin",
            "condition": None,
        },
        {
            "name": "idx_predictions_feature_importance_gin",
            "table": "predictions",
            "columns": ["feature_importance"],
            "method": "gin",
            "condition": "feature_importance IS NOT NULL",
        },
        {
            "name": "idx_matches_league_date_teams",
            "table": "matches",
            "columns": ["league_id", "match_date", "home_team_id", "away_team_id"],
            "method": "btree",
            "condition": None,
        },
        {
            "name": "idx_odds_match_bookmaker_collected",
            "table": "odds",
            "columns": ["match_id", "bookmaker", "collected_at DESC"],
            "method": "btree",
            "condition": None,
        },
        {
            "name": "idx_predictions_model_confidence",
            "table": "predictions",
            "columns": ["model_name", "confidence_score DESC", "predicted_at DESC"],
            "method": "btree",
            "condition": "confidence_score IS NOT NULL",
        },
        {
            "name": "idx_matches_recent_finished",
            "table": "matches",
            "columns": ["match_date DESC", "league_id"],
            "method": "btree",
            "condition": "match_status = 'finished' AND match_date >= CURRENT_DATE - INTERVAL '2 years'",
        },
    ]
    for idx in advanced_indexes:
        try:
            _create_index_if_not_exists(**idx)
        except (SQLAlchemyError, DatabaseError, ConnectionError, TimeoutError) as e:
            logger.info(f"  创建索引 {idx['name']} 失败: {e}")


def _implement_sqlite_optimized_indexes():
    """函数文档字符串"""
    pass  # 添加pass语句
    """SQLite环境下实现优化索引"""
    sqlite_indexes = [
        {
            "name": "idx_matches_date_league",
            "table": "matches",
            "columns": ["match_date DESC", "league_id"],
        },
        {
            "name": "idx_matches_teams_date",
            "table": "matches",
            "columns": ["home_team_id", "away_team_id", "match_date"],
        },
        {
            "name": "idx_predictions_match_model_date",
            "table": "predictions",
            "columns": ["match_id", "model_name", "predicted_at DESC"],
        },
        {
            "name": "idx_odds_match_bookmaker_time",
            "table": "odds",
            "columns": ["match_id", "bookmaker", "collected_at"],
        },
        {
            "name": "idx_features_team_match",
            "table": "features",
            "columns": ["team_id", "match_id"],
        },
        {
            "name": "idx_raw_match_external_id",
            "table": "raw_match_data",
            "columns": ["external_match_id", "data_source"],
        },
        {
            "name": "idx_raw_odds_external_bookmaker",
            "table": "raw_odds_data",
            "columns": ["external_match_id", "bookmaker"],
        },
    ]
    for idx in sqlite_indexes:
        try:
            _create_simple_index(**idx)
        except (SQLAlchemyError, DatabaseError, ConnectionError, TimeoutError) as e:
            logger.info(f"  创建SQLite索引 {idx['name']} 失败: {e}")


def _implement_basic_indexes():
    """函数文档字符串"""
    pass  # 添加pass语句
    """实现基础索引（通用数据库）"""
    basic_indexes = [
        {
            "name": "idx_matches_basic_lookup",
            "table": "matches",
            "columns": ["match_date", "league_id"],
        },
        {
            "name": "idx_predictions_basic_lookup",
            "table": "predictions",
            "columns": ["match_id", "predicted_at"],
        },
    ]
    for idx in basic_indexes:
        try:
            _create_simple_index(**idx)
        except (SQLAlchemyError, DatabaseError, ConnectionError, TimeoutError) as e:
            logger.info(f"  创建基础索引 {idx['name']} 失败: {e}")


def _create_index_if_not_exists(name, table, columns, method="btree", condition=None):
    """函数文档字符串"""
    pass  # 添加pass语句
    """创建PostgreSQL索引（如果不存在）"""
    exists = (
        op.get_bind()
        .execute(
            text(
                """
        SELECT COUNT(*) FROM pg_indexes
        WHERE indexname = :index_name
    """
            ),
            {"index_name": name},
        )
        .scalar()
    )
    if exists > 0:
        logger.info(f"  索引 {name} 已存在,跳过创建")
        return None
    columns_str = ", ".join(columns)
    if method == "gin":
        index_sql = f"CREATE INDEX {name} ON {table} USING gin ({columns_str})"
    else:
        index_sql = f"CREATE INDEX {name} ON {table} ({columns_str})"
    if condition:
        index_sql += f" WHERE {condition}"
    op.execute(text(index_sql))
    logger.info(f"  ✓ 已创建索引: {name}")


def _create_simple_index(name, table, columns):
    """函数文档字符串"""
    pass  # 添加pass语句
    """创建简单索引"""
    try:
        op.create_index(name, table, columns)
        logger.info(f"  ✓ 已创建索引: {name}")
    except (SQLAlchemyError, DatabaseError, ConnectionError, TimeoutError) as e:
        if "already exists" in str(e).lower():
            logger.info(f"  索引 {name} 已存在,跳过创建")
        else:
            raise


def downgrade() -> None:
    """
    降级操作:移除分区表和索引
    注意:分区表的降级需要谨慎操作,可能需要数据迁移
    """
    if context.is_offline_mode():
        logger.info("⚠️  离线模式:跳过分区表降级")
        op.execute("-- offline mode: skipped partitioned tables downgrade")
        op.execute("-- offline mode: skipped advanced indexes removal")
        return None
    logger.info("开始降级分区表和索引优化...")
    if is_postgresql():
        _downgrade_postgresql_features()
    elif is_sqlite():
        _downgrade_sqlite_features()
    logger.info("分区表和索引降级完成")


def _downgrade_postgresql_features():
    """函数文档字符串"""
    pass  # 添加pass语句
    """降级PostgreSQL特性"""
    op.execute(text("DROP FUNCTION IF EXISTS create_match_partition(INTEGER)"))
    op.execute(
        text("DROP FUNCTION IF EXISTS create_prediction_partition(INTEGER, INTEGER)")
    )
    indexes_to_drop = [
        "idx_raw_match_data_jsonb_gin",
        "idx_predictions_feature_importance_gin",
        "idx_matches_league_date_teams",
        "idx_odds_match_bookmaker_collected",
        "idx_predictions_model_confidence",
        "idx_matches_recent_finished",
    ]
    for idx_name in indexes_to_drop:
        try:
            op.execute(text(f"DROP INDEX IF EXISTS {idx_name}"))
            logger.info(f"  ✓ 已删除索引: {idx_name}")
        except (SQLAlchemyError, DatabaseError, ConnectionError, TimeoutError) as e:
            logger.info(f"  删除索引 {idx_name} 失败: {e}")


def _downgrade_sqlite_features():
    """函数文档字符串"""
    pass  # 添加pass语句
    """降级SQLite特性"""
    indexes_to_drop = [
        "idx_matches_date_league",
        "idx_matches_teams_date",
        "idx_predictions_match_model_date",
        "idx_odds_match_bookmaker_time",
        "idx_features_team_match",
        "idx_raw_match_external_id",
        "idx_raw_odds_external_bookmaker",
    ]
    for idx_name in indexes_to_drop:
        try:
            op.drop_index(idx_name)
            logger.info(f"  ✓ 已删除索引: {idx_name}")
        except (SQLAlchemyError, DatabaseError, ConnectionError, TimeoutError) as e:
            logger.info(f"  删除索引 {idx_name} 失败: {e}")
