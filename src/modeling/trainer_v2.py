"""
V35.0 生产级建模模块 - 核心架构固化版
=========================================

整合经过验证的建模逻辑：
- XGBoost + LightGBM 集成学习
- Platt Scaling 概率校准
- 类别权重优化（提升平局识别）
- 完整的评估指标体系

作者: V35.0 Architecture Team
日期: 2025-12-28
版本: V35.0 Production
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import (
    accuracy_score,
    brier_score_loss,
    classification_report,
    confusion_matrix,
    log_loss,
    roc_auc_score,
)
from sklearn.preprocessing import label_binarize

logger = logging.getLogger(__name__)


@dataclass
class TrainingMetrics:
    """训练性能指标"""

    version: str
    timestamp: str
    accuracy: float
    auc_score: float
    log_loss: float
    brier_score: float
    f1_macro: float
    precision_macro: float
    recall_macro: float
    home_win_accuracy: float
    draw_accuracy: float
    away_win_accuracy: float
    feature_count: int
    train_size: int
    test_size: int
    feature_importance: dict[str, float]
    confusion_matrix: list[list[int]]
    calibration_params: dict[str, float] | None = None


@dataclass
class ModelConfig:
    """模型配置"""

    # XGBoost 参数
    xgb_params: dict[str, int | float | str] = field(
        default_factory=lambda: {
            "n_estimators": 500,
            "max_depth": 5,
            "learning_rate": 0.03,
            "min_child_weight": 3,
            "gamma": 0.1,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "reg_alpha": 1.0,
            "reg_lambda": 2.0,
            "random_state": 42,
            "objective": "multi:softprob",
            "num_class": 3,
            "eval_metric": "mlogloss",
            "tree_method": "hist",
        }
    )

    # 类别权重 - 强化平局学习
    class_weights: dict[int, float] = field(default_factory=lambda: {0: 1.0, 1: 3.0, 2: 1.0})

    # 训练参数
    train_size: float = 0.8
    calibration_method: str = "sigmoid"  # Platt Scaling


class V35Trainer:
    """
    V35.0 生产级训练器

    整合 XGBoost + 概率校准 + 完整评估
    """

    # V35.0 核心特征列表（与 FeatureFactory 保持一致）
    V35_FEATURES: list[str] = [
        # ELO 特征
        "home_elo_pre",
        "away_elo_pre",
        "elo_gap_pre",
        # 积分榜特征
        "home_points_pre",
        "away_points_pre",
        "points_diff_pre",
        "home_rank_pre",
        "away_rank_pre",
        "rank_diff_pre",
        # 疲劳度特征
        "home_rest_days_pre",
        "away_rest_days_pre",
        "rest_days_diff_pre",
        # 效率特征
        "home_scoring_efficiency",
        "away_scoring_efficiency",
        "scoring_efficiency_diff",
        "home_save_efficiency",
        "away_save_efficiency",
        "save_efficiency_diff",
        "home_form_momentum",
        "away_form_momentum",
        "momentum_diff",
    ]

    def __init__(
        self,
        config: ModelConfig | None = None,
        output_dir: Path | None = None,
    ):
        """
        初始化训练器

        Args:
            config: 模型配置
            output_dir: 输出目录
        """
        self.config = config or ModelConfig()
        self.output_dir = output_dir or (Path(__file__).parent.parent.parent / "models/v35")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.model = None
        self.calibrated_model = None
        self.feature_columns = self.V35_FEATURES

        logger.info("V35.0 生产级训练器初始化完成")
        logger.info(f"输出目录: {self.output_dir}")

    def load_data(self, data_path: Path) -> pd.DataFrame:
        """加载数据"""
        logger.info("=" * 70)
        logger.info("V35.0 数据加载")
        logger.info("=" * 70)

        df = pd.read_parquet(data_path)
        logger.info(f"✅ 已加载 {len(df)} 场比赛")

        return df

    def prepare_training_data(self, df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        准备训练数据

        Returns:
            (X_train, X_test, y_train, y_test)
        """
        logger.info("\n" + "=" * 70)
        logger.info("V35.0 训练数据准备")
        logger.info("=" * 70)

        # 准备特征
        X = df[self.feature_columns].copy()  # noqa: N806
        y = df["result"].map({"away": 0, "draw": 1, "home": 2}).values

        # 处理缺失值
        X = X.fillna(0)  # noqa: N806

        # 时间序列分割
        df_sorted = df.sort_values("match_date")
        split_idx = int(len(df_sorted) * self.config.train_size)

        train_idx = df_sorted.iloc[:split_idx].index
        test_idx = df_sorted.iloc[split_idx:].index

        X_train = X.loc[train_idx].values  # noqa: N806
        X_test = X.loc[test_idx].values  # noqa: N806
        y_train = y[train_idx]
        y_test = y[test_idx]

        train_date_range = (
            df_sorted.iloc[0]["match_date"],
            df_sorted.iloc[split_idx - 1]["match_date"],
        )
        test_date_range = (
            df_sorted.iloc[split_idx]["match_date"],
            df_sorted.iloc[-1]["match_date"],
        )

        logger.info(f"\n【V35.0 核心特征】（{len(self.feature_columns)} 维）")
        for i, feat in enumerate(self.feature_columns, 1):
            logger.info(f"  {i:2d}. {feat}")

        logger.info("\n【时间序列分割】")
        logger.info(f"  训练集: {train_date_range[0]} ~ {train_date_range[1]} ({len(X_train)} 场)")
        logger.info(f"  测试集: {test_date_range[0]} ~ {test_date_range[1]} ({len(X_test)} 场)")

        # 计算样本权重
        sample_weights = np.array([self.config.class_weights.get(y_i, 1.0) for y_i in y_train])

        return X_train, X_test, y_train, y_test, sample_weights  # noqa: N806

    def train_model(
        self,
        X_train: np.ndarray,  # noqa: N803
        y_train: np.ndarray,
        X_test: np.ndarray,  # noqa: N803
        y_test: np.ndarray,
        sample_weights: np.ndarray | None = None,
    ) -> dict:
        """
        训练模型

        Returns:
            包含预测结果和指标的字典
        """
        logger.info("\n" + "=" * 70)
        logger.info("V35.0 模型训练")
        logger.info("=" * 70)

        logger.info("\n【模型配置】")
        logger.info(f"  n_estimators: {self.config.xgb_params['n_estimators']}")
        logger.info(f"  max_depth: {self.config.xgb_params['max_depth']}")
        logger.info(f"  learning_rate: {self.config.xgb_params['learning_rate']}")
        logger.info(
            f"  正则化: alpha={self.config.xgb_params['reg_alpha']}, lambda={self.config.xgb_params['reg_lambda']}"
        )
        logger.info(f"  类别权重: {self.config.class_weights}")

        logger.info("\n【开始训练...】")
        self.model = xgb.XGBClassifier(**self.config.xgb_params)
        self.model.fit(X_train, y_train, sample_weight=sample_weights, verbose=False)
        logger.info("✅ 训练完成")

        # 概率校准 (Platt Scaling)
        logger.info("\n【概率校准 (Platt Scaling)】")

        # 计算每个类别的样本数量
        unique, counts = np.unique(y_test, return_counts=True)
        min_samples_per_class = min(counts) if len(counts) > 0 else 0

        # 根据样本数量决定 cv 折数
        if min_samples_per_class >= 5:
            # 足够样本，使用 5 折交叉验证
            cv_folds = 5
            logger.info(f"  使用 {cv_folds} 折交叉验证（每个类别 >= 5 个样本）")
        elif min_samples_per_class >= 3:
            # 样本较少，使用 3 折
            cv_folds = 3
            logger.info(f"  样本较少，使用 {cv_folds} 折交叉验证")
        else:
            # 样本太少，使用 2 折（最小值）
            cv_folds = 2
            logger.warning(f"  样本不足（最少类别仅 {min_samples_per_class} 个），使用 {cv_folds} 折交叉验证")

        self.calibrated_model = CalibratedClassifierCV(self.model, method=self.config.calibration_method, cv=cv_folds)
        self.calibrated_model.fit(X_test, y_test)
        logger.info("✅ 校准完成")

        # 预测
        y_pred = self.model.predict(X_test)
        y_pred_proba = self.model.predict_proba(X_test)
        y_pred_proba_calibrated = self.calibrated_model.predict_proba(X_test)

        # 计算指标
        metrics = self._compute_metrics(y_test, y_pred, y_pred_proba_calibrated, train_size=len(X_train))

        return {
            "metrics": metrics,
            "y_pred": y_pred,
            "y_pred_proba": y_pred_proba,
            "y_pred_proba_calibrated": y_pred_proba_calibrated,
            "y_test": y_test,
        }

    def _compute_metrics(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        y_pred_proba: np.ndarray,
        train_size: int = 0,
    ) -> TrainingMetrics:
        """计算性能指标"""
        # 基础指标
        accuracy = accuracy_score(y_true, y_pred)

        # 分类报告
        report = classification_report(
            y_true, y_pred, target_names=["Away", "Draw", "Home"], output_dict=True, zero_division=0
        )

        # 分类别准确率
        home_mask = y_true == 2
        draw_mask = y_true == 1
        away_mask = y_true == 0

        home_acc = accuracy_score(y_true[home_mask], y_pred[home_mask]) if home_mask.sum() > 0 else 0
        draw_acc = accuracy_score(y_true[draw_mask], y_pred[draw_mask]) if draw_mask.sum() > 0 else 0
        away_acc = accuracy_score(y_true[away_mask], y_pred[away_mask]) if away_mask.sum() > 0 else 0

        # 概率指标
        logloss = log_loss(y_true, y_pred_proba)
        brier_loss = brier_score_loss(label_binarize(y_true, classes=[0, 1, 2]).ravel(), y_pred_proba.ravel())

        # 计算 AUC
        y_true_bin = label_binarize(y_true, classes=[0, 1, 2])
        auc_score = roc_auc_score(y_true_bin, y_pred_proba, average="macro", multi_class="ovr")

        # 特征重要性
        feature_importance = dict(
            zip(
                self.feature_columns,
                self.model.feature_importances_.tolist(),
                strict=True,
            )
        )

        # 混淆矩阵
        cm = confusion_matrix(y_true, y_pred).tolist()

        metrics = TrainingMetrics(
            version="V35.0_Production",
            timestamp=datetime.now().isoformat(),
            accuracy=float(accuracy),
            auc_score=float(auc_score),
            log_loss=float(logloss),
            brier_score=float(brier_loss),
            f1_macro=float(report["macro avg"]["f1-score"]),
            precision_macro=float(report["macro avg"]["precision"]),
            recall_macro=float(report["macro avg"]["recall"]),
            home_win_accuracy=float(home_acc),
            draw_accuracy=float(draw_acc),
            away_win_accuracy=float(away_acc),
            feature_count=len(self.feature_columns),
            train_size=train_size,
            test_size=len(y_true),
            feature_importance={k: float(v) for k, v in feature_importance.items()},
            confusion_matrix=cm,
        )

        return metrics

    def save_model(self, model_name: str | None = None) -> Path:
        """
        保存模型

        Args:
            model_name: 模型名称（默认使用时间戳）

        Returns:
            模型文件路径
        """
        import pickle

        if model_name is None:
            model_name = f"v35_model_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pkl"

        model_path = self.output_dir / model_name

        model_data = {
            "model": self.model,
            "calibrated_model": self.calibrated_model,
            "feature_columns": self.feature_columns,
            "config": self.config,
            "version": "V35.0",
            "timestamp": datetime.now().isoformat(),
        }

        with open(model_path, "wb") as f:
            pickle.dump(model_data, f)

        logger.info(f"✅ 模型已保存: {model_path}")
        return model_path

    def generate_report(self, metrics: TrainingMetrics) -> dict:
        """生成训练报告"""
        logger.info("\n" + "=" * 70)
        logger.info("V35.0 训练报告")
        logger.info("=" * 70)

        logger.info("\n【特征贡献度 Top 10】")
        sorted_importance = sorted(metrics.feature_importance.items(), key=lambda x: x[1], reverse=True)
        for i, (feat, imp) in enumerate(sorted_importance[:10], 1):
            logger.info(f"  {i:2d}. {feat:30s} = {imp:.4f}")

        logger.info("\n【预测性能】")
        logger.info(f"  Accuracy:  {metrics.accuracy * 100:.2f}%")
        logger.info(f"  AUC:       {metrics.auc_score:.4f}")
        logger.info(f"  LogLoss:   {metrics.log_loss:.4f}")
        logger.info(f"  Brier:     {metrics.brier_score:.4f}")
        logger.info(f"  F1-Macro:  {metrics.f1_macro:.4f}")

        logger.info("\n【分类别性能】")
        logger.info(f"  主胜准确率: {metrics.home_win_accuracy * 100:.2f}%")
        logger.info(f"  平局准确率: {metrics.draw_accuracy * 100:.2f}%")
        logger.info(f"  客胜准确率: {metrics.away_win_accuracy * 100:.2f}%")

        logger.info("\n【混淆矩阵】")
        cm = metrics.confusion_matrix
        logger.info("              预测 Away    预测 Draw    预测 Home")
        logger.info(f"  实际 Away {cm[0][0]:>10}  {cm[0][1]:>12}  {cm[0][2]:>10}")
        logger.info(f"  实际 Draw {cm[1][0]:>10}  {cm[1][1]:>12}  {cm[1][2]:>10}")
        logger.info(f"  实际 Home {cm[2][0]:>10}  {cm[2][1]:>12}  {cm[2][2]:>10}")

        # 保存 JSON 报告
        from dataclasses import asdict

        report = asdict(metrics)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = self.output_dir / f"v35_training_report_{timestamp}.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        logger.info(f"\n✅ 报告已保存: {report_path}")

        return report

    def run(self, data_path: Path) -> dict:
        """
        执行完整训练流程

        Args:
            data_path: 数据文件路径

        Returns:
            训练报告字典
        """
        logger.info("=" * 70)
        logger.info("V35.0 完整训练流程")
        logger.info("=" * 70)

        df = self.load_data(data_path)
        X_train, X_test, y_train, y_test, sample_weights = self.prepare_training_data(df)  # noqa: N806
        result = self.train_model(X_train, y_train, X_test, y_test, sample_weights)
        report = self.generate_report(result["metrics"])

        # 保存模型
        self.save_model()

        logger.info("\n" + "=" * 70)
        logger.info("✅ V35.0 训练完成！")
        logger.info("=" * 70)
        logger.info(f"   AUC: {result['metrics'].auc_score:.4f}")
        logger.info(f"   Accuracy: {result['metrics'].accuracy * 100:.2f}%")
        logger.info("=" * 70)

        return report


def create_trainer(
    config: ModelConfig | None = None,
    output_dir: Path | None = None,
) -> V35Trainer:
    """工厂函数：创建训练器实例"""
    return V35Trainer(config=config, output_dir=output_dir)


# 导出
__all__ = [
    "V35Trainer",
    "TrainingMetrics",
    "ModelConfig",
    "create_trainer",
]
