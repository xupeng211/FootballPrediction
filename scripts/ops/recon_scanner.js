#!/usr/bin/env node
/**
 * TITAN V6.0 RECON SCANNER - 历史赛季测绘扫描器
 * =================================================
 * 
 * 支持扫描指定赛季的历史结果页，提取带Hash的真实比赛URL
 * 
 * 用法:
 *   node scripts/ops/recon_scanner.js --season 2023-2024 --league EPL
 *   node scripts/ops/recon_scanner.js --season 2022-2023 --all-leagues
 * 
 * @module scripts/ops/recon_scanner
 * @version V6.0-RECON-HISTORICAL
 * @date 2026-03-17
 */

'use strict';

const { chromium } = require('playwright');
const { Pool } = require('pg');
const fs = require('fs');
const path = require('path');

// 数据库配置
const DB_CONFIG = {
  host: process.env.DB_HOST || '127.0.0.1',
  port: parseInt(process.env.DB_PORT || '5432'),
  database: process.env.DB_NAME || 'football_db',
  user: process.env.DB_USER || 'football_user',
  password: process.env.DB_PASSWORD || 'football_pass',
};

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

/**
 * 构建历史结果页 URL
 * @param {Object} leagueConfig - 联赛配置
 * @param {String} season - 赛季格式 2023-2024
 */
function buildResultsUrl(leagueConfig, season) {
  // OddsPortal 历史结果页格式:
  // https://www.oddsportal.com/football/england/premier-league-2023-2024/results/
  const [startYear, endYear] = season.split('-');
  const url = `https://www.oddsportal.com/football/${leagueConfig.country}/${leagueConfig.slug}-${startYear}-${endYear}/results/#/`;
  return url;
}

/**
 * 侦察单个联赛的历史结果页
 * @param {Object} page - Playwright page
 * @param {Object} leagueConfig - 联赛配置
 * @param {String} season - 赛季
 */
