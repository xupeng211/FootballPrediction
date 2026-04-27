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
const {
  MAX_ALIGNMENT_TIME_WINDOW_MS,
  MIN_CONFIDENCE_SCORE,
  MIN_ALIGNMENT_SCORE_GAP,
  selectBestAlignmentCandidate
} = require('./helpers/euroLeagueAdapters');

const DEFAULT_BATCH_SIZE = 1000;
const DEFAULT_ERROR_LOG = path.join(REPO_ROOT, 'logs', 'csv_bulk_loader_errors.jsonl');
const BOOKMAKER_ODDS_HISTORY_MIGRATION = path.join(
  MIGRATIONS_DIR,
  'V12.5__create_bookmaker_odds_history.sql'
);
const BOOKMAKER_ALIGNMENT_META_MIGRATION = path.join(
  MIGRATIONS_DIR,
  'V12.8__add_alignment_meta_to_bookmaker_odds_history.sql'
);
const DATA_SOURCE = 'CSV_BULK_LOADER';
const DATA_VERSION = 'TEP001_PHASE1';
const MATCH_REUSE_WINDOW_MS = MAX_ALIGNMENT_TIME_WINDOW_MS;

function printUsage() {
  console.log('用法: node scripts/ops/csv_bulk_loader.js --file <path> [--commit] [--batch-size <n>] [--error-log <path>]');
  console.log('说明: 默认 dry-run，仅执行流式解析、实体转换、批量聚合和日志预览。');
  console.log('说明: 带 --commit 时会把战术维度同步到已匹配的 matches，并写入 bookmaker_odds_history。');
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

function parseLine(rawValue) {
  return parseDecimal(rawValue);
}

function buildOpenOdds(row) {
  const marketType = normalizeText(row.market_type);
  if (marketType === 'Asian Handicap') {
    return compactObject({
      line: parseLine(row.open_line),
      home: parseDecimal(row.open_home),
      away: parseDecimal(row.open_away)
    });
  }

  if (marketType === 'Over/Under') {
    return compactObject({
      line: parseLine(row.open_line),
      over: parseDecimal(row.open_home),
      under: parseDecimal(row.open_away)
    });
  }

  return compactObject({
    home: parseDecimal(row.open_home),
    draw: parseDecimal(row.open_draw),
    away: parseDecimal(row.open_away)
  });
}

function buildCloseOdds(row) {
  const marketType = normalizeText(row.market_type);
  if (marketType === 'Asian Handicap') {
    return compactObject({
      line: parseLine(row.close_line),
      home: parseDecimal(row.close_home),
      away: parseDecimal(row.close_away)
    });
  }

  if (marketType === 'Over/Under') {
    return compactObject({
      line: parseLine(row.close_line),
      over: parseDecimal(row.close_home),
      under: parseDecimal(row.close_away)
    });
  }

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

class ExistingFotMobMatchResolver {
  constructor(options = {}) {
    this.mapper = options.mapper || new EntityMapper();
    this.pool = options.pool || new Pool(buildDbConnectionConfig());
    this.ownsPool = !options.pool;
    this.cache = new Map();
  }

  async resolve(options = {}) {
    const season = Normalizer.normalizeSeason(String(options.season || '').trim());
    const leagueName = this.mapper.normalizeLeagueName(options.leagueName);
    const homeTeam = this.mapper.normalizeTeamName(options.homeTeam);
    const awayTeam = this.mapper.normalizeTeamName(options.awayTeam);
    const matchDate = new Date(options.matchDate);
    if (Number.isNaN(matchDate.getTime())) {
      throw new Error(`无效日期: ${options.matchDate}`);
    }

    const group = await this._loadGroup(leagueName, season);
    const outcome = selectBestAlignmentCandidate(group.matches, {
      homeTeam,
      awayTeam,
      matchDate
    }, {
      maxTimeWindowMs: MATCH_REUSE_WINDOW_MS,
      minConfidenceScore: MIN_CONFIDENCE_SCORE,
      minScoreGap: MIN_ALIGNMENT_SCORE_GAP
    });

    if (outcome.status === 'not_found') {
      throw new Error(
        `未找到对应 FotMob 比赛: league=${leagueName} season=${season} `
        + `home=${homeTeam} away=${awayTeam} match_date=${matchDate.toISOString()}`
      );
    }

    if (outcome.status !== 'matched') {
      const best = outcome.ranked[0];
      throw new Error(
        `对齐失败 status=${outcome.status} league=${leagueName} season=${season} `
        + `home=${homeTeam} away=${awayTeam} match_date=${matchDate.toISOString()} `
        + `best_score=${best ? best.score.matchScore : 'n/a'}`
      );
    }

    return {
      ...outcome.candidate,
      alignment_meta: outcome.alignmentMeta
    };
  }

  async close() {
    if (!this.ownsPool) {
      return;
    }
    await this.pool.end();
  }

  async _loadGroup(leagueName, season) {
    const cacheKey = `${season}::${leagueName}`;
    if (this.cache.has(cacheKey)) {
      return this.cache.get(cacheKey);
    }

    const client = await this.pool.connect();
    try {
      const result = await client.query(
        `
          SELECT
            match_id,
            external_id,
            league_name,
            season,
            home_team,
            away_team,
            match_date,
            status,
            data_source
          FROM matches
          WHERE season = $1
            AND league_name = $2
            AND match_date IS NOT NULL
            AND external_id IS NOT NULL
            AND COALESCE(data_source, '') <> $3
            AND COALESCE(data_version, '') <> 'CSV_BOOTSTRAP'
            AND COALESCE(external_id, '') NOT LIKE 'csv%'
        `,
        [season, leagueName, DATA_SOURCE]
      );

      const group = { matches: result.rows };

      this.cache.set(cacheKey, group);
      return group;
    } finally {
      client.release();
    }
  }
}

async function buildMatchRecord(row, context) {
  const season = Normalizer.normalizeSeason(String(row.season || '').trim());
  const matchDate = parseDateOrThrow(row.match_date);
  const leagueName = context.mapper.normalizeLeagueName(row.league_name);
  const homeTeam = context.mapper.normalizeTeamName(row.home_team);
  const awayTeam = context.mapper.normalizeTeamName(row.away_team);
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

  const resolvedMatch = await context.matchResolver.resolve({
    requestedMatchId: normalizeText(row.match_id),
    requestedExternalId: toNullableText(row.external_id),
    leagueName,
    season,
    homeTeam,
    awayTeam,
    matchDate
  });
  const identity = context.mapper.bindFotMobIdentity(resolvedMatch);

  return {
    match_id: identity.matchId,
    external_id: identity.externalId,
    league_name: toNullableText(resolvedMatch.league_name) || leagueName,
    season: Normalizer.normalizeSeason(String(resolvedMatch.season || season)),
    home_team: toNullableText(resolvedMatch.home_team) || homeTeam,
    away_team: toNullableText(resolvedMatch.away_team) || awayTeam,
    home_score: parseInteger(row.home_score),
    away_score: parseInteger(row.away_score),
    home_corners: parseInteger(row.home_corners),
    away_corners: parseInteger(row.away_corners),
    home_yellow_cards: parseInteger(row.home_yellow_cards),
    away_yellow_cards: parseInteger(row.away_yellow_cards),
    home_red_cards: parseInteger(row.home_red_cards),
    away_red_cards: parseInteger(row.away_red_cards),
    referee: toNullableText(row.referee),
    match_date: resolvedMatch.match_date instanceof Date
      ? resolvedMatch.match_date
      : parseDateOrThrow(resolvedMatch.match_date || matchDate),
    alignment_meta: resolvedMatch.alignment_meta || parseJson(row.alignment_meta, {}),
    status,
    is_finished: status === 'finished',
    data_version: DATA_VERSION,
    data_source: toNullableText(resolvedMatch.data_source) || 'FotMob'
  };
}

function buildOddsRecord(row, context) {
  const bookmakerName = context.mapper.normalizeBookmakerName(row.bookmaker_name);
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
    closeOdds,
    alignmentMeta: parseJson(row.alignment_meta, context.match.alignment_meta || {})
  });

  return {
    match_id: context.match.match_id,
    bookmaker_name: bookmakerName,
    market_type: marketType,
    open_odds: openOdds,
    close_odds: closeOdds,
    movement_trajectory: buildMovementTrajectory(row, openOdds, closeOdds),
    alignment_meta: parseJson(row.alignment_meta, context.match.alignment_meta || {}),
    source_html_path: context.sourceFile,
    source_digest: sha256(rawDigestPayload)
  };
}

