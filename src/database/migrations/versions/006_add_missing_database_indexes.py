# mypy: ignore-errors
import logging
from typing import Sequence, Union

from sqlalchemy.exc import DatabaseError, SQLAlchemyError

from alembic import context, op
from sqlalchemy import text


# revision identifiers, used by Alembic.


# 检查是否在离线模式
# 在离线模式下执行注释,确保 SQL 生成正常

# 获取数据库连接以执行原生SQL


# ========================================
# 1. idx_recent_matches - 最近比赛查询优化
# ========================================


# ========================================
# 2. idx_team_matches - 球队对战查询优化
# ========================================


# ========================================
# 3. idx_predictions_lookup - 预测数据查询优化
# ========================================


# ========================================
# 4. idx_odds_match_collected - 赔率时间序列查询优化
# ========================================


# ========================================
# 5. 额外的性能优化索引
# ========================================


# matches 表的复合状态索引

# teams 表查询优化（如果表存在）

# odds 表的博彩商索引

# features 表的时间索引（如果表存在）

# ========================================
# 6. 验证索引创建结果
# ========================================


# 检查是否在离线模式

# 在离线模式下执行注释,确保 SQL 生成正常

# 获取数据库连接


# 删除创建的索引


logger = logging.getLogger(__name__)
"""add_missing_database_indexes
补充缺失的数据库索引,提高查询性能.
基于数据架构优化工程师要求,添加以下缺失的索引:
- idx_recent_matches: 支持按日期降序和联赛查询最近比赛
- idx_team_matches: 支持主客队和日期的组合查询
- idx_predictions_lookup: 支持预测数据的快速查找
- idx_odds_match_collected: 优化赔率数据的时间序列查询
Revision ID: 006_missing_indexes
Revises: d6d814cc1078
Create Date: 2025-09-12 01:35:00.000000
"""
revision: str = "006_missing_indexes"
down_revision: Union[str, None] = "d6d814cc1078"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """添加缺失的数据库索引"""
    if context.is_offline_mode():
        logger.info("⚠️  离线模式:跳过索引创建")
        op.execute("-- offline mode: skipped database indexes creation")
        return
    conn = op.get_bind()
    logger.info("开始添加缺失的数据库索引...")
    logger.info("1. 创建 idx_recent_matches 索引...")
    try:
        conn.execute(
            text(
                """
            CREATE INDEX IF NOT EXISTS idx_recent_matches
            ON matches (match_time DESC, league_id)
            WHERE match_status IN ('finished', 'in_progress');
        """
            )
        )
        logger.info("   ✅ idx_recent_matches 索引创建成功")
    except (SQLAlchemyError, DatabaseError, ConnectionError, TimeoutError) as e:
        logger.info(f"   ❌ idx_recent_matches 索引创建失败: {e}")
    logger.info("2. 创建 idx_team_matches 索引...")
    try:
        conn.execute(
            text(
                """
            CREATE INDEX IF NOT EXISTS idx_team_matches
            ON matches (home_team_id, away_team_id, match_time DESC);
        """
            )
        )
        logger.info("   ✅ idx_team_matches 索引创建成功")
    except (SQLAlchemyError, DatabaseError, ConnectionError, TimeoutError) as e:
        logger.info(f"   ❌ idx_team_matches 索引创建失败: {e}")
    logger.info("3. 创建 idx_predictions_lookup 索引...")
    try:
        conn.execute(
            text(
                """
            CREATE INDEX IF NOT EXISTS idx_predictions_lookup
            ON predictions (match_id, model_name, created_at DESC);
        """
            )
        )
        logger.info("   ✅ idx_predictions_lookup 索引创建成功")
    except (SQLAlchemyError, DatabaseError, ConnectionError, TimeoutError) as e:
        logger.info(f"   ❌ idx_predictions_lookup 索引创建失败: {e}")
    logger.info("4. 创建 idx_odds_match_collected 索引...")
    try:
        conn.execute(
            text(
                """
            CREATE INDEX IF NOT EXISTS idx_odds_match_collected
            ON odds (match_id, collected_at DESC);
        """
            )
        )
        logger.info("   ✅ idx_odds_match_collected 索引创建成功")
    except (SQLAlchemyError, DatabaseError, ConnectionError, TimeoutError) as e:
        logger.info(f"   ❌ idx_odds_match_collected 索引创建失败: {e}")
    logger.info("5. 创建额外的性能优化索引...")
    try:
        conn.execute(
            text(
                """
            CREATE INDEX IF NOT EXISTS idx_matches_status_time
            ON matches (match_status, match_time DESC)
            WHERE match_status IN ('scheduled', 'in_progress', 'finished');
        """
            )
        )
        logger.info("   ✅ idx_matches_status_time 索引创建成功")
    except (SQLAlchemyError, DatabaseError, ConnectionError, TimeoutError) as e:
        logger.info(f"   ❌ idx_matches_status_time 索引创建失败: {e}")
    try:
        conn.execute(
            text(
                """
            CREATE INDEX IF NOT EXISTS idx_teams_league
            ON teams (league_id, team_name);
        """
            )
        )
        logger.info("   ✅ idx_teams_league 索引创建成功")
    except (SQLAlchemyError, DatabaseError, ConnectionError, TimeoutError) as e:
        logger.info(f"   ❌ idx_teams_league 索引创建失败 (可能表不存在): {e}")
    try:
        conn.execute(
            text(
                """
            CREATE INDEX IF NOT EXISTS idx_odds_bookmaker_time
            ON odds (bookmaker, collected_at DESC);
        """
            )
        )
        logger.info("   ✅ idx_odds_bookmaker_time 索引创建成功")
    except (SQLAlchemyError, DatabaseError, ConnectionError, TimeoutError) as e:
        logger.info(f"   ❌ idx_odds_bookmaker_time 索引创建失败: {e}")
    try:
        conn.execute(
            text(
                """
            CREATE INDEX IF NOT EXISTS idx_features_created_at
            ON features (created_at DESC);
        """
            )
        )
        logger.info("   ✅ idx_features_created_at 索引创建成功")
    except (SQLAlchemyError, DatabaseError, ConnectionError, TimeoutError) as e:
        logger.info(f"   ❌ idx_features_created_at 索引创建失败 (可能表不存在): {e}")
    logger.info("6. 验证索引创建结果...")
    try:
        result = conn.execute(
            text(
                """
            SELECT
                schemaname,
                tablename,
                indexname,
                indexdef
            FROM pg_indexes
            WHERE indexname IN (
                'idx_recent_matches',
                'idx_team_matches',
                'idx_predictions_lookup',
                'idx_odds_match_collected',
                'idx_matches_status_time',
                'idx_teams_league',
                'idx_odds_bookmaker_time',
                'idx_features_created_at'
            )
            ORDER BY tablename, indexname;
        """
            )
        )
        logger.info("   创建的索引列表:")
        for row in result:
            logger.info(f"   - {row[2]} on {row[1]}")
    except (SQLAlchemyError, DatabaseError, ConnectionError, TimeoutError) as e:
        logger.info(f"   ❌ 验证索引失败: {e}")
    logger.info("✅ 数据库索引优化迁移完成！")


def downgrade() -> None:
    """回滚索引创建（删除添加的索引）"""
    if context.is_offline_mode():
        logger.info("⚠️  离线模式:跳过索引回滚")
        op.execute("-- offline mode: skipped database indexes rollback")
        return
    conn = op.get_bind()
    logger.info("开始回滚数据库索引...")
    indexes_to_drop = [
        "idx_recent_matches",
        "idx_team_matches",
        "idx_predictions_lookup",
        "idx_odds_match_collected",
        "idx_matches_status_time",
        "idx_teams_league",
        "idx_odds_bookmaker_time",
        "idx_features_created_at",
    ]
    for index_name in indexes_to_drop:
        try:
            conn.execute(text(f"DROP INDEX IF EXISTS {index_name};"))
            logger.info(f"   ✅ 删除索引: {index_name}")
        except (SQLAlchemyError, DatabaseError, ConnectionError, TimeoutError) as e:
            logger.info(f"   ❌ 删除索引失败 {index_name}: {e}")
    logger.info("✅ 数据库索引回滚完成！")
