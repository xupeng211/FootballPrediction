#!/usr/bin/env python3
"""
Match Parser v2 - Sprint 3 复杂度治理版本

重构高复杂度函数，降低圈复杂度，提高可维护性。
采用单一职责原则，将大函数拆分为多个小函数。

Sprint 3 改进 (P0-010):
- parse_odds函数复杂度治理 ✅
- 单一职责原则应用 ✅
- 降低圈复杂度 ✅
- 提高可测试性 ✅

设计原则:
- Single Responsibility (单一职责)
- Low Cyclomatic Complexity (低圈复杂度)
- Composable Functions (可组合函数)
- Error Handling (错误处理)
"""

import json
import logging
from typing import Any, Dict, List, Tuple, Optional, Union
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

logger = logging.getLogger(__name__)


@dataclass
class OddsConfig:
    """赔率解析配置"""
    default_bookmakers: List[str]
    default_home_odds: float = 2.5
    default_draw_odds: float = 3.2
    default_away_odds: float = 2.8
    min_odds_value: float = 1.01
    max_odds_value: float = 1000.0


@dataclass
class ParsedOdds:
    """解析后的赔率数据"""
    avg_home_odds: float
    avg_draw_odds: float
    avg_away_odds: float
    implied_home_prob: float
    implied_draw_prob: float
    implied_away_prob: float
    odds_completeness: float
    bookmaker_count: int


