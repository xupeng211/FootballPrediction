/**
 * LineupParser - V177 递归阵容解析器
 * ====================================
 *
 * 从 GoldenDataMerger.py 迁移的深度限制递归搜索逻辑
 * 处理 FotMob 结构变化的阵容 JSON
 *
 * @module parsers/fotmob/LineupParser
 * @version V177.0.0
 */

'use strict';

// ============================================================================
// 常量配置
// ============================================================================

const LINEUP_CONFIG = {
    // 递归深度限制 (防止栈溢出)
    maxSearchDepth: 8,

    // 阵容字段名变体 (FotMob API 变化适配)
    lineupFieldNames: ['lineup', 'startingXi', 'starters', 'starting11', 'firstEleven'],

    // 缺阵字段名变体
    missingFieldNames: ['missingPlayers', 'missing_players', 'injured', 'suspended', 'absences'],

    // 阵型字段名变体
    formationFieldNames: ['formation', 'lineupFormation', 'setup']
};

// ============================================================================
// LineupParser 类
// ============================================================================

class LineupParser {
    constructor(config = {}) {
        this.config = { ...LINEUP_CONFIG, ...config };
    }

    /**
     * 从 FotMob API 响应中解析阵容数据
     *
     * @param {Object} jsonData - FotMob API JSON 响应
     * @param {string} matchId - 比赛 ID (用于日志)
     * @returns {Object} 解析后的阵容数据
     */
    parse(jsonData, matchId = 'unknown') {
        const result = {
            match_id: matchId,
            home: {
                formation: null,
                lineup: [],
                missing_players: [],
                substitutes: []
            },
            away: {
                formation: null,
                lineup: [],
                missing_players: [],
                substitutes: []
            },
            parsed: false,
            error: null
        };

        try {
            // 获取 content 节点
            const content = jsonData?.content || jsonData;

            // 递归查找阵容数据
            const lineupData = this._findLineupData(content);

            if (!lineupData) {
                result.error = 'LINEUP_NOT_FOUND';
                return result;
            }

            // 解析主队数据
            if (lineupData.home) {
                result.home = this._parseTeamLineup(lineupData.home);
            }

            // 解析客队数据
            if (lineupData.away) {
                result.away = this._parseTeamLineup(lineupData.away);
            }

            result.parsed = true;

        } catch (error) {
            result.error = `PARSE_ERROR: ${error.message}`;
        }

        return result;
    }

    /**
     * 递归查找阵容数据节点
     *
     * 算法：深度优先搜索，限制深度防止栈溢出
     *
     * @param {Object} obj - 要搜索的对象
     * @param {number} depth - 当前递归深度
     * @returns {Object|null} 阵容数据节点
     */
    _findLineupData(obj, depth = 0) {
        // 深度限制
        if (depth > this.config.maxSearchDepth) {
            return null;
        }

        // 空值检查
        if (!obj || typeof obj !== 'object') {
            return null;
        }

        // 检查是否是阵容节点 (同时包含 home 和 away，且至少一个有 lineup)
        if (obj.home && obj.away) {
            const homeHasLineup = this._hasLineupField(obj.home);
            const awayHasLineup = this._hasLineupField(obj.away);

            if (homeHasLineup || awayHasLineup) {
                return obj;
            }
        }

        // 递归搜索子节点
        for (const key of Object.keys(obj)) {
            const value = obj[key];

            if (value && typeof value === 'object') {
                // 先检查数组元素
                if (Array.isArray(value)) {
                    for (const item of value) {
                        if (item && typeof item === 'object') {
                            const found = this._findLineupData(item, depth + 1);
                            if (found) return found;
                        }
                    }
                } else {
                    const found = this._findLineupData(value, depth + 1);
                    if (found) return found;
                }
            }
        }

        return null;
    }

    /**
     * 检查对象是否包含阵容字段
     */
    _hasLineupField(obj) {
        if (!obj || typeof obj !== 'object') return false;

        for (const fieldName of this.config.lineupFieldNames) {
            if (obj[fieldName] && (Array.isArray(obj[fieldName]) || typeof obj[fieldName] === 'object')) {
                return true;
            }
        }

        return false;
    }

