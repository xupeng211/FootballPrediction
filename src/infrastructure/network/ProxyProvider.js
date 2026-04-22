/* eslint-disable complexity, max-lines */
'use strict';

const { EventEmitter } = require('node:events');
const http = require('node:http');
const https = require('node:https');
const net = require('node:net');
const { URL } = require('node:url');
const { HttpProxyAgent } = require('http-proxy-agent');
const { HttpsProxyAgent } = require('https-proxy-agent');
const { SocksProxyAgent } = require('socks-proxy-agent');
const { buildProxyServer, normalizeProxyProtocol, resolveProxyPoolConfig } = require('../../../config/proxy_pool');

const DEFAULT_PROTOCOL = 'socks5';
const DEFAULT_TARGET_LATENCY_MS = 1500;
const DEFAULT_SUCCESS_RATE = 0.95;
const DEFAULT_HEARTBEAT_URL = 'https://httpbin.org/ip';
const DEFAULT_FAILURE_COOLDOWN_MS = 300000;
const DEFAULT_HTTP_503_COOLDOWN_MS = 300000;
const DEFAULT_FAILURE_THRESHOLD = 6;
const DEFAULT_HTTP_503_OBSERVATION_THRESHOLD = 3;
const DEFAULT_HEALTH_PROBE_MODE = 'tcp_authoritative';
const DEFAULT_CRITICAL_ERROR_COOLDOWN_MS = 1800000;
const DEFAULT_HEARTBEAT_FAILURE_COOLDOWN_MS = 300000;
const DEFAULT_MIN_HEALTH_SCORE = 60;
const DEFAULT_SUCCESS_HEALTH_REWARD = 4;
const DEFAULT_FAILURE_HEALTH_PENALTY = 10;
const DEFAULT_GATEWAY_PREFLIGHT_TIMEOUT_MS = 1500;
const DEFAULT_TRANSIENT_CONTEXT_COOLDOWN_MS = 3000;
const DEFAULT_UPSTREAM_BLOCK_BASE_COOLDOWN_MS = 5000;
const DEFAULT_UPSTREAM_BLOCK_MAX_COOLDOWN_MS = 15000;

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function ewma(previous, next, alpha) {
  return previous === null || previous === undefined
    ? next
    : (previous * (1 - alpha)) + (next * alpha);
}

function extractStatusCode(reason = '') {
  const message = String(reason || '');
  const match = message.match(/\b(4\d{2}|5\d{2})\b/);
  return match ? Number(match[1]) : null;
}

