/**
 * TITAN V6.0 PRECISION STRIKE - 精确URL侦察与英超实弹入库
 * ======================================================
 * 
 * 1. 侦察英超列表页提取详情页URL
 * 2. DB队名与URL模糊匹配
 * 3. API-EXCAVATOR V3深度收割
 * 4. 物理缝合入库l3_features
 * 
 * @module scripts/ops/precision_strike
 * @version V6.0-PRECISION-STRIKE
 * @date 2026-03-16
 */

'use strict';

const { Pool } = require('pg');
const { OddsPortalHarvester } = require('../../src/infrastructure/harvesters/OddsPortalHarvester');
const { ProxyRotator } = require('../../src/infrastructure/harvesters/ProxyRotator');

// V6.0 HOST-FORCE-UP: 宿主机环境检测
const isHostEnvironment = () => {
  // 检测是否在宿主机运行 (非Docker环境)
  const hasDockerEnv = require('fs').existsSync('/.dockerenv');
  const hasDockerCGroup = require('fs').existsSync('/proc/self/cgroup') &&
    require('fs').readFileSync('/proc/self/cgroup', 'utf8').includes('docker');
  return !hasDockerEnv && !hasDockerCGroup;
};

const IS_HOST_MODE = isHostEnvironment();

// V6.0 HOST-FORCE-UP: 数据库配置自适应
const DB_CONFIG = {
  host: IS_HOST_MODE ? '127.0.0.1' : (process.env.DB_HOST || 'host.docker.internal'),
  port: parseInt(process.env.DB_PORT || '5432'),
  database: process.env.DB_NAME || 'football_db',
  user: process.env.DB_USER || 'football_user',
  password: process.env.DB_PASSWORD || 'football_password',
};

if (IS_HOST_MODE) {
  console.log('🖥️  [HOST-FORCE-UP] 宿主机模式已激活');
  console.log('   📡 DB连接: 127.0.0.1:5432 (直连宿主机PostgreSQL)');
  console.log('   🎭 Browser: headless=false (可见窗口模式)');
}

// 英超列表页URL
const EPL_LISTING_URL = 'https://www.oddsportal.com/football/england/premier-league/';

/**
 * 战前侦察：访问英超列表页提取详情页URL
 */
