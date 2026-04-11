'use strict';

const {
  BOOKMAKER_ID_MAP,
  ODDS_FIELD_PATTERNS,
  calculateVolatilityMetrics,
  findBookieById,
  isObjectLike,
  normalizeOddsTriplet,
  normalizeTimestampValue,
  validatePurity
} = require('./oddsPortalShared');

const OPENING_ALIAS_FIELDS = [
  { field: 'initial', timestampField: 'initial_at', source: 'initial_field' },
  { field: 'start', timestampField: 'start_at', source: 'start_field' },
  { field: 'first', timestampField: 'first_at', source: 'first_field' },
  { field: 'orig', timestampField: 'orig_at', source: 'orig_field' },
  { field: 'original', timestampField: 'original_at', source: 'original_field' }
];

function buildHistoryPoint(odds, path, type, timestamp = null) {
  const point = { o: odds, path, _type: type };
  if (timestamp !== null) {
    point.ts = timestamp;
  }
  return point;
}

function findSiblingTimestamp(container) {
  if (!isObjectLike(container)) {
    return null;
  }

  for (const [key, value] of Object.entries(container)) {
    const lowerKey = key.toLowerCase();
    const hasTimestampHint = ODDS_FIELD_PATTERNS.TIMESTAMP.some(pattern => lowerKey.includes(pattern.toLowerCase()));
    if (!hasTimestampHint) {
      continue;
    }

    const timestamp = normalizeTimestampValue(value);
    if (timestamp) {
      return timestamp;
    }
  }

  return null;
}

function collectRootOddsArrayPoint(obj, path, results) {
  if (!path || !Array.isArray(obj)) {
    return;
  }

  const odds = normalizeOddsTriplet(obj);
  if (!odds) {
    return;
  }

  results.push(buildHistoryPoint(odds, path, 'raw_odds_array'));
}

function collectSiblingOddsPoint(container, value, currentPath, results) {
  if (!Array.isArray(value)) {
    return;
  }

  const odds = normalizeOddsTriplet(value);
  if (!odds) {
    return;
  }

  const timestamp = findSiblingTimestamp(container);
  results.push(buildHistoryPoint(odds, currentPath, timestamp ? 'timestamped_odds' : 'odds_only', timestamp));
}

function collectStructuredOddsPoint(value, currentPath, results) {
  if (!isObjectLike(value) || Array.isArray(value)) {
    return;
  }

  const odds = normalizeOddsTriplet(value.o ?? value.odds ?? value.price);
  if (!odds) {
    return;
  }

  const timestamp = normalizeTimestampValue(value.t ?? value.ts ?? value.timestamp ?? value.time ?? value.dat_h);
  if (timestamp) {
    results.push(buildHistoryPoint(odds, currentPath, 'structured_odds', timestamp));
  }
}

function isHistoryArrayItem(item) {
  if (!isObjectLike(item)) {
    return false;
  }

  const odds = normalizeOddsTriplet(item.o ?? item.odds ?? (Array.isArray(item) ? item : null));
  const hasTimestamp = [item.t, item.ts, item.timestamp, item.time, item.dat_h].some(value => value !== undefined);
  return Boolean(odds || hasTimestamp);
}

function collectHistoryArrayPoints(history, currentPath, results) {
  if (!Array.isArray(history) || history.length === 0 || !history.every(isHistoryArrayItem)) {
    return;
  }

  history.forEach((item, index) => {
    const odds = normalizeOddsTriplet(item.o ?? item.odds ?? item);
    const timestamp = normalizeTimestampValue(item.t ?? item.ts ?? item.timestamp ?? item.time ?? item.dat_h);
    if (odds && timestamp) {
      results.push(buildHistoryPoint(odds, `${currentPath}[${index}]`, 'history_array_item', timestamp));
    }
  });
}

function recursiveHistoryScanner(obj, results = [], maxDepth = 15, currentDepth = 0, path = '') {
  if (currentDepth > maxDepth || !isObjectLike(obj)) {
    return results;
  }

  collectRootOddsArrayPoint(obj, path, results);

  for (const [key, value] of Object.entries(obj)) {
    const currentPath = path ? `${path}.${key}` : key;
    collectSiblingOddsPoint(obj, value, currentPath, results);
    collectStructuredOddsPoint(value, currentPath, results);
    collectHistoryArrayPoints(value, currentPath, results);

    if (isObjectLike(value) && !Array.isArray(value)) {
      recursiveHistoryScanner(value, results, maxDepth, currentDepth + 1, currentPath);
    }
  }

  return results;
}

function dedupeTimelinePoints(points) {
  const uniquePoints = [];
  let lastTimestamp = 0;

  for (const point of points) {
    if (point.ts === lastTimestamp) {
      continue;
    }

    uniquePoints.push(point);
    lastTimestamp = point.ts;
  }

  return uniquePoints;
}

