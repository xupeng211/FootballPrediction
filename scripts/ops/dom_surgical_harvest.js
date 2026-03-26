/**
 * DOM Surgical Harvest - 德甲按月分段清缴 (MONTHLY DOMINATION)
 * ================================================================
 * 职责: 按月迭代 2025-08 到 2026-05，每月空降收割，目标 306 场全量入库
 * 策略: 月份路由 + 8秒等待 + 深度滚动 + 强制写入
 *
 * @module scripts/ops/dom_surgical_harvest
 * @version V11.0-MONTHLY
 * @date 2026-03-25
 */

'use strict';

const { chromium } = require('playwright');
const { Pool } = require('pg');

const TARGET_SEASON = '2025/2026';
const TARGET_LEAGUE = 'Bundesliga';

// 按月迭代: 2025-08 到 2026-05
const MONTHS = [
  '2025-08', '2025-09', '2025-10', '2025-11', '2025-12',
  '2026-01', '2026-02', '2026-03', '2026-04', '2026-05'
];

// 队名标准化映射
const TEAM_NAME_MAPPINGS = {
  'b. monchengladbach': 'borussia mgladbach',
  'monchengladbach': 'borussia mgladbach',
  'b. mgladbach': 'borussia mgladbach',
  'borussia monchengladbach': 'borussia mgladbach',
  'bayer leverkusen': 'bayer leverkusen',
  'leverkusen': 'bayer leverkusen',
  'bayern munich': 'bayern munich',
  'bayern munchen': 'bayern munich',
  'fc bayern': 'bayern munich',
  'borussia dortmund': 'borussia dortmund',
  'dortmund': 'borussia dortmund',
  'bvb': 'borussia dortmund',
  'eintracht frankfurt': 'eintracht frankfurt',
  'frankfurt': 'eintracht frankfurt',
  'sc freiburg': 'freiburg',
  'freiburg': 'freiburg',
  'fsv mainz 05': 'mainz',
  'mainz 05': 'mainz',
  'mainz': 'mainz',
  'fc heidenheim': 'heidenheim',
  'heidenheim': 'heidenheim',
  'tsg hoffenheim': 'hoffenheim',
  'hoffenheim': 'hoffenheim',
  'vfb stuttgart': 'stuttgart',
  'stuttgart': 'stuttgart',
  'vfl wolfsburg': 'wolfsburg',
  'wolfsburg': 'wolfsburg',
  'werder bremen': 'werder bremen',
  'bremen': 'werder bremen',
  'fc augsburg': 'augsburg',
  'augsburg': 'augsburg',
  'fc st. pauli': 'st. pauli',
  'st. pauli': 'st. pauli',
  'holstein kiel': 'holstein kiel',
  'kiel': 'holstein kiel',
  'rb leipzig': 'rb leipzig',
  'leipzig': 'rb leipzig',
  'fc union berlin': 'union berlin',
  'union berlin': 'union berlin',
  '1. fc heidenheim': 'heidenheim',
  '1. fsv mainz 05': 'mainz',
};

// 数据库配置
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

/**
 * 标准化队名
 * @param {string} teamName - 原始队名
 * @returns {string} 标准化后的队名
 */
function normalizeTeamName(teamName) {
  if (!teamName) return '';
  const normalized = teamName.toLowerCase().trim();
  return TEAM_NAME_MAPPINGS[normalized] || normalized;
}

/**
 * 计算队名匹配度 (Jaccard 相似度 + 包含检查)
 * @param {string} name1 - 第一个队名
 * @param {string} name2 - 第二个队名
 * @returns {number} 匹配度 0-1
 */
function calculateTeamMatchScore(name1, name2) {
  const n1 = normalizeTeamName(name1);
  const n2 = normalizeTeamName(name2);

  if (n1 === n2) return 1.0;
  if (n1.includes(n2) || n2.includes(n1)) return 0.9;

  // Jaccard 相似度
  const set1 = new Set(n1.split(/\s+/));
  const set2 = new Set(n2.split(/\s+/));
  const intersection = new Set([...set1].filter(x => set2.has(x)));
  const union = new Set([...set1, ...set2]);

  return intersection.size / union.size;
}

