#!/usr/bin/env python3
"""
测试数据工厂 - 使用factory-boy生成智能测试数据
提高测试数据质量和覆盖率
"""

import factory
from factory import fuzzy
from datetime import datetime, timedelta, timezone
from typing import Dict, Any

# 模拟项目中的模型和枚举
class MockMatchOutcome:
    HOME_WIN = "HOME_WIN"
    DRAW = "DRAW"
    AWAY_WIN = "AWAY_WIN"

class MatchFactory(factory.Factory):
    """比赛数据工厂"""

    class Meta:
        model = dict

    # 基本比赛信息
    match_id = factory.Faker("uuid4")
    home_team = fuzzy.FuzzyChoice([
        "Manchester United", "Arsenal", "Chelsea", "Liverpool",
        "Manchester City", "Tottenham", "Everton", "Newcastle",
        "Leicester City", "West Ham", "Aston Villa", "Wolves"
    ])
    away_team = fuzzy.FuzzyChoice([
        "Manchester City", "Tottenham", "Everton", "Newcastle",
        "Leicester City", "West Ham", "Aston Villa", "Wolves",
        "Manchester United", "Arsenal", "Chelsea", "Liverpool"
    ])

    # 时间和场地
    match_date = fuzzy.FuzzyDateTime(
        datetime.now(timezone.utc) - timedelta(days=30),
        datetime.now(timezone.utc) + timedelta(days=30)
    )
    venue = fuzzy.FuzzyChoice([
        "Old Trafford", "Emirates Stadium", "Stamford Bridge", "Anfield",
        "Etihad Stadium", "Tottenham Hotspur Stadium", "Goodison Park", "St. James' Park"
    ])
    league = "Premier League"
    season = "2023/24"

    # 比分数据
    home_score = fuzzy.FuzzyInteger(0, 5)
    away_score = fuzzy.FuzzyInteger(0, 5)

    # 市场赔率
    market_odds = factory.LazyAttribute(lambda o: {
        "home_win": round(fuzzy.FuzzyFloat(1.2, 4.2).evaluate(o), 2),
        "draw": round(fuzzy.FuzzyFloat(2.8, 4.8).evaluate(o), 2),
        "away_win": round(fuzzy.FuzzyFloat(1.8, 5.8).evaluate(o), 2),
    })

    # 球队统计
    team_stats = factory.LazyAttribute(lambda o: {
        "home": {
            "elo_rating": fuzzy.FuzzyInteger(1500, 2100),
            "recent_form": [fuzzy.FuzzyInteger(0, 1) for _ in range(5)],
            "goals_scored": fuzzy.FuzzyInteger(10, 50),
            "goals_conceded": fuzzy.FuzzyInteger(5, 30),
            "possession_avg": fuzzy.FuzzyFloat(40.0, 65.0),
            "shots_on_target_avg": fuzzy.FuzzyFloat(3.0, 8.0),
        },
        "away": {
            "elo_rating": fuzzy.FuzzyInteger(1500, 2100),
            "recent_form": [fuzzy.FuzzyInteger(0, 1) for _ in range(5)],
            "goals_scored": fuzzy.FuzzyInteger(10, 50),
            "goals_conceded": fuzzy.FuzzyInteger(5, 30),
            "possession_avg": fuzzy.FuzzyFloat(35.0, 60.0),
            "shots_on_target_avg": fuzzy.FuzzyFloat(2.5, 7.0),
        }
    })

    # 历史交锋数据
    h2h_history = factory.LazyAttribute(lambda o: {
        "home_wins": fuzzy.FuzzyInteger(0, 15),
        "away_wins": fuzzy.FuzzyInteger(0, 15),
        "draws": fuzzy.FuzzyInteger(0, 10),
        "last_5_games": [fuzzy.FuzzyInteger(0, 1) for _ in range(5)],
        "total_goals_last_5": fuzzy.FuzzyInteger(8, 25),
    })

    # 自动计算比赛结果
    @factory.lazy_attribute
    def outcome(self):
        if self.home_score > self.away_score:
            return MockMatchOutcome.HOME_WIN
        elif self.away_score > self.home_score:
            return MockMatchOutcome.AWAY_WIN
        else:
            return MockMatchOutcome.DRAW

class PredictionFactory(factory.Factory):
    """预测结果工厂"""

    class Meta:
        model = dict

    # 基本预测信息
    prediction_id = factory.Faker("uuid4")
    match_id = factory.Faker("uuid4")
    model_version = fuzzy.FuzzyChoice(["xgboost_v1", "xgboost_v2", "ensemble_v1"])
    prediction_time = factory.LazyAttribute(lambda o: datetime.now().isoformat())

    # 预测概率 (确保总和为1)
    @factory.lazy_attribute
    def home_win_prob(self):
        base = fuzzy.FuzzyFloat(0.2, 0.7)
        return round(base, 3)

    @factory.lazy_attribute
    def draw_prob(self):
        base = fuzzy.FuzzyFloat(0.1, 0.4)
        return round(base, 3)

    @factory.lazy_attribute
    def away_win_prob(self):
        # 确保概率总和接近1
        home = self.home_win_prob
        draw = self.draw_prob
        remaining = max(0.1, 1.0 - home - draw)
        return round(remaining, 3)

    # 置信度和预测结果
    confidence = fuzzy.FuzzyFloat(0.5, 0.95)
    predicted_class = factory.LazyAttribute(lambda o: (
        "HOME_WIN" if o.home_win_prob > max(o.draw_prob, o.away_prob) else
        "DRAW" if o.draw_prob > o.away_prob else "AWAY_WIN"
    ))

    # 特征信息
    features = factory.LazyAttribute(lambda o: {
        "elo_difference": fuzzy.FuzzyInteger(-300, 300),
        "home_form_avg": fuzzy.FuzzyFloat(0.0, 2.0),
        "away_form_avg": fuzzy.FuzzyFloat(0.0, 2.0),
        "h2h_home_advantage": fuzzy.FuzzyFloat(-0.3, 0.3),
        "venue_advantage": fuzzy.FuzzyFloat(0.0, 0.2),
        "market_implied_prob": fuzzy.FuzzyFloat(0.3, 0.7),
    })

    # 元数据
    metadata = factory.LazyAttribute(lambda o: {
        "processing_time_ms": fuzzy.FuzzyFloat(50.0, 500.0),
        "cache_hit": fuzzy.FuzzyChoice([True, False]),
        "feature_count": fuzzy.FuzzyInteger(8, 15),
        "model_confidence": fuzzy.FuzzyFloat(0.6, 0.9),
    })

