'use strict';

const fs = require('fs');
const https = require('https');
const { Pool } = require('pg');

const { Normalizer } = require('../../src/utils/Normalizer');
const { ReconParser } = require('../../src/infrastructure/recon/ReconParser');
const { ReconDomScraper } = require('../../src/infrastructure/recon/services/ReconDomScraper');
const { L1ConfigManager } = require('../../src/infrastructure/services/L1ConfigManager');
const { FixtureRepository } = require('../../src/infrastructure/services/FixtureRepository');
const { buildDbPoolConfig } = require('./ReconCLIHandler');

const BASE_URL = 'https://www.oddsportal.com';

function parseArgs(argv = process.argv.slice(2)) {
  const result = {
    leagueId: null,
    season: null,
    threshold: 0.1,
    remoteSource: 'auto',
    standingsUrl: null,
    dryRun: false,
    output: null
  };

  for (let index = 0; index < argv.length; index++) {
    const token = argv[index];
    switch (token) {
      case '--league-id':
        result.leagueId = Number(argv[++index]);
        break;
      case '--season':
        result.season = argv[++index];
        break;
      case '--threshold':
        result.threshold = Number(argv[++index]);
        break;
      case '--remote-source':
        result.remoteSource = String(argv[++index] || 'auto').trim().toLowerCase();
        break;
      case '--standings-url':
        result.standingsUrl = String(argv[++index] || '').trim() || null;
        break;
      case '--output':
        result.output = String(argv[++index] || '').trim() || null;
        break;
      case '--dry-run':
        result.dryRun = true;
        break;
      default:
        break;
    }
  }

  if (!Number.isInteger(result.leagueId) || result.leagueId <= 0) {
    throw new Error('必须传入 --league-id，例如 --league-id 140');
  }

  if (!['auto', 'standings', 'mapping_candidates'].includes(result.remoteSource)) {
    throw new Error(`不支持的 --remote-source: ${result.remoteSource}`);
  }

  return result;
}

function normalizePathSegment(value) {
  return String(value || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '');
}

function buildStandingsUrl(league, season) {
  const country = normalizePathSegment(league?.country);
  const slug = String(league?.resultsSlug || league?.slug || '')
    .trim()
    .toLowerCase();
  const normalizedSeason = String(season || '').trim();
  const seasonType = String(league?.seasonType || '').trim().toLowerCase();
  const resultsUrlStrategy = String(league?.resultsUrlStrategy || '').trim().toLowerCase();

  if (resultsUrlStrategy === 'seasonless') {
    return `${BASE_URL}/football/${country}/${slug}/standings/`;
  }

  if (seasonType === 'single_year') {
    const singleYear = normalizedSeason.match(/(\d{4})$/)?.[1] || normalizedSeason;
    return `${BASE_URL}/football/${country}/${slug}-${singleYear}/standings/`;
  }

  return `${BASE_URL}/football/${country}/${slug}-${normalizedSeason.replace('/', '-')}/standings/`;
}

function fetchText(url, redirectCount = 0) {
  return new Promise((resolve, reject) => {
    const request = https.get(url, {
      headers: {
        'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
        'accept-language': 'en-US,en;q=0.9',
        accept: 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
      }
    }, (response) => {
      const location = response.headers.location;
      if (response.statusCode >= 300 && response.statusCode < 400 && location) {
        if (redirectCount >= 5) {
          reject(new Error(`重定向次数过多: ${url}`));
          response.resume();
          return;
        }

        response.resume();
        resolve(fetchText(new URL(location, url).href, redirectCount + 1));
        return;
      }

      if (response.statusCode !== 200) {
        reject(new Error(`HTTP ${response.statusCode}: ${url}`));
        response.resume();
        return;
      }

      const chunks = [];
      response.setEncoding('utf8');
      response.on('data', (chunk) => chunks.push(chunk));
      response.on('end', () => resolve(chunks.join('')));
    });

    request.on('error', reject);
    request.setTimeout(30000, () => {
      request.destroy(new Error(`请求超时: ${url}`));
    });
  });
}

