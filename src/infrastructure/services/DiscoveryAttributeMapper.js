'use strict';

const {
  buildDiscoveryMatchId,
  extractDiscoveryDate,
  getDiscoveryExternalId,
  getDiscoveryTeamSeed,
  toIsoTimestamp
} = require('../shared/helpers/discoveryParserShared');

const STATUS_RESOLVERS = [
  { status: 'finished', matches: (match) => match?.status?.finished || match?.status?.completed || match?.finished || match?.isFinished },
  { status: 'live', matches: (match) => match?.status?.live || match?.status?.started || match?.isLive || match?.live },
  { status: 'cancelled', matches: (match) => match?.status?.cancelled || match?.status?.postponed || match?.cancelled },
  { status: 'scheduled', matches: (match) => match?.status?.scheduled || match?.status?.upcoming || match?.scheduled }
];

function pickTextValue(values) {
  return values.find((value) => typeof value === 'string' && value.trim())?.trim() || null;
}

function resolveLeagueName(leagueConfig, leagueId) {
  const league = leagueConfig?.active_leagues?.find((item) => Number(item?.id) === Number(leagueId));
  return league?.name || 'Unknown League';
}

function buildDateWindow(isHistorical, config = {}) {
  if (isHistorical || config.fullSync === true) {
    return null;
  }

  const now = new Date();
  const past = new Date(now);
  const future = new Date(now);

  past.setDate(past.getDate() - Number(config.lookbackDays || 30));
  future.setDate(future.getDate() + Number(config.lookaheadDays || 7));

  return { past, future };
}

function isOutsideDateWindow(matchDate, dateWindow) {
  return Boolean(dateWindow && (matchDate < dateWindow.past || matchDate > dateWindow.future));
}

function resolveTeamName(match, side) {
  const team = getDiscoveryTeamSeed(match, side);
  if (team && typeof team === 'object') {
    return pickTextValue([team.name, team.shortName, team.longName]) || 'Unknown';
  }

  return pickTextValue([team]) || 'Unknown';
}

function resolveStatus(match) {
  const resolvedStatus = STATUS_RESOLVERS.find((resolver) => resolver.matches(match));
  if (resolvedStatus) {
    return resolvedStatus.status;
  }

  return typeof match?.status === 'string'
    ? match.status.toLowerCase()
    : 'scheduled';
}

class DiscoveryAttributeMapper {
  constructor(options = {}) {
    this.leagueConfig = options.leagueConfig || null;
    this.dataSource = options.dataSource || 'FotMob';
  }

  transformMatches(rawMatches, leagueId, season, isHistorical, config = {}) {
    const context = {
      dateWindow: buildDateWindow(isHistorical, config),
      leagueId,
      leagueName: resolveLeagueName(this.leagueConfig, leagueId),
      season,
      seenIds: new Set(),
      timestamp: toIsoTimestamp(new Date())
    };

    return Array.isArray(rawMatches)
      ? rawMatches.reduce((matches, match) => {
        const normalizedMatch = this.mapMatch(match, context);
        if (normalizedMatch) {
          matches.push(normalizedMatch);
        }
        return matches;
      }, [])
      : [];
  }

  mapMatch(match, context) {
    if (!match || typeof match !== 'object') {
      return null;
    }

    const externalId = getDiscoveryExternalId(match);
    if (!externalId) {
      return null;
    }

    const externalIdText = String(externalId);
    if (context.seenIds.has(externalIdText)) {
      return null;
    }

    const matchDate = extractDiscoveryDate(match);
    if (!matchDate || isOutsideDateWindow(matchDate, context.dateWindow)) {
      return null;
    }

    context.seenIds.add(externalIdText);

    const status = resolveStatus(match);
    return {
      match_id: buildDiscoveryMatchId(context.leagueId, context.season, externalIdText),
      external_id: externalIdText,
      league_name: context.leagueName,
      season: context.season,
      home_team: resolveTeamName(match, 'home'),
      away_team: resolveTeamName(match, 'away'),
      match_date: matchDate.toISOString(),
      status,
      is_finished: status === 'finished',
      data_source: this.dataSource,
      created_at: context.timestamp,
      updated_at: context.timestamp
    };
  }
}

module.exports = { DiscoveryAttributeMapper };
