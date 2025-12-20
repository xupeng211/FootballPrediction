#!/usr/bin/env python3
"""
自动化调优器 - Sprint 6核心组件

基于Backtester的参数优化系统，实现：
1. 超参数自动搜索
2. 策略组合优化
3. 风险调整调优
4. 性能基准测试
5. 最优参数生成

Role: 高级DevOps & 策略部署专家
Sprint: 实时化、可观测性与策略调优
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
import json
import pickle
import hashlib
from pathlib import Path
import numpy as np
from scipy import stats, optimize
import optuna

from ..testing.backtester import BacktestEngine, BacktestConfig, BacktestResult
from ..strategy.kelly_criterion import KellyCriterion, KellyStrategy
from ..ml.features.elo_rating_system import EloRatingSystem
from ..ml.features.poisson_features import PoissonFeatureCalculator
from ..ml.features.odds_movement_features import OddsMovementAnalyzer
from ..ml.inference.predictor import MatchPredictor

logger = logging.getLogger(__name__)


class OptimizationStrategy(Enum):
    """优化策略枚举"""

    GRID_SEARCH = "grid_search"
    RANDOM_SEARCH = "random_search"
    BAYESIAN_OPTIMIZATION = "bayesian"
    GENETIC_ALGORITHM = "genetic"
    PARTICLE_SWARM = "particle_swarm"
    SIMULATED_ANNEALING = "simulated_annealing"


class ObjectiveMetric(Enum):
    """优化目标指标"""

    MAXIMIZE_SHARPE_RATIO = "maximize_sharpe_ratio"
    MAXIMIZE_ROI = "maximize_roi"
    MINIMIZE_MAX_DRAWDOWN = "minimize_max_drawdown"
    MAXIMIZE_WIN_RATE = "maximize_win_rate"
    MAXIMIZE_CALMAR_RATIO = "maximize_calmar_ratio"
    BALANCED_OBJECTIVE = "balanced_objective"


@dataclass
class ParameterSpace:
    """参数空间定义"""

    name: str
    param_type: str  # "categorical", "int", "float", "bool"
    low: Optional[Union[float, int]] = None
    high: Optional[Union[float, int]] = None
    choices: Optional[List[Any]] = None
    default: Any = None

    def sample(self) -> Any:
        """从参数空间中采样"""
        if self.param_type == "categorical":
            if not self.choices:
                return self.default
            return np.random.choice(self.choices)
        elif self.param_type == "int":
            return np.random.randint(self.low or 0, self.high or 100)
        elif self.param_type == "float":
            return np.random.uniform(self.low or 0.0, self.high or 1.0)
        elif self.param_type == "bool":
            return np.random.choice([True, False])
        else:
            return self.default


@dataclass
class OptimizationConfig:
    """优化配置"""

    strategy: OptimizationStrategy = OptimizationStrategy.BAYESIAN_OPTIMIZATION
    objective_metric: ObjectiveMetric = ObjectiveMetric.BALANCED_OBJECTIVE
    n_trials: int = 100
    timeout_seconds: int = 3600
    n_jobs: int = -1  # 并行作业数
    early_stopping_patience: int = 20
    min_improvement: float = 0.01
    random_seed: int = 42

    # 回测配置
    backtest_config: Optional[BacktestConfig] = None

    # 优化范围
    optimize_kelly_parameters: bool = True
    optimize_elo_parameters: bool = True
    optimize_poisson_parameters: bool = True
    optimize_model_weights: bool = True
    optimize_strategy_combination: bool = True


@dataclass
class OptimizationResult:
    """优化结果"""

    best_params: Dict[str, Any]
    best_score: float
    best_trial_number: int
    n_trials_completed: int
    optimization_time_seconds: float

    # 详细结果
    trial_history: List[Dict[str, Any]] = field(default_factory=list)
    parameter_importance: Dict[str, float] = field(default_factory=dict)
    convergence_curve: List[float] = field(default_factory=list)

    # 性能指标
    final_backtest_result: Optional[BacktestResult] = None
    improvement_over_baseline: float = 0.0

    # 元数据
    optimization_id: str = field(default="")
    timestamp: datetime = field(default_factory=datetime.utcnow)
    config: Optional[OptimizationConfig] = None


class HyperparameterTuner:
    """
    超参数自动调优器

    基于Backtester实现全面的参数优化，支持多种优化算法
    和目标函数，自动寻找最优策略参数组合。
    """

    def __init__(self, config: OptimizationConfig):
        self.config = config
        self.optimization_id = self._generate_optimization_id()

        # 初始化组件
        self.backtest_engine: Optional[BacktestEngine] = None
        self.study: Optional[optuna.Study] = None

        # 定义参数空间
        self.parameter_spaces = self._define_parameter_spaces()

        # 结果存储
        self.results_cache: Dict[str, OptimizationResult] = {}
        self.current_best_score = float("-inf")
        self.trials_without_improvement = 0

        logger.info(f"🔧 超参数调优器初始化完成: {self.optimization_id}")

    def _generate_optimization_id(self) -> str:
        """生成优化ID"""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        config_hash = hashlib.md5(
            json.dumps(
                {
                    "strategy": self.config.strategy.value,
                    "objective": self.config.objective_metric.value,
                    "trials": self.config.n_trials,
                },
                sort_keys=True,
            ).encode()
        ).hexdigest()[:8]
        return f"opt_{timestamp}_{config_hash}"

    def _define_parameter_spaces(self) -> Dict[str, ParameterSpace]:
        """定义参数搜索空间"""
        spaces = {}

        if self.config.optimize_kelly_parameters:
            # Kelly准则参数
            spaces.update(
                {
                    "kelly_strategy": ParameterSpace(
                        name="kelly_strategy",
                        param_type="categorical",
                        choices=[s.value for s in KellyStrategy],
                        default=KellyStrategy.FRACTIONAL_KELLY.value,
                    ),
                    "kelly_fraction_multiplier": ParameterSpace(
                        name="kelly_fraction_multiplier",
                        param_type="float",
                        low=0.1,
                        high=0.5,
                        default=0.25,
                    ),
                    "kelly_min_edge_threshold": ParameterSpace(
                        name="kelly_min_edge_threshold",
                        param_type="float",
                        low=0.01,
                        high=0.15,
                        default=0.05,
                    ),
                    "kelly_max_stake_percentage": ParameterSpace(
                        name="kelly_max_stake_percentage",
                        param_type="float",
                        low=0.02,
                        high=0.20,
                        default=0.10,
                    ),
                }
            )

        if self.config.optimize_elo_parameters:
            # Elo评级参数
            spaces.update(
                {
                    "elo_initial_rating": ParameterSpace(
                        name="elo_initial_rating",
                        param_type="int",
                        low=1200,
                        high=1800,
                        default=1500,
                    ),
                    "elo_home_advantage": ParameterSpace(
                        name="elo_home_advantage",
                        param_type="int",
                        low=20,
                        high=100,
                        default=50,
                    ),
                    "elo_base_k_factor": ParameterSpace(
                        name="elo_base_k_factor",
                        param_type="float",
                        low=20.0,
                        high=60.0,
                        default=40.0,
                    ),
                    "elo_dynamic_k_enabled": ParameterSpace(
                        name="elo_dynamic_k_enabled", param_type="bool", default=True
                    ),
                }
            )

        if self.config.optimize_poisson_parameters:
            # 泊松分布参数
            spaces.update(
                {
                    "poisson_home_lambda_default": ParameterSpace(
                        name="poisson_home_lambda_default",
                        param_type="float",
                        low=1.0,
                        high=2.5,
                        default=1.5,
                    ),
                    "poisson_away_lambda_default": ParameterSpace(
                        name="poisson_away_lambda_default",
                        param_type="float",
                        low=0.8,
                        high=2.0,
                        default=1.2,
                    ),
                    "poisson_league_avg_goals": ParameterSpace(
                        name="poisson_league_avg_goals",
                        param_type="float",
                        low=2.2,
                        high=3.2,
                        default=2.7,
                    ),
                    "poisson_time_decay_enabled": ParameterSpace(
                        name="poisson_time_decay_enabled",
                        param_type="bool",
                        default=True,
                    ),
                }
            )

        if self.config.optimize_model_weights:
            # 模型权重参数
            spaces.update(
                {
                    "model_xgboost_weight": ParameterSpace(
                        name="model_xgboost_weight",
                        param_type="float",
                        low=0.2,
                        high=0.7,
                        default=0.4,
                    ),
                    "model_logistic_weight": ParameterSpace(
                        name="model_logistic_weight",
                        param_type="float",
                        low=0.1,
                        high=0.5,
                        default=0.3,
                    ),
                    "model_poisson_weight": ParameterSpace(
                        name="model_poisson_weight",
                        param_type="float",
                        low=0.1,
                        high=0.5,
                        default=0.3,
                    ),
                }
            )

        if self.config.optimize_strategy_combination:
            # 策略组合参数
            spaces.update(
                {
                    "strategy_portfolio_weights": ParameterSpace(
                        name="strategy_portfolio_weights",
                        param_type="categorical",
                        choices=[
                            "equal_weight",
                            "kelly_dominant",
                            "elo_focused",
                            "poisson_balanced",
                            "adaptive_dynamic",
                        ],
                        default="equal_weight",
                    ),
                    "risk_adjustment_factor": ParameterSpace(
                        name="risk_adjustment_factor",
                        param_type="float",
                        low=0.5,
                        high=2.0,
                        default=1.0,
                    ),
                    "confidence_threshold": ParameterSpace(
                        name="confidence_threshold",
                        param_type="float",
                        low=0.6,
                        high=0.9,
                        default=0.75,
                    ),
                }
            )

        return spaces

    async def initialize(self) -> None:
        """初始化调优器"""
        try:
            # 初始化回测引擎
            if self.config.backtest_config:
                self.backtest_engine = BacktestEngine(self.config.backtest_config)
            else:
                # 使用默认配置
                default_config = BacktestConfig(
                    data_path="./data/historical/",
                    strategies=[
                        "kelly_fractional",
                        "elo_based",
                        "poisson_based",
                        "ensemble",
                    ],
                    initial_bankroll=10000.0,
                    n_workers=2,  # 减少并行数以节省资源
                    chunk_size=1000,
                    memory_limit_gb=4.0,
                    output_path="./optimization_results/",
                )
                self.backtest_engine = BacktestEngine(default_config)

            # 初始化优化研究
            self._initialize_optimization_study()

            logger.info(f"✅ 超参数调优器初始化成功: {self.optimization_id}")

        except Exception as e:
            logger.error(f"❌ 超参数调优器初始化失败: {e}")
            raise

    def _initialize_optimization_study(self) -> None:
        """初始化优化研究"""
        try:
            # 根据策略创建不同的研究
            if self.config.strategy == OptimizationStrategy.BAYESIAN_OPTIMIZATION:
                self.study = optuna.create_study(
                    direction="maximize",
                    sampler=optuna.samplers.TPESampler(seed=self.config.random_seed, n_startup_trials=20),
                    pruner=optuna.pruners.MedianPruner(n_startup_trials=10, n_warmup_steps=5, interval_steps=3),
                )
            elif self.config.strategy == OptimizationStrategy.RANDOM_SEARCH:
                self.study = optuna.create_study(
                    direction="maximize",
                    sampler=optuna.samplers.RandomSampler(seed=self.config.random_seed),
                )
            else:
                # 网格搜索等其他策略
                self.study = optuna.create_study(direction="maximize")

            logger.info(f"🎯 优化研究创建完成: {self.config.strategy.value}")

        except Exception as e:
            logger.error(f"❌ 优化研究创建失败: {e}")
            raise

    async def optimize(self) -> OptimizationResult:
        """
        执行参数优化

        Returns:
            OptimizationResult: 优化结果详情
        """
        start_time = time.time()

        logger.info(f"🚀 开始参数优化: {self.config.n_trials} 次试验")

        try:
            # 设置优化目标函数
            objective_func = self._create_objective_function()

            # 执行优化
            if self.config.n_jobs == -1:
                # 使用所有可用CPU
                n_jobs = min(4, len(self.parameter_spaces))  # 限制最大并行数
            else:
                n_jobs = max(1, self.config.n_jobs)

            # 执行优化
            if self.config.strategy == OptimizationStrategy.BAYESIAN_OPTIMIZATION:
                # 使用Optuna的优化
                self.study.optimize(
                    objective_func,
                    n_trials=self.config.n_trials,
                    timeout=self.config.timeout_seconds,
                    n_jobs=n_jobs if n_jobs == 1 else 1,  # Optuna在多进程时需要特殊处理
                    show_progress_bar=True,
                )
            else:
                # 使用自定义优化循环
                await self._custom_optimization_loop(objective_func, n_jobs)

            # 收集最终结果
            optimization_time = time.time() - start_time
            result = self._collect_optimization_result(optimization_time)

            # 运行最终验证回测
            if result.best_params:
                logger.info("🔬 运行最终验证回测...")
                result.final_backtest_result = await self._run_validation_backtest(result.best_params)

            # 计算改进程度
            result.improvement_over_baseline = await self._calculate_improvement(result)

            logger.info(f"✅ 参数优化完成: 最佳得分 {result.best_score:.4f}")
            logger.info(f"⏱️ 总耗时: {optimization_time:.1f}s")

            # 缓存结果
            self.results_cache[self.optimization_id] = result

            return result

        except Exception as e:
            logger.error(f"❌ 参数优化失败: {e}")
            raise

    def _create_objective_function(self) -> Callable[[Dict[str, Any]], float]:
        """创建优化目标函数"""

        def objective(trial) -> float:
            try:
                # 建议参数
                params = {}
                for param_name, param_space in self.parameter_spaces.items():
                    if param_space.param_type == "categorical":
                        if param_space.param_type == "bool":
                            params[param_name] = trial.suggest_categorical(param_name, [True, False])
                        else:
                            params[param_name] = trial.suggest_categorical(
                                param_name, param_space.choices or [param_space.default]
                            )
                    elif param_space.param_type == "int":
                        params[param_name] = trial.suggest_int(
                            param_name, param_space.low or 0, param_space.high or 100
                        )
                    elif param_space.param_type == "float":
                        params[param_name] = trial.suggest_float(
                            param_name, param_space.low or 0.0, param_space.high or 1.0
                        )
                    else:
                        params[param_name] = param_space.default

                # 运行回测评估
                score = asyncio.run(self._evaluate_parameters(params))

                # 早停检查
                self._check_early_stopping(score)

                return score

            except Exception as e:
                logger.warning(f"⚠️ 试验评估失败: {e}")
                return float("-inf")  # 返回最差分数

        return objective

    async def _evaluate_parameters(self, params: Dict[str, Any]) -> float:
        """
        评估给定参数的性能

        Args:
            params: 参数字典

        Returns:
            float: 目标函数得分
        """
        try:
            # 1. 创建定制化的回测配置
            backtest_config = self._create_custom_backtest_config(params)

            # 2. 初始化回测引擎
            engine = BacktestEngine(backtest_config)

            # 3. 注入定制化参数到各组件
            await self._inject_parameters_to_components(engine, params)

            # 4. 运行回测
            backtest_result = await engine.run_backtest()

            # 5. 计算目标函数得分
            score = self._calculate_objective_score(backtest_result, params)

            return score

        except Exception as e:
            logger.warning(f"⚠️ 参数评估失败: {e}")
            return float("-inf")

    def _create_custom_backtest_config(self, params: Dict[str, Any]) -> BacktestConfig:
        """根据参数创建定制化回测配置"""
        base_config = self.config.backtest_config or BacktestConfig()

        # 更新策略配置
        if "strategy_portfolio_weights" in params:
            weight_strategy = params["strategy_portfolio_weights"]
            if weight_strategy == "kelly_dominant":
                strategies = ["kelly_fractional", "kelly_full"]
            elif weight_strategy == "elo_focused":
                strategies = ["elo_based", "kelly_fractional"]
            elif weight_strategy == "poisson_balanced":
                strategies = ["poisson_based", "kelly_fractional"]
            elif weight_strategy == "adaptive_dynamic":
                strategies = ["kelly_adaptive", "ensemble"]
            else:
                strategies = ["kelly_fractional", "elo_based", "poisson_based"]

            base_config.strategies = strategies

        return base_config

    async def _inject_parameters_to_components(self, engine: BacktestEngine, params: Dict[str, Any]) -> None:
        """将参数注入到回测引擎的各组件中"""
        try:
            # 1. Kelly准则参数
            if hasattr(engine, "kelly_system") and engine.kelly_system:
                kelly_params = {k: v for k, v in params.items() if k.startswith("kelly_")}
                if kelly_params:
                    await self._update_kelly_parameters(engine.kelly_system, kelly_params)

            # 2. Elo评级参数
            if hasattr(engine, "elo_system") and engine.elo_system:
                elo_params = {k: v for k, v in params.items() if k.startswith("elo_")}
                if elo_params:
                    await self._update_elo_parameters(engine.elo_system, elo_params)

            # 3. 泊松参数
            if hasattr(engine, "poisson_calculator") and engine.poisson_calculator:
                poisson_params = {k: v for k, v in params.items() if k.startswith("poisson_")}
                if poisson_params:
                    await self._update_poisson_parameters(engine.poisson_calculator, poisson_params)

            # 4. 模型权重参数
            if hasattr(engine, "predictor") and engine.predictor:
                model_params = {k: v for k, v in params.items() if k.startswith("model_")}
                if model_params:
                    await self._update_model_weights(engine.predictor, model_params)

            # 5. 策略组合参数
            strategy_params = {
                k: v
                for k, v in params.items()
                if any(k.startswith(prefix) for prefix in ["strategy_", "risk_", "confidence_"])
            }
            if strategy_params:
                await self._update_strategy_parameters(engine, strategy_params)

        except Exception as e:
            logger.warning(f"⚠️ 参数注入失败: {e}")

    async def _update_kelly_parameters(self, kelly_system: KellyCriterion, params: Dict[str, Any]) -> None:
        """更新Kelly准则参数"""
        try:
            if "kelly_strategy" in params:
                strategy_map = {s.value: s for s in KellyStrategy}
                kelly_system.kelly_strategy = strategy_map.get(params["kelly_strategy"], KellyStrategy.FRACTIONAL_KELLY)

            if "kelly_fraction_multiplier" in params:
                kelly_system.fraction_multiplier = params["kelly_fraction_multiplier"]

            if "kelly_min_edge_threshold" in params:
                kelly_system.min_edge_threshold = params["kelly_min_edge_threshold"]

            if "kelly_max_stake_percentage" in params:
                kelly_system.max_stake_percentage = params["kelly_max_stake_percentage"]

        except Exception as e:
            logger.warning(f"⚠️ Kelly参数更新失败: {e}")

    async def _update_elo_parameters(self, elo_system: EloRatingSystem, params: Dict[str, Any]) -> None:
        """更新Elo评级参数"""
        try:
            if "elo_initial_rating" in params:
                elo_system.initial_rating = params["elo_initial_rating"]

            if "elo_home_advantage" in params:
                elo_system.home_advantage = params["elo_home_advantage"]

            if "elo_base_k_factor" in params:
                elo_system.base_k_factor = params["elo_base_k_factor"]

            if "elo_dynamic_k_enabled" in params:
                elo_system.enable_dynamic_k = params["elo_dynamic_k_enabled"]

        except Exception as e:
            logger.warning(f"⚠️ Elo参数更新失败: {e}")

    async def _update_poisson_parameters(self, poisson_calc: PoissonFeatureCalculator, params: Dict[str, Any]) -> None:
        """更新泊松参数"""
        try:
            if "poisson_home_lambda_default" in params:
                poisson_calc.home_lambda_default = params["poisson_home_lambda_default"]

            if "poisson_away_lambda_default" in params:
                poisson_calc.away_lambda_default = params["poisson_away_lambda_default"]

            if "poisson_league_avg_goals" in params:
                poisson_calc.league_avg_goals = params["poisson_league_avg_goals"]

            if "poisson_time_decay_enabled" in params:
                poisson_calc.enable_time_decay = params["poisson_time_decay_enabled"]

        except Exception as e:
            logger.warning(f"⚠️ 泊松参数更新失败: {e}")

    async def _update_model_weights(self, predictor: MatchPredictor, params: Dict[str, Any]) -> None:
        """更新模型权重"""
        try:
            # 标准化权重
            weights = {}
            total_weight = 0.0

            if "model_xgboost_weight" in params:
                weights["xgboost_model"] = params["model_xgboost_weight"]
                total_weight += params["model_xgboost_weight"]

            if "model_logistic_weight" in params:
                weights["logistic_regression"] = params["model_logistic_weight"]
                total_weight += params["model_logistic_weight"]

            if "model_poisson_weight" in params:
                weights["poisson_model"] = params["model_poisson_weight"]
                total_weight += params["model_poisson_weight"]

            # 标准化权重
            if total_weight > 0:
                for model in weights:
                    weights[model] = weights[model] / total_weight

            # 更新预测器权重
            if hasattr(predictor, "model_weights"):
                predictor.model_weights.update(weights)

        except Exception as e:
            logger.warning(f"⚠️ 模型权重更新失败: {e}")

    async def _update_strategy_parameters(self, engine: BacktestEngine, params: Dict[str, Any]) -> None:
        """更新策略参数"""
        try:
            # 这里可以添加更多策略特定的参数更新逻辑
            # 例如风险调整因子、置信度阈值等

            if "risk_adjustment_factor" in params:
                if hasattr(engine, "risk_adjustment_factor"):
                    engine.risk_adjustment_factor = params["risk_adjustment_factor"]

            if "confidence_threshold" in params:
                if hasattr(engine, "confidence_threshold"):
                    engine.confidence_threshold = params["confidence_threshold"]

        except Exception as e:
            logger.warning(f"⚠️ 策略参数更新失败: {e}")

    def _calculate_objective_score(self, backtest_result: BacktestResult, params: Dict[str, Any]) -> float:
        """
        根据目标指标计算得分

        Args:
            backtest_result: 回测结果
            params: 当前参数

        Returns:
            float: 目标函数得分
        """
        try:
            metric = self.config.objective_metric

            if metric == ObjectiveMetric.MAXIMIZE_SHARPE_RATIO:
                return backtest_result.sharpe_ratio or 0.0

            elif metric == ObjectiveMetric.MAXIMIZE_ROI:
                return backtest_result.total_roi or 0.0

            elif metric == ObjectiveMetric.MINIMIZE_MAX_DRAWDOWN:
                # 转换为最大化问题
                return -(backtest_result.max_drawdown or 100.0)

            elif metric == ObjectiveMetric.MAXIMIZE_WIN_RATE:
                return backtest_result.win_rate or 0.0

            elif metric == ObjectiveMetric.MAXIMIZE_CALMAR_RATIO:
                return backtest_result.calmar_ratio or 0.0

            elif metric == ObjectiveMetric.BALANCED_OBJECTIVE:
                # 平衡目标：综合多个指标
                sharpe = backtest_result.sharpe_ratio or 0.0
                roi = max(backtest_result.total_roi or 0.0, 0)  # 确保非负
                win_rate = backtest_result.win_rate or 0.0

                # 惩罚最大回撤
                drawdown_penalty = max(0, (backtest_result.max_drawdown or 0) - 20) * 0.1

                # 综合得分 (权重可调)
                score = 0.4 * sharpe + 0.3 * (roi / 100) + 0.2 * win_rate - drawdown_penalty  # ROI转换为0-1范围

                return max(0, score)  # 确保得分非负

            else:
                return 0.0

        except Exception as e:
            logger.warning(f"⚠️ 目标得分计算失败: {e}")
            return 0.0

    def _check_early_stopping(self, score: float) -> None:
        """检查早停条件"""
        if score > self.current_best_score * (1 + self.config.min_improvement):
            self.current_best_score = score
            self.trials_without_improvement = 0
        else:
            self.trials_without_improvement += 1

        if self.trials_without_improvement >= self.config.early_stopping_patience:
            raise optuna.exceptions.TrialPruned()

    async def _custom_optimization_loop(self, objective_func: Callable, n_jobs: int) -> None:
        """自定义优化循环 (用于非Bayesian策略)"""
        best_score = float("-inf")
        best_params = {}

        for trial in range(self.config.n_trials):
            try:
                # 生成随机参数
                params = {}
                for param_name, param_space in self.parameter_spaces.items():
                    params[param_name] = param_space.sample()

                # 评估参数
                score = await self._evaluate_parameters(params)

                # 更新最佳结果
                if score > best_score:
                    best_score = score
                    best_params = params.copy()
                    logger.info(f"🎯 新最佳得分: {score:.4f} (试验 {trial + 1})")

                # 早停检查
                if self._check_early_stopping(score):
                    logger.info(f"⏹️ 早停触发: {trial + 1} 次试验")
                    break

            except Exception as e:
                logger.warning(f"⚠️ 试验 {trial + 1} 失败: {e}")
                continue

        # 手动创建study结果 (用于结果收集)
        if not self.study:
            self.study = optuna.create_study(direction="maximize")
            self.study.tell(best_params, best_score)

    def _collect_optimization_result(self, optimization_time: float) -> OptimizationResult:
        """收集优化结果"""
        try:
            if self.study:
                best_trial = self.study.best_trial
                best_params = best_trial.params
                best_score = best_trial.value
                best_trial_number = best_trial.number

                # 收集试验历史
                trial_history = []
                for i, trial in enumerate(self.study.trials):
                    trial_history.append(
                        {
                            "trial_number": i,
                            "params": trial.params,
                            "score": trial.value,
                            "state": trial.state.name,
                        }
                    )

                # 收集参数重要性 (仅适用于某些策略)
                parameter_importance = {}
                try:
                    if len(self.study.trials) > 1:
                        importance = optuna.importance.get_param_importances(self.study)
                        parameter_importance = dict(importance)
                except:
                    pass

                # 收集收敛曲线
                convergence_curve = []
                current_best = float("-inf")
                for trial in self.study.trials:
                    if trial.value and trial.value > current_best:
                        current_best = trial.value
                    convergence_curve.append(current_best)

            else:
                # 默认结果
                best_params = {}
                best_score = float("-inf")
                best_trial_number = 0
                trial_history = []
                parameter_importance = {}
                convergence_curve = []

            return OptimizationResult(
                best_params=best_params,
                best_score=best_score,
                best_trial_number=best_trial_number,
                n_trials_completed=len(trial_history),
                optimization_time_seconds=optimization_time,
                trial_history=trial_history,
                parameter_importance=parameter_importance,
                convergence_curve=convergence_curve,
                optimization_id=self.optimization_id,
                config=self.config,
            )

        except Exception as e:
            logger.error(f"❌ 优化结果收集失败: {e}")
            raise

    async def _run_validation_backtest(self, best_params: Dict[str, Any]) -> BacktestResult:
        """运行验证回测"""
        try:
            # 使用最佳参数创建验证配置
            validation_config = self._create_custom_backtest_config(best_params)
            validation_config.output_path = f"./optimization_results/validation_{self.optimization_id}/"

            # 创建新的回测引擎
            validation_engine = BacktestEngine(validation_config)

            # 注入最佳参数
            await self._inject_parameters_to_components(validation_engine, best_params)

            # 运行验证回测
            result = await validation_engine.run_backtest()

            logger.info(f"✅ 验证回测完成: ROI={result.total_roi:.2f}%, Sharpe={result.sharpe_ratio:.2f}")

            return result

        except Exception as e:
            logger.error(f"❌ 验证回测失败: {e}")
            # 返回一个空的回测结果
            return BacktestResult()

    async def _calculate_improvement(self, result: OptimizationResult) -> float:
        """计算相对于基线的改进程度"""
        try:
            # 运行基线回测 (使用默认参数)
            baseline_params = {}
            for param_name, param_space in self.parameter_spaces.items():
                baseline_params[param_name] = param_space.default

            baseline_score = await self._evaluate_parameters(baseline_params)

            if baseline_score > 0:
                improvement = ((result.best_score - baseline_score) / baseline_score) * 100
                logger.info(f"📈 相对基线改进: {improvement:.2f}%")
                return improvement
            else:
                return 0.0

        except Exception as e:
            logger.warning(f"⚠️ 改进程度计算失败: {e}")
            return 0.0

    def save_results(self, result: OptimizationResult, filepath: Optional[str] = None) -> str:
        """
        保存优化结果

        Args:
            result: 优化结果
            filepath: 保存路径 (可选)

        Returns:
            str: 保存的文件路径
        """
        try:
            if filepath is None:
                filepath = f"./optimization_results/optimization_{result.optimization_id}.json"

            # 确保目录存在
            Path(filepath).parent.mkdir(parents=True, exist_ok=True)

            # 转换结果为可序列化格式
            serializable_result = {
                "optimization_id": result.optimization_id,
                "timestamp": result.timestamp.isoformat(),
                "best_params": result.best_params,
                "best_score": result.best_score,
                "best_trial_number": result.best_trial_number,
                "n_trials_completed": result.n_trials_completed,
                "optimization_time_seconds": result.optimization_time_seconds,
                "improvement_over_baseline": result.improvement_over_baseline,
                "trial_history": result.trial_history,
                "parameter_importance": result.parameter_importance,
                "convergence_curve": result.convergence_curve,
                "config": (
                    {
                        "strategy": (result.config.strategy.value if result.config else None),
                        "objective_metric": (result.config.objective_metric.value if result.config else None),
                        "n_trials": result.config.n_trials if result.config else None,
                    }
                    if result.config
                    else None
                ),
            }

            # 如果有回测结果，添加关键指标
            if result.final_backtest_result:
                serializable_result["final_backtest_metrics"] = {
                    "total_roi": result.final_backtest_result.total_roi,
                    "sharpe_ratio": result.final_backtest_result.sharpe_ratio,
                    "max_drawdown": result.final_backtest_result.max_drawdown,
                    "win_rate": result.final_backtest_result.win_rate,
                    "calmar_ratio": result.final_backtest_result.calmar_ratio,
                }

            # 保存到文件
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(serializable_result, f, indent=2, ensure_ascii=False)

            logger.info(f"💾 优化结果已保存: {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"❌ 结果保存失败: {e}")
            raise

    def load_results(self, filepath: str) -> OptimizationResult:
        """
        加载优化结果

        Args:
            filepath: 结果文件路径

        Returns:
            OptimizationResult: 加载的优化结果
        """
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            # 重构OptimizationResult对象
            result = OptimizationResult(
                best_params=data["best_params"],
                best_score=data["best_score"],
                best_trial_number=data["best_trial_number"],
                n_trials_completed=data["n_trials_completed"],
                optimization_time_seconds=data["optimization_time_seconds"],
                trial_history=data["trial_history"],
                parameter_importance=data["parameter_importance"],
                convergence_curve=data["convergence_curve"],
                improvement_over_baseline=data.get("improvement_over_baseline", 0.0),
                optimization_id=data["optimization_id"],
                timestamp=datetime.fromisoformat(data["timestamp"]),
            )

            logger.info(f"📂 优化结果已加载: {filepath}")
            return result

        except Exception as e:
            logger.error(f"❌ 结果加载失败: {e}")
            raise

    def generate_optimization_report(self, result: OptimizationResult) -> str:
        """
        生成优化报告

        Args:
            result: 优化结果

        Returns:
            str: 格式化的优化报告
        """
        try:
            report = f"""
