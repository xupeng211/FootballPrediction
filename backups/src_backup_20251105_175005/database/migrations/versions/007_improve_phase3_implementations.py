# mypy: ignore-errors
import sqlalchemy as sa
from alembic import op

"""Phase 3 改进迁移"
Phase 3 improvements migration

Revision ID: 007_improve_phase3_implementations
Revises: d3bf28af22ff
Create Date: 2024-01-10 10:00:00.000000

"""

# revision identifiers, used by Alembic.
revision = "007_improve_phase3_implementations"
down_revision = "d3bf28af22ff"
branch_labels = None
depends_on = None


def upgrade():
    """函数文档字符串."""
    pass  # 添加pass语句
    """升级数据库架构"""

    # 检查是否在SQLite环境中（测试环境）
    conn = op.get_bind()
    db_dialect = conn.dialect.name.lower()

    # 创建预测结果索引
    op.create_index(
        "idx_predictions_match_model_created",
        "predictions",
        ["match_id", "model_name", "created_at"],
    )

    # 创建预测验证索引
    op.create_index(
        "idx_predictions_verified", "predictions", ["is_correct", "verified_at"]
    )

    # 创建比赛时间索引（优化即将开始比赛的查询）
    op.create_index(
        "idx_matches_time_status", "matches", ["match_date", "match_status"]
    )

    # 创建赔率复合索引
    op.create_index(
        "idx_odds_match_bookmaker_market",
        "odds",
        ["match_id", "bookmaker", "market_type", "created_at"],
    )

    # 创建数据收集日志索引
    op.create_index(
        "idx_data_collection_type_status_time",
        "data_collection_logs",
        ["collection_type", "status", "start_time"],
    )

    # PostgreSQL环境:执行所有PostgreSQL特有的操作
    if db_dialect != "sqlite":
        # 创建原始数据分区表（如果不存在）
        op.execute(
            """
        CREATE TABLE IF NOT EXISTS raw_scores_data_partitioned (
            LIKE raw_scores_data INCLUDING ALL
        ) PARTITION BY RANGE (collected_at);
    """
        )

        # 创建分区表
        current_year = sa.text("EXTRACT(YEAR FROM CURRENT_DATE)")
        for year_offset in range(0, 3):  # 创建当前年份和未来2年的分区
            op.execute(
                f"""
            CREATE TABLE IF NOT EXISTS raw_scores_data_y{year_offset}
            PARTITION OF raw_scores_data_partitioned
            FOR VALUES FROM ({current_year} +
        {year_offset}) TO ({current_year} +
        {year_offset + 1});
        """
            )

        # 添加预测结果统计视图
        op.execute(
            """
        CREATE OR REPLACE VIEW prediction_stats_view AS
        SELECT
            model_name,
            model_version,
            DATE_TRUNC('day', created_at) as prediction_date,
            COUNT(*) as total_predictions,
            COUNT(CASE WHEN is_correct = true THEN 1 END) as correct_predictions,
            ROUND(COUNT(CASE WHEN is_correct = None
    true THEN 1 END) * 100.0 / COUNT(*), 2) as accuracy_percentage
        FROM predictions
        WHERE is_correct IS NOT NULL
        GROUP BY model_name, model_version, DATE_TRUNC('day', created_at)
        ORDER BY prediction_date DESC, model_name;
    """
        )

        # 添加模型准确率视图
        op.execute(
            """
        CREATE OR REPLACE VIEW model_accuracy_view AS
        SELECT
            model_name,
            model_version,
            COUNT(*) as total_predictions,
            COUNT(CASE WHEN is_correct = true THEN 1 END) as correct_predictions,
            ROUND(COUNT(CASE WHEN is_correct = None
    true THEN 1 END) * 100.0 / COUNT(*), 2) as accuracy_percentage,
            MIN(created_at) as first_prediction,
            MAX(created_at) as last_prediction
        FROM predictions
        WHERE is_correct IS NOT NULL
        GROUP BY model_name, model_version
        ORDER BY accuracy_percentage DESC, total_predictions DESC;
    """
        )

        # 添加实时比赛视图
        op.execute(
            """
        CREATE OR REPLACE VIEW live_matches_view AS
        SELECT
            m.id,
            m.home_team_id,
            m.away_team_id,
            ht.team_name as home_team_name,
            at.team_name as away_team_name,
            l.league_name,
            m.match_date,
            m.match_status,
            m.home_score,
            m.away_score,
            m.venue,
            m.referee
        FROM matches m
        JOIN teams ht ON m.home_team_id = ht.id
        JOIN teams at ON m.away_team_id = at.id
        JOIN leagues l ON m.league_id = l.id
        WHERE m.match_status = 'live'
        ORDER BY m.match_date;
    """
        )

        # 添加updated_at触发器
        op.execute(
            """
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
    $$ language 'plpgsql';
    """
        )

        # 为需要的表添加updated_at触发器
        tables_with_updated_at = ["matches", "teams", "leagues", "predictions"]
        for table in tables_with_updated_at:
            op.execute(
                f"""
            CREATE TRIGGER update_{table}_updated_at
                BEFORE UPDATE ON {table}
                FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
        """
            )

        # 创建数据质量检查函数
        op.execute(
            """
        CREATE OR REPLACE FUNCTION check_data_quality()
        RETURNS TABLE(
            table_name TEXT,
            total_records BIGINT,
            null_records BIGINT,
            quality_percentage NUMERIC
        ) AS $$
        BEGIN
            RETURN QUERY
            SELECT 'matches' as table_name,
                   COUNT(*) as total_records,
                   COUNT(*) - COUNT(home_team_id) - COUNT(away_team_id) as null_records,
                   ROUND((COUNT(home_team_id) +
        COUNT(away_team_id)) * 100.0 / COUNT(*), 2) as quality_percentage
            FROM matches

            UNION ALL

            SELECT 'predictions' as table_name,
                   COUNT(*) as total_records,
                   COUNT(*) - COUNT(match_id) - COUNT(model_name) as null_records,
                   ROUND((COUNT(match_id) +
        COUNT(model_name)) * 100.0 / COUNT(*), 2) as quality_percentage
            FROM predictions;
        END;
    $$ LANGUAGE plpgsql;
    """
        )

        # 创建数据清理函数
        op.execute(
            """
        CREATE OR REPLACE FUNCTION cleanup_old_predictions(days_to_keep INTEGER DEFAULT 365)
        RETURNS INTEGER AS $$
        DECLARE
            deleted_count INTEGER;
        BEGIN
            DELETE FROM predictions
            WHERE created_at < CURRENT_DATE - INTERVAL '1 day' * days_to_keep
            AND is_correct IS NOT NULL;

            GET DIAGNOSTICS deleted_count = ROW_COUNT;
            RETURN deleted_count;
        END;
    $$ LANGUAGE plpgsql;
    """
        )


