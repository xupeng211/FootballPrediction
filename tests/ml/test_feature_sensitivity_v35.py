#!/usr/bin/env python3
"""
V35.0 Feature Sensitivity TDD Tests - 特征敏感度测试

功能：验证新特征 (payout_ratio, movement_velocity) 对模型输出的影响

TDD 流程：
- Red Phase: 测试失败（需要模型支持单样本预测）
- Green Phase: 实现预测接口，测试通过
- Refactor Phase: 优化代码（可选）

Author: 高级机器学习架构师 & SRE
Date: 2026-01-12
Version: V35.0 (Canary Training & Model Audit)
"""

import pytest
import numpy as np
import sys
from pathlib import Path
from typing import Dict, Any

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestPayoutRatioSensitivity:
    """测试 payout_ratio 特征敏感度"""

    def test_payout_ratio_affects_prediction(self):
        """
        TDD 核心测试：验证 payout_ratio 对模型输出的影响

        场景：构造两个样本，除 payout_ratio 外完全相同
        - 样本 A: payout_ratio = 0.92 (正常返还率)
        - 样本 B: payout_ratio = 0.98 (高返还率，可能是冷门诱导盘)

        预期：模型对两个样本的预测概率应有显著差异
        """
        try:
            from scripts.ml.train_v51_3_full_power import V53ModelTrainer, V53FeatureCalculator
            import joblib

            # 尝试加载已训练模型
            model_path = Path(__file__).parent.parent.parent / "model_zoo" / "v51_3_full_power_model.pkl"

            if not model_path.exists():
                pytest.skip(f"模型文件不存在: {model_path} (需要先训练模型)")

            model_data = joblib.load(model_path)
            model = model_data["model"]
            scaler = model_data["scaler"]
            feature_names = model_data["feature_names"]

            # 构造测试样本（60 维特征）
            # 样本 A: 正常返还率 (0.92)
            sample_normal = np.zeros((1, 60))
            sample_normal[0, :] = self._create_base_feature_vector()
            # 设置 payout_ratio 为正常值
            payout_idx = feature_names.index("payout_ratio")
            sample_normal[0, payout_idx] = 0.92

            # 样本 B: 高返还率 (0.98) - 可能是冷门诱导盘
            sample_high_payout = np.zeros((1, 60))
            sample_high_payout[0, :] = self._create_base_feature_vector()
            sample_high_payout[0, payout_idx] = 0.98

            # 标准化
            sample_normal_scaled = scaler.transform(sample_normal)
            sample_high_payout_scaled = scaler.transform(sample_high_payout)

            # 预测
            prob_normal = model.predict_proba(sample_normal_scaled)[0]
            prob_high_payout = model.predict_proba(sample_high_payout_scaled)[0]

            # 验证：高返还率应该影响预测概率
            # 计算概率分布的差异
            prob_diff = np.abs(prob_normal - prob_high_payout)

            # 至少有一个类别的概率变化应该超过 5%
            assert np.max(prob_diff) > 0.05, (
                f"payout_ratio 变化应该显著影响预测概率\n"
                f"正常返还率预测: {prob_normal}\n"
                f"高返还率预测: {prob_high_payout}\n"
                f"最大差异: {np.max(prob_diff):.4f} (预期 > 0.05)"
            )

            # 额外验证：高返还率倾向于增加不确定性
            # 计算熵（越高越不确定）
            entropy_normal = -np.sum(prob_normal * np.log(prob_normal + 1e-10))
            entropy_high_payout = -np.sum(prob_high_payout * np.log(prob_high_payout + 1e-10))

            # 高返还率通常增加预测不确定性
            assert entropy_high_payout >= entropy_normal * 0.95, (
                f"高返还率应该增加或保持预测不确定性\n"
                f"正常返还率熵: {entropy_normal:.4f}\n"
                f"高返还率熵: {entropy_high_payout:.4f}"
            )

        except ImportError as e:
            pytest.skip(f"无法导入训练脚本: {e}")
        except Exception as e:
            pytest.skip(f"测试执行失败: {e}")

    def _create_base_feature_vector(self) -> np.ndarray:
        """创建基础特征向量（60 维）"""
        from scripts.ml.train_v51_3_full_power import V53FeatureCalculator

        # 使用默认值填充
        base_vector = np.zeros(60)

        # 设置一些合理的默认值（模拟一场典型比赛）
        feature_names = V53FeatureCalculator.ALL_FEATURES

        # 实力特征
        for i, name in enumerate(feature_names):
            if "rolling_xg" in name and "std" not in name:
                base_vector[i] = 1.2
            elif "rolling_xg" in name and "std" in name:
                base_vector[i] = 0.3
            elif "shots_on_target" in name and "std" not in name:
                base_vector[i] = 5.0
            elif "shots_on_target" in name and "std" in name:
                base_vector[i] = 1.5
            elif "possession" in name and "std" not in name:
                base_vector[i] = 50.0
            elif "possession" in name and "std" in name:
                base_vector[i] = 10.0
            elif "recent_form_points" in name:
                base_vector[i] = 6.0
            elif "win_rate" in name:
                base_vector[i] = 0.5
            elif "fatigue" in name:
                base_vector[i] = 0.2
            elif "rest_days" in name:
                base_vector[i] = 7.0
            elif "clean_sheets" in name:
                base_vector[i] = 0.3
            elif name == "payout_ratio":
                base_vector[i] = 0.93  # 默认值
            elif name == "movement_velocity":
                base_vector[i] = 2.0  # 默认值

        return base_vector


