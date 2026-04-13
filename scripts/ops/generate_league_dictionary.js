'use strict';

const fs = require('fs');
const { Pool } = require('pg');

const { Normalizer } = require('../../src/utils/Normalizer');
const { ReconParser } = require('../../src/infrastructure/recon/ReconParser');
const { ReconDomScraper } = require('../../src/infrastructure/recon/services/ReconDomScraper');
const { L1ConfigManager } = require('../../src/infrastructure/services/L1ConfigManager');
const { FixtureRepository } = require('../../src/infrastructure/services/FixtureRepository');
const { buildDbPoolConfig } = require('./ReconCLIHandler');
const { parseArgs } = require('./helpers/generateLeagueDictionaryArgs');
const {
  buildStandingsUrl,
  fetchText,
} = require('./helpers/generateLeagueDictionaryRemoteFetch');
const {
  loadRemoteTeamsFromMappingEvidence,
  buildClosedSpaceAssignments,
  printAssignments
} = require('./helpers/generateLeagueDictionaryEvidence');

async function loadStandingsRemoteTeams(args, standingsUrl, scraper) {
  let standingsHtml = '';
  let standingsTeams = [];
  let standingsFetchError = null;

  if (args.remoteSource !== 'auto' && args.remoteSource !== 'standings') {
    return { standingsHtml, standingsTeams, standingsFetchError };
  }

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

  return { standingsHtml, standingsTeams, standingsFetchError };
}

async function resolveRemoteTeams(args, context) {
  const standingsState = await loadStandingsRemoteTeams(args, context.standingsUrl, context.scraper);
  let remoteSource = 'standings';
  let remoteTeams = standingsState.standingsTeams;

  if (args.remoteSource === 'mapping_candidates' || (args.remoteSource === 'auto' && remoteTeams.length === 0)) {
    remoteSource = 'mapping_candidates';
    remoteTeams = await loadRemoteTeamsFromMappingEvidence(
      context.dbPool,
      args.leagueId,
      context.season,
      context.parser,
      context.localTeams
    );
  }

  return {
    ...standingsState,
    remoteSource,
    remoteTeams
  };
}

function buildSummary(args, league, season, remoteState, localTeams, matched, standingsUrl) {
  return {
    generated_at: new Date().toISOString(),
    league_id: args.leagueId,
    league_name: league.name,
    season,
    threshold: args.threshold,
    remote_source: remoteState.remoteSource,
    standings_attempt: {
      url: standingsUrl,
      extracted_count: remoteState.standingsTeams.length,
      fetch_error: remoteState.standingsFetchError ? remoteState.standingsFetchError.message : null,
      unsupported_hint: remoteState.standingsHtml.includes('required league is not supported')
    },
    remote_team_count: remoteState.remoteTeams.length,
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
}

function printSummary(league, args, season, standingsUrl, remoteState, localTeams, matched, summary) {
  console.log(`\n[联赛] ${league.name} (${args.leagueId})`);
  console.log(`[赛季] ${season}`);
  console.log(`[standings] ${standingsUrl}`);
  console.log(`[远端源] ${remoteState.remoteSource}`);
  console.log(`[standings 抽取] ${remoteState.standingsTeams.length} 支球队`);
  if (remoteState.standingsFetchError) {
    console.log(`[standings 错误] ${remoteState.standingsFetchError.message}`);
  }
  if (summary.standings_attempt.unsupported_hint) {
    console.log('[standings 提示] OddsPortal 当前返回 unsupported league 壳页');
  }
  console.log(`[本地队伍] ${localTeams.length}`);
  console.log(`[成功匹配] ${matched.assignments.length}`);
  console.log(`[未匹配远端] ${matched.unresolvedRemote.length}`);
  console.log(`[未匹配本地] ${matched.unresolvedLocal.length}`);
  printAssignments(matched.assignments);
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
  const repository = new FixtureRepository({ dbPool, logger });
  const parser = new ReconParser({
    logger,
    config: {
      teamMappings: require('../../config/recon_config.json').team_mappings || {}
    }
  });
  const scraper = new ReconDomScraper({ logger });

  const localTeams = await repository.getLeagueTeamCatalog(args.leagueId, { season });
  const remoteState = await resolveRemoteTeams(args, {
    dbPool,
    localTeams,
    parser,
    scraper,
    season,
    standingsUrl
  });
  const matched = buildClosedSpaceAssignments(remoteState.remoteTeams, localTeams, parser, args.threshold);
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

  const summary = buildSummary(args, league, season, remoteState, localTeams, matched, standingsUrl);
  printSummary(league, args, season, standingsUrl, remoteState, localTeams, matched, summary);

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
