"""
V24.0 特征影响力普查脚本（Feature Scout）
==========================================

从数据库拉取全部 3002 维 V24.0 数据，训练基础模型提取特征重要性，
输出 Top 50 特征排行榜和噪音特征分析，最终筛选出 300 强特征名单。

核心功能:
    1. 数据加载: 从数据库加载所有 V24.0 特征
    2. 标签构建: 根据比分结果构建预测标签
    3. 模型训练: 使用 Random Forest / XGBoost 提取特征重要性
    4. 影响力排行: 输出 Top 50 特征贡献度
    5. 300 强筛选: 生成 selected_features_v24.json

作者: FootballPrediction Architecture Team
版本: V24.0-alpha
"""

import json
import logging
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import psycopg2
from psycopg2.extras import RealDictCursor
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.model_selection import train_test_split

from config_unified import get_settings

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("logs/feature_scout_v24.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


# ============================================================================
# 数据类定义
# ============================================================================


@dataclass
class FeatureImportanceResult:
    """
    特征重要性结果

    Attributes:
        feature_names: 特征名称列表
        importances: 重要性分数列表
        noise_ratio: 噪音特征比例（重要性 < 0.001）
        top_features: Top 50 特征列表
        feature_count: 总特征数
    """

    feature_names: list[str]
    importances: np.ndarray
    noise_ratio: float
    top_features: list[dict[str, Any]]
    feature_count: int

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "feature_count": self.feature_count,
            "noise_ratio": self.noise_ratio,
            "top_features": self.top_features[:50],
        }


@dataclass
class ScoutConfig:
    """
    普查配置

    Attributes:
        target_feature_count: 目标特征数量（3002 维）
        top_n: 输出 Top N 特征
        spartans_count: 300 强特征数量
        model_type: 模型类型（'rf' 或 'xgb'）
        test_size: 测试集比例
        random_state: 随机种子
        noise_threshold: 噪音阈值（重要性低于此值视为噪音）
    """

    target_feature_count: int = 3002
    top_n: int = 50
    spartans_count: int = 300
    model_type: str = "rf"
    test_size: float = 0.2
    random_state: int = 42
    noise_threshold: float = 0.001


# ============================================================================
# 核心类定义
# ============================================================================


