'use strict';

const { Normalizer } = require('../../utils/Normalizer');
const { L1ConfigManager } = require('../services/L1ConfigManager');

const WARNING_LOW_QUALITY_SOURCE = 'WARNING_LOW_QUALITY_SOURCE';

function normalizeLookupKey(value) {
  return String(value || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, ' ')
    .trim();
}

class EntityMapper {
  constructor(options = {}) {
    this.configManager = options.configManager || new L1ConfigManager();
    this.activeLeagues = this.configManager.getActiveLeagues();
    this.teamAliases = new Map();
    this.leagueAliases = new Map();

    this._seedTeamAliases(options.teamAliases || {});
    this._seedLeagueAliases(options.leagueAliases || {});
  }

  normalizeTeamName(rawName) {
    const raw = String(rawName || '').trim();
    if (!raw) {
      return '';
    }

    const lookupKey = normalizeLookupKey(raw);
    if (this.teamAliases.has(lookupKey)) {
      return this.teamAliases.get(lookupKey);
    }

    return Normalizer.normalizeTeamName(raw) || raw;
  }

  normalizeLeagueName(rawName) {
    const raw = String(rawName || '').trim();
    if (!raw) {
      return '';
    }

    const lookupKey = normalizeLookupKey(raw);
    if (this.leagueAliases.has(lookupKey)) {
      return this.leagueAliases.get(lookupKey);
    }

    const matchedLeague = this.activeLeagues.find((league) => (
      normalizeLookupKey(league?.name) === lookupKey
      || normalizeLookupKey(league?.code) === lookupKey
      || normalizeLookupKey(league?.slug) === lookupKey
    ));

    return matchedLeague?.name || raw;
  }

  buildSourceQualityFlags(options = {}) {
    const flags = [];
    if (options.hasOpenOdds === false) {
      flags.push(WARNING_LOW_QUALITY_SOURCE);
    }
    return flags;
  }

  _registerAlias(store, rawValue, canonicalValue) {
    const lookupKey = normalizeLookupKey(rawValue);
    const canonical = String(canonicalValue || '').trim();
    if (!lookupKey || !canonical) {
      return;
    }

    store.set(lookupKey, canonical);
  }

  _seedTeamAliases(extraAliases = {}) {
    const defaults = {
      QPR: 'Queens Park Rangers',
      'Man Utd': 'Manchester United',
      'Man City': 'Manchester City',
      "Nott'm Forest": 'Nottingham Forest',
      'Nott M Forest': 'Nottingham Forest',
      'Nottm Forest': 'Nottingham Forest',
      Spurs: 'Tottenham Hotspur',
      'Burgos': 'Burgos CF'
    };

    for (const [rawValue, canonicalValue] of Object.entries({ ...defaults, ...extraAliases })) {
      this._registerAlias(this.teamAliases, rawValue, canonicalValue);
    }
  }

  _seedLeagueAliases(extraAliases = {}) {
    for (const league of this.activeLeagues) {
      this._registerAlias(this.leagueAliases, league?.name, league?.name);
      this._registerAlias(this.leagueAliases, league?.code, league?.name);
      this._registerAlias(this.leagueAliases, league?.slug, league?.name);
    }

    const segundaDivision = this.activeLeagues.find((league) => Number(league?.id) === 140)?.name || 'Segunda División';
    const premierLeague = this.activeLeagues.find((league) => Number(league?.id) === 47)?.name || 'Premier League';
    const championsLeague = this.activeLeagues.find((league) => Number(league?.id) === 42)?.name || 'Champions League';
    const mls = this.activeLeagues.find((league) => Number(league?.id) === 130)?.name || 'Major League Soccer';

    const defaults = {
      Segunda: segundaDivision,
      'Segunda Division': segundaDivision,
      LaLiga2: segundaDivision,
      'La Liga 2': segundaDivision,
      EPL: premierLeague,
      'English Premier League': premierLeague,
      UCL: championsLeague,
      'UEFA Champions League': championsLeague,
      MLS: mls
    };

    for (const [rawValue, canonicalValue] of Object.entries({ ...defaults, ...extraAliases })) {
      this._registerAlias(this.leagueAliases, rawValue, canonicalValue);
    }
  }
}

module.exports = {
  EntityMapper,
  WARNING_LOW_QUALITY_SOURCE,
  normalizeLookupKey
};
