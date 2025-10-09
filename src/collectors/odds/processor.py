"""
赔率数据处理
Odds Data Processing

处理和分析赔率数据，计算平均值、最佳赔率等
"""

import logging
from datetime import datetime
from typing import Any, Dict, List

import numpy as np

from .time_utils_compat import utc_now

logger = logging.getLogger(__name__)


class OddsProcessor:
    """赔率数据处理器"""

    def __init__(self):
        """初始化处理器"""
        pass

    async def process_odds_data(
        self,
        match_id: int,
        raw_odds_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        处理和分析赔率数据

        Args:
            match_id: 比赛ID
            raw_odds_data: 原始赔率数据

        Returns:
            处理后的赔率数据
        """
        processed = {
            "match_id": match_id,
            "timestamp": utc_now().isoformat(),
            "bookmakers": [],
            "market_analysis": {},
            "average_odds": {},
            "best_odds": {},
        }

        # 收集所有博彩公司的数据
        all_home_win = []
        all_draw = []
        all_away_win = []

        for source, source_data in raw_odds_data.items():
            for bookmaker in source_data.get("bookmakers", []):
                bookmaker_name = bookmaker.get("key")
                markets = bookmaker.get("markets", {})

                # Match winner odds
                if "match_winner" in markets:
                    h2h_odds = markets["match_winner"]
                    if all(h2h_odds.values()):
                        processed["bookmakers"].append(
                            {
                                "name": bookmaker_name,
                                "home_win": h2h_odds["home_win"],
                                "draw": h2h_odds["draw"],
                                "away_win": h2h_odds["away_win"],
                                "source": source,
                            }
                        )

                        all_home_win.append(h2h_odds["home_win"])
                        all_draw.append(h2h_odds["draw"])
                        all_away_win.append(h2h_odds["away_win"])

        # 计算平均赔率
        if all_home_win and all_draw and all_away_win:
            processed["average_odds"] = {
                "home_win": float(np.mean(all_home_win)),
                "draw": float(np.mean(all_draw)),
                "away_win": float(np.mean(all_away_win)),
            }

            # 计算最佳赔率
            processed["best_odds"] = {
                "home_win": max(all_home_win),
                "draw": max(all_draw),
                "away_win": max(all_away_win),
            }

            # 计算隐含概率
            processed["implied_probabilities"] = {
                "home_win": 1 / processed["best_odds"]["home_win"],
                "draw": 1 / processed["best_odds"]["draw"],
                "away_win": 1 / processed["best_odds"]["away_win"],
            }

            # 市场分析
            total_prob = sum(processed["implied_probabilities"].values())
            processed["market_analysis"] = {
                "total_implied_probability": total_prob,
                "bookmaker_margin": (total_prob - 1) * 100,  # 百分比
                "efficiency": 1 / total_prob if total_prob > 0 else 0,
            }

        return processed

    def validate_odds_data(self, odds_data: Dict[str, Any]) -> bool:
        """
        验证赔率数据的有效性

        Args:
            odds_data: 赔率数据

        Returns:
            是否有效
        """
        # 检查必需字段
        required_fields = ["match_id", "bookmakers"]
        for field in required_fields:
            if field not in odds_data:
                logger.warning(f"赔率数据缺少必需字段: {field}")
                return False

        # 检查博彩公司数据
        bookmakers = odds_data.get("bookmakers", [])
        if not bookmakers:
            logger.warning("没有博彩公司数据")
            return False

        # 检查赔率值
        for bookmaker in bookmakers:
            for key in ["home_win", "draw", "away_win"]:
                if key in bookmaker:
                    odds = bookmaker[key]
                    if odds is None or odds <= 1.0:
                        logger.warning(f"无效的赔率值: {key}={odds}")
                        return False

        return True

    def calculate_odds_movement(
        self,
        current_odds: Dict[str, float],
        previous_odds: Dict[str, float],
    ) -> Dict[str, Any]:
        """
        计算赔率变化

        Args:
            current_odds: 当前赔率
            previous_odds: 之前赔率

        Returns:
            赔率变化数据
        """
        movement = {}
        for outcome in ["home_win", "draw", "away_win"]:
            if outcome in current_odds and outcome in previous_odds:
                current = current_odds[outcome]
                previous = previous_odds[outcome]

                if current != previous:
                    # 计算百分比变化
                    percent_change = ((current - previous) / previous) * 100
                    movement[outcome] = {
                        "previous": previous,
                        "current": current,
                        "absolute_change": current - previous,
                        "percent_change": percent_change,
                        "direction": "up" if current > previous else "down",
                    }

        return movement