function positiveNumber(value, fallback) {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

function createProxyAgent(proxyUrl, proxyProtocol, targetProtocol, timeoutMs) {
  if (normalizeProxyProtocol(proxyProtocol) === 'socks5') {
    return new SocksProxyAgent(proxyUrl, { timeout: timeoutMs });
  }

  if (targetProtocol === 'https:') {
    return new HttpsProxyAgent(proxyUrl, { keepAlive: false, timeout: timeoutMs });
  }

  return new HttpProxyAgent(proxyUrl, { keepAlive: false, timeout: timeoutMs });
}

function normalizeHealthProbeMode(value) {
  const normalized = String(value || '').trim().toLowerCase();
  if (normalized === 'tcp_only' || normalized === 'tcp_authoritative' || normalized === 'tcp_then_http') {
    return normalized;
  }
  return DEFAULT_HEALTH_PROBE_MODE;
}

function isTimeoutLike(reason = '') {
  const message = String(reason || '').toLowerCase();
  return message.includes('timeout')
    || message.includes('timed out')
    || message.includes('etimedout');
}

function normalizeFailureClass(failureClass, statusCode, reason = '') {
  const normalized = String(failureClass || '').trim().toLowerCase();
  if (normalized) {
    return normalized;
  }

  const message = String(reason || '').toLowerCase();
  if (statusCode === 429) {
    return 'rate_limit';
  }
  if (message.includes('err_empty_response') || message.includes('empty_response')) {
    return 'upstream_block';
  }
  if (
    message.includes('execution context was destroyed')
    || message.includes('target closed')
    || message.includes('target page')
    || message.includes('page crashed')
  ) {
    return 'browser_context_transient';
  }
  return 'hard_proxy_failure';
}

function resolveHealthPenalty(statusCode, reason = '', failureClass = 'hard_proxy_failure') {
  if (failureClass === 'browser_context_transient') {
    return 2;
  }
  if (failureClass === 'upstream_block') {
    return 4;
  }
  if (statusCode === 403) {
    return 45;
  }
  if (statusCode === 429) {
    return 30;
  }
  if (statusCode === 503) {
    return 20;
  }
  if (statusCode >= 500) {
    return 18;
  }
  if (isTimeoutLike(reason)) {
    return 25;
  }
  return DEFAULT_FAILURE_HEALTH_PENALTY;
}

class ProxyProvider extends EventEmitter {
  constructor(options = {}) {
    super();

    this.logger = options.logger || console;
    this.now = options.now || (() => Date.now());
    this.probes = {
      tcp: options.probes?.tcp || ((node, config) => this._probeTcp(node, config)),
      http: options.probes?.http || ((node, config) => this._probeHttp(node, config))
    };

    this.config = this._buildConfig(options);
    this.nodes = this.config.ports.map(port => this._createNode(port));
    this.nodeByPort = new Map(this.nodes.map(node => [node.port, node]));
    this.leases = new Map();
    this.stickyLeases = new Map();
    this.sequence = 0;
    this.healthTimer = null;
    this.started = false;
    this.initialized = false;
    this.initializationPromise = null;
  }

  _buildConfig(options = {}) {
    const resolvedPoolConfig = resolveProxyPoolConfig();
    const protocol = normalizeProxyProtocol(
      options.protocol || resolvedPoolConfig.protocol || ProxyProvider.resolveProtocol()
    );
    const host = options.host || resolvedPoolConfig.host || ProxyProvider.resolveHost();
    const ports = Array.isArray(options.ports) && options.ports.length > 0
      ? [...options.ports]
      : Array.isArray(resolvedPoolConfig.ports) && resolvedPoolConfig.ports.length > 0
        ? [...resolvedPoolConfig.ports]
        : ProxyProvider.resolvePorts();
    const failureThreshold = positiveNumber(
      options.failureThreshold,
      positiveNumber(resolvedPoolConfig.failureThreshold, DEFAULT_FAILURE_THRESHOLD)
    );
    const http503ObservationThreshold = positiveNumber(
      options.http503ObservationThreshold,
      positiveNumber(
        resolvedPoolConfig.http503ObservationThreshold,
        Math.max(DEFAULT_HTTP_503_OBSERVATION_THRESHOLD, Math.ceil(failureThreshold / 2))
      )
    );

    return {
      protocol,
      host,
      ports,
      defaultPort: Number(options.defaultPort) || resolvedPoolConfig.defaultPort || ports[0] || 0,
      targetLatencyMs: Number(options.targetLatencyMs) || DEFAULT_TARGET_LATENCY_MS,
      healthCheckIntervalMs: Number(options.healthCheckIntervalMs)
        || resolvedPoolConfig.healthCheckIntervalMs
        || 30000,
      tcpTimeoutMs: Number(options.tcpTimeoutMs) || 1500,
      httpTimeoutMs: Number(options.httpTimeoutMs) || 4000,
      heartbeatUrl: String(options.heartbeatUrl || process.env.PROXY_HEARTBEAT_URL || DEFAULT_HEARTBEAT_URL),
      healthProbeMode: normalizeHealthProbeMode(
        options.healthProbeMode || process.env.PROXY_HEALTH_PROBE_MODE || resolvedPoolConfig.healthProbeMode
      ),
      rateLimitIsolationMs: positiveNumber(
        options.rateLimitIsolationMs,
        positiveNumber(resolvedPoolConfig.rateLimitIsolationMs, 300000)
      ),
      failureCooldownMs: positiveNumber(
        options.failureCooldownMs,
        positiveNumber(resolvedPoolConfig.failureCooldownMs, DEFAULT_FAILURE_COOLDOWN_MS)
      ),
      http503CooldownMs: positiveNumber(
        options.http503CooldownMs,
        positiveNumber(resolvedPoolConfig.http503CooldownMs, DEFAULT_HTTP_503_COOLDOWN_MS)
      ),
      criticalErrorCooldownMs: positiveNumber(
        options.criticalErrorCooldownMs,
        positiveNumber(resolvedPoolConfig.criticalErrorCooldownMs, DEFAULT_CRITICAL_ERROR_COOLDOWN_MS)
      ),
      transientContextCooldownMs: positiveNumber(
        options.transientContextCooldownMs,
        DEFAULT_TRANSIENT_CONTEXT_COOLDOWN_MS
      ),
      upstreamBlockBaseCooldownMs: positiveNumber(
        options.upstreamBlockBaseCooldownMs,
        DEFAULT_UPSTREAM_BLOCK_BASE_COOLDOWN_MS
      ),
      upstreamBlockMaxCooldownMs: positiveNumber(
        options.upstreamBlockMaxCooldownMs,
        DEFAULT_UPSTREAM_BLOCK_MAX_COOLDOWN_MS
      ),
      heartbeatFailureCooldownMs: positiveNumber(
        options.heartbeatFailureCooldownMs,
        positiveNumber(resolvedPoolConfig.heartbeatFailureCooldownMs, DEFAULT_HEARTBEAT_FAILURE_COOLDOWN_MS)
      ),
      failureThreshold,
      minHealthScore: clamp(
        Number(options.minHealthScore) || resolvedPoolConfig.minHealthScore || DEFAULT_MIN_HEALTH_SCORE,
        1,
        100
      ),
      successHealthReward: clamp(
        Number(options.successHealthReward) || DEFAULT_SUCCESS_HEALTH_REWARD,
        1,
        20
      ),
      http503ObservationThreshold,
      successEwmaAlpha: Number(options.successEwmaAlpha) || 0.25,
      latencyEwmaAlpha: Number(options.latencyEwmaAlpha) || 0.2,
      baseWeight: Number(options.baseWeight) || 1
    };
  }

  _createNode(port) {
    const server = `${this.config.protocol}://${this.config.host}:${port}`;
    return {
      port,
      host: this.config.host,
      server,
      url: server,
      baseWeight: this.config.baseWeight,
      leaseCount: 0,
      totalLeases: 0,
      totalRequests: 0,
      successCount: 0,
      failureCount: 0,
      successRateEwma: DEFAULT_SUCCESS_RATE,
      latencyEwmaMs: this.config.targetLatencyMs,
      probeHealthy: true,
      lastHeartbeatAt: 0,
      lastUsedAt: 0,
      lastStatusCode: null,
      lastError: null,
      lastConsumer: null,
      consecutiveFailures: 0,
      healthScore: 100,
      cooldownUntil: 0,
      isolatedUntil: 0
    };
  }

  static resolveHost() {
    return resolveProxyPoolConfig().host;
  }

  static resolvePorts() {
    return [...resolveProxyPoolConfig().ports];
  }

  static resolveProtocol() {
    return normalizeProxyProtocol(resolveProxyPoolConfig().protocol || DEFAULT_PROTOCOL);
  }

  static buildServer(port, options = {}) {
    return buildProxyServer(port, {
      config: {
        ...resolveProxyPoolConfig(),
        protocol: options.protocol || ProxyProvider.resolveProtocol(),
        host: options.host || ProxyProvider.resolveHost()
      },
      protocol: options.protocol,
      host: options.host,
      serverTemplate: options.serverTemplate
    });
  }

  static buildAssignment(port, options = {}) {
    const host = options.host || ProxyProvider.resolveHost();
    const server = ProxyProvider.buildServer(port, {
      protocol: options.protocol,
      host
    });

    return {
      host,
      port: Number(port),
      server,
      url: server
    };
  }

  getPorts() {
    return [...this.config.ports];
  }

  getHost() {
    return this.config.host;
  }

  getServer(port) {
    return ProxyProvider.buildServer(port, {
      protocol: this.config.protocol,
      host: this.config.host
    });
  }

  buildAssignment(port) {
    return ProxyProvider.buildAssignment(port, {
      protocol: this.config.protocol,
      host: this.config.host
    });
  }

  async initialize() {
    if (this.initialized) {
      return {
        ok: true,
        host: this.config.host,
        port: this._resolvePreflightPort(),
        discoveredPorts: this.config.ports
      };
    }

    if (!this.initializationPromise) {
      const radarMode = String(process.env.PROXY_RADAR_MODE || '').toLowerCase() === 'true';

      if (radarMode && this.config.ports.length === 0) {
        this.initializationPromise = this._runRadarDiscovery()
          .then((result) => {
            this.initialized = true;
            this.start();
            return result;
          })
          .catch((error) => {
            this.initializationPromise = null;
            throw error;
          });
      } else {
        this.initializationPromise = this._runGatewayPreflight()
          .then((result) => {
            this.initialized = true;
            this.start();
            return {
              ...result,
              discoveredPorts: this.config.ports,
              totalDiscovered: this.config.ports.length,
              mode: radarMode ? 'radar_with_static_ports' : 'static_ports_only'
            };
          })
          .catch((error) => {
            this.initializationPromise = null;
            throw error;
          });
      }
    }

    return this.initializationPromise;
  }

  async _runRadarDiscovery() {
    const radarStartPort = Number(process.env.PROXY_RADAR_START_PORT) || 10001;
    const radarEndPort = Number(process.env.PROXY_RADAR_END_PORT) || 10040;
    const radarMaxConsecutiveFailures = Number(process.env.PROXY_RADAR_MAX_FAILURES) || 5;
    const radarTimeoutMs = Number(process.env.PROXY_RADAR_TIMEOUT_MS) || 5000;

    if (typeof this.logger.info === 'function') {
      this.logger.info('[ProxyProvider] 🔍 Titan 7.0 L7 雷达扫描启动 (物理隔离端口)', {
        host: this.config.host,
        portRange: `${radarStartPort}-${radarEndPort}`,
        maxConsecutiveFailures: radarMaxConsecutiveFailures,
        mode: 'L7_SOCKS5_VALIDATION'
      });
    }

    const discoveredPorts = [];
    const ghostPorts = [];
    let consecutiveFailures = 0;
    let currentPort = radarStartPort;
    const maxScans = radarEndPort - radarStartPort + 1;
    let scannedCount = 0;

    while (consecutiveFailures < radarMaxConsecutiveFailures && scannedCount < maxScans && currentPort <= radarEndPort) {
      const probeResult = await this._probeL7Proxy(
        { port: currentPort, host: this.config.host },
        { ...this.config, httpTimeoutMs: radarTimeoutMs }
      );

      if (probeResult?.ok && probeResult?.validProxy) {
        discoveredPorts.push(currentPort);
        consecutiveFailures = 0;
        if (typeof this.logger.debug === 'function') {
          this.logger.debug('[ProxyProvider] ✓ L7 验证通过', {
            port: currentPort,
            latencyMs: probeResult.latencyMs,
            remoteIp: probeResult.remoteIp
          });
        }
      } else {
        consecutiveFailures += 1;
        if (probeResult?.ghostPort) {
          ghostPorts.push(currentPort);
        }
      }

      currentPort += 1;
      scannedCount += 1;
    }

    if (discoveredPorts.length === 0) {
      const error = new Error(
        `PROXY_RADAR_NO_NODES: L7 雷达扫描未发现任何真实代理节点 (扫描范围: ${radarStartPort}-${currentPort - 1}, 幽灵端口: ${ghostPorts.length})`
      );
      error.code = 'PROXY_RADAR_NO_NODES';
      error.scannedRange = { start: radarStartPort, end: currentPort - 1 };
      error.ghostPorts = ghostPorts;
      throw error;
    }

    this.config.ports = discoveredPorts;
    this.nodes = discoveredPorts.map(port => this._createNode(port));
    this.nodeByPort = new Map(this.nodes.map(node => [node.port, node]));

    if (typeof this.logger.info === 'function') {
      this.logger.info('[ProxyProvider] 🎯 L7 雷达扫描完成', {
        discoveredCount: discoveredPorts.length,
        ghostPortsFiltered: ghostPorts.length,
        portRange: discoveredPorts.length > 0
          ? `${discoveredPorts[0]}-${discoveredPorts[discoveredPorts.length - 1]}`
          : 'N/A',
        ports: discoveredPorts
      });
    }

    return {
      ok: true,
      host: this.config.host,
      discoveredPorts,
      totalDiscovered: discoveredPorts.length,
      ghostPortsFiltered: ghostPorts.length,
      scannedRange: { start: radarStartPort, end: currentPort - 1 }
    };
  }

  _probeL7Proxy(node, config) {
    return new Promise(resolve => {
      const startedAt = this.now();
      const proxyProtocol = normalizeProxyProtocol(config.protocol || process.env.PROXY_PROTOCOL || DEFAULT_PROTOCOL);
      const proxyUrl = `${proxyProtocol}://${node.host}:${node.port}`;
      const agent = createProxyAgent(proxyUrl, proxyProtocol, 'http:', config.httpTimeoutMs);

      const request = http.request({
        hostname: 'httpbin.org',
        port: 80,
        path: '/ip',
        method: 'GET',
        timeout: config.httpTimeoutMs,
        agent,
        headers: {
          'User-Agent': 'ProxyRadar/7.0',
          'Accept': 'application/json'
        }
      }, response => {
        let body = '';
        response.on('data', chunk => {
          body += chunk.toString();
          if (body.length > 10000) {
            request.destroy(new Error('response_too_large'));
          }
        });

        response.on('end', () => {
          const latencyMs = this.now() - startedAt;
          const statusCode = Number(response.statusCode);

          if (statusCode === 200) {
            try {
              const data = JSON.parse(body);
              const remoteIp = data?.origin || null;

              if (remoteIp && /^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/.test(remoteIp)) {
                resolve({
                  ok: true,
                  validProxy: true,
                  latencyMs,
                  statusCode,
                  remoteIp
                });
                return;
              }
            } catch {
              // JSON 解析失败
            }
          }

          resolve({
            ok: false,
            validProxy: false,
            ghostPort: statusCode >= 200 && statusCode < 500,
            latencyMs,
            statusCode,
            error: `invalid_response_status_${statusCode}`
          });
        });
      });

      request.once('timeout', () => {
        request.destroy(new Error('http_timeout'));
      });

      request.once('error', error => {
        const latencyMs = this.now() - startedAt;
        const errorMessage = String(error.message || '').toLowerCase();

        const isGhostPort = errorMessage.includes('aborted')
          || errorMessage.includes('econnreset')
          || errorMessage.includes('socket hang up');

        resolve({
          ok: false,
          validProxy: false,
          ghostPort: isGhostPort,
          latencyMs,
          error: error.message
        });
      });

      request.end();
    });
  }

  start() {
    if (this.started || this.config.healthCheckIntervalMs <= 0) {
      return this;
    }

    this.started = true;
    this.healthTimer = setInterval(() => {
      void this.runHealthCheck();
    }, this.config.healthCheckIntervalMs);

    if (typeof this.healthTimer.unref === 'function') {
      this.healthTimer.unref();
    }

    return this;
  }

  _resolvePreflightPort() {
    const preferredPort = Number(this.config.defaultPort);
    if (Number.isInteger(preferredPort) && preferredPort > 0) {
      return preferredPort;
    }

    return this.config.ports[0] || 0;
  }

  async _runGatewayPreflight() {
    const port = this._resolvePreflightPort();
    if (!Number.isInteger(port) || port <= 0) {
      return {
        ok: true,
        skipped: true,
        host: this.config.host,
        port: 0
      };
    }

    const result = await this.probes.tcp({
      port,
      host: this.config.host
    }, {
      ...this.config,
      tcpTimeoutMs: positiveNumber(this.config.tcpTimeoutMs, DEFAULT_GATEWAY_PREFLIGHT_TIMEOUT_MS)
    });

    if (result?.ok) {
      if (typeof this.logger.info === 'function') {
        this.logger.info('[ProxyProvider] gateway_preflight_passed', {
          host: this.config.host,
          port,
          latencyMs: result.latencyMs
        });
      }

      return {
        ok: true,
        host: this.config.host,
        port,
        latencyMs: result.latencyMs
      };
    }

    const reason = String(result?.error || 'tcp_preflight_failed');
    const error = new Error(this._buildGatewayPreflightErrorMessage(port, reason));
    error.code = 'PROXY_GATEWAY_UNREACHABLE';
    error.host = this.config.host;
    error.port = port;
    error.reason = reason;

    if (typeof this.logger.warn === 'function') {
      this.logger.warn('[ProxyProvider] gateway_preflight_failed', {
        host: this.config.host,
        port,
        reason
      });
    }

    throw error;
  }

  _buildGatewayPreflightErrorMessage(port, reason) {
    const hostHint = this.config.host === '127.0.0.1'
      ? '请检查 127.0.0.1 在 WSL2 Mirrored 模式下是否可达'
      : `请检查 ${this.config.host} 是否可达`;

    return `PROXY_GATEWAY_UNREACHABLE: ${this.config.host}:${port} (${reason}). ${hostHint}，或通过 PROXY_HOST 指定正确的宿主机地址`;
  }

  stop() {
    if (this.healthTimer) {
      clearInterval(this.healthTimer);
      this.healthTimer = null;
    }

    this.started = false;
  }

  acquireSync(options = {}) {
    const consumer = String(options.consumer || '').trim();
    if (!consumer) {
      throw new Error('ProxyProvider.acquire requires consumer');
    }

    this.start();

    const sticky = options.sticky !== false;
    const sessionKey = options.sessionKey ? `${consumer}:${String(options.sessionKey)}` : null;
    if (sticky && sessionKey) {
      const existingLeaseId = this.stickyLeases.get(sessionKey);
      if (existingLeaseId && this.leases.has(existingLeaseId)) {
        const existing = this.leases.get(existingLeaseId);
        existing.refCount += 1;
        existing.lastUsedAt = this.now();
        return this._cloneLease(existing);
      }
    }

    const node = this._selectNode({
      preferredPort: options.preferredPort,
      excludePorts: options.excludePorts,
      minHealthScore: options.minHealthScore
    });

    if (!node) {
      throw new Error('NO_AVAILABLE_PROXY: no healthy proxy node is available');
    }

    const lease = {
      id: `LEASE-${++this.sequence}`,
      consumer,
      sessionKey,
      sticky,
      refCount: 1,
      createdAt: this.now(),
      lastUsedAt: this.now(),
      proxy: {
        host: node.host,
        port: node.port,
        server: node.server,
        url: node.url
      },
      metadata: { ...(options.metadata || {}) }
    };

    this.leases.set(lease.id, lease);
    if (sticky && sessionKey) {
      this.stickyLeases.set(sessionKey, lease.id);
    }

    node.leaseCount += 1;
    node.totalLeases += 1;
    node.lastUsedAt = this.now();
    node.lastConsumer = consumer;

    return this._cloneLease(lease);
  }

  async acquire(options = {}) {
    return this.acquireSync(options);
  }

  releaseSync(leaseOrId) {
    const lease = this._resolveLease(leaseOrId);
    if (!lease) {
      return false;
    }

    if (lease.refCount > 1) {
      lease.refCount -= 1;
      return true;
    }

    const node = this.nodeByPort.get(lease.proxy.port);
    if (node) {
      node.leaseCount = Math.max(0, node.leaseCount - 1);
    }

    if (lease.sessionKey) {
      this.stickyLeases.delete(lease.sessionKey);
    }

    this.leases.delete(lease.id);
    return true;
  }

  async release(leaseOrId) {
    return this.releaseSync(leaseOrId);
  }

  async reportSuccess(leaseOrId, metadata = {}) {
    const lease = this._resolveLease(leaseOrId);
    const node = this._resolveNode(lease, metadata);
    if (!node) {
      return false;
    }

    const latencyMs = Number(metadata.latencyMs);
    node.totalRequests += 1;
    node.successCount += 1;
    node.lastStatusCode = Number(metadata.statusCode) || 200;
    node.lastError = null;
    node.consecutiveFailures = 0;
    node.probeHealthy = true;
    node.healthScore = clamp(
      node.healthScore + this.config.successHealthReward,
      0,
      100
    );
    node.successRateEwma = ewma(
      node.successRateEwma,
      1,
      this.config.successEwmaAlpha
    );

    if (Number.isFinite(latencyMs) && latencyMs > 0) {
      node.latencyEwmaMs = ewma(
        node.latencyEwmaMs,
        latencyMs,
        this.config.latencyEwmaAlpha
      );
    }

    return true;
  }

  async reportFailure(leaseOrId, metadata = {}) {
    const lease = this._resolveLease(leaseOrId);
    const node = this._resolveNode(lease, metadata);
    if (!node) {
      return false;
    }

    const statusCode = Number(metadata.statusCode) || extractStatusCode(metadata.reason);
    const reason = String(metadata.reason || metadata.error || 'unknown');
    const failureClass = normalizeFailureClass(metadata.failureClass, statusCode, reason);
    const now = this.now();

    node.totalRequests += 1;
    node.failureCount += 1;
    node.consecutiveFailures += 1;
    node.lastStatusCode = statusCode || null;
    node.lastError = reason;
    node.healthScore = clamp(
      node.healthScore - resolveHealthPenalty(statusCode, reason, failureClass),
      0,
      100
    );

    if (failureClass === 'browser_context_transient' || failureClass === 'upstream_block') {
      node.healthScore = Math.max(node.healthScore, this.config.minHealthScore);
    }

    node.successRateEwma = ewma(
      node.successRateEwma,
      0,
      this.config.successEwmaAlpha
    );

    if (statusCode === 429) {
      const cooldownMs = this._resolveFailureCooldownMs(statusCode, failureClass);
      node.isolatedUntil = now + cooldownMs;
      node.cooldownUntil = Math.max(node.cooldownUntil, now + cooldownMs);
      this._emitAlert('rate_limit_isolation', node, {
        statusCode,
        reason,
        isolatedUntil: node.isolatedUntil,
        cooldownUntil: node.cooldownUntil,
        cooldownMs
      });
      this._emitAlert('proxy_cooled_down', node, {
        statusCode,
        reason,
        cooldownUntil: node.cooldownUntil,
        cooldownMs,
        consecutiveFailures: node.consecutiveFailures
      });
      if (node.healthScore < this.config.minHealthScore) {
        this._emitAlert('proxy_health_score_blocked', node, {
          statusCode,
          reason,
          healthScore: node.healthScore,
          minHealthScore: this.config.minHealthScore
        });
      }
      return true;
    }

    if (failureClass === 'browser_context_transient' || failureClass === 'upstream_block') {
      const cooldownMs = this._resolveSoftFailureCooldownMs(failureClass, node);
      if (cooldownMs > 0) {
        node.cooldownUntil = now + cooldownMs;
        this._emitAlert('proxy_soft_backoff', node, {
          statusCode,
          reason,
          failureClass,
          cooldownUntil: node.cooldownUntil,
          cooldownMs,
          consecutiveFailures: node.consecutiveFailures
        });
      }

      return true;
    }

    if (
      statusCode === 503
      && node.consecutiveFailures < this.config.http503ObservationThreshold
    ) {
      this._emitAlert('proxy_under_observation', node, {
        statusCode,
        reason,
        consecutiveFailures: node.consecutiveFailures,
        observationThreshold: this.config.http503ObservationThreshold
      });
      return true;
    }

    if (this._shouldCooldownNode(statusCode, node, failureClass)) {
      const cooldownMs = this._resolveFailureCooldownMs(statusCode, failureClass);
      node.cooldownUntil = now + cooldownMs;
      this._emitAlert('proxy_cooled_down', node, {
        statusCode,
        reason,
        cooldownUntil: node.cooldownUntil,
        cooldownMs,
        consecutiveFailures: node.consecutiveFailures
      });
    }

    if (node.healthScore < this.config.minHealthScore) {
      this._emitAlert('proxy_health_score_blocked', node, {
        statusCode,
        reason,
        healthScore: node.healthScore,
        minHealthScore: this.config.minHealthScore
      });
    }

    return true;
  }

  _shouldCooldownNode(statusCode, node, failureClass = 'hard_proxy_failure') {
    if (failureClass === 'browser_context_transient' || failureClass === 'upstream_block') {
      return false;
    }
    if (statusCode === 403) {
      return true;
    }
    if (statusCode === 503) {
      return node.consecutiveFailures >= this.config.http503ObservationThreshold;
    }
    if (statusCode >= 500) {
      return true;
    }
    return node.consecutiveFailures >= this.config.failureThreshold;
  }

  _resolveFailureCooldownMs(statusCode, failureClass = 'hard_proxy_failure') {
    if (failureClass === 'browser_context_transient' || failureClass === 'upstream_block') {
      return this._resolveSoftFailureCooldownMs(failureClass, { consecutiveFailures: 1 });
    }
    if (statusCode === 403) {
      return this.config.criticalErrorCooldownMs;
    }
    if (statusCode === 429) {
      return this.config.rateLimitIsolationMs;
    }
    return statusCode === 503
      ? this.config.http503CooldownMs
      : this.config.failureCooldownMs;
  }

  _resolveSoftFailureCooldownMs(failureClass, node) {
    if (failureClass === 'browser_context_transient') {
      return Math.min(
        this.config.upstreamBlockMaxCooldownMs,
        this.config.transientContextCooldownMs * Math.max(1, Number(node?.consecutiveFailures) || 1)
      );
    }

    if (failureClass === 'upstream_block') {
      const exponent = Math.max(0, (Number(node?.consecutiveFailures) || 1) - 1);
      return Math.min(
        this.config.upstreamBlockMaxCooldownMs,
        this.config.upstreamBlockBaseCooldownMs * (2 ** exponent)
      );
    }

    return 0;
  }

  getStats() {
    const now = this.now();
    const healthy = this.nodes.filter(node => (
      node.probeHealthy
      && node.healthScore >= this.config.minHealthScore
    )).length;
    const isolated = this.nodes.filter(node => node.isolatedUntil > now).length;
    const cooling = this.nodes.filter(node => node.cooldownUntil > now).length;
    const available = this.nodes.filter(node => this._isNodeAvailable(node, now)).length;

    return {
      host: this.config.host,
      total: this.nodes.length,
      healthy,
      isolated,
      cooling,
      available,
      activeLeases: this.leases.size
    };
  }

  getNodeStates() {
    const now = this.now();
    return this.nodes.map(node => ({
      port: node.port,
      host: node.host,
      server: node.server,
      leaseCount: node.leaseCount,
      successRateEwma: Number(node.successRateEwma.toFixed(4)),
      latencyEwmaMs: Math.round(node.latencyEwmaMs),
      healthScore: Number(node.healthScore.toFixed(1)),
      probeHealthy: node.probeHealthy,
      isolated: node.isolatedUntil > now,
      cooling: node.cooldownUntil > now,
      eligibleForLease: this._isNodeAvailable(node, now),
      dynamicWeight: Number(this._computeDynamicWeight(node).toFixed(4)),
      successCount: node.successCount,
      failureCount: node.failureCount,
      totalRequests: node.totalRequests,
      totalLeases: node.totalLeases,
      consecutiveFailures: node.consecutiveFailures,
      lastStatusCode: node.lastStatusCode,
      lastError: node.lastError,
      lastUsedAt: node.lastUsedAt
    }));
  }

  toPlaywrightProxy(leaseOrId) {
    const lease = this._resolveLease(leaseOrId);
    if (!lease) {
      return null;
    }

    return { server: lease.proxy.server };
  }

  async acquireAssignment(options = {}) {
    const lease = await this.acquire(options);
    return {
      lease,
      assignment: {
        host: lease.proxy.host,
        port: lease.proxy.port,
        url: lease.proxy.url,
        server: lease.proxy.server,
        sessionId: lease.id
      }
    };
  }

  acquireAssignmentSync(options = {}) {
    const lease = this.acquireSync(options);
    return {
      lease,
      assignment: {
        host: lease.proxy.host,
        port: lease.proxy.port,
        url: lease.proxy.url,
        server: lease.proxy.server,
        sessionId: lease.id
      }
    };
  }

  async reportPortSuccess(port, metadata = {}) {
    return this.reportSuccess(null, { ...metadata, port });
  }

  async reportPortFailure(port, metadata = {}) {
    return this.reportFailure(null, { ...metadata, port });
  }

  async runHealthCheck() {
    const results = await Promise.allSettled(
      this.nodes.map(node => this._checkNodeHealth(node))
    );

    const summary = {
      checked: this.nodes.length,
      healthy: 0,
      unhealthy: 0
    };

    results.forEach(result => {
      if (result.status === 'fulfilled' && result.value?.ok) {
        summary.healthy += 1;
      } else {
        summary.unhealthy += 1;
      }
    });

    return summary;
  }

  resetPort(port) {
    const node = this.nodeByPort.get(Number(port));
    if (!node) {
      return false;
    }

    node.failureCount = 0;
    node.successCount = 0;
    node.totalRequests = 0;
    node.consecutiveFailures = 0;
    node.lastStatusCode = null;
    node.lastError = null;
    node.cooldownUntil = 0;
    node.isolatedUntil = 0;
    node.probeHealthy = true;
    node.healthScore = 100;
    node.successRateEwma = DEFAULT_SUCCESS_RATE;
    node.latencyEwmaMs = this.config.targetLatencyMs;
    return true;
  }

  resetAll() {
    this.nodes.forEach(node => {
      this.resetPort(node.port);
    });
    return true;
  }

  _resolveLease(leaseOrId) {
    if (!leaseOrId) {
      return null;
    }

    if (typeof leaseOrId === 'string') {
      return this.leases.get(leaseOrId) || null;
    }

    if (typeof leaseOrId === 'object' && leaseOrId.id) {
      return this.leases.get(leaseOrId.id) || null;
    }

    return null;
  }

  _resolveNode(lease, metadata = {}) {
    if (lease?.proxy?.port) {
      return this.nodeByPort.get(lease.proxy.port) || null;
    }

    if (metadata.port) {
      return this.nodeByPort.get(Number(metadata.port)) || null;
    }

    return null;
  }

  _cloneLease(lease) {
    return {
      ...lease,
      proxy: { ...lease.proxy },
      metadata: { ...(lease.metadata || {}) }
    };
  }

  _isNodeAvailable(node, now = this.now(), minHealthScore = this.config.minHealthScore) {
    return node.probeHealthy
      && node.isolatedUntil <= now
      && node.cooldownUntil <= now
      && node.healthScore >= minHealthScore;
  }

  _computeDynamicWeight(node) {
    const successWeight = clamp(node.successRateEwma, 0.1, 1.5);
    const latencyWeight = clamp(
      this.config.targetLatencyMs / Math.max(node.latencyEwmaMs, 1),
      0.25,
      2.5
    );
    const healthWeight = node.probeHealthy ? 1 : 0.1;

    return node.baseWeight * successWeight * latencyWeight * healthWeight;
  }

  _selectNode(options = {}) {
    const now = this.now();
    const exclude = new Set((options.excludePorts || []).map(Number));
    const preferredPort = Number(options.preferredPort);
    const minHealthScore = clamp(
      Number(options.minHealthScore) || this.config.minHealthScore,
      1,
      100
    );

    if (Number.isFinite(preferredPort)) {
      const preferred = this.nodeByPort.get(preferredPort);
      if (preferred && !exclude.has(preferred.port) && this._isNodeAvailable(preferred, now, minHealthScore)) {
        return preferred;
      }
    }

    const candidates = this.nodes
      .filter(node => !exclude.has(node.port))
      .filter(node => this._isNodeAvailable(node, now, minHealthScore))
      .sort((left, right) => {
        const leftScore = (left.leaseCount + 1) / this._computeDynamicWeight(left);
        const rightScore = (right.leaseCount + 1) / this._computeDynamicWeight(right);

        if (leftScore !== rightScore) {
          return leftScore - rightScore;
        }

        if (left.successRateEwma !== right.successRateEwma) {
          return right.successRateEwma - left.successRateEwma;
        }

        if (left.latencyEwmaMs !== right.latencyEwmaMs) {
          return left.latencyEwmaMs - right.latencyEwmaMs;
        }

        if (left.lastUsedAt !== right.lastUsedAt) {
          return left.lastUsedAt - right.lastUsedAt;
        }

        return left.port - right.port;
      });

    return candidates[0] || null;
  }

  async _checkNodeHealth(node) {
    const now = this.now();
    const tcpResult = await this.probes.tcp(node, this.config);
    node.lastHeartbeatAt = now;
    if (!tcpResult?.ok) {
      node.probeHealthy = false;
      node.lastError = tcpResult?.error || 'tcp_failed';
      node.healthScore = clamp(
        node.healthScore - resolveHealthPenalty(null, tcpResult?.error || 'tcp_failed'),
        0,
        100
      );
      node.cooldownUntil = Math.max(node.cooldownUntil, now + this.config.heartbeatFailureCooldownMs);
      return { ok: false, port: node.port, stage: 'tcp' };
    }

    const tcpLatencyMs = Number(tcpResult?.latencyMs);
    if (this.config.healthProbeMode === 'tcp_only') {
      return this._markNodeHealthyFromHeartbeat(node, {
        latencyMs: tcpLatencyMs,
        statusCode: 200,
        stage: 'tcp'
      });
    }

    const httpResult = await this.probes.http(node, this.config);
    if (!httpResult?.ok) {
      if (this.config.healthProbeMode === 'tcp_authoritative') {
        return this._markNodeHealthyFromHeartbeat(node, {
          latencyMs: tcpLatencyMs,
          statusCode: Number(httpResult?.statusCode) || 200,
          stage: 'tcp_authoritative',
          degradedReason: httpResult?.error || null
        });
      }

      node.probeHealthy = false;
      node.lastError = httpResult?.error || 'http_failed';
      node.healthScore = clamp(
        node.healthScore - resolveHealthPenalty(Number(httpResult?.statusCode) || null, httpResult?.error || 'http_failed'),
        0,
        100
      );
      if (Number(httpResult?.statusCode) === 429) {
        node.isolatedUntil = now + this.config.rateLimitIsolationMs;
      } else {
        node.cooldownUntil = Math.max(node.cooldownUntil, now + this.config.heartbeatFailureCooldownMs);
      }
      return { ok: false, port: node.port, stage: 'http' };
    }

    return this._markNodeHealthyFromHeartbeat(node, {
      latencyMs: Number(httpResult?.latencyMs),
      statusCode: Number(httpResult?.statusCode) || 200,
      stage: 'http'
    });
  }

  _markNodeHealthyFromHeartbeat(node, details = {}) {
    node.probeHealthy = true;
    node.lastError = details.degradedReason ? `heartbeat_degraded:${details.degradedReason}` : null;
    node.lastStatusCode = Number(details.statusCode) || 200;
    node.healthScore = clamp(
      node.healthScore + 1,
      0,
      100
    );
    node.successRateEwma = ewma(
      node.successRateEwma,
      1,
      this.config.successEwmaAlpha
    );

    if (Number.isFinite(details.latencyMs) && details.latencyMs > 0) {
      node.latencyEwmaMs = ewma(
        node.latencyEwmaMs,
        details.latencyMs,
        this.config.latencyEwmaAlpha
      );
    }

    return {
      ok: true,
      port: node.port,
      stage: details.stage || 'http',
      degraded: Boolean(details.degradedReason)
    };
  }

  _probeTcp(node, config) {
    return new Promise(resolve => {
      const socket = new net.Socket();
      let settled = false;
      const startedAt = this.now();

      const finish = (ok, error = null) => {
        if (settled) {
          return;
        }
        settled = true;
        socket.destroy();
        resolve({
          ok,
          error,
          latencyMs: this.now() - startedAt
        });
      };

      socket.setTimeout(config.tcpTimeoutMs);
      socket.once('connect', () => finish(true));
      socket.once('timeout', () => finish(false, 'tcp_timeout'));
      socket.once('error', error => finish(false, error.message));
      socket.connect(node.port, node.host);
    });
  }

  _probeHttp(node, config) {
    return new Promise(resolve => {
      const startedAt = this.now();
      const target = new URL(config.heartbeatUrl);
      const requestLib = target.protocol === 'https:' ? https : http;
      const agent = createProxyAgent(
        node.server,
        config.protocol,
        target.protocol,
        config.httpTimeoutMs
      );

      const request = requestLib.request({
        hostname: target.hostname,
        port: target.port || (target.protocol === 'https:' ? 443 : 80),
        path: `${target.pathname}${target.search}`,
        method: 'HEAD',
        timeout: config.httpTimeoutMs,
        agent,
        headers: {
          'User-Agent': 'ProxyProvider/1.0',
          'Accept': '*/*'
        }
      }, response => {
        response.resume();
        const latencyMs = this.now() - startedAt;
        const ok = Number(response.statusCode) >= 200 && Number(response.statusCode) < 500;
        resolve({
          ok,
          latencyMs,
          statusCode: response.statusCode,
          error: ok ? null : `HTTP_${response.statusCode}`
        });
      });

      request.once('timeout', () => {
        request.destroy(new Error('http_timeout'));
      });

      request.once('error', error => {
        resolve({ ok: false, latencyMs: this.now() - startedAt, error: error.message });
      });

      request.end();
    });
  }

  _emitAlert(type, node, details = {}) {
    const payload = {
      type,
      port: node.port,
      host: node.host,
      server: node.server,
      timestamp: new Date(this.now()).toISOString(),
      ...details
    };

    if (typeof this.logger.warn === 'function') {
      this.logger.warn(`[ProxyProvider] ${type}`, payload);
    }

    this.emit('alert', payload);
  }
}

let singleton = null;

function getProxyProvider(options = {}) {
  if (!singleton) {
    singleton = new ProxyProvider(options);
  }

  return singleton;
}

function resetProxyProvider() {
  if (singleton) {
    singleton.stop();
    singleton.removeAllListeners();
  }

  singleton = null;
}

module.exports = {
  ProxyProvider,
  getProxyProvider,
  resetProxyProvider
};
