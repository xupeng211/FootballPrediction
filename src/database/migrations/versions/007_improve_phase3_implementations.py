from typing import Any, Dict, List, Optional, Union
# mypy: ignore-errors
import sqlalchemy as sa
from sqlalchemy.exc import SQLAlchemyError, DatabaseError

"""Phase 3 改进迁移
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
    """升级数据库架构"""

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
        "idx_matches_time_status", "matches", ["match_time", "match_status"]
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
        ["collection_type", "status", "collected_at"],
    )

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
            FOR VALUES FROM ({current_year} + {year_offset}) TO ({current_year} + {year_offset + 1});
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
            COUNT(CASE WHEN predicted_result = 'home' THEN 1 END) as home_predictions,
            COUNT(CASE WHEN predicted_result = 'draw' THEN 1 END) as draw_predictions,
            COUNT(CASE WHEN predicted_result = 'away' THEN 1 END) as away_predictions,
            AVG(confidence_score) as avg_confidence,
            MAX(confidence_score) as max_confidence,
            MIN(confidence_score) as min_confidence
        FROM predictions
        GROUP BY model_name, model_version, DATE_TRUNC('day', created_at)
        ORDER BY prediction_date DESC;
    """
    )

    # 添加模型准确率视图
    op.execute(
        """
        CREATE OR REPLACE VIEW model_accuracy_view AS
        SELECT
            model_name,
            model_version,
            COUNT(*) as total_verified,
            SUM(CASE WHEN is_correct = true THEN 1 ELSE 0 END) as correct_predictions,
            SUM(CASE WHEN is_correct = false THEN 1 ELSE 0 END) as incorrect_predictions,
            CASE
                WHEN COUNT(*) > 0 THEN
                    SUM(CASE WHEN is_correct = true THEN 1 ELSE 0 END) * 100.0 / COUNT(*)
                ELSE 0
            END as accuracy_percentage
        FROM predictions
        WHERE is_correct IS NOT NULL
        GROUP BY model_name, model_version
        ORDER BY accuracy_percentage DESC;
    """
    )

    # 添加实时比赛统计视图
    op.execute(
        """
        CREATE OR REPLACE VIEW live_matches_view AS
        SELECT
            m.id,
            m.home_team_id,
            m.away_team_id,
            m.league_id,
            m.match_time,
            m.home_score,
            m.away_score,
            m.match_status,
            m.venue,
            ht.team_name as home_team_name,
            at.team_name as away_team_name,
            l.league_name,
            CASE
                WHEN m.match_status = 'IN_PROGRESS' THEN
                    EXTRACT(EPOCH FROM (NOW() - m.match_time)) / 60 as minutes_elapsed
                ELSE NULL
            END,
            -- 最新赔率信息
            (SELECT JSON_AGG(
                JSON_BUILD_OBJECT(
                    'bookmaker', o.bookmaker,
                    'home_win', o.home_win_odds,
                    'draw', o.draw_odds,
                    'away_win', o.away_win_odds,
                    'created_at', o.created_at
                )
            ) FROM odds o
             WHERE o.match_id = m.id
             AND o.market_type = 'match_winner'
             ORDER BY o.created_at DESC
             LIMIT 5) as recent_odds
        FROM matches m
        JOIN teams ht ON m.home_team_id = ht.id
        JOIN teams at ON m.away_team_id = at.id
        JOIN leagues l ON m.league_id = l.id
        WHERE m.match_status IN ('SCHEDULED', 'IN_PROGRESS', 'PAUSED')
        ORDER BY m.match_time;
    """
    )

    # 创建性能优化函数
    op.execute(
        """
        CREATE OR REPLACE FUNCTION cleanup_old_predictions(days_to_keep INTEGER DEFAULT 90)
        RETURNS INTEGER AS $$
        DECLARE
            deleted_count INTEGER;
        BEGIN
            DELETE FROM predictions
            WHERE created_at < NOW() - INTERVAL '1 day' * days_to_keep
            AND is_correct IS NULL  -- 只删除未验证的预测
            RETURNING COUNT(*) INTO deleted_count;

            RETURN deleted_count;
        END;
        $$ LANGUAGE plpgsql;
    """
    )

    # 创建数据质量检查函数
    op.execute(
        """
        CREATE OR REPLACE FUNCTION check_data_quality()
        RETURNS TABLE(
            table_name TEXT,
            issue_type TEXT,
            issue_count BIGINT,
            description TEXT
        ) AS $$
        BEGIN
            -- 检查没有比分的比赛
            RETURN QUERY
            SELECT
                'matches'::TEXT,
                'missing_scores'::TEXT,
                COUNT(*)::BIGINT,
                'Matches marked as finished but missing scores'::TEXT
            FROM matches
            WHERE match_status = 'FINISHED'
            AND (home_score IS NULL OR away_score IS NULL);

            -- 检查异常赔率
            RETURN QUERY
            SELECT
                'odds'::TEXT,
                'invalid_odds'::TEXT,
                COUNT(*)::BIGINT,
                'Odds with invalid values (<= 0 or > 1000)'::TEXT
            FROM odds
            WHERE (home_win_odds <= 0 OR home_win_odds > 1000)
               OR (draw_odds <= 0 OR draw_odds > 1000)
               OR (away_win_odds <= 0 OR away_win_odds > 1000);

            -- 检查孤立的特征数据
            RETURN QUERY
            SELECT
                'features'::TEXT,
                'orphaned_features'::TEXT,
                COUNT(*)::BIGINT,
                'Features without corresponding match'::TEXT
            FROM features f
            LEFT JOIN matches m ON f.match_id = m.id
            WHERE m.id IS NULL;

            -- 检查概率总和异常的预测
            RETURN QUERY
            SELECT
                'predictions'::TEXT,
                'invalid_probabilities'::TEXT,
                COUNT(*)::BIGINT,
                'Predictions with probability sum not close to 1.0'::TEXT
            FROM predictions
            WHERE ABS(home_win_probability + draw_probability + away_win_probability - 1.0) > 0.01;

            RETURN;
        END;
        $$ LANGUAGE plpgsql;
    """
    )

    # 添加更新时间戳触发器函数
    op.execute(
        """
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """
    )

    # 为需要的表添加更新时间戳触发器
    tables_with_updated_at = ["matches", "teams", "leagues", "predictions"]
    for table in tables_with_updated_at:
        try:
            op.execute(
                f"""
                CREATE TRIGGER update_{table}_updated_at
                    BEFORE UPDATE ON {table}
                    FOR EACH ROW
                EXECUTE FUNCTION update_updated_at_column();
            """
            )
        except (SQLAlchemyError, DatabaseError, ConnectionError, TimeoutError):
            # 触发器可能已存在，忽略错误
            pass