async function reconnaissancePhase(harvester) {
  console.log('\n🔍 [Phase 1] 战前侦察 - League Reconnaissance\n');
  console.log(`🎯 目标页面: ${EPL_LISTING_URL}`);
  
  try {
    // 使用worker访问列表页
    await harvester.initialize();
    const worker = harvester.workers[0];
    worker.busy = true;
    
    if (!worker.page) {
      worker.page = await harvester.context.newPage();
    }
    
    console.log('   🔍 访问英超列表页...');
    // V6.0 HOST-FORCE-UP: 更长的超时和渐进式等待
    await worker.page.goto(EPL_LISTING_URL, {
      waitUntil: 'domcontentloaded',
      timeout: 120000
    });

    // 额外等待网络稳定
    await worker.page.waitForTimeout(5000);
    
    // 等待页面加载并滚动以触发懒加载
    console.log('   ⏳ 等待页面渲染...');
    await worker.page.waitForTimeout(5000);
    
    // 滚动页面以加载更多比赛
    for (let i = 0; i < 3; i++) {
      await worker.page.evaluate(() => {
        window.scrollBy(0, 800);
      });
      await worker.page.waitForTimeout(2000);
    }
    
    // 从页面提取所有比赛URL
    console.log('   🔍 提取比赛URL...');
    const matchUrls = await worker.page.evaluate(() => {
      const urls = [];
      
      // 方法1: 从链接中提取
      const links = document.querySelectorAll('a[href*="/football/england/premier-league/"]');
      for (const link of links) {
        const href = link.getAttribute('href');
        if (href && href.includes('/football/england/premier-league/') && 
            !href.includes('#') && 
            !href.includes('?') &&
            href.split('/').length >= 5) {
          const fullUrl = href.startsWith('http') ? href : 'https://www.oddsportal.com' + href;
          if (!urls.includes(fullUrl)) {
            urls.push(fullUrl);
          }
        }
      }
      
      return urls;
    });
    
    worker.busy = false;
    
    console.log(`✅ 侦察到 ${matchUrls.length} 个比赛URL`);
    
    // 显示前5个URL
    if (matchUrls.length > 0) {
      console.log('   📋 样本URL:');
      matchUrls.slice(0, 5).forEach((url, i) => {
        console.log(`      [${i + 1}] ${url}`);
      });
    }
    
    // 构建映射表
    const urlMapping = {};
    for (const url of matchUrls) {
      const match = url.match(/\/football\/england\/premier-league\/([^/]+)\//);
      if (match) {
        const teamPair = match[1];
        urlMapping[teamPair] = url;
      }
    }
    
    console.log(`📋 构建映射表: ${Object.keys(urlMapping).length} 个队名组合`);
    return urlMapping;
    
  } catch (error) {
    console.log(`   ❌ 侦察失败: ${error.message}`);
    console.error(error.stack);
    return {};
  }
}

/**
 * 从HTML中提取URL
 */
function extractUrlsFromHtml(html) {
  const urls = [];
  const regex = /href="(\/football\/england\/premier-league\/[^"]+)"/g;
  let match;
  
  while ((match = regex.exec(html)) !== null) {
    const url = 'https://www.oddsportal.com' + match[1];
    if (!urls.includes(url)) {
      urls.push(url);
    }
  }
  
  return urls;
}

/**
 * 简单的模糊匹配函数
 */
function fuzzyMatch(teamName, urlPart) {
  const normalize = (str) => str.toLowerCase()
    .replace(/[^a-z0-9]/g, '')
    .replace(/fc|united|city|town/g, '');
  
  const teamNorm = normalize(teamName);
  const urlNorm = normalize(urlPart);
  
  // 直接包含
  if (urlNorm.includes(teamNorm) || teamNorm.includes(urlNorm)) {
    return true;
  }
  
  // 编辑距离 <= 2
  const levenshtein = (a, b) => {
    const matrix = [];
    for (let i = 0; i <= b.length; i++) matrix[i] = [i];
    for (let j = 0; j <= a.length; j++) matrix[0][j] = j;
    
    for (let i = 1; i <= b.length; i++) {
      for (let j = 1; j <= a.length; j++) {
        matrix[i][j] = b[i-1] === a[j-1] ? 
          matrix[i-1][j-1] : 
          Math.min(matrix[i-1][j-1] + 1, matrix[i][j-1] + 1, matrix[i-1][j] + 1);
      }
    }
    return matrix[b.length][a.length];
  };
  
  return levenshtein(teamNorm, urlNorm) <= 2;
}

/**
 * 目标对齐：DB队名与侦察URL模糊匹配
 */
