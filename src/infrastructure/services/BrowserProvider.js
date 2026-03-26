/**
 * @file BrowserProvider - Playwright 浏览器生命周期管理
 * @module infrastructure/services/BrowserProvider
 * @version V6.7.4-STEALTH
 * @description
 * 职责: 管理 Playwright 实例、Context 隔离、Stealth 配置
 * 从 DiscoveryService 解耦，支持独立测试和复用
 */

'use strict';

const { chromium } = require('playwright');

/**
 * 浏览器提供者
 * @class BrowserProvider
 */
class BrowserProvider {
  /**
   * 创建浏览器提供者
   * @param {Object} options - 配置选项
   * @param {Object} options.logger - 日志对象
   * @param {boolean} options.headless - 是否无头模式 (默认: true)
   * @param {Object} options.viewport - 视口大小 (默认: 1920x1080)
   */
  constructor(options = {}) {
    this.logger = options.logger || {
      info: () => {},
      warn: () => {},
      error: () => {}
    };
    
    this.config = {
      headless: options.headless !== false,
      viewport: options.viewport || { width: 1920, height: 1080 },
      userAgent: options.userAgent || 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    };
    
    this.browser = null;
    this.page = null;
    this.defaultTimeoutMs = options.defaultTimeoutMs || 20000;
  }

  /**
   * 检查浏览器是否已初始化
   * @returns {boolean}
   */
  isInitialized() {
    return this.browser !== null && this.page !== null;
  }

  /**
   * 初始化浏览器 (闪击模式)
   * @returns {Promise<Page>} Playwright Page 实例
   */
  async initialize() {
    if (this.isInitialized()) {
      return this.page;
    }
    
    this.logger.info('[BrowserProvider] 🕵️  启动影子浏览器 (闪击模式)...');
    
    try {
      this.browser = await chromium.launch({
        headless: this.config.headless,
        args: [
          '--disable-dev-shm-usage',
          '--disable-gpu',
          '--disable-software-rasterizer',
          '--disable-extensions',
          '--disable-background-networking',
          '--disable-sync',
          '--no-first-run',
          '--disable-default-apps',
          '--disable-background-timer-throttling',
          '--disable-backgrounding-occluded-windows',
          '--disable-renderer-backgrounding',
          '--blink-settings=imagesEnabled=false',
          '--disable-setuid-sandbox',
          '--no-sandbox'
        ]
      });
      
      this.page = await this.browser.newPage({
        viewport: this.config.viewport,
        userAgent: this.config.userAgent
      });
      
      this.logger.info('[BrowserProvider] ✅ 浏览器实例创建成功');
      return this.page;
      
    } catch (error) {
      this.logger.error(`[BrowserProvider] ❌ 浏览器启动失败: ${error.message}`);
      throw error;
    }
  }

  /**
   * 访问初始页面获取 Cookies
   * @param {string} url - 初始页面 URL
   * @param {Object} options - 导航选项
   * @returns {Promise<void>}
   */
  async warmup(url = 'https://www.fotmob.com/', options = {}) {
    if (!this.isInitialized()) {
      await this.initialize();
    }
    
    this.logger.info('[BrowserProvider] 🍪 获取初始 Cookies (轻量模式)...');
    
    try {
      await this.page.goto(url, {
        waitUntil: options.waitUntil || 'domcontentloaded',
        timeout: options.timeout || 15000
      });
      
      this.logger.info('[BrowserProvider] ✅ 页面预热完成');
    } catch (error) {
      // 宽容模式: 即使主页加载失败，也可能已获取到 Cookie
      this.logger.warn(`[BrowserProvider] ⚠️  页面预热警告: ${error.message}`);
      this.logger.warn('[BrowserProvider] 💡 继续执行 (Cookie 可能已获取)');
    }
  }

  /**
   * 获取当前 Page 实例
   * @returns {Page|null}
   */
  getPage() {
    return this.page;
  }

  /**
   * 获取当前 Browser 实例
   * @returns {Browser|null}
   */
  getBrowser() {
    return this.browser;
  }

