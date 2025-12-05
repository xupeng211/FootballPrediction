#!/usr/bin/env python3
"""特征选择演示脚本
Feature Selection Demo Script.

演示如何使用智能特征选择器来自动筛选最重要的特征，
包括共线性检测和基于模型重要性的特征排序。
"""

import logging
import numpy as np
import pandas as pd
from pathlib import Path
import sys
import warnings

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ml.feature_selector import FeatureSelector, create_feature_selector
from src.ml.football_prediction_pipeline import FootballPredictionPipeline

# 忽略警告
warnings.filterwarnings("ignore")

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def generate_synthetic_football_data(n_samples=1000, n_features=50, random_state=42):
    """生成合成的足球比赛数据用于演示.

    Args:
        n_samples: 样本数量
        n_features: 特征数量
        random_state: 随机种子

    Returns:
        特征矩阵和目标变量
    """
    np.random.seed(random_state)

    # 生成基础特征
    feature_names = []

    # 球队实力特征 (10个)
    for i in range(5):
        feature_names.extend([
            f'home_team_strength_{i}',
            f'away_team_strength_{i}',
            f'strength_diff_{i}'
        ])

    # 历史交锋特征 (8个)
    for i in range(4):
        feature_names.extend([
            f'historical_home_wins_{i}',
            f'historical_away_wins_{i}'
        ])

    # 近期状态特征 (12个)
    for i in range(6):
        feature_names.extend([
            f'home_recent_form_{i}',
            f'away_recent_form_{i}'
        ])

    # 统计数据特征 (15个)
    stats_features = [
        'home_goals_scored', 'home_goals_conceded',
        'away_goals_scored', 'away_goals_conceded',
        'home_shots_on_target', 'away_shots_on_target',
        'home_possession', 'away_possession',
        'home_pass_accuracy', 'away_pass_accuracy',
        'home_fouls', 'away_fouls',
        'home_corners', 'away_corners',
        'home_yellow_cards'
    ]
    feature_names.extend(stats_features)

    # 环境特征 (5个)
    env_features = ['home_advantage', 'weather_condition', 'crowd_factor', 'travel_distance', 'rest_days']
    feature_names.extend(env_features)

    # 确保特征数量正确
    feature_names = feature_names[:n_features]

    # 生成特征矩阵
    X = pd.DataFrame(np.random.randn(n_samples, n_features), columns=feature_names)

    # 添加一些相关性特征（模拟共线性）
    if n_features >= 20:
        # 创建高度相关的特征对
        if 'home_team_strength_0' in X.columns and 'away_team_strength_0' in X.columns:
            X['home_strength_copy'] = X['home_team_strength_0'] * 0.95 + np.random.normal(0, 0.05, n_samples)
            X['away_strength_copy'] = X['away_team_strength_0'] * 0.98 + np.random.normal(0, 0.02, n_samples)

            # 添加这些新特征到DataFrame
            additional_features = ['home_strength_copy', 'away_strength_copy']
        else:
            additional_features = []

        # 只有当相关特征存在时才添加比值特征
        if 'home_goals_scored' in X.columns and 'away_goals_conceded' in X.columns:
            X['goals_ratio'] = X['home_goals_scored'] / (X['away_goals_conceded'] + 1)
            additional_features.append('goals_ratio')

        # 更新特征名称列表
        if additional_features:
            feature_names.extend(additional_features)
            X = X[feature_names]

    # 生成目标变量（比赛结果）
    # 基于几个重要特征的线性组合
    important_features = [
        'home_team_strength_0', 'away_team_strength_0', 'strength_diff_0',
        'historical_home_wins_0', 'historical_away_wins_0',
        'home_recent_form_0', 'away_recent_form_0',
        'home_advantage'
    ]

    # 确保重要特征存在
    available_important = [f for f in important_features if f in X.columns]

    if available_important:
        # 计算比赛结果的概率
        logit = (
            X[available_important].sum(axis=1) * 0.3 +
            np.random.normal(0, 0.5, n_samples)  # 添加噪声
        )

        # 转换为概率
        prob = 1 / (1 + np.exp(-logit))

        # 生成二元分类结果
        y = (prob > 0.5).astype(int)
    else:
        # 如果没有重要特征，随机生成
        y = np.random.binomial(1, 0.5, n_samples)

    logger.info(f"生成合成数据: {n_samples} 样本, {X.shape[1]} 个特征")
    logger.info(f"目标变量分布: {np.bincount(y)}")

    return X, y


