'use strict';

const BOOKMAKER_ID_MAP = {
  PINNACLE: [18, 27, 'pinnacle', 'Pinnacle', 'PINNACLE'],
  BET365: [16, 'bet365', 'Bet365', 'BET365', '365'],
  BWIN: [1, 'bwin', 'Bwin', 'BWIN', 'bwin.com'],
  WILLIAM_HILL: [2, 'williamhill', 'William Hill', 'WilliamHill', 'WH', 'wh'],
  INTERTOPS: [3, 'interwetten', 'Interwetten', 'Intertops', 'intertops'],
  NAME_TO_KEY: {
    pinnacle: 'pinnacle',
    Pinnacle: 'pinnacle',
    PINNACLE: 'pinnacle',
    '18': 'pinnacle',
    '27': 'pinnacle',
    bet365: 'bet365',
    Bet365: 'bet365',
    BET365: 'bet365',
    '365': 'bet365',
    '16': 'bet365',
    bwin: 'bwin',
    Bwin: 'bwin',
    BWIN: 'bwin',
    'bwin.com': 'bwin',
    '1': 'bwin',
    williamhill: 'william_hill',
    'William Hill': 'william_hill',
    WilliamHill: 'william_hill',
    WH: 'william_hill',
    wh: 'william_hill',
    '2': 'william_hill',
    interwetten: 'intertops',
    Interwetten: 'intertops',
    intertops: 'intertops',
    Intertops: 'intertops',
    '3': 'intertops'
  },
  METADATA: {
    pinnacle: { id: 18, name: 'Pinnacle', tier: 'P0', priority: 1 },
    bet365: { id: 16, name: 'Bet365', tier: 'P0', priority: 2 },
    bwin: { id: 1, name: 'Bwin', tier: 'P1', priority: 3 },
    william_hill: { id: 2, name: 'William Hill', tier: 'P1', priority: 4 },
    intertops: { id: 3, name: 'Interwetten', tier: 'P1', priority: 5 }
  }
};

const ODDS_FIELD_PATTERNS = {
  OPENING: ['opening', 'initial', 'start', 'open', 'first', 'orig', 'original'],
  CLOSING: ['closing', 'current', 'last', 'final', 'end', 'now', 'latest'],
  HISTORY: ['history', 'movement', 'timeline', 'changes', 'trend', 'oddsHistory', 'priceHistory'],
  TIMESTAMP: ['timestamp', 'time', 'dat_h', 'date', 't', 'updated', 'created', 'ts']
};

function normalizeTimestampNumber(numericValue) {
  if (!Number.isFinite(numericValue)) {
    return null;
  }

  if (numericValue > 1000000000000) {
    return Math.floor(numericValue / 1000);
  }

  if (numericValue > 1000000000) {
    return Math.floor(numericValue);
  }

  return null;
}

function normalizeTimestampValue(value) {
  if (value === undefined || value === null) {
    return null;
  }

  if (typeof value === 'number') {
    return normalizeTimestampNumber(value);
  }

  const textValue = String(value).trim();
  if (!textValue) {
    return null;
  }

  if (/^\d+$/.test(textValue)) {
    return normalizeTimestampNumber(Number(textValue));
  }

  const parsed = Date.parse(textValue);
  return Number.isNaN(parsed) ? null : Math.floor(parsed / 1000);
}

function isObjectLike(value) {
  return Boolean(value) && typeof value === 'object';
}

function matchesTargetKey(key, targetKeys) {
  const lowerKey = key.toLowerCase();
  return targetKeys.some(targetKey => {
    const normalizedTarget = targetKey.toLowerCase();
    return lowerKey === normalizedTarget || lowerKey.includes(normalizedTarget);
  });
}

