"""
特征视图定义
Feature View Definitions

定义 Feast 特征存储的特征视图。
"""

from datetime import timedelta
from typing import Dict

from .data_sources import get_match_data_source, get_odds_data_source, get_team_data_source
from .entities import get_entity_definitions
from .mock_feast import FeatureView, Field, Float64, Int64


def get_feature_view_definitions() -> Dict[str, FeatureView]:
    """
    获取特征视图定义

    Returns:
        Dict[str, FeatureView]: 特征视图名称到视图对象的映射
    """
    entities = get_entity_definitions()

    return {
        "team_recent_performance": FeatureView(
            name="team_recent_performance",
            entities=[entities["team"]],
            ttl=timedelta(days=7),
            schema=[
                Field(name="recent_5_wins", dtype=Int64),
                Field(name="recent_5_draws", dtype=Int64),
                Field(name="recent_5_losses", dtype=Int64),
                Field(name="recent_5_goals_for", dtype=Int64),
                Field(name="recent_5_goals_against", dtype=Int64),
                Field(name="recent_5_points", dtype=Int64),
                Field(name="recent_5_home_wins", dtype=Int64),
                Field(name="recent_5_away_wins", dtype=Int64),
                Field(name="recent_5_home_goals_for", dtype=Int64),
                Field(name="recent_5_away_goals_for", dtype=Int64),
            ],
            source=get_team_data_source(),
            description="球队近期表现特征（最近5场比赛）",
        ),
        "historical_matchup": FeatureView(
            name="historical_matchup",
            entities=[entities["match"]],
            ttl=timedelta(days=30),
            schema=[
                Field(name="home_team_id", dtype=Int64),
                Field(name="away_team_id", dtype=Int64),
                Field(name="h2h_total_matches", dtype=Int64),
                Field(name="h2h_home_wins", dtype=Int64),
                Field(name="h2h_away_wins", dtype=Int64),
                Field(name="h2h_draws", dtype=Int64),
                Field(name="h2h_home_goals_total", dtype=Int64),
                Field(name="h2h_away_goals_total", dtype=Int64),
            ],
            source=get_match_data_source(),
            description="球队历史对战特征",
        ),
        "odds_features": FeatureView(
            name="odds_features",
            entities=[entities["match"]],
            ttl=timedelta(hours=6),
            schema=[
                Field(name="home_odds_avg", dtype=Float64),
                Field(name="draw_odds_avg", dtype=Float64),
                Field(name="away_odds_avg", dtype=Float64),
                Field(name="home_implied_probability", dtype=Float64),
                Field(name="draw_implied_probability", dtype=Float64),
                Field(name="away_implied_probability", dtype=Float64),
                Field(name="bookmaker_count", dtype=Int64),
                Field(name="bookmaker_consensus", dtype=Float64),
            ],
            source=get_odds_data_source(),
            description="赔率衍生特征",
        ),
    }