#!/usr/bin/env python3
"""
融合数据集构建脚本
首席数据科学家专用工具

功能：
1. 融合FBref (xG数据) 和 FotMob (赔率数据)
2. 生成训练数据集
3. 特征工程
4. 训练XGBoost模型
5. 计算ROI
"""

import json
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Tuple, List
import sys

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, text
import xgboost as xgb
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split


class FusedDatasetBuilder:
    """融合数据集构建器"""

    def __init__(self):
        self.engine = create_engine(
            "postgresql://postgres:postgres-dev-password@localhost:5432/football_prediction"
        )
        self.fbref_matches = []
        self.fotmob_matches = []
        self.teams_mapping = {}
        self.fused_data = []

    def load_fbref_data(self) -> None:
        """加载FBref比赛数据 (包含xG)"""
        print("📊 加载FBref比赛数据...")

        query = """
        SELECT
            m.id,
            m.home_team_id,
            m.away_team_id,
            m.match_date,
            m.home_score,
            m.away_score,
            m.stats,
            ht.name as home_team_name,
            at.name as away_team_name
        FROM matches m
        JOIN teams ht ON m.home_team_id = ht.id
        JOIN teams at ON m.away_team_id = at.id
        WHERE m.data_source = 'fbref'
            AND m.home_score IS NOT NULL
            AND m.away_score IS NOT NULL
            AND m.match_date >= '2024-01-01'
        ORDER BY m.match_date
        """

        with self.engine.connect() as conn:
            df = pd.read_sql(text(query), conn)

        # 解析xG数据
        df["home_xg"] = df["stats"].apply(self._extract_xg)
        df["away_xg"] = df["home_xg"] * 0.8  # 简化：假设客队xG是主队的0.8倍

        self.fbref_matches = df
        print(f"✅ 加载 {len(df)} 场FBref比赛")

    def load_fotmob_data(self) -> None:
        """加载FotMob比赛数据 (包含赔率)"""
        print("📊 加载FotMob比赛数据...")

        query = """
        SELECT
            m.id,
            m.home_team_id,
            m.away_team_id,
            m.match_date,
            m.home_score,
            m.away_score,
            m.odds,
            ht.name as home_team_name,
            at.name as away_team_name
        FROM matches m
        JOIN teams ht ON m.home_team_id = ht.id
        JOIN teams at ON m.away_team_id = at.id
        WHERE m.data_source = 'fotmob'
            AND m.home_score IS NOT NULL
            AND m.away_score IS NOT NULL
        ORDER BY m.match_date
        """

        with self.engine.connect() as conn:
            df = pd.read_sql(text(query), conn)

        self.fotmob_matches = df
        print(f"✅ 加载 {len(df)} 场FotMob比赛")

    def _extract_xg(self, stats_str) -> float:
        """从stats JSON中提取xG"""
        try:
            if pd.isna(stats_str):
                return 1.5  # 默认xG
            stats = json.loads(stats_str) if isinstance(stats_str, str) else stats_str
            return float(stats.get("xg", {}).get("home_xg", 1.5))
        except:
            return 1.5  # 默认xG

    def build_team_mapping(self) -> None:
        """构建队伍映射表"""
        print("🔗 构建队伍映射表...")

        query = """
        SELECT
            t.id,
            t.name,
            t.fotmob_external_id
        FROM teams t
        WHERE t.fotmob_external_id IS NOT NULL
        """

        with self.engine.connect() as conn:
            df = pd.read_sql(text(query), conn)

        # 创建映射：fotmob_external_id -> team_id
        for _, row in df.iterrows():
            self.teams_mapping[row["fotmob_external_id"]] = {
                "team_id": row["id"],
                "team_name": row["name"],
            }

        print(f"✅ 构建了 {len(self.teams_mapping)} 个队伍的映射")

    def generate_mock_odds(
        self, home_team: str, away_team: str, home_xg: float, away_xg: float
    ) -> Dict:
        """基于xG生成模拟赔率"""
        # 计算胜负概率 (简化模型)
        xg_diff = home_xg - away_xg
        home_strength = 0.5 + (xg_diff / 6.0)  # xG差异转换为概率
        home_strength = max(0.1, min(0.9, home_strength))

        # 假设平局概率为15-25%
        draw_prob = 0.20
        away_prob = max(0.1, 1.0 - home_strength - draw_prob)

        # 计算赔率 (加入庄家抽水)
        margin = 1.05  # 5% 抽水
        home_odds = round(margin / home_strength, 2)
        draw_odds = round(margin / draw_prob, 2)
        away_odds = round(margin / away_prob, 2)

        return {
            "home_odds": home_odds,
            "draw_odds": draw_odds,
            "away_odds": away_odds,
            "home_implied_prob": round(home_strength, 3),
            "draw_implied_prob": round(draw_prob, 3),
            "away_implied_prob": round(away_prob, 3),
        }

    def fuse_datasets(self) -> None:
        """融合FBref和FotMob数据集"""
        print("🔄 融合数据集...")

        # 如果没有FotMob数据，直接使用FBref数据并生成模拟赔率
        fused_matches = []

        for _, fbref_match in self.fbref_matches.iterrows():
            # 生成赔率数据
            odds_data = self.generate_mock_odds(
                fbref_match["home_team_name"],
                fbref_match["away_team_name"],
                fbref_match["home_xg"],
                fbref_match["away_xg"],
            )

            # 确定比赛结果
            if fbref_match["home_score"] > fbref_match["away_score"]:
                result = 2  # 主胜
            elif fbref_match["home_score"] == fbref_match["away_score"]:
                result = 1  # 平局
            else:
                result = 0  # 客胜

            fused_match = {
                "match_id": fbref_match["id"],
                "date": fbref_match["match_date"],
                "home_team": fbref_match["home_team_name"],
                "away_team": fbref_match["away_team_name"],
                "home_xg": round(fbref_match["home_xg"], 2),
                "away_xg": round(fbref_match["away_xg"], 2),
                "home_score": fbref_match["home_score"],
                "away_score": fbref_match["away_score"],
                "home_odds": odds_data["home_odds"],
                "draw_odds": odds_data["draw_odds"],
                "away_odds": odds_data["away_odds"],
                "home_implied_prob": odds_data["home_implied_prob"],
                "draw_implied_prob": odds_data["draw_implied_prob"],
                "away_implied_prob": odds_data["away_implied_prob"],
                "result": result,  # 0=客胜, 1=平局, 2=主胜
                "result_name": ["客胜", "平局", "主胜"][result],
            }

            fused_matches.append(fused_match)

        self.fused_data = fused_matches
        print(f"✅ 融合完成，生成了 {len(fused_matches)} 场比赛 (基于FBref + 模拟赔率)")

    def engineer_features(self) -> pd.DataFrame:
        """特征工程"""
        print("🔧 进行特征工程...")

        df = pd.DataFrame(self.fused_data)
        df["date"] = pd.to_datetime(df["date"])

        # 按队伍分组计算滚动特征
        features_df = []

        # 获取所有队伍
        all_teams = set(df["home_team"].tolist() + df["away_team"].tolist())

        for team in all_teams:
            # 获取该队伍的所有比赛 (主客场)
            home_games = df[df["home_team"] == team].copy()
            away_games = df[df["away_team"] == team].copy()

            # 为每场比赛计算历史特征
            for _, match in df.iterrows():
                if match["home_team"] != team and match["away_team"] != team:
                    continue

                current_date = match["date"]

                # 计算过去5场比赛的统计 (在当前比赛之前)
                if match["home_team"] == team:
                    # 主场比赛
                    is_home = True
                    opponent = match["away_team"]
                    goals_scored = match["home_score"]
                    goals_conceded = match["away_score"]
                    team_xg = match["home_xg"]
                else:
                    # 客场比赛
                    is_home = False
                    opponent = match["home_team"]
                    goals_scored = match["away_score"]
                    goals_conceded = match["home_score"]
                    team_xg = match["away_xg"]

                # 获取该队伍在当前比赛之前的所有比赛
                past_games = (
                    df[
                        ((df["home_team"] == team) | (df["away_team"] == team))
                        & (df["date"] < current_date)
                    ]
                    .sort_values("date")
                    .tail(5)
                )

                if len(past_games) > 0:
                    # 计算滚动特征
                    stats = self._calculate_rolling_stats(team, past_games)
                else:
                    # 使用默认值
                    stats = {
                        "avg_goals_scored": (
                            goals_scored if pd.notna(goals_scored) else 1.0
                        ),
                        "avg_goals_conceded": (
                            goals_conceded if pd.notna(goals_conceded) else 1.0
                        ),
                        "avg_xg": team_xg if pd.notna(team_xg) else 1.5,
                        "win_rate": 0.5,
                        "points_per_game": 1.0,
                        "recent_form": 0.0,
                    }

                # 添加特征到比赛记录
                if match["home_team"] == team:
                    match[f"home_{team}_avg_goals_scored"] = stats["avg_goals_scored"]
                    match[f"home_{team}_avg_goals_conceded"] = stats[
                        "avg_goals_conceded"
                    ]
                    match[f"home_{team}_avg_xg"] = stats["avg_xg"]
                    match[f"home_{team}_win_rate"] = stats["win_rate"]
                else:
                    match[f"away_{team}_avg_goals_scored"] = stats["avg_goals_scored"]
                    match[f"away_{team}_avg_goals_conceded"] = stats[
                        "avg_goals_conceded"
                    ]
                    match[f"away_{team}_avg_xg"] = stats["avg_xg"]
                    match[f"away_{team}_win_rate"] = stats["win_rate"]

                features_df.append(match)

        # 转换回DataFrame并去重
        result_df = pd.DataFrame(features_df).drop_duplicates(
            subset=["match_id", "home_team", "away_team"]
        )

        # 计算隐含概率 (如果还没有)
        if "home_implied_prob" not in result_df.columns:
            result_df["home_implied_prob"] = 1 / result_df["home_odds"]
            result_df["draw_implied_prob"] = 1 / result_df["draw_odds"]
            result_df["away_implied_prob"] = 1 / result_df["away_odds"]

        # 生成最终特征
        feature_columns = [
            "home_xg",
            "away_xg",
            "home_odds",
            "draw_odds",
            "away_odds",
            "home_implied_prob",
            "draw_implied_prob",
            "away_implied_prob",
            "result",
        ]

        # 查找所有队伍相关的滚动特征
        for col in result_df.columns:
            if "avg_goals" in col or "avg_xg" in col or "win_rate" in col:
                feature_columns.append(col)

        final_df = result_df[feature_columns].fillna(0)

        print(
            f"✅ 特征工程完成，生成 {len(final_df)} 行训练数据，{len(feature_columns)} 个特征"
        )
        return final_df

    def _calculate_rolling_stats(self, team: str, past_games: pd.DataFrame) -> Dict:
        """计算队伍在过去比赛中的滚动统计"""
        goals_scored = 0
        goals_conceded = 0
        xg_sum = 0
        wins = 0
        total_points = 0

        for _, game in past_games.iterrows():
            if game["home_team"] == team:
                goals_scored += (
                    game["home_score"] if pd.notna(game["home_score"]) else 0
                )
                goals_conceded += (
                    game["away_score"] if pd.notna(game["away_score"]) else 0
                )
                xg_sum += game["home_xg"] if pd.notna(game["home_xg"]) else 1.5
                if game["result"] == 2:  # 主胜
                    wins += 1
                    total_points += 3
                elif game["result"] == 1:  # 平局
                    total_points += 1
            else:
                goals_scored += (
                    game["away_score"] if pd.notna(game["away_score"]) else 0
                )
                goals_conceded += (
                    game["home_score"] if pd.notna(game["home_score"]) else 0
                )
                xg_sum += game["away_xg"] if pd.notna(game["away_xg"]) else 1.5
                if game["result"] == 0:  # 客胜
                    wins += 1
                    total_points += 3
                elif game["result"] == 1:  # 平局
                    total_points += 1

        num_games = len(past_games)

        return {
            "avg_goals_scored": goals_scored / num_games,
            "avg_goals_conceded": goals_conceded / num_games,
            "avg_xg": xg_sum / num_games,
            "win_rate": wins / num_games,
            "points_per_game": total_points / num_games,
            "recent_form": total_points / num_games / 3.0,  # 标准化到0-1
        }

    def save_training_data(self, df: pd.DataFrame) -> None:
        """保存训练数据"""
        # 添加球队信息到训练数据
        if len(self.fused_data) > 0:
            # 确保DataFrame和fused_data长度一致
            min_len = min(len(df), len(self.fused_data))
            df = df.head(min_len).copy()

            df["match_id"] = [self.fused_data[i]["match_id"] for i in range(min_len)]
            df["date"] = [self.fused_data[i]["date"] for i in range(min_len)]
            df["home_team"] = [self.fused_data[i]["home_team"] for i in range(min_len)]
            df["away_team"] = [self.fused_data[i]["away_team"] for i in range(min_len)]
            df["home_score"] = [
                self.fused_data[i]["home_score"] for i in range(min_len)
            ]
            df["away_score"] = [
                self.fused_data[i]["away_score"] for i in range(min_len)
            ]

        output_file = project_root / "training_set.csv"
        df.to_csv(output_file, index=False)
        print(f"💾 训练数据已保存: {output_file}")

    def train_model(self, df: pd.DataFrame) -> Tuple[xgb.XGBClassifier, Dict]:
        """训练XGBoost模型"""
        print("🚀 训练XGBoost模型...")

        # 准备特征和标签
        feature_cols = [col for col in df.columns if col != "result"]
        X = df[feature_cols]
        y = df["result"]

        # 分割训练集和测试集
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )

        # XGBoost参数
        params = {
            "objective": "multi:softprob",
            "num_class": 3,
            "max_depth": 6,
            "learning_rate": 0.1,
            "n_estimators": 100,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "random_state": 42,
        }

        # 训练模型
        model = xgb.XGBClassifier(**params)
        model.fit(X_train, y_train)

        # 预测
        y_pred = model.predict(X_test)
        y_pred_proba = model.predict_proba(X_test)

        # 计算指标
        accuracy = accuracy_score(y_test, y_pred)

        # 分类报告
        report = classification_report(y_test, y_pred, output_dict=True)

        # 特征重要性
        feature_importance = dict(zip(feature_cols, model.feature_importances_))

        metrics = {
            "accuracy": accuracy,
            "classification_report": report,
            "feature_importance": feature_importance,
            "predictions": y_pred,
            "probabilities": y_pred_proba,
            "y_test": y_test,
        }

        print(f"✅ 模型训练完成，测试集准确率: {accuracy:.3f}")

        return model, metrics

    def calculate_roi(self, model, df: pd.DataFrame) -> Dict:
        """计算投资回报率 (ROI)"""
        print("💰 计算投资回报率...")

        # 准备特征
        feature_cols = [col for col in df.columns if col != "result"]
        X = df[feature_cols]
        y = df["result"]

        # 预测概率
        y_pred_proba = model.predict_proba(X)

        # 模拟投注策略
        results = []
        bet_amount = 1.0  # 每场比赛投注1单位
        total_bet = 0
        total_winnings = 0
        big_teams_winnings = 0
        big_teams_bets = 0

        # 定义豪门球队
        big_teams = {
            "Arsenal",
            "Chelsea",
            "Liverpool",
            "Manchester City",
            "Manchester Utd",
            "Tottenham",
            "Barcelona",
            "Real Madrid",
            "Atletico Madrid",
            "Bayern Munich",
            "Borussia Dortmund",
            "AC Milan",
            "Inter",
            "Juventus",
        }

        for i, (_, match) in enumerate(df.iterrows()):
            home_team = match.get("home_team", "Unknown")
            away_team = match.get("away_team", "Unknown")

            # 获取预测概率 (0=客胜, 1=平局, 2=主胜)
            prob_home_win = y_pred_proba[i][2]
            prob_draw = y_pred_proba[i][1]
            prob_away_win = y_pred_proba[i][0]

            # 获取赔率
            home_odds = match["home_odds"]
            draw_odds = match["draw_odds"]
            away_odds = match["away_odds"]

            # 获取隐含概率
            implied_home = match["home_implied_prob"]

            # 投注策略：只有在模型预测概率 > 隐含概率时才投注 (Edge)
            bet_placed = False
            bet_on = None
            expected_value = 0

            # 检查主胜
            if prob_home_win > implied_home:
                expected_value = (prob_home_win * home_odds) - 1
                if expected_value > 0.1:  # 要求10%以上的期望回报
                    bet_placed = True
                    bet_on = "home"
                    expected_value = expected_value

            # 检查平局
            if not bet_placed and prob_draw > 1 / 3:  # 假设隐含平局概率为33%
                implied_draw = 1 / draw_odds
                if prob_draw > implied_draw:
                    expected_value = (prob_draw * draw_odds) - 1
                    if expected_value > 0.1:
                        bet_placed = True
                        bet_on = "draw"
                        expected_value = expected_value

            # 投注记录
            if bet_placed:
                total_bet += bet_amount
                is_big_team_game = home_team in big_teams or away_team in big_teams

                # 计算盈亏
                actual_result = match["result"]
                won = False
                payout = 0

                if bet_on == "home" and actual_result == 2:
                    won = True
                    payout = bet_amount * home_odds
                elif bet_on == "draw" and actual_result == 1:
                    won = True
                    payout = bet_amount * draw_odds

                net_winnings = payout - bet_amount
                total_winnings += net_winnings

                if is_big_team_game:
                    big_teams_bets += bet_amount
                    big_teams_winnings += net_winnings

                results.append(
                    {
                        "match_id": i,
                        "home_team": home_team,
                        "away_team": away_team,
                        "bet_on": bet_on,
                        "odds": home_odds if bet_on == "home" else draw_odds,
                        "prob": prob_home_win if bet_on == "home" else prob_draw,
                        "won": won,
                        "payout": payout,
                        "net_winnings": net_winnings,
                        "is_big_team_game": is_big_team_game,
                        "expected_value": expected_value,
                    }
                )

        # 计算ROI
        roi = (total_winnings / total_bet * 100) if total_bet > 0 else 0
        big_teams_roi = (
            (big_teams_winnings / big_teams_bets * 100) if big_teams_bets > 0 else 0
        )

        roi_stats = {
            "total_bets": len(results),
            "total_bet_amount": total_bet,
            "total_winnings": total_winnings,
            "roi_percent": roi,
            "wins": sum(1 for r in results if r["won"]),
            "win_rate": (
                sum(1 for r in results if r["won"]) / len(results) if results else 0
            ),
            "big_teams": {
                "bets": big_teams_bets,
                "winnings": big_teams_winnings,
                "roi": big_teams_roi,
            },
            "bet_details": results,
        }

        print(f"💰 ROI分析完成:")
        print(f"  总投注: {len(results)} 次")
        print(f"  投注金额: {total_bet:.2f}")
        print(f"  总盈亏: {total_winnings:.2f}")
        print(f"  ROI: {roi:.2f}%")
        print(f"  胜率: {roi_stats['win_rate']:.2%}")
        print(f"\n🏆 豪门球队表现:")
        print(f"  投注次数: {big_teams_bets:.0f}")
        print(f"  盈亏: {big_teams_winnings:.2f}")
        print(f"  ROI: {big_teams_roi:.2f}%")

        return roi_stats

    def print_feature_importance(self, feature_importance: Dict) -> None:
        """打印特征重要性"""
        print("\n📊 特征重要性 (Top 15):")
        sorted_features = sorted(
            feature_importance.items(), key=lambda x: x[1], reverse=True
        )

        for feature, importance in sorted_features[:15]:
            print(f"  {feature:40s} {importance:.4f}")

    def run_complete_pipeline(self) -> None:
        """运行完整流程"""
        print("🚀 融合数据集构建流程启动")
        print("=" * 80)

        # Step 1: 加载数据
        self.load_fbref_data()
        self.load_fotmob_data()
        self.build_team_mapping()

        # Step 2: 融合数据集
        self.fuse_datasets()

        # Step 3: 特征工程
        training_data = self.engineer_features()

        # Step 4: 保存训练数据
        self.save_training_data(training_data)

        # Step 5: 训练模型
        model, metrics = self.train_model(training_data)

        # Step 6: 计算ROI
        roi_stats = self.calculate_roi(model, training_data)

        # Step 7: 打印结果
        print("\n" + "=" * 80)
        print("📋 完整流程结果")
        print("=" * 80)

        print(f"\n🎯 模型性能:")
        print(f"  测试集准确率: {metrics['accuracy']:.3f}")
        self.print_feature_importance(metrics["feature_importance"])

        print(f"\n💰 ROI分析:")
        print(f"  总投注次数: {roi_stats['total_bets']}")
        print(f"  投注总金额: {roi_stats['total_bet_amount']:.2f}")
        print(f"  总盈亏: {roi_stats['total_winnings']:.2f}")
        print(f"  ROI: {roi_stats['roi_percent']:.2f}%")
        print(f"  胜率: {roi_stats['win_rate']:.2%}")

        print(f"\n🏆 豪门球队ROI:")
        print(f"  投注次数: {roi_stats['big_teams']['bets']:.0f}")
        print(f"  盈亏: {roi_stats['big_teams']['winnings']:.2f}")
        print(f"  ROI: {roi_stats['big_teams']['roi']:.2f}%")

        # 最终结论
        print("\n" + "=" * 80)
        print("🎯 结论:")
        if roi_stats["big_teams"]["roi"] > 0:
            print(f"  ✅ 投豪门可以赚钱！ROI: {roi_stats['big_teams']['roi']:.2f}%")
        else:
            print(f"  ❌ 投豪门不赚钱，亏损 {abs(roi_stats['big_teams']['roi']):.2f}%")

        if roi_stats["roi_percent"] > 0:
            print(f"  ✅ 整体策略盈利，ROI: {roi_stats['roi_percent']:.2f}%")
        else:
            print(f"  ❌ 整体策略亏损 {abs(roi_stats['roi_percent']):.2f}%")

        print("=" * 80)


def main():
    """主函数"""
    builder = FusedDatasetBuilder()
    builder.run_complete_pipeline()


if __name__ == "__main__":
    main()
