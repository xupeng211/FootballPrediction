"""
Football Prediction Model Evaluation Flow

模型评估流程，使用Prefect编排完整的评估流程。
包含模型加载、数据准备、指标计算、校准、可视化等步骤。

Author: Football Prediction Team
Version: 1.0.0
"""

import json
import pickle
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Optional, Union, Any

try:
    from prefect import flow, task, get_run_logger
    from prefect.client.orchestration import get_client
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

from src.evaluation.metrics import Metrics, MetricsResult
from src.evaluation.calibration import AutoCalibrator, CalibrationResult
from src.evaluation.visualizer import EvaluationVisualizer
from src.evaluation.report_builder import ReportBuilder

logger = get_run_logger()


@task
def load_model_task(model_path: Union[str, Path]) -> Any:
    """
    加载训练好的模型

    Args:
        model_path: 模型文件路径

    Returns:
        加载的模型对象
    """
    model_path = Path(model_path)

    if not model_path.exists():
        raise FileNotFoundError(f"Model file not found: {model_path}")

    try:
        # 尝试使用joblib加载
        try:
            import joblib
            model = joblib.load(model_path)
            logger.info(f"Model loaded using joblib: {model_path}")
            return model
        except ImportError:
            pass

        # 尝试使用pickle加载
        with open(model_path, 'rb') as f:
            model = pickle.load(f)

        logger.info(f"Model loaded using pickle: {model_path}")
        return model

    except Exception as e:
        logger.error(f"Error loading model: {e}")
        raise


@task
def load_dataset_task(dataset_path: Union[str, Path], dataset_type: str = "validation") -> pd.DataFrame:
    """
    加载数据集

    Args:
        dataset_path: 数据集文件路径
        dataset_type: 数据集类型 ("train", "validation", "test")

    Returns:
        数据集DataFrame
    """
    dataset_path = Path(dataset_path)

    if not dataset_path.exists():
        raise FileNotFoundError(f"Dataset file not found: {dataset_path}")

    try:
        # 根据文件扩展名选择加载方式
        if dataset_path.suffix == '.csv':
            df = pd.read_csv(dataset_path)
        elif dataset_path.suffix in ['.pkl', '.pickle']:
            df = pd.read_pickle(dataset_path)
        elif dataset_path.suffix in ['.parquet']:
            df = pd.read_parquet(dataset_path)
        else:
            raise ValueError(f"Unsupported file format: {dataset_path.suffix}")

        logger.info(f"Dataset loaded: {dataset_path} ({len(df)} samples)")
        return df

    except Exception as e:
        logger.error(f"Error loading dataset: {e}")
        raise


@task
def extract_features_labels_task(dataset: pd.DataFrame,
                               feature_columns: Optional[list] = None,
                               label_column: str = "target",
                               probability_columns: Optional[list] = None) -> tuple:
    """
    从数据集中提取特征和标签

    Args:
        dataset: 数据集DataFrame
        feature_columns: 特征列名列表（如果为None，使用所有非标签列）
        label_column: 标签列名
        probability_columns: 概率列名列表（如果有）

    Returns:
        (X, y, probabilities) 元组
    """
    try:
        # 确定特征列
        if feature_columns is None:
            # 排除标签列和概率列
            exclude_columns = [label_column]
            if probability_columns:
                exclude_columns.extend(probability_columns)
            feature_columns = [col for col in dataset.columns if col not in exclude_columns]

        # 提取特征
        X = dataset[feature_columns].copy()

        # 提取标签
        if label_column not in dataset.columns:
            raise ValueError(f"Label column '{label_column}' not found in dataset")
        y = dataset[label_column].values

        # 提取概率（如果有）
        probabilities = None
        if probability_columns:
            probabilities = dataset[probability_columns].values
            logger.info(f"Extracted {len(probability_columns)} probability columns")
        elif 'predicted_proba' in dataset.columns:
            probabilities = np.array(dataset['predicted_proba'].tolist())

        logger.info(f"Features extracted: {X.shape[1]} features, {X.shape[0]} samples")
        return X, y, probabilities

    except Exception as e:
        logger.error(f"Error extracting features and labels: {e}")
        raise


@task
def model_predictions_task(model: Any, X: pd.DataFrame) -> tuple:
    """
    使用模型进行预测

    Args:
        model: 训练好的模型
        X: 特征数据

    Returns:
        (predictions, probabilities) 元组
    """
    try:
        # 预测类别
        predictions = model.predict(X)

        # 预测概率（如果支持）
        probabilities = None
        if hasattr(model, 'predict_proba'):
            probabilities = model.predict_proba(X)
        else:
            logger.warning("Model does not support predict_proba method")

        logger.info(f"Predictions generated: {len(predictions)} samples")
        return predictions, probabilities

    except Exception as e:
        logger.error(f"Error during model prediction: {e}")
        raise