async function targetMappingPhase(pool, urlMapping) {
  console.log('\n🎯 [Phase 2] 目标对齐 - Target Mapping & ID Binding\n');
  
  // 从DB获取英超比赛
  const query = `
    SELECT m.match_id, m.home_team, m.away_team, m.match_date 
    FROM matches m
    WHERE m.league_name = 'Premier League'
    AND m.match_date > NOW() - INTERVAL '30 days'
    AND m.match_date > NOW()
    ORDER BY m.match_date
    LIMIT 10;
  `;
  
  const dbMatches = await pool.query(query);
  console.log(`📊 DB中英超比赛: ${dbMatches.rows.length} 场`);
  
  // 模糊匹配
  const matchedTargets = [];
  
  for (const match of dbMatches.rows) {
    const homeTeam = match.home_team.toLowerCase().replace(/\s+/g, '-');
    const awayTeam = match.away_team.toLowerCase().replace(/\s+/g, '-');
    
    // 尝试找到匹配的URL
    let matchedUrl = null;
    
    for (const [teamPair, url] of Object.entries(urlMapping)) {
      const pairLower = teamPair.toLowerCase();
      
      // 检查两队名是否都在URL中
      if ((pairLower.includes(homeTeam) || fuzzyMatch(match.home_team, teamPair)) &&
          (pairLower.includes(awayTeam) || fuzzyMatch(match.away_team, teamPair))) {
        matchedUrl = url;
        break;
      }
    }
    
    if (matchedUrl) {
      matchedTargets.push({
        match_id: match.match_id,
        home_team: match.home_team,
        away_team: match.away_team,
        match_date: match.match_date,
        recon_url: matchedUrl
      });
      console.log(`   ✅ 对齐成功: ${match.home_team} vs ${match.away_team}`);
      console.log(`      URL: ${matchedUrl}`);
    } else {
      console.log(`   ⚠️  未找到匹配: ${match.home_team} vs ${match.away_team}`);
    }
  }
  
  console.log(`\n🎯 对齐成功目标: ${matchedTargets.length} 场`);
  return matchedTargets;
}

/**
 * 深度聚焦收割
 */
async function precisionHarvest(harvester, proxyRotator, targets) {
  console.log('\n⛏️  [Phase 3] 深度聚焦收割 - API-EXCAVATOR V3\n');
  
  const results = [];
  const stats = {
    total: targets.length,
    success: 0,
    failed: 0,
    pinnacleFound: 0
  };
  
  for (let i = 0; i < targets.length; i++) {
    const target = targets[i];
    const proxy = proxyRotator.getNextProxy();
    
    console.log(`\n[${i + 1}/${targets.length}] ⛏️  ${target.home_team} vs ${target.away_team}`);
    console.log(`       🆔 Match ID: ${target.match_id}`);
    console.log(`       🔗 URL: ${target.recon_url}`);
    console.log(`       🔌 Proxy: ${proxy.port}`);
    
    try {
      const result = await harvester.harvest(target.recon_url);
      const ms = result.market_sentiment;
      
      // 验证必须有pinnacle_odds
      const hasPinnacle = ms?.pinnacle_odds?.closing?.length === 3;
      
      console.log(`       ⛏️  API-EXCAVATOR: ${ms?._apiExcavator ? '✅' : '❌'}`);
      console.log(`       🔒 Pinnacle: ${hasPinnacle ? '✅' : '❌'}`);
      
      if (hasPinnacle) {
        console.log(`       💰 Opening: ${ms.pinnacle_odds.opening?.join(' | ') || 'N/A'}`);
        console.log(`       💰 Closing: ${ms.pinnacle_odds.closing?.join(' | ')}`);
        
        const historyLen = ms.pinnacle_odds.history?.length || 0;
        console.log(`       📈 History Points: ${historyLen}`);
        
        stats.pinnacleFound++;
        stats.success++;
        
        results.push({
          target,
          market_sentiment: ms,
          status: 'success'
        });
      } else {
        console.log(`       ⚠️  未找到Pinnacle数据`);
        stats.failed++;
        results.push({
          target,
          status: 'failed',
          reason: 'pinnacle_not_found'
        });
      }
      
    } catch (error) {
      console.log(`       ❌ Error: ${error.message}`);
      stats.failed++;
      results.push({
        target,
        status: 'failed',
        reason: error.message
      });
    }
    
    // 延迟
    if (i < targets.length - 1) {
      await new Promise(r => setTimeout(r, 2000));
    }
  }
  
  console.log(`\n⛏️  收割完成: 成功 ${stats.success}/${stats.total}`);
  return results;
}

/**
 * 物理缝合入库
 */
