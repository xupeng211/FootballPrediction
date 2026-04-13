'use strict';

const DEFAULT_SEASON = '2025/2026';
const DEFAULT_THRESHOLD = 0.15;
const TARGET_STATUSES = ['harvested', 'RECON_MISMATCH'];
const CANONICAL_RESYNC_LEAGUE_IDS = new Set([223, 268]);

function createSilentLogger() {
  return {
    info() {},
    warn() {},
    error() {}
  };
}

function buildPerLeagueCounter() {
  return new Map();
}

function incrementPerLeague(counter, leagueId, amount = 1) {
  const key = String(leagueId || 'unknown');
  counter.set(key, Number(counter.get(key) || 0) + Number(amount || 0));
}

function serializePerLeagueCounter(counter) {
  return Object.fromEntries([...counter.entries()].sort((left, right) => left[0].localeCompare(right[0])));
}

module.exports = {
  DEFAULT_SEASON,
  DEFAULT_THRESHOLD,
  TARGET_STATUSES,
  CANONICAL_RESYNC_LEAGUE_IDS,
  createSilentLogger,
  buildPerLeagueCounter,
  incrementPerLeague,
  serializePerLeagueCounter
};
