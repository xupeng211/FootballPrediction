/**
 * L1 Fixture Harvester - 德甲 25/26 赛季赛程抓取
 * ===============================================
 * 职责: 从 OddsPortal 抓取完整赛程，填充 L1 matches 表至 306 场
 * 目标: https://www.oddsportal.com/football/germany/bundesliga-2025-2026/fixtures/
 *
 * @version V11.0-L1-RECOVERY
 * @date 2026-03-26
 */

'use strict';

const { chromium } = require('playwright');
const { Pool } = require('pg');

// 德甲 18 支标准球队
const BUNDESLIGA_TEAMS = [
  'Bayern München', 'Borussia Dortmund', 'Bayer Leverkusen', 'RB Leipzig',
  'Eintracht Frankfurt', 'Wolfsburg', 'Freiburg', 'Stuttgart',
  'Mainz 05', 'Werder Bremen', 'Hoffenheim', 'Augsburg',
  'Borussia Mönchengladbach', 'Union Berlin', 'Heidenheim', 'St. Pauli',
  'Holstein Kiel', 'Bochum'
];

const DB_CONFIG = {
  host: process.env.DB_HOST || 'db',
  port: parseInt(process.env.DB_PORT || '5432'),
  database: process.env.DB_NAME || 'football_db',
  user: process.env.DB_USER || 'football_user',
  password: process.env.DB_PASSWORD || 'football_pass',
  max: 10,
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 10000,
};

const sleep = (ms) => new Promise(resolve => {
  setTimeout(resolve, ms);
});

/**
 * 生成标准 match_id
 */
function generateMatchId(homeTeam, awayTeam, dateStr) {
  const homeHash = homeTeam.toLowerCase().replace(/[^a-z]/g, '').substring(0, 4);
  const awayHash = awayTeam.toLowerCase().replace(/[^a-z]/g, '').substring(0, 4);
  const dateHash = dateStr.replace(/-/g, '');
  return `54_20252026_${homeHash}${awayHash}${dateHash}`;
}

/**
 * 从页面提取赛程数据
 */
async function extractFixtures(page) {
  console.log('[提取] 开始抓取赛程数据...');

  const fixtures = await page.evaluate((teams) => {
    const results = [];
    const teamSet = new Set(teams.map(t => t.toLowerCase()));

    // 查找所有比赛行
    const rows = document.querySelectorAll('div[role="row"], tr, .eventRow, [data-testid*="match"]');

    rows.forEach(row => {
      try {
        const text = row.textContent || '';
        const lowerText = text.toLowerCase();

        // 检查是否包含德甲球队
        const hasBundesligaTeam = teams.some(team =>
          lowerText.includes(team.toLowerCase())
        );

        if (!hasBundesligaTeam) return;

        // 提取队名 - 查找所有文本元素
        const textElements = row.querySelectorAll('p, div, span, a');
        const texts = Array.from(textElements)
          .map(el => el.textContent?.trim())
          .filter(t => t && t.length > 2 && !t.match(/^\d+$/));

        // 查找日期/时间
        const dateMatch = text.match(/(\d{2})\.(\d{2})\.(\d{4})/);
        const timeMatch = text.match(/(\d{2}):(\d{2})/);

        // 查找比分（如果有）
        const scoreMatch = text.match(/(\d+)\s*-\s*(\d+)/);

        // 提取链接
        const linkEl = row.querySelector('a[href*="/football/germany/bundesliga"]');
        let oddsPortalId = '';
        if (linkEl) {
          const href = linkEl.getAttribute('href') || '';
          const parts = href.split('/');
          oddsPortalId = parts[parts.length - 2] || '';
        }

        // 识别两队（从文本中）
        let homeTeam = '', awayTeam = '';
        for (const t of texts) {
          for (const team of teams) {
            if (t.toLowerCase().includes(team.toLowerCase())) {
              if (!homeTeam) homeTeam = team;
              else if (!awayTeam && team !== homeTeam) awayTeam = team;
            }
          }
        }

        if (homeTeam && awayTeam && dateMatch) {
          const dateStr = `${dateMatch[3]}-${dateMatch[2]}-${dateMatch[1]}`;
          results.push({
            homeTeam,
            awayTeam,
            matchDate: dateStr,
            matchTime: timeMatch ? `${timeMatch[1]}:${timeMatch[2]}` : null,
            homeScore: scoreMatch ? parseInt(scoreMatch[1]) : null,
            awayScore: scoreMatch ? parseInt(scoreMatch[2]) : null,
            oddsPortalId,
            isFinished: !!scoreMatch,
            rawText: text.substring(0, 200)
          });
        }
      } catch (e) {
        // 忽略单行错误
      }
    });

    return results;
  }, BUNDESLIGA_TEAMS);

  // 去重
  const unique = [];
  const seen = new Set();
  fixtures.forEach(f => {
    const key = `${f.homeTeam}-${f.awayTeam}-${f.matchDate}`;
    if (!seen.has(key)) {
      seen.add(key);
      unique.push(f);
    }
  });

  console.log(`[提取] 找到 ${unique.length} 场唯一比赛`);
  return unique;
}

/**
 * 将赛程写入 L1 matches 表
 */
