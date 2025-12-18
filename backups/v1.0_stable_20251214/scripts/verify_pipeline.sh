#!/bin/bash
set -e  # 遇到错误立即停止

echo "🔥 Starting Final Pipeline Verification..."

# 1. Clean & Init
echo "🧹 [1/4] Cleaning database..."
rm -f data/football_prediction.db
python scripts/setup_database.py > /dev/null 2>&1

# 2. Run L1 (Real Data)
echo "📅 [2/4] Running L1 (Schedule)..."
# 使用 fixed 版本，抓取最近 7 天到未来 3 天的数据
python scripts/collect_l1_data_fixed.py --days-back 7 --days-ahead 3 --no-progress

# 3. Run L2 (Real xG)
echo "⚽ [3/4] Running L2 (xG Details)..."
# 限制 10 场以节省时间
python scripts/collect_l2_data.py --limit 10 --no-progress

# 4. Run Odds (Demo Mode)
echo "💰 [4/4] Running Odds Integrator..."
# 使用 working 版本进行演示
python scripts/collect_odds_data_working.py --limit 10 --demo

# 5. Verify Data
echo "📊 === FINAL DATA CHECK ==="
sqlite3 data/football_prediction.db <<EOF
.mode column
.headers on
.width 20 20 8 15 30
SELECT
    t1.name as Home,
    t2.name as Away,
    m.home_score || '-' || m.away_score as Score,
    COALESCE(m.home_xg, 'N/A') || '-' || COALESCE(m.away_xg, 'N/A') as xG,
    COALESCE(m.home_win_odds, 'N/A') || '/' || COALESCE(m.draw_odds, 'N/A') || '/' || COALESCE(m.away_win_odds, 'N/A') as Odds
FROM matches m
JOIN teams t1 ON m.home_team_id = t1.id
JOIN teams t2 ON m.away_team_id = t2.id
WHERE m.home_win_odds IS NOT NULL
LIMIT 5;
EOF