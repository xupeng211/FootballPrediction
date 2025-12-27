"""
FootballPrediction V7.0 模型训练器
使用LightGBM训练新的预测模型
"""

import pickle
from datetime import datetime

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler

from src.core.config import get_config
from src.utils import setup_logger


class ModelTrainer:
    """LightGBM模型训练器"""

    def __init__(self):
        self.config = get_config()
        self.logger = setup_logger("model_trainer")
        self.scaler = StandardScaler()
        self.label_encoder = LabelEncoder()

    def load_training_data(self) -> tuple[pd.DataFrame, pd.Series | None]:
        """加载训练数据"""
        try:
            data_path = self.config.paths.final_features_path
            self.logger.info(f"📊 加载训练数据: {data_path}")

            if not data_path.exists():
                self.logger.error(f"❌ 数据文件不存在: {data_path}")
                return None, None

            df = pd.read_csv(data_path)
            self.logger.info(f"✅ 数据加载成功: {len(df)} 条记录, {df.shape[1]} 个特征")

            # 数据清洗
            df = self._clean_data(df)

            # 特征工程
            X, y = self._prepare_features_and_target(df)

            return X, y

        except Exception as e:
            self.logger.error(f"❌ 数据加载失败: {e}")
            return None, None

    def _clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """数据清洗"""
        self.logger.info("🧹 开始数据清洗...")

        # 移除包含过多空值的行
        threshold = len(df.columns) * 0.7  # 70%以上非空
        df = df.dropna(thresh=threshold)

        # 填充缺失值
        numeric_columns = df.select_dtypes(include=[np.number]).columns
        df[numeric_columns] = df[numeric_columns].fillna(df[numeric_columns].median())

        # 移除异常值（简单的3倍标准差规则）
        for col in numeric_columns:
            if col in ["home_xg", "away_xg", "home_possession", "away_possession"]:
                mean_val = df[col].mean()
                std_val = df[col].std()
                df = df[(df[col] >= mean_val - 3 * std_val) & (df[col] <= mean_val + 3 * std_val)]

        self.logger.info(f"✅ 数据清洗完成: {len(df)} 条记录保留")
        return df

    def _prepare_features_and_target(self, df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
        """准备特征和目标变量"""
        # 核心特征列表
        feature_columns = [
            "home_avg_rating",
            "away_avg_rating",
            "home_big_chances_created",
            "away_big_chances_created",
            "home_total_shots",
            "away_total_shots",
            "home_shots_on_target",
            "away_shots_on_target",
            "home_possession",
            "away_possession",
            "home_xg",
            "away_xg",
            "home_corners",
            "away_corners",
            "home_red_cards",
            "away_red_cards",
            "home_substitutions",
            "away_substitutions",
            "home_early_goal",
            "away_early_goal",
            "home_penalties",
            "away_penalties",
            "home_xg_per_shot",
            "away_xg_per_shot",
            "rating_diff",
            "xg_diff",
            "xg_total",
            "possession_diff",
            "shots_diff",
            "corners_diff",
        ]

        # 确保特征列存在
        available_features = [col for col in feature_columns if col in df.columns]
        missing_features = set(feature_columns) - set(available_features)

        if missing_features:
            self.logger.warning(f"⚠️ 缺失特征: {missing_features}")
            # 创建缺失特征
            for col in missing_features:
                df[col] = 0

        X = df[feature_columns]

        # 创建目标变量：比赛结果
        y = self._create_target_variable(df)

        self.logger.info(f"✅ 特征准备完成: {X.shape[1]} 个特征")
        return X, y

    def _create_target_variable(self, df: pd.DataFrame) -> pd.Series:
        """创建目标变量（比赛结果）"""
        # 基于xG差值和评分差值推断比赛结果
        xg_diff = df["home_xg"] - df["away_xg"]
        rating_diff = df["rating_diff"]

        # 综合评分
        score_diff = xg_diff * 0.7 + rating_diff * 0.3

        # 创建三分类结果
        y = pd.Series(np.where(score_diff > 0.5, "home_win", np.where(score_diff < -0.5, "away_win", "draw")))

        # 编码为数值
        y_encoded = self.label_encoder.fit_transform(y)

        self.logger.info(f"✅ 目标变量创建完成: {y.value_counts().to_dict()}")
        return pd.Series(y_encoded)

    def train_model(self, X: pd.DataFrame, y: pd.Series) -> lgb.LGBMClassifier:
        """训练LightGBM模型"""
        try:
            self.logger.info("🏋️ 开始模型训练...")

            # 数据分割
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

            # 特征标准化
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)

            # LightGBM参数
            params = {
                "objective": "multiclass",
                "num_class": len(np.unique(y)),
                "metric": "multi_logloss",
                "boosting_type": "gbdt",
                "num_leaves": 31,
                "learning_rate": 0.05,
                "feature_fraction": 0.9,
                "bagging_fraction": 0.8,
                "bagging_freq": 5,
                "verbose": -1,
                "random_state": 42,
            }

            # 创建数据集
            train_data = lgb.Dataset(X_train_scaled, label=y_train)
            valid_data = lgb.Dataset(X_test_scaled, label=y_test, reference=train_data)

            # 训练模型
            model = lgb.train(
                params,
                train_data,
                valid_sets=[valid_data],
                num_boost_round=1000,
                callbacks=[lgb.early_stopping(stopping_rounds=50), lgb.log_evaluation(period=100)],
            )

            # 评估模型
            y_pred = model.predict(X_test_scaled, num_iteration=model.best_iteration)
            y_pred_class = np.argmax(y_pred, axis=1)

            accuracy = accuracy_score(y_test, y_pred_class)
            self.logger.info("✅ 模型训练完成!")
            self.logger.info(f"  最佳迭代数: {model.best_iteration}")
            self.logger.info(f"  测试准确率: {accuracy:.4f}")

            # 详细分类报告
            class_names = self.label_encoder.classes_
            report = classification_report(y_test, y_pred_class, target_names=class_names)
            self.logger.info(f"分类报告:\n{report}")

            return model

        except Exception as e:
            self.logger.error(f"❌ 模型训练失败: {e}")
            raise

    def save_model(self, model: lgb.LGBMClassifier) -> bool:
        """保存训练好的模型"""
        try:
            model_path = self.config.paths.current_model_path

            # 确保目录存在
            model_path.parent.mkdir(parents=True, exist_ok=True)

            # 保存模型
            model.save_model(str(model_path))
            self.logger.info(f"✅ 模型已保存: {model_path}")

            # 保存scaler
            scaler_path = model_path.parent / f"{model_path.stem}_scaler.pkl"
            with open(scaler_path, "wb") as f:
                pickle.dump(self.scaler, f)
            self.logger.info(f"✅ 特征缩放器已保存: {scaler_path}")

            # 保存label encoder
            encoder_path = model_path.parent / f"{model_path.stem}_encoder.pkl"
            with open(encoder_path, "wb") as f:
                pickle.dump(self.label_encoder, f)
            self.logger.info(f"✅ 标签编码器已保存: {encoder_path}")

            # 保存训练报告
            report_path = model_path.parent / f"training_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(report_path, "w", encoding="utf-8") as f:
                f.write("FootballPrediction V7.0 训练报告\n")
                f.write(f"训练时间: {datetime.now()}\n")
                f.write(f"模型路径: {model_path}\n")
                f.write(f"特征数量: {model.num_feature()}\n")
                f.write(f"树数量: {model.num_trees()}\n")
                f.write(f"最佳迭代数: {model.best_iteration}\n")

            return True

        except Exception as e:
            self.logger.error(f"❌ 模型保存失败: {e}")
            return False

    def run_training(self) -> bool:
        """运行完整的训练流程"""
        try:
            self.logger.info("🚀 开始模型训练流程")
            self.logger.info("=" * 50)

            # 加载数据
            X, y = self.load_training_data()
            if X is None or y is None:
                return False

            # 训练模型
            model = self.train_model(X, y)

            # 保存模型
            success = self.save_model(model)

            if success:
                self.logger.info("=" * 50)
                self.logger.info("🎉 模型训练完成!")
                self.logger.info(f"✅ 新模型已保存: {self.config.paths.current_model_path}")
                self.logger.info("=" * 50)

            return success

        except Exception as e:
            self.logger.error(f"❌ 训练流程失败: {e}")
            return False


def train_new_model() -> bool:
    """训练新模型的便利函数"""
    trainer = ModelTrainer()
    return trainer.run_training()
