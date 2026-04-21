#!/usr/bin/env node
'use strict';

const crypto = require('crypto');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { once } = require('events');
const { Readable, Writable } = require('stream');
const { pipeline } = require('stream/promises');
const csv = require('csv-parser');
const { Pool } = require('pg');

const { Normalizer } = require('../../src/utils/Normalizer');
const {
  EntityMapper,
  WARNING_LOW_QUALITY_SOURCE
} = require('../../src/infrastructure/etl/EntityMapper');
const {
  REPO_ROOT,
  buildDbConnectionConfig
} = require('./helpers/dbBlueprint');

const LEAGUE_ID = 47;
const MATCH_REUSE_WINDOW_MS = 2 * 60 * 60 * 1000;
const SOURCE_CANDIDATES = [
  {
    seasonCode: '2425',
    season: '2024-2025',
    url: 'https://www.football-data.co.uk/mmz4281/2425/E0.csv'
  },
  {
    seasonCode: '2324',
    season: '2023-2024',
    url: 'https://www.football-data.co.uk/mmz4281/2324/E0.csv'
  },
  {
    seasonCode: '2223',
    season: '2022-2023',
    url: 'https://www.football-data.co.uk/mmz4281/2223/E0.csv'
  },
  {
    seasonCode: '2122',
    season: '2021-2022',
    url: 'https://www.football-data.co.uk/mmz4281/2122/E0.csv'
  },
  {
    seasonCode: '2021',
    season: '2020-2021',
    url: 'https://www.football-data.co.uk/mmz4281/2021/E0.csv'
  }
];
const OUTPUT_PATH = path.join(REPO_ROOT, 'data', 'mock', 'real_epl_adapted.csv');
const OUTPUT_HEADERS = [
  'match_id',
  'external_id',
  'league_name',
  'season',
  'home_team',
  'away_team',
  'match_date',
  'status',
  'bookmaker_name',
  'market_type',
  'open_home',
  'open_draw',
  'open_away',
  'close_home',
  'close_draw',
  'close_away',
  'home_score',
  'away_score',
  'quality_flags'
];

function normalizeText(value) {
  return String(value || '').replace(/\s+/g, ' ').trim();
}

