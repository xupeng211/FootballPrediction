"""
球队工厂 - 用于测试数据创建
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import random

from .base import BaseFactory, DataFactoryMixin, TimestampMixin


class TeamFactory(BaseFactory, DataFactoryMixin, TimestampMixin):
    """球队测试数据工厂"""

    # 示例球队名称池
    TEAM_NAMES = [
        "皇家马德里",
        "巴塞罗那",
        "曼彻斯特联",
        "利物浦",
        "拜仁慕尼黑",
        "巴黎圣日耳曼",
        "尤文图斯",
        "AC米兰",
        "国际米兰",
        "切尔西",
        "曼城",
        "阿森纳",
        "热刺",
        "多特蒙德",
        "马德里竞技",
        "那不勒斯",
        "罗马",
        "拉齐奥",
        "本菲卡",
        "波尔图",
    ]

    # 示例城市
    CITIES = [
        "马德里",
        "巴塞罗那",
        "曼彻斯特",
        "利物浦",
        "慕尼黑",
        "巴黎",
        "都灵",
        "米兰",
        "罗马",
        "伦敦",
        "多特蒙德",
        "里斯本",
        "波尔图",
        "那不勒斯",
        "本菲卡",
    ]

    @classmethod
    def create(cls, **kwargs) -> Dict[str, Any]:
        """创建单个球队实例"""
        default_data = {
            "id": cls.generate_id(),
            "name": random.choice(cls.TEAM_NAMES),
            "city": random.choice(cls.CITIES),
            "country": "西班牙",  # 默认国家
            "founded_year": random.randint(1880, 2020),
            "stadium": f"{random.choice(cls.CITIES)}球场",
            "capacity": random.randint(20000, 100000),
            "league_id": kwargs.get("league_id", cls.generate_id()),
            "created_at": cls.generate_timestamp(),
            "updated_at": cls.generate_timestamp(),
            "is_active": True,
            "ranking": random.randint(1, 100),
            "points": random.randint(0, 100),
        }

        # 合并用户提供的参数
        default_data.update(kwargs)
        return cls.with_timestamps(**default_data)

    @classmethod
    def create_batch(cls, count: int, **kwargs) -> List[Dict[str, Any]]:
        """批量创建球队实例"""
        teams = []
        for i in range(count):
            team_data = cls.create(**kwargs)
            # 如果没有指定名称，添加序号避免重复
            if "name" not in kwargs:
                team_data["name"] = f"{team_data['name']}_{i + 1}"
            teams.append(team_data)
        return teams

    @classmethod
    def create_with_league(cls, league_id: int, **kwargs) -> Dict[str, Any]:
        """创建属于特定联赛的球队"""
        return cls.create(league_id=league_id, **kwargs)

    @classmethod
    def create_top_team(cls, **kwargs) -> Dict[str, Any]:
        """创建顶级球队"""
        top_names = ["皇家马德里", "巴塞罗那", "曼彻斯特联", "利物浦", "拜仁慕尼黑"]
        return cls.create(
            name=random.choice(top_names),
            ranking=random.randint(1, 10),
            points=random.randint(80, 100),
            capacity=random.randint(60000, 100000),
            **kwargs,
        )

    @classmethod
    def create_bottom_team(cls, **kwargs) -> Dict[str, Any]:
        """创建底层球队"""
        return cls.create(
            ranking=random.randint(50, 100),
            points=random.randint(0, 30),
            capacity=random.randint(20000, 40000),
            **kwargs,
        )


class ChineseTeamFactory(TeamFactory):
    """中国球队工厂"""

    CHINESE_TEAM_NAMES = [
        "北京国安",
        "上海海港",
        "广州恒大",
        "山东泰山",
        "大连人",
        "天津津门虎",
        "河南嵩山龙门",
        "长春亚泰",
        "河北队",
        "沧州雄狮",
        "武汉三镇",
        "梅州客家",
        "成都蓉城",
        "青岛海牛",
        "南通支云",
    ]

    CHINESE_CITIES = [
        "北京",
        "上海",
        "广州",
        "深圳",
        "大连",
        "天津",
        "郑州",
        "长春",
        "石家庄",
        "沧州",
        "武汉",
        "梅州",
        "成都",
        "青岛",
        "南通",
    ]

    @classmethod
    def create(cls, **kwargs) -> Dict[str, Any]:
        """创建中国球队"""
        default_data = {
            "id": cls.generate_id(),
            "name": random.choice(cls.CHINESE_TEAM_NAMES),
            "city": random.choice(cls.CHINESE_CITIES),
            "country": "中国",
            "founded_year": random.randint(1990, 2020),
            "stadium": f"{random.choice(cls.CHINESE_CITIES)}体育场",
            "capacity": random.randint(15000, 80000),
            "league_id": kwargs.get("league_id", 1),  # 中超联赛ID
            "created_at": cls.generate_timestamp(),
            "updated_at": cls.generate_timestamp(),
            "is_active": True,
            "ranking": random.randint(1, 16),  # 中超16支球队
            "points": random.randint(0, 60),
        }

        default_data.update(kwargs)
        return cls.with_timestamps(**default_data)


class HistoricTeamFactory(TeamFactory):
    """历史球队工厂"""

    HISTORIC_TEAM_NAMES = [
        "AC米兰 (1980s)",
        "皇家马德里 (1950s)",
        "巴塞罗那 (1990s)",
        "曼联 (1960s)",
        "利物浦 (1970s)",
        "拜仁慕尼黑 (1970s)",
        "阿贾克斯 (1970s)",
        "国际米兰 (1960s)",
        "尤文图斯 (1980s)",
        "凯尔特人 (1960s)",
        "本菲卡 (1960s)",
        "波尔图 (1980s)",
    ]

    @classmethod
    def create(cls, **kwargs) -> Dict[str, Any]:
        """创建历史球队"""
        historic_year = random.randint(1950, 2000)
        default_data = {
            "id": cls.generate_id(),
            "name": random.choice(cls.HISTORIC_TEAM_NAMES),
            "city": random.choice(cls.CITIES),
            "country": "西班牙",  # 默认国家
            "founded_year": historic_year - random.randint(20, 100),
            "stadium": f"{random.choice(cls.CITIES)}历史球场",
            "capacity": random.randint(10000, 80000),
            "league_id": kwargs.get("league_id", cls.generate_id()),
            "created_at": cls.generate_timestamp(),
            "updated_at": cls.generate_timestamp(),
            "is_active": False,  # 历史球队通常不活跃
            "ranking": random.randint(1, 100),
            "points": random.randint(0, 100),
            "historic_period": f"{historic_year}s",  # 历史时期
        }

        default_data.update(kwargs)
        return cls.with_timestamps(**default_data)
