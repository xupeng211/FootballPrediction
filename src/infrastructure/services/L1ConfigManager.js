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
    this.seasonWindowsPath = options.seasonWindowsPath || path.resolve(__dirname, '../../../config/season_windows.json');
    this.runtimeConfig = options.runtimeConfig || this._buildRuntimeConfig();
  }

  getRuntimeConfig() {
    return this.runtimeConfig;
  }

  get(keyPath, defaultValue = null, expectedType = null) {
    if (typeof keyPath !== 'string' || !keyPath.trim()) {
      return defaultValue;
    }

    const value = keyPath
      .split('.')
      .filter(Boolean)
      .reduce((current, segment) => {
        if (!current || typeof current !== 'object' || !(segment in current)) {
          return undefined;
        }

        return current[segment];
      }, this.runtimeConfig);

    if (value === undefined) {
      return defaultValue;
    }

    if (expectedType && !this._matchesExpectedType(value, expectedType)) {
      this.logger.warn(`[L1ConfigManager] 配置 ${keyPath} 类型无效，期望 ${expectedType}`);
      return defaultValue;
    }

    return value;
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

  getProviderLeagueId(leagueId) {
    const league = this.getLeagueById(leagueId);
    return league?.providerId || (Number.isFinite(Number(leagueId)) ? Number(leagueId) : null);
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

  getExpectedMatches(leagueId, season) {
    if (!season) {
      return null;
    }
    return this._resolveExpectedMatches(this.runtimeConfig.season_windows || {}, Number(leagueId), season);
  }

  getSeasonDateWindow(leagueId, season) {
    if (!season) {
      return null;
    }
    return this._resolveSeasonDateWindow(
      this.runtimeConfig.season_windows || {},
      this.runtimeConfig.season_window_derivation || {},
      Number(leagueId),
      season
    );
  }

  buildLeagueApiUrl(leagueId, season) {
    const providerLeagueId = this.getProviderLeagueId(leagueId);
    return `https://www.fotmob.com/api/data/leagues?id=${Number(providerLeagueId)}&season=${encodeURIComponent(season)}`;
  }

  _buildRuntimeConfig() {
    const reconConfig = this._loadRequiredJson(this.reconConfigPath, 'recon_config.json');
    const leaguesConfig = this._loadRequiredJson(this.leaguesConfigPath, 'leagues.json');
    const seasonWindows = this._loadRequiredJson(this.seasonWindowsPath, 'season_windows.json');

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
      single_year_league_ids: singleYearLeagueIds,
      season_windows: seasonWindows.seasons || {},
      season_window_derivation: seasonWindows.derived_windows || {}
    };
  }

  _mergeLeagues(reconLeagues, atlasLeagues, activeSeasons) {
    const merged = [];
    const atlasById = new Map(atlasLeagues.map((league) => [Number(league.id), league]));
    const atlasByKey = new Map(atlasLeagues.map((league) => [this._leagueKey(league.name), league]));
    const seenIds = new Set();

    for (const [code, reconLeague] of Object.entries(reconLeagues)) {
      const league = this._buildReconLeagueEntry(code, reconLeague, atlasById, atlasByKey, activeSeasons);
      merged.push(league);
      seenIds.add(league.id);
    }

    for (const atlasLeague of atlasLeagues) {
      const leagueId = Number(atlasLeague.id);
      if (seenIds.has(leagueId)) {
        continue;
      }

      merged.push(this._buildAtlasLeagueEntry(atlasLeague, activeSeasons));
    }

    return merged.sort((a, b) => a.id - b.id);
  }

  _resolveExpectedMatches(seasonConfig, leagueId, season) {
    const candidates = [
      this._resolveSeasonWindowEntry(seasonConfig, leagueId, season),
      ...Object.values(seasonConfig).filter((window) => this._isSeasonWindowMatch(window, leagueId, season))
    ];
    return candidates.find((window) => Number.isFinite(Number(window?.expected_matches)))?.expected_matches || null;
  }

  _resolveSeasonDateWindow(seasonConfig, derivationConfig, leagueId, season) {
    const explicitWindow = this._resolveSeasonWindowEntry(seasonConfig, leagueId, season);
    if (explicitWindow?.start && explicitWindow?.end) {
      return {
        start: explicitWindow.start,
        end: explicitWindow.end,
        source: 'explicit'
      };
    }

    const derivedWindow = this._buildDerivedSeasonWindow(derivationConfig, leagueId, season);
    if (derivedWindow) {
      return derivedWindow;
    }

    return null;
  }

  _resolveSeasonWindowEntry(seasonConfig, leagueId, season) {
    return [
      this._findSeasonWindowByLeague(seasonConfig[season], leagueId),
      this._findSeasonWindowBySuffix(seasonConfig, leagueId, season)
    ].find(Boolean) || null;
  }

  _buildDerivedSeasonWindow(derivationConfig, leagueId, season) {
    const seasonYears = this._extractSeasonYears(season);
    if (!seasonYears) {
      return null;
    }

    const strategies = derivationConfig?.strategies || {};
    const overrides = derivationConfig?.league_strategy_overrides || {};
    const strategyKey = String(overrides[String(leagueId)] || 'dual_year').trim();
    const strategy = strategies[strategyKey];

    if (!strategy?.start_month_day || !strategy?.end_month_day) {
      return null;
    }

    const startYear = seasonYears.startYear;
    const endYear = strategyKey === 'calendar_year'
      ? seasonYears.startYear
      : seasonYears.endYear > seasonYears.startYear
        ? seasonYears.endYear
        : seasonYears.startYear + 1;

    return {
      start: `${startYear}-${strategy.start_month_day}`,
      end: `${endYear}-${strategy.end_month_day}`,
      source: `derived:${strategyKey}`
    };
  }

  _extractSeasonYears(season) {
    const matches = String(season || '').match(/\d{4}/g);
    if (!Array.isArray(matches) || matches.length === 0) {
      return null;
    }

    const startYear = Number.parseInt(matches[0], 10);
    const endYear = matches.length > 1
      ? Number.parseInt(matches[1], 10)
      : startYear;

    if (!Number.isInteger(startYear) || !Number.isInteger(endYear)) {
      return null;
    }

    return { startYear, endYear };
  }

  _findSeasonWindowByLeague(window, leagueId) {
    return window && Array.isArray(window.leagues) && window.leagues.includes(leagueId) ? window : null;
  }

  _findSeasonWindowBySuffix(seasonConfig, leagueId, season) {
    const league = this.getLeagueById(leagueId);
    const suffix = league?.name ? `-${league.name.replace(/\s+/g, '')}` : null;
    return suffix ? seasonConfig[`${season}${suffix}`] || null : null;
  }

  _isSeasonWindowMatch(window, leagueId, season) {
    return Boolean(window)
      && Array.isArray(window.leagues)
      && window.leagues.includes(leagueId)
      && Number.isFinite(Number(window.expected_matches))
      && Boolean(window.description?.includes(season.slice(2, 4)));
  }

  _buildReconLeagueEntry(code, reconLeague, atlasById, atlasByKey, activeSeasons) {
    this._assertValidReconLeague(code, reconLeague);
    const atlasLeague = atlasById.get(Number(reconLeague.league_id)) || atlasByKey.get(this._leagueKey(reconLeague.name));
    const resolvedId = atlasLeague ? Number(atlasLeague.id) : Number(reconLeague.league_id);
    this._warnOnLeagueConflict(reconLeague, atlasLeague);
    const name = this._resolveLeagueName(reconLeague, atlasLeague, code);
    const resultsConfig = this._resolveResultsConfig(reconLeague, atlasLeague, name, code);
    const seasonConfig = this._resolveSeasonConfig(reconLeague, activeSeasons, resolvedId);
    const runtimeConfig = this._resolveRuntimeLeagueConfig(reconLeague, atlasLeague);

    return {
      id: resolvedId,
      providerId: this._resolveProviderId(reconLeague, atlasLeague, resolvedId),
      code,
      name,
      country: this._resolveLeagueCountry(reconLeague, atlasLeague),
      slug: resultsConfig.slug,
      resultsSlug: resultsConfig.resultsSlug,
      resultsUrlStrategy: resultsConfig.resultsUrlStrategy,
      seasonlessCurrentYearBasis: resultsConfig.seasonlessCurrentYearBasis,
      additionalResultsPaths: resultsConfig.additionalResultsPaths,
      additionalHistoricalResultsPaths: resultsConfig.additionalHistoricalResultsPaths,
      readySelector: runtimeConfig.readySelector,
      awaitingFinals: runtimeConfig.awaitingFinals,
      tier: runtimeConfig.tier,
      enabled: runtimeConfig.enabled,
      seasonType: seasonConfig.seasonType,
      defaultSeason: seasonConfig.defaultSeason,
      supportedSeasons: seasonConfig.supportedSeasons
    };
  }

  _resolveLeagueName(reconLeague, atlasLeague, fallbackCode) {
    return reconLeague.name || atlasLeague?.name || fallbackCode;
  }

  _resolveLeagueCountry(reconLeague, atlasLeague) {
    return reconLeague.country || atlasLeague?.country || 'unknown';
  }

  _resolveResultsConfig(reconLeague, atlasLeague, leagueName, fallbackCode) {
    const slug = reconLeague.slug || atlasLeague?.slug || this._slugify(leagueName || fallbackCode);
    return {
      slug,
      resultsSlug: reconLeague.results_slug || atlasLeague?.results_slug || slug || null,
      resultsUrlStrategy: reconLeague.results_url_strategy || atlasLeague?.results_url_strategy || 'seasonal',
      seasonlessCurrentYearBasis: reconLeague.seasonless_current_year_basis || atlasLeague?.seasonless_current_year_basis || 'end',
      additionalResultsPaths: this._normalizeStringArray(reconLeague.additional_results_paths || atlasLeague?.additional_results_paths),
      additionalHistoricalResultsPaths: this._normalizeStringArray(
        reconLeague.additional_historical_results_paths || atlasLeague?.additional_historical_results_paths
      )
    };
  }

  _resolveRuntimeLeagueConfig(reconLeague, atlasLeague) {
    return {
      readySelector: reconLeague.ready_selector || atlasLeague?.ready_selector || null,
      awaitingFinals: reconLeague.awaiting_finals === true || atlasLeague?.awaiting_finals === true,
      tier: reconLeague.tier || atlasLeague?.tier || 'P0',
      enabled: reconLeague.enabled ?? atlasLeague?.enabled ?? true
    };
  }

  _resolveSeasonConfig(reconLeague, activeSeasons, resolvedId) {
    return {
      seasonType: reconLeague.season_type || this._inferSeasonType(resolvedId),
      defaultSeason: reconLeague.default_season || activeSeasons[activeSeasons.length - 1] || activeSeasons[0] || null,
      supportedSeasons: reconLeague.supported_seasons || activeSeasons
    };
  }

  _warnOnLeagueConflict(reconLeague, atlasLeague) {
    if (atlasLeague && Number(reconLeague.league_id) !== Number(atlasLeague.id)) {
      this.logger.warn(
        `[L1ConfigManager] 联赛 ID 冲突已自动修正: ${reconLeague.name} recon=${reconLeague.league_id} atlas=${atlasLeague.id}`
      );
    }
  }

  _buildAtlasLeagueEntry(atlasLeague, activeSeasons) {
    const leagueId = Number(atlasLeague.id);
    return {
      id: leagueId,
      providerId: this._resolveProviderId(null, atlasLeague, leagueId),
      code: atlasLeague.code || this._codeFromName(atlasLeague.name),
      name: atlasLeague.name,
      country: atlasLeague.country,
      slug: atlasLeague.slug || this._slugify(atlasLeague.name),
      resultsSlug: atlasLeague.results_slug || atlasLeague.slug || null,
      resultsUrlStrategy: atlasLeague.results_url_strategy || 'seasonal',
      seasonlessCurrentYearBasis: atlasLeague.seasonless_current_year_basis || 'end',
      additionalResultsPaths: this._normalizeStringArray(atlasLeague.additional_results_paths),
      additionalHistoricalResultsPaths: this._normalizeStringArray(atlasLeague.additional_historical_results_paths),
      readySelector: atlasLeague.ready_selector || null,
      awaitingFinals: atlasLeague.awaiting_finals === true,
      tier: atlasLeague.tier || 'P0',
      enabled: atlasLeague.enabled !== false,
      seasonType: this._inferSeasonType(leagueId),
      defaultSeason: activeSeasons[activeSeasons.length - 1] || activeSeasons[0] || null,
      supportedSeasons: activeSeasons
    };
  }

  _loadRequiredJson(filePath, label) {
    if (!fs.existsSync(filePath)) {
      throw new Error(`[L1ConfigManager] 缺少必需配置文件: ${label}`);
    }

    try {
      return JSON.parse(fs.readFileSync(filePath, 'utf8'));
    } catch (error) {
      throw new Error(`[L1ConfigManager] 配置文件损坏: ${label} - ${error.message}`);
    }
  }

  _assertValidReconLeague(code, reconLeague) {
    if (!reconLeague || typeof reconLeague !== 'object') {
      throw new Error(`[L1ConfigManager] 联赛配置损坏: ${code}`);
    }

    if (!Number.isFinite(Number(reconLeague.league_id))) {
      throw new Error(`[L1ConfigManager] 联赛 ${code} 缺少有效 league_id`);
    }

    if (!reconLeague.name || typeof reconLeague.name !== 'string') {
      throw new Error(`[L1ConfigManager] 联赛 ${code} 缺少有效 name`);
    }
  }

  _resolveProviderId(reconLeague, atlasLeague, fallbackId) {
    const providerId = atlasLeague?.providerId
      ?? atlasLeague?.provider_id
      ?? reconLeague?.providerId
      ?? reconLeague?.provider_id
      ?? fallbackId;

    return Number.isFinite(Number(providerId)) ? Number(providerId) : Number(fallbackId);
  }

  _normalizeStringArray(value) {
    if (!Array.isArray(value)) {
      return [];
    }

    return value
      .map((item) => String(item || '').trim())
      .filter(Boolean);
  }

  _matchesExpectedType(value, expectedType) {
    if (expectedType === 'array') {
      return Array.isArray(value);
    }

    if (expectedType === 'number') {
      return Number.isFinite(value);
    }

    return typeof value === expectedType;
  }

  _inferSeasonType(leagueId) {
    return DEFAULT_SINGLE_YEAR_LEAGUES.includes(Number(leagueId)) ? 'single_year' : 'dual_year';
  }

  _leagueKey(name) {
    return this._normalizeAscii(name)
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '');
  }

  _slugify(name) {
    return this._normalizeAscii(name)
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-+|-+$/g, '');
  }

  _codeFromName(name) {
    return this._normalizeAscii(name)
      .toUpperCase()
      .replace(/[^A-Z0-9]/g, '');
  }

  _normalizeAscii(value) {
    return String(value || '')
      .normalize('NFKD')
      .replace(/[\u0300-\u036f]/g, '');
  }
}

module.exports = { L1ConfigManager };
