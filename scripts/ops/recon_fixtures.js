/**
 * TITAN V6.0 RECON FIXTURES - 战前侦察子程序
 * ===========================================
 * 访问OddsPortal赛程列表页，提取带Hash的真实比赛URL
 * 
 * @module scripts/ops/recon_fixtures
 * @version V6.0-RECON
 * @date 2026-03-16
 */

'use strict';

const { chromium } = require('playwright');
const { Pool } = require('pg');
const fs = require('fs');
const path = require('path');

// 数据库配置
const DB_CONFIG = {
  host: '127.0.0.1',
  port: 5432,
  database: 'football_db',
  user: 'football_user',
  password: process.env.DB_PASSWORD || 'football_pass',
};

// 联赛列表页配置 - 使用主页面而非fixtures子页
const LEAGUE_PAGES = [
  { name: 'Premier League', url: 'https://www.oddsportal.com/football/england/premier-league/' },
  { name: 'La Liga', url: 'https://www.oddsportal.com/football/spain/laliga/' },
  { name: 'Bundesliga', url: 'https://www.oddsportal.com/football/germany/bundesliga/' }
];

/**
 * 侦察单个联赛的所有比赛URL
 */
async function reconLeague(page, leagueConfig) {
  console.log(`\n🔍 [RECON] 侦察 ${leagueConfig.name}...`);
  console.log(`   URL: ${leagueConfig.url}`);
  
  const matchUrls = [];
  
  try {
    // 访问列表页
    await page.goto(leagueConfig.url, { waitUntil: 'load', timeout: 60000 });
    await page.waitForTimeout(3000);
    
    // 滚动加载更多比赛
    for (let i = 0; i < 5; i++) {
      await page.evaluate(() => window.scrollBy(0, 800));
      await page.waitForTimeout(1500);
    }
    
    // 提取所有比赛URL
    const urls = await page.evaluate(() => {
      const links = [];
      const anchors = document.querySelectorAll('a[href*="/football/"]');
      
      anchors.forEach(a => {
        const href = a.getAttribute('href');
        // 匹配格式: /football/{country}/{league}/{team1}-{team2}-{hash}/
        const match = href.match(/\/football\/[^\/]+\/[^\/]+\/([^\/]+)-([a-zA-Z0-9]{8})\/$/);
        if (match) {
          const fullUrl = href.startsWith('http') ? href : 'https://www.oddsportal.com' + href;
          const slug = match[1]; // e.g., "fulham-burnley"
          const hash = match[2]; // e.g., "8EamNN8b"
          
          links.push({
            url: fullUrl,
            slug: slug,
            hash: hash,
            text: a.textContent?.trim() || ''
          });
        }
      });
      
      return links;
    });
    
    // 去重
    const seen = new Set();
    urls.forEach(item => {
      if (!seen.has(item.url)) {
        seen.add(item.url);
        matchUrls.push(item);
      }
    });
    
    console.log(`   ✅ 侦察到 ${matchUrls.length} 个比赛URL`);
    
    // 显示样本
    if (matchUrls.length > 0) {
      console.log('   📋 URL样本:');
      matchUrls.slice(0, 3).forEach((item, i) => {
        console.log(`      [${i+1}] ${item.slug} | Hash: ${item.hash}`);
        console.log(`          ${item.url}`);
      });
    }
    
  } catch (e) {
    console.log(`   ❌ 侦察失败: ${e.message}`);
  }
  
  return matchUrls;
}

/**
 * 标准化队名用于匹配
 */
function normalizeTeamName(name) {
  return name.toLowerCase()
    .replace(/[^a-z0-9\s]/g, '') // 移除特殊字符
    .replace(/\s+/g, ' ')        // 合并多个空格
    .trim()
    .split(' ')
    .filter(w => w.length > 1 && !['fc', 'cf', 'sv', 'sc', 'vfb', '1', '05'].includes(w));
}

/**
 * 建立StrikeMap：将侦察URL与DB队名对齐
 */
async function buildStrikeMap(pool, reconData) {
  console.log('\n🎯 [STRIKE MAP] 建立目标对齐映射...');
  
  // 从DB获取待匹配比赛
  const query = `
    SELECT match_id, home_team, away_team, league_name 
    FROM matches 
    WHERE league_name IN ('Premier League', 'La Liga', 'Bundesliga')
    AND match_date > NOW()
    LIMIT 100;
  `;
  
  const dbMatches = await pool.query(query);
  console.log(`   📊 DB中待匹配比赛: ${dbMatches.rows.length} 场`);
  console.log(`   📊 侦察URL数量: ${reconData.length} 个`);
  
  const strikeMap = {};
  const reconReport = [];
  
  for (const match of dbMatches.rows) {
    // 标准化队名
    const homeWords = normalizeTeamName(match.home_team);
    const awayWords = normalizeTeamName(match.away_team);
    
    // 在侦察数据中查找匹配
    let bestMatch = null;
    let bestScore = 0;
    
    for (const recon of reconData) {
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
      
      // 联赛匹配加分
      if (recon.league === match.league_name) {
        score += 2;
      }
      
      // 如果主队和客队都有至少一个词匹配，这是高置信度匹配
      if (homeMatched > 0 && awayMatched > 0) {
        score += 10;
      }
      
      if (score > bestScore) {
        bestScore = score;
        bestMatch = recon;
      }
    }
    
    // 阈值：至少6分（主队+客队各一个词）
    const matched = bestMatch && bestScore >= 6;
    
    if (matched) {
      strikeMap[match.match_id] = {
        url: bestMatch.url,
        match_name: `${match.home_team} vs ${match.away_team}`,
        league: match.league_name,
        confidence: bestScore,
        hash: bestMatch.hash
      };
    }
    
    reconReport.push({
      match_id: match.match_id,
      match_name: `${match.home_team} vs ${match.away_team}`,
      league: match.league_name,
      matched: matched,
      confidence: bestScore,
      url: matched ? bestMatch.url : null
    });
  }
  
  console.log(`   ✅ StrikeMap建立完成: ${Object.keys(strikeMap).length} 个目标`);
  return { strikeMap, reconReport };
}

