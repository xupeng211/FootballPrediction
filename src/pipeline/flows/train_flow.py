"""
Train Flow - 模型训练工作流

使用Prefect编排的端到端模型训练流程。
包括数据加载、特征工程、模型训练和保存。

主要功能:
- 自动化训练流水线
- 数据质量检查
- 多算法训练
- 模型版本管理
- 失败重试机制
"""

from __future__ import annotations

import logging
from typing import List, Optional

from prefect import flow, task

from ..config import PipelineConfig
from ..feature_loader import FeatureLoader
from ..model_registry import ModelRegistry
from ..trainer import Trainer

logger = logging.getLogger(__name__)


@task(retries=3, retry_delay_seconds=60)
def load_training_data_task(
    match_ids: list[int],
    config: PipelineConfig,
) -> tuple:
    """
    加载训练数据任务.

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

    # 加载训练数据
    X, y = feature_loader.load_training_data(match_ids)

    logger.info(f"Loaded {len(X)} samples with {len(X.columns)} features")
    return X, y, feature_loader


@task(retries=2, retry_delay_seconds=30)
def train_model_task(
    X,
    y,
    config: PipelineConfig,
    algorithm: str = "xgboost",
) -> dict:
    """
    模型训练任务.

    Args:
        X: 特征数据
        y: 目标变量
        config: 流水线配置
        algorithm: 训练算法

    Returns:
        训练结果
    """
    # 创建训练器和模型注册表
    model_registry = ModelRegistry(config)
    trainer = Trainer(config, model_registry)

    # 训练模型
    training_result = trainer.train(X, y, algorithm=algorithm)

    logger.info(f"Model training completed: {algorithm}")
    return training_result


@task
def save_model_task(
    training_result: dict,
    model_name: str,
    config: PipelineConfig,
) -> str:
    """
    保存模型任务.

    Args:
        training_result: 训练结果
        model_name: 模型名称
        config: 流水线配置

    Returns:
        模型路径
    """
    model_registry = ModelRegistry(config)

    # 准备元数据
    metadata = {
        "algorithm": training_result["algorithm"],
        "metrics": training_result["metrics"],
        "training_record": training_result["training_record"],
    }

    # 保存模型
    model_path = model_registry.save_model(
        model=training_result["model"],
        name=model_name,
        metadata=metadata,
    )

    logger.info(f"Model saved to: {model_path}")
    return model_path


@flow(name="Football Model Training Flow")
def train_flow(
    season: str,
    league_id: Optional[str] = None,
    match_ids: Optional[list[int]] = None,
    model_name: Optional[str] = None,
    algorithm: str = "xgboost",
    config: Optional[PipelineConfig] = None,
) -> dict:
    """
    足球模型训练工作流.

    Args:
        season: 赛季
        league_id: 联赛ID
        match_ids: 比赛ID列表 (None则自动获取)
        model_name: 模型名称
        algorithm: 训练算法
        config: 流水线配置

    Returns:
        训练流程结果
    """
    config = config or PipelineConfig()
    model_name = model_name or f"football_prediction_{season}_{algorithm}"

    logger.info(f"Starting training flow for season {season}")

    try:
        # 1. 获取比赛ID (如果未提供)
        if match_ids is None:
            match_ids = _get_season_matches(season, league_id)

        if not match_ids:
            raise ValueError(f"No matches found for season {season}")

        logger.info(f"Training with {len(match_ids)} matches")

        # 2. 加载训练数据
        X, y, feature_loader = load_training_data_task(match_ids, config)

        # 3. 训练模型
        training_result = train_model_task(X, y, config, algorithm)

        # 4. 保存模型
        model_path = save_model_task(training_result, model_name, config)

        # 5. 返回结果
        result = {
            "status": "success",
            "model_name": model_name,
            "model_path": model_path,
            "algorithm": algorithm,
            "season": season,
            "match_count": len(match_ids),
            "feature_count": len(X.columns),
            "metrics": training_result["metrics"],
            "training_record": training_result["training_record"],
        }

        logger.info(f"Training flow completed successfully: {model_name}")
        return result

    except Exception as e:
        logger.error(f"Training flow failed: {e}")
        return {
            "status": "failed",
            "error": str(e),
            "model_name": model_name,
            "season": season,
        }


def _get_season_matches(season: str, league_id: Optional[str] = None) -> list[int]:
    """
    获取赛季比赛ID.

    Args:
        season: 赛季 (如 "2023-2024")
        league_id: 联赛ID

    Returns:
        比赛ID列表
    """
    # 这里应该实现从数据库获取赛季比赛的逻辑
    # 暂时返回空列表，需要根据实际数据库结构实现
    logger.warning("Season match retrieval not implemented yet")
    return []


# 用于开发测试的简化流程
@flow(name="Quick Training Flow")
def quick_train_flow(
    match_ids: list[int],
    algorithm: str = "xgboost",
    model_name: str = "quick_model",
) -> dict:
    """
    快速训练流程 (用于开发测试).

    Args:
        match_ids: 比赛ID列表
        algorithm: 训练算法
        model_name: 模型名称

    Returns:
        训练结果
    """
    config = PipelineConfig()
    config.debug_mode = True

    return train_flow(
        season="dev",
        match_ids=match_ids,
        algorithm=algorithm,
        model_name=model_name,
        config=config,
    )


if __name__ == "__main__":
    # 开发测试示例
    test_match_ids = list(range(1, 1001))  # 测试数据

    result = quick_train_flow(
        match_ids=test_match_ids,
        algorithm="xgboost",
        model_name="test_model",
    )

    print(f"Training result: {result}")