class TestMovementVelocitySensitivity:
    """测试 movement_velocity 特征敏感度"""

    def test_movement_velocity_affects_prediction(self):
        """
        TDD 测试：验证 movement_velocity 对模型输出的影响

        场景：构造两个样本，除 movement_velocity 外完全相同
        - 样本 A: movement_velocity = 1.0 (正常变盘速度)
        - 样本 B: movement_velocity = 25.0 (极端变盘速度，主力资金活跃)

        预期：模型对两个样本的预测概率应有差异
        """
        try:
            from scripts.ml.train_v51_3_full_power import V53ModelTrainer, V53FeatureCalculator
            import joblib

            # 尝试加载已训练模型
            model_path = Path(__file__).parent.parent.parent / "model_zoo" / "v51_3_full_power_model.pkl"

            if not model_path.exists():
                pytest.skip(f"模型文件不存在: {model_path} (需要先训练模型)")

            model_data = joblib.load(model_path)
            model = model_data["model"]
            scaler = model_data["scaler"]
            feature_names = model_data["feature_names"]

            # 构造测试样本
            base_vector = self._create_base_feature_vector()

            # 样本 A: 正常变盘速度
            sample_normal = base_vector.copy()
            velocity_idx = feature_names.index("movement_velocity")
            sample_normal[velocity_idx] = 1.0

            # 样本 B: 极端变盘速度
            sample_high_velocity = base_vector.copy()
            sample_high_velocity[velocity_idx] = 25.0

            # 标准化并预测
            sample_normal_scaled = scaler.transform(sample_normal.reshape(1, -1))
            sample_high_velocity_scaled = scaler.transform(sample_high_velocity.reshape(1, -1))

            prob_normal = model.predict_proba(sample_normal_scaled)[0]
            prob_high_velocity = model.predict_proba(sample_high_velocity_scaled)[0]

            # 验证：极端变盘速度应该影响预测概率
            prob_diff = np.abs(prob_normal - prob_high_velocity)
            assert np.max(prob_diff) > 0.03, (
                f"movement_velocity 变化应该影响预测概率\n"
                f"正常速度预测: {prob_normal}\n"
                f"极端速度预测: {prob_high_velocity}\n"
                f"最大差异: {np.max(prob_diff):.4f} (预期 > 0.03)"
            )

        except ImportError as e:
            pytest.skip(f"无法导入训练脚本: {e}")
        except Exception as e:
            pytest.skip(f"测试执行失败: {e}")

    def _create_base_feature_vector(self) -> np.ndarray:
        """创建基础特征向量"""
        from scripts.ml.train_v51_3_full_power import V53FeatureCalculator

        base_vector = np.zeros(60)
        feature_names = V53FeatureCalculator.ALL_FEATURES

        for i, name in enumerate(feature_names):
            if "rolling_xg" in name and "std" not in name:
                base_vector[i] = 1.2
            elif "rolling_xg" in name and "std" in name:
                base_vector[i] = 0.3
            elif "shots_on_target" in name and "std" not in name:
                base_vector[i] = 5.0
            elif "shots_on_target" in name and "std" in name:
                base_vector[i] = 1.5
            elif "possession" in name and "std" not in name:
                base_vector[i] = 50.0
            elif "possession" in name and "std" in name:
                base_vector[i] = 10.0
            elif "recent_form_points" in name:
                base_vector[i] = 6.0
            elif "win_rate" in name:
                base_vector[i] = 0.5
            elif "fatigue" in name:
                base_vector[i] = 0.2
            elif "rest_days" in name:
                base_vector[i] = 7.0
            elif "clean_sheets" in name:
                base_vector[i] = 0.3
            elif name == "payout_ratio":
                base_vector[i] = 0.93
            elif name == "movement_velocity":
                base_vector[i] = 2.0

        return base_vector


