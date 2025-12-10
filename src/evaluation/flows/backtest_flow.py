"""
Football Prediction Model Backtest Flow

模型回测流程，使用Prefect编排完整的投注模拟和收益分析流程。
包含赔率数据加载、投注策略执行、收益计算、风险分析等步骤。

Author: Football Prediction Team
Version: 1.0.0
"""

import json
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Optional, Union, Any

try:
    from prefect import flow, task, get_run_logger

    HAS_PREFECT = True
except ImportError:
    HAS_PREFECT = False

    # 创建占位符装饰器
    def flow(func):
        return func

    def task(func):
        return func

    def get_run_logger():
        import logging

        return logging.getLogger(__name__)


from src.evaluation.backtest import (
    Backtester,
    BacktestResult,
    FlatStakingStrategy,
    PercentageStakingStrategy,
    KellyStakingStrategy,
    ValueBettingStrategy,
)
from src.evaluation.visualizer import EvaluationVisualizer
from src.evaluation.report_builder import ReportBuilder

logger = get_run_logger()


@task
def load_odds_data_task(
    odds_path: Union[str, Path], odds_format: str = "csv"
) -> pd.DataFrame:
    """
    加载赔率数据

    Args:
        odds_path: 赔率数据文件路径
        odds_format: 数据格式 ("csv", "json", "parquet")

    Returns:
        赔率数据DataFrame
    """
    odds_path = Path(odds_path)

    if not odds_path.exists():
        raise FileNotFoundError(f"Odds file not found: {odds_path}")

    try:
        if odds_format == "csv":
            odds_df = pd.read_csv(odds_path)
        elif odds_format == "json":
            odds_df = pd.read_json(odds_path)
        elif odds_format == "parquet":
            odds_df = pd.read_parquet(odds_path)
        else:
            raise ValueError(f"Unsupported odds format: {odds_format}")

        logger.info(f"Odds data loaded: {odds_path} ({len(odds_df)} matches)")
        return odds_df

    except Exception as e:
        logger.error(f"Error loading odds data: {e}")
        raise


@task
def load_predictions_task(
    predictions_path: Union[str, Path], predictions_format: str = "csv"
) -> pd.DataFrame:
    """
    加载预测数据

    Args:
        predictions_path: 预测数据文件路径
        predictions_format: 数据格式 ("csv", "json", "parquet")

    Returns:
        预测数据DataFrame
    """
    predictions_path = Path(predictions_path)

    if not predictions_path.exists():
        raise FileNotFoundError(f"Predictions file not found: {predictions_path}")

    try:
        if predictions_format == "csv":
            predictions_df = pd.read_csv(predictions_path)
        elif predictions_format == "json":
            predictions_df = pd.read_json(predictions_path)
        elif predictions_format == "parquet":
            predictions_df = pd.read_parquet(predictions_path)
        else:
            raise ValueError(f"Unsupported predictions format: {predictions_format}")

        logger.info(
            f"Predictions data loaded: {predictions_path} ({len(predictions_df)} matches)"
        )
        return predictions_df

    except Exception as e:
        logger.error(f"Error loading predictions data: {e}")
        raise


@task
def prepare_backtest_data_task(
    predictions_df: pd.DataFrame,
    odds_df: pd.DataFrame,
    match_id_column: str = "match_id",
) -> tuple:
    """
    准备回测数据

    Args:
        predictions_df: 预测数据
        odds_df: 赔率数据
        match_id_column: 比赛ID列名

    Returns:
        (merged_predictions, merged_odds) 元组
    """
    try:
        # 确保都有匹配ID列
        if match_id_column not in predictions_df.columns:
            raise ValueError(
                f"Match ID column '{match_id_column}' not found in predictions"
            )
        if match_id_column not in odds_df.columns:
            raise ValueError(f"Match ID column '{match_id_column}' not found in odds")

        # 设置索引
        predictions_df = predictions_df.set_index(match_id_column)
        odds_df = odds_df.set_index(match_id_column)

        # 找到共同的比赛
        common_matches = predictions_df.index.intersection(odds_df.index)
        logger.info(f"Found {len(common_matches)} common matches for backtesting")

        if len(common_matches) == 0:
            raise ValueError(
                "No common matches found between predictions and odds data"
            )

        # 过滤数据
        filtered_predictions = predictions_df.loc[common_matches]
        filtered_odds = odds_df.loc[common_matches]

        return filtered_predictions, filtered_odds

    except Exception as e:
        logger.error(f"Error preparing backtest data: {e}")
        raise


