/**
 * V87.300 Storage Module
 * ======================
 *
 * Encapsulates PostgreSQL UPSERT logic with connection pool management
 *
 * Core Features:
 *   - Connection Pool Safety (PgBouncer compatible)
 *   - Transaction Management (BEGIN/COMMIT/ROLLBACK)
 *   - Batch Operations (bulk upsert with conflict handling)
 *   - Error Recovery (graceful degradation)
 *
 * V87.300 Enhancements:
 *   - Empty data protection (validates records before UPSERT)
 *   - Empty data alert manager (tracks consecutive empty data)
 *   - Automatic DEBUG_DUMP trigger on threshold breach
 *
 * @module storage
 * @author Senior DevOps & Systems Engineer
 * @version V87.300
 * @since 2026-01-26
 */

'use strict';

const { Client, Pool } = require('pg');
const logger = require('./logger');
const log = logger.createLogger('storage');

// ============================================================================
// CONFIGURATION (Environment Isolation)
// ============================================================================

const getDBConfig = () => ({
    host: process.env.DB_HOST || '172.25.16.1',
    port: parseInt(process.env.DB_PORT) || 5432,
    database: process.env.DB_NAME || 'football_db',
    user: process.env.DB_USER || 'football_user',
    password: process.env.DB_PASSWORD || 'football_pass',
    // Connection pool settings
    max: parseInt(process.env.DB_POOL_MAX) || 20,
    idleTimeoutMillis: parseInt(process.env.DB_IDLE_TIMEOUT) || 30000,
    connectionTimeoutMillis: parseInt(process.env.DB_CONN_TIMEOUT) || 10000
});

// ============================================================================
// ERROR CLASS
// ============================================================================

class StorageError extends Error {
    constructor(type, message, context = {}) {
        super(message);
        this.name = 'StorageError';
        this.errorType = type;
        this.timestamp = new Date().toISOString();
        this.context = context;
    }

    toString() {
        return `[${this.errorType}] [${this.timestamp}] ${this.message}`;
    }
}

// ============================================================================
// CONNECTION MANAGER (Pool-based)
// ============================================================================

/**
 * Create a database connection (single client)
 * @returns {Promise<Client>} - PostgreSQL client
 */
async function createConnection() {
    try {
        const config = getDBConfig();
        const client = new Client({
            host: config.host,
            port: config.port,
            database: config.database,
            user: config.user,
            password: config.password
        });

        await client.connect();
        return client;

    } catch (error) {
        throw new StorageError(
            'CONNECTION_FAILED',
            `Failed to establish database connection: ${error.message}`,
            { originalError: error.message }
        );
    }
}

/**
 * Create a connection pool (for high-throughput scenarios)
 * @returns {Pool} - PostgreSQL connection pool
 */
function createPool() {
    try {
        const config = getDBConfig();
        const pool = new Pool({
            host: config.host,
            port: config.port,
            database: config.database,
            user: config.user,
            password: config.password,
            max: config.max,
            idleTimeoutMillis: config.idleTimeoutMillis,
            connectionTimeoutMillis: config.connectionTimeoutMillis
        });

        // Pool error handler
        pool.on('error', (err) => {
            log.error(`Pool error detected: ${err.message}`, err);
        });

        return pool;

    } catch (error) {
        throw new StorageError(
            'POOL_CREATION_FAILED',
            `Failed to create connection pool: ${error.message}`,
            { originalError: error.message }
        );
    }
}

// ============================================================================
// ENTITY MAPPING
// ============================================================================

/**
 * Get or create entity mapping
 * @param {Client} client - Database client
 * @param {string} sourceId - Source ID
 * @param {string} sourceUrl - Source URL
 * @param {string} entityType - Entity type (default: 'match')
 * @returns {Promise<string>} - Entity ID
 */
