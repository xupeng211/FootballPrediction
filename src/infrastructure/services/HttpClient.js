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

const http = require('http');
const https = require('https');
const { URL } = require('url');
const { HttpProxyAgent } = require('http-proxy-agent');
const { HttpsProxyAgent } = require('https-proxy-agent');

function extractStatusCode(reason = '') {
  const message = String(reason || '');
  const match = message.match(/\b(4\d{2}|5\d{2})\b/);
  return match ? Number(match[1]) : null;
}

function includesAny(message, patterns) {
  return patterns.some(pattern => message.includes(pattern));
}

function buildStealthFailure({
  failureClass,
  rotateProxy = false,
  rebuildBrowserContext = false,
  recoverPage = false
}) {
  return {
    failureClass,
    rotateProxy,
    rebuildBrowserContext,
    recoverPage
  };
}

function resolveStealthStatusFailure(statusCode) {
  if (statusCode === 429) {
    return buildStealthFailure({
      failureClass: 'rate_limit',
      rotateProxy: true
    });
  }

  if (statusCode === 403) {
    return buildStealthFailure({
      failureClass: 'proxy_blocked',
      rotateProxy: true
    });
  }

  if (statusCode >= 500) {
    return buildStealthFailure({
      failureClass: 'upstream_block'
    });
  }

  return null;
}

