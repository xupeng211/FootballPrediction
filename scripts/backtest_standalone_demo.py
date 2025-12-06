#!/usr/bin/env python3
"""
独立回测演示脚本 (Standalone Backtesting Demo)

独立演示回测系统功能，不依赖外部数据库。

作者: Backtesting Engineer (P2-4)
创建时间: 2025-12-06
版本: 1.0.0
"""

import asyncio
import logging
import random
import sys
import time
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import List, Dict, Any

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.backtesting.models import (
    BacktestConfig, BacktestResult, BetDecision, BetResult, BetOutcome, BetType
)
from src.backtesting.portfolio import Portfolio
from src.backtesting.strategy import SimpleValueStrategy, ConservativeStrategy, AggressiveStrategy

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)8s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


class MockMatchGenerator:
    """模拟比赛数据生成器"""

    @staticmethod
    def generate_matches(count: int = 100) -> List[Dict[str, Any]]:
        """生成模拟比赛数据"""
        matches = []
        start_date = datetime.now() - timedelta(days=count)

        for i in range(count):
            match_date = start_date + timedelta(days=i)

            # 生成随机结果
            result = random.random()
            if result < 0.45:  # 主队胜
                home_score = random.randint(2, 4)
                away_score = random.randint(0, 2)
                outcome = "home_win"
                home_prob = random.uniform(0.4, 0.6)
                away_prob = random.uniform(0.2, 0.3)
            elif result < 0.75:  # 客队胜
                home_score = random.randint(0, 2)
                away_score = random.randint(2, 4)
                outcome = "away_win"
                home_prob = random.uniform(0.2, 0.3)
                away_prob = random.uniform(0.4, 0.6)
            else:  # 平局
                home_score = away_score = random.randint(0, 2)
                outcome = "draw"
                home_prob = random.uniform(0.25, 0.35)
                away_prob = random.uniform(0.25, 0.35)

            draw_prob = 1.0 - home_prob - away_prob

            # 生成控球率
            home_possession = round(random.uniform(35, 65), 1)
            away_possession = round(100 - float(home_possession), 1)

            # 生成赔率（包含博彩公司利润）
            margin = 1.05  # 5%利润空间
            home_odds = max(Decimal("1.1"), Decimal(str(1 / (home_prob * margin)))).quantize(Decimal("0.01"))
            draw_odds = max(Decimal("1.1"), Decimal(str(1 / (draw_prob * margin)))).quantize(Decimal("0.01"))
            away_odds = max(Decimal("1.1"), Decimal(str(1 / (away_prob * margin)))).quantize(Decimal("0.01"))

            match = {
                "id": i + 1,
                "home_team_id": (i % 20) + 1,
                "away_team_id": (i % 20) + 21,
                "home_team_name": f"Team {(i % 20) + 1}",
                "away_team_name": f"Team {(i % 20) + 21}",
                "home_score": home_score,
                "away_score": away_score,
                "match_date": match_date,
                "status": "finished",
                "league_id": 1,
                "season": "2023-2024",
                "actual_outcome": outcome,
                "home_win_prob": round(home_prob, 3),
                "draw_prob": round(draw_prob, 3),
                "away_win_prob": round(away_prob, 3),
                "model_confidence": round(random.uniform(0.6, 0.9), 3),
                "home_xg": round(random.uniform(0.8, 3.2), 2),
                "away_xg": round(random.uniform(0.8, 3.2), 2),
                "home_possession": home_possession,
                "away_possession": away_possession,
                "home_shots": random.randint(5, 20),
                "away_shots": random.randint(5, 20),
                "home_shots_on_target": random.randint(2, 8),
                "away_shots_on_target": random.randint(2, 8),
                "odds": {
                    "home": home_odds,
                    "draw": draw_odds,
                    "away": away_odds,
                    "home_odds": home_odds,
                    "draw_odds": draw_odds,
                    "away_odds": away_odds
                }
            }

            matches.append(match)

        return matches


