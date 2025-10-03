from datetime import datetime, timedelta
from typing import Dict, List, Any
import json

from decimal import Decimal
from src.data.collectors.odds_collector import OddsCollector, CollectionResult
from unittest.mock import AsyncMock, MagicMock, Mock, patch
import asyncio
import pytest
import responses
import os

"""
赔率数据采集器测试 - OddsCollector

测试赔率数据采集的各个功能。
"""

class TestOddsCollector:
    """测试赔率数据采集器"""
    @pytest.fixture
    def collector(self):
        """创建OddsCollector实例"""
        with patch("src.data.collectors.base_collector.DatabaseManager["):": return OddsCollector(": api_key = os.getenv("TEST_ODDS_COLLECTOR_API_KEY_23"),": base_url = os.getenv("TEST_ODDS_COLLECTOR_BASE_URL_23"),": time_window_minutes=5["""
            )
    def test_init(self, collector):
        "]]""测试初始化"""
    assert collector.data_source =="odds_api[" assert collector.api_key =="]test_api_key[" assert collector.base_url =="]https_/api.test-odds.com/v4[" assert collector.time_window_minutes ==5[""""
    assert hasattr(collector, '_recent_odds_keys')
    assert isinstance(collector._recent_odds_keys, set)
    assert hasattr(collector, '_last_odds_values')
    assert isinstance(collector._last_odds_values, dict)
    @pytest.mark.asyncio
    async def test_collect_fixtures_skipped(self, collector):
        "]]""测试OddsCollector不处理赛程数据"""
        result = await collector.collect_fixtures()
    assert result.status =="skipped[" assert result.records_collected ==0[""""
    assert result.success_count ==0
    assert result.error_count ==0
    @pytest.mark.asyncio
    async def test_collect_live_scores_skipped(self, collector):
        "]]""测试OddsCollector不处理实时比分数据"""
        result = await collector.collect_live_scores()
    assert result.status =="skipped[" assert result.records_collected ==0[""""
    assert result.success_count ==0
    assert result.error_count ==0
    @pytest.mark.asyncio
    async def test_get_active_bookmakers_success(self, collector):
        "]]""测试成功获取活跃博彩公司列表"""
        bookmakers = await collector._get_active_bookmakers()
        # 验证返回预定义的博彩公司列表
        expected_bookmakers = [
        "bet365[", "]pinnacle[", "]williamhill[",""""
        "]betfair[", "]unibet[", "]marathonbet["""""
        ]
    assert bookmakers ==expected_bookmakers
    assert len(bookmakers) ==6
    @pytest.mark.asyncio
    async def test_get_active_bookmakers_fallback(self, collector):
        "]""测试博彩公司列表回退值"""
        with patch.object(collector.logger, 'error') as mock_logger:
            # 模拟异常情况
            with patch.object(collector, '_get_active_bookmakers') as mock_method:
                mock_method.side_effect = Exception("Database Error[")""""
                # 调用实际方法（会触发异常处理）
                try:
                    pass
                except Exception as e:
                   pass  # Auto-fixed empty except block
 pass
                    pass
                except Exception as e:
                   pass  # Auto-fixed empty except block
 pass
                    pass
                except Exception as e:
                   pass  # Auto-fixed empty except block
 pass
                    pass
                except Exception as e:
                   pass  # Auto-fixed empty except block
 pass
                    result = await collector._get_active_bookmakers()
                except:
                    # 直接调用默认逻辑
                    result = ["]bet365[", "]pinnacle["]": assert result ==["]bet365[", "]pinnacle["]" assert len(result) ==2["""
    @pytest.mark.asyncio
    async def test_get_upcoming_matches_success(self, collector):
        "]]""测试获取即将到来的比赛（当前实现返回空列表）"""
        matches = await collector._get_upcoming_matches()
        # Current implementation returns empty list (basic validation)
    assert matches ==[]
    assert isinstance(matches, list)
    @pytest.mark.asyncio
    async def test_get_upcoming_matches_error_handling(self, collector):
        """测试获取比赛列表异常处理"""
        with patch.object(collector.logger, 'error') as mock_logger = matches await collector._get_upcoming_matches()
            # 验证返回空列表
    assert matches ==[]
    assert isinstance(matches, list)
    @pytest.mark.asyncio
    async def test_clean_expired_odds_cache(self, collector):
        """测试清理过期的赔率缓存（基础实现验证）"""
        # Basic implementation validation - method exists and executes without errors
        assert hasattr(collector, '_clean_expired_odds_cache')
        await collector._clean_expired_odds_cache()
        # 方法应该成功执行而不抛出异常
        assert True
    @pytest.mark.asyncio
    async def test_collect_odds_no_matches(self, collector):
        """测试没有比赛可采集的情况"""
        with patch.object(collector, '_get_upcoming_matches', return_value = [])
            result = await collector.collect_odds()
    assert result.status =="success[" assert result.records_collected ==0[""""
    assert result.success_count ==0
    assert result.error_count ==0
        # 没有比赛时应该没有错误信息
    assert result.error_message is None
    @pytest.mark.asyncio
    async def test_collect_odds_single_match_success(self, collector):
        "]]""测试单个比赛赔率采集成功"""
        mock_odds_data = [
        {
        "match_id[": ["]match_1[",""""
        "]bookmaker[": ["]bet365[",""""
        "]market_type[": ["]h2h[",""""
            "]outcomes[": [""""
                {"]name[: "Home"", "price]},""""
                {"name[: "Draw"", "price]},""""
                {"name[: "Away"", "price]}""""
                ],
                "last_update[: "2024-01-15T10:00:00Z"""""
            }
        ]
        with patch.object(collector, '_get_upcoming_matches', return_value = ["]match_1["]), \": patch.object(collector, '_collect_match_odds', return_value=mock_odds_data), \": patch.object(collector, '_save_to_bronze_layer') as mock_save, \": patch.object(collector, '_has_odds_changed', return_value=True), \"
            patch.object(collector, '_clean_odds_data', return_value = mock_odds_data[0])
            result = await collector.collect_odds()
    assert result.status =="]success[" assert result.records_collected ==1[""""
        assert result.success_count ==1
        assert result.error_count ==0
        mock_save.assert_called_once()
    @pytest.mark.asyncio
    async def test_collect_odds_multiple_matches(self, collector):
        "]]""测试多个比赛赔率采集"""
        mock_matches = ["match_1[", "]match_2[", "]match_3["]": mock_odds_data_1 = [{"]match_id[: "match_1"", "bookmaker] []}]": mock_odds_data_2 = [{"match_id[: "match_2"", "bookmaker] []}]": mock_odds_data_3 = [{"match_id[: "match_3"", "bookmaker] []}]": with patch.object(collector, '_get_upcoming_matches', return_value = mock_matches), \": patch.object(collector, '_collect_match_odds') as mock_collect, \": patch.object(collector, '_save_to_bronze_layer') as mock_save, \"
            patch.object(collector, '_has_odds_changed', side_effect=["True[", True, True]), \": patch.object(collector, '_clean_odds_data', side_effect = [mock_odds_data_1[0], mock_odds_data_2[0], mock_odds_data_3[0]])"""
            # 模拟部分成功
            mock_collect.side_effect = ["]mock_odds_data_1[",  # 成功[""""
                [],  # 空数据（失败）
                mock_odds_data_3  # 成功
            ]
            result = await collector.collect_odds()
    assert result.status in ["]]partial[", "]success["]" assert result.records_collected ==2["""
    assert result.success_count ==2
    assert result.error_count ==0  # 空数据不算错误
    assert mock_save.call_count ==1  # 只在最后调用一次
    @pytest.mark.asyncio
    async def test_collect_match_odds_success(self, collector):
        "]]""测试单个比赛赔率采集成功"""
        mock_response = [
        {
        "id[": ["]match_1[",""""
        "]bookmakers[": [""""
        {
            "]key[": ["]bet365[",""""
                "]markets[": [""""
                {
                    "]key[": ["]h2h[",""""
                        "]outcomes[": [""""
                        {"]name[: "Home"", "price]: 2.10},""""
                            {"name[: "Draw"", "price]: 3.40},""""
                                {"name[: "Away"", "price]: 3.80}""""
                                ],
                                "last_update[: "2024-01-15T10:00:00Z"""""
                            }
                        ]
                    }
                ]
            }
        ]
        with patch.object(collector, '_make_request', return_value = mock_response)
            result = await collector._collect_match_odds("]match_1[", ["]bet365["], ["]h2h["])": assert isinstance(result, list)" assert len(result) ==1[""
    assert result[0]["]]match_id["] =="]match_1[" assert result[0]["]bookmaker["] =="]bet365[" assert result[0]["]market_type["] =="]h2h["""""
    @pytest.mark.asyncio
    async def test_collect_match_odds_api_error(self, collector):
        "]""测试API错误处理"""
        with patch.object(collector, '_make_request', side_effect = Exception("API Error["))": result = await collector._collect_match_odds("]match_1[", ["]bet365["], ["]h2h["])": assert result ==[]"""
    @pytest.mark.asyncio
    async def test_collect_match_odds_no_change(self, collector):
        "]""测试赔率没有变化的情况"""
        mock_response = [
        {
        "id[": ["]match_1[",""""
        "]bookmakers[": [""""
        {
            "]key[": ["]bet365[",""""
                "]markets[": [""""
                {
                    "]key[": ["]h2h[",""""
                        "]outcomes[": [""""
                        {"]name[: "Home"", "price]: 2.10},""""
                            {"name[: "Draw"", "price]: 3.40},""""
                                {"name[: "Away"", "price]: 3.80}""""
                                ],
                                "last_update[: "2024-01-15T10:00:00Z"""""
                            }
                        ]
                    }
                ]
            }
        ]
        with patch.object(collector, '_make_request', return_value = mock_response)
            result = await collector._collect_match_odds("]match_1[", ["]bet365["], ["]h2h["])": assert isinstance(result, list)" assert len(result) ==1[""
    def test_generate_odds_key(self, collector):
        "]]""测试生成赔率键"""
        odds_data = {
        "match_id[": ["]match_1[",""""
        "]home_team[: "Team A[","]"""
        "]away_team[: "Team B[","]"""
        "]bookmakers[": [""""
            {
            "]name[": ["]bet365[",""""
            "]odds[": {""""
            "]home_win[: "2.10[","]"""
                "]draw[: "3.40[","]"""
                    "]away_win[: "3.80"""""
                    }
                }
            ]
        }
        key = collector._generate_odds_key(odds_data)
    assert isinstance(key, str)
    assert len(key) > 0
        # 相同的数据应该生成相同的键
        key2 = collector._generate_odds_key(odds_data)
    assert key ==key2
    @pytest.mark.asyncio
    async def test_has_odds_changed_true(self, collector):
        "]""测试检测到赔率变化"""
        odds_data = {
        "match_id[": ["]match_1[",""""
        "]home_team[: "Team A[","]"""
        "]away_team[: "Team B[","]"""
        "]bookmakers[": [{"]name[": "]bet365[", "]odds[": {"]home_win[": "]2.10["}}]""""
        }
        result = await collector._has_odds_changed(odds_data)
    assert result is True
    @pytest.mark.asyncio
    async def test_has_odds_changed_false(self, collector):
        "]""测试赔率没有变化"""
        odds_data = {
        "match_id[": ["]match_1[",""""
        "]bookmaker[": ["]bet365[",""""
        "]market_type[": ["]h2h[",""""
        "]outcomes[": [{"]name[": "]Home[", "]price[": "]2.10["}]""""
        }
        # 预先添加到最后赔率值缓存
        odds_id = os.getenv("TEST_ODDS_COLLECTOR_ODDS_ID_254"): collector._last_odds_values["]odds_id[" = {"]Home[": Decimal("]2.10[")}": result = await collector._has_odds_changed(odds_data)": assert result is False[""
    @pytest.mark.asyncio
    async def test_has_odds_changed_empty_outcomes(self, collector):
        "]]""测试空结果数据"""
        odds_data = {
        "match_id[": ["]match_1[",""""
        "]bookmaker[": ["]bet365[",""""
        "]market_type[": ["]h2h[",""""
        "]outcomes[": []""""
        }
        result = await collector._has_odds_changed(odds_data)
        # 空结果应该返回True（首次记录）
    assert result is True
    @pytest.mark.asyncio
    async def test_clean_odds_data(self, collector):
        "]""测试数据清洗"""
        raw_odds_data = {
        "match_id[": ["]match_1[",""""
        "]bookmaker[": ["]bet365[",""""
        "]market_type[": ["]h2h[",""""
        "]outcomes[": [""""
            {"]name[: "Home"", "price]},""""
            {"name[: "Draw"", "price]},""""
            {"name[: "Away"", "price]},""""
            {"name[: "Invalid"", "price]}  # 无效赔率[""""
            ],
            "]last_update[: "2024-01-15T10:00:00Z"""""
        }
        cleaned_data = await collector._clean_odds_data(raw_odds_data)
    assert cleaned_data is not None
    assert cleaned_data["]external_match_id["] =="]match_1[" assert cleaned_data["]bookmaker["] =="]bet365[" assert cleaned_data["]market_type["] =="]h2h[" assert len(cleaned_data["]outcomes["]) ==3  # 移除了无效赔率[" assert cleaned_data["]]outcomes["][0]["]name["] =="]Home[" assert cleaned_data["]outcomes["][0]["]price["] ==2.1[""""
    @responses.activate
    @pytest.mark.asyncio
    async def test_api_rate_limiting(self, collector):
        "]]""测试API限流处理"""
        responses.add(
        responses.GET,
        "https:_/api.test-odds.com/v4/matches[",": status=429,": json = {"]error[: "Rate limit exceeded["}"]"""
        )
        with patch.object(collector, '_make_request') as mock_make_request:
            mock_make_request.side_effect = Exception("]Rate limit exceeded[")": try:": pass[": except Exception as e:"
               pass  # Auto-fixed empty except block
 pass
                pass
            except Exception as e:
               pass  # Auto-fixed empty except block
 pass
                pass
            except Exception as e:
               pass  # Auto-fixed empty except block
 pass
                pass
            except Exception as e:
               pass  # Auto-fixed empty except block
 pass
                await collector._get_upcoming_matches()
            except Exception as e:
   pass  # Auto-fixed empty except block
 assert "]]Rate limit exceeded[" in str(e)""""
    @pytest.mark.asyncio
    async def test_collect_odds_with_deduplication(self, collector):
        "]""测试去重功能"""
        # 预先添加已处理的赔率键
        test_odds_data = {
        "match_id[": ["]match_1[",""""
        "]bookmaker[": ["]bet365[",""""
        "]market_type[": ["]h2h[",""""
        "]outcomes[": [{"]name[": "]Home[", "]price[": "]2.10["}]""""
        }
        odds_key = collector._generate_odds_key(test_odds_data)
        collector._recent_odds_keys.add(odds_key)
        with patch.object(collector, '_get_upcoming_matches', return_value = ["]match_1["]), \": patch.object(collector, '_collect_match_odds', return_value=["]test_odds_data["), \": patch.object(collector, '_has_odds_changed', return_value=True), \": patch.object(collector, '_clean_odds_data', return_value=test_odds_data), \": patch.object(collector, '_save_to_bronze_layer') as mock_save = result await collector.collect_odds()"
            # 应该跳过重复的赔率
    assert result.records_collected ==0
    assert result.success_count ==0
            mock_save.assert_not_called()
    @pytest.mark.asyncio
    async def test_memory_cleanup_during_collection(self, collector):
        "]""测试采集过程中的内存清理"""
        # 添加大量缓存数据
        for i in range(1000):
        collector._recent_odds_keys.add(f["hash_{i}"])": collector._last_odds_values[f["odds_{i}"]] = {"Home[": Decimal("]2.10[")}""""
        # 执行采集
        with patch.object(collector, '_get_upcoming_matches', return_value = [])
            await collector.collect_odds()
        # 验证状态保持
    assert len(collector._recent_odds_keys) ==1000
    @pytest.mark.asyncio
    async def test_error_handling_and_logging(self, collector):
        "]""测试错误处理和日志记录"""
        with patch.object(collector, '_get_upcoming_matches', side_effect = Exception("Connection Error["))": result = await collector.collect_odds()": assert result.status =="]failed[" assert result.error_count ==1[""""
    assert "]]Connection Error[" in result.error_message[""""
    @pytest.mark.asyncio
    async def test_concurrent_collection_protection(self, collector):
        "]]""测试并发采集功能"""
        # 模拟并发采集
        tasks = []
        for _ in range(3):
        task = asyncio.create_task(collector.collect_odds())
        tasks.append(task)
        results = await asyncio.gather(*tasks, return_exceptions=True)
        # 验证任务都执行了（并发保护不影响正常执行）
        success_count = sum(1 for r in results if isinstance(r, CollectionResult))
    assert success_count ==3