function splitCandidateNamePair(candidateName) {
  const cleanValue = String(candidateName || '').trim();
  if (!cleanValue) {
    return null;
  }

  const parts = cleanValue.split(/\s+vs\s+/i).map((item) => item.trim()).filter(Boolean);
  if (parts.length !== 2) {
    return null;
  }

  return {
    left: parts[0],
    right: parts[1]
  };
}

function decodeRemoteTeamSegment(segment, fallbackName = null) {
  const cleanSegment = String(segment || '').trim();
  if (!cleanSegment) {
    return null;
  }

  const match = cleanSegment.match(/^(.*)-([A-Za-z0-9]{8})$/);
  if (!match) {
    return null;
  }

  const slug = match[1];
  const remoteHash = match[2];
  const decodedName = slug
    .split('-')
    .filter(Boolean)
    .map((part) => (/^[a-z]{1,3}$/i.test(part) ? part.toUpperCase() : `${part.charAt(0).toUpperCase()}${part.slice(1)}`))
    .join(' ');

  return {
    remoteHash,
    remoteName: String(fallbackName || decodedName).trim(),
    remoteSegment: cleanSegment
  };
}

function decodeSlugName(slug) {
  return String(slug || '')
    .split('-')
    .filter(Boolean)
    .map((part) => (/^[a-z]{1,3}$/i.test(part) ? part.toUpperCase() : `${part.charAt(0).toUpperCase()}${part.slice(1)}`))
    .join(' ')
    .trim();
}

function buildRemoteEvidenceKey(remoteEntry, parser) {
  const normalizedRemoteName = parser?.normalizeTeamName?.(remoteEntry?.remoteName || '')
    || String(remoteEntry?.remoteName || '').trim();
  if (!normalizedRemoteName) {
    return remoteEntry?.remoteHash
      ? String(remoteEntry.remoteHash).trim().toLowerCase()
      : null;
  }

  return normalizedRemoteName.toLowerCase();
}

function upsertRemoteEvidence(map, remoteEntry, evidenceUrl, parser) {
  if (!remoteEntry?.remoteName) {
    return;
  }

  const remoteKey = buildRemoteEvidenceKey(remoteEntry, parser);
  if (!remoteKey) {
    return;
  }

  const existing = map.get(remoteKey);
  if (!existing) {
    map.set(remoteKey, {
      remoteHash: remoteEntry.remoteHash,
      remoteName: remoteEntry.remoteName,
      remoteSegment: remoteEntry.remoteSegment,
      evidenceUrl: evidenceUrl || null,
      source: 'mapping_candidates'
    });
    return;
  }

  if (remoteEntry.remoteName.length > existing.remoteName.length) {
    existing.remoteName = remoteEntry.remoteName;
  }
  if (!existing.evidenceUrl && evidenceUrl) {
    existing.evidenceUrl = evidenceUrl;
  }
}

function findBestLocalTeamMatch(remoteName, localTeams, parser) {
  let bestMatch = null;

  for (const localTeam of Array.isArray(localTeams) ? localTeams : []) {
    const score = Number(parser.calculateSimilarity(remoteName, localTeam.team_name) || 0);
    if (!bestMatch || score > bestMatch.score) {
      bestMatch = {
        teamId: String(localTeam.team_id),
        teamName: String(localTeam.team_name),
        score
      };
    }
  }

  return bestMatch;
}

