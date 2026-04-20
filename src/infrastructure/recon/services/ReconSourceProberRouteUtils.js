'use strict';

const RESULTS_PROBE_SEARCH_SHORT_CIRCUIT_TIMEOUT_MS = 20000;
const RESULTS_PROBE_SEARCH_SHORT_CIRCUIT_LEAGUES = new Set([
  'j1 league',
  'brasileirao'
]);
const SEARCH_ROUTE_NAVIGATION_FAST_FAIL_TIMEOUT_MS = 20000;
const SEARCH_ROUTE_BIDIRECTIONAL_LEAGUES = new Set([
  'j1 league',
  'brasileirao',
  'copa america',
  'segunda division'
]);

function tokenizeSearchKeyword(value = '') {
  return String(value || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^0-9A-Za-z]+/g, ' ')
    .trim()
    .split(/\s+/)
    .filter(Boolean);
}

function buildFuzzyPrefixKeyword(teamName = '') {
  const tokens = tokenizeSearchKeyword(teamName);
  return tokens.slice(0, 2).join(' ').trim();
}

function buildSearchKeywordSlug(keyword = '') {
  return String(keyword || '')
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

function getCandidateCount(routeSource = null) {
  return Array.isArray(routeSource?.candidates) ? routeSource.candidates.length : 0;
}

function normalizeLeagueName(value = '') {
  return String(value || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .trim()
    .toLowerCase();
}

function isMatrixModePruningEnabled(target = {}) {
  return target?.matrixModePruning === true;
}

function resolveMatrixShortCircuitRatio(target = {}) {
  const rawRatio = Number(target?.matrixModeShortCircuitRatio ?? 0.5);
  if (!Number.isFinite(rawRatio)) {
    return 0.5;
  }

  return Math.min(1, Math.max(0, rawRatio));
}

function resolveSampleLinkedThreshold(sampleTarget, target = {}) {
  if (!Number.isInteger(sampleTarget) || sampleTarget <= 0) {
    return 0;
  }

  if (!isMatrixModePruningEnabled(target)) {
    return sampleTarget;
  }

  return Math.max(1, Math.ceil(sampleTarget * resolveMatrixShortCircuitRatio(target)));
}

function shouldForceResultsProbeSearchShortCircuit(target = {}) {
  if (target?.disableSearchRoute === true) {
    return false;
  }

  return RESULTS_PROBE_SEARCH_SHORT_CIRCUIT_LEAGUES.has(
    normalizeLeagueName(target?.league?.name || target?.leagueName || '')
  );
}

function hasForcedResultsProbeSearchShortCircuit(routeSource = null) {
  return routeSource?.forceSearchShortCircuit === true;
}

function shouldTolerateSearchNavigationFailure(target = {}) {
  return shouldForceResultsProbeSearchShortCircuit(target);
}

function shouldUseBidirectionalSearchDescriptors(target = {}) {
  return SEARCH_ROUTE_BIDIRECTIONAL_LEAGUES.has(
    normalizeLeagueName(target?.league?.name || target?.leagueName || '')
  );
}

function resolveSearchNavigationTimeoutMs(target = {}, timeoutMs = 0) {
  const baseTimeoutMs = Number(timeoutMs);
  if (!Number.isFinite(baseTimeoutMs) || baseTimeoutMs <= 0) {
    return baseTimeoutMs;
  }

  if (!shouldTolerateSearchNavigationFailure(target)) {
    return baseTimeoutMs;
  }

  return Math.min(baseTimeoutMs, SEARCH_ROUTE_NAVIGATION_FAST_FAIL_TIMEOUT_MS);
}

function isSearchNavigationTimeoutError(error) {
  const message = String(error?.message || error || '');
  return /Timeout \d+ms exceeded|ERR_TIMED_OUT|net::ERR_ABORTED|This operation was aborted/i.test(message);
}

function normalizeLeagueDeadlineAt(deadlineAt) {
  const normalized = Number(deadlineAt);
  return Number.isFinite(normalized) && normalized > 0 ? normalized : null;
}

function resolveResultsProbeShortCircuitBudget(target = {}, shortCircuitTimeoutMs = 0) {
  const normalizedShortCircuitTimeoutMs = Number(shortCircuitTimeoutMs);
  if (!Number.isFinite(normalizedShortCircuitTimeoutMs) || normalizedShortCircuitTimeoutMs <= 0) {
    return {
      probeDeadlineAt: normalizeLeagueDeadlineAt(target?.leagueDeadlineAt),
      shortCircuitOwnsDeadline: false
    };
  }

  const originalDeadlineAt = normalizeLeagueDeadlineAt(target?.leagueDeadlineAt);
  const shortCircuitDeadlineAt = Date.now() + normalizedShortCircuitTimeoutMs;
  const probeDeadlineAt = originalDeadlineAt === null
    ? shortCircuitDeadlineAt
    : Math.min(originalDeadlineAt, shortCircuitDeadlineAt);

  return {
    probeDeadlineAt,
    shortCircuitOwnsDeadline: originalDeadlineAt === null || probeDeadlineAt < originalDeadlineAt
  };
}

module.exports = {
  RESULTS_PROBE_SEARCH_SHORT_CIRCUIT_TIMEOUT_MS,
  buildFuzzyPrefixKeyword,
  buildSearchKeywordSlug,
  getCandidateCount,
  hasForcedResultsProbeSearchShortCircuit,
  isMatrixModePruningEnabled,
  isSearchNavigationTimeoutError,
  normalizeLeagueDeadlineAt,
  resolveResultsProbeShortCircuitBudget,
  resolveSampleLinkedThreshold,
  resolveSearchNavigationTimeoutMs,
  shouldForceResultsProbeSearchShortCircuit,
  shouldTolerateSearchNavigationFailure,
  shouldUseBidirectionalSearchDescriptors
};
