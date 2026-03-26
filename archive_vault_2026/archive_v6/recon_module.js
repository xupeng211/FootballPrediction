/**
 * TITAN V6.0 RECON MODULE - 全量测绘引擎
 * ======================================
 * 自动轮询五大联赛列表页，生成精确打击队列
 * 
 * @module scripts/ops/recon_module
 * @version V6.0-RECON-ENGINE
 */

'use strict';

const { chromium } = require('playwright');
const { Pool } = require('pg');

// 五大联赛配置
const TOP5_LEAGUES = [
  { name: 'Premier League', slug: 'england/premier-league', id: 'premier' },
  { name: 'Bundesliga', slug: 'germany/bundesliga', id: 'bundesliga' },
  { name: 'La Liga', slug: 'spain/laliga', id: 'laliga' },
  { name: 'Serie A', slug: 'italy/serie-a', id: 'seriea' },
  { name: 'Ligue 1', slug: 'france/ligue-1', id: 'ligue1' }
];

// 数据库配置
const DB_CONFIG = {
  host: '127.0.0.1',
  port: 5432,
  database: 'football_db',
  user: 'football_user',
  password: process.env.DB_PASSWORD || 'football_pass',
};

/**
 * 标准化队名用于匹配
 */
function normalizeTeamName(name) {
  return name.toLowerCase()
    .replace(/[^a-z0-9\s]/g, '')
    .replace(/\s+/g, ' ')
    .trim()
    .split(' ')
    .filter(w => w.length > 1 && !['fc', 'cf', 'sv', 'sc', 'vfb', '1', '05', 'united', 'city'].includes(w));
}

/**
 * 从联赛页面提取比赛URL
 */
async function extractLeagueMatches(page, league) {
  const url = `https://www.oddsportal.com/football/${league.slug}/`;
  console.log(`\n🔍 [RECON] 侦察 ${league.name}...`);
  console.log(`   URL: ${url}`);

  try {
    // 访问联赛页面
    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await page.waitForTimeout(3000);

    // 提取比赛链接
    const matches = await page.evaluate(() => {
      const links = [];
      // 尝试多种选择器
      const selectors = [
        'a[href*="/football/"][href*="-"][href*="/"]',
        '[data-testid="match-title-link"]',
        '.event-list a[href]',
        'a[href^="/football/"]'
      ];

      for (const selector of selectors) {
        const elements = document.querySelectorAll(selector);
        for (const el of elements) {
          const href = el.getAttribute('href');
          if (href && href.includes('/football/') && href.split('/').length >= 4) {
            // 提取hash (8字符)
            const hashMatch = href.match(/-([a-zA-Z0-9]{8})\/?$/);
            if (hashMatch && !links.find(l => l.url === href)) {
              links.push({
                url: href.startsWith('http') ? href : `https://www.oddsportal.com${href}`,
                slug: href.split('/').pop().replace(/-[a-zA-Z0-9]{8}\/?$/, ''),
                hash: hashMatch[1]
              });
            }
          }
        }
      }
      return links;
    });

    console.log(`   ✅ 提取到 ${matches.length} 个URL`);
    return matches.map(m => ({ ...m, league: league.name }));

  } catch (error) {
    console.log(`   ⚠️  侦察失败: ${error.message}`);
    return [];
  }
}

/**
 * 建立StrikeQueue：将侦察URL与DB队名对齐
 */
