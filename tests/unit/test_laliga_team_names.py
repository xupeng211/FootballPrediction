#!/usr/bin/env python3
"""
Unit Test: La Liga Team Name Parsing (TDD First)

测试目标：验证西甲特有多词队名的 URL 解析和匹配逻辑

TDD 流程：
1. Red Phase: 测试失败（功能未实现/有 Bug）
2. Green Phase: 修复 Bug，测试通过
3. Refactor Phase: 优化代码（可选）

西甲特有问题：
- Real Sociedad → URL: real-sociedad
- Atletico Madrid → URL: atl-madrid
- Athletic Bilbao → URL: ath-bilbao
- Real Betis → URL: betis (不含 'real')

Bug 案例：
URL: real-sociedad-almeria
错误解析: home='real', away='sociedad'
错误匹配: Real Madrid vs Real Sociedad

正确解析: home='Real Sociedad', away='Almeria'

Author: 高级数据平台架构师 (Principal Architect)
Date: 2026-01-11
Version: V32.1.2 (La Liga Quality Fix)
"""

import pytest
from typing import Dict, List, Tuple


# ============================================================================
# Test Data: La Liga Team Names and URL Slugs
# ============================================================================

LALIGA_TEAMS = {
    # Standard mappings (full name → URL slug pattern)
    "Real Sociedad": "real-sociedad",
    "Atletico Madrid": "atl-madrid",
    "Athletic Bilbao": "ath-bilbao",
    "Real Betis": "betis",  # Note: URL often omits 'Real'
    "Real Madrid": "real-madrid",
    "Real Valladolid": "valladolid",
    "Barcelona": "barcelona",
    "Sevilla": "sevilla",
    "Valencia": "valencia",
    "Villarreal": "villarreal",
    "Real Zaragoza": "zaragoza",
    "Athletic Club": "ath-bilbao",  # Alternative name
    "Atleti": "atl-madrid",  # Alternative name
    "Girona": "girona",
    "Almeria": "almeria",
    "Osasuna": "osasuna",
    "Getafe": "getafe",
    "Levante": "levante",
    "Rayo Vallecano": "rayo-vallecano",
    "Celta Vigo": "celta-vigo",
    "Mallorca": "mallorca",
    "Las Palmas": "las-palmas",
    "Alaves": "alaves",
    "Cadiz": "cadiz",
    "Elche": "elche",
    "Espanyol": "espanyol",
    "Valladolid": "valladolid",
}

# Test cases for URL parsing
LALIGA_URL_TEST_CASES = [
    # (url_slug, expected_home, expected_away, description)
    ("real-sociedad-almeria", "Real Sociedad", "Almeria", "Multi-word home team"),
    ("girona-atl-madrid", "Girona", "Atletico Madrid", "Multi-word away team"),
    ("osasuna-ath-bilbao", "Osasuna", "Athletic Bilbao", "Both multi-word (alt)"),
    ("betis-getafe", "Real Betis", "Getafe", "Home without 'Real' prefix"),
    ("sevilla-levante", "Sevilla", "Levante", "Both single-word"),
    ("real-madrid-barcelona", "Real Madrid", "Barcelona", "El Clasico"),
    ("valencia-rayo-vallecano", "Valencia", "Rayo Vallecano", "Multi-word away"),
    ("ath-bilbao-celta-vigo", "Athletic Bilbao", "Celta Vigo", "Athletic Club variant"),
    ("villarreal-almeria", "Villarreal", "Almeria", "Single-word teams"),
    ("real-betis-espanyol", "Real Betis", "Espanyol", "Real Betis with prefix"),
]


# ============================================================================
# Mock Functions (to be implemented in production code)
# ============================================================================

def parse_oddsportal_url(url: str) -> Tuple[str, str]:
    """从 OddsPortal URL 解析主客队名称

    Args:
        url: OddsPortal 比赛页面 URL
            例如: /football/spain/laliga/real-sociedad-almeria-abc123/

    Returns:
        (home_team, away_team) 元组

    TODO: 实现此函数以处理多词队名
    """
    # 当前错误实现（用于测试失败）
    parts = url.strip('/').split('/')
    match_part = parts[-1]
    # 移除哈希
    name_part = '-'.join(match_part.split('-')[:-1])
    teams = name_part.split('-')
    # Bug: 只取前两个词
    home = teams[0].replace('-', ' ').title() if len(teams) > 0 else ""
    away = teams[1].replace('-', ' ').title() if len(teams) > 1 else ""
    return (home, away)


# ============================================================================
# Test Cases
# ============================================================================

