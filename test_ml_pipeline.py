#!/usr/bin/env python3
"""
ML Pipeline Test Script
测试机器学习管道的完整功能
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.ml.real_model_training import train_football_prediction_model, RealModelTrainingPipeline
from src.ml.advanced_model_trainer import ModelType
from src.core.logging_system import get_logger

logger = get_logger(__name__)


async def test_feature_calculator():
    """测试特征计算器"""
    logger.info("Testing Feature Calculator...")

    from src.features.features.feature_calculator_calculators import FeatureCalculator, MatchResult
    from datetime import datetime

    # 创建示例数据
    matches = [
        MatchResult(
            match_id="test_001",
            home_team="Team A",
            away_team="Team B",
            home_score=2,
            away_score=1,
            match_date=datetime.now(),
            league="Test League",
            home_win=True,
            draw=False,
            away_win=False,
            home_goals=2,
            away_goals=1,
            total_goals=3,
            goal_difference=1
        ),
        MatchResult(
            match_id="test_002",
            home_team="Team B",
            away_team="Team C",
            home_score=1,
            away_score=1,
            match_date=datetime.now(),
            league="Test League",
            home_win=False,
            draw=True,
            away_win=False,
            home_goals=1,
            away_goals=1,
            total_goals=2,
            goal_difference=0
        )
    ]

    calculator = FeatureCalculator()

    # 测试特征计算
    features = calculator.calculate_all_features("Team A", "Team B", matches)

    logger.info(f"Feature calculator test passed. Generated {len(features)} features")
    return True


async def test_advanced_trainer():
    """测试高级模型训练器"""
    logger.info("Testing Advanced Model Trainer...")

    import pandas as pd
    import numpy as np

    # 创建示例数据
    np.random.seed(42)
    n_samples = 200
    n_features = 10

    X = pd.DataFrame(
        np.random.randn(n_samples, n_features),
        columns=[f"feature_{i}" for i in range(n_features)]
    )
    y = pd.Series(np.random.choice([0, 1, 2], n_samples))

    from src.ml.advanced_model_trainer import AdvancedModelTrainer

    trainer = AdvancedModelTrainer()

    # 测试训练
    result = await trainer.train_model(
        X, y,
        model_type=ModelType.RANDOM_FOREST.value,
        hyperparameter_tuning=False  # 跳过网格搜索以加快测试
    )

    if result["success"]:
        # 测试预测
        test_X = pd.DataFrame(
            np.random.randn(5, n_features),
            columns=[f"feature_{i}" for i in range(n_features)]
        )
        pred_result = await trainer.predict(test_X)

        if pred_result["success"]:
            logger.info("Advanced model trainer test passed")
            return True

    logger.error("Advanced model trainer test failed")
    return False


async def test_ensemble_trainer():
    """测试集成训练器"""
    logger.info("Testing Ensemble Trainer...")

    import pandas as pd
    import numpy as np

    # 创建示例数据
    np.random.seed(42)
    n_samples = 150
    n_features = 8

    X = pd.DataFrame(
        np.random.randn(n_samples, n_features),
        columns=[f"feature_{i}" for i in range(n_features)]
    )
    y = pd.Series(np.random.choice([0, 1, 2], n_samples))

    from src.ml.advanced_model_trainer import EnsembleTrainer

    trainer = EnsembleTrainer()

    # 测试集成训练
    result = await trainer.train_ensemble(
        X, y,
        model_types=[ModelType.RANDOM_FOREST.value],  # 只测试一个模型以加快速度
        hyperparameter_tuning=False
    )

    if result["success"]:
        # 测试集成预测
        test_X = pd.DataFrame(
            np.random.randn(5, n_features),
            columns=[f"feature_{i}" for i in range(n_features)]
        )
        pred_result = await trainer.predict_ensemble(test_X)

        if pred_result["success"]:
            logger.info("Ensemble trainer test passed")
            return True

    logger.error("Ensemble trainer test failed")
    return False


async def test_complete_pipeline():
    """测试完整的训练管道"""
    logger.info("Testing Complete Training Pipeline...")

    # 运行完整管道（使用示例数据）
    result = await train_football_prediction_model(
        use_sample_data=True,
        config={
            'models_dir': 'models/test',
            'hyperparameter_tuning': False  # 跳过网格搜索以加快测试
        }
    )

    if result["success"]:
        logger.info(f"Complete pipeline test passed!")
        logger.info(f"Best model: {result['best_model']}")
        logger.info(f"Best accuracy: {result.get('best_accuracy', 'N/A')}")
        return True
    else:
        logger.error(f"Complete pipeline test failed: {result.get('error')}")
        return False


async def test_feature_importance():
    """测试特征重要性分析"""
    logger.info("Testing Feature Importance Analysis...")

    pipeline = RealModelTrainingPipeline()

    # 创建示例数据
    matches = pipeline.create_sample_match_data(100)

    # 准备训练数据
    X, y, feature_columns = await pipeline.prepare_training_data(matches)

    logger.info(f"Prepared {len(X)} samples with {len(feature_columns)} features")

    # 训练一个简单的模型
    result = await pipeline.train_single_model(
        X, y,
        model_type=ModelType.RANDOM_FOREST.value,
        hyperparameter_tuning=False
    )

    if result["success"] and "feature_importance" in result:
        top_features = list(result["feature_importance"].items())[:5]
        logger.info(f"Top 5 features: {top_features}")
        logger.info("Feature importance test passed")
        return True
    else:
        logger.error("Feature importance test failed")
        return False


async def run_all_tests():
    """运行所有测试"""
    logger.info("Starting ML Pipeline Tests...")

    tests = [
        ("Feature Calculator", test_feature_calculator),
        ("Advanced Model Trainer", test_advanced_trainer),
        ("Ensemble Trainer", test_ensemble_trainer),
        ("Feature Importance", test_feature_importance),
        ("Complete Pipeline", test_complete_pipeline)
    ]

    results = {}
    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        logger.info(f"\n{'='*50}")
        logger.info(f"Running Test: {test_name}")
        logger.info(f"{'='*50}")

        try:
            result = await test_func()
            results[test_name] = result
            if result:
                passed += 1
                logger.info(f"✅ {test_name}: PASSED")
            else:
                logger.error(f"❌ {test_name}: FAILED")
        except Exception as e:
            logger.error(f"❌ {test_name}: ERROR - {e}")
            results[test_name] = False

    # 测试总结
    logger.info(f"\n{'='*50}")
    logger.info("TEST SUMMARY")
    logger.info(f"{'='*50}")
    logger.info(f"Total Tests: {total}")
    logger.info(f"Passed: {passed}")
    logger.info(f"Failed: {total - passed}")
    logger.info(f"Success Rate: {passed/total*100:.1f}%")

    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        logger.info(f"  {test_name}: {status}")

    if passed == total:
        logger.info("\n🎉 All tests passed! ML Pipeline is working correctly.")
    else:
        logger.warning(f"\n⚠️ {total - passed} test(s) failed. Please check the implementation.")

    return results


async def main():
    """主函数"""
    try:
        results = await run_all_tests()
        return results
    except Exception as e:
        logger.error(f"Test execution failed: {e}")
        return None


if __name__ == "__main__":
    asyncio.run(main())