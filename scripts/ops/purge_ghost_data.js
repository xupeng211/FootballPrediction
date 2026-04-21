#!/usr/bin/env node
'use strict';

const { Pool } = require('pg');

const { Normalizer } = require('../../src/utils/Normalizer');
const { buildDbConnectionConfig } = require('./helpers/dbBlueprint');

const DEFAULT_LEAGUE = 'Premier League';
const DEFAULT_SEASON = '2024-2025';
const DEFAULT_CUTOFF = '2025-06-01T00:00:00Z';
const MATCH_REF_TABLES = [
  'bookmaker_odds_history',
  'match_features_training',
  'matches_oddsportal_mapping',
  'odds',
  'predictions',
  'raw_match_data'
];

function parseArgs(argv = process.argv.slice(2)) {
  const options = {
    commit: false,
    leagueName: DEFAULT_LEAGUE,
    season: Normalizer.normalizeSeason(DEFAULT_SEASON),
    cutoffDate: DEFAULT_CUTOFF
  };

  for (let index = 0; index < argv.length; index++) {
    const token = String(argv[index] || '').trim();
    if (!token) {
      continue;
    }

    if (token === '--commit') {
      options.commit = true;
      continue;
    }

    const value = argv[index + 1];
    if (!value || String(value).startsWith('--')) {
      throw new Error(`参数 ${token} 缺少值`);
    }

    if (token === '--league') {
      options.leagueName = value;
    } else if (token === '--season') {
      options.season = Normalizer.normalizeSeason(value);
    } else if (token === '--cutoff') {
      options.cutoffDate = value;
    } else {
      throw new Error(`未知参数: ${token}`);
    }

    index += 1;
  }

  return options;
}

async function inspectGhostTargets(client, options) {
  const result = await client.query(`
    WITH ghost_matches AS (
      SELECT match_id, data_source
      FROM matches
      WHERE league_name = $1
        AND season = $2
        AND match_date > $3::timestamptz
    )
    SELECT
      (SELECT COUNT(*) FROM ghost_matches) AS ghost_match_rows,
      COALESCE(
        (
          SELECT json_object_agg(data_source, row_count)
          FROM (
            SELECT data_source, COUNT(*)::int AS row_count
            FROM ghost_matches
            GROUP BY data_source
          ) grouped
        ),
        '{}'::json
      ) AS by_source
  `, [options.leagueName, options.season, options.cutoffDate]);

  return result.rows[0];
}

async function deleteByMatchIds(client, tableName, ghostFilterSql, params) {
  const result = await client.query(`
    WITH ghost_matches AS (
      ${ghostFilterSql}
    )
    DELETE FROM ${tableName}
    WHERE match_id IN (SELECT match_id FROM ghost_matches)
    RETURNING match_id
  `, params);

  return result.rowCount;
}

async function purgeGhostData(options = {}) {
  const pool = new Pool(buildDbConnectionConfig());
  const client = await pool.connect();
  const ghostFilterSql = `
    SELECT match_id
    FROM matches
    WHERE league_name = $1
      AND season = $2
      AND match_date > $3::timestamptz
  `;
  const params = [options.leagueName, options.season, options.cutoffDate];

  try {
    const inspection = await inspectGhostTargets(client, options);

    if (!options.commit) {
      return {
        ...inspection,
        deletedMatches: 0,
        deletedRefs: Object.fromEntries(MATCH_REF_TABLES.map((tableName) => [tableName, 0])),
        committed: false
      };
    }

    await client.query('BEGIN');
    const deletedRefs = {};
    for (const tableName of MATCH_REF_TABLES) {
      deletedRefs[tableName] = await deleteByMatchIds(client, tableName, ghostFilterSql, params);
    }

    const deletedMatches = await deleteByMatchIds(client, 'matches', ghostFilterSql, params);
    await client.query('COMMIT');

    return {
      ...inspection,
      deletedMatches,
      deletedRefs,
      committed: true
    };
  } catch (error) {
    await client.query('ROLLBACK').catch(() => {});
    throw error;
  } finally {
    client.release();
    await pool.end();
  }
}

async function main() {
  const options = parseArgs();
  const result = await purgeGhostData(options);
  console.log(
    `[PURGE-GHOST] league=${options.leagueName} season=${options.season} cutoff=${options.cutoffDate} `
    + `ghost_matches=${result.ghost_match_rows} by_source=${JSON.stringify(result.by_source)} `
    + `deleted_matches=${result.deletedMatches} deleted_refs=${JSON.stringify(result.deletedRefs)} `
    + `mode=${result.committed ? 'commit' : 'dry-run'}`
  );
}

if (require.main === module) {
  main().catch((error) => {
    console.error(`[PURGE-GHOST] 失败: ${error.message}`);
    process.exit(1);
  });
}

module.exports = {
  MATCH_REF_TABLES,
  inspectGhostTargets,
  parseArgs,
  purgeGhostData
};
