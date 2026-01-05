#!/usr/bin/env python3
"""V117.1 Text Processing Utilities.

This module provides text normalization and processing utilities for the
Football Prediction system, including team name normalization, vendor name
cleaning, fuzzy matching support, and league URL mapping.

Usage:
    from src.utils.text_processor import (
        TeamNameNormalizer,
        VendorNameCleaner,
        LeagueUrlMapper
    )

    # Normalize team names
    normalizer = TeamNameNormalizer()
    normalized = normalizer.normalize("Man Utd")

    # Clean vendor names
    cleaner = VendorNameCleaner()
    cleaned = cleaner.clean("Pinnacle Sports")

    # Map league names to OddsPortal URL slugs (V122.0)
    mapper = LeagueUrlMapper()
    url = mapper.construct_results_url("Premier League", "2023-2024")
"""

import re
import logging
from typing import Optional
from thefuzz import fuzz

logger = logging.getLogger(__name__)


class TeamNameNormalizer:
    """V117.1: Team name normalization utility.

    Provides consistent team name normalization across the entire project,
    handling abbreviations, common variations, and international naming conventions.

    Features:
        - Abbreviation expansion (Man Utd -> Manchester United)
        - Common variation handling (Arsenal FC -> Arsenal)
        - International name mapping (Bayern Munich -> Bayern Munchen)
        - Whitespace and character normalization
    """

    # Common team name abbreviations and variations
    TEAM_NAME_MAPPINGS = {
        # English Premier League
        "man utd": "manchester united",
        "man united": "manchester united",
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

        # Spanish La Liga
        "atleti": "atletico madrid",
        "atletico": "atletico madrid",
        "real madrid": "real madrid",
        "barca": "barcelona",
        "fc barcelona": "barcelona",
        "real betis": "real betis",
        "real sociedad": "real sociedad",
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
    SUFFIXES_TO_STRIP = [
        r"\s+fc$", r"\s+f\.c\.$",
        r"\s+afcd?$", r"\s+a\.f\.c\.d?$",
        r"\s+cf$", r"\s+c\.f\.$",
        r"\s+sc$", r"\s+s\.c\.$",
        r"\s+ac$", r"\s+a\.c\.$",
        r"\s+sd$", r"\s+s\.d\.$",
        r"\s+united$", r"\s+city$",
        r"\s+town$", r"\s+athletic$",
    ]

    def __init__(self) -> None:
        """Initialize the team name normalizer."""
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        """Compile regex patterns for better performance."""
        self.suffix_patterns = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in self.SUFFIXES_TO_STRIP
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
        normalized = re.sub(r"\s+", " ", normalized)  # Normalize whitespace

        # Step 2: Remove common suffixes
        for pattern in self.suffix_patterns:
            normalized = pattern.sub("", normalized)

        # Step 3: Convert to lowercase for mapping
        normalized_lower = normalized.lower()

        # Step 4: Apply team name mappings
        if normalized_lower in self.TEAM_NAME_MAPPINGS:
            normalized = self.TEAM_NAME_MAPPINGS[normalized_lower]
        else:
            # Case-insensitive search for partial matches
            for key, value in self.TEAM_NAME_MAPPINGS.items():
                if key in normalized_lower or normalized_lower in key:
                    normalized = value
                    break

        # Step 5: Final cleanup
        normalized = normalized.strip()
        normalized = re.sub(r"\s+", " ", normalized)

        return normalized

    def are_same_team(self, name1: str, name2: str) -> bool:
        """Check if two team names refer to the same team.

        Args:
            name1: First team name
            name2: Second team name

        Returns:
            True if the normalized names match, False otherwise
        """
        return self.normalize(name1) == self.normalize(name2)

    def fuzzy_match(self, name1: str, name2: str) -> float:
        """Calculate fuzzy match score between two team names.

        Uses multiple matching strategies:
        1. Normalized exact match (score = 100)
        2. Token Sort Ratio (handles word order differences)
        3. Partial Ratio (handles substring matches)

        Args:
            name1: First team name
            name2: Second team name

        Returns:
            Match score between 0 and 100

        Example:
            >>> normalizer = TeamNameNormalizer()
            >>> normalizer.fuzzy_match("Man Utd", "Manchester United")
            95.0
        """
        if not name1 or not name2:
            return 0.0

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

        # Return the highest score
        return float(max(token_sort_score, partial_score, standard_score))


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
    SUFFIXES = [
        "bet", "odds", "sports", "bookmaker", "bookies",
        "sportsbook", "wagering", "gaming"
    ]

    def __init__(self) -> None:
        """Initialize the vendor name cleaner."""
        self.suffix_pattern = re.compile(
            r"\s+(" + "|".join(self.SUFFIXES) + r")$",
            re.IGNORECASE
        )

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
        cleaned = re.sub(r'&[a-z]+;', '', raw_name)
        cleaned = re.sub(r'<[^>]+>', '', cleaned)

        # Remove "1x2" markers (common suffix/prefix)
        cleaned = re.sub(r'1\s*x\s*2', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'1x2', '', cleaned, flags=re.IGNORECASE)

        # Remove all non-alphabetic characters (keep only letters and spaces)
        cleaned = re.sub(r'[^a-zA-Z\s]', '', cleaned)

        # Remove extra whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()

        # Remove common non-provider suffixes
        cleaned = self.suffix_pattern.sub('', cleaned)

        return cleaned


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
        "bundesliga": ("austria", "bundesliga"),
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
        "serie a": ("brazil", "serie-a"),
        "brasileirao": ("brazil", "serie-a"),

        # Argentine Leagues
        "primera division": ("argentina", "primera-division"),
        "argentine primera division": ("argentina", "primera-division"),

        # Mexican Leagues
        "liga mx": ("mexico", "liga-mx"),
        "primera division": ("mexico", "liga-mx"),

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

    def get_league_slug(
        self,
        league_name: str,
        season: str
    ) -> tuple[str, str] | None:
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
        self,
        league_name: str,
        season: str,
        base_url: str = "https://www.oddsportal.com"
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
        for key in self._index.keys():
            if normalized in key or key in normalized:
                return True

        return False


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
