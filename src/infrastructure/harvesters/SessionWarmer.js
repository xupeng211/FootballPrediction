/**
 * SessionWarmer - V6.0 会话预热引擎
 * ================================
 *
 * 通过模拟人类行为预热浏览器会话，建立合规 Cookie
 * 用于突破 Cloudflare 等反爬防护
 *
 * @module infrastructure/harvesters/SessionWarmer
 * @version V6.0.0-RESIDENTIAL
 * @since 2026-03-15
 */

'use strict';

const { chromium } = require('playwright');
const fs = require('fs').promises;
const path = require('path');
const { ProxyRotator } = require('./ProxyRotator');
const RECON_CONFIG = require('../../../config/recon_config.json');

// 配置
const WARMER_CONFIG = {
  SESSION_DIR: '/app/data/sessions',
  BASE_URL: RECON_CONFIG.oddsportal.base_url,
  WARMUP_STEPS: [
    { url: '/', wait: 2000, action: 'visit_homepage' },
    { url: '/soccer/', wait: 3000, action: 'click_soccer' },
    { url: '/soccer/england/premier-league/', wait: 2000, action: 'visit_league' }
  ],
  VIEWPORT_OPTIONS: [
    { width: 1920, height: 1080 },
    { width: 1366, height: 768 },
    { width: 1536, height: 864 },
    { width: 1440, height: 900 }
  ],
  USER_AGENTS: [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15'
  ]
};

/**
 * SessionWarmer 类
 */
class SessionWarmer {
  /**
   * @param {object} options - 配置选项
   * @param {boolean} options.useResidential - 是否使用住宅代理
   * @param {string} options.sessionName - 会话文件名称
   */
  constructor(options = {}) {
    this.useResidential = options.useResidential || false;
    this.sessionName = options.sessionName || 'oddsportal_session.json';
    this.sessionPath = path.join(WARMER_CONFIG.SESSION_DIR, this.sessionName);
    
    this.proxyRotator = new ProxyRotator({
      strategy: 'residential-priority'
    });
    
    this.browser = null;
    this.context = null;
    this.page = null;
    
    console.log('🔥 SessionWarmer V6.0 初始化完成');
  }

  /**
   * 预热会话
   * @returns {Promise<string>} 会话文件路径
   */
  async warmUp() {
    console.log('\n' + '='.repeat(60));
    console.log('🔥 Session Warmer - 预热引擎启动');
    console.log('='.repeat(60));
    
    try {
      // 确保会话目录存在
      await this._ensureSessionDir();
      
      // 启动浏览器
      await this._launchBrowser();
      
      // 执行预热步骤
      for (const step of WARMER_CONFIG.WARMUP_STEPS) {
        await this._executeStep(step);
      }
      
      // 保存会话状态
      const savedPath = await this._saveSession();
      
      console.log('\n✅ 会话预热完成！');
      console.log(`📁 会话文件: ${savedPath}`);
      
      return savedPath;
      
    } catch (error) {
      console.error('\n❌ 会话预热失败:', error.message);
      throw error;
    } finally {
      await this.close();
    }
  }

  /**
   * 启动浏览器
   * @private
   */
  async _launchBrowser() {
    console.log('\n🚀 启动浏览器...');
    
    // 随机选择 viewport 和 UA
    const viewport = WARMER_CONFIG.VIEWPORT_OPTIONS[
      Math.floor(Math.random() * WARMER_CONFIG.VIEWPORT_OPTIONS.length)
    ];
    const userAgent = WARMER_CONFIG.USER_AGENTS[
      Math.floor(Math.random() * WARMER_CONFIG.USER_AGENTS.length)
    ];
    
    console.log(`   🎭 Viewport: ${viewport.width}x${viewport.height}`);
    console.log(`   🎭 User-Agent: ${userAgent.substring(0, 50)}...`);
    
    // 获取代理配置
    const proxyConfig = this.proxyRotator.getPlaywrightProxy({
      forceResidential: this.useResidential
    });
    
    if (proxyConfig) {
      console.log(`   🔌 代理: ${proxyConfig.server}`);
    }
    
    // 启动浏览器
    this.browser = await chromium.launch({
      headless: true,
      args: [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-dev-shm-usage',
        '--disable-accelerated-2d-canvas',
        '--disable-gpu',
        `--window-size=${viewport.width},${viewport.height}`
      ]
    });
    
    // 创建上下文
    const contextOptions = {
      viewport,
      userAgent,
      locale: 'en-US',
      timezoneId: 'America/New_York'
    };
    
    if (proxyConfig) {
      contextOptions.proxy = proxyConfig;
    }
    
    this.context = await this.browser.newContext(contextOptions);
    
    // 注入脚本隐藏 webdriver
    await this.context.addInitScript(() => {
      Object.defineProperty(navigator, 'webdriver', {
        get: () => undefined
      });
      
      // 添加 chrome 对象
      if (!window.chrome) {
        window.chrome = {
          runtime: {}
        };
      }
    });
    
    this.page = await this.context.newPage();
    
    console.log('✅ 浏览器启动完成');
  }