function toCsvCell(value) {
  const normalized = value === null || value === undefined ? '' : String(value);
  if (!/[",\n]/.test(normalized)) {
    return normalized;
  }

  return `"${normalized.replace(/"/g, '""')}"`;
}

function formatCsvLine(row) {
  return `${OUTPUT_HEADERS.map((header) => toCsvCell(row[header] ?? '')).join(',')}\n`;
}

function parseArgs(argv = process.argv.slice(2)) {
  const options = {
    seasonCode: null
  };

  for (let index = 0; index < argv.length; index++) {
    const token = String(argv[index] || '').trim();
    if (!token) {
      continue;
    }

    if (token === '--season-code') {
      const value = argv[index + 1];
      if (!value || String(value).startsWith('--')) {
        throw new Error('参数 --season-code 缺少值');
      }
      options.seasonCode = normalizeText(value);
      index += 1;
      continue;
    }

    if (token === '--help' || token === '-h') {
      options.help = true;
      continue;
    }

    throw new Error(`未知参数: ${token}`);
  }

  return options;
}

function printUsage() {
  console.log('用法: node scripts/ops/fetch_and_adapt_epl.js [--season-code 2425]');
  console.log('说明: 默认优先抓取最新可用赛季；传入 --season-code 时只处理指定赛季。');
}

function parseFootballDataDateTime(dateValue, timeValue) {
  const dateText = normalizeText(dateValue);
  if (!dateText) {
    throw new Error('Date 缺失');
  }

  const match = dateText.match(/^(\d{1,2})\/(\d{1,2})\/(\d{2,4})$/);
  if (!match) {
    throw new Error(`无法识别的 Date: ${dateValue}`);
  }

  const day = Number.parseInt(match[1], 10);
  const month = Number.parseInt(match[2], 10);
  let year = Number.parseInt(match[3], 10);
  if (year < 100) {
    year += 2000;
  }

  const timeText = normalizeText(timeValue) || '15:00';
  const timeMatch = timeText.match(/^(\d{1,2}):(\d{2})$/);
  const hour = timeMatch ? Number.parseInt(timeMatch[1], 10) : 15;
  const minute = timeMatch ? Number.parseInt(timeMatch[2], 10) : 0;

  return new Date(Date.UTC(year, month - 1, day, hour, minute, 0)).toISOString();
}

function buildSeasonTag(season) {
  const normalizedSeason = Normalizer.normalizeSeason(season);
  return normalizedSeason.replace(/\//g, '');
}

function buildFallbackMatchId(season, matchDate, homeTeam, awayTeam) {
  const seasonTag = buildSeasonTag(season);
  const hash = crypto.createHash('sha1')
    .update(`${matchDate}|${homeTeam}|${awayTeam}`)
    .digest('hex')
    .slice(0, 12);
  return `${LEAGUE_ID}_${seasonTag}_${hash}`;
}

function buildKey(homeTeam, awayTeam) {
  return `${normalizeText(homeTeam)}::${normalizeText(awayTeam)}`;
}

function compareCandidatePriority(left, right) {
  const leftPriority = left.data_source === 'CSV_BULK_LOADER' ? 1 : 0;
  const rightPriority = right.data_source === 'CSV_BULK_LOADER' ? 1 : 0;
  if (leftPriority !== rightPriority) {
    return leftPriority - rightPriority;
  }

  return String(left.match_id).localeCompare(String(right.match_id));
}

function extractOddsTriplet(row, columns) {
  return {
    home: normalizeText(row[columns.home]),
    draw: normalizeText(row[columns.draw]),
    away: normalizeText(row[columns.away])
  };
}

function hasAnyOddsValue(oddsTriplet) {
  return Object.values(oddsTriplet).some((value) => value !== '');
}

function hasCompleteOddsTriplet(oddsTriplet) {
  return Object.values(oddsTriplet).every((value) => value !== '');
}

class ExistingMatchResolver {
  constructor(options = {}) {
    this.mapper = options.mapper || new EntityMapper();
    this.leagueName = options.leagueName || 'Premier League';
    this.season = Normalizer.normalizeSeason(options.season || '');
    this.pool = options.pool || new Pool(buildDbConnectionConfig());
    this.ownsPool = !options.pool;
    this.matchesByKey = new Map();
    this.candidateCount = 0;
    this.loaded = false;
  }

  async load() {
    if (this.loaded) {
      return this;
    }

    const client = await this.pool.connect();
    try {
      const leagueName = this.mapper.normalizeLeagueName(this.leagueName);
      const result = await client.query(`
        SELECT
          match_id,
          home_team,
          away_team,
          match_date,
          data_source,
          data_version
        FROM matches
        WHERE season = $1
          AND league_name = $2
          AND COALESCE(data_source, '') <> 'CSV_BULK_LOADER'
          AND match_date IS NOT NULL
      `, [this.season, leagueName]);

      for (const row of result.rows) {
        const key = buildKey(
          this.mapper.normalizeTeamName(row.home_team),
          this.mapper.normalizeTeamName(row.away_team)
        );
        const bucket = this.matchesByKey.get(key) || [];
        bucket.push(row);
        this.matchesByKey.set(key, bucket);
      }

      this.candidateCount = result.rows.length;
      this.loaded = true;
      return this;
    } finally {
      client.release();
    }
  }

  findMatch(options = {}) {
    const matchDate = new Date(options.matchDate);
    if (Number.isNaN(matchDate.getTime())) {
      return null;
    }

    const key = buildKey(options.homeTeam, options.awayTeam);
    const candidates = (this.matchesByKey.get(key) || [])
      .map((candidate) => {
        const candidateDate = new Date(candidate.match_date);
        return {
          ...candidate,
          diffMs: Math.abs(matchDate.getTime() - candidateDate.getTime())
        };
      })
      .filter((candidate) => candidate.diffMs <= MATCH_REUSE_WINDOW_MS)
      .sort((left, right) => left.diffMs - right.diffMs || compareCandidatePriority(left, right));

    return candidates[0] || null;
  }

  async close() {
    if (!this.ownsPool) {
      return;
    }
    await this.pool.end();
  }
}

function buildMatchId(options = {}) {
  const existingMatch = options.resolver?.findMatch({
    homeTeam: options.homeTeam,
    awayTeam: options.awayTeam,
    matchDate: options.matchDate
  });

  if (existingMatch) {
    return {
      matchId: existingMatch.match_id,
      reusedExisting: true,
      matchedSource: existingMatch.data_source || '',
      matchedDate: existingMatch.match_date
    };
  }

  return {
    matchId: buildFallbackMatchId(
      options.season,
      options.matchDate,
      options.homeTeam,
      options.awayTeam
    ),
    reusedExisting: false,
    matchedSource: '',
    matchedDate: null
  };
}

function adaptSourceRow(row, context) {
  const rawHomeTeam = normalizeText(row.HomeTeam);
  const rawAwayTeam = normalizeText(row.AwayTeam);
  if (!rawHomeTeam || !rawAwayTeam) {
    throw new Error('HomeTeam / AwayTeam 缺失');
  }

  const homeTeam = context.mapper.normalizeTeamName(rawHomeTeam);
  const awayTeam = context.mapper.normalizeTeamName(rawAwayTeam);
  const matchDate = parseFootballDataDateTime(row.Date, row.Time);
  const matchIdResolution = buildMatchId({
    season: context.sourceMeta.season,
    matchDate,
    homeTeam,
    awayTeam,
    resolver: context.resolver
  });
  const openOdds = extractOddsTriplet(row, {
    home: 'B365H',
    draw: 'B365D',
    away: 'B365A'
  });
  const closeOddsRaw = extractOddsTriplet(row, {
    home: 'B365CH',
    draw: 'B365CD',
    away: 'B365CA'
  });
  const hasOpenOdds = hasCompleteOddsTriplet(openOdds);
  const hasCloseOdds = hasCompleteOddsTriplet(closeOddsRaw);
  const qualityFlags = context.mapper.buildSourceQualityFlags({ hasOpenOdds });
  const closeOdds = hasCloseOdds ? closeOddsRaw : openOdds;
  if (!hasAnyOddsValue(closeOdds)) {
    throw new Error('Bet365 赔率列缺失');
  }

  return {
    row: {
      match_id: matchIdResolution.matchId,
      external_id: `${context.sourceMeta.seasonCode}_${hashExternalId(matchDate, homeTeam, awayTeam)}`,
      league_name: context.mapper.normalizeLeagueName('Premier League'),
      season: Normalizer.normalizeSeason(context.sourceMeta.season),
      home_team: homeTeam,
      away_team: awayTeam,
      match_date: matchDate,
      status: hasFinalScore(row) ? 'finished' : 'scheduled',
      bookmaker_name: 'Bet365',
      market_type: '1x2',
      open_home: openOdds.home,
      open_draw: openOdds.draw,
      open_away: openOdds.away,
      close_home: closeOdds.home,
      close_draw: closeOdds.draw,
      close_away: closeOdds.away,
      home_score: normalizeText(row.FTHG),
      away_score: normalizeText(row.FTAG),
      quality_flags: qualityFlags.join(';')
    },
    diagnostics: {
      qualityFlags,
      reusedExisting: matchIdResolution.reusedExisting,
      matchedSource: matchIdResolution.matchedSource,
      matchedDate: matchIdResolution.matchedDate
    }
  };
}

function hasFinalScore(row) {
  return normalizeText(row.FTHG) !== '' && normalizeText(row.FTAG) !== '';
}

function hashExternalId(matchDate, homeTeam, awayTeam) {
  return crypto.createHash('md5')
    .update(`${matchDate}|${homeTeam}|${awayTeam}`)
    .digest('hex')
    .slice(0, 10);
}

async function downloadToTempFile(sourceMeta) {
  const response = await fetch(sourceMeta.url, {
    headers: {
      'user-agent': 'FootballPrediction/TEP-001 CSV Adapter'
    }
  });

  if (!response.ok || !response.body) {
    throw new Error(`HTTP ${response.status} ${response.statusText}`.trim());
  }

  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'football-data-epl-'));
  const tempFile = path.join(tempDir, `${sourceMeta.seasonCode}-E0.csv`);
  await pipeline(
    Readable.fromWeb(response.body),
    fs.createWriteStream(tempFile)
  );

  return {
    ...sourceMeta,
    tempDir,
    tempFile
  };
}

