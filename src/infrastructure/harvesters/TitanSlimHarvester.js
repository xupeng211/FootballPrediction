/* eslint-disable complexity, max-lines */
/**
 * TitanSlimHarvester - V6.6-SLIM-PRO 网络硬化版
 * ==============================================
 *
 * 架构理念: 采集只做一件事 - 抓原始 JSON
 * 数据质量: 后置清洗，不阻塞采集流程
 *
 * V6.6-SLIM-PRO 升级:
 * - ✅ 资源拦截: 丢弃 image/stylesheet/font/media
 * - ✅ 智能等待: domcontentloaded 策略
 * - ✅ 代理池: 12 Worker × 12 IP (NetworkShield)
 * - 零 SessionManager 依赖
 * - 12 并发原生支持 (9900X 优化)
 * - 64MB shm 兼容
 *
 * @module infrastructure/harvesters/TitanSlimHarvester
 * @version V6.6-SLIM-PRO
 */

'use strict';

const { Pool } = require('pg');
const { chromium } = require('playwright');
const pLimit = require('p-limit');
const fs = require('fs').promises;
const path = require('path');

// SLIM-PRO: 引入 NetworkShield
const { getNetworkShield } = require('../network/NetworkShield');

// 精简配置
const DEFAULT_CONFIG = {
  concurrency: 12,           // 9900X 默认 12 并发
  minDelayMs: 5000,          // 5-10s 延迟
  maxDelayMs: 10000,
  batchSize: 500,
  headless: true,
  dataPath: 'data/matches',
  verbose: false             // SLIM-PRO: 详细日志开关
};

/**
 * TitanSlimHarvester - 极简收割引擎 (SLIM-PRO 版)
 */
class TitanSlimHarvester {
  constructor(config = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config };
    
    // 数据库连接池
    this.dbPool = new Pool({
      host: process.env.DB_HOST || 'localhost',
      port: process.env.DB_PORT || 5432,
      database: process.env.DB_NAME || 'football_db',
      user: process.env.DB_USER || 'football_user',
      password: process.env.DB_PASSWORD || 'football_pass',
      max: 20,
      idleTimeoutMillis: 30000
    });

    // 浏览器实例 (所有 Worker 共享)
    this.browser = null;
    
    // SLIM-PRO: NetworkShield 代理池
    this.networkShield = getNetworkShield();
    
    // 统计
    this.stats = {
      total: 0,
      success: 0,
      failed: 0,
      startTime: null
    };
    
    // SLENT-MODE: 日志级别控制 (V6.6)
    this.config.silent = config.silent !== undefined ? config.silent : process.env.SILENT_MODE !== 'false';
    
    // 🔧 P1 FIX: 环境变量对齐 - 数据哨兵配置
    this.config.dataSentinelMinSize = parseInt(process.env.DATA_SENTINEL_MIN_SIZE) || 5120; // 默认 5KB
    this.config.enableScreenshot = process.env.ENABLE_SCREENSHOT === 'true'; // 默认 false
    
