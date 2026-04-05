'use strict';

const reconTaskPlannerUrlUtils = {
  formatSeasonForUrl(season) {
    if (!season) return '';
    return String(season).replace('/', '-');
  },

  formatSeasonForLeagueUrl(season, leagueConfig = {}) {
    const formatted = this.formatSeasonForUrl(season);
    const seasonType = String(
      leagueConfig?.seasonType
      || leagueConfig?.season_type
      || ''
    ).trim().toLowerCase();

    if (seasonType !== 'single_year') {
      return formatted;
    }

    const dualYearMatch = formatted.match(/^(\d{4})-(\d{4})$/);
    if (dualYearMatch) {
      return dualYearMatch[2];
    }

    const dbSeasonMatch = String(season || '').match(/^(\d{4})\/(\d{4})$/);
    if (dbSeasonMatch) {
      return dbSeasonMatch[2];
    }

    return formatted;
  },

  isSingleYearLeague(leagueConfig = {}) {
    return String(
      leagueConfig?.seasonType
      || leagueConfig?.season_type
      || ''
    ).trim().toLowerCase() === 'single_year';
  },

  normalizeDbSeason(season) {
    return String(season || '').replace('-', '/');
  },

  filterPlaceholderFixtures(matches = []) {
    if (!this.matchEvaluator || typeof this.matchEvaluator.isPlaceholderFixture !== 'function') {
      return Array.isArray(matches) ? [...matches] : [];
    }

    return (Array.isArray(matches) ? matches : []).filter(
      (match) => !this.matchEvaluator.isPlaceholderFixture(match)
    );
  },

  getFutureFinalsWindow(target, pendingMatches, now = new Date()) {
    const awaitingFinals = target?.league?.awaitingFinals === true || target?.league?.awaiting_finals === true;
    if (!awaitingFinals) {
      return { shouldSkip: false, kickoffDate: null };
    }

    const kickoffDate = (Array.isArray(pendingMatches) ? pendingMatches : [])
      .map((match) => new Date(match?.match_date))
      .filter((value) => Number.isFinite(value.getTime()))
      .sort((left, right) => left.getTime() - right.getTime())[0];

    if (!kickoffDate) {
      return { shouldSkip: false, kickoffDate: null };
    }

    return {
      shouldSkip: kickoffDate.getTime() > now.getTime(),
      kickoffDate: kickoffDate.toISOString()
    };
  },

  shiftSeason(season, delta) {
    const normalized = this.formatSeasonForUrl(season);
    const match = normalized.match(/^(\d{4})-(\d{4})$/);
    if (!match) {
      return normalized;
    }

    const start = Number(match[1]) + Number(delta || 0);
    const end = Number(match[2]) + Number(delta || 0);
    return `${start}-${end}`;
  },

  parseSeasonYears(season) {
    const normalized = this.formatSeasonForUrl(season);
    const match = normalized.match(/^(\d{4})-(\d{4})$/);
    if (!match) {
      return null;
    }

    return {
      startYear: Number(match[1]),
      endYear: Number(match[2])
    };
  },

  getPendingMatchYears(pendingMatches = []) {
    return [...new Set(
      (Array.isArray(pendingMatches) ? pendingMatches : [])
        .map((match) => new Date(match?.match_date))
        .filter((date) => Number.isFinite(date.getTime()))
        .map((date) => date.getUTCFullYear())
    )].sort((left, right) => left - right);
  },

  isCurrentSeason(season) {
    const normalized = this.formatSeasonForUrl(season);
    if (/^\d{4}$/.test(normalized)) {
      return Number(normalized) === new Date().getUTCFullYear();
    }

    const match = normalized.match(/^(\d{4})-(\d{4})$/);
    if (!match) {
      return false;
    }

    const now = new Date();
    const year = now.getUTCFullYear();
    const month = now.getUTCMonth() + 1;
    const seasonStartYear = month >= 7 ? year : year - 1;
    const seasonEndYear = seasonStartYear + 1;

    return Number(match[1]) === seasonStartYear && Number(match[2]) === seasonEndYear;
  },

  buildResultsUrl(leagueConfig, season) {
    const oddsportalSeason = this.formatSeasonForLeagueUrl(season, leagueConfig);
    const country = this.normalizePathSegment(leagueConfig.country);
    const slug = String(leagueConfig.resultsSlug || leagueConfig.slug || '')
      .trim()
      .toLowerCase();
    const resultsUrlStrategy = String(leagueConfig.resultsUrlStrategy || 'seasonal')
      .trim()
      .toLowerCase();
    const normalizedBaseUrl = String(this.baseUrl || '').replace(/\/+$/, '');
    if (resultsUrlStrategy === 'seasonless') {
      return `${normalizedBaseUrl}/football/${country}/${slug}/results/`;
    }
    if (this.slugIncludesYear(slug)) {
      return `${normalizedBaseUrl}/football/${country}/${slug}/results/`;
    }

    const normalizedPath = `${this.resultsPathTemplate}`
      .replace('{country}', country)
      .replace('{league}', slug)
      .replace('{season}', oddsportalSeason)
      .replace(/\/{2,}/g, '/')
      .replace(/^\/?/, '/');

    return `${normalizedBaseUrl}${normalizedPath}`;
  },

  getAdditionalPathTemplates(leagueConfig = {}, fieldName, legacyFieldName = null) {
    const value = leagueConfig?.[fieldName] ?? (legacyFieldName ? leagueConfig?.[legacyFieldName] : undefined);
    if (!Array.isArray(value)) {
      return [];
    }

    return value
      .map((item) => String(item || '').trim())
      .filter(Boolean);
  },

  renderLeaguePathTemplate(template, leagueConfig = {}, replacements = {}) {
    const normalizedBaseUrl = String(this.baseUrl || '').replace(/\/+$/, '');
    const country = this.normalizePathSegment(leagueConfig.country);
    const slug = String(leagueConfig.resultsSlug || leagueConfig.slug || '')
      .trim()
      .toLowerCase();
    const oddsportalSeason = this.formatSeasonForLeagueUrl(replacements.season, leagueConfig);
    const year = replacements.year ?? replacements.season ?? '';
    const normalizedPath = String(template || '')
      .replace('{country}', country)
      .replace('{league}', slug)
      .replace('{season}', oddsportalSeason)
      .replace('{year}', String(year))
      .replace(/\/{2,}/g, '/')
      .replace(/^\/?/, '/');

    return `${normalizedBaseUrl}${normalizedPath}`;
  },

  buildAdditionalResultsUrls(leagueConfig, season) {
    const templates = this.getAdditionalPathTemplates(
      leagueConfig,
      'additionalResultsPaths',
      'additional_results_paths'
    );

    return templates.map((template) => this.renderLeaguePathTemplate(template, leagueConfig, { season }));
  },

  buildAdditionalHistoricalResultsUrls(leagueConfig, year) {
    const templates = this.getAdditionalPathTemplates(
      leagueConfig,
      'additionalHistoricalResultsPaths',
      'additional_historical_results_paths'
    );

    return templates.map((template) => this.renderLeaguePathTemplate(template, leagueConfig, { year }));
  },

  buildCurrentSeasonSourceUrls(leagueConfig, season) {
    const urls = [
      this.buildResultsUrl(leagueConfig, season),
      ...this.buildAdditionalResultsUrls(leagueConfig, season)
    ];

    return [...new Set(urls.filter(Boolean))];
  },

  buildHistoricalSeasonSourceUrls(leagueConfig, year) {
    const urls = [
      this.buildSeasonlessHistoricalResultsUrl(leagueConfig, year),
      ...this.buildAdditionalHistoricalResultsUrls(leagueConfig, year)
    ];

    return [...new Set(urls.filter(Boolean))];
  },

  getResultsUrlStrategy(leagueConfig = {}) {
    return String(
      leagueConfig.resultsUrlStrategy
      || leagueConfig.results_url_strategy
      || 'seasonal'
    ).trim().toLowerCase();
  },

  buildLeagueUrl(leagueConfig) {
    const country = this.normalizePathSegment(leagueConfig.country);
    const slug = String(leagueConfig.resultsSlug || leagueConfig.slug || '')
      .trim()
      .toLowerCase();
    const normalizedBaseUrl = String(this.baseUrl || '').replace(/\/+$/, '');
    return `${normalizedBaseUrl}/football/${country}/${slug}/`;
  },

  buildSeasonlessHistoricalResultsUrl(leagueConfig, year) {
    const country = this.normalizePathSegment(leagueConfig.country);
    const slug = String(leagueConfig.resultsSlug || leagueConfig.slug || '')
      .trim()
      .toLowerCase();
    const normalizedBaseUrl = String(this.baseUrl || '').replace(/\/+$/, '');
    return `${normalizedBaseUrl}/football/${country}/${slug}-${year}/results/`;
  },

  slugIncludesYear(slug) {
    return /(?:^|-)(?:19|20)\d{2}(?:-|$)/.test(String(slug || '').trim().toLowerCase());
  },

  normalizePathSegment(value) {
    return String(value || '')
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-+|-+$/g, '');
  }
};

module.exports = { reconTaskPlannerUrlUtils };
