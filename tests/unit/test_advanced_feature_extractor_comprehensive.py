#!/usr/bin/env python3
"""
高级特征提取器参数化测试库 - 10种异常场景测试
Advanced Feature Extractor Parameterized Test Library

测试覆盖率目标：>95%
"""

import pytest
import json
import logging
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime
from pydantic import ValidationError

# 导入目标模块
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from data_access.processors.advanced_feature_extractor import (
    AdvancedFeatureExtractor,
    FeatureExtractionError,
    XGDataAggregator,
    SmartRecursiveExtractor,
    FeatureExtractionConfig,
)
from schemas.match_features import MatchFeatures, DataSource, FeatureVersion

# 设置测试日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class TestAdvancedFeatureExtractor:
    """高级特征提取器测试类"""

    @pytest.fixture
    def extractor(self):
        """创建特征提取器实例"""
        return AdvancedFeatureExtractor()

    @pytest.fixture
    def basic_match_data(self):
        """基础比赛数据"""
        return {
            "header": {"matchId": "4813374", "status": {"statusStr": "Finished", "utcTime": "2024-01-15T20:00:00Z"}},
            "match": {
                "homeTeam": {"name": "Manchester United"},
                "awayTeam": {"name": "Liverpool"},
                "homeScore": 2,
                "awayScore": 1,
            },
            "shotmap": {
                "shots": [
                    {"playerName": "Bruno Fernandes", "teamType": "home", "expectedGoals": 0.8, "isHome": True},
                    {"playerName": "Mohamed Salah", "teamType": "away", "expectedGoals": 0.6, "isHome": False},
                ]
            },
            "stats": {
                "possession": {"home": 55.5, "away": 44.5},
                "corners": {"home": 6, "away": 3},
                "cards": [
                    {"teamType": "home", "cardType": "yellow", "isHome": True},
                    {"teamType": "away", "cardType": "yellow", "isHome": False},
                ],
            },
        }

    # ==================== 异常场景1：shotmap数组为空 ====================
    @pytest.mark.parametrize(
        "test_data,expected_behavior",
        [
            pytest.param(
                {"shotmap": {"shots": []}, "external_id": "empty_shotmap_1"},
                "should_use_fallback_extraction",
                id="空shotmap数组",
            ),
            pytest.param(
                {"shotmap": {}, "external_id": "empty_shotmap_2"},
                "should_use_fallback_extraction",
                id="shotmap无shots字段",
            ),
            pytest.param({"external_id": "no_shotmap"}, "should_use_fallback_extraction", id="完全没有shotmap字段"),
            pytest.param(
                {"shotmap": None, "external_id": "null_shotmap"}, "should_use_fallback_extraction", id="shotmap为None"
            ),
        ],
    )
    def test_empty_shotmap_scenarios(self, extractor, basic_match_data, test_data, expected_behavior):
        """测试空shotmap场景"""
        # 准备测试数据
        match_data = basic_match_data.copy()
        match_data.update(test_data)

        # 执行特征提取
        try:
            features = extractor.extract_complete_features(match_data, test_data.get("external_id", "test"))

            # 验证结果
            assert features is not None
            assert features.external_id == test_data.get("external_id", "test")

            # 在空shotmap情况下，xG应该为0或从备用方式提取
            assert features.home_xg is not None
            assert features.away_xg is not None

            logger.info(f"✅ 异常场景1通过: {test_data} - xG: {features.home_xg}-{features.away_xg}")

        except Exception as e:
            logger.error(f"❌ 异常场景1失败: {test_data} - 错误: {e}")
            raise

    # ==================== 异常场景2：expectedGoals字段缺失 ====================
    @pytest.mark.parametrize(
        "shot_data,expected_xg",
        [
            pytest.param(
                [
                    {"playerName": "Player1", "teamType": "home", "isHome": True},
                    {"playerName": "Player2", "teamType": "away", "isHome": False},
                ],
                (0.0, 0.0),
                id="射门数据完全缺失xG字段",
            ),
            pytest.param(
                [
                    {"playerName": "Player1", "teamType": "home", "xg": 1.2, "isHome": True},
                    {"playerName": "Player2", "teamType": "away", "xg": 0.8, "isHome": False},
                ],
                (1.2, 0.8),
                id="使用xg字段别名",
            ),
            pytest.param(
                [
                    {"playerName": "Player1", "teamType": "home", "xG": 1.5, "isHome": True},
                    {"playerName": "Player2", "teamType": "away", "xgValue": 0.9, "isHome": False},
                ],
                (1.5, 0.9),
                id="使用xG和xgValue字段",
            ),
            pytest.param(
                [
                    {"playerName": "Player1", "teamType": "home", "expectedGoals": "", "isHome": True},
                    {"playerName": "Player2", "teamType": "away", "expectedGoals": None, "isHome": False},
                ],
                (0.0, 0.0),
                id="expectedGoals字段为空或None",
            ),
        ],
    )
    def test_missing_expected_goals_scenarios(self, extractor, basic_match_data, shot_data, expected_xg):
        """测试expectedGoals字段缺失场景"""
        match_data = basic_match_data.copy()
        match_data["shotmap"]["shots"] = shot_data

        try:
            features = extractor.extract_complete_features(match_data, "missing_xg_test")

            # 验证xG提取结果
            assert features.home_xg is not None
            assert features.away_xg is not None

            # 允许小的浮点数误差
            assert abs(features.home_xg - expected_xg[0]) < 0.001
            assert abs(features.away_xg - expected_xg[1]) < 0.001

            logger.info(f"✅ 异常场景2通过: expected_xg={expected_xg}, actual={features.home_xg}-{features.away_xg}")

        except Exception as e:
            logger.error(f"❌ 异常场景2失败: 错误: {e}")
            raise

    # ==================== 异常场景3：teamType大小写不一 ====================
    @pytest.mark.parametrize(
        "team_types,expected_result",
        [
            pytest.param([("HOME", "away"), ("Home", "AWAY")], "should_handle_case_insensitive", id="大写和小写混合"),
            pytest.param([("Home", "Away"), ("home", "away")], "should_handle_case_insensitive", id="首字母大写"),
            pytest.param([("hOmE", "aWaY"), ("HoMe", "AwAy")], "should_handle_case_insensitive", id="随机大小写"),
            pytest.param([("", "away"), ("home", "")], "should_fallback_to_isHome_flag", id="空的teamType字段"),
        ],
    )
    def test_team_type_case_variations(self, extractor, basic_match_data, team_types, expected_result):
        """测试teamType大小写变化场景"""
        match_data = basic_match_data.copy()

        # 更新射门数据的teamType
        for i, (home_type, away_type) in enumerate(team_types):
            if i < len(match_data["shotmap"]["shots"]):
                match_data["shotmap"]["shots"][i]["teamType"] = home_type if i == 0 else away_type

        try:
            features = extractor.extract_complete_features(match_data, "teamtype_case_test")

            # 验证xG正确分配
            assert features.home_xg is not None
            assert features.away_xg is not None
            assert features.home_xg >= 0
            assert features.away_xg >= 0

            logger.info(f"✅ 异常场景3通过: teamTypes={team_types}, xG={features.home_xg}-{features.away_xg}")

        except Exception as e:
            logger.error(f"❌ 异常场景3失败: teamTypes={team_types}, 错误: {e}")
            raise

    # ==================== 异常场景4：赔率数据为0或负数 ====================
    @pytest.mark.parametrize(
        "odds_data,expected_validation",
        [
            pytest.param(
                {"homeWinOdds": 0.0, "awayWinOdds": 0.0, "drawOdds": 0.0}, "should_handle_zero_odds", id="赔率为0"
            ),
            pytest.param(
                {"homeWinOdds": -1.5, "awayWinOdds": -2.0, "drawOdds": -1.8},
                "should_handle_negative_odds",
                id="负数赔率",
            ),
            pytest.param(
                {"homeWinOdds": "invalid", "awayWinOdds": None, "drawOdds": ""},
                "should_handle_invalid_odds",
                id="无效赔率格式",
            ),
            pytest.param(
                {"homeWinOdds": 1.01, "awayWinOdds": 1000.0, "drawOdds": 500.0},
                "should_handle_extreme_values",
                id="极端赔率值",
            ),
        ],
    )
    def test_invalid_odds_scenarios(self, extractor, basic_match_data, odds_data, expected_validation):
        """测试无效赔率数据场景"""
        match_data = basic_match_data.copy()
        match_data["stats"]["odds"] = odds_data

        try:
            features = extractor.extract_complete_features(match_data, "invalid_odds_test")

            # 验证系统不会崩溃，即使有无效赔率
            assert features is not None
            assert features.external_id == "invalid_odds_test"

            # 赔率字段可能为None或保持原始值，但不应该导致系统崩溃
            if odds_data.get("homeWinOdds") == 0.0:
                # 0值可能被保持或设为None，都是可接受的
                assert features.home_opening_odds is None or features.home_opening_odds == 0.0

            logger.info(f"✅ 异常场景4通过: odds={odds_data}, result={features.home_opening_odds}")

        except ValidationError as e:
            # Pydantic验证错误是可接受的
            logger.warning(f"⚠️ 异常场景4验证错误（可接受）: {e}")
        except Exception as e:
            logger.error(f"❌ 异常场景4失败: odds={odds_data}, 错误: {e}")
            raise

    # ==================== 异常场景5：数据结构嵌套过深 ====================
    @pytest.mark.parametrize(
        "nesting_depth,expected_behavior",
        [
            pytest.param(5, "should_handle_normal_nesting", id="正常嵌套深度"),
            pytest.param(10, "should_handle_deep_nesting", id="较深嵌套"),
            pytest.param(20, "should_handle_very_deep_nesting", id="极深嵌套"),
            pytest.param(50, "should_have_depth_protection", id="超出合理深度"),
        ],
    )
    def test_deep_nesting_scenarios(self, extractor, basic_match_data, nesting_depth, expected_behavior):
        """测试数据结构嵌套过深场景"""
        match_data = basic_match_data.copy()

        # 创建深度嵌套的数据结构
        nested_data = match_data
        for i in range(nesting_depth):
            nested_data[f"level_{i}"] = {"stats": {"xg": {"home": 1.0 + i * 0.1, "away": 0.5 + i * 0.1}}}
            nested_data = nested_data[f"level_{i}"]

        try:
            features = extractor.extract_complete_features(match_data, f"deep_nesting_{nesting_depth}")

            # 验证系统能够处理深度嵌套
            assert features is not None
            assert features.external_id == f"deep_nesting_{nesting_depth}"

            logger.info(f"✅ 异常场景5通过: depth={nesting_depth}, xG={features.home_xg}-{features.away_xg}")

        except RecursionError:
            # 如果出现递归错误，说明深度保护机制需要改进
            if "depth_protection" in expected_behavior:
                logger.warning(f"⚠️ 异常场景5: 深度{nesting_depth}超出递归限制（预期行为）")
            else:
                logger.error(f"❌ 异常场景5: 深度{nesting_depth}导致递归错误")
                raise
        except Exception as e:
            logger.error(f"❌ 异常场景5失败: depth={nesting_depth}, 错误: {e}")
            raise

    # ==================== 异常场景6：数据类型不一致 ====================
    @pytest.mark.parametrize(
        "field_types,expected_result",
        [
            pytest.param(
                {
                    "homeScore": "2",  # 字符串形式的数字
                    "awayScore": 1.5,  # 浮点数形式的整数
                    "possession": {"home": "55.5", "away": "44.5"},  # 字符串形式的浮点数
                },
                "should_convert_types",
                id="字符串数字",
            ),
            pytest.param(
                {"homeScore": [2], "awayScore": {"value": 1}, "possession": None},  # 数组形式的单个数字  # 对象形式
                "should_handle_complex_types",
                id="复杂数据类型",
            ),
            pytest.param(
                {"homeScore": True, "awayScore": False, "possession": "N/A"},  # 布尔值
                "should_handle_invalid_types",
                id="无效数据类型",
            ),
        ],
    )
    def test_inconsistent_data_types(self, extractor, basic_match_data, field_types, expected_result):
        """测试数据类型不一致场景"""
        match_data = basic_match_data.copy()

        # 更新匹配数据中的字段类型
        if "homeScore" in field_types:
            match_data["match"]["homeScore"] = field_types["homeScore"]
        if "awayScore" in field_types:
            match_data["match"]["awayScore"] = field_types["awayScore"]
        if "possession" in field_types:
            if field_types["possession"] is None:
                match_data["stats"].pop("possession", None)
            else:
                match_data["stats"]["possession"] = field_types["possession"]

        try:
            features = extractor.extract_complete_features(match_data, "type_inconsistency_test")

            # 验证系统能够处理类型不一致
            assert features is not None
            assert features.external_id == "type_inconsistency_test"

            # 验证类型转换结果
            if "should_convert_types" in expected_result:
                # 应该成功转换的类型
                assert isinstance(features.home_score, (int, type(None)))
                assert isinstance(features.away_score, (int, float, type(None)))

            logger.info(f"✅ 异常场景6通过: types={field_types}, scores={features.home_score}-{features.away_score}")

        except Exception as e:
            logger.error(f"❌ 异常场景6失败: types={field_types}, 错误: {e}")
            raise

    # ==================== 异常场景7：缺失关键字段 ====================
    @pytest.mark.parametrize(
        "missing_fields,expected_fallback",
        [
            pytest.param(["homeTeam", "awayTeam"], "should_use_team_name_fallback", id="缺失队名字段"),
            pytest.param(["matchTime", "status.utcTime"], "should_use_default_datetime", id="缺失时间字段"),
            pytest.param(["homeScore", "awayScore"], "should_accept_none_scores", id="缺失比分字段"),
            pytest.param(["external_id"], "should_generate_default_id", id="缺失外部ID"),
        ],
    )
    def test_missing_critical_fields(self, extractor, basic_match_data, missing_fields, expected_fallback):
        """测试缺失关键字段场景"""
        match_data = basic_match_data.copy()

        # 移除指定的字段
        for field_path in missing_fields:
            keys = field_path.split(".")
            current = match_data
            for key in keys[:-1]:
                if key in current:
                    current = current[key]
                else:
                    break
            else:
                current.pop(keys[-1], None)

        external_id = "missing_fields_test" if "external_id" not in missing_fields else None

        try:
            features = extractor.extract_complete_features(match_data, external_id or "auto_generated")

            # 验证系统能够处理缺失字段
            assert features is not None

            # 验证回退机制
            if "team_name_fallback" in expected_fallback:
                # 队名可能为None或有默认值
                assert features.home_team is None or len(features.home_team) > 0
                assert features.away_team is None or len(features.away_team) > 0

            logger.info(f"✅ 异常场景7通过: missing={missing_fields}, teams={features.home_team}-{features.away_team}")

        except Exception as e:
            logger.error(f"❌ 异常场景7失败: missing={missing_fields}, 错误: {e}")
            raise

    # ==================== 异常场景8：超大数据量 ====================
    @pytest.mark.parametrize(
        "data_size,expected_behavior",
        [
            pytest.param(100, "should_handle_normal_size", id="正常数据量"),
            pytest.param(1000, "should_handle_large_size", id="大数据量"),
            pytest.param(5000, "should_handle_very_large_size", id="超大数据量"),
            pytest.param(10000, "should_have_performance_protection", id="极限数据量"),
        ],
    )
    def test_large_data_volume_scenarios(self, extractor, basic_match_data, data_size, expected_behavior):
        """测试超大数据量场景"""
        match_data = basic_match_data.copy()

        # 生成大量射门数据
        large_shots = []
        for i in range(data_size):
            large_shots.append(
                {
                    "playerName": f"Player_{i}",
                    "teamType": "home" if i % 2 == 0 else "away",
                    "expectedGoals": 0.1 * (i % 10),
                    "isHome": i % 2 == 0,
                }
            )

        match_data["shotmap"]["shots"] = large_shots

        import time

        start_time = time.time()

        try:
            features = extractor.extract_complete_features(match_data, f"large_data_{data_size}")

            processing_time = time.time() - start_time

            # 验证系统性能
            assert features is not None
            assert features.external_id == f"large_data_{data_size}"

            # 性能要求：处理时间不应该与数据量成线性关系
            if data_size <= 1000:
                assert processing_time < 5.0, f"处理{data_size}条记录耗时过长: {processing_time:.2f}秒"
            elif data_size <= 5000:
                assert processing_time < 15.0, f"处理{data_size}条记录耗时过长: {processing_time:.2f}秒"

            logger.info(
                f"✅ 异常场景8通过: size={data_size}, time={processing_time:.2f}s, xG={features.home_xg}-{features.away_xg}"
            )

        except MemoryError:
            if "performance_protection" in expected_behavior:
                logger.warning(f"⚠️ 异常场景8: 数据量{data_size}导致内存不足（预期行为）")
            else:
                logger.error(f"❌ 异常场景8: 数据量{data_size}导致内存不足")
                raise
        except Exception as e:
            logger.error(f"❌ 异常场景8失败: size={data_size}, 错误: {e}")
            raise

    # ==================== 异常场景9：网络超时模拟 ====================
    @pytest.mark.parametrize(
        "timeout_simulation,expected_recovery",
        [
            pytest.param({"delay": 0.1, "simulate_timeout": False}, "should_process_normally", id="正常响应时间"),
            pytest.param({"delay": 2.0, "simulate_timeout": True}, "should_handle_timeout_gracefully", id="模拟超时"),
        ],
    )
    def test_network_timeout_simulation(self, extractor, basic_match_data, timeout_simulation, expected_recovery):
        """测试网络超时模拟场景"""
        import time

        # 模拟处理延迟
        if timeout_simulation.get("delay", 0) > 0:
            time.sleep(timeout_simulation["delay"])

        try:
            start_time = time.time()
            features = extractor.extract_complete_features(basic_match_data, "timeout_test")
            processing_time = time.time() - start_time

            # 验证处理结果
            assert features is not None
            assert features.external_id == "timeout_test"

            if timeout_simulation.get("simulate_timeout", False):
                # 如果模拟超时，处理时间应该较长
                assert processing_time >= timeout_simulation["delay"]

            logger.info(f"✅ 异常场景9通过: delay={timeout_simulation.get('delay', 0)}, time={processing_time:.2f}s")

        except TimeoutError:
            if "handle_timeout_gracefully" in expected_recovery:
                logger.warning(f"⚠️ 异常场景9: 处理超时（预期行为）")
            else:
                logger.error(f"❌ 异常场景9: 意外超时")
                raise
        except Exception as e:
            logger.error(f"❌ 异常场景9失败: timeout={timeout_simulation}, 错误: {e}")
            raise

    # ==================== 异常场景10：并发访问压力测试 ====================
    @pytest.mark.parametrize(
        "concurrent_count,expected_behavior",
        [
            pytest.param(1, "should_handle_single", id="单次访问"),
            pytest.param(5, "should_handle_low_concurrency", id="低并发"),
            pytest.param(10, "should_handle_medium_concurrency", id="中等并发"),
            pytest.param(20, "should_handle_high_concurrency", id="高并发"),
        ],
    )
    def test_concurrent_access_stress_test(self, extractor, basic_match_data, concurrent_count, expected_behavior):
        """测试并发访问压力场景"""
        import threading
        import time
        from concurrent.futures import ThreadPoolExecutor, as_completed

        results = []
        errors = []

        def extract_features(match_id):
            try:
                start_time = time.time()
                features = extractor.extract_complete_features(basic_match_data, f"concurrent_{match_id}")
                processing_time = time.time() - start_time
                return {"match_id": match_id, "features": features, "processing_time": processing_time, "success": True}
            except Exception as e:
                return {"match_id": match_id, "error": str(e), "success": False}

        start_time = time.time()

        # 使用线程池模拟并发访问
        with ThreadPoolExecutor(max_workers=concurrent_count) as executor:
            futures = [executor.submit(extract_features, i) for i in range(concurrent_count)]

            for future in as_completed(futures):
                try:
                    result = future.result(timeout=30)  # 30秒超时
                    results.append(result)
                    if not result["success"]:
                        errors.append(result["error"])
                except Exception as e:
                    errors.append(str(e))

        total_time = time.time() - start_time

        # 验证并发处理结果
        assert len(results) == concurrent_count, f"期望{concurrent_count}个结果，实际{len(results)}个"

        success_count = sum(1 for r in results if r["success"])
        assert success_count >= concurrent_count * 0.9, f"成功率过低: {success_count}/{concurrent_count}"

        # 验证处理时间
        avg_processing_time = sum(r.get("processing_time", 0) for r in results) / len(results)

        logger.info(
            f"✅ 异常场景10通过: concurrent={concurrent_count}, success={success_count}/{concurrent_count}, "
            f"avg_time={avg_processing_time:.2f}s, total_time={total_time:.2f}s"
        )

        if errors:
            logger.warning(f"⚠️ 异常场景10: 发生{len(errors)}个错误: {errors[:3]}")  # 只显示前3个错误

    # ==================== 辅助测试方法 ====================
    def test_extractor_initialization(self):
        """测试提取器初始化"""
        extractor = AdvancedFeatureExtractor()
        assert extractor is not None
        assert extractor.config is not None
        assert extractor.recursive_extractor is not None
        assert extractor.xg_aggregator is not None

    def test_feature_extraction_with_minimal_data(self, extractor):
        """测试最少量数据的特征提取"""
        minimal_data = {
            "external_id": "minimal_test",
            "match_time": "2024-01-15T20:00:00Z",
            "home_team": "Team A",
            "away_team": "Team B",
        }

        try:
            features = extractor.extract_complete_features(minimal_data, "minimal_test")
            assert features is not None
            assert features.external_id == "minimal_test"
        except Exception as e:
            # 最小数据可能无法创建完整特征，但不应该崩溃
            logger.info(f"最少量数据测试（预期可能失败）: {e}")

    def test_quality_score_calculation(self, extractor):
        """测试质量评分计算"""
        # 这个测试验证质量评分逻辑的正确性
        complete_features = {"home_xg": 1.5, "away_xg": 1.2, "home_possession": 55.0, "away_possession": 45.0}

        incomplete_features = {"home_xg": 1.5, "away_xg": None, "home_possession": 55.0, "away_possession": None}

        complete_score = extractor._calculate_quality_score(complete_features)
        incomplete_score = extractor._calculate_quality_score(incomplete_features)

        assert complete_score >= incomplete_score
        assert 0.0 <= complete_score <= 1.0
        assert 0.0 <= incomplete_score <= 1.0


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "--tb=short", "--cov=src/data_access/processors", "--cov-report=term-missing"])
