/* eslint-disable complexity, max-lines */
'use strict';

const DEFAULT_PROTOCOL_PAGE_SIZE = 50;
const INCOMPLETE_SOURCE_ERROR_CODE = 'RECON_SOURCE_INCOMPLETE';
const RESULTS_RESTRICTED_SOURCE_MODES = new Set([
  'current_season',
  'current_results',
  'current_results_fallback',
  'historical_results',
  'results_archive',
  'results_archive_fallback'
]);

function resolvePendingMatchTimestamp(match = null) {
  const timestamp = new Date(match?.match_date || match?.matchDate || '').getTime();
  return Number.isFinite(timestamp) ? timestamp : null;
}

function isFuturePendingMatch(match = null, now = new Date()) {
  const kickoffAt = resolvePendingMatchTimestamp(match);
  return kickoffAt !== null && kickoffAt > now.getTime();
}

function filterResultsRestrictedSourcesForFutureOnlyPending(sources = [], pendingMatches = [], now = new Date()) {
  const matches = Array.isArray(pendingMatches) ? pendingMatches : [];
  if (matches.length === 0 || !matches.every((match) => isFuturePendingMatch(match, now))) {
    return sources;
  }

  return (Array.isArray(sources) ? sources : []).filter((source) => (
    !RESULTS_RESTRICTED_SOURCE_MODES.has(String(source?.mode || '').trim())
  ));
}

function resolveMatrixModePruning(target, options = {}) {
  return options.matrixModePruning === true || target?.matrixModePruning === true;
}

function resolveMatrixShortCircuitRatio(target, options = {}) {
  const rawRatio = Number(
    options.matrixModeShortCircuitRatio
    ?? target?.matrixModeShortCircuitRatio
    ?? 0.5
  );

  if (!Number.isFinite(rawRatio)) {
    return 0.5;
  }

  return Math.min(1, Math.max(0, rawRatio));
}

function resolveSeasonlessSourceYear(source = {}) {
  const normalizedSeason = String(source?.season || '').trim();
  if (!/^\d{4}$/.test(normalizedSeason)) {
    return null;
  }

  const year = Number(normalizedSeason);
  return Number.isInteger(year) ? year : null;
}

function resolvePureProtocolLimitedMaxPages(maxPages, matchLimit) {
  if (!Number.isInteger(matchLimit) || matchLimit <= 0) {
    return maxPages;
  }

  return Math.min(maxPages, Math.max(3, matchLimit * 5));
}

function resolveRequiredCandidateFloor(pendingMatches = [], matchLimit = null) {
  const pendingTotal = Array.isArray(pendingMatches) ? pendingMatches.length : 0;
  if (!Number.isInteger(matchLimit) || matchLimit <= 0) {
    return pendingTotal;
  }

  return pendingTotal > 0
    ? Math.min(matchLimit, pendingTotal)
    : matchLimit;
}

function hasCandidateSourcePageFailure(stat = {}) {
  return Boolean(
    stat?.error
    || stat?.bodySignal
    || (Number(stat?.statusCode || 0) >= 400)
  );
}

function shouldUseTargetDrivenSingleMatch(matchLimit, orderedPending = [], sample = []) {
  return Number.isInteger(matchLimit)
    && matchLimit === 1
    && Array.isArray(orderedPending)
    && orderedPending.length === 1
    && Array.isArray(sample)
    && sample.length === 1;
}

function shouldDeferMatrixEmptyShortCircuit(sources = [], sourceIndex = 0, source = {}) {
  const currentSeason = String(source?.season || '').trim();
  if (!currentSeason) {
    return false;
  }

  return sources.slice(sourceIndex + 1).some((candidateSource) => {
    if (!candidateSource || typeof candidateSource !== 'object') {
      return false;
    }

    if (String(candidateSource.season || '').trim() !== currentSeason) {
      return false;
    }

    return String(candidateSource.mode || '').trim().startsWith('current_');
  });
}

