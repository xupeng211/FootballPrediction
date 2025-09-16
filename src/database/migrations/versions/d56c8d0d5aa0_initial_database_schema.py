"""Initial database schema


Revision ID: d56c8d0d5aa0
Revises:
Create Date: 2025-09-07 20:13:08.860093

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d56c8d0d5aa0"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 创建联赛表
    op.create_table(
        "leagues",
        sa.Column("id", sa.Integer(), nullable=False, comment="主键ID"),
        sa.Column("league_name", sa.String(length=100), nullable=False, comment="联赛名称"),
        sa.Column("league_code", sa.String(length=20), nullable=True, comment="联赛代码"),
        sa.Column("country", sa.String(length=50), nullable=True, comment="所属国家"),
        sa.Column("level", sa.Integer(), nullable=True, comment="联赛级别"),
        sa.Column("season_start_month", sa.Integer(), nullable=True, comment="赛季开始月份"),
        sa.Column("season_end_month", sa.Integer(), nullable=True, comment="赛季结束月份"),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, default=True, comment="是否活跃"
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False, comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, comment="更新时间"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("league_code"),
    )
    op.create_index("idx_leagues_country", "leagues", ["country"])
    op.create_index("idx_leagues_active", "leagues", ["is_active"])
    op.create_index("idx_leagues_level", "leagues", ["level"])

    # 创建球队表
    op.create_table(
        "teams",
        sa.Column("id", sa.Integer(), nullable=False, comment="主键ID"),
        sa.Column("team_name", sa.String(length=100), nullable=False, comment="球队名称"),
        sa.Column("team_code", sa.String(length=10), nullable=True, comment="球队代码"),
        sa.Column("country", sa.String(length=50), nullable=True, comment="所属国家"),
        sa.Column("league_id", sa.Integer(), nullable=True, comment="所属联赛ID"),
        sa.Column("founded_year", sa.Integer(), nullable=True, comment="成立年份"),
        sa.Column("stadium", sa.String(length=100), nullable=True, comment="主场体育场"),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, default=True, comment="是否活跃"
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False, comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, comment="更新时间"),
        sa.ForeignKeyConstraint(["league_id"], ["leagues.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("team_code"),
    )
    op.create_index("idx_teams_league", "teams", ["league_id"])
    op.create_index("idx_teams_country", "teams", ["country"])
    op.create_index("idx_teams_active", "teams", ["is_active"])

    # 创建比赛表
    op.create_table(
        "matches",
        sa.Column("id", sa.Integer(), nullable=False, comment="主键ID"),
        sa.Column("home_team_id", sa.Integer(), nullable=False, comment="主场球队ID"),
        sa.Column("away_team_id", sa.Integer(), nullable=False, comment="客场球队ID"),
        sa.Column("league_id", sa.Integer(), nullable=False, comment="联赛ID"),
        sa.Column("season", sa.String(length=20), nullable=True, comment="赛季"),
        sa.Column("match_date", sa.DateTime(), nullable=False, comment="比赛日期时间"),
        sa.Column(
            "match_status",
            sa.Enum("scheduled", "live", "finished", "cancelled", name="matchstatus"),
            nullable=False,
            default="scheduled",
            comment="比赛状态",
        ),
        sa.Column("home_score", sa.Integer(), nullable=True, comment="主队得分"),
        sa.Column("away_score", sa.Integer(), nullable=True, comment="客队得分"),
        sa.Column("home_goals_ht", sa.Integer(), nullable=True, comment="主队半场得分"),
        sa.Column("away_goals_ht", sa.Integer(), nullable=True, comment="客队半场得分"),
        sa.Column("attendance", sa.Integer(), nullable=True, comment="观众人数"),
        sa.Column("referee", sa.String(length=100), nullable=True, comment="主裁判"),
        sa.Column("venue", sa.String(length=100), nullable=True, comment="比赛场地"),
        sa.Column(
            "weather_condition", sa.String(length=50), nullable=True, comment="天气状况"
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False, comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, comment="更新时间"),
        sa.ForeignKeyConstraint(["away_team_id"], ["teams.id"]),
        sa.ForeignKeyConstraint(["home_team_id"], ["teams.id"]),
        sa.ForeignKeyConstraint(["league_id"], ["leagues.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_matches_date", "matches", ["match_date"])
    op.create_index("idx_matches_teams", "matches", ["home_team_id", "away_team_id"])
    op.create_index("idx_matches_league_season", "matches", ["league_id", "season"])
    op.create_index("idx_matches_status", "matches", ["match_status"])
    op.create_index(
        "idx_matches_home_team_date", "matches", ["home_team_id", "match_date"]
    )
    op.create_index(
        "idx_matches_away_team_date", "matches", ["away_team_id", "match_date"]
    )

    # 创建赔率表
    op.create_table(
        "odds",
        sa.Column("id", sa.Integer(), nullable=False, comment="主键ID"),
        sa.Column("match_id", sa.Integer(), nullable=False, comment="比赛ID"),
        sa.Column("bookmaker", sa.String(length=50), nullable=False, comment="博彩公司名称"),
        sa.Column(
            "market_type",
            sa.Enum(
                "1x2",
                "over_under",
                "asian_handicap",
                "both_teams_score",
                name="markettype",
            ),
            nullable=False,
            comment="赔率市场类型",
        ),
        sa.Column(
            "home_odds",
            sa.DECIMAL(precision=8, scale=4),
            nullable=True,
            comment="主胜赔率",
        ),
        sa.Column(
            "draw_odds",
            sa.DECIMAL(precision=8, scale=4),
            nullable=True,
            comment="平局赔率",
        ),
        sa.Column(
            "away_odds",
            sa.DECIMAL(precision=8, scale=4),
            nullable=True,
            comment="客胜赔率",
        ),
        sa.Column(
            "over_odds",
            sa.DECIMAL(precision=8, scale=4),
            nullable=True,
            comment="大球赔率",
        ),
        sa.Column(
            "under_odds",
            sa.DECIMAL(precision=8, scale=4),
            nullable=True,
            comment="小球赔率",
        ),
        sa.Column(
            "line_value",
            sa.DECIMAL(precision=4, scale=2),
            nullable=True,
            comment="盘口值",
        ),
        sa.Column("collected_at", sa.DateTime(), nullable=False, comment="赔率收集时间"),
        sa.Column("created_at", sa.DateTime(), nullable=False, comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, comment="更新时间"),
        sa.ForeignKeyConstraint(["match_id"], ["matches.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_odds_match_bookmaker", "odds", ["match_id", "bookmaker"])
    op.create_index("idx_odds_collected_at", "odds", ["collected_at"])
    op.create_index("idx_odds_market_type", "odds", ["market_type"])
    op.create_index("idx_odds_match_market", "odds", ["match_id", "market_type"])

    # 创建特征表
    op.create_table(
        "features",
        sa.Column("id", sa.Integer(), nullable=False, comment="主键ID"),
        sa.Column("match_id", sa.Integer(), nullable=False, comment="比赛ID"),
        sa.Column("team_id", sa.Integer(), nullable=False, comment="球队ID"),
        sa.Column(
            "team_type",
            sa.Enum("home", "away", name="teamtype"),
            nullable=False,
            comment="球队类型",
        ),
        # 基础统计特征
        sa.Column(
            "recent_5_wins",
            sa.Integer(),
            nullable=False,
            default=0,
            comment="最近5场胜利场次",
        ),
        sa.Column(
            "recent_5_draws",
            sa.Integer(),
            nullable=False,
            default=0,
            comment="最近5场平局场次",
        ),
        sa.Column(
            "recent_5_losses",
            sa.Integer(),
            nullable=False,
            default=0,
            comment="最近5场失败场次",
        ),
        sa.Column(
            "recent_5_goals_for",
            sa.Integer(),
            nullable=False,
            default=0,
            comment="最近5场进球数",
        ),
        sa.Column(
            "recent_5_goals_against",
            sa.Integer(),
            nullable=False,
            default=0,
            comment="最近5场失球数",
        ),
        # 主客场特征
        sa.Column(
            "home_wins", sa.Integer(), nullable=False, default=0, comment="主场胜利场次"
        ),
        sa.Column(
            "home_draws",
            sa.Integer(),
            nullable=False,
            default=0,
            comment="主场平局场次",
        ),
        sa.Column(
            "home_losses",
            sa.Integer(),
            nullable=False,
            default=0,
            comment="主场失败场次",
        ),
        sa.Column(
            "away_wins", sa.Integer(), nullable=False, default=0, comment="客场胜利场次"
        ),
        sa.Column(
            "away_draws",
            sa.Integer(),
            nullable=False,
            default=0,
            comment="客场平局场次",
        ),
        sa.Column(
            "away_losses",
            sa.Integer(),
            nullable=False,
            default=0,
            comment="客场失败场次",
        ),
        # 对战历史特征
        sa.Column(
            "h2h_wins",
            sa.Integer(),
            nullable=False,
            default=0,
            comment="历史交锋胜利场次",
        ),
        sa.Column(
            "h2h_draws",
            sa.Integer(),
            nullable=False,
            default=0,
            comment="历史交锋平局场次",
        ),
        sa.Column(
            "h2h_losses",
            sa.Integer(),
            nullable=False,
            default=0,
            comment="历史交锋失败场次",
        ),
        sa.Column(
            "h2h_goals_for",
            sa.Integer(),
            nullable=False,
            default=0,
            comment="历史交锋进球数",
        ),
        sa.Column(
            "h2h_goals_against",
            sa.Integer(),
            nullable=False,
            default=0,
            comment="历史交锋失球数",
        ),
        # 联赛排名特征
        sa.Column("league_position", sa.Integer(), nullable=True, comment="联赛排名"),
        sa.Column("points", sa.Integer(), nullable=True, comment="联赛积分"),
        sa.Column("goal_difference", sa.Integer(), nullable=True, comment="净胜球"),
        # 其他特征
        sa.Column(
            "days_since_last_match",
            sa.Integer(),
            nullable=True,
            comment="距离上场比赛天数",
        ),
        sa.Column(
            "is_derby",
            sa.Boolean(),
            nullable=False,
            default=False,
            comment="是否为德比战",
        ),
        sa.Column(
            "avg_possession",
            sa.DECIMAL(precision=5, scale=2),
            nullable=True,
            comment="平均控球率",
        ),
        sa.Column(
            "avg_shots_per_game",
            sa.DECIMAL(precision=5, scale=2),
            nullable=True,
            comment="场均射门次数",
        ),
        # 扩展特征
        sa.Column(
            "avg_goals_per_game",
            sa.DECIMAL(precision=4, scale=2),
            nullable=True,
            comment="场均进球数",
        ),
        sa.Column(
            "avg_shots_on_target",
            sa.DECIMAL(precision=5, scale=2),
            nullable=True,
            comment="场均射正次数",
        ),
        sa.Column(
            "avg_corners_per_game",
            sa.DECIMAL(precision=4, scale=2),
            nullable=True,
            comment="场均角球数",
        ),
        sa.Column(
            "avg_goals_conceded",
            sa.DECIMAL(precision=4, scale=2),
            nullable=True,
            comment="场均失球数",
        ),
        sa.Column(
            "clean_sheets",
            sa.Integer(),
            nullable=False,
            default=0,
            comment="零失球场次",
        ),
        sa.Column(
            "avg_cards_per_game",
            sa.DECIMAL(precision=4, scale=2),
            nullable=True,
            comment="场均黄牌数",
        ),
        sa.Column("current_form", sa.String(length=10), nullable=True, comment="当前状态"),
        sa.Column(
            "win_streak", sa.Integer(), nullable=False, default=0, comment="连胜场次"
        ),
        sa.Column(
            "unbeaten_streak",
            sa.Integer(),
            nullable=False,
            default=0,
            comment="不败场次",
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False, comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, comment="更新时间"),
        sa.ForeignKeyConstraint(["match_id"], ["matches.id"]),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_features_match", "features", ["match_id"])
    op.create_index("idx_features_team", "features", ["team_id"])
    op.create_index("idx_features_match_team", "features", ["match_id", "team_id"])

    # 创建预测表
    op.create_table(
        "predictions",
        sa.Column("id", sa.Integer(), nullable=False, comment="主键ID"),
        sa.Column("match_id", sa.Integer(), nullable=False, comment="比赛ID"),
        sa.Column("model_name", sa.String(length=50), nullable=False, comment="模型名称"),
        sa.Column(
            "model_version", sa.String(length=20), nullable=False, comment="模型版本号"
        ),
        sa.Column(
            "predicted_result",
            sa.Enum("home_win", "draw", "away_win", name="predictedresult"),
            nullable=False,
            comment="预测的比赛结果",
        ),
        sa.Column(
            "home_win_probability",
            sa.DECIMAL(precision=5, scale=4),
            nullable=False,
            comment="主队获胜概率",
        ),
        sa.Column(
            "draw_probability",
            sa.DECIMAL(precision=5, scale=4),
            nullable=False,
            comment="平局概率",
        ),
        sa.Column(
            "away_win_probability",
            sa.DECIMAL(precision=5, scale=4),
            nullable=False,
            comment="客队获胜概率",
        ),
        sa.Column(
            "predicted_home_score",
            sa.DECIMAL(precision=3, scale=2),
            nullable=True,
            comment="预测主队得分",
        ),
        sa.Column(
            "predicted_away_score",
            sa.DECIMAL(precision=3, scale=2),
            nullable=True,
            comment="预测客队得分",
        ),
        sa.Column(
            "over_2_5_probability",
            sa.DECIMAL(precision=5, scale=4),
            nullable=True,
            comment="大于2.5球概率",
        ),
        sa.Column(
            "both_teams_score_probability",
            sa.DECIMAL(precision=5, scale=4),
            nullable=True,
            comment="双方进球概率",
        ),
        sa.Column(
            "confidence_score",
            sa.DECIMAL(precision=5, scale=4),
            nullable=True,
            comment="预测置信度评分",
        ),
        sa.Column("feature_importance", sa.JSON(), nullable=True, comment="特征重要性数据"),
        sa.Column("predicted_at", sa.DateTime(), nullable=False, comment="预测生成时间"),
        sa.Column("created_at", sa.DateTime(), nullable=False, comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, comment="更新时间"),
        sa.ForeignKeyConstraint(["match_id"], ["matches.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_predictions_match_model", "predictions", ["match_id", "model_name"]
    )
    op.create_index("idx_predictions_predicted_at", "predictions", ["predicted_at"])
    op.create_index(
        "idx_predictions_model_version", "predictions", ["model_name", "model_version"]
    )


def downgrade() -> None:
    # 删除表（按相反顺序）
    op.drop_table("predictions")
    op.drop_table("features")
    op.drop_table("odds")
    op.drop_table("matches")
    op.drop_table("teams")
    op.drop_table("leagues")