function resolveCandidateList(options = {}) {
  if (!options.seasonCode) {
    return SOURCE_CANDIDATES;
  }

  const matched = SOURCE_CANDIDATES.find((candidate) => candidate.seasonCode === options.seasonCode);
  if (!matched) {
    throw new Error(`未配置的 seasonCode: ${options.seasonCode}`);
  }

  return [matched];
}

async function resolveDownloadSource(options = {}) {
  const errors = [];
  for (const candidate of resolveCandidateList(options)) {
    try {
      const resolved = await downloadToTempFile(candidate);
      return resolved;
    } catch (error) {
      errors.push(`${candidate.seasonCode}: ${error.message}`);
    }
  }

  throw new Error(`所有 EPL 下载源都失败了: ${errors.join(' | ')}`);
}

class CollectingWriter extends Writable {
  constructor(sourceMeta, options = {}) {
    super({ objectMode: true });
    this.sourceMeta = sourceMeta;
    this.mapper = options.mapper || new EntityMapper();
    this.resolver = options.resolver || null;
    this.rows = [];
    this.skipped = 0;
    this.errors = [];
    this.stats = {
      reusedExisting: 0,
      generatedNew: 0,
      lowQualityRows: 0
    };
    this.sourceQualityFlags = new Set();
  }

  _write(row, _encoding, callback) {
    try {
      const adapted = adaptSourceRow(row, {
        sourceMeta: this.sourceMeta,
        mapper: this.mapper,
        resolver: this.resolver
      });
      this.rows.push(adapted.row);
      if (adapted.diagnostics.reusedExisting) {
        this.stats.reusedExisting += 1;
      } else {
        this.stats.generatedNew += 1;
      }
      if (adapted.diagnostics.qualityFlags.length > 0) {
        this.stats.lowQualityRows += 1;
      }
      adapted.diagnostics.qualityFlags.forEach((flag) => this.sourceQualityFlags.add(flag));
      callback();
    } catch (error) {
      this.skipped += 1;
      this.errors.push(error.message);
      callback();
    }
  }
}

