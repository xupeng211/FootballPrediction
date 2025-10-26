import logging
import sqlalchemy as sa
from typing import Union, Sequence
from alembic import op

# mypy: ignore-errors
from sqlalchemy import text

logger = logging.getLogger(__name__)
"""add_business_constraints

Revision ID: a20f91c49306
Revises: d82ea26f05d0
Create Date: 2025-09-11 23:59:32.853716

为关键表添加业务逻辑约束和触发器：
1. 比分字段必须 >=0 且 <=99
2. 赔率必须 >1.01
3. 比赛时间必须大于 2000-01-01
4. 外键引用一致性触发器
"""

# revision identifiers, used by Alembic.
revision: str = "a20f91c49306"
down_revision: Union[str, None] = "d82ea26f05d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """添加业务逻辑约束和触发器"""

    # 检查是否在SQLite环境中（测试环境）
    conn = op.get_bind()
    db_dialect = conn.dialect.name.lower()

    if db_dialect == "sqlite":
        logger.info("⚠️  SQLite环境：跳过业务约束和触发器创建")
        op.execute("-- SQLite environment: skipped business constraints and triggers")
        op.execute(
            "-- SQLite environment: SQLite does not support ALTER ADD CONSTRAINT"
        )
        return

    # 1. 添加比分字段CHECK约束（0-99）
    op.create_check_constraint(
        "ck_matches_home_score_range",
        "matches",
        sa.and_(
            sa.or_(
                sa.column("home_score").is_(None),
                sa.and_(sa.column("home_score") >= 0, sa.column("home_score") <= 99),
            )
        ),
    )

    op.create_check_constraint(
        "ck_matches_away_score_range",
        "matches",
        sa.and_(
            sa.or_(
                sa.column("away_score").is_(None),
                sa.and_(sa.column("away_score") >= 0, sa.column("away_score") <= 99),
            )
        ),
    )

    op.create_check_constraint(
        "ck_matches_home_ht_score_range",
        "matches",
        sa.and_(
            sa.or_(
                sa.column("home_ht_score").is_(None),
                sa.and_(
                    sa.column("home_ht_score") >= 0,
                    sa.column("home_ht_score") <= 99,
                ),
            )
        ),
    )

    op.create_check_constraint(
        "ck_matches_away_ht_score_range",
        "matches",
        sa.and_(
            sa.or_(
                sa.column("away_ht_score").is_(None),
                sa.and_(
                    sa.column("away_ht_score") >= 0,
                    sa.column("away_ht_score") <= 99,
                ),
            )
        ),
    )

    # 2. 添加赔率字段CHECK约束（>1.01）
    op.create_check_constraint(
        "ck_odds_home_odds_range",
        "odds",
        sa.or_(sa.column("home_odds").is_(None), sa.column("home_odds") > 1.01),
    )

    op.create_check_constraint(
        "ck_odds_draw_odds_range",
        "odds",
        sa.or_(sa.column("draw_odds").is_(None), sa.column("draw_odds") > 1.01),
    )

    op.create_check_constraint(
        "ck_odds_away_odds_range",
        "odds",
        sa.or_(sa.column("away_odds").is_(None), sa.column("away_odds") > 1.01),
    )

    op.create_check_constraint(
        "ck_odds_over_odds_range",
        "odds",
        sa.or_(sa.column("over_odds").is_(None), sa.column("over_odds") > 1.01),
    )

    op.create_check_constraint(
        "ck_odds_under_odds_range",
        "odds",
        sa.or_(sa.column("under_odds").is_(None), sa.column("under_odds") > 1.01),
    )

    # 3. 添加比赛时间CHECK约束（>2000-01-01）
    op.create_check_constraint(
        "ck_matches_match_time_range",
        "matches",
        sa.column("match_time") > sa.text("'2000-01-01'::date"),
    )

    # 4. 添加触发器函数和触发器（确保外键引用一致性）
    # 4.1 创建触发器函数，确保主队和客队不能相同
    op.execute(
        """
        CREATE OR REPLACE FUNCTION check_match_teams_consistency()
        RETURNS TRIGGER AS $$
        BEGIN
            -- 检查主队和客队不能相同
            IF NEW.home_team_id = NEW.away_team_id THEN
                RAISE EXCEPTION 'Home team and away team cannot be the same: team_id = %', NEW.home_team_id;
            END IF;

            -- 检查主队和客队都必须存在于teams表中
            IF NOT EXISTS (SELECT 1 FROM teams WHERE id = NEW.home_team_id) THEN
                RAISE EXCEPTION 'Home team does not exist: team_id = %', NEW.home_team_id;
            END IF;

            IF NOT EXISTS (SELECT 1 FROM teams WHERE id = NEW.away_team_id) THEN
                RAISE EXCEPTION 'Away team does not exist: team_id = %', NEW.away_team_id;
            END IF;

            -- 检查联赛是否存在
            IF NOT EXISTS (SELECT 1 FROM leagues WHERE id = NEW.league_id) THEN
                RAISE EXCEPTION 'League does not exist: league_id = %', NEW.league_id;
            END IF;

            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """
    )

    # 4.2 创建触发器
    op.execute(
        """
        CREATE TRIGGER tr_check_match_teams_consistency
        BEFORE INSERT OR UPDATE ON matches
        FOR EACH ROW
        EXECUTE FUNCTION check_match_teams_consistency();
    """
    )

    # 4.3 创建赔率表的引用一致性触发器函数
    op.execute(
        """
        CREATE OR REPLACE FUNCTION check_odds_consistency()
        RETURNS TRIGGER AS $$
        BEGIN
            -- 检查比赛是否存在
            IF NOT EXISTS (SELECT 1 FROM matches WHERE id = NEW.match_id) THEN
                RAISE EXCEPTION 'Match does not exist: match_id = %', NEW.match_id;
            END IF;

            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """
    )

    # 4.4 创建赔率表触发器
    op.execute(
        """
        CREATE TRIGGER tr_check_odds_consistency
        BEFORE INSERT OR UPDATE ON odds
        FOR EACH ROW
        EXECUTE FUNCTION check_odds_consistency();
    """
    )


def downgrade() -> None:
    """移除业务逻辑约束和触发器"""

    # 检查是否在SQLite环境中（测试环境）
    conn = op.get_bind()
    db_dialect = conn.dialect.name.lower()

    if db_dialect == "sqlite":
        logger.info("⚠️  SQLite环境：跳过业务约束和触发器移除")
        op.execute(
            "-- SQLite environment: skipped business constraints and triggers removal"
        )
        op.execute("-- SQLite environment: SQLite does not support DROP CONSTRAINT")
        return

    # 移除触发器
    op.execute("DROP TRIGGER IF EXISTS tr_check_odds_consistency ON odds;")
    op.execute("DROP TRIGGER IF EXISTS tr_check_match_teams_consistency ON matches;")

    # 移除触发器函数
    op.execute("DROP FUNCTION IF EXISTS check_odds_consistency();")
    op.execute("DROP FUNCTION IF EXISTS check_match_teams_consistency();")

    # 移除CHECK约束
    op.drop_constraint("ck_matches_match_time_range", "matches", type_="check")

    # 移除赔率约束
    op.drop_constraint("ck_odds_under_odds_range", "odds", type_="check")
    op.drop_constraint("ck_odds_over_odds_range", "odds", type_="check")
    op.drop_constraint("ck_odds_away_odds_range", "odds", type_="check")
    op.drop_constraint("ck_odds_draw_odds_range", "odds", type_="check")
    op.drop_constraint("ck_odds_home_odds_range", "odds", type_="check")

    # 移除比分约束
    op.drop_constraint("ck_matches_away_ht_score_range", "matches", type_="check")
    op.drop_constraint("ck_matches_home_ht_score_range", "matches", type_="check")
    op.drop_constraint("ck_matches_away_score_range", "matches", type_="check")
    op.drop_constraint("ck_matches_home_score_range", "matches", type_="check")
