#!/usr/bin/env python3
"""
V41.18 Match Sanity Checker - 比赛数据合理性检查器

目标：建立逻辑防火墙，彻底终结"Almeria 66-1 Cadiz"这种低级错误

Author: 首席逆向架构师
Version: V41.18
Date: 2026-01-13
"""

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class SanityViolationType(Enum):
    """合理性违规类型"""
    EXCESSIVE_SCORE = "excessive_score"  # 比分过高
    INVALID_HASH_LENGTH = "invalid_hash"  # 哈希长度无效
    INVALID_DATE_RANGE = "invalid_date"  # 日期范围无效
    MISSING_REQUIRED_FIELD = "missing_field"  # 缺少必需字段


@dataclass
class SanityViolation:
    """合理性违规详情"""
    violation_type: SanityViolationType
    field_name: str
    actual_value: Any
    expected_constraint: str
    match_data: Optional[Dict[str, Any]] = None


class SanityViolationError(Exception):
    """合理性违规异常"""

    def __init__(self, violations: list[SanityViolation]):
        self.violations = violations
        message = f"发现 {len(violations)} 个合理性违规:\n"
        for v in violations:
            message += f"  - {v.violation_type.value}: {v.field_name} = {v.actual_value} (期望: {v.expected_constraint})\n"
        super().__init__(message)


@dataclass
class SeasonRange:
    """赛季范围定义"""
    season_start: str  # "2023-07-01"
    season_end: str    # "2024-06-30"
    season_patterns: list[str]  # ["23/24", "2023-2024"]

    @classmethod
    def for_2324(cls) -> "SeasonRange":
        """23/24 赛季范围"""
        return cls(
            season_start="2023-07-01",
            season_end="2024-06-30",
            season_patterns=["23/24", "2023-2024", "2023/24"]
        )


