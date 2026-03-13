#!/usr/bin/env node
/**
 * @file TITAN 数据资产审计系统
 * @description 数据质量全面体检：物理清点、内容抽检、DB对齐、质量报告
 * @version 1.0.0
 * @module scripts/ops/audit_dataset
 */

'use strict';

const fs = require('fs').promises;
const path = require('path');
const { Pool } = require('pg');

// 颜色定义
const COLORS = {
  reset: '\x1b[0m',
  green: '\x1b[32m',
  red: '\x1b[31m',
  yellow: '\x1b[33m',
  cyan: '\x1b[36m',
  magenta: '\x1b[35m',
  white: '\x1b[37m'
};

const LOG_PREFIX = '[AUDIT]';

/**
 * 打印带颜色的日志
 * @param level
 * @param message
 */
function log(level, message) {
  const colorMap = {
    info: COLORS.cyan,
    success: COLORS.green,
    warning: COLORS.yellow,
    error: COLORS.red,
    header: COLORS.magenta
  };
  const color = colorMap[level] || COLORS.reset;
  console.log(`${color}${LOG_PREFIX} ${message}${COLORS.reset}`);
}

/**
 * 显示审计横幅
 */
function showBanner() {
  console.log('\n' + COLORS.magenta + '='.repeat(70) + COLORS.reset);
  console.log(COLORS.magenta + '  TITAN 数据资产审计系统 v1.0' + COLORS.reset);
  console.log(COLORS.magenta + '  Data Asset Audit & Quality Assurance' + COLORS.reset);
  console.log(COLORS.magenta + '='.repeat(70) + COLORS.reset + '\n');
}

/**
 * 数据库配置
 */
const DB_CONFIG = {
  host: process.env.DB_HOST || 'host.docker.internal',
  port: parseInt(process.env.DB_PORT, 10) || 5432,
  database: process.env.DB_NAME || 'football_db',
  user: process.env.DB_USER || 'football_user',
  password: process.env.DB_PASSWORD || 'football_pass',
  max: 5,
  idleTimeoutMillis: 30000
};

/**
 * 数据目录路径
 */
const DATA_PATH = process.env.DATA_MATCHES_PATH
  ? path.resolve(process.cwd(), process.env.DATA_MATCHES_PATH)
  : path.join(process.cwd(), 'data', 'matches');

/**
 * 阶段 1: 物理清点 - 统计 JSON 文件总数
 */
async function physicalInventory() {
  log('header', '📦 阶段 1: 物理清点');
  
  try {
    const files = await fs.readdir(DATA_PATH);
    const jsonFiles = files.filter(f => f.endsWith('.json') && !f.startsWith('.'));
    
    // 统计文件大小分布
    let totalSize = 0;
    const sizeDistribution = { small: 0, medium: 0, large: 0 };
    
    for (const file of jsonFiles.slice(0, 100)) { // 抽样统计前100个
      try {
        const stats = await fs.stat(path.join(DATA_PATH, file));
        totalSize += stats.size;
        
        if (stats.size < 1000) sizeDistribution.small++;
        else if (stats.size < 10000) sizeDistribution.medium++;
        else sizeDistribution.large++;
      } catch (err) {
        // 忽略单个文件错误
      }
    }
    
    const avgSize = jsonFiles.length > 0 ? Math.round(totalSize / Math.min(jsonFiles.length, 100)) : 0;
    
    log('success', `JSON 文件总数: ${jsonFiles.length.toLocaleString()}`);
    log('info', `平均文件大小: ${avgSize.toLocaleString()} bytes`);
    log('info', `大小分布: 小文件(<1KB): ${sizeDistribution.small}, 中文件(1-10KB): ${sizeDistribution.medium}, 大文件(>10KB): ${sizeDistribution.large}`);
    
    return {
      totalFiles: jsonFiles.length,
      files: jsonFiles,
      avgSize,
      sizeDistribution
    };
  } catch (error) {
    log('error', `物理清点失败: ${error.message}`);
    return { totalFiles: 0, files: [], avgSize: 0, sizeDistribution: {} };
  }
}

/**
 * 阶段 2: 内容抽检 - 随机抽取 50 个文件验证完整性
 * @param files
 */