function findBestStandardUrlSplit(matchSlug, localTeams, parser) {
  const parts = String(matchSlug || '').split('-').filter(Boolean);
  if (parts.length < 2) {
    return null;
  }

  let bestSplit = null;

  for (let index = 1; index < parts.length; index++) {
    const leftSlug = parts.slice(0, index).join('-');
    const rightSlug = parts.slice(index).join('-');
    const leftRemoteName = decodeSlugName(leftSlug);
    const rightRemoteName = decodeSlugName(rightSlug);
    const leftMatch = findBestLocalTeamMatch(leftRemoteName, localTeams, parser);
    const rightMatch = findBestLocalTeamMatch(rightRemoteName, localTeams, parser);

    if (!leftMatch || !rightMatch || leftMatch.teamId === rightMatch.teamId) {
      continue;
    }

    const averageScore = (leftMatch.score + rightMatch.score) / 2;
    const minScore = Math.min(leftMatch.score, rightMatch.score);
    const exactBonus = (
      parser.normalizeTeamName(leftRemoteName) === parser.normalizeTeamName(leftMatch.teamName)
      ? 0.05
      : 0
    ) + (
      parser.normalizeTeamName(rightRemoteName) === parser.normalizeTeamName(rightMatch.teamName)
      ? 0.05
      : 0
    );

    const splitCandidate = {
      averageScore,
      minScore,
      totalScore: averageScore + exactBonus,
      leftRemoteName,
      rightRemoteName,
      leftMatch,
      rightMatch
    };

    if (
      !bestSplit
      || splitCandidate.totalScore > bestSplit.totalScore
      || (
        splitCandidate.totalScore === bestSplit.totalScore
        && splitCandidate.minScore > bestSplit.minScore
      )
    ) {
      bestSplit = splitCandidate;
    }
  }

  if (!bestSplit) {
    return null;
  }

  if (bestSplit.averageScore < 0.78 || bestSplit.minScore < 0.65) {
    return null;
  }

  return bestSplit;
}

function parseStandardMatchUrlEvidence(url, candidateName, parser, localTeams) {
  const path = (() => {
    try {
      return new URL(url).pathname;
    } catch {
      return '';
    }
  })();
  if (!path || /\/football\/h2h\//i.test(path)) {
    return [];
  }

  const trimmedPath = String(path).replace(/\/+$/, '');
  const lastSegment = trimmedPath.split('/').filter(Boolean).pop() || '';
  const pair = splitCandidateNamePair(candidateName);
  const parsedUrl = parser?.parseMatchUrl?.(url) || {};

  const match = lastSegment.match(/^(.*)-([A-Za-z0-9]{8})$/);
  if (!match) {
    return [];
  }

  const matchSlug = match[1];
  const remoteSegment = match ? lastSegment : null;
  const names = [];

  if (pair?.left && pair?.right) {
    names.push(pair.left, pair.right);
  }

  const bestSplit = findBestStandardUrlSplit(matchSlug, localTeams, parser);
  if (bestSplit?.leftRemoteName && bestSplit?.rightRemoteName) {
    names.push(bestSplit.leftRemoteName, bestSplit.rightRemoteName);
  } else if (parsedUrl.homeTeam && parsedUrl.homeTeam !== 'Unknown' && parsedUrl.awayTeam && parsedUrl.awayTeam !== 'Unknown') {
    const parsedAverage = (
      Number(parser.calculateSimilarity(parsedUrl.homeTeam, findBestLocalTeamMatch(parsedUrl.homeTeam, localTeams, parser)?.teamName || '') || 0)
      + Number(parser.calculateSimilarity(parsedUrl.awayTeam, findBestLocalTeamMatch(parsedUrl.awayTeam, localTeams, parser)?.teamName || '') || 0)
    ) / 2;

    if (parsedAverage >= 0.85) {
      names.push(parsedUrl.homeTeam, parsedUrl.awayTeam);
    }
  }

  const dedupedNames = [];
  const seen = new Set();
  for (const rawName of names) {
    const cleanName = String(rawName || '').trim();
    if (!cleanName) {
      continue;
    }

    const dedupeKey = String(parser?.normalizeTeamName?.(cleanName) || cleanName).toLowerCase();
    if (!dedupeKey || seen.has(dedupeKey)) {
      continue;
    }

    seen.add(dedupeKey);
    dedupedNames.push(cleanName);
  }

  return dedupedNames.map((remoteName) => ({
    remoteHash: null,
    remoteName,
    remoteSegment
  }));
}

