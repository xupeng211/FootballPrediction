#!/usr/bin/env python3
"""
回测系统演示脚本 (Backtesting System Demo)

演示回测系统的功能，包括：
1. 不同策略的性能对比
2. 历史数据回测
3. 性能指标分析
4. 结果可视化

作者: Backtesting Engineer (P2-4)
创建时间: 2025-12-06
版本: 1.0.0
"""

import asyncio
import logging
import sys
import time
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.backtesting.engine import run_simple_backtest

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)8s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(
            f"/tmp/backtest_demo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        ),
    ],
)
logger = logging.getLogger(__name__)


class BacktestDemo:
    """回测演示类"""

    def __init__(self):
        self.results = {}

    async def run_strategy_comparison(self, days_back: int = 30) -> dict[str, Any]:
        """
        运行策略对比测试

        Args:
            days_back: 回测天数

        Returns:
            策略对比结果
        """
        logger.info("🚀 开始策略对比回测...")
        logger.info(f"📅 回测期间: {days_back}天")

        # 设置回测参数
        start_date = datetime.now() - timedelta(days=days_back)
        end_date = datetime.now()
        initial_balance = Decimal("10000.00")

        # 定义要测试的策略
        strategies = [
            ("simple_value", "简单价值策略", {}),
            ("conservative", "保守策略", {}),
            ("aggressive", "激进策略", {}),
        ]

        results = {}

        for strategy_name, strategy_desc, params in strategies:
            logger.info(f"🧪 测试策略: {strategy_desc}")

            try:
                start_time = time.time()

                # 运行回测
                result = await run_simple_backtest(
                    strategy_name=strategy_name,
                    start_date=start_date,
                    end_date=end_date,
                    initial_balance=initial_balance,
                    **params,
                )

                execution_time = time.time() - start_time

                # 记录结果
                results[strategy_name] = {
                    "description": strategy_desc,
                    "result": result,
                    "execution_time": execution_time,
                }

                logger.info(
                    f"   ✅ 完成 - ROI: {result.roi:+.2f}%, 胜率: {result.win_rate:.2%}, "
                    f"下注: {result.total_bets}场, 耗时: {execution_time:.1f}s"
                )

            except Exception as e:
                logger.error(f"   ❌ {strategy_desc} 失败: {e}")
                results[strategy_name] = {
                    "description": strategy_desc,
                    "error": str(e),
                    "execution_time": 0,
                }

        self.results = results
        return results

    def print_comparison_report(self) -> None:
        """打印策略对比报告"""
        logger.info("\n" + "=" * 80)
        logger.info("📊 策略对比报告")
        logger.info("=" * 80)

        if not self.results:
            logger.info("❌ 没有可用的结果")
            return

        print(
            f"\n{'策略名称':<15} {'ROI':<10} {'胜率':<10} {'下注数':<10} {'盈亏':<15} {'最大连胜':<10}"
        )
        print("-" * 80)

        for strategy_name, data in self.results.items():
            if "error" in data:
                print(
                    f"{data['description']:<15} {'错误':<10} {'-':<10} {'-':<10} {data['error']:<15} {'-':<10}"
                )
            else:
                result = data["result"]
                print(
                    f"{data['description']:<15} "
                    f"{result.roi:+7.2f}% {' ':<2} "
                    f"{result.win_rate:>6.1%} {' ':<3} "
                    f"{result.total_bets:>6} {' ':<3} "
                    f"{result.total_profit_loss:+13,.2f} {' ':<1} "
                    f"{result.max_consecutive_wins:>5}"
                )

        print("\n" + "=" * 80)

        # 找出最佳策略
        best_strategy = None
        best_roi = float("-inf")

        for strategy_name, data in self.results.items():
            if "error" not in data:
                roi = data["result"].roi
                if roi > best_roi:
                    best_roi = roi
                    best_strategy = strategy_name

        if best_strategy:
            best_data = self.results[best_strategy]
            logger.info(f"🏆 最佳策略: {best_data['description']}")
            logger.info(f"   投资回报率: {best_roi:+.2f}%")
            logger.info(f"   胜率: {best_data['result'].win_rate:.2%}")
            logger.info(f"   总盈亏: {best_data['result'].total_profit_loss:+,.2f}")

    async def run_detailed_backtest(self, strategy_name: str = "simple_value") -> None:
        """
        运行详细回测分析

        Args:
            strategy_name: 策略名称
        """
        logger.info(f"🔍 开始详细回测分析: {strategy_name}")

        try:
            # 使用较长的回测期间
            start_date = datetime.now() - timedelta(days=90)
            end_date = datetime.now()
            initial_balance = Decimal("10000.00")

            logger.info(f"📅 回测期间: {start_date.date()} 至 {end_date.date()}")
            logger.info(f"💰 初始资金: {initial_balance}")

            # 运行回测
            result = await run_simple_backtest(
                strategy_name=strategy_name,
                start_date=start_date,
                end_date=end_date,
                initial_balance=initial_balance,
            )

            # 打印详细结果
            logger.info("\n" + "=" * 80)
            logger.info("📈 详细回测结果")
            logger.info("=" * 80)

            summary = result.get_summary()
            print(summary)

            # 风险分析
            logger.info("\n📊 风险分析:")
            logger.info(
                f"   最大资金回撤: {result.initial_balance - result.min_balance:,.2f}"
            )
            logger.info(
                f"   回撤率: {((result.initial_balance - result.min_balance) / result.initial_balance * 100):.2f}%"
            )
            logger.info(f"   夏普比率: {result.sharpe_ratio:.3f}")
            logger.info(f"   盈亏波动率: {result.profit_volatility:.2f}")

            # 下注模式分析
            logger.info("\n💸 下注模式分析:")
            logger.info(f"   总下注金额: {result.total_staked:,.2f}")
            logger.info(f"   平均下注: {result.avg_stake:,.2f}")
            logger.info(f"   跳过下注: {result.skipped_bets}场")

            if len(result.bet_results) > 0:
                # 计算最近10场的表现
                recent_bets = result.bet_results[-10:]
                recent_wins = sum(1 for bet in recent_bets if bet.profit_loss > 0)
                recent_roi = (
                    sum(bet.profit_loss for bet in recent_bets) / initial_balance * 100
                )

                logger.info(
                    f"   最近10场胜率: {recent_wins}/{len(recent_bets)} ({recent_wins / len(recent_bets):.1%})"
                )
                logger.info(f"   最近10场ROI: {recent_roi:+.2f}%")

            # 保存详细结果
            self._save_detailed_results(result, strategy_name)

        except Exception as e:
            logger.error(f"❌ 详细回测失败: {e}")
            import traceback

            traceback.print_exc()

    def _save_detailed_results(self, result, strategy_name: str) -> None:
        """
        保存详细回测结果

        Args:
            result: 回测结果
            strategy_name: 策略名称
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 保存结果摘要
        summary_file = f"/tmp/backtest_summary_{strategy_name}_{timestamp}.txt"
        with open(summary_file, "w", encoding="utf-8") as f:
            f.write(f"回测策略: {strategy_name}\n")
            f.write(f"生成时间: {datetime.now()}\n")
            f.write("=" * 50 + "\n\n")
            f.write(result.get_summary())

        logger.info(f"💾 结果摘要已保存到: {summary_file}")

        # 保存下注记录
        if result.bet_results:
            bets_file = f"/tmp/backtest_bets_{strategy_name}_{timestamp}.csv"
            with open(bets_file, "w", encoding="utf-8") as f:
                # 写入表头
                f.write(
                    "match_id,bet_type,stake,odds,profit_loss,is_correct,timestamp\n"
                )

                # 写入数据
                for bet_result in result.bet_results:
                    f.write(f"{bet_result.decision.match_id},")
                    f.write(f"{bet_result.decision.bet_type.value},")
                    f.write(f"{bet_result.decision.stake},")
                    f.write(f"{bet_result.decision.odds},")
                    f.write(f"{bet_result.profit_loss},")
                    f.write(f"{bet_result.is_correct},")
                    f.write(f"{bet_result.settled_at.isoformat()}\n")

            logger.info(f"💾 下注记录已保存到: {bets_file}")

    def generate_visualization_data(self) -> dict[str, Any]:
        """
        生成可视化数据

        Returns:
            可视化数据字典
        """
        viz_data = {"strategies": [], "performance": {}, "comparison": []}

        for strategy_name, data in self.results.items():
            if "error" not in data:
                result = data["result"]

                viz_data["strategies"].append(strategy_name)
                viz_data["performance"][strategy_name] = {
                    "roi": result.roi,
                    "win_rate": result.win_rate,
                    "total_bets": result.total_bets,
                    "max_consecutive_wins": result.max_consecutive_wins,
                    "max_consecutive_losses": result.max_consecutive_losses,
                    "sharpe_ratio": result.sharpe_ratio,
                }

                if result.balance_history:
                    viz_data["comparison"].append(
                        {
                            "strategy": strategy_name,
                            "balance_history": [
                                float(b) for b in result.balance_history
                            ],
                        }
                    )

        return viz_data


async def main():
    """主函数"""
    print("⚽ 足球预测系统回测演示")
    print("=" * 60)

    demo = BacktestDemo()

    try:
        # 1. 运行策略对比
        logger.info("🎯 第一步：策略对比测试")
        await demo.run_strategy_comparison(days_back=7)  # 使用7天的数据
        demo.print_comparison_report()

        # 2. 运行详细回测
        logger.info("\n🔍 第二步：详细回测分析")
        await demo.run_detailed_backtest("simple_value")

        # 3. 生成可视化数据
        logger.info("\n📊 第三步：生成可视化数据")
        viz_data = demo.generate_visualization_data()

        logger.info(f"✅ 生成了 {len(viz_data['strategies'])} 个策略的可视化数据")

        # 打印总结
        print("\n" + "=" * 60)
        print("🎉 回测演示完成！")
        print("=" * 60)
        print("💡 提示:")
        print("   - 日志文件已保存到 /tmp/backtest_demo_*.log")
        print("   - 详细结果已保存到 /tmp/backtest_*.txt 和 /tmp/backtest_*.csv")
        print("   - 可以使用可视化工具进一步分析结果")

        return 0

    except Exception as e:
        logger.error(f"❌ 演示执行失败: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
