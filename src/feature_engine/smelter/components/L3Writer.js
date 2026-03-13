/**
 * L3Writer - V4.0 L3 特征写入器
 * ==============================
 *
 * 负责 l3_features 表的批量写入与冲突处理（UPSERT）。
 * 管理事务，确保特征数据的一致性。
 *
 * @module feature_engine/smelter/components/L3Writer
 * @version V4.0.0-MODULAR
 * @since 2026-03-14
 */

'use strict';

const { BaseExtractor, ExtractorError } = require('./BaseExtractor');

// ============================================================================
// 配置常量
// ============================================================================

const DEFAULT_CONFIG = {
    batchSize: 100,           // 每批写入数量
    maxRetries: 3,            // 最大重试次数
    retryDelayMs: 1000,       // 初始重试延迟
    enableTransaction: true,  // 是否启用事务
    onConflict: 'upsert'      // 冲突处理: 'upsert' | 'skip' | 'error'
};

// SQL 语句
const SQL = {
    // UPSERT 单条记录
    upsertFeature: `
        INSERT INTO l3_features (
            match_id,
            external_id,
            golden_features,
            tactical_features,
            odds_movement_features,
            elo_features,
            computed_at
        ) VALUES ($1, $2, $3, $4, $5, $6, $7)
        ON CONFLICT (match_id) DO UPDATE SET
            external_id = EXCLUDED.external_id,
            golden_features = EXCLUDED.golden_features,
            tactical_features = EXCLUDED.tactical_features,
            odds_movement_features = EXCLUDED.odds_movement_features,
            elo_features = EXCLUDED.elo_features,
            computed_at = EXCLUDED.computed_at
    `,

    // 插入单条记录（跳过冲突）
    insertFeatureSkip: `
        INSERT INTO l3_features (
            match_id,
            external_id,
            golden_features,
            tactical_features,
            odds_movement_features,
            elo_features,
            computed_at
        ) VALUES ($1, $2, $3, $4, $5, $6, $7)
        ON CONFLICT (match_id) DO NOTHING
    `,

    // 批量插入（使用 unnest）
    bulkInsert: `
        INSERT INTO l3_features (
            match_id,
            external_id,
            golden_features,
            tactical_features,
            odds_movement_features,
            elo_features,
            computed_at
        ) SELECT * FROM UNNEST($1::text[], $2::text[], $3::jsonb[], $4::jsonb[], $5::jsonb[], $6::jsonb[], $7::timestamptz[])
        ON CONFLICT (match_id) DO UPDATE SET
            external_id = EXCLUDED.external_id,
            golden_features = EXCLUDED.golden_features,
            tactical_features = EXCLUDED.tactical_features,
            odds_movement_features = EXCLUDED.odds_movement_features,
            elo_features = EXCLUDED.elo_features,
            computed_at = EXCLUDED.computed_at
    `,

    // 删除旧记录
    deleteByMatchId: `
        DELETE FROM l3_features WHERE match_id = $1
    `,

    // 检查记录是否存在
    checkExists: `
        SELECT 1 FROM l3_features WHERE match_id = $1 LIMIT 1
    `
};

// ============================================================================
// L3Writer 类
// ============================================================================

/**
 * L3 特征写入器
 */
class L3Writer extends BaseExtractor {
    /**
     * @param {object} options - 配置选项
     * @param {object} options.pool - 数据库连接池（必填）
     */
    constructor(options = {}) {
        super({
            name: 'L3Writer',
            version: 'V4.0.0-MODULAR',
            requiredFields: [],
            config: { ...DEFAULT_CONFIG, ...(options.config || {}) }
        });

        if (!options.pool) {
            throw new ExtractorError(
                'L3Writer 需要数据库连接池',
                'MISSING_POOL',
                { options }
            );
        }

        this.pool = options.pool;
    }

    /**
     * 获取默认配置
     * @returns {object}
     */
    getDefaultConfig() {
        return DEFAULT_CONFIG;
    }

    /**
     * 获取特征字段名清单（L3Writer 不产生特征）
     * @returns {Array<string>}
     */
    getFeatureNames() {
        return [];
    }

    /**
     * 执行提取（L3Writer 不使用此方法）
     */
    extract(rawData, context = {}) {
        throw new ExtractorError(
            'L3Writer 不支持 extract 方法，请使用专用方法如 saveFeatures()',
            'UNSUPPORTED_OPERATION',
            { extractor: this.name }
        );
    }

    // ========================================================================
    // 核心写入方法
    // ========================================================================

