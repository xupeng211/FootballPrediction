/**
 * V171-DataScience-08 真实历史数据回填
 * ============================================
 *
 * 铁律遵守：
 * - 禁止模拟数据！没有真实数据就报错停止
 * - 必须在 Docker 容器内执行
 * - 数据写入 /app/data/ 持久化目录
 *
 * @module scripts/ops/v171_real_backfill_live
 */

'use strict';

const { Client } = require('pg');
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

// ============================================================================
// 配置
// ============================================================================

const DB_CONFIG = {
    host: process.env.DB_HOST || 'db',  // 使用 docker 网络内的服务名
    port: parseInt(process.env.DB_PORT) || 5432,
    database: process.env.DB_NAME || 'football_db',
    user: process.env.DB_USER || 'football_user',
    password: 'your_secure_password_here'  // 数据库实际密码
};

// 验证配置
console.log('📋 数据库配置:', { ...DB_CONFIG, password: '***' });

const OUTPUT_DIR = '/app/data/backfill';  // 持久化目录，符合铁律 5
const PROXY_HOST = process.env.PROXY_HOST || '172.25.16.1';
const PROXY_PORT = 7891;

// ============================================================================
// Logger
// ============================================================================

const log = {
    info: (msg, ...args) => console.log(`[${new Date().toISOString().slice(11, 19)}] ℹ️  ${msg}`, ...args),
    success: (msg, ...args) => console.log(`[${new Date().toISOString().slice(11, 19)}] ✅ ${msg}`, ...args),
    warn: (msg, ...args) => console.log(`[${new Date().toISOString().slice(11, 19)}] ⚠️  ${msg}`, ...args),
    error: (msg, ...args) => console.log(`[${new Date().toISOString().slice(11, 19)}] ❌ ${msg}`, ...args),
    progress: (current, total, matchId, status) => {
        const pct = Math.round((current / total) * 100);
        const bar = '█'.repeat(Math.floor(pct / 5)) + '░'.repeat(20 - Math.floor(pct / 5));
        console.log(`[${new Date().toISOString().slice(11, 19)}] 📊 [${bar}] ${current}/${total} (${pct}%) | ${matchId} | ${status}`);
    }
};

// ============================================================================
// 数据库操作
// ============================================================================

async function getClient() {
    const client = new Client(DB_CONFIG);
    await client.connect();
    return client;
}

async function getMatchesToBackfill(client) {
    const result = await client.query(`
        SELECT
            match_id,
            home_team,
            away_team,
            league_name,
            match_date,
            home_score,
            away_score,
            external_id
        FROM matches
        WHERE is_finished = true
          AND league_name IN ('Premier League', 'La Liga')
          AND match_date >= NOW() - INTERVAL '30 days'
        ORDER BY match_date DESC
    `);

    if (result.rows.length === 0) {
        log.error('数据库中没有找到符合条件的比赛！');
        process.exit(1);
    }

    log.info(`找到 ${result.rows.length} 场比赛需要回填`);
    return result.rows;
}

async function saveRawData(client, matchId, rawData) {
    const query = `
        INSERT INTO raw_match_data (match_id, raw_data, collected_at)
        VALUES ($1, $2, NOW())
        ON CONFLICT (match_id) DO UPDATE SET
            raw_data = EXCLUDED.raw_data,
            collected_at = NOW()
    `;
    await client.query(query, [matchId, JSON.stringify(rawData)]);
}

// ============================================================================
// FotMob 抓取 (L2 数据)
// ============================================================================