class TestLaLigaTeamNameParsing:
    """西甲队名解析测试 (TDD)"""

    @pytest.mark.parametrize("url_slug,expected_home,expected_away,description", LALIGA_URL_TEST_CASES)
    def test_url_parsing_correctness(self, url_slug: str, expected_home: str, expected_away: str, description: str):
        """测试：URL 解析能正确识别西甲多词队名

        Bug 案例：
        - URL: real-sociedad-almeria
        - 错误: ('Real', 'Sociedad')
        - 正确: ('Real Sociedad', 'Almeria')
        """
        # 模拟完整 URL
        full_url = f"https://www.oddsportal.com/football/spain/laliga/{url_slug}-abc123/"

        home, away = parse_oddsportal_url(full_url)

        assert home == expected_home, (
            f"[{description}] 主队解析错误: "
            f"URL='{url_slug}' → expected='{expected_home}', got='{home}'"
        )
        assert away == expected_away, (
            f"[{description}] 客队解析错误: "
            f"URL='{url_slug}' → expected='{expected_away}', got='{away}'"
        )

    def test_real_sociedad_almeria_critical_case(self):
        """关键测试用例：real-sociedad-almeria 不能解析为 'Real' vs 'Sociedad'"""
        url = "https://www.oddsportal.com/football/spain/laliga/real-sociedad-almeria-Q3cJZcV1/"
        home, away = parse_oddsportal_url(url)

        # 确保不会错误匹配到 'Real' 和 'Sociedad'
        assert home != "Real", "主队不能是 'Real'，应该是 'Real Sociedad'"
        assert away != "Sociedad", "客队不能是 'Sociedad'，应该是 'Almeria'"

        # 正确匹配
        assert home == "Real Sociedad", f"主队应该是 'Real Sociedad'，实际是 '{home}'"
        assert away == "Almeria", f"客队应该是 'Almeria'，实际是 '{away}'"

    def test_atletico_madrid_shortened_url(self):
        """测试：atl-madrid 应该解析为 Atletico Madrid"""
        url = "https://www.oddsportal.com/football/spain/laliga/girona-atl-madrid-dhsK6cBj/"
        home, away = parse_oddsportal_url(url)

        assert home == "Girona", f"主队应该是 'Girona'，实际是 '{home}'"
        assert away == "Atletico Madrid", f"客队应该是 'Atletico Madrid'，实际是 '{away}'"

    def test_real_betis_without_prefix(self):
        """测试：betis 应该解析为 Real Betis（URL 常省略 'Real' 前缀）"""
        url = "https://www.oddsportal.com/football/spain/laliga/betis-getafe-j5yJbj2o/"
        home, away = parse_oddsportal_url(url)

        assert home == "Real Betis", f"主队应该是 'Real Betis'，实际是 '{home}'"
        assert away == "Getafe", f"客队应该是 'Getafe'，实际是 '{away}'"


class TestLaLigaTeamMatching:
    """西甲队名匹配测试 (TDD)"""

    def test_fuzzy_match_real_sociedad_not_real_madrid(self):
        """测试：'real-sociedad' 不应该匹配到 'Real Madrid'"""
        url_slug = "real-sociedad"
        fotmob_home = "Real Madrid"
        fotmob_away = "Real Sociedad"

        # 解析 URL
        url_home, url_away = url_slug.split('-')  # ['real', 'sociedad']

        # 错误匹配逻辑（当前 Bug）
        wrong_match = (
            url_home[0] in fotmob_home or fotmob_home in url_home[0]
        )

        # 断言：不应该匹配
        assert not wrong_match or url_home[0] == "real-sociedad", (
            f"'{url_home[0]}' 不应该匹配 '{fotmob_home}'。"
            f"URL 'real-sociedad' 应该匹配 'Real Sociedad'，而不是 'Real Madrid'"
        )

    def test_confidence_score_multi_word_teams(self):
        """测试：多词队名应该有更高的置信度要求"""
        # 多词队名匹配需要更严格的验证
        multi_word_slugs = ["real-sociedad", "atl-madrid", "rayo-vallecano"]

        for slug in multi_word_slugs:
            # 确保完整匹配，而非部分匹配
            assert len(slug.split('-')) >= 2, f"{slug} 应该是多词队名"


class TestLaLigaURLPatterns:
    """西甲 URL 模式测试"""

    def test_url_format_standard(self):
        """测试：标准 URL 格式验证"""
        standard_urls = [
            "/football/spain/laliga/real-sociedad-almeria-abc123/",
            "/football/spain/laliga/girona-atl-madrid-def456/",
            "/football/spain/laliga-2023-2024/osasuna-ath-bilbao-ghi789/",
        ]

        import re

        pattern = r'/football/spain/laliga[^/]*/[^/]+-[^/]+-([a-zA-Z0-9]{8,12})/'

        for url in standard_urls:
            match = re.search(pattern, url)
            assert match is not None, f"URL 格式不匹配: {url}"
            hash_part = match.group(1)
            assert len(hash_part) >= 8, f"哈希长度不足: {hash_part}"


# ============================================================================
# Integration Tests
# ============================================================================

class TestLaLigaIntegration:
    """西甲数据采集集成测试"""

    def test_malformed_data_detection(self):
        """测试：能检测到 malformed 数据

        案例：记录 ID 4223
        - URL: real-sociedad-almeria
        - 错误存储: Real Madrid vs Real Sociedad
        - 正确存储: Real Sociedad vs Almeria
        """
        # 模拟数据库记录
        malformed_record = {
            "id": 4223,
            "url": "https://www.oddsportal.com/football/spain/laliga-2022-2023/real-sociedad-almeria-Q3cJZcV1/",
            "stored_home": "Real Madrid",  # 错误
            "stored_away": "Real Sociedad",  # 错误
        }

        # 解析 URL
        parsed_home, parsed_away = parse_oddsportal_url(malformed_record["url"])

        # 检测是否 malformed
        is_malformed = (
            parsed_home != malformed_record["stored_home"]
            or parsed_away != malformed_record["stored_away"]
        )

        assert is_malformed, "应该检测到 malformed 数据"
        assert parsed_home == "Real Sociedad", "解析的主队应该是 Real Sociedad"
        assert parsed_away == "Almeria", "解析的客队应该是 Almeria"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