function buildTargetDrivenSingleMatchSelection(context, sampleMatch, candidates, effectiveConfidenceThreshold) {
  const matched = context.matchEvaluator?.findBestCandidate(sampleMatch, candidates, null) || null;
  const targetDrivenCandidates = matched?.candidate ? [matched.candidate] : [];
  const targetDrivenCandidateMap = new Map();
  if (targetDrivenCandidates.length > 0 && sampleMatch?.match_id) {
    targetDrivenCandidateMap.set(String(sampleMatch.match_id), targetDrivenCandidates);
  }

  return {
    seasonMirror: new Map(),
    sampleLinked: matched && matched.confidence >= effectiveConfidenceThreshold ? 1 : 0,
    targetDrivenCandidateMap,
    targetDrivenBestMatch: matched
      ? {
        matchId: String(sampleMatch?.match_id || ''),
        confidence: Number(matched.confidence || 0),
        candidateHash: matched.candidate?.hash || null,
        candidateUrl: matched.candidate?.url || null
      }
      : null
  };
}

const reconTaskPlannerSourceSelector = {
  _resolveCandidateSourceHealth(extractResult, pendingMatches = [], options = {}) {
    const pageStats = Array.isArray(extractResult?.pageStats) ? extractResult.pageStats : [];
    const pageFailureCount = pageStats.reduce(
      (count, stat) => count + (hasCandidateSourcePageFailure(stat) ? 1 : 0),
      0
    );
    const candidateCount = Array.isArray(extractResult?.matches)
      ? extractResult.matches.length
      : Math.max(0, Number(extractResult?.totalCandidates || 0) || 0);
    const requiredCandidateFloor = resolveRequiredCandidateFloor(pendingMatches, options.matchLimit);
    const candidateShortfall = requiredCandidateFloor > 0
      ? Math.max(0, requiredCandidateFloor - candidateCount)
      : 0;
    const observedPages = Math.max(
      pageStats.length,
      Math.max(0, Number(extractResult?.pagesScanned || 0) || 0)
    );
    const maxObservedTotal = pageStats.reduce(
      (maxTotal, stat) => Math.max(maxTotal, Math.max(0, Number(stat?.total || 0) || 0)),
      Math.max(0, Number(extractResult?.totalCandidates || 0) || 0)
    );
    const pageSize = Math.max(1, Number(options.pageSize || DEFAULT_PROTOCOL_PAGE_SIZE) || DEFAULT_PROTOCOL_PAGE_SIZE);
    const expectedPages = maxObservedTotal > 0
      ? Math.ceil(maxObservedTotal / pageSize)
      : 0;
    const incompleteReasons = [];

    if (pageFailureCount > 0) {
      incompleteReasons.push('page_failure');
    }
    if (
      options.forcePureProtocol === true
      && Number.isInteger(options.matchLimit)
      && options.matchLimit > 0
      && candidateShortfall > 0
    ) {
      incompleteReasons.push('candidate_shortfall');
    }
    if (pageFailureCount > 0 && expectedPages > 0 && observedPages < expectedPages) {
      incompleteReasons.push('expected_pages_unmet');
    }

    return {
      incomplete: incompleteReasons.length > 0,
      incompleteReasons,
      pageFailureCount,
      observedPages,
      expectedPages,
      maxObservedTotal,
      requiredCandidateFloor,
      candidateShortfall,
      candidateCount
    };
  },

  _buildIncompleteSourceError(target, source, sourceHealth, breakerKey) {
    const error = new Error(INCOMPLETE_SOURCE_ERROR_CODE);
    error.code = INCOMPLETE_SOURCE_ERROR_CODE;
    error.retryable = true;
    error.shouldSwitchProxy = true;
    error.league = target?.league?.name || null;
    error.season = target?.dbSeason || null;
    error.sourceSeason = source?.season || null;
    error.sourceUrl = source?.url || null;
    error.breakerKey = breakerKey || null;
    error.incompleteReasons = [...(sourceHealth?.incompleteReasons || [])];
    error.pageFailureCount = Number(sourceHealth?.pageFailureCount || 0);
    error.expectedPages = Number(sourceHealth?.expectedPages || 0);
    error.observedPages = Number(sourceHealth?.observedPages || 0);
    error.requiredCandidateFloor = Number(sourceHealth?.requiredCandidateFloor || 0);
    error.candidateCount = Number(sourceHealth?.candidateCount || 0);
    error.candidateShortfall = Number(sourceHealth?.candidateShortfall || 0);
    return error;
  },

  _shouldAllowPureProtocolLimitShortCircuit(target, pendingMatches, source) {
    if (this.getResultsUrlStrategy(target?.league) !== 'seasonless') {
      return true;
    }

    const pendingYears = this.getPendingMatchYears(pendingMatches);
    if (pendingYears.length === 0) {
      return true;
    }

    const sourceYear = resolveSeasonlessSourceYear(source);
    if (!Number.isInteger(sourceYear)) {
      return true;
    }

    return pendingYears.includes(sourceYear);
  },

  _prioritizePureProtocolLimitSources(target, pendingMatches, sources = [], options = {}) {
    if (!(options.forcePureProtocol && options.matchLimit)) {
      return sources;
    }

    if (this.getResultsUrlStrategy(target?.league) !== 'seasonless') {
      return sources;
    }

    const pendingYears = this.getPendingMatchYears(pendingMatches);
    if (pendingYears.length === 0) {
      return sources;
    }

    const pendingYearSet = new Set(pendingYears);
    const ranked = sources.map((source, index) => ({
      source,
      index,
      aligned: pendingYearSet.has(resolveSeasonlessSourceYear(source))
    }));
    if (!ranked.some((item) => item.aligned)) {
      return sources;
    }

    return ranked
      .sort((left, right) => {
        if (left.aligned !== right.aligned) {
          return Number(right.aligned) - Number(left.aligned);
        }

        return left.index - right.index;
      })
      .map((item) => item.source);
  },

  buildCandidateSources(target) {
    const baseSeason = this.formatSeasonForUrl(target.season || target.dbSeason);
    const strategy = this.getResultsUrlStrategy(target?.league);
    const currentSeasonYears = this.parseSeasonYears(baseSeason);
    const dbSeasonYears = this.parseSeasonYears(this.formatSeasonForUrl(target?.dbSeason));
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

    if (this.isAnnualLeague(target?.league)) {
      for (const source of this.buildAnnualCurrentSeasonSources(target.league, target.season || target.dbSeason)) {
        addSource(source);
      }
      const filteredSources = filterResultsRestrictedSourcesForFutureOnlyPending(
        sources,
        target?.pendingMatches,
        new Date()
      );
      if (filteredSources.length !== sources.length) {
        this.logger?.info?.('recon_future_match_results_sources_filtered', {
          league: target?.league?.name || null,
          dbSeason: target?.dbSeason || null,
          pendingTotal: Array.isArray(target?.pendingMatches) ? target.pendingMatches.length : 0,
          removedModes: sources
            .filter((source) => !filteredSources.includes(source))
            .map((source) => source?.mode)
        });
      }
      return filteredSources;
    }

    if (strategy === 'seasonless') {
      const currentYearBasis = this.getSeasonlessCurrentYearBasis(target?.league);
      const currentSeasonYear = (
        currentYearBasis === 'start'
          ? currentSeasonYears?.startYear || dbSeasonYears?.startYear
          : currentSeasonYears?.endYear || dbSeasonYears?.endYear
      )
        || (Number(/^\d{4}$/.test(baseSeason) ? baseSeason : NaN) || null);

      const currentSourceUrls = this.buildCurrentSeasonSourceUrls(target.league, target.season || target.dbSeason);
      for (const url of currentSourceUrls) {
        addSource({
          season: Number.isInteger(currentSeasonYear) ? String(currentSeasonYear) : baseSeason,
          url,
          mode: 'current_season'
        });
      }

      if (target?.currentSeasonOnly === true) {
        return sources;
      }

      const historicalYears = new Set();

      if (
        currentYearBasis !== 'start'
        && this.isSingleYearLeague(target?.league)
        && Number.isInteger(dbSeasonYears?.startYear)
      ) {
        historicalYears.add(dbSeasonYears.startYear);
      }

      for (const year of pendingYears) {
        if (
          !Number.isInteger(year)
          || !Number.isInteger(currentSeasonYear)
          || year >= currentSeasonYear
        ) {
          continue;
        }
        historicalYears.add(year);
      }

      for (const year of [...historicalYears].sort((left, right) => left - right)) {
        const historicalSourceUrls = this.buildHistoricalSeasonSourceUrls(target.league, year);
        for (const url of historicalSourceUrls) {
          addSource({
            season: String(year),
            url,
            mode: 'historical_results'
          });
        }
      }

      const filteredSources = filterResultsRestrictedSourcesForFutureOnlyPending(
        sources,
        target?.pendingMatches,
        new Date()
      );
      if (filteredSources.length !== sources.length) {
        this.logger?.info?.('recon_future_match_results_sources_filtered', {
          league: target?.league?.name || null,
          dbSeason: target?.dbSeason || null,
          pendingTotal: Array.isArray(target?.pendingMatches) ? target.pendingMatches.length : 0,
          removedModes: sources
            .filter((source) => !filteredSources.includes(source))
            .map((source) => source?.mode)
        });
      }
      return filteredSources;
    }

    const seasonalSourceUrls = typeof this.buildSeasonalSourceUrls === 'function'
      ? this.buildSeasonalSourceUrls(target.league, baseSeason, { dbSeason: target?.dbSeason })
      : [this.buildResultsUrl(target.league, baseSeason)];

    seasonalSourceUrls.forEach((url, index) => {
      addSource({
        season: baseSeason,
        url,
        mode: index === 0 ? 'results_archive' : 'results_archive_fallback'
      });
    });
    const filteredSources = filterResultsRestrictedSourcesForFutureOnlyPending(
      sources,
      target?.pendingMatches,
      new Date()
    );
    if (filteredSources.length !== sources.length) {
      this.logger?.info?.('recon_future_match_results_sources_filtered', {
        league: target?.league?.name || null,
        dbSeason: target?.dbSeason || null,
        pendingTotal: Array.isArray(target?.pendingMatches) ? target.pendingMatches.length : 0,
        removedModes: sources
          .filter((source) => !filteredSources.includes(source))
          .map((source) => source?.mode)
      });
    }
    return filteredSources;
  },

  async selectCandidateSource(target, pendingMatches, confidenceThreshold, options = {}) {
    const navigator = options.navigator || this.navigator;
    const timeoutMs = Math.max(1, Number(options.timeoutMs || this.archiveTimeoutMs));
    const disableTournamentFallback = options.disableTournamentFallback === true;
    const matrixModePruning = resolveMatrixModePruning(target, options);
    if (
      !navigator ||
      (
        typeof navigator.fetchFullSeasonArchive !== 'function'
        && typeof navigator.protocolArchiveExtract !== 'function'
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

    const orderedPending = typeof this.orderPendingMatchesForProcessing === 'function'
      ? this.orderPendingMatchesForProcessing(pendingMatches)
      : [...pendingMatches].sort((a, b) => String(a.match_id).localeCompare(String(b.match_id)));
    const eligibleSamplePool = this.filterPlaceholderFixtures(orderedPending);
    const sample = eligibleSamplePool.slice(0, Math.min(this.sampleSize, eligibleSamplePool.length));
    const sampleTarget = sample.length;
    const sampleLinkedThreshold = matrixModePruning && sampleTarget > 0
      ? Math.max(1, Math.ceil(sampleTarget * resolveMatrixShortCircuitRatio(target, options)))
      : sampleTarget;
    const skippedPlaceholderCount = orderedPending.length - eligibleSamplePool.length;
    let sources = this.buildCandidateSources({
      ...target,
      pendingMatches: orderedPending
    });
    const reconPolicy = this.resolveReconPolicy(target, orderedPending, confidenceThreshold);
    const effectiveConfidenceThreshold = Number(reconPolicy.effectiveConfidenceThreshold || confidenceThreshold || 0);
    const forceDomOnlyMode = target?.forceDomMode === true;
    const forceDomMode = this.forceDomLeagueIds.has(Number(target?.leagueId || target?.league?.id || 0));
    const forceMultiMode = reconPolicy.forceMultiMode === true;
    const forceJsonExtract = target?.forceJsonExtract === true;
    const forcePureProtocol = target?.forcePureProtocol === true;
    const matchLimit = Number.isInteger(target?.matchLimit) && target.matchLimit > 0
      ? target.matchLimit
      : null;
    const resolvedMaxPages = resolvePureProtocolLimitedMaxPages(
      this.resolveArchiveMaxPages(target, orderedPending),
      forcePureProtocol ? matchLimit : null
    );
    sources = this._prioritizePureProtocolLimitSources(target, orderedPending, sources, {
      forcePureProtocol,
      matchLimit
    });
    const circuitBreakerKey = this.buildCircuitBreakerKey(target);
    let best = null;
    const evaluatedSources = [];
    const sourceFailures = [];

    for (const [sourceIndex, source] of sources.entries()) {
      const sourceCircuitBreakerKey = `${circuitBreakerKey}:${source.mode}:${source.season}:${sourceIndex}`;
      const extractOptions = {
        maxPages: resolvedMaxPages,
        timeoutMs,
        preferCurrentSeasonSource: this.isCurrentSeason(source.season),
        circuitBreakerKey: sourceCircuitBreakerKey,
        forcePureProtocol
      };
      if (disableTournamentFallback) {
        extractOptions.disableTournamentFallback = true;
      }
      const rawLeagueDeadlineAt = target?.leagueDeadlineAt ?? options.leagueDeadlineAt;
      const leagueDeadlineAt = rawLeagueDeadlineAt === null || rawLeagueDeadlineAt === undefined
        ? null
        : Number(rawLeagueDeadlineAt);
      if (Number.isFinite(leagueDeadlineAt)) {
        extractOptions.leagueDeadlineAt = leagueDeadlineAt;
      }
      if (target.readySelector) {
        extractOptions.readySelector = target.readySelector;
      }

      let extractResult;
      try {
        if (forcePureProtocol) {
          extractResult = await navigator.protocolArchiveExtract(source.url, {
            ...extractOptions,
            preferCurrentSeasonSource: true,
            forcePureProtocol: true
          });
        } else if (
          (source.mode === 'current_fixtures' || source.mode === 'current_fixtures_fallback')
          && typeof navigator.fetchFullSeasonArchive === 'function'
        ) {
          extractResult = await navigator.fetchFullSeasonArchive(source.url, {
            ...extractOptions,
            preferCurrentSeasonSource: true,
            forceDomOnly: true
          });
        } else if (
          (
            source.mode === 'current_results'
            || source.mode === 'current_results_fallback'
          )
          && typeof navigator.fetchFullSeasonArchive === 'function'
        ) {
          extractResult = await navigator.fetchFullSeasonArchive(source.url, {
            ...extractOptions,
            preferCurrentSeasonSource: true,
            ...(forceDomOnlyMode ? { forceDomOnly: true } : {})
          });
        } else if (forceJsonExtract && typeof navigator.fetchFullSeasonArchive === 'function') {
          extractResult = await navigator.fetchFullSeasonArchive(source.url, {
            ...extractOptions,
            preferCurrentSeasonSource: true,
            forceDomOnly: true,
            forceJsonExtract: true
          });
        } else if (forceDomOnlyMode && typeof navigator.fetchFullSeasonArchive === 'function') {
          extractResult = await navigator.fetchFullSeasonArchive(source.url, {
            ...extractOptions,
            preferCurrentSeasonSource: true,
            forceDomOnly: true
          });
        } else if (forceDomMode && typeof navigator.fetchFullSeasonArchive === 'function') {
          extractResult = await navigator.fetchFullSeasonArchive(source.url, {
            ...extractOptions,
            preferCurrentSeasonSource: true
          });
        } else if (forceMultiMode && typeof navigator.fetchFullSeasonArchive === 'function') {
          extractResult = await navigator.fetchFullSeasonArchive(source.url, {
            ...extractOptions,
            preferCurrentSeasonSource: true
          });
        } else if (source.mode === 'current_season') {
          extractResult = await navigator.protocolArchiveExtract(source.url, {
            ...extractOptions,
            preferCurrentSeasonSource: true
          });
        } else if (typeof navigator.fetchFullSeasonArchive === 'function') {
          extractResult = await navigator.fetchFullSeasonArchive(source.url, extractOptions);
        } else {
          extractResult = await navigator.protocolArchiveExtract(source.url, extractOptions);
        }
      } catch (error) {
        sourceFailures.push({
          source,
          sourceIndex,
          breakerKey: sourceCircuitBreakerKey,
          error
        });
        this.logger.warn('recon_candidate_source_failed', {
          league: target.league.name,
          dbSeason: target.dbSeason,
          sourceSeason: source.season,
          sourceUrl: source.url,
          breakerKey: sourceCircuitBreakerKey,
          error: error.message
        });
        if (error?.code === 'LEAGUE_TIMEOUT') {
          const bestHasUsableCandidates = Array.isArray(best?.candidates)
            && best.candidates.length > 0
            && best?.sourceHealth?.incomplete !== true;
          if (bestHasUsableCandidates) {
            this.logger.warn('recon_candidate_source_timeout_tolerated', {
              league: target.league.name,
              dbSeason: target.dbSeason,
              sourceSeason: source.season,
              sourceUrl: source.url,
              breakerKey: sourceCircuitBreakerKey,
              fallbackError: error.message,
              toleratedSourceUrl: best?.source?.url || null,
              toleratedSourceSeason: best?.source?.season || null,
              toleratedCandidateCount: best.candidates.length,
              toleratedSampleLinked: Number(best?.sampleLinked || 0)
            });
            break;
          }
          throw error;
        }
        continue;
      }

      const candidates = Array.isArray(extractResult?.matches) ? extractResult.matches : [];
      const targetDrivenSingleMatch = shouldUseTargetDrivenSingleMatch(matchLimit, orderedPending, sample);
      const targetDrivenSelection = targetDrivenSingleMatch
        ? buildTargetDrivenSingleMatchSelection(this, sample[0], candidates, effectiveConfidenceThreshold)
        : null;
      const seasonMirror = targetDrivenSelection?.seasonMirror
        || this.mirrorManager?.buildSeasonMirror(candidates)
        || new Map();
      const sampleLinked = targetDrivenSelection
        ? targetDrivenSelection.sampleLinked
        : sample.reduce((count, l1Match) => {
          const matched = this.matchEvaluator?.findBestCandidate(l1Match, candidates, seasonMirror);
          return matched && matched.confidence >= effectiveConfidenceThreshold ? count + 1 : count;
        }, 0);
      const sourceHealth = this._resolveCandidateSourceHealth(extractResult, orderedPending, {
        forcePureProtocol,
        matchLimit
      });

      if (extractResult && typeof extractResult === 'object') {
        extractResult.sourceIncomplete = sourceHealth.incomplete;
        extractResult.sourceHealth = sourceHealth;
      }

      const evaluated = {
        source,
        extractResult,
        candidates,
        seasonMirror,
        sampleLinked,
        sourceHealth,
        targetDrivenSingleMatch,
        targetDrivenCandidateMap: targetDrivenSelection?.targetDrivenCandidateMap || new Map(),
        targetDrivenBestMatch: targetDrivenSelection?.targetDrivenBestMatch || null
      };

      this.logger.info('recon_candidate_source_evaluated', {
        league: target.league.name,
        dbSeason: target.dbSeason,
        requestedSeason: target.season,
        sourceSeason: source.season,
        sourceUrl: source.url,
        forceDomMode,
        forceDomOnlyMode,
        forceJsonExtract,
        forcePureProtocol,
        forceMultiMode,
        sourceMode: source.mode,
        proxyPort: Number(navigator?.proxy?.port || 0) || null,
        effectiveConfidenceThreshold,
        resolvedMaxPages,
        sampleSize: sample.length,
        skippedPlaceholderCount,
        sampleLinked,
        candidateCount: candidates.length,
        sourceState: extractResult?.sourceState || null,
        sourceIncomplete: sourceHealth.incomplete,
        incompleteReasons: sourceHealth.incompleteReasons,
        pageFailureCount: sourceHealth.pageFailureCount,
        observedPages: sourceHealth.observedPages,
        expectedPages: sourceHealth.expectedPages,
        requiredCandidateFloor: sourceHealth.requiredCandidateFloor,
        candidateShortfall: sourceHealth.candidateShortfall,
        targetDrivenSingleMatch
      });

      if (sourceHealth.incomplete) {
        const incompleteError = this._buildIncompleteSourceError(
          target,
          source,
          sourceHealth,
          sourceCircuitBreakerKey
        );
        sourceFailures.push({
          source,
          sourceIndex,
          breakerKey: sourceCircuitBreakerKey,
          error: incompleteError
        });
        this.logger.warn('recon_candidate_source_incomplete', {
          league: target.league.name,
          dbSeason: target.dbSeason,
          sourceSeason: source.season,
          sourceUrl: source.url,
          breakerKey: sourceCircuitBreakerKey,
          sourceMode: source.mode,
          sourceState: extractResult?.sourceState || null,
          incompleteReasons: sourceHealth.incompleteReasons,
          pageFailureCount: sourceHealth.pageFailureCount,
          observedPages: sourceHealth.observedPages,
          expectedPages: sourceHealth.expectedPages,
          requiredCandidateFloor: sourceHealth.requiredCandidateFloor,
          candidateCount: sourceHealth.candidateCount,
          candidateShortfall: sourceHealth.candidateShortfall
        });
        continue;
      }

      evaluatedSources.push(evaluated);

      if (
        !best
        || evaluated.sampleLinked > best.sampleLinked
        || (
          evaluated.sampleLinked === best.sampleLinked
          && evaluated.candidates.length > best.candidates.length
        )
      ) {
        best = evaluated;
      }

      if (
        matrixModePruning
        && sourceIndex === 0
        && evaluated.candidates.length === 0
      ) {
        if (shouldDeferMatrixEmptyShortCircuit(sources, sourceIndex, source)) {
          this.logger.info('recon_candidate_source_matrix_empty_short_circuit_deferred', {
            league: target.league.name,
            dbSeason: target.dbSeason,
            sourceSeason: source.season,
            sourceUrl: source.url,
            sourceMode: source.mode,
            sourceState: extractResult?.sourceState || 'SOURCE_EMPTY',
            deferredSources: sources.slice(sourceIndex + 1)
              .filter((candidateSource) => String(candidateSource?.season || '').trim() === String(source.season || '').trim())
              .map((candidateSource) => ({
                season: candidateSource.season,
                url: candidateSource.url,
                mode: candidateSource.mode
              }))
          });
          continue;
        }

        this.logger.info('recon_candidate_source_matrix_empty_short_circuit', {
          league: target.league.name,
          dbSeason: target.dbSeason,
          sourceSeason: source.season,
          sourceUrl: source.url,
          sourceMode: source.mode,
          sourceState: extractResult?.sourceState || 'SOURCE_EMPTY',
          skippedSources: Math.max(0, sources.length - evaluatedSources.length)
        });
        break;
      }

      if (
        forcePureProtocol
        && matchLimit
        && sourceIndex === 0
        && evaluated.candidates.length > 0
      ) {
        if (!this._shouldAllowPureProtocolLimitShortCircuit(target, orderedPending, source)) {
          this.logger.info('recon_candidate_source_limit_short_circuit_deferred', {
            league: target.league.name,
            dbSeason: target.dbSeason,
            sourceSeason: source.season,
            sourceUrl: source.url,
            sourceMode: source.mode,
            matchLimit,
            candidateCount: evaluated.candidates.length,
            pendingYears: this.getPendingMatchYears(orderedPending)
          });
          continue;
        }

        this.logger.info('recon_candidate_source_limit_short_circuit', {
          league: target.league.name,
          dbSeason: target.dbSeason,
          sourceSeason: source.season,
          sourceUrl: source.url,
          sourceMode: source.mode,
          matchLimit,
          candidateCount: evaluated.candidates.length,
          sampleLinked: evaluated.sampleLinked
        });
        break;
      }

      if (sampleLinkedThreshold > 0 && best?.sampleLinked >= sampleLinkedThreshold) {
        this.logger.info('recon_candidate_source_short_circuit', {
          league: target.league.name,
          dbSeason: target.dbSeason,
          sourceSeason: source.season,
          sourceUrl: source.url,
          sourceMode: source.mode,
          sampleSize: sampleTarget,
          sampleLinked: best.sampleLinked,
          sampleLinkedThreshold,
          matrixModePruning,
          evaluatedSources: evaluatedSources.length
        });
        break;
      }
    }

    if (evaluatedSources.length === 0 && sourceFailures.length > 0) {
      const primaryFailure = sourceFailures[0];
      const error = primaryFailure.error instanceof Error
        ? primaryFailure.error
        : new Error(String(primaryFailure.error || 'Recon candidate source failed'));
      error.sourceFailures = sourceFailures.map((failure) => ({
        sourceSeason: failure.source?.season,
        sourceUrl: failure.source?.url,
        breakerKey: failure.breakerKey,
        error: failure.error instanceof Error ? failure.error.message : String(failure.error || '')
      }));
      throw error;
    }

    if (forceMultiMode && evaluatedSources.length > 1) {
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
        resolvedMaxPages,
        forceMultiMode
      });

      return {
        source: {
          season: [...new Set(evaluatedSources.map((item) => item.source.season))].join(','),
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
};

module.exports = { reconTaskPlannerSourceSelector };
