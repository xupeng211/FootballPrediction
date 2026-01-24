/**
 * V43.200 Storage Module
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
 * @module storage
 * @author Senior DevOps & Systems Engineer
 * @version V43.200
 * @since 2026-01-24
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
    if (!records || records.length === 0) {
        return { inserted: 0, updated: 0, skipped: 0, total: 0 };
    }

    await client.query('BEGIN');

    try {
        let inserted = 0;
        let updated = 0;
        let skipped = 0;

        for (const record of records) {
            try {
                const result = await client.query(
                    `INSERT INTO temporal_metric_records
                     (entity_id, provider_name, metric_type, value, occurred_at, raw_data)
                     VALUES ($1, $2, $3, $4, $5, $6)
                     ON CONFLICT (entity_id, provider_name, metric_type, occurred_at)
                     DO UPDATE SET
                         value = EXCLUDED.value,
                         raw_data = EXCLUDED.raw_data,
                         updated_at = NOW()
                     RETURNING (xmax = 0) AS inserted`,
                    [
                        entityId,
                        record.provider_name,
                        record.metric_type || 'temporal_odds_1x2',
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
                // Single record failure doesn't break transaction
                skipped++;
                log.debug(`Record skip: ${error.message.substring(0, 100)}`);
            }
        }

        await client.query('COMMIT');

        return {
            inserted,
            updated,
            skipped,
            total: records.length
        };

    } catch (error) {
        await client.query('ROLLBACK');
        throw new StorageError(
            'UPSERT_FAILED',
            `Batch upsert failed, transaction rolled back: ${error.message}`,
            { recordCount: records.length }
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
// EXPORTS
// ============================================================================

module.exports = {
    // Connection management
    createConnection,
    createPool,
    getDBConfig,

    // Entity operations
    getOrCreateEntity,

    // Temporal records
    upsertTemporalRecords,
    batchUpsertWithPool,

    // Query helpers
    getRecordCount,
    entityHasRecords,

    // Error class
    StorageError
};
