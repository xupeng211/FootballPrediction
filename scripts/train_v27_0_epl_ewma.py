#!/usr/bin/env python3
"""
V27.0 英超量化预测模型 - EWMA + 主客场拆分 + 对手强度修正
==========================================================

核心升级:
1. EWMA (指数加权移动平均) 替代简单移动平均
2. 主客场表现拆分 (Venue-Specific Features)
3. 对手强度修正 (Strength Adjustment)
4. ROC-AUC 评估

作者: Senior Quant Analyst
日期: 2025-12-29
Phase: V27.0 Quant Model (EWMA + SoS + Split)
"""

import sys
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

import joblib
import matplotlib
import numpy as np
import pandas as pd
import psycopg2
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    log_loss,
    roc_auc_score,
)
from tabulate import tabulate
from xgboost import XGBClassifier

matplotlib.use("Agg")
import matplotlib.pyplot as plt

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config_unified import get_settings

# ============================================
# 数据提取
# ============================================


def fetch_all_match_data():
    """提取所有比赛数据"""
    settings = get_settings()

    conn = psycopg2.connect(
        host=settings.database.host,
        port=settings.database.port,
        database=settings.database.name,
        user=settings.database.user,
        password=settings.database.password.get_secret_value(),
    )

    query = """
    SELECT
        rmd.match_id,
        m.league_id,
        m.season,
        m.match_date,
        m.home_team,
        m.away_team,
        m.home_team_id,
        m.away_team_id,

        -- 当场比赛统计（用于构建未来的滚动窗口）
        mf.home_xg::DOUBLE PRECISION,
        mf.away_xg::DOUBLE PRECISION,
        mf.home_possession::DOUBLE PRECISION,
        mf.away_possession::DOUBLE PRECISION,
        mf.home_shots_on_target::INTEGER,
        mf.away_shots_on_target::INTEGER,
        mf.home_big_chances::INTEGER,
        mf.away_big_chances::INTEGER,
        mf.home_avg_player_rating::DOUBLE PRECISION,
        mf.away_avg_player_rating::DOUBLE PRECISION,

        -- 比分
        CAST(rmd.raw_data#>'{raw_data,header,teams,0,score}' AS INTEGER) as home_score,
        CAST(rmd.raw_data#>'{raw_data,header,teams,1,score}' AS INTEGER) as away_score
    FROM match_features_v1 mf
    JOIN raw_match_data rmd ON mf.match_id = rmd.match_id
    JOIN matches m ON mf.match_id = m.match_id
    WHERE m.league_id = 47
        AND mf.extraction_quality = 'full'
        AND mf.valid_feature_count >= 10
        AND rmd.raw_data#>'{raw_data,header,teams,0,score}' IS NOT NULL
        AND rmd.raw_data#>'{raw_data,header,teams,1,score}' IS NOT NULL
    ORDER BY m.match_date, m.match_id
    """

    df = pd.read_sql_query(query, conn)
    conn.close()

    df["match_date"] = pd.to_datetime(df["match_date"])

    return df


# ============================================
# EWMA 计算器
# ============================================


class EWMACalculator:
    """指数加权移动平均计算器"""

    def __init__(self, alpha=0.3, min_periods=1):
        """
        Args:
            alpha: 平滑系数 (0-1)，越小对历史数据影响越大
            min_periods: 最小观测数
        """
        self.alpha = alpha
        self.min_periods = min_periods

    def update(self, history, new_value):
        """
        更新 EWMA 值

        Args:
            history: 历史值列表
            new_value: 新观测值

        Returns:
            float: 更新后的 EWMA 值
        """
        if not history:
            return new_value

        # 使用 pandas ewma 计算
        series = pd.Series(list(history) + [new_value])
        ewm = series.ewm(alpha=self.alpha, adjust=False)
        return ewm.mean().iloc[-1]

    def compute_ewma(self, history):
        """
        计算历史数据的 EWMA

        Args:
            history: 历史值列表

        Returns:
            float: EWMA 值
        """
        if len(history) < self.min_periods:
            return np.mean(history) if history else 0.0

        series = pd.Series(history)
        ewm = series.ewm(alpha=self.alpha, adjust=False)
        return ewm.mean().iloc[-1]


