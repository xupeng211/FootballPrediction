'use strict';

const reconTaskPlannerSourceSelector = {
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

    if (strategy === 'seasonless') {
      const currentSeasonYear = currentSeasonYears?.endYear
        || dbSeasonYears?.endYear
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

      if (this.isSingleYearLeague(target?.league) && Number.isInteger(dbSeasonYears?.startYear)) {
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

      return sources;
    }

    addSource({
      season: baseSeason,
      url: this.buildResultsUrl(target.league, baseSeason),
      mode: 'results_archive'
    });
    return sources;
  },

  async selectCandidateSource(target, pendingMatches, confidenceThreshold) {
    if (
      !this.navigator ||
      (
        typeof this.navigator.fetchFullSeasonArchive !== 'function'
        && typeof this.navigator.protocolArchiveExtract !== 'function'
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
    const resolvedMaxPages = this.resolveArchiveMaxPages(target, orderedPending);
    const forceDomMode = this.forceDomLeagueIds.has(Number(target?.leagueId || target?.league?.id || 0));
    const forceMultiMode = reconPolicy.forceMultiMode === true;
    const forceJsonExtract = target?.forceJsonExtract === true;
    const forcePureProtocol = target?.forcePureProtocol === true;
    const circuitBreakerKey = this.buildCircuitBreakerKey(target);
    let best = null;
    const evaluatedSources = [];
    const sourceFailures = [];

    for (const [sourceIndex, source] of sources.entries()) {
      const sourceCircuitBreakerKey = `${circuitBreakerKey}:${source.mode}:${source.season}:${sourceIndex}`;
      const extractOptions = {
        maxPages: resolvedMaxPages,
        timeoutMs: this.archiveTimeoutMs,
        preferCurrentSeasonSource: this.isCurrentSeason(source.season),
        circuitBreakerKey: sourceCircuitBreakerKey,
        forcePureProtocol
      };
      if (target.readySelector) {
        extractOptions.readySelector = target.readySelector;
      }

      let extractResult;
      try {
        extractResult = forcePureProtocol
          ? await this.navigator.protocolArchiveExtract(source.url, {
            ...extractOptions,
            preferCurrentSeasonSource: true,
            forcePureProtocol: true
          })
          : forceJsonExtract && typeof this.navigator?.fetchFullSeasonArchive === 'function'
          ? await this.navigator.fetchFullSeasonArchive(source.url, {
            ...extractOptions,
            preferCurrentSeasonSource: true,
            forceDomOnly: true,
            forceJsonExtract: true
          })
          : forceDomMode && typeof this.navigator?.fetchFullSeasonArchive === 'function'
          ? await this.navigator.fetchFullSeasonArchive(source.url, {
            ...extractOptions,
            preferCurrentSeasonSource: true
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
        continue;
      }

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
        forceJsonExtract,
        forcePureProtocol,
        forceMultiMode,
        effectiveConfidenceThreshold,
        resolvedMaxPages,
        sampleSize: sample.length,
        skippedPlaceholderCount,
        sampleLinked,
        candidateCount: candidates.length,
        sourceState: extractResult?.sourceState || null
      });

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
        resolvedMaxPages,
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
};

module.exports = { reconTaskPlannerSourceSelector };
