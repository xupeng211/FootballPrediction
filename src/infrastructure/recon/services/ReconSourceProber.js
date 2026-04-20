'use strict';

const { reconSourceProberRouteFlow } = require('./ReconSourceProberRouteFlow');
const { reconSourceProberSearchFlow } = require('./ReconSourceProberSearchFlow');

const reconSourceProber = {
  ...reconSourceProberRouteFlow,
  ...reconSourceProberSearchFlow,

  async _selectCandidateSourceWithLocalFallback(target, pendingMatches, confidenceThreshold, navigator = null) {
    try {
      const selectedSource = await this._probeCandidateRoutes(
        target,
        pendingMatches,
        confidenceThreshold,
        navigator
      );
      const hasCandidates = Array.isArray(selectedSource?.candidates) && selectedSource.candidates.length > 0;
      if (hasCandidates || !this._canUseLocalDictionaryFallback(target, pendingMatches)) {
        return selectedSource;
      }

      this.logger.warn('recon_local_dictionary_fallback_armed', {
        league: target?.league?.name || null,
        season: target?.dbSeason || null,
        sourceState: selectedSource?.extractResult?.sourceState || 'SOURCE_EMPTY',
        routeKinds: selectedSource?.routeKinds || [],
        pendingTotal: pendingMatches.length
      });
      return this._buildLocalDictionarySelectedSource(target, pendingMatches, 'LOCAL_DICTIONARY_FALLBACK');
    } catch (error) {
      if (!this._canUseLocalDictionaryFallback(target, pendingMatches)) {
        throw error;
      }

      this.logger.warn('recon_local_dictionary_fallback_recovered', {
        league: target?.league?.name || null,
        season: target?.dbSeason || null,
        pendingTotal: pendingMatches.length,
        error: error.message
      });
      return this._buildLocalDictionarySelectedSource(target, pendingMatches, 'LOCAL_DICTIONARY_FALLBACK');
    }
  }
};

module.exports = { reconSourceProber };
