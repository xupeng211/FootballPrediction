/**
 * Normalizer - V6.6 标准化工具类
 * ==============================
 *
 * 提供 L1/L2/L3 全链路数据标准化函数
 * 从 V6.5 FixtureSeeder.js 中提取，供全项目共享
 *
 * @module utils/Normalizer
 * @version V6.6.0
 * @since V6.5
 */

'use strict';

/**
 * 标准化工具类
 */
class Normalizer {
    /**
     * 赛季格式标准化
     * 将各种格式统一转换为 'YYYY/YYYY' 标准格式
     *
     * @param {string} season - 原始赛季字符串
     * @returns {string} 标准化赛季 (如 '2023/2024')
     * @throws {Error} 当格式无法识别时抛出
     *
     * @example
     * Normalizer.normalizeSeason('2324');        // '2023/2024'
     * Normalizer.normalizeSeason('20232024');    // '2023/2024'
     * Normalizer.normalizeSeason('2023-2024');   // '2023/2024'
     * Normalizer.normalizeSeason('2023/2024');   // '2023/2024' (已是标准格式)
     * Normalizer.normalizeSeason('2023_2024');   // '2023/2024'
     * Normalizer.normalizeSeason('2023 2024');   // '2023/2024'
     * Normalizer.normalizeSeason('9900');        // '2099/2100'
     */
    static normalizeSeason(season) {
        if (!season || typeof season !== 'string') {
            throw new Error(`Invalid season: ${season}`);
        }

        // 已经是标准格式
        if (/^\d{4}\/\d{4}$/.test(season)) {
            return season;
        }

        // 处理 '2324' 格式 (4位简写)
        if (/^\d{4}$/.test(season)) {
            const startShort = parseInt(season.substring(0, 2));
            const endShort = parseInt(season.substring(2, 4));
            
            // 世纪边界处理
            // 规则: 如果结束年份 < 开始年份，则结束年份进入下一个世纪 (2099->2100)
            const startYear = `20${season.substring(0, 2)}`;
            const endYear = endShort < startShort 
                ? `21${season.substring(2, 4)}`  // 跨世纪 (如 9900 -> 2099/2100)
                : `20${season.substring(2, 4)}`; // 同世纪 (如 2324 -> 2023/2024)
            
            return `${startYear}/${endYear}`;
        }

        // 处理 '20242025' 格式 (8位完整)
        if (/^\d{8}$/.test(season)) {
            const startYear = season.substring(0, 4);
            const endYear = season.substring(4, 8);
            return `${startYear}/${endYear}`;
        }

        // 处理 '2024-2025' 格式 (横线分隔)
        if (/^\d{4}-\d{4}$/.test(season)) {
            return season.replace('-', '/');
        }

        // 处理 '2024_2025' 格式 (下划线分隔)
        if (/^\d{4}_\d{4}$/.test(season)) {
            return season.replace('_', '/');
        }

        // 处理 '2024 2025' 格式 (空格分隔)
        if (/^\d{4}\s+\d{4}$/.test(season)) {
            return season.replace(/\s+/, '/');
        }

        // 无法识别的格式，抛出错误
        throw new Error(`Unrecognized season format: ${season}`);
    }

    /**
     * 状态字符串标准化
     * 强制转换为小写，确保数据库约束兼容性
     *
     * @param {string} status - 原始状态字符串
     * @returns {string} 小写状态
     */
    static normalizeStatus(status) {
        if (!status || typeof status !== 'string') {
            return 'scheduled';
        }
        return status.toLowerCase().trim();
    }

