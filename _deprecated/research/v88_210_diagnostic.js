/**
 * V88.210 Diagnostic Script
 * Test UPSERT logic directly
 */
'use strict';

const storage = require('./modules/storage');

async function testUpsert() {
    const client = await storage.createConnection();

    try {
        // Create test entity
        const sourceId = `V88_210_DIAG_${Date.now()}`;
        const entityId = await storage.getOrCreateEntity(
            client,
            sourceId,
            'https://test.com',
            'match'
        );

        console.log(`Entity created: ${entityId}`);

        // Test data
        const testData = [{
            timestamp: new Date().toISOString(),
            home_odd: 2.50,
            draw_odd: 3.20,
            away_odd: 2.80,
            payout: 0.95,
            sequence: 0,
            provider_name: 'DIAG_TEST',
            raw_data: { test: true }
        }];

        console.log(`Test data: ${JSON.stringify(testData)}`);

        // Execute upsert
        const result = await storage.upsertFullTemporalRecords(client, entityId, testData);

        console.log(`UPSERT result: ${JSON.stringify(result, null, 2)}`);

        // Verify with direct SQL
        const verifyResult = await client.query(`
            SELECT id, entity_id, provider_name, dimension, value, sequence, created_at
            FROM temporal_metric_records
            WHERE entity_id = $1
            ORDER BY created_at DESC
        `, [entityId]);

        console.log(`Verified records: ${verifyResult.rows.length}`);
        console.log(`Records: ${JSON.stringify(verifyResult.rows, null, 2)}`);

        // Commit transaction
        await client.query('COMMIT');

    } catch (error) {
        console.error(`Error: ${error.message}`);
        console.error(error.stack);
        await client.query('ROLLBACK');
    } finally {
        await client.end();
    }
}

testUpsert().then(() => {
    console.log('Test complete');
    process.exit(0);
}).catch(err => {
    console.error('Fatal error:', err);
    process.exit(1);
});
