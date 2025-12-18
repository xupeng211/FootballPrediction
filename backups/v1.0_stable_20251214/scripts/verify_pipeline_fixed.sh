#!/bin/bash
set -e  # 遇到错误立即停止

echo "🔥 Starting Final Pipeline Verification (Fixed)..."

# 1. Clean & Init
echo "🧹 [1/5] Cleaning database..."
rm -f data/football_prediction.db
python scripts/setup_database.py > /dev/null 2>&1

# 2. Run L1 (Real Data) - 扩大时间范围
echo "📅 [2/5] Running L1 (Schedule) - Extended Range..."
# 扩大时间范围：过去60天到未来30天，确保有数据
python scripts/collect_l1_data_fixed.py --days-back 60 --days-ahead 30 --no-progress

# 3. Add Manual xG Data (Simple L2)
echo "⚽ [3/5] Adding L2 (xG Details) - Simple Version..."
# 使用简化的xG数据添加脚本
python scripts/simple_l2_test.py > /dev/null 2>&1

# 4. Run Odds (Demo Mode)
echo "💰 [4/5] Running Odds Integrator..."
# 使用 working 版本进行演示
python scripts/collect_odds_data_working.py --limit 15 --demo

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
    COALESCE(CAST(m.home_xg AS TEXT), 'N/A') || '-' || COALESCE(CAST(m.away_xg AS TEXT), 'N/A') as xG,
    COALESCE(CAST(m.home_win_odds AS TEXT), 'N/A') || '/' || COALESCE(CAST(m.draw_odds AS TEXT), 'N/A') || '/' || COALESCE(CAST(m.away_win_odds AS TEXT), 'N/A') as Odds
FROM matches m
JOIN teams t1 ON m.home_team_id = t1.id
JOIN teams t2 ON m.away_team_id = t2.id
WHERE m.home_win_odds IS NOT NULL
LIMIT 8;

echo ""
echo "📈 === DATA COMPLETENESS STATISTICS ==="
SELECT
    COUNT(*) as Total_Matches,
    COUNT(CASE WHEN fotmob_id IS NOT NULL THEN 1 END) as With_FotMob_ID,
    COUNT(CASE WHEN home_xg IS NOT NULL THEN 1 END) as With_xG_Data,
    COUNT(CASE WHEN home_win_odds IS NOT NULL THEN 1 END) as With_Odds_Data,
    COUNT(CASE WHEN home_xg IS NOT NULL AND home_win_odds IS NOT NULL THEN 1 END) as With_xG_And_Odds
FROM matches;
EOF

echo ""
echo "✅ Pipeline Verification Complete!"