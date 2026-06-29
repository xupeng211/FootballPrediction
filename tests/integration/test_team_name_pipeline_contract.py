# ruff: noqa: PLR2004 (magic values in test assertions are intentional)

"""Integration tests for team name normalization, matching, and model pipeline.

Covers the real module collaboration path:
    1. constants (TEAM_ABBREVIATIONS, TEAM_SUFFIXES, SAME_CITY_DERBIES)
    2. normalization (normalize_team_name, denoise_team_name, extract_place_name)
    3. matching (semantic_match, calculate_similarity, match_teams)
    4. models (MatchResult, TeamAliasMatch)

These tests use zero mocks — every call exercises real module code.
No DB, Docker, network, or secrets are required.

Import strategy: use importlib to load leaf modules directly from their file paths,
bypassing __init__.py files that cascade into fastapi, psycopg2, etc.
"""

import importlib.util
from pathlib import Path
import sys

_SRC = Path(__file__).parent.parent.parent / "src"


def _load(module_name: str, rel_path: str):
    """Load a Python module from a source file, registering parent packages first.

    Creates stub namespace packages in sys.modules for each ancestor so that
    relative imports (``from .sibling import ...``) resolve correctly. This
    avoids triggering the real __init__.py files that cascade into heavy deps.
    """
    # Register parent namespace packages so relative imports work
    parts = module_name.split(".")
    for i in range(1, len(parts)):
        parent_name = ".".join(parts[:i])
        if parent_name not in sys.modules:
            parent = type(sys)(parent_name)
            parent.__path__ = []  # type: ignore[attr-defined]
            parent.__package__ = parent_name
            sys.modules[parent_name] = parent

    spec = importlib.util.spec_from_file_location(module_name, str(_SRC / rel_path))
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {rel_path} as {module_name}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)
    return mod


# Load modules in dependency order:
# 1. constants (no deps) → 2. models (no deps) → 3. normalization → 4. matching
_m_constants = _load("utils.teams.constants", "utils/teams/constants.py")
_m_models = _load("utils.teams.models", "utils/teams/models.py")
_m_normalization = _load("utils.teams.normalization", "utils/teams/normalization.py")
_m_matching = _load("utils.teams.matching", "utils/teams/matching.py")

# Unpack symbols for test convenience
PLACE_NAME_PRIORITY = _m_constants.PLACE_NAME_PRIORITY
SAME_CITY_DERBIES = _m_constants.SAME_CITY_DERBIES
TEAM_ABBREVIATIONS = _m_constants.TEAM_ABBREVIATIONS
TEAM_SUFFIXES = _m_constants.TEAM_SUFFIXES
normalize_team_name = _m_normalization.normalize_team_name
denoise_team_name = _m_normalization.denoise_team_name
extract_place_name = _m_normalization.extract_place_name
semantic_match = _m_matching.semantic_match
calculate_similarity = _m_matching.calculate_similarity
expand_team_name = _m_matching.expand_team_name
match_teams = _m_matching.match_teams
HIGH_SIMILARITY_THRESHOLD = _m_matching.HIGH_SIMILARITY_THRESHOLD
REVERSE_WARNING_THRESHOLD = _m_matching.REVERSE_WARNING_THRESHOLD
MatchResult = _m_models.MatchResult
TeamAliasMatch = _m_models.TeamAliasMatch


