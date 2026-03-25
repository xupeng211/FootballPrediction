/**
 * ReconNavigator - 导航专家 (V11.0 Clean Sweep 版)
 * =================================================
 *
 * 职责: Playwright 网络拦截、AJAX 流量捕获、协议级数据提取
 * V11.0 变更:
 * - 移除所有 legacy DOM 爬取方法 (bruteForceExtract, extractRuntimeMatchLinks 等)
 * - 集成 ReconDecryptor 处理加密响应
 * - 仅保留协议级数据提取 (干净、稳定、可维护)
 *
 * @module infrastructure/recon/ReconNavigator
 * @version V11.0-CLEAN-SWEEP
 * @date 2026-03-25
 */

'use strict';

const { chromium } = require('playwright');
const { ReconErrorClassifier, ReconRetryStrategy, ReconCircuitBreaker } = require('./ReconResilience');
const { ReconDecryptor } = require('./ReconDecryptor');

/**
 * 导航专家类
 * @class ReconNavigator
 */
class ReconNavigator {
  constructor(options = {}) {
    this.logger = options.logger || console;
    this.proxy = options.proxy;
    this.headless = options.headless !== false;
    this.scrollAttempts = options.scrollAttempts || 10;
    this.scrollDelayMs = options.scrollDelayMs || 2000;

    this.retryStrategy = new ReconRetryStrategy({
      baseDelay: 1000, maxDelay: 30000, maxRetries: 3, jitterFactor: 0.1
    });

    this.circuitBreaker = new ReconCircuitBreaker({
      failureThreshold: 5, resetTimeoutMs: 60000
    });

    this.browser = null;
    this.context = null;
    this.page = null;
    this.isClosed = false;
    this.interceptedData = [];
    this.apiEndpoints = new Set();
    this.decryptor = new ReconDecryptor({ logger: this.logger });
  }

  /**
   * 启动浏览器并启用网络拦截
   * @returns {Promise<Page>}
   */
  async launch(options = {}) {
    return this.circuitBreaker.execute(async () => {
      const timeout = options.timeout || 60000;

      const launchOptions = {
        headless: this.headless,
        args: ['--no-sandbox', '--disable-setuid-sandbox'],
        timeout
      };

      if (this.proxy) {
        launchOptions.proxy = { server: `http://${this.proxy.host}:${this.proxy.port}` };
      }

      this.logger.info('navigator_launch_v11', { headless: this.headless });

      try {
        this.browser = await chromium.launch(launchOptions);
        this.context = await this.browser.newContext({
          userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
          viewport: { width: 1920, height: 1080 }
        });
        this.page = await this.context.newPage();
        this.isClosed = false;
        this.interceptedData = [];

        await this._enableNetworkInterception();
        await this.page.addInitScript(() => {
          Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        });

        return this.page;
      } catch (error) {
        this.logger.error('navigator_launch_failed', { error: error.message });
        throw error;
      }
    });
  }

  /**
   * 启用网络拦截 (V11.0 精简版)
   * @private
   */
  async _enableNetworkInterception() {
    if (!this.page) return;

    this.logger.info('network_interception_enabled');

    this.page.on('response', async (response) => {
      try {
        const url = response.url();
        if (!this._isPotentialMatchApi(url)) return;

        this.apiEndpoints.add(url);
        const body = await response.text();
        const data = await this._parseApiResponse(body, url);
        
        if (data && data.length > 0) {
          this.interceptedData.push(...data);
          this.logger.info('data_intercepted', { url: url.substring(0, 80), count: data.length });
        }
      } catch (e) {
        // 忽略解析错误
      }
    });
  }

  /**
   * 判断是否为潜在的 API 端点
   * @private
   */
  _isPotentialMatchApi(url) {
    const patterns = [
      /\/api\/.*match/i, /\/api\/.*event/i, /ajax\/.*match/i,
      /\/feed\/.*json/i, /\/data\/.*json/i, /\/api\/v\d+\//i,
      /\/matches\/football\/\d+/i, /ajax-sport-country-tournament-archive_/i
    ];
    return patterns.some(p => p.test(url));
  }

  /**
   * 解析 API 响应 (V11.0 简化版 - 优先直接解析)
   * @private
   */
  async _parseApiResponse(body, url = '') {
    if (!body || typeof body !== 'string') return [];
    const trimmed = body.trim();
    if (!trimmed) return [];

    // 标准 JSON 解析 (优先尝试)
    try {
      const json = JSON.parse(trimmed);
      return this._extractMatchesFromJson(json);
    } catch {
      // 不是标准 JSON，尝试解密
    }

    // 如果是加密响应，尝试解密
    if (url.includes('/ajax-')) {
      try {
        if (!this.decryptor.getAlgorithmVersion()) {
          await this.decryptor.extractDecryptor(this.page);
        }
        const decrypted = await this.decryptor.decrypt(trimmed);
        return this._extractMatchesFromJson(decrypted);
      } catch (e) {
        this.logger.debug('decryption_skipped', { url: url.substring(0, 50), reason: 'not_encrypted_or_failed' });
        return [];
      }
    }

    return [];
  }

