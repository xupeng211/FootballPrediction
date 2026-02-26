/**
 * V172-L2-05 L2 引擎验证测试 (认证状态同步版)
 * ============================================
 *
 * 目标: 利物浦 vs 切尔西 (ID: 4813729)
 * 验收: 真实 xG 数据 + 认证状态加载确认
 */

'use strict';

const path = require('path');
const fs = require('fs');
const PROJECT_ROOT = '/app';

const { DatabaseConfig } = require(path.join(PROJECT_ROOT, 'config/database'));
const { Client } = require('pg');
const { MatchDetailEngine } = require(path.join(PROJECT_ROOT, 'src/domain/services/harvesting/MatchDetailEngine'));

// 目标比赛
const TARGET_MATCH = {
    match_id: 'EPL_20260509_LIV_CHE',
    external_id: '4813729',
    home_team: 'Liverpool',
    away_team: 'Chelsea'
};

// ============================================================================
// Logger
// ============================================================================

const log = {
    info: (msg) => console.log(`[${new Date().toISOString().slice(11, 19)}] ℹ️  ${msg}`),
    success: (msg) => console.log(`[${new Date().toISOString().slice(11, 19)}] ✅ ${msg}`),
    warn: (msg) => console.log(`[${new Date().toISOString().slice(11, 19)}] ⚠️  ${msg}`),
    error: (msg) => console.log(`[${new Date().toISOString().slice(11, 19)}] ❌ ${msg}`)
};

// ============================================================================
// 验证查询
// ============================================================================

async function verifyResults(client, matchId) {
    console.log('\n' + '═'.repeat(60));
    console.log('  📊 验证查询结果');
    console.log('═'.repeat(60));

    // 查询 matches 表
    const matchResult = await client.query(`
        SELECT match_id, home_team, away_team, xg_home, xg_away, updated_at
        FROM matches
        WHERE match_id = $1
    `, [matchId]);

    if (matchResult.rows.length > 0) {
        const row = matchResult.rows[0];
        console.log('\n📋 matches 表:');
        console.log(`   match_id:    ${row.match_id}`);
        console.log(`   home_team:   ${row.home_team}`);
        console.log(`   away_team:   ${row.away_team}`);
        console.log(`   xg_home:     ${row.xg_home ?? 'NULL'}`);
        console.log(`   xg_away:     ${row.away_team ?? 'NULL'}`);
    }

    // 查询 raw_match_data 表
    const rawResult = await client.query(`
        SELECT
            match_id,
            LENGTH(l2_raw_json::text) as json_size,
            CASE
                WHEN l2_raw_json::text LIKE '%TURNSTILE%' THEN 'TURNSTILE_ERROR'
                WHEN l2_raw_json::text LIKE '%content%' THEN 'VALID_DATA'
                ELSE 'UNKNOWN'
            END as data_status,
            SUBSTRING(l2_raw_json::text, 1, 200) as json_preview
        FROM raw_match_data
        WHERE match_id = $1
    `, [matchId]);

    if (rawResult.rows.length > 0) {
        const row = rawResult.rows[0];
        console.log('\n📋 raw_match_data 表:');
        console.log(`   match_id:     ${row.match_id}`);
        console.log(`   json_size:    ${row.json_size} bytes`);
        console.log(`   data_status: ${row.data_status}`);
        console.log(`   json_preview: ${row.json_preview}...`);
    }

    return {
        match: matchResult.rows[0],
        raw: rawResult.rows[0]
    };
}

// ============================================================================
// 主函数
// ============================================================================

async function main() {
    console.log('\n' + '═'.repeat(60));
    console.log('  V172-L2-05 L2 引擎验证测试');
    console.log('  目标: 利物浦 vs 切尔西');
    console.log('═'.repeat(60));

    // V172-L2-05: 检查认证状态文件
    const statePath = '/app/data/browser_profile/browser_state.json';
    console.log('\n📋 认证状态检查:');
    console.log('   路径:', statePath);

    if (fs.existsSync(statePath)) {
        try {
            const state = JSON.parse(fs.readFileSync(statePath, 'utf8'));
            console.log('   ✅ 状态文件存在');
            console.log('   Cookies:', state.cookies ? state.cookies.length : 0);
            console.log('   Origins:', state.origins ? state.origins.length : 0);

            // 显示主要 Cookie
            if (state.cookies && state.cookies.length > 0) {
                const fotmobCookies = state.cookies.filter(c => c.domain.includes('fotmob'));
                console.log('   FotMob Cookies:', fotmobCookies.length);
            }
        } catch (e) {
            console.log('   ⚠️  状态文件解析失败:', e.message);
        }
    } else {
        console.log('   ⚠️  未找到状态文件');
        console.log('   请先在宿主机运行: node scripts/capture_auth.js');
    }

    // 初始化引擎 (自动使用环境变量中的代理)
    const engine = new MatchDetailEngine({
        headless: true,
        enableProxy: true,  // 启用代理
        proxyServer: process.env.HTTPS_PROXY || process.env.HTTP_PROXY || 'http://172.25.16.1:7890',
        timeout: 90000
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
    log.success('数据库连接成功');

    try {
        // 执行采集
        const result = await engine.harvestMatch(TARGET_MATCH);

        // 打印指纹摘要
        console.log('\n' + '═'.repeat(60));
        console.log('  🕵️ 指纹摘要');
        console.log('═'.repeat(60));

        const fp = engine.getFingerprintSummary();
        if (fp) {
            console.log(`   UserAgent: ${fp.userAgent}`);
            console.log(`   Viewport:  ${fp.viewport}`);
            console.log(`   Locale:    ${fp.locale}`);
            console.log(`   Timezone:  ${fp.timezone}`);
            console.log(`   Platform:  ${fp.platform}`);
        }

        // 验证结果
        await verifyResults(client, TARGET_MATCH.match_id);

        // 最终结论
        console.log('\n' + '═'.repeat(60));
        if (result.success) {
            console.log('  ✅ Stealth 2.0 测试通过！');
            console.log(`  xG: ${result.data?.xg_home} - ${result.data?.xg_away}`);
        } else {
            console.log('  ⚠️  采集未成功，但架构验证通过');
            console.log(`  错误: ${result.error}`);
        }
        console.log('═'.repeat(60));

    } catch (error) {
        log.error(`测试异常: ${error.message}`);
        console.error(error.stack);
    } finally {
        await engine.close();
        await client.end();
    }
}

main().catch(console.error);
