#!/usr/bin/env python3
"""
V200 西甲实战预测脚本
=====================

使用 Elo + 身价 + 伤病进行预测

特征来源:
- team_elo_ratings: 球队最新 Elo 评分
- l3_features.golden_features: 身价、伤病等基本面

用法:
    docker-compose -f docker-compose.dev.yml exec dev python scripts/ops/predict_laliga.py
"""

import sys
import os
import json
from datetime import datetime

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

import psycopg2


def safe_float(val, default=0.0):
    """安全提取浮点数"""
    try:
        return float(val) if val is not None else default
    except:
        return default


def get_db_connection():
    """获取数据库连接"""
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'db'),
        port=int(os.getenv('DB_PORT', 5432)),
        database=os.getenv('DB_NAME', 'football_db'),
        user=os.getenv('DB_USER', 'football_user'),
        password=os.getenv('DB_PASSWORD', '')
    )


def format_value(value: float) -> str:
    """格式化身价数值"""
    if abs(value) >= 1e9:
        return f"{value/1e9:.2f}亿"
    elif abs(value) >= 1e6:
        return f"{value/1e6:.0f}万"
    else:
        return f"{value:.0f}"


class LaligaPredictor:
    """V200 西甲预测器"""

    HOME_ADVANTAGE_ELO = 50

    def __init__(self):
        self.conn = None
        self.elo_cache = {}

    def init(self):
        """初始化"""
        self.conn = get_db_connection()
        self._load_elo_ratings()

    def close(self):
        """关闭连接"""
        if self.conn:
            self.conn.close()

    def _load_elo_ratings(self):
        """加载 Elo 评分"""
        cur = self.conn.cursor()
        cur.execute("SELECT team_name, elo_rating FROM team_elo_ratings")
        for row in cur.fetchall():
            self.elo_cache[row[0]] = float(row[1])

    def _get_elo(self, team_name: str) -> float:
        """获取球队 Elo"""
        return self.elo_cache.get(team_name, 1500.0)

    def _elo_expected(self, home_elo: float, away_elo: float) -> dict:
        """计算 Elo 期望概率"""
        effective_home_elo = home_elo + self.HOME_ADVANTAGE_ELO
        home_expected = 1 / (1 + 10 ** ((away_elo - effective_home_elo) / 400))

        elo_diff = abs(home_elo - away_elo)
        draw_prob = 0.28 - min(0.08, elo_diff / 2000)

        remaining = 1 - draw_prob
        away_prob = remaining * (1 - home_expected)
        home_prob = remaining * home_expected

        return {'home': home_prob, 'draw': draw_prob, 'away': away_prob}

    def predict_match(self, match_id: str) -> dict:
        """预测单场比赛"""
        cur = self.conn.cursor()

        # 获取比赛信息
        cur.execute("""
            SELECT m.home_team, m.away_team, m.match_date, m.league_name,
                   l3.golden_features
            FROM matches m
            LEFT JOIN l3_features l3 ON m.match_id = l3.match_id
            WHERE m.match_id = %s
        """, (match_id,))

        row = cur.fetchone()
        if not row:
            return None

        home_team, away_team, match_date, league, golden = row
        golden = golden or {}

        # Elo
        home_elo = self._get_elo(home_team)
        away_elo = self._get_elo(away_team)
        probs = self._elo_expected(home_elo, away_elo)

        # 身价调整
        mv_gap = safe_float(golden.get('market_value_gap', 0))
        mv_effect = (mv_gap / 1e8) * 0.02
        probs['home'] = max(0.05, min(0.85, probs['home'] + mv_effect))
        probs['away'] = max(0.05, min(0.85, probs['away'] - mv_effect))

        # 伤病调整
        injury_gap = int(golden.get('injury_count_gap', 0) or 0)
        injury_effect = injury_gap * 0.005
        probs['home'] = max(0.05, min(0.85, probs['home'] - injury_effect))
        probs['away'] = max(0.05, min(0.85, probs['away'] + injury_effect))

        # 预测结果
        prediction = max(probs, key=probs.get)
        confidence = probs[prediction]

        return {
            'match_id': match_id,
            'home_team': home_team,
            'away_team': away_team,
            'match_date': match_date,
            'home_elo': home_elo,
            'away_elo': away_elo,
            'probs': probs,
            'prediction': prediction,
            'confidence': confidence,
            'mv_gap': mv_gap,
            'injury_gap': injury_gap
        }

    def run(self):
        """执行预测"""
        print("\n" + "=" * 80)
        print("   V200 西甲焦点战预测报告")
        print("   基于 Elo + 身价 + 伤病")
        print("=" * 80)

        # 比赛列表
        matches = [
            ('87_20242025_4837372', 'Celta Vigo vs Real Madrid'),
            ('87_20242025_4837370', 'Athletic Club vs Barcelona')
        ]

        for match_id, match_name in matches:
            pred = self.predict_match(match_id)
            if not pred:
                print(f"\n   错误: 未找到 {match_name} 的数据")
                continue

            print(f"\n{'=' * 80}")
            print(f"   {match_name}")
            print(f"   时间: {pred['match_date'].strftime('%Y-%m-%d %H:%M')}")
            print("-" * 40)

            # Elo 分析
            print(f"\n   【Elo 战力评分】")
            print(f"   主队 {pred['home_team']}: {pred['home_elo']:.1f}")
            print(f"   客队 {pred['away_team']}: {pred['away_elo']:.1f}")
            print(f"   差距: {pred['home_elo'] - pred['away_elo']:+.1f}")

            # 基本面
            print(f"\n   【基本面】")
            print(f"   身价差距: {format_value(pred['mv_gap'])}")
            print(f"   伤病差距: {pred['injury_gap']:+d}")

            # 预测
            print(f"\n   【预测结果】")
            pred_cn = {'home': '主胜', 'draw': '平局', 'away': '客胜'}
            print(f"   预测: {pred_cn[pred['prediction']]}")
            print(f"   置信度: {pred['confidence']:.1%}")
            print(f"   概率: 主 {pred['probs']['home']:.1%} | 平 {pred['probs']['draw']:.1%} | 客 {pred['probs']['away']:.1%}")

            # EV 计算（假设市场赔率）
            sim_odds = self._simulate_odds(pred['probs'])
            ev = {
                'home': pred['probs']['home'] * sim_odds['home'] - 1,
                'draw': pred['probs']['draw'] * sim_odds['draw'] - 1,
                'away': pred['probs']['away'] * sim_odds['away'] - 1
            }
            best_ev = max(ev.values())
            best_outcome = max(ev, key=ev.get)

            print(f"\n   【投注建议】")
            if best_ev > 0.05:
                outcome_cn = {'home': f'主胜 ({pred["home_team"]})', 'draw': '平局', 'away': f'客胜 ({pred["away_team"]})'}
                print(f"   建议: {outcome_cn[best_outcome]} @ {sim_odds[best_outcome]:.2f}")
                print(f"   期望值: {best_ev:+.1%}")
            else:
                print(f"   无明显价值投注")

        print(f"\n{'=' * 80}")
        print("   报告完成")
        print("=" * 80 + "\n")

    def _simulate_odds(self, probs: dict) -> dict:
        """模拟市场赔率"""
        vig = 0.05
        return {
            'home': 1 / (probs['home'] * (1 + vig)) if probs['home'] > 0 else 10,
            'draw': 1 / (probs['draw'] * (1 + vig)) if probs['draw'] > 0 else 10,
            'away': 1 / (probs['away'] * (1 + vig)) if probs['away'] > 0 else 10
        }


def run_prediction():
    """执行预测"""
    predictor = LaligaPredictor()
    try:
        predictor.init()
        predictor.run()
    finally:
        predictor.close()


if __name__ == "__main__":
    run_prediction()
