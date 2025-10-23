"""
测试辅助工具 - 接口适配器
Test Interface Adapters for Testing

提供测试中需要的接口适配器，解决接口不匹配问题。
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional
from unittest.mock import MagicMock

from src.domain.strategies.base import PredictionInput as BasePredictionInput
from src.domain.models.match import Match
from src.domain.models.team import Team


@dataclass
class SimplePredictionInput:
    """简化的预测输入数据结构，用于测试"""

    match_id: int
    home_team_id: int
    away_team_id: int
    home_team_form: Optional[str] = None
    away_team_form: Optional[str] = None
    home_team_goals_scored: Optional[list] = None
    away_team_goals_scored: Optional[list] = None
    home_team_goals_conceded: Optional[list] = None
    away_team_goals_conceded: Optional[list] = None
    match_date: Optional[datetime] = field(default_factory=datetime.utcnow)

    def to_base_prediction_input(self) -> BasePredictionInput:
        """转换为标准的PredictionInput"""
        # 创建模拟的Match对象
        mock_match = MagicMock(spec=Match)
        mock_match.id = self.match_id
        mock_match.date = self.match_date

        # 创建模拟的主队对象
        mock_home_team = MagicMock(spec=Team)
        mock_home_team.id = self.home_team_id
        mock_home_team.form = self.home_team_form or ""

        # 创建模拟的客队对象
        mock_away_team = MagicMock(spec=Team)
        mock_away_team.id = self.away_team_id
        mock_away_team.form = self.away_team_form or ""

        # 构建历史数据
        historical_data = {
            "home_team_goals_scored": self.home_team_goals_scored or [],
            "away_team_goals_scored": self.away_team_goals_scored or [],
            "home_team_goals_conceded": self.home_team_goals_conceded or [],
            "away_team_goals_conceded": self.away_team_goals_conceded or [],
            "home_team_form": self.home_team_form or "",
            "away_team_form": self.away_team_form or "",
        }

        return BasePredictionInput(
            match=mock_match,
            home_team=mock_home_team,
            away_team=mock_away_team,
            historical_data=historical_data,
            additional_features={},
        )


# 为了向后兼容，提供一个别名
PredictionInput = SimplePredictionInput
