#!/usr/bin/env python3
"""
赔率变动特征系统单元测试

Phase 5 Advanced Features 核心算法测试覆盖

测试覆盖范围：
- 赔率数据添加和管理
- Market Steam信号检测
- 赔率变动模式分析
- 市场情绪分析
- 异常检测和处理
- 趋势分析算法
- 交易信号生成
- 特征工程提取
- 边界条件处理
- 性能压力测试

Author: Football Prediction Team
Version: 1.0.0 (Sprint 7 Testing)
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List
from decimal import Decimal

# 导入被测试的模块
from src.ml.features.odds_movement_features import OddsMovementAnalyzer
from src.constants import FOOTBALL, MATH, PROBABILITY, ODDS


class TestOddsMovementAnalyzer:
    """赔率变动分析器测试类"""

    @pytest.fixture
    def analyzer(self):
        """创建赔率变动分析器实例"""
        return OddsMovementAnalyzer(
            steam_threshold=0.15,
            significant_move_threshold=0.10,
            time_window_hours=24,
            enable_anomaly_detection=True,
            enable_trend_analysis=True,
            smoothing_window=5,
        )

    @pytest.fixture
    def sample_odds_sequence(self):
        """示例赔率序列数据"""
        base_time = datetime.now() - timedelta(hours=10)
        return [
            {
                "timestamp": base_time + timedelta(hours=i),
                "home_odds": 2.10 - i * 0.02,  # 逐步下降
                "draw_odds": 3.40 + i * 0.01,  # 逐步上升
                "away_odds": 3.80 + i * 0.03,  # 逐步上升
                "bookmaker": "bet365",
                "volume": 1000 + i * 100,
                "market_importance": 1.0,
            }
            for i in range(10)
        ]

    @pytest.fixture
    def steam_odds_sequence(self):
        """Steam信号赔率序列"""
        base_time = datetime.now() - timedelta(hours=5)
        return [
            # 初始稳定期
            {
                "timestamp": base_time + timedelta(hours=i),
                "home_odds": 2.00,
                "draw_odds": 3.40,
                "away_odds": 3.80,
                "bookmaker": "bet365",
                "volume": 1000,
                "market_importance": 1.0,
            }
            for i in range(3)
        ] + [
            # Steam期 - 主胜赔率连续下降
            {
                "timestamp": base_time + timedelta(hours=3 + i),
                "home_odds": 1.95 - i * 0.05,  # 连续下降
                "draw_odds": 3.45 + i * 0.02,
                "away_odds": 3.85 + i * 0.04,
                "bookmaker": "bet365",
                "volume": 1500 + i * 200,  # 成交量增加
                "market_importance": 1.2,
            }
            for i in range(4)
        ]

    @pytest.fixture
    def volatile_odds_sequence(self):
        """高波动性赔率序列"""
        base_time = datetime.now() - timedelta(hours=8)
        np.random.seed(42)  # 确保可重复性
        return [
            {
                "timestamp": base_time + timedelta(hours=i),
                "home_odds": 2.00 + np.random.normal(0, 0.15),
                "draw_odds": 3.40 + np.random.normal(0, 0.20),
                "away_odds": 3.80 + np.random.normal(0, 0.25),
                "bookmaker": "various_bookmakers",
                "volume": 800 + np.random.randint(0, 400),
                "market_importance": 0.8 + np.random.random() * 0.4,
            }
            for i in range(12)
        ]

    @pytest.fixture
    def anomaly_odds_sequence(self):
        """包含异常值的赔率序列"""
        base_time = datetime.now() - timedelta(hours=6)
        normal_data = [
            {
                "timestamp": base_time + timedelta(hours=i),
                "home_odds": 2.10,
                "draw_odds": 3.30,
                "away_odds": 3.90,
                "bookmaker": "normal_bookmaker",
                "volume": 1000,
                "market_importance": 1.0,
            }
            for i in range(5)
        ]

        # 插入异常值
        anomaly_entry = {
            "timestamp": base_time + timedelta(hours=5),
            "home_odds": 1.20,  # 异常低值
            "draw_odds": 4.50,  # 异常高值
            "away_odds": 8.00,  # 异常高值
            "bookmaker": "error_source",
            "volume": 100,
            "market_importance": 0.1,
        }

        return normal_data + [anomaly_entry]

    # ========== 初始化和基础功能测试 ==========

    def test_analyzer_initialization(self):
        """测试分析器初始化"""
        analyzer = OddsMovementAnalyzer()

        assert analyzer.steam_threshold == 0.15
        assert analyzer.significant_move_threshold == 0.10
        assert analyzer.time_window_hours == 24
        assert analyzer.enable_anomaly_detection is True
        assert analyzer.enable_trend_analysis is True
        assert analyzer.smoothing_window == 5
        assert isinstance(analyzer.odds_history, dict)
        assert isinstance(analyzer.analysis_cache, dict)
        assert isinstance(analyzer.stats, dict)

    def test_analyzer_custom_initialization(self):
        """测试自定义参数初始化"""
        analyzer = OddsMovementAnalyzer(
            steam_threshold=0.20,
            significant_move_threshold=0.15,
            time_window_hours=48,
            enable_anomaly_detection=False,
            enable_trend_analysis=False,
            smoothing_window=3,
        )

        assert analyzer.steam_threshold == 0.20
        assert analyzer.significant_move_threshold == 0.15
        assert analyzer.time_window_hours == 48
        assert analyzer.enable_anomaly_detection is False
        assert analyzer.enable_trend_analysis is False
        assert analyzer.smoothing_window == 3

    # ========== 赔率数据管理测试 ==========

    def test_add_odds_data_single(self, analyzer):
        """测试添加单个赔率数据"""
        result = analyzer.add_odds_data(
            match_id="test_match",
            home_odds=2.10,
            draw_odds=3.40,
            away_odds=3.80,
            timestamp=datetime.now(),
            bookmaker="bet365",
            volume=1000,
            market_importance=1.0,
        )

        assert result["status"] == "success"
        assert result["match_id"] == "test_match"
        assert result["total_samples"] == 1
        assert "test_match" in analyzer.odds_history
        assert len(analyzer.odds_history["test_match"]) == 1

        # 验证数据结构
        odds_entry = analyzer.odds_history["test_match"][0]
        assert odds_entry["home_odds"] == 2.10
        assert odds_entry["draw_odds"] == 3.40
        assert odds_entry["away_odds"] == 3.80
        assert odds_entry["bookmaker"] == "bet365"
        assert odds_entry["volume"] == 1000
        assert "implied_prob_home" in odds_entry
        assert "implied_prob_draw" in odds_entry
        assert "implied_prob_away" in odds_entry

    def test_add_odds_data_multiple(self, analyzer, sample_odds_sequence):
        """测试添加多个赔率数据"""
        match_id = "multi_test"

        for odds_data in sample_odds_sequence:
            result = analyzer.add_odds_data(match_id=match_id, **odds_data)
            assert result["status"] == "success"

        assert len(analyzer.odds_history[match_id]) == len(sample_odds_sequence)

        # 验证时间排序
        timestamps = [entry["timestamp"] for entry in analyzer.odds_history[match_id]]
        assert timestamps == sorted(timestamps)

    def test_add_odds_data_default_timestamp(self, analyzer):
        """测试使用默认时间戳"""
        before_time = datetime.now()

        result = analyzer.add_odds_data(
            match_id="timestamp_test",
            home_odds=2.00,
            draw_odds=3.40,
            away_odds=3.80,
        )

        after_time = datetime.now()

        assert result["status"] == "success"
        odds_entry = analyzer.odds_history["timestamp_test"][0]
        assert before_time <= odds_entry["timestamp"] <= after_time

    def test_add_odds_data_cache_clearing(self, analyzer):
        """测试添加数据时缓存清理"""
        # 先添加数据并分析
        analyzer.add_odds_data("cache_test", 2.10, 3.40, 3.80)
        analyzer.analyze_odds_movement("cache_test")
        assert "cache_test" in analyzer.analysis_cache

        # 添加新数据应该清理缓存
        analyzer.add_odds_data("cache_test", 2.05, 3.45, 3.85)
        assert "cache_test" not in analyzer.analysis_cache

    def test_implied_probability_calculation(self, analyzer):
        """测试隐含概率计算"""
        analyzer.add_odds_data(
            "prob_test",
            home_odds=2.00,  # 50%
            draw_odds=3.00,  # 33.33%
            away_odds=4.00,  # 25%
        )

        entry = analyzer.odds_history["prob_test"][0]
        assert abs(entry["implied_prob_home"] - 0.50) < 0.001
        assert abs(entry["implied_prob_draw"] - 0.333) < 0.001
        assert abs(entry["implied_prob_away"] - 0.25) < 0.001

    # ========== 赔率变动分析测试 ==========

    def test_analyze_odds_movement_basic(self, analyzer, sample_odds_sequence):
        """测试基础赔率变动分析"""
        match_id = "basic_analysis"
        for odds_data in sample_odds_sequence:
            analyzer.add_odds_data(match_id, **odds_data)

        result = analyzer.analyze_odds_movement(match_id)

        assert result["match_id"] == match_id
        assert "analysis_timestamp" in result
        assert "data_summary" in result
        assert "basic_statistics" in result
        assert "movement_analysis" in result
        assert "steam_signals" in result
        assert "sentiment_analysis" in result
        assert "efficiency_metrics" in result
        assert "trading_signals" in result
        assert "model_features" in result

    def test_analyze_odds_movement_insufficient_data(self, analyzer):
        """测试数据不足时的分析"""
        # 添加少于最小样本数的数据
        analyzer.add_odds_data("insufficient_test", 2.10, 3.40, 3.80)
        analyzer.add_odds_data("insufficient_test", 2.05, 3.45, 3.85)

        result = analyzer.analyze_odds_movement("insufficient_test")
        assert "error" in result
        assert "数据不足" in result["error"]

    def test_analyze_odds_movement_no_data(self, analyzer):
        """测试无数据时的分析"""
        result = analyzer.analyze_odds_movement("nonexistent_match")
        assert "error" in result
        assert "无赔率数据" in result["error"]

    def test_basic_statistics_calculation(self, analyzer, sample_odds_sequence):
        """测试基础统计计算"""
        match_id = "stats_test"
        for odds_data in sample_odds_sequence:
            analyzer.add_odds_data(match_id, **odds_data)

        result = analyzer.analyze_odds_movement(match_id)
        stats = result["basic_statistics"]

        # 验证主胜赔率统计
        home_stats = stats["home_odds"]
        assert "current" in home_stats
        assert "initial" in home_stats
        assert "mean" in home_stats
        assert "std" in home_stats
        assert "min" in home_stats
        assert "max" in home_stats
        assert "change_pct" in home_stats

        # 验证数值合理性
        assert home_stats["current"] < home_stats["initial"]  # 应该是下降趋势
        assert home_stats["change_pct"] < 0
        assert home_stats["mean"] > 0
        assert home_stats["std"] >= 0

    def test_price_movements_analysis(self, analyzer, sample_odds_sequence):
        """测试价格变动分析"""
        match_id = "movement_test"
        for odds_data in sample_odds_sequence:
            analyzer.add_odds_data(match_id, **odds_data)

        result = analyzer.analyze_odds_movement(match_id)
        movement_analysis = result["movement_analysis"]

        assert "detailed_movements" in movement_analysis
        assert "summary" in movement_analysis

        detailed = movement_analysis["detailed_movements"]
        summary = movement_analysis["summary"]

        # 验证详细变动数据
        for outcome in ["home", "draw", "away"]:
            assert outcome in detailed
            assert outcome in summary

            outcome_moves = detailed[outcome]
            assert len(outcome_moves) == len(sample_odds_sequence) - 1  # n-1个变动

            # 验证变动数据结构
            if outcome_moves:
                first_move = outcome_moves[0]
                assert "timestamp" in first_move
                assert "move_pct" in first_move
                assert "weight" in first_move
                assert "abs_move" in first_move
                assert "volume" in first_move

            # 验证汇总统计
            outcome_summary = summary[outcome]
            assert "total_moves" in outcome_summary
            assert "avg_move" in outcome_summary
            assert "weighted_avg_move" in outcome_summary
            assert "max_move" in outcome_summary
            assert "significant_moves" in outcome_summary

    # ========== Market Steam检测测试 ==========

    def test_steam_signal_detection(self, analyzer, steam_odds_sequence):
        """测试Steam信号检测"""
        match_id = "steam_test"
        for odds_data in steam_odds_sequence:
            analyzer.add_odds_data(match_id, **odds_data)

        result = analyzer.analyze_odds_movement(match_id)
        steam_signals = result["steam_signals"]

        assert steam_signals["steam_detected"] is True
        assert steam_signals["signal_count"] > 0
        assert steam_signals["overall_strength"] > 0

        # 验证Steam信号结构
        signals = steam_signals["signals"]
        for signal in signals:
            assert "outcome" in signal
            assert "direction" in signal
            assert "strength" in signal
            assert "confidence" in signal
            assert signal["strength"] > analyzer.steam_threshold

    def test_outcome_steam_detection(self, analyzer, steam_odds_sequence):
        """测试单个结果Steam检测"""
        # 直接测试内部方法
        match_id = "outcome_steam_test"
        for odds_data in steam_odds_sequence:
            analyzer.add_odds_data(match_id, **odds_data)

        odds_data = analyzer.odds_history[match_id]
        steam_signal = analyzer._detect_outcome_steam(odds_data, "home")

        assert steam_signal is not None
        assert steam_signal["outcome"] == "home"
        assert steam_signal["direction"] == "down"  # 主胜赔率下降
        assert steam_signal["strength"] > analyzer.steam_threshold
        assert steam_signal["duration"] >= 3
        assert steam_signal["confidence"] > 0

    def test_cross_market_steam_detection(self, analyzer, steam_odds_sequence):
        """测试跨市场Steam检测"""
        match_id = "cross_steam_test"
        for odds_data in steam_odds_sequence:
            analyzer.add_odds_data(match_id, **odds_data)

        odds_data = analyzer.odds_history[match_id]
        cross_steam = analyzer._detect_cross_market_steam(odds_data)

        # 高成交量变动可能触发跨市场Steam
        if cross_steam:
            assert cross_steam["outcome"] == "cross_market"
            assert "dominant_outcome" in cross_steam
            assert "strength" in cross_steam
            assert "weighted_moves" in cross_steam

    def test_steam_strength_calculation(self, analyzer):
        """测试Steam强度计算"""
        # 创建多个Steam信号
        steam_signals = [
            {"strength": 0.20, "confidence": 0.8},
            {"strength": 0.15, "confidence": 0.6},
            {"strength": 0.25, "confidence": 0.9},
        ]

        overall_strength = analyzer._calculate_overall_steam_strength(steam_signals)
        expected_strength = sum(s["strength"] for s in steam_signals) / len(
            steam_signals
        )

        assert abs(overall_strength - expected_strength) < 0.001

    def test_no_steam_detection(self, analyzer, sample_odds_sequence):
        """测试无Steam信号的情况"""
        match_id = "no_steam_test"
        for odds_data in sample_odds_sequence:
            analyzer.add_odds_data(match_id, **odds_data)

        result = analyzer.analyze_odds_movement(match_id)
        steam_signals = result["steam_signals"]

        # 平缓变动可能不触发Steam
        if not steam_signals["steam_detected"]:
            assert steam_signals["signal_count"] == 0
            assert steam_signals["overall_strength"] == 0

    # ========== 趋势分析测试 ==========

    def test_trend_analysis(self, analyzer, sample_odds_sequence):
        """测试趋势分析"""
        match_id = "trend_test"
        for odds_data in sample_odds_sequence:
            analyzer.add_odds_data(match_id, **odds_data)

        result = analyzer.analyze_odds_movement(match_id)
        trend_analysis = result["trend_analysis"]

        if analyzer.enable_trend_analysis:
            assert "trends" in trend_analysis
            assert "analysis_period_hours" in trend_analysis

            trends = trend_analysis["trends"]
            for outcome in ["home", "draw", "away"]:
                assert outcome in trends

                outcome_trend = trends[outcome]
                assert "linear_slope" in outcome_trend
                assert "linear_r_squared" in outcome_trend
                assert "linear_p_value" in outcome_trend
                assert "trend_direction" in outcome_trend
                assert "volatility" in outcome_trend

                # 主胜赔率应该是下降趋势
                if outcome == "home":
                    assert outcome_trend["trend_direction"] == "down"
                    assert outcome_trend["linear_slope"] < 0

    def test_trend_analysis_insufficient_data(self, analyzer):
        """测试数据不足时的趋势分析"""
        match_id = "trend_insufficient"

        # 添加少于最小趋势点数的数据
        for i in range(3):
            analyzer.add_odds_data(
                match_id,
                home_odds=2.00 + i * 0.01,
                draw_odds=3.40 - i * 0.01,
                away_odds=3.80 + i * 0.01,
            )

        result = analyzer.analyze_odds_movement(match_id)
        trend_analysis = result["trend_analysis"]

        if analyzer.enable_trend_analysis:
            assert "error" in trend_analysis
            assert "数据点不足" in trend_analysis["error"]

    def test_trend_analysis_disabled(self, analyzer, sample_odds_sequence):
        """测试禁用趋势分析"""
        analyzer.enable_trend_analysis = False

        match_id = "no_trend_test"
        for odds_data in sample_odds_sequence:
            analyzer.add_odds_data(match_id, **odds_data)

        result = analyzer.analyze_odds_movement(match_id)
        trend_analysis = result["trend_analysis"]

        assert trend_analysis == {}

    # ========== 异常检测测试 ==========

    def test_anomaly_detection(self, analyzer, anomaly_odds_sequence):
        """测试异常检测"""
        match_id = "anomaly_test"
        for odds_data in anomaly_odds_sequence:
            analyzer.add_odds_data(match_id, **odds_data)

        result = analyzer.analyze_odds_movement(match_id)
        anomaly_detection = result["anomaly_detection"]

        if analyzer.enable_anomaly_detection:
            assert "anomalies" in anomaly_detection
            assert "total_anomalies" in anomaly_detection
            assert "anomaly_rate" in anomaly_detection

            # 应该检测到异常值
            assert anomaly_detection["total_anomalies"] > 0
            assert anomaly_detection["anomaly_rate"] > 0

            # 验证异常记录结构
            anomalies = anomaly_detection["anomalies"]
            for anomaly in anomalies:
                assert "timestamp" in anomaly
                assert "outcome" in anomaly
                assert "anomaly_type" in anomaly
                assert "severity" in anomaly
                assert 0 <= anomaly["severity"] <= 1

    def test_statistical_outlier_detection(self, analyzer, anomaly_odds_sequence):
        """测试统计异常值检测"""
        match_id = "stat_outlier_test"
        for odds_data in anomaly_odds_sequence:
            analyzer.add_odds_data(match_id, **odds_data)

        odds_data = analyzer.odds_history[match_id]
        anomalies = analyzer._detect_anomalies(odds_data)

        # 应该检测到Z-score异常
        statistical_outliers = [
            a
            for a in anomalies["anomalies"]
            if a["anomaly_type"] == "statistical_outlier"
        ]

        assert len(statistical_outliers) > 0

    def test_large_price_movement_detection(self, analyzer, anomaly_odds_sequence):
        """测试大价格变动异常检测"""
        match_id = "price_move_test"
        for odds_data in anomaly_odds_sequence:
            analyzer.add_odds_data(match_id, **odds_data)

        odds_data = analyzer.odds_history[match_id]
        anomalies = analyzer._detect_anomalies(odds_data)

        # 应该检测到大价格变动异常
        large_movements = [
            a
            for a in anomalies["anomalies"]
            if a["anomaly_type"] == "large_price_movement"
        ]

        # 可能检测到大变动，取决于阈值设置
        if large_movements:
            for movement in large_movements:
                assert movement["price_move"] > analyzer.significant_move_threshold * 2

    def test_anomaly_detection_disabled(self, analyzer, sample_odds_sequence):
        """测试禁用异常检测"""
        analyzer.enable_anomaly_detection = False

        match_id = "no_anomaly_test"
        for odds_data in sample_odds_sequence:
            analyzer.add_odds_data(match_id, **odds_data)

        result = analyzer.analyze_odds_movement(match_id)
        anomaly_detection = result["anomaly_detection"]

        assert anomaly_detection == {}

    # ========== 市场情绪分析测试 ==========

    def test_market_sentiment_analysis(self, analyzer, steam_odds_sequence):
        """测试市场情绪分析"""
        match_id = "sentiment_test"
        for odds_data in steam_odds_sequence:
            analyzer.add_odds_data(match_id, **odds_data)

        result = analyzer.analyze_odds_movement(match_id)
        sentiment_analysis = result["sentiment_analysis"]

        assert "sentiment_metrics" in sentiment_analysis
        assert "dominant_sentiment" in sentiment_analysis
        assert "sentiment_strength" in sentiment_analysis
        assert "market_consensus" in sentiment_analysis

        # 验证情绪指标
        sentiment_metrics = sentiment_analysis["sentiment_metrics"]
        for outcome in ["home", "draw", "away"]:
            if outcome in sentiment_metrics:
                metrics = sentiment_metrics[outcome]
                assert "avg_change" in metrics
                assert "total_change" in metrics
                assert "volatility" in metrics
                assert "momentum" in metrics
                assert "consistency" in metrics
                assert 0 <= metrics["consistency"] <= 1

    def test_market_consensus_calculation(self, analyzer):
        """测试市场共识计算"""
        # 创建高共识数据（明显的热门）
        consensus_data = [
            {
                "timestamp": datetime.now(),
                "home_odds": 1.50,  # 明显热门
                "draw_odds": 4.00,
                "away_odds": 6.00,
            }
        ]

        consensus = analyzer._calculate_market_consensus(consensus_data)
        assert 0 <= consensus <= 1
        # 明显热门应该有较高的共识度
        assert consensus > 0.5

        # 创建低共识数据（接近均势）
        balanced_data = [
            {
                "timestamp": datetime.now(),
                "home_odds": 2.80,
                "draw_odds": 3.20,
                "away_odds": 2.90,
            }
        ]

        balanced_consensus = analyzer._calculate_market_consensus(balanced_data)
        assert 0 <= balanced_consensus <= 1
        # 均势比赛共识度可能较低

    # ========== 市场效率测试 ==========

    def test_market_efficiency_calculation(self, analyzer, sample_odds_sequence):
        """测试市场效率计算"""
        match_id = "efficiency_test"
        for odds_data in sample_odds_sequence:
            analyzer.add_odds_data(match_id, **odds_data)

        result = analyzer.analyze_odds_movement(match_id)
        efficiency_metrics = result["efficiency_metrics"]

        assert "outcome_efficiency" in efficiency_metrics
        assert "overall_efficiency" in efficiency_metrics
        assert "market_classification" in efficiency_metrics

        # 验证效率指标
        outcome_efficiency = efficiency_metrics["outcome_efficiency"]
        for outcome in ["home", "draw", "away"]:
            if outcome in outcome_efficiency:
                metrics = outcome_efficiency[outcome]
                assert "coefficient_of_variation" in metrics
                assert "max_drawdown" in metrics
                assert "efficiency_score" in metrics
                assert "stability" in metrics
                assert 0 <= metrics["efficiency_score"] <= 1
                assert 0 <= metrics["stability"] <= 1

        # 验证市场分类
        classification = efficiency_metrics["market_classification"]
        assert classification in [
            "highly_efficient",
            "efficient",
            "moderately_efficient",
            "inefficient",
            "highly_inefficient",
        ]

    def test_max_drawdown_calculation(self, analyzer):
        """测试最大回撤计算"""
        # 测试上升序列
        rising_values = [1.0, 1.1, 1.2, 1.3, 1.4, 1.5]
        drawdown = analyzer._calculate_max_drawdown(rising_values)
        assert drawdown == 0

        # 测试下降序列
        falling_values = [1.5, 1.4, 1.3, 1.2, 1.1, 1.0]
        drawdown = analyzer._calculate_max_drawdown(falling_values)
        assert drawdown > 0
        assert abs(drawdown - (1.5 - 1.0) / 1.5) < 0.001

        # 测试波动序列
        volatile_values = [1.0, 1.3, 1.1, 1.4, 1.2, 1.5]
        drawdown = analyzer._calculate_max_drawdown(volatile_values)
        assert 0 < drawdown < 1

    # ========== 交易信号生成测试 ==========

    def test_trading_signal_generation(self, analyzer, steam_odds_sequence):
        """测试交易信号生成"""
        match_id = "signals_test"
        for odds_data in steam_odds_sequence:
            analyzer.add_odds_data(match_id, **odds_data)

        result = analyzer.analyze_odds_movement(match_id)
        trading_signals = result["trading_signals"]

        assert "signals" in trading_signals
        assert "signal_count" in trading_signals
        assert "strongest_signal" in trading_signals
        assert "overall_signal_strength" in trading_signals

        signals = trading_signals["signals"]
        assert len(signals) <= 5  # 最多返回5个信号

        # 验证信号结构
        for signal in signals:
            assert "type" in signal
            assert "outcome" in signal
            assert "direction" in signal
            assert "strength" in signal
            assert "confidence" in signal
            assert "reasoning" in signal
            assert signal["strength"] > 0
            assert 0 <= signal["confidence"] <= 1

        # 验证信号类型
        signal_types = [s["type"] for s in signals]
        valid_types = {"steam", "trend", "sentiment"}
        assert all(t in valid_types for t in signal_types)

    def test_steam_signal_generation(self, analyzer, steam_odds_sequence):
        """测试Steam信号生成"""
        match_id = "steam_signals_test"
        for odds_data in steam_odds_sequence:
            analyzer.add_odds_data(match_id, **odds_data)

        result = analyzer.analyze_odds_movement(match_id)
        movement_analysis = result["movement_analysis"]
        steam_signals = result["steam_signals"]
        sentiment_analysis = result["sentiment_analysis"]

        trading_signals = analyzer._generate_trading_signals(
            movement_analysis, steam_signals, sentiment_analysis
        )

        # 应该有Steam信号
        steam_trading_signals = [
            s for s in trading_signals["signals"] if s["type"] == "steam"
        ]
        assert len(steam_trading_signals) > 0

    # ========== 特征工程测试 ==========

    def test_odds_movement_features_extraction(self, analyzer, steam_odds_sequence):
        """测试赔率变动特征提取"""
        match_id = "features_test"
        for odds_data in steam_odds_sequence:
            analyzer.add_odds_data(match_id, **odds_data)

        result = analyzer.analyze_odds_movement(match_id)
        model_features = result["model_features"]

        # 验证基础变动特征
        for outcome in ["home", "draw", "away"]:
            assert f"{outcome}_total_weighted_move" in model_features
            assert f"{outcome}_significant_moves_ratio" in model_features
            assert f"{outcome}_move_volatility" in model_features
            assert f"{outcome}_avg_move" in model_features

        # 验证Steam特征
        assert "steam_detected" in model_features
        assert "steam_strength" in model_features
        assert "steam_signal_count" in model_features

        # 验证市场情绪特征
        assert "dominant_sentiment_strength" in model_features
        for outcome in ["home", "draw", "away"]:
            assert f"{outcome}_sentiment_momentum" in model_features
            assert f"{outcome}_sentiment_consistency" in model_features

        # 验证时间序列特征
        assert "avg_latest_move" in model_features
        assert "max_latest_move" in model_features

        # 验证特征值类型
        for feature_name, feature_value in model_features.items():
            assert isinstance(feature_value, (int, float))
            assert not np.isnan(feature_value)
            assert not np.isinf(feature_value)

    # ========== 辅助方法测试 ==========

    def test_price_move_calculation(self, analyzer):
        """测试价格变动计算"""
        # 上升变动
        move = analyzer._calculate_price_move(2.00, 2.10)
        assert move == 5.0  # (2.10-2.00)/2.00 * 100

        # 下降变动
        move = analyzer._calculate_price_move(2.10, 2.00)
        assert move == -4.761904761904762

        # 无变动
        move = analyzer._calculate_price_move(2.00, 2.00)
        assert move == 0

        # 零除法处理
        move = analyzer._calculate_price_move(0, 2.00)
        assert move == 0

    def test_movement_weight_calculation(self, analyzer):
        """测试变动权重计算"""
        current_time = datetime.now()

        entry = {
            "timestamp": current_time - timedelta(hours=1),  # 1小时前
            "volume": 1000,
            "market_importance": 1.0,
        }

        weight = analyzer._calculate_movement_weight(entry)
        assert weight > 0

        # 测试时效性权重（较新的数据权重更高）
        old_entry = {
            "timestamp": current_time - timedelta(hours=24),  # 24小时前
            "volume": 1000,
            "market_importance": 1.0,
        }

        new_weight = analyzer._calculate_movement_weight(entry)
        old_weight = analyzer._calculate_movement_weight(old_entry)
        assert new_weight > old_weight

    def test_odds_to_probability_conversion(self, analyzer):
        """测试赔率转概率"""
        # 正常赔率
        prob = analyzer._odds_to_probability(2.00)
        assert prob == 0.5

        # 低赔率
        prob = analyzer._odds_to_probability(1.50)
        assert abs(prob - 0.666666) < 0.001

        # 高赔率
        prob = analyzer._odds_to_probability(5.00)
        assert abs(prob - 0.20) < 0.001

        # 边界情况
        prob = analyzer._odds_to_probability(0)
        assert prob == 0

        prob = analyzer._odds_to_probability(-1)
        assert prob == 0

    def test_time_range_calculation(self, analyzer):
        """测试时间范围计算"""
        now = datetime.now()

        # 单个数据点
        single_data = [{"timestamp": now}]
        hours = analyzer._get_time_range_hours(single_data)
        assert hours == 0

        # 多个数据点
        multi_data = [
            {"timestamp": now - timedelta(hours=2)},
            {"timestamp": now},
        ]
        hours = analyzer._get_time_range_hours(multi_data)
        assert hours == 2

    # ========== 边界条件和异常处理测试 ==========

    def test_edge_case_single_data_point(self, analyzer):
        """测试单数据点边界情况"""
        analyzer.add_odds_data("single_test", 2.00, 3.40, 3.80)

        # 单数据点无法进行分析
        result = analyzer.analyze_odds_movement("single_test")
        assert "error" in result

    def test_edge_case_identical_odds(self, analyzer):
        """测试相同赔率的边界情况"""
        match_id = "identical_test"
        for i in range(10):
            analyzer.add_odds_data(
                match_id,
                home_odds=2.00,
                draw_odds=3.40,
                away_odds=3.80,
                timestamp=datetime.now() + timedelta(minutes=i),
            )

        result = analyzer.analyze_odds_movement(match_id)

        # 无变动应该有特定的分析结果
        movement_summary = result["movement_analysis"]["summary"]
        for outcome in ["home", "draw", "away"]:
            assert movement_summary[outcome]["max_move"] == 0
            assert movement_summary[outcome]["significant_moves"] == 0

    def test_edge_case_extreme_odds(self, analyzer):
        """测试极端赔率值"""
        extreme_odds = [
            {"home_odds": 1.01, "draw_odds": 10.00, "away_odds": 25.00},
            {"home_odds": 50.00, "draw_odds": 8.00, "away_odds": 1.05},
        ]

        for i, odds in enumerate(extreme_odds):
            analyzer.add_odds_data(
                "extreme_test", **odds, timestamp=datetime.now() + timedelta(hours=i)
            )

        result = analyzer.analyze_odds_movement("extreme_test")
        assert result is not None
        assert "error" not in result

    def test_edge_case_zero_volume(self, analyzer):
        """测试零成交量情况"""
        analyzer.add_odds_data(
            "zero_volume_test",
            home_odds=2.00,
            draw_odds=3.40,
            away_odds=3.80,
            volume=0,
            market_importance=1.0,
        )

        result = analyzer.analyze_odds_movement("zero_volume_test")
        # 应该能处理零成交量
        assert result is not None

    # ========== 性能测试 ==========

    def test_performance_single_analysis(self, analyzer, sample_odds_sequence):
        """测试单次分析性能"""
        import time

        match_id = "perf_single"
        for odds_data in sample_odds_sequence:
            analyzer.add_odds_data(match_id, **odds_data)

        start_time = time.time()
        result = analyzer.analyze_odds_movement(match_id)
        end_time = time.time()

        analysis_time = end_time - start_time
        assert analysis_time < 1.0  # 应该在1秒内完成
        assert result is not None

    def test_performance_batch_analysis(self, analyzer, sample_odds_sequence):
        """测试批量分析性能"""
        import time

        matches_count = 20
        start_time = time.time()

        for i in range(matches_count):
            match_id = f"perf_batch_{i}"
            for odds_data in sample_odds_sequence:
                analyzer.add_odds_data(match_id, **odds_data)

            result = analyzer.analyze_odds_movement(match_id)
            assert result is not None

        end_time = time.time()
        total_time = end_time - start_time
        avg_time = total_time / matches_count

        assert avg_time < 0.5  # 平均每次分析应该很快

    @pytest.mark.parametrize("data_size", [10, 50, 100, 200])
    def test_performance_data_size_impact(self, analyzer, data_size):
        """测试数据大小对性能的影响"""
        base_time = datetime.now() - timedelta(hours=data_size)

        match_odds = [
            {
                "timestamp": base_time + timedelta(hours=i),
                "home_odds": 2.00 + np.random.normal(0, 0.05),
                "draw_odds": 3.40 + np.random.normal(0, 0.08),
                "away_odds": 3.80 + np.random.normal(0, 0.10),
                "volume": 1000,
                "market_importance": 1.0,
            }
            for i in range(data_size)
        ]

        match_id = f"perf_size_{data_size}"
        for odds_data in match_odds:
            analyzer.add_odds_data(match_id, **odds_data)

        import time

        start_time = time.time()
        result = analyzer.analyze_odds_movement(match_id)
        end_time = time.time()

        analysis_time = end_time - start_time

        # 即使大数据量也应该在合理时间内完成
        assert analysis_time < 2.0
        assert result is not None

    # ========== 统计和报告测试 ==========

    def test_system_stats_retrieval(self, analyzer, sample_odds_sequence):
        """测试系统统计信息获取"""
        # 添加一些数据和分析
        match_id = "stats_retrieval_test"
        for odds_data in sample_odds_sequence:
            analyzer.add_odds_data(match_id, **odds_data)

        analyzer.analyze_odds_movement(match_id)

        stats = analyzer.get_system_stats()

        assert "configuration" in stats
        assert "statistics" in stats
        assert "data_coverage" in stats

        # 验证配置信息
        config = stats["configuration"]
        assert config["steam_threshold"] == analyzer.steam_threshold
        assert (
            config["significant_move_threshold"] == analyzer.significant_move_threshold
        )

        # 验证统计信息
        statistics = stats["statistics"]
        assert statistics["total_analyses"] > 0
        assert "last_updated" in statistics

        # 验证数据覆盖信息
        coverage = stats["data_coverage"]
        assert coverage["matches_analyzed"] > 0
        assert coverage["total_odds_samples"] > 0

    def test_analysis_statistics_update(self, analyzer, steam_odds_sequence):
        """测试分析统计信息更新"""
        initial_stats = analyzer.stats.copy()

        match_id = "stats_update_test"
        for odds_data in steam_odds_sequence:
            analyzer.add_odds_data(match_id, **odds_data)

        result = analyzer.analyze_odds_movement(match_id)
        updated_stats = analyzer.stats

        # 验证统计更新
        assert updated_stats["total_analyses"] > initial_stats["total_analyses"]
        assert "last_updated" in updated_stats
        assert updated_stats["last_updated"] is not None

        # 如果检测到Steam，更新Steam统计
        if result["steam_signals"]["steam_detected"]:
            assert (
                updated_stats["steam_signals_detected"]
                >= initial_stats["steam_signals_detected"]
            )

    def test_repr_method(self, analyzer):
        """测试字符串表示方法"""
        # 添加一些数据
        analyzer.add_odds_data("repr_test", 2.00, 3.40, 3.80)
        analyzer.analyze_odds_movement("repr_test")

        repr_str = repr(analyzer)

        assert "OddsMovementAnalyzer" in repr_str
        assert "matches=1" in repr_str
        assert "analyses=1" in repr_str
        assert "steam_signals=" in repr_str

    # ========== 集成测试 ==========

    def test_full_workflow_integration(self, analyzer, steam_odds_sequence):
        """测试完整工作流程集成"""
        match_id = "full_workflow_test"

        # 1. 添加赔率数据
        for odds_data in steam_odds_sequence:
            result = analyzer.add_odds_data(match_id, **odds_data)
            assert result["status"] == "success"

        # 2. 执行分析
        analysis_result = analyzer.analyze_odds_movement(match_id)
        assert "error" not in analysis_result

        # 3. 验证分析完整性
        assert "basic_statistics" in analysis_result
        assert "movement_analysis" in analysis_result
        assert "steam_signals" in analysis_result
        assert "trading_signals" in analysis_result
        assert "model_features" in analysis_result

        # 4. 验证数据结构完整性
        for key, value in analysis_result.items():
            if key != "error" and isinstance(value, dict):
                assert len(value) > 0, f"Empty section: {key}"

        # 5. 获取系统统计
        system_stats = analyzer.get_system_stats()
        assert system_stats["statistics"]["total_analyses"] > 0

        # 6. 验证特征提取
        model_features = analysis_result["model_features"]
        assert len(model_features) > 10  # 应该有丰富的特征

        # 7. 验证交易信号
        trading_signals = analysis_result["trading_signals"]
        assert trading_signals["signal_count"] >= 0
        if trading_signals["signals"]:
            for signal in trading_signals["signals"]:
                assert all(key in signal for key in ["type", "strength", "confidence"])


class TestOddsMovementAnalyzerEdgeCases:
    """赔率变动分析器边界条件测试"""

    @pytest.fixture
    def minimal_analyzer(self):
        """创建最小配置分析器"""
        return OddsMovementAnalyzer(
            steam_threshold=0.05,
            significant_move_threshold=0.02,
            time_window_hours=1,
            enable_anomaly_detection=False,
            enable_trend_analysis=False,
            smoothing_window=3,
        )

    def test_minimal_configuration(self, minimal_analyzer):
        """测试最小配置下的分析"""
        minimal_analyzer.add_odds_data("minimal_test", 2.00, 3.40, 3.80)
        minimal_analyzer.add_odds_data("minimal_test", 2.02, 3.38, 3.82)

        result = minimal_analyzer.analyze_odds_movement("minimal_test")
        assert result is not None
        assert "error" not in result

    def test_maximal_configuration(self):
        """测试最大配置下的分析"""
        maximal_analyzer = OddsMovementAnalyzer(
            steam_threshold=0.30,
            significant_move_threshold=0.25,
            time_window_hours=168,  # 7天
            enable_anomaly_detection=True,
            enable_trend_analysis=True,
            smoothing_window=15,
        )

        # 添加大量数据
        for i in range(50):
            maximal_analyzer.add_odds_data(
                "maximal_test",
                home_odds=2.00 + np.random.normal(0, 0.1),
                draw_odds=3.40 + np.random.normal(0, 0.15),
                away_odds=3.80 + np.random.normal(0, 0.2),
                timestamp=datetime.now() - timedelta(hours=i),
                volume=1000 + i * 10,
            )

        result = maximal_analyzer.analyze_odds_movement("maximal_test")
        assert result is not None
        assert "error" not in result

    def test_extreme_time_windows(self):
        """测试极端时间窗口"""
        # 非常短的时间窗口
        short_analyzer = OddsMovementAnalyzer(time_window_hours=1)

        # 非常长的时间窗口
        long_analyzer = OddsMovementAnalyzer(time_window_hours=168)  # 7天

        for analyzer in [short_analyzer, long_analyzer]:
            analyzer.add_odds_data("time_test", 2.00, 3.40, 3.80)
            analyzer.add_odds_data("time_test", 2.10, 3.30, 3.90)

            result = analyzer.analyze_odds_movement("time_test")
            # 数据不足是预期行为，但不应该崩溃
            if "error" in result:
                assert "数据不足" in result["error"]
            else:
                assert result is not None

    def test_boundary_steam_thresholds(self):
        """测试边界Steam阈值"""
        # 极低阈值（敏感）
        sensitive_analyzer = OddsMovementAnalyzer(steam_threshold=0.01)

        # 极高阈值（不敏感）
        insensitive_analyzer = OddsMovementAnalyzer(steam_threshold=1.0)

        # Steam信号序列
        steam_data = [
            {
                "timestamp": datetime.now() + timedelta(hours=i),
                "home_odds": 2.00 - i * 0.001,
            }
            for i in range(5)
        ]

        for analyzer in [sensitive_analyzer, insensitive_analyzer]:
            for odds_data in steam_data:
                analyzer.add_odds_data(
                    "boundary_test",
                    home_odds=odds_data["home_odds"],
                    draw_odds=3.40,
                    away_odds=3.80,
                    timestamp=odds_data["timestamp"],
                )

            result = analyzer.analyze_odds_movement("boundary_test")
            assert result is not None