async function fusionUpsert(pool, results) {
  console.log('\n💾 [Phase 4] 物理缝合入库 - Fusion Upsert\n');
  
  const successful = results.filter(r => r.status === 'success');
  
  if (successful.length === 0) {
    console.log('⚠️  无成功数据，跳过后续步骤');
    return [];
  }
  
  const upsertedIds = [];
  
  for (const result of successful) {
    const { target, market_sentiment } = result;
    
    try {
      const query = `
        INSERT INTO l3_features (match_id, market_sentiment, updated_at)
        VALUES ($1, $2, NOW())
        ON CONFLICT (match_id) DO UPDATE SET 
          market_sentiment = EXCLUDED.market_sentiment,
          updated_at = NOW()
        RETURNING match_id;
      `;
      
      const dbResult = await pool.query(query, [
        target.match_id,
        JSON.stringify(market_sentiment)
      ]);

      if (dbResult.rows.length > 0) {
        const insertedId = dbResult.rows[0].match_id;
        console.log(`   ✅ 入库成功: ${insertedId}`);
        console.log(`🎉 历史突破！Match ID [${insertedId}] 真实赔率已成功入库！`);
        upsertedIds.push(insertedId);
      }
    } catch (error) {
      console.log(`   ❌ 入库失败 ${target.match_id}: ${error.message}`);
    }
  }
  
  console.log(`\n💾 入库完成: ${upsertedIds.length}/${successful.length}`);
  return upsertedIds;
}

/**
 * 战报审计
 */
async function auditReport(pool, upsertedIds) {
  console.log('\n📊 [Phase 5] 战报审计 - The Proof of Gold\n');
  
  if (upsertedIds.length === 0) {
    console.log('⚠️  无入库记录');
    return;
  }
  
  const idsList = upsertedIds.map(id => `'${id}'`).join(',');
  
  const auditQuery = `
    SELECT 
      m.match_id,
      m.home_team,
      m.away_team,
      l3.market_sentiment->>'extract_method' as method,
      l3.market_sentiment->'pinnacle_odds'->'closing' as pin_closing,
      l3.market_sentiment->'pinnacle_odds'->'opening' as pin_opening,
      jsonb_array_length(COALESCE(l3.market_sentiment->'pinnacle_odds'->'history', '[]'::jsonb)) as curve_len
    FROM l3_features l3
    JOIN matches m ON l3.match_id = m.match_id
    WHERE l3.match_id IN (${idsList})
    ORDER BY l3.updated_at DESC
    LIMIT 3;
  `;
  
  const result = await pool.query(auditQuery);
  
  console.log('='.repeat(100));
  console.log('📊 实弹入库审计报告');
  console.log('='.repeat(100));
  console.log(`${'Match'.padEnd(35)} | ${'Method'.padEnd(20)} | ${'Opening'.padEnd(18)} | ${'Closing'.padEnd(18)} | Curve`);
  console.log('-'.repeat(100));
  
  for (const row of result.rows) {
    const match = `${row.home_team} vs ${row.away_team}`.slice(0, 33);
    const opening = row.pin_opening ? JSON.parse(row.pin_opening).join('/') : 'N/A';
    const closing = row.pin_closing ? JSON.parse(row.pin_closing).join('/') : 'N/A';
    const method = (row.method || 'N/A').slice(0, 18);
    
    console.log(`${match.padEnd(35)} | ${method.padEnd(20)} | ${opening.padEnd(18)} | ${closing.padEnd(18)} | ${row.curve_len || 0}`);
  }
  
  console.log('='.repeat(100));
  
  // 验证顶级字段
  const fieldCheck = await pool.query(`
    SELECT COUNT(*) as count
    FROM l3_features 
    WHERE match_id IN (${idsList})
    AND market_sentiment ? 'pinnacle_odds'
  `);
  
  console.log(`\n✅ pinnacle_odds 作为顶级字段: ${fieldCheck.rows[0].count}/${result.rows.length}`);
  
  // 验证外键
  const fkCheck = await pool.query(`
    SELECT COUNT(*) as count
    FROM l3_features l3
    JOIN matches m ON l3.match_id = m.match_id
    WHERE l3.match_id IN (${idsList})
  `);
  
  console.log(`✅ 外键约束验证: ${fkCheck.rows[0].count}/${result.rows.length}`);
}

