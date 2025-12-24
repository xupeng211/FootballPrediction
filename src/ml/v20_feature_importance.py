#!/usr/bin/env python3
"""
V20.3 Feature Importance Analysis
==================================

分析 V20.3 提取的特征对平局预测的重要性

数据来源: match_features_training 表
分析方法: XGBoost + Gain 分数
目标: 识别 Top 20 影响平局预测的特征
"""

import os
import sys
import pandas as pd
import numpy as np
import xgboost as xgb
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report, confusion_matrix
import warnings
warnings.filterwarnings('ignore')

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

load_dotenv(override=True)


class V20FeatureImportanceAnalyzer:
    """V20.3 特征重要性分析器"""

    def __init__(self):
        self.conn = None
        self.df = None
        self.X_train = None
        self.X_test = None
        self.y_train = None
        self.y_test = None
        self.model = None
        self.feature_names = None

    def get_db_connection(self):
        """获取数据库连接"""
        host = os.getenv("DB_HOST", "localhost")
        port = int(os.getenv("DB_PORT", 5432))
        database = os.getenv("DB_NAME", "football_db")
        user = os.getenv("DB_USER", "football_user")
        password = os.getenv("DB_PASSWORD", "football_pass")

        # Docker 主机名处理
        if host in ["db", "redis"]:
            import socket
            try:
                socket.create_connection((host, port), timeout=1).close()
            except (socket.timeout, ConnectionRefusedError, OSError):
                host = "localhost"

        self.conn = psycopg2.connect(
            host=host, port=port, database=database,
            user=user, password=password
        )
        return self.conn

    def load_feature_data(self):
        """从 match_features_training 表加载特征数据"""
        print("=" * 60)
        print("V20.3 特征重要性分析器")
        print("=" * 60)

        conn = self.get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # 获取所有数据
        query = """
            SELECT * FROM match_features_training
            WHERE home_score IS NOT NULL
            AND away_score IS NOT NULL
        """
        cursor.execute(query)
        rows = cursor.fetchall()

        # 转换为 DataFrame
        self.df = pd.DataFrame(rows)

        print(f"\n数据集加载完成:")
        print(f"  总比赛数: {len(self.df)}")
        print(f"  特征维度: {len(self.df.columns)}")

        cursor.close()
        conn.close()

        return self.df

    def create_target_variable(self):
        """创建目标变量: 0=主胜, 1=平局, 2=客胜"""
        print("\n创建目标变量...")

        targets = []
        for _, row in self.df.iterrows():
            home_score = row.get('home_score')
            away_score = row.get('away_score')

            if home_score is None or away_score is None:
                targets.append(-1)  # 无效数据
            elif home_score > away_score:
                targets.append(0)  # home_win
            elif home_score == away_score:
                targets.append(1)  # draw
            else:
                targets.append(2)  # away_win

        self.df['target'] = targets

        # 统计分布
        target_counts = pd.Series(targets).value_counts().sort_index()
        print(f"\n目标变量分布:")
        print(f"  主胜 (0): {target_counts.get(0, 0)} 场 ({target_counts.get(0, 0)/len(targets)*100:.1f}%)")
        print(f"  平局 (1): {target_counts.get(1, 0)} 场 ({target_counts.get(1, 0)/len(targets)*100:.1f}%)")
        print(f"  客胜 (2): {target_counts.get(2, 0)} 场 ({target_counts.get(2, 0)/len(targets)*100:.1f}%)")

        # 过滤无效数据
        self.df = self.df[self.df['target'] != -1]
        print(f"\n有效数据: {len(self.df)} 场")

    def prepare_features(self):
        """准备特征矩阵 - 只使用赛前特征（避免数据泄露）"""
        print("\n准备特征矩阵...")

        # 从 enriched_features JSONB 提取所有特征
        all_features = []
        for _, row in self.df.iterrows():
            enriched = row.get('enriched_features')
            if isinstance(enriched, dict):
                all_features.append(enriched)
            else:
                all_features.append({})

        # 转换为 DataFrame
        features_df = pd.DataFrame(all_features)

        print(f"  从 enriched_features 提取了 {len(features_df.columns)} 个特征")

        # V20.3.1: 只使用赛前可用特征（排除赛后统计数据）
        # 赛前特征包括：阵容元数据、球员评分、阵型等
        # 排除：比赛过程中的统计数据（shots, xG, possession等）
        pre_match_keywords = [
            'meta_',           # 阵容元数据
            'formation',       # 阵型
            'coach',           # 教练
            'avg_age',         # 平均年龄
            'market_value',    # 市场价值
            'starter',         # 首发
            'bench',           # 替补
            'unavailable',     # 缺阵
            '_count',          # 计数
            '_rating'          # 评分（基准评分）
        ]

        # 排除赛后统计关键词
        post_match_keywords = [
            'shots', 'xg', 'possession', 'passes', 'corners',
            'fouls', 'offsides', 'accurate_', 'total_', 'diff_',
            'ballposs', 'duels', 'defence_', 'discipline_',
            'expected_goals', 'big_chance', 'clearances', 'interceptions',
            'tackles', 'blocks', 'saves', 'touches', ' aerial'
        ]

        pre_match_features = []
        for col in features_df.columns:
            col_lower = col.lower()

            # 检查是否是赛前特征
            is_pre_match = any(kw in col_lower for kw in pre_match_keywords)
            # 检查是否是赛后统计（需要排除）
            is_post_match = any(kw in col_lower for kw in post_match_keywords)

            if is_pre_match and not is_post_match:
                # 进一步检查：排除包含赛后统计词汇的特征
                if col.startswith('home_') or col.startswith('away_') or col.startswith('diff_') or col.startswith('total_'):
                    # 这些通常是赛后统计，跳过
                    continue
                pre_match_features.append(col)

        print(f"  赛前特征数量: {len(pre_match_features)}")

        # 如果没有赛前特征，使用所有 meta_ 开头的特征
        if not pre_match_features:
            pre_match_features = [col for col in features_df.columns if col.startswith('meta_')]
            print(f"  使用 meta_ 特征: {len(pre_match_features)} 个")

        # 创建特征矩阵
        X = features_df[pre_match_features].copy()

        # 转换为数值
        for col in X.columns:
            X[col] = pd.to_numeric(X[col], errors='coerce')

        # 填充缺失值
        for col in X.columns:
            if X[col].isna().sum() > 0:
                median_val = X[col].median()
                if pd.isna(median_val):
                    X[col].fillna(0, inplace=True)
                else:
                    X[col].fillna(median_val, inplace=True)

        # 移除无穷值和常数列
        X = X.replace([np.inf, -np.inf], 0)

        # 移除常数列（所有值相同）
        constant_cols = []
        for col in X.columns:
            if X[col].nunique() <= 1:
                constant_cols.append(col)

        if constant_cols:
            X = X.drop(columns=constant_cols)
            print(f"  移除常数列: {len(constant_cols)} 个")

        y = self.df['target'].values

        self.feature_names = list(X.columns)

        print(f"  最终特征矩阵形状: {X.shape}")
        print(f"  目标变量形状: {y.shape}")

        return X, y

    def train_model(self, X, y):
        """训练 XGBoost 模型"""
        print("\n训练 XGBoost 模型...")

        # 划分数据集
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )

        self.X_train = X_train
        self.X_test = X_test
        self.y_train = y_train
        self.y_test = y_test

        print(f"  训练集: {len(X_train)} 场")
        print(f"  测试集: {len(X_test)} 场")

        # 训练模型
        self.model = xgb.XGBClassifier(
            n_estimators=200,
            max_depth=6,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            eval_metric='mlogloss',
            use_label_encoder=False
        )

        self.model.fit(X_train, y_train)

        # 评估
        train_acc = self.model.score(X_train, y_train)
        test_acc = self.model.score(X_test, y_test)

        print(f"\n模型性能:")
        print(f"  训练集准确率: {train_acc:.3f}")
        print(f"  测试集准确率: {test_acc:.3f}")

        # 详细分类报告
        y_pred = self.model.predict(X_test)
        print("\n分类报告:")
        print(classification_report(y_test, y_pred,
                                    target_names=['主胜', '平局', '客胜']))

        return self.model

    def analyze_feature_importance(self):
        """分析特征重要性"""
        print("\n" + "=" * 60)
        print("特征重要性分析")
        print("=" * 60)

        # V20.3.1 FIX: 直接使用 feature_importances_ 属性
        # 这个方法更可靠，因为特征顺序与 DataFrame 列顺序一致
        print("  使用 feature_importances_ 属性 (gain-based)")
        raw_importance = self.model.feature_importances_

        # 创建重要性列表
        importance_list = []
        for i, feature in enumerate(self.feature_names):
            importance_list.append({
                'feature': feature,
                'gain_score': float(raw_importance[i])
            })

        importance_df = pd.DataFrame(importance_list)
        importance_df = importance_df.sort_values('gain_score', ascending=False)

        # 只显示有非零重要性的特征
        importance_df = importance_df[importance_df['gain_score'] > 0].reset_index(drop=True)

        # 计算百分比
        total_score = importance_df['gain_score'].sum()
        if total_score > 0:
            importance_df['importance_percent'] = (
                importance_df['gain_score'] / total_score * 100
            )
        else:
            importance_df['importance_percent'] = 0

        # 显示 Top 20
        top_20 = importance_df.head(20)

        print(f"\n🏆 Top 20 重要特征:")
        print("-" * 80)
        for i, row in top_20.iterrows():
            print(f"{row['feature']:<45} | Score: {row['gain_score']:.6f} | {row['importance_percent']:.2f}%")

        # 特征分类
        if len(importance_df) >= 50:
            self._categorize_features(importance_df.head(50))
        else:
            self._categorize_features(importance_df)

        return importance_df

    def _categorize_features(self, top_features):
        """对 Top 50 特征进行分类"""
        print("\n" + "-" * 60)
        print("Top 50 特征分类:")
        print("-" * 60)

        categories = {
            '球员评分 (Player Rating)': [],
            '位置统计 (Position Stats)': [],
            '阵容数据 (Lineup Meta)': [],
            '控球相关 (Possession)': [],
            '射门相关 (Shots/xG)': [],
            '其他 (Other)': []
        }

        for feature in top_features['feature']:
            feature_lower = feature.lower()

            if any(kw in feature_lower for kw in ['rating', 'avg_rating', 'min_rating', 'max_rating']):
                if 'position' in feature_lower or 'gk' in feature_lower or 'df' in feature_lower or 'mf' in feature_lower or 'fw' in feature_lower:
                    categories['位置统计 (Position Stats)'].append(feature)
                else:
                    categories['球员评分 (Player Rating)'].append(feature)
            elif 'meta_' in feature_lower:
                if any(kw in feature_lower for kw in ['formation', 'coach', 'age', 'market', 'count']):
                    categories['阵容数据 (Lineup Meta)'].append(feature)
                else:
                    categories['其他 (Other)'].append(feature)
            elif 'possession' in feature_lower:
                categories['控球相关 (Possession)'].append(feature)
            elif any(kw in feature_lower for kw in ['shot', 'xg', 'goal']):
                categories['射门相关 (Shots/xG)'].append(feature)
            else:
                categories['其他 (Other)'].append(feature)

        for cat_name, features in categories.items():
            if features:
                print(f"\n{cat_name}: {len(features)} 个")
                for f in features[:5]:
                    idx = top_features[top_features['feature'] == f].index[0]
                    imp = top_features.loc[idx, 'importance_percent']
                    print(f"  - {f} ({imp:.2f}%)")

    def analyze_draw_importance(self):
        """专门分析影响平局预测的特征"""
        print("\n" + "=" * 60)
        print("平局预测特征重要性分析")
        print("=" * 60)

        # 训练二分类模型 (平局 vs 非平局)
        # 创建一个专注于平局的模型
        draw_model = xgb.XGBClassifier(
            n_estimators=200,
            max_depth=6,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            eval_metric='logloss',
            use_label_encoder=False
        )

        draw_model.fit(self.X_train, (self.y_train == 1).astype(int))

        # V20.3.1 FIX: 直接使用 feature_importances_ 属性
        print("  使用 feature_importances_ 属性 (gain-based)")
        raw_importance = draw_model.feature_importances_

        importance_list = []
        for i, feature in enumerate(self.feature_names):
            importance_list.append({
                'feature': feature,
                'gain_score': float(raw_importance[i])
            })

        importance_df = pd.DataFrame(importance_list)
        importance_df = importance_df.sort_values('gain_score', ascending=False)

        # 只显示有非零重要性的特征
        importance_df = importance_df[importance_df['gain_score'] > 0].reset_index(drop=True)

        # 计算百分比
        total_score = importance_df['gain_score'].sum()
        if total_score > 0:
            importance_df['importance_percent'] = (
                importance_df['gain_score'] / total_score * 100
            )
        else:
            importance_df['importance_percent'] = 0

        top_20 = importance_df.head(20)

        print(f"\n🎯 Top 20 影响平局预测的特征:")
        print("-" * 80)
        for i, row in top_20.iterrows():
            print(f"{row['feature']:<45} | Score: {row['gain_score']:.6f} | {row['importance_percent']:.2f}%")

        return importance_df

    def save_results(self, general_importance, draw_importance):
        """保存分析结果"""
        output_dir = "data/analysis"
        os.makedirs(output_dir, exist_ok=True)

        # 保存通用特征重要性
        general_path = os.path.join(output_dir, "v20_feature_importance_general.csv")
        general_importance.to_csv(general_path, index=False)
        print(f"\n通用特征重要性已保存到: {general_path}")

        # 保存平局特征重要性
        draw_path = os.path.join(output_dir, "v20_feature_importance_draw.csv")
        draw_importance.to_csv(draw_path, index=False)
        print(f"平局特征重要性已保存到: {draw_path}")

        # 保存 Top 20 汇总
        summary_path = os.path.join(output_dir, "v20_top20_features_summary.txt")
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write("=" * 60 + "\n")
            f.write("V20.3 特征重要性分析报告\n")
            f.write("=" * 60 + "\n\n")

            f.write("数据集规模:\n")
            f.write(f"  总比赛数: {len(self.df)}\n")
            f.write(f"  训练集: {len(self.X_train)}\n")
            f.write(f"  测试集: {len(self.X_test)}\n\n")

            f.write("模型性能:\n")
            f.write(f"  测试集准确率: {self.model.score(self.X_test, self.y_test):.3f}\n\n")

            f.write("-" * 60 + "\n")
            f.write("Top 20 通用特征重要性\n")
            f.write("-" * 60 + "\n")
            for i, row in general_importance.head(20).iterrows():
                f.write(f"{i+1:2d}. {row['feature']:<45} | {row['importance_percent']:.2f}%\n")

            f.write("\n" + "-" * 60 + "\n")
            f.write("Top 20 平局预测特征重要性\n")
            f.write("-" * 60 + "\n")
            for i, row in draw_importance.head(20).iterrows():
                f.write(f"{i+1:2d}. {row['feature']:<45} | {row['importance_percent']:.2f}%\n")

        print(f"分析报告已保存到: {summary_path}")

    def run_full_analysis(self):
        """运行完整分析流程"""
        try:
            # 1. 加载数据
            self.load_feature_data()

            # 2. 创建目标变量
            self.create_target_variable()

            # 3. 准备特征
            X, y = self.prepare_features()

            # 4. 训练模型
            self.train_model(X, y)

            # 5. 分析特征重要性
            general_importance = self.analyze_feature_importance()

            # 6. 分析平局特征重要性
            draw_importance = self.analyze_draw_importance()

            # 7. 保存结果
            self.save_results(general_importance, draw_importance)

            print("\n" + "=" * 60)
            print("✅ V20.3 特征重要性分析完成！")
            print("=" * 60)

            return general_importance, draw_importance

        except Exception as e:
            print(f"\n❌ 分析失败: {e}")
            import traceback
            traceback.print_exc()
            return None, None


def main():
    """主入口"""
    analyzer = V20FeatureImportanceAnalyzer()
    return analyzer.run_full_analysis()


if __name__ == "__main__":
    general_importance, draw_importance = main()
