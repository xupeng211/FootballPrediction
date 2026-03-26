#!/usr/bin/env node
/**
 * TITAN V6.0 GRAND BACKFILL - 终极回填总调度
 * ===========================================
 * 
 * 一体化流水线：测绘 -> 入库 -> 带证收割 -> 数据验证
 * 
 * 用法:
 *   node scripts/ops/titan_grand_backfill.js --season 2023-2024 --league EPL
 *   node scripts/ops/titan_grand_backfill.js --season 2023-2024 --full-pipeline
 *   node scripts/ops/titan_grand_backfill.js --recon-only
 *   node scripts/ops/titan_grand_backfill.js --harvest-only
 * 
 * @module scripts/ops/titan_grand_backfill
 * @version V6.0-GRAND
 * @date 2026-03-17
 */

'use strict';

const { Pool } = require('pg');
const { exec } = require('child_process');
const { promisify } = require('util');
const path = require('path');

const execAsync = promisify(exec);

// 数据库配置
const DB_CONFIG = {
  host: process.env.DB_HOST || '127.0.0.1',
  port: parseInt(process.env.DB_PORT || '5432'),
  database: process.env.DB_NAME || 'football_db',
  user: process.env.DB_USER || 'football_user',
  password: process.env.DB_PASSWORD || 'football_pass',
};

/**
 * 执行shell命令并输出
 */
async function runCommand(cmd, description) {
  console.log(`\n🔄 ${description}...`);
  console.log(`   命令: ${cmd}`);
  try {
    const { stdout, stderr } = await execAsync(cmd, { cwd: process.cwd() });
    if (stdout) console.log(stdout);
    if (stderr) console.error(stderr);
    console.log(`   ✅ ${description} 完成`);
    return true;
  } catch (error) {
    console.error(`   ❌ ${description} 失败:`, error.message);
    return false;
  }
}

/**
 * 检查数据库连接和表结构
 */
async function checkDatabase(pool) {
  console.log('\n📊 检查数据库状态...');
  try {
    // 检查mapping表是否存在
    const tableCheck = await pool.query(`
      SELECT EXISTS (
        SELECT FROM information_schema.tables 
        WHERE table_name = 'matches_oddsportal_mapping'
      );
    `);
    
    if (!tableCheck.rows[0].exists) {
      console.log('   ⚠️  mapping表不存在，正在创建...');
      const fs = require('fs');
      const sql = fs.readFileSync(
        path.join(__dirname, 'matches_oddsportal_mapping.sql'), 
        'utf8'
      );
      await pool.query(sql);
      console.log('   ✅ mapping表已创建');
    } else {
      console.log('   ✅ mapping表已存在');
    }
    
    return true;
  } catch (e) {
    console.error('   ❌ 数据库检查失败:', e.message);
    return false;
  }
}

/**
 * 阶段1: 测绘扫描 (Recon)
 */
async function phaseRecon(season, league) {
  console.log('\n' + '='.repeat(70));
  console.log('🗺️  阶段1: 测绘扫描 (Reconnaissance)');
  console.log('='.repeat(70));
  
  const cmd = `node ${path.join(__dirname, 'recon_scanner.js')} --season ${season} --league ${league}`;
  return await runCommand(cmd, '测绘扫描历史比赛URL');
}

/**
 * 阶段2: 从数据库读取待收割任务
 */
async function phaseLoadTargets(pool, season, limit = 100) {
  console.log('\n' + '='.repeat(70));
  console.log('📋 阶段2: 加载收割目标');
  console.log('='.repeat(70));
  
  const query = `
    SELECT match_id, oddsportal_hash, full_url, home_team, away_team, league_name
    FROM matches_oddsportal_mapping
    WHERE season = $1 
      AND status = 'pending'
      AND retry_count < 3
    ORDER BY retry_count ASC, created_at ASC
    LIMIT $2;
  `;
  
  const result = await pool.query(query, [season, limit]);
  const targets = result.rows;
  
  console.log(`   📊 待收割任务: ${targets.length} 场`);
  
  if (targets.length === 0) {
    console.log('   ⚠️  没有待收割任务，请先运行测绘阶段');
    return null;
  }
  
  // 显示前5个目标
  console.log('   📋 前5个目标:');
  targets.slice(0, 5).forEach((t, i) => {
    console.log(`      ${i+1}. ${t.home_team} vs ${t.away_team} | Hash: ${t.oddsportal_hash}`);
  });
  
  return targets;
}

/**
 * 阶段3: 带证收割 (Harvest with Auth)
 */
async function phaseHarvest(targets) {
  console.log('\n' + '='.repeat(70));
  console.log('🌾 阶段3: 带证收割 (Authenticated Harvest)');
  console.log('='.repeat(70));
  
  // 将目标写入临时文件供 p2p_harvest_v38.js 使用
  const fs = require('fs');
  const targetsPath = path.join(process.cwd(), 'data', 'temp_targets.json');
  
  // 转换格式以匹配 p2p_harvest_v38.js 期望的格式
  const harvestTargets = targets.map(t => ({
    id: t.match_id,
    home_team: t.home_team,
    away_team: t.away_team,
    match_date: new Date().toISOString().split('T')[0],
    url: t.full_url,
    hash: t.oddsportal_hash
  }));
  
  fs.writeFileSync(targetsPath, JSON.stringify(harvestTargets, null, 2));
  console.log(`   📝 已生成目标文件: ${targetsPath}`);
  
  // 运行收割
  const cmd = `node ${path.join(__dirname, 'p2p_harvest_v38.js')} --targets ${targetsPath}`;
  return await runCommand(cmd, '带证收割历史比赛');
}