# ============================================
# V27.0 高级特征工程
# ============================================


def compute_v27_features(df, window_size=5, alpha=0.3):
    """
    计算 V27.0 高级特征 (EWMA + 主客场拆分 + 对手强度)

    Args:
        df: 按时间排序的比赛数据
        window_size: 窗口大小
        alpha: EWMA 平滑系数

    Returns:
        pd.DataFrame: 包含 V27.0 特征的训练数据
    """
    print(f"\n🔧 构建 V27.0 高级特征 (EWMA alpha={alpha})...")

    # 为每支球队维护主场和客场的历史数据
    team_history = defaultdict(
        lambda: {
            # 总体历史（用于 EWMA）
            "all_xg": [],
            "all_possession": [],
            "all_sot": [],
            "all_bc": [],
            "all_rating": [],
            # 主场历史
            "home_xg": [],
            "home_possession": [],
            "home_sot": [],
            "home_bc": [],
            "home_rating": [],
            # 客场历史
            "away_xg": [],
            "away_possession": [],
            "away_sot": [],
            "away_bc": [],
            "away_rating": [],
        }
    )

    # 球队实力评分（用于对手强度修正）
    team_strength = defaultdict(float)  # 基于最近表现的实力评分

    ewma = EWMACalculator(alpha=alpha)
    results = []

    for idx, row in df.iterrows():
        home_team = row["home_team"]
        away_team = row["away_team"]
        home_team_id = row["home_team_id"]
        away_team_id = row["away_team_id"]

        # ========== 1. EWMA 总体特征 ==========
        home_hist = team_history[home_team]
        away_hist = team_history[away_team]

        # 主队 EWMA 特征
        if home_hist["all_xg"]:
            ewma_home_xg = ewma.compute_ewma(home_hist["all_xg"])
            ewma_home_possession = ewma.compute_ewma(home_hist["all_possession"])
            ewma_home_sot = ewma.compute_ewma(home_hist["all_sot"])
            ewma_home_bc = ewma.compute_ewma(home_hist["all_bc"])
            ewma_home_rating = ewma.compute_ewma(home_hist["all_rating"])
        else:
            ewma_home_xg, ewma_home_possession = 1.35, 48.0
            ewma_home_sot, ewma_home_bc = 4.2, 2.2
            ewma_home_rating = 6.85

        # 客队 EWMA 特征
        if away_hist["all_xg"]:
            ewma_away_xg = ewma.compute_ewma(away_hist["all_xg"])
            ewma_away_possession = ewma.compute_ewma(away_hist["all_possession"])
            ewma_away_sot = ewma.compute_ewma(away_hist["all_sot"])
            ewma_away_bc = ewma.compute_ewma(away_hist["all_bc"])
            ewma_away_rating = ewma.compute_ewma(away_hist["all_rating"])
        else:
            ewma_away_xg, ewma_away_possession = 1.15, 46.0
            ewma_away_sot, ewma_away_bc = 3.8, 1.8
            ewma_away_rating = 6.75

        # ========== 2. 主客场拆分特征 ==========
        # 主队的主场表现
        if home_hist["home_xg"]:
            home_at_home_xg = ewma.compute_ewma(home_hist["home_xg"])
            home_at_home_possession = ewma.compute_ewma(home_hist["home_possession"])
            home_at_home_rating = ewma.compute_ewma(home_hist["home_rating"])
        else:
            # 使用总体历史数据
            home_at_home_xg = ewma_home_xg * 1.08  # 主场优势加成
            home_at_home_possession = ewma_home_possession * 1.06
            home_at_home_rating = ewma_home_rating + 0.15

        # 客队的客场表现
        if away_hist["away_xg"]:
            away_at_away_xg = ewma.compute_ewma(away_hist["away_xg"])
            away_at_away_possession = ewma.compute_ewma(away_hist["away_possession"])
            away_at_away_rating = ewma.compute_ewma(away_hist["away_rating"])
        else:
            # 使用总体历史数据
            away_at_away_xg = ewma_away_xg * 0.92  # 客场劣势惩罚
            away_at_away_possession = ewma_away_possession * 0.94
            away_at_away_rating = ewma_away_rating - 0.15

        # ========== 3. 对手强度修正 ==========
        # 对手实力评分（基于 EWMA rating）
        opponent_strength = team_strength.get(away_team_id, 6.7)
        home_vs_opponent_strength_diff = ewma_home_rating - opponent_strength

        # ========== 4. 特征组合 ==========
        results.append(
            {
                "match_id": row["match_id"],
                "league_id": row["league_id"],
                "season": row["season"],
                "match_date": row["match_date"],
                "home_team": home_team,
                "away_team": away_team,
                # EWMA 总体特征
                "ewma_home_xg": ewma_home_xg,
                "ewma_away_xg": ewma_away_xg,
                "ewma_home_possession": ewma_home_possession,
                "ewma_away_possession": ewma_away_possession,
                "ewma_home_sot": ewma_home_sot,
                "ewma_away_sot": ewma_away_sot,
                "ewma_home_bc": ewma_home_bc,
                "ewma_away_bc": ewma_away_bc,
                "ewma_home_rating": ewma_home_rating,
                "ewma_away_rating": ewma_away_rating,
                # 主客场拆分特征
                "home_at_home_xg": home_at_home_xg,
                "home_at_home_rating": home_at_home_rating,
                "away_at_away_xg": away_at_away_xg,
                "away_at_away_rating": away_at_away_rating,
                # 对手强度特征
                "opponent_strength": opponent_strength,
                "home_vs_opponent_rating_diff": home_vs_opponent_strength_diff,
                # 差值特征
                "xg_diff": ewma_home_xg - ewma_away_xg,
                "rating_diff": ewma_home_rating - ewma_away_rating,
                "home_away_advantage": home_at_home_rating - away_at_away_rating,
                # 标签
                "result": None,  # 稍后填充
            }
        )

        # ========== 5. 更新历史记录（当前比赛） ==========
        if pd.notna(row["home_xg"]):
            # 更新主队总体历史
            home_hist["all_xg"].append(row["home_xg"])
            home_hist["all_possession"].append(row["home_possession"] or 50.0)
            home_hist["all_sot"].append(row["home_shots_on_target"] or 0)
            home_hist["all_bc"].append(row["home_big_chances"] or 0)
            if pd.notna(row["home_avg_player_rating"]):
                home_hist["all_rating"].append(row["home_avg_player_rating"])

            # 更新主队主场历史
            home_hist["home_xg"].append(row["home_xg"])
            home_hist["home_possession"].append(row["home_possession"] or 50.0)
            home_hist["home_sot"].append(row["home_shots_on_target"] or 0)
            home_hist["home_bc"].append(row["home_big_chances"] or 0)
            if pd.notna(row["home_avg_player_rating"]):
                home_hist["home_rating"].append(row["home_avg_player_rating"])

        if pd.notna(row["away_xg"]):
            # 更新客队总体历史
            away_hist["all_xg"].append(row["away_xg"])
            away_hist["all_possession"].append(row["away_possession"] or 50.0)
            away_hist["all_sot"].append(row["away_shots_on_target"] or 0)
            away_hist["all_bc"].append(row["away_big_chances"] or 0)
            if pd.notna(row["away_avg_player_rating"]):
                away_hist["all_rating"].append(row["away_avg_player_rating"])

            # 更新客队客场历史
            away_hist["away_xg"].append(row["away_xg"])
            away_hist["away_possession"].append(row["away_possession"] or 50.0)
            away_hist["away_sot"].append(row["away_shots_on_target"] or 0)
            away_hist["away_bc"].append(row["away_big_chances"] or 0)
            if pd.notna(row["away_avg_player_rating"]):
                away_hist["away_rating"].append(row["away_avg_player_rating"])

        # 更新球队实力评分（基于 EWMA rating）
        if pd.notna(row["home_avg_player_rating"]):
            current_home_rating = row["home_avg_player_rating"]
            home_hist_ratings = home_hist["all_rating"] + [current_home_rating]
            team_strength[home_team_id] = ewma.compute_ewma(home_hist_ratings)

        if pd.notna(row["away_avg_player_rating"]):
            current_away_rating = row["away_avg_player_rating"]
            away_hist_ratings = away_hist["all_rating"] + [current_away_rating]
            team_strength[away_team_id] = ewma.compute_ewma(away_hist_ratings)

    # 转换为 DataFrame 并填充结果标签
    result_df = pd.DataFrame(results)

    # 从比分推导比赛结果
    for idx, row in df.iterrows():
        match_id = row["match_id"]
        if pd.notna(row["home_score"]) and pd.notna(row["away_score"]):
            if row["home_score"] > row["away_score"]:
                result = 2  # Home Win
            elif row["home_score"] < row["away_score"]:
                result = 0  # Away Win
            else:
                result = 1  # Draw
        else:
            result = None

        result_df.loc[result_df["match_id"] == match_id, "result"] = result

    return result_df


