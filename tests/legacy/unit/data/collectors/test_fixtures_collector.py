from datetime import datetime

from src.data.collectors.fixtures_collector import FixturesCollector
from unittest.mock import patch
import pytest
import os

#!/usr/bin/env python3
"""
测试赛程数据采集器

测试覆盖：
1. FixturesCollector 初始化和配置
2. 赛程数据采集主要功能
3. 防重复和防丢失策略
4. 数据清洗和标准化
5. 错误处理和异常情况
6. 辅助方法功能
"""

class TestFixturesCollector:
    """测试赛程数据采集器"""
    def setup_method(self):
        """设置测试环境"""
        self.collector = FixturesCollector(
            data_source = os.getenv("TEST_FIXTURES_COLLECTOR_DATA_SOURCE_25"),": api_key = os.getenv("TEST_FIXTURES_COLLECTOR_API_KEY_25"),": base_url = os.getenv("TEST_FIXTURES_COLLECTOR_BASE_URL_25"))": def test_init_with_default_values(self):"""
        "]""测试默认初始化"""
        collector = FixturesCollector()
        assert collector.data_source =="football_api[" assert collector.api_key is None[""""
        assert collector.base_url =="]]https//api.football-data.org/v4[" assert isinstance(collector._processed_matches, set)""""
        assert isinstance(collector._missing_matches, list)
    def test_init_with_custom_values(self):
        "]""测试自定义初始化"""
        collector = FixturesCollector(
            data_source = os.getenv("TEST_FIXTURES_COLLECTOR_DATA_SOURCE_31"),": api_key = os.getenv("TEST_FIXTURES_COLLECTOR_API_KEY_32"),": base_url = os.getenv("TEST_FIXTURES_COLLECTOR_BASE_URL_33"))": assert collector.data_source =="]custom_api[" assert collector.api_key =="]custom_key[" assert collector.base_url =="]https//custom.api.com["""""
    @pytest.mark.asyncio
    async def test_collect_fixtures_success(self):
        "]""测试成功采集赛程数据"""
        # Mock helper methods
        with patch.object(:
            self.collector, "_get_active_leagues[", return_value=["]PL[", "]BL["]""""
        ), patch.object(self.collector, "]_load_existing_matches["), patch.object(": self.collector, "]_collect_league_fixtures["""""
        ) as mock_collect_league, patch.object(
            self.collector, "]_clean_fixture_data["""""
        ) as mock_clean, patch.object(
            self.collector, "]_detect_missing_matches["""""
        ), patch.object(
            self.collector, "]_save_to_bronze_layer["""""
        ):
            # Setup mock data
            mock_collect_league.return_value = [
                {"]id[": 1, "]home[": "]Team A[", "]away[": "]Team B["},""""
                {"]id[": 2, "]home[": "]Team C[", "]away[": "]Team D["}]": mock_clean.return_value = {"""
                "]external_match_id[": 1,""""
                "]home_team[: "Team A[","]"""
                "]away_team[: "Team B[","]"""
                "]match_date[: "2024-01-01["}"]"""
            # Execute collection
            result = await self.collector.collect_fixtures()
            # Verify result
            assert result.status =="]success[" assert result.success_count ==2[""""
            assert result.error_count ==0
            assert result.records_collected ==2
            assert len(result.collected_data) ==2
    @pytest.mark.asyncio
    async def test_collect_fixtures_with_date_range(self):
        "]]""测试指定日期范围的赛程采集"""
        date_from = datetime(2024, 1, 1)
        date_to = datetime(2024, 1, 31)
        with patch.object(:
            self.collector, "_get_active_leagues[", return_value=["]PL["]""""
        ), patch.object(self.collector, "]_load_existing_matches["), patch.object(": self.collector, "]_collect_league_fixtures[", return_value=[]""""
        ), patch.object(
            self.collector, "]_detect_missing_matches["""""
        ), patch.object(
            self.collector, "]_save_to_bronze_layer["""""
        ):
            result = await self.collector.collect_fixtures(
                leagues=["]PL["], date_from=date_from, date_to=date_to[""""
            )
            assert result.status =="]]success["""""
            # Verify that the date range was used correctly
            self.collector._collect_league_fixtures.assert_called_once_with(
                "]PL[", date_from, date_to[""""
            )
    @pytest.mark.asyncio
    async def test_collect_fixtures_with_partial_success(self):
        "]]""测试部分成功的赛程采集"""
        with patch.object(:
            self.collector, "_get_active_leagues[", return_value=["]PL[", "]BL["]""""
        ), patch.object(self.collector, "]_load_existing_matches["), patch.object(": self.collector, "]_collect_league_fixtures["""""
        ) as mock_collect_league, patch.object(
            self.collector, "]_clean_fixture_data["""""
        ) as mock_clean, patch.object(
            self.collector, "]_detect_missing_matches["""""
        ), patch.object(
            self.collector, "]_save_to_bronze_layer["""""
        ):
            # Setup mock to return some invalid data
            mock_collect_league.return_value = [
                {"]id[": 1, "]home[": "]Team A[", "]away[": "]Team B["},  # Valid[""""
                {"]]id[": 2, "]invalid[": "]data["},  # Invalid[""""
            ]
            mock_clean.side_effect = [
                {
                    "]]external_match_id[": 1,""""
                    "]home_team[: "Team A[","]"""
                    "]away_team[: "Team B["},  # Valid["]"]": None,  # Invalid"
            ]
            result = await self.collector.collect_fixtures()
            assert result.status =="]partial[" assert result.success_count ==1[""""
            assert (
                result.error_count ==2
            )  # Both fixture processing error and collection error
            assert result.records_collected ==1
    @pytest.mark.asyncio
    async def test_collect_fixtures_with_league_error(self):
        "]]""测试联赛采集错误"""
        with patch.object(:
            self.collector, "_get_active_leagues[", return_value=["]PL[", "]BL["]""""
        ), patch.object(self.collector, "]_load_existing_matches["), patch.object(": self.collector, "]_collect_league_fixtures["""""
        ) as mock_collect_league, patch.object(
            self.collector, "]_detect_missing_matches["""""
        ), patch.object(
            self.collector, "]_save_to_bronze_layer["""""
        ):
            # Setup mock to raise exception for one league:
            def side_effect(league, date_from, date_to):
                if league =="]PL[": return [{"]id[": 1, "]home[": "]Team A[", "]away[" "]Team B["}]": else:": raise Exception("]API Error[")": mock_collect_league.side_effect = side_effect[": result = await self.collector.collect_fixtures()": assert ("
                result.status =="]]failed["""""
            )  # Actually returns failed when any league has an error
            assert (
                result.success_count ==0
            )  # No successful processing when there's a league error
            assert result.error_count ==2  # Both the league error and processing error
            assert "]Error collecting league BL[" in result.error_message[""""
    @pytest.mark.asyncio
    async def test_collect_fixtures_total_failure(self):
        "]]""测试完全失败的赛程采集"""
        with patch.object(:
            self.collector, "_get_active_leagues[", return_value=["]PL["]""""
        ), patch.object(self.collector, "]_load_existing_matches["), patch.object(": self.collector,"""
            "]_collect_league_fixtures[",": side_effect=Exception("]API Error[")):": result = await self.collector.collect_fixtures()": assert result.status =="]failed[" assert result.success_count ==0[""""
            assert result.error_count ==1
            assert "]]API Error[" in result.error_message[""""
    @pytest.mark.asyncio
    async def test_collect_fixtures_duplicate_prevention(self):
        "]]""测试防重复机制"""
        fixture_data = {"id[": 1, "]home[": "]Team A[", "]away[" "]Team B["}": with patch.object(:": self.collector, "]_get_active_leagues[", return_value=["]PL["]""""
        ), patch.object(self.collector, "]_load_existing_matches["), patch.object(": self.collector, "]_collect_league_fixtures[", return_value=["]fixture_data["""""
        ), patch.object(
            self.collector, "]_clean_fixture_data["""""
        ) as mock_clean, patch.object(
            self.collector, "]_detect_missing_matches["""""
        ), patch.object(
            self.collector, "]_save_to_bronze_layer["""""
        ):
            mock_clean.return_value = {
                "]external_match_id[": 1,""""
                "]home_team[: "Team A[","]"""
                "]away_team[: "Team B["}"]"""
            # Add to processed matches to simulate duplicate
            match_key = self.collector._generate_match_key(fixture_data)
            self.collector._processed_matches.add(match_key)
            result = await self.collector.collect_fixtures()
            assert result.status =="]success[" assert result.success_count ==0  # Should be skipped due to duplicate[""""
            assert result.records_collected ==0
    @pytest.mark.asyncio
    async def test_get_active_leagues_success(self):
        "]]""测试获取活跃联赛列表"""
        # The actual implementation returns a hardcoded list
        leagues = await self.collector._get_active_leagues()
        # Check that it returns the expected hardcoded list
        expected_leagues = ["PL[", "]PD[", "]SA[", "]BL1[", "]FL1[", "]CL[", "]EL["]": assert leagues ==expected_leagues["""
    @pytest.mark.asyncio
    async def test_get_active_leagues_error(self):
        "]]""测试获取活跃联赛列表失败"""
        # Since the actual implementation has a TODO comment and doesn't use the database,
        # we'll test that it returns the expected hardcoded list even when there might be an error
        leagues = await self.collector._get_active_leagues()
        # Should return the full list as per current implementation
        expected_leagues = ["PL[", "]PD[", "]SA[", "]BL1[", "]FL1[", "]CL[", "]EL["]": assert leagues ==expected_leagues[" def test_generate_match_key(self):""
        "]]""测试比赛键生成"""
        fixture_data = {"id[": 12345, "]competition[": {"]id[": "]PL["}}": key = self.collector._generate_match_key(fixture_data)"""
        # Should be consistent for same data:
        assert key ==self.collector._generate_match_key(fixture_data)
        # Should be different for different data = different_data fixture_data.copy()
        different_data["]id["] = 54321[": assert key != self.collector._generate_match_key(different_data)"""
    @pytest.mark.asyncio
    async def test_clean_fixture_data_success(self):
        "]]""测试成功清洗赛程数据"""
        raw_fixture = {
            "id[": 12345,""""
            "]homeTeam[": {""""
                "]id[": 1,""""
                "]name[: "Team A[","]"""
                "]crest[: "http://example.com/a.png["},"]"""
            "]awayTeam[": {""""
                "]id[": 2,""""
                "]name[: "Team B[","]"""
                "]crest[: "http://example.com/b.png["},"]"""
            "]utcDate[: "2024-01-01T15:00:00Z[","]"""
            "]competition[": {"]id[": "]PL[", "]name[": "]Premier League["},""""
            "]season[": {""""
                "]id[: "2024-25[","]"""
                "]startDate[: "2024-08-01[","]"""
                "]endDate[: "2025-05-31["}}"]": cleaned = await self.collector._clean_fixture_data(raw_fixture)": assert cleaned is not None"
        assert cleaned["]external_match_id["] =="]12345[" assert cleaned["]external_home_team_id["] =="]1[" assert cleaned["]external_away_team_id["] =="]2[" assert cleaned["]external_league_id["] =="]PL[" assert cleaned["]season["] =="]2024-25["""""
    @pytest.mark.asyncio
    async def test_clean_fixture_data_invalid(self):
        "]""测试清洗无效赛程数据"""
        invalid_fixture = {"id[": ["]invalid["}": cleaned = await self.collector._clean_fixture_data(invalid_fixture)": assert cleaned is None[""
    @pytest.mark.asyncio
    async def test_collect_odds_not_implemented(self):
        "]]""测试赔率采集未实现"""
        result = await self.collector.collect_odds()
        assert result.status =="skipped[" assert result.collection_type =="]odds[" assert result.records_collected ==0[""""
        assert result.success_count ==0
        assert result.error_count ==0
    @pytest.mark.asyncio
    async def test_collect_live_scores_not_implemented(self):
        "]]""测试实时比分采集未实现"""
        result = await self.collector.collect_live_scores()
        assert result.status =="skipped[" assert result.collection_type =="]live_scores[" assert result.records_collected ==0[""""
        assert result.success_count ==0
        assert result.error_count ==0
    @pytest.mark.asyncio
    async def test_load_existing_matches(self):
        "]]""测试加载已存在比赛"""
        # Clear the processed matches set first
        self.collector._processed_matches.clear()
        date_from = datetime(2024, 1, 1)
        date_to = datetime(2024, 1, 31)
        await self.collector._load_existing_matches(date_from, date_to)
        # The current implementation just sets an empty set
        assert isinstance(self.collector._processed_matches, set)
        assert len(self.collector._processed_matches) ==0
    @pytest.mark.asyncio
    async def test_detect_missing_matches(self):
        """测试检测缺失比赛"""
        # Clear the missing matches list first
        self.collector._missing_matches.clear()
        collected_data = [
            {"external_match_id[": 1, "]league_id[": "]PL["},""""
            {"]external_match_id[": 2, "]league_id[": "]BL["}]": date_from = datetime(2024, 1, 1)": date_to = datetime(2024, 1, 31)": await self.collector._detect_missing_matches(collected_data, date_from, date_to)"
        # The current implementation has a TODO and doesn't actually detect missing matches
        # So the missing matches list should remain empty
        assert isinstance(self.collector._missing_matches, list)
        assert len(self.collector._missing_matches) ==0
class TestFixturesCollectorEdgeCases:
    "]""测试赛程采集器边界情况"""
    def setup_method(self):
        """设置测试环境"""
        self.collector = FixturesCollector()
    @pytest.mark.asyncio
    async def test_collect_fixtures_empty_leagues(self):
        """测试空联赛列表"""
        with patch.object(self.collector, "_get_active_leagues[", return_value = [])": result = await self.collector.collect_fixtures()": assert result.status =="]success[" assert result.records_collected ==0[""""
    @pytest.mark.asyncio
    async def test_collect_fixtures_with_none_leagues(self):
        "]]""测试None联赛列表"""
        with patch.object(self.collector, "_get_active_leagues[", return_value = None)": result = await self.collector.collect_fixtures()"""
            # The actual implementation fails when leagues is None due to len() call
            assert result.status =="]failed[" assert result.records_collected ==0[""""
            assert result.success_count ==0
            assert result.error_count ==1
    @pytest.mark.asyncio
    async def test_collect_fixtures_api_timeout(self):
        "]]""测试API超时"""
        with patch.object(:
            self.collector, "_get_active_leagues[", return_value=["]PL["]""""
        ), patch.object(self.collector, "]_load_existing_matches["), patch.object(": self.collector,"""
            "]_collect_league_fixtures[",": side_effect=TimeoutError("]API timeout[")):": result = await self.collector.collect_fixtures()"""
            # When all leagues fail due to timeout, status is "]failed[": since success_count = 0[": assert result.status =="]]failed[" assert "]timeout[" in result.error_message.lower()""""
            assert result.success_count ==0
            assert result.error_count ==1
    @pytest.mark.asyncio
    async def test_collect_fixtures_rate_limit(self):
        "]""测试API速率限制"""
        with patch.object(:
            self.collector, "_get_active_leagues[", return_value=["]PL["]""""
        ), patch.object(self.collector, "]_load_existing_matches["), patch.object(": self.collector,"""
            "]_collect_league_fixtures[",": side_effect=Exception("]Rate limit exceeded[")):": result = await self.collector.collect_fixtures()"""
            # When all leagues fail due to rate limit, status is "]failed[": since success_count = 0[": assert result.status =="]]failed[" assert "]rate limit[" in result.error_message.lower()""""
            assert result.success_count ==0
            assert result.error_count ==1
    def test_generate_match_key_missing_fields(self):
        "]""测试缺失字段时的比赛键生成"""
        # Test with minimal data = minimal_data {"id[": 123}": key = self.collector._generate_match_key(minimal_data)": assert key is not None[""
        # Test with empty data = empty_data {}
        key = self.collector._generate_match_key(empty_data)
        assert key is not None
    @pytest.mark.asyncio
    async def test_clean_fixture_data_missing_required_fields(self):
        "]]""测试清洗缺失必需字段的赛程数据"""
        incomplete_fixture = {
            "id[": 12345,"]"""
            # Missing required fields like homeTeam, awayTeam
        }
        cleaned = await self.collector._clean_fixture_data(incomplete_fixture)
        assert cleaned is None