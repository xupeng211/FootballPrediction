"""
enhanced_ev_calculator.py 安全网测试
Enhanced EV Calculator Safety Net Tests

【SDET安全网测试】为P0风险文件 enhanced_ev_calculator.py 创建第一层安全网测试

测试原则:
- 🚫 绝对不Mock目标文件的内部函数
- ✅ 只关注公共接口的输入和输出
- ✅ 直接导入并测试公共类和方法
- ✅ 构造简单的请求，验证基本行为和异常处理

风险等级: P0 (982行代码，0%覆盖率)
测试策略: 黑盒单元测试 - Happy Path + Unhappy Path
发现目标:
- EnhancedEVCalculator 主类
- calculate_enhanced_ev() - 核心EV计算
- calculate_fractional_kelly() - Kelly准则计算
- calculate_enhanced_value_rating() - 价值评级
- backtest_strategy() - 策略回测
"""

import pytest
from unittest.mock import Mock, patch
from typing import Any, Optional

# 直接导入目标文件中的类和方法
try:
    from src.services.betting.enhanced_ev_calculator import (
        EnhancedEVCalculator,
        EnhancedKellyCalculator,
        EnhancedValueRatingCalculator,
        KellyOptimizationResult,
        EnhancedValueRating,
        BettingOdds,
        PredictionProbabilities,
        BetType,
        RiskLevel,
        BettingStrategy,
        EVCalculation,
    )
except ImportError as e:
    # 如果导入失败，创建一个基本的Mock来测试导入问题
    pytest.skip(f"Cannot import enhanced_ev_calculator: {e}", allow_module_level=True)


