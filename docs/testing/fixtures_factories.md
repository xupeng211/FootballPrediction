# 测试数据工厂

本文档详细说明足球预测系统中的测试数据工厂和Mock策略，包括factory-boy使用、测试数据管理和Mock配置。

## 📋 目录

- [测试数据工厂概述](#测试数据工厂概述)
  - [设计原则](#设计原则)
  - [目录结构](#目录结构)
  - [最佳实践](#最佳实践)
- [Factory Boy使用](#factory-boy-使用)
  - [基础配置](#基础配置)
  - [关系数据生成](#关系数据生成)
  - [批量数据生成](#批量数据生成)
- [Mock策略](#mock策略)
  - [外部服务Mock](#外部服务mock)
  - [异步Mock](#异步mock)
  - [条件Mock](#条件mock)
- [测试数据管理](#测试数据管理)
  - [数据隔离](#数据隔离)
  - [数据清理](#数据清理)
  - **数据验证**
- [具体实现示例](#具体实现示例)
  - [队伍数据工厂](#队伍数据工厂)
  - [比赛数据工厂](#比赛数据工厂)
  - [预测数据工厂](#预测数据工厂)
- [性能优化](#性能优化)
  - [批量插入优化](#批量插入优化)
  - [缓存策略](#缓存策略)
  - **并行生成**

---

## 测试数据工厂概述

### 设计原则

足球预测系统的测试数据工厂遵循以下设计原则：

1. **真实性**: 生成的数据应该尽可能接近真实数据
2. **一致性**: 确保数据之间的关系和约束得到维护
3. **可重复性**: 每次运行测试应该生成可预测的数据
4. **独立性**: 每个测试应该是独立的，不依赖其他测试的数据
5. **性能**: 数据生成应该快速，不影响测试执行速度

### 目录结构

```
tests/
├── factories/                    # 数据工厂
│   ├── __init__.py
│   ├── base_factory.py          # 基础工厂类
│   ├── team_factory.py          # 队伍工厂
│   ├── match_factory.py         # 比赛工厂
│   ├── prediction_factory.py    # 预测工厂
│   ├── player_factory.py        # 球员工厂
│   ├── league_factory.py        # 联赛工厂
│   └── data_factory.py          # 通用数据工厂
├── fixtures/                    # 测试固件
│   ├── __init__.py
│   ├── database.py             # 数据库固件
│   ├── redis.py                # Redis固件
│   ├── mlflow.py               # MLflow固件
│   └── external_services.py     # 外部服务固件
├── mock_helpers/               # Mock帮助类
│   ├── __init__.py
│   ├── mock_database.py        # 数据库Mock
│   ├── mock_cache.py           # 缓存Mock
│   ├── mock_external_apis.py   # 外部API Mock
│   └── mock_ml_services.py     # 机器学习服务Mock
└── utils/                      # 测试工具
    ├── data_generator.py       # 数据生成器
    ├── test_data_manager.py    # 测试数据管理器
    └── performance_utils.py    # 性能测试工具
```

### 最佳实践

1. **使用Faker生成真实数据**: 利用Faker库生成接近真实的数据
2. **合理设置默认值**: 为所有字段设置合理的默认值
3. **处理数据关系**: 正确处理表之间的外键关系
4. **数据验证**: 在工厂中添加基本的数据验证逻辑
5. **性能考虑**: 对于大量数据生成，使用批量插入

---

## Factory Boy使用

### 基础配置

```python
# tests/factories/base_factory.py
import factory
from factory.alchemy import SQLAlchemyModelFactory
from factory.fuzzy import FuzzyText, FuzzyInteger, FuzzyFloat, FuzzyDate
from factory import Faker, Sequence, lazy_attribute
from datetime import datetime, timedelta
import random
import uuid

class BaseSQLAlchemyFactory(SQLAlchemyModelFactory):
    """基础SQLAlchemy工厂类"""

    class Meta:
        abstract = True
        sqlalchemy_session_persistence = "flush"  # 使用flush而不是commit

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """创建对象时自动处理数据库会话"""
        session = cls._meta.sqlalchemy_session
        if session is None:
            raise RuntimeError("No database session available")

        # 创建对象
        obj = model_class(*args, **kwargs)
        session.add(obj)
        session.flush()  # 确保对象有ID

        return obj

    @classmethod
    def create_batch(cls, size, **kwargs):
        """批量创建对象"""
        session = cls._meta.sqlalchemy_session
        if session is None:
            raise RuntimeError("No database session available")

        objects = []
        for _ in range(size):
            obj = cls.build(**kwargs)
            session.add(obj)
            objects.append(obj)

        session.flush()
        return objects

class FuzzyDateTime(FuzzyDate):
    """模糊日期时间生成器"""

    def __init__(self, start_dt=None, end_dt=None, force_year=None, force_month=None, force_day=None):
        if start_dt is None:
            start_dt = datetime.now() - timedelta(days=365)
        if end_dt is None:
            end_dt = datetime.now() + timedelta(days=365)

        self.start_dt = start_dt
        self.end_dt = end_dt
        self.force_year = force_year
        self.force_month = force_month
        self.force_day = force_day
        super().__init__(start_dt.date(), end_dt.date())

    def fuzz(self):
        dt = super().fuzz()
        if self.force_year:
            dt = dt.replace(year=self.force_year)
        if self.force_month:
            dt = dt.replace(month=self.force_month)
        if self.force_day:
            dt = dt.replace(day=self.force_day)
        return datetime.combine(dt, datetime.min.time())

class FuzzyProbability(FuzzyFloat):
    """模糊概率生成器"""
    def __init__(self, low=0.0, high=1.0):
        super().__init__(low, high)

    def fuzz(self):
        value = super().fuzz()
        return round(value, 3)

class FuzzyPercentage(FuzzyFloat):
    """模糊百分比生成器"""
    def __init__(self, low=0.0, high=100.0):
        super().__init__(low, high)

    def fuzz(self):
        value = super().fuzz()
        return round(value, 2)

class FuzzyMoney(FuzzyFloat):
    """模糊金额生成器"""
    def __init__(self, low=0.0, high=1000000.0):
        super().__init__(low, high)

    def fuzz(self):
        value = super().fuzz()
        return round(value, 2)

class SequenceGenerator:
    """序列生成器"""

    def __init__(self, prefix="", suffix="", start=1):
        self.prefix = prefix
        self.suffix = suffix
        self.counter = start

    def __call__(self):
        result = f"{self.prefix}{self.counter}{self.suffix}"
        self.counter += 1
        return result

class UniqueAttributeGenerator:
    """唯一属性生成器"""
    def __init__(self):
        self._used_values = set()

    def generate_unique_value(self, generator_func, max_attempts=100):
        """生成唯一值"""
        for _ in range(max_attempts):
            value = generator_func()
            if value not in self._used_values:
                self._used_values.add(value)
                return value
        raise ValueError("Failed to generate unique value after max attempts")

    def reset(self):
        """重置已使用的值"""
        self._used_values.clear()
```

### 关系数据生成

```python
# tests/factories/team_factory.py
import factory
from factory.alchemy import SQLAlchemyModelFactory
from factory import Faker, SubFactory, RelatedFactory, Iterator, lazy_attribute, post_generation
from datetime import datetime
import random

from src.database.models.team import Team
from src.database.models.stadium import Stadium
from src.database.models.coach import Coach
from .base_factory import BaseSQLAlchemyFactory, FuzzyInteger, FuzzyDate
from .stadium_factory import StadiumFactory
from .coach_factory import CoachFactory

class TeamFactory(BaseSQLAlchemyFactory):
    """队伍数据工厂"""

    class Meta:
        model = Team
        sqlalchemy_session_persistence = "flush"

    # 基本信息
    name = Faker("company")
    short_name = factory.LazyAttribute(lambda obj: obj.name[:3].upper() if len(obj.name) >= 3 else obj.name[:2].upper())
    tla = factory.LazyAttribute(lambda obj: obj.short_name[:3].upper())

    # 地理信息
    country = Faker("country")
    city = Faker("city")
    founded = FuzzyInteger(1880, 2020)

    # 竞技信息
    league = Faker("random_element", elements=[
        "Premier League", "Championship", "League One", "League Two",
        "La Liga", "Serie A", "Bundesliga", "Ligue 1"
    ])

    # 财务信息
    market_value = factory.LazyAttribute(lambda obj: random.randint(10000000, 1000000000))
    revenue = factory.LazyAttribute(lambda obj: int(obj.market_value * random.uniform(0.1, 0.5)))

    # 联系信息
    website = factory.LazyAttribute(lambda obj: f"https://{obj.name.lower().replace(' ', '')}.com")
    email = factory.LazyAttribute(lambda obj: f"contact@{obj.name.lower().replace(' ', '')}.com")
    phone = Faker("phone_number")

    # 统计信息
    matches_played = FuzzyInteger(0, 1000)
    wins = FuzzyInteger(0, 500)
    draws = FuzzyInteger(0, 300)
    losses = FuzzyInteger(0, 300)
    goals_for = FuzzyInteger(0, 2000)
    goals_against = FuzzyInteger(0, 2000)

    # 状态信息
    is_active = True
    created_at = FuzzyDate(datetime.now() - timedelta(days=365), datetime.now())
    updated_at = factory.LazyAttribute(lambda obj: obj.created_at)

    # 关系字段
    stadium = SubFactory(StadiumFactory)
    coach = SubFactory(CoachFactory)

    @post_generation
    def ensure_short_name_valid(obj, create, extracted, **kwargs):
        """确保短名称有效"""
        if len(obj.short_name) < 2:
            obj.short_name = obj.name[:2].upper()
        if len(obj.tla) < 2:
            obj.tla = obj.short_name[:3].upper()

    @post_generation
    def ensure_stats_consistency(obj, create, extracted, **kwargs):
        """确保统计数据一致性"""
        total_matches = obj.wins + obj.draws + obj.losses
        if total_matches > obj.matches_played:
            obj.matches_played = total_matches

    @post_generation
    def set_derived_fields(obj, create, extracted, **kwargs):
        """设置派生字段"""
        if obj.market_value < 1000000:  # 最小价值100万
            obj.market_value = random.randint(1000000, 10000000)
        if obj.revenue > obj.market_value * 2:  # 收入不应超过价值的2倍
            obj.revenue = int(obj.market_value * random.uniform(0.1, 0.5))

    @classmethod
    def create_premier_league_team(cls, **kwargs):
        """创建英超球队"""
        return cls(
            league="Premier League",
            market_value=random.randint(100000000, 1000000000),
            founded=random.randint(1880, 2000),
            **kwargs
        )

    @classmethod
    def create_championship_team(cls, **kwargs):
        """创建英冠球队"""
        return cls(
            league="Championship",
            market_value=random.randint(20000000, 200000000),
            founded=random.randint(1880, 2000),
            **kwargs
        )

    @classmethod
    def create_with_custom_stadium(cls, stadium_name, capacity, **kwargs):
        """创建带有自定义体育场的队伍"""
        stadium = StadiumFactory(name=stadium_name, capacity=capacity)
        return cls(stadium=stadium, **kwargs)

class HistoricalTeamFactory(TeamFactory):
    """历史队伍工厂（用于测试历史数据）"""

    class Meta:
        model = Team

    is_active = False
    founded = FuzzyInteger(1880, 1950)
    league = Faker("random_element", elements=[
        "First Division", "Second Division", "Non-league"
    ])

class InternationalTeamFactory(TeamFactory):
    """国家队工厂"""

    class Meta:
        model = Team

    country = Faker("country_code")  # 使用国家代码
    city = "National"
    league = "International"
    founded = FuzzyInteger(1860, 1950)

    @post_generation
    def set_international_attributes(obj, create, extracted, **kwargs):
        """设置国家队特有属性"""
        obj.short_name = obj.country
        obj.tla = obj.country[:3].upper()
        obj.market_value = random.randint(50000000, 1000000000)
        obj.revenue = 0  # 国家队通常没有收入
```

### 批量数据生成

```python
# tests/factories/data_factory.py
import factory
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
from typing import List, Dict, Any, Optional
from factory.alchemy import SQLAlchemyModelFactory

from .team_factory import TeamFactory
from .match_factory import MatchFactory
from .prediction_factory import PredictionFactory
from .player_factory import PlayerFactory
from .league_factory import LeagueFactory

class FootballDataGenerator:
    """足球数据生成器"""

    def __init__(self, session=None):
        self.session = session
        self.teams_cache = {}
        self.leagues_cache = {}

    def generate_league_data(self, num_leagues: int = 10) -> List[Dict[str, Any]]:
        """生成联赛数据"""
        leagues = []
        league_types = ["League", "Cup", "Tournament"]

        for i in range(num_leagues):
            league = {
                "id": i + 1,
                "name": f"{Faker('company')} {random.choice(['Premier', 'Championship', 'League'])}",
                "country": Faker("country"),
                "type": random.choice(league_types),
                "founded": random.randint(1880, 2020),
                "teams_count": random.randint(18, 24),
                "season_duration": random.randint(8, 12),  # 月份
                "current_season": f"{random.randint(2020, 2023)}/{random.randint(2021, 2024)}",
                "reputation": random.randint(1, 5),
                "prize_money": random.randint(1000000, 100000000),
                "created_at": datetime.now() - timedelta(days=random.randint(1, 365)),
                "updated_at": datetime.now()
            }
            leagues.append(league)

        return leagues

    def generate_team_batch(self, num_teams: int = 100, league_id: int = None) -> List[Dict[str, Any]]:
        """批量生成队伍数据"""
        teams = []
        countries = ["England", "Spain", "Germany", "Italy", "France", "Netherlands", "Portugal"]

        for i in range(num_teams):
            team_name = f"Team {i + 1}"
            team = {
                "id": i + 1,
                "name": team_name,
                "short_name": team_name[:3].upper(),
                "tla": team_name[:3].upper(),
                "country": random.choice(countries),
                "city": Faker("city"),
                "founded": random.randint(1880, 2020),
                "league_id": league_id,
                "market_value": random.randint(10000000, 1000000000),
                "revenue": random.randint(1000000, 500000000),
                "stadium_name": f"{team_name} Stadium",
                "stadium_capacity": random.randint(20000, 80000),
                "website": f"https://{team_name.lower().replace(' ', '')}.com",
                "is_active": True,
                "created_at": datetime.now() - timedelta(days=random.randint(1, 365)),
                "updated_at": datetime.now()
            }
            teams.append(team)

        return teams

    def generate_player_batch(self, num_players: int = 1000, team_ids: List[int] = None) -> List[Dict[str, Any]]:
        """批量生成球员数据"""
        players = []
        positions = ["Forward", "Midfielder", "Defender", "Goalkeeper"]
        nationalities = ["England", "Spain", "Germany", "Italy", "France", "Brazil", "Argentina"]

        if not team_ids:
            team_ids = list(range(1, 101))  # 假设有100个队伍

        for i in range(num_players):
            first_name = Faker("first_name")
            last_name = Faker("last_name")
            age = random.randint(18, 38)

            player = {
                "id": i + 1,
                "first_name": first_name,
                "last_name": last_name,
                "full_name": f"{first_name} {last_name}",
                "age": age,
                "position": random.choice(positions),
                "nationality": random.choice(nationalities),
                "team_id": random.choice(team_ids),
                "jersey_number": random.randint(1, 99),
                "height": random.randint(165, 200),
                "weight": random.randint(60, 100),
                "market_value": self._calculate_player_value(age, random.choice(positions)),
                "contract_until": datetime.now() + timedelta(days=random.randint(30, 1825)),  # 1个月到5年
                "weekly_salary": random.randint(10000, 500000),
                "goals_scored": random.randint(0, 200),
                "assists": random.randint(0, 100),
                "yellow_cards": random.randint(0, 50),
                "red_cards": random.randint(0, 10),
                "appearances": random.randint(0, 300),
                "created_at": datetime.now() - timedelta(days=random.randint(1, 365)),
                "updated_at": datetime.now()
            }
            players.append(player)

        return players

    def generate_match_schedule(self, num_seasons: int = 3, teams_per_league: int = 20) -> List[Dict[str, Any]]:
        """生成比赛赛程"""
        matches = []
        match_id = 1

        for season in range(num_seasons):
            season_start = datetime(2020 + season, 8, 1)
            season_end = datetime(2021 + season, 5, 31)

            # 为每个联赛生成比赛
            for league_id in range(1, 6):  # 5个联赛
                teams = list(range(1, teams_per_league + 1))

                # 生成主客场双循环赛程
                for home_team in teams:
                    for away_team in teams:
                        if home_team != away_team:
                            # 主场比赛
                            match_date = self._generate_match_date(season_start, season_end)
                            match = {
                                "id": match_id,
                                "home_team_id": home_team,
                                "away_team_id": away_team,
                                "league_id": league_id,
                                "season": f"{2020 + season}/{2021 + season}",
                                "match_date": match_date,
                                "status": "FINISHED" if match_date < datetime.now() else "SCHEDULED",
                                "venue_id": home_team,  # 简化处理
                                "created_at": match_date - timedelta(days=30),
                                "updated_at": match_date
                            }

                            # 如果比赛已完成，生成比分
                            if match["status"] == "FINISHED":
                                match["home_score"] = random.randint(0, 5)
                                match["away_score"] = random.randint(0, 5)
                                match["attendance"] = random.randint(10000, 80000)

                            matches.append(match)
                            match_id += 1

        return matches

    def generate_match_statistics(self, matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """生成比赛统计数据"""
        statistics = []

        for match in matches:
            if match["status"] == "FINISHED":
                # 主队统计
                home_stats = {
                    "match_id": match["id"],
                    "team_id": match["home_team_id"],
                    "possession": random.randint(30, 70),
                    "shots": random.randint(5, 25),
                    "shots_on_target": random.randint(2, 12),
                    "corners": random.randint(2, 12),
                    "fouls": random.randint(5, 20),
                    "yellow_cards": random.randint(0, 5),
                    "red_cards": random.randint(0, 2),
                    "offsides": random.randint(0, 8),
                    "pass_accuracy": random.randint(70, 95)
                }
                statistics.append(home_stats)

                # 客队统计
                away_stats = {
                    "match_id": match["id"],
                    "team_id": match["away_team_id"],
                    "possession": 100 - home_stats["possession"],
                    "shots": random.randint(5, 25),
                    "shots_on_target": random.randint(2, 12),
                    "corners": random.randint(2, 12),
                    "fouls": random.randint(5, 20),
                    "yellow_cards": random.randint(0, 5),
                    "red_cards": random.randint(0, 2),
                    "offsides": random.randint(0, 8),
                    "pass_accuracy": random.randint(70, 95)
                }
                statistics.append(away_stats)

        return statistics

    def generate_odds_data(self, matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """生成赔率数据"""
        odds = []
        bookmakers = ["Bet365", "William Hill", "Ladbrokes", "Paddy Power", "Betfair"]

        for match in matches:
            # 为每个比赛生成多个博彩公司的赔率
            for bookmaker in bookmakers:
                # 基础赔率
                home_win = random.uniform(1.5, 5.0)
                draw = random.uniform(2.5, 4.0)
                away_win = random.uniform(2.0, 6.0)

                # 确保赔率合理
                total_probability = 1/home_win + 1/draw + 1/away_win
                if total_probability > 1.1:  # 如果博彩公司利润过高
                    factor = total_probability / 1.05
                    home_win *= factor
                    draw *= factor
                    away_win *= factor

                odd = {
                    "match_id": match["id"],
                    "bookmaker": bookmaker,
                    "home_win": round(home_win, 2),
                    "draw": round(draw, 2),
                    "away_win": round(away_win, 2),
                    "timestamp": match["match_date"] - timedelta(days=random.randint(1, 7)),
                    "updated_at": datetime.now()
                }
                odds.append(odd)

        return odds

    def generate_training_data(self, num_samples: int = 10000) -> pd.DataFrame:
        """生成机器学习训练数据"""
        features = []
        labels = []

        for _ in range(num_samples):
            # 特征工程
            feature = {
                "home_form": random.uniform(0.0, 1.0),
                "away_form": random.uniform(0.0, 1.0),
                "home_goals_scored": random.randint(0, 5),
                "home_goals_conceded": random.randint(0, 5),
                "away_goals_scored": random.randint(0, 5),
                "away_goals_conceded": random.randint(0, 5),
                "home_league_position": random.randint(1, 20),
                "away_league_position": random.randint(1, 20),
                "head_to_head_wins": random.randint(0, 10),
                "head_to_head_draws": random.randint(0, 10),
                "head_to_head_losses": random.randint(0, 10),
                "home_team_strength": random.uniform(0.5, 1.0),
                "away_team_strength": random.uniform(0.5, 1.0),
                "home_fatigue": random.uniform(0.0, 1.0),
                "away_fatigue": random.uniform(0.0, 1.0),
                "home_motivation": random.uniform(0.5, 1.0),
                "away_motivation": random.uniform(0.5, 1.0)
            }
            features.append(feature)

            # 生成标签（比赛结果）
            home_strength = feature["home_team_strength"] + feature["home_form"] * 0.1
            away_strength = feature["away_team_strength"] + feature["away_form"] * 0.1

            if home_strength > away_strength * 1.1:
                result = "HOME_WIN"
            elif away_strength > home_strength * 1.1:
                result = "AWAY_WIN"
            else:
                result = "DRAW"

            labels.append(result)

        return pd.DataFrame(features), pd.Series(labels)

    def _calculate_player_value(self, age: int, position: str) -> int:
        """计算球员价值"""
        base_value = {
            "Forward": 50000000,
            "Midfielder": 40000000,
            "Defender": 30000000,
            "Goalkeeper": 25000000
        }.get(position, 30000000)

        # 年龄调整
        if 25 <= age <= 28:
            age_multiplier = 1.2
        elif 22 <= age <= 24 or 29 <= age <= 31:
            age_multiplier = 1.0
        elif 18 <= age <= 21:
            age_multiplier = 0.8
        else:
            age_multiplier = 0.6

        return int(base_value * age_multiplier * random.uniform(0.8, 1.2))

    def _generate_match_date(self, season_start: datetime, season_end: datetime) -> datetime:
        """生成比赛日期"""
        # 主要在周末比赛
        weekend_days = [5, 6]  # 周六、周日
        random_days = random.randint(1, 90)  # 赛季内随机天数

        match_date = season_start + timedelta(days=random_days)

        # 调整到最近的周末
        while match_date.weekday() not in weekend_days and match_date < season_end:
            match_date += timedelta(days=1)

        return match_date

    def generate_complete_dataset(self) -> Dict[str, Any]:
        """生成完整的测试数据集"""
        print("Generating complete test dataset...")

        # 生成联赛数据
        leagues = self.generate_league_data(5)
        print(f"Generated {len(leagues)} leagues")

        # 生成队伍数据
        teams = self.generate_team_batch(100)
        print(f"Generated {len(teams)} teams")

        # 生成球员数据
        team_ids = [team["id"] for team in teams]
        players = self.generate_player_batch(1000, team_ids)
        print(f"Generated {len(players)} players")

        # 生成比赛赛程
        matches = self.generate_match_schedule(2, 20)
        print(f"Generated {len(matches)} matches")

        # 生成比赛统计
        statistics = self.generate_match_statistics(matches)
        print(f"Generated {len(statistics)} match statistics")

        # 生成赔率数据
        odds = self.generate_odds_data(matches)
        print(f"Generated {len(odds)} odds records")

        # 生成训练数据
        features, labels = self.generate_training_data(5000)
        print(f"Generated {len(features)} training samples")

        return {
            "leagues": leagues,
            "teams": teams,
            "players": players,
            "matches": matches,
            "statistics": statistics,
            "odds": odds,
            "training_features": features,
            "training_labels": labels
        }

# 批量数据工厂
class BatchDataFactory:
    """批量数据工厂"""

    def __init__(self, session):
        self.session = session
        self.generator = FootballDataGenerator(session)

    def create_batch_teams(self, num_teams: int = 100) -> List[Team]:
        """批量创建队伍"""
        teams_data = self.generator.generate_team_batch(num_teams)
        teams = []

        for team_data in teams_data:
            team = TeamFactory(**team_data)
            teams.append(team)

        self.session.flush()
        return teams

    def create_batch_players(self, num_players: int = 1000, team_ids: List[int] = None) -> List[Player]:
        """批量创建球员"""
        if not team_ids:
            team_ids = [team.id for team in self.session.query(Team).all()]

        players_data = self.generator.generate_player_batch(num_players, team_ids)
        players = []

        for player_data in players_data:
            player = PlayerFactory(**player_data)
            players.append(player)

        self.session.flush()
        return players

    def create_complete_test_data(self):
        """创建完整的测试数据"""
        dataset = self.generator.generate_complete_dataset()

        # 这里可以将数据保存到数据库或文件
        return dataset
```

---

## Mock策略

### 外部服务Mock

```python
# tests/mock_helpers/mock_external_services.py
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any, List, Optional, Union
import asyncio
from datetime import datetime
import aiohttp
import redis.asyncio as redis
from src.services.external_apis import FootballAPIClient, OddsAPIClient
from src.services.ml_service import MLServiceClient
from src.services.notification_service import NotificationService

class ExternalServiceMock:
    """外部服务Mock基类"""

    def __init__(self):
        self.call_history = []
        self.responses = {}
        self.exceptions = {}
        self.delays = {}

    def add_response(self, method: str, response: Any):
        """添加响应"""
        self.responses[method] = response

    def add_exception(self, method: str, exception: Exception):
        """添加异常"""
        self.exceptions[method] = exception

    def add_delay(self, method: str, delay: float):
        """添加延迟"""
        self.delays[method] = delay

    def record_call(self, method: str, args: tuple, kwargs: dict):
        """记录调用"""
        self.call_history.append({
            'method': method,
            'args': args,
            'kwargs': kwargs,
            'timestamp': datetime.now()
        })

    def get_call_count(self, method: str = None) -> int:
        """获取调用次数"""
        if method:
            return len([call for call in self.call_history if call['method'] == method])
        return len(self.call_history)

    def reset(self):
        """重置Mock状态"""
        self.call_history = []
        self.responses = {}
        self.exceptions = {}
        self.delays = {}

class FootballAPIClientMock(ExternalServiceMock):
    """足球API客户端Mock"""

    def __init__(self):
        super().__init__()
        self._setup_default_responses()

    def _setup_default_responses(self):
        """设置默认响应"""
        # 联赛列表
        self.add_response('get_competitions', {
            "count": 5,
            "competitions": [
                {"id": 39, "name": "Premier League", "code": "PL"},
                {"id": 40, "name": "Championship", "code": "ELC"},
                {"id": 41, "name": "League One", "code": "L1"},
                {"id": 42, "name": "League Two", "code": "L2"},
                {"id": 43, "name": "National League", "code": "NL"}
            ]
        })

        # 比赛列表
        self.add_response('get_matches', {
            "count": 10,
            "matches": [
                {
                    "id": 1,
                    "home_team": {"id": 101, "name": "Team A"},
                    "away_team": {"id": 102, "name": "Team B"},
                    "competition": {"id": 39, "name": "Premier League"},
                    "utc_date": "2023-01-01T15:00:00Z",
                    "status": "SCHEDULED"
                },
                {
                    "id": 2,
                    "home_team": {"id": 103, "name": "Team C"},
                    "away_team": {"id": 104, "name": "Team D"},
                    "competition": {"id": 39, "name": "Premier League"},
                    "utc_date": "2023-01-02T15:00:00Z",
                    "status": "FINISHED",
                    "score": {"full_time": {"home_team": 2, "away_team": 1}}
                }
            ]
        })

        # 队伍详情
        self.add_response('get_team', {
            "id": 101,
            "name": "Team A",
            "short_name": "TEA",
            "tla": "TEA",
            "address": "Stadium Address",
            "website": "https://teama.com",
            "founded": 1880,
            "club_colors": "Red / White",
            "venue": "Team A Stadium"
        })

        # 球员列表
        self.add_response('get_team_squad', {
            "count": 25,
            "squad": [
                {
                    "id": 1001,
                    "name": "Player One",
                    "position": "Goalkeeper",
                    "nationality": "England",
                    "date_of_birth": "1990-01-01",
                    "nationality": "England"
                },
                {
                    "id": 1002,
                    "name": "Player Two",
                    "position": "Forward",
                    "nationality": "England",
                    "date_of_birth": "1992-01-01",
                    "nationality": "England"
                }
            ]
        })

    async def get_competitions(self, **kwargs):
        """获取联赛列表"""
        self.record_call('get_competitions', tuple(), kwargs)

        if 'get_competitions' in self.exceptions:
            raise self.exceptions['get_competitions']

        if 'get_competitions' in self.delays:
            await asyncio.sleep(self.delays['get_competitions'])

        return self.responses['get_competitions']

    async def get_matches(self, **kwargs):
        """获取比赛列表"""
        self.record_call('get_matches', tuple(), kwargs)

        if 'get_matches' in self.exceptions:
            raise self.exceptions['get_matches']

        if 'get_matches' in self.delays:
            await asyncio.sleep(self.delays['get_matches'])

        return self.responses['get_matches']

    async def get_team(self, team_id: int):
        """获取队伍详情"""
        self.record_call('get_team', (team_id,), {})

        if 'get_team' in self.exceptions:
            raise self.exceptions['get_team']

        if 'get_team' in self.delays:
            await asyncio.sleep(self.delays['get_team'])

        return self.responses['get_team']

    async def get_team_squad(self, team_id: int):
        """获取队伍阵容"""
        self.record_call('get_team_squad', (team_id,), {})

        if 'get_team_squad' in self.exceptions:
            raise self.exceptions['get_team_squad']

        if 'get_team_squad' in self.delays:
            await asyncio.sleep(self.delays['get_team_squad'])

        return self.responses['get_team_squad']

class OddsAPIClientMock(ExternalServiceMock):
    """赔率API客户端Mock"""

    def __init__(self):
        super().__init__()
        self._setup_default_responses()

    def _setup_default_responses(self):
        """设置默认响应"""
        # 赔率数据
        self.add_response('get_match_odds', {
            "match_id": 1,
            "bookmakers": [
                {
                    "name": "Bet365",
                    "bets": [
                        {
                            "name": "Match Winner",
                            "values": [
                                {"value": "Home", "odd": 2.10},
                                {"value": "Draw", "odd": 3.40},
                                {"value": "Away", "odd": 3.60}
                            ]
                        }
                    ]
                },
                {
                    "name": "William Hill",
                    "bets": [
                        {
                            "name": "Match Winner",
                            "values": [
                                {"value": "Home", "odd": 2.05},
                                {"value": "Draw", "odd": 3.50},
                                {"value": "Away", "odd": 3.70}
                            ]
                        }
                    ]
                }
            ]
        })

        # 历史赔率
        self.add_response('get_historical_odds', {
            "match_id": 1,
            "history": [
                {
                    "timestamp": "2023-01-01T10:00:00Z",
                    "home_odd": 2.10,
                    "draw_odd": 3.40,
                    "away_odd": 3.60
                },
                {
                    "timestamp": "2023-01-01T11:00:00Z",
                    "home_odd": 2.05,
                    "draw_odd": 3.45,
                    "away_odd": 3.65
                }
            ]
        })

    async def get_match_odds(self, match_id: int):
        """获取比赛赔率"""
        self.record_call('get_match_odds', (match_id,), {})

        if 'get_match_odds' in self.exceptions:
            raise self.exceptions['get_match_odds']

        if 'get_match_odds' in self.delays:
            await asyncio.sleep(self.delays['get_match_odds'])

        return self.responses['get_match_odds']

    async def get_historical_odds(self, match_id: int):
        """获取历史赔率"""
        self.record_call('get_historical_odds', (match_id,), {})

        if 'get_historical_odds' in self.exceptions:
            raise self.exceptions['get_historical_odds']

        if 'get_historical_odds' in self.delays:
            await asyncio.sleep(self.delays['get_historical_odds'])

        return self.responses['get_historical_odds']

class MLServiceClientMock(ExternalServiceMock):
    """机器学习服务客户端Mock"""

    def __init__(self):
        super().__init__()
        self._setup_default_responses()

    def _setup_default_responses(self):
        """设置默认响应"""
        # 预测结果
        self.add_response('predict', {
            "match_id": 1,
            "predictions": {
                "home_win": 0.45,
                "draw": 0.30,
                "away_win": 0.25
            },
            "confidence": 0.85,
            "model_version": "1.0.0",
            "features_used": ["home_form", "away_form", "head_to_head"]
        })

        # 批量预测
        self.add_response('batch_predict', {
            "predictions": [
                {
                    "match_id": 1,
                    "home_win": 0.45,
                    "draw": 0.30,
                    "away_win": 0.25
                },
                {
                    "match_id": 2,
                    "home_win": 0.60,
                    "draw": 0.25,
                    "away_win": 0.15
                }
            ]
        })

        # 模型训练
        self.add_response('train_model', {
            "model_id": "model_001",
            "training_time": 120.5,
            "accuracy": 0.85,
            "loss": 0.15,
            "status": "completed"
        })

        # 模型评估
        self.add_response('evaluate_model', {
            "model_id": "model_001",
            "accuracy": 0.85,
            "precision": 0.82,
            "recall": 0.88,
            "f1_score": 0.85,
            "roc_auc": 0.92
        })

    async def predict(self, match_id: int, features: Dict[str, Any]):
        """单场比赛预测"""
        self.record_call('predict', (match_id, features), {})

        if 'predict' in self.exceptions:
            raise self.exceptions['predict']

        if 'predict' in self.delays:
            await asyncio.sleep(self.delays['predict'])

        response = self.responses['predict'].copy()
        response['match_id'] = match_id
        return response

    async def batch_predict(self, match_features: List[Dict[str, Any]]):
        """批量预测"""
        self.record_call('batch_predict', (match_features,), {})

        if 'batch_predict' in self.exceptions:
            raise self.exceptions['batch_predict']

        if 'batch_predict' in self.delays:
            await asyncio.sleep(self.delays['batch_predict'])

        return self.responses['batch_predict']

    async def train_model(self, training_data: Dict[str, Any]):
        """训练模型"""
        self.record_call('train_model', (training_data,), {})

        if 'train_model' in self.exceptions:
            raise self.exceptions['train_model']

        if 'train_model' in self.delays:
            await asyncio.sleep(self.delays['train_model'])

        return self.responses['train_model']

    async def evaluate_model(self, model_id: str, test_data: Dict[str, Any]):
        """评估模型"""
        self.record_call('evaluate_model', (model_id, test_data), {})

        if 'evaluate_model' in self.exceptions:
            raise self.exceptions['evaluate_model']

        if 'evaluate_model' in self.delays:
            await asyncio.sleep(self.delays['evaluate_model'])

        response = self.responses['evaluate_model'].copy()
        response['model_id'] = model_id
        return response

class RedisMock(AsyncMock):
    """Redis Mock"""

    def __init__(self):
        super().__init__()
        self.data = {}
        self.ttl = {}

    async def ping(self):
        """Ping测试"""
        return True

    async def set(self, key: str, value: Any, ex: int = None):
        """设置值"""
        self.data[key] = value
        if ex:
            self.ttl[key] = ex
        return True

    async def get(self, key: str):
        """获取值"""
        return self.data.get(key)

    async def delete(self, key: str):
        """删除值"""
        if key in self.data:
            del self.data[key]
        if key in self.ttl:
            del self.ttl[key]
        return 1 if key in self.data else 0

    async def exists(self, key: str):
        """检查键是否存在"""
        return key in self.data

    async def keys(self, pattern: str = "*"):
        """获取所有键"""
        import fnmatch
        return [key for key in self.data.keys() if fnmatch.fnmatch(key, pattern)]

    async def flushdb(self):
        """清空数据库"""
        self.data.clear()
        self.ttl.clear()
        return True

class MockContextManager:
    """Mock上下文管理器"""

    def __init__(self, mock_obj):
        self.mock_obj = mock_obj

    async def __aenter__(self):
        return self.mock_obj

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

# Mock装饰器
def mock_external_services(func):
    """外部服务Mock装饰器"""
    def wrapper(*args, **kwargs):
        with patch('src.services.external_apis.FootballAPIClient', FootballAPIClientMock), \
             patch('src.services.external_apis.OddsAPIClient', OddsAPIClientMock), \
             patch('src.services.ml_service.MLServiceClient', MLServiceClientMock):

            return func(*args, **kwargs)

    return wrapper

def mock_redis(func):
    """Redis Mock装饰器"""
    def wrapper(*args, **kwargs):
        with patch('redis.asyncio.Redis', RedisMock):
            return func(*args, **kwargs)

    return wrapper

def create_external_service_mocks():
    """创建外部服务Mock"""
    return {
        'football_api': FootballAPIClientMock(),
        'odds_api': OddsAPIClientMock(),
        'ml_service': MLServiceClientMock(),
        'redis': RedisMock()
    }

# 使用示例
class TestWithExternalMocks:
    """使用外部Mock的测试基类"""

    def setup_method(self):
        """设置方法"""
        self.mocks = create_external_service_mocks()

    def setup_mock_responses(self):
        """设置Mock响应"""
        # 设置足球API响应
        self.mocks['football_api'].add_response('get_competitions', {
            "count": 2,
            "competitions": [
                {"id": 39, "name": "Premier League"},
                {"id": 40, "name": "Championship"}
            ]
        })

        # 设置赔率API响应
        self.mocks['odds_api'].add_response('get_match_odds', {
            "match_id": 1,
            "bookmakers": [
                {"name": "Bet365", "odds": {"home": 2.10, "draw": 3.40, "away": 3.60}}
            ]
        })

        # 设置ML服务响应
        self.mocks['ml_service'].add_response('predict', {
            "match_id": 1,
            "predictions": {"home": 0.45, "draw": 0.30, "away": 0.25}
        })

    def verify_mock_calls(self):
        """验证Mock调用"""
        assert self.mocks['football_api'].get_call_count('get_competitions') > 0
        assert self.mocks['odds_api'].get_call_count('get_match_odds') > 0
        assert self.mocks['ml_service'].get_call_count('predict') > 0
```

---

## 测试数据管理

### 数据隔离

```python
# tests/utils/test_data_manager.py
import pytest
import asyncio
from typing import Dict, Any, List, Optional
from contextlib import asynccontextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from src.database.base import Base
from src.database.config import get_test_database_config

class TestDataManager:
    """测试数据管理器"""

    def __init__(self):
        self.test_db_config = get_test_database_config()
        self.engine = None
        self.async_engine = None
        self.SessionLocal = None
        self.AsyncSessionLocal = None

    def setup_databases(self):
        """设置测试数据库"""
        # 同步数据库
        self.engine = create_engine(self.test_db_config['url'])
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)

        # 异步数据库
        self.async_engine = create_async_engine(self.test_db_config['async_url'])
        self.AsyncSessionLocal = sessionmaker(
            self.async_engine,
            class_=AsyncSession,
            expire_on_commit=False
        )

    def teardown_databases(self):
        """清理测试数据库"""
        if self.engine:
            Base.metadata.drop_all(self.engine)
            self.engine.dispose()

        if self.async_engine:
            import asyncio
            async def drop_async_tables():
                async with self.async_engine.begin() as conn:
                    await conn.run_sync(Base.metadata.drop_all)
            asyncio.run(drop_async_tables())
            self.async_engine.dispose()

    @contextmanager
    def get_session(self):
        """获取同步数据库会话"""
        if not self.SessionLocal:
            self.setup_databases()

        session = self.SessionLocal()
        try:
            yield session
        finally:
            session.close()

    @asynccontextmanager
    async def get_async_session(self):
        """获取异步数据库会话"""
        if not self.AsyncSessionLocal:
            self.setup_databases()

        async with self.AsyncSessionLocal() as session:
            try:
                yield session
            finally:
                await session.close()

    def clean_database(self):
        """清理数据库数据"""
        with self.get_session() as session:
            for table in reversed(Base.metadata.sorted_tables):
                session.execute(table.delete())
            session.commit()

    async def clean_async_database(self):
        """清理异步数据库数据"""
        async with self.get_async_session() as session:
            for table in reversed(Base.metadata.sorted_tables):
                await session.execute(table.delete())
            await session.commit()

    def create_test_data(self, data_config: Dict[str, Any]):
        """创建测试数据"""
        with self.get_session() as session:
            for table_name, records in data_config.items():
                if records:
                    table = Base.metadata.tables.get(table_name)
                    if table:
                        for record in records:
                            session.execute(table.insert().values(**record))
            session.commit()

    async def create_async_test_data(self, data_config: Dict[str, Any]):
        """创建异步测试数据"""
        async with self.get_async_session() as session:
            for table_name, records in data_config.items():
                if records:
                    table = Base.metadata.tables.get(table_name)
                    if table:
                        for record in records:
                            await session.execute(table.insert().values(**record))
            await session.commit()

    def get_table_count(self, table_name: str) -> int:
        """获取表记录数"""
        with self.get_session() as session:
            table = Base.metadata.tables.get(table_name)
            if table:
                result = session.execute(table.select().count())
                return result.scalar()
            return 0

    async def get_async_table_count(self, table_name: str) -> int:
        """获取异步表记录数"""
        async with self.get_async_session() as session:
            table = Base.metadata.tables.get(table_name)
            if table:
                result = await session.execute(table.select().count())
                return result.scalar()
            return 0

@pytest.fixture(scope="session")
def test_data_manager():
    """测试数据管理器fixture"""
    manager = TestDataManager()
    manager.setup_databases()
    yield manager
    manager.teardown_databases()

@pytest.fixture
def clean_database(test_data_manager):
    """清理数据库fixture"""
    test_data_manager.clean_database()
    yield
    test_data_manager.clean_database()

@pytest.fixture
async def clean_async_database(test_data_manager):
    """清理异步数据库fixture"""
    await test_data_manager.clean_async_database()
    yield
    await test_data_manager.clean_async_database()
```

---

## 总结

本文档详细介绍了足球预测系统的测试数据工厂和Mock策略，包括：

1. **Factory Boy使用**: 完整的工厂模式实现，支持复杂关系数据生成
2. **Mock策略**: 全面覆盖外部服务Mock，包括异步Mock和条件Mock
3. **测试数据管理**: 数据隔离、清理和验证的完整解决方案
4. **性能优化**: 批量数据生成和缓存策略

这些工具和策略可以帮助构建稳定、高效的测试环境，确保测试的可靠性和可维护性。