class BatchPredictionFactory(factory.Factory):
    """批量预测请求工厂"""

    class Meta:
        model = dict

    batch_id = factory.Faker("uuid4")
    matches = factory.List([
        factory.SubFactory(MatchFactory)
    ])

    request_options = factory.LazyAttribute(lambda o: {
        "include_features": fuzzy.FuzzyChoice([True, False]),
        "include_metadata": fuzzy.FuzzyChoice([True, False]),
        "include_explanation": fuzzy.FuzzyChoice([True, False]),
        "batch_size": len(o.matches),
    })

    created_at = factory.LazyAttribute(lambda o: datetime.now().isoformat())

class PerformanceTestDataFactory(factory.Factory):
    """性能测试数据工厂"""

    class Meta:
        model = dict

    # 生成大量测试数据用于性能测试
    test_scenario = fuzzy.FuzzyChoice([
        "high_volume_predictions",
        "concurrent_requests",
        "large_batch_processing",
        "cache_performance"
    ])

    data_size = fuzzy.FuzzyInteger(100, 10000)
    concurrency_level = fuzzy.FuzzyInteger(1, 50)
    expected_response_time_ms = fuzzy.FuzzyFloat(10, 1000)

    @factory.lazy_attribute
    def test_matches(self):
        """生成指定数量的测试比赛"""
        return [MatchFactory() for _ in range(min(self.data_size, 1000))]

# 使用示例和便捷函数
def create_test_match_with_outcome(home_team: str, away_team: str, outcome: str) -> Dict[str, Any]:
    """创建指定结果的测试比赛"""
    match = MatchFactory(home_team=home_team, away_team=away_team)

    if outcome == MockMatchOutcome.HOME_WIN:
        match.home_score = fuzzy.FuzzyInteger(1, 4)
        match.away_score = fuzzy.FuzzyInteger(0, match.home_score - 1)
    elif outcome == MockMatchOutcome.AWAY_WIN:
        match.away_score = fuzzy.FuzzyInteger(1, 4)
        match.home_score = fuzzy.FuzzyInteger(0, match.away_score - 1)
    else:  # DRAW
        goals = fuzzy.FuzzyInteger(0, 3)
        match.home_score = match.away_score = goals

    return factory.build(dict, **match.__dict__)

def create_edge_case_match(edge_case_type: str) -> Dict[str, Any]:
    """创建边界情况测试数据"""
    if edge_case_type == "extreme_elo_diff":
        match = MatchFactory()
        match.team_stats["home"]["elo_rating"] = 2500  # 极高Elo
        match.team_stats["away"]["elo_rating"] = 1000  # 极低Elo
        return match.__dict__

    elif edge_case_type == "perfect_form":
        match = MatchFactory()
        match.team_stats["home"]["recent_form"] = [1, 1, 1, 1, 1]  # 完美状态
        match.team_stats["away"]["recent_form"] = [0, 0, 0, 0, 0]  # 极差状态
        return match.__dict__

    elif edge_case_type == "high_scoring":
        match = MatchFactory()
        match.home_score = fuzzy.FuzzyInteger(5, 10)
        match.away_score = fuzzy.FuzzyInteger(5, 10)
        return match.__dict__

    else:
        return MatchFactory().__dict__

if __name__ == "__main__":
    # 演示用法
    print("🏭 测试数据工厂演示")

    # 生成单个比赛
    match = MatchFactory()
    print(f"生成的比赛: {match.home_team} vs {match.away_team}")
    print(f"比分: {match.home_score}-{match.away_score}")
    print(f"结果: {match.outcome}")

    # 生成预测
    prediction = PredictionFactory()
    print(f"\n预测结果: {prediction.predicted_class}")
    print(f"概率: 主胜 {prediction.home_win_prob:.1%} | 平局 {prediction.draw_prob:.1%} | 客胜 {prediction.away_win_prob:.1%}")

    # 生成批量数据
    batch = BatchPredictionFactory()
    print(f"\n批量预测: {len(batch.matches)} 场比赛")

    # 边界情况
    extreme_match = create_edge_case_match("extreme_elo_diff")
    print(f"\n极端Elo差异比赛: Elo差 {extreme_match['team_stats']['home']['elo_rating'] - extreme_match['team_stats']['away']['elo_rating']}")