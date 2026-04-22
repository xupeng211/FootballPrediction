#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');
const { Pool } = require('pg');

const { buildDbConnectionConfig, REPO_ROOT } = require('./helpers/dbBlueprint');
const { EntityMapper } = require('../../src/infrastructure/etl/EntityMapper');

const entityMapper = new EntityMapper();

const DEFAULTS = {
  sourceDir: path.join(REPO_ROOT, 'data', 'matches'),
  leagueId: 47,
  season: '2024/2025',
  round: '1',
  dateFrom: '2024-08-16T00:00:00.000Z',
  dateTo: '2024-08-20T00:00:00.000Z',
  allowedLeagueIds: [],
  recursive: false,
  allCandidates: false,
  commit: false,
  limit: null
};

function requireValue(argv, index, flagName) {
  const value = argv[index + 1];
  if (!value || String(value).startsWith('--')) {
    throw new Error(`参数 ${flagName} 缺少值`);
  }
  return value;
}

function resolveOptionValue(rawValue) {
  return String(rawValue || '').trim();
}

function applyPositiveIntegerOption(options, key, rawValue, flagName) {
  const parsed = Number.parseInt(rawValue, 10);
  if (!Number.isFinite(parsed) || parsed <= 0) {
    throw new Error(`参数 ${flagName} 必须是正整数`);
  }
  options[key] = parsed;
}

function parseLeagueIdList(rawValue, flagName) {
  const leagueIds = String(rawValue || '')
    .split(',')
    .map((value) => value.trim())
    .filter(Boolean)
    .map((value) => {
      const parsed = Number.parseInt(value, 10);
      if (!Number.isFinite(parsed) || parsed <= 0) {
        throw new Error(`参数 ${flagName} 必须是逗号分隔的正整数列表`);
      }
      return parsed;
    });

  if (leagueIds.length === 0) {
    throw new Error(`参数 ${flagName} 不能为空`);
  }

  return [...new Set(leagueIds)];
}

const ARGUMENT_HANDLERS = {
  '--commit': {
    apply(options) {
      options.commit = true;
    }
  },
  '--recursive': {
    apply(options) {
      options.recursive = true;
    }
  },
  '--all-candidates': {
    apply(options) {
      options.allCandidates = true;
    }
  },
  '--source-dir': {
    takesValue: true,
    apply(options, value) {
      options.sourceDir = path.resolve(REPO_ROOT, value);
    }
  },
  '--league-id': {
    takesValue: true,
    apply(options, value) {
      applyPositiveIntegerOption(options, 'leagueId', value, '--league-id');
    }
  },
  '--allowed-league-ids': {
    takesValue: true,
    apply(options, value) {
      options.allowedLeagueIds = parseLeagueIdList(value, '--allowed-league-ids');
    }
  },
  '--season': {
    takesValue: true,
    apply(options, value) {
      options.season = resolveOptionValue(value);
    }
  },
  '--round': {
    takesValue: true,
    apply(options, value) {
      options.round = resolveOptionValue(value);
    }
  },
  '--date-from': {
    takesValue: true,
    apply(options, value) {
      options.dateFrom = resolveOptionValue(value);
    }
  },
  '--date-to': {
    takesValue: true,
    apply(options, value) {
      options.dateTo = resolveOptionValue(value);
    }
  },
  '--limit': {
    takesValue: true,
    apply(options, value) {
      applyPositiveIntegerOption(options, 'limit', value, '--limit');
    }
  }
};

function parseArgs(argv = process.argv.slice(2)) {
  const options = { ...DEFAULTS };

  for (let index = 0; index < argv.length; index += 1) {
    const token = String(argv[index] || '').trim();
    if (!token) {
      continue;
    }

    const handler = ARGUMENT_HANDLERS[token];
    if (!handler) {
      throw new Error(`未知参数: ${token}`);
    }

    const value = handler.takesValue
      ? requireValue(argv, index, token)
      : null;
    handler.apply(options, value);
    if (handler.takesValue) {
      index += 1;
    }
  }

  return options;
}

function parseJsonFile(filePath) {
  const rawText = fs.readFileSync(filePath, 'utf8');
  return {
    document: JSON.parse(rawText),
    contentLength: rawText.length
  };
}