    /**
     * 保存单条特征记录
     * @param {object} feature - 特征对象
     * @param {string} feature.match_id - 比赛 ID
     * @param {string} feature.external_id - 外部 ID
     * @param {object} feature.golden_features - 黄金特征
     * @param {object} feature.tactical_features - 战术特征
     * @param {object} feature.odds_movement_features - 赔率特征
     * @param {object} feature.elo_features - Elo 特征
     * @param {string} feature.computed_at - 计算时间
     * @returns {Promise<boolean>} 是否成功
     */
    async saveFeature(feature) {
        if (!this._validateFeature(feature)) {
            this.logger.warn('特征验证失败，跳过保存', { match_id: feature?.match_id });
            return false;
        }

        this.stats.totalCalls++;
        const startTime = Date.now();

        try {
            const sql = this.config.onConflict === 'skip'
                ? SQL.insertFeatureSkip
                : SQL.upsertFeature;

            await this._queryWithRetry(sql, [
                feature.match_id,
                feature.external_id || feature.match_id,
                JSON.stringify(feature.golden_features),
                JSON.stringify(feature.tactical_features),
                JSON.stringify(feature.odds_movement_features),
                JSON.stringify(feature.elo_features),
                feature.computed_at || new Date().toISOString()
            ]);

            this.stats.successfulCalls++;
            this._updateExecutionTime(Date.now() - startTime);

            this.logger.debug('特征保存成功', { match_id: feature.match_id });
            return true;

        } catch (error) {
            this.stats.failedCalls++;
            this.logger.error('特征保存失败', {
                match_id: feature.match_id,
                error: error.message
            });
            return false;
        }
    }

    /**
     * 批量保存特征记录（事务保证）
     * @param {Array<object>} features - 特征数组
     * @returns {Promise<object>} { saved: number, failed: number, errors: Array }
     */
    async saveFeatures(features) {
        if (!features || features.length === 0) {
            return { saved: 0, failed: 0, errors: [] };
        }

        this.stats.totalCalls++;
        const startTime = Date.now();

        const result = {
            saved: 0,
            failed: 0,
            errors: []
        };

        // 验证所有特征
        const validFeatures = features.filter(f => {
            const isValid = this._validateFeature(f);
            if (!isValid) {
                result.failed++;
                result.errors.push({ match_id: f?.match_id, error: 'Validation failed' });
            }
            return isValid;
        });

        if (validFeatures.length === 0) {
            return result;
        }

        // 分批处理
        const batches = this._chunkArray(validFeatures, this.config.batchSize);

        for (const batch of batches) {
            try {
                if (this.config.enableTransaction) {
                    // 使用事务批量写入
                    const batchResult = await this._saveBatchWithTransaction(batch);
                    result.saved += batchResult.saved;
                    result.failed += batchResult.failed;
                    result.errors.push(...batchResult.errors);
                } else {
                    // 逐条写入
                    for (const feature of batch) {
                        const success = await this.saveFeature(feature);
                        if (success) {
                            result.saved++;
                        } else {
                            result.failed++;
                        }
                    }
                }
            } catch (error) {
                this.logger.error('批量保存失败', {
                    batchSize: batch.length,
                    error: error.message
                });
                result.failed += batch.length;
                result.errors.push({ batch: true, error: error.message });
            }
        }

        this.stats.successfulCalls++;
        this._updateExecutionTime(Date.now() - startTime);

        this.logger.info('批量保存完成', {
            total: features.length,
            saved: result.saved,
            failed: result.failed
        });

        return result;
    }

    /**
     * 使用 unnest 进行高性能批量插入
     * @param {Array<object>} features - 特征数组
     * @returns {Promise<number>} 插入数量
     */
    async bulkInsert(features) {
        if (!features || features.length === 0) {
            return 0;
        }

        this.stats.totalCalls++;
        const startTime = Date.now();

        // 验证并准备数据
        const validFeatures = features.filter(f => this._validateFeature(f));

        if (validFeatures.length === 0) {
            return 0;
        }

        try {
            // 准备 unnest 数组
            const matchIds = [];
            const externalIds = [];
            const goldenFeatures = [];
            const tacticalFeatures = [];
            const oddsFeatures = [];
            const eloFeatures = [];
            const computedAts = [];

            for (const f of validFeatures) {
                matchIds.push(f.match_id);
                externalIds.push(f.external_id || f.match_id);
                goldenFeatures.push(JSON.stringify(f.golden_features));
                tacticalFeatures.push(JSON.stringify(f.tactical_features));
                oddsFeatures.push(JSON.stringify(f.odds_movement_features));
                eloFeatures.push(JSON.stringify(f.elo_features));
                computedAts.push(f.computed_at || new Date().toISOString());
            }

            await this._queryWithRetry(SQL.bulkInsert, [
                matchIds,
                externalIds,
                goldenFeatures,
                tacticalFeatures,
                oddsFeatures,
                eloFeatures,
                computedAts
            ]);

            this.stats.successfulCalls++;
            this._updateExecutionTime(Date.now() - startTime);

            this.logger.info('高性能批量插入完成', {
                count: validFeatures.length,
                timeMs: Date.now() - startTime
            });

            return validFeatures.length;

        } catch (error) {
            this.stats.failedCalls++;
            this.logger.error('高性能批量插入失败', {
                count: validFeatures.length,
                error: error.message
            });
            throw error;
        }
    }