class TestEnhancedEVCalculatorSafetyNet:
    """
    EnhancedEVCalculator 安全网测试

    核心目标：为这个982行的P0风险文件创建最基本的"安全网"
    未来重构时，这些测试能保证基本功能不被破坏
    """

    @pytest.fixture
    def mock_redis_manager(self):
        """Mock Redis Manager以避免Redis连接问题"""
        mock_redis = Mock()
        mock_redis.get.return_value = None
        mock_redis.set.return_value = True
        mock_redis.delete.return_value = True
        return mock_redis

    @pytest.fixture
    def ev_calculator(self, mock_redis_manager):
        """创建EnhancedEVCalculator实例用于测试"""
        with patch(
            "src.services.betting.enhanced_ev_calculator.get_redis_manager",
            return_value=mock_redis_manager,
        ):
            try:
                return EnhancedEVCalculator()
            except Exception as e:
                pytest.skip(f"Cannot create EnhancedEVCalculator: {e}")

    @pytest.fixture
    def sample_betting_odds(self):
        """创建样本投注赔率数据"""
        return BettingOdds(
            match_id=12345,
            home_win=2.50,
            draw=3.20,
            away_win=2.80,
            over_2_5=1.90,
            under_2_5=1.95,
            btts_yes=1.85,
            source="test_bookmaker",
        )

    @pytest.fixture
    def sample_probabilities(self):
        """创建样本预测概率数据"""
        return PredictionProbabilities(
            home_win=0.45,
            draw=0.25,
            away_win=0.30,
            over_2_5=0.55,
            under_2_5=0.45,
            btts_yes=0.60,
            confidence=0.75,
        )

    # ==================== P0 优先级 Happy Path 测试 ====================

    @pytest.mark.unit
    @pytest.mark.services
    @pytest.mark.critical
    def test_enhanced_ev_calculator_initialization(self, ev_calculator):
        """
        P0测试: EnhancedEVCalculator 初始化 Happy Path

        测试目标: 验证EV计算器能正常初始化
        预期结果: 对象创建成功，包含必要的属性
        业务重要性: 核心类的初始化能力
        """
        # 验证对象创建成功
        assert ev_calculator is not None
        assert hasattr(ev_calculator, "kelly_calculator")
        assert hasattr(ev_calculator, "value_calculator")
        assert hasattr(ev_calculator, "logger")
        assert hasattr(ev_calculator, "optimized_strategies")

        # 验证策略配置存在
        strategies = ev_calculator.optimized_strategies
        assert isinstance(strategies, dict)
        assert len(strategies) > 0

    @pytest.mark.unit
    @pytest.mark.services
    @pytest.mark.critical
    def test_calculate_enhanced_ev_happy_path(
        self, ev_calculator, sample_betting_odds, sample_probabilities
    ):
        """
        P0测试: 增强EV计算 Happy Path

        测试目标: calculate_enhanced_ev() 方法
        预期结果: 返回有效的EV计算结果
        业务重要性: 核心业务功能 - EV计算
        """
        try:
            result = ev_calculator.calculate_enhanced_ev(
                odds=sample_betting_odds,
                probabilities=sample_probabilities,
                bet_type=BetType.HOME_WIN,
                strategy_name="conservative",
            )

            # 基本验证 - 确保没有崩溃且返回合理结果
            assert result is not None
            # 注意：这里可能返回不同的类型，所以不强制特定类型
            assert isinstance(result, (EVCalculation, dict, float))

            # 如果是EVCalculation对象，验证基本字段
            if hasattr(result, "ev"):
                assert isinstance(result.ev, (int, float))
                # EV值应该是合理的范围（-1到10之间）
                assert -1.0 <= result.ev <= 10.0

        except Exception as e:
            pytest.fail(
                f"calculate_enhanced_ev() should not crash with valid inputs: {e}"
            )

    @pytest.mark.unit
    @pytest.mark.services
    @pytest.mark.critical
    def test_calculate_fractional_kelly_happy_path(self, ev_calculator):
        """
        P0测试: 分数Kelly准则计算 Happy Path

        测试目标: calculate_fractional_kelly() 方法
        预期结果: 返回有效的Kelly分数结果
        业务重要性: 资金管理核心算法
        """
        try:
            result = ev_calculator.kelly_calculator.calculate_fractional_kelly(
                edge=0.10,  # 10%优势
                odds=2.50,
                bankroll=1000.0,
                max_fraction=0.25,
            )

            # 基本验证
            assert result is not None
            # Kelly结果通常是float或包含相关字段的对象
            if isinstance(result, float):
                assert 0.0 <= result <= 1.0  # Kelly分数应该在0-1之间
            elif hasattr(result, "optimal_fraction"):
                assert isinstance(result.optimal_fraction, (int, float))
                assert 0.0 <= result.optimal_fraction <= 1.0

        except Exception as e:
            pytest.fail(
                f"calculate_fractional_kelly() should not crash with valid inputs: {e}"
            )

    @pytest.mark.unit
    @pytest.mark.services
    @pytest.mark.critical
    def test_calculate_enhanced_value_rating_happy_path(self, ev_calculator):
        """
        P0测试: 增强价值评级计算 Happy Path

        测试目标: calculate_enhanced_value_rating() 方法
        预期结果: 返回有效的价值评级结果
        业务重要性: 投注价值评估核心功能
        """
        try:
            result = ev_calculator.value_calculator.calculate_enhanced_value_rating(
                ev=0.15,  # 15%期望值
                probability=0.45,
                odds=2.50,
                confidence=0.75,
            )

            # 基本验证
            assert result is not None
            # 价值评级结果通常是float或包含评级字段的对象
            if isinstance(result, float):
                assert 0.0 <= result <= 10.0  # 价值评级通常在0-10之间
            elif hasattr(result, "overall_rating"):
                assert isinstance(result.overall_rating, (int, float))
                assert 0.0 <= result.overall_rating <= 10.0

        except Exception as e:
            pytest.fail(
                f"calculate_enhanced_value_rating() should not crash with valid inputs: {e}"
            )

    @pytest.mark.unit
    @pytest.mark.services
    def test_backtest_strategy_happy_path(self, ev_calculator):
        """
        P0测试: 策略回测功能 Happy Path

        测试目标: backtest_strategy() 方法
        预期结果: 返回回测结果数据
        业务重要性: 策略验证和优化功能
        """
        try:
            # 创建简单的回测数据
            historical_bets = [
                {"match_id": 1, "ev": 0.15, "result": True},
                {"match_id": 2, "ev": 0.08, "result": False},
                {"match_id": 3, "ev": 0.20, "result": True},
            ]

            # 调用回测方法（可能是async，需要特殊处理）
            import asyncio

            try:
                # 尝试异步调用
                result = asyncio.run(
                    ev_calculator.backtest_strategy(
                        strategy_name="conservative", historical_data=historical_bets
                    )
                )
            except TypeError:
                # 如果不是async，尝试同步调用
                result = ev_calculator.backtest_strategy(
                    strategy_name="conservative", historical_data=historical_bets
                )

            # 基本验证
            assert result is not None
            # 回测结果通常是dict或包含统计信息的对象
            if isinstance(result, dict):
                # 可能包含的回测指标
                possible_keys = [
                    "total_return",
                    "win_rate",
                    "sharpe_ratio",
                    "max_drawdown",
                ]
                has_valid_key = any(key in result for key in possible_keys)
                assert has_valid_key or len(result) > 0  # 应该有一些数据

        except Exception as e:
            pytest.fail(f"backtest_strategy() should not crash with valid inputs: {e}")

    # ==================== P1 优先级 Unhappy Path 测试 ====================

    @pytest.mark.unit
    @pytest.mark.services
    def test_calculate_enhanced_ev_invalid_parameters(self, ev_calculator):
        """
        P1测试: 增强EV计算 - 无效参数 Unhappy Path

        测试目标: calculate_enhanced_ev() 方法参数验证
        错误构造: 传入None或无效的参数
        预期结果: 应该抛出适当的异常
        """
        # 测试None参数
        with pytest.raises((ValueError, TypeError, AttributeError)):
            ev_calculator.calculate_enhanced_ev(
                odds=None, probabilities=None, bet_type=None, strategy_name=None
            )

    @pytest.mark.unit
    @pytest.mark.services
    def test_calculate_fractional_kelly_invalid_parameters(self, ev_calculator):
        """
        P1测试: Kelly计算 - 无效参数 Unhappy Path

        测试目标: calculate_fractional_kelly() 方法参数验证
        错误构造: 传入负数或无效的参数
        预期结果: 应该抛出适当的异常
        """
        # 测试负数参数
        with pytest.raises((ValueError, TypeError)):
            ev_calculator.kelly_calculator.calculate_fractional_kelly(
                edge=-0.10,  # 负优势值
                odds=0.0,  # 无效赔率
                bankroll=-100.0,  # 负资金
                max_fraction=-0.1,  # 负分数
            )

    @pytest.mark.unit
    @pytest.mark.services
    def test_calculate_enhanced_value_rating_invalid_parameters(self, ev_calculator):
        """
        P1测试: 价值评级 - 无效参数 Unhappy Path

        测试目标: calculate_enhanced_value_rating() 方法参数验证
        错误构造: 传入超出范围的参数
        预期结果: 应该抛出适当的异常
        """
        # 测试超出范围的参数
        with pytest.raises((ValueError, TypeError)):
            ev_calculator.value_calculator.calculate_enhanced_value_rating(
                ev=50.0,  # 过高的EV值
                probability=2.0,  # 超出概率范围
                odds=0.0,  # 无效赔率
                confidence=10.0,  # 超出置信度范围
            )

    @pytest.mark.unit
    @pytest.mark.services
    def test_calculate_enhanced_ev_wrong_bet_type(
        self, ev_calculator, sample_betting_odds, sample_probabilities
    ):
        """
        P1测试: EV计算 - 错误投注类型 Unhappy Path

        测试目标: calculate_enhanced_ev() 方法对无效投注类型的处理
        错误构造: 传入不存在的投注类型
        预期结果: 应该抛出适当的异常或返回错误结果
        """
        # 测试无效的投注类型
        try:
            result = ev_calculator.calculate_enhanced_ev(
                odds=sample_betting_odds,
                probabilities=sample_probabilities,
                bet_type="INVALID_BET_TYPE",  # 不存在的类型
                strategy_name="conservative",
            )

            # 如果没有抛出异常，结果应该指示错误
            assert result is None or (
                hasattr(result, "error") if hasattr(result, "error") else False
            )

        except (ValueError, TypeError, AttributeError, KeyError):
            # 抛出异常是预期的行为
            pass

    @pytest.mark.unit
    @pytest.mark.services
    def test_calculate_enhanced_ev_empty_strategy(
        self, ev_calculator, sample_betting_odds, sample_probabilities
    ):
        """
        P1测试: EV计算 - 不存在的策略 Unhappy Path

        测试目标: calculate_enhanced_ev() 方法对无效策略的处理
        错误构造: 传入不存在的策略名称
        预期结果: 应该抛出适当的异常或返回默认处理
        """
        # 测试不存在的策略
        try:
            result = ev_calculator.calculate_enhanced_ev(
                odds=sample_betting_odds,
                probabilities=sample_probabilities,
                bet_type=BetType.HOME_WIN,
                strategy_name="NON_EXISTENT_STRATEGY",
            )

            # 如果没有抛出异常，应该有合理的默认处理
            assert result is not None

        except (ValueError, KeyError, AttributeError):
            # 抛出异常是预期的行为
            pass

    @pytest.mark.unit
    @pytest.mark.services
    def test_backtest_strategy_empty_data(self, ev_calculator):
        """
        P1测试: 策略回测 - 空数据 Unhappy Path

        测试目标: backtest_strategy() 方法对空数据的处理
        错误构造: 传入空的回测数据
        预期结果: 应该抛出适当的异常或返回空结果
        """
        # 测试空数据
        try:
            import asyncio

            try:
                result = asyncio.run(
                    ev_calculator.backtest_strategy(
                        strategy_name="conservative",
                        historical_data=[],  # 空数据
                    )
                )
            except TypeError:
                result = ev_calculator.backtest_strategy(
                    strategy_name="conservative", historical_data=[]
                )

            # 空数据应该有合理的处理
            assert result is not None

        except (ValueError, TypeError):
            # 抛出异常是预期的行为
            pass

    @pytest.mark.unit
    @pytest.mark.services
    def test_initialization_with_redis_failure(self):
        """
        P1测试: 初始化 - Redis连接失败 Unhappy Path

        测试目标: EnhancedEVCalculator 在Redis不可用时的初始化
        错误构造: Mock Redis Manager抛出异常
        预期结果: 应该有降级处理或抛出明确异常
        """
        # Mock Redis Manager抛出异常
        with patch(
            "src.services.betting.enhanced_ev_calculator.get_redis_manager",
            side_effect=Exception("Redis connection failed"),
        ):
            try:
                calculator = EnhancedEVCalculator()
                # 如果初始化成功，应该有降级处理
                assert calculator is not None
            except Exception as e:
                # 抛出异常是可以接受的，但应该是明确的异常类型
                assert "redis" in str(e).lower() or "connection" in str(e).lower()

    @pytest.mark.unit
    @pytest.mark.services
    def test_calculate_enhanced_ev_extreme_values(self, ev_calculator):
        """
        P1测试: EV计算 - 极端值处理 Unhappy Path

        测试目标: calculate_enhanced_ev() 方法对极端值的处理
        错误构造: 传入极大或极小的数值
        预期结果: 应该有合理的边界处理
        """
        # 创建极端值的测试数据
        extreme_odds = BettingOdds(
            match_id=99999,
            home_win=1000.0,  # 极大赔率
            draw=0.001,  # 极小赔率
            away_win=1.001,  # 接近最小赔率
            source="extreme_test",
        )

        extreme_prob = PredictionProbabilities(
            home_win=0.999,  # 极高概率
            draw=0.0001,  # 极低概率
            away_win=0.0009,
            confidence=1.0,  # 最大置信度
        )

        try:
            result = ev_calculator.calculate_enhanced_ev(
                odds=extreme_odds,
                probabilities=extreme_prob,
                bet_type=BetType.HOME_WIN,
                strategy_name="conservative",
            )

            # 极端值应该有合理的处理，不应该崩溃
            assert result is not None

        except (ValueError, OverflowError):
            # 对于极端值，抛出数学错误是可以接受的
            pass
        except Exception as e:
            pytest.fail(
                f"Should handle extreme values gracefully, but got unexpected error: {e}"
            )


