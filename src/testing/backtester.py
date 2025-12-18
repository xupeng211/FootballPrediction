#!/usr/bin/env python3
"""
全量数据回测引擎 - 大规模历史数据分析系统

Sprint 5 核心组件之五

专为处理50GB+大规模足球历史数据设计的高性能回测系统：
- 流式数据处理架构
- 多线程并行计算
- 内存优化的数据管道
- 实时性能监控
- 可配置的策略测试

核心指标：
- Total ROI = (Total Profit / Total Stake) × 100%
- Max Drawdown = Peak - Trough / Peak
- Brier Score = Σ(forecast - outcome)² / N
- Sharpe Ratio = (Return - Risk Free) / Volatility

性能目标：
- 处理50GB数据 < 30分钟
- 内存使用 < 4GB
- 支持1000+策略并发测试

Author: Football Prediction Team
Version: 1.0.0
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple, Union, Callable, Iterator
from decimal import Decimal, ROUND_HALF_UP
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
import multiprocessing as mp
from dataclasses import dataclass, field
from pathlib import Path
import json
import pickle
import gc
import psutil
import time
from functools import partial

from ...constants import FOOTBALL, MATH, PROBABILITY, STATISTICAL
from ..features.elo_rating_system import EloRatingSystem
from ..features.poisson_features import PoissonFeatureCalculator
from ..features.odds_movement_features import OddsMovementAnalyzer
from ..strategy.kelly_criterion import KellyCriterion, KellyStrategy

logger = logging.getLogger(__name__)


@dataclass
class BacktestConfig:
    """回测配置"""
    # 数据配置
    data_path: str = "./data/historical/"           # 数据路径
    start_date: Optional[datetime] = None          # 开始日期
    end_date: Optional[datetime] = None            # 结束日期
    file_pattern: str = "*.parquet"                # 文件模式

    # 处理配置
    chunk_size: int = 10000                       # 数据块大小
    n_workers: int = mp.cpu_count() - 1           # 工作线程数
    memory_limit_gb: float = 4.0                  # 内存限制(GB)
    use_streaming: bool = True                     # 启用流式处理
    cache_features: bool = True                    # 缓存特征

    # 策略配置
    strategies: List[str] = field(default_factory=lambda: [
        "kelly_fractional",
        "elo_based",
        "poisson_based",
        "ensemble",
    ])
    initial_bankroll: float = 10000.0             # 初始资金
    min_odds: float = 1.1                         # 最小赔率
    max_odds: float = 10.0                        # 最大赔率
    min_edge_threshold: float = 0.05              # 最小优势阈值

    # 输出配置
    output_path: str = "./results/backtest/"      # 输出路径
    save_intermediate: bool = True                 # 保存中间结果
    detailed_logs: bool = False                    # 详细日志


@dataclass
class BacktestResult:
    """回测结果"""
    strategy_name: str
    total_bets: int
    winning_bets: int
    total_stake: float
    total_return: float
    total_profit: float
    roi: float
    max_drawdown: float
    brier_score: float
    sharpe_ratio: float
    win_rate: float
    avg_odds: float
    avg_stake: float
    max_consecutive_losses: int
    calmar_ratio: float  # 年化收益率/最大回撤
    sortino_ratio: float  # 下行风险调整收益
    var_95: float       # 95% VaR
    execution_time: float


@dataclass
class PerformanceMetrics:
    """性能指标"""
    start_time: float = 0.0
    end_time: float = 0.0
    peak_memory_mb: float = 0.0
    avg_memory_mb: float = 0.0
    processed_records: int = 0
    processing_speed_rps: float = 0.0
    cache_hit_rate: float = 0.0


class StreamingDataProcessor:
    """流式数据处理器"""

    def __init__(
        self,
        config: BacktestConfig,
        elo_system: EloRatingSystem,
        poisson_calculator: PoissonFeatureCalculator,
        odds_analyzer: OddsMovementAnalyzer,
    ):
        self.config = config
        self.elo_system = elo_system
        self.poisson_calculator = poisson_calculator
        self.odds_analyzer = odds_analyzer

        # 性能监控
        self.performance = PerformanceMetrics()
        self.memory_samples = []

        # 特征缓存
        self.feature_cache = {} if config.cache_features else None

        logger.info("流式数据处理器初始化完成")

    def process_file_stream(
        self,
        file_path: str
    ) -> Iterator[pd.DataFrame]:
        """
        流式处理文件

        Args:
            file_path: 文件路径

        Yields:
            pd.DataFrame: 数据块
        """
        try:
            # 根据文件扩展名选择读取方式
            if file_path.endswith('.parquet'):
                yield from self._process_parquet_stream(file_path)
            elif file_path.endswith('.csv'):
                yield from self._process_csv_stream(file_path)
            elif file_path.endswith('.json'):
                yield from self._process_json_stream(file_path)
            else:
                raise ValueError(f"不支持的文件格式: {file_path}")

        except Exception as e:
            logger.error(f"处理文件失败 {file_path}: {e}")
            raise

    def _process_parquet_stream(
        self,
        file_path: str
    ) -> Iterator[pd.DataFrame]:
        """流式处理Parquet文件"""
        try:
            # 使用pyarrow的流式读取
            import pyarrow.parquet as pq
            parquet_file = pq.ParquetFile(file_path)

            for batch in parquet_file.iter_batches(batch_size=self.config.chunk_size):
                df = batch.to_pandas()

                # 应用日期过滤
                if self.config.start_date or self.config.end_date:
                    df = self._filter_by_date(df)

                if not df.empty:
                    yield df

        except ImportError:
            # 回退到pandas读取
            logger.warning("pyarrow未安装，使用pandas读取（内存使用较高）")
            for chunk in pd.read_parquet(file_path, chunksize=self.config.chunk_size):
                if self.config.start_date or self.config.end_date:
                    chunk = self._filter_by_date(chunk)
                if not chunk.empty:
                    yield chunk

    def _process_csv_stream(
        self,
        file_path: str
    ) -> Iterator[pd.DataFrame]:
        """流式处理CSV文件"""
        for chunk in pd.read_csv(file_path, chunksize=self.config.chunk_size):
            if self.config.start_date or self.config.end_date:
                chunk = self._filter_by_date(chunk)
            if not chunk.empty:
                yield chunk

    def _process_json_stream(
        self,
        file_path: str
    ) -> Iterator[pd.DataFrame]:
        """流式处理JSON文件"""
        # JSON文件通常较小，一次性读取后分块
        df = pd.read_json(file_path)
        if self.config.start_date or self.config.end_date:
            df = self._filter_by_date(df)

        for i in range(0, len(df), self.config.chunk_size):
            yield df.iloc[i:i + self.config.chunk_size]

    def _filter_by_date(self, df: pd.DataFrame) -> pd.DataFrame:
        """按日期过滤数据"""
        date_col = 'match_date'
        if date_col not in df.columns:
            date_col = 'date'

        if date_col not in df.columns:
            return df  # 无日期列，返回全部数据

        # 转换日期格式
        df[date_col] = pd.to_datetime(df[date_col], errors='coerce')

        # 应用过滤
        if self.config.start_date:
            df = df[df[date_col] >= self.config.start_date]

        if self.config.end_date:
            df = df[df[date_col] <= self.config.end_date]

        return df

    def process_chunk(
        self,
        chunk: pd.DataFrame,
        strategy_func: Callable
    ) -> List[Dict[str, Any]]:
        """
        处理数据块

        Args:
            chunk: 数据块
            strategy_func: 策略函数

        Returns:
            List[Dict[str, Any]]: 处理结果
        """
        # 更新性能统计
        self.performance.processed_records += len(chunk)
        self._update_memory_usage()

        results = []

        try:
            # 预处理数据
            processed_chunk = self._preprocess_chunk(chunk)

            # 处理每一行
            for _, row in processed_chunk.iterrows():
                try:
                    result = self._process_single_match(row, strategy_func)
                    if result:
                        results.append(result)
                except Exception as e:
                    logger.warning(f"处理单场比赛失败: {e}")
                    continue

            # 垃圾回收
            del processed_chunk
            gc.collect()

        except Exception as e:
            logger.error(f"处理数据块失败: {e}")

        return results

    def _preprocess_chunk(self, chunk: pd.DataFrame) -> pd.DataFrame:
        """预处理数据块"""
        # 数据清洗
        chunk = chunk.copy()

        # 处理缺失值
        numeric_columns = chunk.select_dtypes(include=[np.number]).columns
        chunk[numeric_columns] = chunk[numeric_columns].fillna(0)

        # 数据类型转换
        if 'match_date' in chunk.columns:
            chunk['match_date'] = pd.to_datetime(chunk['match_date'])

        return chunk

    def _process_single_match(
        self,
        row: pd.Series,
        strategy_func: Callable
    ) -> Optional[Dict[str, Any]]:
        """处理单场比赛"""
        try:
            # 提取基础信息
            match_info = {
                'match_id': row.get('match_id', f"{row.get('home_team')}_{row.get('away_team')}_{row.get('match_date')}"),
                'home_team': row.get('home_team'),
                'away_team': row.get('away_team'),
                'home_goals': row.get('home_goals', 0),
                'away_goals': row.get('away_goals', 0),
                'match_date': row.get('match_date'),
                'home_odds': row.get('home_odds'),
                'draw_odds': row.get('draw_odds'),
                'away_odds': row.get('away_odds'),
            }

            # 验证数据完整性
            if not all([match_info['home_team'], match_info['away_team']]):
                return None

            # 应用策略
            strategy_result = strategy_func(match_info, self)

            if strategy_result:
                return {
                    **match_info,
                    **strategy_result,
                }

            return None

        except Exception as e:
            logger.warning(f"处理比赛失败: {e}")
            return None

    def _update_memory_usage(self):
        """更新内存使用统计"""
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024

        self.memory_samples.append(memory_mb)
        if len(self.memory_samples) > 100:
            self.memory_samples.pop(0)

        self.performance.peak_memory_mb = max(self.performance.peak_memory_mb, memory_mb)
        self.performance.avg_memory_mb = np.mean(self.memory_samples)


class BacktestEngine:
    """
    回测引擎主类

    主要功能：
    1. 大规模数据处理
    2. 多策略并行测试
    3. 性能监控和优化
    4. 结果分析和报告
    """

    def __init__(self, config: BacktestConfig):
        """
        初始化回测引擎

        Args:
            config: 回测配置
        """
        self.config = config

        # 初始化子系统
        self.elo_system = EloRatingSystem()
        self.poisson_calculator = PoissonFeatureCalculator()
        self.odds_analyzer = OddsMovementAnalyzer()

        # 流式处理器
        self.stream_processor = StreamingDataProcessor(
            config, self.elo_system, self.poisson_calculator, self.odds_analyzer
        )

        # 策略映射
        self.strategies = {
            "kelly_fractional": self._kelly_fractional_strategy,
            "elo_based": self._elo_based_strategy,
            "poisson_based": self._poisson_based_strategy,
            "ensemble": self._ensemble_strategy,
        }

        # 结果存储
        self.results: Dict[str, BacktestResult] = {}
        self.detailed_results: Dict[str, List[Dict[str, Any]]] = {}

        logger.info(f"回测引擎初始化完成: {config.n_workers}个工作线程")

    def run_backtest(self) -> Dict[str, BacktestResult]:
        """
        运行回测

        Returns:
            Dict[str, BacktestResult]: 回测结果
        """
        logger.info("开始回测...")

        # 创建输出目录
        Path(self.config.output_path).mkdir(parents=True, exist_ok=True)

        # 获取数据文件列表
        data_files = self._get_data_files()
        logger.info(f"找到 {len(data_files)} 个数据文件")

        # 并行处理策略
        if len(self.config.strategies) > 1:
            results = self._run_strategies_parallel(data_files)
        else:
            results = self._run_single_strategy(data_files)

        # 生成报告
        self._generate_report(results)

        # 保存结果
        self._save_results(results)

        logger.info("回测完成")
        return results

    def _get_data_files(self) -> List[str]:
        """获取数据文件列表"""
        data_path = Path(self.config.data_path)
        files = list(data_path.glob(self.config.file_pattern))

        # 按修改时间排序
        files.sort(key=lambda x: x.stat().st_mtime, reverse=True)

        return [str(f) for f in files]

    def _run_strategies_parallel(
        self,
        data_files: List[str]
    ) -> Dict[str, BacktestResult]:
        """并行运行多个策略"""
        results = {}

        with ThreadPoolExecutor(max_workers=min(len(self.config.strategies), 4)) as executor:
            # 提交所有策略任务
            future_to_strategy = {
                executor.submit(self._run_single_strategy, data_files, strategy): strategy
                for strategy in self.config.strategies
            }

            # 收集结果
            for future in as_completed(future_to_strategy):
                strategy = future_to_strategy[future]
                try:
                    strategy_results = future.result()
                    results.update(strategy_results)
                except Exception as e:
                    logger.error(f"策略 {strategy} 执行失败: {e}")

        return results

    def _run_single_strategy(
        self,
        data_files: List[str],
        strategy_name: Optional[str] = None
    ) -> Dict[str, BacktestResult]:
        """运行单个策略"""
        strategies_to_run = [strategy_name] if strategy_name else self.config.strategies
        results = {}

        for strategy in strategies_to_run:
            if strategy not in self.strategies:
                logger.warning(f"未知策略: {strategy}")
                continue

            logger.info(f"开始执行策略: {strategy}")

            # 获取策略函数
            strategy_func = self.strategies[strategy]

            # 初始化结果收集
            detailed_results = []

            # 重置子系统状态
            self._reset_subsystems()

            # 性能监控
            start_time = time.time()

            try:
                # 流式处理数据文件
                for file_path in data_files:

                    # 流式读取和处理
                    for chunk in self.stream_processor.process_file_stream(file_path):
                        chunk_results = self.stream_processor.process_chunk(
                            chunk, strategy_func
                        )
                        detailed_results.extend(chunk_results)

                        # 内存检查
                        if self._should_take_memory_break():
                            self._memory_break()

                # 计算回测结果
                if detailed_results:
                    backtest_result = self._calculate_backtest_metrics(
                        strategy, detailed_results, time.time() - start_time
                    )
                    results[strategy] = backtest_result
                    self.detailed_results[strategy] = detailed_results
                else:
                    logger.warning(f"策略 {strategy} 无有效结果")

            except Exception as e:
                logger.error(f"策略 {strategy} 执行失败: {e}")

        return results

    def _kelly_fractional_strategy(
        self,
        match_info: Dict[str, Any],
        processor: StreamingDataProcessor
    ) -> Optional[Dict[str, Any]]:
        """凯利分数策略"""
        try:
            # 检查赔率
            if not all([
                match_info.get('home_odds'),
                match_info.get('draw_odds'),
                match_info.get('away_odds')
            ]):
                return None

            # 初始化凯利系统
            kelly = KellyCriterion(
                initial_bankroll=self.config.initial_bankroll,
                kelly_strategy=KellyStrategy.FRACTIONAL_KELLY,
                fraction_multiplier=Decimal("0.25"),
                min_edge_threshold=Decimal(str(self.config.min_edge_threshold))
            )

            # 获取预测概率（这里简化处理，实际应该从模型获取）
            # 使用赔率隐含概率作为基准
            outcomes = {
                "home": {
                    "odds": match_info["home_odds"],
                    "probability": 1.0 / match_info["home_odds"],
                },
                "draw": {
                    "odds": match_info["draw_odds"],
                    "probability": 1.0 / match_info["draw_odds"],
                },
                "away": {
                    "odds": match_info["away_odds"],
                    "probability": 1.0 / match_info["away_odds"],
                },
            }

            # 添加一些随机调整来模拟预测优势
            for outcome in outcomes.values():
                outcome["probability"] *= np.random.uniform(0.95, 1.05)
                outcome["probability"] = min(0.99, max(0.01, outcome["probability"]))

            # 生成投注建议
            recommendations = kelly.generate_bet_recommendation(outcomes)

            if recommendations:
                rec = recommendations[0]  # 取第一个建议

                # 结算投注
                result_profit = 0
                if rec.outcome == "home" and match_info["home_goals"] > match_info["away_goals"]:
                    result_profit = float(rec.stake_amount * rec.odds - rec.stake_amount)
                elif rec.outcome == "draw" and match_info["home_goals"] == match_info["away_goals"]:
                    result_profit = float(rec.stake_amount * rec.odds - rec.stake_amount)
                elif rec.outcome == "away" and match_info["home_goals"] < match_info["away_goals"]:
                    result_profit = float(rec.stake_amount * rec.odds - rec.stake_amount)
                else:
                    result_profit = -float(rec.stake_amount)

                return {
                    "strategy": "kelly_fractional",
                    "outcome": rec.outcome,
                    "odds": float(rec.odds),
                    "predicted_prob": float(rec.predicted_prob),
                    "stake": float(rec.stake_amount),
                    "profit": result_profit,
                    "kelly_fraction": float(rec.kelly_fraction),
                    "expected_value": float(rec.expected_value),
                }

            return None

        except Exception as e:
            logger.warning(f"凯利策略执行失败: {e}")
            return None

    def _elo_based_strategy(
        self,
        match_info: Dict[str, Any],
        processor: StreamingDataProcessor
    ) -> Optional[Dict[str, Any]]:
        """基于Elo的策略"""
        try:
            # 更新Elo评分
            elo_result = processor.elo_system.update_ratings(
                home_team_id=match_info["home_team"],
                away_team_id=match_info["away_team"],
                home_goals=match_info["home_goals"],
                away_goals=match_info["away_goals"],
                match_date=match_info["match_date"]
            )

            # 预测下一场比赛（简化处理）
            prediction = processor.elo_system.predict_match_probabilities(
                home_team_id=match_info["home_team"],
                away_team_id=match_info["away_team"]
            )

            # 基于Elo预测的投注决策
            home_prob = prediction["probabilities"]["home_win"]
            away_prob = prediction["probabilities"]["away_win"]

            # 选择最有价值的结果
            best_outcome = max(
                [("home", home_prob, match_info["home_odds"]),
                 ("away", away_prob, match_info["away_odds"])],
                key=lambda x: x[1] * float(x[2]) - 1
            )

            outcome, prob, odds = best_outcome

            # 简单的投注决策
            edge = prob * float(odds) - 1
            if edge > self.config.min_edge_threshold:
                stake = self.config.initial_bankroll * 0.02  # 2%固定投注

                # 结算
                result_profit = 0
                if outcome == "home" and match_info["home_goals"] > match_info["away_goals"]:
                    result_profit = stake * float(odds) - stake
                elif outcome == "away" and match_info["home_goals"] < match_info["away_goals"]:
                    result_profit = stake * float(odds) - stake
                else:
                    result_profit = -stake

                return {
                    "strategy": "elo_based",
                    "outcome": outcome,
                    "odds": float(odds),
                    "predicted_prob": float(prob),
                    "stake": stake,
                    "profit": result_profit,
                    "elo_rating_diff": elo_result["ratings"]["home"]["after"] - elo_result["ratings"]["away"]["after"],
                    "edge": edge,
                }

            return None

        except Exception as e:
            logger.warning(f"Elo策略执行失败: {e}")
            return None

    def _poisson_based_strategy(
        self,
        match_info: Dict[str, Any],
        processor: StreamingDataProcessor
    ) -> Optional[Dict[str, Any]]:
        """基于泊松分布的策略"""
        try:
            # 计算泊松概率
            probabilities = processor.poisson_calculator.calculate_match_probabilities(
                home_team_id=match_info["home_team"],
                away_team_id=match_info["away_team"]
            )

            # 基于泊松预测的投注决策
            home_prob = probabilities["probabilities"]["home_win"]
            draw_prob = probabilities["probabilities"]["draw"]
            away_prob = probabilities["probabilities"]["away_win"]

            # 选择最有价值的结果
            outcomes = [
                ("home", home_prob, match_info["home_odds"]),
                ("draw", draw_prob, match_info["draw_odds"]),
                ("away", away_prob, match_info["away_odds"])
            ]

            best_outcome = max(outcomes, key=lambda x: x[1] * float(x[2]) - 1)
            outcome, prob, odds = best_outcome

            # 投注决策
            edge = prob * float(odds) - 1
            if edge > self.config.min_edge_threshold:
                stake = self.config.initial_bankroll * 0.03  # 3%固定投注

                # 结算
                result_profit = 0
                if outcome == "home" and match_info["home_goals"] > match_info["away_goals"]:
                    result_profit = stake * float(odds) - stake
                elif outcome == "draw" and match_info["home_goals"] == match_info["away_goals"]:
                    result_profit = stake * float(odds) - stake
                elif outcome == "away" and match_info["home_goals"] < match_info["away_goals"]:
                    result_profit = stake * float(odds) - stake
                else:
                    result_profit = -stake

                return {
                    "strategy": "poisson_based",
                    "outcome": outcome,
                    "odds": float(odds),
                    "predicted_prob": float(prob),
                    "stake": stake,
                    "profit": result_profit,
                    "expected_home_goals": probabilities["expected_goals"]["home"],
                    "expected_away_goals": probabilities["expected_goals"]["away"],
                    "edge": edge,
                }

            return None

        except Exception as e:
            logger.warning(f"泊松策略执行失败: {e}")
            return None

    def _ensemble_strategy(
        self,
        match_info: Dict[str, Any],
        processor: StreamingDataProcessor
    ) -> Optional[Dict[str, Any]]:
        """集成策略"""
        try:
            # 获取各策略的预测
            strategies = ["kelly_fractional", "elo_based", "poisson_based"]
            predictions = []

            for strategy_name in strategies:
                strategy_func = self.strategies[strategy_name]
                prediction = strategy_func(match_info, processor)
                if prediction:
                    predictions.append(prediction)

            if not predictions:
                return None

            # 简单集成：平均投注
            avg_stake = np.mean([p["stake"] for p in predictions])
            avg_profit = np.mean([p["profit"] for p in predictions])

            # 选择最优结果
            best_prediction = max(predictions, key=lambda x: x["profit"])

            return {
                "strategy": "ensemble",
                "outcome": best_prediction["outcome"],
                "odds": best_prediction["odds"],
                "predicted_prob": best_prediction["predicted_prob"],
                "stake": avg_stake,
                "profit": avg_profit,
                "ensemble_size": len(predictions),
                "contributing_strategies": [p["strategy"] for p in predictions],
            }

        except Exception as e:
            logger.warning(f"集成策略执行失败: {e}")
            return None

    def _calculate_backtest_metrics(
        self,
        strategy_name: str,
        detailed_results: List[Dict[str, Any]],
        execution_time: float
    ) -> BacktestResult:
        """计算回测指标"""
        if not detailed_results:
            return BacktestResult(
                strategy_name=strategy_name,
                total_bets=0, winning_bets=0, total_stake=0, total_return=0,
                total_profit=0, roi=0, max_drawdown=0, brier_score=0,
                sharpe_ratio=0, win_rate=0, avg_odds=0, avg_stake=0,
                max_consecutive_losses=0, calmar_ratio=0, sortino_ratio=0,
                var_95=0, execution_time=execution_time
            )

        # 提取数据
        profits = [r["profit"] for r in detailed_results]
        stakes = [r["stake"] for r in detailed_results]
        odds = [r["odds"] for r in detailed_results]
        predicted_probs = [r["predicted_prob"] for r in detailed_results]

        # 基础指标
        total_bets = len(detailed_results)
        winning_bets = sum(1 for p in profits if p > 0)
        total_stake = sum(stakes)
        total_return = sum(s + p for s, p in zip(stakes, profits))
        total_profit = sum(profits)

        # 衍生指标
        roi = (total_profit / total_stake * 100) if total_stake > 0 else 0
        win_rate = (winning_bets / total_bets) if total_bets > 0 else 0
        avg_odds = np.mean(odds) if odds else 0
        avg_stake = np.mean(stakes) if stakes else 0

        # 回撤分析
        max_drawdown = self._calculate_max_drawdown(profits)

        # Brier Score
        brier_score = self._calculate_brier_score(predicted_probs, profits)

        # 风险指标
        returns_array = np.array(profits) / np.array(stakes)
        sharpe_ratio = self._calculate_sharpe_ratio(returns_array)
        sortino_ratio = self._calculate_sortino_ratio(returns_array)
        var_95 = np.percentile(returns_array, 5) if len(returns_array) > 0 else 0

        # Calmar Ratio
        annual_return = roi * 365  # 简化年化
        calmar_ratio = annual_return / max_drawdown if max_drawdown != 0 else 0

        # 最大连续亏损
        max_consecutive_losses = self._calculate_max_consecutive_losses(profits)

        return BacktestResult(
            strategy_name=strategy_name,
            total_bets=total_bets,
            winning_bets=winning_bets,
            total_stake=total_stake,
            total_return=total_return,
            total_profit=total_profit,
            roi=roi,
            max_drawdown=max_drawdown,
            brier_score=brier_score,
            sharpe_ratio=sharpe_ratio,
            win_rate=win_rate,
            avg_odds=avg_odds,
            avg_stake=avg_stake,
            max_consecutive_losses=max_consecutive_losses,
            calmar_ratio=calmar_ratio,
            sortino_ratio=sortino_ratio,
            var_95=var_95,
            execution_time=execution_time
        )

    def _calculate_max_drawdown(self, profits: List[float]) -> float:
        """计算最大回撤"""
        if not profits:
            return 0

        cumulative = np.cumsum(profits)
        peak = cumulative[0]
        max_dd = 0

        for value in cumulative:
            if value > peak:
                peak = value
            dd = (peak - value) / peak if peak != 0 else 0
            max_dd = max(max_dd, dd)

        return max_dd * 100  # 转换为百分比

    def _calculate_brier_score(
        self,
        predicted_probs: List[float],
        profits: List[float]
    ) -> float:
        """计算Brier Score"""
        if not predicted_probs or not profits:
            return 0

        # 将盈亏转换为二分类结果
        outcomes = [1 if p > 0 else 0 for p in profits]

        # 计算Brier Score
        brier = np.mean([(p - o) ** 2 for p, o in zip(predicted_probs, outcomes)])
        return brier

    def _calculate_sharpe_ratio(self, returns: np.ndarray) -> float:
        """计算夏普比率"""
        if len(returns) < 2:
            return 0

        mean_return = np.mean(returns)
        std_return = np.std(returns)

        return mean_return / std_return if std_return != 0 else 0

    def _calculate_sortino_ratio(self, returns: np.ndarray) -> float:
        """计算Sortino比率"""
        if len(returns) < 2:
            return 0

        mean_return = np.mean(returns)
        downside_returns = returns[returns < 0]
        downside_std = np.std(downside_returns) if len(downside_returns) > 0 else 0.0001

        return mean_return / downside_std

    def _calculate_max_consecutive_losses(self, profits: List[float]) -> int:
        """计算最大连续亏损"""
        max_consecutive = 0
        current_consecutive = 0

        for profit in profits:
            if profit < 0:
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 0

        return max_consecutive

    def _reset_subsystems(self):
        """重置子系统状态"""
        # 重新初始化子系统以确保每个策略的独立性
        self.elo_system = EloRatingSystem()
        self.poisson_calculator = PoissonFeatureCalculator()
        self.odds_analyzer = OddsMovementAnalyzer()
        self.stream_processor = StreamingDataProcessor(
            self.config, self.elo_system, self.poisson_calculator, self.odds_analyzer
        )

    def _should_take_memory_break(self) -> bool:
        """检查是否需要内存休息"""
        if psutil.virtual_memory().percent > 80:
            return True
        return False

    def _memory_break(self):
        """内存休息：垃圾回收"""
        logger.info("执行内存清理...")
        gc.collect()
        time.sleep(1)  # 短暂休息

    def _generate_report(self, results: Dict[str, BacktestResult]):
        """生成报告"""
        report_path = Path(self.config.output_path) / "backtest_report.md"

        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("# 足球预测回测报告\n\n")
            f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"回测期间: {self.config.start_date} 至 {self.config.end_date}\n")
            f.write(f"处理策略: {', '.join(self.config.strategies)}\n\n")

            # 策略对比表
            f.write("## 策略性能对比\n\n")
            f.write("| 策略 | 投注次数 | 胜率 | ROI(%) | 最大回撤(%) | 夏普比率 | Brier Score |\n")
            f.write("|------|----------|------|--------|-------------|----------|-------------|\n")

            for strategy, result in results.items():
                f.write(f"| {strategy} | {result.total_bets} | {result.win_rate:.1%} | "
                       f"{result.roi:.2f} | {result.max_drawdown:.2f} | {result.sharpe_ratio:.3f} | "
                       f"{result.brier_score:.4f} |\n")

            # 详细分析
            f.write("\n## 详细分析\n\n")
            for strategy, result in results.items():
                f.write(f"### {strategy}\n\n")
                f.write(f"- **总投注**: {result.total_bets} 次\n")
                f.write(f"- **胜场**: {result.winning_bets} 次\n")
                f.write(f"- **胜率**: {result.win_rate:.1%}\n")
                f.write(f"- **总投注额**: {result.total_stake:.2f}\n")
                f.write(f"- **总盈亏**: {result.total_profit:.2f}\n")
                f.write(f"- **ROI**: {result.roi:.2f}%\n")
                f.write(f"- **最大回撤**: {result.max_drawdown:.2f}%\n")
                f.write(f"- **夏普比率**: {result.sharpe_ratio:.3f}\n")
                f.write(f"- **Sortino比率**: {result.sortino_ratio:.3f}\n")
                f.write(f"- **Calmar比率**: {result.calmar_ratio:.3f}\n")
                f.write(f"- **95% VaR**: {result.var_95:.3f}\n")
                f.write(f"- **平均赔率**: {result.avg_odds:.2f}\n")
                f.write(f"- **平均投注**: {result.avg_stake:.2f}\n")
                f.write(f"- **最大连续亏损**: {result.max_consecutive_losses} 次\n")
                f.write(f"- **执行时间**: {result.execution_time:.2f} 秒\n\n")

        logger.info(f"报告已生成: {report_path}")

    def _save_results(self, results: Dict[str, BacktestResult]):
        """保存结果"""
        # 保存简要结果
        summary_path = Path(self.config.output_path) / "results_summary.json"
        summary_data = {
            strategy: {
                "total_bets": result.total_bets,
                "win_rate": result.win_rate,
                "roi": result.roi,
                "max_drawdown": result.max_drawdown,
                "sharpe_ratio": result.sharpe_ratio,
                "brier_score": result.brier_score,
            } for strategy, result in results.items()
        }

        with open(summary_path, 'w') as f:
            json.dump(summary_data, f, indent=2, ensure_ascii=False)

        # 保存详细结果（如果启用）
        if self.config.save_intermediate:
            detailed_path = Path(self.config.output_path) / "detailed_results.json"
            with open(detailed_path, 'w') as f:
                json.dump(self.detailed_results, f, indent=2, ensure_ascii=False)

        logger.info(f"结果已保存到: {self.config.output_path}")

    def get_performance_metrics(self) -> Dict[str, Any]:
        """获取性能指标"""
        return {
            "streaming_processor": {
                "processed_records": self.stream_processor.performance.processed_records,
                "peak_memory_mb": self.stream_processor.performance.peak_memory_mb,
                "avg_memory_mb": self.stream_processor.performance.avg_memory_mb,
                "processing_speed_rps": self.stream_processor.performance.processing_speed_rps,
            },
            "subsystems": {
                "elo_system": self.elo_system.get_system_stats(),
                "poisson_calculator": self.poisson_calculator.get_system_stats(),
                "odds_analyzer": self.odds_analyzer.get_system_stats(),
            },
        }


def run_backtest(
    data_path: str,
    strategies: Optional[List[str]] = None,
    output_path: str = "./results/backtest/",
    **kwargs
) -> Dict[str, BacktestResult]:
    """
    便捷的回测运行函数

    Args:
        data_path: 数据路径
        strategies: 策略列表
        output_path: 输出路径
        **kwargs: 其他配置参数

    Returns:
        Dict[str, BacktestResult]: 回测结果
    """
    config = BacktestConfig(
        data_path=data_path,
        strategies=strategies or ["kelly_fractional", "elo_based", "poisson_based", "ensemble"],
        output_path=output_path,
        **kwargs
    )

    engine = BacktestEngine(config)
    return engine.run_backtest()