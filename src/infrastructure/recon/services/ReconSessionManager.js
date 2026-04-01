'use strict';

const fs = require('node:fs');
const path = require('node:path');

const DEFAULT_DOMAIN = '.oddsportal.com';
const DEFAULT_SOURCE_URL = 'https://www.oddsportal.com/';
const DEFAULT_EXCLUDE_NAMES = ['oddsportalcom_session'];

class ReconSessionManager {
  constructor(options = {}) {
    this.logger = options.logger || console;
    this.traceId = options.traceId || 'trace-unknown';
    this.sessionPath = String(options.sessionPath || '').trim();
    this.defaultDomain = String(options.defaultDomain || DEFAULT_DOMAIN);
    this.defaultSourceUrl = String(options.defaultSourceUrl || DEFAULT_SOURCE_URL);
    this.excludeNames = Array.isArray(options.excludeNames) ? [...options.excludeNames] : [...DEFAULT_EXCLUDE_NAMES];
  }

  load(options = {}) {
    const resolvedSessionPath = this._resolveSessionPath();
    const excludeNames = this._normalizeNames(options.excludeNames ?? this.excludeNames);
    const includeNames = this._normalizeNames(options.includeNames ?? []);
    if (!resolvedSessionPath) {
      return {
        cookies: [],
        userAgent: '',
        extraHTTPHeaders: {},
        sourceFormat: 'disabled',
        excludeNames,
        includeNames
      };
    }

    let raw = '';
    try {
      raw = fs.readFileSync(resolvedSessionPath, 'utf8');
    } catch (error) {
      this.logger.warn('recon_external_session_read_failed', {
        traceId: this.traceId,
        sessionPath: this.sessionPath,
        error: error.message
      });
      return {
        cookies: [],
        userAgent: '',
        extraHTTPHeaders: {},
        sourceFormat: 'unavailable',
        excludeNames,
        includeNames
      };
    }

    const trimmed = String(raw || '').trim();
    if (!trimmed) {
      return {
        cookies: [],
        userAgent: '',
        extraHTTPHeaders: {},
        sourceFormat: 'empty',
        excludeNames,
        includeNames
      };
    }

    const jsonPayload = this._tryParseJson(trimmed);
    if (jsonPayload !== null) {
      return this._parseJsonPayload(jsonPayload, { excludeNames, includeNames });
    }

    return this._parseHeaderPayload(trimmed, { excludeNames, includeNames });
  }

  _resolveSessionPath() {
    if (!this.sessionPath) {
      return '';
    }

    if (fs.existsSync(this.sessionPath)) {
      return this.sessionPath;
    }

    const basename = path.basename(this.sessionPath);
    const cwdCandidate = path.resolve(process.cwd(), basename);
    if (fs.existsSync(cwdCandidate)) {
      this.logger.info('recon_external_session_path_mapped', {
        traceId: this.traceId,
        originalPath: this.sessionPath,
        resolvedPath: cwdCandidate
      });
      return cwdCandidate;
    }

    return this.sessionPath;
  }

  _tryParseJson(raw) {
    try {
      return JSON.parse(raw);
    } catch {
      return null;
    }
  }

  _normalizeNames(names) {
    return [...new Set(
      (Array.isArray(names) ? names : [])
        .map((name) => String(name || '').trim())
        .filter(Boolean)
    )];
  }

  _shouldKeepCookie(name, includeNames = [], excludeNames = []) {
    const normalizedName = String(name || '').trim();
    if (!normalizedName) {
      return false;
    }

    if (includeNames.length > 0 && !includeNames.includes(normalizedName)) {
      return false;
    }

    if (excludeNames.includes(normalizedName)) {
      return false;
    }

    return true;
  }

  _parseJsonPayload(payload, filters = {}) {
    const includeNames = this._normalizeNames(filters.includeNames);
    const excludeNames = this._normalizeNames(filters.excludeNames);
    const cookies = Array.isArray(payload)
      ? payload
      : Array.isArray(payload?.cookies)
        ? payload.cookies
        : [];
    const normalizedCookies = cookies
      .filter((cookie) => this._shouldKeepCookie(cookie?.name, includeNames, excludeNames))
      .map((cookie) => this._normalizeJsonCookie(cookie))
      .filter(Boolean);
    const userAgent = this._extractJsonUserAgent(payload);

    return {
      cookies: normalizedCookies,
      userAgent,
      extraHTTPHeaders: userAgent ? { 'user-agent': userAgent } : {},
      sourceFormat: 'json',
      excludeNames,
      includeNames
    };
  }

