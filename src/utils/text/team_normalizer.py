#!/usr/bin/env python3
"""队名标准化核心实现。"""

from __future__ import annotations

import logging
import re

from thefuzz import fuzz

from .team_mappings import PREFIXES_TO_STRIP, SUFFIXES_TO_STRIP, TEAM_NAME_MAPPINGS
from .team_slug_parser import TeamSlugParserMixin
from .youth import _youth_detector

logger = logging.getLogger(__name__)


class TeamNameNormalizer(TeamSlugParserMixin):
    """项目级统一队名标准化器。"""

    def __init__(self) -> None:
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        self.suffix_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in SUFFIXES_TO_STRIP]
        self.prefix_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in PREFIXES_TO_STRIP]

    def normalize(self, team_name: str) -> str:
        if not team_name:
            return ""

        normalized = team_name.strip()
        normalized = re.sub(r"\.", "", normalized)
        normalized = re.sub(r"\s*[&]\s*", " ", normalized)
        normalized = re.sub(r"\s+and\s+", " ", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"-", " ", normalized)
        normalized = re.sub(r"\s+", " ", normalized)

        for pattern in self.prefix_patterns:
            normalized = pattern.sub("", normalized)

        for pattern in self.suffix_patterns:
            normalized = pattern.sub("", normalized)

        normalized_lower = normalized.lower()
        if normalized_lower in TEAM_NAME_MAPPINGS:
            normalized = TEAM_NAME_MAPPINGS[normalized_lower]
        else:
            for key, value in TEAM_NAME_MAPPINGS.items():
                if normalized_lower.startswith(key + " ") or normalized_lower.endswith(" " + key):
                    normalized = value
                    break
                if normalized_lower == key:
                    normalized = value
                    break

        normalized = normalized.strip()
        normalized = re.sub(r"\s+", " ", normalized)
        return normalized.lower()

    def are_same_team(self, name1: str, name2: str) -> bool:
        if not name1 or not name2:
            return False

        if _youth_detector.are_different_tiers(name1, name2):
            logger.warning(
                "🚨 V41.29 BLOCKED: Youth team collision rejected: %s vs %s", name1, name2
            )
            return False

        return self.normalize(name1) == self.normalize(name2)

    def fuzzy_match(self, name1: str, name2: str) -> float:
        if not name1 or not name2:
            return 0.0

        if _youth_detector.are_different_tiers(name1, name2):
            norm1 = self.normalize(name1)
            norm2 = self.normalize(name2)
            token_sort_score = fuzz.token_sort_ratio(norm1, norm2)
            partial_score = fuzz.partial_ratio(norm1, norm2)
            standard_score = fuzz.ratio(norm1, norm2)
            base_score = float(max(token_sort_score, partial_score, standard_score))
            penalty_score = base_score * 0.5
            logger.debug(
                "🚨 Youth team penalty applied: %s vs %s (base: %.1f%% -> penalty: %.1f%%)",
                name1,
                name2,
                base_score,
                penalty_score,
            )
            return penalty_score

        norm1 = self.normalize(name1)
        norm2 = self.normalize(name2)

        if norm1 == norm2:
            return 100.0

        token_sort_score = fuzz.token_sort_ratio(norm1, norm2)
        partial_score = fuzz.partial_ratio(norm1, norm2)
        standard_score = fuzz.ratio(norm1, norm2)
        return float(max(token_sort_score, partial_score, standard_score))

    def _extract_core_word(self, team_name: str) -> str:
        normalized = self.normalize(team_name)
        words = normalized.split()
        if len(words) == 1:
            return words[0]

        generic_words = {
            "united",
            "city",
            "town",
            "athletic",
            "hotspur",
            "wanderers",
            "rovers",
            "albion",
            "county",
            "forest",
        }

        for word in words:
            if word not in generic_words:
                return word

        return words[0] if words else ""

    def relaxed_match(self, name1: str, name2: str, base_threshold: int = 85) -> float:  # noqa: PLR0911
        if not name1 or not name2:
            return 0.0

        if self.are_same_team(name1, name2):
            return 100.0

        norm1 = self.normalize(name1)
        norm2 = self.normalize(name2)

        if norm1 in norm2 or norm2 in norm1:
            return 95.0

        core1 = self._extract_core_word(name1)
        core2 = self._extract_core_word(name2)
        if core1 and core2 and core1 == core2:
            logger.debug(
                "✨ V41.790 relaxed_match: core word match '%s' for '%s' vs '%s'",
                core1,
                name1,
                name2,
            )
            return 95.0

        words1 = set(norm1.split())
        words2 = set(norm2.split())
        common_words = words1.intersection(words2)
        if common_words:
            uncommon_words1 = words1 - common_words
            uncommon_words2 = words2 - common_words
            if len(uncommon_words1) <= 1 and len(uncommon_words2) <= 1:
                shared_core_words = common_words - {
                    "fc",
                    "cf",
                    "sc",
                    "afc",
                    "ac",
                    "sd",
                }
                if shared_core_words:
                    return 90.0

        fuzzy_score = self.fuzzy_match(name1, name2)
        if fuzzy_score >= base_threshold:
            return min(fuzzy_score, 95.0)

        return fuzzy_score
