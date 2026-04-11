'use strict';

const {
  getDiscoveryExternalId,
  hasDiscoveryTeams,
  safeJsonPreview
} = require('../shared/helpers/discoveryParserShared');

const GREEDY_CONTAINER_KEYS = new Set([
  'matches',
  'fixtures',
  'games',
  'events',
  'allMatches',
  'leagueMatches',
  'schedule',
  'results'
]);
const GREEDY_THRESHOLD = 10;

function isObjectLike(value) {
  return Boolean(value) && typeof value === 'object';
}

function flattenContainerMatches(containers, arrayKeys) {
  const matches = [];

  for (const container of Array.isArray(containers) ? containers : []) {
    for (const key of arrayKeys) {
      if (Array.isArray(container?.[key])) {
        matches.push(...container[key]);
        break;
      }
    }
  }

  return matches;
}

function flattenGroupedMatches(groupedMatches) {
  const matches = [];
  let groupCount = 0;

  for (const value of Object.values(groupedMatches || {})) {
    if (Array.isArray(value) && value.length > 0 && value[0]?.id) {
      groupCount += 1;
      matches.push(...value);
    }
  }

  return { matches, groupCount };
}

function appendUniqueMatches(items, state) {
  for (const item of Array.isArray(items) ? items : []) {
    if (!state.isMatchObject(item)) {
      continue;
    }

    const id = getDiscoveryExternalId(item);
    if (!id) {
      continue;
    }

    const idText = String(id);
    if (state.seenIds.has(idText)) {
      continue;
    }

    state.seenIds.add(idText);
    state.matches.push(item);
  }
}

function scanArrayNode(items, depth, state) {
  for (const item of items) {
    if (state.isMatchObject(item)) {
      appendUniqueMatches([item], state);
      continue;
    }

    scanDeeply(item, depth + 1, state);
  }
}

function scanDeeply(node, depth, state) {
  if (depth > 3 || !isObjectLike(node)) {
    return;
  }

  if (Array.isArray(node)) {
    scanArrayNode(node, depth, state);
    return;
  }

  for (const [key, value] of Object.entries(node)) {
    if (GREEDY_CONTAINER_KEYS.has(key) && Array.isArray(value)) {
      appendUniqueMatches(value, state);
      continue;
    }

    scanDeeply(value, depth + 1, state);
  }
}

function resolveKnownPath(response) {
  if (Array.isArray(response?.weeksWithMatches)) {
    return {
      matches: flattenContainerMatches(response.weeksWithMatches, ['matches']),
      logMessage: `[PARSER] 路径W: weeksWithMatches 扁平化合并 (${response.weeksWithMatches.length} 周)`
    };
  }

  if (Array.isArray(response?.weeks)) {
    return {
      matches: flattenContainerMatches(response.weeks, ['matches', 'fixtures']),
      logMessage: `[PARSER] 路径W: weeks 扁平化合并 (${response.weeks.length} 周)`
    };
  }

  if (Array.isArray(response?.rounds)) {
    return {
      matches: flattenContainerMatches(response.rounds, ['matches', 'fixtures']),
      logMessage: `[PARSER] 路径R: rounds 扁平化合并 (${response.rounds.length} 轮)`
    };
  }

  if (Array.isArray(response?.fixtures?.allMatches)) {
    return {
      matches: response.fixtures.allMatches,
      logMessage: `[PARSER] 路径E: fixtures.allMatches (${response.fixtures.allMatches.length} 场)`
    };
  }

  if (Array.isArray(response?.fixtures)) {
    return {
      matches: response.fixtures,
      logMessage: `[PARSER] 路径F: fixtures[] (${response.fixtures.length} 场)`
    };
  }

  if (isObjectLike(response?.fixtures)) {
    const groupedFixtures = flattenGroupedMatches(response.fixtures);
    return groupedFixtures.groupCount > 0
      ? {
        matches: groupedFixtures.matches,
        logMessage: `[PARSER] 路径G: fixtures 分组 (${groupedFixtures.groupCount} 轮, ${groupedFixtures.matches.length} 场)`
      }
      : { matches: [] };
  }

  if (Array.isArray(response?.matches?.allMatches)) {
    return {
      matches: response.matches.allMatches,
      logMessage: `[PARSER] 路径A: matches.allMatches (${response.matches.allMatches.length} 场)`
    };
  }

  if (Array.isArray(response?.matches)) {
    return {
      matches: response.matches,
      logMessage: `[PARSER] 路径B: matches[] (${response.matches.length} 场)`
    };
  }

  if (isObjectLike(response?.matches)) {
    const groupedMatches = flattenGroupedMatches(response.matches);
    return groupedMatches.groupCount > 0
      ? {
        matches: groupedMatches.matches,
        logMessage: `[PARSER] 路径C: matches 分组 (${groupedMatches.groupCount} 轮, ${groupedMatches.matches.length} 场)`
      }
      : { matches: [] };
  }

  if (Array.isArray(response)) {
    return {
      matches: response,
      logMessage: `[PARSER] 路径D: response[] (${response.length} 场)`
    };
  }

  return { matches: [] };
}

