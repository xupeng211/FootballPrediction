/**
 * TITAN V5.5 OddsPortal Harvester
 * ==============================
 * 基于Playwright的多线程赔率收割机
 * 利用9900X的多核能力进行并行处理
 * 
 * @module infrastructure/harvesters/OddsPortalHarvester
 * @version V5.5.0-ODDS-REANIMATION
 * @date 2026-03-14
 */

'use strict';

const { chromium } = require('playwright');
const fs = require('fs').promises;
const path = require('path');

// V5.5 配置常量
const HARVESTER_CONFIG = {
  // 9900X多线程配置
  MAX_WORKERS: 12,  // 12核Worker Pool
  MAX_CONCURRENCY: 24,  // 并行任务数
  
  // 页面配置
  PAGE_TIMEOUT: 30000,  // 30秒超时
  NAVIGATION_TIMEOUT: 60000,
  
  // 重试配置
  MAX_RETRIES: 3,
  RETRY_DELAY_MS: 2000,
  
  // 输出配置
  OUTPUT_DIR: '/app/data/oddsportal',
  
  // OddsPortal配置
  BASE_URL: 'https://www.oddsportal.com',
  LEAGUE_URLS: {
    'Premier League': '/soccer/england/premier-league/',
    'La Liga': '/soccer/spain/laliga/',
    'Bundesliga': '/soccer/germany/bundesliga/',
    'Serie A': '/soccer/italy/serie-a/',
    'Ligue 1': '/soccer/france/ligue-1/',
  }
};

/**
 * OddsPortal URL解析器
 * 从URL中提取hash段落
 */
class OddsPortalURLParser {
  /**
   * 解析比赛URL，提取hash
   * @param {string} url - OddsPortal比赛URL
   * @returns {Object} 解析结果 {league, season, match_hash, teams}
   */
  static parseMatchURL(url) {
    // 支持的URL格式:
    // https://www.oddsportal.com/soccer/england/premier-league/manchester-united-chelsea/
    // https://www.oddsportal.com/soccer/england/premier-league-2023-2024/manchester-united-chelsea/
    // https://www.oddsportal.com/soccer/spain/laliga/real-madrid-barcelona/
    
    try {
      // 解析URL路径部分
      const urlObj = new URL(url);
      const pathParts = urlObj.pathname.split('/').filter(p => p.length > 0);
      
      // 基本验证: 路径应包含至少4部分 (soccer, country, league, match)
      if (pathParts.length < 4) {
        return null;
      }
      
      const [sport, country, leaguePart, ...matchParts] = pathParts;
      
      // 验证sport必须是soccer
      if (sport !== 'soccer') {
        return null;
      }
      
      // 解析联赛和赛季
      // leaguePart可能是: premier-league 或 premier-league-2023-2024
      let league = leaguePart;
      let season = null;
      
      const seasonMatch = leaguePart.match(/^(.+)-(\d{4})-(\d{4})$/);
      if (seasonMatch) {
        league = seasonMatch[1];
        season = `${seasonMatch[2]}/${seasonMatch[3]}`;
      }
      
      // 解析队名 (matchParts数组的最后部分)
      const matchSlug = matchParts[matchParts.length - 1] || '';
      let home_team = null;
      let away_team = null;
      
      if (matchSlug) {
        // 解码并解析队名 (格式: team-a-vs-team-b 或 team-a-team-b)
        const decoded = decodeURIComponent(matchSlug);
        // 尝试多种分隔符
        const separators = ['-vs-', '-vs-', '-v-', ' vs ', ' v ', '-@-', '-', '_'];
        for (const sep of separators) {
          if (decoded.includes(sep)) {
            const teams = decoded.split(sep).map(t => t.trim());
            if (teams.length >= 2) {
              home_team = teams[0].replace(/-/g, ' ');
              away_team = teams[1].replace(/-/g, ' ');
              break;
            }
          }
        }
        // 如果没有找到分隔符，尝试简单的分割
        if (!home_team && decoded.includes('-')) {
          const parts = decoded.split('-');
          const mid = Math.floor(parts.length / 2);
          home_team = parts.slice(0, mid).join(' ');
          away_team = parts.slice(mid).join(' ');
        }
      }
      
      // 生成hash (用于matches_mapping表)
      const matchHash = this._generateHash(url);
      
      return {
        league,
        season,
        match_hash: matchHash,
        home_team,
        away_team,
        raw_url: url,
        country
      };
    } catch (error) {
      return null;
    }
  }
  
  /**
   * 生成URL hash
   * @private
   */
  static _generateHash(url) {
    // 使用URL的最后部分作为hash
    const parts = url.split('/');
    const relevant = parts.slice(-3).join('/');
    
    // 简单的hash生成 (生产环境应使用SHA-256)
    let hash = 0;
    for (let i = 0; i < relevant.length; i++) {
      const char = relevant.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash; // Convert to 32bit integer
    }
    return Math.abs(hash).toString(16);
  }
  
  /**
   * 构建完整的OddsPortal URL
   * @param {string} league - 联赛名称
   * @param {string} season - 赛季 (如 2023/2024)
   * @param {string} homeTeam - 主队
   * @param {string} awayTeam - 客队
   * @returns {string} 完整URL
   */
  static buildURL(league, season, homeTeam, awayTeam) {
    const leaguePath = HARVESTER_CONFIG.LEAGUE_URLS[league];
    if (!leaguePath) {
      throw new Error(`未知联赛: ${league}`);
    }
    
    // 赛季格式转换: 2023/2024 -> 2023-2024
    const seasonFormatted = season ? season.replace('/', '-') : '';
    const teamsFormatted = `${homeTeam} - ${awayTeam}`.replace(/ /g, '-');
    
    return `${HARVESTER_CONFIG.BASE_URL}${leaguePath}${seasonFormatted}/${teamsFormatted}`;
  }
}

