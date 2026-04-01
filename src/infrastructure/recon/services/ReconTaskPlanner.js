'use strict';

const { getReconConfigSection } = require('./ReconServiceConfig');

class ReconTaskPlanner {
  constructor(options = {}) {
    const runtimeConfig = getReconConfigSection(['recon_runtime', 'task_planner'], {});

    this.navigator = options.navigator || null;
    this.repository = options.repository || null;
    this.logger = options.logger || console;
    this.configManager = options.configManager || null;
    this.baseUrl = options.baseUrl || runtimeConfig.base_url;
    this.matchEvaluator = options.matchEvaluator || null;
    this.mirrorManager = options.mirrorManager || null;
    this.sampleSize = Math.max(1, Number(options.sampleSize ?? runtimeConfig.sample_size));
    this.archiveMaxPages = Math.max(1, Number(options.archiveMaxPages ?? runtimeConfig.archive_max_pages));
    this.archiveTimeoutMs = Math.max(1, Number(options.archiveTimeoutMs ?? runtimeConfig.archive_timeout_ms));
    this.resultsPathTemplate = options.resultsPathTemplate || runtimeConfig.results_path;
    this.mismatchRetryThresholdDelta = Number(options.mismatchRetryThresholdDelta ?? runtimeConfig.mismatch_retry_threshold_delta ?? 0.05);
    this.mismatchRetryThresholdFloor = Number(options.mismatchRetryThresholdFloor ?? runtimeConfig.mismatch_retry_threshold_floor ?? 0.45);
    this.forceDomLeagueIds = new Set(
      (options.forceDomLeagueIds || runtimeConfig.force_dom_league_ids || [])
        .map((id) => Number(id))
        .filter((id) => Number.isInteger(id) && id > 0)
    );
  }

  buildTarget(season, leagueConfig) {
    return {
      leagueId: Number(leagueConfig?.id || 0),
      league: leagueConfig,
      readySelector: leagueConfig?.readySelector || leagueConfig?.ready_selector || null,
      season: this.formatSeasonForLeagueUrl(season, leagueConfig),
      dbSeason: this.normalizeDbSeason(season),
      resultsUrl: this.buildResultsUrl(leagueConfig, season)
    };
  }

  async buildScanTargets(options = {}) {
    const { season, tier = null, leagueIds = null } = options;

    if (!season || typeof season !== 'string') {
      throw new Error('season is required for buildScanTargets');
    }

    const allowedLeagueIds = Array.isArray(leagueIds) && leagueIds.length > 0
      ? new Set(leagueIds.map((id) => Number(id)))
      : null;

    const leagues = this.configManager
      .getActiveLeagues({ tier })
      .filter((league) => league.enabled !== false)
      .filter((league) => !allowedLeagueIds || allowedLeagueIds.has(Number(league.id)));

    return leagues.map((league) => this.buildTarget(season, league));
  }

  async prepareReconPendingTargets(targets, limit = null, options = {}) {
    const prepared = [];

    for (const target of targets) {
      const pendingMatches = await this.loadReconPendingMatches(target, options);
      if (Array.isArray(pendingMatches) && pendingMatches.length > 0) {
        const reconPolicy = this.resolveReconPolicy(target, pendingMatches, options.confidenceThreshold);
        prepared.push({
          target: {
            ...target,
            reconPolicy
          },
          pendingMatches: [...pendingMatches].sort((a, b) =>
            String(a.match_id).localeCompare(String(b.match_id))
          ),
          desiredLimit: null
        });
      }
    }

    if (!Number.isInteger(limit) || limit <= 0) {
      return prepared;
    }

    const capped = prepared.map(({ target, pendingMatches }) => ({
      target,
      pendingMatches,
      desiredLimit: 0
    }));

    let selected = 0;
    let cursor = 0;
    const capacities = prepared.map(({ pendingMatches }) => pendingMatches.length);

    while (selected < limit) {
      let pickedInRound = false;

      for (let index = 0; index < prepared.length && selected < limit; index++) {
        const currentIndex = (cursor + index) % prepared.length;
        if (capped[currentIndex].desiredLimit >= capacities[currentIndex]) {
          continue;
        }

        capped[currentIndex].desiredLimit += 1;
        selected++;
        pickedInRound = true;
      }

      if (!pickedInRound) {
        break;
      }

      cursor = (cursor + 1) % Math.max(prepared.length, 1);
    }

    return capped.filter(({ desiredLimit }) => desiredLimit > 0);
  }

  async loadReconPendingMatches(target, options = {}) {
    if (this.repository && typeof this.repository.getReconEligibleMatches === 'function') {
      return this.repository.getReconEligibleMatches(target.dbSeason, target.league.name, {
        allowMismatchRetry: options.allowMismatchRetry === true
      });
    }

    return this.repository.getUnstitchedMatches(target.dbSeason, target.league.name);
  }

