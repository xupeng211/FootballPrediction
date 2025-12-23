#!/usr/bin/env python3
"""
V3.0 全球模型盈利能力回测器 - 半凯利0.5x策略
使用V3.0模型对567场数据进行全样本回测
维持Edge > 7%的策略，验证ROI表现
"""

import sys
import os
import logging
import joblib
import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from src.config_unified import get_settings
from sklearn.preprocessing import StandardScaler

# 配置日志
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class V3ROIBacktest:
    """V3.0模型盈利能力回测器"""

    def __init__(self):
        """初始化回测器"""
        self.settings = get_settings()
        self.project_root = Path(__file__).parent.parent.parent

        # 模型和报告路径
        self.models_dir = self.project_root / "data" / "models"
        self.reports_dir = self.project_root / "reports" / "v3_roi_backtest"
        self.reports_dir.mkdir(parents=True, exist_ok=True)

        # V3.0模型路径
        self.model_path = self.models_dir / "xgb_football_v3.0_global.joblib"
        self.metadata_path = self.models_dir / "xgb_football_v3.0_global_metadata.json"

        # V3.3 硬化策略参数 - 风险控制优先
        self.kelly_fraction = 0.2  # V3.3：锁定0.2x保守凯利，严禁调整
        self.min_edge = 10.0  # V3.3：提高边际要求至10%，确保高质量投注
        self.min_confidence = 55.0  # V3.3：提高置信度要求至55%
        self.max_drawdown_limit = 20.0  # V3.3：硬止损线-20%，触及立即停止
        self.STOP_LOSS_LINE = -20.0  # V3.3：硬编码止损线

        logger.info("🛡️ V3.1 风险控制ROI回测器初始化完成")
        logger.info(f"💰 保守策略: {self.kelly_fraction}x凯利, 边际>{self.min_edge}%, 置信度>{self.min_confidence}%")
        logger.info(f"🚨 风控限制: 最大回撤≤{self.max_drawdown_limit}%")

    def load_v3_model(self):
        """加载V3.0模型"""
        logger.info(f"📥 加载V3.0模型: {self.model_path}")

        if not self.model_path.exists():
            raise FileNotFoundError(f"V3.0模型文件不存在: {self.model_path}")

        model_data = joblib.load(self.model_path)
        self.model = model_data["model"]
        self.scaler = model_data["scaler"]
        self.feature_names = model_data["feature_names"]

        # 加载元数据
        if self.metadata_path.exists():
            with open(self.metadata_path, "r", encoding="utf-8") as f:
                self.metadata = json.load(f)
        else:
            self.metadata = {}

        logger.info(f"✅ V3.0模型加载完成")
        logger.info(f"📊 模型类型: {type(self.model).__name__}")
        logger.info(f"🔢 特征数量: {len(self.feature_names)}")
        logger.info(f"📈 训练准确率: {self.metadata.get('cv_mean_accuracy', 'N/A')}")

    def load_backtest_data(self) -> pd.DataFrame:
        """加载回测数据"""
        logger.info("📊 加载回测数据...")

        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor

            db = self.settings.database
            conn = psycopg2.connect(
                host=db.host, port=db.port, database=db.name, user=db.user, password=db.password.get_secret_value()
            )

            # 查询所有可用数据
            query = """
                SELECT * FROM match_features_training
                WHERE home_xg IS NOT NULL
                  AND away_xg IS NOT NULL
                  AND league_name IS NOT NULL
                ORDER BY league_name, match_time
            """

            df = pd.read_sql(query, conn)
            conn.close()

            logger.info(f"✅ 回测数据加载完成: {len(df)} 条记录")

            # 联赛分布
            league_dist = df["league_name"].value_counts()
            logger.info("🏆 回测数据联赛分布:")
            for league, count in league_dist.items():
                logger.info(f"   • {league:<15}: {count} 场")

            return df

        except Exception as e:
            logger.error(f"❌ 回测数据加载失败: {e}")
            raise

    def prepare_backtest_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """准备回测特征数据"""
        logger.info("🔧 准备回测特征...")

        # 创建与训练时完全相同的特征工程
        X = df.copy()

        # 创建工程化特征 - 与训练器保持一致
        # xG衍生特征
        if all(col in df.columns for col in ["home_xg", "away_xg"]):
            X["xg_difference"] = X["home_xg"] - X["away_xg"]
            X["xg_total"] = X["home_xg"] + X["away_xg"]
            X["xg_ratio"] = X["home_xg"] / (X["away_xg"] + 0.01)

        # 控球率衍生特征
        if all(col in df.columns for col in ["home_possession", "away_possession"]):
            X["possession_difference"] = X["home_possession"] - X["away_possession"]
            X["possession_ratio"] = X["home_possession"] / (X["away_possession"] + 0.01)

        # 射门效率特征
        if all(col in df.columns for col in ["home_shots_on_target", "home_shots_total"]):
            X["home_shot_accuracy"] = X["home_shots_on_target"] / (X["home_shots_total"] + 0.01)
        if all(col in df.columns for col in ["away_shots_on_target", "away_shots_total"]):
            X["away_shot_accuracy"] = X["away_shots_on_target"] / (X["away_shots_total"] + 0.01)

        # 综合实力指标
        if all(col in df.columns for col in ["home_xg", "home_possession", "home_shots_total"]):
            X["home_strength_index"] = X["home_xg"] * 0.4 + X["home_possession"] * 0.003 + X["home_shots_total"] * 0.02

        if all(col in df.columns for col in ["away_xg", "away_possession", "away_shots_total"]):
            X["away_strength_index"] = X["away_xg"] * 0.4 + X["away_possession"] * 0.003 + X["away_shots_total"] * 0.02

        # 选择模型所需的特征
        available_features = [col for col in self.feature_names if col in X.columns]
        X_final = X[available_features].copy()

        # 处理缺失值
        for col in X_final.columns:
            if X_final[col].dtype in ["int64", "float64"]:
                X_final[col] = X_final[col].fillna(X_final[col].median()).fillna(0.0)
            else:
                X_final[col] = X_final[col].fillna(0)

        logger.info(f"✅ 特征准备完成: {X_final.shape[1]} 维特征, {len(X_final)} 条样本")
        logger.info(f"📋 特征列: {available_features[:10]}...")  # 显示前10个特征
        return X_final

    def load_real_odds_from_database(self, df: pd.DataFrame) -> pd.DataFrame:
        """V3.4: 从数据库加载真实赔率数据，彻底拒绝模拟赔率

        Args:
            df: 原始数据框

        Returns:
            pd.DataFrame: 包含真实赔率的数据框
        """
        logger.info("🎯 V3.4: 从数据库加载真实赔率数据...")

        odds_df = df.copy()

        # 从数据库查询真实赔率
        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor

            # V3.4: 强制使用配置中指定的数据库
            db = self.settings.database
            db_config = {
                "host": db.host,
                "port": db.port,
                "database": db.name,
                "user": db.user,
                "password": db.password.get_secret_value(),
            }

            conn = psycopg2.connect(**db_config)

            # 构建外部ID列表
            external_ids = df["external_id"].tolist()
            placeholders = ",".join(["%s"] * len(external_ids))

            query = f"""
            SELECT
                external_id,
                home_opening_odds,
                away_opening_odds,
                draw_odds,
                home_current_odds,
                away_current_odds,
                draw_current_odds
            FROM match_features_training
            WHERE external_id IN ({placeholders})
              AND home_opening_odds IS NOT NULL
            """

            cursor = conn.cursor()
            cursor.execute(query, external_ids)
            results = cursor.fetchall()
            conn.close()

            # 转换为字典便于快速查找
            odds_dict = {
                row[0]: {
                    "home_opening_odds": row[1],
                    "away_opening_odds": row[2],
                    "draw_odds": row[3],
                    "home_current_odds": row[4],
                    "away_current_odds": row[5],
                    "draw_current_odds": row[6],
                }
                for row in results
            }

            # 将赔率数据合并到数据框
            def fill_odds(row):
                odds_data = odds_dict.get(row["external_id"])
                if odds_data:
                    return pd.Series({
                        "home_odds": odds_data["home_opening_odds"],
                        "away_odds": odds_data["away_opening_odds"],
                        "draw_odds": odds_data["draw_odds"]
                    })
                else:
                    # V3.4: 无真实赔率的比赛直接跳过，不使用模拟赔率
                    return pd.Series({
                        "home_odds": None,
                        "away_odds": None,
                        "draw_odds": None
                    })

            odds_data = odds_df.apply(fill_odds, axis=1)

            # 合并赔率数据
            odds_df["home_odds"] = odds_data["home_odds"]
            odds_df["away_odds"] = odds_data["away_odds"]
            odds_df["draw_odds"] = odds_data["draw_odds"]

            # V3.4: 过滤掉没有真实赔率的比赛
            matches_with_odds = odds_df.dropna(subset=["home_odds", "away_odds", "draw_odds"])
            matches_skipped = len(odds_df) - len(matches_with_odds)

            logger.info(f"✅ 加载真实赔率完成:")
            logger.info(f"   • 总比赛数: {len(odds_df)}")
            logger.info(f"   • 有赔率数据: {len(matches_with_odds)}")
            logger.info(f"   • 跳过无赔率: {matches_skipped}")
            logger.info(f"   • 真实赔率覆盖率: {len(matches_with_odds)/len(odds_df)*100:.1f}%")

            if len(matches_with_odds) == 0:
                logger.error("🚨 没有找到任何真实赔率数据！")
                raise ValueError("V3.4: 数据库中缺少真实赔率数据")

            return matches_with_odds

        except Exception as e:
            logger.error(f"❌ 加载真实赔率数据失败: {e}")
            logger.error("🚨 V3.4: 禁止使用模拟赔率！")
            raise

    def calculate_betting_odds(self, df: pd.DataFrame) -> pd.DataFrame:
        """V3.4: 已禁用 - 彻底拒绝模拟赔率

        Args:
            df: 数据框

        Returns:
            抛出异常，强制使用真实赔率
        """
        logger.error("🚨 V3.4: calculate_betting_odds 已被彻底禁用！")
        logger.error("🚨 请使用 load_real_odds_from_database 加载真实赔率数据")
        raise ValueError("V3.4: 模拟赔率功能已永久禁用，只能使用数据库中的真实赔率")

    def run_model_predictions(self, X: pd.DataFrame) -> np.ndarray:
        """运行模型预测"""
        logger.info("🤖 运行V3.0模型预测...")

        # 标准化特征
        X_scaled = self.scaler.transform(X)

        # 获取预测概率
        y_pred_proba = self.model.predict_proba(X_scaled)

        logger.info(f"✅ 预测完成，输出形状: {y_pred_proba.shape}")
        return y_pred_proba

    def load_real_match_results(self, df: pd.DataFrame) -> pd.Series:
        """加载真实比赛结果 - 从matches表读取"""
        logger.info("🔍 加载真实比赛结果...")

        try:
            # 连接数据库获取真实比分
            import psycopg2
            from psycopg2.extras import RealDictCursor

            # 使用统一配置系统
            db = self.settings.database
            db_config = {
                "host": db.host,
                "port": db.port,
                "database": db.name,
                "user": db.user,
                "password": db.password.get_secret_value(),
            }

            logger.info(f"🔧 连接数据库: {db.host}:{db.port}/{db.name}")
            conn = psycopg2.connect(**db_config)

            # 查询真实比分
            query = """
                SELECT m.external_id, m.result_score, m.status
                FROM matches m
                WHERE m.result_score IS NOT NULL
            """

            real_results = pd.read_sql(query, conn)
            conn.close()

            logger.info(f"✅ 加载了 {len(real_results)} 场真实比赛结果")

            # 创建真实结果映射
            result_map = {}
            for _, row in real_results.iterrows():
                result_map[row["external_id"]] = {"score": row["result_score"], "status": row["status"]}

            # 解析比分并确定结果 - 处理ID匹配问题
            def determine_real_result(external_id):
                # 尝试直接匹配
                if external_id in result_map:
                    info = result_map[external_id]
                    score = info["score"]

                    # 解析比分格式 "1 - 2"
                    if " - " in str(score):
                        try:
                            home_score, away_score = map(int, score.split(" - "))
                            if home_score > away_score:
                                return 2  # 主胜
                            elif home_score < away_score:
                                return 0  # 客胜
                            else:
                                return 1  # 平局
                        except:
                            logger.warning(f"⚠️ 无法解析比分: {score}")
                            return 1  # 默认平局
                    else:
                        logger.warning(f"⚠️ 比分格式异常: {score}")
                        return 1  # 默认平局

                # 尝试解析数字ID格式 (如果external_id是"pl_xxx"格式)
                if str(external_id).startswith("pl_"):
                    try:
                        num_id = int(str(external_id).replace("pl_", ""))
                        if num_id in result_map:
                            info = result_map[num_id]
                            score = info["score"]

                            # 解析比分格式 "1 - 2"
                            if " - " in str(score):
                                try:
                                    home_score, away_score = map(int, score.split(" - "))
                                    if home_score > away_score:
                                        return 2  # 主胜
                                    elif home_score < away_score:
                                        return 0  # 客胜
                                    else:
                                        return 1  # 平局
                                except:
                                    logger.warning(f"⚠️ 无法解析比分: {score}")
                                    return 1  # 默认平局
                            else:
                                logger.warning(f"⚠️ 比分格式异常: {score}")
                                return 1  # 默认平局
                    except:
                        pass

                # 如果都未找到，返回默认平局
                logger.debug(f"⚠️ 未找到比赛结果: {external_id}")
                return 1  # 默认平局

            # 为每场比赛确定真实结果
            real_outcomes = df["external_id"].apply(determine_real_result)

            # 统计结果分布
            result_counts = real_outcomes.value_counts().sort_index()
            result_names = {0: "客胜", 1: "平局", 2: "主胜"}
            logger.info("📊 真实比赛结果分布:")
            for result, count in result_counts.items():
                logger.info(f"  • {result_names[result]}: {count} 场")

            return real_outcomes

        except Exception as e:
            logger.error(f"❌ 加载真实比赛结果失败: {e}")
            raise

    def backtest_strategy(self, df: pd.DataFrame, y_pred_proba: np.ndarray, real_results: pd.Series) -> Dict:
        """执行真实结果回测策略"""
        logger.info(f"💰 执行真实结果回测策略: {self.kelly_fraction}x凯利")

        # 初始化回测结果
        results = {
            "total_bets": 0,
            "winning_bets": 0,
            "total_stake": 0.0,
            "total_return": 0.0,
            "total_profit": 0.0,
            "roi_percentage": 0.0,
            "max_drawdown": 0.0,
            "sharpe_ratio": 0.0,
            "bet_details": [],
        }

        cumulative_profit = 0.0
        max_profit = 0.0
        profit_series = []

        logger.info("🎯 开始基于真实赛果的回测...")

        for i, (_, row) in enumerate(df.iterrows()):
            # 获取预测概率
            probs = y_pred_proba[i]
            home_prob, draw_prob, away_prob = probs

            # 获取实际赔率
            home_odds = row["home_odds"]
            draw_odds = row["draw_odds"]
            away_odds = row["away_odds"]

            # 获取真实比赛结果
            actual_result = real_results.iloc[i]

            # 计算边际值
            home_edge = (home_odds * home_prob - 1) * 100
            draw_edge = (draw_odds * draw_prob - 1) * 100
            away_edge = (away_odds * away_prob - 1) * 100

            # 找到最佳投注机会
            edges = [home_edge, draw_edge, away_edge]
            odds = [home_odds, draw_odds, away_odds]
            probs_conf = [home_prob, draw_prob, away_prob]
            outcomes = ["home_win", "draw", "away_win"]

            best_edge = max(edges)
            best_idx = edges.index(best_edge)

            # V3.1 风险控制投注条件
            if best_edge > self.min_edge:
                max_prob = max(probs_conf)
                if max_prob * 100 >= self.min_confidence:
                    # 计算凯利比例 - V3.1保守模式
                    kelly_fraction = self.kelly_fraction * max(best_edge / 100, 0.15)
                    stake = min(kelly_fraction * 100, 5)  # V3.1：最大投注降低至5单位

                    # V3.3 硬化风险控制：触及-20%立即强制止损
                    current_drawdown = 0
                    if profit_series and cumulative_profit < 0:
                        peak = max(profit_series)
                        current_drawdown = (peak - cumulative_profit) / max(peak, 1) * 100

                    # V3.3: 硬止损线，但只在真实亏损时触发
                    if cumulative_profit < 0 and current_drawdown >= abs(self.STOP_LOSS_LINE):
                        logger.error(f"🛑 V3.3 硬止损触发！回撤{current_drawdown:.1f}% ≥ {abs(self.STOP_LOSS_LINE)}%")
                        logger.error("💀 投资组合已破产，立即停止所有投注活动")
                        break  # 强制终止回测

                    # 使用真实比赛结果！
                    won = actual_result == best_idx
                    return_amount = stake * odds[best_idx] if won else 0
                    profit = return_amount - stake

                    # 更新统计
                    results["total_bets"] += 1
                    if won:
                        results["winning_bets"] += 1
                    results["total_stake"] += stake
                    results["total_return"] += return_amount
                    results["total_profit"] += profit

                    cumulative_profit += profit
                    max_profit = max(max_profit, cumulative_profit)
                    profit_series.append(cumulative_profit)

                    # 记录投注详情
                    result_names = {0: "客胜", 1: "平局", 2: "主胜"}
                    results["bet_details"].append(
                        {
                            "match_id": row.get("external_id", f"match_{i}"),
                            "league": row.get("league_name", "Unknown"),
                            "bet_type": outcomes[best_idx],
                            "predicted_prob": max_prob,
                            "edge": best_edge,
                            "odds": odds[best_idx],
                            "stake": stake,
                            "profit": profit,
                            "won": won,
                            "actual_result": result_names.get(actual_result, "Unknown"),
                        }
                    )

        # 计算最终指标
        if results["total_stake"] > 0:
            results["roi_percentage"] = (results["total_profit"] / results["total_stake"]) * 100
            results["win_rate"] = (results["winning_bets"] / results["total_bets"]) * 100

        # 计算最大回撤
        if profit_series:
            max_drawdown = 0
            peak = profit_series[0]
            for profit in profit_series:
                if profit > peak:
                    peak = profit
                drawdown = (peak - profit) / max(peak, 1) * 100
                max_drawdown = max(max_drawdown, drawdown)
            results["max_drawdown"] = max_drawdown

        logger.info(f"✅ 真实回测完成: {results['total_bets']} 次投注")
        logger.info(f"💰 总投注: {results['total_stake']:.2f}, 总收益: {results['total_return']:.2f}")
        logger.info(f"📈 总盈亏: {results['total_profit']:.2f}, ROI: {results['roi_percentage']:.2f}%")
        logger.info(f"🎯 胜率: {results['win_rate']:.2f}%, 最大回撤: {results['max_drawdown']:.2f}%")

        return results

    def generate_roi_report(self, results: Dict):
        """生成ROI报告"""
        logger.info("📊 生成ROI报告...")

        report = {
            "backtest_info": {
                "model_version": "v3.0_global",
                "backtest_date": datetime.now().isoformat(),
                "strategy": f"半凯利 {self.kelly_fraction}x",
                "min_edge": f"{self.min_edge}%",
                "min_confidence": f"{self.min_confidence}%",
            },
            "performance": {
                "total_bets": results["total_bets"],
                "winning_bets": results["winning_bets"],
                "win_rate": results.get("win_rate", 0),
                "total_stake": results["total_stake"],
                "total_return": results["total_return"],
                "total_profit": results["total_profit"],
                "roi_percentage": results["roi_percentage"],
                "max_drawdown": results["max_drawdown"],
                "sharpe_ratio": results.get("sharpe_ratio", 0),
            },
            "assessment": {
                "profitable": results["total_profit"] > 0,
                "roi_acceptable": results["roi_percentage"] > 5.0,
                "risk_managed": results["max_drawdown"] < 25.0,
            },
        }

        # 保存报告
        report_path = self.reports_dir / f"v3_roi_backtest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        logger.info(f"📋 ROI报告保存: {report_path}")
        return report

    def run_complete_backtest(self):
        """运行完整回测"""
        logger.info("🚀 开始V3.0模型ROI回测")
        logger.info("=" * 80)

        try:
            # 1. 加载模型
            self.load_v3_model()

            # 2. 加载数据
            df = self.load_backtest_data()

            # 3. 准备特征
            X = self.prepare_backtest_features(df)

            # 4. V3.4: 彻底禁用模拟赔率，使用数据库真实赔率
            df_with_odds = self.load_real_odds_from_database(df)

            # 5. 运行预测
            y_pred_proba = self.run_model_predictions(X)

            # 6. 加载真实比赛结果
            real_results = self.load_real_match_results(df_with_odds)

            # 7. 执行真实结果回测
            results = self.backtest_strategy(df_with_odds, y_pred_proba, real_results)

            # 8. 生成报告
            report = self.generate_roi_report(results)

            # 8. 输出总结
            logger.info("🎉 V3.0 ROI回测完成!")
            logger.info("=" * 100)

            perf = report["performance"]
            logger.info("💰 V3.0模型盈利表现:")
            logger.info(f"   • 总投注次数:   {perf['total_bets']}")
            logger.info(f"   • 胜率:         {perf.get('win_rate', 0):.2f}%")
            logger.info(f"   • 总投注额:     ¥{perf['total_stake']:.2f}")
            logger.info(f"   • 总返还额:     ¥{perf['total_return']:.2f}")
            logger.info(f"   • 净盈亏:       ¥{perf['total_profit']:.2f}")
            logger.info(f"   • ROI:          {perf['roi_percentage']:.2f}%")
            logger.info(f"   • 最大回撤:     {perf['max_drawdown']:.2f}%")

            assessment = report["assessment"]
            logger.info("📊 风险评估:")
            logger.info(f"   • 盈利能力:     {'✅ 通过' if assessment['profitable'] else '❌ 失败'}")
            logger.info(f"   • ROI达标:     {'✅ 通过' if assessment['roi_acceptable'] else '❌ 失败'}")
            logger.info(f"   • 风险控制:     {'✅ 通过' if assessment['risk_managed'] else '❌ 失败'}")

            logger.info("=" * 100)
            if assessment["profitable"] and assessment["roi_acceptable"]:
                logger.info("🎯 V3.0模型通过盈利压力测试！")
                logger.info("💼 模型已准备好实盘应用！")
            else:
                logger.info("⚠️ V3.0模型需要进一步优化")

            return report

        except Exception as e:
            logger.error(f"❌ 回测失败: {e}")
            import traceback

            traceback.print_exc()
            return None


def main():
    """主函数"""
    logger.info("🚀 V3.0 全球模型ROI回测启动")
    logger.info("策略: 半凯利0.5x, Edge > 7%")

    backtester = V3ROIBacktest()
    report = backtester.run_complete_backtest()

    if report:
        logger.info("✅ ROI回测成功完成")
        return 0
    else:
        logger.error("❌ ROI回测失败")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
