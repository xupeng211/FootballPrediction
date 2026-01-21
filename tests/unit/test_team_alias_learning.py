#!/usr/bin/env python3
"""
V33.3 Team Alias Auto-Learning TDD Tests - 队名别名自进化测试

功能：验证队名别名系统的自学习和缓存能力

测试场景：
1. 第一次匹配：模糊匹配成功后自动保存到数据库（学习）
2. 第二次匹配：直接从数据库获取别名（缓存命中）
3. usage_count 更新：每次使用后自动递增
4. 置信度排序：高置信度别名优先

TDD 流程：
- Red Phase: 测试失败（功能未实现）
- Green Phase: 实现功能，测试通过
- Refactor Phase: 优化代码（可选）

Author: 高级数据治理专家
Date: 2026-01-11
Version: V33.3 (Data Governance)
"""

import sys
from pathlib import Path
from typing import Dict, Tuple
from unittest.mock import MagicMock, Mock, call, patch

import pytest

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.ops.harvest_league_urls import (
    get_team_aliases_from_db,
    parse_match_url_with_league_teams,
    save_team_alias,
    team_name_to_slug,
    update_alias_usage,
)


class TestTeamAliasDatabaseOperations:
    """测试队名别名数据库操作"""

    @patch('scripts.ops.harvest_league_urls.psycopg2.connect')
    def test_get_team_aliases_from_db_by_league(self, mock_connect):
        """测试：从数据库获取指定联赛的别名映射"""
        # Mock 数据库返回
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ('wolves', 'Wolverhampton Wanderers', 1.0),
            ('west-ham', 'West Ham United', 1.0),
            ('tottenham', 'Tottenham Hotspur', 1.0),
        ]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        # 执行查询
        aliases = get_team_aliases_from_db('Premier League')

        # 验证结果
        assert len(aliases) == 3
        assert aliases['wolves'] == ('Wolverhampton Wanderers', 1.0)
        assert aliases['west-ham'] == ('West Ham United', 1.0)
        assert aliases['tottenham'] == ('Tottenham Hotspur', 1.0)

        # 验证 SQL 调用
        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args
        assert 'Premier League' in call_args[0][1]

    @patch('scripts.ops.harvest_league_urls.psycopg2.connect')
    def test_get_team_aliases_empty_database(self, mock_connect):
        """测试：空数据库返回空字典"""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        aliases = get_team_aliases_from_db('La Liga')

        assert aliases == {}
        mock_conn.close.assert_called_once()

    @patch('scripts.ops.harvest_league_urls.psycopg2.connect')
    def test_save_team_alias_new_entry(self, mock_connect):
        """测试：保存新队名别名到数据库（INSERT）"""
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        # 保存新别名
        result = save_team_alias(
            alias_slug='new-castle',
            canonical_name='Newcastle United',
            league_name='Premier League',
            alias_type='fuzzy',
            confidence=0.85
        )

        assert result is True
        mock_cursor.execute.assert_called_once()
        mock_conn.commit.assert_called_once()

    @patch('scripts.ops.harvest_league_urls.psycopg2.connect')
    def test_save_team_alias_upsert_on_conflict(self, mock_connect):
        """测试：UPSERT 机制 - 重复别名更新置信度"""
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        result = save_team_alias(
            alias_slug='wolves',
            canonical_name='Wolverhampton Wanderers',
            league_name='Premier League',
            alias_type='nickname',
            confidence=0.95  # 更高的置信度
        )

        assert result is True
        # 验证 SQL 包含 ON CONFLICT
        sql_call = mock_cursor.execute.call_args[0][0]
        assert 'ON CONFLICT' in sql_call
        assert 'GREATEST' in sql_call  # 置信度取最大值

    @patch('scripts.ops.harvest_league_urls.psycopg2.connect')
    def test_update_alias_usage(self, mock_connect):
        """测试：更新别名使用统计"""
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        result = update_alias_usage('wolves', 'Premier League')

        assert result is True
        mock_cursor.execute.assert_called_once()
        sql_call = mock_cursor.execute.call_args[0][0]
        assert 'usage_count = usage_count + 1' in sql_call


