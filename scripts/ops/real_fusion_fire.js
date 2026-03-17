/**
 * TITAN V6.0 REAL FUSION FIRE - 真实ID匹配与全维度赔率入库
 * =========================================================
 * 
 * 利用数据库真实Match ID，将Pinnacle和Bet365的全生命周期数据缝合入库
 * 
 * @module scripts/ops/real_fusion_fire
 * @version V6.0-REAL-FUSION
 * @date 2026-03-16
 */

'use strict';

const { Pool } = require('pg');
const { OddsPortalHarvester } = require('../../src/infrastructure/harvesters/OddsPortalHarvester');
const { ProxyRotator } = require('../../src/infrastructure/harvesters/ProxyRotator');

// 数据库配置
const DB_CONFIG = {
  host: process.env.DB_HOST || 'host.docker.internal',
  port: parseInt(process.env.DB_PORT || '5432'),
  database: process.env.DB_NAME || 'football_db',
  user: process.env.DB_USER || 'football_user',
  password: process.env.DB_PASSWORD || 'football_password',
};

/**
 * 从数据库获取20个真实match_id
 */
async function acquireRealTargets(pool) {
  console.log('\n🔍 [Phase 1] 动态目标获取 - Real-ID Acquisition\n');
  
  const query = `
    SELECT m.match_id, m.home_team, m.away_team, m.match_date 
    FROM matches m
    LEFT JOIN l3_features l3 ON m.match_id = l3.match_id
    WHERE l3.market_sentiment IS NULL 
    AND m.home_team IS NOT NULL
    ORDER BY m.match_date DESC
    LIMIT 20;
  `;
  
  const result = await pool.query(query);
  
  console.log(`✅ 获取到 ${result.rows.length} 个真实Match ID`);
  console.log('\n📋 目标列表:');
  result.rows.forEach((row, i) => {
    console.log(`   [${i + 1}] ${row.match_id}: ${row.home_team} vs ${row.away_team}`);
  });
  
  return result.rows;
}

/**
 * 生成OddsPortal URL
 */
function generateOddsPortalUrl(match) {
  // 简化生成逻辑 - 使用搜索URL格式
  const home = match.home_team.toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '');
  const away = match.away_team.toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '');
  return `https://www.oddsportal.com/search/${home}-${away}/`;
}

/**
 * 执行深度收割与入库
 */
