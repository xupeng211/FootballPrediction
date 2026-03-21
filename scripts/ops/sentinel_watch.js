#!/usr/bin/env node
/**
 * @file TITAN 哨兵监控系统 (Sentinel Watch) - V6.7 Refactored
 * @description 自动化满仓检测与安全停机系统
 * @version 2.0.0
 * @module scripts/ops/sentinel_watch
 * 
 * V6.7 重构:
 * - 修复双重连接池 Bug，使用单一共享连接池
 * - 使用 FixtureRepository 替代直接 Pool 操作
 * - 统一 main().catch() 入口结构
 */

'use strict';

const fs = require('fs').promises;
const path = require('path');
const { exec } = require('child_process');
const { promisify } = require('util');
const { FixtureRepository } = require('../../src/infrastructure/services/FixtureRepository');

const execAsync = promisify(exec);

// 配置常量
const CONFIG = {
  checkInterval: 60000, // 60秒
  dataPath: process.env.DATA_MATCHES_PATH
    ? path.resolve(process.cwd(), process.env.DATA_MATCHES_PATH)
    : path.join(process.cwd(), 'data', 'matches'),
  victoryLogPath: path.join(process.cwd(), 'logs', 'victory.log'),
  debounceThreshold: 2, // 连续2次达标才触发
  dockerComposeFile: 'docker-compose.dev.yml'
};

// 动态目标管理
const dynamicTarget = {
  value: 12000,
  lastUpdated: 0,
  cacheValid: false
};

