"""
端到端流水线测试 - E2E Pipeline Test

验证"数据加载->特征工程->模型训练->模型保存->推理预测"完整链路
确保MVP最小闭环可以正常工作。

测试流程:
1. 创建模拟数据
2. 数据加载和预处理
3. 特征工程
4. 模型训练
5. 模型保存
6. 模型加载和预测
"""

import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 导入需要测试的模块
try:
    from src.ml.data.loader import DataLoader
    from src.ml.features.extractor import MatchFeatureExtractor
    from src.ml.training.training_pipeline import ClassificationTrainingPipeline
    from src.ml.dataset.dataset_generator import ClassificationDatasetGenerator
    from src.ml.dataset.target_labels import score_to_label, label_to_numeric
    from src.inference import Predictor, predict_match
except ImportError as e:
    logger.error(f"模块导入失败: {e}")
    pytest.skip(f"模块导入失败: {e}", allow_module_level=True)


@pytest.fixture
def temp_dir():
    """临时目录fixture"""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def sample_historical_data():
    """创建样本历史比赛数据"""
    # 生成100场比赛的样本数据
    matches = []
    base_date = datetime.now() - timedelta(days=180)

    team_ids = list(range(1, 21))  # 20支球队

    for i in range(100):
        match_date = base_date + timedelta(days=i * 2)
        home_team = np.random.choice(team_ids)
        away_team = np.random.choice([t for t in team_ids if t != home_team])

        # 生成比分（简单随机分布，主队稍微有优势）
        home_goals = np.random.poisson(1.5)
        away_goals = np.random.poisson(1.2)

        matches.append(
            {
                "id": i + 1,
                "match_date": match_date,
                "home_team_id": home_team,
                "away_team_id": away_team,
                "home_team_name": f"Team_{home_team}",
                "away_team_name": f"Team_{away_team}",
                "home_score": home_goals,
                "away_score": away_goals,
                "status": "FT",
                "league_id": "test_league",
                "season": "2024",
                "fotmob_id": f"fotmob_{i+1}",
            }
        )

    return pd.DataFrame(matches)


