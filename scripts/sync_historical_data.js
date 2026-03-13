#!/usr/bin/env node
/**
 * @file 存量数据物理落地方案 (One-Time-Sync)
 * @description 将数据库中历史记录同步到物理文件，支持跨平台路径解析
 * @version 2.0.0
 * @status 一次性工具，即后即焚
 */

require('dotenv').config({ path: path.join(__dirname, '..', 'config', '.env') });

const fs = require('fs').promises;
const path = require('path');
const { Pool } = require('pg');

const LOG_PREFIX = '[HISTORICAL-SYNC]';

/**
 * 数据库配置 (从环境变量读取，带默认值)
 * @type {object}
 */
const DB_CONFIG = {
  host: process.env.DB_HOST || 'host.docker.internal',
  port: parseInt(process.env.DB_PORT, 10) || 5432,
  database: process.env.DB_NAME || 'football_db',
  user: process.env.DB_USER || 'football_user',
  password: process.env.DB_PASSWORD || 'football_pass',
  max: parseInt(process.env.DB_MAX_CONNECTIONS, 10) || 5,
  idleTimeoutMillis: parseInt(process.env.DB_IDLE_TIMEOUT, 10) || 30000
};

/**
 * 目标目录 (跨平台路径解析)
 * @type {string}
 */
const TARGET_DIR = process.env.DATA_MATCHES_PATH
  ? path.resolve(process.cwd(), process.env.DATA_MATCHES_PATH)
  : path.join(process.cwd(), 'data', 'matches');

/**
 * 错误分类器 - 区分错误类型并返回标记
 * @param {Error} error - 错误对象
 * @returns {string} 错误类型标记
 */
function classifyError(error) {
  const message = error.message.toLowerCase();

  if (message.includes('connect') || message.includes('econnrefused') || message.includes('timeout')) {
    return '[NETWORK]';
  }
  if (message.includes('authentication') || message.includes('password') || message.includes('permission denied')) {
    return '[AUTH]';
  }
  if (message.includes('enoent') || message.includes('eacces') || message.includes('not found')) {
    return '[FILESYSTEM]';
  }
  if (message.includes('syntax') || message.includes('parse') || message.includes('invalid')) {
    return '[DATA]';
  }
  return '[UNKNOWN]';
}

/**
 * 主函数 - 执行存量数据同步
 * @async
 * @returns {Promise<void>}
 */
async function main() {
  console.log(`${LOG_PREFIX} 启动存量数据同步工具 v2.0`);
  console.log(`${LOG_PREFIX} 目标目录: ${TARGET_DIR}`);
  console.log(`${LOG_PREFIX} 数据库: ${DB_CONFIG.host}:${DB_CONFIG.port}/${DB_CONFIG.database}`);

  const pool = new Pool(DB_CONFIG);

  try {
    // 1. 获取数据库中所有记录
    console.log(`${LOG_PREFIX} 正在读取数据库...`);
    let result;
    try {
      result = await pool.query(
        'SELECT match_id, raw_data, collected_at FROM raw_match_data ORDER BY collected_at DESC'
      );
    } catch (dbErr) {
      const errType = classifyError(dbErr);
      if (errType === '[NETWORK]') {
        throw new Error(`${errType} 数据库连接失败: 请检查 DB_HOST 和 DB_PORT 配置`);
      }
      if (errType === '[AUTH]') {
        throw new Error(`${errType} 数据库认证失败: 请检查 DB_USER 和 DB_PASSWORD`);
      }
      throw new Error(`${errType} 数据库查询失败: ${dbErr.message}`);
    }

    const totalRecords = result.rows.length;
    console.log(`${LOG_PREFIX} 数据库中共有 ${totalRecords} 条记录`);

    if (totalRecords === 0) {
      console.log(`${LOG_PREFIX} 无数据需要同步，退出`);
      return;
    }

    // 2. 确保目标目录存在
    try {
      await fs.mkdir(TARGET_DIR, { recursive: true });
      console.log(`${LOG_PREFIX} 目标目录准备就绪`);
    } catch (dirErr) {
      const errType = classifyError(dirErr);
      throw new Error(`${errType} 无法创建目标目录 ${TARGET_DIR}: ${dirErr.message}`);
    }

    // 3. 检查现有文件
    const existingFiles = new Set();
    try {
      const files = await fs.readdir(TARGET_DIR);
      files.forEach(f => {
        if (f.endsWith('.json')) {
          existingFiles.add(f.replace('.json', ''));
        }
      });
      console.log(`${LOG_PREFIX} 目标目录已有 ${existingFiles.size} 个文件`);
    } catch (err) {
      console.log(`${LOG_PREFIX} 目标目录为空或不存在，将全新创建`);
    }

    // 4. 批量生成缺失文件
    let created = 0;
    let skipped = 0;
    let failed = 0;

    console.log(`${LOG_PREFIX} 开始同步...\n`);

    for (let i = 0; i < result.rows.length; i++) {
      const row = result.rows[i];
      const matchId = row.match_id;

      // 检查是否已存在
      if (existingFiles.has(matchId)) {
        skipped++;
        process.stdout.write(`\r${LOG_PREFIX} [${i + 1}/${totalRecords}] 跳过已存在: ${matchId}`);
        continue;
      }

      // 生成文件
      const filePath = path.join(TARGET_DIR, `${matchId}.json`);
      const dataToSave = {
        match_id: matchId,
        raw_data: row.raw_data,
        saved_at: row.collected_at?.toISOString?.() || new Date().toISOString(),
        source: 'Historical-Sync-V4.51',
        sync_batch: '2258-migration'
      };

      try {
        await fs.writeFile(filePath, JSON.stringify(dataToSave, null, 2));
        created++;
        process.stdout.write(`\r${LOG_PREFIX} [${i + 1}/${totalRecords}] 已创建: ${matchId}.json`);
      } catch (err) {
        failed++;
        const errType = classifyError(err);
        console.error(`\n${LOG_PREFIX} ${errType} ${matchId} 创建失败: ${err.message}`);
      }

      // 每 100 条暂停一下，避免过载
      if (i % 100 === 0 && i > 0) {
        await new Promise(r => { setTimeout(r, 10); });
      }
    }

    // 5. 汇报结果
    console.log('\n');
    console.log('='.repeat(60));
    console.log('✓ 存量数据同步完成！');
    console.log('='.repeat(60));
    console.log(`总记录数: ${totalRecords}`);
    console.log(`新创建:   ${created}`);
    console.log(`已跳过:   ${skipped}`);
    console.log(`失败:     ${failed}`);
    console.log('='.repeat(60));

    if (created === totalRecords - skipped) {
      console.log(`\n🎉 ${totalRecords} 场历史数据已全部归位！`);
    }

  } catch (error) {
    const errType = classifyError(error);
    console.error(`${LOG_PREFIX} ${errType} 同步失败:`, error.message);
    console.error(error.stack);
    process.exit(1);

  } finally {
    await pool.end();
    console.log(`${LOG_PREFIX} 数据库连接已关闭`);
  }
}

// 执行
main().then(() => {
  process.exit(0);
}).catch(err => {
  console.error('致命错误:', err);
  process.exit(1);
});