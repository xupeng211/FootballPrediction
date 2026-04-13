'use strict';

const reconStitcherPersistence = {
  /**
   * Fetch unmatched L1 fixtures for the target league/season.
   *
   * High-risk area:
   * This method defines the set-closure search space. A wrong season format here
   * silently removes valid reconciliation candidates.
   *
   * @param {string} season
   * @param {string} leagueName
   * @returns {Promise<Object[]>}
   */
  async getDbUnstitchedMatches(season, leagueName) {
    try {
      const dbSeason = this.formatSeasonForDb(season);
      const client = await this.repository.dbPool.connect();
      try {
        const query = `
          SELECT m.match_id, m.home_team, m.away_team, m.match_date
          FROM matches m
          LEFT JOIN matches_oddsportal_mapping map
            ON m.match_id = map.match_id
           AND map.season = $2
           AND COALESCE(map.is_evidence_only, FALSE) = FALSE
          WHERE m.league_name = $1
            AND m.season = $2
            AND map.match_id IS NULL
          ORDER BY m.match_date;
        `;

        const result = await client.query(query, [leagueName, dbSeason]);
        return result.rows;
      } finally {
        client.release();
      }
    } catch (error) {
      this.logger.error('getDbUnstitchedMatches_error', { error: error.message });
      return [];
    }
  },

  /**
   * Persist a stitched mapping after orientation and arbitration checks.
   *
   * High-risk area:
   * This is the last write gate before `matches_oddsportal_mapping`. League/name
   * degradation and hash rollover classification both happen here.
   *
   * @param {Object} match
   * @param {{homeTeam: string, awayTeam: string}} teams
   * @param {Object} matchInfo
   * @param {string} season
   * @param {Object} leagueConfig
   * @returns {Promise<Object>}
   */
  async saveMapping(match, teams, matchInfo, season, leagueConfig) {
    const dbSeason = this.formatSeasonForDb(season);
    const existingMapping = await this.findExistingMappingForMatch(matchInfo.matchId, dbSeason);
    const prepared = this.buildMappingPayload(
      match,
      teams,
      matchInfo,
      dbSeason,
      leagueConfig,
      { existingMapping }
    );

    const result = await this.repository.saveOddsPortalMapping(prepared.mappingData, {
      pipelineStatus: 'RECON_LINKED'
    });

    return {
      ...result,
      mappingMethod: prepared.decision?.mappingMethod || null
    };
  },

  /**
   * Build a persistence-ready mapping payload without writing to the DB.
   *
   * High-risk area:
   * Batch flows reuse this helper to keep arbitration consistent with single
   * writes. Any drift here creates divergent match_id binding behaviour.
   *
   * @param {Object} match
   * @param {{homeTeam: string, awayTeam: string}} teams
   * @param {Object} matchInfo
   * @param {string} season
   * @param {Object} leagueConfig
   * @param {Object} [options]
   * @param {Object|null} [options.existingMapping=null]
   * @returns {{mappingData: Object, decision: Object, orientation: Object}}
   */
  buildMappingPayload(match, teams, matchInfo, season, leagueConfig, options = {}) {
    const l1HomeTeam = matchInfo.dbHome || teams.homeTeam;
    const l1AwayTeam = matchInfo.dbAway || teams.awayTeam;
    const orientation = this._resolveOrientation(
      teams.homeTeam,
      teams.awayTeam,
      l1HomeTeam,
      l1AwayTeam
    );

    if (!orientation.directMatch && !orientation.swappedMatch) {
      const error = new Error('ORIENTATION_UNCERTAIN');
      error.code = 'ORIENTATION_UNCERTAIN';
      throw error;
    }

    const dbSeason = this.formatSeasonForDb(season);
    const existingMapping = options.existingMapping || null;
    const decision = this.arbitrationStrategy
      ? this.arbitrationStrategy.buildMappingDecision({
        match,
        matchInfo,
        leagueConfig,
        existingMapping
      })
      : {
        leagueName: leagueConfig?.name,
        mappingMethod: matchInfo.method || 'exact',
        matchConfidence: matchInfo.confidence || 0.75,
        degradedFields: [],
        hashLifecycle: { changed: false }
      };

    if (decision.hashLifecycle?.changed) {
      this.logger.warn('stitch_hash_rollover_detected', {
        matchId: String(matchInfo.matchId),
        previousHash: decision.hashLifecycle.previousHash,
        incomingHash: decision.hashLifecycle.incomingHash,
        season: dbSeason
      });
    }

    if (decision.degradedFields?.length > 0) {
      this.logger.warn('stitch_field_degradation_applied', {
        matchId: String(matchInfo.matchId),
        hash: match?.hash || null,
        degradedFields: decision.degradedFields,
        leagueName: decision.leagueName
      });
    }

    return {
      orientation,
      decision,
      mappingData: {
        match_id: matchInfo.matchId,
        oddsportal_hash: match.hash,
        full_url: match.url,
        season: dbSeason,
        league_name: decision.leagueName,
        home_team: l1HomeTeam,
        away_team: l1AwayTeam,
        is_reversed: orientation.isReversed,
        match_confidence: decision.matchConfidence,
        mapping_method: decision.mappingMethod,
        status: 'pending'
      }
    };
  },

  _buildFixtureLookupPairKey(homeTeam, awayTeam) {
    const normalizedHome = this._normalizeTeamName(homeTeam);
    const normalizedAway = this._normalizeTeamName(awayTeam);

    if (!normalizedHome || !normalizedAway) {
      return null;
    }

    return `${normalizedHome}__${normalizedAway}`;
  },

  buildFixtureLookup(matches = []) {
    const fixtureLookup = {
      matches: [],
      pairIndex: new Map(),
      homeIndex: new Map()
    };

    for (const match of Array.isArray(matches) ? matches : []) {
      fixtureLookup.matches.push(match);

      const pairKey = this._buildFixtureLookupPairKey(match.home_team, match.away_team);
      if (pairKey) {
        if (!fixtureLookup.pairIndex.has(pairKey)) {
          fixtureLookup.pairIndex.set(pairKey, []);
        }
        fixtureLookup.pairIndex.get(pairKey).push(match);
      }

      const homeKey = this._normalizeTeamName(match.home_team);
      if (homeKey) {
        if (!fixtureLookup.homeIndex.has(homeKey)) {
          fixtureLookup.homeIndex.set(homeKey, []);
        }
        fixtureLookup.homeIndex.get(homeKey).push(match);
      }
    }

    return fixtureLookup;
  },

  /**
   * Preload season fixtures into in-memory lookup maps for batch matching.
   *
   * @param {string} season
   * @param {Object} [options]
   * @param {Object[]} [options.preloadedMatches]
   * @returns {Promise<Object|null>}
   */
  async createFixtureLookupContext(season, options = {}) {
    const preloadedMatches = Array.isArray(options.preloadedMatches)
      ? options.preloadedMatches
      : null;
    const candidates = preloadedMatches || (
      typeof this.repository.findMatchesBySeason === 'function'
        ? await this.repository.findMatchesBySeason(season)
        : null
    );

    if (!Array.isArray(candidates) || candidates.length === 0) {
      return null;
    }

    return this.buildFixtureLookup(candidates);
  },

  _getExactCandidatesFromFixtureLookup(homeTeam, awayTeam, fixtureLookup = null) {
    if (!(fixtureLookup?.pairIndex instanceof Map)) {
      return null;
    }

    const direct = fixtureLookup.pairIndex.get(
      this._buildFixtureLookupPairKey(homeTeam, awayTeam)
    ) || [];
    const reversed = fixtureLookup.pairIndex.get(
      this._buildFixtureLookupPairKey(awayTeam, homeTeam)
    ) || [];

    return [...direct, ...reversed];
  },

  _getHomeCandidatesFromFixtureLookup(homeTeam, fixtureLookup = null) {
    if (!(fixtureLookup?.homeIndex instanceof Map)) {
      return null;
    }

    return fixtureLookup.homeIndex.get(this._normalizeTeamName(homeTeam)) || [];
  },

  _normalizeRepositoryTeamMatch(match, homeTeam, awayTeam) {
    if (!match) {
      return [];
    }

    if (Array.isArray(match)) {
      return match;
    }

    return [{
      match_id: match.matchId,
      home_team: match.dbHome || homeTeam,
      away_team: match.dbAway || awayTeam,
      match_date: match.matchDate || match.match_date || null
    }];
  },

  async _findMatchesByTeamsFromRepository(homeTeam, awayTeam, season) {
    if (typeof this.repository.findMatchesByTeams === 'function') {
      const matches = await this.repository.findMatchesByTeams(homeTeam, awayTeam, season);
      return this._normalizeRepositoryTeamMatch(matches, homeTeam, awayTeam);
    }

    if (typeof this.repository.findMatchByTeams === 'function') {
      const match = await this.repository.findMatchByTeams(homeTeam, awayTeam, season);
      return this._normalizeRepositoryTeamMatch(match, homeTeam, awayTeam);
    }

    return null;
  },

  /**
   * Preload existing season/hash mappings into memory for batch dedupe.
   *
   * @param {string[]} hashes
   * @param {string} season
   * @returns {Promise<Map<string, Object>>}
   */
  async findExistingMappingsByHashes(hashes = [], season) {
    const normalizedHashes = [...new Set(
      (Array.isArray(hashes) ? hashes : [])
        .map((hash) => String(hash || '').trim())
        .filter(Boolean)
    )];

    if (normalizedHashes.length === 0) {
      return new Map();
    }

    const dbSeason = this.formatSeasonForDb(season);
    if (!this.repository?.dbPool?.connect) {
      const rows = await Promise.all(normalizedHashes.map(async (hash) => [
        hash,
        await this.checkExistingMapping(hash, dbSeason)
      ]));
      return new Map(rows.filter(([, mapping]) => mapping));
    }

    const client = await this.repository.dbPool.connect();
    try {
      const result = await client.query(`
        SELECT match_id, oddsportal_hash, season, league_name, full_url, updated_at
        FROM matches_oddsportal_mapping
        WHERE season = $1
          AND oddsportal_hash = ANY($2::text[])
      `, [dbSeason, normalizedHashes]);

      return new Map((result.rows || []).map((row) => [String(row.oddsportal_hash), row]));
    } finally {
      client.release();
    }
  },

  /**
   * Preload existing match_id/season mappings into memory for hash rollover arbitration.
   *
   * @param {string[]} matchIds
   * @param {string} season
   * @returns {Promise<Map<string, Object>>}
   */
  async findExistingMappingsByMatchIds(matchIds = [], season) {
    const normalizedMatchIds = [...new Set(
      (Array.isArray(matchIds) ? matchIds : [])
        .map((matchId) => String(matchId || '').trim())
        .filter(Boolean)
    )];

    if (normalizedMatchIds.length === 0) {
      return new Map();
    }

    const dbSeason = this.formatSeasonForDb(season);
    if (!this.repository?.dbPool?.connect) {
      const rows = await Promise.all(normalizedMatchIds.map(async (matchId) => [
        matchId,
        await this.findExistingMappingForMatch(matchId, dbSeason)
      ]));
      return new Map(rows.filter(([, mapping]) => mapping));
    }

    const client = await this.repository.dbPool.connect();
    try {
      const result = await client.query(`
        SELECT match_id, oddsportal_hash, season, league_name, full_url, updated_at
        FROM matches_oddsportal_mapping
        WHERE season = $1
          AND match_id = ANY($2::text[])
      `, [dbSeason, normalizedMatchIds]);

      return new Map((result.rows || []).map((row) => [String(row.match_id), row]));
    } finally {
      client.release();
    }
  },

  /**
   * Find the most plausible L1 match for parsed web teams.
   *
   * High-risk area:
   * Team equality is not sufficient in cup/league double-headers. Kickoff-aware
   * arbitration is mandatory when duplicate team pairs exist.
   *
   * @param {string} homeTeam
   * @param {string} awayTeam
   * @param {string} season
   * @param {Object} [arbitrationContext]
   * @returns {Promise<Object|null>}
   */
  async findMatchInDb(homeTeam, awayTeam, season, arbitrationContext = {}) {
    const dbSeason = this.formatSeasonForDb(season);
    const sourceMatch = arbitrationContext.match || {
      matchDate: arbitrationContext.matchDate || null
    };
    const exactCandidates = await this.findMatchesByTeams(homeTeam, awayTeam, dbSeason, {
      fixtureLookup: arbitrationContext.fixtureLookup || null
    });
    if (Array.isArray(exactCandidates) && exactCandidates.length > 0) {
      const exactMatch = this.arbitrationStrategy
        ? this.arbitrationStrategy.chooseBestMatchCandidate({
          sourceMatch,
          candidates: exactCandidates,
          homeTeam,
          awayTeam,
          similarityFn: (left, right) => this._calculateTeamSimilarity(left, right),
          fallbackMethod: 'exact'
        })
        : null;
      if (exactMatch) {
        return exactMatch;
      }
    }

    if (this.parser) {
      return this.findWithFuzzyMatch(homeTeam, awayTeam, dbSeason, arbitrationContext);
    }

    return null;
  },

  /**
   * Fuzzy-match source teams against the full season candidate pool.
   *
   * @param {string} homeTeam
   * @param {string} awayTeam
   * @param {string} season
   * @param {Object} [arbitrationContext]
   * @returns {Promise<Object|null>}
   */
  async findWithFuzzyMatch(homeTeam, awayTeam, season, arbitrationContext = {}) {
    const candidates = arbitrationContext.fixtureLookup?.matches
      || await this.repository.findMatchesBySeason(season);
    if (!candidates || candidates.length === 0) return null;

    if (this.arbitrationStrategy) {
      return this.arbitrationStrategy.chooseBestMatchCandidate({
        sourceMatch: arbitrationContext.match || {
          matchDate: arbitrationContext.matchDate || null
        },
        candidates,
        homeTeam,
        awayTeam,
        similarityFn: (left, right) => this._calculateTeamSimilarity(left, right),
        fallbackMethod: 'fuzzy'
      });
    }

    return null;
  },

  /**
   * Recover the away team when only the home side is reliably parsed.
   *
   * @param {string} homeTeam
   * @param {string|null} dateStr
   * @param {string} season
   * @param {string} _leagueName
   * @returns {Promise<Object|null>}
   */
  async findMatchByHomeAndDate(homeTeam, dateStr, season, _leagueName, options = {}) {
    try {
      const dbSeason = this.formatSeasonForDb(season);
      const fixtureLookup = options.fixtureLookup || null;
      const candidates = this._getHomeCandidatesFromFixtureLookup(homeTeam, fixtureLookup)
        || (
          typeof this.repository.findMatchesBySeason === 'function'
            ? await this.repository.findMatchesBySeason(dbSeason)
            : null
        );
      if (!candidates) return null;

      const sourceTs = this.arbitrationStrategy?.toTimestamp(dateStr) ?? null;
      const homeMatches = candidates
        .map((match) => {
          const similarity = this.parser
            ? this.parser.calculateSimilarity(match.home_team, homeTeam)
            : this.simpleSimilarity(match.home_team, homeTeam);
          const kickoff = this.arbitrationStrategy
            ? this.arbitrationStrategy.evaluateKickoffDelta(dateStr, match.match_date)
            : {
              known: false,
              diffMs: null,
              hardReject: false
            };

          return {
            match,
            similarity,
            kickoff
          };
        })
        .filter((entry) => entry.similarity > 0.75 && !entry.kickoff.hardReject)
        .sort((left, right) => {
          const leftKickoff = Number.isFinite(left.kickoff.diffMs) ? left.kickoff.diffMs : Number.MAX_SAFE_INTEGER;
          const rightKickoff = Number.isFinite(right.kickoff.diffMs) ? right.kickoff.diffMs : Number.MAX_SAFE_INTEGER;
          if (leftKickoff !== rightKickoff) {
            return leftKickoff - rightKickoff;
          }

          if (right.similarity !== left.similarity) {
            return right.similarity - left.similarity;
          }

          return String(left.match.match_id).localeCompare(String(right.match.match_id));
        });

      if (!sourceTs && homeMatches.length !== 1) {
        return null;
      }

      if (homeMatches.length >= 1) {
        const bestMatch = homeMatches[0].match;
        return {
          matchId: bestMatch.match_id,
          awayTeam: bestMatch.away_team,
          confidence: Number((homeMatches[0].similarity * 0.9).toFixed(3)),
          matchDate: bestMatch.match_date || null,
          method: 'home_date_fill'
        };
      }

      return null;
    } catch (error) {
      this.logger.error('findMatchByHomeAndDate_error', { error: error.message });
      return null;
    }
  },

  /**
   * Check whether the incoming season/hash already exists.
   *
   * @param {string} hash
   * @param {string} season
   * @returns {Promise<Object|null>}
   */
  async checkExistingMapping(hash, season) {
    try {
      if (!hash) {
        return null;
      }

      const dbSeason = this.formatSeasonForDb(season);
      if (this.repository.findMappingByHash) {
        return await this.repository.findMappingByHash(hash, dbSeason);
      }

      if (!this.repository?.dbPool?.connect) {
        return null;
      }

      const client = await this.repository.dbPool.connect();
      try {
        const result = await client.query(`
          SELECT match_id, oddsportal_hash, season, league_name, full_url, updated_at
          FROM matches_oddsportal_mapping
          WHERE season = $1
            AND oddsportal_hash = $2
          LIMIT 1
        `, [dbSeason, String(hash)]);

        return result.rows[0] || null;
      } finally {
        client.release();
      }
    } catch {
      return null;
    }
  },

  /**
   * Find the currently stored mapping for a specific match_id/season.
   *
   * @param {string} matchId
   * @param {string} season
   * @returns {Promise<Object|null>}
   */
  async findExistingMappingForMatch(matchId, season) {
    try {
      if (!matchId) {
        return null;
      }

      if (this.repository.findMappingByMatchIdAndSeason) {
        return await this.repository.findMappingByMatchIdAndSeason(matchId, season);
      }

      if (!this.repository?.dbPool?.connect) {
        return null;
      }

      const client = await this.repository.dbPool.connect();
      try {
        const result = await client.query(`
          SELECT match_id, oddsportal_hash, season, league_name, full_url, updated_at
          FROM matches_oddsportal_mapping
          WHERE match_id = $1
            AND season = $2
          LIMIT 1
        `, [String(matchId), String(season)]);

        return result.rows[0] || null;
      } finally {
        client.release();
      }
    } catch {
      return null;
    }
  },

  /**
   * Fetch all exact team-pair candidates inside a season.
   *
   * @param {string} homeTeam
   * @param {string} awayTeam
   * @param {string} season
   * @returns {Promise<Object[]>}
   */
  async findMatchesByTeams(homeTeam, awayTeam, season, options = {}) {
    const exactCandidatesFromLookup = this._getExactCandidatesFromFixtureLookup(
      homeTeam,
      awayTeam,
      options.fixtureLookup || null
    );
    if (Array.isArray(exactCandidatesFromLookup)) {
      return exactCandidatesFromLookup;
    }

    const repositoryMatches = await this._findMatchesByTeamsFromRepository(homeTeam, awayTeam, season);
    if (Array.isArray(repositoryMatches)) {
      return repositoryMatches;
    }

    if (!this.repository?.dbPool?.connect) {
      return [];
    }

    const client = await this.repository.dbPool.connect();
    try {
      const result = await client.query(`
        SELECT match_id, home_team, away_team, match_date
        FROM matches
        WHERE season = $1
          AND (
            (LOWER(home_team) = LOWER($2) AND LOWER(away_team) = LOWER($3))
            OR (LOWER(home_team) = LOWER($3) AND LOWER(away_team) = LOWER($2))
          )
        ORDER BY match_date ASC, match_id ASC
      `, [season, homeTeam, awayTeam]);

      return result.rows || [];
    } finally {
      client.release();
    }
  }
};

module.exports = { reconStitcherPersistence };
