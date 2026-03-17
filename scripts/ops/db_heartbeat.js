#!/usr/bin/env node
/**
 * TITAN V6.0 DATABASE HEARTBEAT MONITOR
 * =====================================
 * 高频率数据库巡检脚本 - 捕获ULTIMATE-RECOVERY真金数据
 * 
 * @module scripts/ops/db_heartbeat
 * @version V6.0-RECOVERY
 */

'use strict';

const { Pool } = require('pg');
const fs = require('fs');
const path = require('path');

// 配置
const CONFIG = {
  pollIntervalMs: 30000,    // 30秒轮询
  dbReconnectDelayMs: 5000, // 5秒重连
  logFile: 'data/audit/db_heartbeat.log'
};

// 状态追踪
const state = {
  lastCount: 0,
  lastEntryTime: null,
  knownMatchIds: new Set(),
  totalV6Records: 0,
  startTime: Date.now()
};

// 数据库连接
const pool = new Pool({
  host: process.env.DB_HOST || '127.0.0.1',
  port: process.env.DB_PORT || 5432,
  database: process.env.DB_NAME || 'football_db',
  user: process.env.DB_USER || 'football_user',
  password: process.env.DB_PASSWORD || 'football_pass',
  connectionTimeoutMillis: 5000,
  query_timeout: 10000
});

