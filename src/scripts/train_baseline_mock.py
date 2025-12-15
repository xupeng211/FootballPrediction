#!/usr/bin/env python3
"""
天网系统 - Baseline 模型训练脚本（模拟数据版本）

Phase 2.3: Training Pipeline - 实战训练（模拟数据）

当数据库中缺少比赛数据时，使用模拟数据来测试训练管道。
生成的模拟数据具有真实的足球比赛统计特征。

模拟数据特点：
- 100场比赛，涵盖5个球队
- 包含真实分布的进球数、xG值、控球率
- 时间序列分布，支持滚动窗口特征计算
"""

import asyncio
import logging
import pandas as pd
import numpy as np
import sys
import os
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict

# Ensure src is in pythonpath
sys.path.append(os.getcwd())

from src.ml.features.rolling import RollingAverageTransformer
from src.ml.training.trainer import ModelTrainer

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/training_mock.log')
    ]
)
logger = logging.getLogger(__name__)

# 确保日志目录存在
os.makedirs('logs', exist_ok=True)


class MockDataLoader:
    """模拟数据加载器，生成训练用的模拟比赛数据"""

    def __init__(self, n_matches=200):
        self.n_matches = n_matches

    async def load_data(self) -> pd.DataFrame:
        """生成模拟比赛数据"""
        logger.info(f"📊 生成 {self.n_matches} 场模拟比赛数据...")

        # 创建球队数据
        team_ids = ['team_1', 'team_2', 'team_3', 'team_4', 'team_5']
        team_names = ['Arsenal', 'Manchester United', 'Liverpool', 'Chelsea', 'Manchester City']
        teams = dict(zip(team_ids, team_names))

        # 生成比赛数据
        start_date = datetime(2023, 1, 1)
        matches = []

        np.random.seed(42)  # 确保可重现

        for i in range(self.n_matches):
            match_date = start_date + timedelta(days=i)

            # 随机选择主客场球队
            home_idx = np.random.choice(len(team_ids))
            home_team_id = team_ids[home_idx]
            home_team_name = team_names[home_idx]

            # 确保客场球队不同
            away_idx = np.random.choice([i for i in range(len(team_ids)) if i != home_idx])
            away_team_id = team_ids[away_idx]
            away_team_name = team_names[away_idx]

            # 生成比赛统计（基于真实足球数据的分布）
            # 进球数：使用泊松分布（符合足球进球模式）
            home_score = np.random.poisson(1.4)
            away_score = np.random.poisson(1.1)

            # xG（期望进球）：使用伽马分布
            home_xg = np.random.gamma(2.0, 0.7)
            away_xg = np.random.gamma(1.8, 0.6)

            # 控球率：正态分布，确保两队和为100
            home_possession = np.clip(np.random.normal(50, 15), 20, 80)
            away_possession = 100 - home_possession

            # 射门数
            home_shots = np.random.poisson(12)
            away_shots = np.random.poisson(10)

            # 黄牌数
            home_yellow = np.random.poisson(1.5)
            away_yellow = np.random.poisson(1.2)

            match = {
                'match_date': match_date,
                'home_team_id': home_team_id,
                'home_team_name': home_team_name,
                'away_team_id': away_team_id,
                'away_team_name': away_team_name,
                'home_score': home_score,
                'away_score': away_score,
                'home_expected_goals': round(home_xg, 2),
                'away_expected_goals': round(away_xg, 2),
                'home_possession': home_possession,
                'away_possession': away_possession,
                'home_shots': home_shots,
                'away_shots': away_shots,
                'home_yellow_cards': home_yellow,
                'away_yellow_cards': away_yellow,
                'venue': 'Stadium',
                'attendance': np.random.randint(30000, 80000),
                'status': 'completed'
            }

            matches.append(match)

        df = pd.DataFrame(matches)

        logger.info(f"✅ 成功生成 {len(df)} 场比赛数据")
        logger.info(f"📅 数据时间范围: {df['match_date'].min()} 到 {df['match_date'].max()}")

        # 显示数据统计
        logger.info(f"📈 数据统计:")
        logger.info(f"   平均主队进球: {df['home_score'].mean():.2f}")
        logger.info(f"   平均客队进球: {df['away_score'].mean():.2f}")
        logger.info(f"   平均主队xG: {df['home_expected_goals'].mean():.2f}")
        logger.info(f"   平均客队xG: {df['away_expected_goals'].mean():.2f}")

        return df


