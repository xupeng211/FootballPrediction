#!/usr/bin/env python3
"""V41.570 Odds Data Models - 赔率数据模型定义

This module contains all data models used for odds collection and validation.
Separated from odds_production_extractor.py as part of the Great Decoupling.

Key Models:
    - MultiSourceEntityData: Core odds data model with V41.560 hardened validation

Author: V41.570 Refactoring Team
Date: 2026-01-21
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

# ============================================================================
# Constants
# ============================================================================

# Integrity score validation thresholds
# Valid odds should satisfy: 1.00 < 1/P1 + 1/P2 + 1/P3 < 1.15
# Relaxed range (V139.1) to accommodate varying bookmaker margins (5-15%)
MIN_INTEGRITY_SCORE = 1.00
MAX_INTEGRITY_SCORE = 1.15


# ============================================================================
# Data Models
# ============================================================================


@dataclass
class MultiSourceEntityData:
    """Represents odds data from a single bookmaker for a specific match.

    Attributes:
        match_id: Unique identifier for the match
        source_name: Internal entity code (e.g., "Entity_P")
        init_h/d/a: Initial (opening) odds for home/draw/away
        opening_time_h/d/a: Timestamps when initial odds were published
        final_h/d/a: Final odds before match start
        final_time: Timestamp when final odds were recorded
        integrity_score: Validation score (1/P1 + 1/P2 + 1/P3)
        is_valid: Whether data passes integrity validation
        validation_error: Error message if validation fails
        fully_captured: True if all three dimensions (init, time, final) are present
        data_timestamp: When this record was created
    """

    match_id: str
    source_name: str

    # Initial (opening) odds
    init_h: float | None = None
    init_d: float | None = None
    init_a: float | None = None

    # Initial odds timestamps
    opening_time_h: datetime | None = None
    opening_time_d: datetime | None = None
    opening_time_a: datetime | None = None

    # Final odds
    final_h: float | None = None
    final_d: float | None = None
    final_a: float | None = None

    # Final odds timestamp
    final_time: datetime | None = None

    # Validation metadata
    integrity_score: float | None = None
    is_valid: bool = False
    validation_error: str | None = None
    fully_captured: bool = False
    data_timestamp: datetime | None = None

    def calculate_integrity_score(self) -> float | None:
        """Calculates and validates the integrity score.

        The integrity score is computed as: Score = 1/P1 + 1/P2 + 1/P3
        Valid data must satisfy: 1.00 < Score < 1.15

        Special case: Data with only init_h + opening_time_h (no final odds)
        is marked as valid (hover capture scenario) but not fully captured.

        Returns:
            The integrity score if final odds are present, None otherwise.
        """
        # Full validation requires all final odds
        if not all([self.final_h, self.final_d, self.final_a]):
            # No final odds - check for partial data (hover capture scenario)
            has_init = self.init_h is not None
            has_time = any([self.opening_time_h, self.opening_time_d, self.opening_time_a])

            if has_init and has_time:
                # Partial data from hover capture - mark as valid but not complete
                self.is_valid = True
                self.validation_error = None
                self.fully_captured = False
                return None

            # No usable data
            return None

        # Has all final odds - calculate integrity score
        try:
            self.integrity_score = 1.0 / self.final_h + 1.0 / self.final_d + 1.0 / self.final_a

            if MIN_INTEGRITY_SCORE < self.integrity_score < MAX_INTEGRITY_SCORE:
                self.is_valid = True
                self.validation_error = None
            else:
                self.is_valid = False
                self.validation_error = (
                    f"Integrity score {self.integrity_score:.4f} "
                    f"outside valid range [{MIN_INTEGRITY_SCORE}, {MAX_INTEGRITY_SCORE}]"
                )

            # Check full capture status
            has_final = all([self.final_h, self.final_d, self.final_a])
            has_initial = all([self.init_h, self.init_d, self.init_a])
            has_time = any([self.opening_time_h, self.opening_time_d, self.opening_time_a])
            self.fully_captured = has_final and has_initial and has_time

            return self.integrity_score

        except ZeroDivisionError:
            self.is_valid = False
            self.validation_error = "Division by zero in integrity calculation"
            return None

    def validate_v41_560_hardened(self) -> tuple[bool, str | None]:
        """V41.560: Hardened validation for full-dimensional odds data.

        红线准则:
        1. 宁缺毋滥: 必须包含 [初盘, 变盘, 终盘]
        2. 时间戳锚定: 必须有时间戳数据
        3. 交互提取: 必须通过深度交互获取

        Returns:
            (is_valid, error_message): 验证结果和错误信息

        Validation Rules:
        - 必须有终盘赔率 (final_h/d/a 全部非空)
        - 必须有初盘赔率或变盘历史 (init_h/d/a 至少有一个非空)
        - 必须有时间戳 (opening_time_h/d/a 至少有一个非空)
        - 拒绝空数组: initial_price: [] 这种数据无效
        """
        errors = []

        # Rule 1: 必须有终盘赔率
        if not all([self.final_h, self.final_d, self.final_a]):
            missing = [
                name
                for name, val in [
                    ("final_h", self.final_h),
                    ("final_d", self.final_d),
                    ("final_a", self.final_a),
                ]
                if val is None
            ]
            errors.append(f"Missing final odds: {missing}")

        # Rule 2: 必须有初盘赔率或变盘历史
        has_any_init = any([self.init_h, self.init_d, self.init_a])
        if not has_any_init:
            errors.append("Missing initial odds (no init_h/d/a)")

        # Rule 3: 必须有时间戳锚定
        has_any_timestamp = any(
            [
                self.opening_time_h,
                self.opening_time_d,
                self.opening_time_a,
                self.final_time,
            ]
        )
        if not has_any_timestamp:
            errors.append("Missing timestamp anchoring (no opening_time or final_time)")

        # Rule 4: 拒绝残疾数据 (空数组情况已经在 Rule 2 处理)

        if errors:
            self.is_valid = False
            self.validation_error = "; ".join(errors)
            return False, self.validation_error

        # 所有规则通过，标记为有效并计算完整性评分
        self.calculate_integrity_score()
        return True, None

    def to_dict(self) -> dict[str, Any]:
        """Converts the dataclass to a dictionary.

        Returns:
            Dictionary representation of all fields.
        """
        return {
            "match_id": self.match_id,
            "source_name": self.source_name,
            "init_h": self.init_h,
            "init_d": self.init_d,
            "init_a": self.init_a,
            "final_h": self.final_h,
            "final_d": self.final_d,
            "final_a": self.final_a,
            "final_time": self.final_time,
            "integrity_score": self.integrity_score,
            "is_valid": self.is_valid,
            "validation_error": self.validation_error,
            "fully_captured": self.fully_captured,
            "opening_time_h": self.opening_time_h,
            "opening_time_d": self.opening_time_d,
            "opening_time_a": self.opening_time_a,
            "data_timestamp": self.data_timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MultiSourceEntityData":
        """Creates a MultiSourceEntityData instance from a dictionary.

        Args:
            data: Dictionary containing odds data

        Returns:
            MultiSourceEntityData instance
        """
        return cls(
            match_id=data.get("match_id", ""),
            source_name=data.get("source_name", ""),
            init_h=data.get("init_h"),
            init_d=data.get("init_d"),
            init_a=data.get("init_a"),
            opening_time_h=data.get("opening_time_h"),
            opening_time_d=data.get("opening_time_d"),
            opening_time_a=data.get("opening_time_a"),
            final_h=data.get("final_h"),
            final_d=data.get("final_d"),
            final_a=data.get("final_a"),
            final_time=data.get("final_time"),
            integrity_score=data.get("integrity_score"),
            is_valid=data.get("is_valid", False),
            validation_error=data.get("validation_error"),
            fully_captured=data.get("fully_captured", False),
            data_timestamp=data.get("data_timestamp"),
        )