@task
def calculate_metrics_task(y_true: np.ndarray, y_pred: np.ndarray,
                          y_proba: Optional[np.ndarray] = None) -> MetricsResult:
    """
    计算评估指标

    Args:
        y_true: 真实标签
        y_pred: 预测标签
        y_proba: 预测概率

    Returns:
        评估指标结果
    """
    try:
        calculator = Metrics()
        result = calculator.evaluate_all(y_true, y_pred, y_proba)

        logger.info(f"Metrics calculated: {len(result.metrics)} metrics")
        return result

    except Exception as e:
        logger.error(f"Error calculating metrics: {e}")
        raise


@task
def calibrate_probabilities_task(y_true: np.ndarray, y_proba: np.ndarray,
                                calibration_method: str = "auto") -> tuple:
    """
    校准预测概率

    Args:
        y_true: 真实标签
        y_proba: 原始预测概率
        calibration_method: 校准方法

    Returns:
        (calibrated_probabilities, calibration_result) 元组
    """
    try:
        from src.evaluation.calibration import calibrate_probabilities

        calibrated_proba, calibration_result = calibrate_probabilities(
            y_true, y_proba, method=calibration_method
        )

        logger.info(f"Probability calibration completed: {calibration_result.is_calibrated}")
        return calibrated_proba, calibration_result

    except Exception as e:
        logger.error(f"Error during probability calibration: {e}")
        # 返回原始概率和失败结果
        from src.evaluation.calibration import CalibrationResult
        failed_result = CalibrationResult(
            is_calibrated=False,
            calibration_method="none",
            original_score=0.0,
            calibrated_score=0.0,
            improvement=0.0,
            calibration_params={},
            metadata={"error": str(e)}
        )
        return y_proba, failed_result


@task
def generate_visualizations_task(y_true: np.ndarray, y_pred: np.ndarray,
                               y_proba: np.ndarray, calibrated_proba: Optional[np.ndarray] = None,
                               backtest_result: Optional[Any] = None,
                               metrics_result: Optional[MetricsResult] = None,
                               model_name: str = "Model") -> dict[str, list]:
    """
    生成可视化图表

    Args:
        y_true: 真实标签
        y_pred: 预测标签
        y_proba: 原始预测概率
        calibrated_proba: 校准后的概率
        backtest_result: 回测结果
        metrics_result: 评估指标结果
        model_name: 模型名称

    Returns:
        生成的图表文件路径字典
    """
    try:
        visualizer = EvaluationVisualizer()
        chart_files = {}

        # 生成标准评估图表
        chart_files.update(visualizer.create_comprehensive_report(
            y_true=y_true,
            y_pred=y_pred,
            y_proba=y_proba,
            backtest_result=backtest_result,
            metrics_result=metrics_result,
            model_name=model_name
        ))

        # 如果有校准后的概率，生成对比图表
        if calibrated_proba is not None:
            try:
                # 原始概率校准曲线
                original_calib_files = visualizer.plot_calibration_curves(
                    y_true, y_proba, title=f"{model_name} - 原始概率校准曲线",
                    save_name="original_calibration_curves"
                )
                chart_files['original_calibration'] = original_calib_files

                # 校准后概率校准曲线
                calibrated_calib_files = visualizer.plot_calibration_curves(
                    y_true, calibrated_proba, title=f"{model_name} - 校准后概率校准曲线",
                    save_name="calibrated_calibration_curves"
                )
                chart_files['calibrated_calibration'] = calibrated_calib_files

            except Exception as e:
                logger.warning(f"Error generating calibration comparison charts: {e}")

        logger.info(f"Visualizations generated: {len(chart_files)} chart types")
        return chart_files

    except Exception as e:
        logger.error(f"Error generating visualizations: {e}")
        raise


