"""
Eval Flow - 模型评估工作流

使用Prefect编排的模型评估流程。
包括模型加载、测试数据准备、指标计算和报告生成。

主要功能:
- 自动化评估流水线
- 多指标计算
- 模型比较
- 可视化报告生成
- 性能基准测试
"""

from __future__ import annotations

import logging
from typing import dict, list, Optional

from prefect import flow, task

from ..config import PipelineConfig
from ..evaluators.metrics_calculator import MetricsCalculator
from ..feature_loader import FeatureLoader
from ..model_registry import ModelRegistry

logger = logging.getLogger(__name__)


@task(retries=3, retry_delay_seconds=60)
def load_model_task(model_name: str, version: Optional[str], config: PipelineConfig):
    """
    加载模型任务.

    Args:
        model_name: 模型名称
        version: 模型版本
        config: 流水线配置

    Returns:
        模型和元数据
    """
    model_registry = ModelRegistry(config)
    model, metadata = model_registry.load_model(model_name, version)

    logger.info(f"Loaded model: {model_name}:{metadata['version']}")
    return model, metadata


@task(retries=2, retry_delay_seconds=30)
def load_test_data_task(
    match_ids: list[int],
    config: PipelineConfig,
) -> tuple:
    """
    加载测试数据任务.

    Args:
        match_ids: 比赛ID列表
        config: 流水线配置

    Returns:
        特征数据和目标变量
    """
    from src.features.feature_store import FootballFeatureStore

    # 创建FeatureStore和FeatureLoader
    store = FootballFeatureStore()
    feature_loader = FeatureLoader(store, config)

    # 加载测试数据
    X, y = feature_loader.load_training_data(match_ids)

    logger.info(f"Loaded {len(X)} test samples with {len(X.columns)} features")
    return X, y


@task
def evaluate_model_task(
    model,
    X,
    y,
    config: PipelineConfig,
) -> dict:
    """
    评估模型任务.

    Args:
        model: 训练好的模型
        X: 测试特征
        y: 测试标签
        config: 流水线配置

    Returns:
        评估结果
    """
    # 进行预测
    y_pred = model.predict(X)
    y_pred_proba = None

    if hasattr(model, "predict_proba"):
        try:
            y_pred_proba = model.predict_proba(X)
        except Exception as e:
            logger.warning(f"Probability prediction failed: {e}")

    # 计算指标
    metrics = MetricsCalculator.calculate_classification_metrics(
        y, y_pred, y_pred_proba
    )

    # 生成详细报告
    detailed_report = MetricsCalculator.generate_classification_report(
        y, y_pred, y_pred_proba
    )

    evaluation_result = {
        "metrics": metrics,
        "detailed_report": detailed_report,
        "sample_count": len(X),
        "feature_count": len(X.columns),
    }

    logger.info("Model evaluation completed")
    return evaluation_result


@task
def compare_models_task(
    models_data: dict[str, dict],
    X,
    y,
) -> dict:
    """
    比较多个模型任务.

    Args:
        models_data: 模型数据字典 {model_name: {model, metadata}}
        X: 测试特征
        y: 测试标签

    Returns:
        模型比较结果
    """
    predictions_dict = {}
    probabilities_dict = {}

    # 收集所有模型的预测结果
    for model_name, model_info in models_data.items():
        model = model_info["model"]

        y_pred = model.predict(X)
        predictions_dict[model_name] = y_pred

        if hasattr(model, "predict_proba"):
            try:
                y_pred_proba = model.predict_proba(X)
                probabilities_dict[model_name] = y_pred_proba
            except Exception as e:
                logger.warning(f"Probability prediction failed for {model_name}: {e}")

    # 比较模型性能
    comparison_df = MetricsCalculator.compare_models(
        y, predictions_dict, probabilities_dict
    )

    comparison_result = {
        "comparison_table": comparison_df.to_dict("records"),
        "best_model": comparison_df.iloc[comparison_df["f1_score"].idxmax()]["model"],
        "model_count": len(models_data),
    }

    logger.info("Model comparison completed")
    return comparison_result