async function buildStrikeQueue(pool, reconData) {
  console.log('\n🎯 [STRIKE QUEUE] 建立目标对齐队列...');

  // 从DB获取未来7天待收割比赛
  const query = `
    SELECT 
      m.match_id, 
      m.home_team, 
      m.away_team, 
      m.league_name,
      m.match_date
    FROM matches m
    LEFT JOIN l3_features l3 ON m.match_id = l3.match_id
    WHERE m.league_name IN ('Premier League', 'Bundesliga', 'La Liga', 'Serie A', 'Ligue 1')
    AND m.match_date > NOW()
    AND m.match_date < NOW() + INTERVAL '7 days'
    AND l3.match_id IS NULL
    ORDER BY m.match_date ASC
    LIMIT 200;
  `;

  const dbMatches = await pool.query(query);
  console.log(`   📊 DB中待收割比赛: ${dbMatches.rows.length} 场`);
  console.log(`   📊 侦察URL数量: ${reconData.length} 个`);

  const strikeQueue = [];
  const unmatched = [];

  for (const match of dbMatches.rows) {
    // 标准化队名
    const homeWords = normalizeTeamName(match.home_team);
    const awayWords = normalizeTeamName(match.away_team);

    // 查找最佳匹配
    let bestMatch = null;
    let bestScore = 0;

    for (const recon of reconData) {
      if (recon.league !== match.league_name) continue;

      const slug = recon.slug.toLowerCase().replace(/[^a-z0-9\-]/g, '');
      let score = 0;
      let homeMatched = 0;
      let awayMatched = 0;

      // 检查主队词匹配
      for (const word of homeWords) {
        if (slug.includes(word)) {
          score += 3;
          homeMatched++;
        }
      }

      // 检查客队词匹配
      for (const word of awayWords) {
        if (slug.includes(word)) {
          score += 3;
          awayMatched++;
        }
      }

      // 两队都有匹配
      if (homeMatched > 0 && awayMatched > 0) {
        score += 10;
      }

      if (score > bestScore) {
        bestScore = score;
        bestMatch = recon;
      }
    }

    // 阈值：至少6分
    if (bestMatch && bestScore >= 6) {
      strikeQueue.push({
        match_id: match.match_id,
        match_name: `${match.home_team} vs ${match.away_team}`,
        league: match.league_name,
        match_date: match.match_date,
        url: bestMatch.url,
        hash: bestMatch.hash,
        confidence: bestScore,
        attempts: 0,
        status: 'pending'
      });
    } else {
      unmatched.push({
        match_id: match.match_id,
        match_name: `${match.home_team} vs ${match.away_team}`,
        league: match.league_name
      });
    }
  }

  console.log(`   ✅ StrikeQueue建立完成: ${strikeQueue.length} 个目标`);
  console.log(`   ⚠️  未匹配: ${unmatched.length} 场`);

  return { strikeQueue, unmatched };
}

/**
 * 主测绘函数
 */
async function runReconnaissance(options = {}) {
  const header = `
╔══════════════════════════════════════════════════════════════════╗
║     🔍 TITAN V6.0 RECON MODULE - 全量测绘引擎 🔍               ║
║     五大联赛轮询，建立精确打击队列                             ║
╚══════════════════════════════════════════════════════════════════╝`;
  console.log(header);

  const pool = new Pool(DB_CONFIG);
  let browser = null;
  let context = null;

  try {
    // 启动浏览器
    console.log('\n🚀 启动浏览器...');
    browser = await chromium.launch({
      headless: false,
      args: ['--no-sandbox', '--disable-setuid-sandbox']
    });

    context = await browser.newContext({
      viewport: { width: 1920, height: 1080 },
      userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.0'
    });

    const page = await context.newPage();

    // 轮询五大联赛
    const allReconData = [];
    for (const league of TOP5_LEAGUES) {
      const matches = await extractLeagueMatches(page, league);
      allReconData.push(...matches);

      // 联赛间延迟
      if (league !== TOP5_LEAGUES[TOP5_LEAGUES.length - 1]) {
        await page.waitForTimeout(2000);
      }
    }

    // 建立StrikeQueue
    const { strikeQueue, unmatched } = await buildStrikeQueue(pool, allReconData);

    // 返回结果
    return {
      strikeQueue,
      unmatched,
      stats: {
        total_leagues: TOP5_LEAGUES.length,
        total_urls: allReconData.length,
        matched: strikeQueue.length,
        unmatched_count: unmatched.length,
        coverage_rate: allReconData.length > 0
          ? ((strikeQueue.length / allReconData.length) * 100).toFixed(1)
          : 0
      }
    };

  } finally {
    if (context) await context.close();
    if (browser) await browser.close();
    await pool.end();
  }
}

module.exports = {
  runReconnaissance,
  TOP5_LEAGUES,
  normalizeTeamName
};