/**
 * 保存侦察结果
 */
async function saveReconResults(strikeMap, reconReport) {
  const timestamp = Date.now();
  const reconDir = path.join(process.cwd(), 'data/recon');
  
  if (!fs.existsSync(reconDir)) {
    fs.mkdirSync(reconDir, { recursive: true });
  }
  
  // 保存StrikeMap
  const strikeMapPath = path.join(reconDir, `strike_map_${timestamp}.json`);
  fs.writeFileSync(strikeMapPath, JSON.stringify(strikeMap, null, 2));
  console.log(`\n💾 StrikeMap已保存: ${strikeMapPath}`);
  
  // 保存侦察报告
  const reportPath = path.join(reconDir, `recon_report_${timestamp}.json`);
  fs.writeFileSync(reportPath, JSON.stringify({
    timestamp: new Date().toISOString(),
    total_targets: reconReport.length,
    matched: reconReport.filter(r => r.matched).length,
    unmatched: reconReport.filter(r => !r.matched).length,
    details: reconReport
  }, null, 2));
  console.log(`💾 侦察报告已保存: ${reportPath}`);
  
  return { strikeMapPath, reportPath };
}

/**
 * 显示侦察成果表
 */
function showReconTable(reconReport) {
  console.log('\n📊 侦察成果表 (前10场):');
  console.log('─'.repeat(100));
  console.log(`${'Match'.padEnd(40)} | ${'League'.padEnd(12)} | Status | URL`);
  console.log('─'.repeat(100));
  
  reconReport.slice(0, 10).forEach(r => {
    const match = r.match_name.slice(0, 37);
    const league = r.league.slice(0, 10);
    const status = r.matched ? '✅' : '❌';
    const url = r.url ? r.url.slice(-30) : 'N/A';
    console.log(`${match.padEnd(40)} | ${league.padEnd(12)} | ${status} | ...${url}`);
  });
  
  console.log('─'.repeat(100));
}

/**
 * 主函数
 */
async function runReconnaissance() {
  console.log('\n╔══════════════════════════════════════════════════════════════════╗');
  console.log('║     🔍 TITAN V6.0 RECON FIXTURES - 战前侦察 🔍                 ║');
  console.log('║     提取真实URL，建立精确打击地图                              ║');
  console.log('╚══════════════════════════════════════════════════════════════════╝\n');
  
  const pool = new Pool(DB_CONFIG);
  let browser = null;
  let context = null;
  
  try {
    // 启动浏览器
    console.log('🚀 启动浏览器...');
    browser = await chromium.launch({
      headless: false,
      args: [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--window-size=1920,1080'
      ]
    });
    
    context = await browser.newContext({
      viewport: { width: 1920, height: 1080 },
      userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    });
    
    const page = await context.newPage();
    
    // 侦察所有联赛
    const allReconData = [];
    
    for (const league of LEAGUE_PAGES) {
      const urls = await reconLeague(page, league);
      urls.forEach(u => {
        u.league = league.name;
        allReconData.push(u);
      });
      
      // 联赛间延迟
      if (league !== LEAGUE_PAGES[LEAGUE_PAGES.length - 1]) {
        await new Promise(r => setTimeout(r, 3000));
      }
    }
    
    console.log(`\n📊 侦察完成: 共 ${allReconData.length} 个URL`);
    
    // 建立StrikeMap
    const { strikeMap, reconReport } = await buildStrikeMap(pool, allReconData);
    
    // 显示成果表
    showReconTable(reconReport);
    
    // 保存结果
    await saveReconResults(strikeMap, reconReport);
    
    // 统计
    const matchedCount = Object.keys(strikeMap).length;
    const totalCount = reconReport.length;
    const matchRate = ((matchedCount / totalCount) * 100).toFixed(1);
    
    console.log('\n╔══════════════════════════════════════════════════════════════════╗');
    console.log('║     🔍 RECON FIXTURES 侦察完成 🔍                              ║');
    console.log('╠══════════════════════════════════════════════════════════════════╣');
    console.log(`║     侦察URL总数: ${String(allReconData.length).padStart(3)}                                        ║`);
    console.log(`║     DB匹配成功: ${String(matchedCount).padStart(3)}/${String(totalCount).padStart(3)} (${String(matchRate).padStart(5)}%)                           ║`);
    console.log(`║     StrikeMap: ✅ 已生成，可用于精确打击                       ║`);
    console.log('╚══════════════════════════════════════════════════════════════════╝\n');
    
    return { strikeMap, reconReport };
    
  } catch (error) {
    console.error('\n💥 侦察失败:', error.message);
    throw error;
  } finally {
    if (context) await context.close();
    if (browser) await browser.close();
    await pool.end();
  }
}

// 运行
if (require.main === module) {
  runReconnaissance().catch(console.error);
}

module.exports = { runReconnaissance, buildStrikeMap };