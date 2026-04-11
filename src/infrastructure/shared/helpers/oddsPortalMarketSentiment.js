'use strict';

const {
  BOOKMAKER_ID_MAP,
  calculateVolatilityMetrics,
  validatePurity
} = require('./oddsPortalShared');
const {
  extractClosingOdds,
  extractOpeningOdds
} = require('./oddsPortalTimeline');

function resolveHistoryType(index, length) {
  if (index === 0) {
    return 'OPEN';
  }

  return index === length - 1 ? 'CLOSE' : 'MOVE';
}

function normalizeHistoryEntry(entry) {
  if (!entry || typeof entry !== 'object') {
    return null;
  }

  const candidateOdds = entry.o ?? entry.odds ?? (
    entry.home !== undefined ? [entry.home, entry.draw, entry.away] : null
  );
  const validation = validatePurity(candidateOdds, { strictMode: false });
  if (!validation.valid) {
    return null;
  }

  return {
    t: entry.ts ?? entry.t ?? entry.timestamp,
    o: validation.normalized_odds
  };
}

function buildApiHistory(bookieData) {
  const sourceEntries = Array.isArray(bookieData?.history) && bookieData.history.length > 0
    ? bookieData.history
    : Array.isArray(bookieData?.movement)
      ? bookieData.movement
      : [];

  const normalizedEntries = sourceEntries
    .map(normalizeHistoryEntry)
    .filter(Boolean);

  return normalizedEntries.map((entry, index, list) => ({
    t: entry.t,
    o: entry.o,
    type: resolveHistoryType(index, list.length)
  }));
}

function logSnapshotSource(bookieKey, label, snapshot) {
  if (snapshot?.source) {
    console.log(`[${bookieKey}] ${label}来源: ${snapshot.source}`);
  }
}

function buildApiPayload(bookieData, bookieKey) {
  const opening = extractOpeningOdds(bookieData, bookieKey);
  const closing = extractClosingOdds(bookieData, bookieKey);
  const history = buildApiHistory(bookieData);
  const isComplete = Boolean(bookieData?._is_premium || (opening && closing && opening.source !== 'history_first'));

  logSnapshotSource(bookieKey, '初赔', opening);
  logSnapshotSource(bookieKey, '终赔', closing);

  return {
    opening,
    closing,
    history,
    sourceChannel: bookieData?._detected_channel || 'api',
    isComplete,
    dataQuality: isComplete ? 'PREMIUM-GOLD' : 'STANDARD',
    isPremium: Boolean(bookieData?._is_premium)
  };
}

function buildFallbackPayload(fallbackData, strictValidation) {
  const validation = validatePurity(fallbackData, { strictMode: strictValidation });
  if (!validation.valid) {
    return null;
  }

  const timestamp = Math.floor(Date.now() / 1000);
  return {
    opening: null,
    closing: { o: validation.normalized_odds, t: timestamp },
    history: [{ t: timestamp, o: validation.normalized_odds, type: 'CLOSE' }],
    sourceChannel: 'dom_fallback',
    isComplete: false,
    dataQuality: 'PARTIAL',
    isPremium: false
  };
}

function ensureOpening(payload) {
  if (payload.opening) {
    return payload.opening;
  }

  if (payload.history.length > 0) {
    return {
      o: payload.history[0].o,
      t: payload.history[0].t
    };
  }

  return payload.closing;
}

function calculatePurityScore(payload) {
  let purityScore = 100;

  if (!payload.isComplete) {
    purityScore -= 20;
  }

  if (payload.history.length < 3) {
    purityScore -= 10;
  }

  if (payload.dataQuality === 'PARTIAL') {
    purityScore -= 15;
  }

  return Math.max(0, purityScore);
}

function buildBookieStructure(bookieData, bookieKey, fallbackData, extractionTimestamp, strictValidation) {
  if (!bookieData && !fallbackData) {
    return null;
  }

  const meta = BOOKMAKER_ID_MAP.METADATA[bookieKey];
  if (!meta) {
    return null;
  }

  const payload = bookieData
    ? buildApiPayload(bookieData, bookieKey)
    : buildFallbackPayload(fallbackData, strictValidation);

  if (!payload || !payload.closing) {
    return null;
  }

  const opening = ensureOpening(payload);
  const volatility = calculateVolatilityMetrics(payload.history);

  return {
    bookmaker_id: meta.id,
    bookmaker_name: meta.name,
    tier: meta.tier,
    opening,
    closing: payload.closing,
    movement: {
      history: payload.history,
      point_count: payload.history.length,
      ...volatility
    },
    metadata: {
      purity_score: calculatePurityScore(payload),
      source_channel: payload.sourceChannel,
      extraction_timestamp: extractionTimestamp,
      data_quality: payload.dataQuality,
      is_complete: payload.isComplete
    }
  };
}

function calculateOverallPurity(ms, validBookmakerCount) {
  if (validBookmakerCount === 0) {
    return 0;
  }

  const totalPurity = Object.values(ms)
    .filter(value => value && value.metadata)
    .reduce((sum, value) => sum + value.metadata.purity_score, 0);

  return Math.round(totalPurity / validBookmakerCount);
}

function attachBookmaker(ms, key, apiValue, fallbackValue, context) {
  const structured = buildBookieStructure(
    apiValue,
    key,
    fallbackValue,
    context.extractionTimestamp,
    context.strictValidation
  );

  if (!structured) {
    return;
  }

  ms[key] = structured;
  context.validBookmakerCount += 1;

  if (apiValue?._is_premium) {
    context.premiumCount += 1;
  }
}

function buildMarketSentiment(apiResult, domResult, options = {}) {
  const extractionTimestamp = new Date().toISOString();
  const { strictValidation = true } = options;
  const context = {
    extractionTimestamp,
    premiumCount: 0,
    strictValidation,
    validBookmakerCount: 0
  };

  const marketSentiment = {
    _schema_version: 'V6.0-ULTIMATE',
    _extract_timestamp: extractionTimestamp,
    extract_method: 'ODDS_PORTAL_API_DECRYPT_V6.0',
    source: 'oddsportal_api_decrypt',
    _apiDecrypt: true
  };

  const primaryBookmakers = [
    { key: 'pinnacle', api: apiResult?.pinnacle, fallback: domResult?.pinnacleOdds },
    { key: 'bet365', api: apiResult?.bet365, fallback: domResult?.bet365Odds }
  ];

  for (const bookmaker of primaryBookmakers) {
    attachBookmaker(marketSentiment, bookmaker.key, bookmaker.api, bookmaker.fallback, context);
  }

  const secondaryBookmakers = [
    { key: 'bwin', api: apiResult?.bwin },
    { key: 'william_hill', api: apiResult?.william_hill }
  ];

  for (const bookmaker of secondaryBookmakers) {
    attachBookmaker(marketSentiment, bookmaker.key, bookmaker.api, null, context);
  }

  marketSentiment._summary = {
    total_bookmakers: context.validBookmakerCount,
    premium_gold_count: context.premiumCount,
    has_p0_data: Boolean(marketSentiment.pinnacle || marketSentiment.bet365),
    overall_purity: calculateOverallPurity(marketSentiment, context.validBookmakerCount),
    data_completeness: context.validBookmakerCount > 0 ? 'high' : 'none'
  };

  return marketSentiment;
}

module.exports = {
  buildMarketSentiment
};
