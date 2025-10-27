# mypy: ignore-errors
import logging
from typing import Sequence, Union

from sqlalchemy.exc import DatabaseError, SQLAlchemyError

logger = logging.getLogger(__name__)
from alembic import context, op
from sqlalchemy import text

"""add_performance_critical_indexes

添加性能关键索引，优化高频查询性能。

基于性能分析结果，添加以下关键索引：
- 预测表时间索引：优化创建时间查询
- 比赛表状态时间复合索引：优化状态和时间查询
- 特征表匹配时间索引：优化特征查询
- 数据质量监控索引：优化监控查询
- 审计日志索引：优化审计查询

Revision ID: d3bf28af22ff
Revises: 006_missing_indexes
Create Date: 2025-09-29 23:08:00.000000

"""

# revision identifiers, used by Alembic.
revision: str = "d3bf28af22ff"
down_revision: Union[str, None] = "006_missing_indexes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _create_predictions_indexes(conn) -> None:
    """创建预测表索引"""
    logger.info("1. 创建预测表性能索引...")

    # 创建时间降序索引（用于最近预测查询）
    try:
        conn.execute(
            text(
                """
            CREATE INDEX IF NOT EXISTS idx_predictions_created_at_desc
            ON predictions (created_at DESC);
            """
            )
        )
        logger.info("   ✓ idx_predictions_created_at_desc 创建成功")
    except (SQLAlchemyError, DatabaseError, ConnectionError, TimeoutError) as e:
        logger.info(f"   ✗ idx_predictions_created_at_desc 创建失败: {e}")

    # 比赛ID和创建时间复合索引
    try:
        conn.execute(
            text(
                """
            CREATE INDEX IF NOT EXISTS idx_predictions_match_created
            ON predictions (match_id, created_at DESC);
            """
            )
        )
        logger.info("   ✓ idx_predictions_match_created 创建成功")
    except (SQLAlchemyError, DatabaseError, ConnectionError, TimeoutError) as e:
        logger.info(f"   ✗ idx_predictions_match_created 创建失败: {e}")


def upgrade() -> None:
    """添加性能关键索引"""

    # 检查是否在离线模式
    if context.is_offline_mode():
        logger.info("⚠️  离线模式：跳过性能索引创建")
        op.execute("-- offline mode: skipped performance indexes creation")
        return

    # 获取数据库连接以执行原生SQL
    conn = op.get_bind()

    logger.info("开始添加性能关键索引...")

    # ========================================
    # 1. 预测表索引优化
    # ========================================
    _create_predictions_indexes(conn)

    # ========================================
    # 2. 比赛表复合索引优化
    # ========================================
    _create_matches_indexes(conn)


def _create_matches_indexes(conn) -> None:
    """创建比赛表索引"""
    logger.info("2. 创建比赛表复合索引...")

    # 状态和时间复合索引（优化查询即将开始的比赛）
    try:
        conn.execute(
            text(
                """
            CREATE INDEX IF NOT EXISTS idx_matches_status_time
            ON matches (match_status, match_time DESC);
            """
            )
        )
        logger.info("   ✓ idx_matches_status_time 创建成功")
    except (SQLAlchemyError, DatabaseError, ConnectionError, TimeoutError) as e:
        logger.info(f"   ✗ idx_matches_status_time 创建失败: {e}")

    # 联赛和时间复合索引（优化联赛赛程查询）
    try:
        conn.execute(
            text(
                """
            CREATE INDEX IF NOT EXISTS idx_matches_league_time
            ON matches (league_id, match_time DESC);
            """
            )
        )
        logger.info("   ✓ idx_matches_league_time 创建成功")
    except (SQLAlchemyError, DatabaseError, ConnectionError, TimeoutError) as e:
        logger.info(f"   ✗ idx_matches_league_time 创建失败: {e}")

    # 主队和时间复合索引
    try:
        conn.execute(
            text(
                """
            CREATE INDEX IF NOT EXISTS idx_matches_home_time
            ON matches (home_team_id, match_time DESC);
            """
            )
        )
        logger.info("   ✓ idx_matches_home_time 创建成功")
    except (SQLAlchemyError, DatabaseError, ConnectionError, TimeoutError) as e:
        logger.info(f"   ✗ idx_matches_home_time 创建失败: {e}")


