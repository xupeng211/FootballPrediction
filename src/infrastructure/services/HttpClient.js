/**
 * @file HttpClient - HTTP 通信客户端 (Principal 精修版)
 * @module infrastructure/services/HttpClient
 * @version V6.7.6-PRINCIPAL
 * @description
 * 职责: 封装所有对外 HTTP 通讯
 * 支持: 影子浏览器 fetch 和原生 HTTPS 请求双模式
 * 包含: 重试机制、重定向检测、错误处理 (快速失败原则)
 */

'use strict';

const https = require('https');
const { URL } = require('url');

/**
 * HTTP 客户端错误类
 * @class HttpClientError
 */
class HttpClientError extends Error {
  constructor(message, context = {}) {
    super(message);
    this.name = 'HttpClientError';
    this.url = context.url;
    this.mode = context.mode;
    this.statusCode = context.statusCode;
    this.retryCount = context.retryCount;
    this.timestamp = new Date().toISOString();
  }
}

/**
 * HTTP 客户端
 * @class HttpClient
 */
class HttpClient {
  /**
   * 创建 HTTP 客户端
   * @param {Object} options - 配置选项
   */
  constructor(options = {}) {
    this.logger = options.logger || { info: () => {}, warn: () => {}, error: () => {} };
    this.browserProvider = options.browserProvider;
    this.useStealthMode = options.useStealthMode !== false;
    this.requestTimeoutMs = options.requestTimeoutMs || 20000;
    this.baseBackoffMs = options.baseBackoffMs || 1000;
  }

  /**
   * 执行 API 请求 (Principal 精修: 快速失败原则)
   * V6.7.6-PRINCIPAL: 严禁静默失败，所有错误必须抛出
   * @param {string} url - 请求 URL
   * @returns {Promise<Object>} 响应数据
   * @throws {HttpClientError} 请求失败时抛出
   */
  async request(url) {
    // 添加地区伪装参数
    const urlWithCC = this._addCcodeParam(url);
    this.logger.info(`[HttpClient] 请求: ${urlWithCC}`);

    let lastError = null;
    let attemptCount = 0;
    const maxAttempts = 2; // 原始请求 + 1次纯净URL重试

    while (attemptCount < maxAttempts) {
      try {
        const response = this.useStealthMode
          ? await this._stealthRequest(urlWithCC)
          : await this._rawRequest(urlWithCC);

        // 验证响应有效性
        if (!response || typeof response !== 'object') {
          throw new HttpClientError('响应格式无效', {
            url: urlWithCC,
            mode: this.useStealthMode ? 'stealth' : 'raw',
            retryCount: attemptCount
          });
        }

        return response;

      } catch (error) {
        lastError = error;
        attemptCount++;

        // 如果是第一次失败且包含参数，尝试纯净URL
        if (attemptCount === 1 && url.includes('?') && url.includes('id=')) {
          const cleanUrl = this._getCleanUrl(url);
          if (cleanUrl !== url) {
            this.logger.warn(`[HttpClient] 带参数请求失败，尝试纯净 URL: ${cleanUrl}`);
            url = cleanUrl;
            continue;
          }
        }

        break; // 重试耗尽，抛出错误
      }
    }

    // Principal 标准: 快速失败，抛出增强错误
    const enhancedError = new HttpClientError(
      `请求失败: ${lastError.message}`,
      {
        url: urlWithCC,
        mode: this.useStealthMode ? 'stealth' : 'raw',
        retryCount: attemptCount,
        originalError: lastError.message
      }
    );

    this.logger.error(`[HttpClient] ❌ ${enhancedError.message}`);
    throw enhancedError;
  }

  /**
   * 添加地区伪装参数
   * @private
   */
  _addCcodeParam(url) {
    if (url.includes('/search/suggest')) return url;
    const separator = url.includes('?') ? '&' : '?';
    return `${url}${separator}ccode3=USA`;
  }

  /**
   * 获取纯净URL (仅保留id参数)
   * @private
   */
  _getCleanUrl(url) {
    const baseUrl = url.split('?')[0];
    const idMatch = url.match(/[?&]id=(\d+)/);
    return idMatch ? `${baseUrl}?id=${idMatch[1]}` : url;
  }