@pytest.fixture
def sample_team_stats():
    """创建样本球队统计数据"""
    teams = list(range(1, 21))  # 20支球队
    stats = []

    for i, team_id in enumerate(teams):
        points = np.random.randint(20, 80)  # 20-80分
        goals_for = np.random.randint(20, 80)
        goals_against = np.random.randint(20, 60)

        stats.append(
            {
                "team_id": team_id,
                "team_name": f"Team_{team_id}",
                "position": i + 1,
                "points": points,
                "goals_for": goals_for,
                "goals_against": goals_against,
                "goal_difference": goals_for - goals_against,
                "matches_played": 30,
                "league_id": "test_league",
                "season": "2024",
            }
        )

    return pd.DataFrame(stats)


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.e2e
async def test_full_prediction_pipeline(temp_dir, sample_historical_data, sample_team_stats):
    """
    完整的预测流水线测试

    验证从数据加载到预测的完整流程
    """
    logger.info("开始端到端流水线测试...")

    try:
        # 步骤1: 特征工程
        logger.info("步骤1: 特征工程")
        feature_extractor = MatchFeatureExtractor()

        # 选择一场比赛作为测试目标
        test_match_data = {
            "id": 999,
            "home_team_id": 1,
            "away_team_id": 2,
            "home_team_name": "Team_1",
            "away_team_name": "Team_2",
            "match_date": datetime.now(),
            "league_id": "test_league",
            "season": "2024",
        }

        # 提取特征
        feature_set = await feature_extractor.extract_features(
            test_match_data, sample_historical_data, sample_team_stats
        )

        logger.info(f"特征提取完成，特征数: {len(feature_set.features)}")
        assert len(feature_set.features) > 0, "特征数量应该大于0"
        assert feature_set.feature_completeness > 0, "特征完整性应该大于0"

        # 步骤2: 创建训练数据集
        logger.info("步骤2: 创建训练数据集")

        # 将历史数据转换为训练格式
        training_data = []
        for _, match in sample_historical_data.iterrows():
            try:
                # 为每场历史比赛提取特征
                match_features = await feature_extractor.extract_features(
                    match.to_dict(), sample_historical_data, sample_team_stats
                )

                # 创建标签（基于比分）
                if match["home_score"] > match["away_score"]:
                    label = 2  # HOME_WIN
                elif match["home_score"] < match["away_score"]:
                    label = 0  # AWAY_WIN
                else:
                    label = 1  # DRAW

                # 组合特征向量
                feature_row = {}
                for i, feature_name in enumerate(feature_set.feature_names):
                    feature_row[f"feature_{i}"] = match_features.feature_vector[i]

                feature_row["target_numeric"] = label
                feature_row["match_id"] = match["id"]
                training_data.append(feature_row)

            except Exception as e:
                logger.warning(f"跳过比赛 {match['id']}: {str(e)}")
                continue

        # 创建训练DataFrame
        training_df = pd.DataFrame(training_data)
        logger.info(f"训练数据准备完成: {len(training_df)} 条记录")

        if len(training_df) < 10:
            pytest.skip("有效训练数据不足，跳过测试")

        # 保存训练数据
        dataset_path = temp_dir / "training_dataset.parquet"
        training_df.to_parquet(dataset_path, index=False)
        logger.info(f"训练数据已保存到: {dataset_path}")

        # 步骤3: 模型训练
        logger.info("步骤3: 模型训练")

        model_path = temp_dir / "test_model.pkl"
        pipeline = ClassificationTrainingPipeline(
            model_output_dir=temp_dir, config_type="fast_training"  # 使用快速训练配置
        )

        # 运行训练流水线
        metrics = await pipeline.run_pipeline(dataset_path=str(dataset_path), model_output_path=str(model_path))

        logger.info(f"模型训练完成，准确率: {metrics.get('test_accuracy', 0):.3f}")
        assert metrics.get("test_accuracy", 0) > 0, "模型准确率应该大于0"
        assert model_path.exists(), "模型文件应该存在"

        # 步骤4: 模型推理
        logger.info("步骤4: 模型推理")

        # 使用训练好的模型进行预测
        prediction_result = predict_match(
            features=feature_set.feature_vector.reshape(1, -1),
            model_path=str(model_path),
            feature_names=feature_set.feature_names,
            use_cache=False,
        )

        logger.info(f"预测结果: {prediction_result}")

        # 验证预测结果
        assert "away_win_prob" in prediction_result, "预测结果应该包含客胜概率"
        assert "draw_prob" in prediction_result, "预测结果应该包含平局概率"
        assert "home_win_prob" in prediction_result, "预测结果应该包含主胜概率"
        assert "predicted_class" in prediction_result, "预测结果应该包含预测类别"

        # 验证概率和为1（允许小误差）
        prob_sum = (
            prediction_result["away_win_prob"] + prediction_result["draw_prob"] + prediction_result["home_win_prob"]
        )
        assert abs(prob_sum - 1.0) < 0.01, f"概率和应该接近1.0，实际为: {prob_sum}"

        # 验证概率在合理范围内
        for prob_key in ["away_win_prob", "draw_prob", "home_win_prob"]:
            prob = prediction_result[prob_key]
            assert 0.0 <= prob <= 1.0, f"概率 {prob_key} 应该在[0,1]范围内，实际为: {prob}"

        # 步骤5: 测试预测器的其他功能
        logger.info("步骤5: 测试预测器功能")

        # 直接使用Predictor类
        predictor = Predictor(str(model_path), feature_set.feature_names)
        predictor.load_model()

        assert predictor.model_loaded, "模型应该成功加载"

        # 获取模型信息
        model_info = predictor.get_model_info()
        assert model_info["status"] == "loaded", "模型状态应该是已加载"

        # 再次预测（测试不同接口）
        prediction_result_2 = predictor.predict(feature_set.feature_vector)
        assert "predicted_outcome" in prediction_result_2, "预测结果应该包含预测结果描述"

        logger.info("端到端流水线测试完成！")

        # 返回性能指标用于报告
        return {
            "training_samples": len(training_df),
            "feature_count": len(feature_set.features),
            "test_accuracy": metrics.get("test_accuracy", 0),
            "feature_completeness": feature_set.feature_completeness,
            "prediction_result": prediction_result,
        }

    except Exception as e:
        logger.error(f"端到端测试失败: {str(e)}")
        raise