function findValuesByKey(obj, targetKeys, results = [], maxDepth = 10, currentDepth = 0, path = []) {
  if (currentDepth > maxDepth || !isObjectLike(obj)) {
    return results;
  }

  const keys = Array.isArray(targetKeys) ? targetKeys : [targetKeys];

  for (const [key, value] of Object.entries(obj)) {
    if (matchesTargetKey(key, keys)) {
      results.push({ key, value, depth: currentDepth, path: [...path, key] });
    }

    if (isObjectLike(value)) {
      findValuesByKey(value, targetKeys, results, maxDepth, currentDepth + 1, [...path, key]);
    }
  }

  return results;
}

function resolveBookmakerIdentifiers(bookieKey) {
  return bookieKey === 'pinnacle' ? BOOKMAKER_ID_MAP.PINNACLE : BOOKMAKER_ID_MAP.BET365;
}

function matchesBookmakerId(node, identifiers) {
  const id = node.id ?? node.providerId ?? node.bookieId ?? node.bid;
  if (id === undefined || id === null) {
    return false;
  }

  const idValue = String(id);
  return identifiers.some(target => idValue === String(target));
}

function matchesBookmakerName(node, identifiers) {
  const name = node.name ?? node.bookie ?? node.provider ?? node.label;
  if (!name) {
    return false;
  }

  const normalizedName = String(name).toLowerCase();
  return identifiers
    .filter(target => typeof target === 'string')
    .some(target => normalizedName.includes(target.toLowerCase()));
}

function findBookieById(obj, bookieKey) {
  const identifiers = resolveBookmakerIdentifiers(bookieKey);
  const stack = [{ value: obj, depth: 0 }];

  while (stack.length > 0) {
    const current = stack.pop();
    if (!current) {
      continue;
    }

    const { value, depth } = current;
    if (depth > 10 || !isObjectLike(value)) {
      continue;
    }

    if (!Array.isArray(value) && (matchesBookmakerId(value, identifiers) || matchesBookmakerName(value, identifiers))) {
      return value;
    }

    const nestedValues = Array.isArray(value) ? value : Object.values(value);
    for (let index = nestedValues.length - 1; index >= 0; index--) {
      stack.push({ value: nestedValues[index], depth: depth + 1 });
    }
  }

  return null;
}

