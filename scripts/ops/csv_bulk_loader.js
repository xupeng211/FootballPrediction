#!/usr/bin/env node
'use strict';

const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const { once } = require('events');
const { Transform, Writable } = require('stream');
const { pipeline } = require('stream/promises');
const csv = require('csv-parser');
const { Pool } = require('pg');

const { Normalizer } = require('../../src/utils/Normalizer');
const { EntityMapper } = require('../../src/infrastructure/etl/EntityMapper');
const {
  REPO_ROOT,
  MIGRATIONS_DIR,
  buildDbConnectionConfig,
  readExecutableSql
} = require('./helpers/dbBlueprint');

const DEFAULT_BATCH_SIZE = 1000;
const DEFAULT_ERROR_LOG = path.join(REPO_ROOT, 'logs', 'csv_bulk_loader_errors.jsonl');
const BOOKMAKER_ODDS_HISTORY_MIGRATION = path.join(
  MIGRATIONS_DIR,
  'V12.5__create_bookmaker_odds_history.sql'
);
const DATA_SOURCE = 'CSV_BULK_LOADER';
const DATA_VERSION = 'TEP001_PHASE1';

function printUsage() {
  console.log('用法: node scripts/ops/csv_bulk_loader.js --file <path> [--commit] [--batch-size <n>] [--error-log <path>]');
  console.log('说明: 默认 dry-run，仅执行流式解析、实体转换、批量聚合和日志预览。');
  console.log('说明: 带 --commit 时才会把数据批量写入 matches 和 bookmaker_odds_history。');
}

function resolveCliPath(rawValue) {
  if (!rawValue) {
    return null;
  }

  return path.isAbsolute(rawValue)
    ? path.resolve(rawValue)
    : path.resolve(REPO_ROOT, rawValue);
}

function requireOptionValue(args, index, flagName) {
  const value = args[index + 1];
  if (!value || String(value).startsWith('--')) {
    throw new Error(`参数 ${flagName} 缺少值`);
  }

  return {
    value,
    nextIndex: index + 1
  };
}

function applyBatchSizeOption(options, rawValue) {
  const value = Number.parseInt(rawValue, 10);
  if (!Number.isFinite(value) || value <= 0) {
    throw new Error('参数 --batch-size 必须是正整数');
  }
  options.batchSize = value;
}

const ARGUMENT_HANDLERS = {
  '--commit': {
    apply(options) {
      options.commit = true;
    }
  },
  '--file': {
    takesValue: true,
    apply(options, value) {
      options.inputPath = resolveCliPath(value);
    }
  },
  '--batch-size': {
    takesValue: true,
    apply: applyBatchSizeOption
  },
  '--error-log': {
    takesValue: true,
    apply(options, value) {
      options.errorLogPath = resolveCliPath(value);
    }
  }
};

function parseArgs(argv = process.argv.slice(2)) {
  const args = [...argv];
  const options = {
    inputPath: null,
    commit: false,
    batchSize: DEFAULT_BATCH_SIZE,
    errorLogPath: DEFAULT_ERROR_LOG
  };

  for (let index = 0; index < args.length; index++) {
    const token = String(args[index] || '').trim();
    if (!token) {
      continue;
    }

    if (token === '--help' || token === '-h') {
      options.help = true;
      continue;
    }

    const handler = ARGUMENT_HANDLERS[token];
    if (!handler) {
      throw new Error(`未知参数: ${token}`);
    }

    const resolution = handler.takesValue
      ? requireOptionValue(args, index, token)
      : { value: null, nextIndex: index };
    handler.apply(options, resolution.value);
    index = resolution.nextIndex;
  }

  if (!options.help && !options.inputPath) {
    throw new Error('必须提供 --file <path>');
  }

  return options;
}

function normalizeText(value) {
  return String(value || '').replace(/\s+/g, ' ').trim();
}

function toNullableText(value) {
  const normalized = normalizeText(value);
  return normalized || null;
}

function parseDecimal(rawValue) {
  const normalized = normalizeText(rawValue).replace(/,/g, '.');
  if (!normalized) {
    return null;
  }

  const parsed = Number.parseFloat(normalized);
  return Number.isFinite(parsed) ? parsed : null;
}

