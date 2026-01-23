#!/usr/bin/env python3
"""V144.2 Text Processing Utilities (Stable Baseline).

This module provides text normalization and processing utilities for the
Football Prediction system, including team name normalization, vendor name
cleaning, fuzzy matching support, and league URL mapping.

V41.29: Enhanced with YouthTeamDetector for preventing youth team collisions.

Usage:
    from src.utils.text_processor import (
        TeamNameNormalizer,
        YouthTeamDetector,
        VendorNameCleaner,
        LeagueUrlMapper
    )

    # Normalize team names
    normalizer = TeamNameNormalizer()
    normalized = normalizer.normalize("Man Utd")

    # Detect youth teams (V41.29)
    detector = YouthTeamDetector()
    is_youth = detector.is_youth_team("PSG II")  # Returns True
    different_tiers = detector.are_different_tiers("PSG", "PSG II")  # Returns True

    # Check team matching (V41.29 enhanced)
    same_team = normalizer.are_same_team("PSG", "PSG II")  # Returns False (blocked!)

    # Clean vendor names
    cleaner = VendorNameCleaner()
    cleaned = cleaner.clean("Pinnacle Sports")

    # Map league names to OddsPortal URL slugs (V122.0)
    mapper = LeagueUrlMapper()
    url = mapper.construct_results_url("Premier League", "2023-2024")
"""

import logging
import re

from thefuzz import fuzz

logger = logging.getLogger(__name__)


class YouthTeamDetector:
    """V41.29: Youth team/B team detection utility.

    Provides detection of youth team, reserve team, and B team indicators
    to prevent false positive matches between first teams and youth teams.

    Features:
        - Roman numeral suffix detection (II, III, IV)
        - Letter suffix detection (B, C)
        - Age group detection (U19, U20, U21, U23)
        - Reserve/Academy detection
        - Multilingual keyword support
    """

    # Youth team keywords (case-insensitive matching)
    # V41.29 FIX: Single-letter keywords (ii, iii, iv) cause false positives
    # - "ii" matches "L**iv**erpool", "I**v**a", etc.
    # - "iii" matches "Mississ**i**pp**i**", etc.
    # Solution: Use regex patterns instead for Roman numerals
    YOUTH_KEYWORDS = {
        # Single letter suffixes (must have spaces to be standalone)
        " b ",
        " c ",
        " d ",
        # Age groups (multi-character only)
        "u19",
        "u20",
        "u21",
        "u23",
        "u17",
        # Reserve/Youth indicators (multi-character only)
        "reserve",
        "reserves",
        "youth",
        "academy",
        "amateur",
        # Dotted versions (multi-character)
        "ii.",
        "iii.",
        "iv.",
        # Multilingual (multi-character)
        "b team",
        "b-team",
        "c team",
        "c-team",
        "filial",
        "junior",
        "juniors",
    }

    # Patterns that indicate youth teams (regex)
    YOUTH_PATTERNS = [
        r"\s+[IVX]+\s*$",  # Roman numerals at end: " PSG II"
        r"\s+B\s*$",  # Single B at end: " Real Madrid B"
        r"\s+C\s*$",  # Single C at end
        r"\s+U\d{2}\s*$",  # U followed by 2 digits: " Chelsea U21"
        r"\s+Reserves?\s*$",  # Reserve/Reserves
        r"\s+Youth\s*$",  # Youth
        r"\s+Academy\s*$",  # Academy (V41.29: 强制匹配，不依赖后缀)
        r"\s+Amateur\s*$",  # Amateur
    ]

    def __init__(self) -> None:
        """Initialize the youth team detector."""
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        """Compile regex patterns for better performance."""
        self.patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.YOUTH_PATTERNS]

    def is_youth_team(self, team_name: str) -> bool:
        """Check if a team name indicates a youth/reserve/B team.

        Args:
            team_name: Team name to check

        Returns:
            True if the team name indicates a youth team, False otherwise
        """
        if not team_name:
            return False

        # Check regex patterns first (faster)
        for pattern in self.patterns:
            if pattern.search(team_name):
                logger.debug(f"🚨 Youth team detected by pattern: {team_name}")
                return True

        # Check keyword list
        normalized = team_name.lower().strip()
        for keyword in self.YOUTH_KEYWORDS:
            if keyword in normalized:
                logger.debug(f"🚨 Youth team detected by keyword '{keyword}': {team_name}")
                return True

        return False

    def get_youth_tier(self, team_name: str) -> int:
        """Get the youth team tier level.

        Returns:
            0 for first team (no youth indicators)
            1 for B team / II
            2 for C team / III / U21
            3 for lower youth teams
        """
        if not self.is_youth_team(team_name):
            return 0  # First team

        normalized_lower = team_name.lower()

        # Tier 1: B team / II
        if any(pattern in normalized_lower for pattern in [" b ", "ii", "ii.", " b-team"]):
            return 1
        # Tier 2: C team / III / U21
        if any(pattern in normalized_lower for pattern in [" c ", "iii", "iii.", "u21", "c-team"]):
            return 2
        # Tier 3: Lower youth teams
        return 3

    def are_different_tiers(self, team1: str, team2: str) -> bool:
        """Check if two team names represent different tier levels of the same club.

        This is the key method for preventing youth team collisions.

        Args:
            team1: First team name
            team2: Second team name

        Returns:
            True if the teams are from different tiers (should NOT match)
            False if they are from the same tier OR completely different clubs
        """
        # If either is a youth team, check tiers
        tier1 = self.get_youth_tier(team1)
        tier2 = self.get_youth_tier(team2)

        # If both are first teams (tier 0), they're not different tiers
        if tier1 == 0 and tier2 == 0:
            return False

        # If one is youth and the other is first team, they're different tiers
        if (tier1 == 0 and tier2 > 0) or (tier1 > 0 and tier2 == 0):
            # Additional check: verify they're actually the same club
            # (e.g., "Real Madrid" vs "Barcelona B" should return False)
            if self._are_same_club_base(team1, team2):
                logger.warning(
                    f"🚨 YOUTH TEAM COLLISION BLOCKED: {team1} (tier {tier1}) "
                    f"vs {team2} (tier {tier2})"
                )
                return True
            return False

        # If both are youth teams but different tiers, they're different
        if tier1 != tier2 and self._are_same_club_base(team1, team2):
            logger.warning(
                f"🚨 YOUTH TEAM TIER MISMATCH: {team1} (tier {tier1}) vs {team2} (tier {tier2})"
            )
            return True

        return False

    def _are_same_club_base(self, team1: str, team2: str) -> bool:
        """Check if two team names refer to the same club (stripping youth indicators).

        Args:
            team1: First team name
            team2: Second team name

        Returns:
            True if they're the same club base, False otherwise
        """
        # Normalize both names by removing youth indicators
        base1 = self._strip_youth_indicators(team1)
        base2 = self._strip_youth_indicators(team2)

        # Compare normalized bases
        return base1.lower().strip() == base2.lower().strip()

    def _strip_youth_indicators(self, team_name: str) -> str:
        """Strip youth team indicators from a team name.

        Args:
            team_name: Team name with possible youth indicators

        Returns:
            Team name with youth indicators removed
        """
        if not team_name:
            return ""

        # Remove regex patterns
        result = team_name
        for pattern in self.patterns:
            result = pattern.sub("", result)

        # Remove keyword suffixes
        for keyword in self.YOUTH_KEYWORDS:
            if keyword.strip() in result.lower():
                # Find position of keyword
                idx = result.lower().find(keyword.strip())
                if idx > 0:  # Not at the start
                    result = result[:idx].strip()

        return result.strip()


