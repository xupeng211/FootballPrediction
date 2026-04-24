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
const { BrowserProvider } = require('../services/BrowserProvider');

const DEFAULT_BASE_URL = 'https://www.fotmob.com';
const DEFAULT_REQUEST_TIMEOUT_MS = 20000;
const DEFAULT_JITTER_MIN_MS = 1500;
const DEFAULT_JITTER_MAX_MS = 4000;
const DEFAULT_USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36';
const DEFAULT_BOOTSTRAP_SESSION_TTL_MS = 6 * 60 * 60 * 1000;
const DEFAULT_BROWSER_BOOTSTRAP_TIMEOUT_MS = 30000;
const DEFAULT_BROWSER_BOOTSTRAP_POLL_INTERVAL_MS = 1000;
const CRITICAL_BOOTSTRAP_COOKIE_NAMES = new Set(['cf_clearance', '__cf_bm', '_cfuvid']);

function resolveCookieExpiry(rawExpires) {
  const expires = Number(rawExpires);
  if (!Number.isFinite(expires) || expires <= 0) {
    return { expires: null, expired: false };
  }

  return {
    expires,
    expired: expires < (Date.now() / 1000)
  };
}

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

function normalizeCookieDomain(hostname = '') {
  const normalizedHost = String(hostname || '').trim().replace(/^www\./i, '');
  if (!normalizedHost) {
    return '.fotmob.com';
  }
  return normalizedHost.startsWith('.')
    ? normalizedHost
    : `.${normalizedHost}`;
}

const COOKIE_ATTRIBUTE_HANDLERS = {
  domain(cookie, value) {
    if (value) {
      cookie.domain = value.startsWith('.') ? value : `.${value}`;
    }
  },
  path(cookie, value) {
    if (value) {
      cookie.path = value;
    }
  },
  samesite(cookie, value) {
    if (value) {
      cookie.sameSite = value;
    }
  },
  secure(cookie) {
    cookie.secure = true;
  },
  httponly(cookie) {
    cookie.httpOnly = true;
  }
};

function applyCookieAttribute(cookie, attribute) {
  const [rawKey, ...valueParts] = attribute.split('=');
  const key = String(rawKey || '').trim().toLowerCase();
  const value = valueParts.join('=').trim();
  if (key === 'expires') {
    const timestamp = Date.parse(value);
    if (Number.isFinite(timestamp)) {
      cookie.expires = Math.floor(timestamp / 1000);
    }
    return;
  }

  if (key === 'max-age') {
    const seconds = Number.parseInt(value, 10);
    if (Number.isInteger(seconds) && seconds > 0) {
      cookie.expires = Math.floor((Date.now() + (seconds * 1000)) / 1000);
    }
    return;
  }

  COOKIE_ATTRIBUTE_HANDLERS[key]?.(cookie, value);
}

function parseSetCookieHeader(rawCookie, defaultDomain) {
  const parts = String(rawCookie || '')
    .split(';')
    .map((part) => part.trim())
    .filter(Boolean);

  if (parts.length === 0) {
    return null;
  }

  const separatorIndex = parts[0].indexOf('=');
  if (separatorIndex <= 0) {
    return null;
  }

  const cookie = {
    name: parts[0].slice(0, separatorIndex).trim(),
    value: parts[0].slice(separatorIndex + 1).trim(),
    domain: defaultDomain,
    path: '/',
    httpOnly: false,
    secure: false
  };

  if (!cookie.name || !cookie.value) {
    return null;
  }

  for (const attribute of parts.slice(1)) {
    applyCookieAttribute(cookie, attribute);
  }

  return cookie;
}