def _create_features_indexes(conn) -> None:
    """创建特征表索引"""
    logger.info("3. 创建特征表性能索引...")

    # 匹配ID和创建时间复合索引
    try:
        conn.execute(
            text(
                """
            CREATE INDEX IF NOT EXISTS idx_features_match_created
            ON features (match_id, created_at DESC);
            """
            )
        )
        logger.info("   ✓ idx_features_match_created 创建成功")
    except (SQLAlchemyError, DatabaseError, ConnectionError, TimeoutError) as e:
        logger.info(f"   ✗ idx_features_match_created 创建失败: {e}")

    # 特征类型索引
    try:
        conn.execute(
            text(
                """
            CREATE INDEX IF NOT EXISTS idx_features_type
            ON features (feature_type);
            """
            )
        )
        logger.info("   ✓ idx_features_type 创建成功")
    except (SQLAlchemyError, DatabaseError, ConnectionError, TimeoutError) as e:
        logger.info(f"   ✗ idx_features_type 创建失败: {e}")


def _create_data_quality_indexes(conn) -> None:
    """创建数据质量监控索引"""
    logger.info("4. 创建数据质量监控索引...")

    # 数据质量日志时间索引
    try:
        conn.execute(
            text(
                """
            CREATE INDEX IF NOT EXISTS idx_data_quality_created_at
            ON data_quality_logs (created_at DESC);
            """
            )
        )
        logger.info("   ✓ idx_data_quality_created_at 创建成功")
    except (SQLAlchemyError, DatabaseError, ConnectionError, TimeoutError) as e:
        logger.info(f"   ✗ idx_data_quality_created_at 创建失败: {e}")

    # 数据质量状态索引
    try:
        conn.execute(
            text(
                """
            CREATE INDEX IF NOT EXISTS idx_data_quality_status
            ON data_quality_logs (validation_status);
            """
            )
        )
        logger.info("   ✓ idx_data_quality_status 创建成功")
    except (SQLAlchemyError, DatabaseError, ConnectionError, TimeoutError) as e:
        logger.info(f"   ✗ idx_data_quality_status 创建失败: {e}")