async function getOrCreateEntity(client, sourceId, sourceUrl, entityType = 'match') {
    try {
        // Try to find existing entity
        const selectResult = await client.query(
            `SELECT entity_id FROM entities_mapping
             WHERE source_system = 'oddsportal'
             AND source_id = $1
             AND entity_type = $2`,
            [sourceId, entityType]
        );

        if (selectResult.rows.length > 0) {
            return selectResult.rows[0].entity_id;
        }

        // Create new entity
        const insertResult = await client.query(
            `INSERT INTO entities_mapping (source_system, source_id, entity_type, source_url, entity_name)
             VALUES ('oddsportal', $1, $2, $3, $4)
             ON CONFLICT (source_system, source_id, entity_type)
             DO UPDATE SET source_url = EXCLUDED.source_url, entity_name = EXCLUDED.entity_name
             RETURNING entity_id`,
            [sourceId, entityType, sourceUrl, `Match_${sourceId}`]
        );

        return insertResult.rows[0].entity_id;

    } catch (error) {
        throw new StorageError(
            'ENTITY_MAPPING_FAILED',
            `Failed to get or create entity: ${error.message}`,
            { sourceId, entityType }
        );
    }
}

// ============================================================================
// TEMPORAL RECORDS UPSERT
// ============================================================================

/**
 * UPSERT temporal metric records (transaction-safe)
 * @param {Client} client - Database client
 * @param {string} entityId - Entity UUID
 * @param {Array} records - Array of temporal records
 * @returns {Promise<Object>} - Operation result with counts
 */
async function upsertTemporalRecords(client, entityId, records) {
    // V87.300: 空数据保护 - 早期返回，避免无效事务
    if (!records || records.length === 0) {
        log.warn(`[V87.300] 空数据跳过: entityId=${entityId}, records=0`);
        return { inserted: 0, updated: 0, skipped: 0, total: 0, emptyData: true };
    }

    // V87.300: 验证记录有效性（检查必需字段）
    const validRecords = records.filter(r => {
        const isValid = r &&
                        r.provider_name &&
                        (r.value !== undefined && r.value !== null) &&
                        r.occurred_at;

        if (!isValid) {
            log.debug(`[V87.300] 跳过无效记录: ${JSON.stringify(r).substring(0, 100)}`);
        }

        return isValid;
    });

    if (validRecords.length === 0) {
        log.error(`[V87.300] 所有记录均无效，跳过 UPSERT: entityId=${entityId}`);
        return { inserted: 0, updated: 0, skipped: records.length, total: records.length, allInvalid: true };
    }

    if (validRecords.length < records.length) {
        log.warn(`[V87.300] 过滤无效记录: ${records.length} → ${validRecords.length} (跳过 ${records.length - validRecords.length} 条)`);
    }

    await client.query('BEGIN');

    try {
        let inserted = 0;
        let updated = 0;
        let skipped = 0;

        // V95.000: 使用验证后的记录 - 修复 ON CONFLICT 约束匹配
        for (const record of validRecords) {
            try {
                // V95.000: 使用正确的 ON CONFLICT 约束匹配数据库实际结构
                // 约束: (entity_id, provider_name, occurred_at, dimension, sequence)
                const result = await client.query(
                    `INSERT INTO temporal_metric_records
                     (entity_id, provider_name, metric_type, dimension, sequence, value, occurred_at, raw_data)
                     VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                     ON CONFLICT (entity_id, provider_name, occurred_at, dimension, sequence)
                     DO UPDATE SET
                         value = EXCLUDED.value,
                         raw_data = EXCLUDED.raw_data,
                         updated_at = NOW()
                     RETURNING (xmax = 0) AS inserted`,
                    [
                        entityId,
                        record.provider_name,
                        record.metric_type || 'temporal_odds_1x2',
                        record.dimension || 'single',
                        record.sequence || 0,
                        record.value,
                        record.occurred_at,
                        JSON.stringify(record.raw_data || {})
                    ]
                );

                if (result.rows[0].inserted) {
                    inserted++;
                } else {
                    updated++;
                }

            } catch (error) {
                // V95.000: Report actual errors instead of silently skipping
                skipped++;
                log.error(`[V95.000] Record INSERT ERROR: ${error.message.substring(0, 200)}`);
            }
        }

        await client.query('COMMIT');

        // V87.300: 返回详细统计，包含原始记录数和有效记录数
        return {
            inserted,
            updated,
            skipped,
            total: validRecords.length,
            originalTotal: records.length,
            filteredOut: records.length - validRecords.length
        };

    } catch (error) {
        await client.query('ROLLBACK');
        throw new StorageError(
            'UPSERT_FAILED',
            `Batch upsert failed, transaction rolled back: ${error.message}`,
            { recordCount: validRecords.length, originalCount: records.length }
        );
    }
}