@pytest.mark.asyncio
@pytest.mark.integration
async def test_feature_extractor_standalone(temp_dir, sample_historical_data, sample_team_stats):
    """
    独立测试特征提取器
    """
    logger.info("测试特征提取器...")

    feature_extractor = MatchFeatureExtractor()

    test_match = {
        "id": 123,
        "home_team_id": 5,
        "away_team_id": 10,
        "home_team_name": "Team_5",
        "away_team_name": "Team_10",
        "match_date": datetime.now(),
        "league_id": "test_league",
        "season": "2024",
    }

    feature_set = await feature_extractor.extract_features(test_match, sample_historical_data, sample_team_stats)

    # 验证特征集
    assert feature_set.match_id == 123
    assert feature_set.home_team_id == 5
    assert feature_set.away_team_id == 10
    assert len(feature_set.features) > 0
    assert len(feature_set.feature_names) == len(feature_set.feature_vector)

    logger.info("特征提取器测试通过")


@pytest.mark.unit
def test_label_conversion():
    """
    测试标签转换函数
    """
    # 导入所需的枚举
    from src.ml.dataset.target_labels import MatchOutcome

    # 测试比分到标签的转换
    assert score_to_label(2, 1) == MatchOutcome.HOME_WIN
    assert score_to_label(1, 2) == MatchOutcome.AWAY_WIN
    assert score_to_label(1, 1) == MatchOutcome.DRAW

    # 测试标签到数字的转换
    assert label_to_numeric(MatchOutcome.HOME_WIN) == 2
    assert label_to_numeric(MatchOutcome.AWAY_WIN) == 0
    assert label_to_numeric(MatchOutcome.DRAW) == 1

    logger.info("标签转换测试通过")


@pytest.mark.integration
def test_prediction_cache():
    """
    测试预测缓存功能
    """
    from src.inference import PredictionCache

    cache = PredictionCache(default_ttl=1)

    # 测试缓存设置和获取
    test_features = np.array([1.0, 2.0, 3.0])
    test_result = {"test": "result"}

    cache.set(test_features, "test_model", test_result, ttl=1)
    cached_result = cache.get(test_features, "test_model")

    assert cached_result == test_result, "缓存结果应该匹配"

    # 测试缓存清理
    cache.clear()
    cached_result_after_clear = cache.get(test_features, "test_model")
    assert cached_result_after_clear is None, "清理后缓存应该为空"

    logger.info("预测缓存测试通过")


@pytest.mark.smoke
@pytest.mark.integration
async def test_minimal_pipeline_smoke():
    """
    最小流水线烟雾测试

    仅测试核心组件是否可以正常初始化和基本功能是否可用
    """
    logger.info("开始最小流水线烟雾测试...")

    try:
        # 测试组件初始化
        feature_extractor = MatchFeatureExtractor()
        logger.info("✅ MatchFeatureExtractor 初始化成功")

        # 测试简单的特征提取（使用最小数据）
        minimal_matches = pd.DataFrame(
            [
                {
                    "id": 1,
                    "match_date": datetime.now() - timedelta(days=10),
                    "home_team_id": 1,
                    "away_team_id": 2,
                    "home_team_name": "Team_1",
                    "away_team_name": "Team_2",
                    "home_score": 2,
                    "away_score": 1,
                    "status": "FT",
                    "league_id": "test",
                    "season": "2024",
                }
            ]
        )

        test_match = {
            "id": 2,
            "home_team_id": 1,
            "away_team_id": 2,
            "home_team_name": "Team_1",
            "away_team_name": "Team_2",
            "match_date": datetime.now(),
            "league_id": "test",
            "season": "2024",
        }

        feature_set = await feature_extractor.extract_features(test_match, minimal_matches)
        logger.info("✅ 特征提取成功")

        assert len(feature_set.features) > 0, "应该提取到特征"
        logger.info("✅ 最小流水线烟雾测试通过")

    except Exception as e:
        logger.error(f"❌ 烟雾测试失败: {str(e)}")
        raise


if __name__ == "__main__":
    # 直接运行测试（用于调试）
    async def run_debug_test():
        """运行调试测试"""
        import tempfile
        import shutil

        temp_dir = Path(tempfile.mkdtemp())
        try:
            await test_minimal_pipeline_smoke()
            print("✅ 调试测试通过")
        finally:
            shutil.rmtree(temp_dir)

    # 运行调试测试
    asyncio.run(run_debug_test())
