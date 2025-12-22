#!/usr/bin/env python3
"""
V9.6 防作弊单元测试 - 数据泄露检测
随机抽取特征列，如果发现特征与结果的相关性异常，则自动中止训练并报警

作者: Claude Code
版本: V9.6
"""

import pandas as pd
import numpy as np
from scipy.stats import pearsonr, spearmanr
from sklearn.feature_selection import mutual_info_classif
import sys
import warnings
from typing import Dict, List, Any
warnings.filterwarnings('ignore')


class DataLeakageDetector:
    """
    数据泄露检测器

    功能:
    1. 相关性检测
    2. 互信息检测
    3. 完美预测检测
    4. 随机特征检测
    """

    def __init__(self, correlation_threshold: float = 0.9,
                 mutual_info_threshold: float = 0.5,
                 perfect_prediction_threshold: float = 0.99):
        """
        初始化检测器

        Args:
            correlation_threshold: 相关系数阈值 (默认 0.9)
            mutual_info_threshold: 互信息阈值 (默认 0.5)
            perfect_prediction_threshold: 完美预测阈值 (默认 0.99)
        """
        self.correlation_threshold = correlation_threshold
        self.mutual_info_threshold = mutual_info_threshold
        self.perfect_prediction_threshold = perfect_prediction_threshold

        self.suspicious_features = []
        self.warnings = []

    def detect_correlation_leakage(self, df: pd.DataFrame, target_col: str = 'actual_result') -> Dict:
        """
        检测相关性泄露

        Args:
            df: 数据框
            target_col: 目标列名

        Returns:
            Dict: 检测结果
        """
        print(f"🔍 检测相关性泄露...")

        if target_col not in df.columns:
            return {'status': 'ERROR', 'message': f'目标列 {target_col} 不存在'}

        # 转换目标为数值
        if df[target_col].dtype == 'object':
            y = (df[target_col] == 'H').astype(int)
        else:
            y = df[target_col].astype(int)

        # 获取数值特征
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        if target_col in numeric_cols:
            numeric_cols.remove(target_col)

        correlations = []
        suspicious = []

        for col in numeric_cols:
            if df[col].nunique() <= 1:  # 跳过常数列
                continue

            try:
                corr, p_value = pearsonr(df[col].fillna(0), y)
                correlations.append({
                    'feature': col,
                    'correlation': corr,
                    'abs_correlation': abs(corr),
                    'p_value': p_value
                })

                # 检查是否泄露
                if abs(corr) > self.correlation_threshold:
                    suspicious.append({
                        'feature': col,
                        'correlation': corr,
                        'abs_correlation': abs(corr),
                        'p_value': p_value,
                        'severity': 'HIGH' if abs(corr) > 0.95 else 'MEDIUM'
                    })

            except Exception as e:
                self.warnings.append(f'特征 {col} 相关性计算失败: {e}')

        # 按绝对相关性排序
        correlations.sort(key=lambda x: x['abs_correlation'], reverse=True)

        print(f"  检查了 {len(correlations)} 个特征")
        print(f"  发现 {len(suspicious)} 个可疑特征")

        if suspicious:
            print(f"  🚨 可疑特征:")
            for feat in suspicious[:10]:
                print(f"     - {feat['feature']}: r={feat['correlation']:.4f} (严重程度: {feat['severity']})")

        return {
            'status': 'PASS' if len(suspicious) == 0 else 'FAIL',
            'suspicious_count': len(suspicious),
            'suspicious_features': suspicious,
            'all_correlations': correlations
        }

    def detect_mutual_info_leakage(self, df: pd.DataFrame, target_col: str = 'actual_result') -> Dict:
        """
        检测互信息泄露

        Args:
            df: 数据框
            target_col: 目标列名

        Returns:
            Dict: 检测结果
        """
        print(f"\n🔍 检测互信息泄露...")

        if target_col not in df.columns:
            return {'status': 'ERROR', 'message': f'目标列 {target_col} 不存在'}

        # 转换目标为数值
        if df[target_col].dtype == 'object':
            y = (df[target_col] == 'H').astype(int)
        else:
            y = df[target_col].astype(int)

        # 获取数值特征
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        if target_col in numeric_cols:
            numeric_cols.remove(target_col)

        # 准备特征矩阵
        X = df[numeric_cols].fillna(0)

        # 计算互信息
        try:
            mi_scores = mutual_info_classif(X, y, random_state=42)

            mi_results = []
            suspicious = []

            for i, col in enumerate(numeric_cols):
                mi_score = mi_scores[i]
                mi_results.append({
                    'feature': col,
                    'mutual_info': mi_score
                })

                # 检查是否泄露
                if mi_score > self.mutual_info_threshold:
                    suspicious.append({
                        'feature': col,
                        'mutual_info': mi_score,
                        'severity': 'HIGH' if mi_score > 0.8 else 'MEDIUM'
                    })

            # 按互信息排序
            mi_results.sort(key=lambda x: x['mutual_info'], reverse=True)

            print(f"  检查了 {len(mi_results)} 个特征")
            print(f"  发现 {len(suspicious)} 个可疑特征")

            if suspicious:
                print(f"  🚨 可疑特征:")
                for feat in suspicious[:10]:
                    print(f"     - {feat['feature']}: MI={feat['mutual_info']:.4f} (严重程度: {feat['severity']})")

            return {
                'status': 'PASS' if len(suspicious) == 0 else 'FAIL',
                'suspicious_count': len(suspicious),
                'suspicious_features': suspicious,
                'all_mi_scores': mi_results
            }

        except Exception as e:
            return {
                'status': 'ERROR',
                'message': f'互信息计算失败: {e}'
            }

    def detect_perfect_prediction(self, df: pd.DataFrame, target_col: str = 'actual_result') -> Dict:
        """
        检测完美预测特征

        Args:
            df: 数据框
            target_col: 目标列名

        Returns:
            Dict: 检测结果
        """
        print(f"\n🔍 检测完美预测特征...")

        if target_col not in df.columns:
            return {'status': 'ERROR', 'message': f'目标列 {target_col} 不存在'}

        # 转换目标为数值
        if df[target_col].dtype == 'object':
            y = (df[target_col] == 'H').astype(int)
        else:
            y = df[target_col].astype(int)

        suspicious = []

        for col in df.columns:
            if col == target_col:
                continue

            # 检查是否完美预测
            try:
                unique_vals = df[col].nunique()
                if unique_vals <= 10:  # 只检查低基数特征
                    # 按特征值分组计算目标均值
                    grouped = df.groupby(col)[target_col].agg(['mean', 'count'])

                    # 检查是否存在完美分割
                    for val, row in grouped.iterrows():
                        if row['count'] >= 5:  # 至少5个样本
                            if row['mean'] == 0 or row['mean'] == 1:
                                suspicious.append({
                                    'feature': col,
                                    'value': val,
                                    'target_mean': row['mean'],
                                    'count': row['count'],
                                    'severity': 'HIGH'
                                })

            except Exception as e:
                self.warnings.append(f'特征 {col} 完美预测检测失败: {e}')

        print(f"  检查了 {len(df.columns)} 个特征")
        print(f"  发现 {len(suspicious)} 个完美预测特征")

        if suspicious:
            print(f"  🚨 可疑特征:")
            for feat in suspicious[:10]:
                print(f"     - {feat['feature']}: 值={feat['value']}, 目标均值={feat['target_mean']:.2f}")

        return {
            'status': 'PASS' if len(suspicious) == 0 else 'FAIL',
            'suspicious_count': len(suspicious),
            'suspicious_features': suspicious
        }

    def random_feature_detection(self, df: pd.DataFrame, sample_size: int = 20) -> Dict:
        """
        随机特征检测

        Args:
            df: 数据框
            sample_size: 随机抽样大小

        Returns:
            Dict: 检测结果
        """
        print(f"\n🔍 随机特征检测...")

        # 随机选择特征
        feature_cols = [col for col in df.columns if df[col].dtype in [np.number]]
        if len(feature_cols) > sample_size:
            np.random.seed(42)
            sampled_features = np.random.choice(feature_cols, sample_size, replace=False)
        else:
            sampled_features = feature_cols

        print(f"  随机抽样 {len(sampled_features)} 个特征进行检测")

        # 检查每个特征的基本统计
        suspicious = []

        for col in sampled_features:
            # 检查标准差
            if df[col].std() == 0:
                suspicious.append({
                    'feature': col,
                    'issue': 'constant',
                    'severity': 'MEDIUM'
                })
                continue

            # 检查异常值
            q1 = df[col].quantile(0.25)
            q3 = df[col].quantile(0.75)
            iqr = q3 - q1
            lower_bound = q1 - 3 * iqr
            upper_bound = q3 + 3 * iqr
            outliers = df[(df[col] < lower_bound) | (df[col] > upper_bound)][col]
            outlier_ratio = len(outliers) / len(df)

            if outlier_ratio > 0.1:  # 超过10%的异常值
                suspicious.append({
                    'feature': col,
                    'issue': f'high_outliers_{outlier_ratio:.2%}',
                    'severity': 'LOW'
                })

        print(f"  发现 {len(suspicious)} 个可疑特征")

        if suspicious:
            print(f"  🚨 可疑特征:")
            for feat in suspicious[:10]:
                print(f"     - {feat['feature']}: {feat['issue']}")

        return {
            'status': 'PASS' if len(suspicious) == 0 else 'WARNING',
            'suspicious_count': len(suspicious),
            'suspicious_features': suspicious,
            'sampled_features': list(sampled_features)
        }

    def full_detection(self, df: pd.DataFrame, target_col: str = 'actual_result') -> Dict:
        """
        完整检测流程

        Args:
            df: 数据框
            target_col: 目标列名

        Returns:
            Dict: 完整检测结果
        """
        print("=" * 80)
        print(f"🚨 V9.6 防作弊检测器 - 数据泄露扫描")
        print("=" * 80)

        results = {
            'overall_status': 'PASS',
            'timestamp': pd.Timestamp.now().isoformat(),
            'data_shape': df.shape,
            'checks': {}
        }

        # 1. 相关性检测
        corr_result = self.detect_correlation_leakage(df, target_col)
        results['checks']['correlation'] = corr_result

        if corr_result['status'] == 'FAIL':
            results['overall_status'] = 'FAIL'
            self.suspicious_features.extend(corr_result['suspicious_features'])

        # 2. 互信息检测
        mi_result = self.detect_mutual_info_leakage(df, target_col)
        results['checks']['mutual_info'] = mi_result

        if mi_result['status'] == 'FAIL':
            results['overall_status'] = 'FAIL'
            self.suspicious_features.extend(mi_result['suspicious_features'])

        # 3. 完美预测检测
        perfect_result = self.detect_perfect_prediction(df, target_col)
        results['checks']['perfect_prediction'] = perfect_result

        if perfect_result['status'] == 'FAIL':
            results['overall_status'] = 'FAIL'
            self.suspicious_features.extend(perfect_result['suspicious_features'])

        # 4. 随机特征检测
        random_result = self.random_feature_detection(df)
        results['checks']['random_features'] = random_result

        if random_result['status'] == 'FAIL':
            results['overall_status'] = 'FAIL'
            self.suspicious_features.extend(random_result['suspicious_features'])

        # 5. 生成报告
        print(f"\n" + "=" * 80)
        print(f"📊 检测报告")
        print("=" * 80)

        for check_name, check_result in results['checks'].items():
            status_icon = '✅' if check_result['status'] == 'PASS' else '❌'
            print(f"{status_icon} {check_name}: {check_result['status']}")
            if 'suspicious_count' in check_result:
                print(f"   可疑特征数: {check_result['suspicious_count']}")

        print(f"\n🎯 总体状态: {results['overall_status']}")
        print(f"📊 总可疑特征数: {len(self.suspicious_features)}")

        if self.warnings:
            print(f"\n⚠️ 警告:")
            for warning in self.warnings[:5]:
                print(f"   - {warning}")

        # 6. 决定是否中止训练
        if results['overall_status'] == 'FAIL':
            print(f"\n❌ 检测失败！发现 {len(self.suspicious_features)} 个可疑特征")
            print(f"建议: 检查并清理可疑特征后重新训练")
            return results
        else:
            print(f"\n✅ 检测通过！未发现明显的数据泄露")
            return results


def main():
    """主函数 - 示例用法"""
    # 创建检测器
    detector = DataLeakageDetector(
        correlation_threshold=0.9,
        mutual_info_threshold=0.5
    )

    # 加载测试数据
    try:
        df = pd.read_csv('/home/user/projects/FootballPrediction/data/combined_multi_season_odds.csv')
        print(f"加载数据: {len(df)} 行 x {len(df.columns)} 列")

        # 执行检测
        results = detector.full_detection(df, target_col='actual_result')

        # 根据结果决定是否继续
        if results['overall_status'] == 'FAIL':
            print(f"\n🚫 检测失败，中止训练")
            sys.exit(1)
        else:
            print(f"\n✅ 检测通过，继续训练")
            sys.exit(0)

    except Exception as e:
        print(f"❌ 检测失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
