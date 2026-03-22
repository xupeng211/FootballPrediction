/**
 * TITAN V6.7 RECON SCANNER - 历史赛季测绘扫描器 (重构版)
 * =========================================================
 *
 * V6.7 重构改进:
 * 1. 修复 XPath 非标语法 (contains(@class) → CSS [class*=""])
 * 2. 引入 RapidFuzz C++ 引擎进行模糊匹配
 * 3. 更新 2026 年 OddsPortal 选择器
 * 4. 对齐 Repository 模式，解耦 SQL
 *
 * 用法:
 *   node scripts/ops/recon_scanner.js --season 2023-2024 --league EPL
 *   node scripts/ops/recon_scanner.js --season 2022-2023 --all-leagues
 *
 * @module scripts/ops/recon_scanner
 * @version V6.7-RECON-TDD
 * @date 2026-03-22
 */

'use strict';

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const { ProxyRotator } = require('../../src/infrastructure/harvesters/ProxyRotator');
const { FixtureRepository } = require('../../src/infrastructure/services/FixtureRepository');

// V6.7: 尝试加载 RapidFuzz，失败则使用 JS 回退
let rapidfuzz = null;
try {
  rapidfuzz = require('rapidfuzz');
  console.log('✅ RapidFuzz C++ 引擎加载成功');
} catch (e) {
  console.log('⚠️  RapidFuzz 未安装，使用纯 JavaScript 回退');
}

// ============================================================================
// V6.7: 配置常量 (2026 年更新)
// ============================================================================

// 联赛配置 - 支持赛季参数化
const LEAGUE_CONFIGS = {
  'EPL': {
    name: 'Premier League',
    country: 'england',
    slug: 'premier-league',
    league_id: 47
  },
  'LALIGA': {
    name: 'La Liga',
    country: 'spain',
    slug: 'laliga',
    league_id: 87
  },
  'BUNDESLIGA': {
    name: 'Bundesliga',
    country: 'germany',
    slug: 'bundesliga',
    league_id: 54
  },
  'SERIEA': {
    name: 'Serie A',
    country: 'italy',
    slug: 'serie-a',
    league_id: 98
  },
  'LIGUE1': {
    name: 'Ligue 1',
    country: 'france',
    slug: 'ligue-1',
    league_id: 53
  }
};

// V6.7: 2026 年 OddsPortal 选择器映射 (多层 Fallback)
const SELECTOR_MAP = {
  // 比赛行选择器链 (从精确到模糊)
  matchRow: [
    'div[role="row"]',                    // 2026 新结构
    'div[data-testid*="event"]',          // data-testid 属性
    '[class*="event-row"]',               // CSS 类名包含
    '[class*="EventRow"]',                // 大驼峰变体
    'div[class*="sportName"]',            // 运动类型容器
    'a[href*="/football/"]',              // 最后防线：足球链接
    'a[href*="/soccer/"]'                 // 备选：soccer 路径
  ],

  // 队名元素
  teamName: [
    '[class*="team-name"]',
    '[class*="TeamName"]',
    'span[class*="name"]',
    'div[class*="participant"]'
  ],

  // 比赛 URL
  matchUrl: [
    'a[href*="/football/"]',
    'a[href*="/soccer/"]'
  ],

  // 赔率容器
  oddsContainer: [
    '[class*="odds-table"]',
    '[class*="OddsTable"]',
    '[class*="odds-container"]',
    'div[class*="odds"]'
  ],

  // 基于文本的防御性选择器
  textBased: [
    'text=/\\d+\\.\\d{2}/',                // 包含赔率数字
    'text=/FT|Final|Result/i',            // 比赛状态
    'has-text("-")'                       // 包含连字符
  ]
};

// V6.7: URL 模式正则
const URL_PATTERNS = {
  results: /\/football\/[^\/]+\/[^\/]+-\d{4}-\d{4}\/results\//,
  match: /\/football\/[^\/]+\/[^\/]+\/[^\/]+-[a-zA-Z0-9]{8}\/$/,
  hash: /-([a-zA-Z0-9]{8})\$/
};

// ============================================================================
// V6.7: 队名映射与标准化
// ============================================================================