def demo_basic_feature_selection():
    """演示基础特征选择功能."""
    print("\n" + "="*60)
    print("🎯 演示1: 基础特征选择功能")
    print("="*60)

    # 生成数据
    X, y = generate_synthetic_football_data(n_samples=1000, n_features=30)

    # 创建特征选择器
    selector = create_feature_selector(
        task_type="classification",
        correlation_threshold=0.9,
        min_features=5,
        max_features=20
    )

    # 执行特征选择
    selected_features = selector.select_features(
        X, y,
        top_k=15,
        remove_collinear=True
    )

    # 显示结果
    print("\n📊 特征选择结果:")
    print(f"原始特征数量: {X.shape[1]}")
    print(f"选择的特征数量: {len(selected_features)}")
    print(f"移除的特征数量: {len(selector.removed_features)}")

    print("\n✅ 选择的特征:")
    for i, feature in enumerate(selected_features, 1):
        print(f"  {i:2d}. {feature}")

    # 显示特征重要性
    if selector.feature_importance_df is not None:
        print("\n🔝 前10个最重要的特征:")
        top_features = selector.feature_importance_df.head(10)
        for i, row in top_features.iterrows():
            print(f"  {row['feature']:<25} (重要性: {row['importance_avg']:.4f})")

    # 显示共线性检测结果
    if selector.correlation_matrix is not None:
        high_corr_pairs = []
        corr_matrix = selector.correlation_matrix
        for i in range(len(corr_matrix.columns)):
            for j in range(i + 1, len(corr_matrix.columns)):
                if corr_matrix.iloc[i, j] > 0.9:
                    high_corr_pairs.append((
                        corr_matrix.columns[i],
                        corr_matrix.columns[j],
                        corr_matrix.iloc[i, j]
                    ))

        if high_corr_pairs:
            print("\n⚠️  检测到的高相关性特征对 (r > 0.9):")
            for feat1, feat2, corr in high_corr_pairs[:5]:  # 只显示前5个
                print(f"  {feat1} ↔ {feat2}: {corr:.3f}")
        else:
            print("\n✅ 未检测到高相关性特征对")