async def main():
    """主训练函数"""
    start_time = datetime.now()
    logger.info("🚀 启动天网系统 - Baseline 模型训练任务（模拟数据）")
    logger.info(f"训练开始时间: {start_time}")

    try:
        # 1. 初始化模拟数据加载器
        logger.info("📊 初始化模拟数据加载器...")
        loader = MockDataLoader(n_matches=500)  # 使用500场比赛数据

        # 2. 定义特征工程策略
        logger.info("⚙️ 配置特征工程管道...")

        # 核心特征列：关注球队的关键表现指标
        feature_columns = [
            'home_score',           # 主队进球数
            'away_score',           # 客队进球数
            'home_expected_goals',  # 主队期望进球(xG)
            'away_expected_goals',  # 客队期望进球(xG)
            'home_possession',      # 主队控球率
            'away_possession'       # 客队控球率
        ]

        transformers = [
            RollingAverageTransformer(
                windows=[3, 10],  # 3场(短期)和10场(长期)滚动窗口
                columns=feature_columns,
                group_by=['home_team_id', 'away_team_id'],  # 按主客球队分组计算
                date_column='match_date',
                output_prefix='rolling'  # 特征名前缀
            )
        ]

        logger.info(f"📈 特征工程配置: {len(feature_columns)}个基础特征，{len(transformers)}个转换器")
        logger.info(f"🎯 特征列: {feature_columns}")
        logger.info(f"⏰ 滚动窗口: [3, 10] 场比赛")

        # 3. 初始化模型训练器
        logger.info("🧠 初始化XGBoost模型训练器...")
        trainer = ModelTrainer(
            data_loader=loader,
            feature_transformers=transformers,
            model_params={
                'n_estimators': 100,      # 树的数量
                'max_depth': 4,          # 树的深度（略微增加以处理更复杂特征）
                'learning_rate': 0.1,     # 学习率
                'objective': 'binary:logistic',  # 二分类目标
                'random_state': 42,      # 随机种子，确保结果可重现
                'eval_metric': 'logloss',
                'use_label_encoder': False,
                'n_jobs': -1             # 并行计算
            }
        )

        # 4. 执行训练管道
        logger.info("🏃‍♂️ 开始执行训练管道...")
        logger.info("⚠️ 使用时间序列切分，最后20%数据作为测试集")

        metrics = await trainer.run(test_size=0.2)

        # 5. 输出训练结果
        print("\n" + "="*80)
        print(f"🏆 天网系统 - Baseline 模型训练结果汇报（模拟数据）")
        print(f"训练完成时间: {datetime.now()}")
        print(f"总训练时长: {(datetime.now() - start_time).total_seconds():.1f}秒")
        print("="*80)

        # 性能指标
        print(f"🎯 模型性能指标:")
        print(f"   ✅ Accuracy (准确率): {metrics['accuracy']:.2%}")
        print(f"   ✅ Precision (精准率): {metrics['precision']:.2%}")
        print(f"   📊 训练样本数: {metrics['train_samples']:,}")
        print(f"   🧪 测试样本数: {metrics['test_samples']:,}")
        print(f"   📈 训练/测试比例: {(1-0.2):.1%}/{0.2:.1%}")

        # 模型信息
        print(f"\n🤖 模型配置:")
        print(f"   🌳 XGBoost 树数量: {trainer.model_params['n_estimators']}")
        print(f"   📏 最大深度: {trainer.model_params['max_depth']}")
        print(f"   📚 学习率: {trainer.model_params['learning_rate']}")
        print(f"   🎲 随机种子: {trainer.model_params['random_state']}")

        # 6. 查看特征重要性
        print(f"\n🔑 关键致胜因子 (Feature Importance Top 10):")
        importance_df = trainer.get_feature_importance()
        if importance_df is not None and not importance_df.empty:
            # 格式化输出
            for i, row in importance_df.head(10).iterrows():
                importance_pct = row['importance'] * 100
                feature_name = row['feature']
                print(f"   {i+1:2d}. {feature_name:<25} {importance_pct:>6.2f}%")
        else:
            print("   ⚠️ 无法获取特征重要性信息")

        # 7. 计算业务指标
        accuracy = metrics['accuracy']
        precision = metrics['precision']

        print(f"\n💼 业务价值分析:")
        if accuracy > 0.6:
            print(f"   ✅ 模型准确率 {accuracy:.1%} 超过基线，具备实用价值")
        elif accuracy > 0.55:
            print(f"   ⚠️ 模型准确率 {accuracy:.1%} 略高于随机猜测，有改进空间")
        else:
            print(f"   ❌ 模型准确率 {accuracy:.1%} 低于基线，需要优化")

        if precision > 0.6:
            print(f"   ✅ 模型精准率 {precision:.1%} 表现优秀，预测可靠性高")
        elif precision > 0.5:
            print(f"   ⚠️ 模型精准率 {precision:.1%} 中等水平，可考虑调整")
        else:
            print(f"   ❌ 模型精准率 {precision:.1%} 偏低，存在误报风险")

        # 8. 保存模型和元数据
        print(f"\n💾 保存训练结果...")

        # 创建models目录
        os.makedirs('models', exist_ok=True)

        # 保存模型文件
        import joblib
        model_path = 'models/baseline_v1_mock.pkl'
        joblib.dump(trainer.model, model_path)
        logger.info(f"✅ 模型已保存至: {model_path}")

        # 保存训练元数据
        metadata = {
            'model_version': 'baseline_v1_mock',
            'training_date': start_time.isoformat(),
            'data_source': 'simulated',
            'total_matches': 500,
            'model_params': trainer.model_params,
            'metrics': metrics,
            'feature_importance': importance_df.to_dict('records') if importance_df is not None else None,
            'feature_columns': feature_columns,
            'rolling_windows': [3, 10],
            'data_info': {
                'train_samples': metrics['train_samples'],
                'test_samples': metrics['test_samples'],
                'total_features': len(trainer.feature_names_)
            }
        }

        metadata_path = 'models/baseline_v1_mock_metadata.json'
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        logger.info(f"✅ 元数据已保存至: {metadata_path}")

        # 9. 生成训练报告
        report = f"""
# 天网系统 - Baseline 模型训练报告（模拟数据）

## 训练概要
- **训练时间**: {start_time}
- **模型版本**: baseline_v1_mock
- **数据源**: 模拟数据
- **训练时长**: {(datetime.now() - start_time).total_seconds():.1f}秒

## 模型性能
- **准确率 (Accuracy)**: {accuracy:.2%}
- **精准率 (Precision)**: {precision:.2%}
- **训练样本数**: {metrics['train_samples']:,}
- **测试样本数**: {metrics['test_samples']:,}

## 关键致胜因子 (Top 5)
"""

        if importance_df is not None and not importance_df.empty:
            for i, row in importance_df.head(5).iterrows():
                report += f"{i+1}. {row['feature']}: {row['importance']*100:.2f}%\n"

        report_path = 'models/training_report_mock.md'
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
        logger.info(f"✅ 训练报告已保存至: {report_path}")

        print(f"\n📁 训练结果已保存:")
        print(f"   💾 模型文件: {model_path}")
        print(f"   📄 元数据文件: {metadata_path}")
        print(f"   📝 训练报告: {report_path}")

        print("="*80)
        print("🎉 天网系统 Baseline 模型训练任务完成!")
        print("🚀 模型已准备就绪，可用于生产预测")
        print("📝 注意：此模型使用模拟数据训练，真实场景性能可能有所不同")
        print("="*80)

    except Exception as e:
        logger.error(f"❌ 训练失败: {str(e)}", exc_info=True)
        print(f"\n❌ 训练过程中发生错误:")
        print(f"   错误类型: {type(e).__name__}")
        print(f"   错误信息: {str(e)}")
        print("\n🔧 请检查:")
        print("   1. 依赖包是否正确安装")
        print("   2. 特征工程逻辑是否正确")
        print("   3. 数据格式是否符合要求")
        return 1

    return 0


if __name__ == "__main__":
    # 检查Python版本
    if sys.version_info < (3, 8):
        print("❌ 需要Python 3.8或更高版本")
        sys.exit(1)

    # 运行训练
    exit_code = asyncio.run(main())
    sys.exit(exit_code)