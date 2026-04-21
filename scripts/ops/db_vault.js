#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');
const { Pool } = require('pg');
const {
  REPO_ROOT,
  buildDbConnectionConfig,
  ensureBlueprintOnCurrentDatabase
} = require('./helpers/dbBlueprint');

const SNAPSHOT_DIR = path.join(REPO_ROOT, 'data', 'snapshots');
const DEFAULT_SNAPSHOT_PATH = path.join(SNAPSHOT_DIR, 'mapping_last_stable.sql');
const MATCH_SNAPSHOT_COLUMNS = [
  'match_id',
  'external_id',
  'league_name',
  'season',
  'home_team',
  'away_team',
  'home_score',
  'away_score',
  'actual_result',
  'match_date',
  'venue',
  'status',
  'is_finished',
  'collection_date',
  'created_at',
  'updated_at',
  'data_version',
  'data_source',
  'pipeline_status'
];
const SNAPSHOT_COLUMNS = [
  'id',
  'match_id',
  'oddsportal_hash',
  'full_url',
  'season',
  'league_name',
  'home_team',
  'away_team',
  'status',
  'match_confidence',
  'mapping_method',
  'is_reversed',
  'candidate_name',
  'is_evidence_only',
  'retry_count',
  'last_error',
  'harvested_at',
  'created_at',
  'updated_at'
];
const BATCH_SIZE = 200;

function printUsage() {
  console.log('用法: node scripts/ops/db_vault.js <backup|restore> [--file <path>] [--reason <text>]');
}

function parseArgs(argv = process.argv.slice(2)) {
  const args = [...argv];
  const command = String(args.shift() || '').trim().toLowerCase();
  const result = {
    command,
    filePath: DEFAULT_SNAPSHOT_PATH,
    reason: 'manual',
    skipBlueprint: false
  };

  for (let index = 0; index < args.length; index++) {
    const token = args[index];
    if (token === '--file') {
      const rawFilePath = args[++index];
      if (!rawFilePath || rawFilePath.startsWith('--')) {
        throw new Error('参数 --file 缺少路径');
      }
      result.filePath = path.resolve(REPO_ROOT, rawFilePath);
    } else if (token === '--reason') {
      const rawReason = args[++index];
      if (!rawReason || rawReason.startsWith('--')) {
        throw new Error('参数 --reason 缺少内容');
      }
      result.reason = String(rawReason).trim() || 'manual';
    } else if (token === '--skip-blueprint') {
      result.skipBlueprint = true;
    }
  }

  if (!['backup', 'restore'].includes(result.command)) {
    throw new Error(`非法命令: ${result.command || '<empty>'}`);
  }

  return result;
}

function ensureSnapshotDirectory(filePath) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
}

