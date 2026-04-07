#!/usr/bin/env python3
"""青年队/预备队识别工具。"""

from __future__ import annotations

import logging
import re
from typing import ClassVar

logger = logging.getLogger(__name__)


class YouthTeamDetector:
    """青年队、B 队与预备队识别器。"""

    YOUTH_KEYWORDS: ClassVar[set[str]] = {
        " b ",
        " c ",
        " d ",
        "u19",
        "u20",
        "u21",
        "u23",
        "u17",
        "reserve",
        "reserves",
        "youth",
        "academy",
        "amateur",
        "ii.",
        "iii.",
        "iv.",
        "b team",
        "b-team",
        "c team",
        "c-team",
        "filial",
        "junior",
        "juniors",
    }

    YOUTH_PATTERNS: ClassVar[list[str]] = [
        r"\s+[IVX]+\s*$",
        r"\s+B\s*$",
        r"\s+C\s*$",
        r"\s+U\d{2}\s*$",
        r"\s+Reserves?\s*$",
        r"\s+Youth\s*$",
        r"\s+Academy\s*$",
        r"\s+Amateur\s*$",
    ]

    def __init__(self) -> None:
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        self.patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.YOUTH_PATTERNS]

    def is_youth_team(self, team_name: str) -> bool:
        if not team_name:
            return False

        for pattern in self.patterns:
            if pattern.search(team_name):
                logger.debug("🚨 Youth team detected by pattern: %s", team_name)
                return True

        normalized = team_name.lower().strip()
        for keyword in self.YOUTH_KEYWORDS:
            if keyword in normalized:
                logger.debug("🚨 Youth team detected by keyword '%s': %s", keyword, team_name)
                return True

        return False

    def get_youth_tier(self, team_name: str) -> int:
        if not self.is_youth_team(team_name):
            return 0

        normalized_lower = team_name.lower()
        if any(pattern in normalized_lower for pattern in [" b ", "ii", "ii.", " b-team"]):
            return 1
        if any(pattern in normalized_lower for pattern in [" c ", "iii", "iii.", "u21", "c-team"]):
            return 2
        return 3

    def are_different_tiers(self, team1: str, team2: str) -> bool:
        tier1 = self.get_youth_tier(team1)
        tier2 = self.get_youth_tier(team2)

        if tier1 == 0 and tier2 == 0:
            return False

        if (tier1 == 0 and tier2 > 0) or (tier1 > 0 and tier2 == 0):
            if self._are_same_club_base(team1, team2):
                logger.warning(
                    "🚨 YOUTH TEAM COLLISION BLOCKED: %s (tier %s) vs %s (tier %s)",
                    team1,
                    tier1,
                    team2,
                    tier2,
                )
                return True
            return False

        if tier1 != tier2 and self._are_same_club_base(team1, team2):
            logger.warning(
                "🚨 YOUTH TEAM TIER MISMATCH: %s (tier %s) vs %s (tier %s)",
                team1,
                tier1,
                team2,
                tier2,
            )
            return True

        return False

    def _are_same_club_base(self, team1: str, team2: str) -> bool:
        base1 = self._strip_youth_indicators(team1)
        base2 = self._strip_youth_indicators(team2)
        return base1.lower().strip() == base2.lower().strip()

    def _strip_youth_indicators(self, team_name: str) -> str:
        if not team_name:
            return ""

        result = team_name
        for pattern in self.patterns:
            result = pattern.sub("", result)

        for keyword in self.YOUTH_KEYWORDS:
            if keyword.strip() in result.lower():
                idx = result.lower().find(keyword.strip())
                if idx > 0:
                    result = result[:idx].strip()

        return result.strip()


_youth_detector = YouthTeamDetector()
