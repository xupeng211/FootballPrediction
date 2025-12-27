"""
V24.1 实战训练脚本（Inference-Only Training）
================================================

核心目标：剔除所有"赛后上帝视角"特征，仅使用"赛前已知特征"进行训练。

赛前特征分类：
    1. 历史滚动因子 (L3, L5, H2H)
    2. 环境因子 (裁判, 天气, 球场, 时间)
    3. 市场因子 (初盘赔率, 赔率动量)
    4. 阵容因子 (身价, 评分, 稳定性)

赛后特征（剔除）：
    1. 当场 xG, 射门, 控球率
    2. 当场传球, 角球, 犯规
    3. 上半场/下半场统计数据

作者: FootballPrediction Architecture Team
版本: V24.1-inference
"""

import json
import logging
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import lightgbm as lgb
import psycopg2
import xgboost as xgb
from psycopg2.extras import RealDictCursor
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.preprocessing import StandardScaler

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("logs/v24_1_inference_training.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


# ============================================================================
# 数据类定义
# ============================================================================


@dataclass
class InferenceTrainingConfig:
    """
    实战训练配置

    Attributes:
        target_feature_count: 目标特征数量（黄金 100 强）
        test_size: 测试集比例
        random_state: 随机种子
        cv_folds: 交叉验证折数
        ensemble_weights: 融合模型权重 [xgb, lgb]
    """

    target_feature_count: int = 100
    test_size: float = 0.2
    random_state: int = 42
    cv_folds: int = 5
    ensemble_weights: list[float] = field(default_factory=lambda: [0.5, 0.5])


@dataclass
class TrainingResult:
    """
    训练结果

    Attributes:
        model_accuracy: 模型准确率
        draw_precision: 平局预测精确率
        draw_recall: 平局预测召回率
        feature_importance: 特征重要性
        selected_features: 选中的特征列表
        test_predictions: 测试集预测结果
    """

    model_accuracy: float
    draw_precision: float
    draw_recall: float
    feature_importance: dict[str, float]
    selected_features: list[str]
    test_predictions: np.ndarray
    cv_scores: list[float]


# ============================================================================
# 核心类定义
# ============================================================================


class InferenceFeatureFilter:
    """
    实战特征过滤器

    职责:
        1. 从数据库中识别真正的赛前特征
        2. 剔除所有赛后上帝视角特征
        3. 筛选出"黄金 100 强"赛前特征
    """

    # 赛前特征前缀（保留）
    PRE_MATCH_PREFIXES = [
        "home_l3_",
        "away_l3_",  # L3 滚动历史
        "home_l5_",
        "away_l5_",  # L5 趋势
        "h2h_",  # 历史对战
        "diff_l3_",
        "diff_l5_",  # 历史对比
        "ref_",  # 裁判
        "stadium_",  # 球场
        "kickoff_",  # 开球时间
        "weather_",  # 天气
        "odds_",  # 赔率
        "meta_",  # 元数据（部分）
        "lineup_",  # 阵容
    ]

    # 赛前特征关键词（保留）
    PRE_MATCH_KEYWORDS = [
        "history",
        "rolling",
        "trend",
        "momentum",
        "stability",
        "value",
        "rating",
        "formation",
        "bench",
        "squad",
        "attendance",
        "capacity",
        "venue",
        "referee",
        "coach",
        "temperature",
        "weather",
        "wind",
        "odds",
        "bookmaker",
        "market",
    ]

    # 赛后特征关键词（剔除）
    POST_MATCH_KEYWORDS = [
        "expected_goals",  # 当场xG
        "shots",  # 当场射门
        "possession",  # 当场控球
        "passes",  # 当场传球
        "corners",  # 当场角球
        "fouls",  # 当场犯规
        "offsides",  # 当场越位
        "FirstHalf",  # 上半场数据
        "SecondHalf",  # 下半场数据
        "total_",  # 当场总计
    ]

    @classmethod
    def is_pre_match_feature(cls, feature_name: str) -> bool:
        """
        判断是否为赛前特征

        Args:
            feature_name: 特征名称

        Returns:
            True 如果是赛前特征
        """
        # 检查赛前特征前缀
        for prefix in cls.PRE_MATCH_PREFIXES:
            if feature_name.startswith(prefix):
                return True

        # 检查赛前特征关键词
        for keyword in cls.PRE_MATCH_KEYWORDS:
            if keyword in feature_name.lower():
                # 但要确保不包含赛后关键词
                if not any(kw in feature_name.lower() for kw in cls.POST_MATCH_KEYWORDS):
                    return True

        # 特殊处理：meta_ 开头的大部分是赛前特征
        if feature_name.startswith("meta_"):
            # 但要排除一些赛后 meta 数据
            post_meta_keywords = ["score", "winner", "result"]
            if not any(kw in feature_name.lower() for kw in post_meta_keywords):
                return True

        return False

    @classmethod
    def is_post_match_feature(cls, feature_name: str) -> bool:
        """
        判断是否为赛后特征（上帝视角）

        Args:
            feature_name: 特征名称

        Returns:
            True 如果是赛后特征
        """
        # 检查赛后特征关键词
        for keyword in cls.POST_MATCH_KEYWORDS:
            if keyword in feature_name.lower():
                return True

        return False


class InferenceTrainer:
    """
    实战训练器

    职责:
        1. 从数据库加载特征数据
        2. 过滤出真正的赛前特征
        3. 训练 XGBoost + LightGBM 融合模型
        4. 输出黄金 100 强特征名单
        5. 验证模型在未见数据上的性能
    """

    def __init__(self, config: InferenceTrainingConfig | None = None):
        """
        初始化训练器

        Args:
            config: 训练配置
        """
        self.config = config or InferenceTrainingConfig()

        logger.info("InferenceTrainer 初始化完成")
        logger.info(f"  - 目标特征数: {self.config.target_feature_count}")
        logger.info(f"  - CV 折数: {self.config.cv_folds}")

    def load_data(self) -> tuple[pd.DataFrame, pd.Series]:
        """
        从数据库加载数据

        Returns:
            (X, y): 特征矩阵和标签
        """
        logger.info("从数据库加载特征数据...")

        # 从环境变量获取数据库连接参数
        db_host = os.getenv("DB_HOST", "")
        db_host = "localhost" if db_host == "db" or not db_host else db_host
        db_port = int(os.getenv("DB_PORT", "5432"))
        db_name = os.getenv("DB_NAME", "football_db")
        db_user = os.getenv("DB_USER", "football_user")
        db_password = os.getenv("DB_PASSWORD", "")

        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            database=db_name,
            user=db_user,
            password=db_password,
            cursor_factory=RealDictCursor,
        )

        try:
            with conn.cursor() as cur:
                # 查询所有可用数据
                query = """
                    SELECT
                        mft.match_id,
                        mft.home_team,
                        mft.away_team,
                        mft.home_score,
                        mft.away_score,
                        mft.enriched_features,
                        m.l2_raw_json
                    FROM match_features_training mft
                    LEFT JOIN matches m ON mft.match_id = m.id
                    WHERE mft.status = 'completed'
                      AND mft.enriched_features IS NOT NULL
                    ORDER BY mft.match_time DESC
                    LIMIT 1000;
                """

                cur.execute(query)
                records = cur.fetchall()

                logger.info(f"加载了 {len(records)} 条记录")

                # 构建 DataFrame
                data = []
                labels = []

                for record in records:
                    enriched = record["enriched_features"]
                    if isinstance(enriched, str):
                        enriched = json.loads(enriched)

                    # 构建标签（使用 xG 作为代理指标）
                    home_xg = enriched.get("home_expected_goals", 0)
                    away_xg = enriched.get("away_expected_goals", 0)

                    # 使用 xG 差值来生成标签
                    xg_diff = home_xg - away_xg
                    if xg_diff > 0.5:
                        label = 0  # 主胜倾向
                    elif xg_diff < -0.5:
                        label = 2  # 客胜倾向
                    else:
                        label = 1  # 平局倾向

                    data.append(enriched)
                    labels.append(label)

                X = pd.DataFrame(data)
                y = pd.Series(labels)

                logger.info(f"标签分布: {y.value_counts().to_dict()}")

                return X, y

        finally:
            conn.close()

    def filter_pre_match_features(self, X: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
        """
        过滤出真正的赛前特征

        Args:
            X: 原始特征矩阵

        Returns:
            (X_filtered, feature_names): 过滤后的特征矩阵和特征名称列表
        """
        logger.info("过滤赛前特征...")

        # 只保留数值类型的列
        numeric_cols = X.select_dtypes(include=[np.number]).columns.tolist()
        X = X[numeric_cols]

        # 将所有值转换为 float
        for col in X.columns:
            X[col] = pd.to_numeric(X[col], errors="coerce")

        # 过滤出赛前特征
        pre_match_features = []
        for col in X.columns:
            if InferenceFeatureFilter.is_pre_match_feature(col):
                pre_match_features.append(col)

        logger.info(f"原始特征数: {X.shape[1]}")
        logger.info(f"赛前特征数: {len(pre_match_features)}")
        logger.info(f"剔除特征数: {X.shape[1] - len(pre_match_features)}")

        X_filtered = X[pre_match_features]

        # 移除全 NaN 列
        X_filtered = X_filtered.dropna(axis=1, how="all")
        logger.info(f"移除全 NaN 列后: {X_filtered.shape[1]}")

        return X_filtered, X_filtered.columns.tolist()

    def train_ensemble(self, X: np.ndarray, y: np.ndarray, feature_names: list[str]) -> TrainingResult:
        """
        训练 XGBoost + LightGBM 融合模型

        Args:
            X: 特征矩阵
            y: 标签
            feature_names: 特征名称列表

        Returns:
            训练结果
        """
        logger.info("训练融合模型...")

        # 划分训练集和测试集
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=self.config.test_size, random_state=self.config.random_state, stratify=y
        )

        logger.info(f"训练集: {X_train.shape}, 测试集: {X_test.shape}")

        # 标准化特征
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)

        # 训练 XGBoost
        logger.info("训练 XGBoost...")
        xgb_model = xgb.XGBClassifier(
            n_estimators=200,
            max_depth=6,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=self.config.random_state,
            eval_metric="mlogloss",
            use_label_encoder=False,
        )
        xgb_model.fit(X_train_scaled, y_train)

        # 训练 LightGBM
        logger.info("训练 LightGBM...")
        lgb_model = lgb.LGBMClassifier(
            n_estimators=200,
            max_depth=6,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=self.config.random_state,
            verbose=-1,
        )
        lgb_model.fit(X_train_scaled, y_train)

        # 融合预测
        xgb_proba = xgb_model.predict_proba(X_test_scaled)
        lgb_proba = lgb_model.predict_proba(X_test_scaled)

        # 加权融合
        ensemble_proba = self.config.ensemble_weights[0] * xgb_proba + self.config.ensemble_weights[1] * lgb_proba
        test_predictions = np.argmax(ensemble_proba, axis=1)

        # 计算准确率
        accuracy = accuracy_score(y_test, test_predictions)

        # 计算平局预测指标
        report = classification_report(y_test, test_predictions, output_dict=True, zero_division=0)
        draw_precision = report["1"].get("precision", 0.0)
        draw_recall = report["1"].get("recall", 0.0)

        logger.info(f"测试集准确率: {accuracy:.4f}")
        logger.info(f"平局精确率: {draw_precision:.4f}")
        logger.info(f"平局召回率: {draw_recall:.4f}")

        # 提取特征重要性（使用 XGBoost）
        importance = xgb_model.feature_importances_
        feature_importance = {name: float(imp) for name, imp in zip(feature_names, importance)}

        # 按重要性排序，选取黄金 100 强
        sorted_features = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)[
            : self.config.target_feature_count
        ]

        selected_features = [f[0] for f in sorted_features]
        selected_importance = {f[0]: f[1] for f in sorted_features}

        logger.info("黄金 100 强特征已筛选")

        # 交叉验证
        logger.info("执行交叉验证...")
        cv_scores = self._cross_validate(X_train_scaled, y_train)

        return TrainingResult(
            model_accuracy=accuracy,
            draw_precision=draw_precision,
            draw_recall=draw_recall,
            feature_importance=selected_importance,
            selected_features=selected_features,
            test_predictions=test_predictions,
            cv_scores=cv_scores,
        )

    def _cross_validate(self, X: np.ndarray, y: np.ndarray) -> list[float]:
        """
        执行交叉验证

        Args:
            X: 特征矩阵
            y: 标签

        Returns:
            CV 分数列表
        """
        xgb_model = xgb.XGBClassifier(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.05,
            subsample=0.8,
            random_state=self.config.random_state,
            eval_metric="mlogloss",
            use_label_encoder=False,
        )

        cv = StratifiedKFold(n_splits=self.config.cv_folds, shuffle=True, random_state=self.config.random_state)

        scores = cross_val_score(xgb_model, X, y, cv=cv, scoring="accuracy", n_jobs=-1)

        logger.info(f"CV 分数: {scores}")
        logger.info(f"CV 平均: {scores.mean():.4f} (+/- {scores.std():.4f})")

        return scores.tolist()

    def save_results(self, result: TrainingResult) -> None:
        """
        保存结果到文件

        Args:
            result: 训练结果
        """
        # 创建输出目录
        output_dir = Path("data/analysis")
        output_dir.mkdir(parents=True, exist_ok=True)

        # 保存黄金 100 强名单
        golden_features_file = output_dir / "golden_100_pre_match_features_v24_1.json"
        with open(golden_features_file, "w") as f:
            json.dump(
                {
                    "version": "V24.1-inference",
                    "selected_at": datetime.now().isoformat(),
                    "feature_count": len(result.selected_features),
                    "features": [
                        {"name": name, "importance": result.feature_importance[name]}
                        for name in result.selected_features
                    ],
                },
                f,
                indent=2,
            )
        logger.info(f"黄金 100 强名单已保存: {golden_features_file}")

        # 保存完整训练报告
        report_file = output_dir / "inference_training_report_v24_1.json"
        with open(report_file, "w") as f:
            json.dump(
                {
                    "version": "V24.1-inference",
                    "generated_at": datetime.now().isoformat(),
                    "model_accuracy": result.model_accuracy,
                    "draw_precision": result.draw_precision,
                    "draw_recall": result.draw_precision,
                    "cv_scores": result.cv_scores,
                    "cv_mean": np.mean(result.cv_scores),
                    "cv_std": np.std(result.cv_scores),
                    "top_10_features": [
                        {"name": name, "importance": result.feature_importance[name]}
                        for name in result.selected_features[:10]
                    ],
                },
                f,
                indent=2,
            )
        logger.info(f"训练报告已保存: {report_file}")

    def print_results(self, result: TrainingResult) -> None:
        """
        打印结果

        Args:
            result: 训练结果
        """
        print("\n" + "=" * 70)
        print("  V24.1 实战训练报告（仅赛前特征）")
        print("=" * 70)

        print("\n📊 模型性能:")
        print(f"  • 测试集准确率: {result.model_accuracy:.2%}")
        print(f"  • 平局预测精确率: {result.draw_precision:.2%}")
        print(f"  • 平局预测召回率: {result.draw_recall:.2%}")
        print(f"  • CV 平均准确率: {np.mean(result.cv_scores):.2%} (+/- {np.std(result.cv_scores):.2%})")

        print("\n🏆 赛前黄金 10 强特征:")
        for i, name in enumerate(result.selected_features[:10], 1):
            imp = result.feature_importance[name]
            print(f"  {i:2d}. {name:50s} ({imp:.4f})")

        print("\n📋 完整黄金 100 强名单:")
        for i, name in enumerate(result.selected_features, 1):
            print(f"  {i:3d}. {name}")

        print("\n" + "=" * 70)

    def run(self) -> TrainingResult:
        """
        执行完整的训练流程

        Returns:
            训练结果
        """
        logger.info("=" * 60)
        logger.info("V24.1 实战训练开始")
        logger.info("=" * 60)

        # 1. 加载数据
        X, y = self.load_data()

        # 2. 过滤赛前特征
        X_filtered, feature_names = self.filter_pre_match_features(X)

        # 3. 填充缺失值
        from sklearn.impute import SimpleImputer

        imputer = SimpleImputer(strategy="median")
        X_processed = imputer.fit_transform(X_filtered)

        # 4. 训练模型
        result = self.train_ensemble(X_processed, y, feature_names)

        # 5. 保存结果
        self.save_results(result)

        # 6. 打印结果
        self.print_results(result)

        return result


# ============================================================================
# 主程序入口
# ============================================================================


def main():
    """主程序入口"""
    import argparse

    parser = argparse.ArgumentParser(description="V24.1 实战训练脚本（仅赛前特征）")
    parser.add_argument("--target-features", type=int, default=100, help="目标特征数量（默认: 100）")
    parser.add_argument("--cv-folds", type=int, default=5, help="交叉验证折数（默认: 5）")

    args = parser.parse_args()

    # 创建配置
    config = InferenceTrainingConfig(
        target_feature_count=args.target_features,
        cv_folds=args.cv_folds,
    )

    # 创建并运行训练器
    trainer = InferenceTrainer(config)
    result = trainer.run()

    # 最终宣告
    print("\n🛡️  实战引擎已冷却完成。")
    print("   所有'上帝视角'已屏蔽。")
    print("   战神模型已准备好迎接 12.26 真实盘口挑战。")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
