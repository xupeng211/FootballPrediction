from typing import List
from typing import Dict
from typing import Any
"""
联赛工厂 - 用于测试数据创建
"""

import random

from .base import BaseFactory, DataFactoryMixin, TimestampMixin


class LeagueFactory(BaseFactory, DataFactoryMixin, TimestampMixin):
    """联赛测试数据工厂"""

    # 联赛名称池
    LEAGUE_NAMES = [
        "西甲",
        "英超",
        "意甲",
        "德甲",
        "法甲",
        "中超",
        "日职联",
        "韩K联",
        "荷甲",
        "葡超",
        "俄超",
        "土超",
        "比甲",
        "苏超",
        "奥甲",
    ]

    # 国家对应关系
    LEAGUE_COUNTRIES = {
        "西甲": "西班牙",
        "英超": "英格兰",
        "意甲": "意大利",
        "德甲": "德国",
        "法甲": "法国",
        "中超": "中国",
        "日职联": "日本",
        "韩K联": "韩国",
        "荷甲": "荷兰",
        "葡超": "葡萄牙",
        "俄超": "俄罗斯",
        "土超": "土耳其",
        "比甲": "比利时",
        "苏超": "苏格兰",
        "奥甲": "奥地利",
    }

    @classmethod
    def create(cls, **kwargs) -> Dict[str, Any]:
        """创建单个联赛实例"""
        name = kwargs.get("name", random.choice(cls.LEAGUE_NAMES))
        country = kwargs.get("country", cls.LEAGUE_COUNTRIES.get(name, "未知"))

        default_data = {
            "id": cls.generate_id(),
            "name": name,
            "country": country,
            "founded_year": random.randint(1880, 2000),
            "season_start": random.randint(7, 9),  # 月份
            "season_end": random.randint(4, 6),  # 月份
            "teams_count": random.randint(16, 24),
            "matches_per_team": random.randint(30, 40),
            "created_at": cls.generate_timestamp(),
            "updated_at": cls.generate_timestamp(),
            "is_active": True,
            "level": random.randint(1, 5),  # 联赛级别
            "reputation": random.randint(1, 100),
            "total_teams": random.randint(16, 24),
            "current_matchday": random.randint(1, 38),
            "total_matchdays": random.randint(30, 40),
        }

        # 合并用户提供的参数
        default_data.update(kwargs)
        return cls.with_timestamps(**default_data)

    @classmethod
    def create_batch(cls, count: int, **kwargs) -> List[Dict[str, Any]]:
        """批量创建联赛实例"""
        leagues = []
        available_names = cls.LEAGUE_NAMES.copy()

        for i in range(count):
            if available_names and "name" not in kwargs:
                name = random.choice(available_names)
                available_names.remove(name)
            else:
                name = kwargs.get("name", f"联赛_{i + 1}")

            league_data = cls.create(name=name, **kwargs)
            leagues.append(league_data)

        return leagues

    @classmethod
    def create_top_league(cls, **kwargs) -> Dict[str, Any]:
        """创建顶级联赛"""
        top_names = ["西甲", "英超", "意甲", "德甲", "法甲"]
        return cls.create(
            name=random.choice(top_names),
            level=1,
            reputation=random.randint(90, 100),
            teams_count=random.randint(18, 20),
            **kwargs,
        )

    @classmethod
    def create_minor_league(cls, **kwargs) -> Dict[str, Any]:
        """创建次级联赛"""
        return cls.create(
            level=random.randint(2, 5),
            reputation=random.randint(30, 70),
            teams_count=random.randint(16, 22),
            **kwargs,
        )

    @classmethod
    def create_with_teams(cls, teams_count: int, **kwargs) -> Dict[str, Any]:
        """创建指定球队数量的联赛"""
        return cls.create(
            teams_count=teams_count,
            total_teams=teams_count,
            matches_per_team=(teams_count - 1) * 2,  # 双循环
            total_matchdays=(teams_count - 1) * 2,
            **kwargs,
        )

    @classmethod
    def create_chinese_league(cls, **kwargs) -> Dict[str, Any]:
        """创建中国联赛"""
        return cls.create(
            name="中超",
            country="中国",
            teams_count=16,
            matches_per_team=30,
            total_matchdays=30,
            season_start=3,
            season_end=11,
            **kwargs,
        )

    @classmethod
    def create_european_league(cls, **kwargs) -> Dict[str, Any]:
        """创建欧洲联赛"""
        name = random.choice(["西甲", "英超", "意甲", "德甲", "法甲"])
        country = cls.LEAGUE_COUNTRIES[name]

        return cls.create(
            name=name,
            country=country,
            teams_count=random.randint(18, 20),
            matches_per_team=random.randint(34, 38),
            total_matchdays=random.randint(34, 38),
            season_start=random.randint(8, 9),
            season_end=random.randint(4, 6),
            level=1,
            reputation=random.randint(85, 100),
            **kwargs,
        )


