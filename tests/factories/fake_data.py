"""
Faker工厂模块
Faker Factory Module

用于生成动态测试数据。
Used for generating dynamic test data.
"""

import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from faker import Faker
from pydantic import BaseModel

# 初始化Faker，支持中文
fake = Faker("zh_CN")
Faker.seed(42)  # 确保可重现的测试数据


class FootballDataFactory:
    """足球数据工厂"""

    @staticmethod
    def match() -> Dict:
        """生成比赛数据"""
        home_team = fake.company()
        away_team = fake.company()

        return {
            "match_id": fake.random_int(min=1000, max=9999),
            "home_team": home_team,
            "away_team": away_team,
            "home_score": fake.random_int(min=0, max=5),
            "away_score": fake.random_int(min=0, max=5),
            "match_date": fake.date_time_between(start_date="-30d", end_date="+30d"),
            "league": fake.company_suffix() + "联赛",
            "venue": f"{home_team}主场",
            "attendance": fake.random_int(min=1000, max=50000),
            "weather": random.choice(["晴天", "多云", "小雨", "阴天"]),
            "referee": fake.name(),
        }

    @staticmethod
    def team() -> Dict:
        """生成球队数据"""
        return {
            "team_id": fake.random_int(min=100, max=999),
            "name": fake.company(),
            "league": fake.company_suffix() + "联赛",
            "founded_year": fake.random_int(min=1900, max=2020),
            "home_city": fake.city(),
            "stadium": fake.company() + "体育场",
            "capacity": fake.random_int(min=5000, max=80000),
            "manager": fake.name(),
            "website": fake.url(),
            "created_at": fake.date_time_between(start_date="-2y", end_date="now"),
        }

    @staticmethod
    def player() -> Dict:
        """生成球员数据"""
        positions = ["前锋", "中场", "后卫", "门将"]
        return {
            "player_id": fake.random_int(min=1000, max=9999),
            "name": fake.name(),
            "age": fake.random_int(min=18, max=40),
            "position": random.choice(positions),
            "team": fake.company(),
            "nationality": fake.country(),
            "height": fake.random_int(min=160, max=200),
            "weight": fake.random_int(min=60, max=100),
            "market_value": fake.random_int(min=100000, max=100000000),
            "contract_until": fake.date_between(start_date="today", end_date="+5y"),
        }

    @staticmethod
    def prediction() -> Dict:
        """生成预测数据"""
        outcomes = ["home", "draw", "away"]
        probabilities = [fake.random.uniform(0.1, 0.8) for _ in range(3)]
        # 归一化概率，确保总和为1
        total = sum(probabilities)
        probabilities = [round(p / total, 2) for p in probabilities]
        # 修正舍入误差
        diff = 1.0 - sum(probabilities)
        probabilities[0] += diff

        return {
            "match_id": fake.random_int(min=1000, max=9999),
            "home_win_prob": round(probabilities[0], 2),
            "draw_prob": round(probabilities[1], 2),
            "away_win_prob": round(probabilities[2], 2),
            "predicted_outcome": outcomes[probabilities.index(max(probabilities))],
            "confidence": fake.random.uniform(0.5, 0.95),
            "model_version": f"v{fake.random_int(min=1, max=3)}.{fake.random_int(min=0, max=9)}",
            "predicted_at": fake.date_time_between(start_date="-7d", end_date="now"),
            "features": {
                "team_form": {
                    "home": fake.random_elements(elements=("W", "D", "L"), length=5),
                    "away": fake.random_elements(elements=("W", "D", "L"), length=5),
                },
                "head_to_head": {
                    "wins": fake.random_int(min=0, max=5),
                    "draws": fake.random_int(min=0, max=5),
                    "losses": fake.random_int(min=0, max=5),
                },
                "injuries": {
                    "home": fake.random_int(min=0, max=3),
                    "away": fake.random_int(min=0, max=3),
                },
            },
        }

    @staticmethod
    def user() -> Dict:
        """生成用户数据"""
        return {
            "user_id": fake.uuid4(),
            "username": fake.user_name(),
            "email": fake.email(),
            "full_name": fake.name(),
            "phone": fake.phone_number(),
            "date_of_birth": fake.date_time_between(start_date="-80y", end_date="-18y"),
            "country": fake.country(),
            "city": fake.city(),
            "is_active": fake.boolean(),
            "is_premium": fake.boolean(),
            "registration_date": fake.date_time_between(
                start_date="-2y", end_date="now"
            ),
            "last_login": fake.date_time_between(start_date="-30d", end_date="now"),
        }

    @staticmethod
    def batch_predictions(count: int = 10) -> List[Dict]:
        """生成批量预测数据"""
        return [FootballDataFactory.prediction() for _ in range(count)]

    @staticmethod
    def batch_matches(count: int = 10) -> List[Dict]:
        """生成批量比赛数据"""
        return [FootballDataFactory.match() for _ in range(count)]

    @staticmethod
    def batch_teams(count: int = 10) -> List[Dict]:
        """生成批量球队数据"""
        return [FootballDataFactory.team() for _ in range(count)]


class APIDataFactory:
    """API测试数据工厂"""

    @staticmethod
    def prediction_request() -> Dict:
        """生成预测请求数据"""
        return {
            "match_id": fake.random_int(min=1000, max=9999),
            "model_version": fake.random_element(
                elements=("default", "v1.0", "v2.0", "advanced")
            ),
            "include_details": fake.boolean(),
        }

    @staticmethod
    def batch_prediction_request(match_count: int = None) -> Dict:
        """生成批量预测请求数据"""
        if match_count is None:
            match_count = fake.random_int(min=1, max=20)

        return {
            "match_ids": [
                fake.random_int(min=1000, max=9999) for _ in range(match_count)
            ],
            "model_version": fake.random_element(elements=("default", "v1.0", "v2.0")),
        }

    @staticmethod
    def verification_request() -> Dict:
        """生成验证请求数据"""
        return {
            "match_id": fake.random_int(min=1000, max=9999),
            "actual_result": fake.random_element(elements=("home", "draw", "away")),
        }

    @staticmethod
    def health_check_response() -> Dict:
        """生成健康检查响应数据"""
        services = ["database", "redis", "prediction_engine", "cache", "kafka"]
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "service": "football-prediction-api",
            "version": "1.0.0",
            "checks": {
                service: {
                    "status": fake.random_element(
                        elements=("healthy", "degraded", "unhealthy")
                    ),
                    "response_time": fake.random_int(min=10, max=500),
                    "last_check": datetime.utcnow().isoformat(),
                }
                for service in services
            },
        }


# 便捷函数
def create_fake_match() -> Dict:
    """创建假比赛数据"""
    return FootballDataFactory.match()


def create_fake_prediction() -> Dict:
    """创建假预测数据"""
    return FootballDataFactory.prediction()


def create_fake_user() -> Dict:
    """创建假用户数据"""
    return FootballDataFactory.user()


def create_batch_fake_data(data_type: str, count: int = 10) -> List[Dict]:
    """创建批量假数据"""
    factories = {
        "matches": FootballDataFactory.batch_matches,
        "predictions": FootballDataFactory.batch_predictions,
        "teams": FootballDataFactory.batch_teams,
    }

    if data_type not in factories:
        raise ValueError(f"Unknown data type: {data_type}")

    return factories[data_type](count)