class MatchParserV2:
    """
    比赛数据解析器 - Sprint 3 复杂度治理版本

    主要改进:
    - 将parse_odds函数从91行拆分为8个小函数
    - 每个函数单一职责，圈复杂度<5
    - 提高可测试性和可维护性
    """

    def __init__(self, config: Optional[OddsConfig] = None):
        """初始化解析器"""
        self.config = config or OddsConfig(
            default_bookmakers=['Bet365', 'William Hill', 'Pinnacle', 'Betfair']
        )
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def parse_odds(self, odds_json: Union[dict, str, None]) -> Dict[str, float]:
        """
        解析赔率数据 - Sprint 3 重构版本

        将原来的91行复杂函数拆分为多个简单函数的组合。

        Args:
            odds_json: JSON字符串或字典格式的赔率数据

        Returns:
            包含赔率特征的字典
        """
        # 1. 验证和预处理输入数据
        odds_data = self._validate_and_prepare_input(odds_json)
        if not odds_data:
            return self._get_default_odds_dict()

        # 2. 提取各博彩公司赔率
        bookmaker_odds = self._extract_bookmaker_odds(odds_data)

        # 3. 验证和清理赔率数据
        cleaned_odds = self._validate_and_clean_odds(bookmaker_odds)

        # 4. 计算平均赔率
        average_odds = self._calculate_average_odds(cleaned_odds)

        # 5. 计算隐含概率
        implied_probabilities = self._calculate_implied_probabilities(cleaned_odds)

        # 6. 构建结果
        parsed_odds = self._build_parsed_odds_result(
            average_odds, implied_probabilities, cleaned_odds
        )

        # 7. 转换为字典格式
        return self._convert_to_dict(parsed_odds)

    # === 拆分后的辅助函数 ===

    def _validate_and_prepare_input(self, odds_json: Union[dict, str, None]) -> Optional[Dict[str, Any]]:
        """
        验证和预处理输入数据

        Args:
            odds_json: 原始输入数据

        Returns:
            处理后的字典数据，如果无效则返回None
        """
        if not odds_json:
            return None

        # 处理字符串输入
        if isinstance(odds_json, str):
            return self._parse_json_string(odds_json)

        # 处理字典输入
        if isinstance(odds_json, dict):
            return odds_json

        # 不支持的类型
        self.logger.warning(f"odds_json类型不支持: {type(odds_json)}")
        return None

    def _parse_json_string(self, json_string: str) -> Optional[Dict[str, Any]]:
        """
        解析JSON字符串

        Args:
            json_string: JSON字符串

        Returns:
            解析后的字典，失败时返回None
        """
        try:
            return json.loads(json_string)
        except json.JSONDecodeError as e:
            self.logger.warning(f"odds JSON解析失败: {e}")
            return None

    def _extract_bookmaker_odds(self, odds_data: Dict[str, Any]) -> Dict[str, List[float]]:
        """
        提取各博彩公司的赔率数据

        Args:
            odds_data: 赔率数据字典

        Returns:
            博彩公司到赔率列表的映射
        """
        bookmaker_odds = {
            'home_odds': [],
            'draw_odds': [],
            'away_odds': []
        }

        for bookmaker in self.config.default_bookmakers:
            bm_data = self._safe_get(odds_data, bookmaker, {})
            single_odds = self._extract_single_bookmaker_odds(bm_data)

            if single_odds['home'] is not None:
                bookmaker_odds['home_odds'].append(single_odds['home'])
            if single_odds['draw'] is not None:
                bookmaker_odds['draw_odds'].append(single_odds['draw'])
            if single_odds['away'] is not None:
                bookmaker_odds['away_odds'].append(single_odds['away'])

        return bookmaker_odds

    def _extract_single_bookmaker_odds(self, bm_data: Dict[str, Any]) -> Dict[str, Optional[float]]:
        """
        提取单个博彩公司的赔率

        Args:
            bm_data: 单个博彩公司的数据

        Returns:
            主客平和赔率字典
        """
        return {
            'home': self._parse_odds_value(self._safe_get(bm_data, 'home')),
            'draw': self._parse_odds_value(self._safe_get(bm_data, 'draw')),
            'away': self._parse_odds_value(self._safe_get(bm_data, 'away'))
        }

    def _parse_odds_value(self, odds_value: Any) -> Optional[float]:
        """
        解析单个赔率值

        Args:
            odds_value: 原始赔率值

        Returns:
            解析后的浮点数，无效时返回None
        """
        if odds_value is None:
            return None

        try:
            # 使用Decimal进行精确解析
            decimal_odds = Decimal(str(odds_value))
            float_odds = float(decimal_odds)

            # 验证赔率范围
            if self.config.min_odds_value <= float_odds <= self.config.max_odds_value:
                return float_odds
            else:
                return None

        except (InvalidOperation, ValueError, TypeError):
            return None

    def _validate_and_clean_odds(self, bookmaker_odds: Dict[str, List[float]]) -> Dict[str, List[float]]:
        """
        验证和清理赔率数据

        Args:
            bookmaker_odds: 原始赔率数据

        Returns:
            清理后的赔率数据
        """
        # 移除异常值（使用3-sigma规则）
        cleaned_odds = {}

        for odds_type, odds_list in bookmaker_odds.items():
            if len(odds_list) == 0:
                cleaned_odds[odds_type] = []
                continue

            # 计算统计量
            mean_odds = sum(odds_list) / len(odds_list)
            variance = sum((x - mean_odds) ** 2 for x in odds_list) / len(odds_list)
            std_dev = variance ** 0.5

            # 过滤异常值
            filtered_odds = [
                odds for odds in odds_list
                if abs(odds - mean_odds) <= 3 * std_dev
            ]

            cleaned_odds[odds_type] = filtered_odds if filtered_odds else odds_list

        return cleaned_odds

    def _calculate_average_odds(self, cleaned_odds: Dict[str, List[float]]) -> Tuple[float, float, float]:
        """
        计算平均赔率

        Args:
            cleaned_odds: 清理后的赔率数据

        Returns:
            (主胜平均赔率, 平局平均赔率, 客胜平均赔率)
        """
        avg_home = self._safe_average(
            cleaned_odds.get('home_odds', []),
            self.config.default_home_odds
        )
        avg_draw = self._safe_average(
            cleaned_odds.get('draw_odds', []),
            self.config.default_draw_odds
        )
        avg_away = self._safe_average(
            cleaned_odds.get('away_odds', []),
            self.config.default_away_odds
        )

        return avg_home, avg_draw, avg_away

    def _calculate_implied_probabilities(self, cleaned_odds: Dict[str, List[float]]) -> Tuple[float, float, float]:
        """
        计算隐含概率

        Args:
            cleaned_odds: 清理后的赔率数据

        Returns:
            (主胜隐含概率, 平局隐含概率, 客胜隐含概率)
        """
        # 计算总隐含概率
        total_home_prob = sum(1 / odds for odds in cleaned_odds.get('home_odds', []))
        total_draw_prob = sum(1 / odds for odds in cleaned_odds.get('draw_odds', []))
        total_away_prob = sum(1 / odds for odds in cleaned_odds.get('away_odds', []))

        total_prob = total_home_prob + total_draw_prob + total_away_prob

        if total_prob > 0:
            # 归一化概率
            home_prob = (total_home_prob / total_prob) * 100
            draw_prob = (total_draw_prob / total_prob) * 100
            away_prob = (total_away_prob / total_prob) * 100
        else:
            # 默认均等概率
            home_prob, draw_prob, away_prob = 33.33, 33.33, 33.34

        return home_prob, draw_prob, away_prob

    def _build_parsed_odds_result(
        self,
        average_odds: Tuple[float, float, float],
        implied_probabilities: Tuple[float, float, float],
        cleaned_odds: Dict[str, List[float]]
    ) -> ParsedOdds:
        """
        构建解析结果对象

        Args:
            average_odds: 平均赔率
            implied_probabilities: 隐含概率
            cleaned_odds: 清理后的赔率数据

        Returns:
            解析结果对象
        """
        avg_home, avg_draw, avg_away = average_odds
        implied_home, implied_draw, implied_away = implied_probabilities

        # 计算完整性
        max_bookmakers = len(self.config.default_bookmakers)
        actual_bookmakers = len(cleaned_odds.get('home_odds', []))
        completeness = actual_bookmakers / max_bookmakers if max_bookmakers > 0 else 0.0

        return ParsedOdds(
            avg_home_odds=avg_home,
            avg_draw_odds=avg_draw,
            avg_away_odds=avg_away,
            implied_home_prob=implied_home,
            implied_draw_prob=implied_draw,
            implied_away_prob=implied_away,
            odds_completeness=completeness,
            bookmaker_count=actual_bookmakers
        )

    def _convert_to_dict(self, parsed_odds: ParsedOdds) -> Dict[str, float]:
        """
        将解析结果转换为字典格式

        Args:
            parsed_odds: 解析结果对象

        Returns:
            字典格式的结果
        """
        return {
            'avg_home_odds': parsed_odds.avg_home_odds,
            'avg_draw_odds': parsed_odds.avg_draw_odds,
            'avg_away_odds': parsed_odds.avg_away_odds,
            'implied_home_prob': parsed_odds.implied_home_prob,
            'implied_draw_prob': parsed_odds.implied_draw_prob,
            'implied_away_prob': parsed_odds.implied_away_prob,
            'odds_completeness': parsed_odds.odds_completeness,
            'bookmaker_count': parsed_odds.bookmaker_count
        }

    # === 工具函数 ===

    def _safe_get(self, data: Dict[str, Any], key: str, default: Any = None) -> Any:
        """安全获取字典值"""
        if not isinstance(data, dict):
            return default
        return data.get(key, default)

    def _safe_average(self, values: List[float], default: float) -> float:
        """安全计算平均值"""
        return sum(values) / len(values) if values else default

    def _get_default_odds_dict(self) -> Dict[str, float]:
        """获取默认赔率字典"""
        return {
            'avg_home_odds': self.config.default_home_odds,
            'avg_draw_odds': self.config.default_draw_odds,
            'avg_away_odds': self.config.default_away_odds,
            'implied_home_prob': 33.33,
            'implied_draw_prob': 33.33,
            'implied_away_prob': 33.34,
            'odds_completeness': 0.0,
            'bookmaker_count': 0
        }

    # === 保持其他原有方法 ===

    def parse_stats(self, stats_json: Union[dict, str, None]) -> Dict[str, float]:
        """解析比赛统计数据（保持原有逻辑）"""
        if not stats_json:
            return self._get_default_stats()

        if isinstance(stats_json, str):
            try:
                stats_data = json.loads(stats_json)
            except json.JSONDecodeError:
                return self._get_default_stats()
        elif isinstance(stats_json, dict):
            stats_data = stats_json
        else:
            return self._get_default_stats()

        # 提取统计数据（简化版）
        result = {}
        for team_prefix, team_key in [('home_', 'home'), ('away_', 'away')]:
            team_stats = self._safe_get(stats_data, team_key, {})
            for stat_key in ['possession', 'shots', 'shots_on_target', 'corners']:
                result[f"{team_prefix}{stat_key}"] = self._safe_get(
                    team_stats, stat_key, 0.0
                )

        return result

    def _get_default_stats(self) -> Dict[str, float]:
        """获取默认统计数据"""
        result = {}
        for prefix in ['home_', 'away_']:
            for key in ['possession', 'shots', 'shots_on_target', 'corners']:
                default_value = 50.0 if key == 'possession' else 0.0
                result[f"{prefix}{key}"] = default_value
        return result