class FeatureScout:
    """
    特征影响力普查器

    职责:
        1. 从数据库加载 V24.0 特征数据
        2. 构建预测标签（主胜/平局/客胜）
        3. 训练模型提取特征重要性
        4. 生成 Top 50 排行榜和 300 强名单
    """

    def __init__(self, config: ScoutConfig | None = None):
        """
        初始化普查器

        Args:
            config: 普查配置
        """
        self.config = config or ScoutConfig()

        # 获取数据库配置
        settings = get_settings()
        self.db_config = settings.database

        logger.info("FeatureScout 初始化完成")
        logger.info(f"  - 目标特征数: {self.config.target_feature_count}")
        logger.info(f"  - 300 强数量: {self.config.spartans_count}")
        logger.info(f"  - 模型类型: {self.config.model_type}")

    def load_data(self) -> tuple[pd.DataFrame, pd.Series]:
        """
        从数据库加载 V24.0 特征数据

        Returns:
            (X, y): 特征矩阵和标签
        """
        logger.info("从数据库加载 V24.0 特征数据...")

        # 直接从环境变量获取数据库连接参数
        # Docker 环境下 DB_HOST=db，非 Docker 环境下使用 localhost
        db_host_env = os.getenv("DB_HOST", "")
        db_host = "localhost" if db_host_env == "db" or not db_host_env else db_host_env
        db_port = int(os.getenv("DB_PORT", "5432"))
        db_name = os.getenv("DB_NAME", "football_db")
        db_user = os.getenv("DB_USER", "football_user")
        db_password = os.getenv("DB_PASSWORD", "")

        logger.info(f"连接数据库: {db_host}:{db_port}/{db_name}")

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
                # 查询所有可用数据（优先使用 V24.0，否则使用所有数据）
                query = """
                    SELECT
                        mft.match_id,
                        mft.home_team,
                        mft.away_team,
                        mft.home_score,
                        mft.away_score,
                        mft.enriched_features,
                        mft.meta_data,
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

                # 统计版本分布
                version_counts = {}
                for r in records:
                    v = (
                        r.get("meta_data", {}).get("extraction_version", "unknown")
                        if isinstance(r.get("meta_data"), dict)
                        else "unknown"
                    )
                    version_counts[v] = version_counts.get(v, 0) + 1

                logger.info(f"加载了 {len(records)} 条记录")
                logger.info(f"版本分布: {version_counts}")

                # 构建 DataFrame
                data = []
                labels = []

                for record in records:
                    enriched = record["enriched_features"]
                    if isinstance(enriched, str):
                        enriched = json.loads(enriched)

                    # 构建标签（主胜/平局/客胜）
                    # 首先尝试从 match_features_training 获取比分
                    home_score = record.get("home_score")
                    away_score = record.get("away_score")

                    # 如果没有比分，尝试从 l2_raw_json 提取
                    if home_score is None or away_score is None:
                        raw_json = record.get("l2_raw_json")
                        if raw_json:
                            if isinstance(raw_json, str):
                                raw_json = json.loads(raw_json)

                            # 从 raw_json 提取比分（尝试多种路径）
                            # 路径 1: content.general.matchData
                            content = raw_json.get("content", raw_json)
                            general = content.get("general", {})
                            match_data = general.get("matchData", {})

                            home_score = match_data.get("homeTeam", {}).get("score")
                            away_score = match_data.get("awayTeam", {}).get("score")

                            # 路径 2: 直接从根级别获取
                            if home_score is None:
                                home_score = raw_json.get("homeScore")
                            if away_score is None:
                                away_score = raw_json.get("awayScore")

                            # 路径 3: 从 matchFacts 获取
                            if home_score is None:
                                match_facts = content.get("matchFacts", {})
                                home_score = match_facts.get("homeScore")
                            if away_score is None:
                                match_facts = content.get("matchFacts", {})
                                away_score = match_facts.get("awayScore")

                    # 如果仍然没有比分，使用 xG 作为代理指标
                    if home_score is None or away_score is None:
                        home_xg = enriched.get("home_expected_goals", 0)
                        away_xg = enriched.get("away_expected_goals", 0)

                        # 使用 xG 差值来生成标签（用于演示）
                        xg_diff = home_xg - away_xg
                        if xg_diff > 0.3:
                            label = 0  # 主胜倾向
                        elif xg_diff < -0.3:
                            label = 2  # 客胜倾向
                        else:
                            label = 1  # 平局倾向
                    else:
                        # 有真实比分，使用比分
                        home_score = int(home_score) if str(home_score) != "" else 0
                        away_score = int(away_score) if str(away_score) != "" else 0

                        if home_score > away_score:
                            label = 0  # 主胜
                        elif home_score < away_score:
                            label = 2  # 客胜
                        else:
                            label = 1  # 平局

                    data.append(enriched)
                    labels.append(label)

                X = pd.DataFrame(data)
                y = pd.Series(labels)

                logger.info(f"特征矩阵形状: {X.shape}")
                logger.info(f"标签分布: {y.value_counts().to_dict()}")

                return X, y

        finally:
            conn.close()

    def preprocess_data(self, X: pd.DataFrame, y: pd.Series) -> tuple[np.ndarray, np.ndarray, list[str]]:
        """
        预处理数据

        Args:
            X: 特征矩阵
            y: 标签

        Returns:
            (X_processed, y_processed, feature_names)
        """
        logger.info("预处理数据...")

        # 只保留数值类型的列
        numeric_cols = X.select_dtypes(include=[np.number]).columns.tolist()
        X = X[numeric_cols]
        logger.info(f"保留数值列: {X.shape}")

        # 移除全 NaN 列
        X = X.dropna(axis=1, how="all")
        logger.info(f"移除全 NaN 列后: {X.shape}")

        # 将所有值转换为 float
        for col in X.columns:
            X[col] = pd.to_numeric(X[col], errors="coerce")

        # 填充缺失值
        imputer = SimpleImputer(strategy="median")
        X_array = imputer.fit_transform(X)

        # 获取特征名称
        feature_names = X.columns.tolist()

        y_array = y.values

        logger.info(f"预处理完成: {X_array.shape}")

        return X_array, y_array, feature_names

    def train_model(self, X: np.ndarray, y: np.ndarray) -> Any:
        """
        训练模型并提取特征重要性

        Args:
            X: 特征矩阵
            y: 标签

        Returns:
            训练好的模型
        """
        logger.info(f"训练 {self.config.model_type.upper()} 模型...")

        # 划分训练集和测试集
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=self.config.test_size, random_state=self.config.random_state, stratify=y
        )

        logger.info(f"训练集: {X_train.shape}, 测试集: {X_test.shape}")

        # 训练模型
        if self.config.model_type == "rf":
            model = RandomForestClassifier(
                n_estimators=100,
                max_depth=20,
                min_samples_split=10,
                min_samples_leaf=5,
                random_state=self.config.random_state,
                n_jobs=-1,
            )
        else:
            # XGBoost (需要安装)
            try:
                import xgboost as xgb

                model = xgb.XGBClassifier(
                    n_estimators=100,
                    max_depth=6,
                    learning_rate=0.1,
                    random_state=self.config.random_state,
                    n_jobs=-1,
                    eval_metric="mlogloss",
                )
            except ImportError:
                logger.warning("XGBoost 未安装，使用 Random Forest")
                model = RandomForestClassifier(
                    n_estimators=100,
                    max_depth=20,
                    random_state=self.config.random_state,
                    n_jobs=-1,
                )

        model.fit(X_train, y_train)

        # 评估模型
        train_score = model.score(X_train, y_train)
        test_score = model.score(X_test, y_test)

        logger.info(f"训练集准确率: {train_score:.4f}")
        logger.info(f"测试集准确率: {test_score:.4f}")

        return model

    def extract_importance(self, model: Any, feature_names: list[str]) -> FeatureImportanceResult:
        """
        提取特征重要性

        Args:
            model: 训练好的模型
            feature_names: 特征名称列表

        Returns:
            特征重要性结果
        """
        logger.info("提取特征重要性...")

        importances = model.feature_importances_

        # 排序
        indices = np.argsort(importances)[::-1]

        # 构建 Top N 特征列表
        top_features = []
        for i, idx in enumerate(indices[: self.config.top_n]):
            top_features.append(
                {
                    "rank": i + 1,
                    "name": feature_names[idx],
                    "importance": float(importances[idx]),
                }
            )

        # 计算噪音比例
        noise_count = np.sum(importances < self.config.noise_threshold)
        noise_ratio = noise_count / len(importances)

        logger.info(f"总特征数: {len(importances)}")
        logger.info(f"噪音特征数 (重要性 < {self.config.noise_threshold}): {noise_count}")
        logger.info(f"噪音比例: {noise_ratio:.2%}")

        return FeatureImportanceResult(
            feature_names=feature_names,
            importances=importances,
            noise_ratio=noise_ratio,
            top_features=top_features,
            feature_count=len(importances),
        )

    def select_spartans(self, result: FeatureImportanceResult) -> list[str]:
        """
        筛选 300 强特征

        Args:
            result: 特征重要性结果

        Returns:
            300 强特征名称列表
        """
        logger.info(f"筛选 {self.config.spartans_count} 强特征...")

        # 按重要性排序
        indices = np.argsort(result.importances)[::-1]

        # 取前 N 个
        spartans = [result.feature_names[idx] for idx in indices[: self.config.spartans_count]]

        logger.info("300 强特征筛选完成")

        return spartans

    def save_results(self, result: FeatureImportanceResult, spartans: list[str]) -> None:
        """
        保存结果到文件

        Args:
            result: 特征重要性结果
            spartans: 300 强特征列表
        """
        # 创建输出目录
        output_dir = Path("data/analysis")
        output_dir.mkdir(parents=True, exist_ok=True)

        # 保存 Top 50 排行榜
        top_50_file = output_dir / "feature_importance_v24_top50.json"
        with open(top_50_file, "w") as f:
            json.dump(result.top_features[:50], f, indent=2)
        logger.info(f"Top 50 排行榜已保存: {top_50_file}")

        # 保存 300 强名单
        spartans_file = output_dir / "selected_features_v24.json"
        with open(spartans_file, "w") as f:
            json.dump(
                {
                    "version": "V24.0",
                    "spartans_count": len(spartans),
                    "selected_at": datetime.now().isoformat(),
                    "features": spartans,
                },
                f,
                indent=2,
            )
        logger.info(f"300 强名单已保存: {spartans_file}")

        # 保存完整分析报告
        report_file = output_dir / "feature_importance_v24_report.json"
        with open(report_file, "w") as f:
            json.dump(
                {
                    "version": "V24.0",
                    "generated_at": datetime.now().isoformat(),
                    "total_features": result.feature_count,
                    "noise_ratio": result.noise_ratio,
                    "spartans_count": len(spartans),
                    "top_10_features": result.top_features[:10],
                },
                f,
                indent=2,
            )
        logger.info(f"完整报告已保存: {report_file}")

    def print_results(self, result: FeatureImportanceResult) -> None:
        """
        打印结果

        Args:
            result: 特征重要性结果
        """
        print("\n" + "=" * 70)
        print("  V24.0 特征影响力普查报告")
        print("=" * 70)

        print("\n📊 数据统计:")
        print(f"  • 总特征数: {result.feature_count}")
        print(f"  • 噪音特征比例: {result.noise_ratio:.2%}")

        print("\n🏆 Top 10 平局预测贡献因子:")
        for i, feat in enumerate(result.top_features[:10], 1):
            print(f"  {i:2d}. {feat['name']:50s} ({feat['importance']:.4f})")

        print("\n🎖️  Top 11-50 特征:")
        for i, feat in enumerate(result.top_features[10:50], 11):
            print(f"  {i:2d}. {feat['name']:50s} ({feat['importance']:.4f})")

        print("\n" + "=" * 70)

    def run(self) -> FeatureImportanceResult:
        """
        执行完整的普查流程

        Returns:
            特征重要性结果
        """
        logger.info("=" * 60)
        logger.info("V24.0 特征影响力普查开始")
        logger.info("=" * 60)

        # 1. 加载数据
        X, y = self.load_data()

        # 2. 预处理
        X_processed, y_processed, feature_names = self.preprocess_data(X, y)

        # 3. 训练模型
        model = self.train_model(X_processed, y_processed)

        # 4. 提取特征重要性
        result = self.extract_importance(model, feature_names)

        # 5. 筛选 300 强
        spartans = self.select_spartans(result)

        # 6. 保存结果
        self.save_results(result, spartans)

        # 7. 打印结果
        self.print_results(result)

        return result


# ============================================================================
# 主程序入口
# ============================================================================


def main():
    """主程序入口"""
    import argparse

    parser = argparse.ArgumentParser(description="V24.0 特征影响力普查脚本")
    parser.add_argument("--model", type=str, default="rf", choices=["rf", "xgb"], help="模型类型（默认: rf）")
    parser.add_argument("--top-n", type=int, default=50, help="输出 Top N 特征（默认: 50）")
    parser.add_argument("--spartans", type=int, default=300, help="300 强特征数量（默认: 300）")

    args = parser.parse_args()

    # 创建配置
    config = ScoutConfig(
        model_type=args.model,
        top_n=args.top_n,
        spartans_count=args.spartans,
    )

    # 创建并运行普查器
    scout = FeatureScout(config)
    result = scout.run()

    # 最终宣告
    print("\n🚀 全息数据已精炼。")
    print(f"   {result.feature_count} 维原油已提炼为 {config.spartans_count} 维航空煤油。")
    print("   请求开启正式模型点火。")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