function classifyStealthFailure(error) {
  const message = String(error?.message || '').toLowerCase();
  const statusCode = Number(error?.statusCode) || extractStatusCode(error?.message);
  const statusFailure = resolveStealthStatusFailure(statusCode);

  if (statusFailure) {
    return statusFailure;
  }

  if (includesAny(message, ['err_empty_response', 'empty_response'])) {
    return buildStealthFailure({
      failureClass: 'upstream_block',
      recoverPage: true
    });
  }

  if (message.includes('failed to fetch')) {
    return buildStealthFailure({
      failureClass: 'upstream_block',
      recoverPage: true
    });
  }

  if (includesAny(message, [
    'execution context was destroyed',
    'target closed',
    'target page',
    'page crashed'
  ])) {
    return buildStealthFailure({
      failureClass: 'browser_context_transient',
      recoverPage: true
    });
  }

  if (includesAny(message, [
    '浏览器返回空数据',
    'received html instead of json',
    'browser fetch timeout',
    'browser has been closed'
  ])) {
    return buildStealthFailure({
      failureClass: 'browser_context_transient',
      rebuildBrowserContext: true
    });
  }

  return buildStealthFailure({
    failureClass: 'proxy_transport'
  });
}

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
    this.code = context.code || null;
    this.expectedLeagueId = context.expectedLeagueId;
    this.actualLeagueId = context.actualLeagueId;
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
    this.ensureBrowserHealthy = options.ensureBrowserHealthy || null;
    this.proxyProvider = options.proxyProvider || null;
    this.proxyConsumer = options.proxyConsumer || 'l1-discovery-http';
    this.proxySessionKey = options.proxySessionKey || 'raw-http';
    this.rawProxyLease = null;
    this.stealthRequestTail = Promise.resolve();
  }

  /**
   * 执行 API 请求 (Principal 精修: 快速失败原则)
   * V6.7.6-PRINCIPAL: 严禁静默失败，所有错误必须抛出
   * @param {string} url - 请求 URL
   * @returns {Promise<Object>} 响应数据
   * @throws {HttpClientError} 请求失败时抛出
   */
  async request(url, options = {}) {
    const expectedLeagueId = Number.isFinite(Number(options.expectedLeagueId))
      ? Number(options.expectedLeagueId)
      : null;

    // 添加地区伪装参数
    let requestUrl = this._addCcodeParam(url);
    this.logger.info(`[HttpClient] 请求: ${requestUrl}`);

    let lastError = null;
    let attemptCount = 0;
    const maxAttempts = 2; // 原始请求 + 1次纯净URL重试

    while (attemptCount < maxAttempts) {
      try {
        const response = this.useStealthMode
          ? await this._stealthRequest(requestUrl)
          : await this._rawRequest(requestUrl);

        // 验证响应有效性
        if (!response || typeof response !== 'object') {
          throw new HttpClientError('响应格式无效', {
            url: requestUrl,
            mode: this.useStealthMode ? 'stealth' : 'raw',
            retryCount: attemptCount
          });
        }

        this._assertLeagueIdentity(response, expectedLeagueId, requestUrl);
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
            requestUrl = this._addCcodeParam(url);
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
        url: requestUrl,
        mode: this.useStealthMode ? 'stealth' : 'raw',
        statusCode: lastError.statusCode,
        retryCount: attemptCount,
        originalError: lastError.message,
        code: lastError.code,
        expectedLeagueId: lastError.expectedLeagueId,
        actualLeagueId: lastError.actualLeagueId
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
    if (/[?&]ccode3=/.test(url)) return url;
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
    return this._runSerializedStealthRequest(() => this._stealthRequestInternal(url));
  }

  async _stealthRequestInternal(url) {
    let retryCount = 0;
    const maxRetries = 3;

    if (typeof this.ensureBrowserHealthy === 'function') {
      await this.ensureBrowserHealthy({ reason: 'preflight' });
    }

    while (retryCount < maxRetries) {
      try {
        this.logger.info(`[HttpClient] 🕵️  浏览器内 fetch: ${url} (尝试 ${retryCount + 1}/${maxRetries})`);
        const startedAt = Date.now();

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

        await this._reportProxySuccess({
          latencyMs: Date.now() - startedAt,
          statusCode: result.status || 200
        });
        this.logger.info(`[HttpClient] ✅ 浏览器请求成功`);

        // 重定向检测 (非阻塞)
        await this._detectRedirect(url);

        return result.data;

      } catch (error) {
        retryCount++;
        await this._handleStealthFailure(url, error, retryCount, maxRetries);
      }
    }

    throw new HttpClientError('浏览器模式重试耗尽', { url, mode: 'stealth', retryCount });
  }

  async _handleStealthFailure(url, error, retryCount, maxRetries) {
    const failureMetadata = {
      statusCode: error.statusCode || extractStatusCode(error.message),
      reason: error.message,
      ...classifyStealthFailure(error)
    };
    await this._reportProxyFailure(failureMetadata);
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
    await this._sleep(backoffMs);

    const shouldRotateSoftBlockedProxy = failureMetadata.recoverPage === true
      && retryCount >= 2
      && typeof this.ensureBrowserHealthy === 'function';

    if (shouldRotateSoftBlockedProxy) {
      await this.ensureBrowserHealthy({
        reason: error.message,
        forceRebuild: true
      });
      return;
    }

    if (failureMetadata.recoverPage === true && typeof this.ensureBrowserHealthy === 'function') {
      await this.ensureBrowserHealthy({
        reason: error.message,
        recoverPage: true
      });
      return;
    }

    if (
      (failureMetadata.rebuildBrowserContext === true || this._shouldRebuildBrowserContext(error))
      && typeof this.ensureBrowserHealthy === 'function'
    ) {
      await this.ensureBrowserHealthy({
        reason: error.message,
        forceRebuild: true
      });
      return;
    }

    try {
      await this.browserProvider.goto('https://www.fotmob.com/', {
        waitUntil: 'domcontentloaded',
        timeout: 15000
      });
    } catch (refreshErr) {
      this.logger.warn(`[HttpClient] 刷新页面警告: ${refreshErr.message}`);
    }
  }

  /**
   * 原生 HTTP 请求 (Principal 精修: 错误传播)
   * @private
   */
  async _rawRequest(url) {
    this.logger.info(`[HttpClient] 原生HTTP模式: ${url}`);

    return new Promise((resolve, reject) => {
      const requestUrl = new URL(url);
      const requestLib = requestUrl.protocol === 'https:' ? https : http;
      const startedAt = Date.now();

      const finalizeProxyFailure = (reason, statusCode = null) => {
        void this._reportProxyFailure({
          reason,
          statusCode,
          rotateProxy: Boolean(statusCode === 429 || statusCode >= 500)
        });
      };

      const finalizeProxySuccess = (statusCode = 200) => {
        void this._reportProxySuccess({
          statusCode,
          latencyMs: Date.now() - startedAt
        });
      };

      const buildRequest = async () => {
        const proxyLease = await this._ensureRawProxyLease('raw-request');
        return {
          hostname: requestUrl.hostname,
          port: requestUrl.port || (requestUrl.protocol === 'https:' ? 443 : 80),
          path: requestUrl.pathname + requestUrl.search,
          protocol: requestUrl.protocol,
          agent: proxyLease
            ? (requestUrl.protocol === 'https:'
              ? new HttpsProxyAgent(proxyLease.proxy.server)
              : new HttpProxyAgent(proxyLease.proxy.server))
            : undefined
        };
      };

      void buildRequest().then((requestConfig) => {
        const req = requestLib.request({
          hostname: requestConfig.hostname,
          port: requestConfig.port,
          path: requestConfig.path,
          protocol: requestConfig.protocol,
          agent: requestConfig.agent,
          method: 'GET',
          headers: {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.fotmob.com/',
            'Origin': 'https://www.fotmob.com'
          },
          timeout: this.requestTimeoutMs
        }, (res) => {
          let data = '';
          res.on('data', chunk => data += chunk);
          res.on('end', () => {
            if (res.statusCode < 200 || res.statusCode >= 300) {
              finalizeProxyFailure(`HTTP ${res.statusCode}`, res.statusCode);
              return reject(new HttpClientError(`HTTP ${res.statusCode}`, {
                url,
                mode: 'raw',
                statusCode: res.statusCode
              }));
            }

            try {
              const parsed = JSON.parse(data);
              finalizeProxySuccess(res.statusCode);
              resolve(parsed);
            } catch (e) {
              reject(new HttpClientError(`JSON 解析失败: ${e.message}`, { url, mode: 'raw' }));
            }
          });
        });

        req.on('error', (e) => {
          finalizeProxyFailure(`请求失败: ${e.message}`);
          reject(new HttpClientError(`请求失败: ${e.message}`, { url, mode: 'raw' }));
        });

        req.on('timeout', () => {
          req.destroy();
          finalizeProxyFailure('请求超时');
          reject(new HttpClientError('请求超时', { url, mode: 'raw' }));
        });

        req.end();
      }).catch(reject);
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

  _assertLeagueIdentity(response, expectedLeagueId, url) {
    if (!expectedLeagueId) {
      return;
    }

    const actualLeagueId = this._extractLeagueId(response);
    if (!actualLeagueId) {
      return;
    }

    if (actualLeagueId !== expectedLeagueId) {
      throw new HttpClientError(
        `IDENTITY_MISMATCH: 请求联赛 ${expectedLeagueId}，响应联赛 ${actualLeagueId}`,
        {
          url,
          mode: this.useStealthMode ? 'stealth' : 'raw',
          code: 'IDENTITY_MISMATCH',
          expectedLeagueId,
          actualLeagueId
        }
      );
    }
  }

  _extractLeagueId(response) {
    const detailsId = response?.details?.id;
    if (Number.isFinite(Number(detailsId))) {
      return Number(detailsId);
    }

    const fallbackId = response?.id ?? response?.leagueId ?? response?.general?.leagueId;
    return Number.isFinite(Number(fallbackId)) ? Number(fallbackId) : null;
  }

  _shouldRebuildBrowserContext(error) {
    if (!error) {
      return false;
    }

    if (error.code === 'IDENTITY_MISMATCH') {
      return false;
    }

    const message = String(error.message || '').toLowerCase();
    return message.includes('浏览器返回空数据')
      || message.includes('received html instead of json')
      || message.includes('browser fetch timeout')
      || message.includes('browser has been closed');
  }

  /**
   * 延迟工具
   * @private
   */
  _sleep(ms) {
    return new Promise(resolve => {
      setTimeout(resolve, ms);
    });
  }

  _isRetryableStatus(statusCode) {
    return statusCode === 403 || statusCode === 429 || (statusCode >= 500 && statusCode < 600);
  }

  _computeBackoffMs(retryCount, statusCode = null) {
    const multiplier = statusCode === 429 ? 2 : 1;
    return this.baseBackoffMs * (2 ** (retryCount - 1)) * multiplier;
  }

  async close() {
    await this._releaseRawProxyLease();
  }

  async _ensureRawProxyLease(reason = 'raw-http') {
    if (!this.proxyProvider) {
      return null;
    }

    if (this.rawProxyLease) {
      return this.rawProxyLease;
    }

    this.rawProxyLease = await this.proxyProvider.acquire({
      consumer: this.proxyConsumer,
      sessionKey: this.proxySessionKey,
      sticky: true,
      metadata: { reason }
    });

    return this.rawProxyLease;
  }

  async _releaseRawProxyLease() {
    if (!this.proxyProvider || !this.rawProxyLease) {
      return;
    }

    const lease = this.rawProxyLease;
    this.rawProxyLease = null;
    await this.proxyProvider.release(lease.id);
  }

  async _reportProxySuccess(metadata = {}) {
    if (this.useStealthMode && this.browserProvider?.reportProxySuccess) {
      await this.browserProvider.reportProxySuccess(metadata);
      return;
    }

    if (!this.proxyProvider) {
      return;
    }

    const lease = await this._ensureRawProxyLease('raw-report-success');
    if (lease) {
      await this.proxyProvider.reportSuccess(lease.id, metadata);
    }
  }

  async _reportProxyFailure(metadata = {}) {
    if (this.useStealthMode && this.browserProvider?.reportProxyFailure) {
      await this.browserProvider.reportProxyFailure(metadata);
      if (metadata.rotateProxy && this.ensureBrowserHealthy) {
        await this.ensureBrowserHealthy({
          forceRebuild: true,
          reason: metadata.reason || 'proxy_failure'
        });
      }
      return;
    }

    if (!this.proxyProvider) {
      return;
    }

    const lease = await this._ensureRawProxyLease('raw-report-failure');
    if (!lease) {
      return;
    }

    await this.proxyProvider.reportFailure(lease.id, metadata);

    if (metadata.rotateProxy) {
      await this._releaseRawProxyLease();
    }
  }

  async _runSerializedStealthRequest(task) {
    const previousRequest = this.stealthRequestTail;
    let releaseCurrent = null;
    this.stealthRequestTail = new Promise(resolve => {
      releaseCurrent = resolve;
    });

    await previousRequest.catch(() => {});

    try {
      return await task();
    } finally {
      releaseCurrent();
    }
  }
}

module.exports = { HttpClient, HttpClientError };
