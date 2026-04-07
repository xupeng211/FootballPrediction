/**
 * Registry - 配置注册表
 * ======================
 *
 * 集中管理表名、API 配置等常量
 * @module config/registry
 */

'use strict';

const { MATCH_STATUS } = require('./constants');
const { resolveProxyPoolConfig } = require('./proxy_pool');

/**
 * 数据库表名注册表
 */
const TABLES = {
    MATCHES: 'matches',
    RAW_MATCH_DATA: 'raw_match_data',
    L2_MATCH_DATA: 'l2_match_data',
    L3_FEATURES: 'l3_features',
    PREDICTIONS: 'predictions',
    TEAM_ELO_RATINGS: 'team_elo_ratings',

    /**
     * 获取所有表名
     * @returns {string[]} 表名数组
     */
    all() {
        return [
            this.MATCHES,
            this.RAW_MATCH_DATA,
            this.L2_MATCH_DATA,
            this.L3_FEATURES,
            this.PREDICTIONS,
            this.TEAM_ELO_RATINGS
        ];
    }
};

/**
 * API 配置注册表
 */
const APIS = {
    FOTMOB: {
        BASE_URL: 'https://www.fotmob.com',
        /**
         * 构建联赛 API URL
         * @param {number} leagueId - 联赛 ID
         * @param {string} season - 赛季 (如 '20242025')
         * @returns {string} API URL
         */
        leagues: (leagueId, season) => {
            return `https://www.fotmob.com/api/leagues?id=${leagueId}&season=${season}`;
        }
    }
};

/**
 * 联赛配置注册表
 */
const LEAGUES = {
    BY_ID: {
        47: { name: 'Premier League', country: 'England' },
        55: { name: 'La Liga', country: 'Spain' },
        54: { name: 'Bundesliga', country: 'Germany' },
        53: { name: 'Serie A', country: 'Italy' },
        57: { name: 'Ligue 1', country: 'France' }
    }
};

/**
 * 代理配置注册表
 */
const PROXIES = {
    getAllPorts: () => [...resolveProxyPoolConfig().ports]
};

// PROXY别名（兼容测试）
const PROXY = PROXIES;

module.exports = {
    TABLES,
    APIS,
    LEAGUES,
    PROXIES,
    PROXY,
    MATCH_STATUS
};