@flow(name="Football Model Evaluation Flow")
def eval_flow(
    model_name: str,
    version: Optional[str] = None,
    test_match_ids: Optional[list[int]] = None,
    season: Optional[str] = None,
    compare_with_latest: bool = False,
    config: Optional[PipelineConfig] = None,
) -> dict:
    """
    足球模型评估工作流.

    Args:
        model_name: 模型名称
        version: 模型版本 (None使用最新)
        test_match_ids: 测试比赛ID列表
        season: 赛季 (用于获取测试数据)
        compare_with_latest: 是否与最新模型比较
        config: 流水线配置

    Returns:
        评估结果
    """
    config = config or PipelineConfig()

    logger.info(f"Starting evaluation flow for model: {model_name}")

    try:
        # 1. 加载模型
        model, metadata = load_model_task(model_name, version, config)

        # 2. 获取测试数据
        if test_match_ids is None:
            test_match_ids = _get_test_matches(season)

        if not test_match_ids:
            raise ValueError("No test matches found")

        logger.info(f"Evaluating with {len(test_match_ids)} test matches")

        X_test, y_test = load_test_data_task(test_match_ids, config)

        # 3. 评估单个模型
        evaluation_result = evaluate_model_task(model, X_test, y_test, config)

        result = {
            "status": "success",
            "model_name": model_name,
            "model_version": metadata["version"],
            "test_match_count": len(test_match_ids),
            "evaluation": evaluation_result,
            "model_metadata": metadata,
        }

        # 4. 模型比较 (如果需要)
        if compare_with_latest:
            model_registry = ModelRegistry(config)
            try:
                # 获取其他模型版本
                model_versions = model_registry.list_models(model_name).get(
                    model_name, []
                )

                if len(model_versions) > 1:
                    # 加载多个版本进行比较
                    models_data = {model_name: {"model": model, "metadata": metadata}}

                    for version_info in model_versions[-3:]:  # 最近3个版本
                        other_version = version_info["version"]
                        if other_version != metadata["version"]:
                            try:
                                other_model, other_metadata = model_registry.load_model(
                                    model_name, other_version
                                )
                                models_data[f"{model_name}_v{other_version}"] = {
                                    "model": other_model,
                                    "metadata": other_metadata,
                                }
                            except Exception as e:
                                logger.warning(
                                    f"Failed to load model version {other_version}: {e}"
                                )

                    if len(models_data) > 1:
                        comparison_result = compare_models_task(
                            models_data, X_test, y_test
                        )
                        result["comparison"] = comparison_result

            except Exception as e:
                logger.warning(f"Model comparison failed: {e}")

        logger.info(f"Evaluation flow completed for {model_name}")
        return result

    except Exception as e:
        logger.error(f"Evaluation flow failed: {e}")
        return {
            "status": "failed",
            "error": str(e),
            "model_name": model_name,
        }


@flow(name="Batch Model Evaluation Flow")
def batch_eval_flow(
    models: list[dict[str, str]],  # [{"name": "model1", "version": "v1"}, ...]
    test_match_ids: list[int],
    config: Optional[PipelineConfig] = None,
) -> dict:
    """
    批量模型评估工作流.

    Args:
        models: 模型列表 [{"name": "model1", "version": "v1"}, ...]
        test_match_ids: 测试比赛ID列表
        config: 流水线配置

    Returns:
        批量评估结果
    """
    config = config or PipelineConfig()

    logger.info(f"Starting batch evaluation for {len(models)} models")

    try:
        # 加载测试数据 (只加载一次)
        X_test, y_test = load_test_data_task(test_match_ids, config)

        # 加载所有模型
        models_data = {}
        for model_info in models:
            model_name = model_info["name"]
            version = model_info.get("version")

            model, metadata = load_model_task(model_name, version, config)
            models_data[model_name] = {"model": model, "metadata": metadata}

        # 比较所有模型
        comparison_result = compare_models_task(models_data, X_test, y_test)

        # 生成详细评估报告
        detailed_results = {}
        for model_name, model_info in models_data.items():
            evaluation_result = evaluate_model_task(
                model_info["model"], X_test, y_test, config
            )
            detailed_results[model_name] = evaluation_result

        result = {
            "status": "success",
            "model_count": len(models),
            "test_match_count": len(test_match_ids),
            "comparison": comparison_result,
            "detailed_results": detailed_results,
        }

        logger.info("Batch evaluation flow completed")
        return result

    except Exception as e:
        logger.error(f"Batch evaluation flow failed: {e}")
        return {
            "status": "failed",
            "error": str(e),
            "model_count": len(models),
        }


def _get_test_matches(season: Optional[str] = None) -> list[int]:
    """
    获取测试比赛ID.

    Args:
        season: 赛季

    Returns:
        比赛ID列表
    """
    # 这里应该实现从数据库获取测试比赛的逻辑
    # 暂时返回空列表，需要根据实际数据库结构实现
    logger.warning("Test match retrieval not implemented yet")
    return []


# 开发测试流程
@flow(name="Quick Evaluation Flow")
def quick_eval_flow(
    model_name: str,
    test_match_ids: list[int],
) -> dict:
    """
    快速评估流程 (用于开发测试).

    Args:
        model_name: 模型名称
        test_match_ids: 测试比赛ID列表

    Returns:
        评估结果
    """
    config = PipelineConfig()
    config.debug_mode = True

    return eval_flow(
        model_name=model_name,
        test_match_ids=test_match_ids,
        compare_with_latest=False,
        config=config,
    )


if __name__ == "__main__":
    # 开发测试示例
    test_match_ids = list(range(1001, 1101))  # 测试数据

    result = quick_eval_flow(
        model_name="test_model",
        test_match_ids=test_match_ids,
    )

    print(f"Evaluation result: {result}")
