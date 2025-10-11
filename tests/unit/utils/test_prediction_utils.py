"""
预测工具测试

测试预测工具函数
"""

import pytest
import pandas as pd
from datetime import datetime, timedelta
from src.models.prediction.core import PredictionResult
from src.models.prediction.utils import PredictionUtils


@pytest.fixture
def sample_predictions():
    """创建示例预测结果列表"""
    predictions = []
    for i in range(5):
        pred = PredictionResult(
            match_id=1000 + i,
            model_version="1",
            model_name="football_baseline_model",
            home_win_probability=0.5 + i * 0.05,
            draw_probability=0.3 - i * 0.05,
            away_win_probability=0.2,
            predicted_result="home" if i < 3 else "draw",
            confidence_score=0.5 + i * 0.05,
            features_used={"feature1": 1.0},
            prediction_metadata={},
            created_at=datetime.now() - timedelta(hours=i),
        )
        predictions.append(pred)
    return predictions


class TestPredictionUtils:
    """测试预测工具类"""

    def test_serialize_prediction(self, sample_predictions):
        """测试序列化预测结果"""
        pred = sample_predictions[0]
        serialized = PredictionUtils.serialize_prediction(pred)

        assert serialized["match_id"] == pred.match_id
        assert serialized["model_version"] == pred.model_version
        assert serialized["home_win_probability"] == pred.home_win_probability
        assert "created_at" in serialized
        assert isinstance(serialized["created_at"], str)

    def test_deserialize_prediction(self, sample_predictions):
        """测试反序列化预测结果"""
        pred = sample_predictions[0]
        serialized = PredictionUtils.serialize_prediction(pred)
        deserialized = PredictionUtils.deserialize_prediction(serialized)

        assert deserialized.match_id == pred.match_id
        assert deserialized.model_version == pred.model_version
        assert deserialized.home_win_probability == pred.home_win_probability
        assert deserialized.created_at == pred.created_at

    def test_calculate_prediction_entropy(self):
        """测试计算预测熵值"""
        # 确定性预测（熵值低）
        entropy = PredictionUtils.calculate_prediction_entropy(0.9, 0.05, 0.05)
        assert entropy < 0.5

        # 完全不确定预测（熵值高）
        entropy = PredictionUtils.calculate_prediction_entropy(0.33, 0.33, 0.34)
        assert entropy > 1.0

        # 极端情况
        entropy = PredictionUtils.calculate_prediction_entropy(1.0, 0.0, 0.0)
        assert entropy == 0.0

    def test_get_prediction_certainty_level(self):
        """测试获取预测确定性等级"""
        assert PredictionUtils.get_prediction_certainty_level(0.9) == "very_high"
        assert PredictionUtils.get_prediction_certainty_level(0.7) == "high"
        assert PredictionUtils.get_prediction_certainty_level(0.5) == "medium"
        assert PredictionUtils.get_prediction_certainty_level(0.3) == "low"

    def test_calculate_betting_value(self):
        """测试计算投注价值"""
        # 有价值的投注
        value = PredictionUtils.calculate_betting_value(
            0.5,
            0.3,
            0.2,  # 预测概率
            2.1,
            3.2,
            4.5,  # 赔率
        )
        assert value["home_value"] > 0  # 主胜有价值
        assert value["max_value"] > 0

        # 无价值的投注
        value = PredictionUtils.calculate_betting_value(
            0.4,
            0.3,
            0.3,  # 预测概率
            2.0,
            3.0,
            3.0,  # 赔率（隐含概率等于预测概率）
        )
        assert abs(value["max_value"]) < 0.1

    def test_aggregate_predictions(self, sample_predictions):
        """测试聚合预测结果"""
        stats = PredictionUtils.aggregate_predictions(sample_predictions)

        assert stats["count"] == 5
        assert 0 < stats["avg_confidence"] <= 1
        assert "result_distribution" in stats
        assert "result_percentages" in stats
        assert "probability_averages" in stats
        assert "probability_std" in stats

        # 验证结果分布
        dist = stats["result_distribution"]
        assert dist["home"] == 3  # 前3个是home
        assert dist["draw"] == 2  # 后2个是draw
        assert dist["away"] == 0

    def test_aggregate_empty_predictions(self):
        """测试聚合空预测列表"""
        stats = PredictionUtils.aggregate_predictions([])

        assert stats["count"] == 0
        assert stats["avg_confidence"] == 0.0
        assert stats["result_distribution"] == {}

    def test_filter_predictions_by_confidence(self, sample_predictions):
        """测试根据置信度过滤预测"""
        # 过滤高置信度预测
        filtered = PredictionUtils.filter_predictions_by_confidence(
            sample_predictions, min_confidence=0.55
        )
        assert len(filtered) == 3  # 后3个预测置信度>=0.55

        # 过滤特定范围
        filtered = PredictionUtils.filter_predictions_by_confidence(
            sample_predictions, min_confidence=0.52, max_confidence=0.58
        )
        assert len(filtered) == 1  # 只有第3个预测在范围内

    def test_export_predictions_to_csv(self, sample_predictions, tmp_path):
        """测试导出预测到CSV"""
        file_path = tmp_path / "predictions.csv"

        PredictionUtils.export_predictions_to_csv(sample_predictions, str(file_path))

        # 验证文件存在
        assert file_path.exists()

        # 验证内容
        df = pd.read_csv(file_path)
        assert len(df) == len(sample_predictions)
        assert "match_id" in df.columns
        assert "predicted_result" in df.columns
        assert "confidence_score" in df.columns

    def test_export_empty_predictions(self, tmp_path):
        """测试导出空预测列表"""
        file_path = tmp_path / "empty.csv"
        PredictionUtils.export_predictions_to_csv([], str(file_path))
        # 应该不报错，但文件可能不存在或为空

    def test_calculate_prediction_metrics(self, sample_predictions):
        """测试计算预测准确率指标"""
        # 创建实际结果
        actual_results = {
            1000: "home",  # 正确
            1001: "home",  # 正确
            1002: "away",  # 错误
            1003: "draw",  # 正确
            1004: "draw",  # 正确
            1005: "home",  # 不在预测中
        }

        metrics = PredictionUtils.calculate_prediction_metrics(
            sample_predictions, actual_results
        )

        assert metrics["total_predictions"] == 5
        assert metrics["matched_results"] == 4  # 4个有实际结果
        assert metrics["correct_predictions"] == 3  # 3个预测正确
        assert 0 < metrics["accuracy"] <= 1
        assert metrics["coverage"] == 0.8  # 4/5

    def test_calculate_empty_prediction_metrics(self):
        """测试计算空预测的指标"""
        metrics = PredictionUtils.calculate_prediction_metrics([], {})
        assert metrics["total_predictions"] == 0
        assert metrics["accuracy"] == 0.0

    def test_generate_prediction_report(self, sample_predictions):
        """测试生成预测报告"""
        report = PredictionUtils.generate_prediction_report(
            sample_predictions, "测试报告"
        )

        assert "测试报告" in report
        assert "总预测数：5" in report
        assert "平均置信度：" in report
        assert "预测结果分布：" in report
        assert "主胜：3 次" in report
        assert "平局：2 次" in report

    def test_generate_empty_prediction_report(self):
        """测试生成空预测报告"""
        report = PredictionUtils.generate_prediction_report([], "空报告")
        assert "空报告" in report
        assert "没有预测数据" in report

    def test_get_recent_predictions(self, sample_predictions):
        """测试获取最近的预测"""
        # 获取最近3小时的预测
        recent = PredictionUtils.get_recent_predictions(sample_predictions, hours=3)
        assert len(recent) == 4  # 前4个在3小时内

        # 获取最近1小时的预测
        recent = PredictionUtils.get_recent_predictions(sample_predictions, hours=1)
        assert len(recent) == 1  # 只有第1个在1小时内

        # 获取最近10小时的预测（全部）
        recent = PredictionUtils.get_recent_predictions(sample_predictions, hours=10)
        assert len(recent) == 5
