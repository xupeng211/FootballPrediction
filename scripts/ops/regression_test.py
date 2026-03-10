#!/usr/bin/env python3
# ═══════════════════════════════════════════════════════════════════════════════
# ║   TITAN V4.46.7 回归测试守卫                                                 ║
# ║   Third Line of Defense - Backtest Guard                                     ║
# ═══════════════════════════════════════════════════════════════════════════════
#
# 确保每次代码变更后，44.86% 的认证胜率不发生负向漂移
# 通过准则: 准确率偏差 <= 1%
#
# @module scripts.ops.regression_test
# @version V4.46.7
# ═══════════════════════════════════════════════════════════════════════════════

import argparse
import json
import math
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import joblib
import numpy as np
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor

# ============================================================================
# 配置
# ============================================================================

MODEL_DIR = Path(__file__).parent.parent.parent / "models"
BASELINE_ACCURACY = 0.4486  # 44.86% 认证胜率
ACCURACY_TOLERANCE = 0.01   # 1% 容差

FEATURES = [
    "home_elo_pre", "away_elo_pre", "elo_diff", "expected_home_win", "expected_away_win",
    "log_home_squad_value", "log_away_squad_value", "home_mv_share",
    "h2h_home_win_ratio", "h2h_draw_ratio", "h2h_avg_goal_diff",
]

DEFAULT_VALUES = {
    "home_elo_pre": 1500.0, "away_elo_pre": 1500.0, "elo_diff": 0.0,
    "expected_home_win": 0.45, "expected_away_win": 0.30,
    "log_home_squad_value": 18.0, "log_away_squad_value": 18.0, "home_mv_share": 0.50,
    "h2h_home_win_ratio": 0.40, "h2h_draw_ratio": 0.25, "h2h_avg_goal_diff": 0.0,
}

# ============================================================================
# 工具函数
# ============================================================================

def get_db_connection():
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'host.docker.internal'),
        port=int(os.getenv('DB_PORT', 5432)),
        database=os.getenv('DB_NAME', 'football_db'),
        user=os.getenv('DB_USER', 'football_user'),
        password=os.getenv('DB_PASSWORD', 'football_pass'),
        cursor_factory=RealDictCursor
    )

def safe_float(v, d=0.0):
    try: return float(v) if v is not None else d
    except: return d

def safe_log10(v, d=18.0):
    try: return math.log10(v) if v and v > 0 else d
    except: return d

def parse_jsonb(d):
    if not d: return {}
    if isinstance(d, str):
        try: return json.loads(d)
        except: return {}
    return d if isinstance(d, dict) else {}

# ============================================================================
# 回归测试
# ============================================================================

