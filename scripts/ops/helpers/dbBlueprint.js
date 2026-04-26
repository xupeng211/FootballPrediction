'use strict';

const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const { Pool } = require('pg');

const REPO_ROOT = path.resolve(__dirname, '../../..');
const INIT_DB_PATH = path.join(REPO_ROOT, 'deploy/docker/init_db.sql');
const MIGRATIONS_DIR = path.join(REPO_ROOT, 'database/migrations');
const CORE_TABLES = ['matches', 'raw_match_data', 'matches_oddsportal_mapping'];
const DEFAULT_CONNECT_TIMEOUT_MS = Number.parseInt(
  process.env.DB_BLUEPRINT_CONNECT_TIMEOUT_MS || '5000',
  10
);
const DEFAULT_STATEMENT_TIMEOUT_MS = Number.parseInt(
  process.env.DB_BLUEPRINT_STATEMENT_TIMEOUT_MS || '30000',
  10
);
const REQUIRED_COLUMNS = {
  matches: ['match_id', 'season', 'pipeline_status'],
  raw_match_data: ['match_id', 'raw_data', 'data_version'],
  matches_oddsportal_mapping: ['match_id', 'season', 'oddsportal_hash', 'is_evidence_only']
};

function resolveBlueprintLogger(options = {}) {
  if (typeof options.logger === 'function') {
    return options.logger;
  }

  if (process.env.DB_BLUEPRINT_DEBUG === '1') {
    return (message) => console.log(`[DB-BLUEPRINT] ${message}`);
  }

  return null;
}

function emitBlueprintLog(logger, message) {
  if (typeof logger === 'function') {
    logger(message);
  }
}

function quoteIdentifier(identifier) {
  return `"${String(identifier || '').replace(/"/g, '""')}"`;
}

function parseVersionTokens(fileName) {
  const match = String(fileName || '').match(/^V(\d+(?:\.\d+)*)__/i);
  if (!match) {
    return [Number.MAX_SAFE_INTEGER];
  }

  return match[1]
    .split('.')
    .map((token) => Number.parseInt(token, 10))
    .filter((token) => Number.isFinite(token));
}

function compareVersionedSqlFiles(left, right) {
  const leftTokens = parseVersionTokens(path.basename(left));
  const rightTokens = parseVersionTokens(path.basename(right));
  const length = Math.max(leftTokens.length, rightTokens.length);
  for (let index = 0; index < length; index++) {
    const leftToken = leftTokens[index] ?? 0;
    const rightToken = rightTokens[index] ?? 0;
    if (leftToken !== rightToken) {
      return leftToken - rightToken;
    }
  }

  return String(left).localeCompare(String(right));
}

function resolveBlueprintSqlFiles() {
  const migrationFiles = fs.readdirSync(MIGRATIONS_DIR)
    .filter((fileName) => fileName.endsWith('.sql'))
    .map((fileName) => path.join(MIGRATIONS_DIR, fileName))
    .sort(compareVersionedSqlFiles);

  return [INIT_DB_PATH, ...migrationFiles];
}

function resolveMigrationSqlFiles() {
  return resolveBlueprintSqlFiles()
    .filter((filePath) => path.dirname(filePath) === MIGRATIONS_DIR);
}

function readExecutableSql(filePath) {
  return fs.readFileSync(filePath, 'utf8')
    .replace(/^\uFEFF/, '')
    .split('\n')
    .filter((line) => !line.trim().startsWith('\\'))
    .join('\n')
    .trim();
}

function buildDbConnectionConfig(overrides = {}) {
  return {
    host: process.env.DB_HOST || '127.0.0.1',
    port: Number.parseInt(process.env.DB_PORT || '5432', 10),
    database: process.env.DB_NAME || 'football_db',
    user: process.env.DB_USER || 'football_user',
    password: process.env.DB_PASSWORD || 'football_pass',
    connectionTimeoutMillis: DEFAULT_CONNECT_TIMEOUT_MS,
    ...overrides
  };
}

function formatDbConnectionTrace(connectionConfig = {}) {
  return [
    `host=${connectionConfig.host || '127.0.0.1'}`,
    `port=${connectionConfig.port || 5432}`,
    `user=${connectionConfig.user || 'football_user'}`,
    `database=${connectionConfig.database || 'football_db'}`,
    `connection_timeout_ms=${connectionConfig.connectionTimeoutMillis ?? 'unset'}`
  ].join(' ');
}