# ============================================
# 模型训练与评估
# ============================================


def train_v27_model(df):
    """训练 V27.0 模型"""

    # V27.0 特征列表
    feature_columns = [
        # EWMA 总体特征
        "ewma_home_xg",
        "ewma_away_xg",
        "ewma_home_possession",
        "ewma_away_possession",
        "ewma_home_sot",
        "ewma_away_sot",
        "ewma_home_bc",
        "ewma_away_bc",
        "ewma_home_rating",
        "ewma_away_rating",
        # 主客场拆分特征
        "home_at_home_xg",
        "home_at_home_rating",
        "away_at_away_xg",
        "away_at_away_rating",
        # 对手强度特征
        "opponent_strength",
        "home_vs_opponent_rating_diff",
        # 差值特征
        "xg_diff",
        "rating_diff",
        "home_away_advantage",
    ]

    # 按赛季拆分
    train_seasons = ["20/21", "21/22", "22/23", "23/24"]
    test_season = "24/25"

    df_labeled = df[df["result"].notna()].copy()
    train_df = df_labeled[df_labeled["season"].isin(train_seasons)].copy()
    test_df = df_labeled[df_labeled["season"] == test_season].copy()

    print("\n📊 数据集划分:")
    print(f"  训练集 ({', '.join(train_seasons)}): {len(train_df)} 场")
    print(f"  测试集 ({test_season}): {len(test_df)} 场")

    # 准备特征和标签
    X_train = train_df[feature_columns].copy()
    y_train = train_df["result"].astype(int).values

    X_test = test_df[feature_columns].copy()
    y_test = test_df["result"].astype(int).values

    print(f"\n🔍 特征维度: {X_train.shape[1]}")

    # 标签分布
    print("\n📈 标签分布:")
    label_names = {0: "Away Win", 1: "Draw", 2: "Home Win"}
    for split, y in [("Train", y_train), ("Test", y_test)]:
        print(f"  {split}:")
        for label_val, label_name in label_names.items():
            count = (y == label_val).sum()
            pct = count / len(y) * 100
            print(f"    {label_name}: {count} ({pct:.1f}%)")

    # 初始化 XGBoost
    model = XGBClassifier(
        n_estimators=300,
        max_depth=5,
        learning_rate=0.08,
        subsample=0.85,
        colsample_bytree=0.85,
        random_state=42,
        objective="multi:softprob",
        num_class=3,
        eval_metric=["mlogloss", "merror", "mlogloss"],
    )

    print("\n🚀 开始训练 XGBoost 模型...")
    model.fit(
        X_train,
        y_train,
        eval_set=[(X_train, y_train), (X_test, y_test)],
        verbose=False,
    )

    # 预测
    y_pred = model.predict(X_test)
    y_pred_proba = model.predict_proba(X_test)

    # 评估指标
    accuracy = accuracy_score(y_test, y_pred)
    logloss = log_loss(y_test, y_pred_proba, labels=[0, 1, 2])

    # ROC-AUC (One-vs-Rest)
    from sklearn.preprocessing import label_binarize

    y_test_bin = label_binarize(y_test, classes=[0, 1, 2])
    auc_roc = roc_auc_score(y_test_bin, y_pred_proba, average="macro", multi_class="ovr")

    print(f"\n📊 模型评估 (测试集 - {test_season}):")
    print(f"  Accuracy: {accuracy:.4f} ({accuracy * 100:.2f}%)")
    print(f"  Log Loss: {logloss:.4f}")
    print(f"  ROC-AUC (macro): {auc_roc:.4f}")

    # 混淆矩阵
    cm = confusion_matrix(y_test, y_pred)
    print("\n🔀 混淆矩阵:")
    print(
        tabulate(
            cm,
            headers=["", "Pred: Away", "Pred: Draw", "Pred: Home"],
            showindex=["Actual: Away", "Actual: Draw", "Actual: Home"],
            tablefmt="grid",
        )
    )

    # 详细分类报告
    print("\n📋 分类报告:")
    print(classification_report(y_test, y_pred, target_names=["Away Win", "Draw", "Home Win"], digits=4))

    return {
        "model": model,
        "feature_columns": feature_columns,
        "X_train": X_train,
        "y_train": y_train,
        "X_test": X_test,
        "y_test": y_test,
        "y_pred": y_pred,
        "y_pred_proba": y_pred_proba,
        "accuracy": accuracy,
        "logloss": logloss,
        "auc_roc": auc_roc,
        "confusion_matrix": cm,
        "test_df": test_df.reset_index(drop=True),
    }


