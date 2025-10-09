"""
数据验证器模块

负责验证比赛数据和比分数据的合法性。
"""

import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


class DataValidator:
    """数据验证器"""

    def __init__(self):
        """初始化数据验证器"""
        self.logger = logging.getLogger(f"cleaner.{self.__class__.__name__}")

    def validate_match_data(self, raw_data: Dict[str, Any]) -> bool:
        """
        验证比赛数据的基础字段

        Args:
            raw_data: 原始比赛数据

        Returns:
            bool: 数据是否有效
        """
        required_fields = ["id", "homeTeam", "awayTeam", "utcDate"]
        return all(field in raw_data for field in required_fields)

    def validate_odds_data(self, raw_odds: Dict[str, Any]) -> bool:
        """
        验证赔率数据的基础字段

        Args:
            raw_odds: 原始赔率数据

        Returns:
            bool: 数据是否有效
        """
        required_fields = ["match_id", "bookmaker", "market_type", "outcomes"]
        return all(field in raw_odds for field in required_fields)

    def validate_score(self, score: Any) -> Optional[int]:
        """
        验证比分数据

        Args:
            score: 比分值

        Returns:
            Optional[int]: 有效的比分，无效则返回None
        """
        if score is None:
            return None

        try:
            score_int = int(score)
            # 比分必须是非负整数，上限99
            if 0 <= score_int <= 99:
                return score_int
            else:
                self.logger.warning(f"Score out of range: {score}")
                return None
        except (ValueError, TypeError):
            self.logger.warning(f"Invalid score format: {score}")
            return None

    def standardize_match_status(self, status: Optional[str]) -> str:
        """
        标准化比赛状态

        Args:
            status: 原始状态字符串

        Returns:
            str: 标准化后的状态
        """
        if not status:
            return "unknown"

        status_mapping = {
            "SCHEDULED": "scheduled",
            "TIMED": "scheduled",
            "IN_PLAY": "live",
            "PAUSED": "live",
            "FINISHED": "finished",
            "AWARDED": "finished",
            "POSTPONED": "postponed",
            "CANCELLED": "cancelled",
            "SUSPENDED": "suspended",
        }

        return status_mapping.get(str(status.upper()), "unknown")

    def clean_venue_name(self, venue: Optional[str]) -> Optional[str]:
        """
        清洗场地名称

        Args:
            venue: 原始场地名称

        Returns:
            Optional[str]: 清洗后的场地名称
        """
        if not venue:
            return None

        # 移除多余空格和特殊字符
        cleaned = re.sub(r"\s+", " ", str(venue).strip())
        return cleaned if cleaned else None

    def clean_referee_name(
        self, referees: Optional[List[Dict[str, Any]]]
    ) -> Optional[str]:
        """
        清洗裁判姓名

        Args:
            referees: 裁判列表

        Returns:
            Optional[str]: 主裁判姓名
        """
        if not referees or not isinstance(referees, list):
            return None

        # 查找主裁判
        for referee in referees:
            if referee.get("role") == "REFEREE":
                name = referee.get("name")
                if name:
                    return re.sub(r"\s+", " ", str(name).strip())

        return None