async function contentSampling(files) {
  log('header', '🔍 阶段 2: 内容抽检 (随机 50 个样本)');
  
  if (files.length === 0) {
    log('warning', '无文件可供抽检');
    return { checked: 0, valid: 0, corrupted: 0, details: [] };
  }
  
  // 随机抽取 50 个
  const sampleSize = Math.min(50, files.length);
  const shuffled = [...files].sort(() => 0.5 - Math.random());
  const samples = shuffled.slice(0, sampleSize);
  
  let valid = 0;
  let corrupted = 0;
  const corruptedFiles = [];
  const details = [];
  
  for (let i = 0; i < samples.length; i++) {
    const file = samples[i];
    const filePath = path.join(DATA_PATH, file);
    
    try {
      const content = await fs.readFile(filePath, 'utf8');
      const data = JSON.parse(content);
      
      // 验证结构完整性
      const hasMatchId = !!data.match_id;
      const hasRawData = data.raw_data && Object.keys(data.raw_data).length > 0;
      const hasSavedAt = !!data.saved_at;
      
      if (hasMatchId && hasRawData && hasSavedAt) {
        valid++;
        details.push({ file, status: 'valid', matchId: data.match_id });
      } else {
        corrupted++;
        corruptedFiles.push(file.replace('.json', ''));
        details.push({ file, status: 'incomplete', missing: [] });
        if (!hasMatchId) details[details.length - 1].missing.push('match_id');
        if (!hasRawData) details[details.length - 1].missing.push('raw_data');
        if (!hasSavedAt) details[details.length - 1].missing.push('saved_at');
      }
    } catch (error) {
      corrupted++;
      corruptedFiles.push(file.replace('.json', ''));
      details.push({ file, status: 'error', error: error.message });
    }
    
    process.stdout.write(`\r${LOG_PREFIX} 抽检进度: ${i + 1}/${sampleSize}`);
  }
  
  console.log(); // 换行
  
  const passRate = sampleSize > 0 ? ((valid / sampleSize) * 100).toFixed(2) : 0;
  
  if (corrupted === 0) {
    log('success', `抽检完成: ${valid}/${sampleSize} 通过 (通过率: ${passRate}%)`);
  } else {
    log('warning', `抽检完成: ${valid} 有效, ${corrupted} 损坏 (通过率: ${passRate}%)`);
  }
  
  return {
    checked: sampleSize,
    valid,
    corrupted,
    passRate,
    corruptedFiles,
    details
  };
}

/**
 * 阶段 3: DB 对齐 - 查询数据库并计算对齐率
 */
async function databaseAlignment() {
  log('header', '🗄️  阶段 3: 数据库对齐检查');
  
  const pool = new Pool(DB_CONFIG);
  
  try {
    // 查询数据库总数
    const countResult = await pool.query('SELECT COUNT(*) as count FROM raw_match_data');
    const dbCount = parseInt(countResult.rows[0].count, 10);
    
    // 查询最近更新
    const recentResult = await pool.query(
      'SELECT match_id, collected_at FROM raw_match_data ORDER BY collected_at DESC LIMIT 5'
    );
    
    log('success', `数据库记录总数: ${dbCount.toLocaleString()}`);
    log('info', '最近 5 条更新:');
    recentResult.rows.forEach((row, i) => {
      console.log(`      ${i + 1}. ${row.match_id} @ ${new Date(row.collected_at).toLocaleString()}`);
    });
    
    await pool.end();
    
    return {
      dbCount,
      recentRecords: recentResult.rows
    };
  } catch (error) {
    log('error', `数据库查询失败: ${error.message}`);
    await pool.end();
    return { dbCount: 0, recentRecords: [] };
  }
}

/**
 * 阶段 4: 生成质量报告
 * @param inventory
 * @param sampling
 * @param alignment
 */