async function executeFusionFire(pool, targets) {
  console.log('\n🔥 [Phase 2] 深度收割与入库 - Fusion Fire\n');
  
  const proxyRotator = new ProxyRotator({ strategy: 'round-robin' });
  const harvester = new OddsPortalHarvester({ headless: true });
  
  const stats = {
    total: targets.length,
    success: 0,
    failed: 0,
    consecutiveFailures: 0,
    pinnacleFound: 0,
    bet365Found: 0,
    totalCurvePoints: 0
  };
  
  const processedIds = [];
  
  for (let i = 0; i < targets.length; i++) {
    const match = targets[i];
    const proxy = proxyRotator.getNextProxy();
    
    console.log(`\n[${i + 1}/${targets.length}] 🔥 ${match.home_team} vs ${match.away_team}`);
    console.log(`       🆔 Match ID: ${match.match_id}`);
    console.log(`       🔌 Proxy: ${proxy.port}`);
    
    try {
      const startTime = Date.now();
      
      // 生成URL并收割
      const url = generateOddsPortalUrl(match);
      const result = await harvester.harvest(url);
      const latency = Date.now() - startTime;
      
      // 自检指标
      const bodyTextLength = result.odds?._diagnostic?.bodyTextLength || 0;
      console.log(`       📝 Body: ${bodyTextLength} chars`);
      
      // 深度数据验证
      const ms = result.market_sentiment;
      const hasPinnacle = ms?.pinnacle_odds?.closing?.length === 3;
      const hasBet365 = ms?.bet365_odds?.closing?.length === 3;
      const isExcavator = ms?._apiExcavator === true;
      
      console.log(`       ⏱️  Latency: ${latency}ms`);
      console.log(`       ⛏️  API-EXCAVATOR: ${isExcavator ? '✅' : '❌'}`);
      console.log(`       🔒 Pinnacle: ${hasPinnacle ? '✅' : '❌'}`);
      console.log(`       🔒 Bet365: ${hasBet365 ? '✅' : '❌'}`);
      
      if (hasPinnacle) {
        stats.pinnacleFound++;
        console.log(`       💰 Pinnacle: ${ms.pinnacle_odds.closing.join(' | ')}`);
        if (ms.pinnacle_odds.opening) {
          console.log(`       📈 Opening: ${ms.pinnacle_odds.opening.join(' | ')}`);
        }
      }
      
      if (hasBet365) {
        stats.bet365Found++;
        console.log(`       💰 Bet365: ${ms.bet365_odds.closing.join(' | ')}`);
      }
      
      // 变盘曲线统计
      const curveLength = ms?.pinnacle_odds?.history?.length || 0;
      if (curveLength > 0) {
        stats.totalCurvePoints += curveLength;
        console.log(`       🏔️  Curve Points: ${curveLength}`);
      }
      
      // 物理入库
      if (hasPinnacle || hasBet365) {
        try {
          const upsertQuery = `
            INSERT INTO l3_features (match_id, market_sentiment, updated_at)
            VALUES ($1, $2, NOW())
            ON CONFLICT (match_id) DO UPDATE SET 
              market_sentiment = EXCLUDED.market_sentiment,
              updated_at = NOW()
            RETURNING match_id;
          `;
          
          const upsertResult = await pool.query(upsertQuery, [
            match.match_id,
            JSON.stringify(ms)
          ]);
          
          if (upsertResult.rows.length > 0) {
            console.log(`       💾 ✅ 入库成功: ${upsertResult.rows[0].match_id}`);
            stats.success++;
            stats.consecutiveFailures = 0;
            processedIds.push(match.match_id);
          }
        } catch (dbError) {
          console.log(`       💾 ❌ 入库失败: ${dbError.message}`);
          stats.failed++;
          stats.consecutiveFailures++;
        }
      } else {
        console.log(`       ⚠️  无有效赔率数据，跳过入库`);
        stats.failed++;
        stats.consecutiveFailures++;
      }
      
    } catch (error) {
      console.log(`       ❌ Error: ${error.message}`);
      stats.failed++;
      stats.consecutiveFailures++;
    }
    
    // 熔断检查
    if (stats.consecutiveFailures >= 3) {
      console.log('\n🚫 🚫 🚫 熔断触发: 连续3场失败，停止以保护Session 🚫 🚫 🚫\n');
      break;
    }
    
    // 场次间延迟
    if (i < targets.length - 1) {
      await new Promise(r => setTimeout(r, 2000));
    }
  }
  
  await harvester.close();
  
  return { stats, processedIds };
}

/**
 * 最终审计战报
 */
