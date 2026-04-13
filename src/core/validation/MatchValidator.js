/**
 * @file MatchValidator - 比赛数据验证器 V6.4
 *
 * 三道铁门验证逻辑：
 * 1. leagueId 校验 - 无罪推定原则
 * 2. 赛季时间窗口校验 (含缓冲期机制)
 * 3. 占位符检测
 *
 * @module core/validation/MatchValidator
 * @version V6.4
 */

'use strict';

const fs = require('fs');
const path = require('path');
const {
  buildBufferedWindow,
  containsPlaceholderKeyword,
  extractMatchTime,
  hasInvalidTeamIds,
  initializeStats,
  isProcessableMatch,
  logWindowDebug,
  parseMatchDate
} = require('./matchValidationHelpers');

const CONFIG_PATH = path.resolve(__dirname, '../../../config/season_windows.json');

function loadSeasonConfig() {
  try {
    if (!fs.existsSync(CONFIG_PATH)) {
      throw new Error(`配置文件不存在: ${CONFIG_PATH}`);
    }
    return JSON.parse(fs.readFileSync(CONFIG_PATH, 'utf8'));
  } catch (error) {
    console.error('赛季配置加载失败:', error.message);
    process.exit(1);
  }
}

const SEASON_CONFIG = loadSeasonConfig();

const ValidationConfig = {
  getSeasonWindow(season, leagueId = null) {
    if (leagueId) {
      const leagueSpecificKey = `${season}-${leagueId}`;
      if (SEASON_CONFIG?.seasons?.[leagueSpecificKey]) {
        return SEASON_CONFIG.seasons[leagueSpecificKey];
      }

      const suffix = { 54: 'Bundesliga', 53: 'Ligue1' }[leagueId];
      if (suffix && SEASON_CONFIG?.seasons?.[`${season}-${suffix}`]) {
        return SEASON_CONFIG.seasons[`${season}-${suffix}`];
      }
    }

    return SEASON_CONFIG?.seasons?.[season] || null;
  },
  getPlaceholderKeywords() {
    return SEASON_CONFIG?.validation_rules?.placeholder_keywords || [];
  },
  getDailyThreshold() {
    return SEASON_CONFIG?.validation_rules?.daily_match_threshold || 50;
  },
  getBufferDays() {
    return SEASON_CONFIG?.validation_rules?.buffer_days || 14;
  }
};

function passesMatchGuards(match, leagueInfo, seasonWindow, log, stats, options) {
  if (!validateLeagueId(match, leagueInfo.id)) {
    stats.wrongLeague++;
    return false;
  }

  if (!options.fullSync && seasonWindow && !validateSeasonWindow(match, seasonWindow, log, stats, options)) {
    stats.outsideWindow++;
    return false;
  }

  if (isPlaceholder(match)) {
    stats.placeholder++;
    return false;
  }

  if (!validateBasicData(match)) {
    stats.invalidData++;
    return false;
  }

  return true;
}

function threeGatesFilter(matches, leagueInfo, season, stats, log = console, options = {}) {
  const safeStats = initializeStats(stats);
  if (!Array.isArray(matches)) {
    log.error?.('API 返回非数组数据', { type: typeof matches });
    return [];
  }
  if (!leagueInfo || typeof leagueInfo !== 'object') {
    log.error?.('联赛信息无效');
    return [];
  }

  const validMatches = [];
  const seasonWindow = ValidationConfig.getSeasonWindow(season, leagueInfo.id);

  for (let index = 0; index < matches.length; index++) {
    const match = matches[index];
    if (!isProcessableMatch(match)) {
      safeStats.invalidData++;
      continue;
    }

    try {
      if (passesMatchGuards(match, leagueInfo, seasonWindow, log, safeStats, options)) {
        validMatches.push(match);
      }
    } catch (error) {
      log.warn?.(`索引 ${index} 数据处理异常`, { error: error.message });
      safeStats.invalidData++;
    }
  }

  detectBatchPlaceholders(validMatches, log);
  return validMatches;
}