  /**
   * 从 JSON 中提取比赛数据
   * @private
   */
  _extractMatchesFromJson(json) {
    const matches = [];
    if (!json || typeof json !== 'object') return matches;

    const extract = (obj, depth = 0) => {
      if (depth > 10) return;
      
      if (Array.isArray(obj)) {
        obj.forEach(item => {
          if (this._isMatchObject(item)) {
            const match = this._normalizeMatchObject(item);
            if (match) matches.push(match);
          } else if (typeof item === 'object') {
            extract(item, depth + 1);
          }
        });
      } else {
        Object.values(obj).forEach(value => {
          if (typeof value === 'object' && value !== null) {
            extract(value, depth + 1);
          }
        });
      }
    };

    extract(json);
    return matches;
  }

  /**
   * 判断对象是否为比赛对象
   * @private
   */
  _isMatchObject(obj) {
    if (!obj || typeof obj !== 'object') return false;
    const indicators = ['homeTeam', 'awayTeam', 'home', 'away', 'matchId', 'eventId', 'hash', 'id'];
    const keys = Object.keys(obj).map(k => k.toLowerCase());
    return indicators.filter(i => keys.some(k => k.includes(i.toLowerCase()))).length >= 2;
  }

  /**
   * 标准化比赛对象
   * @private
   */
  _normalizeMatchObject(obj) {
    try {
      let homeTeam = '', awayTeam = '';

      if (Array.isArray(obj.participants) && obj.participants.length >= 2) {
        const home = obj.participants.find(p => p?.side === 'home' || p?.isHome === true) || obj.participants[0];
        const away = obj.participants.find(p => p?.side === 'away' || p?.isHome === false) || obj.participants[1];
        homeTeam = home?.name || home?.title || '';
        awayTeam = away?.name || away?.title || '';
      } else {
        homeTeam = obj.homeTeam || obj.home || obj.home_team || obj.team1 || '';
        awayTeam = obj.awayTeam || obj.away || obj.away_team || obj.team2 || '';
      }

      if (typeof homeTeam === 'object') homeTeam = homeTeam.name || homeTeam.title || '';
      if (typeof awayTeam === 'object') awayTeam = awayTeam.name || awayTeam.title || '';

      const hash = obj.hash || obj.eventHash || obj.id || obj.matchId || obj.eventId || '';
      const slug = obj.slug || obj.eventSlug || '';
      const countrySlug = obj.countrySlug || obj.country || '';
      const leagueSlug = obj.leagueSlug || obj.competitionSlug || '';
      
      let url = obj.url || obj.link || '';
      if (!url && hash) {
        url = `https://www.oddsportal.com/football/${countrySlug}/${leagueSlug}/${slug}-${hash}/`;
      }

      if (!homeTeam || !awayTeam || !hash) return null;

      return { url, hash: hash.toString(), slug, homeTeam, awayTeam, source: 'api_intercept' };
    } catch {
      return null;
    }
  }

  /**
   * 导航到目标 URL
   * @returns {Promise<boolean>}
   */
  async navigate(url, options = {}) {
    if (!this.page) throw new Error('Navigator not launched');

    const timeout = options.timeout || 60000;
    const waitUntil = options.waitUntil || 'networkidle';

    this.logger.info('navigate_start', { url });
    this.interceptedData = [];

    try {
      await this.page.goto(url, { timeout, waitUntil });
      await this.page.waitForTimeout(3000);
      await this._triggerDataLoading();
      
      this.logger.info('navigate_complete', { 
        url, interceptedCount: this.interceptedData.length 
      });
      return true;
    } catch (error) {
      this.logger.error('navigate_error', { url, error: error.message });
      throw error;
    }
  }

  /**
   * 触发数据加载
   * @private
   */
  async _triggerDataLoading() {
    if (!this.page) return;
    
    // 简单滚动触发懒加载
    for (let i = 0; i < 3; i++) {
      await this.page.evaluate(() => window.scrollBy(0, 500));
      await this.page.waitForTimeout(1000);
    }
  }