def demo_feature_selection_pipeline():
    """演示集成到训练流水线中的特征选择."""
    print("\n" + "="*60)
    print("🚀 演示2: 集成特征选择的训练流水线")
    print("="*60)

    # 生成数据
    X, y = generate_synthetic_football_data(n_samples=800, n_features=25)

    # 分割数据
    from sklearn.model_selection import train_test_split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    print(f"训练数据: {X_train.shape[0]} 样本, {X_train.shape[1]} 特征")
    print(f"测试数据: {X_test.shape[0]} 样本, {X_test.shape[1]} 特征")

    try:
        # 创建带特征选择的流水线
        pipeline = FootballPredictionPipeline(
            model_name="demo_football_prediction",
            output_dir="models/demo",
            enable_feature_selection=True,
            feature_selection_params={
                "task_type": "classification",
                "correlation_threshold": 0.85,
                "min_features": 3,
                "max_features": 15
            }
        )

        # 训练模型
        print("\n🏃 开始训练模型...")
        training_result = pipeline.train_model(
            X_train, y_train,
            X_test, y_test,
            model_type="xgboost",
            feature_selection_top_k=10,
            optimize_hyperparameters=False  # 为了演示速度，跳过超参数优化
        )

        # 显示训练结果
        print("\n📈 训练完成!")
        print(f"模型性能: {training_result.get('metrics', {})}")

        # 显示特征选择信息
        feature_selection_info = training_result.get('feature_selection', {})
        if feature_selection_info.get('enabled'):
            print("\n🎯 特征选择结果:")
            print(f"原始特征数: {feature_selection_info.get('original_features', 'N/A')}")
            print(f"选择特征数: {feature_selection_info.get('selected_features', 'N/A')}")
            print(f"移除特征数: {feature_selection_info.get('removed_features', 'N/A')}")

            selected_features = feature_selection_info.get('selected_feature_names', [])
            if selected_features:
                print("\n✅ 最终选择的特征:")
                for i, feature in enumerate(selected_features, 1):
                    print(f"  {i:2d}. {feature}")

        # 评估模型
        print("\n🧪 评估模型性能...")
        predictions = pipeline.predict(X_test)

        # 计算准确率
        accuracy = (predictions == y_test).mean()
        print(f"测试集准确率: {accuracy:.4f}")

        # 显示模型文件
        output_dir = Path("models/demo")
        if output_dir.exists():
            print("\n📁 生成的文件:")
            for file in output_dir.glob("*"):
                if file.is_file():
                    print(f"  {file.name}")

    except Exception as e:
        print(f"\n❌ 流水线演示失败: {e}")
        logger.info("这可能是因为缺少某些依赖模块，这是正常的")


def demo_feature_importance_analysis():
    """演示特征重要性分析."""
    print("\n" + "="*60)
    print("📊 演示3: 特征重要性分析")
    print("="*60)

    # 生成具有明确重要性结构的数据
    X, y = generate_synthetic_football_data(n_samples=500, n_features=20)

    # 创建特征选择器
    selector = FeatureSelector(
        task_type="classification",
        correlation_threshold=0.95,
        random_state=42
    )

    # 执行特征选择
    selected_features = selector.select_features(X, y, top_k=10)

    # 分析特征重要性
    if selector.feature_importance_df is not None:
        importance_df = selector.feature_importance_df

        print("\n🔍 特征重要性详细分析:")

        # 按不同重要性指标排序
        print("\n1️⃣ 按平均重要性排序:")
        avg_top = importance_df.nlargest(5, 'importance_avg')
        for i, row in avg_top.iterrows():
            print(f"   {row['feature']:<20} (平均: {row['importance_avg']:.4f}, "
                  f"最大: {row['importance_max']:.4f})")

        print("\n2️⃣ 按随机森林重要性排序:")
        if 'rf_importance' in importance_df.columns:
            rf_top = importance_df.nlargest(5, 'rf_importance')
            for i, row in rf_top.iterrows():
                print(f"   {row['feature']:<20} (RF重要性: {row['rf_importance']:.4f})")

        print("\n3️⃣ 按互信息排序:")
        if 'mi_importance' in importance_df.columns:
            mi_top = importance_df.nlargest(5, 'mi_importance')
            for i, row in mi_top.iterrows():
                print(f"   {row['feature']:<20} (互信息: {row['mi_importance']:.4f})")

    # 尝试生成特征重要性图
    try:
        selector.plot_feature_importance(top_k=10, save_path="feature_importance_demo.png")
        print("\n📈 特征重要性图已保存到: feature_importance_demo.png")
    except Exception as e:
        print(f"\n⚠️  绘图失败（可能缺少matplotlib）: {e}")