# Singleton instance
_youth_detector = YouthTeamDetector()


class TeamNameNormalizer:
    """V117.1: Team name normalization utility.

    Provides consistent team name normalization across the entire project,
    handling abbreviations, common variations, and international naming conventions.

    V41.29: Enhanced with youth team collision detection.

    Features:
        - Abbreviation expansion (Man Utd -> Manchester United)
        - Common variation handling (Arsenal FC -> Arsenal)
        - International name mapping (Bayern Munich -> Bayern Munchen)
        - Whitespace and character normalization
        - Youth team collision prevention
    """

    # Common team name abbreviations and variations
    TEAM_NAME_MAPPINGS = {
        # English Premier League
        "man utd": "manchester united",
        "man united": "manchester united",
        # V41.35: Add full form mapping for Manchester Utd
        "manchester utd": "manchester united",
        # V41.35 FIX: REMOVED "manchester": "manchester united" mapping
        # This prevents "Manchester City" from being incorrectly mapped to "Manchester United"
        # Since we no longer strip "united" and "city" suffixes, these names stay distinct
        "man city": "manchester city",
        "mancity": "manchester city",
        "leeds": "leeds united",
        "leicester": "leicester city",
        "newcastle": "newcastle united",
        "newcastle utd": "newcastle united",
        "tottenham": "tottenham hotspur",
        "spurs": "tottenham hotspur",
        "west ham": "west ham united",
        "wolves": "wolverhampton wanderers",
        "nottm forest": "nottingham forest",
        "nottingham": "nottingham forest",  # V143.7: Handle stripped "Forest" suffix
        # Spanish La Liga
        "atleti": "atletico madrid",
        "atletico": "atletico madrid",
        "real madrid": "real madrid",
        "barca": "barcelona",
        "fc barcelona": "barcelona",
        "real betis": "real betis",
        "real sociedad": "real sociedad",
        # V41.35: Add core word collision for abbreviated Real Sociedad
        "r. sociedad": "real sociedad",
        "r sociedad": "real sociedad",
        "real valladolid": "real valladolid",
        "ath bilbao": "athletic bilbao",
        "athletic bilbao": "athletic bilbao",
        "valencia cf": "valencia",
        "espanyol": "espanyol",
        # German Bundesliga
        "bayern munich": "bayern munich",
        "bayern munchen": "bayern munich",
        "b dortmund": "borussia dortmund",
        "bvb": "borussia dortmund",
        "b leverkusen": "bayer leverkusen",
        "bayer leverkusen": "bayer leverkusen",
        "e frankfurt": "eintracht frankfurt",
        "eintracht frankfurt": "eintracht frankfurt",
        # Italian Serie A
        "inter milan": "inter milan",
        "inter": "inter milan",
        "ac milan": "milan",
        "juve": "juventus",
        "juventus": "juventus",
        "napoli": "napoli",
        "roma": "roma",
        "as roma": "roma",
        "lazio": "lazio",
        # French Ligue 1
        "psg": "paris saint germain",
        "paris sg": "paris saint germain",
        "olympique marseille": "marseille",
        "marseille": "marseille",
        "olympique lyon": "lyon",
        "lyon": "lyon",
        "nice": "nice",
        "monaco": "monaco",
        # Portuguese Liga
        "benfica": "benfica",
        "sporting cp": "sporting lisbon",
        "sporting lisbon": "sporting lisbon",
        "porto": "porto",
        "fc porto": "porto",
        # Dutch Eredivisie
        "ajax": "ajax",
        "afc ajax": "ajax",
        "feyenoord": "feyenoord",
        "psv": "psv eindhoven",
        "psv eindhoven": "psv eindhoven",
    }

    # Suffixes to strip
    # V41.30 FIX: DO NOT strip "united" or "city" - they are key team identifiers!
    # - "Manchester United" and "Manchester City" must NOT be treated the same
    # - Only strip generic club suffixes like FC, AC, etc.
    SUFFIXES_TO_STRIP = [
        r"\s+fc$",
        r"\s+f\.c\.$",
        r"\s+afcd?$",
        r"\s+a\.f\.c\.d?$",
        r"\s+cf$",
        r"\s+c\.f\.$",
        r"\s+sc$",
        r"\s+s\.c\.$",
        r"\s+ac$",
        r"\s+a\.c\.$",
        r"\s+sd$",
        r"\s+s\.d\.$",
        # V41.30: REMOVED r"\s+united$" and r"\s+city$" to prevent false matches
        r"\s+town$",
        r"\s+athletic$",
    ]

    # V41.35: Prefixes to strip (for handling "AFC Bournemouth" -> "Bournemouth")
    PREFIXES_TO_STRIP = [
        r"^afc\s+",
        r"^AFC\s+",
        r"^fc\s+",
        r"^FC\s+",
    ]

    def __init__(self) -> None:
        """Initialize the team name normalizer."""
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        """Compile regex patterns for better performance."""
        self.suffix_patterns = [
            re.compile(pattern, re.IGNORECASE) for pattern in self.SUFFIXES_TO_STRIP
        ]
        # V41.35: Compile prefix patterns
        self.prefix_patterns = [
            re.compile(pattern, re.IGNORECASE) for pattern in self.PREFIXES_TO_STRIP
        ]

    def normalize(self, team_name: str) -> str:
        """Normalize a team name to its canonical form.

        Args:
            team_name: Raw team name from data source

        Returns:
            Normalized team name (lowercase, no extra spaces, expanded abbreviations)
        """
        if not team_name:
            return ""

        # Step 1: Basic cleaning
        normalized = team_name.strip()

        # V41.30: Remove dots (periods) - they're abbreviations that should be ignored
        # "Man. Utd" → "Man Utd", "Spurs." → "Spurs", "F.C." → "FC"
        normalized = re.sub(r"\.", "", normalized)

        # V41.30: Remove "&" and "and" - they're redundant
        # "Brighton & Hove Albion" → "Brighton Hove Albion"
        # "Brighton and Hove Albion" → "Brighton Hove Albion"
        normalized = re.sub(r"\s*[&]\s*", " ", normalized)
        normalized = re.sub(r"\s+and\s+", " ", normalized, flags=re.IGNORECASE)

        # V41.30: Remove hyphens - they're often used inconsistently
        # "West-Ham United" → "West Ham United"
        normalized = re.sub(r"-", " ", normalized)

        # Normalize whitespace
        normalized = re.sub(r"\s+", " ", normalized)

        # Step 2: Remove common prefixes (V41.35: AFC, FC)
        for pattern in self.prefix_patterns:
            normalized = pattern.sub("", normalized)

        # Step 3: Remove common suffixes
        for pattern in self.suffix_patterns:
            normalized = pattern.sub("", normalized)

        # Step 4: Convert to lowercase for mapping
        normalized_lower = normalized.lower()

        # Step 5: Apply team name mappings
        if normalized_lower in self.TEAM_NAME_MAPPINGS:
            normalized = self.TEAM_NAME_MAPPINGS[normalized_lower]
        else:
            # V143.7: Improved partial matching - only match if key is a word boundary
            # This prevents "brentford newcastle" from matching "newcastle" mapping
            for key, value in self.TEAM_NAME_MAPPINGS.items():
                # Check if the normalized name starts with the key (e.g., "newcastle united" starts with "newcastle")
                if normalized_lower.startswith(key + " ") or normalized_lower.endswith(" " + key):
                    normalized = value
                    break
                # Check for exact match (already handled above, but kept for clarity)
                if normalized_lower == key:
                    normalized = value
                    break

        # Step 6: Final cleanup
        normalized = normalized.strip()
        normalized = re.sub(r"\s+", " ", normalized)

        # V143.7 FIX: Ensure the result is lowercase for case-insensitive comparison
        return normalized.lower()

    def are_same_team(self, name1: str, name2: str) -> bool:
        """Check if two team names refer to the same team.

        V41.29: Enhanced with youth team collision detection.
        This is the P0 safety check that prevents matching first teams with youth teams.

        V41.35: Enhanced with empty string handling.

        Args:
            name1: First team name
            name2: Second team name

        Returns:
            True if the normalized names match AND they're not different tiers
            False otherwise (including youth team collisions or empty strings)
        """
        # V41.35 P0: Handle empty strings - they should not match
        if not name1 or not name2:
            return False

        # V41.29 P0: Check for youth team collision FIRST
        # This prevents "PSG" from matching "PSG II" or "Real Madrid" from matching "Real Madrid B"
        if _youth_detector.are_different_tiers(name1, name2):
            logger.warning(f"🚨 V41.29 BLOCKED: Youth team collision rejected: {name1} vs {name2}")
            return False

        # Original logic: normalize and compare
        return self.normalize(name1) == self.normalize(name2)

    def fuzzy_match(self, name1: str, name2: str) -> float:
        """Calculate fuzzy match score between two team names.

        V41.29: Enhanced with youth team penalty - reduces score for youth team matches.

        Uses multiple matching strategies:
        1. Normalized exact match (score = 100)
        2. Token Sort Ratio (handles word order differences)
        3. Partial Ratio (handles substring matches)
        4. Youth team penalty (V41.29)

        Args:
            name1: First team name
            name2: Second team name

        Returns:
            Match score between 0 and 100

        Example:
            >>> normalizer = TeamNameNormalizer()
            >>> normalizer.fuzzy_match("Man Utd", "Manchester United")
            95.0
            >>> normalizer.fuzzy_match("Nantes", "Nantes II")  # V41.29: youth penalty
            50.0
        """
        if not name1 or not name2:
            return 0.0

        # V41.29 P0: Check for youth team collision FIRST
        # Apply heavy penalty for youth team matches
        if _youth_detector.are_different_tiers(name1, name2):
            # Calculate base score but apply heavy penalty
            norm1 = self.normalize(name1)
            norm2 = self.normalize(name2)

            token_sort_score = fuzz.token_sort_ratio(norm1, norm2)
            partial_score = fuzz.partial_ratio(norm1, norm2)
            standard_score = fuzz.ratio(norm1, norm2)

            base_score = float(max(token_sort_score, partial_score, standard_score))

            # Apply 50% penalty for youth team matches
            # This ensures "Nantes" vs "Nantes II" returns ~50% instead of 100%
            penalty_score = base_score * 0.5

            logger.debug(
                f"🚨 Youth team penalty applied: {name1} vs {name2} "
                f"(base: {base_score:.1f}% -> penalty: {penalty_score:.1f}%)"
            )

            return penalty_score

        # Normalize both names first
        norm1 = self.normalize(name1)
        norm2 = self.normalize(name2)

        # Exact match after normalization
        if norm1 == norm2:
            return 100.0

        # Use fuzzy matching with multiple strategies
        # Token Sort Ratio: ignores word order
        token_sort_score = fuzz.token_sort_ratio(norm1, norm2)

        # Partial Ratio: for substring matches
        partial_score = fuzz.partial_ratio(norm1, norm2)

        # Standard Ratio
        standard_score = fuzz.ratio(norm1, norm2)

        # Calculate base score (highest of the three)
        base_score = float(max(token_sort_score, partial_score, standard_score))

        # ====================================================================
        # V41.35: Similarity Penalty - ABOLISHED by V41.790
        # ====================================================================
        # The V41.35 similarity penalty logic has been removed to allow
        # higher match success rates. The penalty was reducing scores to 60%
        # when teams shared common words but weren't exact matches.
        #
        # V41.790: Golden Sweep - Penalty Removal Strategy
        # - Core word matching takes priority (via relaxed_match)
        # - No automatic score reduction for common prefixes
        # - Relaxed_match provides controlled scoring with 95% cap
        #
        # Original V41.35 code (now disabled):
        # if base_score >= 80.0 and base_score < 95.0:
        #     # Check for common prefixes and apply penalty...
        #
        # Penalty example that is now DISABLED:
        # "Manchester United" vs "Manchester City": 86% -> 51.6% ❌
        # V41.790 behavior: "Manchester United" vs "Manchester City": 86% ✅
        # ====================================================================

        # Return the highest score (no penalty applied)
        return base_score

    def _extract_core_word(self, team_name: str) -> str:
        """V41.780: Extract the core word from a team name.

        The core word is defined as the first meaningful word in the team name,
        after normalization. This is used for Relaxed_Match mode to determine
        if two team names share the same core identity.

        Examples:
            "Arsenal" -> "arsenal"
            "Arsenal FC" -> "arsenal"
            "Manchester United" -> "manchester"
            "Manchester City" -> "manchester"
            "Man Utd" -> "man"
            "Tottenham Hotspur" -> "tottenham"
            "Wolves" -> "wolves"

        Args:
            team_name: Raw team name

        Returns:
            Core word in lowercase, or empty string if input is empty
        """
        if not team_name:
            return ""

        # Normalize the team name first
        normalized = self.normalize(team_name)

        # Split into words and return the first word (core word)
        words = normalized.split()
        if words:
            return words[0]

        return ""

    def relaxed_match(self, name1: str, name2: str) -> float:
        """V41.780: Relaxed matching mode for team names with enhanced tolerance.

        This method implements a more permissive matching strategy designed to
        maximize match success rate while maintaining reasonable accuracy:
        1. If core words are the same AND fuzzy score > 60%, force score to >= 80%
        2. Exact matches (after normalization) return 100%
        3. Youth team collisions are still protected (heavy penalty applied)

        Core Algorithm:
        - Extract core word from both names (first word after normalization)
        - If core words match AND fuzzy score > 60%, boost to >= 80%
        - If normalized names are exact match, return 100%
        - Apply youth team penalty if different tiers detected

        Args:
            name1: First team name
            name2: Second team name

        Returns:
            Match score between 0 and 100

        Examples:
            >>> normalizer = TeamNameNormalizer()
            >>> normalizer.relaxed_match("Man Utd", "Manchester United")
            100.0
            >>> normalizer.relaxed_match("Wolves", "Wolverhampton Wanderers")
            85.0
            >>> normalizer.relaxed_match("Arsenal", "Chelsea")
            25.0
        """
        # Handle empty strings
        if not name1 or not name2:
            return 0.0

        # V41.29 P0: Check for youth team collision FIRST
        # Apply heavy penalty for youth team matches (cannot be bypassed)
        if _youth_detector.are_different_tiers(name1, name2):
            # Calculate base score but apply heavy penalty
            norm1 = self.normalize(name1)
            norm2 = self.normalize(name2)

            token_sort_score = fuzz.token_sort_ratio(norm1, norm2)
            partial_score = fuzz.partial_ratio(norm1, norm2)
            standard_score = fuzz.ratio(norm1, norm2)

            base_score = float(max(token_sort_score, partial_score, standard_score))

            # Apply 50% penalty for youth team matches
            penalty_score = base_score * 0.5

            logger.debug(
                f"🚨 V41.780 Youth team penalty applied: {name1} vs {name2} "
                f"(base: {base_score:.1f}% -> penalty: {penalty_score:.1f}%)"
            )

            return penalty_score

        # Normalize both names
        norm1 = self.normalize(name1)
        norm2 = self.normalize(name2)

        # Exact match after normalization
        if norm1 == norm2:
            return 100.0

        # Extract core words for comparison
        core1 = self._extract_core_word(name1)
        core2 = self._extract_core_word(name2)

        # Calculate fuzzy score using multiple strategies
        token_sort_score = fuzz.token_sort_ratio(norm1, norm2)
        partial_score = fuzz.partial_ratio(norm1, norm2)
        standard_score = fuzz.ratio(norm1, norm2)

        base_score = float(max(token_sort_score, partial_score, standard_score))

        # V41.780: Relaxed matching rule
        # If core words are the same AND fuzzy score > 60%, boost to >= 80%
        if core1 and core2 and core1 == core2 and base_score > 60.0:
            # Boost the score to at least 80%, or keep original if higher
            relaxed_score = max(base_score, 80.0)

            # Cap at 95% to avoid false positives for different teams
            # (e.g., Manchester United vs Manchester City should not be 100%)
            relaxed_score = min(relaxed_score, 95.0)

            logger.debug(
                f"🎯 V41.780 Relaxed match applied: {name1} vs {name2} "
                f"(core: '{core1}' | base: {base_score:.1f}% -> relaxed: {relaxed_score:.1f}%)"
            )

            return relaxed_score

        # ====================================================================
        # V41.35: Similarity Penalty - ABOLISHED by V41.790 in relaxed_match
        # ====================================================================
        # The V41.35 similarity penalty has been removed from relaxed_match too.
        # This ensures consistent behavior between fuzzy_match and relaxed_match.
        #
        # V41.790: Golden Sweep - No penalty for common prefixes
        # - Core word matching (above) handles the boosting logic
        # - No additional penalty for shared words
        # ====================================================================

        # Return the base score (no penalty applied)
        return base_score

    def parse_team_slug_full_path(
        self,
        teams_part: str,
        db_team_names: set[str],
        threshold: float = 85.0,
    ) -> list[str] | None:
        """V143.9: Full-path trial matching parser with intelligent fallback.

        Core algorithm:
        1. Try all possible split points (A-B-C-D → A|BCD, AB|CD, ABC|D)
        2. For each split, find the best home_match and away_match
        3. Use are_same_team for pre-checking (avoid substring matching)
        4. Return the split with [highest combined score] AND [both teams above threshold]

        Cold Start Mode (V143.7):
        - When db_team_names is empty, uses heuristic parsing
        - Rejects obvious non-match URLs (league slugs, standings, etc.)
        - Allows reasonable team splits without database validation

        V143.9: Intelligent Fallback Mode:
        - When no split meets the threshold, use heuristic scoring
        - Prefers balanced splits (e.g., 1-2, 2-2 over 1-3, 3-1)
        - Avoids isolating common suffixes (united, city, utd, fc)

        Args:
            teams_part: Team portion from URL (without hash), e.g., "manchester-united-brentford"
            db_team_names: Set of team names from database (for fast lookup)
            threshold: Similarity threshold (0-100), default 85%

        Returns:
            [home_team_slug, away_team_slug] or None (if parsing failed)

        Example:
            >>> normalizer = TeamNameNormalizer()
            >>> db_names = {"Manchester United", "Brentford", "Arsenal"}
            >>> result = normalizer.parse_team_slug_full_path("manchester-united-brentford", db_names)
            >>> print(result)
            ['manchester-united', 'brentford']
        """
        parts = teams_part.split("-")

        # V143.7: Detect cold start mode (empty database)
        is_cold_start = len(db_team_names) == 0

        # Full-path trial matching
        best_split: list[str] | None = None
        best_combined_score = 0.0

        # V143.7: Common team suffixes that should not be isolated
        suffixes = {"united", "city", "utd", "fc", "afc", "cfc", "rc", "bilbao"}

        # V143.7: Cold start - reject obvious non-match URLs first
        if is_cold_start:
            # V143.8: Enhanced rejection - check if it's a league/season slug
            # Reject if contains 4-digit year (2000-2099) or league keywords
            has_year = any(
                len(part) == 4 and part.isdigit() and part.startswith("20") for part in parts
            )
            league_keywords = {
                "league",
                "ligue",
                "bundesliga",
                "serie",
                "premier",
                "laliga",
                "eredivisie",
            }
            has_league_keyword = any(keyword in teams_part.lower() for keyword in league_keywords)

            if has_year or has_league_keyword:
                logger.debug(f"[V143.8] Cold start: Rejected league/season slug: {teams_part}")
                return None

            # Reject navigation pages
            if teams_part.lower() in {"standings", "table", "outrights", "fixtures", "results"}:
                logger.debug(f"[V143.7] Cold start: Rejected navigation page: {teams_part}")
                return None

            # Reject single-word slugs
            if len(parts) < 2:
                logger.debug(f"[V143.7] Cold start: Rejected single-word slug: {teams_part}")
                return None

        # Try all possible split points
        for i in range(1, len(parts)):
            home_slug = "-".join(parts[:i])
            away_slug = "-".join(parts[i:])

            home_parts = home_slug.split("-")
            away_parts = away_slug.split("-")

            # V143.7: In cold start mode, use relaxed suffix protection
            if is_cold_start:
                # Reject if away is a single-word suffix (e.g., "utd" in "brentford-newcastle-utd")
                # This prevents splits like: ["brentford-newcastle", "utd"]
                if len(away_parts) == 1 and away_parts[0].lower() in suffixes:
                    continue
                # Reject if home is a single-word suffix
                if len(home_parts) == 1 and home_parts[0].lower() in suffixes:
                    continue
            else:
                # Original logic for warm start (with database)
                # Check if home split isolates a suffix
                if len(home_parts) > 1 and home_parts[-1].lower() in suffixes:
                    home_display = " ".join(word.title() for word in home_parts)
                    is_known_team = any(
                        self.are_same_team(home_display, db_name) for db_name in db_team_names
                    )
                    if not is_known_team:
                        continue

                # Check if away split isolates a suffix
                if len(away_parts) == 1 and away_parts[0].lower() in suffixes:
                    away_display = " ".join(word.title() for word in away_parts)
                    is_known_team = any(
                        self.are_same_team(away_display, db_name) for db_name in db_team_names
                    )
                    if not is_known_team:
                        continue

                if len(away_parts) > 1 and away_parts[0].lower() in suffixes:
                    away_display = " ".join(word.title() for word in away_parts)
                    is_known_team = any(
                        self.are_same_team(away_display, db_name) for db_name in db_team_names
                    )
                    if not is_known_team:
                        continue

            # Convert to display names
            home_display = " ".join(word.title() for word in home_slug.split("-"))
            away_display = " ".join(word.title() for word in away_slug.split("-"))

            # V143.7: Cold start mode - use heuristic scoring
            if is_cold_start:
                # In cold start, all reasonable splits get a default high score
                # Prefer splits that balance word count between home and away
                home_word_count = len(home_parts)
                away_word_count = len(away_parts)
                word_count_balance = abs(home_word_count - away_word_count)

                # Base score (lower is better for balance)
                combined_score = 100.0 - (word_count_balance * 5.0)

                # Minimum score threshold
                if combined_score < 85.0:
                    continue
            else:
                # Original warm start logic with database matching
                max_home_score = 0.0
                max_away_score = 0.0

                for db_name in db_team_names:
                    db_word_count = len(db_name.split())

                    if self.are_same_team(home_display, db_name):
                        if len(home_parts) == db_word_count:
                            base_score = 100.0
                        elif len(home_parts) < db_word_count and len(home_parts) >= 2:
                            base_score = 95.0
                        elif len(home_parts) == 1 and db_word_count >= 2:
                            base_score = 92.0
                        else:
                            base_score = 85.0
                        word_count_bonus = 1.0 + (db_word_count - len(home_parts)) * 0.1
                        max_home_score = max(max_home_score, base_score * word_count_bonus)
                    else:
                        norm_home = self.normalize(home_display)
                        norm_db = self.normalize(db_name)
                        token_sort_score = fuzz.token_sort_ratio(norm_home, norm_db)
                        standard_score = fuzz.ratio(norm_home, norm_db)
                        home_score = float(max(token_sort_score, standard_score))
                        word_count_ratio = db_word_count / len(home_parts)
                        if word_count_ratio >= 1.0:
                            home_score *= 1.0 + (word_count_ratio - 1.0) * 0.2
                        max_home_score = max(max_home_score, home_score)

                    # Same for away
                    if self.are_same_team(away_display, db_name):
                        db_word_count = len(db_name.split())
                        if len(away_parts) == db_word_count:
                            base_score = 100.0
                        elif len(away_parts) < db_word_count and len(away_parts) >= 2:
                            base_score = 95.0
                        elif len(away_parts) == 1 and db_word_count >= 2:
                            base_score = 92.0
                        else:
                            base_score = 85.0
                        word_count_bonus = 1.0 + (db_word_count - len(away_parts)) * 0.1
                        max_away_score = max(max_away_score, base_score * word_count_bonus)
                    else:
                        norm_away = self.normalize(away_display)
                        norm_db = self.normalize(db_name)
                        token_sort_score = fuzz.token_sort_ratio(norm_away, norm_db)
                        standard_score = fuzz.ratio(norm_away, norm_db)
                        away_score = float(max(token_sort_score, standard_score))
                        word_count_ratio = db_word_count / len(away_parts)
                        if word_count_ratio >= 1.0:
                            away_score *= 1.0 + (word_count_ratio - 1.0) * 0.2
                        max_away_score = max(max_away_score, away_score)

                # Calculate combined score
                combined_score = (max_home_score + max_away_score) / 2

                # Check if threshold is met
                if max_home_score < threshold or max_away_score < threshold:
                    continue

            if best_split is None or combined_score > best_combined_score:
                best_combined_score = combined_score
                best_split = [home_slug, away_slug]
            elif combined_score == best_combined_score:
                # Tie-breaker: prefer more balanced splits
                home_word_count = len(home_parts)
                away_word_count = len(away_parts)
                current_balance = abs(home_word_count - away_word_count)
                best_balance = (
                    abs(len(best_split[0].split("-")) - len(best_split[1].split("-")))
                    if best_split
                    else 999
                )
                if current_balance < best_balance:
                    best_split = [home_slug, away_slug]

        # V143.9: Intelligent Fallback Mode
        # If no split met the threshold, use heuristic scoring
        if best_split is None and not is_cold_start:
            logger.debug(
                f"[V143.9] No split met threshold, using intelligent fallback: {teams_part}"
            )

            # V143.9: Special handling for known patterns like "city-utd" or "name-united"
            # Check if there's a "utd" or "united" pattern that should be attached to the preceding word
            special_patterns = {
                "utd": ["sheffield", "newcastle"],  # sheffield-utd, newcastle-utd
                "united": ["manchester"],  # manchester-united
            }

            # Try all splits again with heuristic scoring
            for i in range(1, len(parts)):
                home_slug = "-".join(parts[:i])
                away_slug = "-".join(parts[i:])

                home_parts = home_slug.split("-")
                away_parts = away_slug.split("-")

                # V143.9: Enhanced suffix handling for known patterns
                # Check if away starts with a suffix that should be attached to home
                should_reject_split = False
                if len(away_parts) >= 1 and away_parts[0].lower() in suffixes:
                    suffix_to_attach = away_parts[0].lower()
                    # Check if this suffix + home's last word forms a known pattern
                    for pattern, cities in special_patterns.items():
                        if suffix_to_attach == pattern and len(home_parts) >= 1:
                            # Check if home's last word matches one of the known cities
                            if any(city.lower() == home_parts[-1].lower() for city in cities):
                                # This suffix should be attached to home, reject this split
                                should_reject_split = True
                                break

                if should_reject_split:
                    continue

                # Reject if away is a single-word suffix (general case)
                if len(away_parts) == 1 and away_parts[0].lower() in suffixes:
                    continue
                # Reject if home is a single-word suffix
                if len(home_parts) == 1 and home_parts[0].lower() in suffixes:
                    continue

                # Calculate heuristic score based on word count balance
                home_word_count = len(home_parts)
                away_word_count = len(away_parts)
                word_count_balance = abs(home_word_count - away_word_count)

                # Base score (lower is better for balance)
                combined_score = 100.0 - (word_count_balance * 5.0)

                # Minimum score threshold
                if combined_score < 85.0:
                    continue

                if best_split is None or combined_score > best_combined_score:
                    best_combined_score = combined_score
                    best_split = [home_slug, away_slug]
                elif combined_score == best_combined_score:
                    # Tie-breaker: prefer more balanced splits
                    current_balance = word_count_balance
                    best_balance = (
                        abs(len(best_split[0].split("-")) - len(best_split[1].split("-")))
                        if best_split
                        else 999
                    )
                    if current_balance < best_balance:
                        best_split = [home_slug, away_slug]

        if best_split:
            home_display = " ".join(word.title() for word in best_split[0].split("-"))
            away_display = " ".join(word.title() for word in best_split[1].split("-"))
            logger.info(
                f"  ✨ Team match: [{home_display}] vs [{away_display}] "
                f"(score: {int(best_combined_score)}%)"
            )
        else:
            logger.warning(f"  ⚠️  Failed to parse team slug: {teams_part}")

        return best_split