class EuropeanLeagueFactory(LeagueFactory):
    """欧洲联赛工厂"""

    EUROPEAN_LEAGUES = [
        ("西甲", "西班牙"),
        ("英超", "英格兰"),
        ("意甲", "意大利"),
        ("德甲", "德国"),
        ("法甲", "法国"),
        ("荷甲", "荷兰"),
        ("葡超", "葡萄牙"),
        ("比甲", "比利时"),
        ("苏超", "苏格兰"),
        ("俄超", "俄罗斯"),
    ]

    @classmethod
    def create(cls, **kwargs) -> Dict[str, Any]:
        """创建欧洲联赛"""
        if "name" not in kwargs:
            name, country = random.choice(cls.EUROPEAN_LEAGUES)
            kwargs["name"] = name
            kwargs["country"] = country

        return super().create(level=1, reputation=random.randint(80, 100), **kwargs)


class AsianLeagueFactory(LeagueFactory):
    """亚洲联赛工厂"""

    ASIAN_LEAGUES = [
        ("中超", "中国"),
        ("日职联", "日本"),
        ("韩K联", "韩国"),
        ("泰超", "泰国"),
        ("澳超", "澳大利亚"),
        ("沙特联", "沙特阿拉伯"),
    ]

    @classmethod
    def create(cls, **kwargs) -> Dict[str, Any]:
        """创建亚洲联赛"""
        if "name" not in kwargs:
            name, country = random.choice(cls.ASIAN_LEAGUES)
            kwargs["name"] = name
            kwargs["country"] = country

        return super().create(
            level=random.randint(1, 3),
            reputation=random.randint(50, 80),
            season_start=random.randint(2, 6),  # 亚洲联赛多在春季开始
            season_end=random.randint(10, 12),
            **kwargs,
        )


class InternationalLeagueFactory(LeagueFactory):
    """国际联赛工厂"""

    INTERNATIONAL_COMPETITIONS = [
        ("欧洲冠军联赛", "欧洲"),
        ("欧罗巴联赛", "欧洲"),
        ("欧洲协会联赛", "欧洲"),
        ("亚冠联赛", "亚洲"),
        ("世俱杯", "世界"),
        ("欧洲杯", "欧洲"),
        ("亚洲杯", "亚洲"),
        ("世界杯", "世界"),
    ]

    @classmethod
    def create(cls, **kwargs) -> Dict[str, Any]:
        """创建国际联赛/杯赛"""
        if "name" not in kwargs:
            name, continent = random.choice(cls.INTERNATIONAL_COMPETITIONS)
            kwargs["name"] = name
            kwargs["country"] = continent

        return super().create(
            teams_count=random.randint(8, 32),  # 杯赛球队数量变化较大
            is_knockout=random.choice([True, False]),  # 是否淘汰制
            is_international=True,
            level=0,  # 国际级别最高
            reputation=random.randint(90, 100),
            **kwargs,
        )
