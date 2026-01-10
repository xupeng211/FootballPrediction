#!/usr/bin/env python3
"""V150.0 Levenshtein Distance Matcher.

This module implements team name matching using Levenshtein edit distance.
It provides robust fuzzy matching for team names that may have slight variations.

Author: 高级数据架构师
Version: V150.0
Date: 2026-01-07
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class LevenshteinMatcher:
    """Team name matcher based on Levenshtein edit distance.

    This matcher calculates the edit distance between team names and
    determines if they refer to the same team.

    The edit distance is the minimum number of single-character edits
    (insertions, deletions, or substitutions) required to change one
    string into another.

    Example:
        >>> matcher = LevenshteinMatcher(threshold=0.4)  # Use relative threshold
        >>> is_match, confidence = matcher.match_team_names(
        ...     fotmob_home="Man Utd",
        ...     fotmob_away="Chelsea",
        ...     oddsportal_home="Manchester United",
        ...     oddsportal_away="Chelsea"
        ... )
        >>> print(is_match, confidence)
        True 0.9167
    """

    def __init__(self, threshold: int | float = 0.4):
        """Initialize the Levenshtein matcher.

        Args:
            threshold: Maximum edit distance OR relative threshold (default: 0.4)
                      If threshold < 1, it's treated as relative to string length
                      If threshold >= 1, it's treated as absolute distance
        """
        self.threshold = threshold
        self.use_relative = threshold < 1.0
        logger.info(f"🔍 LevenshteinMatcher initialized: threshold={threshold} ({'relative' if self.use_relative else 'absolute'})")

    def match_team_names(
        self,
        fotmob_home: str,
        fotmob_away: str,
        oddsportal_home: str,
        oddsportal_away: str,
    ) -> tuple[bool, float]:
        """Match team names using Levenshtein distance.

        This method tries two combinations:
        1. Direct: fotmob_home vs oddsportal_home, fotmob_away vs oddsportal_away
        2. Swapped: fotmob_home vs oddsportal_away, fotmob_away vs oddsportal_home

        Args:
            fotmob_home: Home team name from FotMob
            fotmob_away: Away team name from FotMob
            oddsportal_home: Home team name from OddsPortal
            oddsportal_away: Away team name from OddsPortal

        Returns:
            Tuple of (is_match, confidence)
            - is_match: Whether the teams match
            - confidence: Confidence score (0.0 to 1.0)
        """
        # Try both direct and swapped combinations
        direct_dist_h = self._levenshtein_distance(
            fotmob_home.lower(),
            oddsportal_home.lower()
        )
        direct_dist_a = self._levenshtein_distance(
            fotmob_away.lower(),
            oddsportal_away.lower()
        )

        swapped_dist_h = self._levenshtein_distance(
            fotmob_home.lower(),
            oddsportal_away.lower()
        )
        swapped_dist_a = self._levenshtein_distance(
            fotmob_away.lower(),
            oddsportal_home.lower()
        )

        # Use the better combination
        if direct_dist_h + direct_dist_a <= swapped_dist_h + swapped_dist_a:
            dist_h, dist_a = direct_dist_h, direct_dist_a
        else:
            dist_h, dist_a = swapped_dist_h, swapped_dist_a

        # Calculate string lengths for relative comparison
        len_h = max(len(fotmob_home), len(oddsportal_home))
        len_a = max(len(fotmob_away), len(oddsportal_away))

        # Check if both teams match within threshold
        if self.use_relative:
            # Relative threshold: compare distance to string length
            ratio_h = dist_h / len_h if len_h > 0 else 0
            ratio_a = dist_a / len_a if len_a > 0 else 0

            # Check if both ratios are within threshold
            if ratio_h <= self.threshold and ratio_a <= self.threshold:
                # Confidence based on average similarity
                avg_ratio = (ratio_h + ratio_a) / 2
                confidence = 1.0 - avg_ratio
                return True, confidence
        else:
            # Absolute threshold: direct distance comparison
            if dist_h <= self.threshold and dist_a <= self.threshold:
                # Calculate confidence based on edit distance
                max_len = max(len_h, len_a)
                confidence = 1.0 - (dist_h + dist_a) / (2 * max_len)
                return True, confidence

        return False, 0.0

    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """Calculate Levenshtein edit distance between two strings.

        This is the classic dynamic programming implementation.

        Args:
            s1: First string
            s2: Second string

        Returns:
            Edit distance (number of edits needed)

        Example:
            >>> matcher = LevenshteinMatcher()
            >>> matcher._levenshtein_distance("kitten", "sitting")
            3
        """
        # Try to use python-Levenshtein package if available (faster)
        try:
            import Levenshtein
            return Levenshtein.distance(s1, s2)
        except ImportError:
            # Fallback to pure Python implementation
            return self._python_levenshtein(s1, s2)

    def _python_levenshtein(self, s1: str, s2: str) -> int:
        """Pure Python implementation of Levenshtein distance.

        This is used as a fallback when the Levenshtein package is not available.
        """
        if len(s1) < len(s2):
            return self._python_levenshtein(s2, s1)

        if len(s2) == 0:
            return len(s1)

        previous_row = list(range(len(s2) + 1))

        for i, c1 in enumerate(s1):
            current_row = [i + 1]

            for j, c2 in enumerate(s2):
                # Cost of substitution
                cost = 0 if c1 == c2 else 1

                # Minimum of deletion, insertion, or substitution
                current_row.append(
                    min(
                        previous_row[j + 1] + 1,  # Deletion
                        current_row[j] + 1,  # Insertion
                        previous_row[j] + cost,  # Substitution
                    )
                )

            previous_row = current_row

        return previous_row[-1]