async function persistFixtures(pool, fixtures) {
  console.log(`[入库] 开始写入 ${fixtures.length} 场比赛到 L1...`);

  let inserted = 0;
  let updated = 0;
  let skipped = 0;

  const client = await pool.connect();

  try {
    await client.query('BEGIN');

    for (const fixture of fixtures) {
      try {
        const matchId = generateMatchId(fixture.homeTeam, fixture.awayTeam, fixture.matchDate);

        // UPSERT 到 matches 表
        const upsertQuery = `
          INSERT INTO matches (
            match_id,
            external_id,
            league_name,
            season,
            home_team,
            away_team,
            home_score,
            away_score,
            match_date,
            match_time,
            status,
            is_finished,
            data_source,
            created_at,
            updated_at
          ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, NOW(), NOW())
          ON CONFLICT (match_id)
          DO UPDATE SET
            home_score = EXCLUDED.home_score,
            away_score = EXCLUDED.away_score,
            match_date = EXCLUDED.match_date,
            match_time = EXCLUDED.match_time,
            status = EXCLUDED.status,
            is_finished = EXCLUDED.is_finished,
            updated_at = NOW()
          RETURNING xmax::text::int = 0 as is_insert
        `;

        const result = await client.query(upsertQuery, [
          matchId,
          fixture.oddsPortalId || null,
          'Bundesliga',
          '2025/2026',
          fixture.homeTeam,
          fixture.awayTeam,
          fixture.homeScore,
          fixture.awayScore,
          fixture.matchDate,
          fixture.matchTime,
          fixture.isFinished ? 'finished' : 'scheduled',
          fixture.isFinished,
          'OddsPortal-L1-Recovery'
        ]);

        if (result.rows[0]?.is_insert) {
          inserted++;
        } else {
          updated++;
        }

      } catch (err) {
        console.error(`  ✗ 写入失败: ${fixture.homeTeam} vs ${fixture.awayTeam}`, err.message);
        skipped++;
      }
    }

    await client.query('COMMIT');

  } catch (err) {
    await client.query('ROLLBACK');
    console.error('[入库] 事务失败，已回滚:', err.message);
  } finally {
    client.release();
  }

  console.log(`[入库] 完成: ${inserted} 新增, ${updated} 更新, ${skipped} 跳过`);
  return inserted + updated;
}

/**
 * 主函数
 */
async function main() {
  console.log('\n' + '='.repeat(70));
  console.log('  L1 Fixture Harvester V11.0 - 德甲赛程补齐');
  console.log('  目标: 填充 L1 matches 表至 306 场');
  console.log('='.repeat(70) + '\n');

  const pool = new Pool(DB_CONFIG);
  let browser = null;

  try {
    // 启动浏览器
    console.log('[启动] 初始化 Playwright 浏览器...');
    browser = await chromium.launch({
      headless: true,
      args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
    });

    const context = await browser.newContext({
      viewport: { width: 1920, height: 1080 },
      userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    });

    const page = await context.newPage();

    // 导航到赛程页面
    const url = 'https://www.oddsportal.com/football/germany/bundesliga-2025-2026/fixtures/';
    console.log(`[导航] 访问: ${url}`);

    await page.goto(url, {
      waitUntil: 'networkidle',
      timeout: 60000
    });

    // 等待页面加载
    console.log('[等待] 等待页面完全加载...');
    await sleep(8000);

    // 处理 Cookie
    try {
      const cookieBtn = await page.$('button:has-text("Agree"), button:has-text("Accept")');
      if (cookieBtn) await cookieBtn.click();
    } catch (e) {
      // 忽略 Cookie 按钮不存在
    }

    // 深度滚动加载所有内容
    console.log('[滚动] 深度滚动加载全部赛程...');
    let previousHeight = 0;
    let attempts = 0;
    while (attempts < 20) {
      const currentHeight = await page.evaluate(() => document.body.scrollHeight);
      if (currentHeight === previousHeight && attempts > 5) break;

      await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
      await sleep(2000);

      // 尝试点击"显示更多"
      const loadMore = await page.$('button:has-text("Show more")');
      if (loadMore) {
        await loadMore.click();
        await sleep(1500);
      }

      previousHeight = currentHeight;
      attempts++;
      console.log(`  滚动 ${attempts}: 高度 ${currentHeight}px`);
    }

    // 提取赛程
    const fixtures = await extractFixtures(page);

    // 写入数据库
    if (fixtures.length > 0) {
      const persisted = await persistFixtures(pool, fixtures);
      console.log(`\n[结果] 成功入库: ${persisted} 场`);
    } else {
      console.log('\n[警告] 未提取到任何赛程');
    }

    // 最终审计
    console.log('\n[审计] 执行最终核对...');
    const auditResult = await pool.query(`
      SELECT
        COUNT(*) as total,
        COUNT(*) FILTER (WHERE match_id LIKE '%20252026%') as season_2526,
        COUNT(*) FILTER (WHERE match_id LIKE '%20242025%') as season_2425,
        COUNT(*) FILTER (WHERE is_finished = true) as finished
      FROM matches
      WHERE season = '2025/2026' AND league_name = 'Bundesliga'
    `);

    const { total, season_2526, season_2425, finished } = auditResult.rows[0];

    console.log('\n' + '='.repeat(70));
    console.log('  【L1 赛程补齐报告】');
    console.log('='.repeat(70));
    console.log(`  总记录数: ${total}`);
    console.log(`  25/26 赛季: ${season_2526}`);
    console.log(`  24/25 误标: ${season_2425}`);
    console.log(`  已完成: ${finished}`);
    console.log(`  目标: 306 场`);
    console.log(`  缺口: ${306 - parseInt(season_2526)} 场`);
    console.log('='.repeat(70));

    if (parseInt(season_2526) >= 306) {
      console.log('\n  🎉 L1 种子补齐完成！306 场全部到位！\n');
    } else {
      console.log(`\n  ⚠️  还需补充 ${306 - parseInt(season_2526)} 场\n`);
    }

    await context.close();

  } catch (err) {
    console.error('[致命错误]', err);
    process.exit(1);
  } finally {
    if (browser) await browser.close();
    await pool.end();
  }
}

main().catch(console.error);
