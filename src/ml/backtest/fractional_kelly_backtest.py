#!/usr/bin/env python3
"""
半凯利公式降噪回测脚本
Financial Logic Recovery - 使用半凯利策略重新回测52场意甲比赛
"""

from datetime import datetime
import json
import logging
from pathlib import Path
import sys

import joblib
import numpy as np

# 添加项目路径 - 修复路径计算
project_root = Path(__file__).parent.parent.parent.parent  # 从src/ml/backtest回到根目录
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from src.ml.strategy.fractional_kelly import calculate_fractional_kelly_for_prediction

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class FractionalKellyBacktester:
    """半凯利公式回测器"""

    def __init__(self, initial_bankroll: float = 10000.0):
        """
        初始化回测器

        Args:
            initial_bankroll: 初始资金
        """
        self.initial_bankroll = initial_bankroll
        self.current_bankroll = initial_bankroll
        self.betting_history = []
        self.project_root = project_root

        # 加载模型 - 使用V2.3新模型
        self.model_path = self.project_root / "data" / "models" / "xgb_football_v2.3_467real.joblib"
        self._load_model()

        logger.info("🎰 半凯利回测器初始化完成")
        logger.info(f"💰 初始资金: ${self.initial_bankroll:,.2f}")
        logger.info("⚠️ 使用半凯利策略降低风险")

    def _load_model(self):
        """加载模型"""
        try:
            # 使用绝对路径
            absolute_model_path = (
                self.project_root / "data" / "models" / "xgb_football_v2.1_simple.joblib"
            )
            model_data = joblib.load(absolute_model_path)
            self.model = model_data["model"]
            self.scaler = model_data["scaler"]
            self.feature_names = model_data["feature_names"]
            logger.info("✅ V2.1模型加载成功")
        except Exception as e:
            logger.exception(f"❌ 模型加载失败: {e}")
            raise

    def prepare_match_features(self, match_data: dict) -> np.ndarray | None:
        """准备比赛特征数据"""
        try:
            # 构建特征向量 - 基于V2.1模型的特征名
            features = []
            for feature_name in self.feature_names:
                if feature_name in match_data:
                    features.append(match_data[feature_name])
                # 使用默认值或估算值
                elif "xg" in feature_name.lower():
                    features.append(1.0)  # 默认xG
                elif "shots" in feature_name.lower():
                    features.append(12.0)  # 默认射门数
                elif "poss" in feature_name.lower() or "possession" in feature_name.lower():
                    features.append(50.0)  # 默认控球率
                elif "corner" in feature_name.lower():
                    features.append(5.0)  # 默认角球数
                elif "card" in feature_name.lower():
                    features.append(2.0)  # 默认牌数
                else:
                    features.append(0.0)

            # 转换为数组并标准化
            feature_array = np.array(features).reshape(1, -1)
            return self.scaler.transform(feature_array)


        except Exception as e:
            logger.warning(f"⚠️ 特征准备失败: {e}")
            return None

    def predict_match_with_fractional_kelly(self, match_data: dict) -> dict | None:
        """
        预测比赛并计算半凯利建议

        Args:
            match_data: 比赛数据

        Returns:
            Optional[Dict]: 预测结果和半凯利建议
        """
        try:
            # 准备特征
            features = self.prepare_match_features(match_data)
            if features is None:
                return None

            # 模型预测
            probabilities = self.model.predict_proba(features)[0]
            predicted_class = self.model.predict(features)[0]

            # 结果映射
            result_map = {0: "客胜", 1: "平局", 2: "主胜"}
            predicted_result = result_map[int(predicted_class)]

            # 模拟赔率 (在实际应用中应从市场获取)
            home_odds = match_data.get("home_odds", 2.0)
            draw_odds = match_data.get("draw_odds", 3.2)
            away_odds = match_data.get("away_odds", 3.8)

            # 计算半凯利建议
            kelly_recommendations = calculate_fractional_kelly_for_prediction(
                float(probabilities[2]),  # home_win
                float(probabilities[1]),  # draw
                float(probabilities[0]),  # away_win
                home_odds,
                draw_odds,
                away_odds,
            )

            # 只考虑有效投注
            valid_recommendations = {
                outcome: rec
                for outcome, rec in kelly_recommendations.items()
                if rec.is_valid_bet and rec.recommended_stake_percent > 0
            }

            if not valid_recommendations:
                return {
                    "predicted_result": predicted_result,
                    "probabilities": {
                        "home_win": float(probabilities[2]),
                        "draw": float(probabilities[1]),
                        "away_win": float(probabilities[0]),
                    },
                    "kelly_recommendations": {
                        "home": kelly_recommendations["home"].recommended_stake_percent,
                        "draw": kelly_recommendations["draw"].recommended_stake_percent,
                        "away": kelly_recommendations["away"].recommended_stake_percent,
                    },
                    "best_bet": None,
                    "market_odds": {"home": home_odds, "draw": draw_odds, "away": away_odds},
                    "valid_bets_count": 0,
                    "skip_reason": "Edge < 5% 或 胜率 < 40%",
                }

            # 获取最佳有效投注
            best_bet = max(
                valid_recommendations.items(), key=lambda x: x[1].recommended_stake_percent
            )
            best_outcome, best_kelly = best_bet

            return {
                "predicted_result": predicted_result,
                "probabilities": {
                    "home_win": float(probabilities[2]),
                    "draw": float(probabilities[1]),
                    "away_win": float(probabilities[0]),
                },
                "kelly_recommendations": {
                    "home": kelly_recommendations["home"].recommended_stake_percent,
                    "draw": kelly_recommendations["draw"].recommended_stake_percent,
                    "away": kelly_recommendations["away"].recommended_stake_percent,
                },
                "best_bet": {
                    "outcome": best_outcome,
                    "stake_percent": best_kelly.recommended_stake_percent,
                    "edge": best_kelly.edge,
                    "confidence": best_kelly.confidence,
                    "risk_level": best_kelly.risk_level,
                    "reason": best_kelly.reason,
                },
                "market_odds": {"home": home_odds, "draw": draw_odds, "away": away_odds},
                "valid_bets_count": len(valid_recommendations),
                "skip_reason": None,
            }

        except Exception as e:
            logger.warning(f"⚠️ 预测失败: {e}")
            return None

    def simulate_fractional_bet(self, prediction: dict, actual_result: str) -> dict:
        """
        模拟半凯利投注结果

        Args:
            prediction: 预测结果
            actual_result: 实际结果

        Returns:
            Dict: 投注结果
        """

        if prediction["best_bet"] is None:
            # 跳过投注
            return {
                "stake_percent": 0.0,
                "stake_amount": 0.0,
                "odds": 0.0,
                "predicted_outcome": None,
                "actual_outcome": None,
                "won": False,
                "profit": 0.0,
                "bankroll_before": self.current_bankroll,
                "bankroll_after": self.current_bankroll,
                "skip": True,
                "skip_reason": prediction.get("skip_reason", "No valid bet"),
            }

        best_bet = prediction["best_bet"]
        stake_percent = best_bet["stake_percent"]
        odds = prediction["market_odds"][best_bet["outcome"]]

        # 计算投注金额
        stake_amount = self.current_bankroll * (stake_percent / 100.0)

        # 判断是否赢钱
        result_map = {"H": "home", "D": "draw", "A": "away"}
        actual_outcome = result_map.get(actual_result, "unknown")

        if actual_outcome == best_bet["outcome"]:
            # 赢钱
            profit = stake_amount * (odds - 1)
            self.current_bankroll += profit
            won = True
        else:
            # 输钱
            self.current_bankroll -= stake_amount
            profit = -stake_amount
            won = False

        bet_result = {
            "stake_percent": stake_percent,
            "stake_amount": stake_amount,
            "odds": odds,
            "predicted_outcome": best_bet["outcome"],
            "actual_outcome": actual_outcome,
            "won": won,
            "profit": profit,
            "bankroll_before": self.current_bankroll - profit,
            "bankroll_after": self.current_bankroll,
            "skip": False,
            "skip_reason": None,
            "edge": best_bet["edge"],
            "confidence": best_bet["confidence"],
        }

        self.betting_history.append(bet_result)
        return bet_result

    def run_fractional_backtest_on_mock_data(self) -> dict:
        """
        在模拟意甲数据上运行半凯利回测

        Returns:
            Dict: 回测结果
        """
        logger.info("📊 开始半凯利公式降噪回测...")

        # 创建52场意甲比赛的模拟数据
        mock_serie_a_matches = self._create_mock_serie_a_data()

        total_matches = len(mock_serie_a_matches)
        won_bets = 0
        total_profit = 0
        skipped_bets = 0

        logger.info(f"🎮 回测 {total_matches} 场意甲比赛（半凯利策略）...")

        for i, match in enumerate(mock_serie_a_matches, 1):
            # 预测比赛
            prediction = self.predict_match_with_fractional_kelly(match)
            if prediction is None:
                continue

            # 模拟投注
            bet_result = self.simulate_fractional_bet(prediction, match["actual_result"])

            if bet_result["skip"]:
                skipped_bets += 1
            elif bet_result["won"]:
                won_bets += 1

            total_profit += bet_result["profit"]

            # 输出进度
            if i % 10 == 0:
                logger.info(
                    f"📈 已处理 {i}/{total_matches} 场，当前资金: ${self.current_bankroll:,.2f}，跳过: {skipped_bets}"
                )

        # 计算回测统计
        total_placed_bets = total_matches - skipped_bets
        win_rate = (won_bets / total_placed_bets) * 100 if total_placed_bets > 0 else 0
        roi = ((self.current_bankroll - self.initial_bankroll) / self.initial_bankroll) * 100

        backtest_results = {
            "summary": {
                "total_matches": total_matches,
                "skipped_bets": skipped_bets,
                "placed_bets": total_placed_bets,
                "won_bets": won_bets,
                "lost_bets": total_placed_bets - won_bets,
                "win_rate": win_rate,
                "initial_bankroll": self.initial_bankroll,
                "final_bankroll": self.current_bankroll,
                "total_profit": self.current_bankroll - self.initial_bankroll,
                "roi_percent": roi,
            },
            "betting_history": self.betting_history,
            "performance_metrics": self._calculate_performance_metrics(),
        }

        # 保存回测结果
        self._save_backtest_results(backtest_results)

        return backtest_results

    def _create_mock_serie_a_data(self) -> list[dict]:
        """创建52场模拟意甲比赛数据"""
        matches = []
        serie_a_teams = [
            "Inter Milan",
            "AC Milan",
            "Juventus",
            "AS Roma",
            "Lazio",
            "Napoli",
            "Atalanta",
            "Fiorentina",
            "Torino",
            "Sassuolo",
            "Verona",
            "Genoa",
        ]

        for _i in range(52):
            home_team = np.random.choice(serie_a_teams)
            away_team = np.random.choice([t for t in serie_a_teams if t != home_team])

            # 创建更真实的比赛数据
            match_data = {
                "home_team": home_team,
                "away_team": away_team,
                "home_xg": np.random.normal(1.3, 0.5),  # 意甲通常xG较低
                "away_xg": np.random.normal(1.1, 0.5),
                "home_total_shots": int(np.random.normal(14, 4)),
                "away_total_shots": int(np.random.normal(12, 4)),
                "home_shots_on_target": int(np.random.normal(4, 2)),
                "away_shots_on_target": int(np.random.normal(3, 2)),
                "total_shots_difference": 0,
                "home_total_passes": int(np.random.normal(500, 100)),
                "away_total_passes": int(np.random.normal(480, 100)),
                "total_passes_difference": 0,
                "home_pass_accuracy": np.random.normal(82, 5),
                "away_pass_accuracy": np.random.normal(80, 5),
                "pass_accuracy_difference": 0,
                "total_xg": 0,
                "xg_difference": 0,
                # 更真实的赔率（意甲通常赔率较高）
                "home_odds": max(1.3, np.random.normal(2.5, 0.8)),
                "draw_odds": max(2.5, np.random.normal(3.3, 0.6)),
                "away_odds": max(2.0, np.random.normal(3.2, 1.2)),
                # 实际结果 - 主队有轻微优势
                "actual_result": np.random.choice(["H", "D", "A"], p=[0.48, 0.26, 0.26]),
            }

            # 计算衍生特征
            match_data["xg_difference"] = match_data["home_xg"] - match_data["away_xg"]
            match_data["total_xg"] = match_data["home_xg"] + match_data["away_xg"]
            match_data["total_shots_difference"] = (
                match_data["home_total_shots"] - match_data["away_total_shots"]
            )
            match_data["total_passes_difference"] = (
                match_data["home_total_passes"] - match_data["away_total_passes"]
            )
            match_data["pass_accuracy_difference"] = (
                match_data["home_pass_accuracy"] - match_data["away_pass_accuracy"]
            )

            matches.append(match_data)

        return matches

    def _calculate_performance_metrics(self) -> dict:
        """计算性能指标"""
        if not self.betting_history:
            return {}

        # 过滤出实际投注的记录
        actual_bets = [bet for bet in self.betting_history if not bet.get("skip", True)]

        if not actual_bets:
            return {}

        profits = [bet["profit"] for bet in actual_bets]
        stake_percents = [bet["stake_percent"] for bet in actual_bets]
        edges = [bet.get("edge", 0) for bet in actual_bets if not bet.get("skip", True)]

        return {
            "total_bets": len(actual_bets),
            "avg_stake_percent": np.mean(stake_percents) if stake_percents else 0,
            "max_profit": max(profits) if profits else 0,
            "max_loss": min(profits) if profits else 0,
            "profit_volatility": np.std(profits) if profits else 0,
            "sharpe_ratio": np.mean(profits) / np.std(profits)
            if profits and np.std(profits) > 0
            else 0,
            "avg_edge": np.mean(edges) if edges else 0,
        }

    def _save_backtest_results(self, results: dict):
        """保存回测结果"""
        output_dir = self.project_root / "reports" / "fractional_kelly_backtest"
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_path = output_dir / f"fractional_kelly_backtest_{timestamp}.json"

        save_data = {
            "summary": results["summary"],
            "performance_metrics": results["performance_metrics"],
            "backtest_date": datetime.now().isoformat(),
            "model_version": "v2.1_simple",
            "strategy": "fractional_kelly_0.5x",
            "risk_controls": ["Edge >= 5%", "Win Probability >= 40%", "Max Stake 12.5%"],
            "initial_bankroll": self.initial_bankroll,
        }

        with open(results_path, "w", encoding="utf-8") as f:
            json.dump(save_data, f, indent=2, ensure_ascii=False)

        logger.info(f"📋 半凯利回测结果保存: {results_path}")

    def generate_report(self, results: dict) -> str:
        """生成回测报告"""
        summary = results["summary"]
        metrics = results["performance_metrics"]

        return f"""
🎰 半凯利公式降噪回测报告
{"=" * 60}

📊 总体统计:
• 比赛场次: {summary["total_matches"]}
• 跳过投注: {summary["skipped_bets"]} ({summary["skipped_bets"] / summary["total_matches"]:.1%})
• 实际投注: {summary["placed_bets"]}
• 赢投注数: {summary["won_bets"]}
• 输投注数: {summary["lost_bets"]}
• 胜率: {summary["win_rate"]:.2f}% (基于实际投注)

💰 资金表现:
• 初始资金: ${summary["initial_bankroll"]:,.2f}
• 最终资金: ${summary["final_bankroll"]:,.2f}
• 总盈亏: ${summary["total_profit"]:,.2f}
• 投资回报率: {summary["roi_percent"]:.2f}

📈 投注指标:
• 实际投注次数: {metrics.get("total_bets", 0)}
• 平均投注比例: {metrics.get("avg_stake_percent", 0):.2f}% (半凯利后)
• 平均边缘优势: {metrics.get("avg_edge", 0):.1f}%
• 最大单笔盈利: ${metrics.get("max_profit", 0):,.2f}
• 最大单笔亏损: ${metrics.get("max_loss", 0):,.2f}
• 盈利波动率: {metrics.get("profit_volatility", 0):.2f}
• 夏普比率: {metrics.get("sharpe_ratio", 0):.3f}

🎯 风控改进效果:
• 投注过滤: Edge < 5% 或 胜率 < 40% 自动跳过
• 风险降低: 半凯利系数 (0.5x)
• 最大仓位: 限制在12.5%以内

🏆 投资建议:
{"✅ 半凯利策略显著改善" if summary["roi_percent"] > -10 else "⚠️ 仍需优化，但风险已控制"}

策略对比:
• 全凯利回测: -24.44% ROI
• 半凯利回测: {summary["roi_percent"]:.2f}% ROI
• 改善幅度: {summary["roi_percent"] - (-24.44):+.2f}个百分点

回测时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
使用模型: V2.1 Simple XGBoost
策略版本: Fractional Kelly V2.0 (0.5x)
        """



def main():
    """主函数"""
    logger.info("🎰 半凯利公式降噪回测启动")
    logger.info("=" * 60)
    logger.info("⚠️ 金融风险控制：使用半凯利策略降低波动")

    try:
        # 创建回测器
        backtester = FractionalKellyBacktester(initial_bankroll=10000.0)

        # 运行半凯利回测
        results = backtester.run_fractional_backtest_on_mock_data()

        # 生成并输出报告
        backtester.generate_report(results)

        logger.info("🎉 半凯利公式降噪回测完成!")
        return 0

    except Exception as e:
        logger.exception(f"❌ 半凯利回测失败: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
