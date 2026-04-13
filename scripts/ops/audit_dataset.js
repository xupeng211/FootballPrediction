#!/usr/bin/env node
/* eslint-disable complexity, max-lines */
/**
 * @file TITAN 数据资产审计系统 (V6.7-Refactored)
 * @description 数据质量全面体检：物理清点、内容抽检、DB对齐、质量报告
 * @version 2.0.0
 * @module scripts/ops/audit_dataset
 * 
 * V6.7 重构:
 * - 移除直接 new Pool()，改用 FixtureRepository
 * - 统一使用环境变量配置
 * - 遵循 titan_discovery.js 的 main().catch() 结构
 */

'use strict';

const fs = require('fs').promises;
const path = require('path');
const { FixtureRepository } = require('../../src/infrastructure/services/FixtureRepository');

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
  console.log(COLORS.magenta + '  TITAN 数据资产审计系统 v2.0 (V6.7架构)' + COLORS.reset);
  console.log(COLORS.magenta + '  Data Asset Audit & Quality Assurance' + COLORS.reset);
  console.log(COLORS.magenta + '='.repeat(70) + COLORS.reset + '\n');
}

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
    
    // 如果文件数为 0，打印绝对路径帮助诊断
    if (jsonFiles.length === 0) {
      log('warning', `未找到 JSON 文件`);
      log('info', `扫描路径: ${path.resolve(DATA_PATH)}`);
      log('info', `请检查 DATA_MATCHES_PATH 环境变量或 Docker 挂载配置`);
    }
    
    // 统计文件大小分布
    let totalSize = 0;
    const sizeDistribution = { small: 0, medium: 0, large: 0 };
    
    for (const file of jsonFiles.slice(0, 100)) {
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
    log('error', `尝试访问的路径: ${path.resolve(DATA_PATH)}`);
    return { totalFiles: 0, files: [], avgSize: 0, sizeDistribution: {} };
  }
}

/**
 * 阶段 2: 内容抽检 - 随机抽取样本验证完整性
 */
async function contentSampling(files) {
  log('header', '🔍 阶段 2: 内容抽检 (随机 50 个样本)');
  
  if (files.length === 0) {
    log('warning', '无文件可供抽检');
    return { checked: 0, valid: 0, corrupted: 0, details: [] };
  }
  
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
  
  console.log();
  
  const passRate = sampleSize > 0 ? ((valid / sampleSize) * 100).toFixed(2) : 0;
  
  if (corrupted === 0) {
    log('success', `抽检完成: ${valid}/${sampleSize} 通过 (通过率: ${passRate}%)`);
  } else {
    log('warning', `抽检完成: ${valid} 有效, ${corrupted} 损坏 (通过率: ${passRate}%)`);
  }
  
  return { checked: sampleSize, valid, corrupted, passRate, corruptedFiles, details };
}

/**
 * 阶段 3: DB 对齐 - 使用 FixtureRepository 查询数据库
 */
async function databaseAlignment(repository) {
  log('header', '🗄️  阶段 3: 数据库对齐检查');
  
  try {
    // V6.7: 使用 Repository 而非直接 Pool
    const dbCount = await repository.getRawMatchDataCount();
    const recentRecords = await repository.getRecentRecords(5);
    
    log('success', `数据库记录总数: ${dbCount.toLocaleString()}`);
    log('info', '最近 5 条更新:');
    recentRecords.forEach((row, i) => {
      console.log(`      ${i + 1}. ${row.match_id} @ ${new Date(row.collected_at).toLocaleString()}`);
    });
    
    return { dbCount, recentRecords };
  } catch (error) {
    log('error', `数据库查询失败: ${error.message}`);
    return { dbCount: 0, recentRecords: [] };
  }
}

/**
 * 阶段 4: 生成质量报告
 */
