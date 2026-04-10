'use strict';

const DEFAULT_PROBE_TIMEOUT_MS = 20000;
const DEFAULT_TIMEOUT_DEGRADE_THRESHOLD = 2;
const SEARCH_BLOCKING_DEGRADED_ROUTES = new Set(['results', 'fixtures']);

function buildProbeFailureResolution(signals, timeoutStreak, timeoutThreshold) {
  const shouldDegrade = signals.has503 || timeoutStreak >= timeoutThreshold;
  return {
    shouldDegrade,
    sourceState: signals.has503
      ? 'ROUTE_DEGRADED_503_FAST_FAIL'
      : 'ROUTE_DEGRADED_TIMEOUT_FAST_FAIL',
    reason: signals.has503 ? 'HTTP_503' : 'TIMEOUT_STREAK'
  };
}

const reconRouteDegradePolicy = {
  _buildEmptyRouteSource(routeKind, target, sourceState = 'SOURCE_EMPTY') {
    return {
      routeKind,
      source: {
        season: target?.dbSeason || null,
        url: ''
      },
      extractResult: {
        matches: [],
        pagesScanned: 0,
        totalCandidates: 0,
        sourceState
      },
      candidates: [],
      seasonMirror: new Map(),
      sampleLinked: 0
    };
  },

  _resetRouteDegradeRegistry() {
    this.routeDegradeRegistry = new Map();
  },

  _getRouteDegradeRegistry() {
    if (!(this.routeDegradeRegistry instanceof Map)) {
      this.routeDegradeRegistry = new Map();
    }

    return this.routeDegradeRegistry;
  },

  _buildRouteDegradeKey(target) {
    return [
      String(target?.leagueId ?? target?.league?.id ?? target?.league?.name ?? 'unknown'),
      String(target?.dbSeason || target?.season || 'unknown')
    ].join('::');
  },

  _getRouteDegradeState(target) {
    const registry = this._getRouteDegradeRegistry();
    const key = this._buildRouteDegradeKey(target);
    if (!registry.has(key)) {
      registry.set(key, {
        degradedRoutes: new Set(),
        timeoutStreaks: Object.create(null),
        searchBlocked: false,
        lastReason: null
      });
    }

    return registry.get(key);
  },

  _resetRouteFailureStreak(target, routeKind) {
    const state = this._getRouteDegradeState(target);
    state.timeoutStreaks[routeKind] = 0;
    return state;
  },

  _is503ProbeFailure(statusCode, message) {
    return statusCode === 503
      || message.includes('http_503')
      || message.includes('503')
      || message.includes('service unavailable');
  },

  _isTimeoutProbeFailure(message) {
    return message.includes('timeout')
      || message.includes('timed out')
      || message.includes('page.goto')
      || message.includes('aborted');
  },

  _extractProbeFailureSignals(error) {
    const items = [
      error,
      ...(Array.isArray(error?.sourceFailures) ? error.sourceFailures : [])
    ];
    let has503 = false;
    let timeoutHits = 0;

    for (const item of items) {
      const statusCode = Number(item?.statusCode || item?.cause?.statusCode || 0) || null;
      const message = String(item?.message || item?.error || '').toLowerCase();

      has503 = has503 || this._is503ProbeFailure(statusCode, message);
      timeoutHits += this._isTimeoutProbeFailure(message) ? 1 : 0;
    }

    return {
      has503,
      hasTimeout: timeoutHits > 0,
      timeoutHits
    };
  },

  _resolveRouteProbeTimeoutMs(_routeKind, _target = null) {
    const configuredProbeTimeout = Number(this.probeArchiveTimeoutMs);
    const hasExplicitProbeTimeout = Number.isFinite(configuredProbeTimeout) && configuredProbeTimeout > 0;
    const archiveTimeout = Math.max(
      1,
      Number(this.archiveTimeoutMs || DEFAULT_PROBE_TIMEOUT_MS)
    );

    if (!hasExplicitProbeTimeout) {
      return archiveTimeout;
    }

    return Math.min(archiveTimeout, configuredProbeTimeout);
  },

  _updateRouteTimeoutStreak(state, routeKind, signals) {
    state.timeoutStreaks[routeKind] = signals.hasTimeout
      ? Number(state.timeoutStreaks[routeKind] || 0) + Math.max(1, signals.timeoutHits)
      : 0;

    return Number(state.timeoutStreaks[routeKind] || 0);
  },

  _applyRouteDegradeState(state, routeKind, resolution) {
    if (resolution.shouldDegrade !== true) {
      return;
    }

    state.degradedRoutes.add(routeKind);
    state.searchBlocked = state.searchBlocked || SEARCH_BLOCKING_DEGRADED_ROUTES.has(routeKind);
    state.lastReason = resolution.reason;
  },

  _logRouteDegrade(target, routeKind, state, timeoutStreak, timeoutThreshold, metadata = {}, error = null) {
    this.logger.warn('recon_route_degraded', {
      league: target?.league?.name || null,
      season: target?.dbSeason || null,
      routeKind,
      reason: state.lastReason,
      timeoutStreak,
      timeoutThreshold,
      timeoutMs: Number(metadata.timeoutMs || 0) || null,
      searchBlocked: state.searchBlocked === true,
      error: error?.message || null
    });
  },

  _recordRouteProbeFailure(target, routeKind, error, metadata = {}) {
    const state = this._getRouteDegradeState(target);
    const signals = this._extractProbeFailureSignals(error);
    const timeoutThreshold = Math.max(
      1,
      Number(this.fastFailTimeoutStreak || DEFAULT_TIMEOUT_DEGRADE_THRESHOLD)
    );
    const timeoutStreak = this._updateRouteTimeoutStreak(state, routeKind, signals);
    const resolution = buildProbeFailureResolution(signals, timeoutStreak, timeoutThreshold);

    this._applyRouteDegradeState(state, routeKind, resolution);
    if (resolution.shouldDegrade) {
      this._logRouteDegrade(target, routeKind, state, timeoutStreak, timeoutThreshold, metadata, error);
    }

    return {
      shouldDegrade: resolution.shouldDegrade,
      searchBlocked: state.searchBlocked === true,
      timeoutStreak,
      signals,
      sourceState: resolution.sourceState
    };
  },

  _isSearchProbeBlocked(target) {
    if (this.searchDisabledOnDegradedLeague !== true) {
      return false;
    }

    const state = this._getRouteDegradeState(target);
    return state.searchBlocked === true || state.degradedRoutes.size > 0;
  },

  _buildDegradedRouteSource(routeKind, target, sourceState, error = null, metadata = {}) {
    this.logger.warn('recon_route_fast_fail', {
      league: target?.league?.name || null,
      season: target?.dbSeason || null,
      routeKind,
      sourceState,
      timeoutMs: Number(metadata.timeoutMs || 0) || null,
      searchBlocked: metadata.searchBlocked === true,
      error: error?.message || null
    });
    return this._buildEmptyRouteSource(routeKind, target, sourceState);
  }
};

module.exports = { reconRouteDegradePolicy };