// ============================================================================
// BATCH OPERATIONS (High-Throughput)
// ============================================================================

/**
 * Batch upsert with connection pool (for high-volume scenarios)
 * @param {Pool} pool - Connection pool
 * @param {string} entityId - Entity UUID
 * @param {Array} records - Array of temporal records
 * @param {number} batchSize - Batch size (default: 100)
 * @returns {Promise<Object>} - Aggregated operation result
 */
async function batchUpsertWithPool(pool, entityId, records, batchSize = 100) {
    const client = await pool.connect();
    let totalInserted = 0;
    let totalUpdated = 0;
    let totalSkipped = 0;

    try {
        // Process records in batches
        for (let i = 0; i < records.length; i += batchSize) {
            const batch = records.slice(i, i + batchSize);
            const result = await upsertTemporalRecords(client, entityId, batch);

            totalInserted += result.inserted;
            totalUpdated += result.updated;
            totalSkipped += result.skipped;
        }

        return {
            inserted: totalInserted,
            updated: totalUpdated,
            skipped: totalSkipped,
            total: records.length
        };

    } finally {
        client.release();
    }
}

// ============================================================================
// QUERY HELPERS
// ============================================================================

/**
 * Get record count for entity
 * @param {Client} client - Database client
 * @param {string} entityId - Entity UUID
 * @returns {Promise<Object>} - Count statistics
 */
async function getRecordCount(client, entityId) {
    try {
        const result = await client.query(
            `SELECT
                COUNT(*) as total,
                COUNT(DISTINCT provider_name) as providers,
                COUNT(DISTINCT metric_type) as metric_types,
                MIN(occurred_at) as earliest,
                MAX(occurred_at) as latest
             FROM temporal_metric_records
             WHERE entity_id = $1`,
            [entityId]
        );

        return result.rows[0] || { total: 0, providers: 0, metric_types: 0 };

    } catch (error) {
        throw new StorageError(
            'QUERY_FAILED',
            `Failed to get record count: ${error.message}`,
            { entityId }
        );
    }
}

/**
 * Check if entity exists in temporal_metric_records
 * @param {Client} client - Database client
 * @param {string} entityId - Entity UUID
 * @returns {Promise<boolean>} - True if records exist
 */
async function entityHasRecords(client, entityId) {
    try {
        const result = await client.query(
            `SELECT EXISTS(
                SELECT 1 FROM temporal_metric_records
                WHERE entity_id = $1
             ) as exists`,
            [entityId]
        );

        return result.rows[0].exists || false;

    } catch (error) {
        throw new StorageError(
            'QUERY_FAILED',
            `Failed to check entity records: ${error.message}`,
            { entityId }
        );
    }
}

// ============================================================================
// V49.000 FULL-SPECTRUM STORAGE (3D Data Support)
// ============================================================================

/**
 * V49.000: Upsert full temporal records with 1X2 dimensions
 *
 * Each temporal point now stores 3 records (home/draw/away) with:
 * - dimension: 'home' | 'draw' | 'away'
 * - sequence: Temporal order (0, 1, 2, ...)
 * - payout: Calculated return rate
 *
 * @param {Client} client - Database client
 * @param {string} entityId - Entity UUID
 * @param {Array} movementData - Array of full temporal records from parser_v49
 * @returns {Promise<Object>} - Operation result with counts
 *
 * @example
 * const movementData = [
 *   {
 *     timestamp: '2026-01-24T10:00:00Z',
 *     home_odd: 2.50,
 *     draw_odd: 3.20,
 *     away_odd: 2.80,
 *     payout: 0.9423,
 *     sequence: 0,
 *     provider_name: 'pinnacle'
 *   },
 *   ...
 * ];
 * const result = await upsertFullTemporalRecords(client, entityId, movementData);
 * // Returns: { inserted: 30, updated: 0, total_records: 30 }  // 10 points * 3 dimensions
 */