class StandaloneBacktestEngine:
    """独立回测引擎"""

    def __init__(self, config: BacktestConfig):
        self.config = config
        self.portfolio = Portfolio(config)

    async def run_backtest(self, matches: List[Dict[str, Any]], strategy) -> BacktestResult:
        """运行回测"""
        logger.info(f"开始回测 {len(matches)} 场比赛")

        result = BacktestResult(config=self.config)
        result.initial_balance = self.config.initial_balance
        result.total_matches = len(matches)

        start_time = time.time()

        for i, match in enumerate(matches):
            try:
                # 获取策略决策
                decision = await strategy.decide(match, match["odds"])

                # 检查是否可以下注
                if self.portfolio.can_place_bet(decision, match["match_date"]):
                    self.portfolio.place_bet(decision)
                    result.total_bets += 1

                    if decision.bet_type != BetType.SKIP:
                        logger.debug(f"第{i+1}场: 下注 {decision.bet_type.value}")
                    else:
                        result.skipped_bets += 1
                else:
                    result.skipped_bets += 1

                # 结算比赛
                actual_outcome = {
                    "home_win": BetOutcome.HOME_WIN,
                    "away_win": BetOutcome.AWAY_WIN,
                    "draw": BetOutcome.DRAW
                }[match["actual_outcome"]]

                bet_result = self.portfolio.settle_bet(
                    match["id"], actual_outcome, match["match_date"]
                )
                if bet_result:
                    result.bet_results.append(bet_result)

                    if bet_result.profit_loss > 0:
                        result.winning_bets += 1
                    elif bet_result.profit_loss < 0:
                        result.losing_bets += 1

                # 更新余额历史
                result.balance_history.append(self.portfolio.current_balance)

                # 进度报告
                if (i + 1) % 20 == 0:
                    logger.info(f"已处理 {i+1}/{len(matches)} 场比赛")

            except Exception as e:
                logger.error(f"处理第 {i+1} 场比赛失败: {e}")
                continue

        # 完成统计
        execution_time = time.time() - start_time
        stats = self.portfolio.get_statistics()

        result.final_balance = stats["current_balance"]
        result.max_balance = stats["max_balance"]
        result.min_balance = stats["min_balance"]
        result.total_staked = stats["total_staked"]
        result.winning_bets = stats["total_wins"]
        result.losing_bets = stats["total_losses"]
        result.skipped_bets = stats["total_skips"]

        # 转移下注记录
        result.bet_results = self.portfolio.bet_history.copy()

        # 计算性能指标
        result.calculate_metrics()

        logger.info(f"回测完成，耗时: {execution_time:.2f}秒")
        logger.info(f"最终资金: {result.final_balance}, ROI: {result.roi:.2f}%")

        return result