/**
 * 五大联赛常见队名词典 (OddsPortal slug 格式)
 * 用于贪婪匹配解析形如 "brentford-newcastle-utd" 的 slug
 */
const COMMON_TEAM_SLUGS = [
  // Premier League
  'arsenal', 'aston-villa', 'bournemouth', 'brentford', 'brighton',
  'burnley', 'chelsea', 'crystal-palace', 'everton', 'fulham',
  'liverpool', 'luton', 'man-city', 'man-united', 'newcastle-utd',
  'nottingham-forest', 'sheffield-utd', 'tottenham', 'west-ham', 'wolves',
  // La Liga
  'alaves', 'almeria', 'athletic-bilbao', 'atletico-madrid', 'barcelona',
  'cadiz', 'celta-vigo', 'getafe', 'girona', 'granada',
  'las-palmas', 'mallorca', 'osasuna', 'rayo-vallecano', 'real-betis',
  'real-madrid', 'real-sociedad', 'sevilla', 'valencia', 'villarreal',
  // Bundesliga
  'augsburg', 'bayer-leverkusen', 'bayern-munich', 'bochum', 'darmstadt',
  'dortmund', 'eintracht-frankfurt', 'freiburg', 'heidenheim', 'hoffenheim',
  'koln', 'mainz', 'monchengladbach', 'rb-leipzig', 'stuttgart',
  'union-berlin', 'werder-bremen', 'wolfsburg',
  // Serie A
  'atalanta', 'bologna', 'cagliari', 'empoli', 'fiorentina',
  'frosinone', 'genoa', 'inter', 'juventus', 'lazio',
  'lecce', 'milan', 'monza', 'napoli', 'roma',
  'salernitana', 'sassuolo', 'torino', 'udinese', 'verona',
  // Ligue 1
  'brest', 'clermont', 'le-havre', 'lens', 'lille',
  'lorient', 'lyon', 'marseille', 'metz', 'monaco',
  'montpellier', 'nantes', 'nice', 'psg', 'reims',
  'rennes', 'strasbourg', 'toulouse'
];

/**
 * 英超队名映射表: OddsPortal 格式 -> 数据库标准格式
 */
const TEAM_NAME_MAPPINGS = {
  // Manchester teams
  'man united': 'Manchester United',
  'man utd': 'Manchester United',
  'manchester united': 'Manchester United',
  'man city': 'Manchester City',
  'manchester city': 'Manchester City',

  // Newcastle
  'newcastle utd': 'Newcastle United',
  'newcastle united': 'Newcastle United',
  'newcastle': 'Newcastle United',

  // Wolves
  'wolverhampton': 'Wolverhampton Wanderers',
  'wolves': 'Wolverhampton Wanderers',
  'wolverhampton wanderers': 'Wolverhampton Wanderers',

  // Tottenham
  'tottenham': 'Tottenham Hotspur',
  'spurs': 'Tottenham Hotspur',
  'tottenham hotspur': 'Tottenham Hotspur',

  // West Ham
  'west ham': 'West Ham United',
  'west ham utd': 'West Ham United',
  'west ham united': 'West Ham United',

  // Nottingham Forest
  'nottingham': 'Nottingham Forest',
  'nottingham forest': 'Nottingham Forest',
  'n forest': 'Nottingham Forest',

  // Brighton
  'brighton': 'Brighton & Hove Albion',
  'brighton hove albion': 'Brighton & Hove Albion',

  // Sheffield United
  'sheffield utd': 'Sheffield United',
  'sheffield united': 'Sheffield United',

  // Luton
  'luton': 'Luton',
  'luton town': 'Luton',

  // Bournemouth
  'bournemouth': 'AFC Bournemouth',
  'afc bournemouth': 'AFC Bournemouth',

  // Standard names
  'arsenal': 'Arsenal',
  'aston villa': 'Aston Villa',
  'brentford': 'Brentford',
  'burnley': 'Burnley',
  'chelsea': 'Chelsea',
  'crystal palace': 'Crystal Palace',
  'everton': 'Everton',
  'fulham': 'Fulham',
  'liverpool': 'Liverpool'
};

// ============================================================================
// V6.7: 核心函数 (导出供测试)
// ============================================================================

