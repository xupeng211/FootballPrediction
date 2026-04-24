/* eslint-disable complexity, max-lines */
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
        this.config.bulkProgressEvery = this._resolveProgressInterval(
            config.bulkProgressEvery || process.env.BULK_PROGRESS_EVERY || 100
        );
        this.config.pressureFailureThreshold = this._resolvePressureFailureThreshold(
            config.pressureFailureThreshold || process.env.PRESSURE_FAILURE_THRESHOLD || 3
        );
        this.config.pressureCooldownMs = this._resolvePressureCooldownMs(
            config.pressureCooldownMs || process.env.PRESSURE_COOLDOWN_MS || 30000
        );
        this.config.browserRecycleEvery = this._resolveBrowserRecycleEvery(
            config.browserRecycleEvery || process.env.BROWSER_RECYCLE_EVERY || 200
        );
        this.config.browserRecycleRssBytes = this._resolveBrowserRecycleRssBytes(
            config.browserRecycleRssBytes || process.env.BROWSER_RECYCLE_RSS_BYTES || (1.5 * 1024 * 1024 * 1024)
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
        await this.persistence.flushPendingWrites();
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
     * @param {object} [filters={}]
     * @returns {Promise<object[]>}
     * @throws {Error} 当数据库查询失败时抛出
     */
    async getPendingMatches(limit = 500, filters = {}) {
        const dbHandle = this.db || this.pool;
        if (!dbHandle || typeof dbHandle.query !== 'function') {
            return [];
        }

        try {
            const statusColumn = await this.persistence.ensurePipelineStatusSchema(dbHandle);
            const pendingPredicate = statusColumn === 'pipeline_status'
                ? `COALESCE(m.pipeline_status, 'pending') = 'pending'`
                : `COALESCE(m.status, 'pending') != 'harvested'`;
            const normalizedFilters = this._normalizePendingFilters(filters);
            const conditions = [
                'r.match_id IS NULL',
                pendingPredicate
            ];
            const params = [limit];

            if (normalizedFilters.leagueIds.length > 0) {
                params.push(normalizedFilters.leagueIds);
                conditions.push(`split_part(m.match_id, '_', 1) = ANY($${params.length}::text[])`);
            }

            if (normalizedFilters.season) {
                params.push(normalizedFilters.season);
                conditions.push(`m.season = $${params.length}`);
            }

            if (normalizedFilters.dateFrom) {
                params.push(normalizedFilters.dateFrom.toISOString());
                conditions.push(`m.match_date >= $${params.length}::timestamptz`);
            }

            if (normalizedFilters.dateTo) {
                params.push(normalizedFilters.dateTo.toISOString());
                conditions.push(`m.match_date < $${params.length}::timestamptz`);
            }

            if (normalizedFilters.finishedOnly) {
                conditions.push('COALESCE(m.is_finished, false) = true');
            }

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
                    WHERE ${conditions.join('\n                      AND ')}
                    ORDER BY m.match_date ASC NULLS LAST, m.match_id ASC, m.created_at ASC NULLS LAST
                    LIMIT $1
                `,
                params
            );
            return (result.rows || []).sort((a, b) => a.match_id.localeCompare(b.match_id));
        } catch (error) {
            throw new Error(`[ProductionHarvester] getPendingMatches 失败: ${error.message}`);
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
     * @returns {Promise<object>} 批量执行结果
     * @throws {Error} 当待处理比赛查询失败时抛出 BULK_ABORT 错误
     */
    async runBulk(payload = {}) {
        const targetLimit = this._resolveTargetLimit(payload.limit);
        const fetchSize = this._resolveBatchLimit(payload.fetchSize || this.config.batchSize);
        const concurrency = this._resolveBulkConcurrency(
            payload.concurrency || this.config.bulkConcurrency || this.config.maxWorkers
        );
        const progressEvery = this._resolveProgressInterval(
            payload.progressEvery || this.config.bulkProgressEvery
        );
        const captureResults = payload.captureResults === true || this.config.captureBulkResults === true;
        const pendingMatchFilters = this._normalizePendingFilters(payload);

        this._ensureContextPoolCapacity(concurrency);

        const state = {
            startedAt: Date.now(),
            total: 0,
            success: 0,
            failed: 0,
            batches: 0,
            totalDurationMs: 0,
            progressEvery,
            targetLimit,
            captureResults,
            results: captureResults ? [] : [],
            lastBrowserRecycleAt: 0,
            browserRecycles: 0
        };

        while (state.total < targetLimit) {
            const remaining = Number.isFinite(targetLimit)
                ? Math.max(0, targetLimit - state.total)
                : fetchSize;

            if (remaining === 0) {
                break;
            }

            const recycleWindow = this._resolveRecycleWindow(fetchSize, state);
            const batchLimit = Number.isFinite(targetLimit)
                ? Math.min(fetchSize, remaining, recycleWindow)
                : Math.min(fetchSize, recycleWindow);

            let pendingMatches;
            try {
                pendingMatches = await this.getPendingMatches(batchLimit, pendingMatchFilters);
            } catch (error) {
                const wrapped = new Error(
                    `[BULK_ABORT] 待处理比赛查询失败: batch=${state.batches + 1} processed=${state.total} message=${error.message}`
                );
                wrapped.code = 'PENDING_MATCH_QUERY_FAILED';
                wrapped.cause = error;
                throw wrapped;
            }

            if (pendingMatches.length === 0) {
                break;
            }

            state.batches++;
            const batchResults = await this._runConcurrentBatch(pendingMatches, concurrency, state);
            const pressureFailures = batchResults.filter(result => this._isPressureFailure(result)).length;

            if (pressureFailures >= this.config.pressureFailureThreshold) {
                console.warn(
                    `[BACKPRESSURE] 本批次出现 ${pressureFailures} 个限流/超时类失败，暂停 ${this.config.pressureCooldownMs}ms 后继续`
                );
                await this._delay(this.config.pressureCooldownMs);
            }

            if (!Number.isFinite(targetLimit) || state.total < targetLimit) {
                await this._maybeRecycleBrowser(state);
            }
        }

        if (state.total > 0 && state.total % progressEvery !== 0) {
            this._logProgressSnapshot(state, { force: true });
        }

        return {
            mode: 'bulk',
            total: state.total,
            success: state.success,
            failed: state.failed,
            concurrency,
            batches: state.batches,
            browserRecycles: state.browserRecycles,
            requestedLimit: Number.isFinite(targetLimit) ? targetLimit : 'ALL',
            filters: {
                leagueIds: pendingMatchFilters.leagueIds,
                season: pendingMatchFilters.season,
                dateFrom: pendingMatchFilters.dateFrom ? pendingMatchFilters.dateFrom.toISOString() : null,
                dateTo: pendingMatchFilters.dateTo ? pendingMatchFilters.dateTo.toISOString() : null,
                finishedOnly: pendingMatchFilters.finishedOnly
            },
            results: state.results
        };
    }

    async _runConcurrentBatch(pendingMatches, concurrency, state) {
        const limiter = pLimit(concurrency);
        const batchOffset = state.total;

        return Promise.all(
            pendingMatches.map((match, index) => limiter(async () => {
                const globalIndex = batchOffset + index;
                let result;

                try {
                    result = await this.harvestWithRetry(match, globalIndex, this.config.maxRetries);
                } catch (error) {
                    result = {
                        success: false,
                        match_id: match.match_id,
                        error: error.message
                    };
                }

                this._recordBulkProgress(state, result);
                return result;
            }))
        );
    }

    _recordBulkProgress(state, result) {
        state.total++;

        if (result?.success) {
            state.success++;
        } else {
            state.failed++;
        }

        if (typeof result?.duration === 'number' && Number.isFinite(result.duration)) {
            state.totalDurationMs += result.duration;
        }

        if (state.captureResults) {
            state.results.push(result);
        }

        if (state.progressEvery > 0 && state.total % state.progressEvery === 0) {
            this._logProgressSnapshot(state);
        }
    }

    _logProgressSnapshot(state, options = {}) {
        const elapsedMs = Math.max(1, Date.now() - state.startedAt);
        const elapsedSeconds = elapsedMs / 1000;
        const throughput = state.total / elapsedSeconds;
        const avgPerMatchSeconds = state.total > 0 ? elapsedSeconds / state.total : 0;
        const memory = this._getProcessMemoryUsage();
        const limitDisplay = Number.isFinite(state.targetLimit) ? state.targetLimit : '?';

        let etaText = 'ETA=未知';
        if (Number.isFinite(state.targetLimit) && throughput > 0) {
            const remaining = Math.max(0, state.targetLimit - state.total);
            const etaSeconds = remaining / throughput;
            etaText = `ETA=${etaSeconds.toFixed(1)}s`;
        }

        console.log(
            `[PROGRESS] 已完成 ${state.total}/${limitDisplay} | success=${state.success} failed=${state.failed} | ` +
            `elapsed=${elapsedSeconds.toFixed(1)}s avg=${avgPerMatchSeconds.toFixed(2)}s | ` +
            `rss=${this._formatMemoryMb(memory.rss)}MB heap=${this._formatMemoryMb(memory.heapUsed)}MB | ${etaText}`
        );

        if (options.force && state.total === 0) {
            console.log('[PROGRESS] 当前没有可处理比赛');
        }
    }

    async _maybeRecycleBrowser(state) {
        const memory = this._getProcessMemoryUsage();
        const reasons = [];
        const processedSinceRecycle = state.total - state.lastBrowserRecycleAt;

        if (this.config.browserRecycleEvery > 0 && processedSinceRecycle >= this.config.browserRecycleEvery) {
            reasons.push(`processed=${processedSinceRecycle}`);
        }

        if (this.config.browserRecycleRssBytes > 0 && memory.rss >= this.config.browserRecycleRssBytes) {
            reasons.push(`rss=${this._formatMemoryMb(memory.rss)}MB`);
        }

        if (reasons.length === 0) {
            return false;
        }

        console.warn(`[BROWSER-RECYCLE] 触发浏览器回收: ${reasons.join(', ')}`);
        await this._recycleBrowserFactory();
        state.lastBrowserRecycleAt = state.total;
        state.browserRecycles++;
        return true;
    }

    async _recycleBrowserFactory() {
        await this._cleanupContextPool();
        if (this.browserFactory) {
            await this.browserFactory.close();
            await this.browserFactory.launch();
        }
    }

    _resolveRecycleWindow(fetchSize, state) {
        if (!(this.config.browserRecycleEvery > 0)) {
            return fetchSize;
        }

        const processedSinceRecycle = state.total - state.lastBrowserRecycleAt;
        const remainingUntilRecycle = this.config.browserRecycleEvery - processedSinceRecycle;
        if (remainingUntilRecycle <= 0) {
            return Math.max(1, Math.min(fetchSize, this.config.browserRecycleEvery));
        }

        return Math.max(1, Math.min(fetchSize, remainingUntilRecycle));
    }

    _isPressureFailure(result) {
        if (!result || result.success) {
            return false;
        }

        const signature = `${result.errorType || ''} ${result.error || ''}`.toLowerCase();
        return /429|too many requests|blocked|turnstile|403|timeout|timed out|econnreset|econnrefused|etimedout|retryable_resource_error/.test(signature);
    }

    _resolveBatchLimit(limit) {
        const parsed = Number.parseInt(limit, 10);
        return Number.isFinite(parsed) && parsed > 0 ? parsed : 500;
    }

    _resolveTargetLimit(limit) {
        if (limit === undefined || limit === null || limit === '') {
            return Number.POSITIVE_INFINITY;
        }

        const parsed = Number.parseInt(limit, 10);
        return Number.isFinite(parsed) && parsed > 0 ? parsed : Number.POSITIVE_INFINITY;
    }

    _resolveBulkConcurrency(value) {
        const parsed = Number.parseInt(value, 10);
        const fallback = Number.isFinite(parsed) ? parsed : 10;
        return Math.min(15, Math.max(8, fallback));
    }

    _resolveProgressInterval(value) {
        const parsed = Number.parseInt(value, 10);
        return Number.isFinite(parsed) && parsed > 0 ? parsed : 100;
    }

    _resolvePressureFailureThreshold(value) {
        const parsed = Number.parseInt(value, 10);
        return Number.isFinite(parsed) && parsed > 0 ? parsed : 3;
    }

    _resolvePressureCooldownMs(value) {
        const parsed = Number.parseInt(value, 10);
        return Number.isFinite(parsed) && parsed > 0 ? parsed : 30000;
    }

    _resolveBrowserRecycleEvery(value) {
        const parsed = Number.parseInt(value, 10);
        return Number.isFinite(parsed) && parsed > 0 ? parsed : 200;
    }

    _resolveBrowserRecycleRssBytes(value) {
        const parsed = Number.parseInt(value, 10);
        return Number.isFinite(parsed) && parsed > 0 ? parsed : Math.floor(1.5 * 1024 * 1024 * 1024);
    }

    _normalizePendingFilters(filters = {}) {
        return {
            leagueIds: this._normalizeLeagueIds(filters.leagueIds),
            season: this._normalizeOptionalString(filters.season),
            dateFrom: this._normalizeDateFilter(filters.dateFrom, 'dateFrom'),
            dateTo: this._normalizeDateFilter(filters.dateTo, 'dateTo'),
            finishedOnly: filters.finishedOnly === true
        };
    }

    _normalizeLeagueIds(value) {
        const rawValues = Array.isArray(value)
            ? value
            : String(value || '')
                .split(',')
                .map((entry) => entry.trim())
                .filter(Boolean);

        return [...new Set(
            rawValues
                .map((entry) => Number.parseInt(entry, 10))
                .filter((entry) => Number.isInteger(entry) && entry > 0)
                .map((entry) => String(entry))
        )];
    }

    _normalizeOptionalString(value) {
        const normalized = String(value || '').trim();
        return normalized || null;
    }

    _normalizeDateFilter(value, fieldName) {
        if (value === undefined || value === null || value === '') {
            return null;
        }

        const parsed = value instanceof Date ? value : new Date(value);
        if (Number.isNaN(parsed.getTime())) {
            throw new Error(`[ProductionHarvester] ${fieldName} 无法解析: ${value}`);
        }
        return parsed;
    }

    _getProcessMemoryUsage() {
        return process.memoryUsage();
    }

    _formatMemoryMb(bytes) {
        return (bytes / 1024 / 1024).toFixed(1);
    }

}

module.exports = ProductionHarvester;
module.exports.ProductionHarvester = ProductionHarvester;
