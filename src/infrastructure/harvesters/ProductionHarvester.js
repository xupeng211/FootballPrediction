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

const pLimit = require('p-limit');

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
        this.config.bulkConcurrency = this._resolveBulkConcurrency(
            config.bulkConcurrency || config.maxWorkers || 10
        );
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
        await this.persistence.ensurePipelineStatusSchema(this.pool);
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
            const statusColumn = await this.persistence.ensurePipelineStatusSchema(dbHandle);
            const pendingPredicate = statusColumn === 'pipeline_status'
                ? `COALESCE(m.pipeline_status, 'pending') = 'pending'`
                : `COALESCE(m.status, 'pending') != 'harvested'`;
            const result = await dbHandle.query(
                `
                    SELECT
                        m.match_id,
                        m.external_id,
                        m.home_team,
                        m.away_team,
                        m.match_date
                    FROM matches m
                    LEFT JOIN raw_match_data r ON m.match_id = r.match_id
                    WHERE r.match_id IS NULL
                      AND ${pendingPredicate}
                    ORDER BY m.match_id ASC, m.match_date ASC NULLS LAST, m.created_at ASC NULLS LAST
                    LIMIT $1
                `,
                [limit]
            );
            return (result.rows || []).sort((a, b) => a.match_id.localeCompare(b.match_id));
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
        if (!payload.match && !payload.matchId) {
            return this.runBulk(payload);
        }

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
     * 批量收割入口
     * @param {object} payload
     * @param {number} [payload.limit]
     * @param {number} [payload.concurrency]
     * @returns {Promise<object>}
     */
    async runBulk(payload = {}) {
        const limit = this._resolveBatchLimit(payload.limit || this.config.batchSize);
        const concurrency = this._resolveBulkConcurrency(
            payload.concurrency || this.config.bulkConcurrency || this.config.maxWorkers
        );

        const pendingMatches = await this.getPendingMatches(limit);
        if (pendingMatches.length === 0) {
            return {
                mode: 'bulk',
                total: 0,
                success: 0,
                failed: 0,
                concurrency,
                results: []
            };
        }

        const limiter = pLimit(concurrency);
        const results = await Promise.all(
            pendingMatches.map((match, index) => limiter(async () => {
                try {
                    return await this.harvestWithRetry(match, index, this.config.maxRetries);
                } catch (error) {
                    return {
                        success: false,
                        match_id: match.match_id,
                        error: error.message
                    };
                }
            }))
        );

        const success = results.filter(result => result?.success).length;
        const failed = results.length - success;

        return {
            mode: 'bulk',
            total: results.length,
            success,
            failed,
            concurrency,
            results
        };
    }

    _resolveBatchLimit(limit) {
        const parsed = Number.parseInt(limit, 10);
        return Number.isFinite(parsed) && parsed > 0 ? parsed : 500;
    }

    _resolveBulkConcurrency(value) {
        const parsed = Number.parseInt(value, 10);
        const fallback = Number.isFinite(parsed) ? parsed : 10;
        return Math.min(12, Math.max(8, fallback));
    }

}

module.exports = ProductionHarvester;
module.exports.ProductionHarvester = ProductionHarvester;
