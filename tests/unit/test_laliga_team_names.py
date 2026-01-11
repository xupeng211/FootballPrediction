#!/usr/bin/env python3
"""
Unit Test: La Liga Team Name Parsing (TDD Green Phase)

测试目标：验证西甲特有多词队名的 URL 解析和匹配逻辑

TDD 流程：
1. Red Phase: 测试失败（功能未实现/有 Bug）✅
2. Green Phase: 修复 Bug，测试通过 ⏳
3. Refactor Phase: 优化代码（可选）

西甲特有问题：
- Real Sociedad → URL: real-sociedad
- Atletico Madrid → URL: atl-madrid
- Athletic Bilbao → URL: ath-bilbao
- Real Betis → URL: betis (不含 'Real')

Bug 案例：
URL: real-sociedad-almeria
错误解析: home='real', away='sociedad'
错误匹配: Real Madrid vs Real Sociedad

正确解析: home='Real Sociedad', away='Almeria'

Author: 高级数据平台架构师 (Principal Architect)
Date: 2026-01-11
Version: V32.2 (La Liga Parser Hardened)
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple
from unittest.mock import Mock, patch

import pytest

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# 导入生产代码
from scripts.ops.harvest_league_urls import (
    parse_match_url_with_league_teams,
    team_name_to_slug,
    get_league_team_names,
)


# ============================================================================
# Test Data: La Liga Team Names and URL Slugs
# ============================================================================

# 使用 team_name_to_slug 函数生成 slug 映射
_LALIGA_TEAM_NAMES = [
    "Real Sociedad",
    "Atletico Madrid",
    "Athletic Bilbao",
    "Athletic Club",
    "Real Betis",
    "Real Madrid",
    "Real Valladolid",
    "Barcelona",
    "Sevilla",
    "Valencia",
    "Villarreal",
    "Real Zaragoza",
    "Girona",
    "Almeria",
    "Osasuna",
    "Getafe",
    "Levante",
    "Rayo Vallecano",
    "Celta Vigo",
    "Mallorca",
    "Las Palmas",
    "Alaves",
    "Cadiz",
    "Elche",
    "Espanyol",
    "Valladolid",
]

# 动态生成 slug 映射
LALIGA_TEAMS = {team: team_name_to_slug(team) for team in _LALIGA_TEAM_NAMES}

# Test cases for URL parsing
LALIGA_URL_TEST_CASES = [
    # (url_slug, expected_home, expected_away, description)
    # 核心多词队名测试 - 这些是关键 Bug 修复
    ("real-sociedad-almeria", "Real Sociedad", "Almeria", "Multi-word home team"),
    ("girona-atl-madrid", "Girona", "Atletico Madrid", "Multi-word away team"),
    ("osasuna-ath-bilbao", "Osasuna", "Athletic Bilbao", "Both multi-word (alt)"),
    ("ath-bilbao-celta-vigo", "Athletic Bilbao", "Celta Vigo", "Athletic Club variant"),
    ("valencia-rayo-vallecano", "Valencia", "Rayo Vallecano", "Multi-word away"),
]


# ============================================================================
# Test Cases
# ============================================================================

class TestLaLigaTeamNameParsing:
    """西甲队名解析测试 (TDD Green Phase)"""

    @patch('scripts.ops.harvest_league_urls.get_league_team_names')
    def test_real_sociedad_almeria_critical_case(self, mock_get_teams):
        """关键测试用例：real-sociedad-almeria 不能解析为 'Real' vs 'Sociedad'"""
        mock_get_teams.return_value = LALIGA_TEAMS

        url = "https://www.oddsportal.com/football/spain/laliga/real-sociedad-almeria-Q3cJZcV1/"
        home, away, confidence = parse_match_url_with_league_teams(url, "La Liga")

        # 确保不会错误匹配到 'Real' 和 'Sociedad'
        assert home != "Real", "主队不能是 'Real'，应该是 'Real Sociedad'"
        assert away != "Sociedad", "客队不能是 'Sociedad'，应该是 'Almeria'"

        # 正确匹配
        assert home == "Real Sociedad", f"主队应该是 'Real Sociedad'，实际是 '{home}'"
        assert away == "Almeria", f"客队应该是 'Almeria'，实际是 '{away}'"
        assert confidence >= 0.9, f"关键案例应该有高置信度: {confidence}"

    @patch('scripts.ops.harvest_league_urls.get_league_team_names')
    def test_atletico_madrid_shortened_url(self, mock_get_teams):
        """测试：atl-madrid 应该解析为 Atletico Madrid"""
        mock_get_teams.return_value = LALIGA_TEAMS

        url = "https://www.oddsportal.com/football/spain/laliga/girona-atl-madrid-dhsK6cBj/"
        home, away, confidence = parse_match_url_with_league_teams(url, "La Liga")

        assert home == "Girona", f"主队应该是 'Girona'，实际是 '{home}'"
        assert away == "Atletico Madrid", f"客队应该是 'Atletico Madrid'，实际是 '{away}'"
        assert confidence >= 0.7, f"置信度过低: {confidence}"

    @patch('scripts.ops.harvest_league_urls.get_league_team_names')
    def test_real_betis_without_prefix(self, mock_get_teams):
        """测试：betis 应该解析为 Real Betis（URL 常省略 'Real' 前缀）"""
        mock_get_teams.return_value = LALIGA_TEAMS

        url = "https://www.oddsportal.com/football/spain/laliga/betis-getafe-j5yJbj2o/"
        home, away, confidence = parse_match_url_with_league_teams(url, "La Liga")

        assert home == "Real Betis", f"主队应该是 'Real Betis'，实际是 '{home}'"
        assert away == "Getafe", f"客队应该是 'Getafe'，实际是 '{away}'"
        assert confidence >= 0.7, f"置信度过低: {confidence}"

    @patch('scripts.ops.harvest_league_urls.get_league_team_names')
    def test_multi_word_teams_ath_bilbao_celta(self, mock_get_teams):
        """测试：ath-bilbao-celta-vigo 正确解析"""
        mock_get_teams.return_value = LALIGA_TEAMS

        url = "https://www.oddsportal.com/football/spain/laliga/ath-bilbao-celta-vigo-xyz123/"
        home, away, confidence = parse_match_url_with_league_teams(url, "La Liga")

        assert home == "Athletic Bilbao", f"主队应该是 'Athletic Bilbao'，实际是 '{home}'"
        assert away == "Celta Vigo", f"客队应该是 'Celta Vigo'，实际是 '{away}'"
        assert confidence >= 0.7, f"置信度过低: {confidence}"

    @patch('scripts.ops.harvest_league_urls.get_league_team_names')
    def test_multi_word_teams_valencia_rayo(self, mock_get_teams):
        """测试：valencia-rayo-vallecano 正确解析"""
        mock_get_teams.return_value = LALIGA_TEAMS

        url = "https://www.oddsportal.com/football/spain/laliga/valencia-rayo-vallecano-xyz123/"
        home, away, confidence = parse_match_url_with_league_teams(url, "La Liga")

        assert home == "Valencia", f"主队应该是 'Valencia'，实际是 '{home}'"
        assert away == "Rayo Vallecano", f"客队应该是 'Rayo Vallecano'，实际是 '{away}'"
        assert confidence >= 0.7, f"置信度过低: {confidence}"


class TestTeamNameSlugMapping:
    """测试队名到 URL slug 的转换"""

    def test_team_name_to_slug_mappings(self):
        """测试：队名正确转换为 URL slug"""
        # 验证特殊映射
        assert team_name_to_slug("Atletico Madrid") == "atl-madrid"
        assert team_name_to_slug("Athletic Bilbao") == "ath-bilbao"
        assert team_name_to_slug("Athletic Club") == "ath-bilbao"
        assert team_name_to_slug("Real Betis") == "betis"

        # 验证标准映射
        assert team_name_to_slug("Real Sociedad") == "real-sociedad"
        assert team_name_to_slug("Real Madrid") == "real-madrid"
        assert team_name_to_slug("Barcelona") == "barcelona"
        assert team_name_to_slug("Rayo Vallecano") == "rayo-vallecano"


class TestLaLigaURLPatterns:
    """西甲 URL 模式测试"""

    def test_url_format_standard(self):
        """测试：标准 URL 格式验证（V32.2 更新）"""
        standard_urls = [
            "/football/spain/laliga-2023-2024/girona-atl-madrid-dhsK6cBj/",
            "/football/spain/laliga-2022-2023/osasuna-ath-bilbao-KpTZf81A/",
        ]

        import re

        # V32.2: 更宽松的模式匹配
        pattern = r'/football/[^/]+/[^/]+/[^/]+-[^/]+-([a-zA-Z0-9]{8,12})/'

        for url in standard_urls:
            match = re.search(pattern, url)
            assert match is not None, f"URL 格式不匹配: {url}"
            hash_part = match.group(1)
            assert len(hash_part) >= 8, f"哈希长度不足: {hash_part}"


class TestLaLigaIntegration:
    """西甲数据采集集成测试"""

    @patch('scripts.ops.harvest_league_urls.get_league_team_names')
    def test_malformed_data_detection(self, mock_get_teams):
        """测试：能检测到 malformed 数据

        案例：记录 ID 4223
        - URL: real-sociedad-almeria
        - 错误存储: Real Madrid vs Real Sociedad
        - 正确存储: Real Sociedad vs Almeria
        """
        mock_get_teams.return_value = LALIGA_TEAMS

        # 模拟数据库记录
        malformed_record = {
            "id": 4223,
            "url": "https://www.oddsportal.com/football/spain/laliga-2022-2023/real-sociedad-almeria-Q3cJZcV1/",
            "stored_home": "Real Madrid",  # 错误
            "stored_away": "Real Sociedad",  # 错误
        }

        # 解析 URL
        parsed_home, parsed_away, _ = parse_match_url_with_league_teams(
            malformed_record["url"],
            "La Liga"
        )

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