async function upsertFullTemporalRecords(client, entityId, movementData) {
    if (!movementData || movementData.length === 0) {
        return { inserted: 0, updated: 0, skipped: 0, total_records: 0 };
    }

    await client.query('BEGIN');

    try {
        let inserted = 0;
        let updated = 0;
        let skipped = 0;
        let totalRecords = 0;

        // Process each temporal point
        for (const record of movementData) {
            // Insert 3 dimensions for each temporal point
            for (const dimension of ['home', 'draw', 'away']) {
                try {
                    const value = record[`${dimension}_odd`];

                    if (!value || value < 1 || value > 100) {
                        skipped++;
                        continue;
                    }

                    const query = `
                        INSERT INTO temporal_metric_records
                            (entity_id, provider_name, metric_type, dimension,
                             value, occurred_at, sequence, payout, raw_data)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                        ON CONFLICT (entity_id, provider_name, occurred_at, dimension, sequence)
                        DO UPDATE SET
                            value = EXCLUDED.value,
                            payout = EXCLUDED.payout,
                            raw_data = EXCLUDED.raw_data,
                            updated_at = NOW()
                        RETURNING (xmax = 0) AS inserted
                    `;

                    const result = await client.query(query, [
                        entityId,
                        record.provider_name || 'unknown',
                        'temporal_odds_1x2_full',
                        dimension,
                        value,
                        record.timestamp,
                        record.sequence,
                        record.payout,
                        JSON.stringify(record.raw_data || {})
                    ]);

                    totalRecords++;

                    if (result.rows[0].inserted) {
                        inserted++;
                    } else {
                        updated++;
                    }

                } catch (error) {
                    // Single dimension failure doesn't break transaction
                    skipped++;
                    log.error(`[V88.210] Dimension INSERT ERROR [${dimension}]: ${error.message}`);
                    log.error(`[V88.210] Error detail: ${JSON.stringify({
                        code: error.code,
                        detail: error.detail,
                        hint: error.hint,
                        schema: error.schema,
                        table: error.table,
                        constraint: error.constraint
                    })}`);
                }
            }
        }

        await client.query('COMMIT');

        log.info(`V49.000 Full-Spectrum Storage: ${inserted} inserted, ${updated} updated, ${skipped} skipped, ${totalRecords} total records`);

        return {
            inserted,
            updated,
            skipped,
            total_records: totalRecords,
            temporal_points: movementData.length
        };

    } catch (error) {
        await client.query('ROLLBACK');
        throw new StorageError(
            'FULL_SPECTRUM_UPSERT_FAILED',
            `Batch upsert failed, transaction rolled back: ${error.message}`,
            { recordCount: movementData.length }
        );
    }
}

/**
 * V49.000: Get full 1X2 movement data for an entity
 * @param {Client} client - Database client
 * @param {string} entityId - Entity UUID
 * @returns {Promise<Array>} - Full movement array with home/draw/away
 */
async function getFull1X2Movement(client, entityId) {
    try {
        const query = `
            SELECT
                occurred_at,
                sequence,
                MAX(CASE WHEN dimension = 'home' THEN value END) as home_odd,
                MAX(CASE WHEN dimension = 'draw' THEN value END) as draw_odd,
                MAX(CASE WHEN dimension = 'away' THEN value END) as away_odd,
                MAX(payout) as payout
            FROM temporal_metric_records
            WHERE entity_id = $1
              AND metric_type = 'temporal_odds_1x2_full'
            GROUP BY occurred_at, sequence
            ORDER BY sequence
        `;

        const result = await client.query(query, [entityId]);

        return result.rows.map(row => ({
            timestamp: row.occurred_at,
            sequence: row.sequence,
            home_odd: parseFloat(row.home_odd),
            draw_odd: parseFloat(row.draw_odd),
            away_odd: parseFloat(row.away_odd),
            payout: parseFloat(row.payout)
        }));

    } catch (error) {
        throw new StorageError(
            'QUERY_FAILED',
            `Failed to get full 1X2 movement: ${error.message}`,
            { entityId }
        );
    }
}