async function checkDbConnection(pool, connectionConfig = {}, options = {}) {
  const label = options.label || 'db_blueprint';
  const startedAt = Date.now();
  console.log(`[DB-BLUEPRINT] checkDbConnection.start label=${label} ${formatDbConnectionTrace(connectionConfig)}`);

  try {
    const client = await pool.connect();
    console.log(`[DB-BLUEPRINT] checkDbConnection.ok label=${label} ms=${Date.now() - startedAt}`);
    return client;
  } catch (err) {
    const elapsedMs = Date.now() - startedAt;
    console.error(
      `[DB-BLUEPRINT] checkDbConnection.fail label=${label} ms=${elapsedMs} ${formatDbConnectionTrace(connectionConfig)}`
    );
    console.error(err?.stack || err);
    throw err;
  }
}

function createBlueprintCheckDatabaseName(prefix = 'gatekeeper_cold_start') {
  const suffix = `${Date.now()}_${crypto.randomUUID().replace(/-/g, '').slice(0, 8)}`;
  return `${prefix}_${suffix}`
    .toLowerCase()
    .replace(/[^a-z0-9_]/g, '_')
    .slice(0, 60);
}

async function executeSqlFile(client, filePath, options = {}) {
  const sql = readExecutableSql(filePath);
  if (!sql) {
    emitBlueprintLog(options.logger, `skip_empty_sql file=${path.relative(REPO_ROOT, filePath)}`);
    return;
  }

  const relativePath = path.relative(REPO_ROOT, filePath);
  const startedAt = Date.now();
  emitBlueprintLog(options.logger, `apply_sql.start file=${relativePath}`);
  await client.query(sql);
  emitBlueprintLog(options.logger, `apply_sql.done file=${relativePath} ms=${Date.now() - startedAt}`);
}

async function applyBlueprint(client, filePaths = resolveBlueprintSqlFiles(), options = {}) {
  const applied = [];
  for (const filePath of filePaths) {
    await executeSqlFile(client, filePath, options);
    applied.push(path.relative(REPO_ROOT, filePath));
  }
  return applied;
}

async function inspectCoreSchema(client) {
  const tableResult = await client.query(`
    SELECT tablename
    FROM pg_tables
    WHERE schemaname = 'public'
      AND tablename = ANY($1::text[])
    ORDER BY tablename ASC
  `, [CORE_TABLES]);

  const columnPairs = Object.entries(REQUIRED_COLUMNS).flatMap(([tableName, columns]) => (
    columns.map((columnName) => [tableName, columnName])
  ));
  const columnResult = await client.query(`
    SELECT table_name, column_name
    FROM information_schema.columns
    WHERE table_schema = 'public'
      AND (table_name, column_name) IN (${columnPairs.map((_, index) => (
        `($${index * 2 + 1}, $${index * 2 + 2})`
      )).join(', ')})
    ORDER BY table_name ASC, column_name ASC
  `, columnPairs.flat());

  const existingTables = new Set(tableResult.rows.map((row) => String(row.tablename)));
  const existingColumns = new Set(columnResult.rows.map((row) => `${row.table_name}.${row.column_name}`));

  const missingTables = CORE_TABLES.filter((tableName) => !existingTables.has(tableName));
  const missingColumns = Object.entries(REQUIRED_COLUMNS).flatMap(([tableName, columns]) => (
    columns
      .filter((columnName) => !existingColumns.has(`${tableName}.${columnName}`))
      .map((columnName) => `${tableName}.${columnName}`)
  ));

  return {
    tables: CORE_TABLES.reduce((accumulator, tableName) => ({
      ...accumulator,
      [tableName]: existingTables.has(tableName)
    }), {}),
    missingTables,
    missingColumns
  };
}

async function assertCoreSchema(client) {
  const inspection = await inspectCoreSchema(client);
  if (inspection.missingTables.length > 0 || inspection.missingColumns.length > 0) {
    const issues = [];
    if (inspection.missingTables.length > 0) {
      issues.push(`缺少核心表: ${inspection.missingTables.join(', ')}`);
    }
    if (inspection.missingColumns.length > 0) {
      issues.push(`缺少核心列: ${inspection.missingColumns.join(', ')}`);
    }
    throw new Error(issues.join('；'));
  }
  return inspection;
}