function escapeSqlString(value) {
  return String(value).replace(/'/g, "''");
}

function formatSqlLiteral(value) {
  if (value === null || value === undefined) {
    return 'NULL';
  }

  if (typeof value === 'number') {
    return Number.isFinite(value) ? String(value) : 'NULL';
  }

  if (typeof value === 'boolean') {
    return value ? 'TRUE' : 'FALSE';
  }

  if (value instanceof Date) {
    return `'${escapeSqlString(value.toISOString())}'::timestamptz`;
  }

  return `'${escapeSqlString(value)}'`;
}

function chunkRows(rows, size = BATCH_SIZE) {
  const chunks = [];
  for (let index = 0; index < rows.length; index += size) {
    chunks.push(rows.slice(index, index + size));
  }
  return chunks;
}

function buildBulkInsertStatements({ tableName, columns, rows, conflictClause = '' }) {
  if (!Array.isArray(rows) || rows.length === 0) {
    return [];
  }

  const insertPrefix = `INSERT INTO ${tableName} (${columns.join(', ')}) VALUES`;
  return chunkRows(rows).map((chunk) => {
    const values = chunk.map((row) => (
      `(${columns.map((column) => formatSqlLiteral(row[column])).join(', ')})`
    ));
    const suffix = conflictClause ? `\n${conflictClause}` : '';
    return `${insertPrefix}\n${values.join(',\n')}${suffix};`;
  });
}

function buildSnapshotSql({ matchRows = [], mappingRows = [], reason = 'manual' } = {}) {
  const matchConflictColumns = MATCH_SNAPSHOT_COLUMNS.filter((column) => column !== 'match_id');
  const matchConflictClause = `
ON CONFLICT (match_id) DO UPDATE SET
${matchConflictColumns.map((column) => `  ${column} = EXCLUDED.${column}`).join(',\n')}
  `.trimEnd();
  const statements = [
    '-- ============================================================================',
    '-- FootballPrediction DB Vault Snapshot',
    `-- Generated at: ${new Date().toISOString()}`,
    `-- Reason: ${reason}`,
    `-- Match row count: ${matchRows.length}`,
    `-- Mapping row count: ${mappingRows.length}`,
    '-- ============================================================================',
    'BEGIN;'
  ];

  statements.push(...buildBulkInsertStatements({
    tableName: 'matches',
    columns: MATCH_SNAPSHOT_COLUMNS,
    rows: matchRows,
    conflictClause: matchConflictClause
  }));

  statements.push('TRUNCATE TABLE matches_oddsportal_mapping RESTART IDENTITY;');
  statements.push(...buildBulkInsertStatements({
    tableName: 'matches_oddsportal_mapping',
    columns: SNAPSHOT_COLUMNS,
    rows: mappingRows
  }));

  if (mappingRows.length > 0) {
    statements.push(`
      SELECT setval(
        pg_get_serial_sequence('matches_oddsportal_mapping', 'id'),
        COALESCE((SELECT MAX(id) FROM matches_oddsportal_mapping), 1),
        TRUE
      );
    `.trim());
  } else {
    statements.push(`
      SELECT setval(
        pg_get_serial_sequence('matches_oddsportal_mapping', 'id'),
        1,
        FALSE
      );
    `.trim());
  }

  statements.push(`
    UPDATE matches m
    SET pipeline_status = 'RECON_LINKED',
        updated_at = NOW()
    FROM matches_oddsportal_mapping map
    WHERE map.match_id = m.match_id
      AND map.season = m.season
      AND COALESCE(map.is_evidence_only, FALSE) = FALSE
      AND m.pipeline_status IS DISTINCT FROM 'RECON_LINKED';
  `.trim());
  statements.push('COMMIT;');
  statements.push('');

  return `${statements.join('\n\n')}\n`;
}

async function withPool(callback) {
  const pool = new Pool(buildDbConnectionConfig());
  try {
    return await callback(pool);
  } finally {
    await pool.end();
  }
}

async function backupSnapshot(options) {
  ensureSnapshotDirectory(options.filePath);
  const startTime = Date.now();
  return withPool(async (pool) => {
    const mappingResult = await pool.query(`
      SELECT ${SNAPSHOT_COLUMNS.map((column) => `map.${column}`).join(', ')}
      FROM matches_oddsportal_mapping
      map
      ORDER BY map.season ASC, map.match_id ASC, map.id ASC
    `);
    const matchResult = await pool.query(`
      SELECT ${MATCH_SNAPSHOT_COLUMNS.map((column) => `m.${column}`).join(', ')}
      FROM matches m
      INNER JOIN (
        SELECT DISTINCT match_id
        FROM matches_oddsportal_mapping
      ) map ON map.match_id = m.match_id
      ORDER BY m.season ASC, m.match_id ASC
    `);
    const distinctMatchIds = new Set((mappingResult.rows || []).map((row) => String(row.match_id)));
    if (distinctMatchIds.size !== matchResult.rowCount) {
      throw new Error(`快照父表不完整: mapping_match_ids=${distinctMatchIds.size}, matches=${matchResult.rowCount}`);
    }

    const sql = buildSnapshotSql({
      matchRows: matchResult.rows || [],
      mappingRows: mappingResult.rows || [],
      reason: options.reason
    });
    fs.writeFileSync(options.filePath, sql, 'utf8');

    const durationMs = Date.now() - startTime;
    console.log(
      `[DB-VAULT] backup 成功: matches=${matchResult.rowCount} mappings=${mappingResult.rowCount} file=${options.filePath} duration_ms=${durationMs}`
    );
    return {
      matchRowCount: matchResult.rowCount,
      mappingRowCount: mappingResult.rowCount,
      filePath: options.filePath,
      durationMs
    };
  });
}

async function restoreSnapshot(options) {
  const snapshotPath = path.resolve(options.filePath);
  if (!fs.existsSync(snapshotPath)) {
    throw new Error(`快照文件不存在: ${snapshotPath}`);
  }

  const startTime = Date.now();
  if (!options.skipBlueprint) {
    const blueprintResult = await ensureBlueprintOnCurrentDatabase();
    console.log(
      `[DB-VAULT] blueprint ${blueprintResult.applied ? '已应用' : '已就绪'}: mode=${blueprintResult.applyMode} applied_files=${blueprintResult.appliedFiles.length}`
    );
  }

  const sql = fs.readFileSync(snapshotPath, 'utf8');
  return withPool(async (pool) => {
    await pool.query(sql);
    const [mappingCountResult, matchCountResult] = await Promise.all([
      pool.query('SELECT COUNT(*)::int AS total FROM matches_oddsportal_mapping'),
      pool.query(`
        SELECT COUNT(*)::int AS total
        FROM matches
        WHERE match_id IN (SELECT match_id FROM matches_oddsportal_mapping)
      `)
    ]);
    const durationMs = Date.now() - startTime;
    const restoredRows = Number(mappingCountResult.rows[0]?.total || 0);
    const restoredMatches = Number(matchCountResult.rows[0]?.total || 0);
    console.log(
      `[DB-VAULT] restore 成功: matches=${restoredMatches} mappings=${restoredRows} file=${snapshotPath} duration_ms=${durationMs}`
    );
    return {
      restoredMatches,
      restoredRows,
      filePath: snapshotPath,
      durationMs
    };
  });
}

async function main(argv = process.argv.slice(2)) {
  const options = parseArgs(argv);
  if (options.command === 'backup') {
    return backupSnapshot(options);
  }
  return restoreSnapshot(options);
}

if (require.main === module) {
  main().catch((error) => {
    console.error(`[DB-VAULT] 失败: ${error.message}`);
    process.exit(1);
  });
}

module.exports = {
  SNAPSHOT_DIR,
  DEFAULT_SNAPSHOT_PATH,
  MATCH_SNAPSHOT_COLUMNS,
  SNAPSHOT_COLUMNS,
  parseArgs,
  buildSnapshotSql,
  backupSnapshot,
  restoreSnapshot,
  main
};
