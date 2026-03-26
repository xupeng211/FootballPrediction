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

const path = require('path');
const fs = require('fs');

// V6.7: 集中式配置加载 (延迟加载以避免循环依赖)
let teamMappings = null;

/**
 * 加载队名映射配置
 * @private
 */
function loadTeamMappings() {
    if (teamMappings) return teamMappings;
    
    try {
        const configPath = path.join(process.cwd(), 'config/recon_config.json');
        if (fs.existsSync(configPath)) {
            const config = JSON.parse(fs.readFileSync(configPath, 'utf8'));
            teamMappings = config.team_mappings || {};
        }
    } catch (e) {
        console.error('[Normalizer] 警告: 无法加载 team_mappings 配置，回退到基础标准化', e.message);
        teamMappings = {};
    }
    return teamMappings;
}

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
     */
    static normalizeSeason(season) {
        if (!season || typeof season !== 'string') {
            throw new Error(`Invalid season: ${season}`);
        }

        const buildSeason = (startYear, endYear) => {
            const start = parseInt(startYear, 10);
            const end = parseInt(endYear, 10);

            if (Number.isNaN(start) || Number.isNaN(end)) {
                throw new Error(`Unrecognized season format: ${season}`);
            }

            if (end !== start + 1) {
                throw new Error(`Unrecognized season format: ${season}`);
            }

            return `${startYear}/${endYear}`;
        };

        // 已经是标准格式
        if (/^\d{4}\/\d{4}$/.test(season)) {
            const [startYear, endYear] = season.split('/');
            return buildSeason(startYear, endYear);
        }

        // 处理 '2324' 格式 (4位简写)
        if (/^\d{4}$/.test(season)) {
            const startShort = parseInt(season.substring(0, 2));
            const endShort = parseInt(season.substring(2, 4));

            const expectedEnd = (startShort + 1) % 100;
            if (endShort !== expectedEnd) {
                throw new Error(`Unrecognized season format: ${season}`);
            }

            const startYear = `20${season.substring(0, 2)}`;
            const endYear = endShort < startShort
                ? `21${season.substring(2, 4)}`
                : `20${season.substring(2, 4)}`;

            return buildSeason(startYear, endYear);
        }

        // 处理 '20242025' 格式 (8位完整)
        if (/^\d{8}$/.test(season)) {
            const startYear = season.substring(0, 4);
            const endYear = season.substring(4, 8);
            return buildSeason(startYear, endYear);
        }

        // 处理 '2024-2025' 格式 (横线分隔)
        if (/^\d{4}-\d{4}$/.test(season)) {
            const [startYear, endYear] = season.split('-');
            return buildSeason(startYear, endYear);
        }

        // 处理 '2024_2025' 格式 (下划线分隔)
        if (/^\d{4}_\d{4}$/.test(season)) {
            const [startYear, endYear] = season.split('_');
            return buildSeason(startYear, endYear);
        }

        // 处理 '2024 2025' 格式 (空格分隔)
        if (/^\d{4}\s+\d{4}$/.test(season)) {
            const [startYear, endYear] = season.trim().split(/\s+/);
            return buildSeason(startYear, endYear);
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
     * 队名标准化 (V6.7 Config-Driven)
     * 处理常见变体，转换为数据库标准格式
     * 不再硬编码队名映射，而是动态从 recon_config.json 加载
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
            .normalize('NFD')
            .replace(/[\u0300-\u036f]/g, '')
            .toLowerCase()
            .replace(/-/g, ' ')
            .replace(/[^\p{L}\p{N}\s]/gu, ' ')
            .replace(/\s+/g, ' ')
            .trim();

        // V6.7: 从中央配置加载映射库
        const mappings = loadTeamMappings();

        // 查找映射表
        if (mappings[normalized]) {
            return mappings[normalized];
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