def demo_collinearity_detection():
    """演示共线性检测功能."""
    print("\n" + "="*60)
    print("🔗 演示4: 共线性检测")
    print("="*60)

    # 生成具有高相关性的数据
    np.random.seed(42)
    n_samples = 200

    # 创建基础特征
    base_data = {
        'feature_A': np.random.randn(n_samples),
        'feature_B': np.random.randn(n_samples),
        'feature_C': np.random.randn(n_samples),
    }

    # 创建高相关性的特征
    base_data['feature_A_copy'] = base_data['feature_A'] * 0.97 + np.random.normal(0, 0.03, n_samples)
    base_data['feature_A_copy2'] = base_data['feature_A'] * 0.99 + np.random.normal(0, 0.01, n_samples)
    base_data['feature_B_near_duplicate'] = base_data['feature_B'] * 0.94 + np.random.normal(0, 0.06, n_samples)

    # 创建一些不相关的特征
    base_data['independent_1'] = np.random.randn(n_samples)
    base_data['independent_2'] = np.random.randn(n_samples)
    base_data['independent_3'] = np.random.randn(n_samples)

    X = pd.DataFrame(base_data)

    # 生成目标变量（只与某些特征相关）
    y = ((base_data['feature_A'] + base_data['feature_B'] * 0.5) > 0).astype(int)

    print("📋 生成的数据特征:")
    print(f"  样本数: {n_samples}")
    print(f"  特征数: {X.shape[1]}")
    print(f"  目标变量分布: {np.bincount(y)}")

    # 展示相关性矩阵
    print("\n📊 特征相关性矩阵:")
    corr_matrix = X.corr()
    for i, col in enumerate(corr_matrix.columns):
        correlations = [f"{corr_matrix.iloc[i, j]:.3f}" for j in range(len(corr_matrix.columns))]
        print(f"  {col:<20} {'  '.join(correlations)}")

    # 使用特征选择器检测共线性
    selector = FeatureSelector(
        task_type="classification",
        correlation_threshold=0.9,
        random_state=42
    )

    print("\n🔍 执行共线性检测...")
    kept_features, removed_features = selector.detect_collinearity(X, y)

    print("\n✅ 共线性检测结果:")
    print(f"保留的特征 ({len(kept_features)}): {kept_features}")
    print(f"移除的特征 ({len(removed_features)}): {removed_features}")

    # 显示具体的高相关性对
    if selector.correlation_matrix is not None:
        high_corr_pairs = []
        for i in range(len(selector.correlation_matrix.columns)):
            for j in range(i + 1, len(selector.correlation_matrix.columns)):
                corr_val = selector.correlation_matrix.iloc[i, j]
                if corr_val > 0.9:
                    high_corr_pairs.append((
                        selector.correlation_matrix.columns[i],
                        selector.correlation_matrix.columns[j],
                        corr_val
                    ))

        if high_corr_pairs:
            print("\n⚠️  发现的高相关性特征对:")
            for feat1, feat2, corr in high_corr_pairs:
                print(f"  {feat1} ↔ {feat2}: r = {corr:.4f}")
        else:
            print("\n✅ 未发现高相关性特征对")


def main():
    """主函数."""
    print("🚀 特征选择系统演示")
    print("="*60)
    print("本演示将展示智能特征选择器的各种功能:")
    print("1. 基础特征选择功能")
    print("2. 集成到训练流水线")
    print("3. 特征重要性分析")
    print("4. 共线性检测")

    try:
        # 演示1: 基础特征选择
        demo_basic_feature_selection()

        # 演示2: 流水线集成
        demo_feature_selection_pipeline()

        # 演示3: 特征重要性分析
        demo_feature_importance_analysis()

        # 演示4: 共线性检测
        demo_collinearity_detection()

        print("\n" + "="*60)
        print("🎉 所有演示完成!")
        print("="*60)
        print("\n💡 主要特性总结:")
        print("✅ 基于多种模型的特征重要性评估")
        print("✅ 智能共线性检测和移除")
        print("✅ 可配置的特征选择参数")
        print("✅ 与训练流水线无缝集成")
        print("✅ 详细的特征分析报告")
        print("✅ 特征选择结果持久化")

        print("\n📁 生成的文件:")
        output_files = [
            "models/demo/selected_features.json",
            "models/demo/feature_selection_results.json",
            "feature_importance_demo.png"
        ]
        for file in output_files:
            if Path(file).exists():
                print(f"  ✅ {file}")
            else:
                print(f"  ❌ {file} (未生成)")

    except Exception as e:
        logger.error(f"演示过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