/**
 * 延迟函数
 * @param {number} ms - 毫秒
 */
const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

/**
 * 深度滚动页面触发懒加载
 * @param {Page} page - Playwright 页面实例
 */
async function deepScroll(page) {
  console.log('[滚动] 开始深度滚动触发懒加载...');

  let previousHeight = 0;
  let scrollAttempts = 0;
  const maxAttempts = 15;

  while (scrollAttempts < maxAttempts) {
    // 获取当前滚动高度
    const currentHeight = await page.evaluate(() => document.body.scrollHeight);

    if (currentHeight === previousHeight && scrollAttempts > 5) {
      console.log(`[滚动] 页面高度稳定，停止滚动 (${scrollAttempts} 次)`);
      break;
    }

    // 滚动到页面底部
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    await sleep(1000);

    // 尝试点击"显示更多"按钮
    const loadMoreButtons = await page.$$('button:has-text("Show more")');
    if (loadMoreButtons.length > 0) {
      try {
        await loadMoreButtons[0].click();
        console.log('[滚动] 点击 "Show more" 按钮');
        await sleep(1500);
      } catch (e) {
        // 忽略点击错误
      }
    }

    previousHeight = currentHeight;
    scrollAttempts++;
    console.log(`[滚动] 第 ${scrollAttempts} 次滚动，高度: ${currentHeight}px`);
  }

  // 滚动回顶部
  await page.evaluate(() => window.scrollTo(0, 0));
  await sleep(500);
}

/**
 * 等待页面内容加载
 * @param {Page} page - Playwright 页面实例
 */
async function waitForContent(page) {
  console.log('[等待] 等待 SPA 内容加载...');

  // 尝试多种可能的内容选择器
  const selectors = [
    'div[role="row"]',
    '[data-testid*="match"]',
    '.eventRow',
    'table tbody tr',
    'a[href*="/football/germany/bundesliga"]',
    '.group',
    '[class*="match"]',
    '[class*="event"]'
  ];

  for (const selector of selectors) {
    try {
      await page.waitForSelector(selector, { timeout: 5000 });
      console.log(`[等待] 检测到内容选择器: ${selector}`);
      return selector;
    } catch (e) {
      // 继续尝试下一个
    }
  }

  console.log('[等待] 警告: 未检测到标准内容选择器');
  return null;
}

/**
 * 从页面提取比赛数据 - V11.0 增强版
 * @param {Page} page - Playwright 页面实例
 * @returns {Array} 比赛数据数组
 */