    /**
     * 解析单个球队的阵容数据
     *
     * @param {Object} teamData - 球队数据节点
     * @returns {Object} 解析后的球队阵容
     */
    _parseTeamLineup(teamData) {
        const result = {
            formation: null,
            lineup: [],
            missing_players: [],
            substitutes: []
        };

        if (!teamData || typeof teamData !== 'object') {
            return result;
        }

        // 解析阵型
        result.formation = this._extractField(teamData, this.config.formationFieldNames);

        // 解析首发阵容
        result.lineup = this._extractLineup(teamData);

        // 解析缺阵球员
        result.missing_players = this._extractMissingPlayers(teamData);

        // 解析替补球员
        if (teamData.substitutes || teamData.bench || teamData.subs) {
            result.substitutes = this._parsePlayers(teamData.substitutes || teamData.bench || teamData.subs || []);
        }

        return result;
    }

    /**
     * 提取首发阵容
     */
    _extractLineup(teamData) {
        // 尝试各种字段名
        for (const fieldName of this.config.lineupFieldNames) {
            const lineupData = teamData[fieldName];
            if (lineupData) {
                return this._parsePlayers(lineupData);
            }
        }

        return [];
    }

    /**
     * 提取缺阵球员
     */
    _extractMissingPlayers(teamData) {
        // 尝试各种字段名
        for (const fieldName of this.config.missingFieldNames) {
            const missingData = teamData[fieldName];
            if (missingData && Array.isArray(missingData)) {
                return this._parseMissingPlayers(missingData);
            }
        }

        return [];
    }

    /**
     * 解析球员列表
     */
    _parsePlayers(playersData) {
        if (!Array.isArray(playersData)) {
            // 可能是对象格式 { players: [...] }
            if (playersData && typeof playersData === 'object') {
                if (playersData.players && Array.isArray(playersData.players)) {
                    playersData = playersData.players;
                } else {
                    return [];
                }
            } else {
                return [];
            }
        }

        return playersData.map(player => this._parsePlayer(player)).filter(p => p);
    }

    /**
     * 解析单个球员
     */
    _parsePlayer(player) {
        if (!player || typeof player !== 'object') return null;

        return {
            name: player.name || player.playerName || player.player_name || 'Unknown',
            position: player.position || player.role || player.playerRole || null,
            rating: this._safeFloat(player.rating || player.playerRating),
            shirt_number: player.shirtNumber || player.number || player.jerseyNumber || null,
            is_captain: player.captain || player.isCaptain || false,
            minutes_played: player.minutesPlayed || player.minutes || null
        };
    }

    /**
     * 解析缺阵球员列表
     */
    _parseMissingPlayers(missingData) {
        if (!Array.isArray(missingData)) return [];

        return missingData.map(player => ({
            name: player.name || player.playerName || 'Unknown',
            reason: player.reason || player.injuryType || player.absenceReason || 'Unknown',
            expected_return: player.expectedReturn || player.returnDate || null
        }));
    }

    /**
     * 提取字段 (支持多种字段名)
     */
    _extractField(obj, fieldNames) {
        for (const name of fieldNames) {
            if (obj[name] !== undefined && obj[name] !== null) {
                return obj[name];
            }
        }
        return null;
    }

    /**
     * 安全解析浮点数
     */
    _safeFloat(value) {
        if (value === null || value === undefined) return null;
        const parsed = parseFloat(value);
        return isNaN(parsed) ? null : parsed;
    }

    /**
     * 检测阵容是否有效
     *
     * @param {Object} lineupResult - parse() 的返回结果
     * @returns {Object} 有效性检查结果
     */
    validate(lineupResult) {
        const issues = [];

        if (!lineupResult.parsed) {
            issues.push('PARSE_FAILED');
        }

        if (lineupResult.error) {
            issues.push(lineupResult.error);
        }

        const homeLineupCount = lineupResult.home?.lineup?.length || 0;
        const awayLineupCount = lineupResult.away?.lineup?.length || 0;

        if (homeLineupCount < 11 && homeLineupCount > 0) {
            issues.push(`HOME_LINEUP_INCOMPLETE:${homeLineupCount}`);
        }

        if (awayLineupCount < 11 && awayLineupCount > 0) {
            issues.push(`AWAY_LINEUP_INCOMPLETE:${awayLineupCount}`);
        }

        return {
            valid: issues.length === 0,
            issues,
            home_lineup_count: homeLineupCount,
            away_lineup_count: awayLineupCount
        };
    }
}

// ============================================================================
// 导出
// ============================================================================

module.exports = {
    LineupParser,
    LINEUP_CONFIG
};
