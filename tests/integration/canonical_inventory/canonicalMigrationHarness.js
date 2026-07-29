'use strict';

// lifecycle: test-fixture
// Disposable-only migration ledger used to prove V26.10 checksum, rollback and
// resume behavior. It is not a persistent migration operator.

const crypto = require('node:crypto');

function checksum(sql) {
    return crypto.createHash('sha256').update(sql, 'utf8').digest('hex');
}

async function ensureMigrationLedger(client) {
    await client.query(`
        CREATE TABLE IF NOT EXISTS public.m3_canonical_schema_migrations (
            version VARCHAR(32) PRIMARY KEY,
            filename TEXT NOT NULL UNIQUE,
            sha256_checksum CHAR(64) NOT NULL,
            applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            applied_by TEXT NOT NULL
        )
    `);
}

async function applyDisposableMigration(client, { version, filename, sql, expectedChecksum = checksum(sql) }) {
    await client.query('BEGIN');
    try {
        const existing = await client.query(
            'SELECT sha256_checksum FROM public.m3_canonical_schema_migrations WHERE version = $1 FOR UPDATE',
            [version]
        );
        if (existing.rowCount === 1) {
            if (existing.rows[0].sha256_checksum !== expectedChecksum) {
                throw Object.assign(new Error('migration checksum conflict'), { code: 'MIGRATION_CHECKSUM_CONFLICT' });
            }
            await client.query('COMMIT');
            return { status: 'already_applied', checksum: expectedChecksum };
        }
        await client.query(sql);
        await client.query(
            `
            INSERT INTO public.m3_canonical_schema_migrations
                (version, filename, sha256_checksum, applied_by)
            VALUES ($1, $2, $3, current_user)
        `,
            [version, filename, expectedChecksum]
        );
        await client.query('COMMIT');
        return { status: 'applied', checksum: expectedChecksum };
    } catch (error) {
        await client.query('ROLLBACK');
        throw error;
    }
}

module.exports = { applyDisposableMigration, checksum, ensureMigrationLedger };
