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
 * 保存到数据库 mapping 表
 */
async function saveToDatabase(pool, matches, season, leagueConfig) {
  console.log(`\n💾 保存到数据库...`);
  
  let inserted = 0;
  let skipped = 0;
  
  for (const match of matches) {
    try {
      // 从 slug 解析队名
      const teams = match.slug.split('-vs-');
      let homeTeam = teams[0] || match.slug.split('-')[0] || 'Unknown';
      let awayTeam = teams[1] || match.slug.split('-').slice(1).join('-') || 'Unknown';
      
      // 生成 match_id（如果没有）
      const matchId = `${leagueConfig.league_id}_${season.replace('-', '')}_${match.hash}`;
      
      const query = `
        INSERT INTO matches_oddsportal_mapping 
          (match_id, oddsportal_hash, full_url, season, league_name, home_team, away_team, status)
        VALUES ($1, $2, $3, $4, $5, $6, $7, 'pending')
        ON CONFLICT (match_id, season) DO NOTHING
        RETURNING match_id;
      `;
      
      const result = await pool.query(query, [
        matchId,
        match.hash,
        match.url,
        season,
        leagueConfig.name,
        homeTeam.replace(/-/g, ' '),
        awayTeam.replace(/-/g, ' ')
      ]);
      
      if (result.rows.length > 0) {
        inserted++;
      } else {
        skipped++;
      }
      
    } catch (e) {
      console.log(`   ❌ 保存失败 ${match.hash}: ${e.message}`);
    }
  }
  
  console.log(`   ✅ 新增: ${inserted} | ⏭️ 跳过(已存在): ${skipped}`);
  return { inserted, skipped };
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