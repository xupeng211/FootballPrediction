/**
 * XGExtractor - xG 数据提取器
 * @module parsers/fotmob/XGExtractor
 */

'use strict';

/**
 * 提取 xG 数据
 * @param {Object} data - API 数据
 * @returns {Object} xG 数据 {xg_home, xg_away, hasXG}
 */
function extractXG(data) {
    if (!data || !data.content || !data.content.stats) {
        return { xg_home: null, xg_away: null, hasXG: false };
    }

    const stats = data.content.stats;
    
    // 方式1: 从 Periods.All.stats 提取 (直接值)
    if (stats.Periods && stats.Periods.All && stats.Periods.All.stats) {
        const xgStat = stats.Periods.All.stats.find(
            s => s.title === 'Expected Goals' || s.title === 'xG'
        );
        if (xgStat && xgStat.stats && xgStat.stats.length >= 2) {
            return {
                xg_home: parseFloat(xgStat.stats[0]),
                xg_away: parseFloat(xgStat.stats[1]),
                hasXG: true
            };
        }
        
        // 方式2: 嵌套结构 (Top stats -> expected_goals)
        const topStats = stats.Periods.All.stats.find(
            s => s.title === 'Top stats'
        );
        if (topStats && topStats.stats) {
            const nestedXg = topStats.stats.find(
                s => s.key === 'expected_goals'
            );
            if (nestedXg && nestedXg.stats && nestedXg.stats.length >= 2) {
                return {
                    xg_home: parseFloat(nestedXg.stats[0]),
                    xg_away: parseFloat(nestedXg.stats[1]),
                    hasXG: true
                };
            }
        }
    }

    return { xg_home: null, xg_away: null, hasXG: false };
}

/**
 * 提取控球率数据
 * @param {Object} data - API 数据
 * @returns {Object} 控球率数据 {possession_home, possession_away, hasPossession}
 */
function extractPossession(data) {
    if (!data || !data.content || !data.content.stats) {
        return { possession_home: null, possession_away: null, hasPossession: false };
    }

    const stats = data.content.stats;
    
    if (stats.Periods && stats.Periods.All && stats.Periods.All.stats) {
        // 方式1: Ball possession 百分比格式
        const posStat = stats.Periods.All.stats.find(
            s => s.title === 'Ball possession' || s.title === 'Possession'
        );
        if (posStat && posStat.stats) {
            const posData = posStat.stats.find(
                s => s.key === 'possession' || s.key === 'ball_possession'
            );
            if (posData && posData.stats && posData.stats.length >= 2) {
                let home = posData.stats[0];
                let away = posData.stats[1];
                
                // 处理百分比字符串 (如 "65%")
                if (typeof home === 'string' && home.includes('%')) {
                    home = parseFloat(home) / 100;
                } else {
                    home = parseFloat(home);
                }
                if (typeof away === 'string' && away.includes('%')) {
                    away = parseFloat(away) / 100;
                } else {
                    away = parseFloat(away);
                }
                
                return {
                    possession_home: home,
                    possession_away: away,
                    hasPossession: true
                };
            }
        }
    }

    return { possession_home: null, possession_away: null, hasPossession: false };
}

/**
 * 提取所有统计数据
 * @param {Object} data - API 数据
 * @returns {Object} 所有统计数据
 */
function extractAllStats(data) {
    const xg = extractXG(data);
    const possession = extractPossession(data);
    
    return {
        xg_home: xg.xg_home,
        xg_away: xg.xg_away,
        possession_home: possession.possession_home,
        possession_away: possession.possession_away,
        hasAnyStats: xg.hasXG || possession.hasPossession
    };
}

/**
 * 验证 xG 数据有效性
 * @param {number} homeXG - 主队 xG
 * @param {number} awayXG - 客队 xG
 * @returns {Object} 验证结果 {valid: boolean, warnings: string[]}
 */
function validateXG(homeXG, awayXG) {
    const warnings = [];
    let valid = true;

    // 处理 null/undefined
    if (homeXG === null || homeXG === undefined || awayXG === null || awayXG === undefined) {
        warnings.push('xG 数据缺失');
        return { valid: true, warnings };
    }

    // 检查负数
    if (homeXG < 0 || awayXG < 0) {
        valid = false;
        warnings.push('xG 值不能为负数');
    }

    // 检查异常高值
    if (homeXG > 10 || awayXG > 10) {
        valid = false;
        warnings.push('xG 值异常高，可能数据错误');
    }

    return { valid, warnings };
}

module.exports = {
    extractXG,
    extractPossession,
    extractAllStats,
    validateXG
};