  resolveReconPolicy(target, pendingMatches, confidenceThreshold = 0.5) {
    const configuredRetry = target?.reconPolicy?.allowMismatchRetry === true;
    const hasMismatchRetry = (Array.isArray(pendingMatches) ? pendingMatches : [])
      .some((match) => String(match?.pipeline_status || '').trim().toUpperCase() === 'RECON_MISMATCH');
    const effectiveThreshold = configuredRetry && hasMismatchRetry
      ? Math.max(
        this.mismatchRetryThresholdFloor,
        Number(confidenceThreshold || 0) - this.mismatchRetryThresholdDelta
      )
      : Number(confidenceThreshold || 0);

    return {
      allowMismatchRetry: configuredRetry,
      hasMismatchRetry,
      effectiveConfidenceThreshold: effectiveThreshold,
      forceMultiMode: configuredRetry && hasMismatchRetry
    };
  }

  buildCandidateSources(target) {
    const baseSeason = this.formatSeasonForUrl(target.season || target.dbSeason);
    const strategy = this.getResultsUrlStrategy(target?.league);
    const currentSeasonYears = this.parseSeasonYears(baseSeason);
    const pendingYears = this.getPendingMatchYears(target?.pendingMatches);
    const sources = [];
    const seen = new Set();

    const addSource = (source) => {
      if (!source?.url || seen.has(source.url)) {
        return;
      }
      seen.add(source.url);
      sources.push(source);
    };

    if (strategy === 'seasonless') {
      addSource({
        season: currentSeasonYears?.endYear ? String(currentSeasonYears.endYear) : baseSeason,
        url: this.buildLeagueUrl(target.league),
        mode: 'current_season'
      });

      for (const year of pendingYears) {
        if (
          !Number.isInteger(year)
          || !Number.isInteger(currentSeasonYears?.endYear)
          || year >= currentSeasonYears.endYear
        ) {
          continue;
        }
        addSource({
          season: String(year),
          url: this.buildSeasonlessHistoricalResultsUrl(target.league, year),
          mode: 'historical_results'
        });
      }

      return sources;
    }

    addSource({
      season: baseSeason,
      url: this.buildResultsUrl(target.league, baseSeason),
      mode: 'results_archive'
    });
    return sources;
  }