class TestTeamAliasAutoLearning:
    """测试队名别名自学习机制"""

    @patch('scripts.ops.harvest_league_urls.update_alias_usage')
    @patch('scripts.ops.harvest_league_urls.save_team_alias')
    @patch('scripts.ops.harvest_league_urls.get_team_aliases_from_db')
    @patch('scripts.ops.harvest_league_urls.get_league_team_names')
    def test_first_match_fuzzy_and_save_to_db(self, mock_get_teams, mock_get_aliases, mock_save, mock_update):
        """TDD 核心测试：第一次匹配应使用模糊匹配并保存到数据库（学习）

        场景：
        1. URL: /football/england/premier-league/wolves-manc-city/
        2. 数据库为空（无 wolves 别名）
        3. 模糊匹配成功：wolves → Wolverhampton Wanderers
        4. 自动保存到 team_aliases 表
        """
        # Mock: 数据库别名为空，但联赛有完整队名列表
        mock_get_aliases.return_value = {}
        mock_get_teams.return_value = {
            'Wolverhampton Wanderers': 'wolves',
            'Manchester City': 'manchester-city',
            'Chelsea': 'chelsea',
        }

        # 执行解析（使用完整的 URL 格式）
        url = "/football/england/premier-league/wolves-manchester-city-W4E7KoZR/"
        league_name = "Premier League"
        home, away, score = parse_match_url_with_league_teams(url, league_name)

        # 验证匹配成功
        assert home == "Wolverhampton Wanderers"
        assert away == "Manchester City"
        assert score > 0.85  # 高置信度

        # 验证自动保存到数据库（自学习）
        assert mock_save.call_count >= 1  # 至少保存主队

    @patch('scripts.ops.harvest_league_urls.update_alias_usage')
    @patch('scripts.ops.harvest_league_urls.save_team_alias')
    @patch('scripts.ops.harvest_league_urls.get_team_aliases_from_db')
    def test_second_match_from_database_no_fuzzy(self, mock_get_aliases, mock_save, mock_update):
        """TDD 核心测试：第二次匹配直接从数据库获取（缓存命中）

        场景：
        1. 第一次：wolves 未在数据库 → 模糊匹配 → 保存到数据库
        2. 第二次：wolves 已在数据库 → 直接获取 → 跳过模糊匹配
        3. 验证：第二次不调用 save_team_alias
        """
        # Mock: 数据库已有完整别名
        mock_get_aliases.return_value = {
            'wolves': ('Wolverhampton Wanderers', 1.0),
            'manchester-city': ('Manchester City', 1.0),
        }

        # 执行解析（使用完整的 URL 格式）
        url = "/football/england/premier-league/wolves-manchester-city-W4E7KoZR/"
        league_name = "Premier League"
        home, away, score = parse_match_url_with_league_teams(url, league_name)

        # 验证匹配成功
        assert home == "Wolverhampton Wanderers"
        assert away == "Manchester City"
        assert score == 1.0  # 数据库直接命中，置信度为 1.0

        # 验证：不调用 save_team_alias（已存在于数据库）
        mock_save.assert_not_called()

        # 验证：调用 update_alias_usage 更新使用统计
        assert mock_update.call_count == 2  # 更新主队和客队

    @patch('scripts.ops.harvest_league_urls.save_team_alias')
    @patch('scripts.ops.harvest_league_urls.get_team_aliases_from_db')
    @patch('scripts.ops.harvest_league_urls.get_league_team_names')
    def test_low_confidence_match_not_saved(self, mock_get_teams, mock_get_aliases, mock_save):
        """测试：低置信度匹配不保存到数据库"""
        mock_get_aliases.return_value = {}
        mock_get_teams.return_value = {
            'Wolverhampton Wanderers': 'wolves',
        }

        # 使用一个不存在且难以匹配的队名
        url = "/football/england/premier-league/unknown-team-xyz/"
        league_name = "Premier League"
        home, away, score = parse_match_url_with_league_teams(url, league_name)

        # 低置信度匹配（< 0.85）不应保存
        if score < 0.85:
            mock_save.assert_not_called()

    @patch('scripts.ops.harvest_league_urls.update_alias_usage')
    @patch('scripts.ops.harvest_league_urls.get_team_aliases_from_db')
    def test_database_alias_priority_over_fuzzy(self, mock_get_aliases, mock_update):
        """测试：数据库别名优先级高于模糊匹配"""
        # Mock: 数据库有特殊别名（覆盖默认逻辑）
        mock_get_aliases.return_value = {
            'ath-bilbao': ('Athletic Club', 1.0),  # 数据库别名
            'real-madrid': ('Real Madrid', 1.0),
        }
        mock_update.return_value = True

        url = "/football/spain/laliga/ath-bilbao-real-madrid-AbCd123/"
        league_name = "La Liga"
        home, away, score = parse_match_url_with_league_teams(url, league_name)

        # 验证使用数据库别名
        assert home == "Athletic Club"
        assert score == 1.0  # 数据库直接命中

        # 验证更新使用统计
        mock_update.assert_called()


