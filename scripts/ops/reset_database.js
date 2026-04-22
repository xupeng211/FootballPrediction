#!/usr/bin/env node
'use strict';

const { Pool } = require('pg');

const { buildDbConnectionConfig } = require('./helpers/dbBlueprint');

const PRIMARY_TABLE = 'matches';
const REQUIRED_TABLES = [
  PRIMARY_TABLE,
  'bookmaker_odds_history',
  'raw_match_data',
  'predictions'
];

function quoteIdentifier(identifier) {
  return `"${String(identifier || '').replace(/"/g, '""')}"`;
}

function parseArgs(argv = process.argv.slice(2)) {
  const options = {
    commit: false
  };

  for (const token of argv) {
    if (!token) {
      continue;
    }

    if (token === '--commit') {
      options.commit = true;
      continue;
    }

    throw new Error(`未知参数: ${token}`);
  }

  return options;
}

async function resolveTargetTables(client) {
  const childResult = await client.query(
    `
      SELECT DISTINCT conrelid::regclass::text AS table_name
      FROM pg_constraint
      WHERE contype = 'f'
        AND confrelid = 'public.matches'::regclass
      ORDER BY table_name ASC
    `
  );

  return [...new Set([...REQUIRED_TABLES, ...childResult.rows.map((row) => String(row.table_name))])];
}

async function inspectTableCounts(client, tableNames = []) {
  const counts = [];

  for (const tableName of tableNames) {
    const result = await client.query(`SELECT COUNT(*)::int AS row_count FROM ${quoteIdentifier(tableName)}`);
    counts.push({
      table_name: tableName,
      row_count: Number(result.rows[0]?.row_count || 0)
    });
  }

  return counts;
}

async function resetDatabase(options = {}) {
  const pool = new Pool(buildDbConnectionConfig());
  const client = await pool.connect();

  try {
    const tableNames = await resolveTargetTables(client);
    const before = await inspectTableCounts(client, tableNames);

    if (!options.commit) {
      return {
        committed: false,
        tableNames,
        before,
        after: before
      };
    }

    await client.query('BEGIN');
    await client.query(`TRUNCATE TABLE ${tableNames.map(quoteIdentifier).join(', ')} RESTART IDENTITY CASCADE`);
    await client.query('COMMIT');

    const after = await inspectTableCounts(client, tableNames);

    return {
      committed: true,
      tableNames,
      before,
      after
    };
  } catch (error) {
    await client.query('ROLLBACK').catch(() => {});
    throw error;
  } finally {
    client.release();
    await pool.end();
  }
}

function formatCounts(counts = []) {
  return counts.map((item) => `${item.table_name}:${item.row_count}`).join(', ');
}

async function main() {
  const options = parseArgs();
  const result = await resetDatabase(options);

  console.log(
    `[RESET-DATABASE] mode=${result.committed ? 'commit' : 'dry-run'} `
    + `tables=${result.tableNames.join(',')} `
    + `before=${formatCounts(result.before)} `
    + `after=${formatCounts(result.after)}`
  );
}

if (require.main === module) {
  main().catch((error) => {
    console.error(`[RESET-DATABASE] 失败: ${error.message}`);
    process.exit(1);
  });
}

module.exports = {
  inspectTableCounts,
  parseArgs,
  resetDatabase,
  resolveTargetTables
};