  async selectCandidateSource(target, pendingMatches, confidenceThreshold) {
    if (
      !this.navigator ||
      (
        typeof this.navigator.fetchFullSeasonArchive !== 'function' &&
        typeof this.navigator.protocolArchiveExtract !== 'function'
      )
    ) {
      throw new Error('ReconTaskPlanner requires a navigator with fetchFullSeasonArchive or protocolArchiveExtract');
    }

    const futureFinalsWindow = this.getFutureFinalsWindow(target, pendingMatches);
    if (futureFinalsWindow.shouldSkip) {
      this.logger.info('skipping_future_finals', {
        league: target.league.name,
        dbSeason: target.dbSeason,
        kickoffDate: futureFinalsWindow.kickoffDate,
        pendingTotal: pendingMatches.length
      });
      return {
        source: {
          season: this.formatSeasonForUrl(target.season || target.dbSeason),
          url: target.resultsUrl
        },
        extractResult: {
          matches: [],
          pagesScanned: 0,
          totalCandidates: 0,
          sourceState: 'SKIPPED_FUTURE_FINALS'
        },
        candidates: [],
        seasonMirror: new Map(),
        sampleLinked: 0
      };
    }

    const orderedPending = [...pendingMatches]
      .sort((a, b) => String(a.match_id).localeCompare(String(b.match_id)));
    const eligibleSamplePool = this.filterPlaceholderFixtures(orderedPending);
    const sample = eligibleSamplePool.slice(0, Math.min(this.sampleSize, eligibleSamplePool.length));
    const skippedPlaceholderCount = orderedPending.length - eligibleSamplePool.length;
    const sources = this.buildCandidateSources({
      ...target,
      pendingMatches: orderedPending
    });
    const reconPolicy = this.resolveReconPolicy(target, orderedPending, confidenceThreshold);
    const effectiveConfidenceThreshold = Number(reconPolicy.effectiveConfidenceThreshold || confidenceThreshold || 0);
    const forceDomMode = this.forceDomLeagueIds.has(Number(target?.leagueId || target?.league?.id || 0));
    const forceMultiMode = reconPolicy.forceMultiMode === true;
    let best = null;
    const evaluatedSources = [];

    for (const source of sources) {
      const extractOptions = {
        maxPages: this.archiveMaxPages,
        timeoutMs: this.archiveTimeoutMs,
        preferCurrentSeasonSource: this.isCurrentSeason(source.season)
      };
      if (target.readySelector) {
        extractOptions.readySelector = target.readySelector;
      }
      const extractResult = forceDomMode && typeof this.navigator?.fetchFullSeasonArchive === 'function'
        ? await this.navigator.fetchFullSeasonArchive(source.url, {
          ...extractOptions,
          preferCurrentSeasonSource: true,
          forceDomOnly: true
        })
        : forceMultiMode && typeof this.navigator?.fetchFullSeasonArchive === 'function'
          ? await this.navigator.fetchFullSeasonArchive(source.url, {
            ...extractOptions,
            preferCurrentSeasonSource: true
          })
        : source.mode === 'current_season'
          ? await this.navigator.protocolArchiveExtract(source.url, {
            ...extractOptions,
            preferCurrentSeasonSource: true
          })
          : typeof this.navigator?.fetchFullSeasonArchive === 'function'
            ? await this.navigator.fetchFullSeasonArchive(source.url, extractOptions)
            : await this.navigator.protocolArchiveExtract(source.url, extractOptions);
      const candidates = Array.isArray(extractResult?.matches) ? extractResult.matches : [];
      const seasonMirror = this.mirrorManager?.buildSeasonMirror(candidates) || new Map();
      const sampleLinked = sample.reduce((count, l1Match) => {
        const matched = this.matchEvaluator?.findBestCandidate(l1Match, candidates, seasonMirror);
        return matched && matched.confidence >= effectiveConfidenceThreshold ? count + 1 : count;
      }, 0);

      const evaluated = {
        source,
        extractResult,
        candidates,
        seasonMirror,
        sampleLinked
      };

      this.logger.info('recon_candidate_source_evaluated', {
        league: target.league.name,
        dbSeason: target.dbSeason,
        requestedSeason: target.season,
        sourceSeason: source.season,
        sourceUrl: source.url,
        forceDomMode,
        forceMultiMode,
        effectiveConfidenceThreshold,
        sampleSize: sample.length,
        skippedPlaceholderCount,
        sampleLinked,
        candidateCount: candidates.length,
        sourceState: extractResult?.sourceState || null
      });

      evaluatedSources.push(evaluated);

      if (
        !best ||
        evaluated.sampleLinked > best.sampleLinked ||
        (
          evaluated.sampleLinked === best.sampleLinked &&
          evaluated.candidates.length > best.candidates.length
        )
      ) {
        best = evaluated;
      }
    }

    if (evaluatedSources.length > 1) {
      const combinedCandidates = [];
      const seenCandidateKeys = new Set();

      for (const evaluated of evaluatedSources) {
        for (const candidate of evaluated.candidates) {
          const key = candidate?.hash || candidate?.url;
          if (!key || seenCandidateKeys.has(key)) {
            continue;
          }
          seenCandidateKeys.add(key);
          combinedCandidates.push(candidate);
        }
      }

      const combinedSeasonMirror = this.mirrorManager?.buildSeasonMirror(combinedCandidates) || new Map();
      const combinedSampleLinked = sample.reduce((count, l1Match) => {
        const matched = this.matchEvaluator?.findBestCandidate(l1Match, combinedCandidates, combinedSeasonMirror);
        return matched && matched.confidence >= effectiveConfidenceThreshold ? count + 1 : count;
      }, 0);

      this.logger.info('recon_candidate_sources_combined', {
        league: target.league.name,
        dbSeason: target.dbSeason,
        sourceCount: evaluatedSources.length,
        candidateCount: combinedCandidates.length,
        sampleSize: sample.length,
        sampleLinked: combinedSampleLinked,
        effectiveConfidenceThreshold,
        forceMultiMode
      });

      return {
        source: {
          season: evaluatedSources.map((item) => item.source.season).join(','),
          url: evaluatedSources.map((item) => item.source.url).join(' | ')
        },
        sources: evaluatedSources.map((item) => item.source),
        extractResult: {
          matches: combinedCandidates,
          pagesScanned: evaluatedSources.reduce((sum, item) => sum + Number(item.extractResult?.pagesScanned || 0), 0),
          totalCandidates: combinedCandidates.length,
          sourceState: combinedCandidates.length > 0 ? 'MULTI_SOURCE_SWEEP' : 'SOURCE_EMPTY'
        },
        candidates: combinedCandidates,
        seasonMirror: combinedSeasonMirror,
        sampleLinked: combinedSampleLinked
      };
    }

    return best || {
      source: {
        season: this.formatSeasonForUrl(target.season || target.dbSeason),
        url: target.resultsUrl
      },
      extractResult: { matches: [], pagesScanned: 0, totalCandidates: 0, sourceState: 'SOURCE_EMPTY' },
      candidates: [],
      seasonMirror: new Map(),
      sampleLinked: 0
    };
  }