@task
def validate_data_quality_task(
    predictions_df: pd.DataFrame, odds_df: pd.DataFrame
) -> dict[str, Any]:
    """
    验证回测数据质量

    Args:
        predictions_df: 预测数据
        odds_df: 赔率数据

    Returns:
        数据质量报告
    """
    quality_report = {
        "total_matches": len(predictions_df),
        "validation_passed": True,
        "issues": [],
        "statistics": {},
    }

    try:
        # 检查概率列
        prob_columns = [col for col in predictions_df.columns if "prob" in col.lower()]
        if len(prob_columns) < 3:
            quality_report["issues"].append(
                "Insufficient probability columns (need at least 3)"
            )
            quality_report["validation_passed"] = False

        # 检查概率和为1
        for idx, row in predictions_df[prob_columns].iterrows():
            prob_sum = row.sum()
            if abs(prob_sum - 1.0) > 0.1:  # 允许10%的误差
                quality_report["issues"].append(
                    f"Probability sum not close to 1.0: {prob_sum:.3f} at match {idx}"
                )
                break

        # 检查赔率列
        odds_columns = [col for col in odds_df.columns if "odds" in col.lower()]
        if len(odds_columns) < 3:
            quality_report["issues"].append(
                "Insufficient odds columns (need at least 3)"
            )
            quality_report["validation_passed"] = False

        # 检查赔率合理性
        for col in odds_columns:
            if col in odds_df.columns:
                min_odds = odds_df[col].min()
                max_odds = odds_df[col].max()
                avg_odds = odds_df[col].mean()

                quality_report["statistics"][f"{col}_min"] = min_odds
                quality_report["statistics"][f"{col}_max"] = max_odds
                quality_report["statistics"][f"{col}_avg"] = avg_odds

                if min_odds <= 1.0:
                    quality_report["issues"].append(f"Odds <= 1.0 found in {col}")

                if max_odds > 1000:
                    quality_report["issues"].append(
                        f"Extremely high odds found in {col}"
                    )

        # 检查实际结果（如果有）
        result_columns = [
            col
            for col in predictions_df.columns
            if "result" in col.lower() or "target" in col.lower()
        ]
        if result_columns:
            quality_report["has_actual_results"] = True
            quality_report["result_column"] = result_columns[0]
        else:
            quality_report["has_actual_results"] = False
            quality_report["issues"].append(
                "No actual results found - backtesting will be simulated"
            )

        logger.info(
            f"Data validation completed. Issues found: {len(quality_report['issues'])}"
        )
        return quality_report

    except Exception as e:
        logger.error(f"Error during data validation: {e}")
        quality_report["validation_passed"] = False
        quality_report["issues"].append(f"Validation error: {str(e)}")
        return quality_report


@task
def create_staking_strategy_task(
    strategy_type: str, strategy_params: Optional[dict[str, Any]] = None
) -> Any:
    """
    创建投注策略

    Args:
        strategy_type: 策略类型 ("flat", "percentage", "kelly", "value")
        strategy_params: 策略参数

    Returns:
        投注策略对象
    """
    if strategy_params is None:
        strategy_params = {}

    try:
        if strategy_type == "flat":
            stake_amount = strategy_params.get("stake_amount", 10.0)
            strategy = FlatStakingStrategy(stake_amount=stake_amount)

        elif strategy_type == "percentage":
            percentage = strategy_params.get("percentage", 0.01)
            strategy = PercentageStakingStrategy(percentage=percentage)

        elif strategy_type == "kelly":
            kelly_fraction = strategy_params.get("kelly_fraction", 0.25)
            min_stake = strategy_params.get("min_stake", 1.0)
            max_stake_percentage = strategy_params.get("max_stake_percentage", 0.05)
            strategy = KellyStakingStrategy(
                kelly_fraction=kelly_fraction,
                min_stake=min_stake,
                max_stake_percentage=max_stake_percentage,
            )

        elif strategy_type == "value":
            min_ev_threshold = strategy_params.get("min_ev_threshold", 0.1)
            base_stake = strategy_params.get("base_stake", 10.0)
            max_stake_percentage = strategy_params.get("max_stake_percentage", 0.05)
            strategy = ValueBettingStrategy(
                min_ev_threshold=min_ev_threshold,
                base_stake=base_stake,
                max_stake_percentage=max_stake_percentage,
            )

        else:
            raise ValueError(f"Unknown staking strategy: {strategy_type}")

        logger.info(
            f"Created {strategy_type} staking strategy with params: {strategy_params}"
        )
        return strategy

    except Exception as e:
        logger.error(f"Error creating staking strategy: {e}")
        raise


