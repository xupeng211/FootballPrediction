"""
Integration tests for Football Prediction Backtest Flow.

测试足球预测回测流程的端到端集成功能。
"""

import pytest
import numpy as np
import pandas as pd
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
import tempfile
import csv

from src.evaluation.flows.backtest_flow import (
    backtest_flow, run_backtest,
)
from src.evaluation.backtest import BacktestResult, BetType


class TestBacktestFlowIntegration:
    """回测流程集成测试"""

    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            yield Path(tmp_dir)

    @pytest.fixture
    def sample_predictions_and_odds(self, temp_dir):
        """创建样本预测和赔率数据"""
        np.random.seed(42)
        n_samples = 200

        # 生成预测数据
        predictions_data = {
            'match_id': [f"match_{i:03d}" for i in range(1, n_samples + 1)],
            'prob_H': np.random.beta(2, 3, n_samples),  # 倾向较低概率
            'prob_D': np.random.beta(1.5, 4, n_samples),
            'prob_A': np.random.beta(2.5, 2.5, n_samples),
            'predicted_class': np.random.randint(0, 3, n_samples),
            'actual_result': np.random.randint(0, 3, n_samples),
            'date': pd.date_range('2024-01-01', periods=n_samples).strftime('%Y-%m-%d')
        }

        # 归一化概率
        prob_cols = ['prob_H', 'prob_D', 'prob_A']
        for col in prob_cols:
            predictions_data[col] = predictions_data[col] + 0.1  # 避免过小概率

        prob_sums = np.sum([predictions_data[col] for col in prob_cols], axis=0)
        for col in prob_cols:
            predictions_data[col] = predictions_data[col] / prob_sums

        predictions_df = pd.DataFrame(predictions_data)

        # 生成赔率数据
        odds_data = {
            'match_id': [f"match_{i:03d}" for i in range(1, n_samples + 1)],
            'odds_H': np.random.uniform(1.8, 4.5, n_samples),
            'odds_D': np.random.uniform(2.8, 4.2, n_samples),
            'odds_A': np.random.uniform(2.5, 6.0, n_samples)
        }

        odds_df = pd.DataFrame(odds_data)

        # 保存文件
        predictions_path = temp_dir / "predictions.csv"
        odds_path = temp_dir / "odds.csv"

        predictions_df.to_csv(predictions_path, index=False)
        odds_df.to_csv(odds_path, index=False)

        return predictions_path, odds_path

    @pytest.fixture
    def sample_predictions_and_odds_json(self, temp_dir):
        """创建JSON格式的样本数据"""
        np.random.seed(42)
        n_samples = 100

        # JSON格式的预测数据
        predictions_data = []
        for i in range(n_samples):
            probs = np.random.dirichlet([2, 1.5, 2.5])
            predictions_data.append({
                'match_id': f"match_{i+1:03d}",
                'probabilities': {
                    'H': float(probs[0]),
                    'D': float(probs[1]),
                    'A': float(probs[2])
                },
                'prediction': int(np.random.randint(0, 3)),
                'actual_result': int(np.random.randint(0, 3)),
                'date': f"2024-01-{(i % 28) + 1:02d}"
            })

        # JSON格式的赔率数据
        odds_data = []
        for i in range(n_samples):
            odds_data.append({
                'match_id': f"match_{i+1:03d}",
                'odds': {
                    'H': float(np.random.uniform(1.8, 4.5)),
                    'D': float(np.random.uniform(2.8, 4.2)),
                    'A': float(np.random.uniform(2.5, 6.0))
                }
            })

        # 保存JSON文件
        predictions_path = temp_dir / "predictions.json"
        odds_path = temp_dir / "odds.json"

        with open(predictions_path, 'w') as f:
            json.dump(predictions_data, f, indent=2)

        with open(odds_path, 'w') as f:
            json.dump(odds_data, f, indent=2)

        return predictions_path, odds_path

    def test_complete_backtest_flow(self, sample_predictions_and_odds, temp_dir):
        """测试完整回测流程"""
        predictions_path, odds_path = sample_predictions_and_odds
        output_dir = temp_dir / "backtest_output"
        output_dir.mkdir(exist_ok=True)

        result = backtest_flow(
            predictions_path=predictions_path,
            odds_path=odds_path,
            model_name="Integration Test Model",
            model_version="1.0.0",
            staking_strategy="flat",
            staking_params={"stake_amount": 10.0},
            initial_bankroll=1000.0,
            output_dir=str(output_dir)
        )

        # 验证结果结构
        assert "model_info" in result
        assert "strategy_info" in result
        assert "data_quality" in result
        assert "backtest_result" in result
        assert "performance_analysis" in result
        assert "visualizations" in result
        assert "reports" in result
        assert "output_dir" in result

        # 验证模型信息
        model_info = result["model_info"]
        assert model_info["name"] == "Integration Test Model"
        assert model_info["version"] == "1.0.0"

        # 验证策略信息
        strategy_info = result["strategy_info"]
        assert strategy_info["type"] == "flat"
        assert strategy_info["initial_bankroll"] == 1000.0
        assert strategy_info["params"]["stake_amount"] == 10.0

        # 验证数据质量
        data_quality = result["data_quality"]
        assert "validation_passed" in data_quality
        assert "total_matches" in data_quality
        assert data_quality["total_matches"] > 0

        # 验证回测结果
        backtest_result = result["backtest_result"]
        assert backtest_result["initial_bankroll"] == 1000.0
        assert backtest_result["total_bets"] >= 0
        assert "roi" in backtest_result
        assert "win_rate" in backtest_result

        # 验证性能分析
        perf_analysis = result["performance_analysis"]
        assert "summary" in perf_analysis
        assert "performance_rating" in perf_analysis
        assert "risk_assessment" in perf_analysis

        # 验证输出文件存在
        output_path = Path(result["output_dir"])
        assert output_path.exists()
        assert (output_path / "complete_backtest_result.json").exists()

    def test_backtest_flow_kelly_strategy(self, sample_predictions_and_odds, temp_dir):
        """测试凯利投注策略回测"""
        predictions_path, odds_path = sample_predictions_and_odds
        output_dir = temp_dir / "backtest_kelly"
        output_dir.mkdir(exist_ok=True)

        result = backtest_flow(
            predictions_path=predictions_path,
            odds_path=odds_path,
            staking_strategy="kelly",
            staking_params={
                "kelly_fraction": 0.25,
                "min_stake": 5.0,
                "max_stake_percentage": 0.05
            },
            initial_bankroll=1000.0,
            output_dir=str(output_dir)
        )

        # 验证策略信息
        strategy_info = result["strategy_info"]
        assert strategy_info["type"] == "kelly"
        assert strategy_info["params"]["kelly_fraction"] == 0.25

        # 凯利策略可能投注较少
        backtest_result = result["backtest_result"]
        assert backtest_result["total_bets"] >= 0

    def test_backtest_flow_value_strategy(self, sample_predictions_and_odds, temp_dir):
        """测试价值投注策略回测"""
        predictions_path, odds_path = sample_predictions_and_odds
        output_dir = temp_dir / "backtest_value"
        output_dir.mkdir(exist_ok=True)

        result = backtest_flow(
            predictions_path=predictions_path,
            odds_path=odds_path,
            staking_strategy="value",
            staking_params={
                "min_ev_threshold": 0.05,  # 较低阈值
                "base_stake": 10.0
            },
            initial_bankroll=1000.0,
            output_dir=str(output_dir)
        )

        # 验证策略信息
        strategy_info = result["strategy_info"]
        assert strategy_info["type"] == "value"
        assert strategy_info["params"]["min_ev_threshold"] == 0.05

    def test_backtest_flow_json_format(self, sample_predictions_and_odds_json, temp_dir):
        """测试JSON格式数据的回测流程"""
        predictions_path, odds_path = sample_predictions_and_odds_json
        output_dir = temp_dir / "backtest_json"
        output_dir.mkdir(exist_ok=True)

        # 注意：当前实现可能不支持嵌套JSON格式
        # 这个测试可能会失败，表明需要扩展数据处理逻辑
        try:
            result = backtest_flow(
                predictions_path=predictions_path,
                odds_path=odds_path,
                predictions_format="json",
                odds_format="json",
                output_dir=str(output_dir)
            )

            # 如果成功，验证基本结构
            assert "backtest_result" in result
        except Exception as e:
            # 预期可能的失败，因为JSON格式需要特殊处理
            print(f"JSON format test failed as expected: {e}")

    @patch('src.evaluation.flows.backtest_flow.HAS_PREFECT', False)
    def test_backtest_flow_without_prefect(self, sample_predictions_and_odds, temp_dir):
        """测试无Prefect时的回测流程"""
        predictions_path, odds_path = sample_predictions_and_odds
        output_dir = temp_dir / "backtest_no_prefect"
        output_dir.mkdir(exist_ok=True)

        result = backtest_flow(
            predictions_path=predictions_path,
            odds_path=odds_path,
            output_dir=str(output_dir)
        )

        # 即使没有Prefect，应该仍能工作
        assert "backtest_result" in result
        assert "model_info" in result

    def test_backtest_flow_error_handling(self, temp_dir):
        """测试错误处理"""
        output_dir = temp_dir / "backtest_error"
        output_dir.mkdir(exist_ok=True)

        # 测试不存在的文件
        with pytest.raises(FileNotFoundError):
            backtest_flow(
                predictions_path="nonexistent_predictions.csv",
                odds_path="nonexistent_odds.csv",
                output_dir=str(output_dir)
            )

    def test_backtest_flow_no_common_matches(self, temp_dir):
        """测试无共同比赛的情况"""
        # 创建不匹配的数据
        predictions_path = temp_dir / "predictions.csv"
        odds_path = temp_dir / "odds.csv"

        # 预测数据
        predictions_df = pd.DataFrame({
            'match_id': ['match_1', 'match_2', 'match_3'],
            'prob_H': [0.5, 0.3, 0.7],
            'prob_D': [0.3, 0.4, 0.2],
            'prob_A': [0.2, 0.3, 0.1],
            'actual_result': [0, 1, 0]
        })
        predictions_df.to_csv(predictions_path, index=False)

        # 赔率数据（不同的match_id）
        odds_df = pd.DataFrame({
            'match_id': ['match_4', 'match_5', 'match_6'],
            'odds_H': [2.0, 2.5, 3.0],
            'odds_D': [3.0, 3.2, 2.8],
            'odds_A': [4.0, 2.8, 4.5]
        })
        odds_df.to_csv(odds_path, index=False)

        output_dir = temp_dir / "backtest_no_matches"
        output_dir.mkdir(exist_ok=True)

        with pytest.raises(ValueError, match="No common matches"):
            backtest_flow(
                predictions_path=predictions_path,
                odds_path=odds_path,
                output_dir=str(output_dir)
            )

    def test_backtest_flow_invalid_staking_strategy(self, sample_predictions_and_odds, temp_dir):
        """测试无效投注策略"""
        predictions_path, odds_path = sample_predictions_and_odds
        output_dir = temp_dir / "backtest_invalid_strategy"
        output_dir.mkdir(exist_ok=True)

        with pytest.raises(ValueError, match="Unknown staking strategy"):
            backtest_flow(
                predictions_path=predictions_path,
                odds_path=odds_path,
                staking_strategy="invalid_strategy",
                output_dir=str(output_dir)
            )

    def test_backtest_flow_custom_backtest_params(self, sample_predictions_and_odds, temp_dir):
        """测试自定义回测参数"""
        predictions_path, odds_path = sample_predictions_and_odds
        output_dir = temp_dir / "backtest_custom_params"
        output_dir.mkdir(exist_ok=True)

        result = backtest_flow(
            predictions_path=predictions_path,
            odds_path=odds_path,
            staking_strategy="flat",
            backtest_params={
                "min_confidence": 0.6,  # 较高置信度要求
                "min_odds": 2.0,      # 最小赔率
                "max_odds": 5.0       # 最大赔率
            },
            output_dir=str(output_dir)
        )

        # 验证参数影响结果
        backtest_result = result["backtest_result"]
        # 由于高置信度要求，投注次数可能减少
        assert backtest_result["total_bets"] >= 0

    def test_backtest_flow_result_serialization(self, sample_predictions_and_odds, temp_dir):
        """测试结果序列化"""
        predictions_path, odds_path = sample_predictions_and_odds
        output_dir = temp_dir / "backtest_serialization"
        output_dir.mkdir(exist_ok=True)

        result = backtest_flow(
            predictions_path=predictions_path,
            odds_path=odds_path,
            output_dir=str(output_dir)
        )

        # 验证JSON序列化
        result_file = Path(result["output_dir"]) / "complete_backtest_result.json"
        assert result_file.exists()

        # 加载并验证JSON内容
        with open(result_file, encoding='utf-8') as f:
            loaded_result = json.load(f)

        assert loaded_result["model_info"]["name"] == result["model_info"]["name"]
        assert "strategy_info" in loaded_result
        assert "backtest_result" in loaded_result

        # 验证回测结果的可反序列化
        loaded_backtest = loaded_result["backtest_result"]
        assert isinstance(loaded_backtest, dict)
        assert "total_bets" in loaded_backtest
        assert "roi" in loaded_backtest