/**
 * 构建历史结果页 URL
 * @param {Object} leagueConfig - 联赛配置
 * @param {String} season - 赛季格式 2023-2024
 * @returns {String} 完整 URL
 */
function buildResultsUrl(leagueConfig, season) {
  const [startYear, endYear] = season.split('-');
  return `https://www.oddsportal.com/football/${leagueConfig.country}/${leagueConfig.slug}-${startYear}-${endYear}/results/#/`;
}

/**
 * 标准化队名 - 将 OddsPortal slug 转换为数据库标准格式
 * @param {String} slug - 队名 slug
 * @returns {String} 标准化队名
 */
function normalizeTeamName(slug) {
  if (!slug) return '';

  const normalized = slug
    .toLowerCase()
    .replace(/-/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();

  if (TEAM_NAME_MAPPINGS[normalized]) {
    return TEAM_NAME_MAPPINGS[normalized];
  }

  return normalized
    .split(' ')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

/**
 * 从 OddsPortal URL slug 提取队名
 * 支持格式: "arsenal-everton" / "manchester-united-chelsea" / "brentford-newcastle-utd"
 * 算法: 贪婪匹配 - 从词典中找最长匹配作为主队，剩余部分作为客队
 * @param {String} slug - URL slug
 * @returns {Object} { homeTeam, awayTeam }
 */
function extractTeamsFromSlug(slug) {
  if (!slug) return { homeTeam: 'Unknown', awayTeam: 'Unknown' };

  // 先尝试 -vs- 格式 (旧格式兼容)
  const vsMatch = slug.match(/^(.+?)-vs-(.+)$/);
  if (vsMatch) {
    return {
      homeTeam: normalizeTeamName(vsMatch[1]),
      awayTeam: normalizeTeamName(vsMatch[2])
    };
  }

  // 贪婪匹配算法: 从 slug 开头匹配最长的可能队名
  const parts = slug.split('-');
  let bestHomeMatch = null;
  let bestHomeLen = 0;

  for (const teamSlug of COMMON_TEAM_SLUGS) {
    const teamParts = teamSlug.split('-');

    if (parts.length >= teamParts.length) {
      const slugPrefix = parts.slice(0, teamParts.length).join('-');
      if (slugPrefix === teamSlug && teamParts.length > bestHomeLen) {
        bestHomeMatch = teamSlug;
        bestHomeLen = teamParts.length;
      }
    }
  }

  if (bestHomeMatch) {
    const awayParts = parts.slice(bestHomeLen);
    const awaySlug = awayParts.join('-');

    if (awayParts.length > 0) {
      return {
        homeTeam: normalizeTeamName(bestHomeMatch),
        awayTeam: normalizeTeamName(awaySlug)
      };
    }
  }

  // 备用方案: 尝试 50/50 分割
  const mid = Math.ceil(parts.length / 2);
  const homeGuess = parts.slice(0, mid).join('-');
  const awayGuess = parts.slice(mid).join('-');

  return {
    homeTeam: normalizeTeamName(homeGuess),
    awayTeam: normalizeTeamName(awayGuess)
  };
}

/**
 * V6.7: RapidFuzz 增强版相似度计算
 * @param {String} name1 - 队名1
 * @param {String} name2 - 队名2
 * @returns {Number} 相似度 0-1
 */
function calculateSimilarity(name1, name2) {
  const n1 = name1.toLowerCase().trim();
  const n2 = name2.toLowerCase().trim();

  if (n1 === n2) return 1.0;

  // V6.7: 使用 RapidFuzz 如果可用
  if (rapidfuzz) {
    try {
      // 使用 WRatio 算法，支持部分匹配和排序
      const score = rapidfuzz.fuzz.WRatio(n1, n2);
      return score / 100; // 转换为 0-1
    } catch (e) {
      // RapidFuzz 失败，回退到 JS 实现
    }
  }

  // V6.7: 增强版 JS 回退算法
  // 1. 检查包含关系
  if (n1.includes(n2) || n2.includes(n1)) return 0.9;

  // 2. 词级别相似度 (Jaccard)
  const words1 = new Set(n1.split(/\s+/));
  const words2 = new Set(n2.split(/\s+/));
  const intersection = new Set([...words1].filter(x => words2.has(x)));
  const union = new Set([...words1, ...words2]);
  const jaccard = intersection.size / union.size;

  // 3. 字符级别相似度 (Levenshtein 近似)
  const longer = n1.length > n2.length ? n1 : n2;
  const shorter = n1.length > n2.length ? n2 : n1;
  const editDistance = longer.split('').filter((c, i) =>
    shorter[i] !== undefined && shorter[i] !== c
  ).length + Math.abs(longer.length - shorter.length);
  const levenshteinSim = 1 - (editDistance / longer.length);

  // 综合评分
  return Math.max(jaccard * 0.8, levenshteinSim * 0.7);
}

/**
 * 转换 season 格式: 2023-2024 -> 2023/2024
 * @param {String} season - 原始赛季格式
 * @returns {String} 数据库格式
 */
function formatSeasonForDb(season) {
  return season.replace('-', '/');
}

// ============================================================================
// V6.7: 侦察核心逻辑
// ============================================================================

/**
 * 侦察单个联赛的历史结果页
 * @param {Object} page - Playwright page
 * @param {Object} leagueConfig - 联赛配置
 * @param {String} season - 赛季
 * @returns {Array} 比赛 URL 列表
 */
async function reconLeagueSeason(page, leagueConfig, season) {
  const resultsUrl = buildResultsUrl(leagueConfig, season);
  console.log(`\n🔍 [RECON] 侦察 ${leagueConfig.name} ${season}赛季...`);
  console.log(`   URL: ${resultsUrl}`);

  const matchUrls = [];

  try {
    // V6.7: 访问历史结果页
    await page.goto(resultsUrl, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForTimeout(5000);

    // V6.7: 使用标准 CSS 选择器等待加载 (修复 XPath 非标语法)
    try {
      // 尝试多个选择器，直到有一个成功
      for (const selector of SELECTOR_MAP.matchRow.slice(0, 3)) {
        try {
          await page.waitForSelector(selector, { timeout: 5000 });
          console.log(`   ✅ 页面加载成功，使用选择器: ${selector}`);
          break;
        } catch (e) {
          // 继续尝试下一个
        }
      }
    } catch (e) {
      console.log('   ⚠️  等待选择器超时，继续执行...');
    }

    // V6.7: 多次滚动加载更多比赛
    console.log('   📜 滚动加载历史比赛...');
    for (let i = 0; i < 10; i++) {
      await page.evaluate(() => window.scrollBy(0, 1000));
      await page.waitForTimeout(2000);

      if (i % 3 === 0) {
        const currentCount = await page.evaluate(() =>
          document.querySelectorAll('a[href*="/football/"]').length
        );
        console.log(`      滚动 ${i + 1}/10 - 发现 ${currentCount} 个链接`);
      }
    }

    // V6.7: 提取所有比赛 URL
    const urls = await page.evaluate((leagueName, selectors) => {
      const links = [];

      // 尝试多种选择器 (修复 contains(@class) 语法)
      let anchors = [];
      for (const selector of selectors) {
        anchors = document.querySelectorAll(selector);
        if (anchors.length > 0) break;
      }

      anchors.forEach(a => {
        const href = a.getAttribute('href') || '';

        // V6.7: 匹配格式: /football/{country}/{league}/{team1}-{team2}-{hash}/
        const match = href.match(/\/football\/[^\/]+\/[^\/]+\/([^\/]+)-([a-zA-Z0-9]{8})\/$/);

        if (match) {
          const fullUrl = href.startsWith('http') ? href : 'https://www.oddsportal.com' + href;
          const slug = match[1];
          const hash = match[2];

          // V6.7: 使用标准 CSS 选择器定位父元素
          const row = a.closest('tr, div[role="row"], [class*="event"], div');
          const text = row ? row.textContent : a.textContent;

          links.push({
            url: fullUrl,
            slug: slug,
            hash: hash,
            text: text?.trim() || '',
            league: leagueName
          });
        }
      });

      return links;
    }, leagueConfig.name, SELECTOR_MAP.matchRow);

    // 去重
    const seen = new Set();
    urls.forEach(item => {
      if (!seen.has(item.url)) {
        seen.add(item.url);
        matchUrls.push(item);
      }
    });

    console.log(`   ✅ 侦察到 ${matchUrls.length} 个历史比赛URL`);

    if (matchUrls.length > 0) {
      console.log('   📋 URL样本:');
      matchUrls.slice(0, 3).forEach((item, i) => {
        console.log(`      [${i+1}] ${item.slug} | Hash: ${item.hash}`);
      });
    }

  } catch (e) {
    console.log(`   ❌ 侦察失败: ${e.message}`);
  }

  return matchUrls;
}

// ============================================================================
// V6.7: Repository 模式对齐
// ============================================================================

/**
 * V6.7: 使用 Repository 模式保存映射
 * @param {FixtureRepository} repository - Repository 实例
 * @param {Array} matches - 比赛列表
 * @param {String} season - 赛季
 * @param {Object} leagueConfig - 联赛配置
 * @returns {Object} 统计结果
 */
async function saveToRepository(repository, matches, season, leagueConfig) {
  console.log(`\n💾 保存到 Repository (执行队名对齐)...`);

  let inserted = 0;
  let skipped = 0;
  let unmatched = 0;
  const unmatchedList = [];

  for (const match of matches) {
    try {
      // 提取并标准化队名
      const { homeTeam, awayTeam } = extractTeamsFromSlug(match.slug);

      if (homeTeam === 'Unknown' || awayTeam === 'Unknown') {
        console.log(`   ⚠️  无法解析队名: ${match.slug}`);
        unmatched++;
        continue;
      }

      // V6.7: 使用 Repository 查找真实 match_id
      const dbSeason = formatSeasonForDb(season);
      const matchInfo = await repository.findMatchByTeams(homeTeam, awayTeam, dbSeason);

      if (!matchInfo) {
        console.log(`   ⚠️  未找到匹配: ${homeTeam} vs ${awayTeam}`);
        unmatchedList.push({ slug: match.slug, home: homeTeam, away: awayTeam });
        unmatched++;
        continue;
      }

      // V6.7: 使用 Repository 保存映射
      const mappingData = {
        match_id: matchInfo.matchId,
        oddsportal_hash: match.hash,
        full_url: match.url,
        season: season,
        league_name: leagueConfig.name,
        home_team: homeTeam,
        away_team: awayTeam,
        match_confidence: matchInfo.confidence,
        mapping_method: matchInfo.method,
        status: 'pending'
      };

      const result = await repository.saveOddsPortalMapping(mappingData);

      if (result.success) {
        inserted++;
        if (matchInfo.method === 'fuzzy') {
          console.log(`   🔗 模糊匹配 [${matchInfo.confidence.toFixed(2)}]: ${homeTeam} vs ${awayTeam} -> ${matchInfo.dbHome} vs ${matchInfo.dbAway}`);
        }
      } else {
        skipped++;
      }

    } catch (e) {
      console.log(`   ❌ 保存失败 ${match.hash}: ${e.message}`);
      unmatched++;
    }
  }

  console.log(`\n   ✅ 成功缝合: ${inserted} | ⏭️ 已存在: ${skipped} | ❓ 未匹配: ${unmatched}`);

  if (unmatchedList.length > 0) {
    console.log(`   ⚠️  未匹配项 (前5个):`);
    unmatchedList.slice(0, 5).forEach(u => {
      console.log(`      - ${u.home} vs ${u.away} (${u.slug})`);
    });
  }

  return { inserted, skipped, unmatched };
}

// ============================================================================
// V6.7: 主函数
// ============================================================================

async function main() {
  // 解析参数
  const args = process.argv.slice(2);
  const seasonIndex = args.indexOf('--season');
  const leagueIndex = args.indexOf('--league');
  const allLeaguesFlag = args.includes('--all-leagues');
  const headlessFlag = args.includes('--headless');

  const season = seasonIndex !== -1 ? args[seasonIndex + 1] : '2023-2024';
  const targetLeague = leagueIndex !== -1 ? args[leagueIndex + 1].toUpperCase() : 'EPL';

  console.log('\n╔══════════════════════════════════════════════════════════════════╗');
  console.log('║     🔍 TITAN V6.7 RECON SCANNER - 历史赛季测绘 🔍              ║');
  console.log('╠══════════════════════════════════════════════════════════════════╣');
  console.log(`║     目标赛季: ${season.padEnd(45)} ║`);
  console.log(`║     目标联赛: ${(allLeaguesFlag ? '全部联赛' : LEAGUE_CONFIGS[targetLeague]?.name || targetLeague).padEnd(45)} ║`);
  console.log(`║     模式: ${(headlessFlag ? '无头模式' : '可视化模式').padEnd(49)} ║`);
  console.log(`║     RapidFuzz: ${(rapidfuzz ? '✅ 已启用' : '⚠️  JS回退').padEnd(43)} ║`);
  console.log('╚══════════════════════════════════════════════════════════════════╝\n');

  let browser = null;
  let repository = null;

  // 初始化代理轮询器
  const proxyRotator = new ProxyRotator({ strategy: 'round-robin' });
  const PROXY_HOST = process.env.PROXY_HOST || '172.25.16.1';

  try {
    // V6.7: 初始化 Repository
    repository = new FixtureRepository({});
    await repository.init();
    console.log('✅ Repository 初始化完成');

    // 获取代理
    const proxy = proxyRotator.getNextProxy();
    const proxyServer = `http://${PROXY_HOST}:${proxy.port}`;
    console.log(`🔌 使用代理: ${proxyServer}`);

    // 启动浏览器
    console.log('🚀 启动浏览器...');
    browser = await chromium.launch({
      headless: headlessFlag,
      args: [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--window-size=1920,1080',
        `--proxy-server=${proxyServer}`
      ]
    });

    const context = await browser.newContext({
      viewport: { width: 1920, height: 1080 },
      userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    });

    const page = await context.newPage();

    // 确定要扫描的联赛
    const leaguesToScan = allLeaguesFlag
      ? Object.values(LEAGUE_CONFIGS)
      : [LEAGUE_CONFIGS[targetLeague] || LEAGUE_CONFIGS['EPL']];

    const allMatches = [];

    // 扫描每个联赛
    for (const league of leaguesToScan) {
      const matches = await reconLeagueSeason(page, league, season);

      if (matches.length > 0) {
        // V6.7: 使用 Repository 保存
        const { inserted } = await saveToRepository(repository, matches, season, league);
        allMatches.push(...matches);

        console.log(`   📊 ${league.name}: +${inserted} 条新记录`);
      }

      // 联赛间延迟
      if (league !== leaguesToScan[leaguesToScan.length - 1]) {
        console.log('   ⏳ 等待3秒...');
        await new Promise(r => setTimeout(r, 3000));
      }
    }

    // 关闭浏览器
    await context.close();
    await browser.close();

    // V6.7: 使用 Repository 获取统计
    const stats = await repository.getMappingStats(season);

    console.log('\n╔══════════════════════════════════════════════════════════════════╗');
    console.log('║     ✅ RECON SCANNER 测绘完成 ✅                               ║');
    console.log('╠══════════════════════════════════════════════════════════════════╣');
    console.log(`║     本次扫描URL: ${String(allMatches.length).padStart(3)}                                        ║`);
    console.log(`║     数据库总计: ${String(stats.total).padStart(3)} (${stats.pending} 待收割 / ${stats.harvested} 已完成)      ║`);
    console.log(`║     赛季: ${season.padEnd(49)} ║`);
    console.log('╚══════════════════════════════════════════════════════════════════╝\n');

    console.log('💡 下一步:');
    console.log('   node scripts/ops/titan_grand_backfill.js --season ' + season);

  } catch (error) {
    console.error('\n💥 测绘失败:', error.message);
    if (browser) await browser.close();
    if (repository) await repository.close();
    process.exit(1);
  } finally {
    if (repository) await repository.close();
  }
}

// 运行
if (require.main === module) {
  main().catch(console.error);
}

// V6.7: 导出供测试
module.exports = {
  reconLeagueSeason,
  buildResultsUrl,
  extractTeamsFromSlug,
  normalizeTeamName,
  calculateSimilarity,
  formatSeasonForDb,
  LEAGUE_CONFIGS,
  SELECTOR_MAP,
  URL_PATTERNS,
  COMMON_TEAM_SLUGS,
  TEAM_NAME_MAPPINGS
};