@task
def run_backtest_task(
    predictions_df: pd.DataFrame,
    odds_df: pd.DataFrame,
    staking_strategy: Any,
    initial_bankroll: float = 1000.0,
    backtest_params: Optional[dict[str, Any]] = None,
) -> BacktestResult:
    """
    运行回测模拟

    Args:
        predictions_df: 预测数据
        odds_df: 赔率数据
        staking_strategy: 投注策略
        initial_bankroll: 初始资金
        backtest_params: 回测参数

    Returns:
        回测结果
    """
    if backtest_params is None:
        backtest_params = {}

    try:
        # 创建回测器
        backtester = Backtester(initial_bankroll=initial_bankroll)

        # 运行回测
        result = backtester.simulate(
            predictions=predictions_df,
            odds=odds_df,
            stake_strategy=staking_strategy,
            **backtest_params,
        )

        logger.info(
            f"Backtest completed: {result.total_bets} bets, ROI: {result.roi:.2f}%"
        )
        return result

    except Exception as e:
        logger.error(f"Error running backtest: {e}")
        raise


@task
def analyze_backtest_performance_task(
    backtest_result: BacktestResult,
) -> dict[str, Any]:
    """
    分析回测性能

    Args:
        backtest_result: 回测结果

    Returns:
        性能分析报告
    """
    try:
        analysis = {
            "summary": {
                "total_bets": backtest_result.total_bets,
                "win_rate": backtest_result.win_rate,
                "roi": backtest_result.roi,
                "net_profit": backtest_result.net_profit,
                "max_drawdown": backtest_result.max_drawdown,
                "sharpe_ratio": backtest_result.sharpe_ratio,
            },
            "performance_rating": "unknown",
            "risk_assessment": "unknown",
            "recommendations": [],
        }

        # 性能评级
        roi = backtest_result.roi
        if roi > 20:
            analysis["performance_rating"] = "excellent"
        elif roi > 10:
            analysis["performance_rating"] = "good"
        elif roi > 0:
            analysis["performance_rating"] = "acceptable"
        else:
            analysis["performance_rating"] = "poor"

        # 风险评估
        max_dd = backtest_result.max_drawdown_percentage
        if max_dd < 10:
            analysis["risk_assessment"] = "low"
        elif max_dd < 25:
            analysis["risk_assessment"] = "moderate"
        else:
            analysis["risk_assessment"] = "high"

        # 生成建议
        if backtest_result.roi < 0:
            analysis["recommendations"].append(
                "Consider adjusting your betting strategy or model"
            )

        if backtest_result.max_drawdown_percentage > 20:
            analysis["recommendations"].append("Implement stricter risk management")

        if backtest_result.sharpe_ratio < 0.5:
            analysis["recommendations"].append("Improve risk-adjusted returns")

        if backtest_result.win_rate < 0.4:
            analysis["recommendations"].append("Focus on improving prediction accuracy")

        logger.info(
            f"Backtest performance analysis: {analysis['performance_rating']} performance, {analysis['risk_assessment']} risk"
        )
        return analysis

    except Exception as e:
        logger.error(f"Error analyzing backtest performance: {e}")
        raise


@task
def generate_backtest_visualizations_task(
    backtest_result: BacktestResult, model_name: str = "Model"
) -> dict[str, list]:
    """
    生成回测可视化图表

    Args:
        backtest_result: 回测结果
        model_name: 模型名称

    Returns:
        生成的图表文件路径字典
    """
    try:
        visualizer = EvaluationVisualizer()
        chart_files = visualizer.plot_backtest_results(
            backtest_result,
            title=f"{model_name} - 回测结果分析",
            save_name="backtest_results",
        )

        logger.info(f"Backtest visualizations generated: {len(chart_files)} files")
        return {"backtest": chart_files}

    except Exception as e:
        logger.error(f"Error generating backtest visualizations: {e}")
        raise


@task
def generate_backtest_report_task(
    backtest_result: BacktestResult,
    performance_analysis: dict[str, Any],
    chart_files: Optional[dict[str, list]] = None,
    model_name: str = "Model",
    model_version: str = "1.0.0",
    output_dir: Optional[str] = None,
) -> dict[str, str]:
    """
    生成回测报告

    Args:
        backtest_result: 回测结果
        performance_analysis: 性能分析
        chart_files: 图表文件路径
        model_name: 模型名称
        model_version: 模型版本
        output_dir: 输出目录

    Returns:
        生成的报告文件路径字典
    """
    try:
        # 准备图表信息
        charts = []
        if chart_files:
            for chart_type, file_paths in chart_files.items():
                for file_path in file_paths:
                    charts.append(
                        {
                            "typing.Type": chart_type,
                            "filename": Path(file_path).name,
                            "path": file_path,
                            "title": f"{chart_type.replace('_', ' ').title()} Chart",
                        }
                    )

        # 生成报告
        builder = ReportBuilder(output_dir=output_dir)
        report_files = builder.build_comprehensive_report(
            metrics_result={},  # 回测专用报告不需要分类指标
            backtest_result=backtest_result,
            charts=charts,
            model_name=model_name,
            model_version=model_version,
            formats=["html", "json"],
        )

        logger.info(f"Backtest reports generated: {list(report_files.keys())}")
        return report_files

    except Exception as e:
        logger.error(f"Error generating backtest report: {e}")
        raise