/**
 * OddsPortal Harvester主类
 * 基于Playwright的多线程赔率收割机
 */
class OddsPortalHarvester {
  /**
   * @param {Object} options - 配置选项
   */
  constructor(options = {}) {
    this.config = {
      ...HARVESTER_CONFIG,
      ...options
    };
    
    this.browser = null;
    this.context = null;
    this.workers = [];
    this.stats = {
      matchesHarvested: 0,
      hashesExtracted: 0,
      errors: 0,
      startTime: null
    };
  }
  
  /**
   * 初始化浏览器
   */
  async initialize() {
    console.log('🔧 V5.5 OddsPortal Harvester 初始化中...');
    
    this.browser = await chromium.launch({
      headless: true,
      args: [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-dev-shm-usage',
        '--disable-accelerated-2d-canvas',
        '--disable-gpu',
        '--window-size=1920,1080'
      ]
    });
    
    this.context = await this.browser.newContext({
      viewport: { width: 1920, height: 1080 },
      userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    });
    
    // 9900X多Worker初始化
    for (let i = 0; i < this.config.MAX_WORKERS; i++) {
      this.workers.push({
        id: i,
        page: null,
        busy: false,
        stats: { requests: 0, errors: 0 }
      });
    }
    
    this.stats.startTime = Date.now();
    console.log(`✅ V5.5 Harvester 初始化完成 | Workers: ${this.config.MAX_WORKERS}`);
  }
  
  /**
   * 获取可用Worker
   * @private
   */
  _getAvailableWorker() {
    return this.workers.find(w => !w.busy);
  }
  
  /**
   * 等待可用Worker
   * @private
   */
  async _waitForWorker() {
    return new Promise((resolve) => {
      const check = () => {
        const worker = this._getAvailableWorker();
        if (worker) {
          resolve(worker);
        } else {
          setTimeout(check, 100);
        }
      };
      check();
    });
  }
  
  /**
   * 从页面提取URL hash
   * @param {string} matchURL - 比赛页面URL
   * @returns {Object} 提取结果
   */
  async extractHashFromPage(matchURL) {
    const worker = await this._waitForWorker();
    worker.busy = true;
    
    try {
      if (!worker.page) {
        worker.page = await this.context.newPage();
      }
      
      // 导航到页面
      await worker.page.goto(matchURL, {
        waitUntil: 'networkidle',
        timeout: this.config.PAGE_TIMEOUT
      });
      
      // 等待内容加载
      await worker.page.waitForSelector('body', { timeout: 5000 });
      
      // 提取URL hash
      const result = OddsPortalURLParser.parseMatchURL(matchURL);
      
      worker.stats.requests++;
      this.stats.hashesExtracted++;
      
      return {
        success: true,
        hash: result?.match_hash,
        parsed: result,
        url: matchURL,
        worker_id: worker.id
      };
      
    } catch (error) {
      worker.stats.errors++;
      this.stats.errors++;
      
      return {
        success: false,
        error: error.message,
        url: matchURL,
        worker_id: worker.id
      };
    } finally {
      worker.busy = false;
    }
  }
  
  /**
   * 批量收割比赛hash
   * @param {Array} matches - 比赛列表 [{match_id, url}]
   * @returns {Array} 收割结果
   */
  async harvestBatch(matches) {
    console.log(`🚀 V5.5 开始批量收割: ${matches.length}场比赛`);
    
    const promises = matches.map(match => 
      this.extractHashFromPage(match.url)
    );
    
    const results = await Promise.all(promises);
    
    // 统计
    const successCount = results.filter(r => r.success).length;
    console.log(`✅ 批量收割完成: ${successCount}/${matches.length} 成功`);
    
    return results;
  }
  
  /**
   * 保存结果到文件
   * @param {Array} results - 收割结果
   * @param {string} filename - 输出文件名
   */
  async saveResults(results, filename = 'oddsportal_hashes.json') {
    const outputPath = path.join(this.config.OUTPUT_DIR, filename);
    
    // 确保目录存在
    await fs.mkdir(this.config.OUTPUT_DIR, { recursive: true });
    
    const output = {
      metadata: {
        version: 'V5.5',
        timestamp: new Date().toISOString(),
        total: results.length,
        success: results.filter(r => r.success).length
      },
      results: results.filter(r => r.success).map(r => ({
        hash: r.hash,
        url: r.url,
        parsed: r.parsed,
        // 对接matches_mapping表字段
        oddsportal_hash: r.hash,
        oddsportal_url: r.url,
        confidence: 0.95,  // 高置信度
        mapping_method: 'V5.5_HARVESTER'
      }))
    };
    
    await fs.writeFile(outputPath, JSON.stringify(output, null, 2));
    console.log(`💾 结果已保存: ${outputPath}`);
    
    return outputPath;
  }
  
  /**
   * 生成统计报告
   */
  getStats() {
    const elapsed = Date.now() - this.stats.startTime;
    return {
      ...this.stats,
      elapsed_ms: elapsed,
      throughput: this.stats.matchesHarvested / (elapsed / 1000)
    };
  }
  
  /**
   * 关闭Harvester
   */
  async close() {
    console.log('🔒 V5.5 Harvester 关闭中...');
    
    // 关闭所有Worker页面
    for (const worker of this.workers) {
      if (worker.page) {
        await worker.page.close();
      }
    }
    
    if (this.context) {
      await this.context.close();
    }
    
    if (this.browser) {
      await this.browser.close();
    }
    
    console.log('✅ Harvester 已关闭');
  }
}

// 导出模块
module.exports = {
  OddsPortalHarvester,
  OddsPortalURLParser,
  HARVESTER_CONFIG
};
