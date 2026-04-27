#!/usr/bin/env node
'use strict';

const fs = require('fs/promises');
const path = require('path');
const { Pool } = require('pg');

const { DatabaseConfig } = require('../../src/infrastructure/database/PostgresClient');
const { FotMobSchemaGuard } = require('../../src/feature_engine/smelter/components/FotMobSchemaGuard');
const { isFotMobComplianceModeEnabled } = require('../../src/infrastructure/compliance/FotMobComplianceMode');

const REPORT_PATH = path.resolve(process.cwd(), 'docs/_reports/FOTMOB_COLLECTION_REPORT.md');
const DEFAULT_SAMPLE_LIMIT = 25;

function parseArgs(argv) {
  const options = {
    output: REPORT_PATH,
    sampleLimit: DEFAULT_SAMPLE_LIMIT
  };

  for (let index = 0; index < argv.length; index++) {
    const arg = argv[index];
    if (arg === '--output' && argv[index + 1]) {
      options.output = path.resolve(process.cwd(), argv[++index]);
    } else if (arg.startsWith('--output=')) {
      options.output = path.resolve(process.cwd(), arg.split('=')[1]);
    } else if (arg === '--sample-limit' && argv[index + 1]) {
      options.sampleLimit = Number.parseInt(argv[++index], 10) || DEFAULT_SAMPLE_LIMIT;
    } else if (arg.startsWith('--sample-limit=')) {
      options.sampleLimit = Number.parseInt(arg.split('=')[1], 10) || DEFAULT_SAMPLE_LIMIT;
    }
  }

  return options;
}

async function tableExists(client, tableName) {
  const result = await client.query(
    `
      SELECT to_regclass($1) AS table_name
    `,
    [`public.${tableName}`]
  );
  return Boolean(result.rows[0]?.table_name);
}

async function columnExists(client, tableName, columnName) {
  const result = await client.query(
    `
      SELECT 1
      FROM information_schema.columns
      WHERE table_schema = 'public'
        AND table_name = $1
        AND column_name = $2
      LIMIT 1
    `,
    [tableName, columnName]
  );
  return result.rowCount > 0;
}

async function collectDatabaseSnapshot(client, sampleLimit) {
  const hasMatches = await tableExists(client, 'matches');
  const hasRaw = await tableExists(client, 'raw_match_data');
  const snapshot = {
    hasMatches,
    hasRaw,
    pipeline: null,
    raw: null,
    failureReasons: [],
    rawSamples: []
  };

  if (hasMatches) {
    const hasPipelineStatus = await columnExists(client, 'matches', 'pipeline_status');
    const statusColumn = hasPipelineStatus ? 'pipeline_status' : 'status';
    snapshot.pipeline = (await client.query(
      `
        SELECT
          COUNT(*)::int AS total_matches,
          COUNT(*) FILTER (WHERE COALESCE(${statusColumn}, 'pending') = 'pending')::int AS pending_count,
          COUNT(*) FILTER (WHERE COALESCE(${statusColumn}, '') = 'harvested')::int AS harvested_count,
          COUNT(*) FILTER (WHERE COALESCE(${statusColumn}, '') = 'failed')::int AS failed_count,
          COUNT(*) FILTER (WHERE COALESCE(${statusColumn}, '') = 'RECON_LINKED')::int AS recon_linked_count
        FROM matches
      `
    )).rows[0];

    const hasLastError = await columnExists(client, 'matches', 'last_error');
    if (hasLastError) {
      snapshot.failureReasons = (await client.query(
        `
          SELECT COALESCE(NULLIF(last_error, ''), 'unknown') AS reason, COUNT(*)::int AS count
          FROM matches
          WHERE COALESCE(${statusColumn}, '') = 'failed'
          GROUP BY reason
          ORDER BY count DESC, reason ASC
          LIMIT 10
        `
      )).rows;
    }
  }

  if (hasRaw) {
    snapshot.raw = (await client.query(
      `
        SELECT
          COUNT(*)::int AS raw_count,
          COALESCE(ROUND(AVG(LENGTH(raw_data::text))), 0)::int AS avg_raw_size,
          MAX(collected_at) AS last_collected_at
        FROM raw_match_data
      `
    )).rows[0];

    snapshot.rawSamples = (await client.query(
      `
        SELECT match_id, raw_data, collected_at
        FROM raw_match_data
        ORDER BY collected_at DESC
        LIMIT $1
      `,
      [sampleLimit]
    )).rows;
  }

  return snapshot;
}

function summarizeSchemaDiff(rawSamples) {
  const guard = new FotMobSchemaGuard({
    logger: { warn() {} }
  });
  const inspections = rawSamples.map(row => guard.inspect(row.raw_data, { matchId: row.match_id }));
  return {
    inspections,
    summary: guard.summarize(inspections)
  };
}