def downgrade():
    """回滚数据库架构"""

    # 删除触发器
    tables_with_updated_at = ["matches", "teams", "leagues", "predictions"]
    for table in tables_with_updated_at:
        op.execute(f"DROP TRIGGER IF EXISTS update_{table}_updated_at ON {table};")

    # 删除函数
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column();")
    op.execute("DROP FUNCTION IF EXISTS check_data_quality();")
    op.execute("DROP FUNCTION IF EXISTS cleanup_old_predictions(INTEGER);")

    # 删除视图
    op.execute("DROP VIEW IF EXISTS live_matches_view;")
    op.execute("DROP VIEW IF EXISTS model_accuracy_view;")
    op.execute("DROP VIEW IF EXISTS prediction_stats_view;")

    # 删除分区表
    op.execute("DROP TABLE IF EXISTS raw_scores_data_y2;")
    op.execute("DROP TABLE IF EXISTS raw_scores_data_y1;")
    op.execute("DROP TABLE IF EXISTS raw_scores_data_y0;")
    op.execute("DROP TABLE IF EXISTS raw_scores_data_partitioned;")

    # 删除索引
    op.drop_index(
        "idx_data_collection_type_status_time", table_name="data_collection_logs"
    )
    op.drop_index("idx_odds_match_bookmaker_market", table_name="odds")
    op.drop_index("idx_matches_time_status", table_name="matches")
    op.drop_index("idx_predictions_verified", table_name="predictions")
    op.drop_index("idx_predictions_match_model_created", table_name="predictions")