@task
def generate_report_task(metrics_result: MetricsResult,
                        calibration_result: Optional[CalibrationResult] = None,
                        backtest_result: Optional[Any] = None,
                        chart_files: Optional[dict[str, list]] = None,
                        model_name: str = "Model",
                        model_version: str = "1.0.0",
                        output_dir: Optional[str] = None) -> dict[str, str]:
    """
    生成评估报告

    Args:
        metrics_result: 评估指标结果
        calibration_result: 校准结果
        backtest_result: 回测结果
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
                    charts.append({
                        'type': chart_type,
                        'filename': Path(file_path).name,
                        'path': file_path,
                        'title': f"{chart_type.replace('_', ' ').title()} Chart"
                    })

        # 生成报告
        builder = ReportBuilder(output_dir=output_dir)
        report_files = builder.build_comprehensive_report(
            metrics_result=metrics_result.metrics,
            calibration_result=calibration_result,
            backtest_result=backtest_result,
            charts=charts,
            model_name=model_name,
            model_version=model_version,
            formats=['html', 'json']
        )

        logger.info(f"Reports generated: {list(report_files.keys())}")
        return report_files

    except Exception as e:
        logger.error(f"Error generating report: {e}")
        raise


@flow(name="model_evaluation_flow", log_prints=True)
def eval_flow(
    model_path: Union[str, Path],
    dataset_path: Union[str, Path],
    dataset_type: str = "validation",
    model_name: str = "Football Prediction Model",
    model_version: str = "1.0.0",
    enable_calibration: bool = True,
    calibration_method: str = "auto",
    feature_columns: Optional[list] = None,
    label_column: str = "target",
    probability_columns: Optional[list] = None,
    output_dir: Optional[str] = None
) -> dict[str, Any]:
    """
    完整的模型评估流程

    Args:
        model_path: 模型文件路径
        dataset_path: 数据集文件路径
        dataset_type: 数据集类型
        model_name: 模型名称
        model_version: 模型版本
        enable_calibration: 是否启用概率校准
        calibration_method: 校准方法
        feature_columns: 特征列名列表
        label_column: 标签列名
        probability_columns: 概率列名列表
        output_dir: 输出目录

    Returns:
        评估结果字典
    """
    logger.info(f"Starting evaluation flow for {model_name}")

    # 设置输出目录
    if output_dir is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = f"artifacts/eval/{model_name.replace(' ', '_').lower()}_eval_{timestamp}"

    # 1. 加载模型
    model = load_model_task(model_path)

    # 2. 加载数据集
    dataset = load_dataset_task(dataset_path, dataset_type)

    # 3. 提取特征和标签
    X, y, existing_probabilities = extract_features_labels_task(
        dataset, feature_columns, label_column, probability_columns
    )

    # 4. 模型预测
    y_pred, y_proba = model_predictions_task(model, X)

    # 5. 计算评估指标
    metrics_result = calculate_metrics_task(y, y_pred, y_proba)

    # 6. 概率校准（可选）
    calibration_result = None
    calibrated_proba = None

    if enable_calibration and y_proba is not None:
        calibrated_proba, calibration_result = calibrate_probabilities_task(
            y, y_proba, calibration_method
        )

    # 7. 生成可视化图表
    chart_files = generate_visualizations_task(
        y, y_pred, y_proba, calibrated_proba,
        metrics_result=metrics_result, model_name=model_name
    )

    # 8. 生成评估报告
    report_files = generate_report_task(
        metrics_result=metrics_result,
        calibration_result=calibration_result,
        chart_files=chart_files,
        model_name=model_name,
        model_version=model_version,
        output_dir=output_dir
    )

    # 9. 整合结果
    evaluation_result = {
        "model_info": {
            "name": model_name,
            "version": model_version,
            "path": str(model_path),
            "dataset_type": dataset_type,
            "dataset_path": str(dataset_path),
            "n_samples": len(X),
            "n_features": X.shape[1]
        },
        "metrics": metrics_result.to_dict(),
        "calibration": calibration_result.to_dict() if calibration_result else None,
        "predictions": {
            "y_true": y.tolist(),
            "y_pred": y_pred.tolist(),
            "y_proba": y_proba.tolist() if y_proba is not None else None,
            "calibrated_proba": calibrated_proba.tolist() if calibrated_proba is not None else None
        },
        "visualizations": chart_files,
        "reports": report_files,
        "output_dir": output_dir
    }

    # 保存完整结果
    result_file = Path(output_dir) / "complete_evaluation_result.json"
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump(evaluation_result, f, indent=2, ensure_ascii=False, default=str)

    logger.info("Evaluation flow completed successfully!")
    logger.info(f"Results saved to: {output_dir}")
    logger.info(f"Key metrics: Accuracy={metrics_result.metrics.get('accuracy', 'N/A'):.4f}, "
               f"LogLoss={metrics_result.metrics.get('logloss', 'N/A'):.4f}")

    return evaluation_result


# 便捷函数
def evaluate_model(
    model_path: Union[str, Path],
    dataset_path: Union[str, Path],
    model_name: str = "Football Prediction Model",
    **kwargs
) -> dict[str, Any]:
    """
    便捷的模型评估函数

    Args:
        model_path: 模型文件路径
        dataset_path: 数据集文件路径
        model_name: 模型名称
        **kwargs: 其他参数

    Returns:
        评估结果字典
    """
    if not HAS_PREFECT:
        # 如果没有Prefect，直接调用评估逻辑
        logger.warning("Prefect not available - running evaluation synchronously")
        return eval_flow.fn(model_path, dataset_path, model_name=model_name, **kwargs)
    else:
        # 使用Prefect flow
        return eval_flow(model_path, dataset_path, model_name=model_name, **kwargs)
