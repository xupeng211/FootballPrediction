'use strict';

const { extractAllStats } = require('./XGExtractor');

function firstValue(values, fallback = null) {
  return values.find(value => value !== undefined && value !== null && value !== '') ?? fallback;
}

function normalizeStat(stat) {
  if (!stat || typeof stat !== 'object') {
    return null;
  }

  return {
    key: firstValue([stat.key, stat.type, stat.title, stat.name]),
    title: firstValue([stat.title, stat.name, stat.type]),
    home: firstValue([stat.home, stat.homeValue, stat.values?.[0]]),
    away: firstValue([stat.away, stat.awayValue, stat.values?.[1]]),
    raw: stat
  };
}

class MatchStatsParser {
  parseStats(rawData = {}) {
    const stats = rawData.stats || rawData.content?.stats || rawData.matchStats || {};
    const groups = Array.isArray(stats) ? stats : (stats.stats || stats.periods || []);
    const rows = [];

    for (const group of groups) {
      const items = Array.isArray(group) ? group : (group.stats || group.items || []);
      for (const item of items) {
        const normalized = normalizeStat(item);
        if (normalized) {
          rows.push(normalized);
        }
      }
    }

    return {
      stats: rows,
      xg: extractAllStats(rawData)
    };
  }
}

module.exports = { MatchStatsParser, normalizeStat };
