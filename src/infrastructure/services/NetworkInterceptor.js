/**
 * @file NetworkInterceptor - 网络请求拦截器
 * @module infrastructure/services/NetworkInterceptor
 * @version V6.7.10-NETWORK
 * @description
 * 职责: 全局请求监听、API 路径截获、噪音过滤
 * 从 DiscoveryService 解耦，支持复用和独立测试
 */

'use strict';

const { URL } = require('url');

/**
 * 网络拦截器
 * @class NetworkInterceptor
 */
class NetworkInterceptor {
  /**
   * 创建网络拦截器
   * @param {Object} options - 配置选项
   * @param {Object} options.logger - 日志对象
   * @param {Function} options.onApiCaptured - API 捕获回调 (url, endpointKey) => void
   * @param {Array<string>} options.noiseDomains - 噪音域名列表
   * @param {Array<string>} options.targetDomains - 目标域名列表
   */
  constructor(options = {}) {
    this.logger = options.logger || {
      info: () => {},
      warn: () => {},
      error: () => {}
    };
    
    this.onApiCaptured = options.onApiCaptured || (() => {});
    
    this.config = {
      noiseDomains: options.noiseDomains || [
        'awsapprunner.com',
        'amazonaws.com',
        'google-analytics.com',
        'googletagmanager.com',
        'doubleclick.net'
      ],
      targetDomains: options.targetDomains || [
        'www.fotmob.com'
      ],
      apiPathPattern: options.apiPathPattern || '/api/data/'
    };
    
    this.capturedApis = new Map();
    this.isSetup = false;
    this.page = null;
    this.boundRequestHandler = null;
    this.boundResponseHandler = null;
  }

  /**
   * 检查 URL 是否为噪音
   * @param {string} url - 请求 URL
   * @returns {boolean}
   */
  isNoise(url) {
    return this.config.noiseDomains.some(domain => url.includes(domain));
  }

  /**
   * 检查 URL 是否为目标 API
   * @param {string} url - 请求 URL
   * @returns {boolean}
   */
  isTargetApi(url) {
    // 检查域名
    const isTargetDomain = this.config.targetDomains.some(domain => url.includes(domain));
    if (!isTargetDomain) return false;
    
    // 检查 API 路径
    return url.includes(this.config.apiPathPattern);
  }

  /**
   * 检查是否为联赛数据 API
   * @param {string} url - 请求 URL
   * @returns {boolean}
   */
  isLeagueApi(url) {
    return this.isTargetApi(url) && 
           (url.includes('leagues') || url.includes('league'));
  }

  /**
   * 提取端点 key
   * @param {string} url - 完整 URL
   * @returns {string|null}
   */
  extractEndpointKey(url) {
    try {
      const urlObj = new URL(url);
      return `${urlObj.pathname}${urlObj.search}`;
    } catch (e) {
      return null;
    }
  }

  /**
   * 设置网络拦截
   * @param {Page} page - Playwright Page 实例
   * @returns {void}
   */
  setup(page) {
    if (!page || this.isSetup) return;
    
    this.logger.info('[NetworkInterceptor] 📡 网络监听已启动');
    this.page = page;
    this.boundRequestHandler = (request) => {
      this.handleRequest(request);
    };
    this.boundResponseHandler = async (response) => {
      await this.handleResponse(response);
    };
    
    // 监听所有请求
    page.on('request', this.boundRequestHandler);
    
    // 监听响应
    page.on('response', this.boundResponseHandler);
    
    this.isSetup = true;
  }

  /**
   * 处理请求
   * @param {Request} request - Playwright Request 对象
   */
  handleRequest(request) {
    const url = request.url();
    
    // 过滤噪音
    if (this.isNoise(url)) return;
    
    // 只关注目标 API 请求
    if (this.isTargetApi(url)) {
      this.logger.info(`[NetworkInterceptor] 📡 拦截请求: ${url.substring(0, 100)}...`);
    }
  }

  /**
   * 处理响应
   * @param {Response} response - Playwright Response 对象
   */
  async handleResponse(response) {
    const url = response.url();
    
    // 过滤非目标域名
    if (!this.config.targetDomains.some(domain => url.includes(domain))) return;
    
    // 过滤非 API 路径
    if (!url.includes(this.config.apiPathPattern)) return;
    
    // 过滤非成功响应
    if (response.status() !== 200) return;
    
    // 过滤噪音
    if (this.isNoise(url)) return;
    
    try {
      const contentType = response.headers()['content-type'] || '';
      if (contentType.includes('application/json')) {
        this.logger.info(`[NetworkInterceptor] ✅ 发现真实 API: ${url}`);
        
        // 存储这个端点
        const endpointKey = this.extractEndpointKey(url);
        if (endpointKey && !this.capturedApis.has(endpointKey)) {
          const apiInfo = {
            url: url,
            timestamp: new Date().toISOString()
          };
          
          this.capturedApis.set(endpointKey, apiInfo);
          
          // 触发回调
          this.onApiCaptured(url, endpointKey);
          
          // 如果是联赛数据 API，额外标记
          if (this.isLeagueApi(url)) {
            this.logger.info(`[NetworkInterceptor] 🎯 关键端点捕获: ${url}`);
          }
        }
      }
    } catch (e) {
      // 忽略解析错误
    }
  }

  /**
   * 获取所有捕获的 API
   * @returns {Map<string, Object>}
   */
  getCapturedApis() {
    return this.capturedApis;
  }

  /**
   * 获取特定端点信息
   * @param {string} endpointKey - 端点 key
   * @returns {Object|undefined}
   */
  getCapturedApi(endpointKey) {
    return this.capturedApis.get(endpointKey);
  }

  /**
   * 检查是否已捕获特定端点
   * @param {string} endpointKey - 端点 key
   * @returns {boolean}
   */
  hasCapturedApi(endpointKey) {
    return this.capturedApis.has(endpointKey);
  }

  /**
   * 获取第一个联赛 API
   * @returns {string|null}
   */
  getFirstLeagueApi() {
    for (const [key, info] of this.capturedApis) {
      if (this.isLeagueApi(info.url)) {
        return info.url;
      }
    }
    return null;
  }

  /**
   * 清空捕获记录
   */
  clear() {
    this.capturedApis.clear();
  }

  /**
   * 重置拦截器状态
   */
  reset() {
    if (this.page && this.boundRequestHandler) {
      this.page.off('request', this.boundRequestHandler);
    }
    if (this.page && this.boundResponseHandler) {
      this.page.off('response', this.boundResponseHandler);
    }
    this.clear();
    this.isSetup = false;
    this.page = null;
    this.boundRequestHandler = null;
    this.boundResponseHandler = null;
  }
}

module.exports = { NetworkInterceptor };
