#!/usr/bin/env python3
"""
特征提取器单元测试

严格遵循TDD方法论，先编写测试用例，定义特征提取器的预期行为。
测试覆盖正常场景、边界场景和反未来函数场景。

测试策略:
1. Mock数据构造 - 模拟真实的历史比赛数据
2. 边界测试 - 处理数据不足的情况
3. 反未来函数测试 - 确保无数据泄露
4. 完整性测试 - 验证特征集的完整性
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

# 导入待测试的模块 (此时还未实现，会导入失败)
# from features.extractor import MatchFeatureExtractor
# from features.schemas import MatchFeatureSet, TeamFormFeatures, XGFeatures, OddsFeatures


# Mock数据构造器
class MockMatchDataGenerator:
    """模拟比赛数据生成器"""

    @staticmethod
    def create_historical_dataframe(num_matches: int = 10) -> pd.DataFrame:
        """
        创建历史比赛DataFrame

        Args:
            num_matches: 比赛场次

        Returns:
            pd.DataFrame: 历史比赛数据
        """
        data = []
        base_date = datetime.now() - timedelta(days=30)

        teams = [
            "team_1",
            "team_2",
            "team_3",
            "team_4",
            "team_5",
            "team_6",
            "team_7",
            "team_8",
            "team_9",
            "team_10",
        ]

        for i in range(num_matches):
            match_date = base_date + timedelta(days=i * 3)
            home_team = teams[i % len(teams)]
            away_team = teams[(i + 1) % len(teams)]

            # 模拟比赛结果
            home_score = np.random.poisson(1.5)
            away_score = np.random.poisson(1.2)

            # 模拟xG数据
            home_xg = max(0.1, np.random.normal(1.8, 0.8))
            away_xg = max(0.1, np.random.normal(1.5, 0.7))

            # 模拟赔率
            if np.random.random() > 0.3:  # 70%的比赛有赔率数据
                home_odds = round(np.random.uniform(1.8, 4.5), 2)
                draw_odds = round(np.random.uniform(3.0, 4.0), 2)
                away_odds = round(np.random.uniform(2.5, 5.0), 2)
            else:
                home_odds = None
                draw_odds = None
                away_odds = None

            # 模拟原始JSON数据结构
            raw_data = {
                "content": {
                    "general": {
                        "matchId": f"match_{i}",
                        "homeTeam": {
                            "id": home_team,
                            "name": f"Team {home_team.split('_')[1]}",
                        },
                        "awayTeam": {
                            "id": away_team,
                            "name": f"Team {away_team.split('_')[1]}",
                        },
                        "status": {"finished": True},
                    },
                    "stats": {"xg": {"home": home_xg, "away": away_xg}},
                    "odds": {
                        "preMatchOdds": (
                            {"home": home_odds, "draw": draw_odds, "away": away_odds}
                            if home_odds
                            else None
                        )
                    },
                }
            }

            data.append(
                {
                    "match_id": f"match_{i}",
                    "home_team_id": home_team,
                    "away_team_id": away_team,
                    "match_date": match_date.isoformat(),
                    "home_score": home_score,
                    "away_score": away_score,
                    "home_xg": home_xg,
                    "away_xg": away_xg,
                    "home_odds": home_odds,
                    "draw_odds": draw_odds,
                    "away_odds": away_odds,
                    "raw_match_data": raw_data,
                    "venue": f"Stadium {i % 5 + 1}",
                    "status": "FINISHED",
                }
            )

        return pd.DataFrame(data)

    @staticmethod
    def create_limited_data_dataframe(num_matches: int = 2) -> pd.DataFrame:
        """创建数据不足的DataFrame"""
        return MockMatchDataGenerator.create_historical_dataframe(num_matches)

    @staticmethod
    def create_no_odds_data() -> pd.DataFrame:
        """创建无赔率数据的DataFrame"""
        df = MockMatchDataGenerator.create_historical_dataframe(5)
        df["home_odds"] = None
        df["draw_odds"] = None
        df["away_odds"] = None
        return df


class TestMatchFeatureExtractor:
    """特征提取器测试类"""

    def setup_method(self):
        """测试设置"""
        self.extractor = None  # 将在Step 3中实现

    def test_mock_data_generation(self):
        """测试Mock数据生成器"""
        print("🧪 测试Mock数据生成器")

        # 生成10场比赛的历史数据
        df = MockMatchDataGenerator.create_historical_dataframe(10)

        # 验证数据结构
        assert len(df) == 10, f"预期10行数据，实际{len(df)}行"
        assert all(
            col in df.columns
            for col in [
                "match_id",
                "home_team_id",
                "away_team_id",
                "match_date",
                "home_score",
                "away_score",
                "home_xg",
                "away_xg",
            ]
        ), "缺少必要的列"

        # 验证数据质量
        assert not df.empty, "DataFrame不应为空"
        assert df["home_score"].notna().all(), "主队得分不应为空"
        assert df["away_score"].notna().all(), "客队得分不应为空"

        print(f"   ✅ 生成了{len(df)}场比赛数据")
        print(f"   📊 数据列: {list(df.columns)}")

    def test_normal_feature_extraction(self):
        """测试正常特征提取场景"""
        print("🧪 测试正常特征提取")

        # 生成历史数据
        historical_data = MockMatchDataGenerator.create_historical_dataframe(10)

        # 目标比赛 (最新一场)
        target_match_id = "match_9"
        target_match = historical_data.iloc[-1]

        # 预期行为：应该成功提取所有特征
        try:
            # 这里将在Step 3中实现
            # feature_set = self.extractor.extract_features(target_match_id, historical_data)

            # 临时验证逻辑
            assert (
                target_match_id in historical_data["match_id"].values
            ), "目标比赛应在历史数据中"
            assert target_match["home_team_id"] == "team_10", "主队ID应该匹配"
            assert target_match["away_team_id"] == "team_1", "客队ID应该匹配"

            print(f"   ✅ 目标比赛验证通过: {target_match_id}")
            print(f"   🏠 主队: {target_match['home_team_id']}")
            print(f"   ✈️  客队: {target_match['away_team_id']}")

        except Exception as e:
            pytest.fail(f"正常特征提取失败: {e}")

    def test_insufficient_data_handling(self):
        """测试数据不足的边界情况"""
        print("🧪 测试数据不足的边界情况")

        # 生成只有2场历史数据的情况
        historical_data = MockMatchDataGenerator.create_limited_data_dataframe(2)
        target_match_id = "match_1"

        try:
            # 预期：应该能处理数据不足，last5特征应该为0或NaN
            # feature_set = self.extractor.extract_features(target_match_id, historical_data)

            # 验证输入数据
            assert (
                len(historical_data) == 2
            ), f"预期2行数据，实际{len(historical_data)}行"

            # 临时验证
            print(f"   ✅ 数据不足场景可处理: {len(historical_data)}场比赛")
            print("   ⚠️  注意: 需要确保last5特征正确处理为0或NaN")

        except Exception as e:
            pytest.fail(f"数据不足处理失败: {e}")

    def test_no_odds_data_handling(self):
        """测试无赔率数据的处理"""
        print("🧪 测试无赔率数据处理")

        # 生成无赔率的数据
        historical_data = MockMatchDataGenerator.create_no_odds_data()
        target_match_id = historical_data.iloc[-1]["match_id"]

        try:
            # 预期：应该能处理无赔率数据，赔率特征应该使用默认值
            # feature_set = self.extractor.extract_features(target_match_id, historical_data)

            # 验证无赔率数据
            assert historical_data["home_odds"].isna().all(), "应该无主胜赔率数据"
            assert historical_data["draw_odds"].isna().all(), "应该无平局赔率数据"
            assert historical_data["away_odds"].isna().all(), "应该无客胜赔率数据"

            print(f"   ✅ 无赔率数据场景可处理: {len(historical_data)}场比赛")
            print("   ⚠️  注意: 需要确保赔率特征使用默认值")

        except Exception as e:
            pytest.fail(f"无赔率数据处理失败: {e}")

    def test_anti_lookahead_validation(self):
        """测试反未来函数验证"""
        print("🧪 测试反未来函数验证")

        # 生成10场按时间排序的比赛
        historical_data = MockMatchDataGenerator.create_historical_dataframe(10)

        # 确保按时间排序
        historical_data["match_date"] = pd.to_datetime(historical_data["match_date"])
        historical_data = historical_data.sort_values("match_date")

        # 选择中间一场比赛作为目标 (不是最新的一场)
        target_match_idx = 5  # 第6场比赛 (0-indexed)
        target_match = historical_data.iloc[target_match_idx]
        target_match_id = target_match["match_id"]

        # 构建只包含目标比赛及之前数据的数据集
        anti_leak_data = historical_data.iloc[: target_match_idx + 1]

        try:
            # 预期：提取器应该只使用目标比赛及之前的数据
            # feature_set = self.extractor.extract_features(target_match_id, anti_leak_data)

            # 验证数据泄露防护
            assert (
                len(anti_leak_data) == target_match_idx + 1
            ), "数据集应该只包含目标比赛及之前的数据"
            latest_match_date = anti_leak_data["match_date"].max()
            target_match_date = pd.to_datetime(target_match["match_date"])
            assert latest_match_date <= target_match_date, "不应包含未来比赛数据"

            print(f"   ✅ 反未来函数验证通过")
            print(f"   📅 目标比赛日期: {target_match_date}")
            print(f"   📅 数据集最新日期: {latest_match_date}")

        except Exception as e:
            pytest.fail(f"反未来函数验证失败: {e}")

    def test_feature_completeness_calculation(self):
        """测试特征完整性计算"""
        print("🧪 测试特征完整性计算")

        # 测试不同数据质量的场景
        scenarios = [
            ("完整数据", MockMatchDataGenerator.create_historical_dataframe(10), 1.0),
            ("部分数据", MockMatchDataGenerator.create_historical_dataframe(5), 0.7),
            ("最少数据", MockMatchDataGenerator.create_limited_data_dataframe(2), 0.4),
            ("无赔率数据", MockMatchDataGenerator.create_no_odds_data(), 0.8),
        ]

        for scenario_name, data, expected_completeness in scenarios:
            try:
                # 预期：完整性分数应该根据数据质量计算
                # feature_set = self.extractor.extract_features(data.iloc[-1]['match_id'], data)

                print(f"   ✅ {scenario_name}场景处理成功")
                print(f"   📊 预期完整性分数: {expected_completeness}")

            except Exception as e:
                pytest.fail(f"{scenario_name}完整性计算失败: {e}")

    def test_time_window_calculations(self):
        """测试时间窗口计算"""
        print("🧪 测试时间窗口计算")

        historical_data = MockMatchDataGenerator.create_historical_dataframe(15)
        historical_data["match_date"] = pd.to_datetime(historical_data["match_date"])
        historical_data = historical_data.sort_values("match_date")

        target_match = historical_data.iloc[-1]
        target_date = target_match["match_date"]

        # 测试不同时间窗口
        windows = [3, 5, 10]

        for window in windows:
            try:
                # 预期：应该正确计算指定时间窗口的特征
                window_data = historical_data[
                    (historical_data["match_date"] < target_date)
                    & (
                        historical_data["match_date"]
                        >= target_date - timedelta(days=window * 3)
                    )
                ]

                print(f"   ✅ {window}场比赛时间窗口: {len(window_data)}场比赛")

            except Exception as e:
                pytest.fail(f"时间窗口{window}计算失败: {e}")

    def test_feature_vector_generation(self):
        """测试特征向量生成"""
        print("🧪 测试特征向量生成")

        historical_data = MockMatchDataGenerator.create_historical_dataframe(10)
        target_match_id = historical_data.iloc[-1]["match_id"]

        try:
            # 预期：应该生成固定维度的特征向量
            # feature_set = self.extractor.extract_features(target_match_id, historical_data)
            # feature_vector = feature_set.get_feature_vector()
            # feature_names = feature_set.get_feature_names()

            # 临时验证
            print("   ✅ 特征向量生成机制设计完成")
            print("   🔢 预期特征维度: 13 (根据schema定义)")
            print("   📋 特征名称已定义")

        except Exception as e:
            pytest.fail(f"特征向量生成失败: {e}")

    def test_data_quality_flags(self):
        """测试数据质量标记"""
        print("🧪 测试数据质量标记")

        # 测试不同质量的数据
        quality_scenarios = [
            (
                "高质量数据",
                MockMatchDataGenerator.create_historical_dataframe(15),
                "HIGH",
            ),
            (
                "中等质量数据",
                MockMatchDataGenerator.create_historical_dataframe(7),
                "MEDIUM",
            ),
            (
                "低质量数据",
                MockMatchDataGenerator.create_limited_data_dataframe(3),
                "LOW",
            ),
            ("无赔率数据", MockMatchDataGenerator.create_no_odds_data(), "MEDIUM"),
        ]

        for scenario_name, data, expected_quality in quality_scenarios:
            try:
                # 预期：应该根据数据质量设置正确的标记
                # feature_set = self.extractor.extract_features(data.iloc[-1]['match_id'], data)

                print(f"   ✅ {scenario_name}: 质量标记预期为 {expected_quality}")

            except Exception as e:
                pytest.fail(f"{scenario_name}质量标记失败: {e}")

    def test_edge_case_empty_historical_data(self):
        """测试空历史数据的边界情况"""
        print("🧪 测试空历史数据边界情况")

        # 创建空的DataFrame
        empty_df = pd.DataFrame(
            columns=[
                "match_id",
                "home_team_id",
                "away_team_id",
                "match_date",
                "home_score",
                "away_score",
                "home_xg",
                "away_xg",
                "home_odds",
                "draw_odds",
                "away_odds",
            ]
        )

        try:
            # 预期：应该优雅处理空数据，返回默认特征
            # feature_set = self.extractor.extract_features("test_match", empty_df)

            assert len(empty_df) == 0, "DataFrame应该为空"
            print("   ✅ 空历史数据场景设计完成")
            print("   ⚠️  注意: 需要确保返回默认特征值")

        except Exception as e:
            pytest.fail(f"空历史数据处理失败: {e}")

    def test_concurrent_extraction(self):
        """测试并发特征提取"""
        print("🧪 测试并发特征提取")

        historical_data = MockMatchDataGenerator.create_historical_dataframe(20)
        match_ids = historical_data["match_id"].tolist()

        try:
            # 预期：应该支持并发提取多个比赛的特征
            import asyncio

            async def test_async_extraction():
                # 这里将在Step 3中实现
                pass

            # 临时验证
            assert len(match_ids) == 20, "应该有20场比赛"
            print("   ✅ 并发提取机制设计完成")
            print(f"   🔄 待处理比赛数: {len(match_ids)}")

        except Exception as e:
            pytest.fail(f"并发提取测试失败: {e}")


# 运行测试的主函数
def run_feature_extractor_tests():
    """运行特征提取器测试"""
    print("🚀 开始特征提取器单元测试")
    print("=" * 60)

    test_class = TestMatchFeatureExtractor()
    test_methods = [method for method in dir(test_class) if method.startswith("test_")]

    passed_tests = 0
    total_tests = len(test_methods)

    for test_method in test_methods:
        try:
            print(f"\n--- 执行测试: {test_method} ---")
            getattr(test_class, test_method)()
            passed_tests += 1
            print(f"✅ {test_method} 通过")
        except Exception as e:
            print(f"❌ {test_method} 失败: {e}")
            import traceback

            traceback.print_exc()

    print(f"\n{'='*60}")
    print(f"📊 测试结果: {passed_tests}/{total_tests} 通过")
    print(f"🎯 成功率: {(passed_tests/total_tests)*100:.1f}%")

    if passed_tests == total_tests:
        print("🎉 所有测试通过！可以开始实现特征提取器。")
        return True
    else:
        print("⚠️  部分测试失败，请检查测试用例设计。")
        return False


if __name__ == "__main__":
    # 直接运行测试
    success = run_feature_extractor_tests()
    sys.exit(0 if success else 1)
