/* eslint-disable complexity, max-lines */
'use strict';

const { RECON_CONFIG } = require('./ReconServiceConfig');

const BASE_URL = RECON_CONFIG.oddsportal.base_url;

const reconStitcherFlow = {
  /**
   * Run the legacy stitcher over a page candidate set.
   *
   * High-risk area:
   * This method orchestrates all fallback passes. If counters drift here, the
   * follow-up set-closure and sniper phases receive corrupted unmatched state.
   *
   * @param {Object[]} matches
   * @param {string} season
   * @param {Object} leagueConfig
   * @returns {Promise<Object>}
   */
  async stitch(matches, season, leagueConfig) {
    const dbSeason = this.formatSeasonForDb(season);
    const fixtureLookup = await this.createFixtureLookupContext(dbSeason);
    this.logger.info('stitch_start', {
      matchCount: matches.length,
      season: dbSeason,
      league: leagueConfig.name
    });

    let inserted = 0;
    let skipped = 0;
    let unmatched = 0;
    this.unmatchedCache = [];

    for (const match of matches) {
      const result = await this.stitchSingle(match, dbSeason, leagueConfig, {
        fixtureLookup
      });
      if (result.status === 'inserted') inserted++;
      else if (result.status === 'skipped') skipped++;
      else {
        unmatched++;
        this.unmatchedCache.push({ match, reason: result.details });
      }
    }

    if (this.unmatchedCache.length > 0) {
      this.logger.info('starting_set_closure_reconciliation', {
        unmatchedCount: this.unmatchedCache.length
      });

      const closureResult = await this.performSetClosure(dbSeason, leagueConfig);
      inserted += closureResult.inserted;
      unmatched -= closureResult.inserted;
    }

    if (this.unmatchedCache.length > 0) {
      this.logger.info('starting_sniper_fill', { remaining: this.unmatchedCache.length });

      const sniperResult = await this.sniperFill(dbSeason, leagueConfig);
      inserted += sniperResult.inserted;
      unmatched -= sniperResult.inserted;
    }

    const successRate = matches.length > 0
      ? `${(((inserted + skipped) / matches.length) * 100).toFixed(2)}%`
      : '0%';

    this.logger.info('stitch_complete', {
      season: dbSeason,
      league: leagueConfig.name,
      inserted,
      skipped,
      unmatched,
      successRate
    });

    return {
      inserted,
      skipped,
      unmatched,
      unmatchedList: this.unmatchedCache.map((item) => item.match),
      successRate
    };
  },

  logStitchSuccess(match, matchId, season, leagueName, metadata = {}) {
    this.logger.info('stitch_success', {
      hash: match?.hash || null,
      matchId: matchId ? String(matchId) : null,
      season: season || null,
      league: leagueName || null,
      url: match?.url || null,
      ...metadata
    });
  },

  /**
   * Stitch a single source match into one canonical match_id.
   *
   * High-risk area:
   * This is the only place where source parsing, idempotency, kickoff-aware DB
   * selection and persistence all meet. A silent fallback here causes wrong links.
   *
   * @param {Object} match
   * @param {string} season
   * @param {Object} leagueConfig
   * @param {Object} [runtimeContext]
   * @returns {Promise<Object>}
   */
  async stitchSingle(match, season, leagueConfig, runtimeContext = {}) {
    const dbSeason = this.formatSeasonForDb(season);
    const lock = await this.acquireHashGuard(match?.hash, {
      leagueName: leagueConfig?.name,
      season: dbSeason
    });
    if (lock?.contended) {
      return { status: 'skipped', details: { reason: 'lock_contended' } };
    }

    try {
      if (match.hash && this.processedHashes.has(match.hash)) {
        return { status: 'skipped', details: { reason: 'idempotent_cache' } };
      }

      const existing = await this.checkExistingMapping(match.hash, dbSeason);
      if (existing) {
        return { status: 'skipped', details: { reason: 'already_exists' } };
      }

      let teams = null;

      if (this.parser) {
        teams = this.parser.extractTeamsFromSlug(match.slug);
      }

      if (
        (!teams || teams.homeTeam === 'Unknown' || teams.awayTeam === 'Unknown')
        && (match.homeTeam || match.home_team)
        && (match.awayTeam || match.away_team)
      ) {
        const incomingHomeTeam = match.homeTeam || match.home_team;
        const incomingAwayTeam = match.awayTeam || match.away_team;
        teams = {
          homeTeam: this.parser?.normalizeTeamName
            ? this.parser.normalizeTeamName(incomingHomeTeam)
            : incomingHomeTeam,
          awayTeam: this.parser?.normalizeTeamName
            ? this.parser.normalizeTeamName(incomingAwayTeam)
            : incomingAwayTeam
        };
      }

      if ((!teams || teams.awayTeam === 'Unknown') && match.rawText) {
        const textTeams = this.extractTeamsFromText(match.rawText);
        if (textTeams) teams = textTeams;
      }

      if (teams && teams.homeTeam !== 'Unknown' && teams.awayTeam === 'Unknown') {
        const dateMatch = await this.findMatchByHomeAndDate(
          teams.homeTeam,
          match.date || match.matchDate || match.match_date || null,
          dbSeason,
          leagueConfig.name,
          {
            fixtureLookup: runtimeContext.fixtureLookup || null
          }
        );
        if (dateMatch) {
          teams.awayTeam = dateMatch.awayTeam;
        }
      }

      if (!teams || teams.homeTeam === 'Unknown' || teams.awayTeam === 'Unknown') {
        return { status: 'unmatched', details: { reason: 'parse_failed', teams } };
      }

      const matchInfo = await this.findMatchInDb(teams.homeTeam, teams.awayTeam, dbSeason, {
        match: {
          ...match,
          matchDate: match.date || match.matchDate || match.match_date || null
        },
        fixtureLookup: runtimeContext.fixtureLookup || null
      });

      if (!matchInfo) {
        return { status: 'unmatched', details: { reason: 'db_not_found', teams } };
      }

      let result;
      try {
        result = await this.saveMapping(match, teams, matchInfo, dbSeason, leagueConfig);
      } catch (error) {
        if (error.code === 'ORIENTATION_UNCERTAIN') {
          this.logger.warn('orientation_uncertain', {
            hash: match.hash,
            season: dbSeason,
            league: leagueConfig.name,
            teams
          });
          return { status: 'unmatched', details: { reason: 'orientation_uncertain', teams } };
        }

        throw error;
      }

      if (result.success) {
        this.processedHashes.add(match.hash);
        this.logStitchSuccess(match, result.matchId || matchInfo.matchId, dbSeason, leagueConfig?.name, {
          mappingMethod: result.mappingMethod || null,
          phase: 'primary'
        });
        return { status: 'inserted', details: { matchId: result.matchId } };
      }

      return { status: 'skipped', details: { reason: 'save_failed' } };
    } finally {
      await this.releaseHashGuard(lock, match?.hash);
    }
  },

  /**
   * Secondary pass that reconciles page leftovers with the DB unmatched set.
   *
   * @param {string} season
   * @param {Object} leagueConfig
   * @returns {Promise<{inserted: number}>}
   */
  async performSetClosure(season, leagueConfig) {
    let inserted = 0;

    try {
      const dbUnstitched = await this.getDbUnstitchedMatches(season, leagueConfig.name);
      const pageUnmatched = this.unmatchedCache;

      this.logger.info('set_closure_analysis', {
        dbUnstitched: dbUnstitched.length,
        pageUnmatched: pageUnmatched.length
      });

      if (Math.abs(dbUnstitched.length - pageUnmatched.length) <= 5) {
        for (const pageItem of pageUnmatched) {
          const match = pageItem.match;
          let homeTeam = null;

          if (this.parser) {
            const parsed = this.parser.extractTeamsFromSlug(match.slug);
            if (parsed && parsed.homeTeam !== 'Unknown') {
              homeTeam = parsed.homeTeam;
            }
          }

          if (!homeTeam && match.rawText) {
            homeTeam = this.extractHomeTeamFromText(match.rawText);
          }

          if (!homeTeam) continue;

          const candidates = dbUnstitched.filter((dbMatch) => {
            const similarity = this.parser
              ? this.parser.calculateSimilarity(dbMatch.home_team, homeTeam)
              : this.simpleSimilarity(dbMatch.home_team, homeTeam);
            return similarity > 0.75;
          });

          if (candidates.length === 1) {
            const dbMatch = candidates[0];
            const teams = {
              homeTeam: dbMatch.home_team,
              awayTeam: dbMatch.away_team
            };

            const matchInfo = {
              matchId: dbMatch.match_id,
              confidence: 0.75,
              method: 'set_closure',
              dbHome: dbMatch.home_team,
              dbAway: dbMatch.away_team,
              matchDate: dbMatch.match_date || null
            };

            const result = await this.saveMapping(match, teams, matchInfo, season, leagueConfig);

            if (result.success) {
              inserted++;
              this.processedHashes.add(match.hash);
              this.logStitchSuccess(match, result.matchId || matchInfo.matchId, season, leagueConfig?.name, {
                mappingMethod: result.mappingMethod || 'set_closure',
                phase: 'set_closure'
              });

              const unmatchedIndex = this.unmatchedCache.indexOf(pageItem);
              if (unmatchedIndex > -1) this.unmatchedCache.splice(unmatchedIndex, 1);

              const dbIndex = dbUnstitched.indexOf(dbMatch);
              if (dbIndex > -1) dbUnstitched.splice(dbIndex, 1);

              this.logger.info('set_closure_stitch', {
                hash: match.hash,
                home: teams.homeTeam,
                away: teams.awayTeam
              });
            }
          }
        }
      }
    } catch (error) {
      this.logger.error('set_closure_error', { error: error.message });
    }

    return { inserted };
  },

  /**
   * Placeholder for search-based recovery of still-unmatched fixtures.
   *
   * @param {string} _season
   * @param {Object} _leagueConfig
   * @returns {Promise<{inserted: number}>}
   */
  async sniperFill(_season, _leagueConfig) {
    const inserted = 0;

    for (const item of [...this.unmatchedCache]) {
      const match = item.match;

      if (match.slug) {
        const searchUrl = `${BASE_URL}/search/${encodeURIComponent(match.slug)}/`;
        this.logger.info('sniper_attempt', { hash: match.hash, url: searchUrl });
      }
    }

    return { inserted };
  },

  _buildHashLockL1Index(l1Matches = []) {
    const l1Index = new Map();

    for (const l1Match of Array.isArray(l1Matches) ? l1Matches : []) {
      const key = `${this._normalizeTeamName(l1Match.home_team)}_${this._normalizeTeamName(l1Match.away_team)}`;
      if (!l1Index.has(key)) {
        l1Index.set(key, []);
      }
      l1Index.get(key).push(l1Match);
    }

    return l1Index;
  },

  _resolveHashLockTargetMatch(match, l1Matches = [], l1Index = new Map()) {
    const exactKey = `${this._normalizeTeamName(match.homeTeam)}_${this._normalizeTeamName(match.awayTeam)}`;
    const reversedKey = `${this._normalizeTeamName(match.awayTeam)}_${this._normalizeTeamName(match.homeTeam)}`;
    const indexedCandidates = [
      ...(l1Index.get(exactKey) || []),
      ...(l1Index.get(reversedKey) || [])
    ];

    for (const candidate of indexedCandidates) {
      const orientation = this._resolveOrientation(
        match.homeTeam,
        match.awayTeam,
        candidate.home_team,
        candidate.away_team
      );
      if (orientation.directMatch || orientation.swappedMatch) {
        return { targetL1: candidate, orientation };
      }
    }

    for (const l1Match of Array.isArray(l1Matches) ? l1Matches : []) {
      const orientation = this._resolveOrientation(
        match.homeTeam,
        match.awayTeam,
        l1Match.home_team,
        l1Match.away_team
      );
      if (orientation.directMatch || orientation.swappedMatch) {
        return { targetL1: l1Match, orientation };
      }
    }

    return { targetL1: null, orientation: null };
  },

  async _persistPreparedMappings(preparedMappings, season, leagueConfig) {
    if (!Array.isArray(preparedMappings) || preparedMappings.length === 0) {
      return { inserted: 0, skipped: 0, unmatched: 0 };
    }

    if (typeof this.repository.batchSaveOddsPortalMappings === 'function') {
      const result = await this.repository.batchSaveOddsPortalMappings(
        preparedMappings.map((entry) => entry.mappingData),
        {
          pipelineStatus: 'RECON_LINKED',
          preserve_linked_status: true
        }
      );
      const inserted = Number(result?.applied ?? result?.inserted ?? 0);

      for (const entry of preparedMappings) {
        this.processedHashes.add(entry.match.hash);
        this.logStitchSuccess(entry.match, entry.matchId, season, leagueConfig?.name, {
          mappingMethod: entry.decision?.mappingMethod || 'hash_lock',
          phase: 'hash_lock_batch'
        });
      }

      return {
        inserted,
        skipped: Math.max(0, preparedMappings.length - inserted),
        unmatched: 0
      };
    }

    let inserted = 0;
    let skipped = 0;
    let unmatched = 0;

    for (const entry of preparedMappings) {
      try {
        const result = await this.repository.saveOddsPortalMapping(entry.mappingData, {
          pipelineStatus: 'RECON_LINKED'
        });
        if (result?.success) {
          this.processedHashes.add(entry.match.hash);
          this.logStitchSuccess(entry.match, entry.matchId, season, leagueConfig?.name, {
            mappingMethod: entry.decision?.mappingMethod || 'hash_lock',
            phase: 'hash_lock_batch'
          });
          inserted++;
        } else {
          skipped++;
        }
      } catch (error) {
        this.logger.error('hash_lock_batch_save_error', {
          hash: entry.match?.hash || null,
          matchId: String(entry.matchId || ''),
          error: error.message
        });
        unmatched++;
      }
    }

    return { inserted, skipped, unmatched };
  },

  /**
   * Bulk stitch pre-matched source/L1 pairs with a single persistence phase.
   *
   * High-risk area:
   * This method deliberately holds per-hash locks across batch persistence to
   * trade small lock lifetimes for far fewer DB round-trips.
   *
   * @param {Object[]} matchPairs
   * @param {string} season
   * @param {Object} leagueConfig
   * @param {Object} [runtimeContext]
   * @returns {Promise<{inserted: number, skipped: number, unmatched: number}>}
   */
  async stitchBatch(matchPairs, season, leagueConfig, runtimeContext = {}) {
    const dbSeason = this.formatSeasonForDb(season);
    const normalizedPairs = Array.isArray(matchPairs) ? matchPairs : [];
    const l1Matches = runtimeContext.l1Matches || normalizedPairs
      .map((pair) => pair?.l1Match)
      .filter(Boolean);
    const l1Index = runtimeContext.l1Index || this._buildHashLockL1Index(l1Matches);
    const existingByHash = await this.findExistingMappingsByHashes(
      normalizedPairs.map((pair) => pair?.rawMatch?.hash || pair?.match?.hash).filter(Boolean),
      dbSeason
    );
    const existingByMatchId = await this.findExistingMappingsByMatchIds(
      normalizedPairs.map((pair) => pair?.l1Match?.match_id).filter(Boolean),
      dbSeason
    );
    const heldGuards = [];
    const queuedHashes = new Set();
    const preparedMappings = [];
    let skipped = 0;
    let unmatched = 0;

    this.logger.info('stitch_batch_start', {
      season: dbSeason,
      league: leagueConfig?.name || null,
      pairCount: normalizedPairs.length
    });

    try {
      for (const pair of normalizedPairs) {
        const rawMatch = pair?.rawMatch || pair?.match || null;
        if (!rawMatch) {
          unmatched++;
          continue;
        }

        let targetL1 = pair?.l1Match || null;
        const resolvedMatch = pair?.match || this._resolveWebMatchTeams(rawMatch, targetL1 ? [targetL1] : l1Matches);
        let orientation = pair?.orientation || null;

        if (!targetL1 || !orientation) {
          const resolvedTarget = this._resolveHashLockTargetMatch(resolvedMatch, l1Matches, l1Index);
          targetL1 = targetL1 || resolvedTarget.targetL1;
          orientation = orientation || resolvedTarget.orientation;
        }

        if (!targetL1 || !orientation || (!orientation.directMatch && !orientation.swappedMatch)) {
          unmatched++;
          continue;
        }

        const guard = await this.acquireHashGuard(resolvedMatch?.hash, {
          leagueName: leagueConfig?.name,
          season: dbSeason
        });
        if (guard?.contended) {
          skipped++;
          continue;
        }

        let keepGuard = false;
        try {
          const hashKey = String(resolvedMatch?.hash || '').trim();
          if (!hashKey) {
            unmatched++;
            continue;
          }

          if (this.processedHashes.has(hashKey) || queuedHashes.has(hashKey)) {
            skipped++;
            continue;
          }

          if (existingByHash.has(hashKey)) {
            this.processedHashes.add(hashKey);
            skipped++;
            continue;
          }

          const prepared = this.buildMappingPayload(
            resolvedMatch,
            {
              homeTeam: resolvedMatch.homeTeam,
              awayTeam: resolvedMatch.awayTeam
            },
            {
              matchId: targetL1.match_id,
              dbHome: targetL1.home_team,
              dbAway: targetL1.away_team,
              matchDate: targetL1.match_date || null,
              confidence: pair?.confidence ?? 0.9,
              method: pair?.method || 'hash_lock'
            },
            dbSeason,
            leagueConfig,
            {
              existingMapping: existingByMatchId.get(String(targetL1.match_id)) || null
            }
          );

          preparedMappings.push({
            ...prepared,
            match: resolvedMatch,
            matchId: String(targetL1.match_id)
          });
          queuedHashes.add(hashKey);
          keepGuard = true;
          heldGuards.push({ hash: hashKey, guard });
        } catch (error) {
          if (error.code === 'ORIENTATION_UNCERTAIN') {
            this.logger.warn('orientation_uncertain', {
              hash: resolvedMatch?.hash || null,
              season: dbSeason,
              league: leagueConfig?.name || null,
              teams: {
                homeTeam: resolvedMatch?.homeTeam || null,
                awayTeam: resolvedMatch?.awayTeam || null
              }
            });
          } else {
            this.logger.error('hash_lock_prepare_error', {
              hash: resolvedMatch?.hash || null,
              matchId: String(targetL1?.match_id || ''),
              error: error.message
            });
          }
          unmatched++;
        } finally {
          if (!keepGuard) {
            await this.releaseHashGuard(guard, resolvedMatch?.hash);
          }
        }
      }

      const persisted = await this._persistPreparedMappings(preparedMappings, dbSeason, leagueConfig);
      return {
        inserted: persisted.inserted,
        skipped: skipped + Number(persisted.skipped || 0),
        unmatched: unmatched + Number(persisted.unmatched || 0)
      };
    } finally {
      for (const { hash, guard } of heldGuards) {
        await this.releaseHashGuard(guard, hash);
      }
    }
  },

  /**
   * Hash-oriented fast path for already-resolved web matches.
   *
   * High-risk area:
   * The method name promises locking. Without a real guard this path degenerates
   * into concurrent upsert contention, so each hash now attempts row-level gating.
   *
   * @param {Object[]} interceptedMatches
   * @param {Object[]} l1Matches
   * @param {string} season
   * @param {Object} leagueConfig
   * @returns {Promise<{inserted: number, skipped: number, unmatched: number}>}
   */
  async stitchWithHashLock(interceptedMatches, l1Matches, season, leagueConfig) {
    this.logger.info('hash_lock_start', {
      intercepted: interceptedMatches.length,
      l1Total: l1Matches.length
    });

    let unmatched = 0;
    const l1Index = this._buildHashLockL1Index(l1Matches);
    const matchPairs = [];

    for (const rawMatch of interceptedMatches) {
      try {
        const match = this._resolveWebMatchTeams(rawMatch, l1Matches);
        const resolvedTarget = this._resolveHashLockTargetMatch(match, l1Matches, l1Index);
        if (!resolvedTarget.targetL1) {
          unmatched++;
          continue;
        }

        matchPairs.push({
          rawMatch,
          match,
          l1Match: resolvedTarget.targetL1,
          orientation: resolvedTarget.orientation,
          method: 'hash_lock',
          confidence: 0.9
        });
      } catch (error) {
        this.logger.error('hash_lock_error', { hash: rawMatch?.hash, error: error.message });
        unmatched++;
      }
    }

    const stitched = await this.stitchBatch(matchPairs, season, leagueConfig, {
      l1Matches,
      l1Index
    });

    return {
      inserted: stitched.inserted,
      skipped: stitched.skipped,
      unmatched: unmatched + stitched.unmatched
    };
  },

  /**
   * Cardinality-based reconciliation fallback for near-complete sets.
   *
   * @param {Object[]} webMatches
   * @param {Object[]} l1Matches
   * @param {string} season
   * @param {Object} leagueConfig
   * @returns {Promise<{inserted: number, unmatched: number}>}
   */
  async setReconciliation(webMatches, l1Matches, season, leagueConfig) {
    this.logger.info('set_reconciliation_start', {
      webCount: webMatches.length,
      l1Count: l1Matches.length
    });

    let inserted = 0;
    let unmatched = 0;
    const dbSeason = this.formatSeasonForDb(season);

    const pendingWeb = webMatches.filter((match) => !this.processedHashes.has(match.hash));
    const pendingL1 = l1Matches.filter((match) => !this.processedHashes.has(match.match_id));

    if (Math.abs(pendingWeb.length - pendingL1.length) <= 2) {
      this.logger.info('set_match_confirmed', {
        web: pendingWeb.length,
        l1: pendingL1.length
      });

      for (const rawWebMatch of pendingWeb) {
        const webMatch = this._resolveWebMatchTeams(rawWebMatch, pendingL1);
        let bestMatch = null;
        let bestScore = 0;

        for (const l1 of pendingL1) {
          const homeRoot = this.getWordRoot(webMatch.homeTeam);
          const l1HomeRoot = this.getWordRoot(l1.home_team);
          const homeSim = this.calculateRootSimilarity(homeRoot, l1HomeRoot);

          if (homeSim > bestScore && homeSim > 0.6) {
            bestScore = homeSim;
            bestMatch = l1;
          }
        }

        if (bestMatch) {
          try {
            const orientation = this._resolveOrientation(
              webMatch.homeTeam,
              webMatch.awayTeam,
              bestMatch.home_team,
              bestMatch.away_team
            );

            if (!orientation.directMatch && !orientation.swappedMatch) {
              unmatched++;
              continue;
            }

            const result = await this.repository.saveOddsPortalMapping({
              match_id: bestMatch.match_id,
              oddsportal_hash: webMatch.hash,
              full_url: webMatch.url,
              season: dbSeason,
              league_name: leagueConfig.name,
              home_team: bestMatch.home_team,
              away_team: bestMatch.away_team,
              is_reversed: orientation.isReversed,
              match_confidence: bestScore,
              mapping_method: 'set_reconciliation',
              status: 'pending'
            }, {
              pipelineStatus: 'RECON_LINKED'
            });

            if (result.success) {
              this.processedHashes.add(webMatch.hash);
              this.logStitchSuccess(webMatch, bestMatch.match_id, dbSeason, leagueConfig?.name, {
                mappingMethod: 'set_reconciliation',
                phase: 'set_reconciliation'
              });
              inserted++;

              const pendingIndex = pendingL1.indexOf(bestMatch);
              if (pendingIndex > -1) pendingL1.splice(pendingIndex, 1);

              this.logger.info('reconciliation_stitch', {
                hash: webMatch.hash,
                home: bestMatch.home_team,
                score: bestScore
              });
            }
          } catch (error) {
            this.logger.error('reconciliation_error', { hash: webMatch.hash, error: error.message });
            unmatched++;
          }
        } else {
          unmatched++;
        }
      }
    } else {
      this.logger.warn('set_mismatch', {
        web: pendingWeb.length,
        l1: pendingL1.length,
        diff: Math.abs(pendingWeb.length - pendingL1.length)
      });
      unmatched = pendingWeb.length;
    }

    return { inserted, unmatched };
  },

  /**
   * Acquire a best-effort per-hash distributed guard.
   *
   * @param {string|null} hash
   * @param {Object} context
   * @returns {Promise<{lock: Object|null, contended: boolean}>}
   */
  async acquireHashGuard(hash, context = {}) {
    if (!hash || !this.enableLocking || !this.lockManager?.acquireRowLock) {
      return { lock: null, contended: false };
    }

    try {
      const lock = await this.lockManager.acquireRowLock(hash);
      return { lock, contended: false };
    } catch (error) {
      if (error?.code && error.code !== 'LOCK_CONTENDED') {
        this.logger.error('stitch_hash_lock_error', {
          hash,
          season: context.season || null,
          league: context.leagueName || null,
          error: error.message,
          code: error.code
        });
        throw error;
      }

      this.logger.warn('stitch_hash_lock_contended', {
        hash,
        season: context.season || null,
        league: context.leagueName || null,
        error: error.message
      });
      return { lock: null, contended: true };
    }
  },

  /**
   * Release the distributed guard acquired for a hash.
   *
   * @param {{lock: Object|null, contended: boolean}|null} guard
   * @param {string|null} hash
   * @returns {Promise<void>}
   */
  async releaseHashGuard(guard, hash) {
    if (!guard?.lock?.release) {
      return;
    }

    try {
      await guard.lock.release();
    } catch (error) {
      this.logger.warn('stitch_hash_lock_release_failed', {
        hash: hash || null,
        error: error.message
      });
    }
  }
};

module.exports = { reconStitcherFlow };
