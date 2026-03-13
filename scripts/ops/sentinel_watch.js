#!/usr/bin/env node
/**
 * @file TITAN 哨兵监控系统 (Sentinel Watch)
 * @description 自动化满仓检测与安全停机系统
 * @version 1.0.0
 * @module scripts/ops/sentinel_watch
 */

'use strict';

const fs = require('fs').promises;
const path = require('path');
const { exec } = require('child_process');
const { promisify } = require('util');
const { Pool } = require('pg');

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
  value: 12000,        // 初始默认值
  lastUpdated: 0,      // 上次更新时间
  cacheValid: false    // 缓存是否有效
};

// 数据库配置
const DB_CONFIG = {
  host: process.env.DB_HOST || 'host.docker.internal',
  port: parseInt(process.env.DB_PORT, 10) || 5432,
  database: process.env.DB_NAME || 'football_db',
  user: process.env.DB_USER || 'football_user',
  password: process.env.DB_PASSWORD || 'football_pass',
  max: 2, // 最小连接数
  idleTimeoutMillis: 30000
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
    sentinel: COLORS.magenta
  };
  const color = colorMap[level] || COLORS.reset;
  const timestamp = new Date().toISOString();
  console.log(`${color}[SENTINEL]${COLORS.reset} ${message}`);
}

/**
 * ASCII Art - VICTORY
 * @param target
 */
function printVictoryArt(target) {
  const art = `
${COLORS.green}${COLORS.bright}
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║     ████████╗██╗████████╗ █████╗ ███╗   ██╗    ███████╗██╗   ██╗██╗     ██╗      █████╗ ███╗   ██╗██████╗  ║
║     ╚══██╔══╝██║╚══██╔══╝██╔══██╗████╗  ██║    ██╔════╝██║   ██║██║     ██║     ██╔══██╗████╗  ██║██╔══██╗ ║
║        ██║   ██║   ██║   ███████║██╔██╗ ██║    █████╗  ██║   ██║██║     ██║     ███████║██╔██╗ ██║██║  ██║ ║
║        ██║   ██║   ██║   ██╔══██║██║╚██╗██║    ██╔══╝  ╚██╗ ██╔╝██║     ██║     ██╔══██║██║╚██╗██║██║  ██║ ║
║        ██║   ██║   ██║   ██║  ██║██║ ╚████║    ██║      ╚████╔╝ ███████╗███████╗██║  ██║██║ ╚████║██████╔╝ ║
║        ╚═╝   ╚═╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═══╝    ╚═╝       ╚═══╝  ╚══════╝╚══════╝╚═╝  ╚═╝╚═╝  ╚═══╝╚═════╝  ║
║                                                                  ║
║                    🎯 TARGET ACHIEVED: ${target.toLocaleString().padStart(6)} MATCHES 🎯         ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
${COLORS.reset}`;
  console.log(art);
}

/**
 * ASCII Art - FULL TANK
 * @param target
 */
