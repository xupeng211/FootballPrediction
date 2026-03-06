/**
 * DataSourceProvider - 数据源提供者抽象接口
 * ==============================================
 *
 * 定义数据源的标准接口，支持 FotMob、OddsPortal 等多种数据源的无缝切换。
 *
 * 设计原则:
 * - 依赖倒置: 高层模块依赖抽象接口，不依赖具体实现
 * - 开闭原则: 对扩展开放，对修改关闭
 * - 单一职责: 每个 Provider 只负责一个数据源
 *
 * @module interfaces/DataSourceProvider
 * @version V197.0.0
 * @since V196-TECH-DEBT-002
 */

'use strict';

const Registry = require('../../config/registry');

/**
 * 数据源类型枚举
 * @readonly
 * @enum {string}
 */
const DataSourceType = Object.freeze({
    FOTMOB: 'fotmob',
    ODDSPORTAL: 'oddsportal',
    BETEXPLORER: 'betexplorer',
    FLASHSCORE: 'flashscore'
});

/**
 * 比赛信息数据结构
 * @typedef {Object} MatchInfo
 * @property {string} match_id - 比赛唯一标识符
 * @property {string} external_id - 外部系统 ID
 * @property {string} league_name - 联赛名称
 * @property {string} season - 赛季
 * @property {string} home_team - 主队名称
 * @property {string} away_team - 客队名称
 * @property {Date|null} match_date - 比赛时间
 * @property {number|null} home_score - 主队得分
 * @property {number|null} away_score - 客队得分
 * @property {string} status - 比赛状态
 * @property {string} data_source - 数据来源
 */

/**
 * 联赛信息数据结构
 * @typedef {Object} LeagueInfo
 * @property {number} id - 联赛 ID
 * @property {string} name - 联赛名称
 * @property {string} country - 所属国家
 * @property {string} season - 当前赛季
 */

/**
 * 原始比赛数据结构
 * @typedef {Object} RawMatchData
 * @property {Object} content - 比赛内容数据
 * @property {Object} general - 通用信息
 * @property {Object} header - 头部信息
 */

/**
 * 数据源提供者抽象基类
 * 所有数据源实现必须继承此类
 *
 * @abstract
 * @class DataSourceProvider
 */
class DataSourceProvider {
    /**
     * 数据源类型
     * @type {string}
     */
    get sourceType() {
        throw new Error('Abstract property sourceType must be overridden');
    }

    /**
     * 数据源显示名称
     * @type {string}
     */
    get displayName() {
        throw new Error('Abstract property displayName must be overridden');
    }

    /**
     * 初始化提供者
     * @abstract
     * @async
     * @returns {Promise<void>}
     * @throws {Error} 初始化失败时抛出错误
     */
    async initialize() {
        throw new Error('Abstract method initialize() must be implemented');
    }

    /**
     * 获取联赛赛程数据
     * @abstract
     * @async
     * @param {number} leagueId - 联赛 ID
     * @param {string} season - 赛季 (格式: 2024/2025)
     * @returns {Promise<Object|null>} 联赛数据对象
     */
    async fetchLeagueFixtures(leagueId, season) {
        throw new Error('Abstract method fetchLeagueFixtures() must be implemented');
    }

    /**
     * 获取比赛详情数据
     * @abstract
     * @async
     * @param {string} externalId - 外部比赛 ID
     * @returns {Promise<RawMatchData|null>} 比赛详情数据
     */
    async fetchMatchDetails(externalId) {
        throw new Error('Abstract method fetchMatchDetails() must be implemented');
    }

    /**
     * 解析联赛数据为比赛列表
     * @abstract
     * @param {Object} leagueData - 原始联赛数据
     * @param {LeagueInfo} leagueInfo - 联赛配置信息
     * @param {string} season - 赛季
     * @returns {MatchInfo[]} 比赛数据数组
     */
    parseFixtures(leagueData, leagueInfo, season) {
        throw new Error('Abstract method parseFixtures() must be implemented');
    }

    /**
     * 解析单场比赛数据
     * @abstract
     * @param {Object} match - 原始比赛对象
     * @param {LeagueInfo} leagueInfo - 联赛配置信息
     * @param {string} season - 赛季
     * @returns {MatchInfo|null} 比赛数据对象
     */
    parseMatch(match, leagueInfo, season) {
        throw new Error('Abstract method parseMatch() must be implemented');
    }

    /**
     * 健康检查
     * @async
     * @returns {Promise<{healthy: boolean, latency?: number, error?: string}>}
     */
    async healthCheck() {
        return { healthy: false, error: 'Not implemented' };
    }

    /**
     * 关闭提供者，释放资源
     * @async
     * @returns {Promise<void>}
     */
    async close() {
        // 默认空实现，子类可覆盖
    }
}

/**
 * 数据源提供者工厂
 * 用于创建和管理数据源提供者实例
 *
 * @class DataSourceProviderFactory
 */
class DataSourceProviderFactory {
    constructor() {
        /** @type {Map<string, DataSourceProvider>} */
        this._providers = new Map();

        /** @type {Map<string, typeof DataSourceProvider>} */
        this._registry = new Map();
    }

    /**
     * 注册数据源提供者类
     * @param {string} type - 数据源类型
     * @param {typeof DataSourceProvider} ProviderClass - 提供者类
     */
    register(type, ProviderClass) {
        if (!type || !ProviderClass) {
            throw new Error('Invalid type or ProviderClass');
        }
        this._registry.set(type, ProviderClass);
    }

    /**
     * 创建数据源提供者实例
     * @param {string} type - 数据源类型
     * @param {Object} [config={}] - 配置选项
     * @returns {DataSourceProvider} 提供者实例
     */
    create(type, config = {}) {
        const ProviderClass = this._registry.get(type);
        if (!ProviderClass) {
            throw new Error(`Unknown data source type: ${type}`);
        }
        return new ProviderClass(config);
    }

    /**
     * 获取或创建单例提供者
     * @param {string} type - 数据源类型
     * @param {Object} [config={}] - 配置选项
     * @returns {DataSourceProvider} 提供者实例
     */
    getOrCreate(type, config = {}) {
        if (!this._providers.has(type)) {
            const provider = this.create(type, config);
            this._providers.set(type, provider);
        }
        return this._providers.get(type);
    }

    /**
     * 获取所有已注册的数据源类型
     * @returns {string[]}
     */
    getRegisteredTypes() {
        return Array.from(this._registry.keys());
    }

    /**
     * 清理所有提供者实例
     * @async
     * @returns {Promise<void>}
     */
    async cleanup() {
        for (const provider of this._providers.values()) {
            try {
                await provider.close();
            } catch (error) {
                console.error(`Failed to close provider: ${error.message}`);
            }
        }
        this._providers.clear();
    }
}

// 全局工厂实例
const factory = new DataSourceProviderFactory();

// ============================================================================
// 导出
// ============================================================================

module.exports = {
    DataSourceProvider,
    DataSourceProviderFactory,
    DataSourceType,
    factory
};