# 超参数优化报告

## 基本信息
- **优化ID**: {result.optimization_id}
- **优化时间**: {result.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
- **优化策略**: {result.config.strategy.value if result.config else 'N/A'}
- **目标指标**: {result.config.objective_metric.value if result.config else 'N/A'}
- **总试验次数**: {result.n_trials_completed}
- **优化耗时**: {result.optimization_time_seconds:.1f} 秒

## 最佳结果
- **最佳得分**: {result.best_score:.4f}
- **最佳试验**: {result.best_trial_number}
- **相对基线改进**: {result.improvement_over_baseline:.2f}%

## 最佳参数
"""

            for param_name, param_value in result.best_params.items():
                report += f"- **{param_name}**: {param_value}\n"

            if result.final_backtest_result:
                br = result.final_backtest_result
                report += f"""

## 验证回测性能
- **总ROI**: {br.total_roi:.2f}%
- **夏普比率**: {br.sharpe_ratio:.2f}
- **最大回撤**: {br.max_drawdown:.2f}%
- **胜率**: {br.win_rate:.2%}
- **卡尔玛比率**: {br.calmar_ratio:.2f}
"""

            if result.parameter_importance:
                report += "\n## 参数重要性\n"
                # 按重要性排序
                sorted_importance = sorted(
                    result.parameter_importance.items(),
                    key=lambda x: x[1],
                    reverse=True,
                )
                for param, importance in sorted_importance[:10]:  # 只显示前10个
                    report += f"- **{param}**: {importance:.3f}\n"

            report += f"""
## 优化统计
- **收敛曲线最佳值**: {(max(result.convergence_curve) if result.convergence_curve else 'N/A'):.4f}
- **早期停止触发**: {'是' if len(result.trial_history) < result.config.n_trials else '否'}
"""

            return report

        except Exception as e:
            logger.error(f"❌ 报告生成失败: {e}")
            return f"报告生成失败: {str(e)}"


# 便捷函数
async def run_optimization(
    config: OptimizationConfig,
    save_results: bool = True,
    results_dir: str = "./optimization_results/",
) -> OptimizationResult:
    """
    运行完整的优化流程

    Args:
        config: 优化配置
        save_results: 是否保存结果
        results_dir: 结果保存目录

    Returns:
        OptimizationResult: 优化结果
    """
    tuner = HyperparameterTuner(config)
    await tuner.initialize()

    # 执行优化
    result = await tuner.optimize()

    # 保存结果
    if save_results:
        filepath = f"{results_dir}/optimization_{result.optimization_id}.json"
        tuner.save_results(result, filepath)

        # 生成并保存报告
        report = tuner.generate_optimization_report(result)
        report_path = f"{results_dir}/optimization_{result.optimization_id}_report.md"

        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)

        logger.info(f"📄 优化报告已保存: {report_path}")

    return result


# 示例配置
def create_default_optimization_config() -> OptimizationConfig:
    """创建默认优化配置"""
    return OptimizationConfig(
        strategy=OptimizationStrategy.BAYESIAN_OPTIMIZATION,
        objective_metric=ObjectiveMetric.BALANCED_OBJECTIVE,
        n_trials=50,
        timeout_seconds=1800,  # 30分钟
        early_stopping_patience=15,
        min_improvement=0.005,
        # 优化范围
        optimize_kelly_parameters=True,
        optimize_elo_parameters=True,
        optimize_poisson_parameters=False,  # 先关闭以减少复杂度
        optimize_model_weights=True,
        optimize_strategy_combination=True,
    )


if __name__ == "__main__":
    # 示例使用
    async def main():
        # 创建默认配置
        config = create_default_optimization_config()

        # 运行优化
        result = await run_optimization(config)

        # 打印结果摘要

    # 运行示例
    asyncio.run(main())
