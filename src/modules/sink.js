/**
 * V66.000 - Data Sink Module
 * ===========================
 *
 * Database persistence layer with idempotent upsert and transaction management.
 * Ensures data consistency and proper resource cleanup.
 *
 * @module modules/sink
 * @author Principal Software Architect
 * @version V66.000
 * @since 2026-01-25
 */

'use strict';

const { Pool } = require('pg');
const { generateTraceId } = require('../core/retry');

// ============================================================================
// CONFIGURATION
// ============================================================================

const SINK_CONFIG = {
    // Connection pool settings
    poolMax: parseInt(process.env.DB_POOL_MAX) || 20,
    poolMin: parseInt(process.env.DB_POOL_MIN) || 2,
    idleTimeout: parseInt(process.env.DB_IDLE_TIMEOUT) || 30000,
    connectionTimeout: parseInt(process.env.DB_CONN_TIMEOUT) || 10000,

    // Transaction settings
    statementTimeout: parseInt(process.env.STATEMENT_TIMEOUT) || 30000,
    queryTimeout: parseInt(process.env.QUERY_TIMEOUT) || 60000,

    // Batch settings
    defaultBatchSize: parseInt(process.env.BATCH_SIZE) || 100,

    // Idempotency settings
    conflictResolution: 'EXCLUDED'  // Use EXCLUDED for idempotent updates
};

// ============================================================================
// ERROR CLASS
// ============================================================================

class SinkError extends Error {
    constructor(code, message, traceId = null, context = {}) {
        super(message);
        this.name = 'SinkError';
        this.errorCode = code;
        this.traceId = traceId || generateTraceId();
        this.timestamp = new Date().toISOString();
        this.context = context;
    }

    toJSON() {
        return {
            error_code: this.errorCode,
            trace_id: this.traceId,
            timestamp: this.timestamp,
            message: this.message,
            context: this.context
        };
    }
}

// ============================================================================
// DATABASE CONNECTION
// ============================================================================>

/**
 * Create a connection pool
 * @param {Object} [config={}] - Configuration overrides
 * @returns {Pool} - PostgreSQL connection pool
 */
function createPool(config = {}) {
    const finalConfig = { ...SINK_CONFIG, ...config };

    const pool = new Pool({
        host: process.env.DB_HOST || '172.25.16.1',
        port: parseInt(process.env.DB_PORT) || 5432,
        database: process.env.DB_NAME || 'football_db',
        user: process.env.DB_USER || 'football_user',
        password: process.env.DB_PASSWORD || 'football_pass',
        max: finalConfig.poolMax,
        min: finalConfig.poolMin,
        idleTimeoutMillis: finalConfig.idleTimeout,
        connectionTimeoutMillis: finalConfig.connectionTimeout,
        statementTimeout: finalConfig.statementTimeout
    });

    // Pool error handler
    pool.on('error', (err) => {
        console.error(JSON.stringify({
            level: 'error',
            module: 'modules/sink/pool',
            message: 'Pool error',
            error: err.message
        }));
    });

    return pool;
}

// ============================================================================
// ENTITY MAPPING
// ============================================================================

/**
 * Get or create entity mapping
 * @param {import('pg').PoolClient} client - Database client
 * @param {string} sourceId - Source identifier
 * @param {string} sourceUrl - Source URL
 * @param {string} [entityType='match'] - Entity type
 * @returns {Promise<string>} - Entity UUID
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
        throw new SinkError(
            'ENTITY_MAPPING_FAILED',
            `Failed to get or create entity: ${error.message}`,
            null,
            { sourceId, entityType }
        );
    }
}

// ============================================================================
// IDEMPOPENT UPSERT
// ============================================================================

/**
 * Idempotent upsert for temporal metric records
 *
 * Ensures that repeated execution with the same data produces identical results.
 * Uses ON CONFLICT DO UPDATE to handle duplicate keys.
 *
 * @param {import('pg').PoolClient} client - Database client
 * @param {string} entityId - Entity UUID
 * @param {Array} records - Array of temporal records
 * @returns {Promise<Object>} - Operation result with counts
 */
