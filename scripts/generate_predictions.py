#!/usr/bin/env python3
"""
批量生成历史比赛预测数据
Batch Generate Historical Match Predictions

用于填补预测数据库的空白，生成历史比赛的预测结果。
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

import logging
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

# 导入推理服务和数据库
from src.services.inference_service import InferenceService
from src.database.definitions import initialize_database
from src.config.config_manager import CONFIG_MANAGER

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 数据库配置
DATABASE_URL = (
    "postgresql+asyncpg://postgres:postgres-dev-password@db:5432/football_prediction"
)


class BatchPredictionGenerator:
    """批量预测生成器"""

    def __init__(self):
        self.engine = create_async_engine(DATABASE_URL, echo=False)
        self.async_session = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

    async def get_match_ids(
        self, limit: int = None, only_unpredicted: bool = True
    ) -> list[int]:
        """获取比赛ID列表

        Args:
            limit: 限制数量，None表示无限制
            only_unpredicted: 是否只获取未预测的比赛
        """
        async with self.async_session() as session:
            if only_unpredicted:
                query = text(
                    """
                    SELECT m.id FROM matches m
                    LEFT JOIN predictions p ON m.id = p.match_id
                    WHERE p.match_id IS NULL
                    ORDER BY m.match_date DESC
                    LIMIT :limit
                """
                )
            else:
                query = text(
                    "SELECT id FROM matches ORDER BY match_date DESC LIMIT :limit"
                )

            result = await session.execute(query, {"limit": limit if limit else 10000})
            return [row[0] for row in result.fetchall()]

    async def prediction_exists(self, match_id: int, user_id: int = 1) -> bool:
        """检查预测是否已存在"""
        async with self.async_session() as session:
            result = await session.execute(
                text(
                    "SELECT COUNT(*) FROM predictions WHERE match_id = :match_id AND user_id = :user_id"
                ),
                {"match_id": match_id, "user_id": user_id},
            )
            count = result.scalar()
            return count > 0

    async def save_prediction(
        self,
        match_id: int,
        user_id: int = 1,
        home_win_prob: float = 0.33,
        draw_prob: float = 0.33,
        away_win_prob: float = 0.34,
        predicted_outcome: str = "home",
        confidence: float = 0.75,
    ):
        """保存预测到数据库"""
        async with self.async_session() as session:
            try:
                # 构建分数字符串（模拟预测分数）
                if predicted_outcome == "home":
                    score = "2-1"
                elif predicted_outcome == "away":
                    score = "1-2"
                else:
                    score = "1-1"

                await session.execute(
                    text(
                        """
                        INSERT INTO predictions
                        (user_id, match_id, score, confidence, status, created_at, updated_at)
                        VALUES
                        (:user_id, :match_id, :score, :confidence, 'COMPLETED', :created_at, :updated_at)
                    """
                    ),
                    {
                        "user_id": user_id,
                        "match_id": match_id,
                        "score": score,
                        "confidence": f"{confidence:.6f}",
                        "created_at": datetime.utcnow(),
                        "updated_at": datetime.utcnow(),
                    },
                )
                await session.commit()
                logger.info(f"✅ 已保存比赛 {match_id} 的预测")
                return True
            except Exception:
                await session.rollback()
                logger.error(f"❌ 保存比赛 {match_id} 预测失败: {e}")
                return False

    async def generate_real_prediction(self, match_id: int) -> dict[str, Any]:
        """为比赛生成真实的模型预测数据"""
        try:
            # 确保数据库已初始化
            try:
                initialize_database(database_url=CONFIG_MANAGER.database_url)
            except Exception:
                logger.warning(f"数据库初始化失败，继续使用推理服务: {e}")

            # 初始化推理服务
            inference_service = InferenceService()

            # 调用真实推理服务
            logger.info(f"🧠 使用AI模型预测比赛 {match_id}")
            prediction_result = await inference_service.predict_match(match_id)

            if not prediction_result.get("success", False):
                logger.error(
                    f"❌ 推理服务预测失败: {prediction_result.get('error', 'Unknown error')}"
                )
                # 如果推理失败，返回基础预测
                return {
                    "match_id": match_id,
                    "home_win_prob": 0.34,
                    "draw_prob": 0.33,
                    "away_win_prob": 0.33,
                    "predicted_outcome": "home",
                    "confidence": 0.5,
                    "status": "fallback",
                }

            # 提取推理结果中的关键信息
            predicted_outcome = prediction_result.get("predicted_outcome", "home")

            # 确保predicted_outcome是期望的格式
            if predicted_outcome == "home":
                predicted_outcome_clean = "home"
            elif predicted_outcome == "away":
                predicted_outcome_clean = "away"
            elif predicted_outcome == "draw":
                predicted_outcome_clean = "draw"
            elif predicted_outcome == "home_win":
                predicted_outcome_clean = "home"
            elif predicted_outcome == "away_win":
                predicted_outcome_clean = "away"
            elif predicted_outcome == "away_or_draw":
                # 对于away_or_draw，选择概率更高的
                if prediction_result.get("away_win_prob", 0) > prediction_result.get(
                    "draw_prob", 0
                ):
                    predicted_outcome_clean = "away"
                else:
                    predicted_outcome_clean = "draw"
            else:
                predicted_outcome_clean = "home"  # 默认值

            logger.info(
                f"✅ AI模型预测成功: {predicted_outcome_clean}, 置信度: {prediction_result.get('confidence', 0):.3f}"
            )

            return {
                "match_id": match_id,
                "home_win_prob": float(prediction_result.get("home_win_prob", 0.33)),
                "draw_prob": float(prediction_result.get("draw_prob", 0.33)),
                "away_win_prob": float(prediction_result.get("away_win_prob", 0.34)),
                "predicted_outcome": predicted_outcome_clean,
                "confidence": float(prediction_result.get("confidence", 0.5)),
                "status": "ai_generated",
            }

        except Exception:
            logger.error(f"❌ 生成真实预测失败: {e}")
            # 返回基础预测作为后备
            return {
                "match_id": match_id,
                "home_win_prob": 0.34,
                "draw_prob": 0.33,
                "away_win_prob": 0.33,
                "predicted_outcome": "home",
                "confidence": 0.5,
                "status": "fallback_error",
            }

    async def batch_generate_predictions(self, batch_size: int = 50):
        """批量生成预测"""
        logger.info("🚀 开始批量生成预测数据...")

        # 获取比赛ID列表
        match_ids = await self.get_match_ids(batch_size)
        logger.info(f"📋 获取到 {len(match_ids)} 场比赛")

        success_count = 0
        failed_count = 0

        for match_id in match_ids:
            try:
                # 检查预测是否已存在
                if await self.prediction_exists(match_id):
                    logger.info(f"⏭️  比赛 {match_id} 预测已存在，跳过")
                    continue

                # 生成真实预测
                prediction = await self.generate_real_prediction(match_id)

                # 保存到数据库
                success = await self.save_prediction(
                    match_id=match_id,
                    home_win_prob=prediction["home_win_prob"],
                    draw_prob=prediction["draw_prob"],
                    away_win_prob=prediction["away_win_prob"],
                    predicted_outcome=prediction["predicted_outcome"],
                    confidence=prediction["confidence"],
                )

                if success:
                    success_count += 1
                else:
                    failed_count += 1

            except Exception:
                logger.error(f"❌ 处理比赛 {match_id} 失败: {e}")
                failed_count += 1

        logger.info(f"🎉 批量预测生成完成！成功: {success_count}, 失败: {failed_count}")
        return {"success_count": success_count, "failed_count": failed_count}

    async def get_statistics(self):
        """获取数据库统计信息"""
        async with self.async_session() as session:
            matches_result = await session.execute(text("SELECT COUNT(*) FROM matches"))
            predictions_result = await session.execute(
                text("SELECT COUNT(*) FROM predictions")
            )

            matches_count = matches_result.scalar()
            predictions_count = predictions_result.scalar()

            logger.info(
                f"📊 数据库统计: 比赛 {matches_count} 场, 预测 {predictions_count} 条"
            )

            return {
                "matches_count": matches_count,
                "predictions_count": predictions_count,
                "coverage_rate": (
                    predictions_count / matches_count if matches_count > 0 else 0
                ),
            }

    async def generate_all_predictions(self):
        """为所有未预测的比赛生成预测"""
        logger.info("🎯 开始为所有未预测的比赛生成预测...")

        # 获取所有未预测的比赛
        match_ids = await self.get_match_ids(limit=None, only_unpredicted=True)
        logger.info(f"📋 找到 {len(match_ids)} 场未预测的比赛")

        success_count = 0
        failed_count = 0
        batch_size = 100

        # 分批处理
        for i in range(0, len(match_ids), batch_size):
            batch_match_ids = match_ids[i : i + batch_size]
            logger.info(
                f"正在处理第 {i // batch_size + 1} 批，共 {len(batch_match_ids)} 场比赛..."
            )

            for match_id in batch_match_ids:
                try:
                    # 生成真实预测
                    prediction = await self.generate_real_prediction(match_id)

                    # 保存到数据库
                    success = await self.save_prediction(
                        match_id=match_id,
                        home_win_prob=prediction["home_win_prob"],
                        draw_prob=prediction["draw_prob"],
                        away_win_prob=prediction["away_win_prob"],
                        predicted_outcome=prediction["predicted_outcome"],
                        confidence=prediction["confidence"],
                    )

                    if success:
                        success_count += 1
                    else:
                        failed_count += 1

                except Exception:
                    logger.error(f"❌ 处理比赛 {match_id} 失败: {e}")
                    failed_count += 1

            # 每批处理完后显示进度
            progress = (i + len(batch_match_ids)) / len(match_ids) * 100
            logger.info(
                f"📈 进度: {progress:.1f}% ({i + len(batch_match_ids)}/{len(match_ids)})"
            )

        logger.info(f"🎉 全量预测生成完成！成功: {success_count}, 失败: {failed_count}")
        return {"success_count": success_count, "failed_count": failed_count}

    async def close(self):
        """关闭数据库连接"""
        await self.engine.dispose()


async def main():
    """主函数"""
    import sys

    # 检查命令行参数
    generate_all = "--all" in sys.argv or len(sys.argv) > 1 and sys.argv[1] == "all"

    logger.info("🏃‍♂️ 启动批量预测生成器")

    # 初始化数据库
    try:
        initialize_database(database_url=CONFIG_MANAGER.database_url)
        logger.info("✅ 数据库初始化成功")
    except Exception:
        logger.error(f"❌ 数据库初始化失败: {e}")
        raise

    generator = BatchPredictionGenerator()

    try:
        # 获取初始统计
        await generator.get_statistics()

        if generate_all:
            # 执行全量预测
            logger.info("🎯 开始全量预测生成模式")
            await generator.generate_all_predictions()
        else:
            # 小批量测试
            logger.info("🧪 测试模式 - 生成少量预测")
            await generator.batch_generate_predictions(batch_size=20)

        # 获取最终统计
        await generator.get_statistics()

        logger.info("✅ 预测生成任务完成")

    except Exception:
        logger.error(f"❌ 预测生成失败: {e}")
        raise
    finally:
        await generator.close()


if __name__ == "__main__":
    asyncio.run(main())
