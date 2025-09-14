#!/usr/bin/env python3
"""
预测结果回填脚本

功能：
1. 扫描已完成的比赛，获取实际结果
2. 更新predictions表中的actual_result、is_correct和verified_at字段
3. 计算模型准确率趋势（过去N场的移动平均）
4. 生成准确率报告
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import click
from sqlalchemy import and_, desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.logging import get_logger  # noqa: E402
from src.database.connection import get_async_session  # noqa: E402
from src.database.models.match import Match, MatchStatus  # noqa: E402
from src.database.models.predictions import Predictions  # noqa: E402

logger = get_logger(__name__)


class PredictionResultUpdater:
    """预测结果更新器"""

    def __init__(self):
        self.session: Optional[AsyncSession] = None

    async def __aenter__(self):
        """异步上下文管理器入口"""
        self.session = get_async_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self.session:
            await self.session.close()

    def _calculate_match_result(self, home_score: int, away_score: int) -> str:
        """
        根据比分计算比赛结果

        Args:
            home_score: 主队比分
            away_score: 客队比分

        Returns:
            str: 比赛结果 ('home_win', 'draw', 'away_win')
        """
        if home_score > away_score:
            return "home_win"
        elif home_score < away_score:
            return "away_win"
        else:
            return "draw"

    def _is_prediction_correct(self, predicted_result: str, actual_result: str) -> bool:
        """
        判断预测是否正确

        Args:
            predicted_result: 预测结果
            actual_result: 实际结果

        Returns:
            bool: 预测是否正确
        """
        return predicted_result == actual_result

    async def get_finished_matches_without_feedback(
        self, limit: int = 100
    ) -> List[Tuple]:
        """
        获取已完成但未回填预测结果的比赛

        Args:
            limit: 获取数量限制

        Returns:
            List[Tuple]: 比赛和预测数据的元组列表
        """
        if not self.session:
            raise RuntimeError("Session not initialized")

        logger.info(f"获取最多{limit}场已完成但未回填结果的比赛")

        # 查询已完成的比赛，且存在未验证的预测
        stmt = (
            select(Match, Predictions)
            .join(Predictions, Match.id == Predictions.match_id)
            .where(
                and_(
                    Match.match_status == MatchStatus.FINISHED,
                    Match.home_score.isnot(None),
                    Match.away_score.isnot(None),
                    Predictions.verified_at.is_(None),  # 未验证的预测
                )
            )
            .order_by(desc(Match.match_time))
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        matches_and_predictions = result.all()

        logger.info(f"找到{len(matches_and_predictions)}场需要更新的比赛预测")
        return list(matches_and_predictions)  # type: ignore[arg-type]

    async def update_prediction_result(
        self, prediction_id: int, actual_result: str, is_correct: bool
    ) -> bool:
        """
        更新单个预测的结果

        Args:
            prediction_id: 预测ID
            actual_result: 实际结果
            is_correct: 预测是否正确

        Returns:
            bool: 更新是否成功
        """
        if not self.session:
            raise RuntimeError("Session not initialized")

        try:
            stmt = (
                update(Predictions)
                .where(Predictions.id == prediction_id)
                .values(
                    actual_result=actual_result,
                    is_correct=is_correct,
                    verified_at=datetime.utcnow(),
                )
            )

            result = await self.session.execute(stmt)
            await self.session.commit()

            if result.rowcount > 0:
                logger.debug(
                    f"成功更新预测 {prediction_id}: {actual_result}, 正确={is_correct}"
                )
                return True
            else:
                logger.warning(f"未找到预测 {prediction_id} 或更新失败")
                return False

        except Exception as e:
            logger.error(f"更新预测 {prediction_id} 失败: {e}")
            await self.session.rollback()
            return False

    async def batch_update_predictions(self) -> Dict[str, int]:
        """
        批量更新预测结果

        Returns:
            Dict[str, int]: 更新统计信息
        """
        stats = {
            "total_processed": 0,
            "successful_updates": 0,
            "failed_updates": 0,
            "correct_predictions": 0,
            "incorrect_predictions": 0,
        }

        matches_and_predictions = await self.get_finished_matches_without_feedback()

        for match, prediction in matches_and_predictions:
            stats["total_processed"] += 1

            # 计算实际结果
            actual_result = self._calculate_match_result(
                match.home_score, match.away_score
            )

            # 判断预测是否正确
            predicted_result_value = prediction.predicted_result.value
            is_correct = self._is_prediction_correct(
                predicted_result_value, actual_result
            )

            # 更新统计
            if is_correct:
                stats["correct_predictions"] += 1
            else:
                stats["incorrect_predictions"] += 1

            # 更新数据库
            success = await self.update_prediction_result(
                prediction.id, actual_result, is_correct
            )

            if success:
                stats["successful_updates"] += 1
            else:
                stats["failed_updates"] += 1

            logger.info(
                f"比赛 {match.id} ({match.match_name}): "
                f"预测={predicted_result_value}, 实际={actual_result}, "
                f"正确={is_correct}"
            )

        return stats

    async def calculate_model_accuracy_trends(
        self, days_back: int = 30, window_size: int = 10
    ) -> Dict[str, List[Dict]]:
        """
        计算模型准确率趋势

        Args:
            days_back: 回看天数
            window_size: 移动平均窗口大小

        Returns:
            Dict[str, List[Dict]]: 各模型的准确率趋势数据
        """
        if not self.session:
            raise RuntimeError("Session not initialized")

        logger.info(f"计算过去{days_back}天的模型准确率趋势，移动窗口={window_size}")

        # 获取指定时间范围内的已验证预测
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)

        stmt = (
            select(Predictions)
            .where(
                and_(
                    Predictions.verified_at >= cutoff_date,
                    Predictions.verified_at.isnot(None),
                )
            )
            .order_by(Predictions.verified_at.desc())
        )

        result = await self.session.execute(stmt)
        predictions = result.scalars().all()

        # 按模型分组
        model_predictions: Dict[str, List[Any]] = {}
        for pred in predictions:
            model_key = f"{pred.model_name}_{pred.model_version}"
            if model_key not in model_predictions:
                model_predictions[model_key] = []
            model_predictions[model_key].append(pred)

        # 计算每个模型的移动平均准确率
        model_trends = {}

        for model_key, preds in model_predictions.items():
            if len(preds) < window_size:
                continue

            trends = []

            # 对预测按时间排序
            preds.sort(key=lambda x: x.verified_at)

            # 计算移动窗口准确率
            for i in range(window_size - 1, len(preds)):
                window_preds = preds[i - window_size + 1 : i + 1]
                correct_count = sum(1 for p in window_preds if p.is_correct)
                accuracy = correct_count / window_size

                trends.append(
                    {
                        "date": window_preds[-1].verified_at.isoformat(),
                        "accuracy": round(accuracy, 4),
                        "total_predictions": window_size,
                        "correct_predictions": correct_count,
                        "sample_size": len(window_preds),
                    }
                )

            model_trends[model_key] = trends

        logger.info(f"计算了{len(model_trends)}个模型的准确率趋势")
        return model_trends

    async def generate_accuracy_report(self, days_back: int = 30) -> Dict:
        """
        生成准确率报告

        Args:
            days_back: 回看天数

        Returns:
            Dict: 准确率报告数据
        """
        if not self.session:
            raise RuntimeError("Session not initialized")

        logger.info(f"生成过去{days_back}天的准确率报告")

        cutoff_date = datetime.utcnow() - timedelta(days=days_back)

        # 总体统计
        stmt = select(
            func.count().label("total_predictions"),
            func.sum(func.cast(Predictions.is_correct, func.Integer)).label(  # type: ignore[arg-type]
                "correct_predictions"
            ),
        ).where(
            and_(
                Predictions.verified_at >= cutoff_date,
                Predictions.verified_at.isnot(None),
            )
        )

        result = await self.session.execute(stmt)
        overall_stats = result.first()

        overall_accuracy = 0.0
        if overall_stats.total_predictions > 0:
            overall_accuracy = (
                overall_stats.correct_predictions / overall_stats.total_predictions
            )

        # 按模型统计
        from sqlalchemy.sql import Select

        model_stmt: Select = (
            select(  # type: ignore[assignment]
                Predictions.model_name,
                Predictions.model_version,
                func.count().label("total_predictions"),
                func.sum(func.cast(Predictions.is_correct, func.Integer)).label(  # type: ignore[arg-type]
                    "correct_predictions"
                ),
            )
            .where(
                and_(
                    Predictions.verified_at >= cutoff_date,
                    Predictions.verified_at.isnot(None),
                )
            )
            .group_by(Predictions.model_name, Predictions.model_version)
            .order_by(desc(func.count()))
        )

        result = await self.session.execute(model_stmt)
        model_stats = result.all()

        model_accuracies = []
        for stat in model_stats:
            accuracy = (
                stat.correct_predictions / stat.total_predictions
                if stat.total_predictions > 0
                else 0
            )
            model_accuracies.append(
                {
                    "model_name": stat.model_name,
                    "model_version": stat.model_version,
                    "total_predictions": stat.total_predictions,
                    "correct_predictions": stat.correct_predictions,
                    "accuracy": round(accuracy, 4),
                }
            )

        report = {
            "report_period": {
                "start_date": cutoff_date.isoformat(),
                "end_date": datetime.utcnow().isoformat(),
                "days": days_back,
            },
            "overall_statistics": {
                "total_predictions": overall_stats.total_predictions,
                "correct_predictions": overall_stats.correct_predictions,
                "accuracy": round(overall_accuracy, 4),
            },
            "model_statistics": model_accuracies,
            "generated_at": datetime.utcnow().isoformat(),
        }

        return report


@click.command()
@click.option("--update", is_flag=True, help="更新预测结果")
@click.option("--report", is_flag=True, help="生成准确率报告")
@click.option("--trends", is_flag=True, help="计算准确率趋势")
@click.option("--days", default=30, help="回看天数")
@click.option("--window", default=10, help="移动平均窗口大小")
@click.option("--limit", default=100, help="单次处理限制")
@click.option("--verbose", is_flag=True, help="详细输出")
def main(
    update: bool,
    report: bool,
    trends: bool,
    days: int,
    window: int,
    limit: int,
    verbose: bool,
):
    """预测结果反馈脚本主入口"""

    # 配置日志级别
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    async def run():
        async with PredictionResultUpdater() as updater:
            # 更新预测结果
            if update:
                click.echo("🔄 开始更新预测结果...")
                stats = await updater.batch_update_predictions()

                click.echo("\n📊 更新统计:")
                click.echo(f"  总处理数: {stats['total_processed']}")
                click.echo(f"  成功更新: {stats['successful_updates']}")
                click.echo(f"  更新失败: {stats['failed_updates']}")
                click.echo(f"  正确预测: {stats['correct_predictions']}")
                click.echo(f"  错误预测: {stats['incorrect_predictions']}")

                if stats["total_processed"] > 0:
                    accuracy = stats["correct_predictions"] / stats["total_processed"]
                    click.echo(f"  准确率: {accuracy:.2%}")

            # 生成报告
            if report:
                click.echo(f"\n📈 生成过去{days}天准确率报告...")
                report_data = await updater.generate_accuracy_report(days)

                click.echo("\n🎯 整体统计:")
                overall = report_data["overall_statistics"]
                click.echo(f"  总预测数: {overall['total_predictions']}")
                click.echo(f"  正确预测: {overall['correct_predictions']}")
                click.echo(f"  整体准确率: {overall['accuracy']:.2%}")

                click.echo("\n🤖 模型统计:")
                for model in report_data["model_statistics"]:
                    click.echo(
                        f"  {model['model_name']} v{model['model_version']}: "
                        f"{model['accuracy']:.2%} ({model['correct_predictions']}/{model['total_predictions']})"
                    )

            # 计算趋势
            if trends:
                click.echo(f"\n📊 计算过去{days}天准确率趋势（窗口大小: {window}）...")
                trends_data = await updater.calculate_model_accuracy_trends(
                    days, window
                )

                for model_key, trend_points in trends_data.items():
                    click.echo(f"\n📈 {model_key} 趋势:")
                    if trend_points:
                        latest = trend_points[-1]
                        click.echo(f"  最新准确率: {latest['accuracy']:.2%}")
                        click.echo(f"  趋势点数: {len(trend_points)}")

                        # 简单趋势分析
                        if len(trend_points) >= 2:
                            recent_avg = sum(
                                p["accuracy"] for p in trend_points[-3:]
                            ) / min(3, len(trend_points))
                            early_avg = sum(
                                p["accuracy"] for p in trend_points[:3]
                            ) / min(3, len(trend_points))

                            if recent_avg > early_avg:
                                trend_desc = "📈 上升"
                            elif recent_avg < early_avg:
                                trend_desc = "📉 下降"
                            else:
                                trend_desc = "➡️ 稳定"

                            click.echo(f"  趋势: {trend_desc}")

            if not any([update, report, trends]):
                click.echo("请指定至少一个操作选项 (--update, --report, --trends)")
                click.echo("使用 --help 查看详细帮助")

    # 运行异步函数
    asyncio.run(run())


if __name__ == "__main__":
    main()