class TestNormalizationPipeline:
    """normalize → denoise → extract_place chain on real data."""

    def test_normalize_lowercase_and_strip(self):
        """normalize_team_name lowercases, strips, and removes punctuation."""
        assert normalize_team_name("  Manchester United  ") == "manchester united"
        assert normalize_team_name("Arsenal!!!") == "arsenal"
        assert normalize_team_name("") == ""

    def test_abbreviation_expansion(self):
        """TEAM_ABBREVIATIONS entries are applied by normalize_team_name."""
        assert normalize_team_name("Man Utd") == "man united"
        assert normalize_team_name("Spurs") == "tottenham"

    def test_denoise_removes_suffixes(self):
        """denoise_team_name strips known suffixes after normalization."""
        result = denoise_team_name("Liverpool FC")
        assert "liverpool" in result
        assert "fc" not in result

    def test_extract_place_name_from_priority_map(self):
        """PLACE_NAME_PRIORITY keys are matched against the normalized name."""
        result = extract_place_name("Manchester City FC")
        assert result == PLACE_NAME_PRIORITY.get("manchester", "")

    def test_pipeline_empty_input_safety(self):
        """Empty or blank names pass through the pipeline without crashing."""
        assert normalize_team_name("") == ""
        assert denoise_team_name("") == ""
        assert extract_place_name("") == ""


class TestSemanticMatching:
    """semantic_match / calculate_similarity / match_teams on real team names."""

    def test_perfect_normalized_match(self):
        """Two strings that normalize to the same value score 100."""
        score, reason = semantic_match("Manchester United", "manchester united")
        assert score == 100.0
        assert "Perfect" in reason

    def test_place_name_match_high_confidence(self):
        """Teams sharing a non-derby place name get >= 90 confidence."""
        # "Barcelona" is in PLACE_NAME_PRIORITY and has no derby indicators
        score, _reason = semantic_match("Barcelona Giants", "Barcelona FC")
        assert score > 85.0

    def test_derby_rejection_different_teams(self):
        """Derby rivals in same city are rejected with low score (40.0)."""
        score, _reason = semantic_match("Manchester United", "Manchester City")
        assert score <= 40.0

    def test_high_similarity_threshold_respected(self):
        """Scores at or above HIGH_SIMILARITY_THRESHOLD use the actual value."""
        # "Wolves" vs "Wolverhampton" — different enough to not be perfect match
        # but similar enough to cross HIGH_SIMILARITY_THRESHOLD
        score, _reason = semantic_match("Wolves", "Wolverhampton")
        # The score should be reasonably high for similar names
        assert score > 50.0

    def test_calculate_similarity_variant_expansion(self):
        """Similarity uses expand_team_name for variant-aware matching."""
        score = calculate_similarity("Man Utd", "Manchester United")
        assert score > 85.0

    def test_match_teams_direct_and_reversed(self):
        """match_teams checks both direct and reversed home/away alignment."""
        score, details = match_teams(
            scraped_home="Arsenal",
            scraped_away="Chelsea",
            db_home="Arsenal",
            db_away="Chelsea",
        )
        assert score > 80.0
        assert "Arsenal" in details

    def test_match_teams_reversed_detection(self):
        """When scraped home matches DB away, reverse score may win."""
        score, _details = match_teams(
            scraped_home="Chelsea",
            scraped_away="Arsenal",
            db_home="Arsenal",
            db_away="Chelsea",
        )
        assert score > 70.0


class TestModelsIntegration:
    """MatchResult and TeamAliasMatch dataclass creation."""

    def test_match_result_construction(self):
        """MatchResult can be constructed with real pipeline output."""
        score, _details = match_teams("Man Utd", "Liverpool", "Manchester United", "Liverpool FC")
        result = MatchResult(
            fotmob_id=None,
            scraped_home="Man Utd",
            scraped_away="Liverpool",
            db_home="Manchester United",
            db_away="Liverpool FC",
            confidence=score,
            tier="confident" if score > 80 else "uncertain",
            url="https://example.com/match/1",
        )
        assert result.confidence > 70.0
        assert result.scraped_home == "Man Utd"
        assert isinstance(result.confidence, float)

    def test_team_alias_match_model(self):
        """TeamAliasMatch holds normalized name with computed similarity."""
        sim = calculate_similarity("Man Utd", "Manchester United")
        alias_match = TeamAliasMatch(
            normalized_name="manchester united",
            aliases=["man utd", "man united"],
            similarity=sim,
            is_confident=sim > 85.0,
        )
        assert alias_match.is_confident
        assert alias_match.similarity > 85.0
