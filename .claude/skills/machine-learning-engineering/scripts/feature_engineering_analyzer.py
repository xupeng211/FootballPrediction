#!/usr/bin/env python3
"""
特征工程分析器
专门为足球赛果预测系统设计的特征工程分析和优化工具
"""

import warnings

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy.stats import spearmanr
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_selection import RFE, SelectKBest, VarianceThreshold, mutual_info_classif

warnings.filterwarnings("ignore")


class FootballFeatureAnalyzer:
    """足球特征工程分析器"""

    def __init__(self):
        self.feature_stats = {}
        self.correlation_matrix = None
        self.feature_importance = None
        self.selected_features = None

    def analyze_feature_quality(self, df: pd.DataFrame, target_col: str = "target"):
        """全面分析特征质量"""
        print("🔍 特征质量分析报告")
        print("=" * 60)

        # 基础统计
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        if target_col in numeric_cols:
            numeric_cols = numeric_cols.drop(target_col)

        print(f"数值特征数量: {len(numeric_cols)}")
        print(f"总样本数: {len(df)}")

        # 缺失值分析
        missing_analysis = self._analyze_missing_values(df, target_col)

        # 方差分析
        variance_analysis = self._analyze_variance(df[numeric_cols])

        # 异常值分析
        outlier_analysis = self._analyze_outliers(df[numeric_cols])

        # 相关性分析
        correlation_analysis = self._analyze_correlations(df[numeric_cols], target_col)

        # 特征与目标的关系
        target_relation = self._analyze_target_relation(df, target_col)

        return {
            "missing_values": missing_analysis,
            "variance": variance_analysis,
            "outliers": outlier_analysis,
            "correlations": correlation_analysis,
            "target_relation": target_relation,
        }

    def _analyze_missing_values(self, df: pd.DataFrame, target_col: str) -> Dict:
        """分析缺失值"""
        missing_counts = df.isnull().sum()
        missing_pct = (missing_counts / len(df)) * 100

        missing_analysis = {
            "total_missing": missing_counts.sum(),
            "features_with_missing": (missing_counts > 0).sum(),
            "missing_by_feature": missing_counts[missing_counts > 0].to_dict(),
            "missing_percentage_by_feature": missing_pct[missing_pct > 0].to_dict(),
        }

        print("\n📊 缺失值分析:")
        print(f"总缺失值: {missing_analysis['total_missing']}")
        print(f"有缺失值的特征数: {missing_analysis['features_with_missing']}")

        if missing_analysis["features_with_missing"] > 0:
            print("缺失值最多的特征:")
            top_missing = missing_analysis["missing_percentage_by_feature"]
            for feature, pct in sorted(top_missing.items(), key=lambda x: x[1], reverse=True)[:5]:
                print(f"  {feature}: {pct:.2f}%")

        return missing_analysis

    def _analyze_variance(self, df: pd.DataFrame) -> Dict:
        """分析方差"""
        variance = df.var()
        zero_variance = variance[variance == 0]
        low_variance = variance[variance < 0.01]

        variance_analysis = {
            "zero_variance_features": zero_variance.index.tolist(),
            "low_variance_features": low_variance.index.tolist(),
            "variance_stats": {
                "mean": variance.mean(),
                "std": variance.std(),
                "min": variance.min(),
                "max": variance.max(),
            },
        }

        print("\n📈 方差分析:")
        print(f"零方差特征数: {len(zero_variance)}")
        print(f"低方差特征数 (<0.01): {len(low_variance)}")
        print(f"平均方差: {variance.mean():.4f}")

        return variance_analysis

    def _analyze_outliers(self, df: pd.DataFrame) -> Dict:
        """分析异常值 (IQR方法)"""
        outlier_counts = {}
        outlier_percentages = {}

        for col in df.columns:
            Q1 = df[col].quantile(0.25)
            Q3 = df[col].quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR

            outliers = df[(df[col] < lower_bound) | (df[col] > upper_bound)]
            outlier_counts[col] = len(outliers)
            outlier_percentages[col] = (len(outliers) / len(df)) * 100

        outlier_analysis = {"outlier_counts": outlier_counts, "outlier_percentages": outlier_percentages}

        print("\n⚠️  异常值分析:")
        high_outlier_features = {k: v for k, v in outlier_percentages.items() if v > 5}
        if high_outlier_features:
            print("异常值较多的特征 (>5%):")
            for feature, pct in sorted(high_outlier_features.items(), key=lambda x: x[1], reverse=True)[:5]:
                print(f"  {feature}: {pct:.2f}%")
        else:
            print("没有异常值过多的特征")

        return outlier_analysis

    def _analyze_correlations(self, df: pd.DataFrame, target_col: str) -> Dict:
        """分析相关性"""
        self.correlation_matrix = df.corr()

        # 高相关性特征对
        high_corr_pairs = []
        for i in range(len(self.correlation_matrix.columns)):
            for j in range(i + 1, len(self.correlation_matrix.columns)):
                corr_val = abs(self.correlation_matrix.iloc[i, j])
                if corr_val > 0.8:
                    high_corr_pairs.append(
                        (self.correlation_matrix.columns[i], self.correlation_matrix.columns[j], corr_val)
                    )

        correlation_analysis = {
            "correlation_matrix": self.correlation_matrix,
            "high_correlation_pairs": high_corr_pairs,
            "avg_correlation": self.correlation_matrix.abs().mean().mean(),
        }

        print("\n🔗 相关性分析:")
        print(f"平均相关系数: {correlation_analysis['avg_correlation']:.4f}")
        print(f"高相关性特征对 (>0.8): {len(high_corr_pairs)}")

        if high_corr_pairs:
            print("高相关性特征对:")
            for pair in high_corr_pairs[:5]:
                print(f"  {pair[0]} - {pair[1]}: {pair[2]:.3f}")

        return correlation_analysis

    def _analyze_target_relation(self, df: pd.DataFrame, target_col: str) -> Dict:
        """分析特征与目标的关系"""
        if target_col not in df.columns:
            return {"error": f"Target column {target_col} not found"}

        numeric_cols = df.select_dtypes(include=[np.number]).columns
        features = [col for col in numeric_cols if col != target_col]

        # 计算互信息
        from sklearn.feature_selection import mutual_info_classif

        mi_scores = mutual_info_classif(df[features], df[target_col])

        feature_target_mi = dict(zip(features, mi_scores))

        # 计算点双列相关系数（对于分类目标）
        feature_target_corr = {}
        for feature in features:
            if df[feature].nunique() > 1:  # 避免常量特征
                corr, p_value = spearmanr(df[feature], df[target_col])
                feature_target_corr[feature] = {"correlation": corr, "p_value": p_value}

        target_relation = {
            "mutual_info_scores": feature_target_mi,
            "correlations": feature_target_corr,
            "top_features_by_mi": sorted(feature_target_mi.items(), key=lambda x: x[1], reverse=True)[:10],
            "top_features_by_corr": sorted(
                feature_target_corr.items(), key=lambda x: abs(x[1]["correlation"]), reverse=True
            )[:10],
        }

        print("\n🎯 特征与目标关系分析:")
        print("互信息得分最高的特征:")
        for feature, score in target_relation["top_features_by_mi"][:5]:
            print(f"  {feature}: {score:.4f}")

        return target_relation

    def suggest_feature_engineering(self, analysis_results: Dict) -> Dict:
        """基于分析结果建议特征工程操作"""
        suggestions = []

        # 缺失值处理建议
        missing = analysis_results["missing_values"]
        if missing["features_with_missing"] > 0:
            high_missing = [k for k, v in missing["missing_percentage_by_feature"].items() if v > 20]
            if high_missing:
                suggestions.append(
                    {
                        "type": "missing_values",
                        "action": "drop_features",
                        "features": high_missing,
                        "reason": "缺失值超过20%，建议删除",
                    }
                )

            moderate_missing = [k for k, v in missing["missing_percentage_by_feature"].items() if 5 < v <= 20]
            if moderate_missing:
                suggestions.append(
                    {
                        "type": "missing_values",
                        "action": "impute",
                        "features": moderate_missing,
                        "method": "median" if len(moderate_missing) > 3 else "mean",
                        "reason": "缺失值适中，建议插补",
                    }
                )

        # 低方差特征建议
        variance = analysis_results["variance"]
        if variance["zero_variance_features"]:
            suggestions.append(
                {
                    "type": "variance",
                    "action": "drop_features",
                    "features": variance["zero_variance_features"],
                    "reason": "零方差特征，无预测能力",
                }
            )

        if variance["low_variance_features"]:
            suggestions.append(
                {
                    "type": "variance",
                    "action": "consider_drop",
                    "features": variance["low_variance_features"],
                    "reason": "低方差特征，预测能力有限",
                }
            )

        # 高相关性特征建议
        correlations = analysis_results["correlations"]
        if correlations["high_correlation_pairs"]:
            to_drop = set()
            for feat1, feat2, corr in correlations["high_correlation_pairs"]:
                # 简单策略：保留第一个特征
                if feat1 not in to_drop and feat2 not in to_drop:
                    to_drop.add(feat2)

            if to_drop:
                suggestions.append(
                    {
                        "type": "correlation",
                        "action": "drop_features",
                        "features": list(to_drop),
                        "reason": "存在高相关性特征对，避免多重共线性",
                    }
                )

        # 特征选择建议
        target_relation = analysis_results.get("target_relation", {})
        if "mutual_info_scores" in target_relation:
            low_importance = [k for k, v in target_relation["mutual_info_scores"].items() if v < 0.01]
            if low_importance:
                suggestions.append(
                    {
                        "type": "feature_importance",
                        "action": "consider_drop",
                        "features": low_importance,
                        "reason": "与目标变量互信息得分过低",
                    }
                )

        print("\n💡 特征工程建议:")
        for i, suggestion in enumerate(suggestions, 1):
            print(
                f"\n{i}. {suggestion.get('type', '').title()} - {suggestion.get('action', '').replace('_', ' ').title()}"
            )
            print(f"   原因: {suggestion.get('reason', '')}")
            if len(suggestion.get("features", [])) <= 5:
                print(f"   特征: {', '.join(suggestion.get('features', []))}")
            else:
                print(f"   特征数量: {len(suggestion.get('features', []))}")

        return {"suggestions": suggestions}

    def create_new_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """创建新特征"""
        df_new = df.copy()

        print("\n🔧 创建新特征...")

        # 交互特征
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for i, col1 in enumerate(numeric_cols[:5]):  # 限制前5个特征避免组合爆炸
            for col2 in numeric_cols[i + 1 : i + 3]:  # 每个特征只与前2个创建交互
                df_new[f"{col1}_x_{col2}"] = df_new[col1] * df_new[col2]
                df_new[f"{col1}_div_{col2}"] = df_new[col1] / (df_new[col2] + 1e-8)

        # 多项式特征（对重要特征）
        if "mutual_info_scores" in self.feature_stats:
            top_features = sorted(self.feature_stats["mutual_info_scores"].items(), key=lambda x: x[1], reverse=True)[
                :3
            ]
            for feature, _ in top_features:
                df_new[f"{feature}_squared"] = df_new[feature] ** 2
                df_new[f"{feature}_sqrt"] = np.sqrt(np.abs(df_new[feature]))

        # 统计特征
        if len(numeric_cols) > 3:
            df_new["feature_mean"] = df[numeric_cols].mean(axis=1)
            df_new["feature_std"] = df[numeric_cols].std(axis=1)
            df_new["feature_max"] = df[numeric_cols].max(axis=1)
            df_new["feature_min"] = df[numeric_cols].min(axis=1)

        print(f"创建了 {len(df_new.columns) - len(df.columns)} 个新特征")
        return df_new

    def optimize_features(self, X, y, method: str = "mutual_info", k: int = 20):
        """优化特征选择"""
        print(f"\n🎯 特征优化 (方法: {method}, 目标特征数: {k})")

        if method == "mutual_info":
            selector = SelectKBest(mutual_info_classif, k=k)
        elif method == "rfe":
            rf = RandomForestClassifier(n_estimators=100, random_state=42)
            selector = RFE(rf, n_features_to_select=k)
        elif method == "variance":
            selector = VarianceThreshold(threshold=0.01)
        else:
            raise ValueError(f"Unknown feature selection method: {method}")

        X_selected = selector.fit_transform(X, y)
        selected_features = X.columns[selector.get_support()].tolist()

        self.selected_features = selected_features

        print(f"选择了 {len(selected_features)} 个特征:")
        for i, feature in enumerate(selected_features[:10], 1):
            print(f"  {i}. {feature}")

        if len(selected_features) > 10:
            print(f"  ... 还有 {len(selected_features) - 10} 个特征")

        return X_selected, selected_features

    def visualize_feature_analysis(self, df: pd.DataFrame, target_col: str = "target"):
        """可视化特征分析结果"""
        plt.style.use("seaborn-v0_8")

        # 相关性热力图
        if self.correlation_matrix is not None:
            plt.figure(figsize=(12, 10))
            mask = np.triu(np.ones_like(self.correlation_matrix, dtype=bool))
            sns.heatmap(
                self.correlation_matrix,
                mask=mask,
                cmap="coolwarm",
                center=0,
                annot=False,
                fmt=".2f",
                cbar_kws={"shrink": 0.8},
            )
            plt.title("特征相关性热力图")
            plt.tight_layout()
            plt.savefig("feature_correlation_heatmap.png", dpi=300, bbox_inches="tight")
            plt.show()

        # 特征分布
        numeric_cols = df.select_dtypes(include=[np.number]).columns[:12]  # 显示前12个
        if len(numeric_cols) > 0:
            fig, axes = plt.subplots(3, 4, figsize=(16, 12))
            axes = axes.ravel()

            for i, col in enumerate(numeric_cols):
                axes[i].hist(df[col].dropna(), bins=30, alpha=0.7, edgecolor="black")
                axes[i].set_title(f"{col} 分布")
                axes[i].set_xlabel("")
                axes[i].set_ylabel("")

            # 隐藏多余的子图
            for i in range(len(numeric_cols), 12):
                axes[i].set_visible(False)

            plt.suptitle("特征分布图", y=1.02)
            plt.tight_layout()
            plt.savefig("feature_distributions.png", dpi=300, bbox_inches="tight")
            plt.show()

        print("可视化图表已保存")


def main():
    """主函数示例"""
    print("足球特征工程分析器")
    print("=" * 50)

    # 示例使用
    analyzer = FootballFeatureAnalyzer()

    print("请根据实际数据情况调用以下方法:")
    print("1. results = analyzer.analyze_feature_quality(df, target_col='target')")
    print("2. suggestions = analyzer.suggest_feature_engineering(results)")
    print("3. df_new = analyzer.create_new_features(df)")
    print("4. X_selected, selected_features = analyzer.optimize_features(X, y)")
    print("5. analyzer.visualize_feature_analysis(df)")


if __name__ == "__main__":
    main()
