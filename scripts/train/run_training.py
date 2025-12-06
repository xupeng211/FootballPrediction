#!/usr/bin/env python3
"""
模型训练脚本 (Model Training Script)

调用ML Pipeline训练流程，训练XGBoost模型并保存到模型注册表。

作者: ML Engineer (P2-5)
创建时间: 2025-12-06
版本: 1.0.0
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.pipeline.flows.train_flow import train_flow, quick_train_flow
from src.pipeline.config import PipelineConfig
from src.database.async_manager import get_db_session
from src.database.models import Match
from sqlalchemy import select, and_, or_
import pandas as pd

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)8s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(f"/tmp/training_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.log")
    ]
)
logger = logging.getLogger(__name__)


class TrainingRunner:
    """训练运行器"""

    def __init__(self):
        self.config = PipelineConfig()
        self.config.debug_mode = False
        self.config.use_mlflow = True

    async def get_available_match_ids(self, limit: Optional[int] = None) -> list[int]:
        """
        获取可用的比赛ID

        Args:
            limit: 限制返回的比赛数量

        Returns:
            比赛ID列表
        """
        logger.info("📊 获取可用比赛ID...")

        async with get_db_session() as session:
            # 查询已完成的比赛，包含统计字段
            conditions = [
                Match.status.in_(["finished", "completed"]),
                Match.home_score.isnot(None),
                Match.away_score.isnot(None),
                # 确保有所需的统计字段
                Match.home_xg.isnot(None),
                Match.away_xg.isnot(None),
                Match.home_possession.isnot(None),
                Match.away_possession.isnot(None),
            ]

            query = select(Match.id).where(and_(*conditions)).order_by(Match.match_date.desc())

            if limit:
                query = query.limit(limit)

            result = await session.execute(query)
            match_ids = [row[0] for row in result.fetchall()]

            logger.info(f"   找到 {len(match_ids)} 场符合条件的比赛")
            return match_ids

    async def run_full_training(
        self,
        season: str = "2023-2024",
        league_id: Optional[str] = None,
        limit: Optional[int] = 5000,
        algorithm: str = "xgboost"
    ) -> dict:
        """
        运行完整训练流程

        Args:
            season: 赛季
            league_id: 联赛ID
            limit: 训练数据限制
            algorithm: 训练算法

        Returns:
            训练结果
        """
        logger.info("🚀 开始完整训练流程")
        logger.info(f"   赛季: {season}")
        logger.info(f"   算法: {algorithm}")
        logger.info(f"   数据限制: {limit if limit else '无限制'}")

        try:
            # 获取比赛ID
            match_ids = await self.get_available_match_ids(limit)

            if not match_ids:
                raise ValueError("没有找到可用的训练数据")

            logger.info(f"   使用 {len(match_ids)} 场比赛进行训练")

            # 构建模型名称
            model_name = f"football_prediction_v1_{algorithm}_{season}_{len(match_ids)}matches"

            # 运行训练流程
            result = train_flow(
                season=season,
                league_id=league_id,
                match_ids=match_ids,
                model_name=model_name,
                algorithm=algorithm,
                config=self.config
            )

            return result

        except Exception as e:
            logger.error(f"❌ 完整训练流程失败: {e}")
            raise

    async def run_quick_training(
        self,
        limit: int = 1000,
        algorithm: str = "xgboost"
    ) -> dict:
        """
        运行快速训练流程（用于开发测试）

        Args:
            limit: 训练数据限制
            algorithm: 训练算法

        Returns:
            训练结果
        """
        logger.info("⚡ 开始快速训练流程")
        logger.info(f"   算法: {algorithm}")
        logger.info(f"   数据限制: {limit}")

        try:
            # 获取比赛ID
            match_ids = await self.get_available_match_ids(limit)

            if not match_ids:
                raise ValueError("没有找到可用的训练数据")

            logger.info(f"   使用 {len(match_ids)} 场比赛进行训练")

            # 构建模型名称
            model_name = f"quick_model_{algorithm}_{len(match_ids)}matches"

            # 运行快速训练流程
            result = quick_train_flow(
                match_ids=match_ids,
                algorithm=algorithm,
                model_name=model_name
            )

            return result

        except Exception as e:
            logger.error(f"❌ 快速训练流程失败: {e}")
            raise

    def print_training_result(self, result: dict):
        """
        打印训练结果

        Args:
            result: 训练结果
        """
        logger.info("\n" + "="*60)
        logger.info("📊 训练结果报告")
        logger.info("="*60)

        if result["status"] == "success":
            logger.info(f"✅ 训练成功")
            logger.info(f"   模型名称: {result['model_name']}")
            logger.info(f"   算法: {result['algorithm']}")
            logger.info(f"   赛季: {result['season']}")
            logger.info(f"   训练数据: {result['match_count']} 场比赛")
            logger.info(f"   特征数量: {result['feature_count']} 个")
            logger.info(f"   模型路径: {result['model_path']}")

            # 打印评估指标
            metrics = result.get("metrics", {})
            if metrics:
                logger.info("\n📈 评估指标:")
                for metric_name, metric_value in metrics.items():
                    if isinstance(metric_value, float):
                        logger.info(f"   {metric_name}: {metric_value:.4f}")
                    else:
                        logger.info(f"   {metric_name}: {metric_value}")

            # 打印训练记录
            training_record = result.get("training_record", {})
            if training_record:
                logger.info("\n🎯 训练记录:")
                for key, value in training_record.items():
                    logger.info(f"   {key}: {value}")

        else:
            logger.error(f"❌ 训练失败")
            logger.error(f"   错误: {result.get('error', '未知错误')}")
            logger.error(f"   模型名称: {result.get('model_name', '未知')}")

        logger.info("="*60)


async def main():
    """主函数"""
    print("🤖 XGBoost模型训练开始")
    print("="*60)

    runner = TrainingRunner()

    try:
        # 解析命令行参数
        import argparse
        parser = argparse.ArgumentParser(description="足球预测模型训练")
        parser.add_argument("--mode", choices=["quick", "full"], default="quick", help="训练模式")
        parser.add_argument("--algorithm", default="xgboost", help="训练算法")
        parser.add_argument("--limit", type=int, default=1000, help="训练数据限制")
        parser.add_argument("--season", default="2023-2024", help="赛季")
        parser.add_argument("--league-id", help="联赛ID")

        args = parser.parse_args()

        if args.mode == "quick":
            # 快速训练模式
            result = await runner.run_quick_training(
                limit=args.limit,
                algorithm=args.algorithm
            )
        else:
            # 完整训练模式
            result = await runner.run_full_training(
                season=args.season,
                league_id=args.league_id,
                limit=args.limit,
                algorithm=args.algorithm
            )

        # 打印结果
        runner.print_training_result(result)

        # 返回适当的退出码
        if result["status"] == "success":
            print("\n✅ 模型训练完成!")
            return 0
        else:
            print("\n❌ 模型训练失败!")
            return 1

    except Exception as e:
        logger.error(f"❌ 训练脚本执行失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)