#!/usr/bin/env python3
"""
简化版测试数据工厂 - 专注于实用功能
"""

import random
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from faker import Faker

# 初始化Faker
fake = Faker("en_GB")


class SimpleMatchFactory:
    """简化的比赛数据工厂"""

    TEAMS = [
        "Manchester United",
        "Arsenal",
        "Chelsea",
        "Liverpool",
        "Manchester City",
        "Tottenham",
        "Everton",
        "Newcastle",
        "Leicester City",
        "West Ham",
        "Aston Villa",
        "Wolves",
    ]

    VENUES = [
        "Old Trafford",
        "Emirates Stadium",
        "Stamford Bridge",
        "Anfield",
        "Etihad Stadium",
        "Tottenham Hotspur Stadium",
        "Goodison Park",
        "St. James' Park",
    ]

    @classmethod
    def create_match(cls, **overrides) -> Dict[str, Any]:
        """创建测试比赛数据"""
        home_team = overrides.get("home_team", random.choice(cls.TEAMS))

        # 确保主客队不同
        away_team = overrides.get("away_team", random.choice([t for t in cls.TEAMS if t != home_team]))

        base_match = {
            "match_id": overrides.get("match_id", fake.uuid4()),
            "home_team": home_team,
            "away_team": away_team,
            "match_date": overrides.get(
                "match_date", datetime.now(timezone.utc) + timedelta(days=random.randint(1, 30))
            ),
            "venue": overrides.get("venue", random.choice(cls.VENUES)),
            "league": "Premier League",
            "season": "2023/24",
            "home_score": overrides.get("home_score", random.randint(0, 4)),
            "away_score": overrides.get("away_score", random.randint(0, 4)),
            "market_odds": {
                "home_win": round(random.uniform(1.5, 4.5), 2),
                "draw": round(random.uniform(2.8, 4.0), 2),
                "away_win": round(random.uniform(1.8, 5.5), 2),
            },
            "team_stats": {
                "home": {
                    "elo_rating": random.randint(1500, 2100),
                    "recent_form": [random.randint(0, 1) for _ in range(5)],
                    "goals_scored": random.randint(10, 50),
                    "goals_conceded": random.randint(5, 30),
                },
                "away": {
                    "elo_rating": random.randint(1500, 2100),
                    "recent_form": [random.randint(0, 1) for _ in range(5)],
                    "goals_scored": random.randint(10, 50),
                    "goals_conceded": random.randint(5, 30),
                },
            },
            "h2h_history": {
                "home_wins": random.randint(0, 15),
                "away_wins": random.randint(0, 15),
                "draws": random.randint(0, 10),
                "last_5_games": [random.randint(0, 1) for _ in range(5)],
            },
        }

        # 确定比赛结果
        if base_match["home_score"] > base_match["away_score"]:
            base_match["outcome"] = "HOME_WIN"
        elif base_match["away_score"] > base_match["home_score"]:
            base_match["outcome"] = "AWAY_WIN"
        else:
            base_match["outcome"] = "DRAW"

        # 应用覆盖
        base_match.update(overrides)
        return base_match

    @classmethod
    def create_batch(cls, count: int, **overrides) -> List[Dict[str, Any]]:
        """创建批量比赛数据"""
        return [cls.create_match(**overrides) for _ in range(count)]