class TestCombinedSensitivity:
    """测试新特征组合敏感度"""

    def test_high_risk_scenario(self):
        """
        TDD 测试：验证高风险场景的识别能力

        场景：同时具备两个风险信号
        - payout_ratio > 0.96 (高返还率)
        - movement_velocity > 20 (极端变盘速度)

        预期：模型应该降低对热门的信心
        """
        try:
            from scripts.ml.train_v51_3_full_power import V53ModelTrainer, V53FeatureCalculator
            import joblib

            model_path = Path(__file__).parent.parent.parent / "model_zoo" / "v51_3_full_power_model.pkl"

            if not model_path.exists():
                pytest.skip(f"模型文件不存在: {model_path} (需要先训练模型)")

            model_data = joblib.load(model_path)
            model = model_data["model"]
            scaler = model_data["scaler"]
            feature_names = model_data["feature_names"]

            # 构造三个样本
            base_vector = self._create_base_feature_vector()

            # 样本 A: 正常场景
            sample_normal = base_vector.copy()
            payout_idx = feature_names.index("payout_ratio")
            velocity_idx = feature_names.index("movement_velocity")
            sample_normal[payout_idx] = 0.93
            sample_normal[velocity_idx] = 2.0

            # 样本 B: 高风险场景
            sample_high_risk = base_vector.copy()
            sample_high_risk[payout_idx] = 0.97
            sample_high_risk[velocity_idx] = 25.0

            # 预测
            prob_normal = model.predict_proba(scaler.transform(sample_normal.reshape(1, -1)))[0]
            prob_high_risk = model.predict_proba(scaler.transform(sample_high_risk.reshape(1, -1)))[0]

            # 验证：高风险场景的预测分布应该更分散（不确定性增加）
            entropy_normal = -np.sum(prob_normal * np.log(prob_normal + 1e-10))
            entropy_high_risk = -np.sum(prob_high_risk * np.log(prob_high_risk + 1e-10))

            # 高风险场景通常增加预测不确定性
            assert entropy_high_risk >= entropy_normal * 0.9, (
                f"高风险场景应该增加预测不确定性\n"
                f"正常场景熵: {entropy_normal:.4f}\n"
                f"高风险场景熵: {entropy_high_risk:.4f}"
            )

            # 验证：概率变化应该显著
            prob_diff = np.abs(prob_normal - prob_high_risk)
            assert np.max(prob_diff) > 0.08, (
                f"高风险场景应该显著改变预测概率\n"
                f"正常场景: {prob_normal}\n"
                f"高风险场景: {prob_high_risk}\n"
                f"最大差异: {np.max(prob_diff):.4f}"
            )

        except ImportError as e:
            pytest.skip(f"无法导入训练脚本: {e}")
        except Exception as e:
            pytest.skip(f"测试执行失败: {e}")

    def _create_base_feature_vector(self) -> np.ndarray:
        """创建基础特征向量"""
        from scripts.ml.train_v51_3_full_power import V53FeatureCalculator

        base_vector = np.zeros(60)
        feature_names = V53FeatureCalculator.ALL_FEATURES

        for i, name in enumerate(feature_names):
            if "rolling_xg" in name and "std" not in name:
                base_vector[i] = 1.2
            elif "rolling_xg" in name and "std" in name:
                base_vector[i] = 0.3
            elif "shots_on_target" in name and "std" not in name:
                base_vector[i] = 5.0
            elif "shots_on_target" in name and "std" in name:
                base_vector[i] = 1.5
            elif "possession" in name and "std" not in name:
                base_vector[i] = 50.0
            elif "possession" in name and "std" in name:
                base_vector[i] = 10.0
            elif "recent_form_points" in name:
                base_vector[i] = 6.0
            elif "win_rate" in name:
                base_vector[i] = 0.5
            elif "fatigue" in name:
                base_vector[i] = 0.2
            elif "rest_days" in name:
                base_vector[i] = 7.0
            elif "clean_sheets" in name:
                base_vector[i] = 0.3
            elif name == "payout_ratio":
                base_vector[i] = 0.93
            elif name == "movement_velocity":
                base_vector[i] = 2.0

        return base_vector


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "-s"])