function parseInteger(rawValue) {
  const normalized = normalizeText(rawValue);
  if (!normalized) {
    return null;
  }

  const parsed = Number.parseInt(normalized, 10);
  return Number.isFinite(parsed) ? parsed : null;
}

function parseDateOrThrow(rawValue) {
  const normalized = normalizeText(rawValue);
  if (!normalized) {
    throw new Error('match_date 不能为空');
  }

  const parsed = new Date(normalized);
  if (Number.isNaN(parsed.getTime())) {
    throw new Error(`无效日期: ${rawValue}`);
  }

  return parsed;
}

function parseJson(rawValue, fallbackValue) {
  const normalized = normalizeText(rawValue);
  if (!normalized) {
    return fallbackValue;
  }

  try {
    return JSON.parse(normalized);
  } catch {
    return fallbackValue;
  }
}

function compactObject(value) {
  return Object.fromEntries(
    Object.entries(value || {}).filter(([, entryValue]) => entryValue !== null && entryValue !== undefined)
  );
}

function buildOpenOdds(row) {
  return compactObject({
    home: parseDecimal(row.open_home),
    draw: parseDecimal(row.open_draw),
    away: parseDecimal(row.open_away)
  });
}

function buildCloseOdds(row) {
  return compactObject({
    home: parseDecimal(row.close_home),
    draw: parseDecimal(row.close_draw),
    away: parseDecimal(row.close_away)
  });
}

function buildMovementTrajectory(row, openOdds, closeOdds) {
  const explicitTrajectory = parseJson(row.movement_trajectory, null);
  if (Array.isArray(explicitTrajectory)) {
    return explicitTrajectory;
  }

  const trajectory = [];
  if (Object.keys(openOdds).length > 0) {
    trajectory.push({ stage: 'open', odds: openOdds });
  }
  if (Object.keys(closeOdds).length > 0) {
    trajectory.push({ stage: 'close', odds: closeOdds });
  }
  return trajectory;
}

function sha256(content) {
  return crypto.createHash('sha256').update(content).digest('hex');
}

async function writeJsonLine(stream, payload) {
  const chunk = `${JSON.stringify(payload)}\n`;
  if (stream.write(chunk)) {
    return;
  }
  await once(stream, 'drain');
}

function buildImportRunId() {
  return `csv_bulk_${Date.now()}_${crypto.randomUUID().replace(/-/g, '').slice(0, 8)}`;
}

function buildMatchRecord(row, mapper) {
  const matchId = normalizeText(row.match_id);
  if (!matchId) {
    throw new Error('match_id 缺失');
  }

  const season = Normalizer.normalizeSeason(String(row.season || '').trim());
  const matchDate = parseDateOrThrow(row.match_date);
  const leagueName = mapper.normalizeLeagueName(row.league_name);
  const homeTeam = mapper.normalizeTeamName(row.home_team);
  const awayTeam = mapper.normalizeTeamName(row.away_team);
  const status = Normalizer.normalizeStatus(row.status || 'scheduled');

  if (!leagueName) {
    throw new Error('league_name 缺失');
  }
  if (!homeTeam) {
    throw new Error('home_team 缺失');
  }
  if (!awayTeam) {
    throw new Error('away_team 缺失');
  }

  return {
    match_id: matchId,
    external_id: toNullableText(row.external_id),
    league_name: leagueName,
    season,
    home_team: homeTeam,
    away_team: awayTeam,
    home_score: parseInteger(row.home_score),
    away_score: parseInteger(row.away_score),
    match_date: matchDate,
    status,
    is_finished: status === 'finished',
    data_version: DATA_VERSION,
    data_source: DATA_SOURCE
  };
}

function buildOddsRecord(row, context) {
  const bookmakerName = normalizeText(row.bookmaker_name);
  const marketType = normalizeText(row.market_type);
  if (!bookmakerName) {
    throw new Error('bookmaker_name 缺失');
  }
  if (!marketType) {
    throw new Error('market_type 缺失');
  }

  const openOdds = buildOpenOdds(row);
  const closeOdds = buildCloseOdds(row);
  const rawDigestPayload = JSON.stringify({
    file: context.sourceFile,
    rowNumber: context.sourceRowNumber,
    match_id: context.match.match_id,
    bookmaker_name: bookmakerName,
    market_type: marketType,
    openOdds,
    closeOdds
  });

  return {
    match_id: context.match.match_id,
    bookmaker_name: bookmakerName,
    market_type: marketType,
    open_odds: openOdds,
    close_odds: closeOdds,
    movement_trajectory: buildMovementTrajectory(row, openOdds, closeOdds),
    source_html_path: context.sourceFile,
    source_digest: sha256(rawDigestPayload)
  };
}

