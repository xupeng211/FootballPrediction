"""
核心回测引擎 (Backtest Engine)

负责执行历史数据回测，管理策略执行和结果统计。

作者: Backtesting Engineer (P2-4)
创建时间: 2025-12-06
版本: 1.0.0
"""

import asyncio
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import dict, list, Optional, Any, tuple

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.async_manager import get_db_session
from src.database.models import Match, Team

from .models import (
    BacktestConfig,
    BacktestResult,
    BetResult,
    BetDecision,
    BetOutcome,
    BetType,
    StrategyProtocol,
)
from .portfolio import Portfolio
from .strategy import BaseStrategy

logger = logging.getLogger(__name__)


class BacktestEngine:
    """
    回测引擎

    负责执行历史数据回测，管理策略执行和结果统计。
    """

    def __init__(self, config: BacktestConfig):
        """
        初始化回测引擎

        Args:
            config: 回测配置
        """
        self.config = config
        self.portfolio = Portfolio(config)
        self.strategy: Optional[BaseStrategy] = None

        # 结果统计
        self.result = BacktestResult(config=config)
        self.progress_callback: Optional[callable] = None

        logger.info(
            f"BacktestEngine initialized with initial balance: {config.initial_balance}"
        )

    def set_strategy(self, strategy: StrategyProtocol) -> None:
        """
        设置回测策略

        Args:
            strategy: 策略实例
        """
        self.strategy = strategy
        logger.info(
            f"Strategy set: {strategy.name if hasattr(strategy, 'name') else typing.Type(strategy).__name__}"
        )

    def set_progress_callback(self, callback: callable) -> None:
        """
        设置进度回调函数

        Args:
            callback: 进度回调函数，接收 (current, total, message) 参数
        """
        self.progress_callback = callback

    async def run_backtest(
        self,
        start_date: datetime,
        end_date: datetime,
        league_ids: Optional[list[int]] = None,
    ) -> BacktestResult:
        """
        执行回测

        Args:
            start_date: 开始日期
            end_date: 结束日期
            league_ids: 联赛ID列表（可选）

        Returns:
            回测结果
        """
        if not self.strategy:
            raise ValueError("Strategy must be set before running backtest")

        logger.info(f"Starting backtest from {start_date.date()} to {end_date.date()}")

        # 初始化结果
        self.result = BacktestResult(config=self.config)
        self.result.initial_balance = self.config.initial_balance
        self.result.final_balance = self.config.initial_balance
        self.result.total_matches = 0

        try:
            # 获取历史比赛数据
            matches = await self._get_historical_matches(
                start_date, end_date, league_ids
            )

            if not matches:
                logger.warning("No matches found for the specified period")
                return self.result

            self.result.total_matches = len(matches)
            logger.info(f"Found {len(matches)} matches for backtesting")

            # 执行回测
            await self._execute_backtest_loop(matches)

            # 计算最终统计
            self._finalize_results()

            logger.info(
                f"Backtest completed. Final balance: {self.result.final_balance}, ROI: {self.result.roi:.2f}%"
            )

        except Exception as e:
            logger.error(f"Backtest failed: {e}")
            raise

        return self.result

    async def _get_historical_matches(
        self,
        start_date: datetime,
        end_date: datetime,
        league_ids: Optional[list[int]] = None,
    ) -> list[dict[str, Any]]:
        """
        获取历史比赛数据

        Args:
            start_date: 开始日期
            end_date: 结束日期
            league_ids: 联赛ID列表

        Returns:
            比赛数据列表
        """
        matches = []

        async with get_db_session() as session:
            # 构建查询条件
            conditions = [
                and_(
                    Match.match_date >= start_date,
                    Match.match_date <= end_date,
                    Match.status.in_(["finished", "completed"]),  # 只获取已完成的比赛
                )
            ]

            if league_ids:
                conditions.append(Match.league_id.in_(league_ids))

            # 查询比赛
            query = select(Match).where(and_(*conditions)).order_by(Match.match_date)

            result = await session.execute(query)
            db_matches = result.scalars().all()

            logger.info(f"Found {len(db_matches)} matches in database")

            # 转换为字典格式
            for match in db_matches:
                try:
                    # 获取球队信息
                    home_team = await session.get(Team, match.home_team_id)
                    away_team = await session.get(Team, match.away_team_id)

                    match_data = {
                        "id": match.id,
                        "home_team_id": match.home_team_id,
                        "away_team_id": match.away_team_id,
                        "home_team_name": home_team.name if home_team else "Unknown",
                        "away_team_name": away_team.name if away_team else "Unknown",
                        "home_score": match.home_score,
                        "away_score": match.away_score,
                        "match_date": match.match_date,
                        "status": match.status,
                        "league_id": match.league_id,
                        "season": match.season,
                        # 包含新的统计字段
                        "home_xg": getattr(match, "home_xg", None),
                        "away_xg": getattr(match, "away_xg", None),
                        "home_possession": getattr(match, "home_possession", None),
                        "away_possession": getattr(match, "away_possession", None),
                        "home_shots": getattr(match, "home_shots", None),
                        "away_shots": getattr(match, "away_shots", None),
                        "home_shots_on_target": getattr(
                            match, "home_shots_on_target", None
                        ),
                        "away_shots_on_target": getattr(
                            match, "away_shots_on_target", None
                        ),
                    }

                    # 添加模拟的模型预测数据
                    match_data.update(self._generate_mock_predictions(match_data))

                    # 添加模拟的赔率数据
                    odds_data = self._generate_mock_odds(match_data)
                    match_data["odds"] = odds_data

                    matches.append(match_data)

                except Exception as e:
                    logger.error(f"Error processing match {match.id}: {e}")
                    continue

        return matches

    def _generate_mock_predictions(self, match_data: dict[str, Any]) -> dict[str, Any]:
        """
        生成模拟的模型预测数据

        在实际应用中，这里应该调用真实的预测模型。

        Args:
            match_data: 比赛数据

        Returns:
            预测数据
        """
        import random

        # 基于历史数据生成合理的预测概率
        home_prob = random.uniform(0.25, 0.55)
        away_prob = random.uniform(0.20, 0.45)
        draw_prob = 1.0 - home_prob - away_prob

        return {
            "home_win_prob": round(home_prob, 3),
            "draw_prob": round(draw_prob, 3),
            "away_win_prob": round(away_prob, 3),
            "model_confidence": round(random.uniform(0.6, 0.9), 3),
        }

    def _generate_mock_odds(self, match_data: dict[str, Any]) -> dict[str, Decimal]:
        """
        生成模拟的赔率数据

        Args:
            match_data: 比赛数据

        Returns:
            赔率数据
        """
        import random

        # 基于概率生成合理的赔率（包含博彩公司的利润空间）
        base_margin = 1.05  # 5%的博彩公司利润空间

        home_prob = match_data.get("home_win_prob", 0.33)
        draw_prob = match_data.get("draw_prob", 0.34)
        away_prob = match_data.get("away_win_prob", 0.33)

        # 计算赔率（博彩公司赔率 = 1 / (概率 * 利润空间)）
        home_odds = max(
            Decimal("1.1"), Decimal(str(1 / (home_prob * base_margin)))
        ).quantize(Decimal("0.01"))
        draw_odds = max(
            Decimal("1.1"), Decimal(str(1 / (draw_prob * base_margin)))
        ).quantize(Decimal("0.01"))
        away_odds = max(
            Decimal("1.1"), Decimal(str(1 / (away_prob * base_margin)))
        ).quantize(Decimal("0.01"))

        return {
            "home": home_odds,
            "draw": draw_odds,
            "away": away_odds,
            "home_odds": home_odds,
            "draw_odds": draw_odds,
            "away_odds": away_odds,
        }

    async def _execute_backtest_loop(self, matches: list[dict[str, Any]]) -> None:
        """
        执行回测主循环

        Args:
            matches: 比赛数据列表
        """
        total_matches = len(matches)

        for i, match in enumerate(matches):
            try:
                # 报告进度
                if self.progress_callback:
                    self.progress_callback(
                        i + 1, total_matches, f"Processing match {match['id']}"
                    )

                # 执行策略决策
                decision = await self.strategy.decide(match, match["odds"])

                # 检查是否可以下注
                if self.portfolio.can_place_bet(decision, match["match_date"]):
                    self.portfolio.place_bet(decision)
                    self.result.total_bets += 1

                    if decision.bet_type != BetType.SKIP:
                        logger.debug(
                            f"Bet placed on match {match['id']}: {decision.bet_type.value}"
                        )
                    else:
                        self.result.skipped_bets += 1
                else:
                    self.result.skipped_bets += 1

                # 模拟比赛结算（因为历史数据，我们可以立即结算）
                await self._settle_match(match)

                # 更新余额历史
                self.result.balance_history.append(self.portfolio.current_balance)

            except Exception as e:
                logger.error(f"Error processing match {match['id']}: {e}")
                continue

    async def _settle_match(self, match: dict[str, Any]) -> None:
        """
        结算比赛

        Args:
            match: 比赛数据
        """
        match_id = match["id"]
        home_score = match.get("home_score", 0) or 0
        away_score = match.get("away_score", 0) or 0

        # 确定比赛结果
        if home_score > away_score:
            outcome = BetOutcome.HOME_WIN
        elif away_score > home_score:
            outcome = BetOutcome.AWAY_WIN
        else:
            outcome = BetOutcome.DRAW

        # 结算下注
        result = self.portfolio.settle_bet(match_id, outcome, match["match_date"])
        if result:
            self.result.bet_results.append(result)

            if result.profit_loss > 0:
                self.result.winning_bets += 1
            elif result.profit_loss < 0:
                self.result.losing_bets += 1

    def _finalize_results(self) -> None:
        """
        完成回测结果统计
        """
        # 获取最终资金信息
        stats = self.portfolio.get_statistics()

        self.result.final_balance = stats["current_balance"]
        self.result.max_balance = stats["max_balance"]
        self.result.min_balance = stats["min_balance"]
        self.result.total_staked = stats["total_staked"]
        self.result.winning_bets = stats["total_wins"]
        self.result.losing_bets = stats["total_losses"]
        self.result.skipped_bets = stats["total_skips"]

        # 转移下注记录
        self.result.bet_results = self.portfolio.bet_history.copy()

        # 计算性能指标
        self.result.calculate_metrics()

        logger.info(f"Backtest finalized: {self.result.get_summary()}")

    def get_progress_info(self) -> dict[str, Any]:
        """
        获取回测进度信息

        Returns:
            进度信息字典
        """
        stats = self.portfolio.get_statistics()
        return {
            "current_balance": stats["current_balance"],
            "total_bets": stats["total_bets"],
            "win_rate": stats["win_rate"],
            "roi_percent": stats["roi_percent"],
            "max_drawdown": stats["max_drawdown"],
        }


# 回测执行工具函数
async def run_simple_backtest(
    strategy_name: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    initial_balance: Decimal = Decimal("10000.00"),
    **strategy_kwargs,
) -> BacktestResult:
    """
    运行简单的回测

    Args:
        strategy_name: 策略名称
        start_date: 开始日期（默认30天前）
        end_date: 结束日期（默认今天）
        initial_balance: 初始资金
        **strategy_kwargs: 策略参数

    Returns:
        回测结果
    """
    from .strategy import StrategyFactory

    # 设置默认日期范围
    if end_date is None:
        end_date = datetime.now()
    if start_date is None:
        start_date = end_date - timedelta(days=30)

    # 创建配置
    config = BacktestConfig(initial_balance=initial_balance)

    # 创建引擎
    engine = BacktestEngine(config)

    # 创建策略
    strategy = StrategyFactory.create_strategy(strategy_name, **strategy_kwargs)
    engine.set_strategy(strategy)

    # 运行回测
    result = await engine.run_backtest(start_date, end_date)

    return result