  /**
   * 影子浏览器模式请求 (Principal 精修: 错误传播)
   * @private
   */
  async _stealthRequest(url) {
    let retryCount = 0;
    const maxRetries = 3;

    while (retryCount < maxRetries) {
      try {
        this.logger.info(`[HttpClient] 🕵️  浏览器内 fetch: ${url} (尝试 ${retryCount + 1}/${maxRetries})`);

        const result = await this.browserProvider.fetch(url, { timeout: this.requestTimeoutMs });

        // 检查浏览器返回结果
        if (result.error) {
          const retryable = this._isRetryableStatus(result.status);
          const error = new HttpClientError(`浏览器返回错误: ${result.error}`, {
            url,
            mode: 'stealth',
            statusCode: result.status,
            retryCount
          });
          error.retryable = retryable;
          throw error;
        }

        if (!result.data || Object.keys(result.data).length === 0) {
          throw new Error('浏览器返回空数据');
        }

        this.logger.info(`[HttpClient] ✅ 浏览器请求成功`);

        // 重定向检测 (非阻塞)
        await this._detectRedirect(url);

        return result.data;

      } catch (error) {
        retryCount++;
        this.logger.warn(`[HttpClient] 尝试 ${retryCount} 失败: ${error.message}`);

        if (retryCount >= maxRetries) {
          throw new HttpClientError(`浏览器模式请求失败: ${error.message}`, {
            url,
            mode: 'stealth',
            retryCount
          });
        }

        const backoffMs = this._computeBackoffMs(retryCount, error.statusCode);
        this.logger.warn(`[HttpClient] ${backoffMs}ms 后重试...`);

        // 刷新页面重试
        await this._sleep(backoffMs);
        try {
          await this.browserProvider.goto('https://www.fotmob.com/', {
            waitUntil: 'domcontentloaded',
            timeout: 15000
          });
        } catch (refreshErr) {
          this.logger.warn(`[HttpClient] 刷新页面警告: ${refreshErr.message}`);
        }
      }
    }

    throw new HttpClientError('浏览器模式重试耗尽', { url, mode: 'stealth', retryCount });
  }

  /**
   * 原生 HTTP 请求 (Principal 精修: 错误传播)
   * @private
   */
  async _rawRequest(url) {
    this.logger.info(`[HttpClient] 原生HTTP模式: ${url}`);

    return new Promise((resolve, reject) => {
      const options = new URL(url);
      const req = https.request({
        hostname: options.hostname,
        path: options.pathname + options.search,
        method: 'GET',
        headers: {
          'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
          'Accept': 'application/json, text/plain, */*',
          'Accept-Language': 'en-US,en;q=0.9',
          'Referer': 'https://www.fotmob.com/',
          'Origin': 'https://www.fotmob.com'
        },
        timeout: 20000
      }, (res) => {
        let data = '';
        res.on('data', chunk => data += chunk);
        res.on('end', () => {
          if (res.statusCode < 200 || res.statusCode >= 300) {
            return reject(new HttpClientError(`HTTP ${res.statusCode}`, {
              url,
              mode: 'raw',
              statusCode: res.statusCode
            }));
          }

          try {
            const parsed = JSON.parse(data);
            resolve(parsed);
          } catch (e) {
            reject(new HttpClientError(`JSON 解析失败: ${e.message}`, { url, mode: 'raw' }));
          }
        });
      });

      req.on('error', (e) => {
        reject(new HttpClientError(`请求失败: ${e.message}`, { url, mode: 'raw' }));
      });

      req.on('timeout', () => {
        req.destroy();
        reject(new HttpClientError('请求超时', { url, mode: 'raw' }));
      });

      req.end();
    });
  }

  /**
   * 检测 ID 偏移重定向
   * @private
   */
  async _detectRedirect(url) {
    try {
      const currentUrl = await this.browserProvider.getCurrentUrl();
      const requestedId = url.match(/[?&]id=(\d+)/)?.[1];
      const currentId = currentUrl.match(/\/leagues\/(\d+)/)?.[1];

      if (requestedId && currentId && requestedId !== currentId) {
        this.logger.error(`[HttpClient] 🚨 ID 偏移重定向: ${requestedId} -> ${currentId}`);
      }
    } catch (e) {
      // 忽略重定向检测错误
    }
  }

  /**
   * 延迟工具
   * @private
   */
  _sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  _isRetryableStatus(statusCode) {
    return statusCode === 403 || statusCode === 429 || (statusCode >= 500 && statusCode < 600);
  }

  _computeBackoffMs(retryCount, statusCode = null) {
    const multiplier = statusCode === 429 ? 2 : 1;
    return this.baseBackoffMs * (2 ** (retryCount - 1)) * multiplier;
  }
}

module.exports = { HttpClient, HttpClientError };
