'use strict';

const fs = require('node:fs');
const path = require('node:path');

const DEFAULT_DOMAIN = '.oddsportal.com';
const DEFAULT_SOURCE_URL = 'https://www.oddsportal.com/';
const DEFAULT_EXCLUDE_NAMES = ['oddsportalcom_session'];
const DEFAULT_BUFFER_POOL_TTL_MS = 30 * 60 * 1000;
const BUFFER_POOL_VERSION = 1;
const BUFFER_POOL_KIND_GOLDEN = 'GOLDEN_SNAPSHOT';
const BUFFER_POOL_KIND_LINEAGE = 'LINEAGE_SNAPSHOT';
const BUFFER_POOL_ROLE_PREFLIGHT = 'preflight';
const BUFFER_POOL_ROLE_WORKER = 'worker';

class ReconSessionManager {
  constructor(options = {}) {
    this.logger = options.logger || console;
    this.traceId = options.traceId || 'trace-unknown';
    this.sessionPath = String(options.sessionPath || '').trim();
    this.defaultDomain = String(options.defaultDomain || DEFAULT_DOMAIN);
    this.defaultSourceUrl = String(options.defaultSourceUrl || DEFAULT_SOURCE_URL);
    this.excludeNames = Array.isArray(options.excludeNames) ? [...options.excludeNames] : [...DEFAULT_EXCLUDE_NAMES];
    this.bufferPoolPath = String(
      options.bufferPoolPath || process.env.RECON_SESSION_BUFFER_PATH || ''
    ).trim();
    this.bufferPoolTtlMs = this._normalizePositiveInteger(
      options.bufferPoolTtlMs ?? process.env.RECON_SESSION_BUFFER_TTL_MS,
      DEFAULT_BUFFER_POOL_TTL_MS
    );
    this.bufferPoolRole = this._normalizeBufferPoolRole(
      options.bufferPoolRole || process.env.RECON_SESSION_BUFFER_ROLE || BUFFER_POOL_ROLE_WORKER
    );
    this.proxyPort = this._normalizeProxyPort(
      options.proxyPort ?? options.proxy?.port ?? process.env.RECON_SESSION_PROXY_PORT
    );
    this.runtimeSnapshot = null;
  }

  load(options = {}) {
    const excludeNames = this._normalizeNames(options.excludeNames ?? this.excludeNames);
    const includeNames = this._normalizeNames(options.includeNames ?? []);
    const filters = {
      excludeNames,
      includeNames,
      allowStaleBuffer: options.allowStaleBuffer !== false
    };
    let snapshot = this._loadPersistentSnapshot(filters);
    snapshot = this._mergeBufferPoolSnapshot(snapshot, filters);
    return this._mergeRuntimeSnapshot(snapshot, filters);
  }

  setRuntimeSnapshot(snapshot = {}, options = {}) {
    const normalized = this._normalizeRuntimeSnapshot(snapshot);
    if (!normalized) {
      return {
        applied: false,
        cookies: 0,
        sourceFormat: 'runtime_empty'
      };
    }

    this.runtimeSnapshot = normalized;
    const persisted = this._persistSnapshotToBufferPool(normalized, options);
    this.logger.info('recon_runtime_session_snapshot_updated', {
      traceId: this.traceId,
      cookies: normalized.cookies.length,
      hasUserAgent: Boolean(normalized.userAgent),
      bufferPoolPersisted: persisted.persisted === true,
      snapshotKind: persisted.snapshotKind || null,
      lineageKey: persisted.lineageKey || null
    });
    return {
      applied: true,
      cookies: normalized.cookies.length,
      sourceFormat: normalized.sourceFormat,
      bufferPoolPersisted: persisted.persisted === true,
      snapshotKind: persisted.snapshotKind || null,
      lineageKey: persisted.lineageKey || null
    };
  }

  clearRuntimeSnapshot() {
    this.runtimeSnapshot = null;
  }

