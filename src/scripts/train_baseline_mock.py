#!/usr/bin/env python3
"""
模拟数据基线模型训练脚本
使用完全模拟的数据测试ML训练流程
"""

import asyncio
import sys
import os
import logging
from pathlib import Path
from typing import Dict, Any
import json
from datetime import datetime

import pandas as pd
import numpy as np
from xgboost import XGBClassifier
from sklearn.metrics import accuracy_score, precision_score
import joblib

# 添加项目根路径
project_root = Path(__file__).parent.parent  # src/scripts -> src
football_prediction_root = project_root.parent  # src -> project root

sys.path.insert(0, str(football_prediction_root))
sys.path.insert(0, str(football_prediction_root / "FootballPrediction"))
from src.ml.features.rolling import RollingAverageTransformer

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MockDataLoader:
    """模拟数据加载器 - 生成符合ML需求的足球比赛数据"""

    def __init__(self, num_teams: int = 20, num_matches: int = 500):
        self.num_teams = num_teams
        self.num_matches = num_matches
        self.teams = self._generate_teams()

    def _generate_teams(self) -> list:
        """生成球队列表"""
        team_names = [
            f"球队{i}" for i in range(1, self.num_teams + 1)
        ]
        team_ids = list(range(1001, 1001 + self.num_teams))

        return list(zip(team_ids, team_names))

    async def load_data(self) -> pd.DataFrame:
        """生成模拟比赛数据

        返回格式:
        - 每行代表一支球队在一场比赛中的表现
        - 包含 team_id, match_date, goals_scored, goals_conceded, xg, shots, corners, result
        """
        np.random.seed(42)  # 确保可重现

        matches = []
        match_id = 1

        # 生成比赛日程
        for match_date in pd.date_range('2022-01-01', '2024-12-01', freq='3D'):
            if len(matches) >= self.num_matches * 2:  # 每场比赛生成两条记录（主队+客队）
                break

            # 随机选择两支球队
            team1_idx, team2_idx = np.random.choice(len(self.teams), 2, replace=False)
            team1_id, team1_name = self.teams[team1_idx]
            team2_id, team2_name = self.teams[team2_idx]

            # 模拟球队实力（隐藏变量）
            team1_strength = np.random.normal(0.5, 0.15)
            team2_strength = np.random.normal(0.5, 0.15)

            # 主队优势
            home_advantage = 0.1

            # 基于实力生成期望进球
            team1_xg = min(max(team1_strength + home_advantage + np.random.normal(0, 0.1), 0.1), 0.9)
            team2_xg = min(max(team2_strength - home_advantage + np.random.normal(0, 0.1), 0.1), 0.9)

            # 生成实际进球（泊松分布）
            team1_goals = np.random.poisson(team1_xg * 2.5)
            team2_goals = np.random.poisson(team2_xg * 2.5)

            # 生成其他统计
            team1_shots = int(team1_xg * 15 + np.random.normal(0, 3))
            team2_shots = int(team2_xg * 15 + np.random.normal(0, 3))
            team1_shots = max(5, min(30, team1_shots))
            team2_shots = max(5, min(30, team2_shots))

            team1_corners = int(team1_xg * 8 + np.random.normal(0, 2))
            team2_corners = int(team2_xg * 8 + np.random.normal(0, 2))
            team1_corners = max(1, min(15, team1_corners))
            team2_corners = max(1, min(15, team2_corners))

            # 主队记录
            home_result = 'win' if team1_goals > team2_goals else ('draw' if team1_goals == team2_goals else 'loss')
            matches.append({
                'match_id': match_id,
                'match_date': match_date,
                'team_id': team1_id,
                'opponent_id': team2_id,
                'venue': 'home',
                'goals_scored': team1_goals,
                'goals_conceded': team2_goals,
                'xg': team1_xg,
                'shots': team1_shots,
                'corners': team1_corners,
                'result': home_result
            })

            # 客队记录
            away_result = 'win' if team2_goals > team1_goals else ('draw' if team2_goals == team1_goals else 'loss')
            matches.append({
                'match_id': match_id,
                'match_date': match_date,
                'team_id': team2_id,
                'opponent_id': team1_id,
                'venue': 'away',
                'goals_scored': team2_goals,
                'goals_conceded': team1_goals,
                'xg': team2_xg,
                'shots': team2_shots,
                'corners': team2_corners,
                'result': away_result
            })

            match_id += 1

        df = pd.DataFrame(matches)

        # 确保数据类型正确
        numeric_cols = ['goals_scored', 'goals_conceded', 'xg', 'shots', 'corners']
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        # 按日期排序
        df = df.sort_values('match_date').reset_index(drop=True)

        logger.info(f"✅ 生成模拟数据: {len(df)} 条记录")
        logger.info(f"📊 比赛场次: {df['match_id'].nunique()}")
        logger.info(f"🏆 球队数量: {df['team_id'].nunique()}")
        logger.info(f"📅 数据时间范围: {df['match_date'].min()} 到 {df['match_date'].max()}")

        return df