function resolveRawEnvelope(document) {
  return document?.raw_data || document || {};
}

function resolveMatchDate(rawData = {}) {
  const general = rawData.general || {};
  const header = rawData.header || {};
  return (
    general.matchTimeUTCDateTime
    || general.matchTimeUTCDate
    || general.matchDate
    || general.matchTime
    || header?.status?.utcTime
    || null
  );
}

function toDate(value, fieldName) {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    throw new Error(`${fieldName} 无法解析: ${value}`);
  }
  return parsed;
}

function pickTeamName(rawData, side) {
  const general = rawData.general || {};
  const header = rawData.header || {};
  const teams = Array.isArray(header.teams) ? header.teams : [];
  if (side === 'home') {
    return String(general.homeTeam?.name || teams[0]?.name || '').trim();
  }
  return String(general.awayTeam?.name || teams[1]?.name || '').trim();
}

function resolveLeagueId(rawData = {}) {
  const general = rawData.general || {};
  return Number.parseInt(String(general.leagueId || general.parentLeagueId || ''), 10);
}

function resolveRound(rawData = {}) {
  const general = rawData.general || {};
  return String(general.matchRound || general.leagueRoundName || '').trim();
}

function resolveMatchId(rawData = {}) {
  const general = rawData.general || {};
  return String(general.matchId || general.id || '').trim();
}

function resolveFileMatchId(filePath) {
  return String(path.basename(filePath, '.json').split('_').pop() || '').trim();
}

function resolveFileSeason(filePath) {
  const parts = String(path.basename(filePath, '.json') || '').split('_');
  const seasonTag = String(parts[1] || '').trim();
  if (!/^\d{8}$/.test(seasonTag)) {
    return null;
  }

  return `${seasonTag.slice(0, 4)}/${seasonTag.slice(4, 8)}`;
}

