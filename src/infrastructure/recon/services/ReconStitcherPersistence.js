'use strict';

const reconStitcherPersistence = {
  async getDbUnstitchedMatches(season, leagueName) {
    try {
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

        const result = await client.query(query, [leagueName, season]);
        return result.rows;
      } finally {
        client.release();
      }
    } catch (error) {
      this.logger.error('getDbUnstitchedMatches_error', { error: error.message });
      return [];
    }
  },

  async saveMapping(match, teams, matchInfo, season, leagueConfig) {
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

    const mappingData = {
      match_id: matchInfo.matchId,
      oddsportal_hash: match.hash,
      full_url: match.url,
      season: season.replace('-', '/'),
      league_name: leagueConfig.name,
      home_team: l1HomeTeam,
      away_team: l1AwayTeam,
      is_reversed: orientation.isReversed,
      match_confidence: matchInfo.confidence || 0.75,
      mapping_method: matchInfo.method || 'exact',
      status: 'pending'
    };

    return this.repository.saveOddsPortalMapping(mappingData, {
      pipelineStatus: 'RECON_LINKED'
    });
  },

  async findMatchInDb(homeTeam, awayTeam, season) {
    const matchInfo = await this.repository.findMatchByTeams(homeTeam, awayTeam, season);
    if (matchInfo) return matchInfo;

    if (this.parser) {
      return this.findWithFuzzyMatch(homeTeam, awayTeam, season);
    }

    return null;
  },

  async findWithFuzzyMatch(homeTeam, awayTeam, season) {
    const candidates = await this.repository.findMatchesBySeason(season);
    if (!candidates || candidates.length === 0) return null;

    const homeCandidates = candidates.map((match) => match.home_team);
    const homeMatch = this.parser.findBestMatch(homeTeam, homeCandidates, 0.75);

    if (!homeMatch) return null;

    const awayCandidates = candidates.map((match) => match.away_team);
    const awayMatch = this.parser.findBestMatch(awayTeam, awayCandidates, 0.75);

    if (!awayMatch) return null;

    const matchedGame = candidates.find((match) =>
      match.home_team === homeMatch.team && match.away_team === awayMatch.team
    );

    if (matchedGame) {
      return {
        matchId: matchedGame.match_id,
        confidence: (homeMatch.confidence + awayMatch.confidence) / 2,
        method: 'fuzzy'
      };
    }

    return null;
  },

  async findMatchByHomeAndDate(homeTeam, _dateStr, season, _leagueName) {
    if (!this.repository.findMatchesBySeason) return null;

    try {
      const candidates = await this.repository.findMatchesBySeason(season);
      if (!candidates) return null;

      const homeMatches = candidates.filter((match) => {
        const similarity = this.parser
          ? this.parser.calculateSimilarity(match.home_team, homeTeam)
          : this.simpleSimilarity(match.home_team, homeTeam);
        return similarity > 0.75;
      });

      if (homeMatches.length === 1) {
        return {
          matchId: homeMatches[0].match_id,
          awayTeam: homeMatches[0].away_team,
          confidence: 0.85
        };
      }

      return null;
    } catch (error) {
      this.logger.error('findMatchByHomeAndDate_error', { error: error.message });
      return null;
    }
  },

  async checkExistingMapping(hash, season) {
    try {
      if (this.repository.findMappingByHash) {
        return await this.repository.findMappingByHash(hash, season.replace('-', '/'));
      }
      return null;
    } catch {
      return null;
    }
  }
};

module.exports = { reconStitcherPersistence };