async def train_mock_model():
    """使用模拟数据训练基线模型"""
    logger.info("🚀 开始模拟数据基线模型训练")

    try:
        # 1. 数据加载
        logger.info("📊 第1步: 数据加载...")
        data_loader = MockDataLoader(num_teams=20, num_matches=400)
        df = await data_loader.load_data()

        logger.info(f"📋 数据列名: {list(df.columns)}")
        logger.info(f"📋 数据样例:\n{df.head(3).to_string()}")

        # 2. 特征工程
        logger.info("⚙️ 第2步: 特征工程...")
        rolling_transformer = RollingAverageTransformer(
            windows=[3, 10],
            columns=['goals_scored', 'goals_conceded', 'xg', 'shots', 'corners'],
            group_by=['team_id'],
            date_column='match_date'
        )

        # 应用特征工程
        df_features = rolling_transformer.fit_transform(df)
        logger.info(f"✅ 特征工程完成，新增 {len(df_features.columns) - len(df.columns)} 个特征")

        # 3. 数据预处理
        logger.info("🔧 第3步: 数据预处理...")

        # 删除包含NaN的行（由于滚动窗口的shift(1)）
        initial_rows = len(df_features)
        df_clean = df_features.dropna()
        cleaned_rows = len(df_clean)
        logger.info(f"🧹 数据清洗: {initial_rows} -> {cleaned_rows} 行 (删除 {initial_rows - cleaned_rows} 行)")

        # 创建目标变量
        df_clean['target'] = (df_clean['result'] == 'win').astype(int)

        # 选择特征列
        feature_cols = [col for col in df_clean.columns
                       if col.startswith('rolling_') and col.endswith('_mean')]

        logger.info(f"🎯 特征数量: {len(feature_cols)}")
        logger.info(f"📋 特征列表: {feature_cols[:5]}...")  # 显示前5个

        X = df_clean[feature_cols]
        y = df_clean['target']

        # 4. 时间序列分割
        logger.info("✂️ 第4步: 时间序列数据分割...")
        split_idx = int(len(X) * 0.8)
        X_train = X.iloc[:split_idx]
        X_test = X.iloc[split_idx:]
        y_train = y.iloc[:split_idx]
        y_test = y.iloc[split_idx:]

        logger.info(f"📊 训练集: {len(X_train)} 样本")
        logger.info(f"📊 测试集: {len(X_test)} 样本")
        logger.info(f"📈 胜率 - 训练集: {y_train.mean():.2%}, 测试集: {y_test.mean():.2%}")

        # 5. 模型训练
        logger.info("🧠 第5步: XGBoost模型训练...")
        model = XGBClassifier(
            n_estimators=100,
            max_depth=4,
            learning_rate=0.1,
            random_state=42,
            eval_metric='logloss',
            use_label_encoder=False
        )

        model.fit(X_train, y_train)
        logger.info("✅ 模型训练完成")

        # 6. 模型评估
        logger.info("📊 第6步: 模型评估...")
        y_pred = model.predict(X_test)

        accuracy = accuracy_score(y_test, y_pred)
        precision = precision_score(y_test, y_pred, zero_division=0)

        logger.info(f"🎯 模型性能:")
        logger.info(f"   Accuracy: {accuracy:.4f} ({accuracy:.2%})")
        logger.info(f"   Precision: {precision:.4f} ({precision:.2%})")

        # 7. 特征重要性
        logger.info("🔍 第7步: 特征重要性分析...")
        feature_importance = model.get_booster().get_score(importance_type='gain')

        # 排序并显示前10个重要特征
        sorted_features = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)
        top_features = sorted_features[:10]

        logger.info("🏆 Top 10 重要特征:")
        for i, (feature, importance) in enumerate(top_features, 1):
            logger.info(f"   {i:2d}. {feature:<25} : {importance:.4f}")

        # 8. 模型保存
        logger.info("💾 第8步: 保存模型...")
        model_dir = football_prediction_root / "models"
        model_dir.mkdir(exist_ok=True)

        model_path = model_dir / "baseline_v1_mock.json"
        model.save_model(str(model_path))

        # 保存特征信息
        model_info = {
            "model_type": "XGBClassifier",
            "features": feature_cols,
            "feature_importance": feature_importance,
            "performance": {
                "accuracy": float(accuracy),
                "precision": float(precision)
            },
            "training_data": {
                "total_samples": len(X),
                "train_samples": len(X_train),
                "test_samples": len(X_test),
                "feature_count": len(feature_cols)
            },
            "training_date": datetime.now().isoformat(),
            "data_type": "mock"
        }

        info_path = model_dir / "baseline_v1_mock_info.json"
        with open(info_path, 'w', encoding='utf-8') as f:
            json.dump(model_info, f, indent=2, ensure_ascii=False)

        logger.info(f"✅ 模型已保存到: {model_path}")
        logger.info(f"📄 模型信息已保存到: {info_path}")

        # 9. 总结报告
        logger.info("📋 第9步: 生成训练报告...")
        logger.info("=" * 60)
        logger.info("🎉 模拟数据基线模型训练完成!")
        logger.info("=" * 60)
        logger.info(f"📊 模型性能:")
        logger.info(f"   • Accuracy:  {accuracy:.2%}")
        logger.info(f"   • Precision: {precision:.2%}")
        logger.info(f"🔧 技术规格:")
        logger.info(f"   • 特征数量:   {len(feature_cols)}")
        logger.info(f"   • 训练样本:   {len(X_train):,}")
        logger.info(f"   • 测试样本:   {len(X_test):,}")
        logger.info(f"   • 模型类型:   XGBoost v2.0+")
        logger.info(f"💾 输出文件:")
        logger.info(f"   • 模型文件:   {model_path}")
        logger.info(f"   • 信息文件:   {info_path}")
        logger.info("=" * 60)

        return {
            "accuracy": accuracy,
            "precision": precision,
            "feature_importance": top_features,
            "model_path": str(model_path)
        }

    except Exception as e:
        logger.error(f"❌ 训练失败: {e}")
        import traceback
        traceback.print_exc()
        return None


async def main():
    """主函数"""
    logger.info("🚀 足球预测系统 - 模拟数据基线模型训练")
    logger.info("=" * 60)

    result = await train_mock_model()

    if result:
        logger.info("✅ 训练流程圆满完成!")
        logger.info("🎯 下一步:")
        logger.info("  1. 检查模型文件: models/baseline_v1_mock.json")
        logger.info("  2. 查看特征重要性: models/baseline_v1_mock_info.json")
        logger.info("  3. 测试模型推理: 创建预测脚本")
        logger.info("  4. 准备真实数据: 连接生产数据库")
    else:
        logger.error("❌ 训练失败，请检查错误信息")


if __name__ == "__main__":
    asyncio.run(main())