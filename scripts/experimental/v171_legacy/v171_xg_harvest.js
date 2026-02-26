/**
 * V171-DataScience-07 xG 数据真实抓取（Playwright 浏览器自动化）
 * ============================================
 *
 * 攻克 Turnstile 验证：使用真实浏览器访问比赛页面提取 xG 数据
 *
 * @module scripts/ops/v171_xg_harvest
 */

'use strict';

const { Client } = require('pg');
const { chromium } = require('playwright');
const fs = require('fs');

// ============================================================================
// 配置
// ============================================================================

const DB_CONFIG = {
    host: process.env.DB_HOST || 'host.docker.internal',
    port: parseInt(process.env.DB_PORT) || 5432,
    database: process.env.DB_NAME || 'football_db',
    user: process.env.DB_USER || 'football_user',
    password: 'your_secure_password_here'
};

const OUTPUT_DIR = '/app/data/backfill';

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
        console.log(`[${new Date().toISOString().slice(11, 19)}] 📊 [${bar}] ${current}/${total} | ${matchId} | ${status}`);
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

async function getMatchesToHarvest(client, limit = 10) {
    const result = await client.query(`
        SELECT
            m.match_id,
            m.home_team,
            m.away_team,
            m.league_name,
            m.match_date,
            m.home_score,
            m.away_score,
            m.external_id as fotmob_id
        FROM matches m
        WHERE m.is_finished = true
          AND m.league_name IN ('Premier League', 'La Liga')
          AND m.home_score IS NOT NULL
          AND NOT EXISTS (
              SELECT 1 FROM raw_match_data r
              WHERE r.match_id = m.match_id
              AND r.raw_data->'l2_fotmob'->'data'->'xg' IS NOT NULL
          )
        ORDER BY m.match_date DESC
        LIMIT $1
    `, [limit]);

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
// xG 数据抓取
// ============================================================================

async function fetchXGData(browser, match) {
    const { home_team, away_team, fotmob_id } = match;

    log.info(`  抓取 xG: ${home_team} vs ${away_team} (ID: ${fotmob_id || 'N/A'})`);

    const context = await browser.newContext({
        userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        viewport: { width: 1920, height: 1080 },
        locale: 'en-US'
    });

    const page = await context.newPage();
    let xgData = null;

    try {
        // 如果有 fotmob_id，直接访问比赛页面
        if (fotmob_id) {
            const matchUrl = `https://www.fotmob.com/matches/${home_team.toLowerCase().replace(/ /g, '-')}-vs-${away_team.toLowerCase().replace(/ /g, '-')}/${fotmob_id}`;
            log.info(`  访问: ${matchUrl}`);

            await page.goto(matchUrl, { waitUntil: 'domcontentloaded', timeout: 60000 });
            await page.waitForTimeout(5000);

        } else {
            // 搜索比赛
            const searchUrl = `https://www.fotmob.com/search?query=${encodeURIComponent(`${home_team} vs ${away_team}`)}`;
            log.info(`  搜索: ${searchUrl}`);

            await page.goto(searchUrl, { waitUntil: 'domcontentloaded', timeout: 60000 });
            await page.waitForTimeout(3000);

            // 点击第一个搜索结果
            const matchLink = await page.$('a[href*="/matches/"]');
            if (matchLink) {
                await matchLink.click();
                await page.waitForTimeout(5000);
            }
        }

        // 从页面提取 xG 数据
        xgData = await page.evaluate(() => {
            const result = {
                url: window.location.href,
                xg: null,
                possession: null,
                shots: null
            };

            // 方法1: 查找包含 "xG" 文本的元素
            const allText = document.body.innerText;
            const xgMatch = allText.match(/(\d+\.?\d*)\s*xG|xG\s*(\d+\.?\d*)/gi);
            if (xgMatch) {
                const values = xgMatch.map(m => parseFloat(m.match(/\d+\.?\d*/)?.[0])).filter(v => !isNaN(v));
                if (values.length >= 2) {
                    result.xg = { home: values[0], away: values[1] };
                }
            }

            // 方法2: 查找 stats 区域
            const statElements = document.querySelectorAll('[class*="stat"], [class*="Stat"]');
            for (const el of statElements) {
                const text = el.textContent || '';
                if (text.toLowerCase().includes('xg') || text.toLowerCase().includes('expected')) {
                    const numbers = text.match(/\d+\.?\d*/g);
                    if (numbers && numbers.length >= 2) {
                        result.xg = { home: parseFloat(numbers[0]), away: parseFloat(numbers[1]) };
                        break;
                    }
                }
            }

            // 方法3: 查找表格数据
            const tables = document.querySelectorAll('table, [class*="table"]');
            for (const table of tables) {
                const rows = table.querySelectorAll('tr, [class*="row"]');
                for (const row of rows) {
                    const text = row.textContent || '';
                    if (text.toLowerCase().includes('xg')) {
                        const numbers = text.match(/\d+\.?\d*/g);
                        if (numbers && numbers.length >= 2) {
                            result.xg = { home: parseFloat(numbers[0]), away: parseFloat(numbers[1]) };
                            break;
                        }
                    }
                }
                if (result.xg) break;
            }

            // 提取控球率
            const possessionMatch = allText.match(/(\d+)%\s*(?:Possession|Ball)/i);
            if (possessionMatch) {
                result.possession = possessionMatch[1];
            }

            return result;
        });

        // 拦截 API 请求获取更详细数据
        const apiData = await tryInterceptAPI(page);
        if (apiData?.xg && !xgData.xg) {
            xgData.xg = apiData.xg;
            xgData.api = apiData;
        }

        if (xgData.xg) {
            log.success(`  xG 数据获取成功: ${JSON.stringify(xgData.xg)}`);
        } else {
            log.warn(`  未能提取 xG 数据`);
        }

        return { source: 'fotmob', data: xgData, timestamp: new Date().toISOString() };

    } catch (e) {
        log.error(`  抓取失败: ${e.message}`);
        return { source: 'fotmob', data: null, error: e.message };
    } finally {
        await context.close();
    }
}

/**
 * 尝试拦截 FotMob API 请求
 */
async function tryInterceptAPI(page) {
    return new Promise((resolve) => {
        let result = null;

        page.on('response', async (response) => {
            if (response.url().includes('/api/matchDetails')) {
                try {
                    const data = await response.json();
                    if (data?.content?.stats) {
                        const xgStats = data.content.stats.find(s =>
                            s.title?.toLowerCase().includes('expected') ||
                            s.title?.toLowerCase().includes('xg')
                        );
                        if (xgStats?.stats) {
                            result = {
                                xg: {
                                    home: parseFloat(xgStats.stats[0]?.statValue),
                                    away: parseFloat(xgStats.stats[1]?.statValue)
                                }
                            };
                        }
                    }
                } catch (e) {}
            }
        });

        // 等待一段时间让 API 请求完成
        setTimeout(() => resolve(result), 10000);
    });
}

// ============================================================================
// 主函数
// ============================================================================

async function main() {
    console.log('');
    console.log('═'.repeat(65));
    console.log('  V171-DataScience-07 xG 数据真实抓取');
    console.log('═'.repeat(65));
    console.log('');

    // 确保输出目录存在
    if (!fs.existsSync(OUTPUT_DIR)) {
        fs.mkdirSync(OUTPUT_DIR, { recursive: true });
    }

    const client = await getClient();
    log.success('数据库连接成功');

    const matches = await getMatchesToHarvest(client, 20);
    log.info(`找到 ${matches.length} 场比赛需要抓取 xG 数据`);

    if (matches.length === 0) {
        log.warn('没有需要抓取的比赛');
        await client.end();
        return;
    }

    log.info('启动 Chromium 浏览器...');
    const browser = await chromium.launch({
        headless: true,
        args: ['--disable-blink-features=AutomationControlled', '--no-sandbox']
    });
    log.success('浏览器启动成功');

    const stats = { total: matches.length, success: 0, failed: 0 };
    const successMatches = [];

    for (let i = 0; i < matches.length; i++) {
        const match = matches[i];
        log.progress(i + 1, matches.length, match.match_id, '抓取中');

        try {
            const l2Data = await fetchXGData(browser, match);

            const rawData = {
                match_id: match.match_id,
                home_team: match.home_team,
                away_team: match.away_team,
                league_name: match.league_name,
                match_date: match.match_date,
                home_score: match.home_score,
                away_score: match.away_score,
                l2_fotmob: l2Data,
                collected_at: new Date().toISOString()
            };

            await saveRawData(client, match.match_id, rawData);

            const filePath = `${OUTPUT_DIR}/${match.match_id}.json`;
            fs.writeFileSync(filePath, JSON.stringify(rawData, null, 2));

            if (l2Data.data?.xg) {
                stats.success++;
                successMatches.push({ id: match.match_id, xg: l2Data.data.xg });
                log.progress(i + 1, matches.length, match.match_id, `✅ xG: ${l2Data.data.xg.home} - ${l2Data.data.xg.away}`);
            } else {
                stats.failed++;
                log.progress(i + 1, matches.length, match.match_id, '❌ 无 xG');
            }

            // 每 5 场汇报
            if ((i + 1) % 5 === 0) {
                log.info(`📊 阶段汇报: 成功 ${stats.success}/${i + 1}`);
            }

            // 成功 5 场后可以停止
            if (stats.success >= 5) {
                log.success('已成功抓取 5 场 xG 数据，达到验收标准！');
                break;
            }

            await new Promise(r => setTimeout(r, 3000 + Math.random() * 2000));

        } catch (e) {
            stats.failed++;
            log.error(`${match.match_id} 异常: ${e.message}`);
        }
    }

    await browser.close();
    await client.end();

    console.log('');
    console.log('═'.repeat(65));
    console.log('  📊 xG 抓取完成');
    console.log('═'.repeat(65));
    console.log(`  总计: ${stats.total} 场`);
    console.log(`  ✅ 成功: ${stats.success} 场`);
    console.log(`  ❌ 失败: ${stats.failed} 场`);
    console.log('═'.repeat(65));

    if (successMatches.length > 0) {
        console.log('\n  🏆 成功抓取 xG 的比赛:');
        successMatches.forEach((m, i) => {
            console.log(`     ${i + 1}. ${m.id} | xG: ${m.xg.home} - ${m.xg.away}`);
        });
    }
}

main().catch(e => {
    console.error('❌ 程序异常:', e);
    process.exit(1);
});