  selectProcessablePendingMatches(pendingMatches, candidates, confidenceThreshold, matchLimit = null, seasonMirror = null) {
    const orderedPending = [...pendingMatches].sort((a, b) =>
      String(a.match_id).localeCompare(String(b.match_id))
    );

    if (!Number.isInteger(matchLimit) || matchLimit <= 0 || orderedPending.length <= matchLimit) {
      return orderedPending;
    }

    const ranked = orderedPending.map((match) => {
      const candidateMatch = this.matchEvaluator?.findBestCandidate(match, candidates, seasonMirror);
      return {
        match,
        confidence: candidateMatch?.confidence || 0,
        matchDate: match.match_date || null
      };
    });

    const linkedFirst = ranked
      .filter((item) => item.confidence >= confidenceThreshold)
      .sort((left, right) => {
        if (right.confidence !== left.confidence) {
          return right.confidence - left.confidence;
        }

        const rightDate = right.matchDate ? new Date(right.matchDate).getTime() : 0;
        const leftDate = left.matchDate ? new Date(left.matchDate).getTime() : 0;
        if (rightDate !== leftDate) {
          return rightDate - leftDate;
        }

        return String(right.match.match_id).localeCompare(String(left.match.match_id));
      })
      .slice(0, matchLimit)
      .map((item) => item.match);

    if (linkedFirst.length >= matchLimit) {
      return linkedFirst;
    }

    const selectedIds = new Set(linkedFirst.map((item) => item.match_id));
    const fallbackMatches = orderedPending
      .filter((item) => !selectedIds.has(item.match_id))
      .slice(0, matchLimit - linkedFirst.length);

    return [...linkedFirst, ...fallbackMatches];
  }

  formatSeasonForUrl(season) {
    if (!season) return '';
    return String(season).replace('/', '-');
  }

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
  }

  normalizeDbSeason(season) {
    return String(season || '').replace('-', '/');
  }

  filterPlaceholderFixtures(matches = []) {
    if (!this.matchEvaluator || typeof this.matchEvaluator.isPlaceholderFixture !== 'function') {
      return Array.isArray(matches) ? [...matches] : [];
    }

    return (Array.isArray(matches) ? matches : []).filter(
      (match) => !this.matchEvaluator.isPlaceholderFixture(match)
    );
  }

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
  }

  shiftSeason(season, delta) {
    const normalized = this.formatSeasonForUrl(season);
    const match = normalized.match(/^(\d{4})-(\d{4})$/);
    if (!match) {
      return normalized;
    }

    const start = Number(match[1]) + Number(delta || 0);
    const end = Number(match[2]) + Number(delta || 0);
    return `${start}-${end}`;
  }

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
  }

  getPendingMatchYears(pendingMatches = []) {
    return [...new Set(
      (Array.isArray(pendingMatches) ? pendingMatches : [])
        .map((match) => new Date(match?.match_date))
        .filter((date) => Number.isFinite(date.getTime()))
        .map((date) => date.getUTCFullYear())
    )].sort((left, right) => left - right);
  }

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
  }

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
  }

  getResultsUrlStrategy(leagueConfig = {}) {
    return String(
      leagueConfig.resultsUrlStrategy
      || leagueConfig.results_url_strategy
      || 'seasonal'
    ).trim().toLowerCase();
  }

  buildLeagueUrl(leagueConfig) {
    const country = this.normalizePathSegment(leagueConfig.country);
    const slug = String(leagueConfig.resultsSlug || leagueConfig.slug || '')
      .trim()
      .toLowerCase();
    const normalizedBaseUrl = String(this.baseUrl || '').replace(/\/+$/, '');
    return `${normalizedBaseUrl}/football/${country}/${slug}/`;
  }

  buildSeasonlessHistoricalResultsUrl(leagueConfig, year) {
    const country = this.normalizePathSegment(leagueConfig.country);
    const slug = String(leagueConfig.resultsSlug || leagueConfig.slug || '')
      .trim()
      .toLowerCase();
    const normalizedBaseUrl = String(this.baseUrl || '').replace(/\/+$/, '');
    return `${normalizedBaseUrl}/football/${country}/${slug}-${year}/results/`;
  }

  slugIncludesYear(slug) {
    return /(?:^|-)(?:19|20)\d{2}(?:-|$)/.test(String(slug || '').trim().toLowerCase());
  }

  normalizePathSegment(value) {
    return String(value || '')
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-+|-+$/g, '');
  }
}

module.exports = { ReconTaskPlanner };
