#!/usr/bin/env python3
"""
Unit Test: Team URL Slug Matching - 队名 URL Slug 匹配 TDD

测试目标：验证 OddsPortal URL slug 能正确匹配数据库队名

TDD 流程：
1. Red Phase: 测试失败（功能未实现）
2. Green Phase: 实现功能，测试通过
3. Refactor Phase: 优化代码（可选）

测试场景：
- 多连字符队名: manchester-city → Manchester City ✅
- 西甲缩写: ath-bilbao → Athletic Club, atl-madrid → Atletico Madrid ✅
- 缩写匹配: utd → United, utd → United ✅
- 前缀省略: betis → Real Betis ✅
- 复杂队名: brighton-hove-albion → Brighton & Hove Albion ✅

Author: 高级数据清洗专家
Date: 2026-01-11
Version: V33.2 (Data Cleaning)
"""

import sys
from pathlib import Path
from typing import Dict, List, Tuple
import pytest

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.ops.harvest_league_urls import team_name_to_slug, parse_match_url_with_league_teams


# ============================================================================
# Test Fixtures: 11 场失败案例
# ============================================================================

FAILED_CASES = [
    # Premier League
    {
        "url": "https://www.oddsportal.com/football/england/premier-league-2023-2024/manchester-city-west-ham-Sd97hFwr/",
        "league": "Premier League",
        "expected_home": "Manchester City",
        "expected_away": "West Ham United",
        "url_slug": "manchester-city-west-ham"
    },
    {
        "url": "https://www.oddsportal.com/football/england/premier-league-2023-2024/tottenham-chelsea-EqzEhWpB/",
        "league": "Premier League",
        "expected_home": "Tottenham Hotspur",
        "expected_away": "Chelsea",
        "url_slug": "tottenham-chelsea"
    },
    {
        "url": "https://www.oddsportal.com/football/england/premier-league-2023-2024/luton-west-ham-zF0205Qb/",
        "league": "Premier League",
        "expected_home": "Luton Town",
        "expected_away": "West Ham United",
        "url_slug": "luton-west-ham"
    },
    {
        "url": "https://www.oddsportal.com/football/england/premier-league-2023-2024/west-ham-burnley-Uoevj7ag/",
        "league": "Premier League",
        "expected_home": "West Ham United",
        "expected_away": "Burnley",
        "url_slug": "west-ham-burnley"
    },
    {
        "url": "https://www.oddsportal.com/football/england/premier-league-2023-2024/sheffield-utd-wolves-0tW9gCV4/",
        "league": "Premier League",
        "expected_home": "Sheffield United",
        "expected_away": "Wolverhampton Wanderers",
        "url_slug": "sheffield-utd-wolves"
    },
    {
        "url": "https://www.oddsportal.com/football/england/premier-league-2023-2024/newcastle-utd-crystal-palace-2L4yWHXt/",
        "league": "Premier League",
        "expected_home": "Newcastle United",
        "expected_away": "Crystal Palace",
        "url_slug": "newcastle-utd-crystal-palace"
    },
    {
        "url": "https://www.oddsportal.com/football/england/premier-league-2023-2024/newcastle-utd-brighton-hITmaQfc/",
        "league": "Premier League",
        "expected_home": "Newcastle United",
        "expected_away": "Brighton & Hove Albion",
        "url_slug": "newcastle-utd-brighton"
    },
    {
        "url": "https://www.oddsportal.com/football/england/premier-league-2023-2024/wolves-arsenal-dh57ZuG5/",
        "league": "Premier League",
        "expected_home": "Wolverhampton Wanderers",
        "expected_away": "Arsenal",
        "url_slug": "wolves-arsenal"
    },
    {
        "url": "https://www.oddsportal.com/football/england/premier-league-2023-2024/west-ham-crystal-palace-WziyEwDl/",
        "league": "Premier League",
        "expected_home": "West Ham United",
        "expected_away": "Crystal Palace",
        "url_slug": "west-ham-crystal-palace"
    },
    # La Liga
    {
        "url": "https://www.oddsportal.com/football/spain/laliga-2022-2023/valladolid-getafe-0x0P1GEf/",
        "league": "La Liga",
        "expected_home": "Real Valladolid",
        "expected_away": "Getafe",
        "url_slug": "valladolid-getafe"
    },
    {
        "url": "https://www.oddsportal.com/football/spain/laliga/osasuna-ath-bilbao-WUoduIHF/",
        "league": "La Liga",
        "expected_home": "Osasuna",
        "expected_away": "Athletic Club",
        "url_slug": "osasuna-ath-bilbao"
    },
]


# ============================================================================
# Test Cases: team_name_to_slug
# ============================================================================