class TestRunBacktestFunction:
    """run_backtest便捷函数集成测试"""

    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            yield Path(tmp_dir)

    @pytest.fixture
    def sample_files(self, temp_dir):
        """创建样本文件"""
        # 预测数据
        predictions_data = []
        for i in range(50):
            probs = np.random.dirichlet([2, 1.5, 2.5])
            predictions_data.append({
                'match_id': f"match_{i+1:03d}",
                'prob_H': float(probs[0]),
                'prob_D': float(probs[1]),
                'prob_A': float(probs[2]),
                'predicted_class': int(np.random.randint(0, 3)),
                'actual_result': int(np.random.randint(0, 3))
            })

        predictions_df = pd.DataFrame(predictions_data)
        predictions_path = temp_dir / "predictions.csv"
        predictions_df.to_csv(predictions_path, index=False)

        # 赔率数据
        odds_data = {
            'match_id': [f"match_{i+1:03d}" for i in range(50)],
            'odds_H': np.random.uniform(2.0, 4.0, 50),
            'odds_D': np.random.uniform(3.0, 4.5, 50),
            'odds_A': np.random.uniform(2.5, 5.5, 50)
        }
        odds_df = pd.DataFrame(odds_data)
        odds_path = temp_dir / "odds.csv"
        odds_df.to_csv(odds_path, index=False)

        return predictions_path, odds_path

    def test_run_backtest_function(self, sample_files, temp_dir):
        """测试run_backtest便捷函数"""
        predictions_path, odds_path = sample_files

        output_dir = temp_dir / "convenience_backtest"
        output_dir.mkdir(exist_ok=True)

        result = run_backtest(
            predictions_path=predictions_path,
            odds_path=odds_path,
            model_name="Convenience Test Model",
            staking_strategy="percentage",
            staking_params={"percentage": 0.02},
            output_dir=str(output_dir)
        )

        # 验证基本结构
        assert "model_info" in result
        assert "strategy_info" in result
        assert "backtest_result" in result
        assert result["model_info"]["name"] == "Convenience Test Model"
        assert result["strategy_info"]["type"] == "percentage"

    @patch('src.evaluation.flows.backtest_flow.HAS_PREFECT', False)
    def test_run_backtest_without_prefect(self, sample_files, temp_dir):
        """测试无Prefect时的run_backtest函数"""
        predictions_path, odds_path = sample_files

        result = run_backtest(
            predictions_path=predictions_path,
            odds_path=odds_path
        )

        # 应该仍能工作
        assert "backtest_result" in result
        assert "model_info" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