    this.logger = {
      info: (...args) => !this.config.silent && console.log(...args),
      warn: (...args) => console.warn(...args),
      error: (...args) => console.error(...args),
      banner: (...args) => console.log(...args),
      progress: (...args) => console.log(...args)
    };
  }

  /**
   * 初始化浏览器 (只启动一次)
   */
  async init() {
    this.logger.info('🚀 [TITAN-SLIM] 启动浏览器...');
    
    this.browser = await chromium.launch({
      headless: this.config.headless,
      args: [
        '--disable-dev-shm-usage',     // 关键: 禁用 /dev/shm，使用磁盘
        '--disable-gpu',
        '--disable-software-rasterizer',
        '--disable-extensions',
        '--disable-background-networking',
        '--disable-sync',
        '--no-first-run',
        '--no-sandbox',
        '--disable-setuid-sandbox'
      ]
    });

    this.logger.info('✅ [TITAN-SLIM] 浏览器就绪');
  }

  /**
   * 批量收割
   * @param {Array} matches - 比赛列表 [{match_id, external_id, ...}]
   * @returns {Promise<object>} 统计
   */
  async batchHarvest(matches) {
    if (!matches || matches.length === 0) {
      return { success: false, reason: 'EMPTY_LIST' };
    }

    this.stats.total = matches.length;
    this.stats.startTime = Date.now();

    this.logger.banner('');
    this.logger.banner('╔═══════════════════════════════════════════════════════════════╗');
    this.logger.banner('║  🚀 TITAN-SLIM-PRO V6.6                                       ║');
    this.logger.banner('║  网络硬化 | 资源拦截 | 12 Worker × 12 IP | 极速采集          ║');
    this.logger.banner('╚═══════════════════════════════════════════════════════════════╝');
    this.logger.banner(`📊 任务: ${matches.length} 场比赛`);
    this.logger.banner(`🐝 并发: ${this.config.concurrency} (9900X 优化)`);
    this.logger.banner(`🛡️  代理: NetworkShield 22 节点池 (Worker 独立 IP)`);
    this.logger.banner(`⚡ 策略: domcontentloaded + 拦截 image/css/font/media`);
    this.logger.banner(`💾 存储: 直接入库 raw_match_data (无实时校验)`);
    this.logger.banner(`🔇 静默模式: ${this.config.silent ? '开启 (仅看板输出)' : '关闭 (详细输出)'}`);
    this.logger.banner('');

    // pLimit 并发控制
    const limit = pLimit(this.config.concurrency);

    const results = await Promise.all(
      matches.map((match, index) =>
        limit(async () => {
          // 错峰延迟
          const delay = this.config.minDelayMs + 
            Math.random() * (this.config.maxDelayMs - this.config.minDelayMs);
          await this._sleep(delay);

          return this._harvestSingle(match, index);
        })
      )
    );

    // 汇总
    results.forEach(r => {
      if (r.success) this.stats.success++;
      else this.stats.failed++;
    });

    return this._generateReport();
  }

  /**
   * 单场收割 (SLIM-PRO 核心逻辑)
   * @private
   */
  async _harvestSingle(match, index) {
    const { match_id, external_id, home_team, away_team } = match;
    const workerId = (index % this.config.concurrency) + 1;
    const startTime = Date.now();
    
    // 🔒 P1 FIX: 资源声明移到 try 外，确保 finally 可以访问
    let context = null;
    let page = null;
    let proxyConfig = null;

    try {
      this.logger.info(`[W${workerId}] 🎯 ${match_id} | ${home_team} vs ${away_team}`);

      // SLIM-PRO: 从 NetworkShield 获取代理配置
      proxyConfig = this.networkShield.assignPort(workerId);
      
      this.logger.info(`[W${workerId}] 🔌 代理: ${proxyConfig.host}:${proxyConfig.port}`);

      // 创建上下文 (带代理)
      context = await this.browser.newContext({
        viewport: { width: 1920, height: 1080 },
        userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.0',
        proxy: {
          server: proxyConfig.url
        }
      });
      
      page = await context.newPage();

      // SLIM-PRO: 资源拦截 - 丢弃 image/stylesheet/font/media
      await page.route('**/*', (route) => {
        const resourceType = route.request().resourceType();
        if (['image', 'stylesheet', 'font', 'media'].includes(resourceType)) {
          this.logger.info(`[W${workerId}] 🚫 拦截 ${resourceType}: ${route.request().url().substring(0, 60)}...`);
          route.abort();
        } else {
          route.continue();
        }
      });

      // SLIM-PRO: 智能等待 - domcontentloaded 策略 (极速采集)
      const url = `https://www.fotmob.com/match/${external_id}`;
      const navStart = Date.now();
      
      await page.goto(url, { 
        waitUntil: 'domcontentloaded',  // 只要 DOM 构建完成就继续
        timeout: 30000 
      });
      
      const navTime = Date.now() - navStart;

      // 🔒 数据哨兵: 从 __NEXT_DATA__ 提取 (FotMob V2025 架构)
      let rawData = null;
      let dataSource = '';
      
      // 方式 1: 等待 __NEXT_DATA__ script 标签出现 (script 是 hidden，用 state: 'attached')
      try {
        await page.waitForSelector('#__NEXT_DATA__', { 
          state: 'attached',  // script 标签是 hidden，不能等 'visible'
          timeout: 10000 
        });
        rawData = await page.evaluate(() => {
          const el = document.getElementById('__NEXT_DATA__');
          return el ? JSON.parse(el.textContent) : null;
        });
        
        if (rawData && Object.keys(rawData).length > 0) {
          dataSource = '__NEXT_DATA__';
          this.logger.info(`[W${workerId}] 🔒 数据哨兵: ${dataSource} 已提取 (${Date.now() - navStart}ms)`);
        } else {
          throw new Error('__NEXT_DATA__ 为空');
        }
      } catch (e) {
        // 方式 2: 兜底 - 返回错误信息
        throw new Error(`数据哨兵: 无法提取 __NEXT_DATA__ - ${e.message}`);
      }

      // 🔒 数据哨兵: 断言检查 (使用环境变量配置)
      const dataSize = JSON.stringify(rawData).length;
      if (dataSize < this.config.dataSentinelMinSize) {
        throw new Error(`数据哨兵拦截: 数据源=${dataSource}, 数据仅 ${(dataSize/1024).toFixed(1)}KB (< ${this.config.dataSentinelMinSize/1024}KB 阈值)，判定为无效空壳`);
      }

      const totalTime = Date.now() - startTime;

      // 直接入库
      await this._saveToDatabase(match_id, external_id, rawData);

      // SLIM-PRO: 详细性能日志 (始终显示数据大小)
      if (this.config.verbose) {
        this.logger.progress(`[W${workerId}] ✅ ${match_id} | 导航:${navTime}ms 稳定:500ms 总:${totalTime}ms 数据:${(dataSize/1024).toFixed(1)}KB`);
      } else {
        this.logger.progress(`[W${workerId}] ✅ ${match_id} | 已入库 (${totalTime}ms, ${(dataSize/1024).toFixed(1)}KB)`);
      }
      
      // 标记代理成功 (健壮性检查)
      if (this.networkShield && typeof this.networkShield.markSuccess === 'function') {
        this.networkShield.markSuccess(proxyConfig.port);
      }
      
      return { success: true, match_id, size: dataSize, time: totalTime };

    } catch (error) {
      const failTime = Date.now() - startTime;
      this.logger.error(`[W${workerId}] ❌ ${match_id} | ${error.message} (${failTime}ms)`);
      
      // 标记代理失败 (使用正确的 API: markFailed)
      if (proxyConfig && this.networkShield && typeof this.networkShield.markFailed === 'function') {
        try {
          this.networkShield.markFailed(proxyConfig.port, error.message);
        } catch (e) {
          // 忽略代理标记错误
        }
      }
      
      return { success: false, match_id, error: error.message, time: failTime };
      
    } finally {
      // 🔒 P1 FIX: 确保资源释放，防止内存泄露
      if (page) {
        try { await page.close(); } catch (e) { /* 忽略关闭错误 */ }
      }
      if (context) {
        try { await context.close(); } catch (e) { /* 忽略关闭错误 */ }
      }
    }
  }

  /**
   * 保存到数据库 (带数据哨兵最终检查)
   * @private
   */
  async _saveToDatabase(matchId, externalId, rawData) {
    const client = await this.dbPool.connect();
    
    try {
      // 🔒 数据哨兵: 入库前最终检查
      const jsonData = JSON.stringify(rawData);
      if (jsonData.length < 1024) {  // 必须 > 1KB
        throw new Error(`数据哨兵最终拦截: 数据仅 ${(jsonData.length/1024).toFixed(1)}KB，拒绝入库`);
      }

      const query = `
        INSERT INTO raw_match_data (match_id, external_id, raw_data, collected_at, data_version)
        VALUES ($1, $2, $3, NOW(), 'V26.1')
        ON CONFLICT (match_id)
        DO UPDATE SET 
          raw_data = EXCLUDED.raw_data,
          collected_at = NOW()
        RETURNING match_id
      `;
      
      await client.query(query, [
        matchId,
        externalId,
        jsonData
      ]);
      
    } finally {
      client.release();
    }
  }

  /**
   * 获取待收割比赛 (查询 matches 表)
   */
  async getPendingMatches(limit = 500) {
    const client = await this.dbPool.connect();
    
    try {
      const query = `
        SELECT m.match_id, m.external_id, m.home_team, m.away_team, m.match_date
        FROM matches m
        LEFT JOIN raw_match_data r ON m.match_id = r.match_id
        WHERE r.match_id IS NULL
        ORDER BY m.match_date
        LIMIT $1
      `;
      
      const result = await client.query(query, [limit]);
      return result.rows;
      
    } finally {
      client.release();
    }
  }

  /**
   * 生成报告
   * @private
   */
  _generateReport() {
    const duration = Date.now() - this.stats.startTime;
    const rate = this.stats.total > 0 ? (this.stats.total / (duration / 1000)).toFixed(2) : '0.00';

    return {
      total: this.stats.total,
      success: this.stats.success,
      failed: this.stats.failed,
      duration: `${(duration / 1000).toFixed(1)}s`,
      rate: `${rate} 场/秒`,
      efficiency: `${((this.stats.success / this.stats.total) * 100).toFixed(1)}%`
    };
  }

  /**
   * 清理资源
   */
  async cleanup() {
    if (this.browser) {
      await this.browser.close();
      this.logger.info('🛑 [TITAN-SLIM] 浏览器已关闭');
    }
    
    if (this.dbPool) {
      await this.dbPool.end();
      this.logger.info('🛑 [TITAN-SLIM] 数据库连接已释放');
    }
  }

  /**
   * 延迟
   * @private
   */
  _sleep(ms) {
    return new Promise(resolve => {
      setTimeout(resolve, ms);
    });
  }
}

module.exports = { TitanSlimHarvester };