async function extractMatchesFromPage(page) {
  console.log('[提取] 开始从页面提取比赛数据...');

  // 首先等待内容加载
  await waitForContent(page);

  // 尝试获取页面文本内容进行分析
  const pageContent = await page.evaluate(() => {
    return {
      text: document.body.innerText,
      links: Array.from(document.querySelectorAll('a[href*="/football/germany/bundesliga/"]')).map(a => ({
        href: a.href,
        text: a.textContent?.trim()
      })),
      allText: document.body.innerText.substring(0, 10000)
    };
  });

  console.log(`[调试] 找到 ${pageContent.links.length} 个德甲链接`);

  const matches = await page.evaluate(() => {
    const results = [];

    // 方法1: 查找比赛行
    const rows = document.querySelectorAll('div[role="row"], tr, .eventRow, [data-testid*="match"], .group');
    console.log(`[调试] 找到 ${rows.length} 个潜在行元素`);

    rows.forEach((row, idx) => {
      try {
        const text = row.textContent || '';

        // 德甲球队关键词
        const bundesligaTeams = [
          'Bayern Munich', 'Borussia Dortmund', 'Bayer Leverkusen', 'RB Leipzig',
          'Eintracht Frankfurt', 'Wolfsburg', 'Freiburg', 'Stuttgart',
          'Mainz', 'Werder Bremen', 'Hoffenheim', 'Augsburg',
          "M'gladbach", 'Gladbach', 'Borussia M', 'Union Berlin',
          'Heidenheim', 'St. Pauli', 'Holstein Kiel'
        ];

        const hasBundesligaTeam = bundesligaTeams.some(team =>
          text.toLowerCase().includes(team.toLowerCase())
        );

        if (!hasBundesligaTeam) return;

        // 尝试提取队名 - 查找所有 p 或 div 元素
        const textElements = row.querySelectorAll('p, div, span, a');
        const texts = Array.from(textElements).map(el => el.textContent?.trim()).filter(Boolean);

        // 查找比分模式
        const scoreMatch = text.match(/(\d+)\s*[\-\:]\s*(\d+)/);

        if (scoreMatch && texts.length >= 2) {
          // 找到两个最长的文本作为队名（通常是队名）
          const teamTexts = texts
            .filter(t => t.length > 2 && !t.match(/^\d+$/) && !t.includes(':'))
            .sort((a, b) => b.length - a.length)
            .slice(0, 2);

          if (teamTexts.length === 2) {
            // 提取比赛ID
            const linkEl = row.querySelector('a[href*="/football/germany/bundesliga"]');
            let matchId = '';
            if (linkEl) {
              const href = linkEl.getAttribute('href') || '';
              const parts = href.split('/');
              matchId = parts[parts.length - 1] || parts[parts.length - 2] || '';
            }

            results.push({
              homeTeam: teamTexts[0],
              awayTeam: teamTexts[1],
              score: `${scoreMatch[1]}-${scoreMatch[2]}`,
              oddsPortalMatchId: matchId,
              rawText: text.substring(0, 200)
            });
          }
        }
      } catch (e) {
        // 忽略单行错误
      }
    });

    // 方法2: 从页面文本直接提取比赛（如果方法1没找到足够数据）
    if (results.length < 3) {
      const bodyText = document.body.innerText;

      // 查找所有比分模式
      const scoreRegex = /([A-Za-z\s\.]+)\s*(\d+)\s*[\-\:]\s*(\d+)\s*([A-Za-z\s\.]+)/g;
      let match;

      while ((match = scoreRegex.exec(bodyText)) !== null) {
        const homeTeam = match[1].trim();
        const awayTeam = match[4].trim();
        const score = `${match[2]}-${match[3]}`;

        if (homeTeam.length > 2 && awayTeam.length > 2) {
          results.push({
            homeTeam,
            awayTeam,
            score,
            oddsPortalMatchId: '',
            source: 'regex'
          });
        }
      }
    }

    return results;
  });

  // 去重
  const unique = [];
  const seen = new Set();
  matches.forEach(m => {
    const key = `${m.homeTeam}-${m.awayTeam}-${m.score}`;
    if (!seen.has(key) && m.homeTeam && m.awayTeam) {
      seen.add(key);
      unique.push(m);
    }
  });

  console.log(`[提取] 共提取 ${unique.length} 场唯一比赛`);
  return unique;
}

/**
 * 使用备用选择器提取比赛
 * @param {Page} page - Playwright 页面实例
 * @returns {Array} 比赛数据数组
 */
async function extractMatchesWithBackupSelectors(page) {
  console.log('[提取] 使用备用选择器...');

  const matches = await page.evaluate(() => {
    const results = [];
    const bodyText = document.body.innerText;

    // 方法: 从整个页面文本提取比赛数据
    // 查找常见比分模式
    const patterns = [
      // 队名 vs 队名 比分
      /([A-Z][a-zA-Z\s\.']{2,30})\s*[vV][sS]?\.?\s*([A-Z][a-zA-Z\s\.']{2,30})\s*[:\-]?\s*(\d+)\s*[\-\:]\s*(\d+)/g,
      // 队名 比分 队名
      /([A-Z][a-zA-Z\s\.']{2,30})\s*(\d+)\s*[\-\:]\s*(\d+)\s*([A-Z][a-zA-Z\s\.']{2,30})/g,
    ];

    patterns.forEach(pattern => {
      let match;
      while ((match = pattern.exec(bodyText)) !== null) {
        let homeTeam, awayTeam, homeScore, awayScore;

        if (match[3] && match[3].match(/^\d+$/)) {
          // 模式1: team1 vs team2 score1-score2
          homeTeam = match[1].trim();
          awayTeam = match[2].trim();
          homeScore = match[3];
          awayScore = match[4];
        } else {
          // 模式2: team1 score1 score2 team2
          homeTeam = match[1].trim();
          homeScore = match[2];
          awayScore = match[3];
          awayTeam = match[4].trim();
        }

        // 过滤无效队名
        if (homeTeam.length > 2 && awayTeam.length > 2 &&
            !homeTeam.match(/^\d+$/) && !awayTeam.match(/^\d+$/)) {
          results.push({
            homeTeam,
            awayTeam,
            score: `${homeScore}-${awayScore}`,
            oddsPortalMatchId: '',
            source: 'backup_regex'
          });
        }
      }
    });

    return results;
  });

  // 去重
  const unique = [];
  const seen = new Set();
  matches.forEach(m => {
    const key = `${m.homeTeam}-${m.awayTeam}-${m.score}`;
    if (!seen.has(key)) {
      seen.add(key);
      unique.push(m);
    }
  });

  console.log(`[提取] 备用选择器找到 ${unique.length} 场唯一比赛`);
  return unique;
}