async def run_strategy_demo():
    """运行策略演示"""
    print("⚽ 足球预测系统回测演示 (独立版)")
    print("=" * 60)

    # 生成模拟数据
    logger.info("🎲 生成模拟比赛数据...")
    matches = MockMatchGenerator.generate_matches(100)
    logger.info(f"生成了 {len(matches)} 场比赛数据")

    # 配置回测参数
    config = BacktestConfig(
        initial_balance=Decimal("10000.00"),
        max_stake_pct=0.05,
        min_stake=Decimal("100.00"),
        max_stake=Decimal("500.00"),
        value_threshold=0.1,
        min_confidence=0.3,
        max_daily_bets=10
    )

    # 测试不同策略
    strategies = [
        ("简单价值策略", SimpleValueStrategy(value_threshold=0.1, min_confidence=0.3)),
        ("保守策略", ConservativeStrategy(value_threshold=0.15, min_confidence=0.5)),
        ("激进策略", AggressiveStrategy(value_threshold=0.05, min_confidence=0.2))
    ]

    results = {}

    for strategy_name, strategy in strategies:
        logger.info(f"\n🧪 测试策略: {strategy_name}")

        # 创建新的引擎实例
        engine = StandaloneBacktestEngine(config)

        try:
            # 运行回测
            result = await engine.run_backtest(matches, strategy)
            results[strategy_name] = result

            print(f"\n{strategy_name} 结果:")
            print(f"   总下注: {result.total_bets}")
            print(f"   胜场: {result.winning_bets}")
            print(f"   败场: {result.losing_bets}")
            print(f"   胜率: {result.win_rate:.2%}")
            print(f"   总盈亏: {result.total_profit_loss:+,.2f}")
            print(f"   投资回报率: {result.roi:+.2f}%")
            print(f"   最大连胜: {result.max_consecutive_wins}")
            print(f"   最大连败: {result.max_consecutive_losses}")

        except Exception as e:
            logger.error(f"❌ {strategy_name} 失败: {e}")
            print(f"❌ {strategy_name} 失败: {e}")

    # 策略对比
    print("\n" + "=" * 60)
    print("📊 策略对比总结")
    print("=" * 60)

    print(f"{'策略名称':<15} {'下注数':<8} {'胜率':<10} {'ROI':<12} {'最大连胜':<10}")
    print("-" * 65)

    best_strategy = None
    best_roi = float("-inf")

    for strategy_name, result in results.items():
        print(f"{strategy_name:<15} {result.total_bets:>6} {result.win_rate:>8.1%} "
              f"{result.roi:>10.2f}% {result.max_consecutive_wins:>8}")

        if result.roi > best_roi:
            best_roi = result.roi
            best_strategy = strategy_name

    if best_strategy:
        best_result = results[best_strategy]
        print(f"\n🏆 最佳策略: {best_strategy}")
        print(f"   投资回报率: {best_roi:+.2f}%")
        print(f"   总盈亏: {best_result.total_profit_loss:+,.2f}")

    # 详细分析最佳策略
    if best_strategy and best_result in results:
        best_result = results[best_strategy]

        print(f"\n🔍 {best_strategy} 详细分析:")
        print(f"   初始资金: {best_result.initial_balance:,.2f}")
        print(f"   最终资金: {best_result.final_balance:,.2f}")
        print(f"   最大资金: {best_result.max_balance:,.2f}")
        print(f"   最小资金: {best_result.min_balance:,.2f}")
        print(f"   总下注金额: {best_result.total_staked:,.2f}")
        print(f"   平均下注: {best_result.avg_stake:,.2f}")
        print(f"   夏普比率: {best_result.sharpe_ratio:.3f}")
        print(f"   盈亏波动率: {best_result.profit_volatility:.2f}")

        if len(best_result.bet_results) > 0:
            # 计算最近10场表现
            recent_bets = best_result.bet_results[-10:]
            recent_wins = sum(1 for bet in recent_bets if bet.profit_loss > 0)
            recent_profit = sum(bet.profit_loss for bet in recent_bets)

            print(f"\n📈 最近10场表现:")
            print(f"   胜场: {recent_wins}/{len(recent_bets)} ({recent_wins/len(recent_bets):.1%})")
            print(f"   盈亏: {recent_profit:+.2f}")

        # 风险指标
        max_drawdown = best_result.initial_balance - best_result.min_balance
        drawdown_pct = (max_drawdown / best_result.initial_balance * 100)

        print(f"\n⚠️ 风险指标:")
        print(f"   最大回撤: {max_drawdown:,.2f} ({drawdown_pct:.2f}%)")

        # 保存结果
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        summary_file = f"/tmp/backtest_standalone_{timestamp}.txt"

        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(f"回测系统独立演示报告\n")
            f.write(f"生成时间: {datetime.now()}\n")
            f.write(f"策略: {best_strategy}\n")
            f.write(f"="*50 + "\n\n")
            f.write(best_result.get_summary())

        logger.info(f"💾 报告已保存到: {summary_file}")

    return results


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(run_strategy_demo())
        print("\n🎉 演示完成！")
        sys.exit(0 if results else 1)
    except KeyboardInterrupt:
        print("\n⏰ 用户中断")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ 演示失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)