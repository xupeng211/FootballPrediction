'use strict';

/**
 * FotMob API 纯 HTTP 客户端。
 * 约束: 这里只接收由 ProxyProvider 分配出来的代理 server/lease，不自行发现或绕过代理层。
 */
const http = require('node:http');
const https = require('node:https');
const { randomInt } = require('node:crypto');
const { URL } = require('node:url');
const { HttpProxyAgent } = require('http-proxy-agent');
const { HttpsProxyAgent } = require('https-proxy-agent');
const { SocksProxyAgent } = require('socks-proxy-agent');

const DEFAULT_BASE_URL = 'https://www.fotmob.com';
const DEFAULT_REQUEST_TIMEOUT_MS = 20000;
const DEFAULT_JITTER_MIN_MS = 1500;
const DEFAULT_JITTER_MAX_MS = 4000;
const DEFAULT_USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36';

function createProxyAgent(proxyServer, targetProtocol, timeoutMs) {
  if (!proxyServer) {
    return undefined;
  }

  const normalizedProxyUrl = String(proxyServer);
  if (/^socks5h?:\/\//i.test(normalizedProxyUrl)) {
    return new SocksProxyAgent(normalizedProxyUrl, { timeout: timeoutMs });
  }

  if (targetProtocol === 'https:') {
    return new HttpsProxyAgent(normalizedProxyUrl, { keepAlive: false, timeout: timeoutMs });
  }

  return new HttpProxyAgent(normalizedProxyUrl, { keepAlive: false, timeout: timeoutMs });
}

function buildCookieHeader(cookies = []) {
  return (Array.isArray(cookies) ? cookies : [])
    .map((cookie) => {
      const name = String(cookie?.name || '').trim();
      const value = String(cookie?.value || '').trim();
      if (!name || !value) {
        return null;
      }
      return `${name}=${value}`;
    })
    .filter(Boolean)
    .join('; ');
}

class FotMobApiError extends Error {
  constructor(message, context = {}) {
    super(message);
    this.name = 'FotMobApiError';
    this.code = context.code || null;
    this.statusCode = Number(context.statusCode) || null;
    this.url = context.url || null;
    this.responseBody = context.responseBody || '';
    this.headers = context.headers || {};
    this.fallbackToBrowser = context.fallbackToBrowser === true;
  }
}

class FotMobApiClient {
  constructor(options = {}) {
    this.logger = options.logger || console;
    this.baseUrl = String(options.baseUrl || DEFAULT_BASE_URL);
    this.requestTimeoutMs = Number(options.requestTimeoutMs) || DEFAULT_REQUEST_TIMEOUT_MS;
    this.jitterMinMs = Number(options.jitterMinMs) || DEFAULT_JITTER_MIN_MS;
    this.jitterMaxMs = Number(options.jitterMaxMs) || DEFAULT_JITTER_MAX_MS;
    this.sessionManager = options.sessionManager || null;
  }

  setSessionManager(sessionManager) {
    this.sessionManager = sessionManager || null;
  }

  async fetchMatchDetails(match, options = {}) {
    const externalId = String(match?.external_id || '').trim();
    if (!externalId) {
      throw new FotMobApiError('MISSING_MATCH_ID', { code: 'MISSING_MATCH_ID' });
    }

    const identity = options.identity || null;
    const referer = String(options.referer || `${this.baseUrl}/match/${externalId}`);
    const port = Number(identity?.proxy?.port || options.port || 0);
    const proxyServer = options.proxyServer || identity?.proxy?.server || identity?.proxy?.url || null;
    const session = await this._resolveSession(port, proxyServer, options.session);
    const userAgent = String(
      options.userAgent
      || session?.userAgent
      || identity?.stealth?.userAgent
      || DEFAULT_USER_AGENT
    ).trim();

    await this._applyJitter();

    const url = new URL('/api/data/matchDetails', this.baseUrl);
    url.searchParams.set('matchId', externalId);

    const headers = {
      accept: 'application/json, text/plain, */*',
      'accept-language': 'zh-Hans,zh;q=0.9,en;q=0.8',
      'accept-encoding': 'identity',
      referer,
      'user-agent': userAgent,
      'x-requested-with': 'XMLHttpRequest'
    };

    const cookieHeader = buildCookieHeader(session?.cookies);
    if (cookieHeader) {
      headers.cookie = cookieHeader;
    }

    return this._requestJson(url, {
      headers,
      proxyServer
    });
  }

