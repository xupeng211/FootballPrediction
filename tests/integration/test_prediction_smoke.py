"""
预测烟雾测试 - 集成测试
从临时predict_match_v7.py迁移而来的核心预测测试逻辑
"""

import pytest
import pandas as pd
import numpy as np
import lightgbm as lgb
from pathlib import Path
import tempfile
import json

# 添加src路径
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


@pytest.mark.integration
@pytest.mark.slow
class TestPredictionSmoke:
    """预测烟雾测试类"""

    @pytest.fixture
    def sample_model_data(self):
        """创建样本模型数据"""
        # 创建一个简单的LightGBM模型用于测试
        from sklearn.datasets import make_classification
        from sklearn.model_selection import train_test_split

        # 生成样本数据
        X, y = make_classification(n_samples=100, n_features=30, n_classes=3,
                                 n_informative=20, random_state=42)

        return X, y

    @pytest.fixture
    def temp_model_file(self, sample_model_data):
        """创建临时模型文件"""
        X, y = sample_model_data

        # 训练一个简单的LightGBM模型
        train_data = lgb.Dataset(X, label=y)
        params = {
            'objective': 'multiclass',
            'num_class': 3,
            'metric': 'multi_logloss',
            'verbose': -1
        }

        model = lgb.train(params, train_data, num_boost_round=10)

        # 保存到临时文件
        with tempfile.NamedTemporaryFile(suffix='.model', delete=False) as tmp:
            model.save_model(tmp.name)
            return tmp.name

    @pytest.fixture
    def sample_features_df(self):
        """创建样本特征DataFrame"""
        data = {
            'home_xg': [2.1, 1.5, 0.8, 1.2, 2.5],
            'away_xg': [1.8, 2.2, 1.1, 0.9, 1.6],
            'home_possession': [65, 45, 55, 60, 70],
            'away_possession': [35, 55, 45, 40, 30],
            'home_shots': [18, 12, 8, 15, 20],
            'away_shots': [12, 15, 10, 9, 14],
            'home_corners': [8, 4, 6, 7, 9],
            'away_corners': [3, 7, 5, 6, 4],
            'home_yellow_cards': [2, 1, 3, 2, 1],
            'away_yellow_cards': [3, 2, 1, 3, 2],
            'home_red_cards': [0, 1, 0, 0, 1],
            'away_red_cards': [0, 0, 1, 0, 0],
            'result': [1, 0, 2, 1, 1],  # 1=主胜, 0=平局, 2=客胜
            'home_team': ['Man City', 'Chelsea', 'Arsenal', 'Liverpool', 'Man United'],
            'away_team': ['Liverpool', 'Man United', 'Tottenham', 'Chelsea', 'Arsenal']
        }
        return pd.DataFrame(data)

    def test_model_loading(self, temp_model_file):
        """测试模型加载"""
        try:
            model = lgb.Booster(model_file=temp_model_file)
            assert model is not None
            assert model.num_feature() > 0
        except Exception as e:
            pytest.fail(f"模型加载失败: {e}")

    def test_data_loading(self, sample_features_df):
        """测试数据加载"""
        assert sample_features_df is not None
        assert len(sample_features_df) > 0
        assert 'home_xg' in sample_features_df.columns
        assert 'away_xg' in sample_features_df.columns

    def test_feature_extraction(self, sample_features_df):
        """测试特征提取"""
        # 获取数值特征列
        exclude_cols = ['result', 'home_team', 'away_team', 'match_time',
                       'league_name', 'feature_version', 'data_source']
        numeric_cols = sample_features_df.select_dtypes(include=['number']).columns.tolist()
        feature_cols = [col for col in numeric_cols if col not in exclude_cols]

        assert len(feature_cols) > 0
        assert 'home_xg' in feature_cols

    def test_prediction_basic_flow(self, temp_model_file, sample_features_df):
        """测试基本预测流程"""
        try:
            # 1. 加载模型
            model = lgb.Booster(model_file=temp_model_file)

            # 2. 准备特征
            exclude_cols = ['result', 'home_team', 'away_team', 'match_time',
                           'league_name', 'feature_version', 'data_source']
            numeric_cols = sample_features_df.select_dtypes(include=['number']).columns.tolist()
            feature_cols = [col for col in numeric_cols if col not in exclude_cols]

            # 3. 获取特征数据
            test_features = sample_features_df[feature_cols].iloc[0:1]

            # 4. 检查特征数量
            model_feature_num = model.num_feature()
            actual_feature_num = len(feature_cols)

            # 5. 处理特征数量不匹配
            if actual_feature_num != model_feature_num:
                # 创建全0特征向量
                full_features = np.zeros((1, model_feature_num))
                for i, col in enumerate(feature_cols):
                    if i < model_feature_num:
                        full_features[0, i] = test_features[col].iloc[0]
                test_features = pd.DataFrame(full_features,
                                            columns=[f"feature_{i}" for i in range(model_feature_num)])

            # 6. 执行预测
            prediction = model.predict(test_features, predict_disable_shape_check=True)

            assert prediction is not None
            assert len(prediction) > 0

        except Exception as e:
            pytest.fail(f"预测流程失败: {e}")

    def test_prediction_result_format(self, temp_model_file, sample_features_df):
        """测试预测结果格式"""
        try:
            model = lgb.Booster(model_file=temp_model_file)

            # 准备特征（简化版）
            exclude_cols = ['result', 'home_team', 'away_team']
            numeric_cols = sample_features_df.select_dtypes(include=['number']).columns.tolist()
            feature_cols = [col for col in numeric_cols if col not in exclude_cols]

            test_features = sample_features_df[feature_cols].iloc[0:1]

            # 处理特征对齐
            model_feature_num = model.num_feature()
            actual_feature_num = len(feature_cols)

            if actual_feature_num != model_feature_num:
                full_features = np.zeros((1, model_feature_num))
                for i, col in enumerate(feature_cols):
                    if i < model_feature_num:
                        full_features[0, i] = test_features[col].iloc[0]
                test_features = pd.DataFrame(full_features,
                                            columns=[f"feature_{i}" for i in range(model_feature_num)])

            # 执行预测
            prediction = model.predict(test_features, predict_disable_shape_check=True)
            pred_value = float(prediction[0] if len(prediction.shape) == 1 else prediction[0][0])

            # 验证结果格式
            assert isinstance(pred_value, (int, float))
            assert not np.isnan(pred_value)
            assert not np.isinf(pred_value)

        except Exception as e:
            pytest.fail(f"预测结果格式测试失败: {e}")

    def test_prediction_result_saving(self, temp_model_file, sample_features_df, tmp_path):
        """测试预测结果保存"""
        try:
            model = lgb.Booster(model_file=temp_model_file)

            # 执行预测（简化版）
            exclude_cols = ['result', 'home_team', 'away_team']
            numeric_cols = sample_features_df.select_dtypes(include=['number']).columns.tolist()
            feature_cols = [col for col in numeric_cols if col not in exclude_cols]

            test_features = sample_features_df[feature_cols].iloc[0:1]

            model_feature_num = model.num_feature()
            actual_feature_num = len(feature_cols)

            if actual_feature_num != model_feature_num:
                full_features = np.zeros((1, model_feature_num))
                for i, col in enumerate(feature_cols):
                    if i < model_feature_num:
                        full_features[0, i] = test_features[col].iloc[0]
                test_features = pd.DataFrame(full_features,
                                            columns=[f"feature_{i}" for i in range(model_feature_num)])

            prediction = model.predict(test_features, predict_disable_shape_check=True)
            pred_value = float(prediction[0] if len(prediction.shape) == 1 else prediction[0][0])

            # 构建结果
            result = {
                "match_id": "test_4147463",
                "prediction": 1 if pred_value > 0.5 else 0,
                "raw_prediction": pred_value,
                "probabilities": {
                    "home_win": max(0, pred_value),
                    "draw": max(0, 1 - pred_value),
                    "away_win": max(0, pred_value * 0.1)
                },
                "model_info": {
                    "type": "LightGBM",
                    "features_count": len(feature_cols),
                    "test_data_shape": test_features.shape
                },
                "status": "success"
            }

            # 保存结果
            output_file = tmp_path / "test_prediction_result.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)

            # 验证文件存在且可读
            assert output_file.exists()

            with open(output_file, 'r', encoding='utf-8') as f:
                loaded_result = json.load(f)

            assert loaded_result["status"] == "success"
            assert "match_id" in loaded_result
            assert "prediction" in loaded_result

        except Exception as e:
            pytest.fail(f"预测结果保存测试失败: {e}")

    def test_edge_case_empty_features(self, temp_model_file):
        """测试空特征边缘情况"""
        try:
            model = lgb.Booster(model_file=temp_model_file)

            # 创建空特征
            empty_features = pd.DataFrame(np.zeros((1, model.num_feature())),
                                        columns=[f"feature_{i}" for i in range(model.num_feature())])

            prediction = model.predict(empty_features, predict_disable_shape_check=True)

            assert prediction is not None
            assert len(prediction) > 0

        except Exception as e:
            pytest.fail(f"空特征测试失败: {e}")

    def test_edge_case_extreme_values(self, temp_model_file):
        """测试极端值边缘情况"""
        try:
            model = lgb.Booster(model_file=temp_model_file)

            # 创建包含极端值的特征
            extreme_features = pd.DataFrame(np.array([[1e10, -1e10, np.inf, -np.inf, 0] + [0] * (model.num_feature() - 5)]),
                                          columns=[f"feature_{i}" for i in range(model.num_feature())])

            # 可能抛出异常，但不应该崩溃
            try:
                prediction = model.predict(extreme_features, predict_disable_shape_check=True)
                assert prediction is not None
            except ValueError:
                # 极端值导致的错误是可以接受的
                pass

        except Exception as e:
            pytest.fail(f"极端值测试失败: {e}")