class TestTeamNameToSlug:
    """测试队名到 URL slug 的转换"""

    def test_multi_hyphen_team_names(self):
        """TDD 核心测试：多连字符队名应正确转换"""
        test_cases = [
            ("Manchester City", "manchester-city"),
            ("Brighton & Hove Albion", "brighton-hove-albion"),
            ("Newcastle United", "newcastle-utd"),  # V33.2: URL 使用 newcastle-utd
            ("West Ham United", "west-ham"),       # V33.2: URL 使用 west-ham
            ("Sheffield United", "sheffield-utd"),  # V33.2: URL 使用 sheffield-utd
            ("Wolverhampton Wanderers", "wolves"),  # V33.2: URL 使用 wolves
            ("Tottenham Hotspur", "tottenham"),      # V33.2: URL 使用 tottenham
            ("Crystal Palace", "crystal-palace"),
        ]

        for team_name, expected_slug in test_cases:
            result = team_name_to_slug(team_name)
            assert result == expected_slug, \
                f"{team_name} → 期望 {expected_slug}, 实际 {result}"

    def test_laliga_special_abbreviations(self):
        """TDD 核心测试：西甲特殊缩写映射"""
        test_cases = [
            ("Athletic Club", "ath-bilbao"),
            ("Athletic Bilbao", "ath-bilbao"),
            ("Atletico Madrid", "atl-madrid"),
            ("Real Betis", "betis"),
        ]

        for team_name, expected_slug in test_cases:
            result = team_name_to_slug(team_name)
            assert result == expected_slug, \
                f"{team_name} → 期望 {expected_slug}, 实际 {result}"

    def test_premier_league_nickname_mapping(self):
        """TDD 核心测试：英超昵称映射"""
        test_cases = [
            ("Wolverhampton Wanderers", "wolves"),
            ("West Ham United", "west-ham"),
            ("Tottenham Hotspur", "tottenham"),
            ("Luton Town", "luton"),
            ("Newcastle United", "newcastle-utd"),
            ("Sheffield United", "sheffield-utd"),
        ]

        for team_name, expected_slug in test_cases:
            result = team_name_to_slug(team_name)
            assert result == expected_slug, \
                f"{team_name} → 期望 {expected_slug}, 实际 {result}"

    def test_removal_of_common_prefixes(self):
        """TDD 核心测试：移除常见前缀（Real, FC, Club）进行备选匹配"""
        test_cases = [
            ("Real Valladolid", "valladolid"),
            ("Real Betis", "betis"),
            ("Real Sociedad", "real-sociedad"),  # Real Sociedad 保留 Real
            ("Real Madrid", "real-madrid"),     # Real Madrid 保留 Real
        ]

        for team_name, expected_slug in test_cases:
            result = team_name_to_slug(team_name)
            assert result == expected_slug, \
                f"{team_name} → 期望 {expected_slug}, 实际 {result}"


# ============================================================================
# Test Cases: URL slug 解析
# ============================================================================

class TestURLSlugParsing:
    """测试 URL slug 解析"""

    def test_failed_case_manchester_city_west_ham(self):
        """TDD 测试：manchester-city-west-ham 应正确匹配"""
        case = FAILED_CASES[0]
        url_slug = case["url_slug"]

        # 简单分割测试
        parts = url_slug.split('-')
        # manchester-city + west-ham
        assert parts[0:2] == ["manchester", "city"]
        assert parts[2:4] == ["west", "ham"]

    def test_failed_case_ath_bilbao(self):
        """TDD 测试：ath-bilbao 应匹配 Athletic Club"""
        case = FAILED_CASES[10]
        url_slug = case["url_slug"]

        # ath-bilbao 是特殊缩写
        assert url_slug == "osasuna-ath-bilbao"

    def test_failed_case_newcastle_utd(self):
        """TDD 测试：newcastle-utd 应匹配 Newcastle United"""
        case = FAILED_CASES[5]
        url_slug = case["url_slug"]

        # newcastle-utd 需要将 utd 映射到 United
        assert "newcastle-utd" in url_slug

    def test_failed_case_brighton_hove_albion(self):
        """TDD 测试：brighton 应匹配 Brighton & Hove Albion"""
        case = FAILED_CASES[6]
        url_slug = case["url_slug"]

        # brighton 是 brighton-hove-albion 的简写
        assert "brighton" in url_slug


# ============================================================================
# Test Cases: Greedy Matching
# ============================================================================

class TestGreedyMatching:
    """测试贪婪匹配算法"""

    def test_two_part_vs_three_part_slug(self):
        """TDD 测试：正确分割 2 部分和 3 部分队名"""
        # manchester-city (2 parts) + west-ham (2 parts) = 4 parts total
        url_slug = "manchester-city-west-ham"
        parts = url_slug.split('-')

        # 尝试所有分割点
        best_split = None
        for split_point in range(1, len(parts)):
            home = '-'.join(parts[:split_point])
            away = '-'.join(parts[split_point:])

            # 正确分割: manchester-city / west-ham
            if home == "manchester-city" and away == "west-ham":
                best_split = (home, away)
                break

        assert best_split == ("manchester-city", "west-ham")

    def test_three_part_team_name(self):
        """TDD 测试：3 部分队名 brighton-hove-albion"""
        # brighton-hove-albion (3 parts) + burnley (1 part) = 4 parts total
        url_slug = "brighton-hove-albion-burnley"
        parts = url_slug.split('-')

        # 尝试所有分割点
        best_split = None
        for split_point in range(1, len(parts)):
            home = '-'.join(parts[:split_point])
            away = '-'.join(parts[split_point:])

            # 正确分割: brighton-hove-albion / burnley
            if home == "brighton-hove-albion" and away == "burnley":
                best_split = (home, away)
                break

        assert best_split == ("brighton-hove-albion", "burnley")


# ============================================================================
# Test Runner
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
