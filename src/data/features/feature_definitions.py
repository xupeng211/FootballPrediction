"""
足球预测系统特征定义

定义用于机器学习模型的实体和特征视图。
包括比赛特征、球队统计特征、赔率衍生特征等。

基于 DATA_DESIGN.md 第6.1节特征仓库设计。
"""

from datetime import timedelta
from typing import Dict, List, Optional


class FeatureDefinitions:
    """特征定义类，包含所有特征相关的定义"""

    # 实体定义
    ENTITIES = {
        "match_id": "比赛唯一标识符",
        "team_id": "球队唯一标识符",
        "league_id": "联赛唯一标识符",
    }

    # 特征视图定义
    FEATURE_VIEWS = {
        "match_features": {
            "name": "match_features",
            "description": "比赛基本特征",
            "ttl_days": 30,
            "features": [
                "home_team_id",
                "away_team_id",
                "league_id",
                "season",
                "match_round",
                "venue_id",
            ],
        },
        "team_recent_stats": {
            "name": "team_recent_stats",
            "description": "球队近期表现特征",
            "ttl_days": 7,
            "features": [
                "recent_5_wins",
                "recent_5_goals_for",
                "recent_5_goals_against",
                "recent_10_wins",
                "home_wins",
                "away_wins",
            ],
        },
        "odds_features": {
            "name": "odds_features",
            "description": "赔率衍生特征",
            "ttl_hours": 6,
            "features": [
                "home_win_odds",
                "draw_odds",
                "away_win_odds",
                "over_2_5_odds",
                "under_2_5_odds",
            ],
        },
    }


# 为了兼容性，提供简化的模拟对象
class MockEntity:
    def __init__(self, name: str, description: str, join_keys: List[str]) -> None:
        self.name = name
        self.description = description
        self.join_keys = join_keys


class MockFeatureView:
    def __init__(
        self,
        name: str,
        entities: Optional[List[MockEntity]] = None,
        ttl: Optional[timedelta] = None,
        source: Optional["MockFileSource"] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> None:
        self.name = name
        self.entities = entities or []
        self.ttl = ttl
        self.source = source
        self.tags = tags or {}


class MockFileSource:
    def __init__(self, name: str, path: str, timestamp_field: str) -> None:
        self.name = name
        self.path = path
        self.timestamp_field = timestamp_field


# 实体定义
match_entity = MockEntity(name="match_id", description="比赛唯一标识符", join_keys=["match_id"])

team_entity = MockEntity(name="team_id", description="球队唯一标识符", join_keys=["team_id"])

league_entity = MockEntity(name="league_id", description="联赛唯一标识符", join_keys=["league_id"])

# 数据源定义
match_features_source = MockFileSource(
    name="match_features_source",
    path="data/match_features.parquet",
    timestamp_field="event_timestamp",
)

team_stats_source = MockFileSource(
    name="team_recent_stats_source",
    path="data/team_stats.parquet",
    timestamp_field="event_timestamp",
)

odds_features_source = MockFileSource(
    name="odds_features_source",
    path="data/odds_features.parquet",
    timestamp_field="event_timestamp",
)

# 特征视图定义
match_features_view = MockFeatureView(
    name="match_features",
    entities=[match_entity],
    ttl=timedelta(days=30),
    source=match_features_source,
    tags={"team": "data", "type": "match_context"},
)

team_recent_stats_view = MockFeatureView(
    name="team_recent_stats",
    entities=[team_entity],
    ttl=timedelta(days=7),
    source=team_stats_source,
    tags={"team": "data", "type": "team_performance"},
)

odds_features_view = MockFeatureView(
    name="odds_features",
    entities=[match_entity],
    ttl=timedelta(hours=6),
    source=odds_features_source,
    tags={"team": "data", "type": "betting_odds"},
)

head_to_head_features_view = MockFeatureView(
    name="head_to_head_features",
    entities=[match_entity],
    ttl=timedelta(days=365),
    source=odds_features_source,  # 复用数据源
    tags={"team": "data", "type": "historical_matchup"},
)


# 特征服务定义（简化版本）
class FeatureServices:
    """特征服务定义类"""

    MATCH_PREDICTION = {
        "name": "match_prediction_v1",
        "features": [
            "match_features",
            "team_recent_stats",
            "odds_features",
            "head_to_head_features",
        ],
        "tags": {"model": "match_outcome", "version": "v1"},
    }

    GOALS_PREDICTION = {
        "name": "goals_prediction_v1",
        "features": ["team_recent_stats", "odds_features", "head_to_head_features"],
        "tags": {"model": "goals_total", "version": "v1"},
    }

    REAL_TIME_PREDICTION = {
        "name": "real_time_prediction_v1",
        "features": ["odds_features", "team_recent_stats"],
        "tags": {"model": "real_time", "version": "v1", "latency": "low"},
    }