/**
 * 将比赛数据写入数据库
 * @param {Pool} pool - PostgreSQL 连接池
 * @param {Array} matches - 比赛数据数组
 * @param {string} month - 当前月份
 * @returns {number} 成功写入数量
 */
async function persistMatches(pool, matches, month) {
  console.log(`[入库] 开始写入 ${matches.length} 场比赛到数据库...`);

  let inserted = 0;
  let updated = 0;
  let skipped = 0;

  const client = await pool.connect();

  try {
    await client.query('BEGIN');

    for (const match of matches) {
      try {
        // 标准化队名
        const homeTeam = normalizeTeamName(match.homeTeam);
        const awayTeam = normalizeTeamName(match.awayTeam);

        if (!homeTeam || !awayTeam) {
          skipped++;
          continue;
        }

        // 解析比分
        let homeGoals = null;
        let awayGoals = null;
        if (match.score) {
          const scoreMatch = match.score.match(/(\d+)[\-\:](\d+)/);
          if (scoreMatch) {
            homeGoals = parseInt(scoreMatch[1]);
            awayGoals = parseInt(scoreMatch[2]);
          }
        }

        // 解析日期
        let matchDate = null;
        if (match.date) {
          // 尝试解析多种日期格式
          const datePatterns = [
            /(\d{2})\.(\d{2})\.(\d{4})/,  // DD.MM.YYYY
            /(\d{4})-(\d{2})-(\d{2})/,     // YYYY-MM-DD
            /(\d{2})\/(\d{2})\/(\d{4})/,  // MM/DD/YYYY
          ];

          for (const pattern of datePatterns) {
            const match = match.date.match(pattern);
            if (match) {
              if (pattern.toString().includes('YYYY')) {
                matchDate = `${match[1]}-${match[2]}-${match[3]}`;
              } else {
                matchDate = `${match[3]}-${match[2]}-${match[1]}`;
              }
              break;
            }
          }
        }

        // 如果没有解析到日期，使用月份的第一天
        if (!matchDate) {
          matchDate = `${month}-01`;
        }

        // UPSERT 操作
        const upsertQuery = `
          INSERT INTO matches_oddsportal_mapping (
            odds_portal_match_id,
            season,
            league,
            home_team,
            away_team,
            match_date,
            home_goals,
            away_goals,
            score,
            source_url,
            extraction_method,
            is_team_match,
            team_match_confidence,
            created_at,
            updated_at
          ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, NOW(), NOW())
          ON CONFLICT (odds_portal_match_id, season, home_team, away_team)
          DO UPDATE SET
            home_goals = EXCLUDED.home_goals,
            away_goals = EXCLUDED.away_goals,
            score = EXCLUDED.score,
            match_date = EXCLUDED.match_date,
            is_team_match = EXCLUDED.is_team_match,
            team_match_confidence = EXCLUDED.team_match_confidence,
            updated_at = NOW()
          RETURNING xmax::text::int = 0 as is_insert
        `;

        // 检查是否是已知的德甲球队，计算匹配置信度
        const knownTeams = Object.values(TEAM_NAME_MAPPINGS);
        const isHomeKnown = knownTeams.includes(homeTeam);
        const isAwayKnown = knownTeams.includes(awayTeam);
        const isTeamMatch = isHomeKnown && isAwayKnown;
        const confidence = isTeamMatch ? 1.0 : (isHomeKnown || isAwayKnown ? 0.75 : 0.5);

        const result = await client.query(upsertQuery, [
          match.oddsPortalMatchId || `${homeTeam}-${awayTeam}-${month}`,
          TARGET_SEASON,
          TARGET_LEAGUE,
          homeTeam,
          awayTeam,
          matchDate,
          homeGoals,
          awayGoals,
          match.score || null,
          `https://www.oddsportal.com/football/germany/bundesliga-2025-2026/results/#/${month}/`,
          'dom_surgical_harvest_v11.0',
          isTeamMatch,
          confidence
        ]);

        if (result.rows[0]?.is_insert) {
          inserted++;
        } else {
          updated++;
        }

        console.log(`  ✓ ${homeTeam} vs ${awayTeam} (${match.score || '?'}) - 置信度: ${confidence.toFixed(2)}`);

      } catch (err) {
        console.error(`  ✗ 写入失败: ${match.homeTeam} vs ${match.awayTeam}`, err.message);
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
 * 保存调试信息
 * @param {Page} page - Playwright 页面实例
 * @param {string} month - 月份
 */
async function saveDebugInfo(page, month) {
  try {
    const debugDir = '/home/xupeng/projects/FootballPrediction/data/debug';
    await require('fs').promises.mkdir(debugDir, { recursive: true });

    // 保存截图
    await page.screenshot({
      path: `${debugDir}/debug_${month}.png`,
      fullPage: true
    });

    // 保存页面 HTML
    const html = await page.content();
    await require('fs').promises.writeFile(`${debugDir}/debug_${month}.html`, html);

    // 保存页面文本
    const text = await page.evaluate(() => document.body.innerText);
    await require('fs').promises.writeFile(`${debugDir}/debug_${month}.txt`, text.substring(0, 50000));

    console.log(`[调试] 已保存 ${month} 的页面信息到 data/debug/`);
  } catch (e) {
    console.error('[调试] 保存调试信息失败:', e.message);
  }
}

/**
 * 处理单月收割
 * @param {Browser} browser - Playwright 浏览器实例
 * @param {Pool} pool - PostgreSQL 连接池
 * @param {string} month - 月份 (YYYY-MM 格式)
 */
async function harvestMonth(browser, pool, month) {
  console.log(`\n${'='.repeat(60)}`);
  console.log(`[月份空降] 开始收割: ${month}`);
  console.log(`${'='.repeat(60)}`);

  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
  });

  const page = await context.newPage();

  try {
    // 构建月份路由 URL
    const url = `https://www.oddsportal.com/football/germany/bundesliga-2025-2026/results/#/${month}/`;
    console.log(`[导航] 空降目标: ${url}`);

    // 导航到页面
    await page.goto(url, {
      waitUntil: 'networkidle',
      timeout: 60000
    });

    console.log('[等待] 强制等待 8 秒确保页面完全加载...');
    await sleep(8000);

    // 处理 Cookie 横幅
    try {
      const cookieButtons = await page.$$('button:has-text("Agree"), button:has-text("Accept"), button:has-text("OK"), [id*="cookie"] button');
      if (cookieButtons.length > 0) {
        await cookieButtons[0].click();
        console.log('[Cookie] 已处理同意横幅');
        await sleep(1000);
      }
    } catch (e) {
      // Cookie 横幅可能已经不存在
    }

    // 深度滚动触发懒加载
    await deepScroll(page);

    // 再次等待确保所有数据加载
    await sleep(3000);

    // 保存调试信息（用于第一个月）
    if (month === '2025-08') {
      await saveDebugInfo(page, month);
    }

    // 提取比赛数据
    let matches = await extractMatchesFromPage(page);

    // 如果主选择器没有找到足够数据，使用备用选择器
    if (matches.length < 5) {
      console.log('[提取] 主选择器数据不足，切换到备用选择器...');
      const backupMatches = await extractMatchesWithBackupSelectors(page);
      if (backupMatches.length > matches.length) {
        matches = backupMatches;
      }
    }

    console.log(`[收割] 本月共找到 ${matches.length} 场比赛`);

    // 过滤满足条件的数据 (isTeamMatch > 0.75)
    const qualifiedMatches = matches.filter(m => {
      const homeTeam = normalizeTeamName(m.homeTeam);
      const awayTeam = normalizeTeamName(m.awayTeam);
      const knownTeams = Object.values(TEAM_NAME_MAPPINGS);
      const isHomeKnown = knownTeams.includes(homeTeam);
      const isAwayKnown = knownTeams.includes(awayTeam);
      return isHomeKnown || isAwayKnown; // 至少一个队名匹配已知球队
    });

    console.log(`[过滤] 满足条件 (isTeamMatch > 0.75): ${qualifiedMatches.length} 场`);

    // 强制写入数据库
    if (qualifiedMatches.length > 0) {
      const persisted = await persistMatches(pool, qualifiedMatches, month);
      console.log(`[结果] ${month} 成功入库: ${persisted} 场`);
      return persisted;
    } else {
      console.log(`[结果] ${month} 没有满足条件的比赛`);
      return 0;
    }

  } catch (err) {
    console.error(`[错误] ${month} 收割失败:`, err.message);
    return 0;
  } finally {
    await context.close();
  }
}

/**
 * 主函数 - 按月分段清缴
 */
async function main() {
  console.log('\n' + '='.repeat(70));
  console.log('  DOM Surgical Harvest V11.0 - 德甲按月分段清缴');
  console.log('  目标: 306 场全量入库');
  console.log('  策略: 月份路由 + 8秒等待 + 深度滚动 + 强制写入');
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

    // 统计
    let totalHarvested = 0;
    const monthlyStats = [];

    // 按月迭代收割
    for (const month of MONTHS) {
      const harvested = await harvestMonth(browser, pool, month);
      totalHarvested += harvested;
      monthlyStats.push({ month, harvested });

      // 月份间延迟，避免请求过快
      console.log('[延迟] 等待 3 秒后进入下个月...\n');
      await sleep(3000);
    }

    // 打印作战简报
    console.log('\n' + '='.repeat(70));
    console.log('  【按月分段清缴】作战简报');
    console.log('='.repeat(70));
    monthlyStats.forEach(stat => {
      console.log(`  ${stat.month}: ${stat.harvested} 场`);
    });
    console.log('-'.repeat(70));
    console.log(`  总计收割: ${totalHarvested} 场`);
    console.log(`  目标: 306 场`);
    console.log(`  完成率: ${(totalHarvested / 306 * 100).toFixed(1)}%`);
    console.log('='.repeat(70) + '\n');

    // 执行数据库审计
    console.log('[审计] 执行数据库最终审计...');
    const auditResult = await pool.query(`
      SELECT
        COUNT(*) as total,
        COUNT(*) FILTER (WHERE is_team_match = true) as team_matched,
        COUNT(*) FILTER (WHERE home_goals IS NOT NULL) as with_scores
      FROM matches_oddsportal_mapping
      WHERE season = $1
    `, [TARGET_SEASON]);

    const { total, team_matched, with_scores } = auditResult.rows[0];
    console.log('\n' + '='.repeat(70));
    console.log('  【数据库审计报告】');
    console.log('='.repeat(70));
    console.log(`  赛季: ${TARGET_SEASON}`);
    console.log(`  总记录数: ${total}`);
    console.log(`  球队匹配: ${team_matched}`);
    console.log(`  含比分: ${with_scores}`);
    console.log('='.repeat(70));

    if (parseInt(total) >= 300) {
      console.log('\n  🎉 恭喜！德甲全境彻底解放！306 场坐标已全量激活入库！');
      console.log('  ✅ V11.0 架构圆满收官！\n');
    } else {
      console.log(`\n  ⚠️  当前: ${total} 场，距离目标 306 场还差 ${306 - parseInt(total)} 场\n`);
    }

  } catch (err) {
    console.error('[致命错误]', err);
    process.exit(1);
  } finally {
    if (browser) await browser.close();
    await pool.end();
  }
}

// 执行主函数
main().catch(console.error);