class DiscoveryDataValidator {
  constructor(options = {}) {
    this.logger = options.logger || console;
  }

  extractRawMatches(response) {
    if (!isObjectLike(response)) {
      return [];
    }

    const { matches, logMessage } = resolveKnownPath(response);
    if (logMessage) {
      this.logger.info(logMessage);
    }

    if (matches.length >= GREEDY_THRESHOLD) {
      return matches;
    }

    this.logger.info(`[PARSER] 触发贪婪搜索 (当前仅 ${matches.length} 场)...`);
    const greedyMatches = this.greedyScan(response);
    if (greedyMatches.length > matches.length) {
      this.logger.info(`[PARSER] 贪婪搜索发现 ${greedyMatches.length} 场，覆盖标准路径`);
      return greedyMatches;
    }

    return matches;
  }

  greedyScan(response) {
    const state = {
      matches: [],
      seenIds: new Set(),
      isMatchObject: (item) => this.isMatchObject(item)
    };

    if (Array.isArray(response?.weeksWithMatches)) {
      this.logger.info('[PARSER-GREEDY] 发现 weeksWithMatches，执行扁平化合并...');
      for (const week of response.weeksWithMatches) {
        appendUniqueMatches(week?.matches, state);
      }
    }

    if (Array.isArray(response?.rounds)) {
      this.logger.info('[PARSER-GREEDY] 发现 rounds，执行扁平化合并...');
      for (const round of response.rounds) {
        appendUniqueMatches(round?.matches, state);
      }
    }

    scanDeeply(response, 0, state);
    return state.matches;
  }

  isMatchObject(obj) {
    return isObjectLike(obj)
      && Boolean(getDiscoveryExternalId(obj))
      && hasDiscoveryTeams(obj);
  }

  diagnoseEmptyResponse(response) {
    const keys = isObjectLike(response) ? Object.keys(response) : [];
    const preview = safeJsonPreview(response);

    this.logger.warn(`[PARSER-DEBUG] 未找到比赛数据! Keys: [${keys.join(', ')}]`);
    this.logger.warn(`[PARSER-DEBUG] 预览: ${preview}...`);

    if (Array.isArray(response?.allAvailableSeasons)) {
      this.logger.info(`[PARSER-DEBUG] 💡 该联赛支持的赛季: ${response.allAvailableSeasons.join(', ')}`);
      this.logger.info('[PARSER-DEBUG] 💡 请使用上述赛季格式重新请求');
    }

    if (response?.details?.selectedSeason) {
      this.logger.info(`[PARSER-DEBUG] 💡 API 返回的当前赛季: ${response.details.selectedSeason}`);
    }
  }
}

module.exports = { DiscoveryDataValidator };