class MatchSanityChecker:
    """V41.18: 比赛数据合理性检查器"""

    # 配置常量
    MAX_HOME_SCORE = 15
    MAX_AWAY_SCORE = 15
    MIN_SCORE = 0
    EXPECTED_HASH_LENGTH = 8
    ACCEPTABLE_HASH_LENGTHS = [7, 8]  # V41.19: 接受 7 或 8 位哈希（数据库实际情况）

    # 允许的日期格式
    DATE_FORMATS = [
        "%Y-%m-%d",
        "%d.%m.%Y",
        "%d/%m/%Y",
        "%d.%m.%y",
    ]

    def __init__(self, season_range: Optional[SeasonRange] = None):
        """
        初始化检查器

        Args:
            season_range: 赛季范围，默认 23/24
        """
        self.season_range = season_range or SeasonRange.for_2324()
        self.violations: list[SanityViolation] = []

    def clear(self) -> None:
        """清除违规记录"""
        self.violations.clear()

    def check_match(self, match_data: Dict[str, Any], raise_on_error: bool = True) -> bool:
        """
        检查单场比赛数据的合理性

        Args:
            match_data: 比赛数据字典
            raise_on_error: 发现违规时是否抛出异常

        Returns:
            True 如果数据合理，False 如果存在违规

        Raises:
            SanityViolationError: 发现违规且 raise_on_error=True
        """
        self.clear()

        # 1. 检查比分合理性
        self._check_scores(match_data)

        # 2. 检查哈希长度
        self._check_hash(match_data)

        # 3. 检查日期范围
        self._check_date(match_data)

        # 4. 检查必需字段
        self._check_required_fields(match_data)

        if self.violations and raise_on_error:
            raise SanityViolationError(self.violations)

        return len(self.violations) == 0

    def check_batch(self, matches: list[Dict[str, Any]], raise_on_error: bool = True) -> tuple[bool, list[Dict]]:
        """
        批量检查比赛数据

        Args:
            matches: 比赛数据列表
            raise_on_error: 发现违规时是否抛出异常

        Returns:
            (全部合理, 合理的比赛列表)

        Raises:
            SanityViolationError: 发现违规且 raise_on_error=True
        """
        valid_matches = []
        all_violations = []

        for match in matches:
            self.clear()
            self._check_scores(match)
            self._check_hash(match)
            self._check_date(match)
            self._check_required_fields(match)

            if self.violations:
                all_violations.extend(self.violations)
            else:
                valid_matches.append(match)

        if all_violations and raise_on_error:
            raise SanityViolationError(all_violations)

        return (len(all_violations) == 0, valid_matches)

    def _check_scores(self, match_data: Dict[str, Any]) -> None:
        """检查比分合理性"""
        home_score = match_data.get('home_score')
        away_score = match_data.get('away_score')

        # 检查主场比分
        if home_score is not None:
            try:
                home_int = int(home_score)
                if home_int > self.MAX_HOME_SCORE:
                    self.violations.append(SanityViolation(
                        violation_type=SanityViolationType.EXCESSIVE_SCORE,
                        field_name="home_score",
                        actual_value=home_score,
                        expected_constraint=f"<= {self.MAX_HOME_SCORE}",
                        match_data=match_data
                    ))
                elif home_int < self.MIN_SCORE:
                    self.violations.append(SanityViolation(
                        violation_type=SanityViolationType.EXCESSIVE_SCORE,
                        field_name="home_score",
                        actual_value=home_score,
                        expected_constraint=f">= {self.MIN_SCORE}",
                        match_data=match_data
                    ))
            except (ValueError, TypeError):
                self.violations.append(SanityViolation(
                    violation_type=SanityViolationType.EXCESSIVE_SCORE,
                    field_name="home_score",
                    actual_value=home_score,
                    expected_constraint="必须是整数",
                    match_data=match_data
                ))

        # 检查客场比分
        if away_score is not None:
            try:
                away_int = int(away_score)
                if away_int > self.MAX_AWAY_SCORE:
                    self.violations.append(SanityViolation(
                        violation_type=SanityViolationType.EXCESSIVE_SCORE,
                        field_name="away_score",
                        actual_value=away_score,
                        expected_constraint=f"<= {self.MAX_AWAY_SCORE}",
                        match_data=match_data
                    ))
                elif away_int < self.MIN_SCORE:
                    self.violations.append(SanityViolation(
                        violation_type=SanityViolationType.EXCESSIVE_SCORE,
                        field_name="away_score",
                        actual_value=away_score,
                        expected_constraint=f">= {self.MIN_SCORE}",
                        match_data=match_data
                    ))
            except (ValueError, TypeError):
                self.violations.append(SanityViolation(
                    violation_type=SanityViolationType.EXCESSIVE_SCORE,
                    field_name="away_score",
                    actual_value=away_score,
                    expected_constraint="必须是整数",
                    match_data=match_data
                ))

    def _check_hash(self, match_data: Dict[str, Any]) -> None:
        """检查哈希长度"""
        match_id = match_data.get('match_id')
        hash_value = match_data.get('hash')

        # V41.19: 检查 match_id 长度（接受 7 或 8 位）
        if match_id is not None:
            match_id_str = str(match_id)
            if len(match_id_str) not in self.ACCEPTABLE_HASH_LENGTHS:
                self.violations.append(SanityViolation(
                    violation_type=SanityViolationType.INVALID_HASH_LENGTH,
                    field_name="match_id",
                    actual_value=f"{match_id} (长度: {len(match_id_str)})",
                    expected_constraint=f"长度 ∈ {self.ACCEPTABLE_HASH_LENGTHS}",
                    match_data=match_data
                ))

        # 检查 hash 长度
        if hash_value is not None:
            hash_str = str(hash_value)
            if len(hash_str) not in self.ACCEPTABLE_HASH_LENGTHS:
                self.violations.append(SanityViolation(
                    violation_type=SanityViolationType.INVALID_HASH_LENGTH,
                    field_name="hash",
                    actual_value=f"{hash_value} (长度: {len(hash_str)})",
                    expected_constraint=f"长度 ∈ {self.ACCEPTABLE_HASH_LENGTHS}",
                    match_data=match_data
                ))

    def _check_date(self, match_data: Dict[str, Any]) -> None:
        """检查日期是否在赛季范围内"""
        date_str = match_data.get('date') or match_data.get('match_date') or match_data.get('match_time')

        if not date_str:
            return  # 日期是可选的，不强制

        parsed_date = self._parse_date(date_str)
        if not parsed_date:
            # 无法解析日期，但不一定算违规
            return

        # 检查是否在赛季范围内
        season_start = datetime.strptime(self.season_range.season_start, "%Y-%m-%d")
        season_end = datetime.strptime(self.season_range.season_end, "%Y-%m-%d")

        if not (season_start <= parsed_date <= season_end):
            self.violations.append(SanityViolation(
                violation_type=SanityViolationType.INVALID_DATE_RANGE,
                field_name="date",
                actual_value=str(parsed_date.date()),
                expected_constraint=f"{self.season_range.season_start} 到 {self.season_range.season_end}",
                match_data=match_data
            ))

    def _check_required_fields(self, match_data: Dict[str, Any]) -> None:
        """检查必需字段"""
        required_fields = ['home_team', 'away_team']

        for field in required_fields:
            value = match_data.get(field)
            if not value or (isinstance(value, str) and not value.strip()):
                self.violations.append(SanityViolation(
                    violation_type=SanityViolationType.MISSING_REQUIRED_FIELD,
                    field_name=field,
                    actual_value=value,
                    expected_constraint="非空字符串",
                    match_data=match_data
                ))

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """尝试解析日期字符串"""
        if not date_str:
            return None

        # 首先尝试清理日期字符串
        date_str = str(date_str).strip()

        # 尝试各种格式
        for fmt in self.DATE_FORMATS:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        return None


# 单例实例
_default_checker = MatchSanityChecker()


def check_match_sanity(match_data: Dict[str, Any], raise_on_error: bool = True) -> bool:
    """
    快捷函数：检查单场比赛数据的合理性

    Args:
        match_data: 比赛数据字典
        raise_on_error: 发现违规时是否抛出异常

    Returns:
        True 如果数据合理

    Raises:
        SanityViolationError: 发现违规且 raise_on_error=True
    """
    return _default_checker.check_match(match_data, raise_on_error)


def check_batch_sanity(matches: list[Dict[str, Any]], raise_on_error: bool = True) -> tuple[bool, list[Dict]]:
    """
    快捷函数：批量检查比赛数据

    Args:
        matches: 比赛数据列表
        raise_on_error: 发现违规时是否抛出异常

    Returns:
        (全部合理, 合理的比赛列表)

    Raises:
        SanityViolationError: 发现违规且 raise_on_error=True
    """
    return _default_checker.check_batch(matches, raise_on_error)
