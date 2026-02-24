/**
 * V171.001 Quick Harvest - 快速收割脚本
 */

'use strict';

const path = require('path');
const PROJECT_ROOT = '/app';

async function harvest() {
    console.log('');
    console.log('═══════════════════════════════════════════════════════════════');
    console.log('  V171.001 实战收割 - 使用预设 URL');
    console.log('═══════════════════════════════════════════════════════════════');
    console.log('');

    const { QuantHarvester } = require(path.join(PROJECT_ROOT, 'src/infrastructure/engines/QuantHarvester'));
    const { Client } = require('pg');

    // 连接数据库
    const client = new Client({
        host: process.env.DB_HOST || 'db',
        database: 'football_db',
        user: 'football_user',
        password: process.env.DB_PASSWORD || 'your_secure_password_here'
    });
    await client.connect();

    // 获取有真实验证过 URL 的比赛
    const result = await client.query(`
        SELECT match_id, home_team, away_team, league_name, external_id as url
        FROM matches
        WHERE external_id LIKE '%CE2gREmB%' OR external_id LIKE '%KbUrxW1T%'
    `);

    const matches = result.rows;
    console.log('📋 找到 ' + matches.length + ' 场有 URL 的比赛');
    matches.forEach((m, i) => {
        console.log('   ' + (i+1) + '. ' + m.home_team + ' vs ' + m.away_team);
    });
    console.log('');

    if (matches.length === 0) {
        console.log('⚠️ 没有可收割的比赛');
        await client.end();
        return;
    }

    console.log('🚀 初始化 QuantHarvester...');
    const harvester = new QuantHarvester({
        enableProxy: true,
        enablePythonBridge: true,
        logLevel: 'error'
    });
    await harvester.init();

    const harvestData = matches.map(m => ({
        id: m.match_id,
        url: m.url,
        league_name: m.league_name
    }));

    console.log('');
    console.log('🎯 开始收割...');
    console.log('');

    const startTime = Date.now();
    const results = await harvester.harvestBatch(harvestData);
    const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);

    let success = 0;
    results.forEach(r => r.success && success++);

    console.log('');
    console.log('────────────────────────────────────────────────────────────');
    console.log('  成功: ' + success + '/' + matches.length + '  耗时: ' + elapsed + 's');
    console.log('────────────────────────────────────────────────────────────');
    console.log('');

    for (let i = 0; i < matches.length; i++) {
        const m = matches[i];
        const r = results[i];
        if (r.success) {
            await client.query("UPDATE matches SET status = 'completed', updated_at = NOW() WHERE match_id = $1", [m.match_id]);
            console.log('✅ ' + m.home_team + ' vs ' + m.away_team + ' → completed');
        } else {
            console.log('❌ ' + m.home_team + ' vs ' + m.away_team + ' → ' + (r.error || 'Failed'));
        }
    }

    await harvester.shutdown();
    await client.end();

    console.log('');
    console.log('═══════════════════════════════════════════════════════════════');
    console.log('  V171.001 收割完成');
    console.log('═══════════════════════════════════════════════════════════════');
}

harvest().catch(e => {
    console.error('Fatal:', e.message);
    process.exit(1);
});