async function normalizeCsvRow(row, context) {
  const match = await buildMatchRecord(row, context);
  const odds = buildOddsRecord(row, {
    match,
    mapper: context.mapper,
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
    this.matchResolver = options.matchResolver;
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
        const normalized = await normalizeCsvRow(row, {
          mapper: this.mapper,
          matchResolver: this.matchResolver,
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

      const matchRows = dedupeByKey(
        records.map((record) => record.match),
        (item) => item.match_id
      );
      const oddsRows = dedupeByKey(
        records.map((record) => record.odds),
        (item) => `${item.match_id}::${item.bookmaker_name}::${item.market_type}`
      );

      const matchResult = await syncResolvedMatches(client, matchRows);
      const oddsResult = await upsertBookmakerOddsHistory(client, oddsRows);
      await client.query('COMMIT');

      this.stats.rowsProcessed = (this.stats.rowsProcessed || 0) + records.length;
      this.stats.matchesUpdated = (this.stats.matchesUpdated || 0) + matchResult.updated;
      this.stats.oddsInserted = (this.stats.oddsInserted || 0) + oddsResult.inserted;
      this.stats.oddsUpdated = (this.stats.oddsUpdated || 0) + oddsResult.updated;

      console.log(
        `[CSV-BULK] commit batch=${this.batchIndex} rows=${records.length} `
        + `resolved_matches=${new Set(records.map((record) => record.match.match_id)).size} `
        + `matches(updated=${matchResult.updated}) `
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

    const columnResult = await client.query(`
      SELECT 1
      FROM information_schema.columns
      WHERE table_schema = 'public'
        AND table_name = 'bookmaker_odds_history'
        AND column_name = 'alignment_meta'
      LIMIT 1
    `);
    if (columnResult.rowCount === 0) {
      await client.query(readExecutableSql(BOOKMAKER_ALIGNMENT_META_MIGRATION));
    }

    this.tableEnsured = true;
  }
}

async function syncResolvedMatches(client, rows = []) {
  if (!Array.isArray(rows) || rows.length === 0) {
    return { updated: 0 };
  }

  const values = [];
  const placeholders = rows.map((row, index) => {
    const offset = index * 12;
    values.push(
      row.match_id,
      row.home_score,
      row.away_score,
      row.status,
      row.is_finished,
      row.home_corners,
      row.away_corners,
      row.home_yellow_cards,
      row.away_yellow_cards,
      row.home_red_cards,
      row.away_red_cards,
      row.referee
    );

    return `($${offset + 1}::varchar, $${offset + 2}::int, $${offset + 3}::int, $${offset + 4}::varchar, $${offset + 5}::boolean, $${offset + 6}::int, $${offset + 7}::int, $${offset + 8}::int, $${offset + 9}::int, $${offset + 10}::int, $${offset + 11}::int, $${offset + 12}::varchar)`;
  });

  const result = await client.query(`
    UPDATE matches AS target
    SET
      home_score = COALESCE(source.home_score, target.home_score),
      away_score = COALESCE(source.away_score, target.away_score),
      status = COALESCE(source.status, target.status),
      is_finished = COALESCE(source.is_finished, target.is_finished),
      home_corners = COALESCE(source.home_corners, target.home_corners),
      away_corners = COALESCE(source.away_corners, target.away_corners),
      home_yellow_cards = COALESCE(source.home_yellow_cards, target.home_yellow_cards),
      away_yellow_cards = COALESCE(source.away_yellow_cards, target.away_yellow_cards),
      home_red_cards = COALESCE(source.home_red_cards, target.home_red_cards),
      away_red_cards = COALESCE(source.away_red_cards, target.away_red_cards),
      referee = COALESCE(source.referee, target.referee),
      updated_at = NOW()
    FROM (
      VALUES ${placeholders.join(', ')}
    ) AS source(
      match_id,
      home_score,
      away_score,
      status,
      is_finished,
      home_corners,
      away_corners,
      home_yellow_cards,
      away_yellow_cards,
      home_red_cards,
      away_red_cards,
      referee
    )
    WHERE target.match_id = source.match_id
    RETURNING target.match_id
  `, values);

  if (result.rowCount !== rows.length) {
    throw new Error(
      `matches 同步失败: expected=${rows.length} updated=${result.rowCount}`
    );
  }

  return { updated: result.rowCount };
}

function dedupeByKey(items = [], keySelector) {
  const map = new Map();
  for (const item of items) {
    map.set(keySelector(item), item);
  }
  return [...map.values()];
}

async function upsertBookmakerOddsHistory(client, rows = []) {
  if (!Array.isArray(rows) || rows.length === 0) {
    return { inserted: 0, updated: 0 };
  }

  const values = [];
  const placeholders = rows.map((row, index) => {
    const offset = index * 9;
    values.push(
      row.match_id,
      row.bookmaker_name,
      row.market_type,
      JSON.stringify(row.open_odds || {}),
      JSON.stringify(row.close_odds || {}),
      JSON.stringify(Array.isArray(row.movement_trajectory) ? row.movement_trajectory : []),
      JSON.stringify(row.alignment_meta || {}),
      row.source_html_path || null,
      row.source_digest || null
    );

    return `($${offset + 1}, $${offset + 2}, $${offset + 3}, $${offset + 4}::jsonb, $${offset + 5}::jsonb, $${offset + 6}::jsonb, $${offset + 7}::jsonb, $${offset + 8}, $${offset + 9})`;
  });

  const result = await client.query(`
    INSERT INTO bookmaker_odds_history (
      match_id,
      bookmaker_name,
      market_type,
      open_odds,
      close_odds,
      movement_trajectory,
      alignment_meta,
      source_html_path,
      source_digest
    )
    VALUES ${placeholders.join(', ')}
    ON CONFLICT (match_id, bookmaker_name, market_type) DO UPDATE SET
      open_odds = EXCLUDED.open_odds,
      close_odds = EXCLUDED.close_odds,
      movement_trajectory = EXCLUDED.movement_trajectory,
      alignment_meta = EXCLUDED.alignment_meta,
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
  const mapper = new EntityMapper();
  const matchResolver = new ExistingFotMobMatchResolver({ mapper });
  const errorSink = fs.createWriteStream(options.errorLogPath, { flags: 'a' });
  const rowTransform = new CsvRowTransform({
    mapper,
    matchResolver,
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
    await matchResolver.close();
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
  ExistingFotMobMatchResolver,
  CsvBulkLoaderWriter,
  CsvRowTransform,
  buildMovementTrajectory,
  normalizeCsvRow,
  parseArgs,
  runCsvBulkLoader,
  syncResolvedMatches,
  upsertBookmakerOddsHistory
};