async function parseAndAdaptCsv(sourceMeta, options = {}) {
  const collector = new CollectingWriter(sourceMeta, options);
  await pipeline(
    fs.createReadStream(sourceMeta.tempFile, { encoding: 'utf8' }),
    csv(),
    collector
  );

  return {
    rows: collector.rows,
    skipped: collector.skipped,
    errors: collector.errors,
    stats: collector.stats,
    sourceQualityFlags: [...collector.sourceQualityFlags]
  };
}

async function writeAdaptedCsv(outputPath, rows) {
  fs.mkdirSync(path.dirname(outputPath), { recursive: true });
  const output = fs.createWriteStream(outputPath, { encoding: 'utf8' });
  output.write(`${OUTPUT_HEADERS.join(',')}\n`);
  for (const row of rows) {
    output.write(formatCsvLine(row));
  }
  output.end();
  await once(output, 'finish');
}

function cleanupTempDir(tempDir) {
  if (!tempDir) {
    return;
  }

  fs.rmSync(tempDir, { recursive: true, force: true });
}

async function main() {
  const options = parseArgs();
  if (options.help) {
    printUsage();
    return;
  }

  const mapper = new EntityMapper();
  const sourceMeta = await resolveDownloadSource(options);
  const resolver = new ExistingMatchResolver({
    mapper,
    leagueName: 'Premier League',
    season: sourceMeta.season
  });

  console.log(`[FETCH-EPL] 下载成功 season=${sourceMeta.season} url=${sourceMeta.url}`);

  try {
    await resolver.load();
    console.log(
      `[FETCH-EPL] 现有候选加载 season=${Normalizer.normalizeSeason(sourceMeta.season)} `
      + `league=Premier League candidates=${resolver.candidateCount}`
    );

    const adapted = await parseAndAdaptCsv(sourceMeta, {
      mapper,
      resolver
    });
    await writeAdaptedCsv(OUTPUT_PATH, adapted.rows);

    console.log(
      `[FETCH-EPL] 适配完成 output=${path.relative(REPO_ROOT, OUTPUT_PATH)} `
      + `rows=${adapted.rows.length} skipped=${adapted.skipped} `
      + `reused_existing=${adapted.stats.reusedExisting} generated_new=${adapted.stats.generatedNew}`
    );

    if (adapted.sourceQualityFlags.includes(WARNING_LOW_QUALITY_SOURCE)) {
      console.log(
        `[FETCH-EPL] 数据源质量告警 flags=${adapted.sourceQualityFlags.join(',')} `
        + '原因=缺少 Bet365 初盘列，不满足 ML 训练要求'
      );
    } else {
      console.log('[FETCH-EPL] 数据源质量诊断: 已检测到 Bet365 开盘与收盘列');
    }

    if (adapted.rows[0]) {
      console.log('[FETCH-EPL] 首行样本:');
      console.log(JSON.stringify(adapted.rows[0], null, 2));
    }
    if (adapted.errors.length > 0) {
      console.log(`[FETCH-EPL] 跳过样本原因: ${adapted.errors.slice(0, 3).join(' | ')}`);
    }
  } finally {
    await resolver.close();
    cleanupTempDir(sourceMeta.tempDir);
  }
}

if (require.main === module) {
  main().catch((error) => {
    console.error(`[FETCH-EPL] 失败: ${error.message}`);
    process.exit(1);
  });
}

module.exports = {
  ExistingMatchResolver,
  OUTPUT_PATH,
  SOURCE_CANDIDATES,
  adaptSourceRow,
  buildFallbackMatchId,
  buildMatchId,
  parseArgs,
  parseFootballDataDateTime
};