function generateReport(inventory, sampling, alignment) {
  log('header', '📊 阶段 4: 数据质量报告');
  
  // 防御性处理：确保所有字段都有默认值
  const safeInventory = {
    totalFiles: inventory?.totalFiles ?? 0,
    avgSize: inventory?.avgSize ?? 0,
    files: inventory?.files ?? []
  };
  
  const safeSampling = {
    checked: sampling?.checked ?? 0,
    valid: sampling?.valid ?? 0,
    corrupted: sampling?.corrupted ?? 0,
    passRate: sampling?.passRate ?? 0,
    corruptedFiles: sampling?.corruptedFiles ?? []
  };
  
  const safeAlignment = {
    dbCount: alignment?.dbCount ?? 0,
    recentRecords: alignment?.recentRecords ?? []
  };
  
  console.log('\n' + COLORS.cyan + '╔════════════════════════════════════════════════════════════════╗' + COLORS.reset);
  console.log(COLORS.cyan + '║                    TITAN 数据资产质量报告                      ║' + COLORS.reset);
  console.log(COLORS.cyan + '╚════════════════════════════════════════════════════════════════╝' + COLORS.reset);
  
  console.log('\n' + COLORS.white + '【物理资产】' + COLORS.reset);
  console.log(`  JSON 文件总数:    ${safeInventory.totalFiles.toLocaleString().padStart(8)}`);
  console.log(`  平均文件大小:     ${safeInventory.avgSize.toLocaleString().padStart(8)} bytes`);
  
  console.log('\n' + COLORS.white + '【质量抽检】' + COLORS.reset);
  console.log(`  抽检样本数:       ${(safeSampling.checked || 'N/A').toString().padStart(8)}`);
  console.log(`  有效文件:         ${(safeSampling.valid || 'N/A').toString().padStart(8)}`);
  console.log(`  损坏/异常:        ${COLORS.red}${(safeSampling.corrupted || 'N/A').toString().padStart(8)}${COLORS.reset}`);
  console.log(`  抽检通过率:       ${safeSampling.checked > 0 ? safeSampling.passRate.toString() : 'N/A'}%`);
  
  console.log('\n' + COLORS.white + '【数据库对齐】' + COLORS.reset);
  console.log(`  数据库记录数:     ${safeAlignment.dbCount.toLocaleString().padStart(8)}`);
  
  const alignmentRate = safeAlignment.dbCount > 0 
    ? ((safeInventory.totalFiles / safeAlignment.dbCount) * 100).toFixed(2)
    : '0.00';
  const diff = safeInventory.totalFiles - safeAlignment.dbCount;
  
  console.log(`  文件/DB 对齐率:   ${alignmentRate.toString().padStart(8)}%`);
  
  if (diff === 0) {
    console.log(`  差异:             ${COLORS.green}完全对齐 ✓${COLORS.reset}`);
  } else if (diff > 0) {
    console.log(`  差异:             ${COLORS.yellow}文件多 ${diff} 个${COLORS.reset}`);
  } else {
    console.log(`  差异:             ${COLORS.yellow}DB 多 ${Math.abs(diff)} 个${COLORS.reset}`);
  }
  
  console.log('\n' + COLORS.cyan + '【总体评估】' + COLORS.reset);
  
  // 零资产情况特殊处理
  let quality;
  if (safeInventory.totalFiles === 0 && safeAlignment.dbCount === 0) {
    quality = { label: '空白资产', color: COLORS.yellow };
  } else if (safeInventory.totalFiles === 0) {
    quality = { label: '仅DB数据', color: COLORS.yellow };
  } else if (safeSampling.checked === 0) {
    quality = { label: '未抽检', color: COLORS.yellow };
  } else {
    quality = safeSampling.passRate >= 95 && Math.abs(diff) <= 10 
      ? { label: '优秀', color: COLORS.green }
      : safeSampling.passRate >= 90 && Math.abs(diff) <= 50
      ? { label: '良好', color: COLORS.yellow }
      : { label: '需关注', color: COLORS.red };
  }
  
  console.log(`  数据健康度:       ${quality.color}${quality.label}${COLORS.reset}`);
  
  if (safeSampling.corrupted > 0 && safeSampling.corruptedFiles.length > 0) {
    console.log('\n' + COLORS.red + '【建议补抓 ID 列表】' + COLORS.reset);
    safeSampling.corruptedFiles.slice(0, 10).forEach((id, i) => {
      console.log(`  ${i + 1}. ${id}`);
    });
    if (safeSampling.corruptedFiles.length > 10) {
      console.log(`  ... 还有 ${safeSampling.corruptedFiles.length - 10} 个`);
    }
  }
  
  console.log('\n' + COLORS.cyan + '='.repeat(66) + COLORS.reset + '\n');
  
  return {
    totalFiles: safeInventory.totalFiles,
    dbCount: safeAlignment.dbCount,
    alignmentRate,
    quality: quality.label,
    corruptedCount: safeSampling.corrupted,
    corruptedFiles: safeSampling.corruptedFiles
  };
}

/**
 * 主函数 (V6.7: 统一入口结构)
 */
async function main() {
  showBanner();
  
  const startTime = Date.now();
  let repository = null;
  
  try {
    // V6.7: 初始化 Repository 而非直接连接池
    repository = new FixtureRepository({
      dbPool: null, // 内部自动创建
      logger: { info: () => {}, error: () => {} },
      batchSize: 50
    });
    await repository.init();
    
    // 执行四个阶段
    const inventory = await physicalInventory();
    const sampling = await contentSampling(inventory.files);
    const alignment = await databaseAlignment(repository);
    const report = generateReport(inventory, sampling, alignment);
    
    const duration = ((Date.now() - startTime) / 1000).toFixed(2);
    log('success', `审计完成，耗时 ${duration} 秒`);
    
    return report.quality === '需关注' ? 1 : 0;
    
  } catch (error) {
    log('error', `审计失败: ${error.message}`);
    console.error(error.stack);
    return 1;
  } finally {
    // V6.7: 确保资源释放
    if (repository) {
      try {
        await repository.close();
      } catch (e) {
        log('warning', `Repository 关闭警告: ${e.message}`);
      }
    }
  }
}

// V6.7: 统一退出结构
main().then((exitCode) => {
  process.exit(exitCode || 0);
}).catch((error) => {
  log('error', `未捕获的异常: ${error.message}`);
  console.error(error.stack);
  process.exit(1);
});