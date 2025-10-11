"""
赔率处理器模块

负责处理赔率数据的清洗、验证和标准化。
"""

import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .time_processor import TimeProcessor


class OddsProcessor:
    """赔率处理器"""

    def __init__(self, time_processor: Optional[TimeProcessor] = None):
        """
        初始化赔率处理器

        Args:
            time_processor: 时间处理器实例
        """
        self.time_processor = time_processor or TimeProcessor()
        self.logger = logging.getLogger(f"cleaner.{self.__class__.__name__}")

    def validate_odds_value(self, price: Any) -> bool:
        """
        验证赔率值

        Args:
            price: 赔率值

        Returns:
            bool: 赔率值是否有效
        """
        try:
            odds_value = float(price)
            # 赔率必须大于1.01
            return odds_value >= 1.01
        except (ValueError, TypeError):
            return False

    def standardize_outcome_name(self, name: Optional[str]) -> str:
        """
        标准化结果名称

        Args:
            name: 原始结果名称

        Returns:
            str: 标准化后的结果名称
        """
        if not name:
            return "unknown"

        name_mapping = {
            "1": "home",
            "X": "draw",
            "2": "away",
            "HOME": "home",
            "DRAW": "draw",
            "AWAY": "away",
            "Over": "over",
            "Under": "under",
        }

        return name_mapping.get(str(str(name).strip()), str(name).lower())

    def standardize_bookmaker_name(self, bookmaker: Optional[str]) -> str:
        """
        标准化博彩公司名称

        Args:
            bookmaker: 原始博彩公司名称

        Returns:
            str: 标准化后的博彩公司名称
        """
        if not bookmaker:
            return "unknown"

        # 移除空格并转换为小写
        return re.sub(r"\s+", "_", str(bookmaker).strip().lower())

    def standardize_market_type(self, market_type: Optional[str]) -> str:
        """
        标准化市场类型

        Args:
            market_type: 原始市场类型

        Returns:
            str: 标准化后的市场类型
        """
        if not market_type:
            return "unknown"

        market_mapping = {
            "h2h": "1x2",
            "spreads": "asian_handicap",
            "totals": "over_under",
            "btts": "both_teams_score",
        }

        return market_mapping.get(
            str(str(market_type).lower()), str(market_type).lower()
        )

    def validate_odds_consistency(self, outcomes: List[Dict[str, Any]]) -> bool:
        """
        验证赔率合理性

        Args:
            outcomes: 赔率结果列表

        Returns:
            bool: 赔率是否合理
        """
        try:
            if not outcomes:
                return False

            # 计算总概率
            total_prob = sum(1.0 / outcome["price"] for outcome in outcomes)

            # 总概率应该在95%-120%之间（考虑博彩公司抽水）
            return 0.95 <= total_prob <= 1.20  # type: ignore

        except (KeyError, ZeroDivisionError, TypeError):
            return False

    def calculate_implied_probabilities(
        self, outcomes: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """
        计算隐含概率

        Args:
            outcomes: 赔率结果列表

        Returns:
            Dict[str, float]: 隐含概率字典
        """
        try:
            probabilities = {}
            total_prob = 0.0

            # 计算原始概率
            for outcome in outcomes:
                name = outcome["name"]
                price = outcome["price"]
                prob = 1.0 / price
                probabilities[name] = prob
                total_prob += prob

            # 标准化概率（去除博彩公司利润边际）
            if total_prob > 0:
                for name in probabilities:
                    probabilities[name] = probabilities[name] / total_prob

            return probabilities

        except (KeyError, ZeroDivisionError, TypeError):
            return {}

    def process_outcomes(self, outcomes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        处理赔率结果

        Args:
            outcomes: 原始结果列表

        Returns:
            List[Dict[str, Any]]: 处理后的结果列表
        """
        cleaned_outcomes = []

        for outcome in outcomes:
            price = outcome.get("price")
            if price and self.validate_odds_value(price):
                cleaned_outcomes.append(
                    {
                        "name": self.standardize_outcome_name(outcome.get("name")),
                        "price": round(float(price), 3),  # 保留3位小数
                    }
                )

        return cleaned_outcomes

    async def clean_odds_data(
        self, raw_odds: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        清洗赔率数据

        Args:
            raw_odds: 原始赔率数据列表

        Returns:
            List[Dict]: 清洗后的赔率数据列表
        """
        cleaned_odds = []

        for odds in raw_odds:
            try:
                # 基础字段验证
                if not self._validate_basic_odds_fields(odds):
                    continue

                # 处理结果
                outcomes = odds.get("outcomes", [])
                cleaned_outcomes = self.process_outcomes(outcomes)

                if not cleaned_outcomes:
                    continue

                # 赔率合理性检查
                if not self.validate_odds_consistency(cleaned_outcomes):
                    self.logger.warning(
                        f"Inconsistent odds detected: {cleaned_outcomes}"
                    )
                    continue

                cleaned_data = {
                    "external_match_id": str(odds.get("match_id", "")),
                    "bookmaker": self.standardize_bookmaker_name(odds.get("bookmaker")),
                    "market_type": self.standardize_market_type(
                        odds.get("market_type")
                    ),
                    "outcomes": cleaned_outcomes,
                    "last_update": self.time_processor.to_utc_time(
                        odds.get("last_update")
                    ),
                    "implied_probabilities": self.calculate_implied_probabilities(
                        cleaned_outcomes
                    ),
                    "cleaned_at": datetime.now(timezone.utc).isoformat(),
                    "data_source": "cleaned",
                }

                cleaned_odds.append(cleaned_data)

            except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
                self.logger.error(f"Failed to clean odds data: {str(e)}")
                continue

        return cleaned_odds

    def _validate_basic_odds_fields(self, raw_odds: Dict[str, Any]) -> bool:
        """
        验证基础字段

        Args:
            raw_odds: 原始赔率数据

        Returns:
            bool: 是否包含必需字段
        """
        required_fields = ["match_id", "bookmaker", "market_type", "outcomes"]
        return all(field in raw_odds for field in required_fields)