async function loadRemoteTeamsFromMappingEvidence(pool, leagueId, season, parser, localTeams) {
  const matchIdPrefix = `${Number(leagueId)}_%`;
  const result = await pool.query(`
    SELECT full_url, candidate_name, match_confidence
    FROM matches_oddsportal_mapping
    WHERE match_id LIKE $1
      AND season = $2
      AND full_url LIKE 'https://www.oddsportal.com/football/%'
    ORDER BY match_confidence DESC NULLS LAST, updated_at DESC NULLS LAST, created_at DESC NULLS LAST
  `, [matchIdPrefix, season]);

  const teamsByHash = new Map();

  for (const row of result.rows || []) {
    const url = String(row.full_url || '').trim();
    const path = (() => {
      try {
        return new URL(url).pathname;
      } catch {
        return '';
      }
    })();
    const match = path.match(/\/football\/h2h\/([^/]+)\/([^/]+)\/?$/i);
    if (!match) {
      const standardTeams = parseStandardMatchUrlEvidence(url, row.candidate_name, parser, localTeams);
      for (const remoteEntry of standardTeams) {
        upsertRemoteEvidence(teamsByHash, remoteEntry, url, parser);
      }
      continue;
    }

    const pair = splitCandidateNamePair(row.candidate_name);
    const left = decodeRemoteTeamSegment(match[1], pair?.left || null);
    const right = decodeRemoteTeamSegment(match[2], pair?.right || null);
    upsertRemoteEvidence(teamsByHash, left, url, parser);
    upsertRemoteEvidence(teamsByHash, right, url, parser);
  }

  return [...teamsByHash.values()].sort((left, right) => left.remoteName.localeCompare(right.remoteName));
}

function buildClosedSpaceAssignments(remoteTeams, localTeams, parser, threshold) {
  const candidatePairs = [];

  for (const remote of remoteTeams) {
    for (const local of localTeams) {
      const score = Number(parser.calculateSimilarity(remote.remoteName, local.team_name) || 0);
      if (score < threshold) {
        continue;
      }

      candidatePairs.push({
        remoteHash: remote.remoteHash || null,
        remoteName: remote.remoteName,
        remoteSegment: remote.remoteSegment || null,
        evidenceUrl: remote.evidenceUrl || remote.teamUrl || null,
        localTeamId: String(local.team_id),
        localTeamName: local.team_name,
        score
      });
    }
  }

  candidatePairs.sort((left, right) => (
    right.score - left.score
    || left.remoteName.localeCompare(right.remoteName)
    || left.localTeamName.localeCompare(right.localTeamName)
  ));

  const usedRemote = new Set();
  const usedLocal = new Set();
  const assignments = [];

  for (const candidate of candidatePairs) {
    const remoteKey = String(candidate.remoteHash || candidate.remoteName).toLowerCase();
    const localKey = String(candidate.localTeamId);
    if (usedRemote.has(remoteKey) || usedLocal.has(localKey)) {
      continue;
    }

    usedRemote.add(remoteKey);
    usedLocal.add(localKey);
    assignments.push(candidate);
  }

  const unresolvedRemote = remoteTeams.filter((remote) => {
    const remoteKey = String(remote.remoteHash || remote.remoteName).toLowerCase();
    return !usedRemote.has(remoteKey);
  });
  const unresolvedLocal = localTeams.filter((local) => !usedLocal.has(String(local.team_id)));

  return {
    assignments,
    unresolvedRemote,
    unresolvedLocal
  };
}

function printAssignments(assignments) {
  console.log('\n[字典预览]');
  for (const item of assignments) {
    console.log(
      `- ${item.remoteName.padEnd(24)} -> ${String(item.localTeamName).padEnd(24)} ` +
      `(team_id=${item.localTeamId}, score=${item.score.toFixed(2)}, hash=${item.remoteHash || 'n/a'})`
    );
  }
}