// ANSI颜色代码
const COLORS = {
  reset: '\x1b[0m',
  bright: '\x1b[1m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  magenta: '\x1b[35m',
  cyan: '\x1b[36m',
  red: '\x1b[31m',
  gold: '\x1b[38;5;220m'
};

/**
 * 日志输出
 */
function log(level, message) {
  const timestamp = new Date().toISOString();
  const logLine = `[${timestamp}] [${level}] ${message}`;
  
  // 控制台输出
  if (level === 'NEW-GOLD-IN') {
    console.log(`${COLORS.gold}${COLORS.bright}${message}${COLORS.reset}`);
  } else if (level === 'HEARTBEAT') {
    console.log(`${COLORS.cyan}${message}${COLORS.reset}`);
  } else if (level === 'ERROR') {
    console.error(`${COLORS.red}${logLine}${COLORS.reset}`);
  } else {
    console.log(logLine);
  }
  
  // 文件日志
  try {
    fs.appendFileSync(CONFIG.logFile, logLine + '\n');
  } catch (e) {}
}

/**
 * 格式化时间差
 */
function formatTimeDiff(ms) {
  const seconds = Math.floor(ms / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  
  if (hours > 0) return `${hours}h ${minutes % 60}m`;
  if (minutes > 0) return `${minutes}m ${seconds % 60}s`;
  return `${seconds}s`;
}

/**
 * 生成变盘阶梯图
 */
function generateOddsLadder(history) {
  if (!history || history.length === 0) return 'N/A';
  
  const ladder = history.map((point, i) => {
    const odds = point.o || point.odds;
    if (!Array.isArray(odds) || odds.length < 3) return null;
    
    const homeOdds = parseFloat(odds[0]).toFixed(2);
    const arrow = i > 0 ? '→' : '│';
    return `${arrow} ${homeOdds}`;
  }).filter(Boolean);
  
  return ladder.join(' ');
}

/**
 * 生成完整的变盘路径展示
 */
function generateMovementDisplay(bet365Data) {
  if (!bet365Data || !bet365Data.movement || !bet365Data.movement.history) {
    return '无历史数据';
  }
  
  const history = bet365Data.movement.history;
  const lines = [];
  
  // 开盘
  if (bet365Data.opening) {
    const o = bet365Data.opening.o;
    lines.push(`  [OPEN ] ${new Date(bet365Data.opening.t).toLocaleTimeString()} | H:${o[0]} D:${o[1]} A:${o[2]}`);
  }
  
  // 中间点（最多显示3个）
  const midPoints = history.slice(1, -1);
  const displayPoints = midPoints.length > 3 
    ? [...midPoints.slice(0, 1), { t: '...', o: ['...', '...', '...'] }, ...midPoints.slice(-1)]
    : midPoints;
  
  for (const point of displayPoints.slice(0, 3)) {
    if (point.o === '...') {
      lines.push(`  [MOVE ] ...`);
    } else {
      const o = point.o || point.odds;
      const t = typeof point.t === 'number' 
        ? new Date(point.t * 1000).toLocaleTimeString() 
        : new Date(point.t).toLocaleTimeString();
      lines.push(`  [MOVE ] ${t} | H:${o[0]} D:${o[1]} A:${o[2]}`);
    }
  }
  
  // 收盘
  if (bet365Data.closing) {
    const o = bet365Data.closing.o;
    lines.push(`  [CLOSE] ${new Date(bet365Data.closing.t).toLocaleTimeString()} | H:${o[0]} D:${o[1]} A:${o[2]}`);
  }
  
  return lines.join('\n');
}

/**
 * 查询V6.0-ULTIMATE记录
 */
async function queryV6Records() {
  const query = `
    SELECT 
      match_id,
      market_sentiment->>'_schema_version' as schema_version,
      market_sentiment->>'extract_method' as method,
      market_sentiment->'bet365'->'metadata'->>'data_quality' as quality,
      market_sentiment->'bet365'->'metadata'->>'purity_score' as purity,
      jsonb_array_length(market_sentiment->'bet365'->'movement'->'history') as history_points,
      market_sentiment->'bet365' as bet365_data,
      market_sentiment->'_summary' as summary,
      created_at,
      updated_at
    FROM l3_features 
    WHERE market_sentiment->>'_schema_version' = 'V6.0-ULTIMATE'
    ORDER BY created_at DESC
  `;
  
  const result = await pool.query(query);
  return result.rows;
}

/**
 * 查询最新比赛的球队名称
 */
async function getMatchDetails(matchId) {
  try {
    const query = `
      SELECT home_team, away_team, match_date
      FROM matches 
      WHERE match_id = $1
      LIMIT 1
    `;
    const result = await pool.query(query, [matchId]);
    return result.rows[0] || { home_team: 'Unknown', away_team: 'Unknown', match_date: null };
  } catch (e) {
    return { home_team: 'Unknown', away_team: 'Unknown', match_date: null };
  }
}

/**
 * 检测新记录并触发告警
 */
async function detectNewRecords(records) {
  const currentCount = records.length;
  const newRecords = [];
  
  for (const record of records) {
    if (!state.knownMatchIds.has(record.match_id)) {
      newRecords.push(record);
      state.knownMatchIds.add(record.match_id);
    }
  }
  
  // 更新状态
  if (currentCount > state.lastCount) {
    state.totalV6Records = currentCount;
    state.lastEntryTime = new Date();
    
    // 触发黄金入库告警
    for (const record of newRecords) {
      await triggerGoldenAlert(record);
    }
  }
  
  state.lastCount = currentCount;
  return newRecords.length;
}

/**
 * 黄金入库告警
 */
async function triggerGoldenAlert(record) {
  const matchDetails = await getMatchDetails(record.match_id);
  const bet365Data = record.bet365_data || {};
  
  console.log('\n' + '═'.repeat(80));
  log('NEW-GOLD-IN', `✨ [NEW-GOLD-IN] Match: ${matchDetails.home_team} vs ${matchDetails.away_team} | ID: ${record.match_id}`);
  console.log('─'.repeat(80));
  
  // 数据质量检查
  const quality = record.quality || 'UNKNOWN';
  const points = record.history_points || 0;
  const purity = record.purity || 'N/A';
  
  console.log(`${COLORS.green}Quality: ${quality} | Points: ${points} | Purity: ${purity}${COLORS.reset}`);
  console.log(`${COLORS.yellow}Extract Method: ${record.method || 'N/A'}${COLORS.reset}`);
  console.log(`${COLORS.cyan}Created: ${record.created_at}${COLORS.reset}`);
  
  // 变盘阶梯图
  console.log('\n📈 变盘阶梯图:');
  const ladder = generateOddsLadder(bet365Data.movement?.history);
  console.log(`${COLORS.gold}${ladder}${COLORS.reset}`);
  
  // 详细变盘路径
  console.log('\n📊 变盘路径详情:');
  const movementDisplay = generateMovementDisplay(bet365Data);
  console.log(movementDisplay);
  
  console.log('═'.repeat(80) + '\n');
}

/**
 * 打印心跳汇总行
 */
function printHeartbeat(records) {
  const now = new Date();
  const timestamp = now.toLocaleTimeString();
  const count = records.length;
  
  let latencyStr = 'N/A';
  if (state.lastEntryTime) {
    const latencyMs = now - state.lastEntryTime;
    latencyStr = formatTimeDiff(latencyMs) + ' ago';
  } else if (count > 0) {
    latencyStr = 'initial';
  }
  
  // 计算平均变盘点
  const avgPoints = count > 0 
    ? (records.reduce((sum, r) => sum + (r.history_points || 0), 0) / count).toFixed(1)
    : 0;
  
  // 统计PREMIUM-GOLD数量
  const premiumCount = records.filter(r => r.quality === 'PREMIUM-GOLD').length;
  
  const heartbeatMsg = `[HEARTBEAT] ${timestamp} | Total V6: ${count} | Premium: ${premiumCount} | Avg Points: ${avgPoints} | Latency: ${latencyStr}`;
  
  log('HEARTBEAT', heartbeatMsg);
}

/**
 * 打印汇总报告
 */
function printSummary(records) {
  const runTime = formatTimeDiff(Date.now() - state.startTime);
  const premiumCount = records.filter(r => r.quality === 'PREMIUM-GOLD').length;
  
  console.log('\n' + '╔' + '═'.repeat(78) + '╗');
  console.log('║' + ' '.repeat(20) + '📊 ULTIMATE-RECOVERY 汇总报告' + ' '.repeat(27) + '║');
  console.log('╠' + '═'.repeat(78) + '╣');
  console.log(`║  运行时长: ${runTime.padEnd(66)}║`);
  console.log(`║  V6.0-ULTIMATE总记录: ${String(records.length).padEnd(50)}║`);
  console.log(`║  PREMIUM-GOLD记录: ${String(premiumCount).padEnd(53)}║`);
  console.log(`║  上次入库: ${(state.lastEntryTime ? state.lastEntryTime.toLocaleTimeString() : 'N/A').padEnd(59)}║`);
  console.log('╚' + '═'.repeat(78) + '╝\n');
}

/**
 * 主巡检循环
 */
async function heartbeatLoop() {
  try {
    // 查询V6.0记录
    const records = await queryV6Records();
    
    // 检测新记录
    const newCount = await detectNewRecords(records);
    
    // 打印心跳行
    printHeartbeat(records);
    
    // 如果有新记录，打印汇总
    if (newCount > 0) {
      printSummary(records);
    }
    
  } catch (error) {
    log('ERROR', `数据库查询失败: ${error.message}`);
    
    // 尝试重连
    if (error.code === 'ECONNREFUSED' || error.code === '28P01') {
      log('ERROR', '数据库连接失败，5秒后重试...');
      await new Promise(r => setTimeout(r, CONFIG.dbReconnectDelayMs));
    }
  }
}

/**
 * 初始化
 */
async function init() {
  // 确保日志目录存在
  const logDir = path.dirname(CONFIG.logFile);
  if (!fs.existsSync(logDir)) {
    fs.mkdirSync(logDir, { recursive: true });
  }
  
  // 打印启动横幅
  console.log('\n' + '╔' + '═'.repeat(78) + '╗');
  console.log('║' + ' '.repeat(15) + '💓 TITAN V6.0 DATABASE HEARTBEAT MONITOR' + ' '.repeat(22) + '║');
  console.log('║' + ' '.repeat(20) + 'ULTIMATE-RECOVERY 实时监视器' + ' '.repeat(29) + '║');
  console.log('╠' + '═'.repeat(78) + '╣');
  console.log(`║  轮询间隔: ${String(CONFIG.pollIntervalMs + 'ms').padEnd(63)}║`);
  console.log(`║  日志文件: ${CONFIG.logFile.padEnd(63)}║`);
  console.log(`║  数据库: ${String(pool.options.host + ':' + pool.options.port).padEnd(65)}║`);
  console.log('╚' + '═'.repeat(78) + '╝\n');
  
  // 首次查询
  await heartbeatLoop();
  
  // 启动定时轮询
  setInterval(heartbeatLoop, CONFIG.pollIntervalMs);
  
  log('INIT', '💓 心跳监视器已启动，每30秒巡检一次...');
}

// 优雅退出
process.on('SIGINT', async () => {
  console.log('\n\n' + '╔' + '═'.repeat(78) + '╗');
  console.log('║' + ' '.repeat(25) + '👋 监视器正在关闭...' + ' '.repeat(32) + '║');
  console.log('╚' + '═'.repeat(78) + '╝\n');
  
  await pool.end();
  process.exit(0);
});

process.on('SIGTERM', async () => {
  await pool.end();
  process.exit(0);
});

// 启动
init().catch(err => {
  log('ERROR', `启动失败: ${err.message}`);
  process.exit(1);
});