  /**
   * 执行预热步骤
   * @private
   * @param {object} step - 步骤配置
   */
  async _executeStep(step) {
    const url = WARMER_CONFIG.BASE_URL + step.url;
    
    console.log(`\n📍 步骤: ${step.action}`);
    console.log(`   🔗 URL: ${url}`);
    
    try {
      // 导航到页面
      await this.page.goto(url, {
        waitUntil: 'domcontentloaded',
        timeout: 30000
      });
      
      // 等待页面加载
      await this.page.waitForTimeout(step.wait);
      
      // 模拟人类滚动行为
      await this._humanLikeScroll();
      
      // 检查页面标题
      const title = await this.page.title();
      console.log(`   📄 Title: ${title || 'N/A'}`);
      
      // 检查是否被拦截
      if (title.includes('Just a moment') || title.includes('Cloudflare')) {
        console.log('   ⚠️  检测到 Cloudflare 拦截');
        throw new Error('CLOUDFLARE_BLOCKED');
      }
      
      // 获取 cookies
      const cookies = await this.context.cookies();
      console.log(`   🍪 Cookies: ${cookies.length} 个`);
      
      console.log(`   ✅ 步骤完成`);
      
    } catch (error) {
      console.log(`   ❌ 步骤失败: ${error.message}`);
      throw error;
    }
  }

  /**
   * 模拟人类滚动
   * @private
   */
  async _humanLikeScroll() {
    try {
      // 随机向下滚动
      const scrollAmount = 100 + Math.floor(Math.random() * 300);
      await this.page.evaluate((amount) => {
        window.scrollBy(0, amount);
      }, scrollAmount);
      
      // 等待一下
      await this.page.waitForTimeout(500 + Math.floor(Math.random() * 1000));
      
      // 有时向上滚动一点
      if (Math.random() > 0.5) {
        const scrollUp = 50 + Math.floor(Math.random() * 100);
        await this.page.evaluate((amount) => {
          window.scrollBy(0, -amount);
        }, scrollUp);
        
        await this.page.waitForTimeout(300 + Math.floor(Math.random() * 500));
      }
    } catch (e) {
      // 滚动失败不中断流程
    }
  }

  /**
   * 保存会话状态
   * @private
   * @returns {Promise<string>} 文件路径
   */
  async _saveSession() {
    console.log('\n💾 保存会话状态...');
    
    const storageState = await this.context.storageState();
    
    // 添加元数据
    const sessionData = {
      ...storageState,
      _metadata: {
        createdAt: new Date().toISOString(),
        version: 'V6.0',
        warmed: true,
        steps: WARMER_CONFIG.WARMUP_STEPS.length
      }
    };
    
    await fs.writeFile(
      this.sessionPath,
      JSON.stringify(sessionData, null, 2)
    );
    
    console.log(`   ✅ 会话已保存: ${this.sessionPath}`);
    
    return this.sessionPath;
  }

  /**
   * 确保会话目录存在
   * @private
   */
  async _ensureSessionDir() {
    try {
      await fs.mkdir(WARMER_CONFIG.SESSION_DIR, { recursive: true });
    } catch (e) {
      // 目录已存在
    }
  }

  /**
   * 加载现有会话
   * @returns {Promise<object|null>} 会话数据
   */
  async loadSession() {
    try {
      const data = await fs.readFile(this.sessionPath, 'utf-8');
      const session = JSON.parse(data);
      
      console.log('📁 加载现有会话:');
      console.log(`   创建时间: ${session._metadata?.createdAt || 'N/A'}`);
      console.log(`   Cookies: ${session.cookies?.length || 0} 个`);
      
      return session;
    } catch (e) {
      return null;
    }
  }

  /**
   * 检查会话是否有效
   * @returns {Promise<boolean>}
   */
  async isSessionValid() {
    const session = await this.loadSession();
    if (!session) return false;
    
    // 检查会话年龄（超过24小时认为过期）
    if (session._metadata?.createdAt) {
      const created = new Date(session._metadata.createdAt);
      const age = Date.now() - created.getTime();
      const maxAge = 24 * 60 * 60 * 1000; // 24小时
      
      if (age > maxAge) {
        console.log('⚠️  会话已过期（超过24小时）');
        return false;
      }
    }
    
    // 检查是否有 cookies
    if (!session.cookies || session.cookies.length === 0) {
      return false;
    }
    
    return true;
  }

  /**
   * 关闭浏览器
   */
  async close() {
    if (this.browser) {
      await this.browser.close();
      this.browser = null;
      this.context = null;
      this.page = null;
      console.log('\n🔒 浏览器已关闭');
    }
  }
}

module.exports = { SessionWarmer, WARMER_CONFIG };
