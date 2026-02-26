/**
 * V172-L2-08 最终实战验证 - 曼联 vs 狼队
 * ========================================
 *
 * 目标: 历史比赛 xG 真实抓取
 * 技术: 会话镜像 (Session Mirroring)
 */

'use strict';

const path = require('path');
const fs = require('fs');
const PROJECT_ROOT = '/app';

const { DatabaseConfig } = require(path.join(PROJECT_ROOT, 'config/database'));
const { Client } = require('pg');
const { MatchDetailEngine } = require(path.join(PROJECT_ROOT, 'src/domain/services/harvesting/MatchDetailEngine'));

// 目标比赛 - 2025-12-30 曼联 vs 狼队 (历史比赛)
const TARGET_MATCH = {
    match_id: 'EPL_20251230_MAN_WOL',
    external_id: '4813561',
    home_team: 'Manchester United',
    away_team: 'Wolverhampton Wanderers',
    date: '2025-12-30'
};

// ============================================================================
// 主函数
// ============================================================================

async function main() {
    console.log('\n' + '═'.repeat(70));
    console.log('  V172-L2-08 最终实战验证');
    console.log('  目标: 曼联 vs 狼队 (2025-12-30)');
    console.log('═'.repeat(70));

    // 检查认证状态
    const statePath = '/app/data/browser_profile/browser_state.json';
    console.log('\n📋 Step 1: 认证状态检查');

    if (fs.existsSync(statePath)) {
        const state = JSON.parse(fs.readFileSync(statePath, 'utf8'));
        console.log('   ✅ 状态文件存在');
        console.log('   Cookies:', state.cookies ? state.cookies.length : 0);
        console.log('   路径:', statePath);
    } else {
        console.log('   ❌ 未找到状态文件');
        console.log('   请先运行: node scripts/inject_cookie.js "your_cookies"');
        process.exit(1);
    }

    // 初始化引擎
    console.log('\n🚀 Step 2: 初始化 L2 引擎');
    const engine = new MatchDetailEngine({
        headless: true,
        enableProxy: true,
        proxyServer: process.env.HTTPS_PROXY || process.env.HTTP_PROXY || 'http://172.25.16.1:7890',
        timeout: 120000
    });

    // 连接数据库
    const client = new Client({
        host: DatabaseConfig.host,
        port: DatabaseConfig.port,
        database: DatabaseConfig.database,
        user: DatabaseConfig.user,
        password: DatabaseConfig.password
    });

    await client.connect();
    console.log('   ✅ 数据库连接成功');

    try {
        // 执行采集
        console.log('\n📍 Step 3: 执行采集');
        const result = await engine.harvestMatch(TARGET_MATCH);

        // 打印指纹信息
        console.log('\n' + '─'.repeat(70));
        console.log('  🕵️ Step 4: 指纹信息');
        console.log('─'.repeat(70));

        const fp = engine.getFingerprintSummary();
        if (fp) {
            console.log(`   UserAgent: ${fp.userAgent}`);
            console.log(`   Viewport:  ${fp.viewport}`);
            console.log(`   Locale:    ${fp.locale}`);
            console.log(`   Timezone:  ${fp.timezone}`);

            // 检查 UA 是否带 Headless
            if (fp.userAgent.toLowerCase().includes('headless')) {
                console.log('   ❌ 警告: UA 包含 Headless 字样！');
            } else {
                console.log('   ✅ UA 检查通过 (无 Headless)');
            }
        }

        // 验证结果
        console.log('\n' + '─'.repeat(70));
        console.log('  📊 Step 5: 采集结果');
        console.log('─'.repeat(70));

        if (result.success) {
            console.log('\n   ✅ 采集成功!\n');
            console.log('   xG 数据:');
            console.log(`      主队 (曼联): ${result.data.xg_home}`);
            console.log(`      客队 (狼队): ${result.data.xg_away}`);
            console.log('');
            console.log('   控球率:');
            console.log(`      主队: ${result.data.possession_home ? result.data.possession_home + '%' : 'N/A'}`);
            console.log(`      客队: ${result.data.possession_away ? result.data.possession_away + '%' : 'N/A'}`);
            console.log('');
            console.log('   射门:');
            console.log(`      主队: ${result.data.shots_home || 'N/A'}`);
            console.log(`      客队: ${result.data.shots_away || 'N/A'}`);
            console.log('');
            console.log(`   原始数据大小: ${result.rawSize} bytes`);

            // 类型验证
            console.log('\n   🔍 类型验证:');
            const xgHomeType = typeof result.data.xg_home;
            const xgAwayType = typeof result.data.xg_away;

            if (xgHomeType === 'number' && xgAwayType === 'number') {
                console.log('   ✅ xG 值为数字类型');
                if (result.data.xg_home > 0 || result.data.xg_away > 0) {
                    console.log('   ✅ xG 值有效 (非零)');
                }
            } else {
                console.log(`   ⚠️  xG 类型异常: xg_home=${xgHomeType}, xg_away=${xgAwayType}`);
            }

        } else {
            console.log('\n   ❌ 采集失败');
            console.log(`   错误: ${result.error}`);
        }

        // 数据库验证
        console.log('\n' + '─'.repeat(70));
        console.log('  💾 Step 6: 数据库验证');
        console.log('─'.repeat(70));

        const dbResult = await client.query(`
            SELECT match_id, xg_home, xg_away, updated_at
            FROM matches
            WHERE match_id = $1
        `, [TARGET_MATCH.match_id]);

        if (dbResult.rows.length > 0) {
            const row = dbResult.rows[0];
            console.log(`   match_id:  ${row.match_id}`);
            console.log(`   xg_home:   ${row.xg_home}`);
            console.log(`   xg_away:   ${row.xg_away}`);
            console.log(`   updated:   ${row.updated_at}`);
        }

        // 查询原始 JSON
        const rawResult = await client.query(`
            SELECT match_id,
                   LENGTH(l2_raw_json::text) as json_size,
                   CASE
                       WHEN l2_raw_json::text LIKE '%TURNSTILE%' THEN 'TURNSTILE_ERROR'
                       WHEN l2_raw_json::text LIKE '%content%' THEN 'VALID_DATA'
                       ELSE 'UNKNOWN'
                   END as data_status
            FROM raw_match_data
            WHERE match_id = $1
        `, [TARGET_MATCH.match_id]);

        if (rawResult.rows.length > 0) {
            const row = rawResult.rows[0];
            console.log(`\n   raw_match_data:`);
            console.log(`   json_size:   ${row.json_size} bytes`);
            console.log(`   data_status: ${row.data_status}`);
        }

        // 最终结论
        console.log('\n' + '═'.repeat(70));
        if (result.success &&
            typeof result.data.xg_home === 'number' &&
            typeof result.data.xg_away === 'number') {
            console.log('  ✅ V172-L2-08 验证通过！');
            console.log('  🎯 真实 xG 数据已成功获取并存储');
            console.log(`  📊 曼联 xG: ${result.data.xg_home}, 狼队 xG: ${result.data.xg_away}`);
        } else {
            console.log('  ⚠️  V172-L2-08 验证未完全成功');
            console.log('  建议: 检查 Cookie 是否有效，或重新注入 Cookie');
        }
        console.log('═'.repeat(70));

    } catch (error) {
        console.error('\n❌ 测试异常:', error.message);
        console.error(error.stack);
    } finally {
        await engine.close();
        await client.end();
    }
}

main().catch(console.error);