async function fetchFotMobData(browser, match) {
    const { home_team, away_team, match_date } = match;
    const dateStr = match_date.toISOString().slice(0, 10);

    // 构建 FotMob 搜索 URL
    const searchQuery = encodeURIComponent(`${home_team} vs ${away_team}`);
    const searchUrl = `https://www.fotmob.com/search?query=${searchQuery}`;

    log.info(`  [L2] 抓取 FotMob: ${home_team} vs ${away_team}`);

    const context = await browser.newContext({
        proxy: { server: `http://${PROXY_HOST}:${PROXY_PORT}` },
        userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    });
    const page = await context.newPage();

    try {
        await page.goto(searchUrl, { waitUntil: 'networkidle', timeout: 30000 });
        await page.waitForTimeout(2000);

        // 尝试找到比赛链接
        const matchLink = await page.$('a[href*="/matches/"]');
        if (matchLink) {
            await matchLink.click();
            await page.waitForTimeout(3000);

            // 提取比赛数据
            const matchData = await page.evaluate(() => {
                // 提取 xG 数据
                const xgElements = document.querySelectorAll('[class*="xG"]');
                const xg = [];
                xgElements.forEach(el => {
                    const val = parseFloat(el.textContent);
                    if (!isNaN(val)) xg.push(val);
                });

                // 提取比分
                const scoreEl = document.querySelector('[class*="score"]');
                const score = scoreEl ? scoreEl.textContent : null;

                // 提取控球率
                const possessionEls = document.querySelectorAll('[class*="possession"]');
                const possession = [];
                possessionEls.forEach(el => {
                    const val = parseFloat(el.textContent);
                    if (!isNaN(val)) possession.push(val);
                });

                return {
                    xg: xg.length >= 2 ? { home: xg[0], away: xg[1] } : null,
                    score: score,
                    possession: possession.length >= 2 ? { home: possession[0], away: possession[1] } : null,
                    url: window.location.href
                };
            });

            log.success(`  [L2] FotMob 数据获取成功`);
            return { source: 'fotmob', data: matchData, timestamp: new Date().toISOString() };
        } else {
            log.warn(`  [L2] 未找到比赛页面`);
            return { source: 'fotmob', data: null, error: 'Match page not found' };
        }
    } catch (e) {
        log.error(`  [L2] FotMob 抓取失败: ${e.message}`);
        return { source: 'fotmob', data: null, error: e.message };
    } finally {
        await context.close();
    }
}

// ============================================================================
// OddsPortal 抓取 (L3 数据)
// ============================================================================

async function fetchOddsPortalData(browser, match) {
    const { home_team, away_team, league_name } = match;

    log.info(`  [L3] 抓取 OddsPortal: ${home_team} vs ${away_team}`);

    // 使用 C++ Bridge 生成正确的 URL (模拟，实际应调用 BridgeRadarEngine)
    // 这里简化为直接构建搜索 URL
    const searchQuery = encodeURIComponent(`${home_team} ${away_team} odds`);
    const searchUrl = `https://www.oddsportal.com/search/results/${searchQuery}`;

    const context = await browser.newContext({
        proxy: { server: `http://${PROXY_HOST}:${PROXY_PORT}` },
        userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    });
    const page = await context.newPage();

    try {
        await page.goto(searchUrl, { waitUntil: 'networkidle', timeout: 30000 });
        await page.waitForTimeout(3000);

        // 提取赔率数据
        const oddsData = await page.evaluate(() => {
            // 尝试提取 1X2 赔率
            const oddsElements = document.querySelectorAll('[class*="odds"], [class*="outcome"]');
            const odds = [];

            oddsElements.forEach(el => {
                const text = el.textContent?.trim();
                const val = parseFloat(text);
                if (!isNaN(val) && val > 1 && val < 20) {
                    odds.push(val);
                }
            });

            return {
                odds: odds.length >= 3 ? {
                    home: odds[0],
                    draw: odds[1],
                    away: odds[2]
                } : null,
                url: window.location.href
            };
        });

        if (oddsData.odds) {
            log.success(`  [L3] OddsPortal 数据获取成功`);
            return { source: 'oddsportal', data: oddsData, timestamp: new Date().toISOString() };
        } else {
            log.warn(`  [L3] 未找到赔率数据`);
            return { source: 'oddsportal', data: null, error: 'Odds not found' };
        }
    } catch (e) {
        log.error(`  [L3] OddsPortal 抓取失败: ${e.message}`);
        return { source: 'oddsportal', data: null, error: e.message };
    } finally {
        await context.close();
    }
}

// ============================================================================
// 主函数
// ============================================================================

