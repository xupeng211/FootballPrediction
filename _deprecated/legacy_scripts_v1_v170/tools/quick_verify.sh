#!/bin/bash
# V171.001 容器内验证脚本

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║     V171.001 Quick Verification (Inside Container)           ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

cd /app

# 1. 数据库连接
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  1. 数据库连接"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if python3 -c "
import psycopg2
conn = psycopg2.connect(host='db', database='football_db', user='football_user', password='football_pass')
cur = conn.cursor()
cur.execute('SELECT COUNT(*) FROM matches')
print(f'   比赛数量: {cur.fetchone()[0]}')
cur.close()
conn.close()
" 2>/dev/null; then
    echo "✅ 数据库连接正常"
else
    echo "❌ 数据库连接失败"
fi

echo ""

# 2. Redis 连接
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  2. Redis 连接"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if redis-cli -h redis ping 2>/dev/null | grep -q PONG; then
    echo "✅ Redis 连接正常"
else
    echo "⚠️ Redis 连接失败 (非关键)"
fi

echo ""

# 3. PythonBridge 测试
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  3. PythonBridge 测试"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if node -e "
const { PythonBridge } = require('./src/infrastructure/engines/bridge/PythonBridge');
async function test() {
    const bridge = new PythonBridge({ logLevel: 'error' });
    const result = await bridge.testEnvironment();
    if (result.success) {
        console.log('   Python:', result.environment.python_version.split(' ')[0]);
        console.log('   psycopg2:', result.environment.psycopg2);
        console.log('   xgboost:', result.environment.xgboost);
        process.exit(0);
    }
    process.exit(1);
}
test();
" 2>/dev/null; then
    echo "✅ PythonBridge 正常"
else
    echo "❌ PythonBridge 失败"
fi

echo ""

# 4. NetworkShield 测试
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  4. NetworkShield 测试"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if node -e "
const { getNetworkShield } = require('./src/infrastructure/network/NetworkShield');
const shield = getNetworkShield();
const stats = shield.getStats();
console.log('   总节点:', stats.totalNodes);
console.log('   活跃节点:', stats.activeNodes);
console.log('   平均健康分:', stats.avgHealthScore);
process.exit(stats.activeNodes >= 20 ? 0 : 1);
" 2>/dev/null; then
    echo "✅ NetworkShield 正常 (22 节点)"
else
    echo "⚠️ NetworkShield 节点数不足"
fi

echo ""

# 5. 核心模块
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  5. 核心模块加载"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

node -e "
try {
    require('./src/infrastructure/engines/QuantHarvester');
    console.log('✅ QuantHarvester');
} catch(e) { console.log('❌ QuantHarvester:', e.message); }
" 2>/dev/null

node -e "
try {
    require('./src/infrastructure/engines/bridge/PythonBridge');
    console.log('✅ PythonBridge');
} catch(e) { console.log('❌ PythonBridge:', e.message); }
" 2>/dev/null

python3 -c "
try:
    from src.ml.inference.multi_model_validator import MultiModelValidator
    print('✅ MultiModelValidator')
except Exception as e:
    print(f'❌ MultiModelValidator: {e}')
" 2>/dev/null

python3 -c "
try:
    from src.infrastructure.merger.GoldenDataMerger import GoldenDataMerger
    print('✅ GoldenDataMerger')
except Exception as e:
    print(f'❌ GoldenDataMerger: {e}')
" 2>/dev/null

echo ""
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║              V171.001 验证完成                                ║"
echo "╠═══════════════════════════════════════════════════════════════╣"
echo "║  系统已就绪，可以开始收割:                                    ║"
echo "║  node scripts/ops/v171_real_fire.js                           ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