    /**
     * 队名标准化
     * 处理常见变体，转换为数据库标准格式
     *
     * @param {string} teamName - 原始队名
     * @returns {string} 标准化队名
     */
    static normalizeTeamName(teamName) {
        if (!teamName || typeof teamName !== 'string') {
            return '';
        }

        // 清理格式
        const normalized = teamName
            .toLowerCase()
            .replace(/-/g, ' ')
            .replace(/\s+/g, ' ')
            .trim();

        // 英超队名映射表
        const TEAM_NAME_MAPPINGS = {
            // Manchester teams
            'man united': 'Manchester United',
            'man utd': 'Manchester United',
            'manchester united': 'Manchester United',
            'man city': 'Manchester City',
            'manchester city': 'Manchester City',

            // Newcastle
            'newcastle utd': 'Newcastle United',
            'newcastle united': 'Newcastle United',
            'newcastle': 'Newcastle United',

            // Wolves
            'wolverhampton': 'Wolverhampton Wanderers',
            'wolves': 'Wolverhampton Wanderers',

            // Tottenham
            'tottenham': 'Tottenham Hotspur',
            'spurs': 'Tottenham Hotspur',

            // West Ham
            'west ham': 'West Ham United',
            'west ham utd': 'West Ham United',

            // Nottingham Forest
            'nottingham': 'Nottingham Forest',
            'nottingham forest': 'Nottingham Forest',
            'n forest': 'Nottingham Forest',

            // Brighton
            'brighton': 'Brighton & Hove Albion',
            'brighton hove albion': 'Brighton & Hove Albion',

            // Bournemouth
            'bournemouth': 'AFC Bournemouth',
            'afc bournemouth': 'AFC Bournemouth',

            // 标准名称
            'arsenal': 'Arsenal',
            'aston villa': 'Aston Villa',
            'brentford': 'Brentford',
            'burnley': 'Burnley',
            'chelsea': 'Chelsea',
            'crystal palace': 'Crystal Palace',
            'everton': 'Everton',
            'fulham': 'Fulham',
            'liverpool': 'Liverpool',
            'luton': 'Luton',
            'sheffield utd': 'Sheffield United',
            'sheffield united': 'Sheffield United'
        };

        // 查找映射表
        if (TEAM_NAME_MAPPINGS[normalized]) {
            return TEAM_NAME_MAPPINGS[normalized];
        }

        // 无映射时，首字母大写
        return normalized
            .split(' ')
            .map(word => word.charAt(0).toUpperCase() + word.slice(1))
            .join(' ');
    }

    /**
     * match_id 格式校验
     * 格式: {league_id}_{season_tag}_{external_id}
     * 示例: 47_20232024_4193450
     *
     * @param {string} matchId - match_id 字符串
     * @returns {boolean} 是否有效
     */
    static isValidMatchId(matchId) {
        if (!matchId || typeof matchId !== 'string') {
            return false;
        }
        return /^\d+_\d{8}_\d+$/.test(matchId);
    }

    /**
     * 解析 match_id
     *
     * @param {string} matchId - match_id 字符串
     * @returns {Object|null} 解析结果 {leagueId, seasonTag, externalId}
     */
    static parseMatchId(matchId) {
        if (!this.isValidMatchId(matchId)) {
            return null;
        }

        const parts = matchId.split('_');
        return {
            leagueId: parts[0],
            seasonTag: parts[1],
            externalId: parts[2]
        };
    }

    /**
     * 构建标准 match_id
     *
     * @param {number|string} leagueId - 联赛 ID
     * @param {string} season - 赛季 (YYYY/YYYY 格式)
     * @param {string} externalId - 外部 ID
     * @returns {string} 标准 match_id
     * @throws {Error} 当参数无效时抛出
     */
    static buildMatchId(leagueId, season, externalId) {
        // 参数校验
        if (leagueId === null || leagueId === undefined || leagueId === '') {
            throw new Error(`Invalid leagueId: ${leagueId}`);
        }
        if (externalId === null || externalId === undefined || externalId === '') {
            throw new Error(`Invalid externalId: ${externalId}`);
        }
        
        const normalizedSeason = this.normalizeSeason(season);
        const seasonTag = normalizedSeason.replace('/', '');
        return `${leagueId}_${seasonTag}_${externalId}`;
    }
}

module.exports = { Normalizer };