  inspectBufferPool(options = {}) {
    const referenceTimeMs = this._resolveReferenceTime(options.referenceTime);
    const lineageKey = this._buildLineageKey(this.proxyPort);
    if (!this.bufferPoolPath) {
      return {
        enabled: false,
        path: '',
        ttlMs: this.bufferPoolTtlMs,
        exists: false,
        hasGoldenSnapshot: false,
        hasLineageSnapshot: false,
        needsRefresh: true,
        isStale: true,
        goldenAgeMs: null,
        lineageKey
      };
    }

    const pool = this._readBufferPool();
    const goldenSnapshot = this._extractBufferRecord(pool?.goldenSnapshot);
    const lineageSnapshot = lineageKey ? this._extractBufferRecord(pool?.lineages?.[lineageKey]) : null;
    const goldenAgeMs = goldenSnapshot
      ? Math.max(0, referenceTimeMs - this._parseTimestampMs(goldenSnapshot.updatedAt))
      : null;
    const lineageAgeMs = lineageSnapshot
      ? Math.max(0, referenceTimeMs - this._parseTimestampMs(lineageSnapshot.updatedAt))
      : null;
    const isGoldenStale = !goldenSnapshot || goldenAgeMs === null || goldenAgeMs > this.bufferPoolTtlMs;
    const isLineageStale = !lineageSnapshot || lineageAgeMs === null || lineageAgeMs > this.bufferPoolTtlMs;

    return {
      enabled: true,
      path: this.bufferPoolPath,
      ttlMs: this.bufferPoolTtlMs,
      exists: Boolean(pool),
      hasGoldenSnapshot: Boolean(goldenSnapshot),
      hasLineageSnapshot: Boolean(lineageSnapshot),
      goldenUpdatedAt: goldenSnapshot?.updatedAt || null,
      lineageUpdatedAt: lineageSnapshot?.updatedAt || null,
      goldenAgeMs,
      lineageAgeMs,
      isStale: isGoldenStale,
      isGoldenStale,
      isLineageStale,
      needsRefresh: isGoldenStale,
      lineageKey
    };
  }

  shouldRefreshGoldenSnapshot(options = {}) {
    return this.inspectBufferPool(options).needsRefresh;
  }

  acquireGoldenRefreshLease(options = {}) {
    if (!this.bufferPoolPath) {
      return { acquired: false, reason: 'buffer_pool_disabled', lease: null };
    }

    const lease = {
      traceId: this.traceId,
      pid: process.pid,
      acquiredAt: new Date(this._resolveReferenceTime(options.referenceTime)).toISOString()
    };
    const lockPath = this._getRefreshLockPath();
    fs.mkdirSync(path.dirname(lockPath), { recursive: true });

    try {
      fs.writeFileSync(lockPath, JSON.stringify(lease, null, 2), { encoding: 'utf8', flag: 'wx' });
      return { acquired: true, reason: 'acquired', lease };
    } catch (error) {
      if (error.code !== 'EEXIST') {
        throw error;
      }
      return {
        acquired: false,
        reason: 'busy',
        lease: this._readJsonFile(lockPath)
      };
    }
  }

  releaseGoldenRefreshLease(lease = null) {
    const lockPath = this._getRefreshLockPath();
    if (!lockPath || !fs.existsSync(lockPath)) {
      return false;
    }

    const activeLease = this._readJsonFile(lockPath);
    if (
      lease
      && activeLease
      && activeLease.traceId
      && lease.traceId
      && activeLease.traceId !== lease.traceId
    ) {
      return false;
    }

    fs.unlinkSync(lockPath);
    return true;
  }

  resolveProtocolIdentity(options = {}) {
    const proxyPort = this._normalizeProxyPort(options.proxyPort ?? this.proxyPort);
    const ciphersCount = this._normalizePositiveInteger(options.ciphersCount, 1);
    const sigalgsCount = this._normalizePositiveInteger(options.sigalgsCount, 1);
    const lineageKey = this._buildLineageKey(proxyPort);
    const pool = this._readBufferPool() || this._createEmptyBufferPool();
    const existingIdentity = lineageKey && pool.nodeIdentities
      ? pool.nodeIdentities[lineageKey]
      : null;

    if (
      existingIdentity
      && Number(existingIdentity.ciphersCount) === ciphersCount
      && Number(existingIdentity.sigalgsCount) === sigalgsCount
    ) {
      return {
        ...existingIdentity,
        source: 'session_buffer_pool'
      };
    }

    const normalizedPort = Number(proxyPort || 0);
    const cipherIdx = normalizedPort % ciphersCount;
    const sigalgIdx = (normalizedPort + 1) % sigalgsCount;
    const identity = {
      lineageKey,
      proxyPort,
      ciphersCount,
      sigalgsCount,
      cipherIdx,
      sigalgIdx,
      ja3ProfileId: `${lineageKey}:${cipherIdx}:${sigalgIdx}`,
      updatedAt: new Date().toISOString()
    };

    if (this.bufferPoolPath && lineageKey) {
      pool.updatedAt = identity.updatedAt;
      pool.ttlMs = this.bufferPoolTtlMs;
      pool.nodeIdentities = {
        ...(pool.nodeIdentities || {}),
        [lineageKey]: identity
      };
      this._writeBufferPool(pool);
      return {
        ...identity,
        source: 'session_buffer_pool'
      };
    }

    return {
      ...identity,
      source: 'derived'
    };
  }