# ============================================
# 特征重要性分析
# ============================================


def plot_feature_importance(model, feature_columns, output_path):
    """绘制特征重要性图表"""
    importance = model.feature_importances_
    indices = np.argsort(importance)[::-1]

    plt.figure(figsize=(14, 8))
    plt.title("V27.0 EPL Quant Model - Feature Importance (EWMA + SoS + Split)", fontsize=16, fontweight="bold")
    plt.bar(range(len(importance)), importance[indices], color="steelblue", alpha=0.8)
    plt.xticks(range(len(importance)), [feature_columns[i] for i in indices], rotation=45, ha="right")
    plt.xlabel("Features", fontsize=12)
    plt.ylabel("Importance Score", fontsize=12)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()

    print("\n📊 特征重要性排行榜:")
    feature_importance_df = pd.DataFrame(
        {
            "Feature": [feature_columns[i] for i in indices],
            "Importance": importance[indices],
            "Rank": range(1, len(importance) + 1),
        }
    )
    print(tabulate(feature_importance_df, headers="keys", tablefmt="grid", showindex=False))

    return feature_importance_df


# ============================================
# 样本预测展示
# ============================================


def show_sample_predictions(results, n_samples=5):
    """展示样本预测"""
    test_df = results["test_df"]
    y_pred_proba = results["y_pred_proba"]
    y_pred = results["y_pred"]

    sample_indices = np.random.choice(len(test_df), n_samples, replace=False)

    print(f"\n🎯 实战样本预测 (随机抽取 {n_samples} 场 {test_df.iloc[0]['season']} 赛季比赛):")

    samples = []
    for idx in sample_indices:
        row = test_df.iloc[idx]
        proba = y_pred_proba[idx]
        pred = y_pred[idx]

        if pd.notna(row["match_id"]):
            # 从原始数据获取比分
            pass  # 比分已在原始 DF 中

        # 推导实际结果
        if "result" in row and pd.notna(row["result"]):
            pred_map = {0: "A", 1: "D", 2: "H"}
            actual = pred_map[int(row["result"])]
        else:
            actual = "?"

        pred_map = {0: "A", 1: "D", 2: "H"}
        pred_label = pred_map[pred]

        samples.append(
            {
                "Match ID": row["match_id"],
                "Date": row["match_date"].strftime("%Y-%m-%d") if pd.notna(row["match_date"]) else "N/A",
                "Actual": actual,
                "Predicted": pred_label,
                "P(Away)": f"{proba[0]:.1%}",
                "P(Draw)": f"{proba[1]:.1%}",
                "P(Home)": f"{proba[2]:.1%}",
                "Confidence": f"{max(proba):.1%}",
                "Correct": "✅" if actual == pred_label else "❌",
            }
        )

    samples.sort(key=lambda x: x["Date"])
    print(tabulate(samples, headers="keys", tablefmt="grid"))

    correct = sum(1 for s in samples if s["Correct"] == "✅")
    avg_confidence = np.mean([float(s["Confidence"].rstrip("%")) / 100 for s in samples])
    print(f"\n样本准确率: {correct}/{n_samples} ({correct / n_samples * 100:.1f}%)")
    print(f"平均预测置信度: {avg_confidence:.1%}")


