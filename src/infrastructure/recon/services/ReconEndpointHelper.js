'use strict';

class ReconEndpointHelper {
  static hasMissingTournamentToken(url) {
    return typeof url === 'string' && url.includes('/1//X');
  }

  static repairArchiveEndpointWithTournamentToken(archiveEndpoint, tournamentToken) {
    if (
      typeof archiveEndpoint !== 'string'
      || typeof tournamentToken !== 'string'
      || tournamentToken.trim() === ''
      || !this.hasMissingTournamentToken(archiveEndpoint)
    ) {
      return archiveEndpoint;
    }

    return archiveEndpoint.replace('/1//X', `/1/${tournamentToken.trim()}/X`);
  }
}

module.exports = {
  ReconEndpointHelper
};