function validateLeagueId(match, expectedLeagueId) {
  if (!isProcessableMatch(match) || typeof expectedLeagueId !== 'number') {
    return false;
  }
  if (match.leagueId !== undefined && match.leagueId !== null) {
    return match.leagueId === expectedLeagueId;
  }
  if (match.parent?.leagueId !== undefined) {
    return match.parent.leagueId === expectedLeagueId;
  }
  return true;
}

function validateSeasonWindow(match, window, log = null, stats = null, options = {}) {
  if (!isProcessableMatch(match)) {
    return false;
  }
  if (!window || options.fullSync) {
    return true;
  }

  const { rawTime, usedField } = extractMatchTime(match);
  if (!rawTime) {
    return true;
  }

  try {
    const matchDate = parseMatchDate(rawTime);
    if (!matchDate || Number.isNaN(matchDate.getTime())) {
      logWindowDebug(log, stats, '时间解析失败，放行处理', {
        matchId: match.id,
        field: usedField,
        rawTime: String(rawTime),
        type: typeof rawTime
      });
      return true;
    }

    const bufferedWindow = buildBufferedWindow(window, ValidationConfig.getBufferDays());
    if (!bufferedWindow) {
      return true;
    }

    const inWindow = matchDate >= bufferedWindow.validStart && matchDate <= bufferedWindow.validEnd;
    if (!inWindow) {
      logWindowDebug(log, stats, '时间窗口拦截详情', {
        matchId: match.id,
        field: usedField,
        rawTime: String(rawTime),
        rawTimeType: typeof rawTime,
        parsedDate: matchDate.toISOString(),
        parsedTimestamp: matchDate.getTime(),
        windowStart: bufferedWindow.validStart.toISOString(),
        windowEnd: bufferedWindow.validEnd.toISOString(),
        windowStartTs: bufferedWindow.validStart.getTime(),
        windowEndTs: bufferedWindow.validEnd.getTime()
      });
    }

    return inWindow;
  } catch (error) {
    logWindowDebug(log, stats, '时间窗口校验异常，放行处理', {
      matchId: match.id,
      field: usedField,
      rawTime: String(rawTime),
      error: error.message
    });
    return true;
  }
}

function isPlaceholder(match) {
  if (!isProcessableMatch(match)) {
    return true;
  }
  return containsPlaceholderKeyword(match, ValidationConfig.getPlaceholderKeywords())
    || hasInvalidTeamIds(match);
}

function validateBasicData(match) {
  if (!isProcessableMatch(match)) {
    return false;
  }

  const matchId = match.id;
  if (matchId === null || matchId === undefined || matchId === '') {
    return false;
  }
  if (typeof matchId !== 'number' && typeof matchId !== 'string') {
    return false;
  }

  const homeName = String(match?.home?.name || '').trim();
  const awayName = String(match?.away?.name || '').trim();
  return Boolean(homeName && awayName && homeName.length >= 3 && awayName.length >= 3);
}

function detectBatchPlaceholders(matches, log = console) {
  if (!Array.isArray(matches) || matches.length === 0) {
    return;
  }

  const matchesByDate = {};
  for (const match of matches) {
    const utcTime = match?.status?.utcTime || match?.time;
    if (!utcTime) {
      continue;
    }

    try {
      const date = new Date(utcTime);
      if (Number.isNaN(date.getTime())) {
        continue;
      }
      const dateKey = date.toISOString().split('T')[0];
      matchesByDate[dateKey] = (matchesByDate[dateKey] || 0) + 1;
    } catch (_error) {
      continue;
    }
  }

  const threshold = ValidationConfig.getDailyThreshold();
  for (const [date, count] of Object.entries(matchesByDate)) {
    if (count > threshold) {
      log.warn?.(`异常检测: ${date} 有 ${count} 场比赛，超过阈值(${threshold})`);
    }
  }
}

module.exports = {
  threeGatesFilter,
  validateLeagueId,
  validateSeasonWindow,
  isPlaceholder,
  validateBasicData,
  ValidationConfig
};