  /**
   * 在浏览器上下文内执行 fetch 请求
   * @param {string} url - 请求 URL
   * @param {Object} options - fetch 选项
   * @returns {Promise<Object>} 响应数据
   */
  async fetch(url, options = {}) {
    if (!this.isInitialized()) {
      await this.initialize();
    }
    
    const defaultOptions = {
      method: 'GET',
      headers: {
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': 'https://www.fotmob.com/'
      },
      credentials: 'include'
    };
    
    const fetchOptions = { ...defaultOptions, ...options };
    
    // 🔧 修复: 将多个参数封装为单个对象传递
    const timeoutMs = options.timeout || this.defaultTimeoutMs;
    return await Promise.race([
      this.page.evaluate(async ({ apiUrl, opts }) => {
        try {
          const response = await fetch(apiUrl, opts);
          
          if (!response.ok) {
            return { error: `HTTP ${response.status}`, status: response.status };
          }
          
          const contentType = response.headers.get('content-type') || '';
          if (contentType.includes('text/html')) {
            return { error: 'Received HTML instead of JSON', isHtml: true, status: response.status };
          }
          
          const data = await response.json();
          return { success: true, data, status: response.status };
        } catch (e) {
          return { error: e.message };
        }
      }, { apiUrl: url, opts: fetchOptions }),
      new Promise((_, reject) => {
        setTimeout(() => reject(new Error(`Browser fetch timeout after ${timeoutMs}ms`)), timeoutMs);
      })
    ]);
  }

  /**
   * 获取当前页面 URL
   * @returns {Promise<string>}
   */
  async getCurrentUrl() {
    if (!this.page) return '';
    return await this.page.url();
  }

  /**
   * 导航到指定 URL
   * @param {string} url - 目标 URL
   * @param {Object} options - 导航选项
   * @returns {Promise<void>}
   */
  async goto(url, options = {}) {
    if (!this.isInitialized()) {
      await this.initialize();
    }
    
    await this.page.goto(url, {
      waitUntil: options.waitUntil || 'domcontentloaded',
      timeout: options.timeout || 20000
    });
  }

  /**
   * 执行页面滚动
   * @param {Object} options - 滚动选项
   * @returns {Promise<number>} 滚动后的页面高度
   */
  async scroll(options = {}) {
    if (!this.page) return 0;
    
    const scrollTo = options.to || 'bottom';
    
    if (scrollTo === 'bottom') {
      await this.page.evaluate(() => {
        window.scrollTo(0, document.body.scrollHeight);
      });
    } else if (scrollTo === 'top') {
      await this.page.evaluate(() => {
        window.scrollTo(0, 0);
      });
    }
    
    // 返回当前页面高度
    return await this.page.evaluate(() => document.body.scrollHeight);
  }

  /**
   * 获取页面高度
   * @returns {Promise<number>}
   */
  async getPageHeight() {
    if (!this.page) return 0;
    return await this.page.evaluate(() => document.body.scrollHeight);
  }

  /**
   * 等待选择器
   * @param {string} selector - CSS 选择器
   * @param {Object} options - 等待选项
   * @returns {Promise<void>}
   */
  async waitForSelector(selector, options = {}) {
    if (!this.page) return;
    await this.page.waitForSelector(selector, {
      state: options.state || 'attached',
      timeout: options.timeout || 10000
    });
  }

  /**
   * 在页面内执行函数
   * @param {Function} fn - 要执行的函数
   * @param {Array} args - 函数参数
   * @returns {Promise<any>}
   */
  async evaluate(fn, ...args) {
    if (!this.page) return null;
    return await Promise.race([
      this.page.evaluate(fn, ...args),
      new Promise((_, reject) => {
        setTimeout(() => reject(new Error(`Browser evaluate timeout after ${this.defaultTimeoutMs}ms`)), this.defaultTimeoutMs);
      })
    ]);
  }

  /**
   * 等待指定时间
   * @param {number} ms - 毫秒
   * @returns {Promise<void>}
   */
  async sleep(ms) {
    await new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * 关闭浏览器
   * @returns {Promise<void>}
   */
  async close() {
    if (!this.browser) return;

    this.logger.info('[BrowserProvider] 🔒 关闭浏览器...');
    try {
      if (this.page) {
        this.page.removeAllListeners();
      }
      await this.browser.close();
      this.logger.info('[BrowserProvider] ✅ 浏览器已关闭');
    } finally {
      this.browser = null;
      this.page = null;
    }
  }
}

module.exports = { BrowserProvider };