class SimplePredictionFactory:
    """简化的预测结果工厂"""

    @classmethod
    def create_prediction(cls, **overrides) -> Dict[str, Any]:
        """创建预测结果"""
        home_prob = round(random.uniform(0.2, 0.7), 3)
        draw_prob = round(random.uniform(0.1, 0.4), 3)
        remaining = max(0.1, 1.0 - home_prob - draw_prob)
        away_prob = round(remaining, 3)

        base_prediction = {
            "prediction_id": overrides.get("prediction_id", fake.uuid4()),
            "match_id": overrides.get("match_id", fake.uuid4()),
            "model_version": random.choice(["xgboost_v1", "xgboost_v2", "ensemble_v1"]),
            "prediction_time": datetime.now(timezone.utc).isoformat(),
            "home_win_prob": home_prob,
            "draw_prob": draw_prob,
            "away_win_prob": away_prob,
            "confidence": round(random.uniform(0.5, 0.95), 3),
            "features": {
                "elo_difference": random.randint(-300, 300),
                "home_form_avg": round(random.uniform(0.0, 2.0), 2),
                "away_form_avg": round(random.uniform(0.0, 2.0), 2),
                "venue_advantage": round(random.uniform(0.0, 0.2), 2),
            },
            "metadata": {
                "processing_time_ms": round(random.uniform(50.0, 500.0), 1),
                "cache_hit": random.choice([True, False]),
                "feature_count": random.randint(8, 15),
            },
        }

        # 确定预测类别
        if home_prob > max(draw_prob, away_prob):
            base_prediction["predicted_class"] = "HOME_WIN"
        elif draw_prob > away_prob:
            base_prediction["predicted_class"] = "DRAW"
        else:
            base_prediction["predicted_class"] = "AWAY_WIN"

        # 应用覆盖
        base_prediction.update(overrides)
        return base_prediction

    @classmethod
    def create_batch(cls, count: int, **overrides) -> List[Dict[str, Any]]:
        """创建批量预测结果"""
        return [cls.create_prediction(**overrides) for _ in range(count)]


class EdgeCaseFactory:
    """边界情况测试数据工厂"""

    @classmethod
    def create_extreme_lo_match(cls) -> Dict[str, Any]:
        """创建极端Elo差异的比赛"""
        return SimpleMatchFactory.create_match(
            home_team="Manchester City",
            away_team="Newly Promoted Team",
            **{
                "team_stats": {
                    "home": {"elo_rating": 2500},  # 极高Elo
                    "away": {"elo_rating": 1000},  # 极低Elo
                }
            },
        )

    @classmethod
    def create_perfect_form_match(cls) -> Dict[str, Any]:
        """创建完美状态的对比"""
        return SimpleMatchFactory.create_match(
            home_team="Team Perfect Form",
            away_team="Team Poor Form",
            **{
                "team_stats": {
                    "home": {"recent_form": [1, 1, 1, 1, 1]},  # 完美状态
                    "away": {"recent_form": [0, 0, 0, 0, 0]},  # 极差状态
                }
            },
        )

    @classmethod
    def create_high_scoring_match(cls) -> Dict[str, Any]:
        """创建高比分比赛"""
        return SimpleMatchFactory.create_match(home_score=random.randint(5, 8), away_score=random.randint(5, 8))


# 便捷函数
def create_test_scenarios() -> Dict[str, Any]:
    """创建常用测试场景"""
    return {
        "normal_match": SimpleMatchFactory.create_match(),
        "extreme_elo": EdgeCaseFactory.create_extreme_elo_match(),
        "perfect_form": EdgeCaseFactory.create_perfect_form_match(),
        "high_scoring": EdgeCaseFactory.create_high_scoring_match(),
        "batch_predictions": SimplePredictionFactory.create_batch(5),
        "batch_matches": SimpleMatchFactory.create_batch(3),
    }


if __name__ == "__main__":
    # 演示用法
    print("🏭 简化版测试数据工厂演示")

    # 创建单个比赛
    match = SimpleMatchFactory.create_match()
    print(f"✅ 生成比赛: {match['home_team']} vs {match['away_team']}")
    print(f"   比分: {match['home_score']}-{match['away_score']}")
    print(f"   结果: {match['outcome']}")
    print(f"   场馆: {match['venue']}")

    # 创建预测
    prediction = SimplePredictionFactory.create_prediction()
    print(f"\n✅ 生成预测: {prediction['predicted_class']}")
    print(
        f"   概率: 主胜 {prediction['home_win_prob']:.1%} | 平局 {prediction['draw_prob']:.1%} | 客胜 {prediction['away_win_prob']:.1%}"
    )
    print(f"   置信度: {prediction['confidence']:.1%}")
    print(f"   模型版本: {prediction['model_version']}")

    # 创建批量数据
    batch_matches = SimpleMatchFactory.create_batch(3)
    print(f"\n✅ 批量生成: {len(batch_matches)} 场比赛")

    # 边界情况
    extreme_match = EdgeCaseFactory.create_extreme_lo_match()
    elo_diff = extreme_match["team_stats"]["home"]["elo_rating"] - extreme_match["team_stats"]["away"]["elo_rating"]
    print(f"\n✅ 极端Elo差异: {elo_diff} 分")

    print("\n🎉 简化测试数据工厂工作正常！")