class VendorNameCleaner:
    """V117.1: Vendor/Bookmaker name cleaning utility.

    Provides consistent vendor name normalization for fuzzy matching
    in the market data extraction engine.

    Features:
        - Remove HTML entities and special characters
        - Strip "1x2" markers and suffixes
        - Remove non-alphabetic characters
        - Clean common suffixes (bet, odds, sports)
    """

    # Suffixes to remove
    SUFFIXES = ["bet", "odds", "sports", "bookmaker", "bookies", "sportsbook", "wagering", "gaming"]

    def __init__(self) -> None:
        """Initialize the vendor name cleaner."""
        self.suffix_pattern = re.compile(r"\s+(" + "|".join(self.SUFFIXES) + r")$", re.IGNORECASE)

    def clean(self, raw_name: str) -> str:
        """Clean and normalize a vendor name.

        Args:
            raw_name: Raw vendor name from the page

        Returns:
            Deep cleaned vendor name suitable for fuzzy matching
        """
        if not raw_name:
            return ""

        # Remove HTML entities and special characters
        cleaned = re.sub(r"&[a-z]+;", "", raw_name)
        cleaned = re.sub(r"<[^>]+>", "", cleaned)

        # Remove "1x2" markers (common suffix/prefix)
        cleaned = re.sub(r"1\s*x\s*2", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"1x2", "", cleaned, flags=re.IGNORECASE)

        # Remove all non-alphabetic characters (keep only letters and spaces)
        cleaned = re.sub(r"[^a-zA-Z\s]", "", cleaned)

        # Remove extra whitespace
        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        # Remove common non-provider suffixes
        return self.suffix_pattern.sub("", cleaned)