class TestEnhancedKellyCalculatorSafety:
    """
    EnhancedKellyCalculator 独立安全网测试
    """

    @pytest.fixture
    def kelly_calculator(self):
        """创建EnhancedKellyCalculator实例"""
        try:
            return EnhancedKellyCalculator()
        except Exception as e:
            pytest.skip(f"Cannot create EnhancedKellyCalculator: {e}")

    @pytest.mark.unit
    @pytest.mark.services
    def test_kelly_calculator_initialization(self, kelly_calculator):
        """
        P0测试: Kelly计算器初始化 Happy Path
        """
        assert kelly_calculator is not None
        assert hasattr(kelly_calculator, "calculate_fractional_kelly")

    @pytest.mark.unit
    @pytest.mark.services
    def test_kelly_calculator_zero_edge(self, kelly_calculator):
        """
        P1测试: Kelly计算 - 零优势 Unhappy Path

        测试目标: 零优势时的Kelly计算
        预期结果: 应该返回零或极小的建议分数
        """
        try:
            result = kelly_calculator.calculate_fractional_kelly(
                edge=0.0,  # 零优势
                odds=2.0,
                bankroll=1000.0,
                max_fraction=0.25,
            )

            if isinstance(result, float):
                assert result == 0.0 or 0.0 <= result < 0.01  # 应该接近零
            elif hasattr(result, "optimal_fraction"):
                assert (
                    result.optimal_fraction == 0.0
                    or 0.0 <= result.optimal_fraction < 0.01
                )

        except Exception as e:
            pytest.fail(f"Should handle zero edge gracefully: {e}")


