'use strict';

const {
  deepParseOddsData,
  processOddsTimeline,
  recursiveHistoryScanner
} = require('../shared/helpers/oddsPortalTimeline');
const {
  BOOKMAKER_ID_MAP,
  ODDS_FIELD_PATTERNS,
  calculateVolatilityMetrics,
  extractOddsArrays,
  findBookieById,
  findValuesByKey,
  validatePurity
} = require('../shared/helpers/oddsPortalShared');
const { extractOddsFromDOM } = require('../shared/helpers/oddsPortalDom');
const { buildMarketSentiment } = require('../shared/helpers/oddsPortalMarketSentiment');
const { OddsPortalURLParser } = require('../shared/helpers/OddsPortalURLParser');

module.exports = {
  recursiveHistoryScanner,
  processOddsTimeline,
  deepParseOddsData,
  validatePurity,
  calculateVolatilityMetrics,
  extractOddsFromDOM,
  buildMarketSentiment,
  extractOddsArrays,
  OddsPortalURLParser,
  findValuesByKey,
  findBookieById,
  BOOKMAKER_ID_MAP,
  ODDS_FIELD_PATTERNS
};