  _extractJsonUserAgent(payload) {
    if (typeof payload?.userAgent === 'string' && payload.userAgent.trim()) {
      return payload.userAgent.trim();
    }

    if (typeof payload?.origins?.[0]?.userAgent === 'string' && payload.origins[0].userAgent.trim()) {
      return payload.origins[0].userAgent.trim();
    }

    return '';
  }

  _normalizeJsonCookie(cookie) {
    if (!cookie || typeof cookie !== 'object') {
      return null;
    }

    const name = typeof cookie.name === 'string' ? cookie.name.trim() : '';
    if (!name) {
      return null;
    }

    const value = typeof cookie.value === 'string' ? cookie.value : '';
    const domain = typeof cookie.domain === 'string' && cookie.domain.trim()
      ? cookie.domain.trim()
      : this.defaultDomain;
    const path = typeof cookie.path === 'string' && cookie.path.trim() ? cookie.path.trim() : '/';
    const expires = Number(cookie.expires ?? cookie.expirationDate ?? -1);
    const sameSite = this._normalizeSameSite(cookie.sameSite);

    return {
      name,
      value,
      domain,
      path,
      expires: Number.isFinite(expires) ? expires : -1,
      httpOnly: cookie.httpOnly === true,
      secure: cookie.secure === true,
      sameSite
    };
  }

  _normalizeSameSite(value) {
    const normalized = String(value || '').trim().toLowerCase();
    if (normalized === 'lax') {
      return 'Lax';
    }

    if (normalized === 'strict') {
      return 'Strict';
    }

    if (normalized === 'none' || normalized === 'no_restriction') {
      return 'None';
    }

    return 'Lax';
  }

  _parseHeaderPayload(raw, filters = {}) {
    const includeNames = this._normalizeNames(filters.includeNames);
    const excludeNames = this._normalizeNames(filters.excludeNames);
    const lines = raw
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter(Boolean);
    const headers = new Map();

    for (const line of lines) {
      const separatorIndex = line.indexOf(':');
      if (separatorIndex <= 0) {
        continue;
      }

      const name = line.slice(0, separatorIndex).trim().toLowerCase();
      const value = line.slice(separatorIndex + 1).trim();
      if (name) {
        headers.set(name, value);
      }
    }

    const userAgent = headers.get('user-agent') || '';
    const cookieHeader = headers.get('cookie') || '';
    const referer = headers.get('referer') || headers.get('origin') || this.defaultSourceUrl;
    const domain = this._extractDomainFromUrl(referer) || this.defaultDomain;
    const cookies = cookieHeader
      .split(';')
      .map((entry) => entry.trim())
      .filter(Boolean)
      .map((entry) => {
        const separatorIndex = entry.indexOf('=');
        if (separatorIndex <= 0) {
          return null;
        }

        const cookieName = entry.slice(0, separatorIndex).trim();
        if (!this._shouldKeepCookie(cookieName, includeNames, excludeNames)) {
          return null;
        }

        return {
          name: cookieName,
          value: entry.slice(separatorIndex + 1).trim(),
          domain,
          path: '/',
          expires: -1,
          httpOnly: false,
          secure: true,
          sameSite: 'Lax'
        };
      })
      .filter(Boolean);

    const extraHTTPHeaders = {};
    if (userAgent) {
      extraHTTPHeaders['user-agent'] = userAgent;
    }
    if (headers.get('accept-language')) {
      extraHTTPHeaders['accept-language'] = headers.get('accept-language');
    }

    return {
      cookies,
      userAgent,
      extraHTTPHeaders,
      sourceFormat: 'header',
      excludeNames,
      includeNames
    };
  }

  _extractDomainFromUrl(url) {
    try {
      const parsed = new URL(url);
      return parsed.hostname.startsWith('.') ? parsed.hostname : `.${parsed.hostname}`;
    } catch {
      return '';
    }
  }
}

module.exports = {
  ReconSessionManager
};
