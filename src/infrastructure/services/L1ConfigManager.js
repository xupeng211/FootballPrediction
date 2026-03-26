/**
 * @file L1ConfigManager - L1 配置统一管理器
 * @module infrastructure/services/L1ConfigManager
 * @description
 * 统一整合 recon_config.json 与 leagues.json，向 L1 发现引擎提供单一配置视图。
 */

'use strict';

const fs = require('fs');
const path = require('path');

const DEFAULT_SINGLE_YEAR_LEAGUES = [120, 121, 130, 223, 230, 268, 8974];

class L1ConfigManager {
  constructor(options = {}) {
    this.logger = options.logger || {
      info: () => {},
      warn: () => {},
      error: () => {}
    };

    this.reconConfigPath = options.reconConfigPath || path.resolve(__dirname, '../../../config/recon_config.json');
    this.leaguesConfigPath = options.leaguesConfigPath || path.resolve(__dirname, '../../../config/leagues.json');
    this.runtimeConfig = options.runtimeConfig || this._buildRuntimeConfig();
  }

  getRuntimeConfig() {
    return this.runtimeConfig;
  }

  getActiveLeagues(filters = {}) {
    const { tier = null } = filters;
    const leagues = this.runtimeConfig.active_leagues.filter((league) => league.enabled !== false);
    return tier ? leagues.filter((league) => league.tier === tier) : leagues;
  }

  getLeagueById(leagueId) {
    return this.runtimeConfig.active_leagues.find((league) => league.id === Number(leagueId)) || null;
  }

  getLeagueByCode(code) {
    return this.runtimeConfig.active_leagues.find((league) => league.code === code) || null;
  }

  getActiveSeasons() {
    return [...this.runtimeConfig.active_seasons];
  }

  getDefaultSeason(leagueId = null) {
    if (leagueId) {
      const league = this.getLeagueById(leagueId);
      if (league?.defaultSeason) {
        return league.defaultSeason;
      }
    }

    return this.runtimeConfig.default_season || this.runtimeConfig.active_seasons[0] || null;
  }

  getSingleYearLeagueIds() {
    return this.runtimeConfig.single_year_league_ids || [];
  }

  buildLeagueApiUrl(leagueId, season) {
    return `https://www.fotmob.com/api/data/leagues?id=${Number(leagueId)}&season=${encodeURIComponent(season)}`;
  }

  _buildRuntimeConfig() {
    const reconConfig = this._loadJson(this.reconConfigPath);
    const leaguesConfig = this._loadJson(this.leaguesConfigPath);

    if (!reconConfig && !leaguesConfig) {
      return this._buildFallbackRuntimeConfig();
    }

    const atlasLeagues = Array.isArray(leaguesConfig?.active_leagues) ? leaguesConfig.active_leagues : [];
    const activeSeasons = Array.isArray(leaguesConfig?.active_seasons) && leaguesConfig.active_seasons.length > 0
      ? [...leaguesConfig.active_seasons]
      : ['2024/2025'];

    const leagues = this._mergeLeagues(reconConfig?.leagues || {}, atlasLeagues, activeSeasons);
    const defaultSeason = activeSeasons[activeSeasons.length - 1] || activeSeasons[0] || null;
    const singleYearLeagueIds = leagues
      .filter((league) => league.seasonType === 'single_year')
      .map((league) => league.id);

    return {
      active_leagues: leagues,
      active_seasons: activeSeasons,
      default_season: defaultSeason,
      single_year_league_ids: singleYearLeagueIds
    };
  }

