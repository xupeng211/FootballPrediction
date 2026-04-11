'use strict';

function normalizeUniqueTextValues(values) {
  return [...new Set(values.map((value) => String(value)))];
}

function buildOptionalFieldLookup(fields, rows) {
  const existingFields = rows.map((row) => row.column_name);
  return fields.reduce((accumulator, fieldName) => ({
    ...accumulator,
    [fieldName]: existingFields.includes(fieldName)
  }), {});
}

class ReconMappingQueries {
  constructor(options = {}) {
    this.getDbPool = options.getDbPool;
    this.executeWithRetry = options.executeWithRetry;
    this.sqlTemplates = options.sqlTemplates || {};
  }

  async checkOptionalFields(tableName, fields) {
    return this.executeWithRetry(async () => {
      const result = await this.getDbPool().query(
        this.sqlTemplates.check_optional_fields || `
          SELECT column_name
          FROM information_schema.columns
          WHERE table_name = $1 AND column_name = ANY($2)
        `,
        [tableName, fields]
      );

      return buildOptionalFieldLookup(fields, result.rows || []);
    }, 'checkOptionalFields');
  }

  async fetchMappingBySeasonHashWithClient(client, season, oddsportalHash) {
    const result = await client.query(`
      SELECT season, oddsportal_hash, match_id, full_url, league_name, home_team, away_team,
             status, match_confidence, mapping_method, is_reversed, candidate_name,
             is_evidence_only, updated_at
      FROM matches_oddsportal_mapping
      WHERE season = $1
        AND oddsportal_hash = $2
      LIMIT 1
    `, [
      String(season),
      String(oddsportalHash)
    ]);

    return result.rows[0] || null;
  }

  async fetchMappingsBySeasonHashesWithClient(client, mappings = []) {
    if (!Array.isArray(mappings) || mappings.length === 0) {
      return [];
    }

    const seasons = normalizeUniqueTextValues(mappings.map((mapping) => mapping.season));
    const hashes = normalizeUniqueTextValues(mappings.map((mapping) => mapping.oddsportal_hash));
    const result = await client.query(`
      SELECT season, oddsportal_hash, match_id, full_url, home_team, away_team, match_confidence, updated_at,
             is_evidence_only
      FROM matches_oddsportal_mapping
      WHERE season = ANY($1::text[])
        AND oddsportal_hash = ANY($2::text[])
    `, [seasons, hashes]);

    return result.rows || [];
  }

  async fetchMatchesByIdsWithClient(client, matchIds = []) {
    if (!Array.isArray(matchIds) || matchIds.length === 0) {
      return new Map();
    }

    const result = await client.query(`
      SELECT match_id, season, match_date, home_team, away_team, pipeline_status
      FROM matches
      WHERE match_id = ANY($1::text[])
    `, [normalizeUniqueTextValues(matchIds)]);

    return new Map((result.rows || []).map((row) => [String(row.match_id), row]));
  }
}

module.exports = { ReconMappingQueries };
