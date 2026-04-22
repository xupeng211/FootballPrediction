#!/usr/bin/env node
'use strict';

const { Pool } = require('pg');

const { Normalizer } = require('../../src/utils/Normalizer');
const { buildDbConnectionConfig } = require('./helpers/dbBlueprint');

const DEFAULT_DATA_SOURCE = 'ProductionHarvester';
const DEFAULT_SEASON = '2024-2025';
const REFERENCE_ORPHAN_COUNT = 978;

function parsePositiveInteger(rawValue, flagName) {
    const parsed = Number.parseInt(String(rawValue || '').trim(), 10);
    if (!Number.isFinite(parsed) || parsed < 0) {
        throw new Error(`参数 ${flagName} 必须是非负整数`);
    }
    return parsed;
}

function parseArgs(argv = process.argv.slice(2)) {
    const options = {
        commit: false,
        dataSource: DEFAULT_DATA_SOURCE,
        season: Normalizer.normalizeSeason(DEFAULT_SEASON),
        expectedCount: null,
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
            options.season = Normalizer.normalizeSeason(value);
        } else if (token === '--data-source') {
            options.dataSource = String(value).trim();
        } else if (token === '--expected-count') {
            options.expectedCount = parsePositiveInteger(value, token);
        } else {
            throw new Error(`未知参数: ${token}`);
        }

        index += 1;
    }

    return options;
}

async function inspectTargets(client, options) {
    const result = await client.query(
        `
    WITH orphan_matches AS (
      SELECT match_id, league_name
      FROM matches
      WHERE data_source = $1
        AND season = $2
        AND NOT EXISTS (
          SELECT 1
          FROM bookmaker_odds_history h
          WHERE h.match_id = matches.match_id
        )
    ),
    grouped AS (
      SELECT league_name, COUNT(*)::int AS row_count
      FROM orphan_matches
      GROUP BY league_name
      ORDER BY league_name
    )
    SELECT
      (SELECT COUNT(*)::int FROM orphan_matches) AS orphan_match_rows,
      COALESCE(
        (
          SELECT json_object_agg(league_name, row_count)
          FROM grouped
        ),
        '{}'::json
      ) AS by_league
  `,
        [options.dataSource, options.season]
    );

    return result.rows[0];
}

function assertExpectedCount(targetCount, options) {
    if (options.expectedCount === null) {
        return;
    }

    if (Number(targetCount) !== Number(options.expectedCount)) {
        throw new Error(`命中数量与预期不一致: actual=${targetCount} expected=${options.expectedCount}`);
    }
}

async function purgeOrphans(options = {}) {
    const pool = new Pool(buildDbConnectionConfig());
    const client = await pool.connect();

    try {
        const inspection = await inspectTargets(client, options);
        assertExpectedCount(inspection.orphan_match_rows, options);

        if (!options.commit) {
            return {
                ...inspection,
                deleted_match_rows: 0,
                committed: false,
            };
        }

        await client.query('BEGIN');
        const deletion = await client.query(
            `
      WITH target_matches AS (
        SELECT match_id
        FROM matches
        WHERE data_source = $1
          AND season = $2
          AND NOT EXISTS (
            SELECT 1
            FROM bookmaker_odds_history h
            WHERE h.match_id = matches.match_id
          )
      )
      DELETE FROM matches
      WHERE match_id IN (SELECT match_id FROM target_matches)
      RETURNING match_id
    `,
            [options.dataSource, options.season]
        );
        await client.query('COMMIT');

        return {
            ...inspection,
            deleted_match_rows: deletion.rowCount,
            committed: true,
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
    const result = await purgeOrphans(options);
    const referenceDelta = Number(result.orphan_match_rows) - REFERENCE_ORPHAN_COUNT;

    console.log(
        `[PURGE-ORPHANS] season=${options.season} data_source=${options.dataSource} ` +
            `orphan_matches=${result.orphan_match_rows} by_league=${JSON.stringify(result.by_league)} ` +
            `reference_count=${REFERENCE_ORPHAN_COUNT} reference_delta=${referenceDelta} ` +
            `deleted_matches=${result.deleted_match_rows} ` +
            `mode=${result.committed ? 'commit' : 'dry-run'}`
    );
}

if (require.main === module) {
    main().catch(error => {
        console.error(`[PURGE-ORPHANS] 失败: ${error.message}`);
        process.exit(1);
    });
}

module.exports = {
    REFERENCE_ORPHAN_COUNT,
    inspectTargets,
    parseArgs,
    purgeOrphans,
};