  /**
   * 协议级档案抓取 (V11.0 主要数据获取方式)
   * @returns {Promise<Object>}
   */
  async protocolArchiveExtract(baseUrl, options = {}) {
    if (!this.page) throw new Error('Navigator not launched');

    const maxPages = options.maxPages || 50;
    const timeoutMs = options.timeoutMs || 90000;

    this.logger.info('protocol_archive_start', { baseUrl, maxPages });
    await this.navigate(baseUrl, { waitUntil: 'networkidle' });

    // 等待 API 端点被发现
    await this.page.waitForTimeout(2000);
    
    const archiveEndpoints = Array.from(this.apiEndpoints)
      .filter(url => /ajax-sport-country-tournament-archive_/i.test(url));

    if (archiveEndpoints.length === 0) {
      this.logger.warn('protocol_archive_no_api');
      return { matches: [], pagesScanned: 0, totalCandidates: 0 };
    }

    // 使用评分最高的端点
    const archiveApiUrl = archiveEndpoints.sort((a, b) => this._scoreArchiveUrl(b) - this._scoreArchiveUrl(a))[0];
    
    // 执行解密抓取
    const result = await this._fetchAndDecrypt(archiveApiUrl, maxPages, timeoutMs);
    
    this.logger.info('protocol_archive_complete', {
      pagesScanned: result.pageStats.length,
      totalCandidates: result.matches.length
    });

    return result;
  }

  /**
   * 评分档案 URL 质量
   * @private
   */
  _scoreArchiveUrl(url) {
    let score = 0;
    if (!url.includes('/1//')) score += 5;
    if (/\/archive_\/\d+\/[^/]+\/[^/]+\/\d+\/\d+\//i.test(url)) score += 8;
    if (/\/page\/\d+\//i.test(url)) score += 2;
    score += Math.min(url.length / 100, 3);
    return score;
  }

  /**
   * 获取并解密数据
   * @private
   */
  async _fetchAndDecrypt(apiBaseUrl, maxPages, timeoutMs) {
    const seenHashes = new Set();
    const matches = [];
    const pageStats = [];

    // 确保解密器已初始化
    if (!this.decryptor.getAlgorithmVersion()) {
      await this.decryptor.extractDecryptor(this.page);
    }

    const base = apiBaseUrl.split('?')[0].replace(/\/page\/\d+\/?$/, '').replace(/\/+$/, '');

    for (let page = 1; page <= maxPages; page++) {
      const url = page === 1 ? `${base}/?_=${Date.now()}` : `${base}/page/${page}/?_=${Date.now()}`;
      
      try {
        const response = await this.page.evaluate(async (fetchUrl, fetchTimeout) => {
          const ctrl = new AbortController();
          const timer = setTimeout(() => ctrl.abort(), fetchTimeout);
          try {
            const res = await fetch(fetchUrl, { credentials: 'include', signal: ctrl.signal });
            clearTimeout(timer);
            return { success: true, text: await res.text() };
          } catch (e) {
            clearTimeout(timer);
            return { success: false, error: e.message };
          }
        }, url, timeoutMs);

        if (!response.success) {
          pageStats.push({ page, rows: 0, error: response.error });
          break;
        }

        // 解密响应
        let decoded;
        try {
          decoded = await this.decryptor.decrypt(response.text);
        } catch (e) {
          pageStats.push({ page, rows: 0, error: 'decrypt_failed' });
          break;
        }

        const parsed = JSON.parse(decoded);
        const rows = Array.isArray(parsed?.d?.rows) ? parsed.d.rows : [];
        const total = Number(parsed?.d?.total) || 0;

        let newRows = 0;
        for (const row of rows) {
          const hash = row?.encodeEventId || '';
          if (!hash || seenHashes.has(hash)) continue;
          seenHashes.add(hash);
          newRows++;

          matches.push({
            url: `https://www.oddsportal.com${row.url || ''}`,
            hash: hash.toString(),
            homeTeam: row['home-name'] || row.homeName || '',
            awayTeam: row['away-name'] || row.awayName || '',
            matchDate: row['date-start-timestamp'] ? new Date(row['date-start-timestamp'] * 1000).toISOString() : null,
            source: 'archive_api'
          });
        }

        pageStats.push({ page, rows: rows.length, newRows, total });
        if (rows.length === 0) break;
        
        // 动态调整最大页数
        if (total > 0) {
          maxPages = Math.min(maxPages, Math.ceil(total / 50));
        }
      } catch (e) {
        pageStats.push({ page, rows: 0, error: e.message });
        break;
      }
    }

    return { matches, pagesScanned: pageStats.length, totalCandidates: matches.length, pageStats };
  }

  /**
   * 获取拦截数据
   * @returns {Array}
   */
  getInterceptedData() {
    const seen = new Set();
    return this.interceptedData.filter(item => {
      const key = item.hash || item.url;
      if (!key || seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  }

  /**
   * 关闭浏览器
   */
  async close() {
    this.isClosed = true;
    if (this.browser) {
      await this.browser.close();
      this.browser = null;
      this.page = null;
    }
  }
}

module.exports = { ReconNavigator };