/**
 * TITAN V6.0 - 模拟数据清理脚本
 * ==============================
 * 
 * 物理删除所有带有 GOLD/STRESS/HIST 标签的测试数据
 * 为零模拟真实抓取做准备
 * 
 * @module scripts/ops/cleanup_mock_data
 * @version V6.0.0-CLEANUP
 * @date 2026-03-15
 */

'use strict';

const { Pool } = require('pg');

// 数据库配置
const DB_CONFIG = {
  host: process.env.DB_HOST || 'host.docker.internal',
  port: parseInt(process.env.DB_PORT || '5432'),
  database: process.env.DB_NAME || 'football_db',
  user: process.env.DB_USER || 'football_user',
  password: process.env.DB_PASSWORD || 'football_password',
};

async function cleanupMockData() {
  console.log('🧹 TITAN V6.0 模拟数据清理\n');
  console.log('='.repeat(70));
  
  const pool = new Pool(DB_CONFIG);
  
  try {
    // 1. 清理 backfill_progress 表
    console.log('\n📋 清理 backfill_progress 表...');
    
    const backfillResult = await pool.query(`
      DELETE FROM backfill_progress 
      WHERE match_id LIKE 'GOLD_%' 
         OR match_id LIKE 'STRESS_%' 
         OR match_id LIKE 'HIST_%'
      RETURNING match_id
    `);
    
    console.log(`   ✅ 已删除 ${backfillResult.rowCount} 条测试记录`);
    
    // 2. 清理 l3_features 表中的测试数据
    console.log('\n📋 清理 l3_features 表...');
    
    const l3Result = await pool.query(`
      DELETE FROM l3_features 
      WHERE match_id LIKE 'GOLD_%' 
         OR match_id LIKE 'STRESS_%' 
         OR match_id LIKE 'HIST_%'
      RETURNING match_id
    `);
    
    console.log(`   ✅ 已删除 ${l3Result.rowCount} 条测试记录`);
    
    // 3. 验证清理结果
    console.log('\n📊 清理验证...');
    
    const verifyBackfill = await pool.query(`
      SELECT COUNT(*) as count 
      FROM backfill_progress 
      WHERE match_id LIKE 'GOLD_%' 
         OR match_id LIKE 'STRESS_%' 
         OR match_id LIKE 'HIST_%'
    `);
    
    const verifyL3 = await pool.query(`
      SELECT COUNT(*) as count 
      FROM l3_features 
      WHERE match_id LIKE 'GOLD_%' 
         OR match_id LIKE 'STRESS_%' 
         OR match_id LIKE 'HIST_%'
    `);
    
    console.log(`   backfill_progress 残留: ${verifyBackfill.rows[0].count}`);
    console.log(`   l3_features 残留: ${verifyL3.rows[0].count}`);
    
    if (verifyBackfill.rows[0].count === 0 && verifyL3.rows[0].count === 0) {
      console.log('\n✅ 清理完成！数据库已就绪 for 真实抓取\n');
    } else {
      console.log('\n⚠️  清理不完全，仍有残留数据\n');
    }
    
    console.log('='.repeat(70));
    
  } catch (error) {
    console.error('\n❌ 清理失败:', error.message);
    throw error;
  } finally {
    await pool.end();
  }
}

// 主入口
async function main() {
  console.log('\n');
  console.log('╔══════════════════════════════════════════════════════════════════╗');
  console.log('║     TITAN V6.0 - ZERO-MOCK CLEANUP PROTOCOL                      ║');
  console.log('║     物理删除所有模拟数据                                          ║');
  console.log('╚══════════════════════════════════════════════════════════════════╝');
  console.log('\n');
  
  try {
    await cleanupMockData();
    console.log('🚀 数据库已净化，准备真实点火！\n');
    process.exit(0);
  } catch (error) {
    console.error('\n💥 清理失败:', error);
    process.exit(1);
  }
}

if (require.main === module) {
  main();
}

module.exports = { cleanupMockData };
