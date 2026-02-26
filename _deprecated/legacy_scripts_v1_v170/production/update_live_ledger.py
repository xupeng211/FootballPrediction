#!/usr/bin/env python3
"""
收益对账系统 (Live Ledger Reconciliation)
==========================================

功能:
1. 每天自动核对前一天的比赛结果
2. 计算 v26_smart_predict_results.csv 中高价值信号的实际盈亏
3. 更新到 reports/live_performance_2026.md

使用方式:
    # 手动执行
    python scripts/production/update_live_ledger.py

    # 指定日期范围
    python scripts/production/update_live_ledger.py --from-date 2026-01-01 --to-date 2026-01-07

    # 使用 cron 每天自动执行
    0 9 * * * cd /path/to/FootballPrediction && python scripts/production/update_live_ledger.py

Author: Senior Data Analyst & Betting Expert
Version: 1.0.0
Date: 2025-12-31
"""

import argparse
import asyncio
import logging
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

import aiohttp
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
from tenacity import retry, stop_after_attempt, wait_exponential

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.config_unified import get_settings
from src.ops.alert_manager import AlertManager, AlertSeverity

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(PROJECT_ROOT / "logs" / "live_ledger.log"),
    ],
)
logger = logging.getLogger(__name__)


# ============================================================================
# 配置
# ============================================================================

# 假设投注金额（单位：点）
UNIT_STAKE = 10  # 每注 10 点

# 高价值定义
HIGH_VALUE_CONFIDENCE = 0.60  # 置信度 > 60%
HIGH_VALUE_ROI = 0.05  # 预期 ROI > 5%

# 报告文件路径
PERFORMANCE_REPORT_PATH = PROJECT_ROOT / "reports" / "live_performance_2026.md"
PREDICTION_FILE_PATH = PROJECT_ROOT / "predictions" / "v26_smart_predict_results.csv"


# ============================================================================
# 对账系统类
# ============================================================================