function mergeCookies(...collections) {
  const merged = new Map();

  for (const collection of collections) {
    for (const cookie of Array.isArray(collection) ? collection : []) {
      const name = String(cookie?.name || '').trim();
      const value = String(cookie?.value || '').trim();
      if (!name || !value) {
        continue;
      }

      const domain = String(cookie?.domain || '').trim();
      const path = String(cookie?.path || '/').trim() || '/';
      merged.set(`${name}|${domain}|${path}`, {
        ...cookie,
        name,
        value,
        path
      });
    }
  }

  return Array.from(merged.values());
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
    this.bootstrapSessionTtlMs = Number(options.bootstrapSessionTtlMs) || DEFAULT_BOOTSTRAP_SESSION_TTL_MS;
    this.browserBootstrapTimeoutMs = Number(options.browserBootstrapTimeoutMs) || DEFAULT_BROWSER_BOOTSTRAP_TIMEOUT_MS;
    this.browserBootstrapPollIntervalMs = Number(options.browserBootstrapPollIntervalMs) || DEFAULT_BROWSER_BOOTSTRAP_POLL_INTERVAL_MS;
    this.sessionManager = options.sessionManager || null;
    this.browserBootstrapFactory = typeof options.browserBootstrapFactory === 'function'
      ? options.browserBootstrapFactory
      : (bootstrapOptions) => this._createDefaultBrowserBootstrapProvider(bootstrapOptions);
  }

  setSessionManager(sessionManager) {
    this.sessionManager = sessionManager || null;
  }

  _resolveRequestContext(match, options = {}) {
    const externalId = String(match?.external_id || '').trim();
    if (!externalId) {
      throw new FotMobApiError('MISSING_MATCH_ID', { code: 'MISSING_MATCH_ID' });
    }

    const identity = options.identity || null;
    const referer = String(options.referer || `${this.baseUrl}/match/${externalId}`);
    const port = Number(identity?.proxy?.port || options.port || 0);
    const proxyServer = options.proxyServer || identity?.proxy?.server || identity?.proxy?.url || null;
    const userAgent = String(
      options.userAgent
      || identity?.stealth?.userAgent
      || DEFAULT_USER_AGENT
    ).trim();

    return {
      externalId,
      identity,
      referer,
      port,
      proxyServer,
      userAgent
    };
  }

  _buildMatchDetailsHeaders(session, userAgent, referer) {
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

    return headers;
  }

  async fetchMatchDetails(match, options = {}) {
    const requestContext = this._resolveRequestContext(match, options);
    const {
      externalId,
      port,
      proxyServer,
      referer,
      userAgent: defaultUserAgent
    } = requestContext;

    const session = await this._ensureSession({
      port,
      proxyServer,
      referer,
      userAgent: defaultUserAgent,
      explicitSession: options.session,
      identity: requestContext.identity
    });
    const userAgent = String(
      options.userAgent
      || session?.userAgent
      || requestContext.identity?.stealth?.userAgent
      || DEFAULT_USER_AGENT
    ).trim();

    await this._applyJitter();

    const url = new URL('/api/data/matchDetails', this.baseUrl);
    url.searchParams.set('matchId', externalId);

    return this._requestJson(url, {
      headers: this._buildMatchDetailsHeaders(session, userAgent, referer),
      proxyServer
    });
  }

  _hasUsableSession(session) {
    return Array.isArray(session?.cookies) && session.cookies.some((cookie) => {
      const name = String(cookie?.name || '').trim();
      const value = String(cookie?.value || '').trim();
      return name && value;
    });
  }

  async _ensureSession(options = {}) {
    const session = await this._resolveSession(options.port, options.proxyServer, options.explicitSession);
    if (this._hasUsableSession(session)) {
      return session;
    }

    const bootstrapSession = await this._bootstrapSessionFromProbe(options);
    if (bootstrapSession) {
      return bootstrapSession;
    }

    return session;
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

  _resolveBootstrapTargets(referer) {
    const baseOrigin = new URL(this.baseUrl);
    const bootstrapTargets = [new URL('/', baseOrigin)];

    if (!referer) {
      return bootstrapTargets;
    }

    try {
      const refererUrl = new URL(referer, this.baseUrl);
      if (refererUrl.hostname === baseOrigin.hostname) {
        bootstrapTargets.push(refererUrl);
      }
    } catch {
      // 忽略非法 referer
    }

    return bootstrapTargets;
  }

  _normalizeBrowserCookie(rawCookie = {}, defaultDomain) {
    const name = String(rawCookie?.name || '').trim();
    const value = String(rawCookie?.value || '').trim();
    const domain = String(rawCookie?.domain || defaultDomain || '').trim() || defaultDomain;

    if (!name || !value || !domain) {
      return null;
    }

    const normalized = {
      name,
      value,
      domain,
      path: String(rawCookie?.path || '/').trim() || '/',
      httpOnly: Boolean(rawCookie?.httpOnly),
      secure: Boolean(rawCookie?.secure)
    };

    const expiry = resolveCookieExpiry(rawCookie?.expires);
    if (expiry.expired) {
      return null;
    }
    if (expiry.expires) {
      normalized.expires = expiry.expires;
    }

    const sameSite = String(rawCookie?.sameSite || '').trim();
    if (sameSite) {
      normalized.sameSite = sameSite;
    }

    return normalized;
  }

  _normalizeBrowserCookies(cookies = [], defaultDomain) {
    return (Array.isArray(cookies) ? cookies : [])
      .map((cookie) => this._normalizeBrowserCookie(cookie, defaultDomain))
      .filter(Boolean);
  }

  _hasCriticalBootstrapCookie(cookies = []) {
    return (Array.isArray(cookies) ? cookies : []).some((cookie) => {
      const name = String(cookie?.name || '').trim().toLowerCase();
      return CRITICAL_BOOTSTRAP_COOKIE_NAMES.has(name);
    });
  }

  _resolveBootstrapViewport(identity) {
    const width = Number(identity?.stealth?.viewport?.width);
    const height = Number(identity?.stealth?.viewport?.height);
    if (width > 0 && height > 0) {
      return { width, height };
    }
    return undefined;
  }

  _createBrowserLogger() {
    return {
      info: (...args) => this.logger?.info?.(...args),
      warn: (...args) => this.logger?.warn?.(...args),
      error: (...args) => this.logger?.error?.(...args)
    };
  }

  _createDefaultBrowserBootstrapProvider(options = {}) {
    const fixedProxy = options.proxyServer
      ? {
        server: String(options.proxyServer),
        port: Number(options.port) || 0
      }
      : null;

    return new BrowserProvider({
      logger: this._createBrowserLogger(),
      headless: true,
      userAgent: options.userAgent || DEFAULT_USER_AGENT,
      viewport: options.viewport || undefined,
      defaultTimeoutMs: this.browserBootstrapTimeoutMs,
      fixedProxy
    });
  }

  async _collectBrowserBootstrapCookies(browserProvider, target, defaultDomain) {
    const page = browserProvider?.getPage?.();
    const context = page?.context?.();
    if (!context || typeof context.cookies !== 'function') {
      return [];
    }

    const targetUrls = [this.baseUrl];
    if (target?.href) {
      targetUrls.push(target.href);
    }

    const deadline = Date.now() + this.browserBootstrapTimeoutMs;
    let cookies = [];

    while (Date.now() <= deadline) {
      let rawCookies = [];
      try {
        rawCookies = await context.cookies(targetUrls);
      } catch (error) {
        if (typeof this.logger?.warn === 'function') {
          this.logger.warn(`[FotMobApiClient] 浏览器读取 Cookie 失败: ${error.message}`);
        }
        break;
      }

      cookies = mergeCookies(cookies, this._normalizeBrowserCookies(rawCookies, defaultDomain));
      if (this._hasCriticalBootstrapCookie(cookies)) {
        return cookies;
      }

      await browserProvider.sleep(this.browserBootstrapPollIntervalMs);
    }

    return cookies;
  }

  async _runBrowserBootstrapTarget(browserProvider, target, index, defaultDomain) {
    if (index === 0) {
      await browserProvider.warmup(target.href, {
        waitUntil: 'domcontentloaded',
        timeout: this.browserBootstrapTimeoutMs
      });
    } else {
      await browserProvider.goto(target.href, {
        waitUntil: 'domcontentloaded',
        timeout: this.browserBootstrapTimeoutMs
      });
    }

    const freshCookies = await this._collectBrowserBootstrapCookies(browserProvider, target, defaultDomain);
    if (freshCookies.length > 0 && typeof this.logger?.info === 'function') {
      const cookieSummary = this._hasCriticalBootstrapCookie(freshCookies) ? '命中关键 Cookie' : '获取到基础 Cookie';
      this.logger.info(
        `[FotMobApiClient] 浏览器破冰成功: ${target.href} -> ${freshCookies.length} 个 Cookie (${cookieSummary})`
      );
    }

    return freshCookies;
  }

  async _closeBrowserBootstrapProvider(browserProvider) {
    if (!browserProvider || typeof browserProvider.close !== 'function') {
      return;
    }

    try {
      await browserProvider.close();
    } catch (error) {
      if (typeof this.logger?.warn === 'function') {
        this.logger.warn(`[FotMobApiClient] 浏览器破冰关闭失败: ${error.message}`);
      }
    }
  }

  async _persistBootstrapSession(port, session) {
    if (
      !this.sessionManager
      || !Number.isInteger(port)
      || port <= 0
      || typeof this.sessionManager.storeSession !== 'function'
    ) {
      return session;
    }

    try {
      return await this.sessionManager.storeSession(port, session);
    } catch (error) {
      if (typeof this.logger?.warn === 'function') {
        this.logger.warn(`[FotMobApiClient] 预热会话持久化失败: ${error.message}`);
      }
      return session;
    }
  }

  async _bootstrapSessionFromProbe(options = {}) {
    const proxyServer = options.proxyServer || null;
    const userAgent = String(options.userAgent || DEFAULT_USER_AGENT).trim();
    const defaultDomain = normalizeCookieDomain(new URL(this.baseUrl).hostname);
    const bootstrapTargets = this._resolveBootstrapTargets(options.referer);
    const browserProvider = this.browserBootstrapFactory({
      identity: options.identity || null,
      port: options.port,
      proxyServer,
      userAgent,
      viewport: this._resolveBootstrapViewport(options.identity)
    });

    let collectedCookies = [];
    try {
      for (const [index, target] of bootstrapTargets.entries()) {
        try {
          const freshCookies = await this._runBrowserBootstrapTarget(browserProvider, target, index, defaultDomain);
          if (freshCookies.length > 0) {
            collectedCookies = mergeCookies(collectedCookies, freshCookies);
          }

          if (this._hasCriticalBootstrapCookie(collectedCookies)) {
            break;
          }
        } catch (error) {
          if (typeof this.logger?.warn === 'function') {
            this.logger.warn(`[FotMobApiClient] 浏览器破冰失败: ${target.href} -> ${error.message}`);
          }
        }
      }
    } finally {
      await this._closeBrowserBootstrapProvider(browserProvider);
    }

    if (collectedCookies.length === 0) {
      return null;
    }

    const session = {
      port: Number.isInteger(options.port) && options.port > 0 ? options.port : 0,
      cookies: collectedCookies,
      origins: [],
      createdAt: Date.now(),
      expiresAt: Date.now() + this.bootstrapSessionTtlMs,
      userAgent,
      viewport: this._resolveBootstrapViewport(options.identity) || null,
      proxyUrl: proxyServer || null,
      source: 'browser_bootstrap_probe'
    };

    return this._persistBootstrapSession(options.port, session);
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

  async _requestJson(url, options = {}) {
    const { statusCode, headers, body } = await this._requestRaw(url, options);
    if (statusCode < 200 || statusCode >= 300) {
      throw new FotMobApiError(`HTTP_${statusCode}`, {
        code: 'HTTP_ERROR',
        statusCode,
        url: (url instanceof URL ? url.href : String(url)),
        responseBody: body,
        headers
      });
    }

    try {
      const parsed = JSON.parse(body);
      if (!parsed || typeof parsed !== 'object') {
        throw new FotMobApiError('INVALID_JSON_PAYLOAD', {
          code: 'INVALID_JSON_PAYLOAD',
          statusCode,
          url: (url instanceof URL ? url.href : String(url)),
          responseBody: body,
          headers
        });
      }
      return parsed;
    } catch (error) {
      if (error instanceof FotMobApiError) {
        throw error;
      }

      const isHtmlLike = /^\s*</.test(body);
      throw new FotMobApiError(isHtmlLike ? 'HTML_CHALLENGE_RESPONSE' : `JSON_PARSE_ERROR:${error.message}`, {
        code: isHtmlLike ? 'HTML_CHALLENGE_RESPONSE' : 'JSON_PARSE_ERROR',
        statusCode,
        url: (url instanceof URL ? url.href : String(url)),
        responseBody: body,
        headers
      });
    }
  }

  _requestRaw(url, options = {}) {
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
          resolve({
            statusCode: Number(res.statusCode) || 0,
            headers: res.headers || {},
            body: rawBody
          });
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
  buildCookieHeader,
  mergeCookies,
  parseSetCookieHeader
};