function topEntries(counter, limit = 10) {
  return Object.entries(counter || {})
    .sort((left, right) => right[1] - left[1] || left[0].localeCompare(right[0]))
    .slice(0, limit);
}

function formatMetric(value) {
  return value === null || value === undefined ? 'n/a' : String(value);
}

function calculateRawCoverage(pipelineStats, rawStats) {
  const totalMatches = Number(pipelineStats.total_matches || 0);
  const rawCount = Number(rawStats.raw_count || 0);
  return totalMatches > 0 ? `${((rawCount / totalMatches) * 100).toFixed(2)}%` : 'n/a';
}

function formatFailureReasons(failureReasons = []) {
  if (failureReasons.length === 0) {
    return '- No persisted failure reason column was available, or no failed rows were found.';
  }

  return failureReasons.map(row => `- ${row.reason}: ${row.count}`).join('\n');
}

function formatCounterSection(counter) {
  const entries = topEntries(counter);
  if (entries.length === 0) {
    return '- None';
  }

  return entries.map(([key, count]) => `- ${key}: ${count}`).join('\n');
}

function renderReport({ generatedAt, snapshot, schema, dbError }) {
  const pipeline = snapshot?.pipeline || {};
  const raw = snapshot?.raw || {};
  const successRate = calculateRawCoverage(pipeline, raw);
  const added = topEntries(schema?.summary?.added || {});
  const removed = topEntries(schema?.summary?.removed || {});
  const failureReasons = snapshot?.failureReasons || [];
  const databaseStatus = dbError ? `unavailable (${dbError})` : 'available';

  return [
    '# FOTMOB Collection Report',
    '',
    `- Generated at: ${generatedAt}`,
    `- Compliance mode: ${isFotMobComplianceModeEnabled() ? 'enabled' : 'disabled'}`,
    `- Database status: ${databaseStatus}`,
    '',
    '## Collection Health',
    '',
    `- Total matches: ${formatMetric(pipeline.total_matches)}`,
    `- Raw JSON rows: ${formatMetric(raw.raw_count)}`,
    `- Raw coverage: ${successRate}`,
    `- Pending: ${formatMetric(pipeline.pending_count)}`,
    `- Harvested: ${formatMetric(pipeline.harvested_count)}`,
    `- Failed: ${formatMetric(pipeline.failed_count)}`,
    `- RECON linked: ${formatMetric(pipeline.recon_linked_count)}`,
    `- Average raw size: ${formatMetric(raw.avg_raw_size)} bytes`,
    `- Last collected at: ${formatMetric(raw.last_collected_at)}`,
    '',
    '## Failure Reasons',
    '',
    formatFailureReasons(failureReasons),
    '',
    '## Schema Diff',
    '',
    `- Samples inspected: ${schema?.summary?.inspected || 0}`,
    `- Samples with changes: ${schema?.summary?.changed || 0}`,
    '',
    '### Added Keys',
    '',
    formatCounterSection(Object.fromEntries(added)),
    '',
    '### Removed Keys',
    '',
    formatCounterSection(Object.fromEntries(removed)),
    '',
    '## Notes',
    '',
    '- This report reads raw_match_data first and does not call FotMob or any live network endpoint.',
    '- Schema diff is structural only: it compares key paths, not business values.',
    ''
  ].join('\n');
}

async function main() {
  const options = parseArgs(process.argv.slice(2));
  const generatedAt = new Date().toISOString();
  const pool = new Pool({
    host: DatabaseConfig.host,
    port: DatabaseConfig.port,
    database: DatabaseConfig.database,
    user: DatabaseConfig.user,
    password: DatabaseConfig.password,
    max: 2,
    connectionTimeoutMillis: Number.parseInt(process.env.DB_CONNECTION_TIMEOUT_MS || '3000', 10)
  });

  let snapshot = {
    pipeline: null,
    raw: null,
    failureReasons: [],
    rawSamples: []
  };
  let dbError = null;

  try {
    const client = await pool.connect();
    try {
      snapshot = await collectDatabaseSnapshot(client, options.sampleLimit);
    } finally {
      client.release();
    }
  } catch (error) {
    dbError = error.message;
  } finally {
    await pool.end().catch(() => {});
  }

  const schema = summarizeSchemaDiff(snapshot.rawSamples || []);
  const report = renderReport({ generatedAt, snapshot, schema, dbError });
  await fs.mkdir(path.dirname(options.output), { recursive: true });
  await fs.writeFile(options.output, report, 'utf8');
  console.log(`[FOTMOB-REPORT] ${options.output}`);
}

if (require.main === module) {
  main().catch(error => {
    console.error(`[FOTMOB-REPORT] failed: ${error.message}`);
    process.exit(1);
  });
}

module.exports = {
  collectDatabaseSnapshot,
  renderReport,
  summarizeSchemaDiff
};