# ============================================
# 主流程
# ============================================


def main():
    """主训练流程"""
    print("=" * 100)
    print(" " * 25 + "V27.0 EPL 量化预测模型 (EWMA + SoS + Split)")
    print("=" * 100)
    print(f"\n训练时间: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}\n")

    # 1. 提取数据
    print("📥 步骤 1: 从数据库提取英超数据...")
    df = fetch_all_match_data()
    print(f"  ✅ 提取完成: {len(df)} 场比赛")
    print(f"  赛季分布: {', '.join(sorted(df['season'].unique()))}")

    # 2. 构建 V27.0 特征
    print("\n🔧 步骤 2: 构建 V27.0 高级特征...")
    v27_df = compute_v27_features(df, window_size=5, alpha=0.3)
    print(f"  ✅ 特征构建完成: {len(v27_df)} 场比赛")

    # 3. 训练模型
    print("\n🔧 步骤 3: 训练 XGBoost 模型...")
    results = train_v27_model(v27_df)

    # 4. 特征重要性
    print("\n📊 步骤 4: 分析特征重要性...")
    importance_plot_path = project_root / "models" / "v27_0_epl_feature_importance.png"
    importance_plot_path.parent.mkdir(exist_ok=True)
    feature_importance_df = plot_feature_importance(results["model"], results["feature_columns"], importance_plot_path)
    print(f"  ✅ 特征重要性图表已保存: {importance_plot_path}")

    # 5. 样本预测
    print("\n🎯 步骤 5: 实战样本预测...")
    show_sample_predictions(results, n_samples=5)

    # 6. 保存模型
    print("\n💾 步骤 6: 保存模型...")
    model_path = project_root / "models" / "v27_0_epl_ewma.pkl"
    joblib.dump(results["model"], model_path)
    print(f"  💾 模型已保存至: {model_path}")

    # 最终总结
    print("\n" + "=" * 100)
    print(" " * 40 + "训练总结")
    print("=" * 100)

    summary = [
        ["数据规模", f"{len(v27_df)} 场 (训练: {len(results['X_train'])}, 测试: {len(results['X_test'])})"],
        ["特征维度", f"{len(results['feature_columns'])} 维 (EWMA + 主客场拆分 + 对手强度)"],
        ["测试集 Accuracy", f"{results['accuracy']:.4f} ({results['accuracy'] * 100:.2f}%)"],
        ["测试集 Log Loss", f"{results['logloss']:.4f}"],
        ["测试集 ROC-AUC", f"{results['auc_roc']:.4f}"],
        ["最重要特征", feature_importance_df.iloc[0]["Feature"]],
        ["模型路径", str(model_path)],
    ]

    print(tabulate(summary, tablefmt="plain", numalign="right"))

    print("\n" + "=" * 100)
    print(" " * 40 + "V27.0 技术亮点")
    print("=" * 100)
    print("✅ EWMA (alpha=0.3) - 近期比赛权重更高")
    print("✅ 主客场拆分 - 捕捉主客场表现差异")
    print("✅ 对手强度修正 - 考虑对手实力影响")
    print("✅ ROC-AUC 评估 - 概率排序能力更准确")
    print("=" * 100)


if __name__ == "__main__":
    main()