// 颜色定义
const COLORS = {
  reset: '\x1b[0m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  cyan: '\x1b[36m',
  magenta: '\x1b[35m',
  red: '\x1b[31m',
  bright: '\x1b[1m'
};

// 状态追踪
const state = {
  checkCount: 0,
  consecutiveHits: 0,
  startTime: Date.now(),
  lastFileCount: 0,
  lastDbCount: 0,
  isTriggered: false
};

// V6.7: 共享 Repository 实例
let repository = null;

/**
 * 打印带颜色的日志
 */
function log(level, message) {
  const colorMap = {
    info: COLORS.cyan,
    success: COLORS.green,
    warning: COLORS.yellow,
    error: COLORS.red,
    sentinel: COLORS.magenta
  };
  const color = colorMap[level] || COLORS.reset;
  console.log(`${color}[SENTINEL]${COLORS.reset} ${message}`);
}

/**
 * ASCII Art - VICTORY
 */
function printVictoryArt(target) {
  const art = `
${COLORS.green}${COLORS.bright}
╔══════════════════════════════════════════════════════════════════╗
║                    TITAN VICTORY LOG                             ║
║                    TARGET: ${target.toLocaleString().padStart(6)} MATCHES                    ║
╚══════════════════════════════════════════════════════════════════╝
${COLORS.reset}`;
  console.log(art);
}

/**
 * 获取文件数量
 */
async function getFileCount() {
  try {
    const files = await fs.readdir(CONFIG.dataPath);
    const jsonFiles = files.filter(f => f.endsWith('.json') && !f.startsWith('.'));
    return jsonFiles.length;
  } catch (error) {
    log('error', `读取目录失败: ${error.message}`);
    return 0;
  }
}

/**
 * 获取数据库记录数 (V6.7: 使用共享 Repository)
 */
async function getDbCount() {
  try {
    return await repository.getRawMatchDataCount();
  } catch (error) {
    log('error', `数据库查询失败: ${error.message}`);
    return 0;
  }
}

/**
 * 获取动态目标值 (V6.7: 使用共享 Repository)
 */
async function getDynamicTarget() {
  try {
    // 查询 matches 表总数
    const client = await repository.dbPool.connect();
    try {
      const result = await client.query('SELECT COUNT(*) as total FROM matches');
      const newTarget = parseInt(result.rows[0].total, 10);
      
      dynamicTarget.value = newTarget;
      dynamicTarget.lastUpdated = Date.now();
      dynamicTarget.cacheValid = true;
      
      return newTarget;
    } finally {
      client.release();
    }
  } catch (error) {
    if (dynamicTarget.cacheValid) {
      log('warning', `数据库暂不可用，使用缓存目标值: ${dynamicTarget.value}`);
      return dynamicTarget.value;
    }
    log('warning', `数据库连接失败，使用初始默认值: ${dynamicTarget.value}`);
    return dynamicTarget.value;
  }
}

/**
 * 写入胜利日志
 */
async function writeVictoryLog(fileCount, dbCount, targetCount) {
  const duration = Date.now() - state.startTime;
  const durationMinutes = Math.round(duration / 60000);
  const avgSpeed = durationMinutes > 0 ? (fileCount / durationMinutes).toFixed(2) : 0;

  const logEntry = `
╔═══════════════════════════════════════════════════════════════╗
║                    TITAN VICTORY LOG                          ║
╠═══════════════════════════════════════════════════════════════╣
║ 达成时间: ${new Date().toISOString()}                           ║
║ 最终场数: ${fileCount.toLocaleString()} / ${targetCount.toLocaleString()}                              ║
║ 数据库数: ${dbCount.toLocaleString()}                              ║
║ 运行时长: ${durationMinutes} 分钟                                    ║
║ 平均速度: ${avgSpeed} 场/分钟                                     ║
╚═══════════════════════════════════════════════════════════════╝
`;

  try {
    await fs.mkdir(path.dirname(CONFIG.victoryLogPath), { recursive: true });
    await fs.appendFile(CONFIG.victoryLogPath, logEntry);
    log('success', `胜利日志已写入: ${CONFIG.victoryLogPath}`);
  } catch (error) {
    log('error', `写入日志失败: ${error.message}`);
  }

  return { durationMinutes, avgSpeed };
}

/**
 * 执行安全停机
 */
async function executeShutdown() {
  log('warning', '正在执行安全停机...');

  try {
    const { stdout, stderr } = await execAsync(
      `docker-compose -f ${CONFIG.dockerComposeFile} stop dev`,
      { cwd: process.cwd(), timeout: 30000 }
    );

    if (stdout) log('info', stdout);
    if (stderr) log('warning', stderr);

    log('success', '✓ 所有 Worker 已安全停止');
    return true;
  } catch (error) {
    log('error', `停机失败: ${error.message}`);
    return false;
  }
}

/**
 * 单次检查循环
 */
async function checkCycle() {
  if (state.isTriggered) return;

  state.checkCount++;
  
  const targetCount = await getDynamicTarget();
  const fileCount = await getFileCount();
  const dbCount = await getDbCount();

  state.lastFileCount = fileCount;
  state.lastDbCount = dbCount;

  const remaining = Math.max(0, targetCount - fileCount);
  const progress = ((fileCount / targetCount) * 100).toFixed(1);

  process.stdout.write('\r');
  process.stdout.write(
    `${COLORS.cyan}[SENTINEL]${COLORS.reset} ` +
    `检查 #${state.checkCount.toString().padStart(3)} | ` +
    `文件: ${COLORS.bright}${fileCount.toLocaleString()}${COLORS.reset}/${targetCount.toLocaleString()} ` +
    `(${progress}%) | ` +
    `DB: ${dbCount.toLocaleString()} | ` +
    `剩余: ${remaining.toLocaleString()} | ` +
    `连续命中: ${state.consecutiveHits}/${CONFIG.debounceThreshold}`
  );

  if (fileCount >= targetCount) {
    state.consecutiveHits++;

    if (state.consecutiveHits >= CONFIG.debounceThreshold) {
      console.log('\n');
      state.isTriggered = true;

      printVictoryArt(targetCount);

      log('success', `目标达成！连续 ${CONFIG.debounceThreshold} 次检测确认`);
      log('info', `最终文件数: ${fileCount.toLocaleString()}`);
      log('info', `数据库记录: ${dbCount.toLocaleString()}`);

      const stats = await writeVictoryLog(fileCount, dbCount, targetCount);
      log('info', `平均收割速度: ${stats.avgSpeed} 场/分钟`);

      await executeShutdown();

      log('success', '══════════════════════════════════════════════════');
      log('success', '  TITAN 任务圆满完成！系统已进入休眠状态。');
      log('success', '══════════════════════════════════════════════════');

      return true; // 触发退出
    }
  } else {
    if (state.consecutiveHits > 0) {
      console.log('\n');
      log('warning', `进度回落，重置防抖计数器`);
    }
    state.consecutiveHits = 0;
  }
  
  return false;
}

/**
 * 主监控循环
 */
async function main() {
  console.log('\n');
  log('sentinel', '══════════════════════════════════════════════════');
  log('sentinel', '  TITAN 哨兵监控系统启动 (V6.7)');
  log('sentinel', '══════════════════════════════════════════════════');

  // V6.7: 初始化 Repository
  repository = new FixtureRepository({
    dbPool: null,
    logger: { info: () => {}, error: () => {} },
    batchSize: 50
  });
  await repository.init();
  
  const initialTarget = await getDynamicTarget();
  log('info', `当前动态目标: ${initialTarget.toLocaleString()}`);
  log('info', `检查间隔: ${CONFIG.checkInterval / 1000} 秒`);
  log('info', `防抖阈值: ${CONFIG.debounceThreshold} 次连续达标`);
  log('sentinel', '══════════════════════════════════════════════════\n');

  // 初始检查
  const shouldExit = await checkCycle();
  if (shouldExit) return 0;

  // 启动监控循环
  return new Promise((resolve) => {
    const intervalId = setInterval(async () => {
      const shouldExit = await checkCycle();
      if (shouldExit) {
        clearInterval(intervalId);
        resolve(0);
      }
    }, CONFIG.checkInterval);

    // 优雅退出处理
    process.on('SIGINT', async () => {
      console.log('\n');
      log('warning', '接收到中断信号，哨兵正在撤退...');
      clearInterval(intervalId);
      if (repository) await repository.close();
      resolve(0);
    });

    process.on('SIGTERM', async () => {
      console.log('\n');
      log('warning', '接收到终止信号，哨兵正在撤退...');
      clearInterval(intervalId);
      if (repository) await repository.close();
      resolve(0);
    });
  });
}

// V6.7: 统一入口结构
main().then((exitCode) => {
  process.exit(exitCode || 0);
}).catch((err) => {
  log('error', `哨兵系统异常: ${err.message}`);
  console.error(err);
  process.exit(1);
});
