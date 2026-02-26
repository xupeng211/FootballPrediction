#!/usr/bin/env python3
"""
V171.000 Daily Bets Checker - 战果看板
=====================================

筛选高置信度预测，生成投注推荐。

Usage:
    python scripts/ops/check_daily_bets.py
"""

import os
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Any

# 确保项目根目录在路径中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import psycopg2
from psycopg2.extras import RealDictCursor


def get_connection():
    """获取数据库连接"""
    return psycopg2.connect(
        host=os.environ.get('DB_HOST', 'db'),
        port=int(os.environ.get('DB_PORT', 5432)),
        database=os.environ.get('DB_NAME', 'football_db'),
        user=os.environ.get('DB_USER', 'football_user'),
        password=os.environ.get('DB_PASSWORD', 'football_pass')
    )


def get_high_confidence_predictions(min_confidence: float = 0.75) -> List[Dict[str, Any]]:
    """
    获取高置信度预测

    Args:
        min_confidence: 最低置信度阈值

    Returns:
        预测列表
    """
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # 查询最近24小时的高置信度预测
        query = """
            SELECT
                p.match_id,
                p.predicted_result,
                p.final_confidence,
                p.model_version,
                p.confidence_home,
                p.confidence_draw,
                p.confidence_away,
                p.recommended_bet,
                p.prediction_date,
                m.home_team,
                m.away_team,
                m.league_name,
                m.match_date
            FROM predictions p
            JOIN matches m ON p.match_id = m.match_id
            WHERE p.final_confidence >= %s
              AND p.prediction_date >= NOW() - INTERVAL '24 hours'
            ORDER BY p.final_confidence DESC, p.prediction_date DESC
        """

        cur.execute(query, (min_confidence,))
        results = cur.fetchall()

        return [dict(row) for row in results]

    finally:
        cur.close()
        conn.close()


def classify_recommendation(confidence: float, model_version: str) -> str:
    """
    分类推荐级别

    Args:
        confidence: 置信度
        model_version: 模型版本

    Returns:
        推荐级别 (SSR/SR/R)
    """
    is_unanimous = 'UNA' in model_version.upper()

    if confidence >= 0.90 and is_unanimous:
        return 'SSR'  # Super Strong Recommendation
    elif confidence >= 0.80 and is_unanimous:
        return 'SR'   # Strong Recommendation
    elif confidence >= 0.75:
        return 'R'    # Recommendation
    else:
        return 'W'    # Watch


def format_prediction(pred: Dict[str, Any]) -> str:
    """格式化单条预测"""
    rec_level = classify_recommendation(
        pred['final_confidence'],
        pred['model_version']
    )

    # 预测方向
    direction_map = {
        'home': '主胜',
        'draw': '平局',
        'away': '客胜'
    }
    direction = direction_map.get(pred['predicted_result'].lower(), pred['predicted_result'])

    # 时间
    pred_time = pred['prediction_date'].strftime('%m-%d %H:%M')

    # 置信度
    conf_pct = pred['final_confidence'] * 100

    # 推荐级别样式
    rec_style = {
        'SSR': '🔥🔥🔥',
        'SR': '🔥🔥',
        'R': '🔥',
        'W': '👀'
    }.get(rec_level, '')

    return (
        f"[{pred_time}] {pred['home_team']} vs {pred['away_team']} | "
        f"{direction} | {conf_pct:.1f}% | {rec_level} {rec_style}"
    )


def print_dashboard(predictions: List[Dict[str, Any]]):
    """打印战果看板"""
    print('')
    print('╔════════════════════════════════════════════════════════════════════════════════╗')
    print('║              V171.000 Daily Bets Dashboard - 战果看板                         ║')
    print('╚════════════════════════════════════════════════════════════════════════════════╝')
    print('')

    if not predictions:
        print('⚠️  暂无高置信度预测 (≥75%)')
        print('')
        return

    # 分类统计
    ssr = [p for p in predictions if classify_recommendation(p['final_confidence'], p['model_version']) == 'SSR']
    sr = [p for p in predictions if classify_recommendation(p['final_confidence'], p['model_version']) == 'SR']
    r = [p for p in predictions if classify_recommendation(p['final_confidence'], p['model_version']) == 'R']

    # 统计摘要
    print('📊 统计摘要')
    print('─' * 80)
    print(f'   总预测数: {len(predictions)}')
    print(f'   SSR (≥90% + 全票): {len(ssr)} 场 🔥🔥🔥')
    print(f'   SR  (≥80% + 全票): {len(sr)} 场 🔥🔥')
    print(f'   R   (≥75%):        {len(r)} 场 🔥')
    print('')

    # 按联赛分组
    leagues = {}
    for pred in predictions:
        league = pred['league_name'] or 'Unknown'
        if league not in leagues:
            leagues[league] = []
        leagues[league].append(pred)

    # 打印详情
    print('📋 推荐详情')
    print('─' * 80)

    for league, preds in sorted(leagues.items(), key=lambda x: -len(x[1])):
        print(f'\n🏆 {league} ({len(preds)} 场)')

        for pred in preds:
            print(f'   {format_prediction(pred)}')

    # 顶部推荐
    if ssr:
        print('')
        print('╔════════════════════════════════════════════════════════════════════════════════╗')
        print('║                    🔥 TOP RECOMMENDATIONS (SSR) 🔥                            ║')
        print('╠════════════════════════════════════════════════════════════════════════════════╣')

        for pred in ssr[:5]:  # 最多显示5场
            print(f'║  {format_prediction(pred):<74} ║')

        print('╚════════════════════════════════════════════════════════════════════════════════╝')

    # 风险提示
    print('')
    print('⚠️  风险提示:')
    print('   - 预测仅供参考，不构成投资建议')
    print('   - 置信度基于历史数据，不代表未来结果')
    print('   - 请合理控制投注金额')
    print('')


def print_summary_stats():
    """打印总体统计"""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # 总预测数
        cur.execute("SELECT COUNT(*) as total FROM predictions")
        total = cur.fetchone()['total']

        # 最近24小时
        cur.execute("""
            SELECT COUNT(*) as total
            FROM predictions
            WHERE prediction_date >= NOW() - INTERVAL '24 hours'
        """)
        last_24h = cur.fetchone()['total']

        # 平均置信度
        cur.execute("""
            SELECT AVG(final_confidence) as avg_conf
            FROM predictions
            WHERE prediction_date >= NOW() - INTERVAL '24 hours'
        """)
        result = cur.fetchone()
        avg_conf = result['avg_conf'] if result['avg_conf'] else 0

        # 预测分布
        cur.execute("""
            SELECT predicted_result, COUNT(*) as count
            FROM predictions
            WHERE prediction_date >= NOW() - INTERVAL '24 hours'
            GROUP BY predicted_result
        """)
        distribution = cur.fetchall()

        print('📈 数据库统计')
        print('─' * 80)
        print(f'   总预测记录: {total}')
        print(f'   最近24小时: {last_24h}')
        print(f'   平均置信度: {avg_conf * 100:.1f}%')
        print('   预测分布:')
        for row in distribution:
            result = row['predicted_result']
            count = row['count']
            direction = {'home': '主胜', 'draw': '平局', 'away': '客胜'}.get(result.lower(), result)
            print(f'      {direction}: {count} 场')
        print('')

    finally:
        cur.close()
        conn.close()


def main():
    print('')
    print('正在查询数据库...')
    print('')

    # 打印总体统计
    print_summary_stats()

    # 获取高置信度预测
    predictions = get_high_confidence_predictions(min_confidence=0.75)

    # 打印看板
    print_dashboard(predictions)


if __name__ == '__main__':
    main()
