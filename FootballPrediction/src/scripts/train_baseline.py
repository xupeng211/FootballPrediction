#!/usr/bin/env python3
"""
天网系统 - Baseline 模型训练脚本

Phase 2.3: Training Pipeline - 实战训练

连接真实数据库，使用完整的ML管道进行第一次全量训练。
生成基线模型，评估性能，并分析特征重要性。

训练目标：
- 使用历史比赛数据训练预测模型
- 实现严格的时间序列切分（防数据泄露）
- 评估模型性能：Accuracy、Precision等关键指标
- 识别关键致胜因子（特征重要性）

特征工程策略：
- 进球能力：home_score, away_score的滚动统计
- 创造机会：home_expected_goals, away_expected_goals的滚动统计
- 控制力：home_possession, away_possession的滚动统计
- 时间窗口：3场和10场滚动平均，捕捉短期和长期趋势
"""

import asyncio
import logging
import pandas as pd
import sys
import os
import json
from pathlib import Path
from datetime import datetime

# Ensure src is in pythonpath
sys.path.append(os.getcwd())

from src.ml.data.loader import DataLoader
from src.ml.features.rolling import RollingAverageTransformer
from src.ml.training.trainer import ModelTrainer

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/training.log')
    ]
)
logger = logging.getLogger(__name__)

# 确保日志目录存在
os.makedirs('logs', exist_ok=True)


async def main():
    """主训练函数"""
    start_time = datetime.now()
    logger.info("🚀 启动天网系统 - Baseline 模型训练任务")
    logger.info(f"训练开始时间: {start_time}")

    try:
        # 1. 初始化数据加载器
        logger.info("📊 初始化数据加载器...")
        loader = DataLoader()

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
                group_by=['team_id'],  # 按球队分组计算
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
                'max_depth': 3,          # 树的深度
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
        print(f"🏆 天网系统 - Baseline 模型训练结果汇报")
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
        model_path = 'models/baseline_v1.pkl'
        joblib.dump(trainer.model, model_path)
        logger.info(f"✅ 模型已保存至: {model_path}")

        # 保存训练元数据
        metadata = {
            'model_version': 'baseline_v1',
            'training_date': start_time.isoformat(),
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

        metadata_path = 'models/baseline_v1_metadata.json'
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        logger.info(f"✅ 元数据已保存至: {metadata_path}")

        # 9. 生成训练报告
        report = f"""
# 天网系统 - Baseline 模型训练报告

## 训练概要
- **训练时间**: {start_time}
- **模型版本**: baseline_v1
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

        report_path = 'models/training_report.md'
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
        print("="*80)

    except Exception as e:
        logger.error(f"❌ 训练失败: {str(e)}", exc_info=True)
        print(f"\n❌ 训练过程中发生错误:")
        print(f"   错误类型: {type(e).__name__}")
        print(f"   错误信息: {str(e)}")
        print("\n🔧 请检查:")
        print("   1. 数据库连接是否正常")
        print("   2. 数据表是否有数据")
        print("   3. 特征列是否存在")
        print("   4. 依赖包是否正确安装")
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