async function runBlueprintWriteProbe(client, options = {}) {
  const probeExternalId = `${Date.now()}`;
  const probeMatchId = `999_20252026_${probeExternalId}`;
  emitBlueprintLog(options.logger, `write_probe.start match_id=${probeMatchId}`);
  await client.query('BEGIN');
  try {
    await client.query(`
      INSERT INTO matches (
        match_id,
        external_id,
        league_name,
        season,
        home_team,
        away_team,
        match_date,
        status,
        is_finished,
        data_source,
        pipeline_status
      ) VALUES (
        $1,
        $2,
        'Cold Start League',
        '2025/2026',
        'Probe Home',
        'Probe Away',
        NOW(),
        'scheduled',
        FALSE,
        'ColdStartProbe',
        'harvested'
      )
    `, [probeMatchId, probeExternalId]);

    await client.query(`
      INSERT INTO raw_match_data (
        match_id,
        external_id,
        raw_data,
        collected_at,
        data_version
      ) VALUES (
        $1,
        $2,
        $3::jsonb,
        NOW(),
        'V26.1'
      )
    `, [
      probeMatchId,
      `${Date.now()}`,
      JSON.stringify({
        matchId: probeMatchId,
        general: { matchId: probeMatchId },
        header: { status: { finished: false } }
      })
    ]);

    await client.query(`
      INSERT INTO matches_oddsportal_mapping (
        match_id,
        oddsportal_hash,
        full_url,
        season,
        league_name,
        home_team,
        away_team,
        status,
        match_confidence,
        mapping_method,
        is_reversed,
        candidate_name,
        is_evidence_only,
        retry_count
      ) VALUES (
        $1,
        'abcd1234',
        'https://www.oddsportal.com/football/test/cold-start-probe-abcd1234/',
        '2025/2026',
        'Cold Start League',
        'Probe Home',
        'Probe Away',
        'pending',
        0.95,
        'protocol_extract',
        FALSE,
        'Probe Home vs Probe Away',
        FALSE,
        0
      )
    `, [probeMatchId]);

    await client.query('ROLLBACK');
    emitBlueprintLog(options.logger, `write_probe.done match_id=${probeMatchId}`);
  } catch (error) {
    await client.query('ROLLBACK');
    emitBlueprintLog(options.logger, `write_probe.fail match_id=${probeMatchId} error=${error.message}`);
    throw error;
  }
}

async function withTemporaryDatabase(options = {}, callback) {
  const logger = resolveBlueprintLogger(options);
  const adminConfig = buildDbConnectionConfig({
    database: options.adminDatabase || process.env.DB_ADMIN_NAME || 'postgres'
  });
  const adminPool = new Pool(adminConfig);
  const databaseName = options.databaseName || createBlueprintCheckDatabaseName(options.prefix);
  let adminClient = null;
  try {
    adminClient = await checkDbConnection(adminPool, adminConfig, { label: 'admin_database' });
    emitBlueprintLog(
      logger,
      `create_database.start database=${databaseName} host=${adminConfig.host} port=${adminConfig.port} timeout_ms=${adminConfig.connectionTimeoutMillis}`
    );
    await adminClient.query(`CREATE DATABASE ${quoteIdentifier(databaseName)}`);
    emitBlueprintLog(logger, `create_database.done database=${databaseName}`);
    const scopedConfig = buildDbConnectionConfig({ database: databaseName });
    const scopedPool = new Pool(scopedConfig);
    try {
      emitBlueprintLog(
        logger,
        `connect_scoped.ready database=${databaseName} host=${scopedConfig.host} port=${scopedConfig.port} timeout_ms=${scopedConfig.connectionTimeoutMillis}`
      );
      return await callback({
        databaseName,
        pool: scopedPool,
        connectionConfig: scopedConfig,
        logger
      });
    } finally {
      await scopedPool.end();
      emitBlueprintLog(logger, `connect_scoped.closed database=${databaseName}`);
    }
  } finally {
    try {
      if (adminClient) {
        emitBlueprintLog(logger, `drop_database.start database=${databaseName}`);
        await adminClient.query(`
          SELECT pg_terminate_backend(pid)
          FROM pg_stat_activity
          WHERE datname = $1
            AND pid <> pg_backend_pid()
        `, [databaseName]);
        await adminClient.query(`DROP DATABASE IF EXISTS ${quoteIdentifier(databaseName)}`);
        emitBlueprintLog(logger, `drop_database.done database=${databaseName}`);
      }
    } finally {
      if (adminClient) {
        adminClient.release();
      }
      await adminPool.end();
      emitBlueprintLog(logger, `admin_pool.closed database=${databaseName}`);
    }
  }
}