def _create_audit_logs_indexes(conn) -> None:
    """创建审计日志索引"""
    logger.info("5. 创建审计日志索引...")

    # 审计日志时间索引
    try:
        conn.execute(
            text(
                """
            CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at
            ON audit_logs (created_at DESC);
            """
            )
        )
        logger.info("   ✓ idx_audit_logs_created_at 创建成功")
    except (SQLAlchemyError, DatabaseError, ConnectionError, TimeoutError) as e:
        logger.info(f"   ✗ idx_audit_logs_created_at 创建失败: {e}")

    # 审计日志用户索引
    try:
        conn.execute(
            text(
                """
            CREATE INDEX IF NOT EXISTS idx_audit_logs_user
            ON audit_logs (user_id);
            """
            )
        )
        logger.info("   ✓ idx_audit_logs_user 创建成功")
    except (SQLAlchemyError, DatabaseError, ConnectionError, TimeoutError) as e:
        logger.info(f"   ✗ idx_audit_logs_user 创建失败: {e}")

    # ========================================
    # 3. 特征表索引优化
    # ========================================
    _create_features_indexes(conn)

    # ========================================
    # 4. 数据质量监控索引
    # ========================================
    _create_data_quality_indexes(conn)

    # ========================================
    # 5. 审计日志索引
    # ========================================
    _create_audit_logs_indexes(conn)

    # 审计日志操作类型索引
    try:
        conn.execute(
            text(
                """
            CREATE INDEX IF NOT EXISTS idx_audit_logs_action
            ON audit_logs (action_type);
            """
            )
        )
        logger.info("   ✓ idx_audit_logs_action 创建成功")
    except (SQLAlchemyError, DatabaseError, ConnectionError, TimeoutError) as e:
        logger.info(f"   ✗ idx_audit_logs_action 创建失败: {e}")

    # ========================================
    # 6. 数据采集日志索引
    # ========================================

    logger.info("6. 创建数据采集日志索引...")

    # 数据采集日志时间索引
    try:
        conn.execute(
            text(
                """
            CREATE INDEX IF NOT EXISTS idx_collection_logs_created_at
            ON data_collection_logs (created_at DESC);
            """
            )
        )
        logger.info("   ✓ idx_collection_logs_created_at 创建成功")
    except (SQLAlchemyError, DatabaseError, ConnectionError, TimeoutError) as e:
        logger.info(f"   ✗ idx_collection_logs_created_at 创建失败: {e}")

    # 数据采集日志源和状态复合索引
    try:
        conn.execute(
            text(
                """
            CREATE INDEX IF NOT EXISTS idx_collection_logs_source_status
            ON data_collection_logs (data_source, collection_status);
            """
            )
        )
        logger.info("   ✓ idx_collection_logs_source_status 创建成功")
    except (SQLAlchemyError, DatabaseError, ConnectionError, TimeoutError) as e:
        logger.info(f"   ✗ idx_collection_logs_source_status 创建失败: {e}")

    # ========================================
    # 7. 错误日志索引优化
    # ========================================

    logger.info("7. 创建错误日志优化索引...")

    # 错误日志任务名称索引
    try:
        conn.execute(
            text(
                """
            CREATE INDEX IF NOT EXISTS idx_error_logs_task_name
            ON error_logs (task_name);
            """
            )
        )
        logger.info("   ✓ idx_error_logs_task_name 创建成功")
    except (SQLAlchemyError, DatabaseError, ConnectionError, TimeoutError) as e:
        logger.info(f"   ✗ idx_error_logs_task_name 创建失败: {e}")

    # 错误日志创建时间索引
    try:
        conn.execute(
            text(
                """
            CREATE INDEX IF NOT EXISTS idx_error_logs_created_at
            ON error_logs (created_at DESC);
            """
            )
        )
        logger.info("   ✓ idx_error_logs_created_at 创建成功")
    except (SQLAlchemyError, DatabaseError, ConnectionError, TimeoutError) as e:
        logger.info(f"   ✗ idx_error_logs_created_at 创建失败: {e}")

    # 错误日志任务状态复合索引
    try:
        conn.execute(
            text(
                """
            CREATE INDEX IF NOT EXISTS idx_error_logs_task_status
            ON error_logs (task_name, error_message IS NOT NULL);
            """
            )
        )
        logger.info("   ✓ idx_error_logs_task_status 创建成功")
    except (SQLAlchemyError, DatabaseError, ConnectionError, TimeoutError) as e:
        logger.info(f"   ✗ idx_error_logs_task_status 创建失败: {e}")

    logger.info("✅ 性能关键索引创建完成！")


def downgrade() -> None:
    """删除性能关键索引"""

    # 检查是否在离线模式
    if context.is_offline_mode():
        logger.info("⚠️  离线模式：跳过索引删除")

        op.execute("-- offline mode: skipped performance indexes removal")
        return

    # 获取数据库连接以执行原生SQL
    conn = op.get_bind()

    logger.info("开始删除性能关键索引...")

    # 定义要删除的索引列表
    indexes_to_drop = [
        "idx_predictions_created_at_desc",
        "idx_predictions_match_created",
        "idx_matches_status_time",
        "idx_matches_league_time",
        "idx_matches_home_time",
        "idx_features_match_created",
        "idx_features_type",
        "idx_data_quality_created_at",
        "idx_data_quality_status",
        "idx_audit_logs_created_at",
        "idx_audit_logs_user",
        "idx_audit_logs_action",
        "idx_collection_logs_created_at",
        "idx_collection_logs_source_status",
        "idx_error_logs_task_name",
        "idx_error_logs_created_at",
        "idx_error_logs_task_status",
    ]

    for index_name in indexes_to_drop:
        try:
            conn.execute(text(f"DROP INDEX IF EXISTS {index_name};"))
            logger.info(f"   ✓ {index_name} 删除成功")
        except (SQLAlchemyError, DatabaseError, ConnectionError, TimeoutError) as e:
            logger.info(f"   ✗ {index_name} 删除失败: {e}")

    logger.info("✅ 性能关键索引删除完成！")
