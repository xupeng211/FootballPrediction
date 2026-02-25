/**
 * V88.210 Transaction Trace Script
 */
'use strict';

const { Client } = require('pg');

async function testTransaction() {
    const client = new Client({
        host: '172.25.16.1',
        port: 5432,
        database: 'football_db',
        user: 'football_user',
        password: 'football_pass'
    });

    await client.connect();

    try {
        // Create test entity first
        const entityResult = await client.query(`
            INSERT INTO entities_mapping (source_system, source_id, entity_type, source_url, entity_name)
            VALUES ('oddsportal', $1, 'match', $2, $3)
            ON CONFLICT (source_system, source_id, entity_type)
            DO UPDATE SET source_url = EXCLUDED.source_url
            RETURNING entity_id
        `, [`V88_210_TRACE_${Date.now()}`, 'https://trace-test.com', 'TraceTest']);

        const entityId = entityResult.rows[0].entity_id;
        console.log(`Entity ID: ${entityId}`);

        // Start transaction
        console.log('Starting transaction...');
        await client.query('BEGIN');

        // Insert test record
        console.log('Inserting test record...');
        const insertResult = await client.query(`
            INSERT INTO temporal_metric_records
                (entity_id, provider_name, metric_type, dimension, value, occurred_at, sequence, payout)
            VALUES ($1, $2, $3, $4, $5, NOW(), 0, 0.95)
            RETURNING id, (xmax = 0) AS inserted
        `, [entityId, 'TRACE_TEST', 'test_metric', 'home', 2.50]);

        console.log(`Insert result: ${JSON.stringify(insertResult.rows)}`);

        // Verify within transaction
        console.log('Verifying within transaction...');
        const verifyInTx = await client.query(`
            SELECT COUNT(*) as count FROM temporal_metric_records WHERE entity_id = $1
        `, [entityId]);

        console.log(`Records in transaction: ${verifyInTx.rows[0].count}`);

        // Commit
        console.log('Committing transaction...');
        await client.query('COMMIT');

        // Verify after commit
        console.log('Verifying after commit...');
        const verifyAfterCommit = await client.query(`
            SELECT COUNT(*) as count FROM temporal_metric_records WHERE entity_id = $1
        `, [entityId]);

        console.log(`Records after commit: ${verifyAfterCommit.rows[0].count}`);

        // Get all records
        const allRecords = await client.query(`
            SELECT id, entity_id, provider_name, dimension, value, created_at
            FROM temporal_metric_records
            WHERE entity_id = $1
        `, [entityId]);

        console.log(`All records: ${JSON.stringify(allRecords.rows, null, 2)}`);

    } catch (error) {
        console.error(`Error: ${error.message}`);
        await client.query('ROLLBACK');
    } finally {
        await client.end();
    }
}

testTransaction();