  _loadPersistentSnapshot(filters = {}) {
    const resolvedSessionPath = this._resolveSessionPath();
    const excludeNames = this._normalizeNames(filters.excludeNames);
    const includeNames = this._normalizeNames(filters.includeNames);
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

  _mergeBufferPoolSnapshot(baseSnapshot, filters = {}) {
    if (!this.bufferPoolPath) {
      return baseSnapshot;
    }

    const pool = this._readBufferPool();
    if (!pool) {
      return baseSnapshot;
    }

    const inspect = this.inspectBufferPool();
    const includeStale = filters.allowStaleBuffer !== false;
    let merged = baseSnapshot;
    const goldenRecord = this._extractBufferRecord(pool.goldenSnapshot);
    if (
      goldenRecord
      && (includeStale || inspect.isGoldenStale !== true)
    ) {
      merged = this._mergeSnapshot(merged, {
        ...goldenRecord.snapshot,
        sourceFormat: inspect.isGoldenStale ? 'session_buffer_golden_stale' : 'session_buffer_golden'
      }, filters);
    }

    const lineageKey = inspect.lineageKey;
    const lineageRecord = lineageKey ? this._extractBufferRecord(pool?.lineages?.[lineageKey]) : null;
    if (
      lineageRecord
      && (includeStale || inspect.isLineageStale !== true)
    ) {
      merged = this._mergeSnapshot(merged, {
        ...lineageRecord.snapshot,
        sourceFormat: inspect.isLineageStale ? 'session_buffer_lineage_stale' : 'session_buffer_lineage'
      }, filters);
    }

    return merged;
  }

  _persistSnapshotToBufferPool(snapshot, options = {}) {
    if (!this.bufferPoolPath) {
      return { persisted: false, snapshotKind: null, lineageKey: null };
    }

    const snapshotKind = this._resolveSnapshotKind(options.snapshotKind);
    const lineageKey = this._buildLineageKey(this.proxyPort);
    const pool = this._readBufferPool() || this._createEmptyBufferPool();
    const updatedAt = new Date().toISOString();
    pool.updatedAt = updatedAt;
    pool.ttlMs = this.bufferPoolTtlMs;

    if (snapshotKind === BUFFER_POOL_KIND_GOLDEN) {
      pool.goldenSnapshot = this._buildBufferRecord(snapshot, {
        kind: BUFFER_POOL_KIND_GOLDEN,
        updatedAt,
        lineageKey
      });
    } else if (lineageKey) {
      pool.lineages = {
        ...(pool.lineages || {}),
        [lineageKey]: this._buildBufferRecord(snapshot, {
          kind: BUFFER_POOL_KIND_LINEAGE,
          updatedAt,
          lineageKey
        })
      };
    }

    if (lineageKey) {
      const protocolIdentity = this.resolveProtocolIdentity({
        proxyPort: this.proxyPort,
        ciphersCount: 3,
        sigalgsCount: 2
      });
      pool.nodeIdentities = {
        ...(pool.nodeIdentities || {}),
        [lineageKey]: {
          lineageKey,
          proxyPort: this.proxyPort,
          ciphersCount: protocolIdentity.ciphersCount,
          sigalgsCount: protocolIdentity.sigalgsCount,
          cipherIdx: protocolIdentity.cipherIdx,
          sigalgIdx: protocolIdentity.sigalgIdx,
          ja3ProfileId: protocolIdentity.ja3ProfileId,
          updatedAt
        }
      };
    }

    this._writeBufferPool(pool);
    return {
      persisted: true,
      snapshotKind,
      lineageKey
    };
  }

  _resolveSnapshotKind(snapshotKind = '') {
    const normalized = String(snapshotKind || '').trim().toUpperCase();
    if (normalized === BUFFER_POOL_KIND_GOLDEN || normalized === BUFFER_POOL_KIND_LINEAGE) {
      return normalized;
    }

    return this.bufferPoolRole === BUFFER_POOL_ROLE_PREFLIGHT
      ? BUFFER_POOL_KIND_GOLDEN
      : BUFFER_POOL_KIND_LINEAGE;
  }

  _buildBufferRecord(snapshot, metadata = {}) {
    return {
      kind: metadata.kind || BUFFER_POOL_KIND_LINEAGE,
      traceId: this.traceId,
      proxyPort: this.proxyPort,
      lineageKey: metadata.lineageKey || this._buildLineageKey(this.proxyPort),
      updatedAt: metadata.updatedAt || new Date().toISOString(),
      snapshot: this._cloneSnapshot(snapshot)
    };
  }

  _extractBufferRecord(record) {
    if (!record || typeof record !== 'object') {
      return null;
    }

    const snapshot = this._normalizeRuntimeSnapshot(record.snapshot || {});
    if (!snapshot) {
      return null;
    }

    return {
      kind: String(record.kind || '').trim() || BUFFER_POOL_KIND_LINEAGE,
      traceId: String(record.traceId || '').trim(),
      proxyPort: this._normalizeProxyPort(record.proxyPort),
      lineageKey: String(record.lineageKey || '').trim(),
      updatedAt: String(record.updatedAt || '').trim(),
      snapshot
    };
  }

  _cloneSnapshot(snapshot = {}) {
    return {
      cookies: (Array.isArray(snapshot.cookies) ? snapshot.cookies : []).map((cookie) => ({
        ...cookie
      })),
      userAgent: String(snapshot.userAgent || '').trim(),
      extraHTTPHeaders: { ...(snapshot.extraHTTPHeaders || {}) },
      sourceFormat: String(snapshot.sourceFormat || '').trim()
    };
  }

  _createEmptyBufferPool() {
    return {
      version: BUFFER_POOL_VERSION,
      ttlMs: this.bufferPoolTtlMs,
      updatedAt: null,
      goldenSnapshot: null,
      lineages: {},
      nodeIdentities: {}
    };
  }

  _readBufferPool() {
    if (!this.bufferPoolPath || !fs.existsSync(this.bufferPoolPath)) {
      return null;
    }

    try {
      const parsed = JSON.parse(fs.readFileSync(this.bufferPoolPath, 'utf8'));
      return parsed && typeof parsed === 'object'
        ? {
          ...this._createEmptyBufferPool(),
          ...parsed,
          lineages: parsed?.lineages && typeof parsed.lineages === 'object' ? parsed.lineages : {},
          nodeIdentities: parsed?.nodeIdentities && typeof parsed.nodeIdentities === 'object'
            ? parsed.nodeIdentities
            : {}
        }
        : this._createEmptyBufferPool();
    } catch (error) {
      this.logger.warn('recon_session_buffer_pool_read_failed', {
        traceId: this.traceId,
        bufferPoolPath: this.bufferPoolPath,
        error: error.message
      });
      return null;
    }
  }

  _writeBufferPool(pool) {
    if (!this.bufferPoolPath) {
      return;
    }

    fs.mkdirSync(path.dirname(this.bufferPoolPath), { recursive: true });
    const tempPath = `${this.bufferPoolPath}.${process.pid}.tmp`;
    fs.writeFileSync(tempPath, JSON.stringify(pool, null, 2), 'utf8');
    fs.renameSync(tempPath, this.bufferPoolPath);
  }

  _readJsonFile(targetPath) {
    try {
      if (!targetPath || !fs.existsSync(targetPath)) {
        return null;
      }
      return JSON.parse(fs.readFileSync(targetPath, 'utf8'));
    } catch {
      return null;
    }
  }

  _getRefreshLockPath() {
    return this.bufferPoolPath ? `${this.bufferPoolPath}.refresh.lock` : '';
  }

  _resolveReferenceTime(referenceTime = Date.now()) {
    if (referenceTime instanceof Date) {
      return referenceTime.getTime();
    }
    const numeric = Number(referenceTime);
    return Number.isFinite(numeric) ? numeric : Date.now();
  }

  _parseTimestampMs(value) {
    const parsed = Date.parse(String(value || ''));
    return Number.isFinite(parsed) ? parsed : 0;
  }

  _normalizePositiveInteger(value, fallback) {
    const normalized = Number.parseInt(String(value ?? ''), 10);
    return Number.isInteger(normalized) && normalized > 0 ? normalized : fallback;
  }

  _normalizeBufferPoolRole(value) {
    const normalized = String(value || '').trim().toLowerCase();
    return normalized === BUFFER_POOL_ROLE_PREFLIGHT
      ? BUFFER_POOL_ROLE_PREFLIGHT
      : BUFFER_POOL_ROLE_WORKER;
  }

  _normalizeProxyPort(value) {
    const normalized = Number.parseInt(String(value ?? ''), 10);
    return Number.isInteger(normalized) && normalized > 0 ? normalized : null;
  }

  _buildLineageKey(proxyPort = null) {
    return proxyPort ? `proxy:${proxyPort}` : 'proxy:direct';
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
    const cookiePath = typeof cookie.path === 'string' && cookie.path.trim() ? cookie.path.trim() : '/';
    const expires = Number(cookie.expires ?? cookie.expirationDate ?? -1);
    const sameSite = this._normalizeSameSite(cookie.sameSite);

    return {
      name,
      value,
      domain,
      path: cookiePath,
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

  _normalizeRuntimeSnapshot(snapshot = {}) {
    if (!snapshot || typeof snapshot !== 'object') {
      return null;
    }

    const cookies = (Array.isArray(snapshot.cookies) ? snapshot.cookies : [])
      .map((cookie) => this._normalizeJsonCookie(cookie))
      .filter(Boolean);
    const userAgent = typeof snapshot.userAgent === 'string' && snapshot.userAgent.trim()
      ? snapshot.userAgent.trim()
      : '';
    const extraHTTPHeaders = this._normalizeExtraHTTPHeaders(snapshot.extraHTTPHeaders);
    if (userAgent) {
      extraHTTPHeaders['user-agent'] = userAgent;
    }

    if (cookies.length === 0 && !userAgent && Object.keys(extraHTTPHeaders).length === 0) {
      return null;
    }

    return {
      cookies,
      userAgent,
      extraHTTPHeaders,
      sourceFormat: 'runtime'
    };
  }

  _normalizeExtraHTTPHeaders(headers) {
    const normalized = {};
    for (const [rawName, rawValue] of Object.entries(headers || {})) {
      const name = String(rawName || '').trim().toLowerCase();
      const value = typeof rawValue === 'string' ? rawValue.trim() : '';
      if (!name || !value) {
        continue;
      }
      normalized[name] = value;
    }
    return normalized;
  }

  _mergeRuntimeSnapshot(snapshot, filters = {}) {
    const runtimeSnapshot = this._normalizeRuntimeSnapshot(this.runtimeSnapshot);
    if (!runtimeSnapshot) {
      return snapshot;
    }

    return this._mergeSnapshot(snapshot, runtimeSnapshot, {
      ...filters,
      sourceFormat: runtimeSnapshot.sourceFormat
    });
  }

  _mergeSnapshot(baseSnapshot = {}, incomingSnapshot = {}, filters = {}) {
    const includeNames = this._normalizeNames(filters.includeNames);
    const excludeNames = this._normalizeNames(filters.excludeNames);
    const incomingCookies = (Array.isArray(incomingSnapshot.cookies) ? incomingSnapshot.cookies : [])
      .filter((cookie) => this._shouldKeepCookie(cookie?.name, includeNames, excludeNames));
    const mergedCookies = this._mergeCookies(baseSnapshot?.cookies, incomingCookies);
    const userAgent = incomingSnapshot.userAgent || baseSnapshot?.userAgent || '';
    const extraHTTPHeaders = {
      ...(baseSnapshot?.extraHTTPHeaders || {}),
      ...(incomingSnapshot.extraHTTPHeaders || {})
    };

    return {
      ...(baseSnapshot || {}),
      cookies: mergedCookies,
      userAgent,
      extraHTTPHeaders,
      sourceFormat: this._mergeSourceFormats(
        baseSnapshot?.sourceFormat,
        filters.sourceFormat || incomingSnapshot.sourceFormat
      ),
      excludeNames,
      includeNames
    };
  }

  _mergeCookies(baseCookies = [], runtimeCookies = []) {
    const merged = new Map();
    const append = (cookies) => {
      for (const cookie of Array.isArray(cookies) ? cookies : []) {
        const name = String(cookie?.name || '').trim();
        if (!name) {
          continue;
        }
        const domain = String(cookie?.domain || this.defaultDomain).trim();
        const cookiePath = String(cookie?.path || '/').trim() || '/';
        merged.set(`${name}|${domain}|${cookiePath}`, cookie);
      }
    };

    append(baseCookies);
    append(runtimeCookies);
    return [...merged.values()];
  }

  _mergeSourceFormats(primary = '', secondary = '') {
    const parts = [primary, secondary]
      .map((value) => String(value || '').trim())
      .filter(Boolean);
    return parts.length > 0 ? [...new Set(parts)].join('+') : 'runtime';
  }
}

module.exports = {
  ReconSessionManager,
  BUFFER_POOL_KIND_GOLDEN,
  BUFFER_POOL_KIND_LINEAGE
};
