'use strict';

const SPECIAL_URL_RULES_BY_LEAGUE_ID = new Map([
  [42, { seasonlessResults: true, rootPage: true }],
  [53, { seasonlessResults: true }],
  [57, { seasonlessResults: true }],
  [121, { seasonlessCurrentOnly: true }],
  [77, { rootPage: true, allowFutureFixturesSweep: true }],
  [140, { canonicalResultsSlug: 'laliga2', canonicalSeasonalResults: true, seasonlessResults: true }],
  [181, { seasonlessResults: true, rootPage: true }],
  [209, { seasonlessResults: true }],
  [230, { seasonlessResults: true, seasonlessPrimary: true, rootPage: true }],
  [8974, { annualLike: true, seasonlessResults: true, seasonlessPrimary: true, disableFixturesSweep: true }]
]);

const reconTaskPlannerUrlUtils = {
  getLeagueId(leagueConfig = {}) {
    const leagueId = Number(leagueConfig?.id || 0);
    return Number.isInteger(leagueId) && leagueId > 0 ? leagueId : null;
  },

  getSpecialUrlRule(leagueConfig = {}) {
    const leagueId = this.getLeagueId(leagueConfig);
    if (!leagueId) {
      return null;
    }

    return SPECIAL_URL_RULES_BY_LEAGUE_ID.get(leagueId) || null;
  },

  formatSeasonForUrl(season) {
    if (!season) return '';
    return String(season).replace('/', '-');
  },

  formatSeasonForAnnualLeagueUrl(season) {
    const formatted = this.formatSeasonForUrl(season);
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

  formatSeasonForLeagueUrl(season, leagueConfig = {}) {
    if (this.isAnnualLeague(leagueConfig)) {
      return this.formatSeasonForAnnualLeagueUrl(season);
    }

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

  isAnnualLeague(leagueConfig = {}) {
    const leagueId = this.getLeagueId(leagueConfig);
    if (!leagueId) {
      return false;
    }

    const specialRule = this.getSpecialUrlRule(leagueConfig);
    if (specialRule?.annualLike === true) {
      return true;
    }

    return this.annualLeagueIds instanceof Set
      ? this.annualLeagueIds.has(leagueId)
      : false;
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

    const specialRule = this.getSpecialUrlRule(target?.league || {});
    if (specialRule?.allowFutureFixturesSweep === true) {
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

  renderSeasonPathUrl(template, leagueConfig, season) {
    const normalizedBaseUrl = String(this.baseUrl || '').replace(/\/+$/, '');
    const country = this.normalizePathSegment(leagueConfig.country);
    const slug = this.getResultsSlug(leagueConfig);
    const oddsportalSeason = this.formatSeasonForLeagueUrl(season, leagueConfig);
    const normalizedPath = String(template || '')
      .replace('{country}', country)
      .replace('{league}', slug)
      .replace('{season}', oddsportalSeason)
      .replace(/\/{2,}/g, '/')
      .replace(/^\/?/, '/');

    return `${normalizedBaseUrl}${normalizedPath}`;
  },

  renderExplicitSeasonPathUrl(template, leagueConfig, season) {
    const normalizedBaseUrl = String(this.baseUrl || '').replace(/\/+$/, '');
    const country = this.normalizePathSegment(leagueConfig.country);
    const slug = this.getResultsSlug(leagueConfig);
    const normalizedPath = String(template || '')
      .replace('{country}', country)
      .replace('{league}', slug)
      .replace('{season}', this.formatSeasonForUrl(season))
      .replace(/\/{2,}/g, '/')
      .replace(/^\/?/, '/');

    return `${normalizedBaseUrl}${normalizedPath}`;
  },

  buildResultsUrl(leagueConfig, season) {
    const country = this.normalizePathSegment(leagueConfig.country);
    const slug = this.getResultsSlug(leagueConfig);
    const specialRule = this.getSpecialUrlRule(leagueConfig);
    const resultsUrlStrategy = this.getResultsUrlStrategy(leagueConfig);
    const normalizedBaseUrl = String(this.baseUrl || '').replace(/\/+$/, '');
    if (specialRule?.seasonlessPrimary === true) {
      return `${normalizedBaseUrl}/football/${country}/${slug}/results/`;
    }
    if (specialRule?.seasonlessCurrentOnly === true && this.isCurrentSeason(season)) {
      return `${normalizedBaseUrl}/football/${country}/${slug}/results/`;
    }
    if (this.isAnnualLeague(leagueConfig)) {
      return this.renderSeasonPathUrl(this.resultsPathTemplate, leagueConfig, season);
    }
    if (resultsUrlStrategy === 'seasonless') {
      return `${normalizedBaseUrl}/football/${country}/${slug}/results/`;
    }
    if (this.slugIncludesYear(slug)) {
      return `${normalizedBaseUrl}/football/${country}/${slug}/results/`;
    }

    return this.renderSeasonPathUrl(this.resultsPathTemplate, leagueConfig, season);
  },

  buildFixturesUrl(leagueConfig, season) {
    if (!this.fixturesPathTemplate) {
      return null;
    }

    const specialRule = this.getSpecialUrlRule(leagueConfig);
    if (specialRule?.disableFixturesSweep === true) {
      return null;
    }

    return this.renderSeasonPathUrl(this.fixturesPathTemplate, leagueConfig, season);
  },

  buildSeasonlessSubpageUrl(leagueConfig, subpage) {
    const normalizedBaseUrl = String(this.baseUrl || '').replace(/\/+$/, '');
    const country = this.normalizePathSegment(leagueConfig.country);
    const slug = this.getResultsSlug(leagueConfig);
    const normalizedSubpage = String(subpage || '')
      .trim()
      .replace(/^\/+|\/+$/g, '');

    if (!normalizedSubpage) {
      return `${normalizedBaseUrl}/football/${country}/${slug}/`;
    }

    return `${normalizedBaseUrl}/football/${country}/${slug}/${normalizedSubpage}/`;
  },

  buildSeasonlessResultsUrl(leagueConfig) {
    return this.buildSeasonlessSubpageUrl(leagueConfig, 'results');
  },

  buildSeasonlessFixturesUrl(leagueConfig) {
    return this.buildSeasonlessSubpageUrl(leagueConfig, 'fixtures');
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
    const slug = this.getResultsSlug(leagueConfig);
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

  buildSeasonalSourceUrls(leagueConfig, season, options = {}) {
    const baseUrls = [
      this.buildResultsUrl(leagueConfig, season),
      ...this.buildAdditionalResultsUrls(leagueConfig, season),
      ...this.buildSeasonalFallbackResultsUrls(leagueConfig, season, options)
    ];

    return [...new Set(baseUrls.filter(Boolean))];
  },

  buildAnnualCurrentSeasonSources(leagueConfig, season) {
    const annualSeason = this.formatSeasonForAnnualLeagueUrl(season);
    const specialRule = this.getSpecialUrlRule(leagueConfig);
    const preferSeasonlessCurrent = specialRule?.seasonlessCurrentOnly === true && this.isCurrentSeason(season);
    const currentResultsUrl = preferSeasonlessCurrent
      ? this.buildSeasonlessResultsUrl(leagueConfig)
      : this.buildResultsUrl(leagueConfig, annualSeason);
    const currentResultsFallbackUrl = preferSeasonlessCurrent
      ? this.renderSeasonPathUrl(this.resultsPathTemplate, leagueConfig, annualSeason)
      : this.buildSeasonlessResultsUrl(leagueConfig);
    const sources = [
      {
        season: annualSeason,
        url: currentResultsUrl,
        mode: 'current_results'
      },
      {
        season: annualSeason,
        url: currentResultsFallbackUrl,
        mode: 'current_results_fallback'
      },
      ...(specialRule?.disableFixturesSweep === true
        ? []
        : [
          {
            season: annualSeason,
            url: this.buildFixturesUrl(leagueConfig, annualSeason),
            mode: 'current_fixtures'
          },
          {
            season: annualSeason,
            url: this.buildSeasonlessFixturesUrl(leagueConfig),
            mode: 'current_fixtures_fallback'
          }
        ])
    ].filter((source) => Boolean(source.url));

    const seen = new Set();
    return sources.filter((source) => {
      if (seen.has(source.url)) {
        return false;
      }
      seen.add(source.url);
      return true;
    });
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

  getSeasonlessCurrentYearBasis(leagueConfig = {}) {
    return String(
      leagueConfig.seasonlessCurrentYearBasis
      || leagueConfig.seasonless_current_year_basis
      || 'end'
    ).trim().toLowerCase();
  },

  buildLeagueUrl(leagueConfig) {
    const country = this.normalizePathSegment(leagueConfig.country);
    const slug = this.getResultsSlug(leagueConfig);
    const normalizedBaseUrl = String(this.baseUrl || '').replace(/\/+$/, '');
    return `${normalizedBaseUrl}/football/${country}/${slug}/`;
  },

  buildSeasonlessHistoricalResultsUrl(leagueConfig, year) {
    const country = this.normalizePathSegment(leagueConfig.country);
    const slug = this.getResultsSlug(leagueConfig);
    const normalizedBaseUrl = String(this.baseUrl || '').replace(/\/+$/, '');
    return `${normalizedBaseUrl}/football/${country}/${slug}-${year}/results/`;
  },

  getResultsSlug(leagueConfig = {}) {
    return String(leagueConfig.resultsSlug || leagueConfig.slug || '')
      .trim()
      .toLowerCase();
  },

  getCanonicalResultsSlug(leagueConfig = {}) {
    const specialRule = this.getSpecialUrlRule(leagueConfig);
    const fallbackSlug = this.getResultsSlug(leagueConfig);
    return String(specialRule?.canonicalResultsSlug || fallbackSlug)
      .trim()
      .toLowerCase();
  },

  buildCanonicalLeagueConfig(leagueConfig = {}) {
    const canonicalSlug = this.getCanonicalResultsSlug(leagueConfig);
    if (!canonicalSlug || canonicalSlug === this.getResultsSlug(leagueConfig)) {
      return leagueConfig;
    }

    return {
      ...leagueConfig,
      slug: canonicalSlug,
      resultsSlug: canonicalSlug
    };
  },

  buildSeasonalFallbackResultsUrls(leagueConfig = {}, season, options = {}) {
    const specialRule = this.getSpecialUrlRule(leagueConfig);
    if (!specialRule) {
      return [];
    }

    const urls = [];
    const canonicalLeague = this.buildCanonicalLeagueConfig(leagueConfig);
    const dbSeason = options.dbSeason || season;

    if (specialRule.canonicalSeasonalResults === true) {
      urls.push(this.renderSeasonPathUrl(this.resultsPathTemplate, canonicalLeague, season));
    }

    if (specialRule.seasonlessResults === true) {
      urls.push(this.buildSeasonlessResultsUrl(canonicalLeague));
    }

    if (specialRule.rootPage === true) {
      urls.push(this.buildLeagueUrl(canonicalLeague));
    }

    if (Number(this.getLeagueId(leagueConfig)) === 230) {
      urls.push(this.renderExplicitSeasonPathUrl(this.resultsPathTemplate, canonicalLeague, dbSeason));
    }

    return [...new Set(urls.filter(Boolean))];
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