function normalizeCsvRow(row, context) {
  const match = buildMatchRecord(row, context.mapper);
  const odds = buildOddsRecord(row, {
    match,
    sourceFile: context.sourceFile,
    sourceRowNumber: context.sourceRowNumber
  });

  return {
    import_run_id: context.importRunId,
    source_file: context.sourceFile,
    source_row_number: context.sourceRowNumber,
    match,
    odds
  };
}

class CsvRowTransform extends Transform {
  constructor(options = {}) {
    super({ objectMode: true });
    this.mapper = options.mapper || new EntityMapper();
    this.errorSink = options.errorSink;
    this.importRunId = options.importRunId || buildImportRunId();
    this.sourceFile = options.sourceFile || 'unknown.csv';
    this.stats = options.stats || {};
    this.rawRowIndex = 0;
  }

  _transform(row, _encoding, callback) {
    (async () => {
      this.rawRowIndex += 1;
      this.stats.rowsRead = (this.stats.rowsRead || 0) + 1;

      try {
        const normalized = normalizeCsvRow(row, {
          mapper: this.mapper,
          importRunId: this.importRunId,
          sourceFile: this.sourceFile,
          sourceRowNumber: this.rawRowIndex + 1
        });
        this.stats.rowsValidated = (this.stats.rowsValidated || 0) + 1;
        this.push(normalized);
      } catch (error) {
        this.stats.rowsSkipped = (this.stats.rowsSkipped || 0) + 1;
        await writeJsonLine(this.errorSink, {
          timestamp: new Date().toISOString(),
          import_run_id: this.importRunId,
          source_file: this.sourceFile,
          source_row_number: this.rawRowIndex + 1,
          error_code: 'ROW_ISOLATED',
          error_message: error.message,
          raw_row: row
        });
      }
    })().then(() => callback(), callback);
  }
}

class BatchAggregator extends Writable {
  constructor(options = {}) {
    super({ objectMode: true });
    this.batchSize = options.batchSize || DEFAULT_BATCH_SIZE;
    this.flushBatch = options.flushBatch;
    this.buffer = [];
  }

  _write(record, _encoding, callback) {
    (async () => {
      this.buffer.push(record);
      if (this.buffer.length < this.batchSize) {
        return;
      }
      await this._flush();
    })().then(() => callback(), callback);
  }

  _final(callback) {
    this._flush().then(() => callback(), callback);
  }

  async _flush() {
    if (this.buffer.length === 0) {
      return;
    }

    const pending = this.buffer;
    this.buffer = [];
    await this.flushBatch(pending);
  }
}

class CsvBulkLoaderWriter {
  constructor(options = {}) {
    this.commit = options.commit === true;
    this.stats = options.stats || {};
    this.pool = this.commit ? new Pool(buildDbConnectionConfig()) : null;
    this.batchIndex = 0;
    this.tableEnsured = false;
  }

