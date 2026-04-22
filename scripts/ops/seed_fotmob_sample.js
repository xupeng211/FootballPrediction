#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');
const { Pool } = require('pg');

const { buildDbConnectionConfig, REPO_ROOT } = require('./helpers/dbBlueprint');

const DEFAULTS = {
  sourceDir: path.join(REPO_ROOT, 'data', 'matches'),
  leagueId: 47,
  season: '2024/2025',
  round: '1',
  dateFrom: '2024-08-16T00:00:00.000Z',
  dateTo: '2024-08-20T00:00:00.000Z',
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

const ARGUMENT_HANDLERS = {
  '--commit': {
    apply(options) {
      options.commit = true;
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
  return JSON.parse(fs.readFileSync(filePath, 'utf8'));
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

function assertCandidateField(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

function extractCandidate(filePath) {
  const document = parseJsonFile(filePath);
  const rawData = resolveRawEnvelope(document);
  const general = rawData.general || {};
  const header = rawData.header || {};
  const matchId = resolveMatchId(rawData);
  const leagueId = resolveLeagueId(rawData);
  const round = resolveRound(rawData);
  const matchDateRaw = resolveMatchDate(rawData);
  const homeTeam = pickTeamName(rawData, 'home');
  const awayTeam = pickTeamName(rawData, 'away');
  const leagueName = String(general.leagueName || '').trim();

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

function filterCandidates(candidates = [], options = {}) {
  const dateFrom = toDate(options.dateFrom, 'dateFrom');
  const dateTo = toDate(options.dateTo, 'dateTo');

  return candidates
    .filter((candidate) => candidate.leagueId === options.leagueId)
    .filter((candidate) => String(candidate.round) === String(options.round))
    .filter((candidate) => candidate.matchDate >= dateFrom && candidate.matchDate < dateTo)
    .sort((left, right) => left.matchDate - right.matchDate || left.matchId.localeCompare(right.matchId))
    .slice(0, options.limit || Number.MAX_SAFE_INTEGER);
}

function loadCandidates(options = {}) {
  if (!fs.existsSync(options.sourceDir)) {
    throw new Error(`sourceDir 不存在: ${options.sourceDir}`);
  }

  const files = fs.readdirSync(options.sourceDir)
    .filter((fileName) => fileName.endsWith('.json'))
    .map((fileName) => path.join(options.sourceDir, fileName));

  const candidates = [];
  const errors = [];

  for (const filePath of files) {
    try {
      candidates.push(extractCandidate(filePath));
    } catch (error) {
      errors.push(`${path.basename(filePath)}: ${error.message}`);
    }
  }

  return {
    candidates,
    errors
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
  const { candidates, errors } = loadCandidates(options);
  const selected = filterCandidates(candidates, options);

  if (selected.length === 0) {
    return {
      committed: false,
      selected,
      scanned: candidates.length,
      errors,
      message: '未找到符合条件的本地 FotMob 样本'
    };
  }

  if (!options.commit) {
    return {
      committed: false,
      selected,
      scanned: candidates.length,
      errors,
      message: 'dry-run'
    };
  }

  const pool = new Pool(buildDbConnectionConfig());
  const client = await pool.connect();

  try {
    await client.query('BEGIN');
    await upsertMatches(client, selected, options);
    await upsertRawMatchData(client, selected);
    await client.query('COMMIT');

    return {
      committed: true,
      selected,
      scanned: candidates.length,
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

function formatSelection(rows = []) {
  return rows
    .map((row) => `${row.matchId}|${row.round}|${row.matchDate.toISOString()}|${row.homeTeam} vs ${row.awayTeam}|${row.fileName}`)
    .join(', ');
}

async function main() {
  const options = parseArgs();
  const result = await seedFotMobSample(options);

  console.log(
    `[SEED-FOTMOB-SAMPLE] mode=${result.committed ? 'commit' : 'dry-run'} `
      + `league_id=${options.leagueId} season=${options.season} round=${options.round} `
      + `date_from=${options.dateFrom} date_to=${options.dateTo} `
      + `scanned=${result.scanned} selected=${result.selected.length} `
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
  extractCandidate,
  filterCandidates,
  loadCandidates,
  parseArgs,
  seedFotMobSample
};