  async _resolveSession(port, proxyServer, explicitSession) {
    if (explicitSession) {
      return explicitSession;
    }

    if (!this.sessionManager || !Number.isInteger(port) || port <= 0) {
      return null;
    }

    try {
      return await this.sessionManager.getOrRefreshSession(port, { proxyUrl: proxyServer || undefined });
    } catch (error) {
      if (typeof this.logger?.warn === 'function') {
        this.logger.warn(`[FotMobApiClient] 会话获取失败: ${error.message}`);
      }
      return null;
    }
  }

  async _applyJitter() {
    const minMs = Math.max(0, this.jitterMinMs);
    const maxMs = Math.max(minMs, this.jitterMaxMs);
    const delayMs = maxMs > minMs
      ? randomInt(minMs, maxMs + 1)
      : minMs;

    if (delayMs <= 0) {
      return;
    }

    await new Promise((resolve) => {
      setTimeout(resolve, delayMs);
    });
  }

  _requestJson(url, options = {}) {
    const target = url instanceof URL ? url : new URL(String(url));
    const requestLib = target.protocol === 'https:' ? https : http;
    const agent = createProxyAgent(options.proxyServer, target.protocol, this.requestTimeoutMs);

    return new Promise((resolve, reject) => {
      const req = requestLib.request({
        hostname: target.hostname,
        port: target.port || (target.protocol === 'https:' ? 443 : 80),
        path: `${target.pathname}${target.search}`,
        method: 'GET',
        timeout: this.requestTimeoutMs,
        agent,
        headers: options.headers || {}
      }, (res) => {
        let rawBody = '';

        res.setEncoding('utf8');
        res.on('data', (chunk) => {
          rawBody += chunk;
        });
        res.on('end', () => {
          const statusCode = Number(res.statusCode) || 0;
          if (statusCode < 200 || statusCode >= 300) {
            return reject(new FotMobApiError(`HTTP_${statusCode}`, {
              code: 'HTTP_ERROR',
              statusCode,
              url: target.href,
              responseBody: rawBody
            }));
          }

          try {
            const parsed = JSON.parse(rawBody);
            if (!parsed || typeof parsed !== 'object') {
              return reject(new FotMobApiError('INVALID_JSON_PAYLOAD', {
                code: 'INVALID_JSON_PAYLOAD',
                statusCode,
                url: target.href,
                responseBody: rawBody
              }));
            }
            resolve(parsed);
          } catch (error) {
            const isHtmlLike = /^\s*</.test(rawBody);
            reject(new FotMobApiError(isHtmlLike ? 'HTML_CHALLENGE_RESPONSE' : `JSON_PARSE_ERROR:${error.message}`, {
              code: isHtmlLike ? 'HTML_CHALLENGE_RESPONSE' : 'JSON_PARSE_ERROR',
              statusCode,
              url: target.href,
              responseBody: rawBody
            }));
          }
        });
      });

      req.once('timeout', () => {
        req.destroy(new FotMobApiError('REQUEST_TIMEOUT', {
          code: 'REQUEST_TIMEOUT',
          url: target.href
        }));
      });

      req.once('error', (error) => {
        if (error instanceof FotMobApiError) {
          reject(error);
          return;
        }

        reject(new FotMobApiError(error.message || 'REQUEST_FAILED', {
          code: 'REQUEST_FAILED',
          url: target.href
        }));
      });

      req.end();
    });
  }
}

module.exports = {
  FotMobApiClient,
  FotMobApiError,
  buildCookieHeader
};