// ============================================================================
// V87.300: 连续空数据报警机制
// ============================================================================

/**
 * 空数据报警器 - 跟踪连续的空数据情况
 *
 * 当连续出现空数据时，自动触发 DEBUG_DUMP
 */
class EmptyDataAlertManager {
    constructor() {
        this.emptyDataCount = 0;
        this.threshold = 10;  // 连续 10 场空数据触发报警
        this.lastResetTime = Date.now();
        this.alertCallbacks = [];
    }

    /**
     * 记录 UPSERT 结果
     * @param {Object} result - upsertTemporalRecords 的返回值
     * @param {string} entityId - 实体 ID
     * @returns {boolean} - 是否触发报警
     */
    recordUpsertResult(result, entityId) {
        const isEmpty = result.emptyData || result.allInvalid || (result.inserted === 0 && result.updated === 0 && result.total > 0);

        if (isEmpty) {
            this.emptyDataCount++;
            log.warn(`[V87.300] 空数据计数: ${this.emptyDataCount}/${this.threshold} (entityId: ${entityId})`);

            if (this.emptyDataCount >= this.threshold) {
                this._triggerAlert(entityId);
                return true;  // 触发了报警
            }
        } else {
            // 有数据，重置计数器
            if (this.emptyDataCount > 0) {
                log.info(`[V87.300] 空数据重置: ${this.emptyDataCount} → 0 (entityId: ${entityId})`);
            }
            this.emptyDataCount = 0;
            this.lastResetTime = Date.now();
        }

        return false;  // 未触发报警
    }

    /**
     * 注册报警回调
     * @param {Function} callback - 报警触发时的回调函数
     */
    onAlert(callback) {
        this.alertCallbacks.push(callback);
    }

    /**
     * 手动重置计数器
     */
    reset() {
        this.emptyDataCount = 0;
        this.lastResetTime = Date.now();
        log.info('[V87.300] 空数据报警器已手动重置');
    }

    /**
     * 获取当前状态
     */
    getStatus() {
        return {
            emptyDataCount: this.emptyDataCount,
            threshold: this.threshold,
            percentage: (this.emptyDataCount / this.threshold * 100).toFixed(1) + '%',
            timeSinceLastReset: Date.now() - this.lastResetTime
        };
    }

    /**
     * 触发报警
     * @private
     * @param {string} entityId - 触发报警的实体 ID
     */
    _triggerAlert(entityId) {
        const alertMessage = `[V87.300] 🚨 空数据报警触发！连续 ${this.emptyDataCount} 场空数据 (阈值: ${this.threshold})`;

        log.error(alertMessage);
        log.error(`[V87.300] 最后失败实体: ${entityId}`);
        log.error(`[V87.300] 建议: 检查 OneTrust Cookie Consent 横幅是否已处理`);

        // 触发所有注册的回调
        this.alertCallbacks.forEach(callback => {
            try {
                callback({
                    count: this.emptyDataCount,
                    threshold: this.threshold,
                    entityId: entityId,
                    timestamp: new Date().toISOString()
                });
            } catch (error) {
                log.error(`[V87.300] 回调执行失败: ${error.message}`);
            }
        });

        // 重置计数器
        this.emptyDataCount = 0;
    }
}

// 全局单例
const emptyDataAlertManager = new EmptyDataAlertManager();

// ============================================================================
// EXPORTS
// ============================================================================

module.exports = {
    // Connection management
    createConnection,
    createPool,
    getDBConfig,

    // Entity operations
    getOrCreateEntity,

    // Temporal records (V43.200 legacy)
    upsertTemporalRecords,
    batchUpsertWithPool,

    // V49.000 Full-spectrum storage (NEW)
    upsertFullTemporalRecords,
    getFull1X2Movement,

    // Query helpers
    getRecordCount,
    entityHasRecords,

    // Error class
    StorageError,

    // V87.300: 空数据报警管理器
    EmptyDataAlertManager,
    emptyDataAlertManager
};
