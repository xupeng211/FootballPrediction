/**
 * XGExtractor - xG 数据提取器
 * ==============================================
 *
 * 从 FotMob API 数据中提取 xG (期望进球) 数据
 * 纯函数设计，易于测试
 *
 * @module parsers/fotmob/XGExtractor
 * @version V174.0.0
 */

'use strict';

/**
 * 从 API 数据中提取 xG 数据
 *
 * @param {object} apiData - API 响应数据
 * @returns {{ xg_home: number|null, xg_away: number|null, hasXG: boolean }}
 */
function extractXG(apiData) {
    const result = {
        xg_home: null,
        xg_away: null,
        hasXG: false
    };

    try {
        // FotMob 数据结构: content.stats.Periods.All.stats
        const periods = apiData?.content?.stats?.Periods;
        const allStats = periods?.All?.stats || [];

        // 遍历所有分组查找 xG 数据
        for (const group of allStats) {
            const groupTitle = (group.title || '').toLowerCase();

            // 检查分组标题是否包含 xG 相关关键词
            if (groupTitle.includes('expected goals') || groupTitle.includes('xg')) {
                // 方式 1: xG 数据直接在分组的 stats 数组中（作为值）
                if (group.stats && Array.isArray(group.stats) && group.stats.length >= 2) {
                    const first = group.stats[0];
                    // 检查是否是数字或数字字符串
                    if (typeof first === 'number' || (typeof first === 'string' && !isNaN(parseFloat(first)))) {
                        result.xg_home = parseFloat(first);
                        result.xg_away = parseFloat(group.stats[1]);
                        result.hasXG = !isNaN(result.xg_home) && !isNaN(result.xg_away);
                        if (result.hasXG) break;
                    }
                }

                // 方式 2: 在 stats 数组中查找 expected_goals 条目
                if (group.stats && Array.isArray(group.stats)) {
                    for (const stat of group.stats) {
                        if (stat && stat.stats && Array.isArray(stat.stats) && stat.stats.length >= 2) {
                            const statKey = (stat.key || '').toLowerCase();
                            const statTitle = (stat.title || '').toLowerCase();

                            if (statKey === 'expected_goals' || statTitle.includes('expected goals')) {
                                result.xg_home = parseFloat(stat.stats[0]);
                                result.xg_away = parseFloat(stat.stats[1]);
                                result.hasXG = !isNaN(result.xg_home) && !isNaN(result.xg_away);
                                if (result.hasXG) break;
                            }
                        }
                    }
                    if (result.hasXG) break;
                }
            }

            // 方式 3: 在 "Top stats" 分组中查找 expected_goals
            if (groupTitle.includes('top stats') && group.stats && Array.isArray(group.stats)) {
                for (const stat of group.stats) {
                    if (stat && stat.stats && Array.isArray(stat.stats) && stat.stats.length >= 2) {
                        const statKey = (stat.key || '').toLowerCase();
                        const statTitle = (stat.title || '').toLowerCase();

                        if (statKey === 'expected_goals' || statTitle.includes('expected goals')) {
                            result.xg_home = parseFloat(stat.stats[0]);
                            result.xg_away = parseFloat(stat.stats[1]);
                            result.hasXG = !isNaN(result.xg_home) && !isNaN(result.xg_away);
                            if (result.hasXG) break;
                        }
                    }
                }
                if (result.hasXG) break;
            }
        }

    } catch (e) {
        // 解析失败，返回默认值
    }

    // NaN 容错
    if (isNaN(result.xg_home)) result.xg_home = null;
    if (isNaN(result.xg_away)) result.xg_away = null;
    result.hasXG = result.xg_home !== null && result.xg_away !== null;

    return result;
}

/**
 * 从 API 数据中提取控球率
 *
 * @param {object} apiData - API 响应数据
 * @returns {{ possession_home: number|null, possession_away: number|null, hasPossession: boolean }}
 */
function extractPossession(apiData) {
    const result = {
        possession_home: null,
        possession_away: null,
        hasPossession: false
    };

    try {
        const periods = apiData?.content?.stats?.Periods;
        const allStats = periods?.All?.stats || [];

        // 查找 Ball possession 分组
        const possessionGroup = allStats.find(g => {
            const title = (g.title || '').toLowerCase();
            return title.includes('possession') || title.includes('ball');
        });

        if (possessionGroup?.stats) {
            const possessionRow = possessionGroup.stats.find(s =>
                (s.key || '').toLowerCase().includes('possession')
            );

            if (possessionRow?.stats?.length >= 2) {
                // 控球率可能是百分比字符串或数字
                const home = possessionRow.stats[0];
                const away = possessionRow.stats[1];

                result.possession_home = parsePossessionValue(home);
                result.possession_away = parsePossessionValue(away);
                result.hasPossession = result.possession_home !== null && result.possession_away !== null;
            }
        }

    } catch (e) {
        // 解析失败
    }

    return result;
}

/**
 * 解析控球率值
 *
 * @param {string|number} value - 控球率值
 * @returns {number|null}
 */
function parsePossessionValue(value) {
    if (value === null || value === undefined) return null;

    // 如果是数字，直接返回
    if (typeof value === 'number') {
        return value > 1 ? value / 100 : value;  // 如果大于1，假设是百分比
    }

    // 如果是字符串，解析百分比
    if (typeof value === 'string') {
        const num = parseFloat(value.replace('%', ''));
        if (isNaN(num)) return null;
        return num > 1 ? num / 100 : num;
    }

    return null;
}

/**
 * 提取所有统计数据
 *
 * @param {object} apiData - API 响应数据
 * @returns {object} 统计数据对象
 */
function extractAllStats(apiData) {
    const xg = extractXG(apiData);
    const possession = extractPossession(apiData);

    return {
        ...xg,
        ...possession,
        hasAnyStats: xg.hasXG || possession.hasPossession
    };
}

/**
 * 从原始 JSON 数据中提取 xG（简化版）
 *
 * @param {object} rawJson - 原始 JSON 数据
 * @returns {{ xg_home: number|null, xg_away: number|null }}
 */
function extractXGFromRaw(rawJson) {
    return extractXG(rawJson);
}

/**
 * 验证 xG 数据合理性
 *
 * @param {number} xgHome - 主队 xG
 * @param {number} xgAway - 客队 xG
 * @returns {{ valid: boolean, warnings: string[] }}
 */
function validateXG(xgHome, xgAway) {
    const warnings = [];

    if (xgHome === null || xgAway === null) {
        return { valid: true, warnings: ['xG 数据缺失'] };
    }

    if (xgHome < 0 || xgAway < 0) {
        warnings.push('xG 值为负数');
    }

    if (xgHome > 10 || xgAway > 10) {
        warnings.push('xG 值异常高');
    }

    return {
        valid: warnings.length === 0,
        warnings
    };
}

module.exports = {
    extractXG,
    extractPossession,
    parsePossessionValue,
    extractAllStats,
    extractXGFromRaw,
    validateXG
};