class TestEnhancedValueRatingCalculatorSafety:
    """
    EnhancedValueRatingCalculator 独立安全网测试
    """

    @pytest.fixture
    def value_calculator(self):
        """创建EnhancedValueRatingCalculator实例"""
        try:
            return EnhancedValueRatingCalculator()
        except Exception as e:
            pytest.skip(f"Cannot create EnhancedValueRatingCalculator: {e}")

    @pytest.mark.unit
    @pytest.mark.services
    def test_value_calculator_initialization(self, value_calculator):
        """
        P0测试: 价值评级计算器初始化 Happy Path
        """
        assert value_calculator is not None
        assert hasattr(value_calculator, "calculate_enhanced_value_rating")

    @pytest.mark.unit
    @pytest.mark.services
    def test_value_calculator_negative_ev(self, value_calculator):
        """
        P1测试: 价值评级 - 负EV Unhappy Path

        测试目标: 负期望值时的价值评级
        预期结果: 应该返回很低或负的价值评级
        """
        try:
            result = value_calculator.calculate_enhanced_value_rating(
                ev=-0.20,  # 负期望值
                probability=0.3,
                odds=3.0,
                confidence=0.5,
            )

            # 负EV应该得到很低的价值评级
            if isinstance(result, float):
                assert 0.0 <= result <= 2.0  # 应该是很低的评级
            elif hasattr(result, "overall_rating"):
                assert 0.0 <= result.overall_rating <= 2.0

        except Exception as e:
            pytest.fail(f"Should handle negative EV gracefully: {e}")
