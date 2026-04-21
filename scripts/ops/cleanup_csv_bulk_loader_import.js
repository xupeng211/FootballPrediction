#!/usr/bin/env node
'use strict';

const { Pool } = require('pg');

const { Normalizer } = require('../../src/utils/Normalizer');
const { buildDbConnectionConfig } = require('./helpers/dbBlueprint');

function parseArgs(argv = process.argv.slice(2)) {
  const options = {
    commit: false,
    season: '2024-2025',
    leagueName: 'Premier League',
    dataSource: 'CSV_BULK_LOADER',
    dataVersion: 'TEP001_PHASE1'
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

    if (token === '--season') {
      options.season = value;
    } else if (token === '--league') {
      options.leagueName = value;
    } else if (token === '--data-source') {
      options.dataSource = value;
    } else if (token === '--data-version') {
      options.dataVersion = value;
    } else {
      throw new Error(`未知参数: ${token}`);
    }

    index += 1;
  }

  options.season = Normalizer.normalizeSeason(options.season);
  return options;
}

async function inspectTargets(client, options) {
  const result = await client.query(`
    WITH target_matches AS (
      SELECT match_id
      FROM matches
      WHERE season = $1
        AND league_name = $2
        AND data_source = $3
        AND data_version = $4
    )
    SELECT
      (SELECT COUNT(*) FROM target_matches) AS target_match_rows,
      (SELECT COUNT(*) FROM bookmaker_odds_history boh WHERE boh.match_id IN (SELECT match_id FROM target_matches)) AS target_odds_rows
  `, [
    options.season,
    options.leagueName,
    options.dataSource,
    options.dataVersion
  ]);

  return result.rows[0];
}

async function cleanupImport(options = {}) {
  const pool = new Pool(buildDbConnectionConfig());
  const client = await pool.connect();

  try {
    const inspection = await inspectTargets(client, options);

    if (!options.commit) {
      return {
        ...inspection,
        deleted_match_rows: 0,
        deleted_odds_rows: 0,
        committed: false
      };
    }

    await client.query('BEGIN');
    const deletion = await client.query(`
      WITH target_matches AS (
        SELECT match_id
        FROM matches
        WHERE season = $1
          AND league_name = $2
          AND data_source = $3
          AND data_version = $4
      ),
      deleted_odds AS (
        DELETE FROM bookmaker_odds_history
        WHERE match_id IN (SELECT match_id FROM target_matches)
        RETURNING match_id
      ),
      deleted_matches AS (
        DELETE FROM matches
        WHERE match_id IN (SELECT match_id FROM target_matches)
        RETURNING match_id
      )
      SELECT
        (SELECT COUNT(*) FROM deleted_matches) AS deleted_match_rows,
        (SELECT COUNT(*) FROM deleted_odds) AS deleted_odds_rows
    `, [
      options.season,
      options.leagueName,
      options.dataSource,
      options.dataVersion
    ]);
    await client.query('COMMIT');

    return {
      ...inspection,
      ...deletion.rows[0],
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
  const result = await cleanupImport(options);
  console.log(
    `[CLEANUP-CSV-IMPORT] season=${options.season} league=${options.leagueName} `
    + `data_source=${options.dataSource} data_version=${options.dataVersion} `
    + `target_matches=${result.target_match_rows} target_odds=${result.target_odds_rows} `
    + `deleted_matches=${result.deleted_match_rows} deleted_odds=${result.deleted_odds_rows} `
    + `mode=${result.committed ? 'commit' : 'dry-run'}`
  );
}

if (require.main === module) {
  main().catch((error) => {
    console.error(`[CLEANUP-CSV-IMPORT] 失败: ${error.message}`);
    process.exit(1);
  });
}

module.exports = {
  cleanupImport,
  inspectTargets,
  parseArgs
};