function generateReport(inventory, sampling, alignment) {
  log('header', '📊 阶段 4: 数据质量报告');
  
  console.log('\n' + COLORS.cyan + '╔════════════════════════════════════════════════════════════════╗' + COLORS.reset);
  console.log(COLORS.cyan + '║                    TITAN 数据资产质量报告                      ║' + COLORS.reset);
  console.log(COLORS.cyan + '╚════════════════════════════════════════════════════════════════╝' + COLORS.reset);
  
  console.log('\n' + COLORS.white + '【物理资产】' + COLORS.reset);
  console.log(`  JSON 文件总数:    ${inventory.totalFiles.toLocaleString().padStart(8)}`);
  console.log(`  平均文件大小:     ${inventory.avgSize.toLocaleString().padStart(8)} bytes`);
  
  console.log('\n' + COLORS.white + '【质量抽检】' + COLORS.reset);
  console.log(`  抽检样本数:       ${sampling.checked.toString().padStart(8)}`);
  console.log(`  有效文件:         ${sampling.valid.toString().padStart(8)}`);
  console.log(`  损坏/异常:        ${COLORS.red}${sampling.corrupted.toString().padStart(8)}${COLORS.reset}`);
  console.log(`  抽检通过率:       ${sampling.passRate.toString().padStart(8)}%`);
  
  console.log('\n' + COLORS.white + '【数据库对齐】' + COLORS.reset);
  console.log(`  数据库记录数:     ${alignment.dbCount.toLocaleString().padStart(8)}`);
  
  // 计算对齐率
  const alignmentRate = alignment.dbCount > 0 
    ? ((inventory.totalFiles / alignment.dbCount) * 100).toFixed(2)
    : 0;
  const diff = inventory.totalFiles - alignment.dbCount;
  
  console.log(`  文件/DB 对齐率:   ${alignmentRate.toString().padStart(8)}%`);
  
  if (diff === 0) {
    console.log(`  差异:             ${COLORS.green}完全对齐 ✓${COLORS.reset}`);
  } else if (diff > 0) {
    console.log(`  差异:             ${COLORS.yellow}文件多 ${diff} 个${COLORS.reset}`);
  } else {
    console.log(`  差异:             ${COLORS.yellow}DB 多 ${Math.abs(diff)} 个${COLORS.reset}`);
  }
  
  // 总体评估
  console.log('\n' + COLORS.cyan + '【总体评估】' + COLORS.reset);
  
  const quality = sampling.passRate >= 95 && Math.abs(diff) <= 10 
    ? { label: '优秀', color: COLORS.green }
    : sampling.passRate >= 90 && Math.abs(diff) <= 50
    ? { label: '良好', color: COLORS.yellow }
    : { label: '需关注', color: COLORS.red };
  
  console.log(`  数据健康度:       ${quality.color}${quality.label}${COLORS.reset}`);
  
  // 建议补抓列表
  if (sampling.corrupted > 0 && sampling.corruptedFiles.length > 0) {
    console.log('\n' + COLORS.red + '【建议补抓 ID 列表】' + COLORS.reset);
    sampling.corruptedFiles.slice(0, 10).forEach((id, i) => {
      console.log(`  ${i + 1}. ${id}`);
    });
    if (sampling.corruptedFiles.length > 10) {
      console.log(`  ... 还有 ${sampling.corruptedFiles.length - 10} 个`);
    }
  }
  
  console.log('\n' + COLORS.cyan + '='.repeat(66) + COLORS.reset + '\n');
  
  return {
    totalFiles: inventory.totalFiles,
    dbCount: alignment.dbCount,
    alignmentRate,
    quality: quality.label,
    corruptedCount: sampling.corrupted,
    corruptedFiles: sampling.corruptedFiles
  };
}

/**
 * 主函数
 */
async function main() {
  showBanner();
  
  const startTime = Date.now();
  
  try {
    // 执行四个阶段
    const inventory = await physicalInventory();
    const sampling = await contentSampling(inventory.files);
    const alignment = await databaseAlignment();
    const report = generateReport(inventory, sampling, alignment);
    
    const duration = ((Date.now() - startTime) / 1000).toFixed(2);
    log('success', `审计完成，耗时 ${duration} 秒`);
    
    // 根据质量决定退出码
    process.exit(report.quality === '需关注' ? 1 : 0);
    
  } catch (error) {
    log('error', `审计失败: ${error.message}`);
    console.error(error.stack);
    process.exit(1);
  }
}

// 执行
main();
