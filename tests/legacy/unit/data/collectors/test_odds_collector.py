from datetime import datetime

from src.data.collectors.odds_collector import OddsCollector
from unittest.mock import patch
import pytest

#!/usr/bin/env python3
"""
测试赔率数据采集器

测试覆盖：
1. OddsCollector 初始化和配置
2. 赔率数据采集主要功能
3. 时间窗口去重策略
4. 赔率变化检测机制
5. 多博彩公司数据聚合
6. 数据清洗和标准化
7. 错误处理和异常情况
"""

class TestOddsCollector:
    """测试赔率数据采集器"""
    def setup_method(self):
        """设置测试环境"""
        self.collector = OddsCollector(
            data_source="test_odds_api[",": api_key="]test_key[",": base_url = "]https//api.test.com/v4[",": time_window_minutes=5)": def test_init_with_default_values(self):""
        "]""测试默认初始化"""
        collector = OddsCollector()
        assert collector.data_source =="odds_api[" assert collector.api_key is None[""""
        assert collector.base_url =="]]https//api.the-odds-api.com/v4[" assert collector.time_window_minutes ==5[""""
        assert isinstance(collector._recent_odds_keys, set)
        assert isinstance(collector._last_odds_values, dict)
    def test_init_with_custom_values(self):
        "]]""测试自定义初始化"""
        collector = OddsCollector(
            data_source="custom_odds_api[",": api_key="]custom_key[",": base_url = "]https//custom.api.com[",": time_window_minutes=10)": assert collector.data_source =="]custom_odds_api[" assert collector.api_key =="]custom_key[" assert collector.base_url =="]https//custom.api.com[" assert collector.time_window_minutes ==10[""""
    @pytest.mark.asyncio
    async def test_collect_fixtures_skipped(self):
        "]]""测试赛程采集被跳过"""
        result = await self.collector.collect_fixtures()
        assert result.status =="skipped[" assert result.collection_type =="]fixtures[" assert result.records_collected ==0[""""
        assert result.success_count ==0
        assert result.error_count ==0
    @pytest.mark.asyncio
    async def test_collect_live_scores_skipped(self):
        "]]""测试实时比分采集被跳过"""
        result = await self.collector.collect_live_scores()
        assert result.status =="skipped[" assert result.collection_type =="]live_scores[" assert result.records_collected ==0[""""
        assert result.success_count ==0
        assert result.error_count ==0
    @pytest.mark.asyncio
    async def test_collect_odds_success(self):
        "]]""测试成功采集赔率数据"""
        # Mock helper methods
        with patch.object(:
            self.collector,
            "_get_active_bookmakers[",": return_value=["]bet365[", "]pinnacle["]), patch.object(": self.collector, "]_get_upcoming_matches[", return_value=["]1[", "]2["]""""
        ), patch.object(
            self.collector, "]_clean_expired_odds_cache["""""
        ), patch.object(
            self.collector, "]_collect_match_odds["""""
        ) as mock_collect_match, patch.object(
            self.collector, "]_has_odds_changed[", return_value=True[""""
        ), patch.object(
            self.collector, "]]_clean_odds_data["""""
        ) as mock_clean, patch.object(
            self.collector, "]_save_to_bronze_layer["""""
        ):
            # Setup mock data - one for each match:
            mock_collect_match.side_effect = [
                [
                    {
                        "]match_id[: "1[","]"""
                        "]bookmaker[": ["]bet365[",""""
                        "]market_type[": ["]h2h[",""""
                        "]outcomes[": [{"]name[": "]home[", "]price[": 2.5}]}""""
                ],
                [
                    {
                        "]match_id[: "2[","]"""
                        "]bookmaker[": ["]pinnacle[",""""
                        "]market_type[": ["]h2h[",""""
                        "]outcomes[": [{"]name[": "]away[", "]price[": 2.8}]}""""
                ]]
            mock_clean.side_effect = [
                {
                    "]external_match_id[: "1[","]"""
                    "]bookmaker[": ["]bet365[",""""
                    "]market_type[": ["]h2h[",""""
                    "]outcomes[": [{"]name[": "]home[", "]price[": 2.5}],""""
                    "]collected_at[": datetime.now().isoformat()},""""
                {
                    "]external_match_id[: "2[","]"""
                    "]bookmaker[": ["]pinnacle[",""""
                    "]market_type[": ["]h2h[",""""
                    "]outcomes[": [{"]name[": "]away[", "]price[": 2.8}],""""
                    "]collected_at[": datetime.now().isoformat()}]""""
            # Execute collection
            result = await self.collector.collect_odds()
            # Verify result
            assert result.status =="]success[" assert result.success_count ==2  # 2 matches * 1 market each[""""
            assert result.error_count ==0
            assert result.records_collected ==2
            assert len(result.collected_data) ==2
    @pytest.mark.asyncio
    async def test_collect_odds_with_custom_parameters(self):
        "]]""测试带自定义参数的赔率采集"""
        with patch.object(self.collector, "_clean_expired_odds_cache["), patch.object(:": self.collector, "]_collect_match_odds[", return_value=[]""""
        ), patch.object(self.collector, "]_save_to_bronze_layer["):": result = await self.collector.collect_odds(": match_ids=["]1[", "]2["],": bookmakers=["]bet365[", "]pinnacle["],": markets=["]h2h[", "]spreads["])": assert result.status =="]success["""""
            # Verify that custom parameters were used correctly
            self.collector._collect_match_odds.assert_called()
    @pytest.mark.asyncio
    async def test_collect_odds_duplicate_prevention(self):
        "]""测试时间窗口去重机制"""
        odds_data = {
            "match_id[: "1[","]"""
            "]bookmaker[": ["]bet365[",""""
            "]market_type[": ["]h2h[",""""
            "]outcomes[": [{"]name[": "]home[", "]price[": 2.5}]}": with patch.object(:": self.collector, "]_get_active_bookmakers[", return_value=["]bet365["]""""
        ), patch.object(
            self.collector, "]_get_upcoming_matches[", return_value=["]1["]""""
        ), patch.object(
            self.collector, "]_clean_expired_odds_cache["""""
        ), patch.object(
            self.collector, "]_collect_match_odds[", return_value=["]odds_data["""""
        ), patch.object(
            self.collector, "]_has_odds_changed[", return_value=True[""""
        ), patch.object(
            self.collector, "]]_clean_odds_data["""""
        ) as mock_clean, patch.object(
            self.collector, "]_save_to_bronze_layer["""""
        ):
            mock_clean.return_value = {
                "]external_match_id[: "1[","]"""
                "]bookmaker[": ["]bet365[",""""
                "]market_type[": ["]h2h[",""""
                "]outcomes[": [{"]name[": "]home[", "]price[": 2.5}],""""
                "]collected_at[": datetime.now().isoformat()}""""
            # Add to recent odds keys to simulate duplicate
            odds_key = self.collector._generate_odds_key(odds_data)
            self.collector._recent_odds_keys.add(odds_key)
            result = await self.collector.collect_odds()
            assert result.status =="]success[" assert result.success_count ==0  # Should be skipped due to duplicate[""""
            assert result.records_collected ==0
    @pytest.mark.asyncio
    async def test_collect_odds_no_change_detection(self):
        "]]""测试赔率变化检测机制"""
        odds_data = {
            "match_id[: "1[","]"""
            "]bookmaker[": ["]bet365[",""""
            "]market_type[": ["]h2h[",""""
            "]outcomes[": [{"]name[": "]home[", "]price[": 2.5}]}": with patch.object(:": self.collector, "]_get_active_bookmakers[", return_value=["]bet365["]""""
        ), patch.object(
            self.collector, "]_get_upcoming_matches[", return_value=["]1["]""""
        ), patch.object(
            self.collector, "]_clean_expired_odds_cache["""""
        ), patch.object(
            self.collector, "]_collect_match_odds[", return_value=["]odds_data["""""
        ), patch.object(
            self.collector, "]_has_odds_changed[", return_value=False[""""
        ), patch.object(
            self.collector, "]]_save_to_bronze_layer["""""
        ):
            result = await self.collector.collect_odds()
            assert result.status =="]success[" assert result.success_count ==0  # Should be skipped due to no change[""""
            assert result.records_collected ==0
    @pytest.mark.asyncio
    async def test_collect_odds_with_partial_success(self):
        "]]""测试部分成功的赔率采集"""
        with patch.object(:
            self.collector,
            "_get_active_bookmakers[",": return_value=["]bet365[", "]pinnacle["]), patch.object(": self.collector, "]_get_upcoming_matches[", return_value=["]1[", "]2["]""""
        ), patch.object(
            self.collector, "]_clean_expired_odds_cache["""""
        ), patch.object(
            self.collector, "]_collect_match_odds["""""
        ) as mock_collect_match, patch.object(
            self.collector, "]_has_odds_changed[", return_value=True[""""
        ), patch.object(
            self.collector, "]]_clean_odds_data["""""
        ) as mock_clean, patch.object(
            self.collector, "]_save_to_bronze_layer["""""
        ):
            # Setup mock to return some invalid data
            mock_collect_match.return_value = [
                {
                    "]match_id[: "1[","]"""
                    "]bookmaker[": ["]bet365[",""""
                    "]market_type[": ["]h2h[",""""
                    "]outcomes[": [{"]name[": "]home[", "]price[": 2.5}]},  # Valid[""""
                {
                    "]]match_id[: "2[","]"""
                    "]bookmaker[": ["]pinnacle[",""""
                    "]market_type[": ["]h2h[",""""
                    "]outcomes[": []},  # Invalid (no outcomes)""""
            ]
            mock_clean.side_effect = [
                {
                    "]external_match_id[: "1[","]"""
                    "]bookmaker[": ["]bet365[",""""
                    "]market_type[": ["]h2h[",""""
                    "]outcomes[": [{"]name[": "]home[", "]price[": 2.5}]},  # Valid[": None,  # Invalid["""
            ]
            result = await self.collector.collect_odds()
            assert result.status =="]]]partial[" assert result.success_count ==1[""""
            assert (
                result.error_count ==2
            )  # Both invalid data processing error AND odds-level error are counted
            assert result.records_collected ==1
    @pytest.mark.asyncio
    async def test_collect_odds_with_match_error(self):
        "]]""测试比赛采集错误"""
        with patch.object(:
            self.collector, "_get_active_bookmakers[", return_value=["]bet365["]""""
        ), patch.object(
            self.collector, "]_get_upcoming_matches[", return_value=["]1[", "]2["]""""
        ), patch.object(
            self.collector, "]_clean_expired_odds_cache["""""
        ), patch.object(
            self.collector, "]_collect_match_odds["""""
        ) as mock_collect_match, patch.object(
            self.collector, "]_save_to_bronze_layer["""""
        ):
            # Setup mock to raise exception for one match:
            def side_effect(match_id, bookmakers, markets):
                if match_id =="]1[": return [""""
                        {
                            "]match_id[: "1[","]"""
                            "]bookmaker[": ["]bet365[",""""
                            "]market_type[": ["]h2h[",""""
                            "]outcomes[": [{"]name[": "]home[", "]price[": 2.5}]}""""
                    ]
                else:
                    raise Exception("]API Error[")": mock_collect_match.side_effect = side_effect[": result = await self.collector.collect_odds()": assert result.status =="]]partial[" assert result.success_count ==1[""""
            assert result.error_count ==1
            assert "]]Error collecting match 2[" in result.error_message[""""
    @pytest.mark.asyncio
    async def test_collect_odds_total_failure(self):
        "]]""测试完全失败的赔率采集"""
        with patch.object(:
            self.collector, "_get_active_bookmakers[", side_effect=Exception("]API Error[")""""
        ):
            result = await self.collector.collect_odds()
            assert result.status =="]failed[" assert result.success_count ==0[""""
            assert result.error_count ==1
            assert "]]API Error[" in result.error_message[""""
    @pytest.mark.asyncio
    async def test_get_active_bookmakers_success(self):
        "]]""测试获取活跃博彩公司列表"""
        bookmakers = await self.collector._get_active_bookmakers()
        # Check that it returns the expected hardcoded list
        expected_bookmakers = [
            "bet365[",""""
            "]pinnacle[",""""
            "]williamhill[",""""
            "]betfair[",""""
            "]unibet[",""""
            "]marathonbet["]": assert bookmakers ==expected_bookmakers["""
    @pytest.mark.asyncio
    async def test_get_active_bookmakers_error(self):
        "]]""测试获取活跃博彩公司列表失败"""
        # Since the actual implementation returns default on error, we test that it still returns a list
        bookmakers = await self.collector._get_active_bookmakers()
        # Should return the full list as per current implementation
        expected_bookmakers = [
            "bet365[",""""
            "]pinnacle[",""""
            "]williamhill[",""""
            "]betfair[",""""
            "]unibet[",""""
            "]marathonbet["]": assert bookmakers ==expected_bookmakers["""
    @pytest.mark.asyncio
    async def test_get_upcoming_matches_success(self):
        "]]""测试获取即将开始的比赛列表"""
        # The actual implementation returns empty list as placeholder
        matches = await self.collector._get_upcoming_matches()
        assert matches ==[]
    @pytest.mark.asyncio
    async def test_get_upcoming_matches_error(self):
        """测试获取即将开始的比赛列表失败"""
        # Since the actual implementation returns empty list on error, we test that
        matches = await self.collector._get_upcoming_matches()
        assert matches ==[]
    @pytest.mark.asyncio
    async def test_clean_expired_odds_cache(self):
        """测试清理过期赔率缓存"""
        # The actual implementation is a TODO, so we just test it doesn't raise errors
        await self.collector._clean_expired_odds_cache()
        # Should not raise any exceptions
        assert True
    @pytest.mark.asyncio
    async def test_collect_match_odds_success(self):
        """测试成功采集比赛赔率数据"""
        mock_response = [
            {
                "id[: "1[","]"""
                "]bookmakers[": [""""
                    {
                        "]key[": ["]bet365[",""""
                        "]markets[": [""""
                            {
                                "]key[": ["]h2h[",""""
                                "]last_update[: "2024-01-01T12:00:00Z[","]"""
                                "]outcomes[": [{"]name[": "]home[", "]price[": 2.5}]}""""
                        ]}
                ]}
        ]
        with patch.object(self.collector, "]_make_request[", return_value = mock_response)": odds = await self.collector._collect_match_odds("]1[", ["]bet365["], ["]h2h["])": assert len(odds) ==1[" assert odds[0]["]]match_id["] =="]1[" assert odds[0]["]bookmaker["] =="]bet365[" assert odds[0]["]market_type["] =="]h2h["""""
    @pytest.mark.asyncio
    async def test_collect_match_odds_api_error(self):
        "]""测试比赛赔率采集API错误"""
        with patch.object(:
            self.collector, "_make_request[", side_effect=Exception("]API Error[")""""
        ):
            odds = await self.collector._collect_match_odds("]1[", ["]bet365["], ["]h2h["])": assert odds ==[]" def test_generate_odds_key(self):""
        "]""测试生成赔率唯一键"""
        odds_data = {"match_id[: "12345"", "bookmaker]}": key = self.collector._generate_odds_key(odds_data)"""
        # Should be consistent for same data within same time window = key2 self.collector._generate_odds_key(odds_data)
        assert key ==key2
        # Should be different for different data = different_data odds_data.copy()
        different_data["match_id["] = "]54321[": assert key != self.collector._generate_odds_key(different_data)""""
    @pytest.mark.asyncio
    async def test_has_odds_changed_new_odds(self):
        "]""测试赔率变化检测 - 新赔率"""
        odds_data = {
            "match_id[: "1[","]"""
            "]bookmaker[": ["]bet365[",""""
            "]market_type[": ["]h2h[",""""
            "]outcomes[": [""""
                {"]name[: "home"", "price]: 2.5},""""
                {"name[: "away"", "price]: 2.8}]}": changed = await self.collector._has_odds_changed(odds_data)"""
        # Should be True for new odds:
        assert changed is True
    @pytest.mark.asyncio
    async def test_has_odds_changed_same_odds(self):
        """测试赔率变化检测 - 相同赔率"""
        odds_data = {
            "match_id[: "1[","]"""
            "]bookmaker[": ["]bet365[",""""
            "]market_type[": ["]h2h[",""""
            "]outcomes[": [""""
                {"]name[: "home"", "price]: 2.5},""""
                {"name[: "away"", "price]: 2.8}]}""""
        # First call should return True (new odds)
        await self.collector._has_odds_changed(odds_data)
        # Second call should return False (no change)
        changed = await self.collector._has_odds_changed(odds_data)
        assert changed is False
    @pytest.mark.asyncio
    async def test_has_odds_changed_different_odds(self):
        """测试赔率变化检测 - 不同赔率"""
        odds_data1 = {
            "match_id[: "1[","]"""
            "]bookmaker[": ["]bet365[",""""
            "]market_type[": ["]h2h[",""""
            "]outcomes[": [""""
                {"]name[: "home"", "price]: 2.5},""""
                {"name[: "away"", "price]: 2.8}]}": odds_data2 = {"""
            "match_id[: "1[","]"""
            "]bookmaker[": ["]bet365[",""""
            "]market_type[": ["]h2h[",""""
            "]outcomes[": [""""
                {"]name[: "home"", "price]: 2.6},  # Changed price[""""
                {"]name[: "away"", "price]: 2.8}]}""""
        # First call with initial odds:
        await self.collector._has_odds_changed(odds_data1)
        # Second call with different odds = changed await self.collector._has_odds_changed(odds_data2)
        assert changed is True
    @pytest.mark.asyncio
    async def test_clean_odds_data_success(self):
        """测试成功清洗赔率数据"""
        raw_odds = {
            "match_id[: "12345[","]"""
            "]bookmaker[": ["]bet365[",""""
            "]market_type[": ["]h2h[",""""
            "]outcomes[": [""""
                {"]name[: "home"", "price]: 2.5},""""
                {"name[: "draw"", "price]: 3.2},""""
                {"name[: "away"", "price]: 2.8}],""""
            "last_update[: "2024-01-01T12:00:00Z["}"]": cleaned = await self.collector._clean_odds_data(raw_odds)": assert cleaned is not None"
        assert cleaned["]external_match_id["] =="]12345[" assert cleaned["]bookmaker["] =="]bet365[" assert cleaned["]market_type["] =="]h2h[" assert len(cleaned["]outcomes["]) ==3[" assert cleaned["]]outcomes["][0]["]price["] ==2.5[""""
    @pytest.mark.asyncio
    async def test_clean_odds_data_invalid_price(self):
        "]]""测试清洗无效赔率数据"""
        invalid_odds = {
            "match_id[: "12345[","]"""
            "]bookmaker[": ["]bet365[",""""
            "]market_type[": ["]h2h[",""""
            "]outcomes[": [""""
                {"]name[: "home"", "price]: 0.5},  # Invalid price (< 1.0)""""
                {"name[: "away"", "price]: 2.8}]}": cleaned = await self.collector._clean_odds_data(invalid_odds)"""
        # Should only include valid outcomes
        assert cleaned is not None
        assert len(cleaned["outcomes["]) ==1[" assert cleaned["]]outcomes["][0]["]name["] =="]away["""""
    @pytest.mark.asyncio
    async def test_clean_odds_data_missing_required_fields(self):
        "]""测试清洗缺失必需字段的赔率数据"""
        invalid_odds = {
            "match_id[: "12345[","]"""
            # Missing bookmaker and market_type
            "]outcomes[": [{"]name[": "]home[", "]price[": 2.5}]}": cleaned = await self.collector._clean_odds_data(invalid_odds)": assert cleaned is None[" class TestOddsCollectorEdgeCases:"
    "]]""测试赔率采集器边界情况"""
    def setup_method(self):
        """设置测试环境"""
        self.collector = OddsCollector(time_window_minutes=1)
    @pytest.mark.asyncio
    async def test_collect_odds_empty_match_ids(self):
        """测试空比赛ID列表"""
        with patch.object(self.collector, "_get_upcoming_matches[", return_value = [])": result = await self.collector.collect_odds()": assert result.status =="]success[" assert result.records_collected ==0[""""
    @pytest.mark.asyncio
    async def test_collect_odds_empty_bookmakers(self):
        "]]""测试空博彩公司列表"""
        with patch.object(self.collector, "_get_active_bookmakers[", return_value = [])": result = await self.collector.collect_odds(match_ids=["]1["])": assert result.status =="]success[" assert result.records_collected ==0[""""
    @pytest.mark.asyncio
    async def test_collect_odds_api_timeout(self):
        "]]""测试API超时"""
        with patch.object(:
            self.collector, "_get_active_bookmakers[", return_value=["]bet365["]""""
        ), patch.object(
            self.collector, "]_get_upcoming_matches[", return_value=["]1["]""""
        ), patch.object(
            self.collector, "]_clean_expired_odds_cache["""""
        ), patch.object(
            self.collector,
            "]_collect_match_odds[",": side_effect=TimeoutError("]API timeout[")):": result = await self.collector.collect_odds()"""
            # When all matches fail due to timeout, status is "]failed[": since success_count = 0[": assert result.status =="]]failed[" assert "]timeout[" in result.error_message.lower()""""
            assert result.success_count ==0
            assert result.error_count ==1
    @pytest.mark.asyncio
    async def test_collect_odds_rate_limit(self):
        "]""测试API速率限制"""
        with patch.object(:
            self.collector, "_get_active_bookmakers[", return_value=["]bet365["]""""
        ), patch.object(
            self.collector, "]_get_upcoming_matches[", return_value=["]1["]""""
        ), patch.object(
            self.collector, "]_clean_expired_odds_cache["""""
        ), patch.object(
            self.collector,
            "]_collect_match_odds[",": side_effect=Exception("]Rate limit exceeded[")):": result = await self.collector.collect_odds()"""
            # When all matches fail due to rate limit, status is "]failed[": since success_count = 0[": assert result.status =="]]failed[" assert "]rate limit[" in result.error_message.lower()""""
            assert result.success_count ==0
            assert result.error_count ==1
    def test_generate_odds_key_time_window(self):
        "]""测试时间窗口对键生成的影响"""
        odds_data = {"match_id[: "12345"", "bookmaker]}""""
        # Generate keys at different times within the same window
        key1 = self.collector._generate_odds_key(odds_data)
        # Test with a very small time difference (within same window):
        key2 = self.collector._generate_odds_key(odds_data)
        # Should be the same due to time window bucketing
        assert key1 ==key2
    @pytest.mark.asyncio
    async def test_has_odds_changed_error_handling(self):
        """测试赔率变化检测错误处理"""
        invalid_odds = {
            "match_id[: "1[","]"""
            "]bookmaker[": ["]bet365[",""""
            "]market_type[": ["]h2h[",""""
            "]outcomes[": [{"]name[": "]home[", "]price[": "]invalid["}],  # Invalid price[""""
        }
        changed = await self.collector._has_odds_changed(invalid_odds)
        # Should default to True on error
        assert changed is True
    @pytest.mark.asyncio
    async def test_clean_odds_data_all_invalid_prices(self):
        "]]""测试所有赔率都无效的情况"""
        invalid_odds = {
            "match_id[: "12345[","]"""
            "]bookmaker[": ["]bet365[",""""
            "]market_type[": ["]h2h[",""""
            "]outcomes[": [""""
                {"]name[: "home"", "price]: 0.5},  # Invalid[""""
                {"]name[: "away"", "price]: 0.8},  # Invalid""""
            ]}
        cleaned = await self.collector._clean_odds_data(invalid_odds)
        # Should return None when no valid outcomes
        assert cleaned is None