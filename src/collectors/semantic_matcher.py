#!/usr/bin/env python3
"""V150.0 Semantic Matcher.

This module implements semantic matching for football matches using
date, league, and team name similarity.

Author: 高级数据架构师
Version: V150.0
Date: 2026-01-07
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class MatchSignature:
    """Signature of a football match for semantic matching.

    Attributes:
        date: Match start time
        league: League name
        home_team: Home team name
        away_team: Away team name
    """

    date: datetime
    league: str
    home_team: str
    away_team: str


class SemanticMatcher:
    """Semantic matcher for football matches.

    This matcher finds candidate matches based on:
    1. Date proximity (within tolerance)
    2. League matching
    3. Team name similarity

    Example:
        >>> matcher = SemanticMatcher()
        >>> fotmob_match = MatchSignature(
        ...     date=datetime(2024, 11, 1, 15, 0),
        ...     league="Premier League",
        ...     home_team="Arsenal",
        ...     away_team="Chelsea",
        ... )
        >>> candidates = [MatchSignature(...), ...]
        >>> results = matcher.find_candidates(fotmob_match, candidates)
    """

    def __init__(self):
        """Initialize the semantic matcher."""
        # Import LevenshteinMatcher for team name comparison
        try:
            from src.collectors.levenshtein_matcher import LevenshteinMatcher

            self.levenshtein = LevenshteinMatcher(threshold=5)
        except ImportError:
            self.levenshtein = None
            logger.warning("LevenshteinMatcher not available, using basic string comparison")

        logger.info("🔍 SemanticMatcher initialized")

    def find_candidates(
        self,
        fotmob_match: MatchSignature,
        oddsportal_matches: list[MatchSignature],
        date_tolerance_hours: int = 6,
    ) -> list[tuple[MatchSignature, float]]:
        """Find candidate matches from a pool of OddsPortal matches.

        Args:
            fotmob_match: The FotMob match to find candidates for
            oddsportal_matches: List of candidate OddsPortal matches
            date_tolerance_hours: Maximum time difference in hours (default: 6)

        Returns:
            List of (candidate, confidence) tuples, sorted by confidence descending

        Example:
            >>> results = matcher.find_candidates(fotmob_match, oddsportal_matches, date_tolerance_hours=6)
            >>> for candidate, confidence in results:
            ...     print(f"{candidate.home_team} vs {candidate.away_team}: {confidence}")
        """
        candidates = []

        for op_match in oddsportal_matches:
            # Step 1: Check date proximity
            time_diff = abs((fotmob_match.date - op_match.date).total_seconds())
            if time_diff > date_tolerance_hours * 3600:
                continue

            # Step 2: Check league match
            if not self._leagues_match(fotmob_match.league, op_match.league):
                continue

            # Step 3: Calculate team name similarity
            name_similarity = self._calculate_team_similarity(
                fotmob_match.home_team,
                fotmob_match.away_team,
                op_match.home_team,
                op_match.away_team,
            )

            # Step 4: Calculate overall confidence
            confidence = self._calculate_confidence(
                fotmob_match,
                op_match,
                time_diff,
                name_similarity,
            )

            candidates.append((op_match, confidence))

        # Sort by confidence descending
        candidates.sort(key=lambda x: x[1], reverse=True)

        return candidates

    def _leagues_match(self, league1: str, league2: str) -> bool:
        """Check if two league names refer to the same league.

        Args:
            league1: First league name
            league2: Second league name

        Returns:
            True if leagues match
        """
        # Direct match (case-insensitive)
        if league1.lower() == league2.lower():
            return True

        # Common variations
        league1_lower = league1.lower()
        league2_lower = league2.lower()

        # Premier League variations
        premier_variations = ["premier league", "premier league", "english premier league"]
        if league1_lower in premier_variations and league2_lower in premier_variations:
            return True

        # La Liga variations
        laliga_variations = ["la liga", "la liga santander", "primera división"]
        if league1_lower in laliga_variations and league2_lower in laliga_variations:
            return True

        # Bundesliga variations
        bundesliga_variations = ["bundesliga", "1. bundesliga", "german bundesliga"]
        if league1_lower in bundesliga_variations and league2_lower in bundesliga_variations:
            return True

        # Serie A variations
        seriea_variations = ["serie a", "serie a tim", "italian serie a"]
        if league1_lower in seriea_variations and league2_lower in seriea_variations:
            return True

        # Ligue 1 variations
        ligue1_variations = ["ligue 1", "ligue 1 uber eats", "french ligue 1"]
        return bool(league1_lower in ligue1_variations and league2_lower in ligue1_variations)

    def _calculate_team_similarity(
        self,
        fotmob_home: str,
        fotmob_away: str,
        op_home: str,
        op_away: str,
    ) -> float:
        """Calculate team name similarity score.

        Returns a value between 0.0 and 1.0.

        Args:
            fotmob_home: FotMob home team name
            fotmob_away: FotMob away team name
            op_home: OddsPortal home team name
            op_away: OddsPortal away team name

        Returns:
            Similarity score (0.0 to 1.0)
        """
        if self.levenshtein:
            # Use Levenshtein matcher
            _is_match_h, conf_h = self.levenshtein.match_team_names(fotmob_home, "", op_home, "")
            _is_match_a, conf_a = self.levenshtein.match_team_names(fotmob_away, "", op_away, "")

            # Average confidence
            return (conf_h + conf_a) / 2
        # Fallback: simple string comparison
        home_sim = 1.0 if fotmob_home.lower() == op_home.lower() else 0.0
        away_sim = 1.0 if fotmob_away.lower() == op_away.lower() else 0.0
        return (home_sim + away_sim) / 2

    def _calculate_confidence(
        self,
        fotmob: MatchSignature,
        oddsportal: MatchSignature,
        time_diff: float,
        name_similarity: float,
    ) -> float:
        """Calculate overall match confidence.

        Weights:
        - Time similarity: 40%
        - Team name similarity: 60%

        Args:
            fotmob: FotMob match signature
            oddsportal: OddsPortal match signature
            time_diff: Time difference in seconds
            name_similarity: Team name similarity score

        Returns:
            Overall confidence score (0.0 to 1.0)
        """
        # Time similarity (closer is better)
        # Max tolerance is 6 hours = 21600 seconds
        max_time_diff = 6 * 3600
        time_score = 1.0 - min(time_diff / max_time_diff, 1.0)

        # Weighted average
        return 0.4 * time_score + 0.6 * name_similarity