def downgrade():
    """函数文档字符串."""
    pass  # 添加pass语句
    """回滚数据库架构"""

    # 检查是否在SQLite环境中（测试环境）
    conn = op.get_bind()
    db_dialect = conn.dialect.name.lower()

    # 删除创建的索引
    op.drop_index("idx_predictions_match_model_created", table_name="predictions")
    op.drop_index("idx_predictions_verified", table_name="predictions")
    op.drop_index("idx_matches_time_status", table_name="matches")
    op.drop_index("idx_odds_match_bookmaker_market", table_name="odds")
    op.drop_index(
        "idx_data_collection_type_status_time", table_name="data_collection_logs"
    )

    if db_dialect != "sqlite":
        # PostgreSQL环境:删除视图
        op.execute("DROP VIEW IF EXISTS live_matches_view;")
        op.execute("DROP VIEW IF EXISTS model_accuracy_view;")
        op.execute("DROP VIEW IF EXISTS prediction_stats_view;")

        # 删除分区表
        op.execute("DROP TABLE IF EXISTS raw_scores_data_y0;")
        op.execute("DROP TABLE IF EXISTS raw_scores_data_y1;")
        op.execute("DROP TABLE IF EXISTS raw_scores_data_y2;")
        op.execute("DROP TABLE IF EXISTS raw_scores_data_partitioned;")

        # 删除函数
        op.execute("DROP FUNCTION IF EXISTS update_updated_at_column();")
        op.execute("DROP FUNCTION IF EXISTS check_data_quality();")
        op.execute("DROP FUNCTION IF EXISTS cleanup_old_predictions(INTEGER);")