function buildOddsOnlyTimeline(historyPoints) {
  const oddsOnlyPoints = historyPoints.filter(point => point.o !== undefined);
  if (oddsOnlyPoints.length === 0) {
    return null;
  }

  return {
    opening: oddsOnlyPoints[0].o,
    closing: oddsOnlyPoints[oddsOnlyPoints.length - 1].o,
    history: oddsOnlyPoints.map(point => ({ o: point.o })),
    volatility_index: 0,
    last_changed_at: null,
    _point_count: oddsOnlyPoints.length,
    _is_premium: oddsOnlyPoints.length >= 3
  };
}

function buildTimestampedTimeline(points) {
  const volatility = calculateVolatilityMetrics(points);
  return {
    opening: points[0].o,
    closing: points[points.length - 1].o,
    history: points.map(point => ({ ts: point.ts, o: point.o })),
    volatility_index: volatility.volatility_index,
    last_changed_at: points[points.length - 1].ts,
    opening_at: points[0].ts,
    _point_count: points.length,
    _is_premium: points.length >= 3
  };
}

function processOddsTimeline(historyPoints) {
  if (!Array.isArray(historyPoints) || historyPoints.length === 0) {
    return null;
  }

  const timestampedPoints = historyPoints
    .filter(point => point.ts !== undefined)
    .sort((left, right) => left.ts - right.ts);

  const uniquePoints = dedupeTimelinePoints(timestampedPoints);
  return uniquePoints.length > 0 ? buildTimestampedTimeline(uniquePoints) : buildOddsOnlyTimeline(historyPoints);
}

function resolveTimestamp(values, fallback = Date.now()) {
  const candidate = values.find(value => value !== undefined && value !== null);
  return candidate ?? fallback;
}

function buildSnapshot(odds, timestamp, source) {
  return odds ? { o: odds, t: timestamp, source } : null;
}

function extractSnapshotFromNamedObject(bookieData, fieldName, source, timestampValues = []) {
  const candidate = bookieData?.[fieldName];
  if (!isObjectLike(candidate) || Array.isArray(candidate)) {
    return null;
  }

  const odds = normalizeOddsTriplet(candidate);
  return buildSnapshot(odds, resolveTimestamp([candidate.timestamp, candidate.ts, ...timestampValues]), source);
}

function extractSnapshotFromArrayField(bookieData, fieldName, source, timestampValues = []) {
  const odds = normalizeOddsTriplet(bookieData?.[fieldName]);
  return buildSnapshot(odds, resolveTimestamp(timestampValues), source);
}

function extractSnapshotFromHistory(bookieData, source, position) {
  const history = bookieData?.history ?? bookieData?.movement;
  if (!Array.isArray(history) || history.length === 0) {
    return null;
  }

  const entry = position === 'last' ? history[history.length - 1] : history[0];
  const odds = normalizeOddsTriplet(entry?.o ?? entry?.odds ?? entry);
  return buildSnapshot(odds, resolveTimestamp([entry?.timestamp, entry?.t, entry?.ts]), source);
}

function extractSnapshotFromNestedOdds(bookieData, nestedField, source) {
  const oddsNode = bookieData?.odds?.[nestedField];
  if (!isObjectLike(oddsNode) || Array.isArray(oddsNode)) {
    return null;
  }

  const odds = normalizeOddsTriplet(oddsNode);
  return buildSnapshot(odds, resolveTimestamp([oddsNode.timestamp, oddsNode.ts]), source);
}

function extractSnapshotFromAliases(bookieData, aliasFields) {
  for (const alias of aliasFields) {
    const candidate = bookieData?.[alias.field];
    const odds = normalizeOddsTriplet(candidate);
    if (odds) {
      return buildSnapshot(odds, resolveTimestamp([bookieData?.[alias.timestampField]]), alias.source);
    }
  }

  return null;
}

function finalizeSnapshot(snapshot, bookieKey, strictMode, label) {
  if (!snapshot) {
    return null;
  }

  const validation = validatePurity(snapshot.o, { strictMode });
  if (!validation.valid) {
    console.warn(`[${bookieKey}] ${label}纯度验证失败:`, validation._rejection_reason || validation.errors?.join('; '));
    return null;
  }

  return {
    ...snapshot,
    o: validation.normalized_odds
  };
}

function runSnapshotExtractors(extractors) {
  for (const extract of extractors) {
    const snapshot = extract();
    if (snapshot) {
      return snapshot;
    }
  }

  return null;
}

