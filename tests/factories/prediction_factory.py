"""预测工厂"""

import factory
from factory import fuzzy
from datetime import datetime, timedelta
from .base import BaseFactory


class MatchFactory(BaseFactory):
    """比赛工厂"""

    class Meta:
        model = None  # 需要导入实际模型
        sqlalchemy_session = None

    home_team = factory.Faker("company")
    away_team = factory.Faker("company")
    match_date = factory.LazyFunction(lambda: datetime.now() + timedelta(days=fuzzy.FuzzyInteger(1, 30).fuzz()))
    league = factory.Faker("word")
    season = factory.LazyFunction(lambda: datetime.now().year)
    is_finished = False
    home_score = None
    away_score = None


class PredictionFactory(BaseFactory):
    """预测工厂"""

    class Meta:
        model = None  # 需要导入实际模型
        sqlalchemy_session = None

    match_id = 1
    predicted_home_score = fuzzy.FuzzyInteger(0, 5)
    predicted_away_score = fuzzy.FuzzyInteger(0, 5)
    confidence = fuzzy.FuzzyFloat(0.5, 1.0)
    created_at = factory.LazyFunction(datetime.now)
    status = fuzzy.FuzzyChoice(["pending", "processing", "completed", "failed"])
    result = None

    @factory.post_generation
    def set_result(self, create, extracted, **kwargs):
        """设置结果"""
        if self.status == "completed" and not self.result:
            self.result = f"{self.predicted_home_score}-{self.predicted_away_score}"