/**
 * 阶段4: 数据验证 (Validation)
 */
async function phaseValidation(pool, season) {
  console.log('\n' + '='.repeat(70));
  console.log('✅ 阶段4: 数据验证');
  console.log('='.repeat(70));
  
  // 运行赔率完整性检查
  const cmd = `python3 ${path.join(__dirname, '../maintenance/odds_integrity_guard.py')} --league "${season}"`;
  return await runCommand(cmd, '赔率完整性验证');
}

/**
 * 更新收割状态
 */
async function updateHarvestStatus(pool, matchId, status, error = null) {
  const query = `
    UPDATE matches_oddsportal_mapping
    SET status = $2,
        ${status === 'harvested' ? 'harvested_at = NOW(),' : ''}
        ${status === 'failed' ? 'retry_count = retry_count + 1, last_error = $3,' : ''}
        updated_at = NOW()
    WHERE match_id = $1;
  `;
  
  await pool.query(query, [matchId, status, error]);
}

/**
 * 生成最终报告
 */
async function generateFinalReport(pool, season) {
  console.log('\n' + '='.repeat(70));
  console.log('📊 最终报告');
  console.log('='.repeat(70));
  
  const stats = await pool.query(`
    SELECT 
      COUNT(*) as total,
      COUNT(*) FILTER (WHERE status = 'pending') as pending,
      COUNT(*) FILTER (WHERE status = 'harvested') as harvested,
      COUNT(*) FILTER (WHERE status = 'failed') as failed,
      COUNT(*) FILTER (WHERE status = 'processing') as processing
    FROM matches_oddsportal_mapping
    WHERE season = $1;
  `, [season]);
  
  const s = stats.rows[0];
  const harvestRate = s.total > 0 ? ((s.harvested / s.total) * 100).toFixed(1) : 0;
  
  console.log(`\n赛季: ${season}`);
  console.log(`总比赛数: ${s.total}`);
  console.log(`已收割: ${s.harvested} (${harvestRate}%)`);
  console.log(`待收割: ${s.pending}`);
  console.log(`失败: ${s.failed}`);
  console.log(`处理中: ${s.processing}`);
  
  if (parseFloat(harvestRate) >= 90) {
    console.log('\n🎉 收割率 >= 90%，任务达标！');
  } else if (parseFloat(harvestRate) >= 50) {
    console.log('\n✅ 收割率 >= 50%，继续加油！');
  } else {
    console.log('\n⚠️  收割率 < 50%，建议检查问题');
  }
}

/**
 * 主函数
 */
async function main() {
  // 解析参数
  const args = process.argv.slice(2);
  const seasonIndex = args.indexOf('--season');
  const leagueIndex = args.indexOf('--league');
  const fullPipeline = args.includes('--full-pipeline');
  const reconOnly = args.includes('--recon-only');
  const harvestOnly = args.includes('--harvest-only');
  
  const season = seasonIndex !== -1 ? args[seasonIndex + 1] : '2023-2024';
  const league = leagueIndex !== -1 ? args[leagueIndex + 1] : 'EPL';
  
  console.log('\n╔══════════════════════════════════════════════════════════════════╗');
  console.log('║     🔥 TITAN V6.0 GRAND BACKFILL - 终极回填流水线 🔥            ║');
  console.log('╠══════════════════════════════════════════════════════════════════╣');
  console.log(`║     赛季: ${season.padEnd(49)} ║`);
  console.log(`║     联赛: ${league.padEnd(49)} ║`);
  console.log(`║     模式: ${(reconOnly ? '仅测绘' : harvestOnly ? '仅收割' : '完整流水线').padEnd(49)} ║`);
  console.log('╚══════════════════════════════════════════════════════════════════╝\n');
  
  const pool = new Pool(DB_CONFIG);
  
  try {
    // 检查数据库
    const dbOk = await checkDatabase(pool);
    if (!dbOk) {
      console.error('数据库检查失败，退出');
      process.exit(1);
    }
    
    // 阶段1: 测绘
    if (!harvestOnly) {
      const reconOk = await phaseRecon(season, league);
      if (!reconOk) {
        console.error('测绘阶段失败');
        // 继续执行，可能有历史数据可用
      }
    }
    
    // 阶段2-3: 加载目标并收割
    if (!reconOnly) {
      const targets = await phaseLoadTargets(pool, season);
      
      if (targets && targets.length > 0) {
        const harvestOk = await phaseHarvest(targets);
        if (!harvestOk) {
          console.error('收割阶段部分失败');
        }
      }
      
      // 阶段4: 验证
      if (fullPipeline) {
        await phaseValidation(pool, season);
      }
    }
    
    // 生成报告
    await generateFinalReport(pool, season);
    
    console.log('\n╔══════════════════════════════════════════════════════════════════╗');
    console.log('║     ✅ GRAND BACKFILL 执行完成 ✅                               ║');
    console.log('╚══════════════════════════════════════════════════════════════════╝\n');
    
  } catch (error) {
    console.error('\n💥 流水线执行失败:', error.message);
    console.error(error.stack);
    process.exit(1);
  } finally {
    await pool.end();
  }
}

// 运行
if (require.main === module) {
  main().catch(err => {
    console.error('💥 致命错误:', err);
    process.exit(1);
  });
}

module.exports = {
  phaseRecon,
  phaseLoadTargets,
  phaseHarvest,
  phaseValidation,
  generateFinalReport
};