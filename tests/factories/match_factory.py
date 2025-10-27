"""
比赛工厂 - 用于测试数据创建
"""

import random
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from .base import BaseFactory, DataFactoryMixin, TimestampMixin


class MatchFactory(BaseFactory, DataFactoryMixin, TimestampMixin):
    """比赛测试数据工厂"""

    # 比赛状态
    MATCH_STATUSES = ["scheduled", "live", "completed", "postponed", "cancelled"]

    # 比赛结果
    MATCH_RESULTS = ["home_win", "away_win", "draw"]

    @classmethod
    def create(cls, **kwargs) -> Dict[str, Any]:
        """创建单个比赛实例"""
        default_data = {
            "id": cls.generate_id(),
            "home_team_id": kwargs.get("home_team_id", cls.generate_id()),
            "away_team_id": kwargs.get("away_team_id", cls.generate_id()),
            "league_id": kwargs.get("league_id", cls.generate_id()),
            "match_date": cls._generate_match_date(),
            "status": kwargs.get("status", random.choice(cls.MATCH_STATUSES)),
            "home_score": kwargs.get("home_score", random.randint(0, 5)),
            "away_score": kwargs.get("away_score", random.randint(0, 5)),
            "venue": kwargs.get("venue", f"球场_{random.randint(1, 100)}"),
            "attendance": random.randint(1000, 100000),
            "referee": f"裁判_{random.randint(1, 100)}",
            "weather": random.choice(["晴", "雨", "雪", "多云"]),
            "created_at": cls.generate_timestamp(),
            "updated_at": cls.generate_timestamp(),
            "match_duration": random.randint(90, 120),  # 分钟
            "home_team_formation": random.choice(["4-4-2", "4-3-3", "3-5-2", "5-3-2"]),
            "away_team_formation": random.choice(["4-4-2", "4-3-3", "3-5-2", "5-3-2"]),
            "home_possession": round(random.uniform(30, 70), 1),
            "away_possession": round(random.uniform(30, 70), 1),
            "home_shots": random.randint(5, 25),
            "away_shots": random.randint(5, 25),
            "home_shots_on_target": random.randint(2, 15),
            "away_shots_on_target": random.randint(2, 15),
            "home_corners": random.randint(2, 12),
            "away_corners": random.randint(2, 12),
            "home_fouls": random.randint(5, 20),
            "away_fouls": random.randint(5, 20),
            "home_yellow_cards": random.randint(0, 5),
            "away_yellow_cards": random.randint(0, 5),
            "home_red_cards": random.randint(0, 2),
            "away_red_cards": random.randint(0, 2),
        }

        # 确保控球率总和为100
        total_possession = (
            default_data["home_possession"] + default_data["away_possession"]
        )
        if total_possession != 100:
            default_data["home_possession"] = round(
                default_data["home_possession"] / total_possession * 100, 1
            )
            default_data["away_possession"] = 100 - default_data["home_possession"]

        # 如果比赛已完成，确定结果
        if default_data["status"] == "completed":
            if default_data["home_score"] > default_data["away_score"]:
                default_data["result"] = "home_win"
            elif default_data["away_score"] > default_data["home_score"]:
                default_data["result"] = "away_win"
            else:
                default_data["result"] = "draw"
        else:
            default_data["result"] = None

        # 合并用户提供的参数
        default_data.update(kwargs)
        return cls.with_timestamps(**default_data)

    @classmethod
    def create_batch(cls, count: int, **kwargs) -> List[Dict[str, Any]]:
        """批量创建比赛实例"""
        matches = []
        for i in range(count):
            match_data = cls.create(**kwargs)
            matches.append(match_data)
        return matches

    @classmethod
    def create_completed(cls, **kwargs) -> Dict[str, Any]:
        """创建已完成的比赛"""
        home_score = kwargs.get("home_score", random.randint(0, 5))
        away_score = kwargs.get("away_score", random.randint(0, 5))

        return cls.create(
            status="completed", home_score=home_score, away_score=away_score, **kwargs
        )

    @classmethod
    def create_scheduled(cls, **kwargs) -> Dict[str, Any]:
        """创建计划中的比赛"""
        future_date = datetime.now(timezone.utc) + timedelta(days=random.randint(1, 30))
        return cls.create(
            match_date=future_date,
            status="scheduled",
            home_score=0,
            away_score=0,
            **kwargs,
        )

    @classmethod
    def create_live(cls, **kwargs) -> Dict[str, Any]:
        """创建进行中的比赛"""
        return cls.create(
            status="live",
            match_date=datetime.now(timezone.utc)
            - timedelta(minutes=random.randint(1, 89)),
            **kwargs,
        )

    @classmethod
    def create_for_teams(
        cls, home_team_id: int, away_team_id: int, **kwargs
    ) -> Dict[str, Any]:
        """为特定球队创建比赛"""
        return cls.create(
            home_team_id=home_team_id, away_team_id=away_team_id, **kwargs
        )

    @classmethod
    def create_high_scoring(cls, **kwargs) -> Dict[str, Any]:
        """创建高比分比赛"""
        return cls.create(
            home_score=random.randint(3, 8),
            away_score=random.randint(3, 8),
            total_goals=random.randint(6, 16),
            **kwargs,
        )

    @classmethod
    def create_low_scoring(cls, **kwargs) -> Dict[str, Any]:
        """创建低比分比赛"""
        return cls.create(
            home_score=random.randint(0, 2),
            away_score=random.randint(0, 2),
            total_goals=random.randint(0, 4),
            **kwargs,
        )

    @classmethod
    def create_draw(cls, **kwargs) -> Dict[str, Any]:
        """创建平局比赛"""
        score = random.randint(0, 3)
        return cls.create_completed(home_score=score, away_score=score, **kwargs)

    @classmethod
    def create_home_win(cls, **kwargs) -> Dict[str, Any]:
        """创建主队获胜比赛"""
        home_score = random.randint(1, 5)
        away_score = random.randint(0, home_score - 1)
        return cls.create_completed(
            home_score=home_score, away_score=away_score, **kwargs
        )

    @classmethod
    def create_away_win(cls, **kwargs) -> Dict[str, Any]:
        """创建客队获胜比赛"""
        away_score = random.randint(1, 5)
        home_score = random.randint(0, away_score - 1)
        return cls.create_completed(
            home_score=home_score, away_score=away_score, **kwargs
        )

    @classmethod
    def _generate_match_date(cls) -> datetime:
        """生成比赛日期"""
        days_offset = random.randint(-30, 30)
        return datetime.now(timezone.utc) + timedelta(days=days_offset)


