#!/usr/bin/env python3
"""兼容旧模块内置测试入口。"""
# ruff: noqa: PLR2004

from __future__ import annotations

import logging
import unittest

from .matching import calculate_similarity, expand_team_name, match_teams, semantic_match
from .normalization import denoise_team_name, extract_place_name, normalize_team_name
from .url_tools import determine_tier, is_safe_confidence

logger = logging.getLogger(__name__)


class _TeamAliasTests:
    """内部单元测试（用于验证别名引擎功能）。"""

    @staticmethod
    def run_tests() -> bool:
        class TestTeamAlias(unittest.TestCase):
            def test_normalize_abbreviations(self) -> None:
                assert normalize_team_name("Man Utd") == "man united"
                assert normalize_team_name("Spurs") == "tottenham"
                assert normalize_team_name("WHU") == "west ham"

            def test_expand_aliases(self) -> None:
                variants = expand_team_name("man utd")
                assert "manchester united" in variants

            def test_similarity_perfect(self) -> None:
                assert calculate_similarity("Arsenal", "Arsenal") == 100.0

            def test_similarity_abbreviation(self) -> None:
                assert calculate_similarity("Man Utd", "Manchester United") >= 95.0

            def test_match_teams(self) -> None:
                score, _details = match_teams("Arsenal", "Chelsea", "Arsenal", "Chelsea")
                assert score == 100.0

            def test_tier_classification(self) -> None:
                assert determine_tier(95) == "HIGH"
                assert determine_tier(80) == "MEDIUM"
                assert determine_tier(50) == "LOW"

            def test_safe_confidence(self) -> None:
                assert is_safe_confidence(90)
                assert not is_safe_confidence(80)

            def test_v39_4_denoise_team_name(self) -> None:
                assert denoise_team_name("Manchester United FC") == "manchester"
                assert denoise_team_name("Newcastle United") == "newcastle"
                assert denoise_team_name("Wolverhampton Wanderers") == "wolverhampton"
                assert denoise_team_name("Brighton & Hove Albion") == "brighton hove"

            def test_v39_4_extract_place_name(self) -> None:
                assert extract_place_name("Manchester United") == "manchester"
                assert extract_place_name("Newcastle United") == "newcastle"
                assert extract_place_name("Inter Milan") == "milan"
                assert extract_place_name("Brighton & Hove Albion") == "brighton"

            def test_v39_4_semantic_match_newcastle(self) -> None:
                confidence, details = semantic_match("Newcastle United", "Newcastle")
                assert confidence >= 98.0, details

            def test_v39_4_semantic_match_manchester(self) -> None:
                confidence, details = semantic_match("Manchester United", "Manchester")
                assert confidence >= 95.0, details

            def test_v39_4_semantic_match_wolves(self) -> None:
                confidence, details = semantic_match("Wolverhampton Wanderers", "Wolves")
                assert confidence >= 95.0, details

            def test_v39_4_semantic_match_crystal_palace(self) -> None:
                confidence, details = semantic_match("Crystal Palace", "Crystal")
                assert confidence >= 90.0, details

            def test_v39_4_semantic_match_nottingham_forest(self) -> None:
                confidence, details = semantic_match("Nottingham Forest", "Nottingham")
                assert confidence >= 95.0, details

            def test_v39_4_semantic_match_brighton(self) -> None:
                confidence, details = semantic_match("Brighton & Hove Albion", "Brighton")
                assert confidence >= 90.0, details

            def test_v39_4_semantic_match_west_bromwich(self) -> None:
                confidence, details = semantic_match("West Bromwich Albion", "West Bromwich")
                assert confidence >= 95.0, details

        suite = unittest.TestLoader().loadTestsFromTestCase(TestTeamAlias)
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        return result.wasSuccessful()


def run_module_tests() -> int:
    logging.basicConfig(level=logging.INFO)
    success = _TeamAliasTests.run_tests()
    if success:
        logger.info("✅ 所有单元测试通过")
        return 0
    logger.error("❌ 单元测试失败")
    return 1