  async flushBatch(records = []) {
    if (!Array.isArray(records) || records.length === 0) {
      return;
    }

    this.batchIndex += 1;
    if (!this.commit) {
      records.forEach((record) => {
        console.log(
          `[CSV-BULK] dry-run row=${record.source_row_number} `
          + `match_id=${record.match.match_id} `
          + `league=${record.match.league_name} `
          + `bookmaker=${record.odds.bookmaker_name} `
          + `market=${record.odds.market_type}`
        );
      });
      this.stats.rowsProcessed = (this.stats.rowsProcessed || 0) + records.length;
      return;
    }

    const client = await this.pool.connect();
    try {
      await client.query('BEGIN');
      await this._ensureOddsHistoryTable(client);

      const matches = dedupeByKey(records.map((record) => record.match), (item) => item.match_id);
      const oddsRows = dedupeByKey(
        records.map((record) => record.odds),
        (item) => `${item.match_id}::${item.bookmaker_name}::${item.market_type}`
      );

      const matchResult = await upsertMatches(client, matches);
      const oddsResult = await upsertBookmakerOddsHistory(client, oddsRows);
      await client.query('COMMIT');

      this.stats.rowsProcessed = (this.stats.rowsProcessed || 0) + records.length;
      this.stats.matchInserted = (this.stats.matchInserted || 0) + matchResult.inserted;
      this.stats.matchUpdated = (this.stats.matchUpdated || 0) + matchResult.updated;
      this.stats.oddsInserted = (this.stats.oddsInserted || 0) + oddsResult.inserted;
      this.stats.oddsUpdated = (this.stats.oddsUpdated || 0) + oddsResult.updated;

      console.log(
        `[CSV-BULK] commit batch=${this.batchIndex} rows=${records.length} `
        + `matches(inserted=${matchResult.inserted},updated=${matchResult.updated}) `
        + `odds(inserted=${oddsResult.inserted},updated=${oddsResult.updated})`
      );
    } catch (error) {
      await client.query('ROLLBACK').catch(() => {});
      throw error;
    } finally {
      client.release();
    }
  }

  async close() {
    if (!this.pool) {
      return;
    }
    await this.pool.end();
  }

  async _ensureOddsHistoryTable(client) {
    if (this.tableEnsured) {
      return;
    }

    const result = await client.query(`
      SELECT to_regclass('public.bookmaker_odds_history') AS table_name
    `);
    if (!result.rows[0]?.table_name) {
      await client.query(readExecutableSql(BOOKMAKER_ODDS_HISTORY_MIGRATION));
    }

    this.tableEnsured = true;
  }
}

function dedupeByKey(items = [], keySelector) {
  const map = new Map();
  for (const item of items) {
    map.set(keySelector(item), item);
  }
  return [...map.values()];
}

async function upsertMatches(client, rows = []) {
  if (!Array.isArray(rows) || rows.length === 0) {
    return { inserted: 0, updated: 0 };
  }

  const values = [];
  const placeholders = rows.map((row, index) => {
    const offset = index * 14;
    values.push(
      row.match_id,
      row.external_id,
      row.league_name,
      row.season,
      row.home_team,
      row.away_team,
      row.home_score,
      row.away_score,
      row.match_date,
      row.status,
      row.is_finished,
      row.data_version,
      row.data_source,
      row.match_date
    );

    return `($${offset + 1}, $${offset + 2}, $${offset + 3}, $${offset + 4}, $${offset + 5}, $${offset + 6}, $${offset + 7}, $${offset + 8}, $${offset + 9}, $${offset + 10}, $${offset + 11}, $${offset + 12}, $${offset + 13}, $${offset + 14})`;
  });

  const result = await client.query(`
    INSERT INTO matches (
      match_id,
      external_id,
      league_name,
      season,
      home_team,
      away_team,
      home_score,
      away_score,
      match_date,
      status,
      is_finished,
      data_version,
      data_source,
      collection_date
    )
    VALUES ${placeholders.join(', ')}
    ON CONFLICT (match_id) DO UPDATE SET
      external_id = COALESCE(EXCLUDED.external_id, matches.external_id),
      league_name = EXCLUDED.league_name,
      season = EXCLUDED.season,
      home_team = EXCLUDED.home_team,
      away_team = EXCLUDED.away_team,
      home_score = COALESCE(EXCLUDED.home_score, matches.home_score),
      away_score = COALESCE(EXCLUDED.away_score, matches.away_score),
      match_date = COALESCE(EXCLUDED.match_date, matches.match_date),
      status = EXCLUDED.status,
      is_finished = EXCLUDED.is_finished,
      data_version = EXCLUDED.data_version,
      data_source = EXCLUDED.data_source,
      updated_at = NOW()
    RETURNING (xmax = 0) AS inserted
  `, values);

  const inserted = result.rows.filter((row) => row.inserted).length;
  return { inserted, updated: result.rows.length - inserted };
}

