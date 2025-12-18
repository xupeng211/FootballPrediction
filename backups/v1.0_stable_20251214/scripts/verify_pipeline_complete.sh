#!/bin/bash
set -e  # 遇到错误立即停止

echo "🔥 Starting Final Pipeline Verification (Complete)..."

# 1. Clean & Init
echo "🧹 [1/6] Cleaning database..."
rm -f data/football_prediction.db
python scripts/setup_database.py > /dev/null 2>&1

# 2. Add Odds Fields to Database Schema
echo "🏗️ [2/6] Adding odds fields to database..."
sqlite3 data/football_prediction.db "ALTER TABLE matches ADD COLUMN home_win_odds REAL; ALTER TABLE matches ADD COLUMN draw_odds REAL; ALTER TABLE matches ADD COLUMN away_win_odds REAL;" > /dev/null 2>&1 || echo "Odds fields already exist"

# 3. Run L1 (Real Data) - 扩大时间范围
echo "📅 [3/6] Running L1 (Schedule) - Extended Range..."
# 使用固定值进行测试，先尝试获取一些最近的历史数据
python scripts/collect_l1_data_fixed.py --days-back 365 --days-ahead 365 --no-progress

# 4. Add Manual xG Data (Simple L2)
echo "⚽ [4/6] Adding L2 (xG Details) - Simple Version..."
# 使用简化的xG数据添加脚本
python scripts/simple_l2_test.py > /dev/null 2>&1

# 5. Run Odds (Demo Mode)
echo "💰 [5/6] Running Odds Integrator..."
# 使用 working 版本进行演示
python scripts/collect_odds_data_working.py --limit 10 --demo

# 6. Verify Data
echo "📊 === FINAL DATA CHECK ==="
sqlite3 data/football_prediction.db <<EOF
.mode column
.headers on
.width 20 20 8 15 35
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
ORDER BY m.id DESC
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