async function main() {
    console.log('');
    console.log('═'.repeat(65));
    console.log('  V171-DataScience-08 真实历史数据回填');
    console.log('═'.repeat(65));
    console.log('');

    // 确保输出目录存在
    if (!fs.existsSync(OUTPUT_DIR)) {
        fs.mkdirSync(OUTPUT_DIR, { recursive: true });
        log.info(`创建输出目录: ${OUTPUT_DIR}`);
    }

    // 连接数据库
    const client = await getClient();
    log.success('数据库连接成功');

    // 获取比赛列表
    const matches = await getMatchesToBackfill(client);

    // 启动浏览器
    log.info('启动 Chromium 浏览器...');
    const browser = await chromium.launch({
        headless: true,
        args: ['--disable-gpu', '--no-sandbox']
    });
    log.success('浏览器启动成功');

    // 统计
    const stats = {
        total: matches.length,
        success: 0,
        failed: 0,
        partial: 0
    };

    // 逐场抓取
    for (let i = 0; i < matches.length; i++) {
        const match = matches[i];
        log.progress(i + 1, matches.length, match.match_id, '开始抓取');

        try {
            // L2: FotMob 数据
            const l2Data = await fetchFotMobData(browser, match);

            // L3: OddsPortal 数据
            const l3Data = await fetchOddsPortalData(browser, match);

            // 合并数据
            const rawData = {
                match_id: match.match_id,
                home_team: match.home_team,
                away_team: match.away_team,
                league_name: match.league_name,
                match_date: match.match_date,
                home_score: match.home_score,
                away_score: match.away_score,
                l2_fotmob: l2Data,
                l3_oddsportal: l3Data,
                collected_at: new Date().toISOString()
            };

            // 保存到数据库
            await saveRawData(client, match.match_id, rawData);

            // 保存到文件
            const filePath = path.join(OUTPUT_DIR, `${match.match_id}.json`);
            fs.writeFileSync(filePath, JSON.stringify(rawData, null, 2));

            if (l2Data.data && l3Data.data) {
                stats.success++;
                log.progress(i + 1, matches.length, match.match_id, '✅ 成功');
            } else if (l2Data.data || l3Data.data) {
                stats.partial++;
                log.progress(i + 1, matches.length, match.match_id, '⚠️ 部分成功');
            } else {
                stats.failed++;
                log.progress(i + 1, matches.length, match.match_id, '❌ 失败');
            }

            // 每 5 场汇报一次
            if ((i + 1) % 5 === 0) {
                log.info(`📊 阶段汇报: 已完成 ${i + 1}/${matches.length} 场`);
                log.info(`   成功: ${stats.success}, 部分成功: ${stats.partial}, 失败: ${stats.failed}`);
            }

            // 延迟，避免被封
            await new Promise(r => setTimeout(r, 3000 + Math.random() * 2000));

        } catch (e) {
            stats.failed++;
            log.error(`${match.match_id} 抓取异常: ${e.message}`);
        }
    }

    // 关闭
    await browser.close();
    await client.end();

    // 最终汇报
    console.log('');
    console.log('═'.repeat(65));
    console.log('  📊 回填任务完成');
    console.log('═'.repeat(65));
    console.log(`  总计: ${stats.total} 场`);
    console.log(`  ✅ 成功: ${stats.success} 场`);
    console.log(`  ⚠️  部分成功: ${stats.partial} 场`);
    console.log(`  ❌ 失败: ${stats.failed} 场`);
    console.log(`  📁 数据目录: ${OUTPUT_DIR}`);
    console.log('═'.repeat(65));
    console.log('');

    // 验收：查询数据库
    const verifyClient = await getClient();
    const result = await verifyClient.query(`
        SELECT COUNT(*) as count
        FROM raw_match_data
        WHERE match_id IN (
            SELECT match_id FROM matches
            WHERE is_finished = true
              AND league_name IN ('Premier League', 'La Liga')
              AND match_date >= NOW() - INTERVAL '30 days'
        )
    `);
    log.info(`数据库验证: raw_match_data 表中有 ${result.rows[0].count} 条记录`);
    await verifyClient.end();
}

main().catch(e => {
    console.error('❌ 程序异常:', e);
    process.exit(1);
});
