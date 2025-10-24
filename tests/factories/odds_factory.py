"""
赔率工厂 - 用于测试数据创建
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import random

from .base import BaseFactory, DataFactoryMixin, TimestampMixin


class OddsFactory(BaseFactory, DataFactoryMixin, TimestampMixin):
    """赔率测试数据工厂"""

    # 博彩公司名称
    BOOKMAKERS = [
        "William Hill", "Bet365", "Betfair", "Ladbrokes", "Paddy Power",
        "Coral", "Betfred", "888sport", "Unibet", "Betway"
    ]

    @classmethod
    def create(cls, **kwargs) -> Dict[str, Any]:
        """创建单个赔率实例"""
        default_data = {
            'id': cls.generate_id(),
            'match_id': kwargs.get('match_id', cls.generate_id()),
            'bookmaker': kwargs.get('bookmaker', random.choice(cls.BOOKMAKERS)),
            'home_win_odds': round(random.uniform(1.1, 10.0), 2),
            'draw_odds': round(random.uniform(2.0, 5.0), 2),
            'away_win_odds': round(random.uniform(1.1, 10.0), 2),
            'over_under_2_5_over': round(random.uniform(1.6, 2.5), 2),
            'over_under_2_5_under': round(random.uniform(1.4, 2.8), 2),
            'both_teams_to_score_yes': round(random.uniform(1.5, 3.0), 2),
            'both_teams_to_score_no': round(random.uniform(1.2, 2.8), 2),
            'correct_score_home': round(random.uniform(3.0, 15.0), 2),
            'correct_score_draw': round(random.uniform(5.0, 20.0), 2),
            'correct_score_away': round(random.uniform(3.0, 15.0), 2),
            'asian_handicap_home': round(random.uniform(1.7, 2.3), 2),
            'asian_handicap_away': round(random.uniform(1.7, 2.3), 2),
            'first_goal_scorer_home': round(random.uniform(4.0, 25.0), 2),
            'first_goal_scorer_away': round(random.uniform(4.0, 25.0), 2),
            'odds_update_time': cls.generate_timestamp(),
            'match_start_time': kwargs.get('match_start_time', cls.generate_timestamp()),
            'is_live': False,
            'volume': random.randint(10000, 1000000),
            'margin': round(random.uniform(0.02, 0.15), 4),  # 博彩公司利润率
            'created_at': cls.generate_timestamp(),
            'updated_at': cls.generate_timestamp(),
        }

        # 确保赔率合理性（总和应该包含博彩公司利润）
        home_prob = 1 / default_data['home_win_odds']
        draw_prob = 1 / default_data['draw_odds']
        away_prob = 1 / default_data['away_win_odds']
        total_prob = home_prob + draw_prob + away_prob

        # 调整赔率以包含博彩公司利润
        if total_prob < 1.0:
            margin_adjustment = 1.0 / (1.0 - default_data['margin'])
            default_data['home_win_odds'] = round(default_data['home_win_odds'] * margin_adjustment, 2)
            default_data['draw_odds'] = round(default_data['draw_odds'] * margin_adjustment, 2)
            default_data['away_win_odds'] = round(default_data['away_win_odds'] * margin_adjustment, 2)

        # 合并用户提供的参数
        default_data.update(kwargs)
        return cls.with_timestamps(**default_data)

    @classmethod
    def create_batch(cls, count: int, **kwargs) -> List[Dict[str, Any]]:
        """批量创建赔率实例"""
        odds_list = []
        for i in range(count):
            odds_data = cls.create(**kwargs)
            odds_list.append(odds_data)
        return odds_list

    @classmethod
    def create_for_match(cls, match_id: int, **kwargs) -> Dict[str, Any]:
        """为特定比赛创建赔率"""
        return cls.create(
            match_id=match_id,
            **kwargs
        )

    @classmethod
    def create_low_odds(cls, **kwargs) -> Dict[str, Any]:
        """创建低赔率（热门）"""
        return cls.create(
            home_win_odds=round(random.uniform(1.1, 1.8), 2),
            away_win_odds=round(random.uniform(3.0, 8.0), 2),
            draw_odds=round(random.uniform(2.5, 4.0), 2),
            **kwargs
        )

    @classmethod
    def create_high_odds(cls, **kwargs) -> Dict[str, Any]:
        """创建高赔率（冷门）"""
        return cls.create(
            home_win_odds=round(random.uniform(3.0, 8.0), 2),
            away_win_odds=round(random.uniform(1.1, 1.8), 2),
            draw_odds=round(random.uniform(2.5, 4.0), 2),
            **kwargs
        )

    @classmethod
    def create_balanced_odds(cls, **kwargs) -> Dict[str, Any]:
        """创建平衡赔率（势均力敌）"""
        return cls.create(
            home_win_odds=round(random.uniform(2.2, 2.8), 2),
            away_win_odds=round(random.uniform(2.2, 2.8), 2),
            draw_odds=round(random.uniform(2.8, 3.5), 2),
            **kwargs
        )

    @classmethod
    def create_live_odds(cls, **kwargs) -> Dict[str, Any]:
        """创建实时赔率"""
        return cls.create(
            is_live=True,
            odds_update_time=datetime.now(timezone.utc),
            # 实时赔率通常变化更频繁
            home_win_odds=round(random.uniform(1.2, 5.0), 2),
            draw_odds=round(random.uniform(2.0, 4.5), 2),
            away_win_odds=round(random.uniform(1.2, 5.0), 2),
            volume=random.randint(50000, 2000000),
            **kwargs
        )

    @classmethod
    def create_from_bookmaker(cls, bookmaker: str, **kwargs) -> Dict[str, Any]:
        """创建指定博彩公司的赔率"""
        return cls.create(
            bookmaker=bookmaker,
            **kwargs
        )

    @classmethod
    def create_with_margin(cls, margin: float, **kwargs) -> Dict[str, Any]:
        """创建指定利润率的赔率"""
        return cls.create(
            margin=round(margin, 4),
            **kwargs
        )

    @classmethod
    def create_correct_score_odds(cls, **kwargs) -> Dict[str, Any]:
        """创建正确比分赔率"""
        default_data = cls.create(**kwargs)

        # 添加更多比分赔率
        scores = ["1-0", "2-0", "2-1", "3-0", "3-1", "3-2", "0-0", "1-1", "2-2", "0-1", "0-2", "1-2"]
        correct_scores = {}

        for score in scores:
            if score in ["0-0", "1-1", "2-2"]:  # 平局比分
                correct_scores[f"correct_score_{score.replace('-', '_')}"] = round(random.uniform(8.0, 25.0), 2)
            elif score in ["1-0", "2-0", "2-1"]:  # 常见比分
                correct_scores[f"correct_score_{score.replace('-', '_')}"] = round(random.uniform(6.0, 15.0), 2)
            else:  # 其他比分
                correct_scores[f"correct_score_{score.replace('-', '_')}"] = round(random.uniform(10.0, 50.0), 2)

        default_data.update(correct_scores)
        return default_data

    @classmethod
    def create_asian_handicap_odds(cls, handicap: float, **kwargs) -> Dict[str, Any]:
        """创建亚洲盘口赔率"""
        return cls.create(
            asian_handicap=handicap,
            asian_handicap_home=round(random.uniform(1.8, 2.2), 2),
            asian_handicap_away=round(random.uniform(1.8, 2.2), 2),
            **kwargs
        )


class HistoricalOddsFactory(OddsFactory):
    """历史赔率工厂"""

    @classmethod
    def create(cls, **kwargs) -> Dict[str, Any]:
        """创建历史赔率"""
        days_ago = random.randint(1, 365)
        historical_date = datetime.now(timezone.utc).replace(day=datetime.now(timezone.utc).day - days_ago)

        return super().create(
            odds_update_time=historical_date,
            is_historical=True,
            is_settled=True,  # 历史赔率已结算
            settlement_result=kwargs.get('settlement_result', random.choice(['home_win', 'draw', 'away_win'])),
            **kwargs
        )


class LiveOddsFactory(OddsFactory):
    """实时赔率工厂"""

    @classmethod
    def create(cls, **kwargs) -> Dict[str, Any]:
        """创建实时赔率"""
        return super().create(
            is_live=True,
            odds_update_time=datetime.now(timezone.utc),
            volume=random.randint(100000, 5000000),
            # 实时赔率通常更紧凑
            margin=round(random.uniform(0.01, 0.08), 4),
            **kwargs
        )