function parseOddsNumber(value) {
  const parsed = parseFloat(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function isValidOddsTriplet(odds) {
  return Array.isArray(odds) && odds.length === 3 && odds.every(num => Number.isFinite(num) && num > 1 && num < 100);
}

function normalizeArrayOdds(candidate) {
  if (!Array.isArray(candidate) || candidate.length < 3) {
    return null;
  }

  const odds = candidate.slice(0, 3).map(parseOddsNumber);
  return isValidOddsTriplet(odds) ? odds : null;
}

function normalizeObjectOdds(candidate) {
  if (!isObjectLike(candidate) || Array.isArray(candidate)) {
    return null;
  }

  const values = [
    candidate.home ?? candidate[0] ?? candidate.h,
    candidate.draw ?? candidate[1] ?? candidate.d,
    candidate.away ?? candidate[2] ?? candidate.a
  ];

  return values.some(value => value === undefined) ? null : normalizeArrayOdds(values);
}

function normalizeOddsTriplet(candidate) {
  if (Array.isArray(candidate)) {
    return normalizeArrayOdds(candidate);
  }

  if (isObjectLike(candidate)) {
    return normalizeObjectOdds(candidate);
  }

  return null;
}

function validatePurity(odds, options = {}) {
  const errors = [];
  const {
    minOdds = 1.01,
    maxOdds = 99.99,
    requireLength = 3,
    strictMode = true
  } = options;

  if (!Array.isArray(odds)) {
    errors.push('赔率数据必须是数组');
    return { valid: false, errors, purity_score: 0 };
  }

  if (odds.length !== requireLength) {
    errors.push(`赔率数组长度必须为${requireLength}，当前为${odds.length}`);
    return { valid: false, errors, purity_score: 0 };
  }

  let validCount = 0;
  for (let index = 0; index < odds.length; index++) {
    const num = parseFloat(odds[index]);

    if (Number.isNaN(num)) {
      errors.push(`位置${index}的值不是有效数字: ${odds[index]}`);
      continue;
    }

    if (num < minOdds || num > maxOdds) {
      errors.push(`位置${index}的数值越界: ${num} (允许范围: ${minOdds}-${maxOdds})`);
      continue;
    }

    validCount++;
  }

  const purity_score = Math.round((validCount / requireLength) * 100);
  if (strictMode && errors.length > 0) {
    return {
      valid: false,
      errors,
      purity_score,
      _rejected: true,
      _rejection_reason: errors.join('; ')
    };
  }

  return {
    valid: errors.length === 0,
    errors,
    purity_score,
    normalized_odds: odds.map(value => parseFloat(value))
  };
}

function calculatePointMovement(previousOdds, currentOdds) {
  const homeChange = Math.abs(currentOdds[0] - previousOdds[0]);
  const drawChange = Math.abs(currentOdds[1] - previousOdds[1]);
  const awayChange = Math.abs(currentOdds[2] - previousOdds[2]);

  return {
    homeChange,
    drawChange,
    awayChange,
    relativeChange: (
      (homeChange / previousOdds[0]) +
      (drawChange / previousOdds[1]) +
      (awayChange / previousOdds[2])
    ) / 3
  };
}

function calculateVolatilityMetrics(history) {
  if (!Array.isArray(history) || history.length < 2) {
    return {
      volatility_index: 0,
      max_home_movement: 0,
      max_draw_movement: 0,
      max_away_movement: 0,
      total_movement_count: Array.isArray(history) ? history.length : 0
    };
  }

  let volatilitySum = 0;
  let maxHomeMove = 0;
  let maxDrawMove = 0;
  let maxAwayMove = 0;

  for (let index = 1; index < history.length; index++) {
    const movement = calculatePointMovement(history[index - 1].o, history[index].o);
    maxHomeMove = Math.max(maxHomeMove, movement.homeChange);
    maxDrawMove = Math.max(maxDrawMove, movement.drawChange);
    maxAwayMove = Math.max(maxAwayMove, movement.awayChange);
    volatilitySum += movement.relativeChange;
  }

  const volatilityIndex = (volatilitySum / (history.length - 1)) * 100;
  return {
    volatility_index: parseFloat(volatilityIndex.toFixed(4)),
    max_home_movement: parseFloat(maxHomeMove.toFixed(4)),
    max_draw_movement: parseFloat(maxDrawMove.toFixed(4)),
    max_away_movement: parseFloat(maxAwayMove.toFixed(4)),
    total_movement_count: history.length
  };
}

function extractOddsArray(results) {
  if (!Array.isArray(results) || results.length === 0) {
    return null;
  }

  for (const result of results) {
    const odds = normalizeOddsTriplet(result.value);
    if (odds) {
      return odds;
    }
  }

  return null;
}

function extractOddsArrays(obj, result = { rawArrays: [] }, depth = 0, path = '') {
  if (depth > 15 || !isObjectLike(obj)) {
    return result;
  }

  for (const [key, value] of Object.entries(obj)) {
    const currentPath = path ? `${path}.${key}` : key;
    const odds = Array.isArray(value) ? normalizeOddsTriplet(value) : null;

    if (odds) {
      result.rawArrays.push({
        path: currentPath,
        values: odds,
        depth
      });
    }

    if (isObjectLike(value)) {
      extractOddsArrays(value, result, depth + 1, currentPath);
    }
  }

  return result;
}

module.exports = {
  BOOKMAKER_ID_MAP,
  ODDS_FIELD_PATTERNS,
  calculateVolatilityMetrics,
  extractOddsArray,
  extractOddsArrays,
  findBookieById,
  findValuesByKey,
  isObjectLike,
  normalizeOddsTriplet,
  normalizeTimestampValue,
  validatePurity
};
