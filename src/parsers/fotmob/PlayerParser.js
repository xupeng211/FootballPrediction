'use strict';

function normalizePlayer(player, side = null) {
  if (!player || typeof player !== 'object') {
    return null;
  }

  return {
    id: player.id || player.playerId || null,
    name: player.name || player.fullName || player.playerName || null,
    side,
    position: player.position || player.role || null,
    rating: Number.isFinite(Number(player.rating)) ? Number(player.rating) : null,
    raw: player
  };
}

class PlayerParser {
  parsePlayers(rawData = {}) {
    const lineup = rawData.lineup || rawData.content?.lineup || rawData.lineups || {};
    const players = [];

    for (const side of ['home', 'away']) {
      const sideLineup = lineup[side] || lineup[`${side}Team`] || {};
      const starters = sideLineup.starters || sideLineup.lineup || sideLineup.players || [];
      const bench = sideLineup.bench || sideLineup.substitutes || [];

      for (const player of [...starters, ...bench]) {
        const normalized = normalizePlayer(player, side);
        if (normalized) {
          players.push(normalized);
        }
      }
    }

    return players;
  }
}

module.exports = { PlayerParser, normalizePlayer };
