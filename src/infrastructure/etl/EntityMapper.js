'use strict';

const { Normalizer } = require('../../utils/Normalizer');
const { L1ConfigManager } = require('../services/L1ConfigManager');

const WARNING_LOW_QUALITY_SOURCE = 'WARNING_LOW_QUALITY_SOURCE';

function normalizeLookupKey(value) {
  return String(value || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^\p{Letter}\p{Number}]+/gu, ' ')
    .trim();
}

class EntityMapper {
  constructor(options = {}) {
    this.configManager = options.configManager || new L1ConfigManager();
    this.activeLeagues = this.configManager.getActiveLeagues();
    this.teamAliases = new Map();
    this.leagueAliases = new Map();
    this.bookmakerAliases = new Map();

    this._seedTeamAliases(options.teamAliases || {});
    this._seedLeagueAliases(options.leagueAliases || {});
    this._seedBookmakerAliases(options.bookmakerAliases || {});
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

  normalizeFotMobExternalId(rawValue) {
    return String(rawValue || '').trim();
  }

  normalizeBookmakerName(rawName) {
    const raw = String(rawName || '').trim();
    if (!raw) {
      return '';
    }

    const lookupKey = normalizeLookupKey(raw);
    if (this.bookmakerAliases.has(lookupKey)) {
      return this.bookmakerAliases.get(lookupKey);
    }

    return raw;
  }

  buildMatchLookupKey(homeTeam, awayTeam) {
    const normalizedHome = this.normalizeTeamName(homeTeam);
    const normalizedAway = this.normalizeTeamName(awayTeam);
    return `${normalizeLookupKey(normalizedHome)}::${normalizeLookupKey(normalizedAway)}`;
  }

  bindFotMobIdentity(match = {}) {
    const matchId = String(match.match_id || match.matchId || '').trim();
    const externalId = this.normalizeFotMobExternalId(match.external_id || match.externalId);

    if (!matchId) {
      throw new Error('未找到可复用的 FotMob match_id');
    }
    if (!externalId) {
      throw new Error(`比赛 ${matchId} 缺少 FotMob external_id`);
    }

    return {
      matchId,
      externalId
    };
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
      'Burgos': 'Burgos CF',
      Vallecano: 'Rayo Vallecano',
      Oviedo: 'Real Oviedo',
      Alaves: 'Deportivo Alaves',
      'Ath Madrid': 'Atletico Madrid',
      Betis: 'Real Betis',
      Celta: 'Celta Vigo',
      Espanol: 'Espanyol',
      Sociedad: 'Real Sociedad',
      'Ein Frankfurt': 'Eintracht Frankfurt',
      'FC Koln': '1 Fc Koln',
      Heidenheim: 'Fc Heidenheim',
      Leverkusen: 'Bayer Leverkusen',
      "M'gladbach": 'Borussia Monchengladbach',
      Mainz: 'Mainz 05',
      Verona: 'Hellas Verona',
      'Paris SG': 'Paris Saint Germain'
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
    const laLiga = this.activeLeagues.find((league) => Number(league?.id) === 87)?.name || 'La Liga';
    const championsLeague = this.activeLeagues.find((league) => Number(league?.id) === 42)?.name || 'Champions League';
    const mls = this.activeLeagues.find((league) => Number(league?.id) === 130)?.name || 'Major League Soccer';

    const defaults = {
      Segunda: segundaDivision,
      'Segunda Division': segundaDivision,
      LaLiga: laLiga,
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

  _seedBookmakerAliases(extraAliases = {}) {
    const defaults = {
      'Macau Slot': 'MACAU_SLOT',
      '澳门彩票': 'MACAU_SLOT',
      '澳彩': 'MACAU_SLOT',
      MacauSlot: 'MACAU_SLOT',
      Crown: 'CROWN',
      '皇冠': 'CROWN',
      IBC: 'CROWN',
      IBCBET: 'CROWN',
      '188Bet': '188BET',
      '利记': '188BET',
      '188': '188BET'
    };

    for (const [rawValue, canonicalValue] of Object.entries({ ...defaults, ...extraAliases })) {
      this._registerAlias(this.bookmakerAliases, rawValue, canonicalValue);
    }
  }
}

module.exports = {
  EntityMapper,
  WARNING_LOW_QUALITY_SOURCE,
  normalizeLookupKey
};