async function runColdStartBlueprintCheck(options = {}) {
  return withTemporaryDatabase({ prefix: options.prefix || 'gatekeeper_cold_start', ...options }, async ({
    pool,
    databaseName,
    connectionConfig,
    logger
  }) => {
    const client = await checkDbConnection(pool, connectionConfig, { label: 'cold_start_scoped_database' });
    try {
      if (Number.isFinite(DEFAULT_STATEMENT_TIMEOUT_MS) && DEFAULT_STATEMENT_TIMEOUT_MS > 0) {
        await client.query(`SET statement_timeout TO ${DEFAULT_STATEMENT_TIMEOUT_MS}`);
        emitBlueprintLog(logger, `statement_timeout.set database=${databaseName} timeout_ms=${DEFAULT_STATEMENT_TIMEOUT_MS}`);
      }

      emitBlueprintLog(logger, `cold_start.begin database=${databaseName}`);
      const appliedFiles = await applyBlueprint(client, options.filePaths, { logger });
      const inspection = await assertCoreSchema(client);
      emitBlueprintLog(
        logger,
        `schema_assert.done database=${databaseName} missing_tables=${inspection.missingTables.length} missing_columns=${inspection.missingColumns.length}`
      );
      if (options.runWriteProbe !== false) {
        await runBlueprintWriteProbe(client, { logger });
      }
      emitBlueprintLog(logger, `cold_start.done database=${databaseName} applied_files=${appliedFiles.length}`);
      return {
        databaseName,
        appliedFiles,
        inspection
      };
    } finally {
      client.release();
      emitBlueprintLog(logger, `client.released database=${databaseName}`);
    }
  });
}

async function ensureBlueprintOnCurrentDatabase(options = {}) {
  const connectionConfig = buildDbConnectionConfig({
    database: options.database || process.env.DB_NAME || 'football_db'
  });
  const pool = new Pool(connectionConfig);
  let client = null;
  try {
    client = await checkDbConnection(pool, connectionConfig, { label: 'current_database_blueprint' });
    const before = await inspectCoreSchema(client);
    const requiresBlueprint = before.missingTables.length > 0 || before.missingColumns.length > 0;
    const appliedFiles = [];
    let applyMode = 'none';

    if (requiresBlueprint) {
      const tableState = await client.query(`
        SELECT
          to_regclass('public.matches') IS NOT NULL AS has_matches,
          to_regclass('public.raw_match_data') IS NOT NULL AS has_raw_match_data
      `);
      const hasBaseSchema = Boolean(tableState.rows[0]?.has_matches || tableState.rows[0]?.has_raw_match_data);
      const filePaths = options.filePaths
        || (hasBaseSchema ? resolveMigrationSqlFiles() : resolveBlueprintSqlFiles());
      applyMode = hasBaseSchema ? 'migrations_only' : 'full_blueprint';
      appliedFiles.push(...await applyBlueprint(client, filePaths));
    }

    const after = await assertCoreSchema(client);
    if (options.runWriteProbe === true) {
      await runBlueprintWriteProbe(client);
    }

    return {
      applied: requiresBlueprint,
      applyMode,
      appliedFiles,
      before,
      after
    };
  } finally {
    if (client) {
      client.release();
    }
    await pool.end();
  }
}

module.exports = {
  CORE_TABLES,
  REQUIRED_COLUMNS,
  REPO_ROOT,
  INIT_DB_PATH,
  MIGRATIONS_DIR,
  buildDbConnectionConfig,
  resolveBlueprintSqlFiles,
  resolveMigrationSqlFiles,
  readExecutableSql,
  checkDbConnection,
  applyBlueprint,
  inspectCoreSchema,
  assertCoreSchema,
  runBlueprintWriteProbe,
  runColdStartBlueprintCheck,
  ensureBlueprintOnCurrentDatabase,
  createBlueprintCheckDatabaseName
};