function assertCandidateField(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

function extractCandidate(filePath) {
  const { document, contentLength } = parseJsonFile(filePath);
  const rawData = resolveRawEnvelope(document);
  const general = rawData.general || {};
  const header = rawData.header || {};
  const matchId = resolveMatchId(rawData);
  const fileMatchId = resolveFileMatchId(filePath);
  const fileSeason = resolveFileSeason(filePath);
  const leagueId = resolveLeagueId(rawData);
  const round = resolveRound(rawData);
  const matchDateRaw = resolveMatchDate(rawData);
  const homeTeam = pickTeamName(rawData, 'home');
  const awayTeam = pickTeamName(rawData, 'away');
  const leagueName = entityMapper.normalizeLeagueName(String(general.leagueName || '').trim());

  assertCandidateField(matchId, `缺少 general.matchId: ${path.basename(filePath)}`);
  assertCandidateField(/^\d+$/.test(matchId), `match_id 不是纯数字 FotMob ID: ${matchId}`);
  assertCandidateField(Number.isFinite(leagueId), `缺少 leagueId: ${path.basename(filePath)}`);
  assertCandidateField(matchDateRaw, `缺少 matchDate: ${path.basename(filePath)}`);
  assertCandidateField(homeTeam && awayTeam, `缺少主客队: ${path.basename(filePath)}`);

  const matchDate = toDate(matchDateRaw, 'matchDate');
  const finished = Boolean(header?.status?.finished ?? general.finished);
  const started = Boolean(header?.status?.started ?? general.started);
  const status = finished ? 'finished' : (started ? 'inprogress' : 'scheduled');

  return {
    filePath,
    fileName: path.basename(filePath),
    fileMatchId,
    fileSeason,
    fileNameMatchesMatchId: Boolean(fileMatchId) && fileMatchId === matchId,
    contentLength,
    matchId,
    externalId: matchId,
    leagueId,
    round,
    leagueName,
    homeTeam,
    awayTeam,
    matchDate,
    status,
    isFinished: finished,
    rawData
  };
}

function listJsonFiles(sourceDir, recursive = false) {
  if (!recursive) {
    return fs.readdirSync(sourceDir)
      .filter((fileName) => fileName.endsWith('.json'))
      .map((fileName) => path.join(sourceDir, fileName))
      .sort();
  }

  const queue = [sourceDir];
  const files = [];

  while (queue.length > 0) {
    const currentDir = queue.shift();
    const entries = fs.readdirSync(currentDir, { withFileTypes: true })
      .sort((left, right) => left.name.localeCompare(right.name));

    for (const entry of entries) {
      const fullPath = path.join(currentDir, entry.name);
      if (entry.isDirectory()) {
        queue.push(fullPath);
        continue;
      }

      if (entry.isFile() && entry.name.endsWith('.json')) {
        files.push(fullPath);
      }
    }
  }

  return files.sort();
}

function compareCandidateQuality(left, right) {
  if ((left.contentLength || 0) !== (right.contentLength || 0)) {
    return (left.contentLength || 0) - (right.contentLength || 0);
  }

  if (Number(left.isFinished) !== Number(right.isFinished)) {
    return Number(left.isFinished) - Number(right.isFinished);
  }

  if (Number(left.fileNameMatchesMatchId) !== Number(right.fileNameMatchesMatchId)) {
    return Number(left.fileNameMatchesMatchId) - Number(right.fileNameMatchesMatchId);
  }

  return String(right.filePath || '').localeCompare(String(left.filePath || ''));
}

function dedupeCandidates(candidates = []) {
  const grouped = new Map();
  let filenameMismatches = 0;

  for (const candidate of candidates) {
    if (!candidate.fileNameMatchesMatchId) {
      filenameMismatches += 1;
    }

    if (!grouped.has(candidate.matchId)) {
      grouped.set(candidate.matchId, []);
    }

    grouped.get(candidate.matchId).push(candidate);
  }

  const deduped = [];
  let duplicateMatchIds = 0;
  let duplicateCandidates = 0;

  for (const group of grouped.values()) {
    let best = group[0];
    for (let index = 1; index < group.length; index += 1) {
      const challenger = group[index];
      if (compareCandidateQuality(challenger, best) > 0) {
        best = challenger;
      }
    }

    if (group.length > 1) {
      duplicateMatchIds += 1;
      duplicateCandidates += group.length - 1;
    }

    deduped.push(best);
  }

  return {
    candidates: deduped,
    stats: {
      uniqueMatchIds: deduped.length,
      filenameMismatches,
      duplicateMatchIds,
      duplicateCandidates
    }
  };
}

function applyAllowedLeagueFilter(candidates = [], allowedLeagueIds = []) {
  if (!Array.isArray(allowedLeagueIds) || allowedLeagueIds.length === 0) {
    return {
      candidates,
      excludedByLeagueId: 0
    };
  }

  const allowed = new Set(allowedLeagueIds.map((leagueId) => Number(leagueId)));
  const filtered = candidates.filter((candidate) => allowed.has(Number(candidate.leagueId)));

  return {
    candidates: filtered,
    excludedByLeagueId: candidates.length - filtered.length
  };
}

function filterCandidates(candidates = [], options = {}) {
  const sorted = [...candidates]
    .sort((left, right) => left.matchDate - right.matchDate || left.matchId.localeCompare(right.matchId));

  const seasonFiltered = sorted.filter((candidate) => {
    if (!options.season || !candidate.fileSeason) {
      return true;
    }
    return String(candidate.fileSeason) === String(options.season);
  });

  if (options.allCandidates) {
    return seasonFiltered.slice(0, options.limit || Number.MAX_SAFE_INTEGER);
  }

  const dateFrom = toDate(options.dateFrom, 'dateFrom');
  const dateTo = toDate(options.dateTo, 'dateTo');

  return seasonFiltered
    .filter((candidate) => candidate.leagueId === options.leagueId)
    .filter((candidate) => String(candidate.round) === String(options.round))
    .filter((candidate) => candidate.matchDate >= dateFrom && candidate.matchDate < dateTo)
    .slice(0, options.limit || Number.MAX_SAFE_INTEGER);
}

function chunkValues(values = [], size = 500) {
  const chunks = [];
  for (let index = 0; index < values.length; index += size) {
    chunks.push(values.slice(index, index + size));
  }
  return chunks;
}

function loadCandidates(options = {}) {
  if (!fs.existsSync(options.sourceDir)) {
    throw new Error(`sourceDir 不存在: ${options.sourceDir}`);
  }

  const files = listJsonFiles(options.sourceDir, options.recursive);

  const candidates = [];
  const errors = [];

  for (const filePath of files) {
    try {
      candidates.push(extractCandidate(filePath));
    } catch (error) {
      errors.push(`${path.basename(filePath)}: ${error.message}`);
    }
  }

  const leagueFiltered = applyAllowedLeagueFilter(candidates, options.allowedLeagueIds);
  const dedupeResult = dedupeCandidates(leagueFiltered.candidates);

  return {
    candidates: dedupeResult.candidates,
    errors,
    stats: {
      scannedFiles: files.length,
      parsedFiles: candidates.length,
      excludedByLeagueId: leagueFiltered.excludedByLeagueId,
      filteredCandidates: leagueFiltered.candidates.length,
      ...dedupeResult.stats
    }
  };
}

async function resolveExistingMatchIdentities(client, rows = [], options = {}) {
  const externalIds = [...new Set(rows
    .map((row) => String(row?.externalId || '').trim())
    .filter(Boolean))];

  if (externalIds.length === 0) {
    return {
      rows,
      stats: {
        matchedExistingRows: 0,
        reusedExistingIdentities: 0,
        newSeedIdentities: rows.length
      }
    };
  }

  const existingByExternalId = new Map();
  for (const chunk of chunkValues(externalIds, 500)) {
    const result = await client.query(
      `
        SELECT external_id, match_id
        FROM matches
        WHERE season = $1
          AND external_id = ANY($2::text[])
        ORDER BY updated_at DESC NULLS LAST, created_at DESC NULLS LAST, match_id
      `,
      [options.season, chunk]
    );

    for (const record of result.rows) {
      const externalId = String(record?.external_id || '').trim();
      const matchId = String(record?.match_id || '').trim();
      if (!externalId || !matchId || existingByExternalId.has(externalId)) {
        continue;
      }
      existingByExternalId.set(externalId, matchId);
    }
  }

  let matchedExistingRows = 0;
  let reusedExistingIdentities = 0;
  const resolvedRows = rows.map((row) => {
    const existingMatchId = existingByExternalId.get(String(row.externalId || '').trim());
    if (!existingMatchId) {
      return row;
    }

    matchedExistingRows += 1;
    if (existingMatchId !== row.matchId) {
      reusedExistingIdentities += 1;
    }

    return {
      ...row,
      matchId: existingMatchId
    };
  });

  return {
    rows: resolvedRows,
    stats: {
      matchedExistingRows,
      reusedExistingIdentities,
      newSeedIdentities: rows.length - matchedExistingRows
    }
  };
}

async function upsertMatches(client, rows = [], options = {}) {
  for (const row of rows) {
    await client.query(
      `
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
          data_version,
          data_source,
          pipeline_status
        ) VALUES (
          $1, $2, $3, $4, $5, $6, $7, $8, $9, 'FOTMOB_SAMPLE_SEED', 'FotMob', 'harvested'
        )
        ON CONFLICT (match_id) DO UPDATE SET
          external_id = EXCLUDED.external_id,
          league_name = EXCLUDED.league_name,
          season = EXCLUDED.season,
          home_team = EXCLUDED.home_team,
          away_team = EXCLUDED.away_team,
          match_date = EXCLUDED.match_date,
          status = EXCLUDED.status,
          is_finished = EXCLUDED.is_finished,
          data_version = EXCLUDED.data_version,
          data_source = EXCLUDED.data_source,
          pipeline_status = EXCLUDED.pipeline_status,
          updated_at = NOW()
      `,
      [
        row.matchId,
        row.externalId,
        row.leagueName,
        options.season,
        row.homeTeam,
        row.awayTeam,
        row.matchDate,
        row.status,
        row.isFinished
      ]
    );
  }
}

async function upsertRawMatchData(client, rows = []) {
  for (const row of rows) {
    await client.query(
      `
        INSERT INTO raw_match_data (
          match_id,
          external_id,
          raw_data,
          collected_at,
          data_version
        ) VALUES (
          $1, $2, $3::jsonb, NOW(), 'FOTMOB_SAMPLE_SEED'
        )
        ON CONFLICT (match_id) DO UPDATE SET
          external_id = EXCLUDED.external_id,
          raw_data = EXCLUDED.raw_data,
          collected_at = NOW(),
          data_version = EXCLUDED.data_version
      `,
      [
        row.matchId,
        row.externalId,
        JSON.stringify(row.rawData)
      ]
    );
  }
}

async function seedFotMobSample(options = {}) {
  const { candidates, errors, stats } = loadCandidates(options);
  const selected = filterCandidates(candidates, options);

  if (selected.length === 0) {
    return {
      committed: false,
      selected,
      stats,
      errors,
      message: '未找到符合条件的本地 FotMob 样本'
    };
  }

  if (!options.commit) {
    return {
      committed: false,
      selected,
      stats,
      errors,
      message: 'dry-run'
    };
  }

  const pool = new Pool(buildDbConnectionConfig());
  const client = await pool.connect();

  try {
    const identityResolution = await resolveExistingMatchIdentities(client, selected, options);
    const resolvedSelected = identityResolution.rows;
    await client.query('BEGIN');
    await upsertMatches(client, resolvedSelected, options);
    await upsertRawMatchData(client, resolvedSelected);
    await client.query('COMMIT');

    return {
      committed: true,
      selected: resolvedSelected,
      stats: {
        ...stats,
        ...identityResolution.stats
      },
      errors,
      message: 'commit'
    };
  } catch (error) {
    await client.query('ROLLBACK').catch(() => {});
    throw error;
  } finally {
    client.release();
    await pool.end();
  }
}

function formatSelection(rows = [], limit = 20) {
  const selected = rows.slice(0, limit);
  const preview = selected
    .map((row) => `${row.matchId}|${row.round}|${row.matchDate.toISOString()}|${row.homeTeam} vs ${row.awayTeam}|${row.fileName}`)
    .join(', ');

  if (rows.length <= limit) {
    return preview;
  }

  return `${preview} ... (+${rows.length - limit} more)`;
}

function formatFilterSummary(options = {}) {
  if (options.allCandidates) {
    return 'filter=all';
  }

  return (
    `filter=window league_id=${options.leagueId} round=${options.round} `
    + `date_from=${options.dateFrom} date_to=${options.dateTo}`
  );
}

async function main() {
  const options = parseArgs();
  const result = await seedFotMobSample(options);

  console.log(
    `[SEED-FOTMOB-SAMPLE] mode=${result.committed ? 'commit' : 'dry-run'} `
      + `source_dir=${options.sourceDir} recursive=${options.recursive} `
      + `allowed_league_ids=${options.allowedLeagueIds.length > 0 ? options.allowedLeagueIds.join(',') : 'any'} `
      + `season=${options.season} ${formatFilterSummary(options)} `
      + `scanned_files=${result.stats.scannedFiles} parsed_files=${result.stats.parsedFiles} `
      + `filtered_candidates=${result.stats.filteredCandidates} excluded_by_league_id=${result.stats.excludedByLeagueId} `
      + `unique_match_ids=${result.stats.uniqueMatchIds} filename_mismatches=${result.stats.filenameMismatches} `
      + `duplicate_match_ids=${result.stats.duplicateMatchIds} duplicate_candidates=${result.stats.duplicateCandidates} `
      + `matched_existing_rows=${result.stats.matchedExistingRows || 0} `
      + `reused_existing_identities=${result.stats.reusedExistingIdentities || 0} `
      + `new_seed_identities=${result.stats.newSeedIdentities || 0} `
      + `selected=${result.selected.length} `
      + `selection=${formatSelection(result.selected)} `
      + `parse_errors=${result.errors.length} message=${result.message}`
  );

  if (result.selected.length === 0) {
    process.exitCode = 1;
  }
}

if (require.main === module) {
  main().catch((error) => {
    console.error(`[SEED-FOTMOB-SAMPLE] 失败: ${error.message}`);
    process.exit(1);
  });
}

module.exports = {
  applyAllowedLeagueFilter,
  compareCandidateQuality,
  dedupeCandidates,
  extractCandidate,
  filterCandidates,
  listJsonFiles,
  loadCandidates,
  parseArgs,
  resolveExistingMatchIdentities,
  resolveFileMatchId,
  resolveFileSeason,
  seedFotMobSample
};
