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
      const result = await this.stitchSingle(match, dbSeason, leagueConfig);
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
   * @returns {Promise<Object>}
   */
  async stitchSingle(match, season, leagueConfig) {
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

      if ((!teams || teams.awayTeam === 'Unknown') && match.rawText) {
        const textTeams = this.extractTeamsFromText(match.rawText);
        if (textTeams) teams = textTeams;
      }

      if (teams && teams.homeTeam !== 'Unknown' && teams.awayTeam === 'Unknown') {
        const dateMatch = await this.findMatchByHomeAndDate(
          teams.homeTeam,
          match.date || match.matchDate || match.match_date || null,
          dbSeason,
          leagueConfig.name
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
        }
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

    let inserted = 0;
    let skipped = 0;
    let unmatched = 0;
    const dbSeason = this.formatSeasonForDb(season);

    const l1Map = new Map();
    for (const match of l1Matches) {
      const key = `${this._normalizeTeamName(match.home_team)}_${this._normalizeTeamName(match.away_team)}`;
      l1Map.set(key, match);
    }

    for (const rawMatch of interceptedMatches) {
      const lock = await this.acquireHashGuard(rawMatch?.hash, {
        leagueName: leagueConfig?.name,
        season: dbSeason
      });
      if (lock?.contended) {
        skipped++;
        continue;
      }

      try {
        const match = this._resolveWebMatchTeams(rawMatch, l1Matches);
        if (match.hash && this.processedHashes.has(match.hash)) {
          skipped++;
          continue;
        }

        const existing = await this.checkExistingMapping(match.hash, dbSeason);
        if (existing) {
          this.processedHashes.add(match.hash);
          skipped++;
          continue;
        }

        let targetL1 = null;
        let orientation = null;
        const exactKey = `${this._normalizeTeamName(match.homeTeam)}_${this._normalizeTeamName(match.awayTeam)}`;
        targetL1 = l1Map.get(exactKey);
        if (targetL1) {
          orientation = this._resolveOrientation(match.homeTeam, match.awayTeam, targetL1.home_team, targetL1.away_team);
        }

        if (!targetL1) {
          const reversedKey = `${this._normalizeTeamName(match.awayTeam)}_${this._normalizeTeamName(match.homeTeam)}`;
          targetL1 = l1Map.get(reversedKey);
          if (targetL1) {
            orientation = this._resolveOrientation(match.homeTeam, match.awayTeam, targetL1.home_team, targetL1.away_team);
          }
        }

        if (!targetL1) {
          for (const [, l1] of l1Map.entries()) {
            const candidateOrientation = this._resolveOrientation(match.homeTeam, match.awayTeam, l1.home_team, l1.away_team);
            if (candidateOrientation.directMatch || candidateOrientation.swappedMatch) {
              targetL1 = l1;
              orientation = candidateOrientation;
              break;
            }
          }
        }

        if (!targetL1 || !orientation || (!orientation.directMatch && !orientation.swappedMatch)) {
          unmatched++;
          continue;
        }

        const result = await this.repository.saveOddsPortalMapping({
          match_id: targetL1.match_id,
          oddsportal_hash: match.hash,
          full_url: match.url,
          season: dbSeason,
          league_name: leagueConfig.name,
          home_team: targetL1.home_team,
          away_team: targetL1.away_team,
          is_reversed: orientation.isReversed,
          match_confidence: 0.9,
          mapping_method: 'hash_lock',
          status: 'pending'
        }, {
          pipelineStatus: 'RECON_LINKED'
        });

        if (result.success) {
          this.processedHashes.add(match.hash);
          inserted++;
        } else {
          skipped++;
        }
      } catch (error) {
        this.logger.error('hash_lock_error', { hash: rawMatch?.hash, error: error.message });
        unmatched++;
      } finally {
        await this.releaseHashGuard(lock, rawMatch?.hash);
      }
    }

    return { inserted, skipped, unmatched };
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