async function upsertTemporalRecords(client, entityId, records) {
    if (!records || records.length === 0) {
        return { inserted: 0, updated: 0, skipped: 0, total: 0 };
    }

    const traceId = generateTraceId();
    let inserted = 0;
    let updated = 0;
    let skipped = 0;

    try {
        await client.query('BEGIN');

        for (const record of records) {
            try {
                const result = await client.query(
                    `INSERT INTO temporal_metric_records
                     (entity_id, provider_name, metric_type, dimension,
                      value, occurred_at, sequence, payout, raw_data)
                     VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                     ON CONFLICT (entity_id, provider_name, occurred_at, dimension, sequence)
                     DO UPDATE SET
                         value = EXCLUDED.value,
                         payout = EXCLUDED.payout,
                         raw_data = EXCLUDED.raw_data,
                         updated_at = NOW()
                     RETURNING (xmax = 0) AS inserted`,
                    [
                        entityId,
                        record.provider_name,
                        record.metric_type || 'temporal_odds_1x2_full',
                        record.dimension,
                        record.value,
                        record.occurred_at,
                        record.sequence,
                        record.payout,
                        JSON.stringify(record.raw_data || {})
                    ]
                );

                if (result.rows[0].inserted) {
                    inserted++;
                } else {
                    updated++;
                }

            } catch (error) {
                // Single record failure doesn't break transaction
                skipped++;
                console.debug(JSON.stringify({
                    level: 'debug',
                    trace_id: traceId,
                    module: 'modules/sink',
                    message: 'Record skip',
                    error: error.message.substring(0, 100)
                }));
            }
        }

        await client.query('COMMIT');

        console.info(JSON.stringify({
            level: 'info',
            trace_id: traceId,
            module: 'modules/sink',
            message: 'Upsert complete',
            inserted,
            updated,
            skipped,
            total: records.length
        }));

        return {
            inserted,
            updated,
            skipped,
            total: records.length
        };

    } catch (error) {
        await client.query('ROLLBACK');
        throw new SinkError(
            'UPSERT_FAILED',
            `Batch upsert failed, transaction rolled back: ${error.message}`,
            traceId,
            { recordCount: records.length }
        );
    }
}

/**
 * Batch upsert with connection pool
 * @param {Pool} pool - Connection pool
 * @param {string} entityId - Entity UUID
 * @param {Array} records - Array of temporal records
 * @param {number} [batchSize] - Batch size
 * @returns {Promise<Object>} - Aggregated operation result
 */