async function main() {
  const args = parseArgs();
  const logger = { info() {}, warn() {}, error() {} };
  const configManager = new L1ConfigManager({ logger });
  const league = configManager.getLeagueById(args.leagueId);

  if (!league) {
    throw new Error(`未找到 league_id=${args.leagueId} 的联赛配置`);
  }

  const season = Normalizer.normalizeSeason(args.season || configManager.getDefaultSeason(args.leagueId));
  const standingsUrl = args.standingsUrl || buildStandingsUrl(league, season);
  const dbPool = new Pool(buildDbPoolConfig());
  const repository = new FixtureRepository({
    dbPool,
    logger
  });
  const parser = new ReconParser({
    logger,
    config: {
      teamMappings: require('../../config/recon_config.json').team_mappings || {}
    }
  });
  const scraper = new ReconDomScraper({ logger });

  let standingsHtml = '';
  let standingsTeams = [];
  let standingsFetchError = null;

  if (args.remoteSource === 'auto' || args.remoteSource === 'standings') {
    try {
      standingsHtml = await fetchText(standingsUrl);
      if (!standingsHtml.includes('required league is not supported')) {
        standingsTeams = scraper.extractTeamsFromStandings(standingsHtml, {
          currentUrl: standingsUrl
        }).map((entry) => ({
          remoteName: entry.teamName,
          remoteHash: entry.teamHash || null,
          remoteSegment: null,
          teamUrl: entry.teamUrl || null,
          evidenceUrl: entry.teamUrl || null,
          source: 'standings'
        }));
      }
    } catch (error) {
      standingsFetchError = error;
    }
  }

  let remoteSource = 'standings';
  let remoteTeams = standingsTeams;
  const localTeams = await repository.getLeagueTeamCatalog(args.leagueId, { season });
  if ((args.remoteSource === 'mapping_candidates') || (args.remoteSource === 'auto' && remoteTeams.length === 0)) {
    remoteSource = 'mapping_candidates';
    remoteTeams = await loadRemoteTeamsFromMappingEvidence(dbPool, args.leagueId, season, parser, localTeams);
  }

  const matched = buildClosedSpaceAssignments(remoteTeams, localTeams, parser, args.threshold);
  const dictionaryRows = matched.assignments.map((item) => ({
    league_id: args.leagueId,
    season,
    remote_name: item.remoteName,
    local_team_id: item.localTeamId
  }));

  if (!args.dryRun) {
    await repository.replaceLeagueDictionaryEntries(dictionaryRows, {
      leagueId: args.leagueId,
      season
    });
  }

  const summary = {
    generated_at: new Date().toISOString(),
    league_id: args.leagueId,
    league_name: league.name,
    season,
    threshold: args.threshold,
    remote_source: remoteSource,
    standings_attempt: {
      url: standingsUrl,
      extracted_count: standingsTeams.length,
      fetch_error: standingsFetchError ? standingsFetchError.message : null,
      unsupported_hint: standingsHtml.includes('required league is not supported')
    },
    remote_team_count: remoteTeams.length,
    local_team_count: localTeams.length,
    matched_count: matched.assignments.length,
    unmatched_remote_count: matched.unresolvedRemote.length,
    unmatched_local_count: matched.unresolvedLocal.length,
    dry_run: args.dryRun,
    dictionary: matched.assignments.map((item) => ({
      remote_name: item.remoteName,
      remote_hash: item.remoteHash || null,
      evidence_url: item.evidenceUrl || null,
      local_team_id: item.localTeamId,
      local_team_name: item.localTeamName,
      score: Number(item.score.toFixed(4))
    }))
  };

  console.log(`\n[联赛] ${league.name} (${args.leagueId})`);
  console.log(`[赛季] ${season}`);
  console.log(`[standings] ${standingsUrl}`);
  console.log(`[远端源] ${remoteSource}`);
  console.log(`[standings 抽取] ${standingsTeams.length} 支球队`);
  if (standingsFetchError) {
    console.log(`[standings 错误] ${standingsFetchError.message}`);
  }
  if (summary.standings_attempt.unsupported_hint) {
    console.log('[standings 提示] OddsPortal 当前返回 unsupported league 壳页');
  }
  console.log(`[本地队伍] ${localTeams.length}`);
  console.log(`[成功匹配] ${matched.assignments.length}`);
  console.log(`[未匹配远端] ${matched.unresolvedRemote.length}`);
  console.log(`[未匹配本地] ${matched.unresolvedLocal.length}`);
  printAssignments(matched.assignments);

  if (args.output) {
    fs.writeFileSync(args.output, `${JSON.stringify(summary, null, 2)}\n`, 'utf8');
    console.log(`\n[输出] ${args.output}`);
  }

  await dbPool.end();
}

main().catch(async (error) => {
  console.error(`❌ generate_league_dictionary 失败: ${error.message}`);
  process.exitCode = 1;
});