function extractOpeningOdds(bookieData, bookieKey) {
  if (!isObjectLike(bookieData)) {
    return null;
  }

  const snapshot = runSnapshotExtractors([
    () => extractSnapshotFromNamedObject(bookieData, 'opening', 'opening_object', [bookieData?.opening_at]),
    () => extractSnapshotFromArrayField(bookieData, 'opening', 'opening_array', [bookieData?.opening_at, bookieData?.first_seen_at]),
    () => extractSnapshotFromHistory(bookieData, 'history_first', 'first'),
    () => extractSnapshotFromNestedOdds(bookieData, 'opening', 'odds.opening'),
    () => extractSnapshotFromAliases(bookieData, OPENING_ALIAS_FIELDS)
  ]);

  return finalizeSnapshot(snapshot, bookieKey, false, '初赔');
}

function extractClosingOdds(bookieData, bookieKey) {
  if (!isObjectLike(bookieData)) {
    return null;
  }

  const snapshot = runSnapshotExtractors([
    () => extractSnapshotFromNamedObject(bookieData, 'current', 'current_object', [bookieData?.last_changed_at]),
    () => extractSnapshotFromNamedObject(bookieData, 'closing', 'closing_object', [bookieData?.last_changed_at]),
    () => extractSnapshotFromArrayField(bookieData, 'current', 'current_array', [bookieData?.last_changed_at]),
    () => extractSnapshotFromArrayField(bookieData, 'closing', 'closing_array', [bookieData?.last_changed_at]),
    () => extractSnapshotFromHistory(bookieData, 'history_last', 'last'),
    () => extractSnapshotFromNestedOdds(bookieData, 'current', 'odds.current')
  ]);

  return finalizeSnapshot(snapshot, bookieKey, true, '终赔');
}

function buildFallbackPoint(snapshot) {
  const timestamp = normalizeTimestampValue(snapshot?.t);
  return snapshot?.o ? (timestamp ? { ts: timestamp, o: snapshot.o } : { o: snapshot.o }) : null;
}

function shouldAppendSnapshot(previousSnapshot, nextSnapshot) {
  if (!nextSnapshot?.o) {
    return false;
  }

  if (!previousSnapshot?.o) {
    return true;
  }

  const oddsChanged = JSON.stringify(previousSnapshot.o) !== JSON.stringify(nextSnapshot.o);
  const timestampChanged = normalizeTimestampValue(previousSnapshot.t) !== normalizeTimestampValue(nextSnapshot.t);
  return oddsChanged || timestampChanged;
}

function buildFallbackHistory(openingFallback, closingFallback) {
  const fallbackHistory = [];
  const openingPoint = buildFallbackPoint(openingFallback);

  if (openingPoint) {
    fallbackHistory.push(openingPoint);
  }

  if (shouldAppendSnapshot(openingFallback, closingFallback)) {
    const closingPoint = buildFallbackPoint(closingFallback);
    if (closingPoint) {
      fallbackHistory.push(closingPoint);
    }
  }

  return fallbackHistory;
}

function buildBookmakerPayload(bookieData, bookieKey, bookmakerId) {
  if (!bookieData) {
    return null;
  }

  const timeline = processOddsTimeline(recursiveHistoryScanner(bookieData));
  const openingFallback = extractOpeningOdds(bookieData, bookieKey);
  const closingFallback = extractClosingOdds(bookieData, bookieKey);
  const openingAt = normalizeTimestampValue(openingFallback?.t);
  const lastChangedAt = normalizeTimestampValue(closingFallback?.t);
  const fallbackHistory = buildFallbackHistory(openingFallback, closingFallback);

  return {
    detected: true,
    bookmaker_id: bookmakerId,
    opening: timeline?.opening ?? openingFallback?.o ?? null,
    closing: timeline?.closing ?? closingFallback?.o ?? openingFallback?.o ?? null,
    history: timeline?.history ?? fallbackHistory,
    volatility_index: timeline?.volatility_index ?? 0,
    last_changed_at: timeline?.last_changed_at ?? lastChangedAt,
    opening_at: timeline?.opening_at ?? openingAt,
    _point_count: timeline?._point_count ?? fallbackHistory.length,
    _is_premium: timeline?._is_premium ?? fallbackHistory.length >= 3
  };
}

function deepParseOddsData(apiData) {
  const result = {
    pinnacle: null,
    bet365: null,
    raw: apiData,
    _apiDecrypt: true,
    _apiExcavator: true,
    _version: 'V6.0-DECRYPT'
  };

  if (!isObjectLike(apiData)) {
    return result;
  }

  const bookmakerConfigs = [
    { key: 'pinnacle', id: BOOKMAKER_ID_MAP.METADATA.pinnacle.id },
    { key: 'bet365', id: BOOKMAKER_ID_MAP.METADATA.bet365.id }
  ];

  for (const config of bookmakerConfigs) {
    result[config.key] = buildBookmakerPayload(findBookieById(apiData, config.key), config.key, config.id);
  }

  return result;
}

module.exports = {
  deepParseOddsData,
  extractClosingOdds,
  extractOpeningOdds,
  processOddsTimeline,
  recursiveHistoryScanner
};
