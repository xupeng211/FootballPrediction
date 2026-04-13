'use strict';

const MAX_DEBUG_LOGS = 3;

function initializeStats(stats = {}) {
  stats.wrongLeague = Number(stats.wrongLeague || 0);
  stats.outsideWindow = Number(stats.outsideWindow || 0);
  stats.placeholder = Number(stats.placeholder || 0);
  stats.invalidData = Number(stats.invalidData || 0);
  return stats;
}

function isProcessableMatch(match) {
  return Boolean(match) && typeof match === 'object' && !Array.isArray(match);
}

function extractMatchTime(match = {}) {
  for (const [field, value] of [
    ['utcTime', match.utcTime],
    ['status.utcTime', match.status?.utcTime],
    ['time', match.time]
  ]) {
    if (value !== undefined && value !== null) {
      return { rawTime: value, usedField: field };
    }
  }

  return { rawTime: null, usedField: null };
}

function parseMatchDate(rawTime) {
  if (rawTime === null || rawTime === undefined) {
    return null;
  }

  const strTime = String(rawTime).trim();
  if (!strTime) {
    return null;
  }

  if (typeof rawTime === 'string' && (strTime.includes('T') || strTime.includes('-'))) {
    return new Date(strTime);
  }

  if (/^\d+$/.test(strTime)) {
    const numTime = Number.parseInt(strTime, 10);
    if (strTime.length === 13 || numTime > 1000000000000) {
      return new Date(numTime);
    }
    return strTime.length === 10 || numTime > 1000000000 ? new Date(numTime * 1000) : null;
  }

  if (typeof rawTime === 'number') {
    return rawTime > 1000000000000
      ? new Date(rawTime)
      : rawTime > 1000000000
        ? new Date(rawTime * 1000)
        : null;
  }

  return new Date(strTime);
}

function buildBufferedWindow(window, bufferDays) {
  const startDate = new Date(window.start);
  const endDate = new Date(window.end);
  if (Number.isNaN(startDate.getTime()) || Number.isNaN(endDate.getTime())) {
    return null;
  }

  const bufferMs = Number(bufferDays || 0) * 24 * 60 * 60 * 1000;
  return {
    validStart: new Date(startDate.getTime() - bufferMs),
    validEnd: new Date(endDate.getTime() + bufferMs)
  };
}

function logWindowDebug(log, stats, label, payload) {
  if (!stats) {
    return;
  }

  stats._debugLogCount = Number(stats._debugLogCount || 0) + 1;
  if (stats._debugLogCount <= MAX_DEBUG_LOGS) {
    log?.info?.(`[DEBUG ${stats._debugLogCount}/${MAX_DEBUG_LOGS}] ${label}`, payload);
  }
}

function containsPlaceholderKeyword(match, keywords = []) {
  const homeName = String(match?.home?.name || '').toLowerCase().trim();
  const awayName = String(match?.away?.name || '').toLowerCase().trim();
  return keywords.some((keyword) => homeName.includes(keyword) || awayName.includes(keyword));
}

function hasInvalidTeamIds(match) {
  const ids = [match?.home?.id, match?.away?.id];
  return ids.some((teamId) => teamId === null || teamId === undefined || teamId === 0 || teamId === '0' || teamId === '');
}

module.exports = {
  buildBufferedWindow,
  containsPlaceholderKeyword,
  extractMatchTime,
  hasInvalidTeamIds,
  initializeStats,
  isProcessableMatch,
  logWindowDebug,
  parseMatchDate
};