  _mergeLeagues(reconLeagues, atlasLeagues, activeSeasons) {
    const merged = [];
    const atlasById = new Map(atlasLeagues.map((league) => [Number(league.id), league]));
    const atlasByKey = new Map(atlasLeagues.map((league) => [this._leagueKey(league.name), league]));
    const seenIds = new Set();

    for (const [code, reconLeague] of Object.entries(reconLeagues)) {
      const atlasLeague = atlasById.get(Number(reconLeague.league_id)) || atlasByKey.get(this._leagueKey(reconLeague.name));
      const resolvedId = atlasLeague ? Number(atlasLeague.id) : Number(reconLeague.league_id);

      if (atlasLeague && Number(reconLeague.league_id) !== Number(atlasLeague.id)) {
        this.logger.warn(
          `[L1ConfigManager] 联赛 ID 冲突已自动修正: ${reconLeague.name} recon=${reconLeague.league_id} atlas=${atlasLeague.id}`
        );
      }

      const league = {
        id: resolvedId,
        code,
        name: reconLeague.name || atlasLeague?.name,
        country: reconLeague.country || atlasLeague?.country || 'unknown',
        slug: reconLeague.slug || this._slugify(reconLeague.name || atlasLeague?.name || code),
        tier: reconLeague.tier || atlasLeague?.tier || 'P0',
        enabled: reconLeague.enabled ?? atlasLeague?.enabled ?? true,
        seasonType: reconLeague.season_type || this._inferSeasonType(resolvedId),
        defaultSeason: reconLeague.default_season || activeSeasons[activeSeasons.length - 1] || activeSeasons[0] || null,
        supportedSeasons: reconLeague.supported_seasons || activeSeasons
      };

      merged.push(league);
      seenIds.add(league.id);
    }

    for (const atlasLeague of atlasLeagues) {
      const leagueId = Number(atlasLeague.id);
      if (seenIds.has(leagueId)) {
        continue;
      }

      merged.push({
        id: leagueId,
        code: atlasLeague.code || this._codeFromName(atlasLeague.name),
        name: atlasLeague.name,
        country: atlasLeague.country,
        slug: atlasLeague.slug || this._slugify(atlasLeague.name),
        tier: atlasLeague.tier || 'P0',
        enabled: atlasLeague.enabled !== false,
        seasonType: this._inferSeasonType(leagueId),
        defaultSeason: activeSeasons[activeSeasons.length - 1] || activeSeasons[0] || null,
        supportedSeasons: activeSeasons
      });
    }

    return merged.sort((a, b) => a.id - b.id);
  }

  _buildFallbackRuntimeConfig() {
    const activeSeasons = ['2024/2025'];
    const activeLeagues = [
      { id: 47, code: 'EPL', name: 'Premier League', country: 'England', slug: 'premier-league', tier: 'P0', enabled: true, seasonType: 'dual_year', defaultSeason: '2024/2025', supportedSeasons: activeSeasons },
      { id: 87, code: 'LALIGA', name: 'La Liga', country: 'Spain', slug: 'laliga', tier: 'P0', enabled: true, seasonType: 'dual_year', defaultSeason: '2024/2025', supportedSeasons: activeSeasons },
      { id: 54, code: 'BUNDESLIGA', name: 'Bundesliga', country: 'Germany', slug: 'bundesliga', tier: 'P0', enabled: true, seasonType: 'dual_year', defaultSeason: '2024/2025', supportedSeasons: activeSeasons },
      { id: 55, code: 'SERIEA', name: 'Serie A', country: 'Italy', slug: 'serie-a', tier: 'P0', enabled: true, seasonType: 'dual_year', defaultSeason: '2024/2025', supportedSeasons: activeSeasons },
      { id: 53, code: 'LIGUE1', name: 'Ligue 1', country: 'France', slug: 'ligue-1', tier: 'P0', enabled: true, seasonType: 'dual_year', defaultSeason: '2024/2025', supportedSeasons: activeSeasons }
    ];

    return {
      active_leagues: activeLeagues,
      active_seasons: activeSeasons,
      default_season: '2024/2025',
      single_year_league_ids: []
    };
  }

  _loadJson(filePath) {
    try {
      if (!fs.existsSync(filePath)) {
        return null;
      }

      return JSON.parse(fs.readFileSync(filePath, 'utf8'));
    } catch (error) {
      this.logger.warn(`[L1ConfigManager] 配置加载失败: ${filePath} - ${error.message}`);
      return null;
    }
  }

  _inferSeasonType(leagueId) {
    return DEFAULT_SINGLE_YEAR_LEAGUES.includes(Number(leagueId)) ? 'single_year' : 'dual_year';
  }

  _leagueKey(name) {
    return String(name || '')
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '');
  }

  _slugify(name) {
    return String(name || '')
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-+|-+$/g, '');
  }

  _codeFromName(name) {
    return String(name || '')
      .toUpperCase()
      .replace(/[^A-Z0-9]/g, '');
  }
}

module.exports = { L1ConfigManager };