class DerbyMatchFactory(MatchFactory):
    """德比比赛工厂"""

    DERBY_NAMES = [
        "国家德比",
        "米兰德比",
        "伦敦德比",
        "曼彻斯特德比",
        "西班牙德比",
        "德国德比",
        "法国德比",
        "意大利德比",
    ]

    @classmethod
    def create(cls, **kwargs) -> Dict[str, Any]:
        """创建德比比赛"""
        match = super().create(**kwargs)

        # 添加德比特有字段
        match.update(
            {
                "is_derby": True,
                "derby_name": random.choice(cls.DERBY_NAMES),
                "rivalry_intensity": random.randint(7, 10),
                "media_attention": random.choice(["high", "very_high", "global"]),
                "ticket_price_multiplier": round(random.uniform(1.5, 3.0), 1),
                "security_level": "high",
            }
        )

        # 德比比赛通常更激烈
        match.update(
            {
                "home_fouls": random.randint(10, 25),
                "away_fouls": random.randint(10, 25),
                "home_yellow_cards": random.randint(2, 6),
                "away_yellow_cards": random.randint(2, 6),
                "home_red_cards": random.randint(0, 3),
                "away_red_cards": random.randint(0, 3),
            }
        )

        return match


class CupMatchFactory(MatchFactory):
    """杯赛比赛工厂"""

    @classmethod
    def create(cls, **kwargs) -> Dict[str, Any]:
        """创建杯赛比赛"""
        match = super().create(**kwargs)

        # 添加杯赛特有字段
        match.update(
            {
                "is_cup_match": True,
                "cup_round": kwargs.get(
                    "cup_round",
                    random.choice(
                        [
                            "first_round",
                            "second_round",
                            "quarter_final",
                            "semi_final",
                            "final",
                        ]
                    ),
                ),
                "two_legged_tie": kwargs.get(
                    "two_legged_tie", random.choice([True, False])
                ),
                "away_goals_rule": kwargs.get("away_goals_rule", True),
                "extra_time_possible": kwargs.get("extra_goals_rule", True),
                "penalties_possible": kwargs.get("penalties_possible", True),
            }
        )

        return match
