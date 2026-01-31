/**
 * V88.210 UPSERT Param Test
 * Test exact parameters used by upsertFullTemporalRecords
 */
'use strict';

const { Client } = require('pg');

async function testExactUpsert() {
    const client = new Client({
        host: '172.25.16.1',
        port: 5432,
        database: 'football_db',
        user: 'football_user',
        password: 'football_pass'
    });

    await client.connect();

    try {
        // Create entity
        const entityResult = await client.query(`
            INSERT INTO entities_mapping (source_system, source_id, entity_type, source_url, entity_name)
            VALUES ('oddsportal', $1, 'match', $2, $3)
            ON CONFLICT (source_system, source_id, entity_type)
            DO UPDATE SET source_url = EXCLUDED.source_url
            RETURNING entity_id
        `, [`V88_210_PARAM_${Date.now()}`, 'https://param-test.com', 'ParamTest']);

        const entityId = entityResult.rows[0].entity_id;
        console.log(`Entity ID: ${entityId}`);

        await client.query('BEGIN');

        // Exact same INSERT as upsertFullTemporalRecords
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

        const testParams = [
            entityId,
            'TEST_PROVIDER',
            'temporal_odds_1x2_full',
            'home',
            2.5,
            new Date().toISOString(),
            0,
            0.95,
            JSON.stringify({ test: true })
        ];

        console.log('Executing INSERT with exact params...');
        const result = await client.query(query, testParams);

        console.log(`Insert result: ${JSON.stringify(result.rows)}`);

        // Verify
        const verify = await client.query(`
            SELECT id, entity_id, provider_name, metric_type, dimension, value
            FROM temporal_metric_records
            WHERE entity_id = $1
        `, [entityId]);

        console.log(`Verification: ${verify.rows.length} records`);
        console.log(`Records: ${JSON.stringify(verify.rows, null, 2)}`);

        await client.query('COMMIT');

        console.log('Committed successfully');

    } catch (error) {
        console.error(`Error: ${error.message}`);
        console.error(`Detail: ${error.detail}`);
        console.error(`Hint: ${error.hint}`);
        await client.query('ROLLBACK');
    } finally {
        await client.end();
    }
}

testExactUpsert();
