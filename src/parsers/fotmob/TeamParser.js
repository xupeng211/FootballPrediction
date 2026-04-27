'use strict';

function normalizeTeam(team, side) {
  if (!team || typeof team !== 'object') {
    return null;
  }

  return {
    side,
    id: team.id || team.teamId || team.fotmobId || null,
    name: team.name || team.teamName || team.shortName || null,
    score: Number.isFinite(Number(team.score)) ? Number(team.score) : null,
    raw: team
  };
}

class TeamParser {
  parseTeams(rawData = {}) {
    const general = rawData.general || rawData.content?.general || {};
    const header = rawData.header || rawData.content?.header || {};
    const home = general.homeTeam || header.homeTeam || header.teams?.[0] || rawData.home || null;
    const away = general.awayTeam || header.awayTeam || header.teams?.[1] || rawData.away || null;

    return [normalizeTeam(home, 'home'), normalizeTeam(away, 'away')].filter(Boolean);
  }
}

module.exports = { TeamParser, normalizeTeam };