async function reconLeagueSeason(page, leagueConfig, season) {
  const resultsUrl = buildResultsUrl(leagueConfig, season);
  console.log(`\n🔍 [RECON] 侦察 ${leagueConfig.name} ${season}赛季...`);
  console.log(`   URL: ${resultsUrl}`);
  
  const matchUrls = [];
  
  try {
    // 访问历史结果页
    await page.goto(resultsUrl, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForTimeout(5000);
    
    // 等待赛季选择器加载
    try {
      await page.waitForSelector('div[eventtreeid], div[contains(@class, "event")], a[href*="/football/"]', { timeout: 10000 });
    } catch (e) {
      console.log('   ⚠️  等待选择器超时，继续执行...');
    }
    
    // 多次滚动加载更多比赛
    console.log('   📜 滚动加载历史比赛...');
    for (let i = 0; i < 10; i++) {
      await page.evaluate(() => window.scrollBy(0, 1000));
      await page.waitForTimeout(2000);
      
      // 每3次滚动检查一次是否加载了更多内容
      if (i % 3 === 0) {
        const currentCount = await page.evaluate(() => 
          document.querySelectorAll('a[href*="/football/"]').length
        );
        console.log(`      滚动 ${i + 1}/10 - 发现 ${currentCount} 个链接`);
      }
    }
    
    // 提取所有比赛URL（从历史结果页）
    const urls = await page.evaluate((leagueName) => {
      const links = [];
      
      // 尝试多种选择器
      const selectors = [
        'a[href*="/football/"]',
        '[eventtreeid] a',
        '.event a',
        'table a',
        '[class*="event"] a'
      ];
      
      let anchors = [];
      for (const selector of selectors) {
        anchors = document.querySelectorAll(selector);
        if (anchors.length > 0) break;
      }
      
      anchors.forEach(a => {
        const href = a.getAttribute('href') || '';
        
        // 匹配格式: /football/{country}/{league}-{year-year}/{team1}-{team2}-{hash}/
        // 或: /football/{country}/{league}/{team1}-{team2}-{hash}/
        const match = href.match(/\/football\/[^\/]+\/[^\/]+\/([^\/]+)-([a-zA-Z0-9]{8})\/$/);
        
        if (match) {
          const fullUrl = href.startsWith('http') ? href : 'https://www.oddsportal.com' + href;
          const slug = match[1]; // e.g., "fulham-burnley"
          const hash = match[2]; // e.g., "8EamNN8b"
          
          // 从页面文本提取队名和日期
          const row = a.closest('tr, div[eventtreeid], [class*="event"]');
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
    }, leagueConfig.name);
    
    // 去重
    const seen = new Set();
    urls.forEach(item => {
      if (!seen.has(item.url)) {
        seen.add(item.url);
        matchUrls.push(item);
      }
    });
    
    console.log(`   ✅ 侦察到 ${matchUrls.length} 个历史比赛URL`);
    
    // 显示样本
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

/**
 * 英超队名映射表: OddsPortal 格式 -> 数据库标准格式
 * 【关键】必须与 matches 表中的队名完全一致！
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
  
  // Brighton (注意数据库中的格式)
  'brighton': 'Brighton & Hove Albion',
  'brighton hove albion': 'Brighton & Hove Albion',
  
  // Sheffield United
  'sheffield utd': 'Sheffield United',
  'sheffield united': 'Sheffield United',
  
  // Luton (数据库中是 Luton)
  'luton': 'Luton',
  'luton town': 'Luton',
  
  // Bournemouth (数据库中是 AFC Bournemouth)
  'bournemouth': 'AFC Bournemouth',
  'afc bournemouth': 'AFC Bournemouth',
  
  // Standard names (数据库中就是这些)
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

/**
 * 标准化队名 - 将 OddsPortal slug 转换为数据库标准格式
 * 例如: "manchester-united" -> "Manchester United"
 */
function normalizeTeamName(slug) {
  if (!slug) return '';
  
  // 清理格式
  const normalized = slug
    .toLowerCase()
    .replace(/-/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
  
  // 查找映射表
  if (TEAM_NAME_MAPPINGS[normalized]) {
    return TEAM_NAME_MAPPINGS[normalized];
  }
  
  // 无映射时，首字母大写
  return normalized
    .split(' ')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

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
 * 从 OddsPortal URL slug 提取队名
 * 支持格式: "arsenal-everton" / "manchester-united-chelsea" / "brentford-newcastle-utd"
 * 算法: 贪婪匹配 - 从词典中找最长匹配作为主队，剩余部分作为客队
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
  
  // 遍历所有可能的队名，找最长匹配
  for (const teamSlug of COMMON_TEAM_SLUGS) {
    const teamParts = teamSlug.split('-');
    
    // 检查 slug 是否以这个队名开头
    if (parts.length >= teamParts.length) {
      const slugPrefix = parts.slice(0, teamParts.length).join('-');
      if (slugPrefix === teamSlug && teamParts.length > bestHomeLen) {
        bestHomeMatch = teamSlug;
        bestHomeLen = teamParts.length;
      }
    }
  }
  
  if (bestHomeMatch) {
    // 提取客队 (剩余部分)
    const awayParts = parts.slice(bestHomeLen);
    const awaySlug = awayParts.join('-');
    
    if (awayParts.length > 0) {
      return {
        homeTeam: normalizeTeamName(bestHomeMatch),
        awayTeam: normalizeTeamName(awaySlug)
      };
    }
  }
  
  // 备用方案: 尝试 50/50 分割 (针对未知队名)
  const mid = Math.ceil(parts.length / 2);
  const homeGuess = parts.slice(0, mid).join('-');
  const awayGuess = parts.slice(mid).join('-');
  
  return {
    homeTeam: normalizeTeamName(homeGuess),
    awayTeam: normalizeTeamName(awayGuess)
  };
}

/**
 * 模糊匹配队名 - 计算相似度
 */
function calculateSimilarity(name1, name2) {
  const n1 = name1.toLowerCase().trim();
  const n2 = name2.toLowerCase().trim();
  
  if (n1 === n2) return 1.0;
  if (n1.includes(n2) || n2.includes(n1)) return 0.9;
  
  // 简单的词重叠计算
  const words1 = new Set(n1.split(/\s+/));
  const words2 = new Set(n2.split(/\s+/));
  const intersection = new Set([...words1].filter(x => words2.has(x)));
  const union = new Set([...words1, ...words2]);
  
  return intersection.size / union.size;
}

/**
 * 转换 season 格式: 2023-2024 -> 2023/2024
 */
function formatSeasonForDb(season) {
  return season.replace('-', '/');
}

/**
 * 查找真实 FotMob match_id
 * 策略: 标准化队名 + season 字段匹配
 * 【修复】改用 season 字段而非日期范围，适配数据库格式
 */
async function findRealMatchId(pool, homeTeam, awayTeam, season) {
  try {
    // 转换 season 格式为数据库格式 (2023-2024 -> 2023/2024)
    const dbSeason = formatSeasonForDb(season);
    
    // 1. 首先尝试精确匹配标准化队名 (忽略大小写)
    const exactQuery = `
      SELECT match_id, home_team, away_team, match_date
      FROM matches
      WHERE season = $1
        AND (
          (LOWER(home_team) = LOWER($2) AND LOWER(away_team) = LOWER($3))
          OR (LOWER(home_team) = LOWER($3) AND LOWER(away_team) = LOWER($2))
        )
      LIMIT 1;
    `;
    
    const exactResult = await pool.query(exactQuery, [
      dbSeason, homeTeam, awayTeam
    ]);
    
    if (exactResult.rows.length > 0) {
      return {
        matchId: exactResult.rows[0].match_id,
        confidence: 1.0,
        method: 'exact',
        dbHome: exactResult.rows[0].home_team,
        dbAway: exactResult.rows[0].away_team
      };
    }
    
    // 2. 精确匹配失败，尝试模糊匹配
    const fuzzyQuery = `
      SELECT match_id, home_team, away_team, match_date
      FROM matches
      WHERE season = $1
      LIMIT 50;
    `;
    
    const fuzzyResult = await pool.query(fuzzyQuery, [dbSeason]);
    
    let bestMatch = null;
    let bestScore = 0;
    
    for (const row of fuzzyResult.rows) {
      const homeScore = calculateSimilarity(homeTeam, row.home_team);
      const awayScore = calculateSimilarity(awayTeam, row.away_team);
      const avgScore = (homeScore + awayScore) / 2;
      
      // 同时检查主客场是否互换
      const swappedHomeScore = calculateSimilarity(homeTeam, row.away_team);
      const swappedAwayScore = calculateSimilarity(awayTeam, row.home_team);
      const swappedScore = (swappedHomeScore + swappedAwayScore) / 2;
      
      const finalScore = Math.max(avgScore, swappedScore);
      
      if (finalScore > bestScore && finalScore >= 0.6) {
        bestScore = finalScore;
        bestMatch = row;
      }
    }
    
    if (bestMatch) {
      return {
        matchId: bestMatch.match_id,
        confidence: bestScore,
        method: 'fuzzy',
        dbHome: bestMatch.home_team,
        dbAway: bestMatch.away_team
      };
    }
    
    // 3. 未找到匹配
    return null;
    
  } catch (e) {
    console.error(`   ❌ 查找 match_id 失败: ${e.message}`);
    return null;
  }
}

/**
 * 保存到数据库 mapping 表
 * 【修复后】使用真实 FotMob match_id，而不是伪造
 */
async function saveToDatabase(pool, matches, season, leagueConfig) {
  console.log(`\n💾 保存到数据库 (执行队名对齐)...`);
  
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
      
      // 【关键修复】查询真实的 FotMob match_id
      const matchInfo = await findRealMatchId(pool, homeTeam, awayTeam, season);
      
      if (!matchInfo) {
        console.log(`   ⚠️  未找到匹配: ${homeTeam} vs ${awayTeam}`);
        unmatchedList.push({ slug: match.slug, home: homeTeam, away: awayTeam });
        unmatched++;
        continue;
      }
      
      // 使用真实的 match_id
      const matchId = matchInfo.match_id;
      
      // 插入 mapping 表
      const query = `
        INSERT INTO matches_oddsportal_mapping 
          (match_id, oddsportal_hash, full_url, season, league_name, home_team, away_team, 
           match_confidence, mapping_method, status)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, 'pending')
        ON CONFLICT (match_id, season) DO UPDATE SET
          oddsportal_hash = EXCLUDED.oddsportal_hash,
          full_url = EXCLUDED.full_url,
          match_confidence = EXCLUDED.match_confidence,
          mapping_method = EXCLUDED.mapping_method,
          updated_at = NOW()
        RETURNING match_id;
      `;
      
      const result = await pool.query(query, [
        matchId,
        match.hash,
        match.url,
        season,
        leagueConfig.name,
        homeTeam,
        awayTeam,
        matchInfo.confidence,
        matchInfo.method
      ]);
      
      if (result.rows.length > 0) {
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

/**
 * 主函数
 */
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
  console.log('║     🔍 TITAN V6.0 RECON SCANNER - 历史赛季测绘 🔍              ║');
  console.log('╠══════════════════════════════════════════════════════════════════╣');
  console.log(`║     目标赛季: ${season.padEnd(45)} ║`);
  console.log(`║     目标联赛: ${(allLeaguesFlag ? '全部联赛' : LEAGUE_CONFIGS[targetLeague]?.name || targetLeague).padEnd(45)} ║`);
  console.log(`║     模式: ${(headlessFlag ? '无头模式' : '可视化模式').padEnd(49)} ║`);
  console.log('╚══════════════════════════════════════════════════════════════════╝\n');
  
  const pool = new Pool(DB_CONFIG);
  let browser = null;
  
  try {
    // 启动浏览器
    console.log('🚀 启动浏览器...');
    browser = await chromium.launch({
      headless: headlessFlag,
      args: ['--no-sandbox', '--disable-setuid-sandbox', '--window-size=1920,1080']
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
        // 保存到数据库
        const { inserted, skipped } = await saveToDatabase(pool, matches, season, league);
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
    
    // 最终统计
    const statsResult = await pool.query(`
      SELECT 
        COUNT(*) as total,
        COUNT(*) FILTER (WHERE status = 'pending') as pending,
        COUNT(*) FILTER (WHERE status = 'harvested') as harvested
      FROM matches_oddsportal_mapping 
      WHERE season = $1
    `, [season]);
    
    const stats = statsResult.rows[0];
    
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
    process.exit(1);
  } finally {
    await pool.end();
  }
}

// 运行
if (require.main === module) {
  main().catch(console.error);
}

module.exports = { reconLeagueSeason, buildResultsUrl, LEAGUE_CONFIGS };