class RegressionTest:
    """回归测试执行器"""

    def __init__(self):
        self.model = None
        self.scaler = None
        self.conn = None

    def load_model(self) -> bool:
        """加载模型"""
        model_path = MODEL_DIR / "titan_v4466_real_combat.joblib"
        scaler_path = MODEL_DIR / "titan_v4466_real_combat_scaler.joblib"

        if not model_path.exists():
            print(f"❌ 模型文件不存在: {model_path}")
            return False

        try:
            self.model = joblib.load(str(model_path))
            if scaler_path.exists():
                self.scaler = joblib.load(str(scaler_path))
            print(f"✅ 模型加载成功: {model_path.name}")
            return True
        except Exception as e:
            print(f"❌ 模型加载失败: {e}")
            return False

    def load_test_data(self) -> List[Dict]:
        """加载测试集 (2026年已完赛)"""
        self.conn = get_db_connection()
        cur = self.conn.cursor()

        cur.execute("""
            SELECT m.match_id, m.home_team, m.away_team, m.actual_result,
                   m.league_name, m.match_date,
                   l.elo_features, l.lineup_features, l.h2h_features
            FROM matches m
            INNER JOIN l3_features l ON m.match_id = l.match_id
            WHERE m.status = 'finished'
              AND m.actual_result IN ('H', 'D', 'A')
              AND m.match_date >= '2026-01-01'
              AND l.elo_features IS NOT NULL
              AND l.elo_features != '{}'::jsonb
            ORDER BY m.match_date ASC
        """)

        rows = cur.fetchall()
        cur.close()
        print(f"✅ 测试集加载: {len(rows)} 场 (2026年已完赛)")
        return rows

    def extract_features(self, row: Dict) -> List[float]:
        """提取特征"""
        elo = parse_jsonb(row['elo_features'])
        lineup = parse_jsonb(row['lineup_features'])
        h2h = parse_jsonb(row['h2h_features'])

        f = {}

        # Elo
        home_elo = safe_float(elo.get('home_elo_pre', elo.get('home_elo', 1500)), 1500)
        away_elo = safe_float(elo.get('away_elo_pre', elo.get('away_elo', 1500)), 1500)
        f['home_elo_pre'] = home_elo
        f['away_elo_pre'] = away_elo
        f['elo_diff'] = safe_float(elo.get('elo_diff', home_elo - away_elo))
        f['expected_home_win'] = safe_float(elo.get('expected_home_win', 0.45))
        f['expected_away_win'] = safe_float(elo.get('expected_away_win', 0.30))

        # 身价
        home_mv = safe_float(lineup.get('home_squad_value_eur', 0), 0)
        away_mv = safe_float(lineup.get('away_squad_value_eur', 0), 0)
        f['log_home_squad_value'] = safe_log10(home_mv, 18.0) if home_mv > 0 else 18.0
        f['log_away_squad_value'] = safe_log10(away_mv, 18.0) if away_mv > 0 else 18.0
        total_mv = home_mv + away_mv
        f['home_mv_share'] = home_mv / total_mv if total_mv > 0 else 0.5

        # H2H
        f['h2h_home_win_ratio'] = safe_float(h2h.get('h2h_home_win_ratio', h2h.get('home_win_ratio', 0.4)), 0.4)
        f['h2h_draw_ratio'] = safe_float(h2h.get('h2h_draw_ratio', h2h.get('draw_ratio', 0.25)), 0.25)
        f['h2h_avg_goal_diff'] = safe_float(h2h.get('h2h_avg_goal_diff', h2h.get('avg_goal_diff', 0)), 0)

        return [f.get(n, DEFAULT_VALUES.get(n, 0.0)) for n in FEATURES]

    def run_test(self) -> Tuple[float, Dict]:
        """运行回归测试"""
        if not self.load_model():
            return 0.0, {'error': 'Model load failed'}

        test_data = self.load_test_data()
        if not test_data:
            return 0.0, {'error': 'No test data'}

        correct = 0
        total = 0
        results_by_league = {}

        for row in test_data:
            try:
                features = self.extract_features(row)
                X = pd.DataFrame([features], columns=FEATURES)

                if self.scaler:
                    X = self.scaler.transform(X)

                probs = self.model.predict_proba(X)[0]
                pred = np.argmax(probs)  # 0=AWAY, 1=DRAW, 2=HOME

                actual_map = {'A': 0, 'D': 1, 'H': 2}
                actual = actual_map.get(row['actual_result'], -1)

                if pred == actual:
                    correct += 1
                total += 1

                # 按联赛统计
                league = row['league_name'] or 'Unknown'
                if league not in results_by_league:
                    results_by_league[league] = {'correct': 0, 'total': 0}
                results_by_league[league]['total'] += 1
                if pred == actual:
                    results_by_league[league]['correct'] += 1

            except Exception as e:
                print(f"  ⚠️ 跳过 {row['match_id']}: {e}")
                continue

        accuracy = correct / total if total > 0 else 0

        stats = {
            'correct': correct,
            'total': total,
            'accuracy': accuracy,
            'baseline': BASELINE_ACCURACY,
            'deviation': accuracy - BASELINE_ACCURACY,
            'by_league': results_by_league
        }

        if self.conn:
            self.conn.close()

        return accuracy, stats

    def print_report(self, accuracy: float, stats: Dict):
        """打印报告"""
        print("\n" + "=" * 70)
        print("  🛡️ TITAN V4.46.7 回归测试报告")
        print("=" * 70)

        if 'error' in stats:
            print(f"  ❌ 错误: {stats['error']}")
            return False

        deviation = stats['deviation']
        passed = abs(deviation) <= ACCURACY_TOLERANCE

        print(f"\n  📊 测试结果:")
        print(f"     样本数:    {stats['total']} 场")
        print(f"     正确数:    {stats['correct']} 场")
        print(f"     准确率:    {accuracy:.4f} ({accuracy*100:.2f}%)")
        print(f"     基线:      {BASELINE_ACCURACY:.4f} ({BASELINE_ACCURACY*100:.2f}%)")
        print(f"     偏差:      {deviation:+.4f} ({deviation*100:+.2f}%)")

        print(f"\n  📋 按联赛统计:")
        for league, data in sorted(stats['by_league'].items(), key=lambda x: x[1]['total'], reverse=True)[:5]:
            league_acc = data['correct'] / data['total'] if data['total'] > 0 else 0
            print(f"     {league:<20}: {data['correct']}/{data['total']} ({league_acc:.1%})")

        print("\n" + "─" * 70)

        if passed:
            print(f"  ✅ 测试通过! 偏差 {deviation*100:+.2f}% 在容差 ±{ACCURACY_TOLERANCE*100}% 内")
        else:
            print(f"  ❌ 测试失败! 偏差 {deviation*100:+.2f}% 超出容差 ±{ACCURACY_TOLERANCE*100}%")
            print(f"     模型可能已退化，请检查代码变更!")

        print("=" * 70)

        return passed


def main():
    parser = argparse.ArgumentParser(description='TITAN 回归测试守卫')
    parser.add_argument('--json', action='store_true', help='JSON 输出')
    parser.add_argument('--strict', action='store_true', help='严格模式 (失败时退出码非零)')
    args = parser.parse_args()

    tester = RegressionTest()
    accuracy, stats = tester.run_test()
    passed = tester.print_report(accuracy, stats)

    if args.json:
        output = {
            'timestamp': datetime.now().isoformat(),
            'passed': passed,
            'accuracy': accuracy,
            'baseline': BASELINE_ACCURACY,
            'deviation': stats.get('deviation', 0),
            'stats': stats
        }
        print(json.dumps(output, indent=2, ensure_ascii=False))

    # 返回码
    if passed or not args.strict:
        return 0
    return 1


if __name__ == '__main__':
    sys.exit(main())
