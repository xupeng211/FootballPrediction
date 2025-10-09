"""
特征定义模块
Feature Definitions Module
"""

# 尝试导入Feast
try:
    from feast import Entity, FeatureView, Field
    from feast.types import Float32, Int64, String
    from feast.data_source import PushSource
    from feast.value_type import ValueType
    from datetime import timedelta
    HAS_FEAST = True
except ImportError:
    HAS_FEAST = False

# 创建虚拟类以防Feast未安装
if not HAS_FEAST:
    class Entity:
        def __init__(self, *args, **kwargs):
            pass

    class FeatureView:
        def __init__(self, *args, **kwargs):
            pass

    class Field:
        def __init__(self, *args, **kwargs):
            pass

    class Float32:
        pass

    class Int64:
        pass

    class String:
        pass

    class PushSource:
        def __init__(self, *args, **kwargs):
            pass

    class timedelta:
        def __init__(self, *args, **kwargs):
            pass

    class ValueType:
        INT64 = "int64"
        STRING = "string"
        FLOAT = "float"

# 定义实体
match_entity = Entity(
    name="match_id",
    join_keys=["match_id"],
    description="比赛实体",
    value_type=ValueType.INT64 if HAS_FEAST else Int64,
)

team_entity = Entity(
    name="team_id",
    join_keys=["team_id"],
    description="球队实体",
    value_type=ValueType.INT64 if HAS_FEAST else Int64,
)

# 定义数据源 - 使用None作为占位符
match_data_source = None if not HAS_FEAST else PushSource(
    name="match_data_source",
    batch_source=None,
)

team_data_source = None if not HAS_FEAST else PushSource(
    name="team_data_source",
    batch_source=None,
)

odds_data_source = None if not HAS_FEAST else PushSource(
    name="odds_data_source",
    batch_source=None,
)

head_to_head_data_source = None if not HAS_FEAST else PushSource(
    name="head_to_head_data_source",
    batch_source=None,
)

# 定义特征视图 - 创建简化版本
match_features_view = None
team_recent_stats_view = None
odds_features_view = None
head_to_head_features_view = None

# 如果Feast可用，创建完整的特征视图
if HAS_FEAST:
    try:
        match_features_view = FeatureView(
            name="match_features",
            entities=[match_entity],
            ttl=timedelta(days=365),
            schema=[
                Field(name="home_team_id", dtype=Int64),
                Field(name="away_team_id", dtype=Int64),
                Field(name="league_id", dtype=Int64),
                Field(name="venue", dtype=String),
                Field(name="match_time", dtype=String),
                Field(name="home_score", dtype=Int64),
                Field(name="away_score", dtype=Int64),
                Field(name="match_status", dtype=String),
            ],
            source=match_data_source,
        )

        team_recent_stats_view = FeatureView(
            name="team_recent_stats",
            entities=[team_entity],
            ttl=timedelta(days=30),
            schema=[
                Field(name="recent_form", dtype=String),
                Field(name="goals_scored_avg", dtype=Float32),
                Field(name="goals_conceded_avg", dtype=Float32),
                Field(name="win_rate", dtype=Float32),
                Field(name="clean_sheets", dtype=Int64),
                Field(name="failed_to_score", dtype=Int64),
            ],
            source=team_data_source,
        )

        odds_features_view = FeatureView(
            name="odds_features",
            entities=[match_entity],
            ttl=timedelta(days=7),
            schema=[
                Field(name="home_win_odds", dtype=Float32),
                Field(name="draw_odds", dtype=Float32),
                Field(name="away_win_odds", dtype=Float32),
                Field(name="over_under_odds", dtype=Float32),
                Field(name="asian_handicap", dtype=Float32),
            ],
            source=odds_data_source,
        )

        head_to_head_features_view = FeatureView(
            name="head_to_head_features",
            entities=[match_entity],
            ttl=timedelta(days=365),
            schema=[
                Field(name="home_wins", dtype=Int64),
                Field(name="away_wins", dtype=Int64),
                Field(name="draws", dtype=Int64),
                Field(name="home_goals", dtype=Int64),
                Field(name="away_goals", dtype=Int64),
                Field(name="last_meeting_date", dtype=String),
            ],
            source=head_to_head_data_source,
        )
    except:
        # 如果创建失败，保持为None
        pass