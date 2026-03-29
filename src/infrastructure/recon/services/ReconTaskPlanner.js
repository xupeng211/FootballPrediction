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
  }

  buildTarget(season, leagueConfig) {
    return {
      leagueId: Number(leagueConfig?.id || 0),
      league: leagueConfig,
      season: this.formatSeasonForUrl(season),
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

  async prepareReconPendingTargets(targets, limit = null) {
    const prepared = [];

    for (const target of targets) {
      const pendingMatches = await this.loadReconPendingMatches(target);
      if (Array.isArray(pendingMatches) && pendingMatches.length > 0) {
        prepared.push({
          target,
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

  async loadReconPendingMatches(target) {
    if (this.repository && typeof this.repository.getReconEligibleMatches === 'function') {
      return this.repository.getReconEligibleMatches(target.dbSeason, target.league.name);
    }

    return this.repository.getUnstitchedMatches(target.dbSeason, target.league.name);
  }

  buildCandidateSources(target) {
    const baseSeason = this.formatSeasonForUrl(target.season || target.dbSeason);
    return [{
      season: baseSeason,
      url: this.buildResultsUrl(target.league, baseSeason)
    }];
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
    const sources = this.buildCandidateSources(target);
    let best = null;

    for (const source of sources) {
      const extractOptions = {
        maxPages: this.archiveMaxPages,
        timeoutMs: this.archiveTimeoutMs,
        preferCurrentSeasonSource: this.isCurrentSeason(source.season)
      };
      const extractResult = typeof this.navigator?.fetchFullSeasonArchive === 'function'
        ? await this.navigator.fetchFullSeasonArchive(source.url, extractOptions)
        : await this.navigator.protocolArchiveExtract(source.url, extractOptions);
      const candidates = Array.isArray(extractResult?.matches) ? extractResult.matches : [];
      const seasonMirror = this.mirrorManager?.buildSeasonMirror(candidates) || new Map();
      const sampleLinked = sample.reduce((count, l1Match) => {
        const matched = this.matchEvaluator?.findBestCandidate(l1Match, candidates, seasonMirror);
        return matched && matched.confidence >= confidenceThreshold ? count + 1 : count;
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
        sampleSize: sample.length,
        skippedPlaceholderCount,
        sampleLinked,
        candidateCount: candidates.length,
        sourceState: extractResult?.sourceState || null
      });

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

  isCurrentSeason(season) {
    const normalized = this.formatSeasonForUrl(season);
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
    const oddsportalSeason = this.formatSeasonForUrl(season);
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
