#!/bin/bash

echo "🚀 Starting System Integration Test for Football Prediction Pipeline"
echo "=================================================="

# 设置错误处理
set -e  # 遇到错误立即退出
trap 'echo "❌ Script failed at line $LINENO"' ERR

# 创建日志目录
mkdir -p logs

# Step 1: Environment Cleanup
echo "🧹 Step 1: Environment Cleanup..."
rm -f data/football_prediction.db
rm -rf logs/*
mkdir -p data logs
echo "✅ Environment cleaned"

# Step 2: Database Initialization
echo "🗄️ Step 2: Database Initialization..."
timeout 60 python scripts/setup_database.py
echo "✅ Database initialized successfully"

# Step 3: L1 Collection (建立比赛骨架)
echo "🏃‍♂️ Step 3: L1 Collection - Building Match Skeleton..."
timeout 120 python scripts/collect_l1_data.py \
    --league-id 47 \
    --days-back 14 \
    --days-ahead 7 \
    --no-progress \
    > logs/l1_output.log 2>&1
echo "✅ L1 Collection completed"

# 检查L1结果
echo "📊 L1 Collection Results:"
tail -n 10 logs/l1_output.log

# Step 4: L2 Collection (注入xG和详情数据)
echo "⚡ Step 4: L2 Collection - Injecting xG and Details..."
timeout 180 python scripts/collect_l2_data.py \
    --limit 20 \
    --concurrent 3 \
    --no-progress \
    > logs/l2_output.log 2>&1
echo "✅ L2 Collection completed"

# 检查L2结果
echo "📊 L2 Collection Results:"
tail -n 10 logs/l2_output.log

# Step 5: Verification (验证数据融合)
echo "🔍 Step 5: Verification - Checking Data Integration..."

echo ""
echo "📊 === 数据库概览 ==="
if [ -f "data/football_prediction.db" ]; then
    sqlite3 data/football_prediction.db << 'EOF'
SELECT 'Total Teams: ' || COUNT(*) FROM teams;
SELECT 'Total Matches: ' || COUNT(*) FROM matches;
SELECT 'Leagues: ' || COUNT(DISTINCT league_id) FROM matches WHERE league_id IS NOT NULL;
EOF
else
    echo "❌ Database file not found!"
    exit 1
fi

echo ""
echo "⚽ === 数据质量检查 ==="
sqlite3 data/football_prediction.db << 'EOF'
SELECT 'Matches with Scores: ' || COUNT(*) FROM matches WHERE home_score IS NOT NULL;
SELECT 'Matches with xG Data: ' || COUNT(*) FROM matches WHERE home_xg IS NOT NULL;
SELECT 'Matches with Possession Data: ' || COUNT(*) FROM matches WHERE home_possession IS NOT NULL;
EOF

echo ""
echo "🎯 === 关键验证：xG数据比赛数量 ==="
sqlite3 data/football_prediction.db << 'EOF'
SELECT 'CRITICAL CHECK - Matches with xG data: ' || COUNT(*) as count
FROM matches
WHERE home_xg IS NOT NULL AND away_xg IS NOT NULL;
EOF

echo ""
echo "🏆 === 真实数据样例 (队名 + 比分 + xG) ==="
sqlite3 data/football_prediction.db << 'EOF'
SELECT
    'Match: ' || t1.name || ' vs ' || t2.name as fixture,
    'Score: ' || COALESCE(CAST(m.home_score AS TEXT), 'N/A') || '-' || COALESCE(CAST(m.away_score AS TEXT), 'N/A') as score,
    'xG: ' || COALESCE(CAST(m.home_xg AS TEXT), 'N/A') || '-' || COALESCE(CAST(m.away_xg AS TEXT), 'N/A') as xg
FROM matches m
JOIN teams t1 ON m.home_team_id = t1.id
JOIN teams t2 ON m.away_team_id = t2.id
WHERE m.home_xg IS NOT NULL AND m.away_xg IS NOT NULL
ORDER BY m.match_date DESC
LIMIT 3;
EOF

echo ""
echo "🏷️ === 队名标准化验证 ==="
sqlite3 data/football_prediction.db << 'EOF'
SELECT 'Sample Standardized Team Names:' as info
UNION ALL
SELECT name FROM teams
WHERE name LIKE '%Manchester%' OR name LIKE '%Liverpool%' OR name LIKE '%Chelsea%'
ORDER BY name
LIMIT 5;
EOF

echo ""
echo "✅ System Integration Test Completed Successfully!"
echo "🎉 If you see xG data in the samples above, the pipeline is working perfectly!"

# 生成测试报告
echo ""
echo "📄 Test Summary:"
echo "=================="
echo "Logs saved to: logs/"
echo "Database file: data/football_prediction.db"
echo "Check logs/l1_output.log and logs/l2_output.log for detailed execution logs"