/**
 * 主函数
 */
async function precisionStrike() {
  console.log('\n╔══════════════════════════════════════════════════════════════════╗');
  console.log('║     🎯 TITAN V6.0 PRECISION STRIKE 🎯                           ║');
  console.log('║     精确URL侦察与英超实弹入库                                   ║');
  console.log('╚══════════════════════════════════════════════════════════════════╝\n');

  // V6.0 HOST-FORCE-UP: 宿主机模式强制可见
  const harvesterOptions = IS_HOST_MODE ? { headless: false } : { headless: true };

  const pool = new Pool(DB_CONFIG);
  const harvester = new OddsPortalHarvester(harvesterOptions);
  const proxyRotator = new ProxyRotator({ strategy: 'round-robin' });
  
  try {
    // Phase 1: 侦察
    const urlMapping = await reconnaissancePhase(harvester);
    
    if (Object.keys(urlMapping).length === 0) {
      console.log('⚠️  侦察失败，任务终止');
      return;
    }
    
    // Phase 2: 对齐
    const targets = await targetMappingPhase(pool, urlMapping);
    
    if (targets.length === 0) {
      console.log('⚠️  无对齐目标，任务终止');
      return;
    }
    
    // Phase 3: 收割
    const results = await precisionHarvest(harvester, proxyRotator, targets);
    
    // Phase 4: 入库
    const upsertedIds = await fusionUpsert(pool, results);
    
    // Phase 5: 审计
    await auditReport(pool, upsertedIds);
    
    // 终极宣告
    const successCount = results.filter(r => r.status === 'success').length;
    const pinnacleCount = results.filter(r => r.market_sentiment?.pinnacle_odds?.closing).length;

    console.log('\n╔══════════════════════════════════════════════════════════════════╗');
    console.log('║     🎯 TITAN V6.0 PRECISION STRIKE 终极宣告 🎯                 ║');
    console.log('╠══════════════════════════════════════════════════════════════════╣');
    console.log(`║     侦察URL: ${String(Object.keys(urlMapping).length).padStart(3)} 个                                        ║`);
    console.log(`║     对齐目标: ${String(targets.length).padStart(2)} 场                                          ║`);
    console.log(`║     收割成功: ${String(successCount).padStart(2)} 场                                          ║`);
    console.log(`║     Pinnacle入库: ${String(pinnacleCount).padStart(2)} 场                                      ║`);
    console.log(`║     数据库实弹: ${String(upsertedIds.length).padStart(2)} 条记录                                   ║`);
    console.log('╠══════════════════════════════════════════════════════════════════╣');

    if (upsertedIds.length > 0) {
      console.log('║     ✅ l3_features表已迎来第一批"带有平博血统"的真实数据！     ║');
      console.log('║                                                                  ║');
      console.log('║     🏆 TITAN V6.0 已彻底终结"零记录"时代！                      ║');
      console.log('║        从黑暗走进光明，金砖已入库！                              ║');
      if (IS_HOST_MODE) {
        console.log('║        🖥️  宿主机强制收割协议执行完毕                           ║');
      }
    } else {
      console.log('║     ⚠️  本次未入库成功                                           ║');
    }
    console.log('╚══════════════════════════════════════════════════════════════════╝\n');
    
  } catch (error) {
    console.error('\n💥 执行失败:', error.message);
    console.error(error.stack);
  } finally {
    await harvester.close();
    await pool.end();
  }
}

// 运行
if (require.main === module) {
  precisionStrike().catch(console.error);
}

module.exports = { precisionStrike };