class LeagueUrlMapper:
    """V122.0: League to OddsPortal URL slug mapper.

    Provides mapping between league names and their corresponding OddsPortal
    URL slugs for league results page scraping.

    Features:
        - League name to URL slug mapping
        - Season format conversion (2023-2024 -> 2023-2024)
        - Top 20 European leagues coverage
        - Fuzzy matching for league name variations

    Example:
        >>> mapper = LeagueUrlMapper()
        >>> slug, country = mapper.get_league_slug("Premier League", "2023-2024")
        >>> print(f"{country}/{slug}/2023-2024/results/")
        england/premier-league/2023-2024/results/
    """

    # League name to (country, slug) mapping
    LEAGUE_MAPPINGS: dict[str, tuple[str, str]] = {
        # English Leagues
        "premier league": ("england", "premier-league"),
        "english premier league": ("england", "premier-league"),
        "epl": ("england", "premier-league"),
        "championship": ("england", "championship"),
        "efl cup": ("england", "efl-cup"),
        "fa cup": ("england", "fa-cup"),
        # Spanish Leagues
        "la liga": ("spain", "laliga"),
        "primera divisin": ("spain", "laliga"),
        "segunda divisin": ("spain", "segunda-division"),
        "copa del rey": ("spain", "copa-del-rey"),
        # Italian Leagues
        "serie a": ("italy", "serie-a"),
        "serie b": ("italy", "serie-b"),
        "coppa italia": ("italy", "coppa-italia"),
        # German Leagues
        "bundesliga": ("germany", "bundesliga"),
        "1. bundesliga": ("germany", "bundesliga"),
        "2. bundesliga": ("germany", "2-bundesliga"),
        "dfb pokal": ("germany", "dfb-pokal"),
        # French Leagues
        "ligue 1": ("france", "ligue-1"),
        "ligue 2": ("france", "ligue-2"),
        "coupe de france": ("france", "coupe-de-france"),
        # Portuguese Leagues
        "primeira liga": ("portugal", "primeira-liga"),
        "taça de portugal": ("portugal", "tacca-de-portugal"),
        "taça da liga": ("portugal", "tacca-da-liga"),
        # Dutch Leagues
        "eredivisie": ("netherlands", "eredivisie"),
        "eerste divisie": ("netherlands", "eerste-divisie"),
        "knvb beker": ("netherlands", "knvb-beker"),
        # Belgian Leagues
        "first division a": ("belgium", "first-division-a"),
        "jupiler pro league": ("belgium", "first-division-a"),
        "belgian first division a": ("belgium", "first-division-a"),
        "belgian cup": ("belgium", "belgian-cup"),
        # Scottish Leagues
        "premiership": ("scotland", "premiership"),
        "scottish premiership": ("scotland", "premiership"),
        "scottish championship": ("scotland", "championship"),
        "scottish cup": ("scotland", "scottish-cup"),
        # Turkish Leagues
        "super lig": ("turkey", "super-lig"),
        "turkish super lig": ("turkey", "super-lig"),
        # Greek Leagues
        "super league greece": ("greece", "super-league"),
        "greek super league": ("greece", "super-league"),
        # Russian Leagues
        "russian premier league": ("russia", "premier-league"),
        # Ukrainian Leagues
        "ukrainian premier league": ("ukraine", "premier-league"),
        # Polish Leagues
        "ekstraklasa": ("poland", "ekstraklasa"),
        # Czech Leagues
        "first league": ("czech-republic", "1-liga"),
        "czech first league": ("czech-republic", "1-liga"),
        # Austrian Leagues
        "austrian bundesliga": ("austria", "bundesliga"),
        # Swiss Leagues
        "super league": ("switzerland", "super-league"),
        "swiss super league": ("switzerland", "super-league"),
        # Danish Leagues
        "superliga": ("denmark", "superliga"),
        "danish superliga": ("denmark", "superliga"),
        # Norwegian Leagues
        "eliteserien": ("norway", "eliteserien"),
        "norwegian eliteserien": ("norway", "eliteserien"),
        # Swedish Leagues
        "allsvenskan": ("sweden", "allsvenskan"),
        # Brazilian Leagues
        "brasileirao": ("brazil", "serie-a"),
        "brazilian serie a": ("brazil", "serie-a"),
        # Argentine Leagues
        "primera division": ("argentina", "primera-division"),
        "argentine primera division": ("argentina", "primera-division"),
        # Mexican Leagues
        "liga mx": ("mexico", "liga-mx"),
        "mexican primera division": ("mexico", "liga-mx"),
        # USA/Canada Leagues
        "major league soccer": ("usa", "mls"),
        "mls": ("usa", "mls"),
        # Chinese Leagues
        "chinese super league": ("china", "super-league"),
        # Japanese Leagues
        "j1 league": ("japan", "j1-league"),
        "j league": ("japan", "j1-league"),
        # Korean Leagues
        "k league 1": ("south-korea", "k-league-1"),
        # Australian A-League
        "a-league": ("australia", "a-league"),
        # International Competitions
        "champions league": ("europe", "champions-league"),
        "uefa champions league": ("europe", "champions-league"),
        "europa league": ("europe", "europa-league"),
        "uefa europa league": ("europe", "europa-league"),
        "conference league": ("europe", "conference-league"),
        "uefa conference league": ("europe", "conference-league"),
        "euro championship": ("europe", "euro"),
        "european championship": ("europe", "euro"),
        "world cup": ("world", "world-cup"),
        "copa america": ("south-america", "copa-america"),
    }

    def __init__(self) -> None:
        """Initialize the league URL mapper."""
        # Build reverse lookup for fuzzy matching
        self._build_reverse_index()

    def _build_reverse_index(self) -> None:
        """Build reverse index for fuzzy matching."""
        self._index: dict[str, tuple[str, str]] = {}
        for league_name, (country, slug) in self.LEAGUE_MAPPINGS.items():
            # Store normalized name
            normalized = league_name.lower().strip()
            self._index[normalized] = (country, slug)

    def get_league_slug(self, league_name: str, season: str) -> tuple[str, str] | None:
        """Get OddsPortal URL slug for a league.

        Args:
            league_name: League name (e.g., "Premier League")
            season: Season string (e.g., "2023-2024")

        Returns:
            Tuple of (country, slug) if found, None otherwise

        Example:
            >>> mapper = LeagueUrlMapper()
            >>> result = mapper.get_league_slug("Premier League", "2023-2024")
            >>> print(result)
            ('england', 'premier-league')
        """
        if not league_name:
            return None

        # Normalize league name for lookup
        normalized = league_name.lower().strip()

        # Direct lookup
        if normalized in self._index:
            return self._index[normalized]

        # Fuzzy matching - try partial matches
        for key, value in self._index.items():
            if normalized in key or key in normalized:
                return value

        # Not found
        logger.warning(f"League slug not found for: {league_name}")
        return None

    def construct_results_url(
        self, league_name: str, season: str, base_url: str = "https://www.oddsportal.com"
    ) -> str | None:
        """Construct the full results page URL.

        Args:
            league_name: League name
            season: Season string (e.g., "2023-2024")
            base_url: Base URL (default: OddsPortal)

        Returns:
            Full URL to the results page if found, None otherwise

        Example:
            >>> mapper = LeagueUrlMapper()
            >>> url = mapper.construct_results_url("Premier League", "2023-2024")
            >>> print(url)
            https://www.oddsportal.com/football/england/premier-league-2023-2024/results/
        """
        result = self.get_league_slug(league_name, season)
        if not result:
            return None

        country, slug = result

        # Format season for URL (e.g., "2023-2024" stays as is)
        season_formatted = season.strip()

        return f"{base_url}/football/{country}/{slug}-{season_formatted}/results/"

    def get_all_mappings(self) -> dict[str, tuple[str, str]]:
        """Get all league mappings.

        Returns:
            Dictionary mapping league names to (country, slug) tuples
        """
        return self.LEAGUE_MAPPINGS.copy()

    def is_supported(self, league_name: str) -> bool:
        """Check if a league is supported.

        Args:
            league_name: League name to check

        Returns:
            True if the league is in the mapping, False otherwise
        """
        normalized = league_name.lower().strip()

        # Direct check
        if normalized in self._index:
            return True

        # Fuzzy check
        return any(normalized in key or key in normalized for key in self._index)


def normalize_team_list(team_names: list[str]) -> list[str]:
    """Normalize a list of team names.

    Args:
        team_names: List of raw team names

    Returns:
        List of normalized team names
    """
    normalizer = TeamNameNormalizer()
    return [normalizer.normalize(name) for name in team_names]


def normalize_vendor_list(vendor_names: list[str]) -> list[str]:
    """Clean a list of vendor names.

    Args:
        vendor_names: List of raw vendor names

    Returns:
        List of cleaned vendor names
    """
    cleaner = VendorNameCleaner()
    return [cleaner.clean(name) for name in vendor_names]