class LiveLedgerReconciler:
    """
    收益对账系统

    职责:
    1. 从数据库获取已完成的比赛结果
    2. 读取预测文件中的投注信号
    3. 计算实际盈亏
    4. 生成/更新性能报告
    """

    def __init__(self):
        """初始化"""
        self.settings = get_settings()
        self.alert_manager = AlertManager()
        self._conn = None

        # 确保报告目录存在
        PERFORMANCE_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    def get_connection(self):
        """获取数据库连接"""
        if self._conn is None or self._conn.closed:
            self._conn = psycopg2.connect(
                host=self.settings.database.host,
                port=self.settings.database.port,
                database=self.settings.database.name,
                user=self.settings.database.user,
                password=self.settings.database.password.get_secret_value(),
                cursor_factory=RealDictCursor,
            )
        return self._conn

    def _parse_confidence(self, conf_str: str) -> float:
        """解析置信度字符串 (如 "64.87%" -> 0.6487)"""
        if pd.isna(conf_str):
            return 0.0
        if isinstance(conf_str, float):
            return conf_str / 100.0 if conf_str > 1 else conf_str
        if isinstance(conf_str, str):
            return float(conf_str.rstrip("%")) / 100.0
        return 0.0

    def _parse_roi(self, roi_str: str) -> float:
        """解析 ROI 字符串 (如 "5.23%" -> 0.0523)"""
        if pd.isna(roi_str):
            return 0.0
        if isinstance(roi_str, float):
            return roi_str / 100.0 if roi_str > 1 else roi_str
        if isinstance(roi_str, str):
            return float(roi_str.rstrip("%")) / 100.0
        return 0.0

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def _fetch_match_result(self, session, match_id: str) -> dict:
        """
        从 FotMob API 获取比赛结果

        Args:
            session: aiohttp 会话
            match_id: 比赛 ID

        Returns:
            包含实际结果的字典
        """
        url = f"https://www.fotmob.com/api/matchDetails"
        params = {"matchId": str(match_id)}

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
            "Referer": "https://www.fotmob.com/",
        }

        try:
            async with session.get(url, params=params, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as response:
                if response.status == 200:
                    data = await response.json()

                    # 提取比赛状态和比分
                    status_data = data.get("header", {}).get("status", {})
                    match_status = status_data.get("statusStr", "").lower()

                    score_str = status_data.get("scoreStr", "")

                    home_score = None
                    away_score = None

                    if score_str:
                        match = re.search(r"(\d+)\s*-\s*(\d+)", score_str)
                        if match:
                            home_score = int(match.group(1))
                            away_score = int(match.group(2))

                    return {
                        "status": match_status,
                        "home_score": home_score,
                        "away_score": away_score,
                        "finished": match_status in ["finished", "ft", "ended"],
                    }

                elif response.status == 404:
                    return {"status": "not_found", "home_score": None, "away_score": None, "finished": False}
                else:
                    logger.warning(f"⚠️  比赛 {match_id}: HTTP {response.status}")
                    return {"status": "error", "home_score": None, "away_score": None, "finished": False}

        except asyncio.TimeoutError:
            logger.warning(f"⚠️  比赛 {match_id}: 请求超时")
            return {"status": "timeout", "home_score": None, "away_score": None, "finished": False}
        except Exception as e:
            logger.warning(f"⚠️  比赛 {match_id}: {e}")
            return {"status": "error", "home_score": None, "away_score": None, "finished": False}

    async def _update_match_results_from_api(self, predictions_df: pd.DataFrame) -> pd.DataFrame:
        """
        从 API 更新比赛结果

        Args:
            predictions_df: 预测数据框

        Returns:
            更新后的数据框（添加 actual_result, actual_home_score, actual_away_score 列）
        """
        predictions_df["actual_result"] = None
        predictions_df["actual_home_score"] = None
        predictions_df["actual_away_score"] = None
        predictions_df["match_finished"] = False

        async with aiohttp.ClientSession() as session:
            for idx, row in predictions_df.iterrows():
                match_id = row["match_id"]

                # 只更新已完成的比赛
                result = await self._fetch_match_result(session, match_id)

                predictions_df.at[idx, "match_finished"] = result["finished"]
                predictions_df.at[idx, "actual_home_score"] = result["home_score"]
                predictions_df.at[idx, "actual_away_score"] = result["away_score"]

                # 判断实际结果
                if result["finished"]:
                    if result["home_score"] > result["away_score"]:
                        predictions_df.at[idx, "actual_result"] = "Home"
                    elif result["home_score"] < result["away_score"]:
                        predictions_df.at[idx, "actual_result"] = "Away"
                    else:
                        predictions_df.at[idx, "actual_result"] = "Draw"

                # 避免过快请求
                await asyncio.sleep(0.5)

        return predictions_df

    def _get_finished_matches_from_db(self, from_date: datetime, to_date: datetime) -> pd.DataFrame:
        """
        从数据库获取已完成的比赛

        Args:
            from_date: 起始日期
            to_date: 结束日期

        Returns:
            比赛数据框
        """
        conn = self.get_connection()

        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT
                    m.match_id,
                    m.home_team,
                    m.away_team,
                    m.match_date,
                    m.home_score,
                    m.away_score,
                    m.status,
                    m.league_name
                FROM matches m
                WHERE m.status = 'finished'
                  AND m.home_score IS NOT NULL
                  AND m.away_score IS NOT NULL
                  AND m.match_date >= %s
                  AND m.match_date < %s
                ORDER BY m.match_date DESC
            """, (from_date, to_date))

            matches_data = cursor.fetchall()

            if matches_data:
                return pd.DataFrame(matches_data)
            else:
                return pd.DataFrame()

    def _calculate_pnl(self, predictions_df: pd.DataFrame) -> dict:
        """
        计算盈亏

        Args:
            predictions_df: 包含预测和实际结果的数据框

        Returns:
            盈亏统计字典
        """
        # 早期返回：空数据框或缺少必需列
        required_columns = ["confidence_pct", "expected_roi_pct", "match_finished"]
        if predictions_df.empty or not all(col in predictions_df.columns for col in required_columns):
            return {
                "total_bets": 0,
                "won_bets": 0,
                "lost_bets": 0,
                "win_rate": 0.0,
                "total_stake": 0,
                "total_return": 0,
                "net_pnl": 0,
                "roi": 0.0,
            }

        # 筛选高价值信号
        # 注意：expected_roi_pct 是由 _parse_roi 返回的小数格式 (如 0.065)
        # 所以应该直接与 HIGH_VALUE_ROI (0.05) 比较，而不是乘以 100
        high_value_df = predictions_df[
            (predictions_df["confidence_pct"] >= HIGH_VALUE_CONFIDENCE) &
            (predictions_df["expected_roi_pct"] >= HIGH_VALUE_ROI)
        ].copy()

        # 筛选已完成的比赛
        finished_df = high_value_df[high_value_df["match_finished"] == True].copy()

        if len(finished_df) == 0:
            return {
                "total_bets": 0,
                "won_bets": 0,
                "lost_bets": 0,
                "win_rate": 0.0,
                "total_stake": 0,
                "total_return": 0,
                "net_pnl": 0,
                "roi": 0.0,
            }

        # 计算每场盈亏
        results = []
        for _, row in finished_df.iterrows():
            prediction = row["prediction"]
            actual = row["actual_result"]

            if pd.isna(actual):
                continue

            # 判断输赢
            won = (prediction == actual)

            # 计算回报（简化版：假设赔率为 1/概率）
            if prediction == "Home":
                prob = row["prob_home_pct"]
            elif prediction == "Draw":
                prob = row["prob_draw_pct"]
            else:  # Away
                prob = row["prob_away_pct"]

            # 简化赔率（公平赔率，不考虑利润率）
            if prob > 0:
                decimal_odds = 1.0 / prob
            else:
                decimal_odds = 1.0

            stake = UNIT_STAKE
            if won:
                profit = stake * (decimal_odds - 1)
                return_stake = stake + profit
            else:
                profit = -stake
                return_stake = 0

            results.append({
                "match_id": row["match_id"],
                "home_team": row["home_team"],
                "away_team": row["away_team"],
                "match_date": row["match_date"],
                "prediction": prediction,
                "actual": actual,
                "confidence": row["confidence"],
                "expected_roi": row["expected_roi"],
                "won": won,
                "stake": stake,
                "odds": decimal_odds,
                "profit": profit,
                "return": return_stake,
            })

        if not results:
            return {
                "total_bets": 0,
                "won_bets": 0,
                "lost_bets": 0,
                "win_rate": 0.0,
                "total_stake": 0,
                "total_return": 0,
                "net_pnl": 0,
                "roi": 0.0,
            }

        results_df = pd.DataFrame(results)

        total_bets = len(results_df)
        won_bets = results_df["won"].sum()
        lost_bets = total_bets - won_bets
        win_rate = won_bets / total_bets if total_bets > 0 else 0
        total_stake = results_df["stake"].sum()
        total_return = results_df["return"].sum()
        net_pnl = results_df["profit"].sum()
        roi = (net_pnl / total_stake * 100) if total_stake > 0 else 0

        return {
            "total_bets": total_bets,
            "won_bets": won_bets,
            "lost_bets": lost_bets,
            "win_rate": win_rate,
            "total_stake": total_stake,
            "total_return": total_return,
            "net_pnl": net_pnl,
            "roi": roi,
            "details": results_df,
        }

    def _generate_performance_report(self, stats: dict, from_date: datetime, to_date: datetime) -> str:
        """
        生成性能报告

        Args:
            stats: 统计数据
            from_date: 起始日期
            to_date: 结束日期

        Returns:
            Markdown 格式的报告
        """
        report = f"""# 2026 实战预测性能报告

> 最后更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
> 数据范围: {from_date.strftime('%Y-%m-%d')} 至 {to_date.strftime('%Y-%m-%d')}

---

## 核心指标

| 指标 | 数值 |
|------|------|
| **总投注数** | {stats['total_bets']} 注 |
| **命中投注** | {stats['won_bets']} 注 |
| **未命中投注** | {stats['lost_bets']} 注 |
| **命中率** | {stats['win_rate']:.2%} |
| **总投注额** | {stats['total_stake']:.0f} 点 |
| **总回报** | {stats['total_return']:.0f} 点 |
| **净盈亏** | {stats['net_pnl']:+.0f} 点 |
| **投资回报率 (ROI)** | {stats['roi']:+.2f}% |

---

## 盈亏趋势

"""

        if stats.get("details") is not None and len(stats["details"]) > 0:
            details_df = stats["details"]

            # 按日期汇总
            details_df["match_date"] = pd.to_datetime(details_df["match_date"])
            daily_pnl = details_df.groupby(details_df["match_date"].dt.date).agg({
                "profit": "sum",
                "won": "sum",
                "stake": "sum",
            }).reset_index()
            daily_pnl.columns = ["date", "profit", "wins", "stake"]
            daily_pnl["roi"] = (daily_pnl["profit"] / daily_pnl["stake"] * 100)

            report += "| 日期 | 投注 | 命中 | 盈亏 | ROI |\n"
            report += "|------|------|------|------|-----|\n"

            for _, row in daily_pnl.iterrows():
                profit_color = "🟢" if row["profit"] >= 0 else "🔴"
                report += f"| {row['date']} | {int(row['stake']/UNIT_STAKE)} | {int(row['wins'])} | {profit_color} {row['profit']:+.0f} | {row['roi']:+.1f}% |\n"

        report += "\n---\n\n## 详细投注记录\n\n"

        if stats.get("details") is not None and len(stats["details"]) > 0:
            details_df = stats["details"]

            report += "| 日期 | 对阵 | 预测 | 实际 | 置信度 | 赔率 | 盈亏 |\n"
            report += "|------|------|------|------|--------|------|------|\n"

            for _, row in details_df.iterrows():
                match_date = pd.to_datetime(row["match_date"]).strftime("%m-%d")
                matchup = f"{row['home_team'][:10]} vs {row['away_team'][:10]}"
                pred_icon = "✓" if row["won"] else "✗"
                profit_color = "🟢" if row["profit"] >= 0 else "🔴"

                report += f"| {match_date} | {matchup} | {row['prediction']} {pred_icon} | {row['actual']} | {row['confidence']} | {row['odds']:.2f} | {profit_color} {row['profit']:+.0f} |\n"

        report += f"\n---\n\n## 说明\n\n"
        report += f"- **投注单位**: {UNIT_STAKE} 点/注\n"
        report += f"- **高价值定义**: 置信度 > {HIGH_VALUE_CONFIDENCE*100:.0f}% 且 预期 ROI > {HIGH_VALUE_ROI*100:.0f}%\n"
        report += f"- **赔率计算**: 使用模型预测概率的倒数作为公平赔率（未考虑博彩公司利润率）\n"
        report += f"- **数据来源**: FotMob API + V26.8 预测模型\n"
        report += f"\n---\n\n"
        report += f"<p style='color: #6c757d; font-size: 12px;'>"
        report += f"FootballPrediction 收益对账系统 | V26.8 Production<br>"
        report += f"本报告由 scripts/production/update_live_ledger.py 自动生成"
        report += f"</p>\n"

        return report

    def reconcile(self, from_date: datetime | None = None, to_date: datetime | None = None) -> dict:
        """
        执行对账

        Args:
            from_date: 起始日期（默认昨天）
            to_date: 结束日期（默认今天）

        Returns:
            对账结果
        """
        logger.info("")
        logger.info("=" * 60)
        logger.info("收益对账系统启动")
        logger.info("=" * 60)

        # 默认对账昨天
        if from_date is None:
            from_date = datetime.now() - timedelta(days=1)
            from_date = from_date.replace(hour=0, minute=0, second=0, microsecond=0)
        if to_date is None:
            to_date = from_date + timedelta(days=1)

        logger.info(f"对账期间: {from_date.strftime('%Y-%m-%d')} 至 {to_date.strftime('%Y-%m-%d')}")
        logger.info("")

        # 1. 从数据库获取已完成的比赛
        logger.info("步骤 1: 获取已完成的比赛...")
        finished_matches = self._get_finished_matches_from_db(from_date, to_date)

        if len(finished_matches) == 0:
            logger.info("✓ 该期间无已完成的比赛")
            return {"status": "no_matches", "stats": None}
        else:
            logger.info(f"✓ 找到 {len(finished_matches)} 场已完成比赛")

        # 2. 读取预测文件
        logger.info("")
        logger.info("步骤 2: 读取预测文件...")

        if not PREDICTION_FILE_PATH.exists():
            logger.error(f"✗ 预测文件不存在: {PREDICTION_FILE_PATH}")
            return {"status": "no_predictions", "stats": None}

        predictions_df = pd.read_csv(PREDICTION_FILE_PATH)
        logger.info(f"✓ 预测文件已加载: {len(predictions_df)} 条记录")

        # 解析数值列
        predictions_df["confidence_pct"] = predictions_df["confidence"].apply(self._parse_confidence)
        predictions_df["prob_home_pct"] = predictions_df["prob_home"].apply(self._parse_confidence)
        predictions_df["prob_draw_pct"] = predictions_df["prob_draw"].apply(self._parse_confidence)
        predictions_df["prob_away_pct"] = predictions_df["prob_away"].apply(self._parse_confidence)
        predictions_df["expected_roi_pct"] = predictions_df["expected_roi"].apply(self._parse_roi)

        # 筛选该期间的比赛
        predictions_df["match_date_dt"] = pd.to_datetime(predictions_df["match_date"])
        period_predictions = predictions_df[
            (predictions_df["match_date_dt"] >= from_date) &
            (predictions_df["match_date_dt"] < to_date)
        ]

        logger.info(f"✓ 该期间预测: {len(period_predictions)} 条")

        # 3. 从数据库更新实际结果
        logger.info("")
        logger.info("步骤 3: 更新比赛结果...")

        # 创建 match_id 到实际结果的映射
        result_map = {}
        for _, match in finished_matches.iterrows():
            result_map[match["match_id"]] = {
                "home_score": match["home_score"],
                "away_score": match["away_score"],
                "actual_result": "Home" if match["home_score"] > match["away_score"] else
                                "Draw" if match["home_score"] == match["away_score"] else
                                "Away",
            }

        for idx, row in period_predictions.iterrows():
            match_id = row["match_id"]
            if match_id in result_map:
                period_predictions.at[idx, "actual_result"] = result_map[match_id]["actual_result"]
                period_predictions.at[idx, "actual_home_score"] = result_map[match_id]["home_score"]
                period_predictions.at[idx, "actual_away_score"] = result_map[match_id]["away_score"]
                period_predictions.at[idx, "match_finished"] = True
            else:
                period_predictions.at[idx, "match_finished"] = False

        finished_count = period_predictions["match_finished"].sum()
        logger.info(f"✓ 已更新 {finished_count} 场比赛结果")

        # 4. 计算盈亏
        logger.info("")
        logger.info("步骤 4: 计算盈亏...")

        stats = self._calculate_pnl(period_predictions)

        logger.info(f"  总投注: {stats['total_bets']} 注")
        logger.info(f"  命中: {stats['won_bets']} 注")
        logger.info(f"  命中率: {stats['win_rate']:.2%}")
        logger.info(f"  净盈亏: {stats['net_pnl']:+.0f} 点")
        logger.info(f"  ROI: {stats['roi']:+.2f}%")

        # 5. 生成报告
        logger.info("")
        logger.info("步骤 5: 生成性能报告...")

        report = self._generate_performance_report(stats, from_date, to_date)

        with open(PERFORMANCE_REPORT_PATH, "w", encoding="utf-8") as f:
            f.write(report)

        logger.info(f"✓ 报告已生成: {PERFORMANCE_REPORT_PATH}")

        # 6. 发送告警（如果需要）
        if stats["total_bets"] > 0:
            if stats["roi"] < -10:
                # ROI 低于 -10%，发送警告
                asyncio.run(self.alert_manager.send_alert(
                    title="⚠️ 收益对账警告",
                    message=f"对账期间 {from_date.strftime('%Y-%m-%d')} 至 {to_date.strftime('%Y-%m-%d')} ROI 为 {stats['roi']:+.2f}%，请关注！",
                    severity=AlertSeverity.WARNING,
                    alert_type="ledger_warning",
                    metadata={
                        "from_date": from_date.isoformat(),
                        "to_date": to_date.isoformat(),
                        "total_bets": str(stats["total_bets"]),
                        "roi": f"{stats['roi']:.2f}%",
                        "net_pnl": f"{stats['net_pnl']:.0f}",
                    }
                ))
            elif stats["roi"] > 20:
                # ROI 高于 20%，发送祝贺
                asyncio.run(self.alert_manager.send_alert(
                    title="🎉 收益对账喜报",
                    message=f"对账期间 {from_date.strftime('%Y-%m-%d')} 至 {to_date.strftime('%Y-%m-%d')} ROI 高达 {stats['roi']:+.2f}%！",
                    severity=AlertSeverity.INFO,
                    alert_type="ledger_success",
                    metadata={
                        "from_date": from_date.isoformat(),
                        "to_date": to_date.isoformat(),
                        "total_bets": str(stats["total_bets"]),
                        "roi": f"{stats['roi']:.2f}%",
                        "net_pnl": f"{stats['net_pnl']:.0f}",
                    }
                ))

        logger.info("")
        logger.info("=" * 60)
        logger.info("✓ 收益对账完成")
        logger.info("=" * 60)

        return {
            "status": "success",
            "stats": stats,
            "report_path": str(PERFORMANCE_REPORT_PATH),
        }


# ============================================================================
# 主函数
# ============================================================================


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="收益对账系统")
    parser.add_argument("--from-date", type=str, help="起始日期 (YYYY-MM-DD)")
    parser.add_argument("--to-date", type=str, help="结束日期 (YYYY-MM-DD)")
    args = parser.parse_args()

    # 解析日期
    from_date = None
    to_date = None

    if args.from_date:
        from_date = datetime.strptime(args.from_date, "%Y-%m-%d")
    if args.to_date:
        to_date = datetime.strptime(args.to_date, "%Y-%m-%d")
        # 对结束日期加一天，使其包含当天
        to_date = to_date + timedelta(days=1)

    # 创建对账系统
    reconciler = LiveLedgerReconciler()

    # 执行对账
    result = reconciler.reconcile(from_date, to_date)

    if result["status"] == "success":
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
