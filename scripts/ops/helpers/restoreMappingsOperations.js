'use strict';

const { L1ConfigManager } = require('../../../src/infrastructure/services/L1ConfigManager');
const { ReconParser } = require('../../../src/infrastructure/recon/ReconParser');
const { ReconMatchEvaluator } = require('../../../src/infrastructure/recon/services/ReconMatchEvaluator');
const { RECON_CONFIG } = require('../../../src/infrastructure/recon/services/ReconServiceConfig');
const { reconTaskPlannerUrlUtils } = require('../../../src/infrastructure/recon/services/ReconTaskPlannerUrlUtils');
const {
  CANONICAL_RESYNC_LEAGUE_IDS,
  TARGET_STATUSES,
  createSilentLogger
} = require('./restoreMappingsShared');
const {
  collectTeamSlugs,
  extractHashFromUrl,
  isCanonicalEventUrl
} = require('./restoreMappingsCandidates');

function buildParser() {
  return new ReconParser({
    logger: createSilentLogger(),
    config: {
      teamSlugs: collectTeamSlugs(RECON_CONFIG),
      teamMappings: RECON_CONFIG?.team_mappings || {}
    }
  });
}

function buildEvaluator(parser) {
  return new ReconMatchEvaluator({
    parser,
    logger: createSilentLogger()
  });
}

function buildResultsUrlResolver() {
  const configManager = new L1ConfigManager({ logger: createSilentLogger() });
  const runtimeResultsPath = RECON_CONFIG?.recon_runtime?.engine?.results_path
    || RECON_CONFIG?.oddsportal?.results_path
    || '/football/{country}/{league}-{season}/results/';
  const baseUrl = RECON_CONFIG?.recon_runtime?.engine?.base_url
    || RECON_CONFIG?.oddsportal?.base_url
    || 'https://www.oddsportal.com';
  const urlUtilsContext = {
    ...reconTaskPlannerUrlUtils,
    baseUrl,
    resultsPathTemplate: runtimeResultsPath
  };

  return (leagueId, season) => {
    const leagueConfig = configManager.getLeagueById(Number(leagueId));
    if (!leagueConfig) {
      return null;
    }

    return reconTaskPlannerUrlUtils.buildResultsUrl.call(urlUtilsContext, leagueConfig, season);
  };
}

async function loadTargetRows(client, season, limit = null) {
  const params = [String(season), TARGET_STATUSES];
  let limitClause = '';

  if (Number.isInteger(limit) && limit > 0) {
    params.push(limit);
    limitClause = ` LIMIT $${params.length}`;
  }

  const result = await client.query(`
    SELECT
      m.match_id,
      m.season,
      m.league_name,
      m.home_team,
      m.away_team,
      m.match_date,
      m.pipeline_status,
      NULLIF(split_part(m.match_id, '_', 1), '')::int AS league_id,
      map.oddsportal_hash AS evidence_hash,
      map.full_url AS evidence_url,
      map.match_confidence AS evidence_confidence,
      map.mapping_method AS evidence_method,
      map.home_team AS evidence_home_team,
      map.away_team AS evidence_away_team,
      r.raw_data
    FROM matches m
    LEFT JOIN matches_oddsportal_mapping map
      ON map.match_id = m.match_id
     AND map.season = m.season
     AND COALESCE(map.is_evidence_only, FALSE) = TRUE
    LEFT JOIN raw_match_data r
      ON r.match_id = m.match_id
    WHERE m.season = $1
      AND m.pipeline_status = ANY($2::text[])
    ORDER BY
      CASE WHEN map.match_id IS NULL THEN 1 ELSE 0 END ASC,
      COALESCE(map.match_confidence, 0) DESC,
      m.match_date ASC NULLS LAST,
      m.match_id ASC
    ${limitClause}
  `, params);

  return result.rows || [];
}

async function loadCanonicalResyncRows(client, season, limit = null) {
  const params = [String(season), [...CANONICAL_RESYNC_LEAGUE_IDS]];
  let limitClause = '';

  if (Number.isInteger(limit) && limit > 0) {
    params.push(limit);
    limitClause = ` LIMIT $${params.length}`;
  }

  const result = await client.query(`
    SELECT
      m.match_id,
      m.season,
      m.league_name,
      m.home_team,
      m.away_team,
      m.match_date,
      m.pipeline_status,
      NULLIF(split_part(m.match_id, '_', 1), '')::int AS league_id,
      map.oddsportal_hash,
      map.full_url,
      map.status AS mapping_status,
      map.match_confidence,
      map.mapping_method,
      map.home_team AS remote_home_team,
      map.away_team AS remote_away_team,
      r.raw_data
    FROM matches m
    JOIN matches_oddsportal_mapping map
      ON map.match_id = m.match_id
     AND map.season = m.season
     AND COALESCE(map.is_evidence_only, FALSE) = FALSE
    LEFT JOIN raw_match_data r
      ON r.match_id = m.match_id
    WHERE m.season = $1
      AND NULLIF(split_part(m.match_id, '_', 1), '')::int = ANY($2::int[])
      AND map.full_url ~ '/football/h2h/'
    ORDER BY m.match_date ASC NULLS LAST, m.match_id ASC
    ${limitClause}
  `, params);

  return result.rows || [];
}

async function loadStatusDistribution(client, season) {
  const result = await client.query(`
    SELECT COALESCE(pipeline_status, 'NULL') AS pipeline_status, COUNT(*)::int AS total
    FROM matches
    WHERE season = $1
    GROUP BY 1
    ORDER BY total DESC, pipeline_status ASC
  `, [String(season)]);

  return Object.fromEntries((result.rows || []).map((row) => [
    String(row.pipeline_status),
    Number(row.total || 0)
  ]));
}

async function loadTargetBreakdown(client, season) {
  const result = await client.query(`
    SELECT
      COUNT(*) FILTER (WHERE map.match_id IS NULL)::int AS no_mapping,
      COUNT(*) FILTER (WHERE map.match_id IS NOT NULL AND COALESCE(map.is_evidence_only, FALSE) = TRUE)::int AS evidence_only,
      COUNT(*) FILTER (WHERE map.match_id IS NOT NULL AND COALESCE(map.is_evidence_only, FALSE) = FALSE)::int AS formal_mapping,
      COUNT(*)::int AS total
    FROM matches m
    LEFT JOIN matches_oddsportal_mapping map
      ON map.match_id = m.match_id
     AND map.season = m.season
    WHERE m.season = $1
      AND m.pipeline_status = ANY($2::text[])
  `, [String(season), TARGET_STATUSES]);

  return result.rows[0] || {
    no_mapping: 0,
    evidence_only: 0,
    formal_mapping: 0,
    total: 0
  };
}

module.exports = {
  buildParser,
  buildEvaluator,
  buildResultsUrlResolver,
  loadTargetRows,
  loadCanonicalResyncRows,
  loadStatusDistribution,
  loadTargetBreakdown
};