async function batchUpsert(pool, entityId, records, batchSize) {
    const client = await pool.connect();
    const finalBatchSize = batchSize || SINK_CONFIG.defaultBatchSize;

    let totalInserted = 0;
    let totalUpdated = 0;
    let totalSkipped = 0;

    try {
        // Process in batches
        for (let i = 0; i < records.length; i += finalBatchSize) {
            const batch = records.slice(i, i + finalBatchSize);
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
// FULL SPECTRUM UPSERT
// ============================================================================

/**
 * Upsert full 1X2 temporal records (3 dimensions per point)
 * @param {import('pg').PoolClient} client - Database client
 * @param {string} entityId - Entity UUID
 * @param {Array} movementData - Array of temporal records
 * @returns {Promise<Object>} - Operation result
 */
async function upsertFullTemporalRecords(client, entityId, movementData) {
    if (!movementData || movementData.length === 0) {
        return { inserted: 0, updated: 0, skipped: 0, total_records: 0 };
    }

    const traceId = generateTraceId();
    let inserted = 0;
    let updated = 0;
    let skipped = 0;
    let totalRecords = 0;

    try {
        await client.query('BEGIN');

        for (const record of movementData) {
            // Insert 3 dimensions for each temporal point
            for (const dimension of ['home', 'draw', 'away']) {
                try {
                    const value = record[`${dimension}_odd`];

                    if (!value || value < 1 || value > 100) {
                        skipped++;
                        continue;
                    }

                    const result = await client.query(
                        `INSERT INTO temporal_metric_records
                            (entity_id, provider_name, metric_type, dimension,
                             value, occurred_at, sequence, payout, raw_data)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                        ON CONFLICT (entity_id, provider_name, occurred_at, dimension, sequence)
                        DO UPDATE SET
                            value = EXCLUDED.value,
                            payout = EXCLUDED.payout,
                            raw_data = EXCLUDED.raw_data,
                            updated_at = NOW()
                        RETURNING (xmax = 0) AS inserted`,
                        [
                            entityId,
                            record.provider_name || 'unknown',
                            'temporal_odds_1x2_full',
                            dimension,
                            value,
                            record.timestamp,
                            record.sequence,
                            record.payout,
                            JSON.stringify(record.raw_data || {})
                        ]
                    );

                    totalRecords++;

                    if (result.rows[0].inserted) {
                        inserted++;
                    } else {
                        updated++;
                    }

                } catch (error) {
                    skipped++;
                }
            }
        }

        await client.query('COMMIT');

        console.info(JSON.stringify({
            level: 'info',
            trace_id: traceId,
            module: 'modules/sink',
            message: 'Full spectrum upsert complete',
            inserted,
            updated,
            skipped,
            total_records: totalRecords,
            temporal_points: movementData.length
        }));

        return {
            inserted,
            updated,
            skipped,
            total_records: totalRecords,
            temporal_points: movementData.length
        };

    } catch (error) {
        await client.query('ROLLBACK');
        throw new SinkError(
            'FULL_SPECTRUM_UPSERT_FAILED',
            `Batch upsert failed, transaction rolled back: ${error.message}`,
            traceId,
            { recordCount: movementData.length }
        );
    }
}

// ============================================================================
// QUERY HELPERS
// ============================================================================

/**
 * Get record count for entity
 * @param {Pool} pool - Connection pool
 * @param {string} entityId - Entity UUID
 * @returns {Promise<Object>} - Count statistics
 */
async function getRecordCount(pool, entityId) {
    const client = await pool.connect();

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

    } finally {
        client.release();
    }
}

/**
 * Check if entity has records
 * @param {Pool} pool - Connection pool
 * @param {string} entityId - Entity UUID
 * @returns {Promise<boolean>} - True if records exist
 */
async function entityHasRecords(pool, entityId) {
    const client = await pool.connect();

    try {
        const result = await client.query(
            `SELECT EXISTS(
                SELECT 1 FROM temporal_metric_records
                WHERE entity_id = $1
             ) as exists`,
            [entityId]
        );

        return result.rows[0].exists || false;

    } finally {
        client.release();
    }
}

// ============================================================================
// POOL CLEANUP
// ============================================================================

/**
 * Gracefully close connection pool
 * @param {Pool} pool - Connection pool to close
 * @returns {Promise<void>}
 */
async function closePool(pool) {
    if (!pool) return;

    try {
        await pool.end();
        console.info(JSON.stringify({
            level: 'info',
            module: 'modules/sink',
            message: 'Connection pool closed'
        }));
    } catch (error) {
        console.error(JSON.stringify({
            level: 'error',
            module: 'modules/sink',
            message: 'Pool close error',
            error: error.message
        }));
    }
}

// ============================================================================
// EXPORTS
// ============================================================================

module.exports = {
    // Connection management
    createPool,
    closePool,

    // Entity operations
    getOrCreateEntity,

    // Idempotent upsert
    upsertTemporalRecords,
    batchUpsert,
    upsertFullTemporalRecords,

    // Query helpers
    getRecordCount,
    entityHasRecords,

    // Error class
    SinkError,

    // Config
    SINK_CONFIG
};
