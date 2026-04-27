'use strict';

const { transformToApiFormat } = require('./NextDataParser');
const { TeamParser } = require('./TeamParser');

function firstValue(values, fallback = null) {
  return values.find(value => value !== undefined && value !== null && value !== '') ?? fallback;
}

class MatchParser {
  constructor(options = {}) {
    this.teamParser = options.teamParser || new TeamParser();
  }

  parseMatch(rawData = {}, context = {}) {
    const data = rawData?.props?.pageProps
      ? transformToApiFormat(rawData, context.matchId || context.externalId)
      : rawData;
    const general = firstValue([data?.general, data?.content?.general], {});
    const header = firstValue([data?.header, data?.content?.header], {});

    return {
      matchId: firstValue([data?.matchId, general.matchId, header.matchId, context.matchId]),
      externalId: firstValue([context.externalId, data?.externalId, data?.matchId]),
      status: firstValue([general.status, header.status, data?.status]),
      startTime: firstValue([general.matchTimeUTC, header.matchTimeUTC, header.timeUTC, data?.matchTimeUTC]),
      teams: this.teamParser.parseTeams(data),
      raw: data
    };
  }
}

module.exports = { MatchParser, firstValue };