    // ========================================================================
    // 事务管理
    // ========================================================================

    /**
     * 使用事务保存批次
     * @private
     * @param {Array<object>} batch - 特征批次
     * @returns {Promise<object>} { saved: number, failed: number, errors: Array }
     */
    async _saveBatchWithTransaction(batch) {
        const client = await this.pool.connect();
        const result = { saved: 0, failed: 0, errors: [] };

        try {
            await client.query('BEGIN');

            for (const feature of batch) {
                try {
                    const sql = this.config.onConflict === 'skip'
                        ? SQL.insertFeatureSkip
                        : SQL.upsertFeature;

                    await client.query(sql, [
                        feature.match_id,
                        feature.external_id || feature.match_id,
                        JSON.stringify(feature.golden_features),
                        JSON.stringify(feature.tactical_features),
                        JSON.stringify(feature.odds_movement_features),
                        JSON.stringify(feature.elo_features),
                        feature.computed_at || new Date().toISOString()
                    ]);

                    result.saved++;
                } catch (error) {
                    result.failed++;
                    result.errors.push({
                        match_id: feature.match_id,
                        error: error.message
                    });

                    // 如果配置为遇到错误即中止，则抛出
                    if (this.config.onConflict === 'error') {
                        throw error;
                    }
                }
            }

            await client.query('COMMIT');
            return result;

        } catch (error) {
            await client.query('ROLLBACK');
            throw error;
        } finally {
            client.release();
        }
    }

    // ========================================================================
    // 辅助方法
    // ========================================================================

    /**
     * 验证特征对象
     * @private
     * @param {object} feature - 特征对象
     * @returns {boolean}
     */
    _validateFeature(feature) {
        if (!feature || typeof feature !== 'object') {
            return false;
        }

        // 检查必需字段
        if (!feature.match_id) {
            return false;
        }

        // 检查特征对象是否存在
        if (!feature.golden_features || !feature.tactical_features ||
            !feature.odds_movement_features || !feature.elo_features) {
            return false;
        }

        return true;
    }

    /**
     * 将数组分块
     * @private
     * @param {Array} array - 源数组
     * @param {number} size - 块大小
     * @returns {Array<Array>}
     */
    _chunkArray(array, size) {
        const chunks = [];
        for (let i = 0; i < array.length; i += size) {
            chunks.push(array.slice(i, i + size));
        }
        return chunks;
    }

    // ========================================================================
    // 重试与错误处理
    // ========================================================================

    /**
     * 带重试的查询
     * @private
     * @param {string} query - SQL 查询
     * @param {Array} params - 查询参数
     * @returns {Promise<object>}
     */
    async _queryWithRetry(query, params) {
        let lastError;
        let delay = this.config.retryDelayMs;

        for (let attempt = 0; attempt < this.config.maxRetries; attempt++) {
            try {
                return await this.pool.query(query, params);
            } catch (error) {
                lastError = error;

                if (!this._isRetryableError(error)) {
                    throw error;
                }

                this.logger.warn(`写入失败，${this.config.maxRetries - attempt - 1} 次重试剩余`, {
                    attempt: attempt + 1,
                    error: error.message
                });

                await this._sleep(delay);
                delay *= 2;
            }
        }

        throw lastError;
    }

    /**
     * 检查错误是否可重试
     * @private
     * @param {Error} error - 错误对象
     * @returns {boolean}
     */
    _isRetryableError(error) {
        if (!error) return false;

        const retryableCodes = [
            'ECONNRESET',
            'ETIMEDOUT',
            'ECONNREFUSED',
            '08000',
            '08003',
            '08006',
            '40001',
            '40P01'  // deadlock_detected
        ];

        return retryableCodes.some(code =>
            error.code === code ||
            (error.message && error.message.includes(code))
        );
    }

    /**
     * 睡眠
     * @private
     * @param {number} ms - 毫秒
     * @returns {Promise<void>}
     */
    _sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    /**
     * 更新执行时间
     * @private
     * @param {number} executionTime - 执行时间
     */
    _updateExecutionTime(executionTime) {
        const { successfulCalls } = this.stats;
        if (successfulCalls === 1) {
            this.stats.avgExecutionTimeMs = executionTime;
        } else {
            this.stats.avgExecutionTimeMs =
                (this.stats.avgExecutionTimeMs * (successfulCalls - 1) + executionTime) / successfulCalls;
        }
    }
}

// ============================================================================
// 导出
// ============================================================================
module.exports = {
    L3Writer,
    SQL,
    DEFAULT_CONFIG
};
