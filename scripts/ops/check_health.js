#!/usr/bin/env node
/**
 * @file TITAN 生产环境健康检查脚本
 * @description 自动检查：环境变量、数据库联通性、存储目录写入权限
 * @version 1.0.0
 * @module scripts/ops/check_health
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
  cyan: '\x1b[36m'
};

const LOG_PREFIX = '[HEALTH-CHECK]';

/**
 * 打印带颜色的日志
 * @param {string} level - 日志级别 (info|success|warning|error)
 * @param {string} message - 日志消息
 */
function log(level, message) {
  const colorMap = {
    info: COLORS.cyan,
    success: COLORS.green,
    warning: COLORS.yellow,
    error: COLORS.red
  };
  const color = colorMap[level] || COLORS.reset;
  const prefix = level === 'success' ? '✓' : level === 'error' ? '✗' : level === 'warning' ? '⚠' : 'ℹ';
  console.log(`${color}${prefix} ${LOG_PREFIX} ${message}${COLORS.reset}`);
}

/**
 * 显示横幅
 */
function showBanner() {
  console.log('\n' + '='.repeat(60));
  console.log('  TITAN 生产环境健康检查 v1.0');
  console.log('  Production Environment Health Check');
  console.log('='.repeat(60) + '\n');
}

/**
 * 检查 1: 环境变量加载状态
 * @returns {Promise<object>} 检查结果
 */
async function checkEnvironmentVariables() {
  log('info', '检查环境变量...');

  const requiredVars = [
    'DB_HOST',
    'DB_PORT',
    'DB_NAME',
    'DB_USER',
    'DB_PASSWORD'
  ];

  const optionalVars = [
    'DATA_MATCHES_PATH',
    'MAX_WORKERS',
    'MIN_DELAY_MS',
    'MAX_DELAY_MS',
    'PROXY_HOST',
    'PROXY_PORT'
  ];

  const results = {
    passed: true,
    required: {},
    optional: {},
    configPath: null
  };

  // 尝试加载 .env 文件
  const envPaths = [
    path.join(process.cwd(), 'config', '.env'),
    path.join(process.cwd(), '.env')
  ];

  let envLoaded = false;
  for (const envPath of envPaths) {
    try {
      await fs.access(envPath);
      require('dotenv').config({ path: envPath });
      results.configPath = envPath;
      envLoaded = true;
      break;
    } catch (err) {
      // 继续尝试下一个路径
    }
  }

  if (!envLoaded) {
    log('warning', '未找到 .env 文件，将使用默认配置');
  } else {
    log('success', `已加载环境变量: ${results.configPath}`);
  }

  // 检查必需变量
  for (const varName of requiredVars) {
    const value = process.env[varName];
    if (value && value !== 'your_secure_password_here') {
      results.required[varName] = { present: true, value: maskSensitive(varName, value) };
    } else {
      results.required[varName] = { present: false, value: null };
      results.passed = false;
    }
  }

  // 检查可选变量
  for (const varName of optionalVars) {
    const value = process.env[varName];
    results.optional[varName] = { present: !!value, value: value || '使用默认值' };
  }

  return results;
}

/**
 * 脱敏敏感信息
 * @param {string} varName - 变量名
 * @param {string} value - 变量值
 * @returns {string} 脱敏后的值
 */
function maskSensitive(varName, value) {
  if (varName.includes('PASSWORD') || varName.includes('SECRET') || varName.includes('KEY')) {
    return value.substring(0, 3) + '***' + value.substring(value.length - 3);
  }
  return value;
}

/**
 * 检查 2: 数据库联通性
 * @returns {Promise<object>} 检查结果
 */
async function checkDatabaseConnectivity() {
  log('info', '检查数据库联通性...');

  const dbConfig = {
    host: process.env.DB_HOST || 'host.docker.internal',
    port: parseInt(process.env.DB_PORT, 10) || 5432,
    database: process.env.DB_NAME || 'football_db',
    user: process.env.DB_USER || 'football_user',
    password: process.env.DB_PASSWORD || 'football_pass',
    connectionTimeoutMillis: 5000
  };

  const pool = new Pool(dbConfig);

  try {
    const client = await pool.connect();
    const result = await client.query('SELECT version(), NOW() as current_time');
    const version = result.rows[0].version.split(' ')[0];
    const currentTime = result.rows[0].current_time;

    // 检查数据表
    const tableResult = await client.query(`
      SELECT COUNT(*) as count FROM information_schema.tables
      WHERE table_schema = 'public' AND table_name = 'raw_match_data'
    `);
    const tableExists = tableResult.rows[0].count > 0;

    // 统计数据量
    let recordCount = 0;
    if (tableExists) {
      const countResult = await client.query('SELECT COUNT(*) as count FROM raw_match_data');
      recordCount = parseInt(countResult.rows[0].count, 10);
    }

    client.release();

    return {
      passed: true,
      host: dbConfig.host,
      port: dbConfig.port,
      database: dbConfig.database,
      version,
      currentTime,
      tableExists,
      recordCount
    };
  } catch (error) {
    return {
      passed: false,
      error: error.message,
      code: error.code
    };
  } finally {
    await pool.end();
  }
}

/**
 * 检查 3: 存储目录写入权限
 * @returns {Promise<object>} 检查结果
 */
