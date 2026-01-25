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
                    log.debug(`Dimension skip [${dimension}]: ${error.message.substring(0, 100)}`);
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
    StorageError
};
