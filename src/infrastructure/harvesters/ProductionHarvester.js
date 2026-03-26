/**
 * ProductionHarvester - 生产收割器兼容实现
 * ======================================
 *
 * 为历史测试与现有运行时保留稳定入口：
 * - 基于 AbstractHarvester 复用通用收割流程
 * - 委托 FotMobStrategy 处理 URL/解析
 * - 委托 Persistence 处理数据库与文件双写
 */

'use strict';

const { AbstractHarvester } = require('./base/AbstractHarvester');
const { FotMobStrategy } = require('./strategies/FotMobStrategy');
const { Persistence } = require('./components/Persistence');
const { Normalizer } = require('../../utils/Normalizer');

class ProductionHarvester extends AbstractHarvester {
    /**
     * @param {object} [config]
     */
    constructor(config = {}) {
        const resolvedDataPath = config.dataMatchesPath || process.env.DATA_MATCHES_PATH || 'data/matches';

        super({
            dataMatchesPath: resolvedDataPath,
            ...config
        });

        this.config.dataMatchesPath = resolvedDataPath;
        this.sessionMatchCount = 0;
        this.sessionRotationThreshold = 20;
        this.strategy = new FotMobStrategy(this.config);
        this.persistence = new Persistence({ dataPath: this.config.dataMatchesPath });
        this.db = null;
    }

    /**
     * 初始化收割器并保留数据库别名
     * @returns {Promise<ProductionHarvester>}
     */
    async init() {
        await super.init();
        this.db = this.pool;
        return this;
    }

    /**
     * 清理资源
     * @returns {Promise<void>}
     */
    async cleanup() {
        await super.cleanup();
        this.db = null;
    }

    /**
     * 获取目标 URL
     * @param {object} match
     * @returns {string}
     */
    getTargetUrl(match) {
        const externalId = match?.external_id || String(match?.match_id || '').split('_').pop();
        if (!match || !externalId) {
            throw new Error('子类必须实现 getTargetUrl() 所需 external_id');
        }

        return this.strategy.getTargetUrl({ ...match, external_id: externalId });
    }

    /**
     * 提取数据
     * @param {import('playwright').Page} page
     * @param {object} match
     * @returns {Promise<object>}
     */
    async extractData(page, match) {
        if (!page || !match) {
            throw new Error('子类必须实现 extractData() 所需 page/match 参数');
        }

        return this.strategy.extractData(page, match);
    }

    /**
     * 保存数据
     * @param {string} matchId
     * @param {object} data
     * @returns {Promise<object>}
     */
    async saveData(matchId, data) {
        const dbHandle = this.db || this.pool;
        if (!dbHandle) {
            throw new Error('子类必须实现 saveData() 所需 pool 初始化');
        }

        const parsed = Normalizer.parseMatchId(matchId);
        if (!parsed) {
            throw new Error(`INVALID_MATCH_ID:${matchId}`);
        }

        return this.persistence.dualSave(
            dbHandle,
            parsed.leagueId,
            parsed.seasonTag,
            parsed.externalId,
            data,
            { source: 'ProductionHarvester' }
        );
    }

    /**
     * 获取待处理比赛
     * @param {number} [limit=500]
     * @returns {Promise<object[]>}
     */
    async getPendingMatches(limit = 500) {
        const dbHandle = this.db || this.pool;
        if (!dbHandle || typeof dbHandle.query !== 'function') {
            return [];
        }

        try {
            const result = await dbHandle.query(
                `
                    SELECT match_id, external_id, home_team, away_team
                    FROM matches
                    ORDER BY match_date ASC NULLS LAST, created_at ASC NULLS LAST
                    LIMIT $1
                `,
                [limit]
            );
            return result.rows || [];
        } catch (error) {
            if (this.config.verboseLogging) {
                console.warn(`[ProductionHarvester] getPendingMatches 失败: ${error.message}`);
            }
            return [];
        }
    }

    /**
     * 兼容 SwarmHarvester 的入口
     * @param {object} payload
     * @param {string|number} [payload.matchId]
     * @param {object} [payload.match]
     * @returns {Promise<object>}
     */
    async run(payload = {}) {
        const fallbackMatchId = payload.matchId || payload.match?.match_id || '0_20232024_0';
        const fallbackExternalId = payload.match?.external_id || String(fallbackMatchId).split('_').pop();

        const match = payload.match || {
            match_id: fallbackMatchId,
            external_id: fallbackExternalId,
            home_team: payload.home_team || 'UNKNOWN_HOME',
            away_team: payload.away_team || 'UNKNOWN_AWAY'
        };

        return this.harvestWithRetry(match, 0, this.config.maxRetries);
    }

    /**
     * 数据库错误分类
     * @param {Error} error
     * @returns {string}
     */
    _classifyDatabaseError(error) {
        const message = (error?.message || '').toLowerCase();

        if (message.includes('duplicate key') || error?.code === '23505') {
            return 'DUPLICATE_KEY';
        }
        if (
            message.includes('econnrefused') ||
            message.includes('connection') ||
            error?.code === 'ECONNREFUSED'
        ) {
            return 'CONNECTION_ERROR';
        }
        if (
            message.includes('timeout') ||
            message.includes('timed out') ||
            error?.code === 'ETIMEDOUT'
        ) {
            return 'TIMEOUT';
        }

        return 'UNKNOWN';
    }

    /**
     * 文件错误分类
     * @param {Error} error
     * @returns {string}
     */
    _classifyFileError(error) {
        const message = (error?.message || '').toLowerCase();

        if (message.includes('eacces') || message.includes('permission denied')) {
            return 'PERMISSION_DENIED';
        }
        if (message.includes('enospc') || message.includes('no space left on device')) {
            return 'NO_SPACE';
        }

        return 'UNKNOWN';
    }
}

module.exports = ProductionHarvester;
module.exports.ProductionHarvester = ProductionHarvester;