async function executeAuditReport(pool, processedIds) {
  console.log('\n📊 [Phase 3] 最终审计战报 - The Proof of Gold\n');
  
  if (processedIds.length === 0) {
    console.log('⚠️  无成功入库的记录，跳过审计');
    return;
  }
  
  const idsList = processedIds.map(id => `'${id}'`).join(',');
  
  const auditQuery = `
    SELECT 
      match_id,
      market_sentiment->>'extract_method' as method,
      market_sentiment->'pinnacle_odds'->'closing' as pin_closing,
      market_sentiment->'bet365_odds'->'closing' as b365_closing,
      jsonb_array_length(COALESCE(market_sentiment->'pinnacle_odds'->'history', '[]'::jsonb)) as curve_len,
      market_sentiment->>'_v3Lock' as v3_lock,
      market_sentiment->>'_apiExcavator' as excavator
    FROM l3_features 
    WHERE match_id IN (${idsList})
    ORDER BY updated_at DESC;
  `;
  
  const result = await pool.query(auditQuery);
  
  console.log('='.repeat(100));
  console.log('📊 入库数据审计报告');
  console.log('='.repeat(100));
  console.log(`${'Match ID'.padEnd(30)} | ${'Method'.padEnd(25)} | ${'Pinnacle'.padEnd(20)} | ${'Bet365'.padEnd(20)} | Curve`);
  console.log('-'.repeat(100));
  
  for (const row of result.rows) {
    const pin = row.pin_closing ? JSON.parse(row.pin_closing).join('/') : 'N/A';
    const b365 = row.b365_closing ? JSON.parse(row.b365_closing).join('/') : 'N/A';
    const method = (row.method || 'N/A').slice(0, 25);
    
    console.log(`${row.match_id.padEnd(30)} | ${method.padEnd(25)} | ${pin.padEnd(20)} | ${b365.padEnd(20)} | ${row.curve_len || 0}`);
  }
  
  console.log('-'.repeat(100));
  
  // 核心断言验证
  const v3Count = result.rows.filter(r => r.v3_lock === 'true').length;
  const excavatorCount = result.rows.filter(r => r.excavator === 'true').length;
  const pinCount = result.rows.filter(r => r.pin_closing !== null).length;
  const b365Count = result.rows.filter(r => r.b365_closing !== null).length;
  
  console.log('\n✅ 核心断言验证:');
  console.log(`   _v3Lock 标记: ${v3Count}/${result.rows.length}`);
  console.log(`   _apiExcavator 标记: ${excavatorCount}/${result.rows.length}`);
  console.log(`   pinnacle_odds 存在: ${pinCount}/${result.rows.length}`);
  console.log(`   bet365_odds 存在: ${b365Count}/${result.rows.length}`);
  
  // 顶级字段验证
  const fieldCheckQuery = `
    SELECT match_id
    FROM l3_features 
    WHERE match_id IN (${idsList})
    AND market_sentiment ? 'pinnacle_odds'
    AND market_sentiment->'pinnacle_odds' ? 'closing';
  `;
  
  const fieldCheck = await pool.query(fieldCheckQuery);
  console.log(`   pinnacle_odds 作为顶级字段: ${fieldCheck.rows.length}/${result.rows.length} ✅`);
  
  return result.rows;
}

/**
 * 主函数
 */
async function realFusionFire() {
  console.log('\n╔══════════════════════════════════════════════════════════════════╗');
  console.log('║     🔥 TITAN V6.0 REAL FUSION FIRE 🔥                           ║');
  console.log('║     真实ID匹配与全维度赔率入库                                  ║');
  console.log('╚══════════════════════════════════════════════════════════════════╝\n');
  
  const pool = new Pool(DB_CONFIG);
  
  try {
    // Phase 1: 获取真实目标
    const targets = await acquireRealTargets(pool);
    
    if (targets.length === 0) {
      console.log('⚠️  没有找到可处理的比赛');
      return;
    }
    
    // Phase 2: 执行收割与入库
    const { stats, processedIds } = await executeFusionFire(pool, targets);
    
    // Phase 3: 审计报告
    await executeAuditReport(pool, processedIds);
    
    // 终极宣告
    console.log('\n╔══════════════════════════════════════════════════════════════════╗');
    console.log('║     🔥 TITAN V6.0 REAL FUSION FIRE 终极宣告 🔥                 ║');
    console.log('╠══════════════════════════════════════════════════════════════════╣');
    console.log(`║     总目标: ${String(stats.total).padStart(2)} 场                                          ║`);
    console.log(`║     入库成功: ${String(stats.success).padStart(2)} 场 (${((stats.success/stats.total)*100).toFixed(0)}%)                    ║`);
    console.log(`║     Pinnacle找到: ${String(stats.pinnacleFound).padStart(2)} 场                         ║`);
    console.log(`║     Bet365找到: ${String(stats.bet365Found).padStart(2)} 场                           ║`);
    console.log(`║     总变盘点数: ${String(stats.totalCurvePoints).padStart(3)} 个                      ║`);
    console.log(`║     熔断触发: ${stats.consecutiveFailures >= 3 ? '是 ✅' : '否'}                           ║`);
    console.log('╠══════════════════════════════════════════════════════════════════╣');
    console.log('║     ✅ 不仅要进门，还要把金矿搬回家！                          ║');
    console.log('╚══════════════════════════════════════════════════════════════════╝\n');
    
  } catch (error) {
    console.error('\n💥 执行失败:', error.message);
    console.error(error.stack);
  } finally {
    await pool.end();
  }
}

// 运行
if (require.main === module) {
  realFusionFire().catch(console.error);
}

module.exports = { realFusionFire };