function printFullTankArt(target) {
  const targetStr = target.toLocaleString();
  const padding = Math.max(0, 10 - targetStr.length);
  const leftPad = ' '.repeat(Math.floor(padding / 2));
  const rightPad = ' '.repeat(Math.ceil(padding / 2));
  
  const art = `
${COLORS.yellow}${COLORS.bright}
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║    ████████╗██╗████████╗ █████╗ ███╗   ██╗    ███████╗██╗   ██╗██╗     ███████╗    ║
║    ╚══██╔══╝██║╚══██╔══╝██╔══██╗████╗  ██║    ██╔════╝██║   ██║██║     ██╔════╝    ║
║       ██║   ██║   ██║   ███████║██╔██╗ ██║    █████╗  ██║   ██║██║     ███████╗    ║
║       ██║   ██║   ██║   ██╔══██║██║╚██╗██║    ██╔══╝  ╚██╗ ██╔╝██║     ╚════██║    ║
║       ██║   ██║   ██║   ██║  ██║██║ ╚████║    ██║      ╚████╔╝ ███████╗███████║    ║
║       ╚═╝   ╚═╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═══╝    ╚═╝       ╚═══╝  ╚══════╝╚══════╝    ║
║                                                                  ║
║              ████████╗ █████╗ ███╗   ██╗██╗  ██╗              ║
║              ╚══██╔══╝██╔══██╗████╗  ██║██║ ██╔╝              ║
║                 ██║   ███████║██╔██╗ ██║█████╔╝               ║
║                 ██║   ██╔══██║██║╚██╗██║██╔═██╗               ║
║                 ██║   ██║  ██║██║ ╚████║██║  ██╗              ║
║                 ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝              ║
║                                                                  ║
║                    🚀 ${leftPad}${targetStr} MATCHES COMPLETE ${rightPad}🚀                 ║
║                                                                  ║
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
 * 获取数据库记录数
 */
async function getDbCount() {
  const pool = new Pool(DB_CONFIG);
  try {
    const result = await pool.query('SELECT COUNT(*) as count FROM raw_match_data');
    return parseInt(result.rows[0].count, 10);
  } catch (error) {
    log('error', `数据库查询失败: ${error.message}`);
    return 0;
  } finally {
    await pool.end();
  }
}

/**
 * 获取动态目标值（从数据库查询总比赛数）
 * V4.51.5: 动态目标，拒绝硬编码
 */
async function getDynamicTarget() {
  const pool = new Pool(DB_CONFIG);
  try {
    const result = await pool.query('SELECT COUNT(*) as total FROM matches');
    const newTarget = parseInt(result.rows[0].total, 10);
    
    // 更新缓存
    dynamicTarget.value = newTarget;
    dynamicTarget.lastUpdated = Date.now();
    dynamicTarget.cacheValid = true;
    
    return newTarget;
  } catch (error) {
    // 容错处理：数据库连接失败时使用缓存值
    if (dynamicTarget.cacheValid) {
      log('warning', `数据库暂不可用，使用缓存目标值: ${dynamicTarget.value}`);
      return dynamicTarget.value;
    }
    
    // 如果连缓存都没有，使用初始默认值
    log('warning', `数据库连接失败，使用初始默认值: ${dynamicTarget.value}`);
    return dynamicTarget.value;
  } finally {
    await pool.end();
  }
}

/**
 * 写入胜利日志
 * @param fileCount
 * @param dbCount
 * @param targetCount
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
║ 对齐率:   ${dbCount > 0 ? ((fileCount / dbCount) * 100).toFixed(2) : 0}%                                     ║
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
  
  // V4.51.5: 每次循环开始时查询动态目标
  const targetCount = await getDynamicTarget();
  
  const fileCount = await getFileCount();
  const dbCount = await getDbCount();

  state.lastFileCount = fileCount;
  state.lastDbCount = dbCount;

  const remaining = Math.max(0, targetCount - fileCount);
  const progress = ((fileCount / targetCount) * 100).toFixed(1);

  // 打印进度
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

  // 检查是否达标
  if (fileCount >= targetCount) {
    state.consecutiveHits++;

    if (state.consecutiveHits >= CONFIG.debounceThreshold) {
      console.log('\n');
      state.isTriggered = true;

      // 触发庆典
      printVictoryArt(targetCount);
      printFullTankArt(targetCount);

      log('success', `🎯 目标达成！连续 ${CONFIG.debounceThreshold} 次检测确认`);
      log('info', `最终文件数: ${fileCount.toLocaleString()}`);
      log('info', `数据库记录: ${dbCount.toLocaleString()}`);

      // 写入日志
      const stats = await writeVictoryLog(fileCount, dbCount, targetCount);
      log('info', `平均收割速度: ${stats.avgSpeed} 场/分钟`);

      // 执行停机
      await executeShutdown();

      log('success', '══════════════════════════════════════════════════');
      log('success', '  TITAN 任务圆满完成！系统已进入休眠状态。');
      log('success', '══════════════════════════════════════════════════');

      process.exit(0);
    }
  } else {
    // 未达标，重置连续计数
    if (state.consecutiveHits > 0) {
      console.log('\n');
      log('warning', `进度回落，重置防抖计数器`);
    }
    state.consecutiveHits = 0;
  }
}

/**
 * 主监控循环
 */
async function main() {
  console.log('\n');
  log('sentinel', '══════════════════════════════════════════════════');
  log('sentinel', '  TITAN 哨兵监控系统启动');
  log('sentinel', '══════════════════════════════════════════════════');
  
  // V4.51.5: 查询动态目标
  const initialTarget = await getDynamicTarget();
  log('info', `当前动态目标: ${initialTarget.toLocaleString()} (由数据库实时提供)`);
  
  log('info', `检查间隔: ${CONFIG.checkInterval / 1000} 秒`);
  log('info', `数据目录: ${CONFIG.dataPath}`);
  log('info', `防抖阈值: ${CONFIG.debounceThreshold} 次连续达标`);
  log('sentinel', '══════════════════════════════════════════════════\n');

  // 初始检查
  await checkCycle();

  // 启动监控循环
  const intervalId = setInterval(async () => {
    await checkCycle();
  }, CONFIG.checkInterval);

  // 优雅退出处理
  process.on('SIGINT', () => {
    console.log('\n');
    log('warning', '接收到中断信号，哨兵正在撤退...');
    clearInterval(intervalId);
    process.exit(0);
  });

  process.on('SIGTERM', () => {
    console.log('\n');
    log('warning', '接收到终止信号，哨兵正在撤退...');
    clearInterval(intervalId);
    process.exit(0);
  });
}

// 执行
main().catch(err => {
  log('error', `哨兵系统异常: ${err.message}`);
  console.error(err);
  process.exit(1);
});