async function checkStoragePermissions() {
  log('info', '检查存储目录权限...');

  const paths = [
    {
      name: 'DATA_MATCHES_PATH',
      path: process.env.DATA_MATCHES_PATH
        ? path.resolve(process.cwd(), process.env.DATA_MATCHES_PATH)
        : path.join(process.cwd(), 'data', 'matches'),
      required: true
    },
    {
      name: 'DATA_SESSIONS_PATH',
      path: process.env.DATA_SESSIONS_PATH
        ? path.resolve(process.cwd(), process.env.DATA_SESSIONS_PATH)
        : path.join(process.cwd(), 'data', 'sessions'),
      required: false
    },
    {
      name: 'DATA_DEBUG_PATH',
      path: process.env.DATA_DEBUG_PATH
        ? path.resolve(process.cwd(), process.env.DATA_DEBUG_PATH)
        : path.join(process.cwd(), 'data', 'debug'),
      required: false
    }
  ];

  const results = {
    passed: true,
    directories: {}
  };

  for (const dir of paths) {
    const dirResult = { path: dir.path };

    try {
      // 尝试创建目录
      await fs.mkdir(dir.path, { recursive: true });

      // 测试写入权限
      const testFile = path.join(dir.path, '.healthcheck_test');
      await fs.writeFile(testFile, 'test');
      await fs.unlink(testFile);

      dirResult.writable = true;
      dirResult.exists = true;
      log('success', `${dir.name}: ${dir.path} (可读写)`);
    } catch (error) {
      dirResult.writable = false;
      dirResult.error = error.message;
      results.passed = false;
      log('error', `${dir.name}: ${dir.path} - ${error.message}`);
    }

    results.directories[dir.name] = dirResult;
  }

  // 统计现有文件数量
  try {
    const matchesDir = results.directories['DATA_MATCHES_PATH']?.path;
    if (matchesDir) {
      const files = await fs.readdir(matchesDir);
      const jsonFiles = files.filter(f => f.endsWith('.json'));
      results.existingFiles = jsonFiles.length;
    }
  } catch (err) {
    results.existingFiles = 0;
  }

  return results;
}

/**
 * 检查 4: 会话文件存在性
 * @returns {Promise<object>} 检查结果
 */
async function checkSessionFile() {
  log('info', '检查会话文件...');

  const sessionPaths = [
    path.join(process.cwd(), 'manual_session.json'),
    path.join(process.cwd(), 'data', 'sessions', 'fotmob_session.json')
  ];

  for (const sessionPath of sessionPaths) {
    try {
      const stats = await fs.stat(sessionPath);
      const content = await fs.readFile(sessionPath, 'utf8');
      const data = JSON.parse(content);
      const cookieCount = data.cookies?.length || 0;

      return {
        found: true,
        path: sessionPath,
        size: stats.size,
        cookies: cookieCount,
        modified: stats.mtime
      };
    } catch (err) {
      // 继续检查下一个路径
    }
  }

  return {
    found: false,
    message: '未找到会话文件，请运行 Cookie 采集或导入脚本'
  };
}

/**
 * 生成总结报告
 * @param {object} results - 所有检查结果
 */
function generateReport(results) {
  console.log('\n' + '='.repeat(60));
  console.log('  健康检查总结报告');
  console.log('='.repeat(60));

  // 环境变量
  console.log('\n📋 环境变量:');
  console.log(`  配置文件: ${results.env.configPath || '未加载'}`);
  const requiredPassed = Object.values(results.env.required).filter(v => v.present).length;
  const requiredTotal = Object.keys(results.env.required).length;
  console.log(`  必需变量: ${requiredPassed}/${requiredTotal} 已配置`);

  // 数据库
  console.log('\n🗄️  数据库:');
  if (results.db.passed) {
    console.log(`  状态: ✓ 正常`);
    console.log(`  地址: ${results.db.host}:${results.db.port}/${results.db.database}`);
    console.log(`  版本: ${results.db.version}`);
    console.log(`  数据表: ${results.db.tableExists ? '已创建' : '未创建'}`);
    console.log(`  记录数: ${results.db.recordCount.toLocaleString()}`);
  } else {
    console.log(`  状态: ✗ 异常`);
    console.log(`  错误: ${results.db.error}`);
    console.log(`  代码: ${results.db.code}`);
  }

  // 存储目录
  console.log('\n💾 存储目录:');
  for (const [name, dir] of Object.entries(results.storage.directories)) {
    const status = dir.writable ? '✓ 可读写' : '✗ 不可写';
    console.log(`  ${name}: ${status}`);
  }
  console.log(`  现有数据文件: ${results.storage.existingFiles} 个`);

  // 会话文件
  console.log('\n🔐 会话文件:');
  if (results.session.found) {
    console.log(`  状态: ✓ 已找到`);
    console.log(`  路径: ${results.session.path}`);
    console.log(`  Cookie数量: ${results.session.cookies}`);
    console.log(`  修改时间: ${new Date(results.session.modified).toLocaleString()}`);
  } else {
    console.log(`  状态: ⚠ 未找到`);
    console.log(`  提示: ${results.session.message}`);
  }

  // 总体状态
  console.log('\n' + '='.repeat(60));
  const allPassed = results.env.passed && results.db.passed && results.storage.passed;
  if (allPassed) {
    console.log(`${COLORS.green}✓ 所有检查通过，系统准备就绪！${COLORS.reset}`);
  } else {
    console.log(`${COLORS.red}✗ 检查未通过，请修复上述问题后再启动收割${COLORS.reset}`);
  }
  console.log('='.repeat(60) + '\n');

  return allPassed;
}

/**
 * 主函数
 */
async function main() {
  showBanner();

  const results = {
    env: null,
    db: null,
    storage: null,
    session: null
  };

  try {
    // 执行各项检查
    results.env = await checkEnvironmentVariables();
    results.db = await checkDatabaseConnectivity();
    results.storage = await checkStoragePermissions();
    results.session = await checkSessionFile();

    // 生成报告
    const allPassed = generateReport(results);

    process.exit(allPassed ? 0 : 1);

  } catch (error) {
    log('error', `检查过程发生错误: ${error.message}`);
    console.error(error.stack);
    process.exit(1);
  }
}

// 执行
main();