async function upsertBookmakerOddsHistory(client, rows = []) {
  if (!Array.isArray(rows) || rows.length === 0) {
    return { inserted: 0, updated: 0 };
  }

  const values = [];
  const placeholders = rows.map((row, index) => {
    const offset = index * 8;
    values.push(
      row.match_id,
      row.bookmaker_name,
      row.market_type,
      JSON.stringify(row.open_odds || {}),
      JSON.stringify(row.close_odds || {}),
      JSON.stringify(Array.isArray(row.movement_trajectory) ? row.movement_trajectory : []),
      row.source_html_path || null,
      row.source_digest || null
    );

    return `($${offset + 1}, $${offset + 2}, $${offset + 3}, $${offset + 4}::jsonb, $${offset + 5}::jsonb, $${offset + 6}::jsonb, $${offset + 7}, $${offset + 8})`;
  });

  const result = await client.query(`
    INSERT INTO bookmaker_odds_history (
      match_id,
      bookmaker_name,
      market_type,
      open_odds,
      close_odds,
      movement_trajectory,
      source_html_path,
      source_digest
    )
    VALUES ${placeholders.join(', ')}
    ON CONFLICT (match_id, bookmaker_name, market_type) DO UPDATE SET
      open_odds = EXCLUDED.open_odds,
      close_odds = EXCLUDED.close_odds,
      movement_trajectory = EXCLUDED.movement_trajectory,
      source_html_path = EXCLUDED.source_html_path,
      source_digest = EXCLUDED.source_digest,
      collected_at = NOW(),
      updated_at = NOW()
    RETURNING (xmax = 0) AS inserted
  `, values);

  const inserted = result.rows.filter((row) => row.inserted).length;
  return { inserted, updated: result.rows.length - inserted };
}

async function runCsvBulkLoader(options = {}) {
  const inputPath = resolveCliPath(options.inputPath);
  if (!inputPath || !fs.existsSync(inputPath)) {
    throw new Error(`CSV 文件不存在: ${inputPath || 'N/A'}`);
  }

  fs.mkdirSync(path.dirname(options.errorLogPath), { recursive: true });

  const stats = {
    rowsRead: 0,
    rowsValidated: 0,
    rowsSkipped: 0,
    rowsProcessed: 0
  };
  const importRunId = buildImportRunId();
  const errorSink = fs.createWriteStream(options.errorLogPath, { flags: 'a' });
  const rowTransform = new CsvRowTransform({
    mapper: new EntityMapper(),
    errorSink,
    importRunId,
    sourceFile: path.relative(REPO_ROOT, inputPath),
    stats
  });
  const writer = new CsvBulkLoaderWriter({
    commit: options.commit,
    stats
  });
  const aggregator = new BatchAggregator({
    batchSize: options.batchSize,
    flushBatch: writer.flushBatch.bind(writer)
  });

  try {
    await pipeline(
      fs.createReadStream(inputPath, { encoding: 'utf8' }),
      csv({
        strict: false,
        skipLines: 0,
        mapHeaders: ({ header }) => normalizeText(header)
      }),
      rowTransform,
      aggregator
    );
  } finally {
    errorSink.end();
    await once(errorSink, 'finish').catch(() => {});
    await writer.close();
  }

  console.log(
    `[CSV-BULK] 完成 import_run_id=${importRunId} `
    + `rowsRead=${stats.rowsRead} `
    + `rowsValidated=${stats.rowsValidated} `
    + `rowsProcessed=${stats.rowsProcessed} `
    + `rowsSkipped=${stats.rowsSkipped} `
    + `mode=${options.commit ? 'commit' : 'dry-run'}`
  );

  return {
    importRunId,
    stats,
    errorLogPath: options.errorLogPath
  };
}

async function main() {
  const options = parseArgs();
  if (options.help) {
    printUsage();
    return;
  }

  await runCsvBulkLoader(options);
}

if (require.main === module) {
  main().catch((error) => {
    console.error(`[CSV-BULK] 失败: ${error.message}`);
    process.exit(1);
  });
}

module.exports = {
  BatchAggregator,
  CsvBulkLoaderWriter,
  CsvRowTransform,
  buildMovementTrajectory,
  normalizeCsvRow,
  parseArgs,
  runCsvBulkLoader,
  upsertBookmakerOddsHistory,
  upsertMatches
};