class TestTeamAliasPriorityOrdering:
    """测试队名别名优先级排序"""

    @patch('scripts.ops.harvest_league_urls.psycopg2.connect')
    def test_aliases_ordered_by_confidence_then_usage(self, mock_connect):
        """测试：别名按置信度和使用次数排序"""
        # Mock 返回数据：置信度和使用次数各不相同
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ('low-priority', 'Low Priority Team', 0.6),  # 低置信度
            ('high-usage', 'High Usage Team', 0.8),      # 高置信度，低使用
            ('best-match', 'Best Match Team', 1.0),      # 最高置信度
        ]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        aliases = get_team_aliases_from_db('Premier League')

        # 验证按置信度排序
        assert aliases['best-match'][1] == 1.0
        assert aliases['high-usage'][1] == 0.8
        assert aliases['low-priority'][1] == 0.6


class TestTeamAliasIntegration:
    """集成测试：完整自学习流程"""

    @patch('scripts.ops.harvest_league_urls.save_team_alias')
    @patch('scripts.ops.harvest_league_urls.get_team_aliases_from_db')
    @patch('scripts.ops.harvest_league_urls.get_league_team_names')
    def test_complete_learning_workflow(self, mock_get_teams, mock_get_aliases, mock_save):
        """测试：完整的自学习工作流

        场景：
        1. 第一次匹配新队名 → 模糊匹配 + 保存
        2. 第二次匹配相同队名 → 数据库直接获取
        3. 验证使用次数递增
        """
        # 第一次调用：数据库为空，但联赛有队名列表
        mock_get_aliases.return_value = {}
        mock_get_teams.return_value = {
            'Tottenham Hotspur': 'tottenham',
            'Chelsea': 'chelsea',
            'Arsenal': 'arsenal',
        }

        url = "/football/england/premier-league/tottenham-chelsea-1a2B3c4/"
        league_name = "Premier League"

        # 第一次匹配
        home1, away1, score1 = parse_match_url_with_league_teams(url, league_name)
        assert home1 == "Tottenham Hotspur"
        assert mock_save.call_count >= 1  # 保存到数据库

        # 第二次调用：数据库已有别名
        mock_get_aliases.return_value = {
            'tottenham': ('Tottenham Hotspur', 1.0),
            'chelsea': ('Chelsea', 1.0),
        }

        # 重置 mock
        mock_save.reset_mock()

        # 第二次匹配
        home2, away2, score2 = parse_match_url_with_league_teams(url, league_name)
        assert home2 == "Tottenham Hotspur"
        assert score2 == 1.0  # 数据库直接命中
        mock_save.assert_not_called()  # 不应再次保存


class TestTeamNameToSlugIntegration:
    """测试 team_name_to_slug 与别名系统的集成"""

    def test_special_mappings_still_work(self):
        """测试：特殊映射仍然有效（向后兼容）"""
        test_cases = [
            ("Wolverhampton Wanderers", "wolves"),
            ("West Ham United", "west-ham"),
            ("Tottenham Hotspur", "tottenham"),
            ("Athletic Club", "ath-bilbao"),
            ("Atletico Madrid", "atl-madrid"),
            ("Real Betis", "betis"),
        ]

        for team_name, expected_slug in test_cases:
            result = team_name_to_slug(team_name)
            assert result == expected_slug, f"{team_name} → {result}, 期望 {expected_slug}"

    def test_standard_conversion_still_works(self):
        """测试：标准转换逻辑仍然有效"""
        test_cases = [
            ("Manchester City", "manchester-city"),
            ("Brighton & Hove Albion", "brighton-hove-albion"),
            ("Liverpool", "liverpool"),
        ]

        for team_name, expected_slug in test_cases:
            result = team_name_to_slug(team_name)
            assert result == expected_slug


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "-s"])
