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

// 配置路径
const CONFIG_PATH = path.resolve(__dirname, '../../../config/season_windows.json');

/**
 * 加载赛季窗口配置
 * @returns {Object} 赛季配置对象
 */
function loadSeasonConfig() {
    try {
        if (!fs.existsSync(CONFIG_PATH)) {
            throw new Error(`配置文件不存在: ${CONFIG_PATH}`);
        }
        const raw = fs.readFileSync(CONFIG_PATH, 'utf8');
        return JSON.parse(raw);
    } catch (error) {
        console.error('赛季配置加载失败:', error.message);
        process.exit(1);
    }
}

const SEASON_CONFIG = loadSeasonConfig();

/**
 * 获取配置访问器
 */
const ValidationConfig = {
    getSeasonWindow(season) {
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

/**
 * 三道铁门主过滤器
 * @param {Array} matches - 原始比赛数据
 * @param {Object} leagueInfo - 联赛信息
 * @param {string} season - 赛季
 * @param {Object} stats - 统计对象
 * @param {Function} log - 日志函数
 * @returns {Array} 过滤后的比赛
 */
function threeGatesFilter(matches, leagueInfo, season, stats, log = console) {
    // 初始化统计
    stats = stats || {};
    stats.wrongLeague = stats.wrongLeague || 0;
    stats.outsideWindow = stats.outsideWindow || 0;
    stats.placeholder = stats.placeholder || 0;
    stats.invalidData = stats.invalidData || 0;

    // 类型检查
    if (!Array.isArray(matches)) {
        log.error?.('API 返回非数组数据', { type: typeof matches });
        return [];
    }

    if (!leagueInfo || typeof leagueInfo !== 'object') {
        log.error?.('联赛信息无效');
        return [];
    }

    const validMatches = [];
    const seasonWindow = ValidationConfig.getSeasonWindow(season);

    for (let i = 0; i < matches.length; i++) {
        const match = matches[i];

        // 对象类型检查
        if (!match || typeof match !== 'object' || Array.isArray(match)) {
            stats.invalidData++;
            continue;
        }

        try {
            // 铁门 1: leagueId 校验
            if (!validateLeagueId(match, leagueInfo.id)) {
                stats.wrongLeague++;
                continue;
            }

            // 铁门 2: 赛季时间窗口校验
            if (seasonWindow && !validateSeasonWindow(match, seasonWindow, log, stats)) {
                stats.outsideWindow++;
                continue;
            }

            // 铁门 3: 占位符检测
            if (isPlaceholder(match)) {
                stats.placeholder++;
                continue;
            }

            // 基础数据完整性校验
            if (!validateBasicData(match)) {
                stats.invalidData++;
                continue;
            }

            validMatches.push(match);
        } catch (error) {
            log.warn?.(`索引 ${i} 数据处理异常`, { error: error.message });
            stats.invalidData++;
            continue;
        }
    }

    detectBatchPlaceholders(validMatches, log);
    return validMatches;
}

/**
 * 铁门 1: leagueId 校验 - 无罪推定原则
 */
function validateLeagueId(match, expectedLeagueId) {
    if (!match || typeof match !== 'object') return false;
    if (typeof expectedLeagueId !== 'number') return false;

    // 优先检查 match.leagueId
    if (match.leagueId !== undefined && match.leagueId !== null) {
        return match.leagueId === expectedLeagueId;
    }

    // 备选：检查 parent 层级
    if (match.parent?.leagueId !== undefined) {
        return match.parent.leagueId === expectedLeagueId;
    }

    // 无罪推定 - 无 leagueId 字段时信任 API
    return true;
}

/**
 * 铁门 2: 赛季时间窗口校验 - V6.4 修复版
 * 支持: ISO字符串 / Unix秒 / Unix毫秒
 */
const MAX_DEBUG_LOGS = 3;

function validateSeasonWindow(match, window, log = null, stats = null) {
    if (!match || typeof match !== 'object') return false;
    if (!window) return true;

    // V6.3: 多重路径提取（按优先级）
    let rawTime = null;
    let usedField = null;

    // 路径1: match.utcTime (根级别最常见)
    if (match.utcTime !== undefined && match.utcTime !== null) {
        rawTime = match.utcTime;
        usedField = 'utcTime';
    }
    // 路径2: match.status?.utcTime (嵌套状态)
    else if (match.status?.utcTime !== undefined && match.status?.utcTime !== null) {
        rawTime = match.status.utcTime;
        usedField = 'status.utcTime';
    }
    // 路径3: match.time (Unix秒字段)
    else if (match.time !== undefined && match.time !== null) {
        rawTime = match.time;
        usedField = 'time';
    }

    // 无时间数据时放行
    if (!rawTime) {
        return true;
    }

    try {
        let matchDate = null;
        const strTime = String(rawTime).trim();

        // V6.3: 绝对日期优先 - 禁止使用parseInt处理日期字符串
        // 策略1: ISO格式识别 (包含 T 或 - 的字符串)
        if (typeof rawTime === 'string' && (strTime.includes('T') || strTime.includes('-'))) {
            // 直接解析，不使用parseInt
            matchDate = new Date(strTime);
        }
        // 策略2: 纯数字Unix时间戳 (仅当纯数字时才转换)
        else if (/^\d+$/.test(strTime)) {
            const numTime = parseInt(strTime, 10);
            // 10位 = Unix秒, 13位 = Unix毫秒
            if (strTime.length === 10) {
                matchDate = new Date(numTime * 1000);
            } else if (strTime.length === 13) {
                matchDate = new Date(numTime);
            } else if (numTime > 1000000000000) {
                matchDate = new Date(numTime); // 毫秒级大数字
            } else if (numTime > 1000000000) {
                matchDate = new Date(numTime * 1000); // 秒级
            }
        }
        // 策略3: 数字类型直接处理
        else if (typeof rawTime === 'number') {
            if (rawTime > 1000000000000) {
                matchDate = new Date(rawTime); // 毫秒
            } else if (rawTime > 1000000000) {
                matchDate = new Date(rawTime * 1000); // 秒
            }
        }
        // 策略4: 其他格式尝试解析
        else {
            matchDate = new Date(strTime);
        }

        // 解析失败时记录并放行
        if (!matchDate || isNaN(matchDate.getTime())) {
            if (stats) {
                stats._debugLogCount = (stats._debugLogCount || 0) + 1;
                if (stats._debugLogCount <= MAX_DEBUG_LOGS) {
                    log?.info?.(`[DEBUG ${stats._debugLogCount}/${MAX_DEBUG_LOGS}] 时间解析失败，放行处理`, {
                        matchId: match.id,
                        field: usedField,
                        rawTime: String(rawTime),
                        type: typeof rawTime
                    });
                }
            }
            return true;
        }

        const startDate = new Date(window.start);
        const endDate = new Date(window.end);

        if (isNaN(startDate.getTime()) || isNaN(endDate.getTime())) {
            return true;
        }

        const bufferMs = ValidationConfig.getBufferDays() * 24 * 60 * 60 * 1000;
        const validStart = new Date(startDate.getTime() - bufferMs);
        const validEnd = new Date(endDate.getTime() + bufferMs);

        const inWindow = matchDate >= validStart && matchDate <= validEnd;

        // V6.4: 强制统计日志 - 拦截时使用INFO级别(前3场)
        if (!inWindow) {
            if (stats) {
                stats._debugLogCount = (stats._debugLogCount || 0) + 1;
                if (stats._debugLogCount <= MAX_DEBUG_LOGS) {
                    log?.info?.(`[DEBUG ${stats._debugLogCount}/${MAX_DEBUG_LOGS}] 时间窗口拦截详情`, {
                        matchId: match.id,
                        field: usedField,
                        rawTime: String(rawTime),
                        rawTimeType: typeof rawTime,
                        parsedDate: matchDate.toISOString(),
                        parsedTimestamp: matchDate.getTime(),
                        windowStart: validStart.toISOString(),
                        windowEnd: validEnd.toISOString(),
                        windowStartTs: validStart.getTime(),
                        windowEndTs: validEnd.getTime()
                    });
                }
            }
        }

        return inWindow;
    } catch (error) {
        if (stats) {
            stats._debugLogCount = (stats._debugLogCount || 0) + 1;
            if (stats._debugLogCount <= MAX_DEBUG_LOGS) {
                log?.info?.(`[DEBUG ${stats._debugLogCount}/${MAX_DEBUG_LOGS}] 时间窗口校验异常，放行处理`, {
                    matchId: match.id,
                    field: usedField,
                    rawTime: String(rawTime),
                    error: error.message
                });
            }
        }
        return true;
    }
}

/**
 * 铁门 3: 占位符检测
 */
function isPlaceholder(match) {
    if (!match || typeof match !== 'object') return true;

    const homeName = String(match?.home?.name || '').toLowerCase().trim();
    const awayName = String(match?.away?.name || '').toLowerCase().trim();

    // 关键词检测
    const keywords = ValidationConfig.getPlaceholderKeywords();
    for (const keyword of keywords) {
        if (homeName.includes(keyword) || awayName.includes(keyword)) {
            return true;
        }
    }

    // ID 有效性检查（覆盖 0, '0', null, undefined, ''）
    const homeId = match?.home?.id;
    const awayId = match?.away?.id;

    if (homeId == null || awayId == null) return true;
    if (homeId === 0 || awayId === 0 || homeId === '0' || awayId === '0') return true;
    if (homeId === '' || awayId === '') return true;

    return false;
}

/**
 * 基础数据完整性校验
 */
function validateBasicData(match) {
    if (!match || typeof match !== 'object') return false;

    // match.id 校验
    const matchId = match.id;
    if (matchId == null || matchId === '') return false;
    if (typeof matchId !== 'number' && typeof matchId !== 'string') return false;

    // 球队信息校验
    if (!match.home || typeof match.home !== 'object') return false;
    if (!match.away || typeof match.away !== 'object') return false;

    const homeName = String(match.home.name || '').trim();
    const awayName = String(match.away.name || '').trim();

    if (!homeName || !awayName) return false;
    if (homeName.length < 3 || awayName.length < 3) return false;

    return true;
}

/**
 * 批量占位符检测
 */
function detectBatchPlaceholders(matches, log = console) {
    if (!Array.isArray(matches) || matches.length === 0) return;

    const matchesByDate = {};

    for (const match of matches) {
        const utcTime = match?.status?.utcTime || match?.time;
        if (!utcTime) continue;

        try {
            const date = new Date(utcTime);
            if (isNaN(date.getTime())) continue;

            const dateKey = date.toISOString().split('T')[0];
            matchesByDate[dateKey] = (matchesByDate[dateKey] || 0) + 1;
        } catch (e) {
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