@flow(name="model_backtest_flow", log_prints=True)
def backtest_flow(
    predictions_path: Union[str, Path],
    odds_path: Union[str, Path],
    model_name: str = "Football Prediction Model",
    model_version: str = "1.0.0",
    staking_strategy: str = "flat",
    staking_params: Optional[dict[str, Any]] = None,
    initial_bankroll: float = 1000.0,
    backtest_params: Optional[dict[str, Any]] = None,
    match_id_column: str = "match_id",
    output_dir: Optional[str] = None,
) -> dict[str, Any]:
    """
    完整的模型回测流程

    Args:
        predictions_path: 预测数据文件路径
        odds_path: 赔率数据文件路径
        model_name: 模型名称
        model_version: 模型版本
        staking_strategy: 投注策略类型
        staking_params: 投注策略参数
        initial_bankroll: 初始资金
        backtest_params: 回测参数
        match_id_column: 比赛ID列名
        output_dir: 输出目录

    Returns:
        回测结果字典
    """
    logger.info(f"Starting backtest flow for {model_name}")

    # 设置输出目录
    if output_dir is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = f"artifacts/eval/{model_name.replace(' ', '_').lower()}_backtest_{timestamp}"

    # 1. 加载预测数据
    predictions_df = load_predictions_task(predictions_path)

    # 2. 加载赔率数据
    odds_df = load_odds_data_task(odds_path)

    # 3. 准备回测数据
    merged_predictions, merged_odds = prepare_backtest_data_task(
        predictions_df, odds_df, match_id_column
    )

    # 4. 验证数据质量
    quality_report = validate_data_quality_task(merged_predictions, merged_odds)

    if not quality_report["validation_passed"]:
        logger.warning("Data validation issues found, proceeding with caution")

    # 5. 创建投注策略
    strategy = create_staking_strategy_task(staking_strategy, staking_params)

    # 6. 运行回测
    backtest_result = run_backtest_task(
        merged_predictions, merged_odds, strategy, initial_bankroll, backtest_params
    )

    # 7. 分析回测性能
    performance_analysis = analyze_backtest_performance_task(backtest_result)

    # 8. 生成可视化图表
    chart_files = generate_backtest_visualizations_task(backtest_result, model_name)

    # 9. 生成回测报告
    report_files = generate_backtest_report_task(
        backtest_result,
        performance_analysis,
        chart_files,
        model_name,
        model_version,
        output_dir,
    )

    # 10. 整合结果
    backtest_flow_result = {
        "model_info": {
            "name": model_name,
            "version": model_version,
            "predictions_path": str(predictions_path),
            "odds_path": str(odds_path),
        },
        "strategy_info": {
            "typing.Type": staking_strategy,
            "params": staking_params or {},
            "initial_bankroll": initial_bankroll,
        },
        "data_quality": quality_report,
        "backtest_result": backtest_result.to_dict(),
        "performance_analysis": performance_analysis,
        "visualizations": chart_files,
        "reports": report_files,
        "output_dir": output_dir,
    }

    # 保存完整结果
    result_file = Path(output_dir) / "complete_backtest_result.json"
    with open(result_file, "w", encoding="utf-8") as f:
        import json

        json.dump(backtest_flow_result, f, indent=2, ensure_ascii=False, default=str)

    logger.info("Backtest flow completed successfully!")
    logger.info(f"Results saved to: {output_dir}")
    logger.info(
        f"Backtest summary: {backtest_result.total_bets} bets, "
        f"ROI: {backtest_result.roi:.2f}%, "
        f"Performance: {performance_analysis['performance_rating']}"
    )

    return backtest_flow_result


# 便捷函数
def run_backtest(
    predictions_path: Union[str, Path],
    odds_path: Union[str, Path],
    model_name: str = "Football Prediction Model",
    **kwargs,
) -> dict[str, Any]:
    """
    便捷的回测函数

    Args:
        predictions_path: 预测数据文件路径
        odds_path: 赔率数据文件路径
        model_name: 模型名称
        **kwargs: 其他参数

    Returns:
        回测结果字典
    """
    if not HAS_PREFECT:
        # 如果没有Prefect，直接调用回测逻辑
        logger.warning("Prefect not available - running backtest synchronously")
        return backtest_flow.fn(
            predictions_path, odds_path, model_name=model_name, **kwargs
        )
    else:
        # 使用Prefect flow
        return backtest_flow(
            predictions_path, odds_path, model_name=model_name, **kwargs
        )
