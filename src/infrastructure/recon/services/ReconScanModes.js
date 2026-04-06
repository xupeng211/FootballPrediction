'use strict';

const reconScanModes = {
  async protocolArchiveScan(season, leagueConfig) {
    const startTime = Date.now();
    const dbSeason = this.taskPlanner.normalizeDbSeason(season);

    this.logger.info('protocol_archive_scan_start', { season, dbSeason, league: leagueConfig.name });

    try {
      const unstitched = await this.taskPlanner.loadReconPendingMatches({ dbSeason, league: leagueConfig }, {
        allNonLinked: this.allNonLinked === true
      });
      if (unstitched.length === 0) {
        return { success: true, season, league: leagueConfig.name, inserted: 0, reason: 'no_pending_matches' };
      }

      const resultsUrl = this.taskPlanner.buildResultsUrl(leagueConfig, season);
      const preferCurrentSeasonSource = leagueConfig?.defaultSeason === dbSeason;
      const circuitBreakerKey = typeof this.taskPlanner?.buildCircuitBreakerKey === 'function'
        ? this.taskPlanner.buildCircuitBreakerKey({
          leagueId: Number(leagueConfig?.id || 0),
          league: leagueConfig,
          dbSeason
        })
        : undefined;
      const extractResult = await this.navigator.protocolArchiveExtract(resultsUrl, {
        maxPages: this.archiveMaxPages,
        timeoutMs: this.archiveTimeoutMs,
        preferCurrentSeasonSource,
        circuitBreakerKey
      });

      this.logger.info('protocol_extract_complete', { candidates: extractResult.matches.length, pagesScanned: extractResult.pagesScanned });

      const { inserted, unmatched } = await this._matchAndStitch(
        extractResult.matches,
        unstitched,
        dbSeason,
        leagueConfig
      );

      let reconciled = 0;
      if (unmatched > 0 && this.stitcher?.setReconciliation) {
        const recResult = await this.stitcher.setReconciliation(
          extractResult.matches,
          unstitched,
          dbSeason,
          leagueConfig
        );
        reconciled = recResult.inserted || 0;
      }

      const totalInserted = inserted + reconciled;
      const coverage = unstitched.length > 0 ? (totalInserted / unstitched.length * 100).toFixed(2) : '0.00';

      return {
        success: true,
        season,
        league: leagueConfig.name,
        pendingTotal: unstitched.length,
        candidatesFound: extractResult.matches.length,
        inserted: totalInserted,
        unmatched: unmatched - reconciled,
        coverage: parseFloat(coverage),
        durationMs: Date.now() - startTime
      };
    } catch (error) {
      this.logger.error('protocol_archive_scan_failed', { error: error.message });
      return { success: false, season, league: leagueConfig.name, error: error.message };
    }
  },

  async dateDrivenScan(season, leagueConfig, options = {}) {
    this.logger.warn('date_driven_scan_deprecated', {
      season,
      league: leagueConfig?.name || null,
      fallback: 'season_mirror'
    });
    return this.smartScan(season, leagueConfig, options);
  },

  async crossLeagueScan(season, leagueConfig, additionalSlugs = [], options = {}) {
    const startTime = Date.now();
    this.logger.info('cross_league_scan_start', { season, league: leagueConfig.name, additionalSlugs });

    const allResults = [];
    const mainResult = await this.smartScan(season, leagueConfig, options);
    allResults.push({ slug: leagueConfig.slug, ...mainResult });

    for (const slug of additionalSlugs) {
      const slugConfig = { ...leagueConfig, slug };
      const slugResult = await this.smartScan(season, slugConfig, options);
      allResults.push({ slug, ...slugResult });
    }

    const totalInserted = allResults.reduce((sum, result) => (
      sum + Number(result.inserted || result.totalInserted || 0)
    ), 0);

    return {
      success: true,
      season,
      primaryLeague: leagueConfig.name,
      scannedLeagues: allResults.length,
      totalInserted,
      details: allResults,
      durationMs: Date.now() - startTime
    };
  },

  async smartScan(season, leagueConfig, options = {}) {
    const startTime = Date.now();

    if (this.reconStrategy === 'legacy') {
      this.logger.warn('smart_scan_strategy_override', {
        season,
        league: leagueConfig?.name || null,
        strategy: 'legacy_protocol_archive'
      });
      const legacyResult = await this.protocolArchiveScan(season, leagueConfig);

      if (legacyResult.success === false) {
        return {
          ...legacyResult,
          strategy: 'legacy_protocol_archive',
          durationMs: Date.now() - startTime
        };
      }

      return {
        success: true,
        season,
        league: leagueConfig.name,
        strategy: 'legacy_protocol_archive',
        pendingTotal: legacyResult.pendingTotal || 0,
        inserted: legacyResult.inserted || 0,
        linked: legacyResult.inserted || 0,
        mismatched: legacyResult.unmatched || 0,
        totalInserted: legacyResult.inserted || 0,
        coverage: Number(legacyResult.coverage || 0),
        sourceSeason: this.taskPlanner.formatSeasonForUrl(season),
        sourceUrl: this.taskPlanner.buildResultsUrl(leagueConfig, season),
        candidateCount: legacyResult.candidatesFound || 0,
        durationMs: Date.now() - startTime
      };
    }

    const target = this.taskPlanner.buildTarget(season, leagueConfig, {
      currentSeasonOnly: this.currentSeasonOnly
    });

    this.logger.info('smart_scan_start', {
      season,
      league: leagueConfig.name,
      strategy: 'season_mirror',
      disableDomFallback: this.disableDomFallback
    });

    const pendingMatches = await this.taskPlanner.loadReconPendingMatches(target, {
      allNonLinked: this.allNonLinked === true
    });
    if (!Array.isArray(pendingMatches) || pendingMatches.length === 0) {
      return {
        success: true,
        season,
        league: leagueConfig.name,
        strategy: 'season_mirror',
        pendingTotal: 0,
        inserted: 0,
        linked: 0,
        mismatched: 0,
        totalInserted: 0,
        coverage: 100,
        durationMs: Date.now() - startTime
      };
    }

    try {
      const result = await this._runReconTarget(target, {
        concurrency: this.defaultReconConcurrency,
        batchSize: this.reconBatchSize,
        confidenceThreshold: this.confidenceThreshold,
        forceDomMode: options.forceDomMode ?? this.forceDomMode,
        pendingMatches
      });
      const coverage = result.pendingTotal > 0
        ? Number(((result.linked / result.pendingTotal) * 100).toFixed(2))
        : 100;

      this.logger.info('smart_scan_complete', {
        strategy: 'season_mirror',
        coverage,
        linked: result.linked,
        mismatched: result.mismatched,
        candidateCount: result.candidateCount
      });

      return {
        success: true,
        season,
        league: leagueConfig.name,
        strategy: 'season_mirror',
        pendingTotal: result.pendingTotal,
        inserted: result.linked,
        linked: result.linked,
        mismatched: result.mismatched,
        totalInserted: result.linked,
        coverage,
        sourceSeason: result.sourceSeason,
        sourceUrl: result.sourceUrl,
        candidateCount: result.candidateCount,
        durationMs: Date.now() - startTime
      };
    } catch (error) {
      if (error.code === 'SKIPPED_FUTURE_FINALS') {
        this.logger.info('smart_scan_skipped', {
          season,
          league: leagueConfig.name,
          strategy: 'season_mirror',
          sourceState: error.code
        });
        return {
          success: true,
          skipped: true,
          sourceState: error.code,
          season,
          league: leagueConfig.name,
          strategy: 'season_mirror',
          pendingTotal: 0,
          skippedPendingTotal: pendingMatches.length,
          inserted: 0,
          linked: 0,
          mismatched: 0,
          totalInserted: 0,
          coverage: 100,
          sourceUrl: error.sourceUrl || target.resultsUrl,
          sourceSeason: error.sourceSeason || this.taskPlanner.formatSeasonForUrl(target.season),
          durationMs: Date.now() - startTime
        };
      }

      if (error.code === 'SOURCE_EMPTY' && this.disableDomFallback) {
        this.logger.warn('season_sweep_empty_dom_fallback_disabled', {
          season,
          league: leagueConfig.name,
          strategy: 'season_mirror',
          error: error.message
        });
        return {
          success: false,
          season,
          league: leagueConfig.name,
          strategy: 'season_mirror_dom_disabled',
          error: error.message,
          durationMs: Date.now() - startTime
        };
      }

      if (error.code === 'SOURCE_EMPTY' && typeof this.domFallbackScan === 'function') {
        this.logger.warn('season_sweep_empty', { season, league: leagueConfig.name, fallback: 'dom_fallback' });
        const domResult = await this.domFallbackScan(season, leagueConfig);
        const coverage = pendingMatches.length > 0
          ? Number((((domResult.inserted || 0) / pendingMatches.length) * 100).toFixed(2))
          : 100;

        return {
          success: Boolean(domResult.success),
          season,
          league: leagueConfig.name,
          strategy: 'season_mirror_dom_fallback',
          pendingTotal: pendingMatches.length,
          inserted: domResult.inserted || 0,
          linked: domResult.inserted || 0,
          mismatched: Math.max(0, pendingMatches.length - Number(domResult.inserted || 0)),
          totalInserted: domResult.inserted || 0,
          coverage,
          durationMs: Date.now() - startTime
        };
      }

      this.logger.error('smart_scan_failed', { season, league: leagueConfig.name, error: error.message });
      return {
        success: false,
        season,
        league: leagueConfig.name,
        strategy: 'season_mirror',
        error: error.message,
        durationMs: Date.now() - startTime
      };
    }
  },

  async domFallbackScan(season, leagueConfig) {
    const startTime = Date.now();
    this.logger.info('dom_fallback_scan_start', { season, league: leagueConfig.name });

    try {
      const dbSeason = this.taskPlanner.normalizeDbSeason(season);
      const unstitched = await this.taskPlanner.loadReconPendingMatches({ dbSeason, league: leagueConfig }, {
        allNonLinked: this.allNonLinked === true
      });

      if (unstitched.length === 0) {
        return { success: true, inserted: 0, reason: 'no_pending_matches' };
      }

      const baseUrl = this.taskPlanner.buildResultsUrl(leagueConfig, season);
      const absoluteBaseUrl = this.baseUrl;
      const leagueCountry = String(leagueConfig.country || '').toLowerCase();
      const leagueSlug = String(leagueConfig.slug || '').toLowerCase();

      await this.navigator.navigate(baseUrl, { waitUntil: 'domcontentloaded' });
      await this.navigator.page.waitForTimeout(this.pageSettleWaitMs);

      for (let index = 0; index < 5; index++) {
        await this.navigator.page.evaluate((scrollStepPx) => window.scrollBy(0, scrollStepPx), this.domScrollStepPx);
        await this.navigator.page.waitForTimeout(this.domScrollDelayMs);
      }

      const domMatches = await this.navigator.page.evaluate(({ absoluteBaseUrl, leagueCountry, leagueSlug }) => {
        const matches = [];
        const hashPattern = /-([a-zA-Z0-9]{8})\/$/;

        document.querySelectorAll('a[href*="/football/"]').forEach((link) => {
          const href = link.getAttribute('href') || '';
          const match = href.match(hashPattern);

          if (match && href.includes(leagueCountry) && href.includes(leagueSlug)) {
            const hash = match[1];
            const parent = link.closest('div[role="row"], div[data-testid*="event"], div[data-testid*="match"], div[class*="event"], div[class*="sportName"], tr');
            let text = '';

            if (parent) {
              text = parent.innerText || parent.textContent || '';
            } else {
              text = link.innerText || link.textContent || '';
            }

            matches.push({
              url: href.startsWith('http') ? href : `${absoluteBaseUrl}${href}`,
              hash,
              rawText: text.replace(/\s+/g, ' ').trim(),
              source: 'dom_fallback'
            });
          }
        });

        const seen = new Set();
        return matches.filter((matchItem) => {
          if (seen.has(matchItem.hash)) {
            return false;
          }
          seen.add(matchItem.hash);
          return true;
        });
      }, { absoluteBaseUrl, leagueCountry, leagueSlug });

      this.logger.info('dom_extract_complete', { candidates: domMatches.length });

      let inserted = 0;
      for (const l1Match of unstitched) {
        const matched = domMatches.find((domMatch) => {
          const text = domMatch.rawText.toLowerCase();
          return text.includes(l1Match.home_team.toLowerCase()) && text.includes(l1Match.away_team.toLowerCase());
        });

        if (matched && this.stitcher) {
          try {
            const result = await this.stitcher.stitchWithHashLock(
              [{
                ...matched,
                homeTeam: l1Match.home_team,
                awayTeam: l1Match.away_team
              }],
              [l1Match],
              dbSeason,
              leagueConfig
            );
            inserted += result.inserted || 0;
          } catch (error) {
            this.logger.warn('dom_stitch_failed', { matchId: l1Match.match_id, error: error.message });
          }
        }
      }

      this.logger.info('dom_fallback_scan_complete', { inserted, candidates: domMatches.length });

      return {
        success: true,
        season,
        league: leagueConfig.name,
        candidatesFound: domMatches.length,
        inserted,
        durationMs: Date.now() - startTime
      };
    } catch (error) {
      this.logger.error('dom_fallback_scan_failed', { error: error.message });
      return { success: false, error: error.message };
    }
  },

  async _matchAndStitch(candidates, l1Matches, season, leagueConfig) {
    let inserted = 0;
    let unmatched = 0;
    const usedCandidates = new Set();

    for (const l1Match of l1Matches) {
      let matched = null;

      for (const candidate of candidates) {
        const key = candidate.hash || candidate.url;
        if (!key || usedCandidates.has(key)) {
          continue;
        }

        if (this._isStrictMatch(candidate, l1Match)) {
          matched = candidate;
          usedCandidates.add(key);
          break;
        }
      }

      if (matched && this.stitcher) {
        try {
          const result = await this.stitcher.stitchWithHashLock(
            [matched],
            [l1Match],
            season,
            leagueConfig
          );
          inserted += result.inserted || 0;
        } catch (error) {
          this.logger.error('stitch_failed', { matchId: l1Match.match_id, error: error.message });
          unmatched++;
        }
      } else {
        unmatched++;
      }
    }

    return { inserted, unmatched };
  },

  _isStrictMatch(candidate, l1Match) {
    return this.matchEvaluator.isStrictMatch(candidate, l1Match);
  }
};

module.exports = { reconScanModes };
